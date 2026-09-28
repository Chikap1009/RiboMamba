"""Budgeted candidate evaluation and the cheap, non-neural design controls (Stage A, item 5).

Evaluator  one (method, target, seed) unit: scores proposals with scoring.score,
           caches repeated sequences, enforces the budget and a wall-clock
           deadline, and keeps one trace row per proposal.

Budget unit: one candidate evaluation = one proposal scored, INCLUDING the
initial candidate and including cache hits (a method that re-proposes a
sequence spends budget but no oracle call). Oracle calls (cache misses) are
counted separately, by kind, so quality can be plotted against either.

Controls (all start from the same shared start per target and seed, drawn
from the targeted initialisation also used by SAMFEO: every target pair G-C
or C-G at random, every unpaired position A):

  random_pairs         independent designs from that same distribution; no search
  random_pair_edits    (1+1) local search; each proposal resamples 1 or 2
                       structural sites (a site is a target pair, always
                       resampled to a different canonical pair, or an unpaired
                       position, resampled to a different base); the 2nd site
                       is a sequence neighbour of the 1st (a stem/loop edit);
                       sites chosen uniformly. Accept if NED does not increase.
  feedback_pair_edits  the same moves, sizes, acceptance and objective, but the
                       1st site is drawn in proportion to its ensemble defect
                       (+ FEEDBACK_FLOOR) and the 2nd is the site holding the
                       strongest competing partner of the 1st, when that
                       pairing probability is >= COMPETITOR_MIN; otherwise
                       another defect-weighted site.

The two edit controls differ ONLY in where the edit goes, which is the contrast
Stage B needs (feedback-selected versus random masks, identical proposals).
"""

import hashlib
import math
import time
from dataclasses import dataclass, field

import numpy as np

from ribomamba.design.scoring import Counters, Score, score
from ribomamba.eval.folding import pair_table

PAIRS = ("AU", "UA", "GC", "CG", "GU", "UG")
BASES = "ACGU"
INIT_PAIRS = ("GC", "CG")
INIT_UNPAIRED = "A"
TWO_SITE_PROB = 0.5
FEEDBACK_FLOOR = 0.01
COMPETITOR_MIN = 0.1


class BudgetExhausted(Exception):
    """The unit has used its whole candidate budget."""


class TimeLimitReached(Exception):
    """The unit's own method-time limit (final protocol) is used up: a terminal outcome."""


class DeadlineReached(Exception):
    """The run's wall-clock cap passed while this unit was running."""


def rng_for(*parts) -> np.random.Generator:
    """A generator seeded by a stable hash of its labels (independent of Python's hash salt)."""
    digest = hashlib.sha256("\x1f".join(map(str, parts)).encode()).digest()
    return np.random.default_rng(int.from_bytes(digest[:16], "little"))


@dataclass
class Target:
    id: str
    structure: str
    pt: list[int] = field(init=False)
    sites: list[tuple[int, ...]] = field(init=False)      # (i,) unpaired or (i, j) paired, i < j
    site_of: np.ndarray = field(init=False)               # position -> site index

    def __post_init__(self):
        self.pt = pair_table(self.structure)
        self.sites = [(i,) if j < 0 else (i, j) for i, j in enumerate(self.pt) if j < 0 or j > i]
        self.site_of = np.empty(len(self.structure), dtype=int)
        for k, site in enumerate(self.sites):
            self.site_of[list(site)] = k

    def __len__(self):
        return len(self.structure)


@dataclass
class Candidate:
    index: int
    sequence: str
    score: Score

    @property
    def objective(self) -> float:
        return self.score.objective


