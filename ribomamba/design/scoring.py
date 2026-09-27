"""Robust scoring of one candidate design against one target structure (Stage A).

Same oracle as ribomamba.eval.folding: ViennaRNA 2.7.2, Turner 2004, 37 C,
dangles = 2, lonely pairs allowed. Unlike fold_one, a candidate that cannot
form the target never raises: it is scored as a failure, with its own folding
feedback kept.

Why p_target is set here, not read from ViennaRNA. For a target pair the
candidate cannot form (e.g. G-A), ViennaRNA 2.7.2 does NOT refuse:
eval_structure returns a finite energy and pr_structure a non-zero probability
(GGGAAAACC against (((...))): 1.10 kcal/mol, p = 0.070, checked 2026-09-27).
The target's true Boltzmann weight is zero, so p_target = 0 and
log_p_target = -inf are assigned explicitly. The same holds for a pair
enclosing fewer than MIN_HAIRPIN nucleotides.

The ensemble defect needs no such patch: it is defined from the candidate's
own base-pair probabilities P, which are valid for any target,

    d_i = 1 - P(i, t_i)          if the target pairs i with t_i
    d_i = 1 - (1 - sum_j P(i,j)) if the target leaves i unpaired
    NED = mean_i d_i

and ViennaRNA assigns P = 0 to a pair it cannot form, so an unformable
target pair contributes d_i = 1 to both of its ends, as it should.

MFE success, three tie policies (recorded separately, never merged):
  mfe_backtrack  ViennaRNA's backtracked MFE structure equals the target
                 (RNAfold's convention; ties broken by its backtracking)
  mfe_any        the target's energy equals the MFE (the target is AN
                 optimal structure; ties allowed)
  umfe           the target is the UNIQUE optimal structure (strictest;
                 the pilot's primary success endpoint)
umfe needs a suboptimal enumeration at zero energy band, run only when mfe_any
holds and counted as a subopt call.
"""

import math
import time
from dataclasses import dataclass, field

import numpy as np
import RNA

from ribomamba.eval.folding import CANONICAL_PAIRS, MIN_HAIRPIN, TEMPERATURE_C, model_details, pair_table

KT = (TEMPERATURE_C + 273.15) * 1.98717 / 1000     # RT in kcal/mol, ViennaRNA's gas constant
NUCLEOTIDES = frozenset("ACGU")
SUCCESS_POLICIES = ("umfe", "mfe_backtrack", "mfe_any")
PRIMARY_SUCCESS = "umfe"


@dataclass
class Counters:
    """Oracle calls, counted by kind: a partition function costs more than an MFE fold."""
    mfe: int = 0
    pf: int = 0
    subopt: int = 0
    eval: int = 0          # eval_structure: O(n), cheap, counted for completeness

    def add(self, other: "Counters") -> None:
        for k in ("mfe", "pf", "subopt", "eval"):
            setattr(self, k, getattr(self, k) + getattr(other, k))

    def as_dict(self, prefix: str = "") -> dict:
        return {f"{prefix}{k}": getattr(self, k) for k in ("mfe", "pf", "subopt", "eval")}


@dataclass
class Score:
    """Everything the trace records about one candidate, plus per-position feedback arrays."""
    sequence: str
    valid: bool = True                   # A/C/G/U only and the target's length
    error: str | None = None             # why scoring failed, if it did
    mfe_structure: str | None = None
    mfe_energy: float = math.nan
    ensemble_energy: float = math.nan    # -RT ln Z
    target_feasible: bool = False        # every target pair canonical on this sequence, hairpins >= 3
    infeasible_pairs: int = 0
    target_energy: float = math.nan      # NaN when infeasible
    mfe_backtrack: bool = False
    mfe_any: bool = False
    umfe: bool = False
    mfe_ties: int = 0                    # optimal structures, counted only when mfe_any (else 0)
    bp_distance: int = -1
    p_target: float = 0.0
    log_p_target: float = -math.inf
    ned: float = math.nan
    wall_s: float = 0.0
    defect: np.ndarray | None = field(default=None, repr=False)        # (n,) per-position defect d_i
    competitor: np.ndarray | None = field(default=None, repr=False)    # (n,) most probable non-target partner (-1: none)
    competitor_p: np.ndarray | None = field(default=None, repr=False)  # (n,) its pairing probability

    @property
    def objective(self) -> float:
        """The repair methods' objective: NED, lower is better; a failed score is worst."""
        return self.ned if self.valid and self.error is None and not math.isnan(self.ned) else math.inf

    def success(self, policy: str = PRIMARY_SUCCESS) -> bool:
        return bool(getattr(self, policy))

    def row(self) -> dict:
        """Trace columns (scalars only)."""
        return {k: getattr(self, k) for k in (
            "sequence", "valid", "error", "mfe_structure", "mfe_energy", "ensemble_energy",
            "target_feasible", "infeasible_pairs", "target_energy", "mfe_backtrack", "mfe_any", "umfe",
            "mfe_ties", "bp_distance", "p_target", "log_p_target", "ned")}


