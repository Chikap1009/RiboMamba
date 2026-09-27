"""Pilot summaries from raw traces: budget checkpoints, target-level aggregation, runtime estimates.

Endpoints at each nested budget b (the first b proposals of a unit):
  success_<policy>   any candidate so far met the policy (scoring.py tie policies)
  best_ned           lowest NED so far          best_log10_p   highest log10 P(target) so far
  evals_to_success   first eval_index + 1 meeting the primary policy (null: never)
  costs              cumulative oracle calls by kind (harness scoring), internal calls
                     (external baselines only), wall and CPU seconds at the checkpoint
A unit that stopped early (early_stop) keeps its final values at larger budgets;
a unit that errored counts as unsuccessful, with its error kept in the status.

Aggregation: seeds are averaged WITHIN each target first; uncertainty is a
bootstrap over targets (seeds are not independent targets). Paired method
differences use the same per-target means.
"""

import json
import math
from pathlib import Path

import numpy as np
import polars as pl

from ribomamba.design.runner import TERMINAL, unit_paths
from ribomamba.design.scoring import PRIMARY_SUCCESS, SUCCESS_POLICIES
from ribomamba.eval.stats import bootstrap_ci

BUDGETS = (64, 256, 1024)
LOG10E = math.log10(math.e)
LOWER_IS_BETTER = {"best_ned", "evals_to_success", "elapsed_s", "cpu_s"}
WALL_BUDGETS_S = (1, 2, 4, 8, 16, 32, 64, 128, 256)
# Methods whose feedback comes from their OWN (counted) oracle calls: the harness's re-scoring
# of their candidates is measurement overhead and is subtracted from their wall time. For
# every other method the harness scoring IS the method's feedback, so it counts.
EXTERNAL = {"samfeo", "rnainverse", "mfe_repair", "samfeo_efilter", "samfeo_cfilter",
            *(f"samfeo_efilter_k{k}" for k in (4, 16, 32, 64))}


def load_run(run_dir: Path) -> tuple[dict, list[dict], pl.DataFrame]:
    run_dir = Path(run_dir)
    config = json.loads((run_dir / "run_config.json").read_text())
    statuses, frames = [], []
    for status_path in sorted((run_dir / "units").rglob("*.json")):
        status = json.loads(status_path.read_text())
        statuses.append(status)
        trace_path = unit_paths(run_dir, status["unit"])[0]
        if trace_path.exists():
            frames.append(pl.read_parquet(trace_path))
    traces = pl.concat(frames, how="vertical") if frames else pl.DataFrame()
    return config, statuses, traces


def max_homopolymer(sequence: str) -> int:
    best = run = 1
    for a, b in zip(sequence, sequence[1:]):
        run = run + 1 if a == b else 1
        best = max(best, run)
    return best


def unit_checkpoints(trace: pl.DataFrame, status: dict, budgets=BUDGETS) -> list[dict]:
    """One row per budget <= the unit's budget."""
    out = []
    trace = trace.sort("eval_index")
    for b in budgets:
        if b > status["budget"]:
            continue
        prefix = trace.filter(pl.col("eval_index") < b)
        row = {"method": status["method"], "target_id": status["target_id"], "seed": status["seed"], "budget": b,
               "status": status["status"], "evals_used": prefix.height}
        if prefix.height == 0:
            out.append({**row, **{f"success_{p}": False for p in SUCCESS_POLICIES}})
            continue
        for p in SUCCESS_POLICIES:
            row[f"success_{p}"] = bool(prefix[p].any())
        hits = prefix.filter(pl.col(PRIMARY_SUCCESS))["eval_index"]
        row["evals_to_success"] = int(hits.min()) + 1 if hits.len() else None
        defined = prefix.filter(pl.col("ned").is_not_nan() & pl.col("valid") & pl.col("error").is_null())
        best = defined.sort(["ned", "eval_index"]).row(0, named=True) if defined.height else None
        row["best_ned"] = best["ned"] if best else math.nan
        row["best_log10_p"] = float(prefix["log_p_target"].max()) * LOG10E
        last = prefix.row(-1, named=True)
        row.update({k: last[k] for k in last if k.startswith("cum_")})
        row.update({"elapsed_s": last["elapsed_s"], "cpu_s": last["cpu_s"], "score_wall_s": last["score_wall_s"],
                    "cum_model_calls": last.get("cum_model_calls"), "model_wall_s": last.get("model_wall_s"),
                    "invalid_or_error": int((~prefix["valid"] | prefix["error"].is_not_null()).sum()),
                    "infeasible_proposals": int((~prefix["target_feasible"]).sum()),
                    "distinct_fraction": prefix["sequence"].n_unique() / prefix.height})
        if best:
            seq = best["sequence"]
            row["best_gc"] = (seq.count("G") + seq.count("C")) / len(seq)
            row["best_max_homopolymer"] = max_homopolymer(seq)
        out.append(row)
    return out


