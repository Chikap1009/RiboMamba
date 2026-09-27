"""Per-position critics trained on sibling groups (competition-residual experiment, variants 6/7).

Three variants share the critic_v1 architecture (critic.py) and the same data:
  generic   predicts y = Delta ln P directly                          (score = y_hat)
  norival   predicts c = -Delta ln Z_rest; globals add a, parent logit (score = a + c_hat)
  rival     norival + per-position rival channels and rival globals   (score = a + c_hat)

Rival channels: the M strongest rivals of the parent (lowest parent energy first).
At each position i and for rival m, a state: 0 unpaired in the rival; 1 paired in the
rival exactly as in the target; 2 paired differently and formable on the child;
3 paired differently and NOT formable on the child (an incompatible fold contributes
no energy anywhere). Rival globals per rank: parent Boltzmann weight within the bank,
Delta E / RT on the child (0 if not formable), not-formable flag.
"""

import math

import numpy as np
import torch
import torch.nn as nn

from ribomamba.design.critic import Critic, CriticConfig, encode_example
from ribomamba.design.scoring import KT
from ribomamba.eval.folding import CANONICAL_PAIRS, pair_table

M_RIVALS = 4
VARIANTS = ("generic", "norival", "rival")


def encode_sibling(row: dict, variant: str, pt_cache: dict) -> dict:
    structure = row["structure"]
    pt = pt_cache.setdefault(structure, pair_table(structure))
    e = encode_example(structure, row["parent"], row["child"], np.asarray(row["parent_defect"]),
                       row["target_energy"] - row["parent_target_energy"], pt)
    lp = row["parent_ln_p"]
    parent_logit = lp - math.log(-math.expm1(lp)) if lp < 0 else 30.0
    extra = [row["a"] / 10, parent_logit / 10] if variant != "generic" else [0.0, 0.0]
    L = len(structure)
    states = np.zeros((M_RIVALS, L), dtype=np.int8)
    rival_globals = np.zeros(3 * M_RIVALS, dtype=np.float32)
    if variant == "rival":
        rivals = row["rivals"][:M_RIVALS]
        pe = np.asarray(row["parent_rival_energy"], dtype=float)
        ce = np.asarray(row["rival_energy"], dtype=float)
        if len(pe):
            w = np.exp(-(pe - pe.min()) / KT)
            w /= w.sum()
        child = row["child"]
        for m, s in enumerate(rivals):
            rpt = pair_table(s)
            for i, j in enumerate(rpt):
                if j < 0:
                    continue
                if j == pt[i]:
                    states[m, i] = 1
                elif child[i] + child[j] in CANONICAL_PAIRS:
                    states[m, i] = 2
                else:
                    states[m, i] = 3
            formable = math.isfinite(ce[m])
            rival_globals[3 * m:3 * m + 3] = [w[m], (ce[m] - pe[m]) / KT / 10 if formable else 0.0,
                                              0.0 if formable else 1.0]
    e["rival_states"] = states
    e["extra_globals"] = np.concatenate([np.asarray(extra, dtype=np.float32), rival_globals])
    return e


def collate_sibling(examples: list[dict], device) -> dict:
    from ribomamba.design.critic import collate
    batch = collate(examples, device)
    L = batch["parent"].shape[1]
    states = torch.zeros((len(examples), M_RIVALS, L), dtype=torch.long)
    for b, e in enumerate(examples):
        states[b, :, :e["rival_states"].shape[1]] = torch.from_numpy(e["rival_states"]).long()
    batch["rival_states"] = states.to(device)
    batch["extra_globals"] = torch.tensor(np.stack([e["extra_globals"] for e in examples]), device=device)
    return batch


class SiblingCritic(Critic):
    """critic_v1 plus optional extra globals and per-position rival channels; one regression output."""

    def __init__(self, cfg: CriticConfig = CriticConfig(), use_rivals: bool = False):
        super().__init__(cfg)
        d = cfg.d_model
        self.use_rivals = use_rivals
        self.extra = nn.Linear(2 + 3 * M_RIVALS, d)
        self.rival_state = nn.ModuleList(nn.Embedding(4, d) for _ in range(M_RIVALS)) if use_rivals else None

    def forward(self, batch: dict) -> torch.Tensor:
        x = (self.parent(batch["parent"]) + self.child(batch["child"]) + self.bracket(batch["bracket"])
             + self.changed(batch["changed"]) + self.p_partner(batch["p_partner"])
             + self.c_partner(batch["c_partner"]) + self.defect(batch["defect"][..., None]))
        if self.use_rivals:
            for m, emb in enumerate(self.rival_state):
                x = x + emb(batch["rival_states"][:, m])
        g = (self.global_token + self.globals(batch["globals"]) + self.extra(batch["extra_globals"]))[:, None, :]
        x = torch.cat([g, x], dim=1)
        for block in self.blocks:
            x = block(x, batch["mask"])
        x = self.norm(x)
        changed = batch["changed"].float()[..., None]
        pooled = (x[:, 1:] * changed).sum(1) / changed.sum(1).clamp(min=1)
        return self.head(torch.cat([x[:, 0], pooled], dim=-1))[:, 0]
