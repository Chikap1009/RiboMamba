"""Stage C candidate: a learned critic that ranks coordinated mutations before they are folded.

See docs/experiments/2026-09-27-stageC-repair-critic.md for the hypothesis,
data provenance, decision rule and prior-art caveats. Summary:

  example  (target structure, parent sequence, parent per-position defects,
           child sequence, Delta E(target) child - parent)
           -> Delta log10 P(target) (child - parent) and "improved" (> 0)
  source   SAMFEO trajectories (unfiltered, defaults) on TRAINING-pool puzzles
           only; parent defects recomputed with scoring.score (the same
           numbers SAMFEO passes to its mutation function)
  model    ~0.8 M-parameter bidirectional Transformer (the project's RoPE
           blocks) over per-position features; a global feature token carries
           Delta E(target) and the length; head reads the global token and the
           mean over changed positions
  use      FILTERS["critic"] in baselines.py: rank SAMFEO's K children, fold the best
"""

import math
from dataclasses import dataclass

import numpy as np
import polars as pl
import torch
import torch.nn as nn
import torch.nn.functional as F

from ribomamba.eval.folding import pair_table
from ribomamba.models.transformer import Block, TransformerConfig

LOG10E = math.log10(math.e)
NT = {"A": 0, "C": 1, "G": 2, "U": 3}
BRACKET = {".": 0, "(": 1, ")": 2}
DELTA_CLIP = 3.0                     # |Delta log10 P| clipped for the regression target
MAX_LEN = 256


@dataclass
class CriticConfig:
    d_model: int = 128
    n_layers: int = 4
    n_heads: int = 4
    dropout: float = 0.1


def encode_example(structure: str, parent: str, child: str, defect: np.ndarray, delta_e: float,
                   pt: list[int] | None = None) -> dict:
    """Integer/float feature arrays for one (parent -> child) proposal; length L = len(structure)."""
    pt = pt if pt is not None else pair_table(structure)
    L = len(structure)
    partner = np.asarray(pt)
    p = np.array([NT[c] for c in parent], dtype=np.int8)            # int8: ~0.7 GB for 273K examples, not ~4 GB
    c = np.array([NT[x] for x in child], dtype=np.int8)
    paired = partner >= 0
    p_partner = np.full(L, 4, dtype=np.int8)
    c_partner = np.full(L, 4, dtype=np.int8)
    p_partner[paired] = p[partner[paired]]
    c_partner[paired] = c[partner[paired]]
    return {"parent": p, "child": c, "bracket": np.array([BRACKET[x] for x in structure], dtype=np.int8),
            "changed": (p != c).astype(np.int8), "p_partner": p_partner, "c_partner": c_partner,
            "defect": np.asarray(defect, dtype=np.float32), "delta_e": np.float32(delta_e),
            "length": np.float32(L / MAX_LEN)}


def collate(examples: list[dict], device) -> dict:
    L = max(len(e["parent"]) for e in examples)
    B = len(examples)
    out = {k: torch.zeros((B, L), dtype=torch.long) for k in ("parent", "child", "bracket", "changed",
                                                              "p_partner", "c_partner")}
    out["defect"] = torch.zeros((B, L))
    out["mask"] = torch.zeros((B, L + 1), dtype=torch.bool)
    for b, e in enumerate(examples):
        n = len(e["parent"])
        for k in ("parent", "child", "bracket", "changed", "p_partner", "c_partner"):
            out[k][b, :n] = torch.from_numpy(e[k]).long()
        out["defect"][b, :n] = torch.from_numpy(e["defect"])
        out["mask"][b, :n + 1] = True                              # +1: the global token (position 0)
    out["globals"] = torch.tensor([[e["delta_e"], e["length"]] for e in examples], dtype=torch.float32)
    return {k: v.to(device) for k, v in out.items()}