def method_wall(trace: pl.DataFrame, method: str) -> pl.Series:
    """Cumulative wall seconds attributable to the method (see EXTERNAL)."""
    wall = trace["elapsed_s"]
    return wall - trace["score_wall_s"] if method in EXTERNAL else wall


def wall_checkpoints(trace: pl.DataFrame, status: dict, walls=WALL_BUDGETS_S) -> list[dict]:
    """Best-so-far endpoints by wall-clock seconds, for comparisons across unlike 'candidates'.

    A unit that finished (complete or early_stop) before a wall budget keeps its final
    values there; a unit whose trace ends earlier only because its candidate budget ran
    out is marked truncated=True at larger wall budgets (it might have improved further).
    """
    trace = trace.sort("eval_index").with_columns(method_wall(trace.sort("eval_index"), status["method"])
                                                  .alias("method_wall_s"))
    out = []
    for w in walls:
        prefix = trace.filter(pl.col("method_wall_s") <= w)
        row = {"method": status["method"], "target_id": status["target_id"], "seed": status["seed"], "wall_s": w,
               "truncated": status["status"] == "complete" and trace.height and float(trace["method_wall_s"][-1]) < w,
               "evals": prefix.height}
        for p in SUCCESS_POLICIES:
            row[f"success_{p}"] = bool(prefix[p].any()) if prefix.height else False
        defined = prefix.filter(pl.col("ned").is_not_nan() & pl.col("valid"))
        row["best_ned"] = float(defined["ned"].min()) if defined.height else math.nan
        out.append(row)
    return out


def checkpoints(run_dir: Path, budgets=BUDGETS) -> tuple[dict, list[dict], pl.DataFrame]:
    config, statuses, traces = load_run(run_dir)
    rows = []
    for status in statuses:
        if status["status"] not in TERMINAL:
            continue
        unit = traces.filter((pl.col("method") == status["method"]) & (pl.col("target_id") == status["target_id"])
                             & (pl.col("seed") == status["seed"])) if traces.height else traces
        rows.extend(unit_checkpoints(unit, status, budgets))
    return config, statuses, pl.DataFrame(rows, infer_schema_length=None)


def target_means(cp: pl.DataFrame, metric: str) -> pl.DataFrame:
    """Seeds averaged within target: one value per (method, budget, target)."""
    return (cp.with_columns(pl.col(metric).cast(pl.Float64))
            .group_by(["method", "budget", "target_id"]).agg(pl.col(metric).mean().alias(metric)))


def aggregate(cp: pl.DataFrame, metrics=None, seed: int = 0) -> list[dict]:
    metrics = metrics or [f"success_{p}" for p in SUCCESS_POLICIES] + ["best_ned", "best_log10_p"]
    out = []
    for (method, budget), _ in cp.group_by(["method", "budget"], maintain_order=True):
        row = {"method": method, "budget": budget}
        sub = cp.filter((pl.col("method") == method) & (pl.col("budget") == budget))
        row["units"] = sub.height
        row["targets"] = sub["target_id"].n_unique()
        for metric in metrics:
            values = target_means(sub, metric)[metric].drop_nans().drop_nulls().to_numpy()
            if len(values):
                est, low, high = bootstrap_ci(values, seed=seed)
                row[metric] = {"mean": est, "low": low, "high": high, "n_targets": len(values)}
        for cost in ("cum_cache_misses", "cum_oracle_mfe", "cum_oracle_pf", "cum_oracle_subopt",
                     "cum_internal_mfe", "cum_internal_pf", "cum_internal_subopt", "elapsed_s", "cpu_s",
                     "score_wall_s", "cum_model_calls", "model_wall_s"):
            if cost in sub.columns and sub[cost].null_count() < sub.height:
                row[f"mean_{cost}"] = float(sub[cost].cast(pl.Float64).mean())
        row["errors"] = int((sub["status"] == "error").sum())
        row["early_stops"] = int((sub["status"] == "early_stop").sum())
        out.append(row)
    return sorted(out, key=lambda r: (r["budget"], r["method"]))


def paired(cp: pl.DataFrame, a: str, b: str, metric: str, budget: int, seed: int = 0) -> dict | None:
    """Per-target mean difference a - b (seeds averaged within target first), bootstrap over targets."""
    ta = target_means(cp.filter((pl.col("method") == a) & (pl.col("budget") == budget)), metric)
    tb = target_means(cp.filter((pl.col("method") == b) & (pl.col("budget") == budget)), metric)
    joined = ta.join(tb, on="target_id", suffix="_b").drop_nans([metric, f"{metric}_b"])
    if joined.height == 0:
        return None
    diff = (joined[metric] - joined[f"{metric}_b"]).to_numpy()
    est, low, high = bootstrap_ci(diff, seed=seed)
    a_wins = diff < 0 if metric in LOWER_IS_BETTER else diff > 0
    b_wins = diff > 0 if metric in LOWER_IS_BETTER else diff < 0
    return {"a": a, "b": b, "metric": metric, "budget": budget, "mean_diff": est, "low": low, "high": high,
            "n_targets": len(diff), "a_better": int(a_wins.sum()), "b_better": int(b_wins.sum()),
            "ties": int((diff == 0).sum()), "lower_is_better": metric in LOWER_IS_BETTER}


