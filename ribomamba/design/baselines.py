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
import time
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
RNAINVERSE_SETTINGS = {"mode": "mfe (RNA.inverse_fold)", "restart_start": "shared start, then targeted init",
                       "max_restarts": None}


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
    if log is not None:                               # the settings that actually run, not only the registered ones
        log.write("effective settings: " + repr(sorted(s.items())) + "\n")
    if s["commit"] != SAMFEO_COMMIT:
        raise ValueError(f"settings name SAMFEO commit {s['commit']}, loaded {SAMFEO_COMMIT}")
    proxy.counters = evaluate.internal
    module.seed_np = 2020 + seed * 2021
    module.objective_name = {"pd": "probability_defect", "ned": "ensemble_defect"}[s["objective"]]
    module.name_pair = s["init"]
    module.STAY = s["stay"]
    originals = {name: getattr(module, name) for name in ("position_ed_pd_mfe", "mutate_structured",
                                                          "mutate_tradition", "init_k")}
    parents: dict[str, str] = {}

    def evaluated(sequence, structure):
        evaluate.check()                                   # stop BEFORE SAMFEO spends oracle calls
        out = originals["position_ed_pd_mfe"](sequence, structure)
        defect_list, negative_prob, _ = out
        objective = negative_prob if s["objective"] == "pd" else float(np.mean(defect_list)) - 1
        parent = evaluate.first_index.get(parents.get(sequence), -1)
        evaluate(sequence, parent=parent, objective=float(objective))
        return out

    def timed(hook):
        """Count every call of a mutation hook and its wall time (proposal overhead; no semantic change)."""
        def wrapped(*args, **kwargs):
            start = time.perf_counter()
            try:
                return hook(*args, **kwargs)
            finally:
                evaluate.proposal_calls += 1
                evaluate.proposal_wall_s += time.perf_counter() - start
        return wrapped

    def logging_mutation(mutate):
        def wrapped(sequence, *args, **kwargs):
            child = mutate(sequence, *args, **kwargs)
            parents[child] = sequence                        # the last child made is the one evaluated
            return child
        return timed(wrapped)

    eps = float(s.get("epsilon", 0.0))
    eps_rng = rng_for("filter_epsilon", target.id, seed)

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
            if eps > 0 and eps_rng.random() < eps:            # exploration: a random sibling, unscored
                best = children[int(eps_rng.integers(len(children)))]
                parents[best] = sequence
                return best
            scores = scorer(target, sequence, children, defect_list, evaluate)
            best = children[int(np.argmin(scores))]
            parents[best] = sequence
            return best
        return timed(wrapped)

    module.position_ed_pd_mfe = evaluated
    if s.get("proposal_model"):                      # SAMFEO picks the sites, the TCD picks the letters
        from ribomamba.design import tcd as _tcd
        tcd_model, tcd_device = _tcd.load(s["proposal_model"])
        tcd_rng = rng_for("tcd_proposal", target.id, seed)
        k_prop = int(s.get("filter_k", 1)) if s.get("filter") else 1
        scorer = make_filter(s) if s.get("filter") else None

        def tcd_mutation(sequence, pairs, defect_list, *args, **kwargs):
            start = time.perf_counter()
            drafts = [originals["mutate_structured"](sequence, pairs, defect_list, *args, **kwargs) for _ in range(k_prop)]
            masks = [[i for i, (x, y) in enumerate(zip(sequence, d)) if x != y] or [int(tcd_rng.integers(len(sequence)))]
                     for d in drafts]
            children = _tcd.infill(tcd_model, tcd_device, target.structure, target.pt, sequence, masks, tcd_rng)
            evaluate.model_calls += 1
            evaluate.model_wall_s += time.perf_counter() - start
            fresh = [c for c in dict.fromkeys(children) if c not in evaluate.first_index]
            if scorer is not None and len(fresh) > 1:
                child = fresh[int(np.argmin(scorer(target, sequence, fresh, defect_list, evaluate)))]
            else:
                child = fresh[0] if fresh else children[0]
            parents[child] = sequence
            return child
        module.mutate_structured = timed(tcd_mutation)
    elif s.get("init_model"):                          # SAMFEO's k initial designs drawn from a model instead
        from ribomamba.design.tcd import tcd_initial_designs
        module.init_k = lambda target_ss, pos_pairs, k: tcd_initial_designs(
            target, seed, k, evaluate, {"checkpoint": s["init_model"]})
    if s.get("proposal_model"):
        pass                                          # handled above (the filter, if any, is applied inside)
    elif s.get("filter"):
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
    """The scorer named by settings["filter"]; learned models are loaded once per process."""
    if settings["filter"] in ("residual", "sibling"):
        from ribomamba.design.residual_filter import ResidualScorer, SiblingScorer
        from ribomamba.paths import REPO_ROOT
        path = str(REPO_ROOT / settings["residual_model"])
        if path not in _CRITICS:
            _CRITICS[path] = (SiblingScorer if settings["filter"] == "sibling" else ResidualScorer)(path)
        return _CRITICS[path]
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
    max_restarts = settings.get("max_restarts")
    while max_restarts is None or evaluate.count < max_restarts:
        evaluate.check()
        designed, distance = RNA.inverse_fold(start, target.structure)
        evaluate(designed.upper(), objective=float(distance))
        start = random_design(target, rng)


