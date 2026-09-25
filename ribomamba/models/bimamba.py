"""Mamba-2 backbones for Phase 4: the bidirectional denoiser (BiMamba) and the left-to-right model.

Interface shared with TransformerDenoiser, so the diffusion code and the
evaluation harness never need to know which backbone they are talking to:

    logits = model(input_ids, attention_mask)
        input_ids       (B, L)  int64   letters, <mask>, <bos>/<eos> markers or <pad>
        attention_mask  (B, L)  bool    True = real position; padding must sit at the right end
        logits          (B, L, V=8)     raw scores per token id; forbidden tokens are -inf

Shape flow (d = 384, 14 layers; D-015, D-016):
    (B, L) ids --embed--> (B, L, d) --N x [x + Mixer(LayerNorm(x))]--> (B, L, d) --LayerNorm, head--> (B, L, V)

bidirectional=True  -> BiMamba denoiser for masked diffusion: each layer scans left-to-right AND
                       right-to-left; all four special tokens are forbidden outputs.
bidirectional=False -> autoregressive (AR) Mamba: one left-to-right scan, so position i sees only
                       positions <= i; its output at i predicts the token at i + 1, and <eos> is an
                       allowed output (it ends the sequence).

Everything except the mixer is the Transformer's: the same embedding, pre-norm residual blocks with
LayerNorm, final LayerNorm and untied linear head, so the comparison changes the mixing only.
"""

import math
from dataclasses import dataclass

import torch
import torch.nn as nn
from mamba_ssm.modules.mamba2 import Mamba2
from mamba_ssm.ops.triton.ssd_combined import mamba_split_conv1d_scan_combined

from ribomamba.data.tokenizer import EOS_ID, SPECIAL_TOKENS, VOCAB, VOCAB_SIZE


@dataclass
class MambaConfig:
    d_model: int = 384        # width d, as the Transformer (D-015: match parameters by depth)
    n_layers: int = 14        # 14 layers x ~1.0 M parameters ~ the Transformer's 14.17 M
    d_state: int = 128        # N: state numbers per channel (the library's Mamba-2 default)
    expand: int = 2           # channels inside the mixer: expand x d = 768
    headdim: int = 64         # channels per head; a head shares one keep factor per letter
    d_conv: int = 4           # width of the short causal convolution before the scan
    bidirectional: bool = True
    vocab_size: int = VOCAB_SIZE
    dropout: float = 0.0      # D-012: dropout on each residual branch during training


def reversal_index(attention_mask: torch.Tensor) -> torch.Tensor:
    """(B, L) index that reverses each sequence WITHIN ITS OWN LENGTH and leaves padding where it is.

    Example: mask [T, T, T, F, F] -> index [2, 1, 0, 3, 4], so  G G A <pad> <pad>  becomes  A G G <pad> <pad>.
    Reversing the whole row instead would put the padding FIRST, where the backward scan would write it
    into its state before any real letter (a scan has no attention mask to skip it). Applying the index
    twice restores the original order.
    """
    B, L = attention_mask.shape
    lengths = attention_mask.sum(dim=1, keepdim=True)                               # (B, 1)
    positions = torch.arange(L, device=attention_mask.device).expand(B, L)         # (B, L)
    return torch.where(positions < lengths, lengths - 1 - positions, positions)    # (B, L)


def reorder(x: torch.Tensor, index: torch.Tensor) -> torch.Tensor:
    """x (B, L, C) with its positions rearranged by index (B, L): out[b, i] = x[b, index[b, i]]."""
    return x.gather(1, index.unsqueeze(-1).expand(-1, -1, x.shape[-1]))


class BiMamba2Mixer(nn.Module):
    """One layer's sequence mixing, read in both directions (D-016).

    Shared by the two directions: in_proj (d -> z, x, B, C, dt) and out_proj (d_inner -> d), which hold
    almost 99 % of the layer's parameters. Each direction has its own short convolution, dt bias, A (the
    keep factors), D (the skip) and gate-normalisation weight, because RNA is read differently 5'->3' and
    3'->5' (e.g. a GC stack is worth -3.40 kcal/mol, a CG stack -2.40). The two scans' outputs are added,
    then projected once.
    """

    def __init__(self, cfg: MambaConfig):
        super().__init__()
        kwargs = dict(d_model=cfg.d_model, d_state=cfg.d_state, d_conv=cfg.d_conv, expand=cfg.expand,
                      headdim=cfg.headdim)
        self.fwd = Mamba2(**kwargs)          # built by the library, so every parameter gets Mamba's own init
        self.bwd = Mamba2(**kwargs)
        del self.bwd.in_proj, self.bwd.out_proj   # the backward scan uses the forward module's projections

    @staticmethod
    def _scan(zxbcdt: torch.Tensor, m: Mamba2) -> torch.Tensor:
        """Convolution + selective scan + gate/RMSNorm of one direction: (B, L, d_in_proj) -> (B, L, d_inner).

        The same fused kernel Mamba2.forward calls, with the same settings, minus the output projection.
        """
        return mamba_split_conv1d_scan_combined(
            zxbcdt, m.conv1d.weight.squeeze(1), m.conv1d.bias, m.dt_bias, -torch.exp(m.A_log.float()),
            D=m.D, chunk_size=m.chunk_size, activation=m.activation, rmsnorm_weight=m.norm.weight,
            rmsnorm_eps=m.norm.eps, outproj_weight=None, headdim=m.headdim, ngroups=m.ngroups,
            norm_before_gate=m.norm_before_gate)

    def forward(self, u: torch.Tensor, reverse: torch.Tensor) -> torch.Tensor:
        zxbcdt = self.fwd.in_proj(u)                                        # (B, L, 2*768 + 2*128 + 12 = 1804)
        y_fwd = self._scan(zxbcdt, self.fwd)                                # (B, L, 768) reads left to right
        # in_proj acts on each position separately, so reversing its output = projecting the reversed input
        y_bwd = reorder(self._scan(reorder(zxbcdt, reverse), self.bwd), reverse)   # (B, L, 768) right to left
        return self.fwd.out_proj(y_fwd + y_bwd)                             # (B, L, d)