def unformable_pairs(sequence: str, target_pt: list[int]) -> list[tuple[int, int]]:
    """Target pairs this sequence can never form: non-canonical letters, or < MIN_HAIRPIN enclosed."""
    return [(i, j) for i, j in enumerate(target_pt)
            if j > i and (sequence[i] + sequence[j] not in CANONICAL_PAIRS or j - i - 1 < MIN_HAIRPIN)]


def _energy_key(e: float) -> int:
    """Energies are whole 0.01 kcal/mol; compare them as integers, not floats."""
    return int(round(e * 100))


def positional_defect(P: np.ndarray, target_pt: list[int]) -> np.ndarray:
    """d_i from a symmetric pair-probability matrix P (n, n) and the target's partner list."""
    n = len(target_pt)
    pt = np.asarray(target_pt)
    paired = pt >= 0
    unpaired_prob = 1.0 - P.sum(axis=1)                               # (n,) q_i
    d = np.empty(n)
    d[paired] = 1.0 - P[np.flatnonzero(paired), pt[paired]]
    d[~paired] = 1.0 - unpaired_prob[~paired]
    return np.clip(d, 0.0, 1.0)                                       # float noise can leave -1e-16


def score(sequence: str, target: str, target_pt: list[int] | None = None,
          counters: Counters | None = None) -> Score:
    """Score one candidate. Never raises for a bad candidate; see the module docstring."""
    start = time.perf_counter()
    counters = counters if counters is not None else Counters()
    pt = target_pt if target_pt is not None else pair_table(target)
    s = Score(sequence=sequence)
    if len(sequence) != len(target) or not set(sequence) <= NUCLEOTIDES:
        s.valid = False
        s.error = (f"length {len(sequence)} != target {len(target)}" if len(sequence) != len(target)
                   else f"letters outside A/C/G/U: {sorted(set(sequence) - NUCLEOTIDES)}")
        s.wall_s = time.perf_counter() - start
        return s
    try:
        fc = RNA.fold_compound(sequence, model_details())
        mfe_structure, mfe = fc.mfe()
        counters.mfe += 1
        s.mfe_structure, s.mfe_energy = mfe_structure, round(mfe, 2)
        s.bp_distance = RNA.bp_distance(mfe_structure, target)
        bad = unformable_pairs(sequence, pt)
        s.infeasible_pairs = len(bad)
        s.target_feasible = not bad
        if s.target_feasible:
            s.target_energy = round(fc.eval_structure(target), 2)
            counters.eval += 1
            s.mfe_backtrack = mfe_structure == target
            s.mfe_any = _energy_key(s.target_energy) == _energy_key(s.mfe_energy)
            if s.mfe_backtrack and not s.mfe_any:
                raise RuntimeError(f"backtracked MFE equals target but energies differ "
                                   f"({s.target_energy} vs {s.mfe_energy})")
            if s.mfe_any:
                optimal = [o.structure for o in fc.subopt(0)]           # every structure at the MFE
                counters.subopt += 1
                s.mfe_ties = len(optimal)
                s.umfe = optimal == [target]
        fc.exp_params_rescale(mfe)
        _, ensemble_energy = fc.pf()
        counters.pf += 1
        s.ensemble_energy = round(ensemble_energy, 4)
        if s.target_feasible:
            s.p_target = fc.pr_structure(target)
            s.log_p_target = (ensemble_energy - s.target_energy) / KT   # exact even where p underflows
        upper = np.array(fc.bpp())[1:, 1:]                              # (n, n), upper triangle, 1-based dropped
        P = upper + upper.T
        s.defect = positional_defect(P, pt)
        s.ned = float(s.defect.mean())
        off = P.copy()
        idx = np.flatnonzero(np.asarray(pt) >= 0)
        off[idx, np.asarray(pt)[idx]] = 0.0                             # exclude each position's target partner
        s.competitor = off.argmax(axis=1)
        s.competitor_p = off.max(axis=1)
        s.competitor[s.competitor_p <= 0] = -1
    except Exception as e:                                              # recorded as a failed candidate, not dropped
        s.error = f"{type(e).__name__}: {e}"
    s.wall_s = time.perf_counter() - start
    return s
