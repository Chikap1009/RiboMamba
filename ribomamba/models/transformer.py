"""Bidirectional Transformer denoiser for masked diffusion (Phase 2, D-010).

Interface shared by every backbone in this project (so the diffusion code
never needs to know which one it is talking to):

    logits = model(input_ids, attention_mask)
        input_ids       (B, L)  int64   letters, <mask> or <pad>
        attention_mask  (B, L)  bool    True = real position, False = padding
        logits          (B, L, V=8)     raw scores per token id; special tokens are -inf

Shape flow:
    (B, L) ids --embed--> (B, L, d) --N x Block--> (B, L, d) --LayerNorm, head--> (B, L, V)
"""

from dataclasses import dataclass

import torch
import torch.nn as nn
import torch.nn.functional as F

from ribomamba.data.tokenizer import SPECIAL_TOKENS, VOCAB, VOCAB_SIZE


@dataclass
class TransformerConfig:
    d_model: int = 384        # width d: numbers describing each position
    n_layers: int = 8         # N blocks
    n_heads: int = 6          # h attention heads; head size d/h = 64
    mlp_ratio: int = 4        # MLP expands d -> 4d -> d
    rope_base: float = 10000.0
    vocab_size: int = VOCAB_SIZE


class RotaryEmbedding(nn.Module):
    """RoPE: rotate each (even, odd) pair of features at position m by angle m * theta_k.

    Treat features (2k, 2k+1) as one complex number z = x_2k + j x_2k+1 and
    multiply by e^{j m theta_k}. Then q_m . k_n depends only on m - n, because
    e^{j m theta} * conj(e^{j n theta}) = e^{j (m - n) theta}.
    theta_k = base^(-2k / head_dim): a bank of frequencies from 1 rad/position
    (resolves neighbours) down to ~1/base (resolves long distances). No weights.
    """

    def __init__(self, head_dim: int, base: float):
        super().__init__()
        theta = base ** (-torch.arange(0, head_dim, 2, dtype=torch.float32) / head_dim)  # (head_dim/2,)
        self.register_buffer("theta", theta, persistent=False)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x: (B, H, L, head_dim)
        positions = torch.arange(x.shape[-2], device=x.device, dtype=torch.float32)       # (L,)
        angles = torch.outer(positions, self.theta)                                       # (L, head_dim/2)
        cos, sin = angles.cos(), angles.sin()
        real, imag = x[..., 0::2].float(), x[..., 1::2].float()                           # (B, H, L, head_dim/2) each
        rotated = torch.stack([real * cos - imag * sin,                                   # complex multiply:
                               real * sin + imag * cos], dim=-1)                          # (B, H, L, head_dim/2, 2)
        return rotated.flatten(-2).type_as(x)                                             # (B, H, L, head_dim)


class SelfAttention(nn.Module):
    """Multi-head bidirectional self-attention with RoPE and a padding mask."""

    def __init__(self, cfg: TransformerConfig):
        super().__init__()
        assert cfg.d_model % cfg.n_heads == 0, "d_model must divide evenly into heads"
        self.n_heads = cfg.n_heads
        self.head_dim = cfg.d_model // cfg.n_heads
        self.qkv = nn.Linear(cfg.d_model, 3 * cfg.d_model, bias=False)   # W_Q, W_K, W_V in one matrix
        self.out = nn.Linear(cfg.d_model, cfg.d_model, bias=False)       # W_O: mixes the heads
        self.rope = RotaryEmbedding(self.head_dim, cfg.rope_base)

    def forward(self, x: torch.Tensor, attention_mask: torch.Tensor) -> torch.Tensor:
        B, L, d = x.shape                                                 # x: (B, L, d)
        q, k, v = (self.qkv(x)                                            # (B, L, 3d)
                   .view(B, L, 3, self.n_heads, self.head_dim)            # (B, L, 3, H, head_dim)
                   .permute(2, 0, 3, 1, 4))                               # (3, B, H, L, head_dim)
        q, k = self.rope(q), self.rope(k)                                 # positions enter here only
        # Boolean mask for PyTorch's fused attention: True = "this key may be looked at".
        # (B, 1, 1, L) broadcasts over heads and over query positions: nobody attends to padding.
        o = F.scaled_dot_product_attention(q, k, v, attn_mask=attention_mask[:, None, None, :])  # (B, H, L, head_dim)
        o = o.transpose(1, 2).reshape(B, L, d)                            # (B, L, d): heads side by side
        return self.out(o)                                                # (B, L, d)


class Block(nn.Module):
    """Pre-norm Transformer block: x + Attn(LN(x)), then x + MLP(LN(x))."""

    def __init__(self, cfg: TransformerConfig):
        super().__init__()
        d, hidden = cfg.d_model, cfg.mlp_ratio * cfg.d_model
        self.norm1 = nn.LayerNorm(d)
        self.attn = SelfAttention(cfg)
        self.norm2 = nn.LayerNorm(d)
        self.mlp = nn.Sequential(nn.Linear(d, hidden, bias=False), nn.GELU(), nn.Linear(hidden, d, bias=False))

    def forward(self, x: torch.Tensor, attention_mask: torch.Tensor) -> torch.Tensor:
        x = x + self.attn(self.norm1(x), attention_mask)    # communicate between positions (B, L, d)
        x = x + self.mlp(self.norm2(x))                      # think within each position   (B, L, d)
        return x


class TransformerDenoiser(nn.Module):
    """Embedding -> N blocks -> LayerNorm -> linear head; special tokens can never be predicted."""

    def __init__(self, cfg: TransformerConfig):
        super().__init__()
        self.cfg = cfg
        self.embed = nn.Embedding(cfg.vocab_size, cfg.d_model)
        self.blocks = nn.ModuleList(Block(cfg) for _ in range(cfg.n_layers))
        self.norm = nn.LayerNorm(cfg.d_model)
        self.head = nn.Linear(cfg.d_model, cfg.vocab_size, bias=False)
        forbidden = torch.tensor([token in SPECIAL_TOKENS for token in VOCAB])    # (V,) True for <pad> <mask> <bos> <eos>
        self.register_buffer("forbidden", forbidden, persistent=False)
        self.apply(self._init_weights)
        # Each block ADDS its attention and MLP outputs to the residual stream. With
        # 2N additions, starting those output layers smaller (std / sqrt(2N)) keeps the
        # stream's size roughly constant with depth at initialisation (GPT-2's recipe).
        for block in self.blocks:
            for layer in (block.attn.out, block.mlp[2]):
                nn.init.normal_(layer.weight, mean=0.0, std=0.02 / (2 * cfg.n_layers) ** 0.5)

    @staticmethod
    def _init_weights(module: nn.Module) -> None:
        # Small random starting weights (normal, std 0.02), the standard GPT/BERT choice.
        if isinstance(module, (nn.Linear, nn.Embedding)):
            nn.init.normal_(module.weight, mean=0.0, std=0.02)

    def forward(self, input_ids: torch.Tensor, attention_mask: torch.Tensor) -> torch.Tensor:
        x = self.embed(input_ids)                            # (B, L) -> (B, L, d)
        for block in self.blocks:
            x = block(x, attention_mask)                     # (B, L, d)
        logits = self.head(self.norm(x))                     # (B, L, V)
        return logits.masked_fill(self.forbidden, float("-inf"))   # specials: probability exactly 0


def count_parameters(model: nn.Module) -> int:
    return sum(p.numel() for p in model.parameters())
