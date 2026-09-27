"""Target-conditioned masked-diffusion denoiser: the Phase 2 Transformer plus zero-initialised adapters.

docs/experiments/2026-09-28-target-conditioned-denoiser.md. The base TransformerDenoiser is used
unchanged; two adapters add the target structure:

  bracket embedding   E_b[bracket_i] added to the token embedding, bracket in
                      {0 '.', 1 '(', 2 ')', 3 special (<bos>, <eos>, <pad>)}
  pair messages       after block l: h_i += W_l LayerNorm_l(h_partner(i)) for every position i
                      that the TARGET pairs (partner(i) = i otherwise, and the message is masked)

Both are initialised to zero, so before training the model computes exactly what the base does.

Inputs use the framed layout of Phase 2: position 0 is <bos>, 1..L the nucleotides, L+1 <eos>.
partner_index holds, per framed position, the framed index of its target partner or -1.
"""

import torch
import torch.nn as nn
import torch.nn.functional as F

from ribomamba.models.transformer import TransformerConfig, TransformerDenoiser

BRACKET = {".": 0, "(": 1, ")": 2}
SPECIAL_BRACKET = 3


class ConditionedDenoiser(nn.Module):
    def __init__(self, cfg: TransformerConfig):
        super().__init__()
        self.base = TransformerDenoiser(cfg)
        d = cfg.d_model
        self.bracket = nn.Embedding(4, d)
        self.pair_norm = nn.ModuleList(nn.LayerNorm(d) for _ in range(cfg.n_layers))
        self.pair_proj = nn.ModuleList(nn.Linear(d, d, bias=False) for _ in range(cfg.n_layers))
        nn.init.zeros_(self.bracket.weight)
        for proj in self.pair_proj:
            nn.init.zeros_(proj.weight)

    @classmethod
    def from_unconditional(cls, base: TransformerDenoiser) -> "ConditionedDenoiser":
        model = cls(base.cfg)
        model.base.load_state_dict(base.state_dict())
        return model

    def adapter_parameters(self):
        return list(self.bracket.parameters()) + list(self.pair_norm.parameters()) + list(self.pair_proj.parameters())

    def forward(self, input_ids: torch.Tensor, attention_mask: torch.Tensor, bracket_ids: torch.Tensor,
                partner_index: torch.Tensor) -> torch.Tensor:
        b = self.base
        x = b.embed(input_ids) + self.bracket(bracket_ids)                        # (B, W, d)
        has_partner = (partner_index >= 0)[..., None]                             # (B, W, 1)
        gather_idx = partner_index.clamp(min=0)[..., None].expand(-1, -1, x.shape[-1])
        for block, norm, proj in zip(b.blocks, self.pair_norm, self.pair_proj):
            x = block(x, attention_mask)
            partner = torch.gather(x, 1, gather_idx)                              # (B, W, d) h_partner(i)
            x = x + proj(norm(partner)) * has_partner
        logits = b.head(b.norm(x))
        return logits.masked_fill(b.forbidden, float("-inf"))


def structure_inputs(structures: list[str], width: int, device) -> tuple[torch.Tensor, torch.Tensor]:
    """(bracket_ids, partner_index), each (B, width), in the framed layout (<bos> at 0)."""
    from ribomamba.eval.folding import pair_table
    B = len(structures)
    bracket = torch.full((B, width), SPECIAL_BRACKET, dtype=torch.long)
    partner = torch.full((B, width), -1, dtype=torch.long)
    for k, s in enumerate(structures):
        pt = pair_table(s)
        bracket[k, 1:len(s) + 1] = torch.tensor([BRACKET[c] for c in s])
        idx = torch.tensor(pt)
        paired = idx >= 0
        partner[k, 1:len(s) + 1][paired] = idx[paired] + 1
    return bracket.to(device), partner.to(device)


def conditioned_nelbo(model: ConditionedDenoiser, input_ids: torch.Tensor, attention_mask: torch.Tensor,
                      bracket_ids: torch.Tensor, partner_index: torch.Tensor,
                      generator: torch.Generator | None = None) -> tuple[torch.Tensor, dict]:
    """The Phase 2 masked-diffusion NELBO, conditioned on the target structure (nats per nucleotide)."""
    import math

    from ribomamba.data.tokenizer import is_nucleotide
    from ribomamba.diffusion.masked import mask_tokens, masked_nelbo, sample_times
    t = sample_times(input_ids.shape[0], input_ids.device, generator)
    z, is_masked = mask_tokens(input_ids, t, generator)
    logits = model(z, attention_mask, bracket_ids, partner_index)
    per_sequence = masked_nelbo(logits, input_ids, is_masked, t)
    n = is_nucleotide(input_ids).sum()
    loss = per_sequence.sum() / n
    return loss, {"bits_per_nt": loss.detach() / math.log(2)}
