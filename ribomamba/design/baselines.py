"""External design baselines, run through the same Evaluator as the controls (Stage A, item 6).

SAMFEO — Zhou, Dai, Li, Ward, Mathews & Huang (2023), "RNA design via
structure-aware multifrontier ensemble optimization", Bioinformatics 39(S1):i563.
  source   https://github.com/shanry/SAMFEO, branch main, pinned at SAMFEO_COMMIT
           (2026-08-29). The ISMB 2023 reference code is branch ismb2023 (5afd050);
           main is the authors' current, numerically revised implementation.
  license  NO license file and no GitHub-detected license at this commit
           (checked 2026-09-27). Used locally for research comparison only: it is
           cloned unmodified into external/SAMFEO (ignored by Git), never vendored
           or redistributed. Resolve with the authors before any code release.
  run      its own samfeo() function, imported (not reimplemented), with its
           defaults: probability-defect objective, k = 10 frontier, T = 1,
           targeted 'cg' initialisation, structured mutation, MFE bookkeeping.
           Seed: its repeat convention, numpy seed 2020 + 2021 * seed.
  changes  none to its source. At run time only: (1) the RNA module inside its
           utils.vienna is replaced by a proxy that builds every fold compound
           with this project's EXPLICIT model details (identical to ViennaRNA's
           defaults: 37 C, dangles 2, Turner 2004, lonely pairs) and counts every
           mfe / pf / subopt / structure-evaluation call; (2) its candidate
           evaluation and mutation functions are wrapped to log each candidate
           (with its parent) through the Evaluator and to stop at the budget;
           (3) its stdout goes to the unit's log; (4) its module-level
           multiprocessing.set_start_method("fork") and its pandas import (used
           only for batch CSV output, which is not called) are neutralised.
  budget   one SAMFEO candidate evaluation = one Evaluator proposal. SAMFEO never
           re-evaluates a sequence (history set), so its internal calls per
           candidate are exact: 1 zero-band subopt (includes an MFE fill),
           1 partition function, 1 structure probability. The harness re-scores
           each candidate with scoring.score (measurement, counted separately as
           oracle calls), so every method's endpoints come from identical code.
           It stops itself when P(target) > 0.99 (its STOP rule): 'early_stop'.

RNAinverse (ViennaRNA 2.7.2, RNA.inverse_fold) — a sanity control only.
  Each restart is one adaptive walk returning one candidate; the walk's internal
  folds are NOT countable from Python, so internal calls are recorded as
  unavailable and its cost is wall time only. Restart 0 starts from the shared
  start, later restarts from fresh targeted-initialisation designs.
"""

import contextlib
import importlib.util
import multiprocessing
import subprocess
import sys
import types
from pathlib import Path

import numpy as np
import RNA

from ribomamba.design.scoring import Counters
from ribomamba.design.search import BudgetExhausted, Evaluator, Target, random_design, rng_for, shared_start
from ribomamba.eval.folding import model_details
from ribomamba.paths import EXTERNAL_DIR

SAMFEO_URL = "https://github.com/shanry/SAMFEO.git"
SAMFEO_COMMIT = "e78b4b5dc6082b0e832e0ed388f18d78e4bf7a5d"
SAMFEO_DIR = EXTERNAL_DIR / "SAMFEO"
SAMFEO_SETTINGS = {"objective": "pd", "k": 10, "t": 1.0, "init": "cg", "structured_mutation": True,
                   "check_mfe": True, "stay": 2000, "commit": SAMFEO_COMMIT}
SAMFEO_EFILTER_SETTINGS = {**SAMFEO_SETTINGS, "filter": "energy", "filter_k": 8}
SAMFEO_CFILTER_SETTINGS = {**SAMFEO_SETTINGS, "filter": "critic", "filter_k": 8,
                           "critic_ckpt": "checkpoints/critic_v1/critic.pt"}
RNAINVERSE_SETTINGS = {"mode": "mfe (RNA.inverse_fold)", "restart_start": "shared start, then targeted init"}


class CountingFoldCompound:
    """A ViennaRNA fold compound that counts oracle calls into a Counters object."""
    _COUNTED = {"mfe": "mfe", "pf": "pf", "subopt": "subopt", "subopt_cb": "subopt",
                "eval_structure": "eval", "pr_structure": "eval"}

    def __init__(self, fc, owner):
        self._fc, self._owner = fc, owner

    def __getattr__(self, name):
        attr = getattr(self._fc, name)
        kind = self._COUNTED.get(name)
        if kind is None:
            return attr

        def counted(*args, **kwargs):
            counters = self._owner.counters
            setattr(counters, kind, getattr(counters, kind) + 1)
            return attr(*args, **kwargs)
        return counted