DESIRNA_URL = "https://github.com/fryzjergda/DesiRNA.git"
DESIRNA_COMMIT = "bdb490839941daf30fe9119cbc4e2961d57f3a36"
DESIRNA_DIR = EXTERNAL_DIR / "DesiRNA"
DESIRNA_SETTINGS = {"commit": DESIRNA_COMMIT, "param": 2004, "replicas": 10, "time_limit_s": 64, "one_core": True,
                    "conda_env": "desirna", "stop_when_solved": "off"}


def run_external(cmd: list[str], limit_s: float, cwd, env: dict, stdin_text: str | None, log) -> dict:
    """Run an external designer in its own process group; kill the whole group at limit_s.

    stdout lines are read as they arrive and stamped with seconds since launch (monotonic clock,
    which excludes suspend). Returns {"lines": [(t, line)], "killed": bool, "returncode", "stderr",
    "t0"}; the raw stdout/stderr (truncated) go to the unit log.
    """
    import os
    import signal
    import threading
    t0 = time.monotonic()
    env = {**env, "EXTERNAL_T0": repr(t0)}
    proc = subprocess.Popen(cmd, cwd=cwd, env=env, stdin=subprocess.PIPE if stdin_text is not None else subprocess.DEVNULL,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1, start_new_session=True)
    lines, err = [], []
    readers = [threading.Thread(target=lambda: [lines.append((time.monotonic() - t0, l.rstrip("\n"))) for l in proc.stdout],
                                daemon=True),
               threading.Thread(target=lambda: [err.append(l) for l in proc.stderr], daemon=True)]
    for th in readers:
        th.start()
    if stdin_text is not None:
        proc.stdin.write(stdin_text)
        proc.stdin.close()
    killed = False
    try:
        proc.wait(timeout=max(0.0, limit_s - (time.monotonic() - t0)))
    except subprocess.TimeoutExpired:
        killed = True
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        proc.wait()
    for th in readers:
        th.join(timeout=5)
    if log is not None:
        log.write(f"cmd: {' '.join(map(str, cmd))}\n"
                  f"{'KILLED at the time limit' if killed else f'exited {proc.returncode}'} after "
                  f"{time.monotonic() - t0:.1f} s; stdout lines {len(lines)}\n")
        log.write("---- stdout (t_s, line), last 400 lines ----\n")
        log.writelines(f"{t:.2f}\t{l}\n" for t, l in lines[-400:])
        log.write("---- stderr (last 100 lines) ----\n" + "".join(err[-100:]))
    return {"lines": lines, "killed": killed, "returncode": proc.returncode, "stderr": "".join(err[-100:]), "t0": t0}