def per_eval_seconds(traces: pl.DataFrame, statuses: list[dict]) -> pl.DataFrame:
    """Wall seconds per candidate evaluation for each finished unit, with the target length."""
    rows = []
    for s in statuses:
        if s["status"] in ("complete", "early_stop") and s["n_rows"]:
            length = traces.filter(pl.col("target_id") == s["target_id"])["sequence"][0]
            rows.append({"method": s["method"], "length": len(length), "s_per_eval": s["wall_s"] / s["n_rows"]})
    return pl.DataFrame(rows)


def runtime_estimate(per_eval: pl.DataFrame, lengths: list[int], seeds: int, budget: int, workers: int) -> dict:
    """Fit log(s/eval) = a + b log(length) per method and extrapolate to a target set, in hours.

    An estimate from a handful of units: it ignores early stops (which only shorten
    runs) and scheduling imbalance, and assumes per-evaluation cost does not change
    with budget (SAMFEO's does not; the controls' cache hit rate can only rise).
    """
    out = {}
    for method in per_eval["method"].unique(maintain_order=True).to_list():
        sub = per_eval.filter(pl.col("method") == method)
        x, y = np.log(sub["length"].to_numpy()), np.log(sub["s_per_eval"].to_numpy())
        slope, intercept = np.polyfit(x, y, 1) if len(set(x)) > 1 else (0.0, float(y.mean()))
        seconds = sum(math.exp(intercept + slope * math.log(n)) for n in lengths) * seeds * budget
        out[method] = {"cpu_hours": seconds / 3600, "wall_hours_at_workers": seconds / 3600 / workers,
                       "length_exponent": float(slope)}
    return out


def markdown_table(summary: list[dict], budget: int) -> str:
    head = ("| method | targets | uMFE success | MFE (backtrack) | MFE (any tie) | best NED | best log10 P "
            "| oracle misses | internal pf | wall s/unit | errors | early stops |")
    lines = [head, "|" + "---|" * 12]

    def ci(cell, pct=False, digits=3):
        if not cell:
            return "n/a"
        scale = 100 if pct else 1
        fmt = f"{{:.{0 if pct else digits}f}}"
        return f"{fmt.format(cell['mean'] * scale)} [{fmt.format(cell['low'] * scale)}, {fmt.format(cell['high'] * scale)}]"
    for r in summary:
        if r["budget"] != budget:
            continue
        lines.append(f"| {r['method']} | {r['targets']} | {ci(r.get('success_umfe'), True)}% "
                     f"| {ci(r.get('success_mfe_backtrack'), True)}% | {ci(r.get('success_mfe_any'), True)}% "
                     f"| {ci(r.get('best_ned'))} | {ci(r.get('best_log10_p'), digits=2)} "
                     f"| {r.get('mean_cum_cache_misses', math.nan):.0f} | "
                     f"{r.get('mean_cum_internal_pf', math.nan):.0f} | {r.get('mean_elapsed_s', math.nan):.2f} "
                     f"| {r['errors']} | {r['early_stops']} |")
    return "\n".join(lines)


def wall_table(run_dir: Path, walls=WALL_BUDGETS_S) -> pl.DataFrame:
    """Per (method, wall budget): target-level means (seeds averaged within target first)."""
    _, statuses, traces = load_run(run_dir)
    rows = []
    for status in statuses:
        if status["status"] not in TERMINAL:
            continue
        unit = traces.filter((pl.col("method") == status["method"]) & (pl.col("target_id") == status["target_id"])
                             & (pl.col("seed") == status["seed"]))
        rows.extend(wall_checkpoints(unit, status, walls))
    cp = pl.DataFrame(rows)
    per_target = cp.group_by(["method", "wall_s", "target_id"]).agg(
        pl.col("success_umfe").cast(pl.Float64).mean(), pl.col("best_ned").mean(),
        pl.col("truncated").cast(pl.Float64).mean(), pl.col("evals").mean())
    return per_target.group_by(["method", "wall_s"]).agg(
        pl.col("success_umfe").mean().alias("success_umfe"), pl.col("best_ned").mean().alias("best_ned"),
        pl.col("truncated").mean().alias("truncated_share"), pl.col("evals").mean().alias("mean_evals"),
        pl.len().alias("targets")).sort(["wall_s", "method"])
