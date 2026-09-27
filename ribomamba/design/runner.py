"""Resumable pilot runs: one trace file per (method, target, seed) unit (Stage A, item 4).

Layout of a run directory (data/repair_pilot/<run>/):
  run_config.json            what was run; its config_hash must match on resume
  units/<method>/<target>__seed<k>.parquet   one row per candidate evaluation
  units/<method>/<target>__seed<k>.json      unit status: complete | early_stop | error | capped
  units/<method>/<target>__seed<k>.log       the method's own stdout (external baselines)
  events.jsonl               start/stop/cap events, appended

Each unit is written only when it ends, to a temporary name then renamed, so a
file is either whole or absent; the status is written last and records the
trace's SHA-256 and row count. On resume a unit is skipped only if its status
is terminal (complete, early_stop, or error unless retrying errors), matches
the run's config_hash, and its trace re-validates (hash, rows, contiguous
indices, budget). Anything else is re-run from scratch. Units stopped by the
run's wall-clock cap are written as 'capped' (partial, kept for inspection)
and re-run on resume. Errors are kept as failures, never dropped.
"""

import datetime as dt
import hashlib
import json
import os
import platform
import time
import traceback
from pathlib import Path

import polars as pl

from ribomamba.design.baselines import BASELINE_SETTINGS, BASELINES, SAMFEO_COMMIT
from ribomamba.design.manifest import LOOKS_PATH, canonical_json
from ribomamba.design.mfe_repair import MFE_METHODS, MFE_REPAIR_SETTINGS
from ribomamba.design.neural import NEURAL, NEURAL_METHOD_SETTINGS
from ribomamba.design.scoring import PRIMARY_SUCCESS, SUCCESS_POLICIES
from ribomamba.design.search import CONTROL_SETTINGS, CONTROLS, BudgetExhausted, DeadlineReached, Evaluator, Target
from ribomamba.eval.folding import DANGLES, TEMPERATURE_C
from ribomamba.eval.protocol import git_commit

TRACE_SCHEMA_VERSION = 2          # 2: model-call columns (Stage B)
METHODS = {**CONTROLS, **BASELINES, **NEURAL, **MFE_METHODS}
METHOD_SETTINGS = {**CONTROL_SETTINGS, **BASELINE_SETTINGS, **NEURAL_METHOD_SETTINGS, "mfe_repair": MFE_REPAIR_SETTINGS}
TERMINAL = ("complete", "early_stop", "error")
CLOCK_GAP_S = 30.0


def wall_limited(method: str) -> bool:
    """External methods whose own time limit or step times use the wall clock."""
    return method.startswith("desirna") or method.startswith("samplingdesign")
ORACLE = {"package": "ViennaRNA", "version": "2.7.2", "parameters": "Turner 2004", "temperature_c": TEMPERATURE_C,
          "dangles": DANGLES, "lonely_pairs": True}
BUDGET_UNIT = ("one candidate evaluation = one proposal scored, including the initial candidate and cache hits; "
               "oracle calls (cache misses) counted separately by kind")

_COUNTS = ["mfe", "pf", "subopt", "eval"]
SCHEMA = {
    "method": pl.String, "target_id": pl.String, "seed": pl.Int64,
    "eval_index": pl.Int64, "parent_index": pl.Int64, "changed_positions": pl.List(pl.Int64), "cache_hit": pl.Boolean,
    "objective": pl.Float64, "sequence": pl.String, "valid": pl.Boolean, "error": pl.String,
    "mfe_structure": pl.String, "mfe_energy": pl.Float64, "ensemble_energy": pl.Float64,
    "target_feasible": pl.Boolean, "infeasible_pairs": pl.Int64, "target_energy": pl.Float64,
    "mfe_backtrack": pl.Boolean, "mfe_any": pl.Boolean, "umfe": pl.Boolean, "mfe_ties": pl.Int64,
    "bp_distance": pl.Int64, "p_target": pl.Float64, "log_p_target": pl.Float64, "ned": pl.Float64,
    "cum_proposals": pl.Int64, "cum_cache_misses": pl.Int64,
    **{f"cum_oracle_{k}": pl.Int64 for k in _COUNTS}, **{f"cum_internal_{k}": pl.Int64 for k in _COUNTS},
    "elapsed_s": pl.Float64, "cpu_s": pl.Float64, "score_wall_s": pl.Float64,
    "cum_model_calls": pl.Int64, "model_wall_s": pl.Float64,
}


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def atomic_write_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    with open(tmp, "wb") as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def atomic_write_json(path: Path, obj) -> None:
    atomic_write_bytes(path, (json.dumps(obj, indent=1, sort_keys=True) + "\n").encode())


def append_event(run_dir: Path, **event) -> None:
    with open(Path(run_dir) / "events.jsonl", "a") as f:
        f.write(json.dumps({"time_utc": utc_now(), **event}) + "\n")


def unit_key(method: str, target_id: str, seed: int) -> str:
    return f"{method}/{target_id.replace(':', '_').replace('/', '_')}__seed{seed}"