def desirna(target: Target, seed: int, evaluate: Evaluator, settings: dict, log=None) -> None:
    """DesiRNA (Apache-2.0; pinned DESIRNA_COMMIT) in its own env (ViennaRNA 2.7.2), with REAL timing.

    Run through scripts/external/desirna_wrapped.py, which logs every replica's state after every
    replica-exchange round with seconds since launch (DesiRNA itself writes its trajectory only at
    the end and checks its limit only between rounds, so a nominal 128 s run could last ~240 s:
    review of 2026-09-28). The whole process group is killed at time_limit_s; only rows logged by
    then are replayed, each stamped with its real time. A kill at the limit is status time_limit;
    a voluntary finish is early_stop. one_core pins the group to one CPU (replicas time-share).
    Internal calls are not countable.
    """
    import math
    import os
    import shutil
    import tempfile
    from ribomamba.design.search import TimeLimitReached
    s = {**DESIRNA_SETTINGS, **settings}
    evaluate.internal_available = False
    limit = float(s["time_limit_s"])
    work = Path(tempfile.mkdtemp(prefix="desirna_"))
    try:
        (work / "in.txt").write_text(f">name\nt\n>sec_struct\n{target.structure}\n>seq_restr\n{'N' * len(target)}\n")
        timelog = work / "timelog.tsv"
        conda_python = Path(os.environ.get("CONDA_EXE", "/home/chirag/miniforge3/bin/conda")).parent.parent / "envs" / \
            s["conda_env"] / "bin" / "python"
        entry = Path(__file__).resolve().parents[2] / "scripts" / "external" / "desirna_wrapped.py"
        cmd = [str(conda_python), str(entry), "-f", "in.txt", "-t", str(int(math.ceil(limit))), "-p", str(s["param"]),
               "-R", str(s["replicas"]), "-seed", str(seed + 1), "-sws", s["stop_when_solved"], "-od", "out"]
        if s["one_core"]:
            ident = (multiprocessing.current_process()._identity or (os.getpid(),))[0]
            cmd = ["taskset", "-c", str((ident - 1) % (os.cpu_count() or 1))] + cmd
        env = {**os.environ, "DESIRNA_DIR": str(DESIRNA_DIR), "DESIRNA_TIMELOG": str(timelog),
               "DESIRNA_FILTER_K": str(s.get("filter_k") or 0)}
        # desirna_wrapped.py reads DESIRNA_T0; run_external provides the launch time as EXTERNAL_T0.
        env["DESIRNA_T0_FROM"] = "EXTERNAL_T0"
        res = run_external(cmd, limit, work, env, None, log)
        rows = []
        if timelog.exists():
            for line in timelog.read_text().splitlines():
                t, replica, step, score, seq = line.split("\t")
                rows.append((float(t), int(replica), int(step), float(score), seq))
        if log is not None:
            log.write(f"timelog rows {len(rows)}, within limit {sum(r[0] <= limit for r in rows)}\n")
        if not res["killed"] and res["returncode"] != 0:
            raise RuntimeError(f"DesiRNA exited {res['returncode']}: {res['stderr'][-500:]}")
        seen = set()
        for t, replica, step, score, seq in sorted(r for r in rows if r[0] <= limit):
            if seq not in seen:
                seen.add(seq)
                evaluate(seq, objective=score, method_time_s=t)
        if res["killed"]:
            raise TimeLimitReached
    finally:
        shutil.rmtree(work, ignore_errors=True)


SAMPLINGDESIGN_URL = "https://github.com/weiyutang1010/SamplingDesign.git"
SAMPLINGDESIGN_COMMIT = "f0283c495c1031c52d4d7ecd06975a2894f5865b"
SAMPLINGDESIGN_DIR = EXTERNAL_DIR / "SamplingDesign"
# The upstream wrapper's defaults (external/SamplingDesign/main), passed positionally to bin/main.
SAMPLINGDESIGN_DEFAULTS = {"mode": "ncrna_design", "objective": "prob", "init": "targeted", "eps": 0.75,
                           "softmax": 1, "adam": 1, "nesterov": 0, "beta_1": 0.9, "beta_2": 0.999, "lr": 0.01,
                           "lr_decay": 0, "lr_decay_rate": 0.5, "adaptive_lr": 0, "k_ma_lr": 20, "lr_decay_step": 50,
                           "num_steps": 2000, "early_stop": 1, "k_ma": 50, "beamsize": 250, "sharpturn": 0,
                           "is_lazy": 0, "sample_size": 2500, "best_k": 1, "importance": 0, "mismatch": 1,
                           "trimismatch": 1, "verbose": 0, "num_threads": 1, "boxplot": 0}