class CountingRNA(types.ModuleType):
    """Stands in for the RNA module inside a baseline: explicit model details, counted calls."""

    def __init__(self):
        super().__init__("RNA")
        self.counters = Counters()

    def fold_compound(self, sequence, md=None, *args):
        return CountingFoldCompound(RNA.fold_compound(sequence, md if md is not None else model_details(), *args),
                                    self)

    def __getattr__(self, name):
        return getattr(RNA, name)


_SAMFEO = None


def samfeo_checkout_problem(path: Path = SAMFEO_DIR) -> str | None:
    """None if the pinned, unmodified checkout is present; otherwise what is wrong."""
    if not (path / "main.py").exists():
        return f"no SAMFEO checkout at {path} (git clone {SAMFEO_URL} {path}; git -C {path} checkout {SAMFEO_COMMIT})"
    head = subprocess.run(["git", "-C", str(path), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    if head != SAMFEO_COMMIT:
        return f"SAMFEO checkout is at {head or 'unknown'}, pinned {SAMFEO_COMMIT}"
    dirty = subprocess.run(["git", "-C", str(path), "status", "--porcelain", "--untracked-files=no"],
                           capture_output=True, text=True).stdout.strip()
    if dirty:
        return f"SAMFEO checkout has local modifications:\n{dirty}"
    return None


def load_samfeo(path: Path = SAMFEO_DIR):
    """Import the pinned SAMFEO main.py once per process; returns (module, counting RNA proxy)."""
    global _SAMFEO
    if _SAMFEO is not None:
        return _SAMFEO
    problem = samfeo_checkout_problem(path)
    if problem:
        raise RuntimeError(problem)
    if "utils" in sys.modules and not str(getattr(sys.modules["utils"], "__file__", "")).startswith(str(path)):
        raise RuntimeError("a different module named 'utils' is already imported; SAMFEO's would clash")
    stubbed_pandas = "pandas" not in sys.modules and importlib.util.find_spec("pandas") is None
    if stubbed_pandas:
        stub = types.ModuleType("pandas")
        stub.__getattr__ = lambda name: (_ for _ in ()).throw(
            RuntimeError(f"pandas.{name} used: SAMFEO batch output is not supported here"))
        sys.modules["pandas"] = stub
    set_start_method = multiprocessing.set_start_method
    multiprocessing.set_start_method = lambda *a, **k: None
    sys.path.insert(0, str(path))
    try:
        spec = importlib.util.spec_from_file_location("samfeo_main", path / "main.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    finally:
        sys.path.remove(str(path))
        multiprocessing.set_start_method = set_start_method
        if stubbed_pandas:
            del sys.modules["pandas"]
    proxy = CountingRNA()
    sys.modules["utils.vienna"].RNA = proxy
    _SAMFEO = (module, proxy)
    return _SAMFEO


def samfeo(target: Target, seed: int, evaluate: Evaluator, settings: dict, log=None) -> None:
    """Run SAMFEO until the Evaluator's budget is spent (BudgetExhausted) or it stops itself."""
    module, proxy = load_samfeo()
    s = {**SAMFEO_SETTINGS, **settings}
    if s["commit"] != SAMFEO_COMMIT:
        raise ValueError(f"settings name SAMFEO commit {s['commit']}, loaded {SAMFEO_COMMIT}")
    proxy.counters = evaluate.internal
    module.seed_np = 2020 + seed * 2021
    module.objective_name = {"pd": "probability_defect", "ned": "ensemble_defect"}[s["objective"]]
    module.name_pair = s["init"]
    module.STAY = s["stay"]
    originals = {name: getattr(module, name) for name in ("position_ed_pd_mfe", "mutate_structured",
                                                          "mutate_tradition")}
    parents: dict[str, str] = {}

    def evaluated(sequence, structure):
        evaluate.check()                                   # stop BEFORE SAMFEO spends oracle calls
        out = originals["position_ed_pd_mfe"](sequence, structure)
        defect_list, negative_prob, _ = out
        objective = negative_prob if s["objective"] == "pd" else float(np.mean(defect_list)) - 1
        parent = evaluate.first_index.get(parents.get(sequence), -1)
        evaluate(sequence, parent=parent, objective=float(objective))
        return out

    def logging_mutation(mutate):
        def wrapped(sequence, *args, **kwargs):
            child = mutate(sequence, *args, **kwargs)
            parents[child] = sequence                        # the last child made is the one evaluated
            return child
        return wrapped

    def filtered_mutation(mutate, scorer, k):
        """Draw k children with SAMFEO's own mutation; keep the one the scorer ranks best (lowest).

        Children already evaluated are skipped (SAMFEO would reject them anyway); if every
        draw was already evaluated, the last is returned and SAMFEO's own retry loop runs.
        """
        def wrapped(sequence, pairs, defect_list, *args, **kwargs):
            children, child = [], None
            for _ in range(k):
                child = mutate(sequence, pairs, defect_list, *args, **kwargs)
                if child not in evaluate.first_index and child not in children:
                    children.append(child)
            if not children:
                parents[child] = sequence
                return child
            scores = scorer(target, sequence, children, defect_list, evaluate)
            best = children[int(np.argmin(scores))]
            parents[best] = sequence
            return best
        return wrapped

    module.position_ed_pd_mfe = evaluated
    if s.get("filter"):
        scorer = make_filter(s)
        module.mutate_structured = filtered_mutation(originals["mutate_structured"], scorer, s["filter_k"])
        module.mutate_tradition = filtered_mutation(originals["mutate_tradition"], scorer, s["filter_k"])
    else:
        module.mutate_structured = logging_mutation(originals["mutate_structured"])
        module.mutate_tradition = logging_mutation(originals["mutate_tradition"])
    try:
        with contextlib.redirect_stdout(log if log is not None else open("/dev/null", "w")):
            module.samfeo(target.structure, evaluate.budget, k=s["k"], t=s["t"], check_mfe=s["check_mfe"],
                          sm=s["structured_mutation"])
    finally:
        for name, fn in originals.items():
            setattr(module, name, fn)


def energy_scores(target: Target, parent: str, children: list[str], defect_list, evaluate: Evaluator) -> list[float]:
    """Non-neural filter: E(target structure) of each child, kcal/mol (lower = target more stable).

    One O(n) structure evaluation per child, counted as the method's own eval calls.
    """
    md = model_details()
    evaluate.internal.eval += len(children)
    return [RNA.fold_compound(c, md).eval_structure(target.structure) for c in children]


FILTERS = {"energy": energy_scores}
_CRITICS: dict = {}


def make_filter(settings: dict):
    """The scorer named by settings["filter"]; a learned critic is loaded once per process."""
    if settings["filter"] == "critic":
        from ribomamba.design.critic import CriticScorer
        from ribomamba.paths import REPO_ROOT
        path = str(REPO_ROOT / settings["critic_ckpt"])
        if path not in _CRITICS:
            _CRITICS[path] = CriticScorer(path)
        return _CRITICS[path]
    return FILTERS[settings["filter"]]


def samfeo_cfilter(target: Target, seed: int, evaluate: Evaluator, settings: dict, log=None) -> None:
    """SAMFEO with its mutations pre-screened by the learned critic (best of filter_k)."""
    samfeo(target, seed, evaluate, {**SAMFEO_CFILTER_SETTINGS, **settings}, log)


def samfeo_efilter(target: Target, seed: int, evaluate: Evaluator, settings: dict, log=None) -> None:
    """SAMFEO with its mutations pre-screened by target energy (best of filter_k); otherwise unchanged."""
    samfeo(target, seed, evaluate, {**SAMFEO_EFILTER_SETTINGS, **settings}, log)


def rnainverse(target: Target, seed: int, evaluate: Evaluator, settings: dict, log=None) -> None:
    """RNAinverse restarts until the budget is spent; internal calls unavailable (see module docstring)."""
    evaluate.internal_available = False
    rng = rng_for("rnainverse", target.id, seed)
    RNA.init_rand(int(rng.integers(2**31 - 1)))
    start = shared_start(target, seed)
    while True:
        evaluate.check()
        designed, distance = RNA.inverse_fold(start, target.structure)
        evaluate(designed.upper(), objective=float(distance))
        start = random_design(target, rng)


BASELINES = {"samfeo": samfeo, "rnainverse": rnainverse, "samfeo_efilter": samfeo_efilter,
             "samfeo_cfilter": samfeo_cfilter}
BASELINE_SETTINGS = {"samfeo": SAMFEO_SETTINGS, "rnainverse": RNAINVERSE_SETTINGS,
                     "samfeo_efilter": SAMFEO_EFILTER_SETTINGS, "samfeo_cfilter": SAMFEO_CFILTER_SETTINGS}
__all__ = ["BASELINES", "BASELINE_SETTINGS", "BudgetExhausted", "load_samfeo", "samfeo_checkout_problem"]