def unit_paths(run_dir: Path, key: str) -> tuple[Path, Path, Path]:
    base = Path(run_dir) / "units" / key
    return base.with_suffix(".parquet"), base.with_suffix(".json"), base.with_suffix(".log")


def make_config(manifest: dict, subset: str, targets: list[dict], methods: list[str], seeds: list[int],
                budget: int, settings_override: dict | None = None) -> dict:
    unknown = set(methods) - set(METHODS)
    if unknown:
        raise ValueError(f"unknown methods {sorted(unknown)}; available {sorted(METHODS)}")
    settings = {m: {**METHOD_SETTINGS[m], **(settings_override or {}).get(m, {})} for m in methods}
    hashed = {
        "manifest": {"name": manifest["name"], "content_sha256": manifest["content_sha256"]},
        "subset": subset, "target_ids": [t["id"] for t in targets], "methods": settings,
        "seeds": list(seeds), "budget": budget, "oracle": ORACLE, "trace_schema_version": TRACE_SCHEMA_VERSION,
        "budget_unit": BUDGET_UNIT, "success_policies": list(SUCCESS_POLICIES), "primary_success": PRIMARY_SUCCESS,
    }
    return {**hashed, "config_hash": hashlib.sha256(canonical_json(hashed)).hexdigest()}


def hardware() -> dict:
    cpu = next((line.split(":", 1)[1].strip() for line in open("/proc/cpuinfo") if line.startswith("model name")),
               platform.processor()) if Path("/proc/cpuinfo").exists() else platform.processor()
    return {"cpu": cpu, "logical_cpus": os.cpu_count(), "platform": platform.platform(),
            "python": platform.python_version(), "gpu_used": False}


def validate_unit(run_dir: Path, key: str, config_hash: str, budget: int, retry_errors: bool = False) -> str | None:
    """None if the unit is finished and intact; otherwise why it must (re-)run."""
    trace_path, status_path, _ = unit_paths(run_dir, key)
    if not status_path.exists():
        return "missing"
    try:
        status = json.loads(status_path.read_text())
    except json.JSONDecodeError:
        return "unreadable status"
    if status.get("config_hash") != config_hash:
        return "config hash differs"
    if status.get("status") not in TERMINAL:
        return f"status {status.get('status')}"
    if status["status"] == "error" and retry_errors:
        return "retrying error"
    if wall_limited(status.get("method", "")):
        # DesiRNA (time.time) and SamplingDesign (gettimeofday) budget by WALL CLOCK; if the machine
        # slept during the unit, their budget was spent asleep and their step times jumped.
        try:
            clock = (dt.datetime.fromisoformat(status["finished_utc"])
                     - dt.datetime.fromisoformat(status["started_utc"])).total_seconds()
        except (KeyError, ValueError):
            clock = 0.0
        if clock - status.get("wall_s", clock) > CLOCK_GAP_S:
            return "clock gap during a wall-limited unit (machine suspended?)"
    if not trace_path.exists() or hashlib.sha256(trace_path.read_bytes()).hexdigest() != status.get("sha256"):
        return "trace missing or hash differs"
    trace = pl.read_parquet(trace_path)
    n = trace.height
    if n != status.get("n_rows") or trace["eval_index"].to_list() != list(range(n)):
        return "trace rows inconsistent"
    if n > budget or (status["status"] == "complete" and n != budget):
        return "trace length does not match the budget"
    return None


def run_unit(job: dict) -> dict:
    """Run one unit to its end and write it. Executed in a worker process."""
    run_dir, key = Path(job["run_dir"]), job["key"]
    base = {"unit": key, "method": job["method"], "target_id": job["target"]["id"], "seed": job["seed"],
            "budget": job["budget"], "config_hash": job["config_hash"]}
    if time.time() > job["deadline"]:
        return {**base, "status": "not_started", "reason": "run wall-clock cap reached"}
    trace_path, status_path, log_path = unit_paths(run_dir, key)
    trace_path.parent.mkdir(parents=True, exist_ok=True)
    target = Target(job["target"]["id"], job["target"]["structure"])
    evaluate = Evaluator(target, job["budget"], job["deadline"])
    started, reason = utc_now(), None
    with open(log_path, "w") as log:
        try:
            method = METHODS[job["method"]]
            kwargs = {"log": log} if job["method"] in BASELINES else {}
            method(target, job["seed"], evaluate, job["settings"], **kwargs)
            status, reason = "early_stop", "the method stopped itself before the budget"
        except BudgetExhausted:
            status = "complete"
        except DeadlineReached:
            status, reason = "capped", "run wall-clock cap reached mid-unit (partial trace)"
        except Exception:
            status, reason = "error", traceback.format_exc()
    rows = [{"method": job["method"], "target_id": target.id, "seed": job["seed"], **r} for r in evaluate.rows]
    frame = pl.DataFrame(rows, schema=SCHEMA, strict=False) if rows else pl.DataFrame(schema=SCHEMA)
    tmp = trace_path.with_name(trace_path.name + ".tmp")
    frame.write_parquet(tmp)
    with open(tmp, "rb") as f:
        os.fsync(f.fileno())
    os.replace(tmp, trace_path)
    result = {**base, "status": status, "reason": reason, "n_rows": frame.height,
              "sha256": hashlib.sha256(trace_path.read_bytes()).hexdigest(),
              "wall_s": time.perf_counter() - evaluate.t0, "cpu_s": time.process_time() - evaluate.c0,
              "score_wall_s": evaluate.score_wall_s, "cache_misses": evaluate.cache_misses,
              "model_calls": evaluate.model_calls, "model_wall_s": evaluate.model_wall_s,
              "oracle_calls": evaluate.oracle.as_dict(),
              "internal_calls": evaluate.internal.as_dict() if evaluate.internal_available else None,
              "started_utc": started, "finished_utc": utc_now(), "git_commit": job["git_commit"],
              "hostname": platform.node(), "pid": os.getpid()}
    atomic_write_json(status_path, result)
    return result