SAMPLINGDESIGN_SETTINGS = {"commit": SAMPLINGDESIGN_COMMIT, "time_limit_s": 64, **SAMPLINGDESIGN_DEFAULTS}


def samplingdesign(target: Target, seed: int, evaluate: Evaluator, settings: dict, log=None) -> None:
    """SamplingDesign (Apache-2.0; pinned f0283c49; built with the separate rmtools g++), REAL timing.

    bin/main is run line-buffered (stdbuf -oL, so nothing is lost when the group is killed at the
    limit) with the upstream wrapper's defaults, num_threads = 1, seed = seed + 1. Each step prints
    the distribution's most probable sequence and the step's best sample; both are replayed as
    candidates stamped with the time their line ARRIVED (seconds since launch), and only lines that
    arrived within time_limit_s count. At its defaults (2,500 LinearPartition samples per step) one
    step takes ~2 min on one thread for ~180 nt on this machine (measured 2026-09-28), so on long
    puzzles no step may finish within the limit: that is recorded as a time_limit unit with zero
    candidates, not as an adapter failure. A voluntary finish (its own convergence rule) is early_stop.
    """
    import os
    import re
    from ribomamba.design.search import TimeLimitReached
    s = {**SAMPLINGDESIGN_SETTINGS, **settings}
    evaluate.internal_available = False
    limit = float(s["time_limit_s"])
    order = ["mode", "objective", "init", "eps", "softmax", "adam", "nesterov", "beta_1", "beta_2", "lr", "lr_decay",
             "lr_decay_rate", "adaptive_lr", "k_ma_lr", "lr_decay_step", "num_steps", "early_stop", "k_ma", "beamsize",
             "sharpturn", "is_lazy", "sample_size", "best_k", "importance", "mismatch", "trimismatch"]
    cmd = ["stdbuf", "-oL", "-eL", str(SAMPLINGDESIGN_DIR / "bin" / "main")] + [str(s[k]) for k in order] + \
        [str(seed + 1), str(s["verbose"]), str(s["num_threads"]), str(s["boxplot"])]
    env = {**os.environ, "OMP_NUM_THREADS": str(s["num_threads"])}
    res = run_external(cmd, limit, None, env, target.structure + "\n", log)
    if not res["killed"] and res["returncode"] != 0:
        raise RuntimeError(f"SamplingDesign exited {res['returncode']}: {res['stderr'][-500:]}")
    best_next = False
    for t, line in res["lines"]:
        if t > limit:
            break
        m = re.match(r"max-probability solution: ([ACGU]+) ", line)
        if m:
            if m.group(1) not in evaluate.cache:
                evaluate(m.group(1), method_time_s=t)
            continue
        if line.startswith("best samples"):
            best_next = True
            continue
        if best_next:
            best_next = False
            seq = line.split()[0] if line.split() else ""
            if re.fullmatch(r"[ACGU]+", seq) and seq not in evaluate.cache:
                evaluate(seq, method_time_s=t)
    if res["killed"]:
        raise TimeLimitReached


BASELINES = {"samfeo": samfeo, "rnainverse": rnainverse, "samfeo_efilter": samfeo_efilter, "desirna": desirna,
             "samplingdesign": samplingdesign,
             "samfeo_cfilter": samfeo_cfilter}
BASELINE_SETTINGS = {"samfeo": SAMFEO_SETTINGS, "rnainverse": RNAINVERSE_SETTINGS, "desirna": DESIRNA_SETTINGS,
                     "samplingdesign": SAMPLINGDESIGN_SETTINGS,
                     "samfeo_efilter": SAMFEO_EFILTER_SETTINGS, "samfeo_cfilter": SAMFEO_CFILTER_SETTINGS}