class Evaluator:
    """Scores proposals for one unit; see the module docstring for the budget rule."""

    def __init__(self, target: Target, budget: int, deadline: float = math.inf, time_limit_s: float | None = None,
                 subtract_scoring: bool = False):
        self.target, self.budget, self.deadline = target, budget, deadline
        self.time_limit_s, self.subtract_scoring = time_limit_s, subtract_scoring
        self.oracle = Counters()          # the harness's own scoring calls (cache misses only)
        self.internal = Counters()        # calls an external baseline makes inside itself
        self.internal_available = True    # False when a baseline's internal calls cannot be counted
        self.cache: dict[str, Score] = {}
        self.first_index: dict[str, int] = {}
        self.rows: list[dict] = []
        self.cache_misses = 0
        self.score_wall_s = 0.0
        self.model_calls = 0              # neural proposal forward passes (Stage B)
        self.model_wall_s = 0.0
        self.proposal_calls = 0           # calls of a host method's mutation hook (every method, incl. re-calls)
        self.proposal_wall_s = 0.0        # wall time inside those hooks (drafts, model, screen, dedup)
        self.t0, self.c0 = time.perf_counter(), time.process_time()

    @property
    def count(self) -> int:
        return len(self.rows)

    def check(self, method_time_s: float | None = None) -> None:
        """Raise before any more work if the budget or the deadline is used up.

        method_time_s: for candidates replayed from an external run (DesiRNA, SamplingDesign), the
        method's own time for that candidate; the unit time limit is judged on it, not on the
        harness clock (which already includes the whole external run by the time of the replay).
        """
        if self.count >= self.budget:
            raise BudgetExhausted
        if time.time() > self.deadline:
            raise DeadlineReached
        if self.time_limit_s is not None:
            used = self.method_time() if method_time_s is None else method_time_s
            if used > self.time_limit_s:
                raise TimeLimitReached

    def method_time(self) -> float:
        """Seconds of the method's own work so far (monotonic clock, so a machine suspend is excluded);
        harness re-scoring is excluded for methods that score candidates themselves."""
        return time.perf_counter() - self.t0 - (self.score_wall_s if self.subtract_scoring else 0.0)

    def __call__(self, sequence: str, parent: int = -1, objective: float | None = None,
                 method_time_s: float | None = None) -> Candidate:
        """Score one proposal. method_time_s: for replayed external runs (DesiRNA), the method's own
        time at which this candidate existed; recorded as elapsed_s instead of the harness clock."""
        self.check(method_time_s)
        hit = sequence in self.cache
        if not hit:
            result = score(sequence, self.target.structure, self.target.pt, self.oracle)
            self.cache[sequence] = result
            self.cache_misses += 1
            self.score_wall_s += result.wall_s
        result = self.cache[sequence]
        index = self.count
        self.first_index.setdefault(sequence, index)
        if parent >= 0:
            before = self.rows[parent]["sequence"]
            changed = [k for k, (a, b) in enumerate(zip(before, sequence)) if a != b]
        else:
            changed = []
        self.rows.append({
            "eval_index": index, "parent_index": parent, "changed_positions": changed, "cache_hit": hit,
            "objective": result.objective if objective is None else objective, **result.row(),
            "cum_proposals": index + 1, "cum_cache_misses": self.cache_misses,
            **self.oracle.as_dict("cum_oracle_"),
            **{k: (v if self.internal_available else None) for k, v in self.internal.as_dict("cum_internal_").items()},
            "elapsed_s": time.perf_counter() - self.t0 if method_time_s is None else method_time_s,
            "cpu_s": time.process_time() - self.c0,
            "score_wall_s": self.score_wall_s, "cum_model_calls": self.model_calls, "model_wall_s": self.model_wall_s,
        })
        return Candidate(index, sequence, result)


# ---- designs and moves ------------------------------------------------------------------------

def random_design(target: Target, rng: np.random.Generator, pairs=INIT_PAIRS, unpaired=INIT_UNPAIRED) -> str:
    seq = [""] * len(target)
    for site in target.sites:
        if len(site) == 2:
            seq[site[0]], seq[site[1]] = pairs[int(rng.integers(len(pairs)))]
        else:
            seq[site[0]] = unpaired[int(rng.integers(len(unpaired)))]
    return "".join(seq)


def shared_start(target: Target, seed: int) -> str:
    """The start every repair method shares for this target and seed (independent of the method)."""
    return random_design(target, rng_for("shared_start", target.id, seed))


