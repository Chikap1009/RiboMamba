"""Sibling groups with rival banks for the competition-residual experiment.

Specification: docs/experiments/2026-09-27-competition-residual.md.

For a parent state of a SAMFEO search on a TRAINING-pool puzzle:
  1. score the parent (scoring.score: MFE + partition function) and draw a rival
     bank from its Boltzmann ensemble (one more partition function + stochastic
     backtracking; distinct structures other than the target, the R lowest-energy
     on the parent, plus the parent's MFE structure if it is not the target);
  2. draw K children with SAMFEO's own structured mutation (T = 1, the parent's
     positional defects), seeded; drop children equal to the parent or repeated;
  3. score EVERY child (full partition function) and evaluate every rival on it,
     but only where the rival can form on the child (all its pairs canonical);
     an incompatible rival's energy is stored as NaN and never used.

Labels (natural logs, RT = scoring.KT), from finite, unclipped oracle values:
  y = Delta ln P,  a = -Delta E_target / RT,  r = y - a = -Delta ln Z  (as first specified),
  c = Delta logit P - a = -Delta ln Z_rest, where Z_rest = Z - exp(-E_target/RT) is the
      partition function of every structure EXCEPT the target (the pure rival term).
Because ln P is monotone in logit P and logit P_child = logit P_parent + a + c, ranking
siblings by y is exactly ranking by a + c; c excludes the target's own weight, which
makes r ~ -a mechanically when P -> 1 (the saturation effect, amendment of 2026-09-27).
"""

import math
import time

import numpy as np
import RNA

from ribomamba.design.scoring import KT, score, unformable_pairs
from ribomamba.eval.folding import model_details, pair_table

K_CHILDREN = 16
N_SAMPLES = 200
R_RIVALS = 16


def rival_bank(parent: str, target: str, n_samples: int = N_SAMPLES, r_max: int = R_RIVALS,
               seed: int = 0) -> tuple[list[str], dict]:
    """Rival folds of the parent: distinct Boltzmann samples (not the target), lowest parent energy first."""
    t0 = time.perf_counter()
    RNA.init_rand(seed)
    fc = RNA.fold_compound(parent, model_details())
    mfe_structure, mfe = fc.mfe()
    fc.exp_params_rescale(mfe)
    fc.pf()
    samples = set(fc.pbacktrack(n_samples))
    if mfe_structure != target:
        samples.add(mfe_structure)
    samples.discard(target)
    ranked = sorted(samples, key=lambda s: (fc.eval_structure(s), s))[:r_max]   # the MFE, if a rival, sorts first
    cost = {"mfe": 1, "pf": 1, "pbacktrack_samples": n_samples, "eval": len(samples),
            "seconds": time.perf_counter() - t0}
    return ranked, cost


def rival_energies(sequence: str, rivals: list[str], pts: list[list[int]]) -> np.ndarray:
    """E(rival) on this sequence in kcal/mol; NaN where the rival cannot form on it."""
    fc = RNA.fold_compound(sequence, model_details())
    out = np.full(len(rivals), np.nan)
    for k, (s, pt) in enumerate(zip(rivals, pts)):
        if not unformable_pairs(sequence, pt):
            out[k] = fc.eval_structure(s)
    return out


def log_sum_exp_bank(e_target: float | None, energies: np.ndarray) -> float:
    """ln of the Boltzmann weight of the compatible rivals (plus the target unless e_target is None)."""
    terms = -energies[np.isfinite(energies)] / KT
    if e_target is not None:
        terms = np.concatenate([[-e_target / KT], terms])
    if len(terms) == 0:
        return -math.inf
    m = terms.max()
    return float(m + np.log(np.exp(terms - m).sum()))


def logit_from_ln_p(ln_p: float) -> float:
    """ln(P / (1 - P)) from ln P, stable for small P; +inf if P rounds to 1."""
    return ln_p - math.log(-math.expm1(ln_p)) if ln_p < 0 else math.inf


def sibling_group(target: str, parent: str, mutate, pairs, rng_seed: int, k: int = K_CHILDREN) -> dict:
    """One parent and its scored siblings. `mutate` and `pairs` are SAMFEO's mutate_structured and pairs_match."""
    t0 = time.perf_counter()
    pt = pair_table(target)
    p = score(parent, target, pt)
    if p.error or not p.target_feasible:
        raise ValueError(f"parent cannot be scored against its target: {p.error}")
    rivals, bank_cost = rival_bank(parent, target, seed=rng_seed % (2**31 - 1))
    rival_pts = [pair_table(s) for s in rivals]
    parent_rivals = rival_energies(parent, rivals, rival_pts)
    np.random.seed(rng_seed % (2**32 - 1))                          # SAMFEO's mutation uses numpy's global RNG
    children, drawn, same_as_parent, repeated = [], 0, 0, 0
    while len(children) < k and drawn < 20 * k:
        child = mutate(parent, pairs, list(p.defect), 1.0)
        drawn += 1
        if child == parent:
            same_as_parent += 1
        elif child in children:
            repeated += 1
        else:
            children.append(child)
    rows = []
    for child in children:
        c = score(child, target, pt)
        if c.error or not math.isfinite(c.log_p_target):
            raise ValueError(f"child could not be scored: {c.error}")
        energies = rival_energies(child, rivals, rival_pts)
        a = -(c.target_energy - p.target_energy) / KT
        y = c.log_p_target - p.log_p_target
        comp = logit_from_ln_p(c.log_p_target) - logit_from_ln_p(p.log_p_target) - a
        rest_child, rest_parent = log_sum_exp_bank(None, energies), log_sum_exp_bank(None, parent_rivals)
        rows.append({"child": child, "changed": [i for i, (x, z) in enumerate(zip(parent, child)) if x != z],
                     "y": y, "a": a, "r": y - a, "ln_p": c.log_p_target, "ensemble_energy": c.ensemble_energy,
                     "target_energy": c.target_energy, "ned": c.ned, "umfe": c.umfe,
                     "mfe_structure": c.mfe_structure, "rival_energy": energies.tolist(),
                     "rivals_compatible": int(np.isfinite(energies).sum()),
                     "r_bank": -(log_sum_exp_bank(c.target_energy, energies)
                                 - log_sum_exp_bank(p.target_energy, parent_rivals)),
                     "c": comp, "c_bank": (-(rest_child - rest_parent)
                                           if math.isfinite(rest_child) and math.isfinite(rest_parent) else math.nan)})
    return {"parent": parent, "parent_ln_p": p.log_p_target, "parent_target_energy": p.target_energy,
            "parent_ensemble_energy": p.ensemble_energy, "parent_ned": p.ned, "parent_umfe": p.umfe,
            "parent_defect": [float(x) for x in p.defect], "parent_mfe_structure": p.mfe_structure,
            "rivals": rivals, "parent_rival_energy": parent_rivals.tolist(), "children": rows,
            "draws": {"drawn": drawn, "same_as_parent": same_as_parent, "repeated": repeated, "kept": len(children)},
            "cost": {"child_scores": len(children), "parent_scores": 1, "rival_bank": bank_cost,
                     "rival_evals": len(rivals) * (len(children) + 1),
                     "seconds": time.perf_counter() - t0}}