# Competition-residual filters (docs/experiments/2026-09-27-competition-residual.md), frozen models only.
RESIDUAL_VARIANTS = {"samfeo_rfilter_linear": "checkpoints/residual_v1/linear_rivals.json",
                     "samfeo_rfilter_linear_norival": "checkpoints/residual_v1/linear_no_rivals.json",
                     "samfeo_rfilter_mlp": "checkpoints/residual_v1/mlp_rivals.pt",
                     "samfeo_rfilter_mlp_norival": "checkpoints/residual_v1/mlp_no_rivals.pt",
                     "samfeo_rfilter_bank": "physics:bank"}
for _name, _path in RESIDUAL_VARIANTS.items():
    BASELINES[_name] = samfeo_efilter
    BASELINE_SETTINGS[_name] = {**SAMFEO_SETTINGS, "filter": "residual", "filter_k": 8, "residual_model": _path}
for _v in ("generic", "norival", "rival"):
    BASELINES[f"samfeo_sfilter_{_v}"] = samfeo_efilter
    BASELINE_SETTINGS[f"samfeo_sfilter_{_v}"] = {**SAMFEO_SETTINGS, "filter": "sibling", "filter_k": 8,
                                                 "residual_model": f"checkpoints/residual_v1/sibling_{_v}.pt"}
BASELINES["desirna_efilter"] = desirna
BASELINE_SETTINGS["desirna_efilter"] = {**DESIRNA_SETTINGS, "filter_k": 8}
for _t in (256,):
    BASELINES[f"desirna_t{_t}"] = desirna
    BASELINE_SETTINGS[f"desirna_t{_t}"] = {**DESIRNA_SETTINGS, "time_limit_s": _t}
    BASELINES[f"samplingdesign_t{_t}"] = samplingdesign
    BASELINE_SETTINGS[f"samplingdesign_t{_t}"] = {**SAMPLINGDESIGN_SETTINGS, "time_limit_s": _t}
BASELINES["rnainverse_r256"] = rnainverse
BASELINE_SETTINGS["rnainverse_r256"] = {**RNAINVERSE_SETTINGS, "max_restarts": 256}
BASELINES["rnainverse_r64"] = rnainverse
BASELINE_SETTINGS["rnainverse_r64"] = {**RNAINVERSE_SETTINGS, "max_restarts": 64}
BASELINES["samfeo_efilter_tcdinit"] = samfeo_efilter
BASELINE_SETTINGS["samfeo_efilter_tcdinit"] = {**SAMFEO_EFILTER_SETTINGS, "init_model": "checkpoints/tcd_v1/tcd.pt"}
# Registered through samfeo (NOT samfeo_efilter, whose defaults would silently add the energy screen:
# the bug that made ew_dev_tcdprop_v1's "samfeo_tcdprop" arm identical to its energy-screened arm).
BASELINES["samfeo_tcdprop_only"] = samfeo
BASELINE_SETTINGS["samfeo_tcdprop_only"] = {**SAMFEO_SETTINGS, "proposal_model": "checkpoints/tcd_v1/tcd.pt"}
BASELINES["samfeo_tcdprop"] = samfeo_efilter             # kept as run (it WAS energy-screened); see above
BASELINE_SETTINGS["samfeo_tcdprop"] = {**SAMFEO_SETTINGS, "proposal_model": "checkpoints/tcd_v1/tcd.pt"}
BASELINES["samfeo_tcdprop_efilter"] = samfeo_efilter
BASELINE_SETTINGS["samfeo_tcdprop_efilter"] = {**SAMFEO_EFILTER_SETTINGS, "proposal_model": "checkpoints/tcd_v1/tcd.pt"}
BASELINES["samfeo_efilter_eps"] = samfeo_efilter
BASELINE_SETTINGS["samfeo_efilter_eps"] = {**SAMFEO_EFILTER_SETTINGS, "epsilon": 0.125}

# Development ablation of the filter width K (energy filter), registered as separate method names so
# runs can be compared side by side. Changing K is a new candidate revision (needs its own look).
for _k in (4, 16, 32, 64):
    BASELINES[f"samfeo_efilter_k{_k}"] = samfeo_efilter
    BASELINE_SETTINGS[f"samfeo_efilter_k{_k}"] = {**SAMFEO_EFILTER_SETTINGS, "filter_k": _k}
__all__ = ["BASELINES", "BASELINE_SETTINGS", "BudgetExhausted", "load_samfeo", "samfeo_checkout_problem"]