def resample(sequence: str, target: Target, site_indices: list[int], rng: np.random.Generator) -> str:
    """Change every chosen site: a pair to a different canonical pair, an unpaired base to a different base."""
    seq = list(sequence)
    for k in site_indices:
        site = target.sites[k]
        if len(site) == 2:
            i, j = site
            options = [p for p in PAIRS if p != seq[i] + seq[j]]
            seq[i], seq[j] = options[int(rng.integers(len(options)))]
        else:
            options = [b for b in BASES if b != seq[site[0]]]
            seq[site[0]] = options[int(rng.integers(len(options)))]
    return "".join(seq)


def neighbour_site(target: Target, first: int, rng: np.random.Generator) -> int | None:
    """A site adjacent in sequence to any position of `first` (for a pair: the stacked neighbour, usually)."""
    near = {p + d for p in target.sites[first] for d in (-1, 1)} & set(range(len(target)))
    options = sorted({int(target.site_of[p]) for p in near} - {first})
    return options[int(rng.integers(len(options)))] if options else None


def pick_random_sites(target: Target, current: Score, rng: np.random.Generator) -> list[int]:
    first = int(rng.integers(len(target.sites)))
    if rng.random() < TWO_SITE_PROB:
        second = neighbour_site(target, first, rng)
        if second is not None:
            return [first, second]
    return [first]


def site_defects(target: Target, current: Score) -> np.ndarray:
    return np.array([current.defect[list(site)].mean() for site in target.sites])


def pick_feedback_sites(target: Target, current: Score, rng: np.random.Generator) -> list[int]:
    if current.defect is None:                                # a failed score carries no feedback
        return pick_random_sites(target, current, rng)
    weights = site_defects(target, current) + FEEDBACK_FLOOR
    first = int(rng.choice(len(weights), p=weights / weights.sum()))
    if rng.random() < TWO_SITE_PROB and len(target.sites) > 1:
        positions = list(target.sites[first])
        best = max(positions, key=lambda p: current.competitor_p[p])
        if current.competitor_p[best] >= COMPETITOR_MIN:
            second = int(target.site_of[current.competitor[best]])
            if second != first:
                return [first, second]
        weights[first] = 0.0
        return [first, int(rng.choice(len(weights), p=weights / weights.sum()))]
    return [first]


# ---- methods: (target, seed, evaluator, settings) -> None; they run until the budget is spent ------

def random_pairs(target: Target, seed: int, evaluate: Evaluator, settings: dict) -> None:
    evaluate(shared_start(target, seed))
    rng = rng_for("random_pairs", target.id, seed)
    while True:
        evaluate(random_design(target, rng))


def _local_search(target: Target, seed: int, evaluate: Evaluator, pick, name: str) -> None:
    current = evaluate(shared_start(target, seed))
    rng = rng_for(name, target.id, seed)
    while True:
        child = resample(current.sequence, target, pick(target, current.score, rng), rng)
        proposal = evaluate(child, parent=current.index)
        if proposal.objective <= current.objective:          # ties accepted: neutral drift
            current = proposal


def random_pair_edits(target: Target, seed: int, evaluate: Evaluator, settings: dict) -> None:
    _local_search(target, seed, evaluate, pick_random_sites, "random_pair_edits")


def feedback_pair_edits(target: Target, seed: int, evaluate: Evaluator, settings: dict) -> None:
    _local_search(target, seed, evaluate, pick_feedback_sites, "feedback_pair_edits")


CONTROLS = {
    "random_pairs": random_pairs,
    "random_pair_edits": random_pair_edits,
    "feedback_pair_edits": feedback_pair_edits,
}
CONTROL_SETTINGS = {
    "random_pairs": {"init_pairs": list(INIT_PAIRS), "init_unpaired": INIT_UNPAIRED},
    "random_pair_edits": {"two_site_prob": TWO_SITE_PROB, "acceptance": "NED non-increasing",
                          "second_site": "sequence neighbour"},
    "feedback_pair_edits": {"two_site_prob": TWO_SITE_PROB, "acceptance": "NED non-increasing",
                            "site_weight": f"site defect + {FEEDBACK_FLOOR}",
                            "second_site": f"strongest competitor if p >= {COMPETITOR_MIN}, else defect-weighted"},
}