def log_confirmation_look(run_name: str, subset: str, label: str, config: dict, path: Path = LOOKS_PATH) -> None:
    """Every run touching confirmation targets is logged BEFORE it starts (RESEARCH_PLAN.md Stage A, item 2)."""
    if not label:
        raise PermissionError(f"subset {subset!r} includes confirmation targets: pass a declared candidate "
                              "revision label (--confirmation-look) so the look is logged")
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a") as f:
        f.write(json.dumps({"time_utc": utc_now(), "run": run_name, "subset": subset, "label": label,
                            "config_hash": config["config_hash"], "methods": sorted(config["methods"]),
                            "git_commit": git_commit()}) + "\n")


def run(run_dir: Path, config: dict, targets: list[dict], workers: int = 4, max_hours: float | None = None,
        retry_errors: bool = False, progress=print) -> dict:
    """Run every unfinished unit of the configuration. Returns counts by final status."""
    run_dir = Path(run_dir)
    config_path = run_dir / "run_config.json"
    if config_path.exists():
        existing = json.loads(config_path.read_text())
        if existing["config_hash"] != config["config_hash"]:
            raise ValueError(f"{run_dir} holds a different configuration (hash {existing['config_hash'][:12]}); "
                             "use a new run directory")
    else:
        atomic_write_json(config_path, {**config, "created_utc": utc_now(), "git_commit": git_commit(),
                                        "hardware": hardware(), "samfeo_commit": SAMFEO_COMMIT})
    by_id = {t["id"]: t for t in targets}
    if [t["id"] for t in targets] != config["target_ids"]:
        raise ValueError("targets do not match the configuration's target_ids")
    jobs, skipped = [], 0
    start = time.time()
    deadline = float("inf") if max_hours is None else start + max_hours * 3600
    commit = git_commit()
    for method in config["methods"]:
        for target_id in config["target_ids"]:
            for seed in config["seeds"]:
                key = unit_key(method, target_id, seed)
                why = validate_unit(run_dir, key, config["config_hash"], config["budget"], retry_errors)
                if why is None:
                    skipped += 1
                    continue
                jobs.append({"run_dir": str(run_dir), "key": key, "method": method, "target": by_id[target_id],
                             "seed": seed, "budget": config["budget"], "settings": config["methods"][method],
                             "config_hash": config["config_hash"], "deadline": deadline, "git_commit": commit})
    # Longest targets first, so the slowest units do not straggle at the end.
    jobs.sort(key=lambda j: -len(j["target"]["structure"]))
    append_event(run_dir, event="start", pending=len(jobs), already_done=skipped, workers=workers,
                 max_hours=max_hours, git_commit=commit)
    progress(f"{len(jobs)} units to run, {skipped} already complete; {workers} workers, cap {max_hours} h")
    counts: dict[str, int] = {"skipped_complete": skipped}
    if jobs:
        os.environ.setdefault("OMP_NUM_THREADS", "1")
        if workers <= 1:
            results = map(run_unit, jobs)
            pool = None
        else:
            import multiprocessing as mp
            pool = mp.get_context("spawn").Pool(workers)
            results = pool.imap_unordered(run_unit, jobs)
        try:
            for done, result in enumerate(results, 1):
                counts[result["status"]] = counts.get(result["status"], 0) + 1
                if result["status"] not in ("complete", "not_started"):
                    progress(f"  {result['unit']}: {result['status']}"
                             + (f" ({result['reason'].strip().splitlines()[-1]})" if result.get("reason") else ""))
                if done % 20 == 0 or done == len(jobs):
                    progress(f"  {done}/{len(jobs)} units, {time.time() - start:.0f} s")
        finally:
            if pool is not None:
                pool.close()
                pool.join()
    append_event(run_dir, event="stop", counts=counts, wall_s=round(time.time() - start, 1))
    return counts