class CausalMamba2Mixer(nn.Module):
    """The library's Mamba-2 layer unchanged: one left-to-right scan (the AR model)."""

    def __init__(self, cfg: MambaConfig):
        super().__init__()
        self.mamba = Mamba2(d_model=cfg.d_model, d_state=cfg.d_state, d_conv=cfg.d_conv, expand=cfg.expand,
                            headdim=cfg.headdim)

    def forward(self, u: torch.Tensor, reverse: torch.Tensor | None = None) -> torch.Tensor:
        return self.mamba(u)                                                # (B, L, d)


class MambaBlock(nn.Module):
    """Pre-norm residual block: x + Dropout(Mixer(LayerNorm(x))). No separate MLP: in a Mamba layer the
    expansion to 768 channels and the SiLU gate do the MLP's job (the standard Mamba design)."""

    def __init__(self, cfg: MambaConfig):
        super().__init__()
        self.norm = nn.LayerNorm(cfg.d_model)
        self.mixer = BiMamba2Mixer(cfg) if cfg.bidirectional else CausalMamba2Mixer(cfg)
        self.drop = nn.Dropout(cfg.dropout)

    def forward(self, x: torch.Tensor, reverse: torch.Tensor | None) -> torch.Tensor:
        return x + self.drop(self.mixer(self.norm(x), reverse))            # (B, L, d)


class MambaModel(nn.Module):
    """Embedding -> N Mamba blocks -> LayerNorm -> linear head, with forbidden outputs at -inf."""

    def __init__(self, cfg: MambaConfig):
        super().__init__()
        self.cfg = cfg
        self.embed = nn.Embedding(cfg.vocab_size, cfg.d_model)
        self.blocks = nn.ModuleList(MambaBlock(cfg) for _ in range(cfg.n_layers))
        self.norm = nn.LayerNorm(cfg.d_model)
        self.head = nn.Linear(cfg.d_model, cfg.vocab_size, bias=False)
        # The denoiser only ever predicts letters. The AR model must also be able to say "<eos>".
        allowed_special = set() if cfg.bidirectional else {VOCAB[EOS_ID]}
        forbidden = torch.tensor([t in SPECIAL_TOKENS and t not in allowed_special for t in VOCAB])   # (V,)
        self.register_buffer("forbidden", forbidden, persistent=False)
        # Initialisation. Embedding and head: normal(0, 0.02), as in the Transformer. Mixers: Mamba2's own
        # constructor (dt bias from its [0.001, 0.1] range, A in [1, 16], D = 1, PyTorch defaults for the
        # projections and the convolution), then the library's GPT-2-style rescale of each residual
        # branch's output layer by 1/sqrt(n_layers) (mamba_ssm/models/mixer_seq_simple.py, _init_weights),
        # so the residual stream's size stays roughly constant with depth.
        nn.init.normal_(self.embed.weight, mean=0.0, std=0.02)
        nn.init.normal_(self.head.weight, mean=0.0, std=0.02)
        for block in self.blocks:
            out_proj = block.mixer.fwd.out_proj if cfg.bidirectional else block.mixer.mamba.out_proj
            nn.init.kaiming_uniform_(out_proj.weight, a=math.sqrt(5))
            with torch.no_grad():
                out_proj.weight /= math.sqrt(cfg.n_layers)

    def forward(self, input_ids: torch.Tensor, attention_mask: torch.Tensor) -> torch.Tensor:
        lengths = attention_mask.sum(dim=1, keepdim=True)                                        # (B, 1)
        if not torch.equal(attention_mask, torch.arange(attention_mask.shape[1], device=lengths.device) < lengths):
            raise ValueError("padding must sit at the right end of every row (collate() guarantees this)")
        reverse = reversal_index(attention_mask) if self.cfg.bidirectional else None           # (B, L)
        x = self.embed(input_ids)                                                                # (B, L) -> (B, L, d)
        for block in self.blocks:
            x = block(x, reverse)                                                                # (B, L, d)
        logits = self.head(self.norm(x))                                                         # (B, L, V)
        return logits.masked_fill(self.forbidden, float("-inf"))


def expected_parameters(cfg: MambaConfig) -> int:
    """Parameter count from the layer shapes, written out so a test can pin it (the D-015 arithmetic)."""
    d, N, K, V = cfg.d_model, cfg.d_state, cfg.d_conv, cfg.vocab_size
    inner = cfg.expand * d
    heads = inner // cfg.headdim
    projections = d * (2 * inner + 2 * N + heads) + inner * d        # in_proj (z, x, B, C, dt) + out_proj
    per_direction = (inner + 2 * N) * (K + 1) + 3 * heads + inner     # conv weights + biases, dt_bias/A/D, gate norm
    layer = projections + per_direction * (2 if cfg.bidirectional else 1) + 2 * d     # + the block's LayerNorm
    return cfg.n_layers * layer + V * d + 2 * d + d * V                 # + embedding, final LayerNorm, head