class Critic(nn.Module):
    def __init__(self, cfg: CriticConfig = CriticConfig()):
        super().__init__()
        d = cfg.d_model
        self.cfg = cfg
        self.parent = nn.Embedding(4, d)
        self.child = nn.Embedding(4, d)
        self.bracket = nn.Embedding(3, d)
        self.changed = nn.Embedding(2, d)
        self.p_partner = nn.Embedding(5, d)
        self.c_partner = nn.Embedding(5, d)
        self.defect = nn.Linear(1, d)
        self.globals = nn.Linear(2, d)
        self.global_token = nn.Parameter(torch.zeros(d))
        tcfg = TransformerConfig(d_model=d, n_layers=cfg.n_layers, n_heads=cfg.n_heads, dropout=cfg.dropout)
        self.blocks = nn.ModuleList(Block(tcfg) for _ in range(cfg.n_layers))
        self.norm = nn.LayerNorm(d)
        self.head = nn.Sequential(nn.Linear(2 * d, d), nn.GELU(), nn.Linear(d, 2))   # (delta, improve logit)

    def forward(self, batch: dict) -> torch.Tensor:
        x = (self.parent(batch["parent"]) + self.child(batch["child"]) + self.bracket(batch["bracket"])
             + self.changed(batch["changed"]) + self.p_partner(batch["p_partner"])
             + self.c_partner(batch["c_partner"]) + self.defect(batch["defect"][..., None]))      # (B, L, d)
        g = (self.global_token + self.globals(batch["globals"]))[:, None, :]                      # (B, 1, d)
        x = torch.cat([g, x], dim=1)                                                              # (B, L+1, d)
        for block in self.blocks:
            x = block(x, batch["mask"])
        x = self.norm(x)
        changed = batch["changed"].float()[..., None]                                             # (B, L, 1)
        pooled = (x[:, 1:] * changed).sum(1) / changed.sum(1).clamp(min=1)                        # (B, d)
        return self.head(torch.cat([x[:, 0], pooled], dim=-1))                                    # (B, 2)


def loss_fn(out: torch.Tensor, delta: torch.Tensor, improved: torch.Tensor) -> torch.Tensor:
    target = delta.clamp(-DELTA_CLIP, DELTA_CLIP)
    return F.huber_loss(out[:, 0], target) + F.binary_cross_entropy_with_logits(out[:, 1], improved)


def transitions_from_traces(traces: pl.DataFrame) -> pl.DataFrame:
    """(target_id, seed, parent sequence, child sequence, Delta log10 P, Delta E, improved) per evaluated child."""
    rows = []
    for (target_id, seed), unit in traces.group_by(["target_id", "seed"]):
        unit = unit.sort("eval_index")
        seqs = unit["sequence"].to_list()
        logp = unit["log_p_target"].to_numpy()
        energy = unit["target_energy"].to_numpy()
        for k, parent in enumerate(unit["parent_index"].to_list()):
            if parent < 0 or not (np.isfinite(logp[k]) and np.isfinite(logp[parent])):
                continue
            rows.append({"target_id": target_id, "seed": seed, "parent": seqs[parent], "child": seqs[k],
                         "delta": float((logp[k] - logp[parent]) * LOG10E),
                         "delta_e": float(energy[k] - energy[parent]), "improved": bool(logp[k] > logp[parent])})
    return pl.DataFrame(rows)


class CriticScorer:
    """FILTERS-compatible scorer: lower score = better child (the negated predicted improvement)."""

    def __init__(self, path, device: str | None = None):
        device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        state = torch.load(path, map_location="cpu", weights_only=False)
        self.model = Critic(CriticConfig(**state["config"])).to(device).eval()
        self.model.load_state_dict(state["model"])
        self.device = device

    @torch.no_grad()
    def __call__(self, target, parent: str, children: list[str], defect_list, evaluate) -> list[float]:
        import time

        import RNA

        from ribomamba.eval.folding import model_details
        start = time.perf_counter()
        md = model_details()
        e_parent = RNA.fold_compound(parent, md).eval_structure(target.structure)
        e_children = [RNA.fold_compound(c, md).eval_structure(target.structure) for c in children]
        evaluate.internal.eval += 1 + len(children)
        batch = collate([encode_example(target.structure, parent, c, np.asarray(defect_list), e - e_parent,
                                        target.pt) for c, e in zip(children, e_children)], self.device)
        with torch.autocast("cuda", dtype=torch.bfloat16, enabled=self.device == "cuda"):
            out = self.model(batch).float()
        evaluate.model_calls += 1
        evaluate.model_wall_s += time.perf_counter() - start
        return (-out[:, 0]).cpu().tolist()
