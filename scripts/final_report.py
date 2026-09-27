"""Final-benchmark analysis for protocol v2 (docs/PROTOCOL_design_v2.md, frozen 2026-09-27).

  python scripts/final_report.py --eternafold   # FINAL: refuses unless every expected unit of all three
                                                # sets is valid and the corrective retry pass is done
  python scripts/final_report.py --interim      # diagnostics on an incomplete benchmark, written to a
                                                # separate file and labelled INTERIM (never final results)

Endpoints exactly as frozen: puzzles solved (uMFE) by 128 s of method time — by any of the 3
seeds and the mean over seeds — per set; uMFE at 1/4/16/64/128 s; best NED; best log10 P;
evaluations to first solution; paired per-puzzle comparisons (method vs samfeo, method vs
samfeo_efilter, tcd_sample vs random_pairs) with bootstrap 95 % intervals over puzzles.
V1 = V2 results on the 81 identical structures + final_eterna100_v1only (19 puzzles).
Every error / time-limit / early-stop outcome is counted. Zero-candidate time_limit units (the method's first
design came after 128 s) are legitimate unsolved outcomes and are listed per method; units that ended in
`error` are implementation failures until diagnosed, so FINAL refuses while any remain unless
--accept-errors is given (they then count as unsolved and are listed). Writes
data/repair_pilot/final_v2_report.json and prints a markdown summary.
"""

import argparse
import json
import math

import numpy as np
import polars as pl

from ribomamba.design import runner, summary
from ribomamba.design.manifest import MANIFESTS_DIR, load_manifest
from ribomamba.eval.stats import bootstrap_ci
from ribomamba.paths import PILOT_DIR

SETS = ("eterna100_v2", "eterna100_v1only", "rfam_taneda27")
WALLS = (1, 4, 16, 64, 128)
LIMIT_S = 128.0
RETRY_DONE = PILOT_DIR / "final_v2_retry.done"
PAIRS = [("samfeo_efilter", "samfeo"), ("samfeo_tcdprop_efilter", "samfeo"), ("samfeo_tcdprop_efilter", "samfeo_efilter"),
         ("desirna", "samfeo_efilter"), ("rnainverse", "samfeo_efilter"), ("samplingdesign", "samfeo_efilter"),
         ("tcd_sample", "random_pairs"), ("tcd_sample", "samfeo_efilter")]


def run_dir(s: str):
    return PILOT_DIR / f"final_v2_{s}"


def audit(s: str) -> dict:
    d = run_dir(s)
    cfg = json.loads((d / "run_config.json").read_text())
    reasons, statuses, zero, errors = {}, {}, {}, []
    for m in cfg["methods"]:
        for t in cfg["target_ids"]:
            for seed in cfg["seeds"]:
                key = runner.unit_key(m, t, seed)
                why = runner.validate_unit(d, key, cfg["config_hash"], cfg["budget"]) or "valid"
                reasons[why] = reasons.get(why, 0) + 1
                p = runner.unit_paths(d, key)[1]
                if p.exists():
                    j = json.loads(p.read_text())
                    st = j["status"]
                    statuses[f"{m}:{st}"] = statuses.get(f"{m}:{st}", 0) + 1
                    if st == "error":
                        last = [x for x in str(j.get("reason", "")).splitlines() if x.strip()]
                        errors.append({"unit": key, "reason": last[-1][:200] if last else ""})
                    elif j.get("n_rows") == 0:
                        zero[f"{m}:{st}"] = zero.get(f"{m}:{st}", 0) + 1
    return {"config_hash": cfg["config_hash"], "validation": reasons, "statuses": statuses,
            "zero_candidate_units": zero, "error_units": errors,
            "methods": sorted(cfg["methods"]), "n_targets": len(cfg["target_ids"])}


def per_unit(s: str) -> pl.DataFrame:
    """One row per (method, target, seed, wall budget) with success/NED, plus the unit's best-P design
    and first uMFE success, both chosen ONLY among candidates within LIMIT_S of method time (the same
    eligibility rule as the success curves; review of 2026-09-28)."""
    units = summary.wall_unit_table(run_dir(s), walls=WALLS)
    _, statuses, traces = summary.load_run(run_dir(s))
    frames = []
    for (method,), t in traces.group_by(["method"]):
        t = t.sort(["target_id", "seed", "eval_index"])
        frames.append(t.with_columns(summary.method_wall(t, method).alias("method_wall_s")))
    eligible = pl.concat(frames).filter(pl.col("method_wall_s") <= LIMIT_S) if frames else traces
    best = (eligible.sort("log_p_target", descending=True).group_by(["method", "target_id", "seed"]).first()
            .select("method", "target_id", "seed", (pl.col("log_p_target") / math.log(10)).alias("best_log10_p"),
                    "sequence"))
    first = (eligible.filter(pl.col("umfe")).group_by(["method", "target_id", "seed"])
             .agg((pl.col("eval_index").min() + 1).alias("evals_to_first"),
                  pl.col("method_wall_s").min().alias("seconds_to_first")))
    return units.join(best, on=["method", "target_id", "seed"], how="left").join(
        first, on=["method", "target_id", "seed"], how="left")


def solved_counts(u: pl.DataFrame, wall: int) -> pl.DataFrame:
    x = u.filter(pl.col("wall_s") == wall)
    per_target = x.group_by(["method", "target_id"]).agg(pl.col("success_umfe").any().alias("any_seed"),
                                                         pl.col("success_umfe").cast(pl.Float64).mean().alias("mean"))
    return per_target.group_by("method").agg(pl.col("any_seed").sum().alias("solved_any_seed"),
                                              pl.col("mean").sum().alias("solved_mean_over_seeds"),
                                              pl.len().alias("targets")).sort("method")


def paired(u: pl.DataFrame, a: str, b: str, wall: int, metric: str) -> dict | None:
    x = u.filter(pl.col("wall_s") == wall)
    ta = x.filter(pl.col("method") == a).group_by("target_id").agg(pl.col(metric).cast(pl.Float64).mean())
    tb = x.filter(pl.col("method") == b).group_by("target_id").agg(pl.col(metric).cast(pl.Float64).mean())
    j = ta.join(tb, on="target_id", suffix="_b").drop_nans().drop_nulls()
    if j.height == 0:
        return None
    diff = (j[metric] - j[f"{metric}_b"]).to_numpy()
    est, lo, hi = bootstrap_ci(diff)
    lower = metric in ("best_ned",)
    return {"a": a, "b": b, "metric": metric, "wall_s": wall, "mean_diff": est, "low": lo, "high": hi,
            "a_better": int(((diff < 0) if lower else (diff > 0)).sum()),
            "b_better": int(((diff > 0) if lower else (diff < 0)).sum()), "n": len(diff)}


def eternafold_check(frames: dict) -> dict:
    """Best-P design per (method, target, seed) on V2: does EternaFold's MFE equal the target?"""
    from ribomamba.eval.eternafold import eternafold_many
    v2 = frames["eterna100_v2"].filter(pl.col("wall_s") == 128).drop_nulls("sequence")
    structures = {t["id"]: t["structure"] for t in load_manifest(MANIFESTS_DIR / "final_eterna100_v2.json")["targets"]}
    seqs = v2["sequence"].to_list()
    targets = [structures[t] for t in v2["target_id"].to_list()]
    res = eternafold_many(seqs, compare=[[t] for t in targets], processes=4)
    v2 = v2.with_columns(pl.Series("ef_match", [bool(r["ef_match_0"]) for r in res]),
                         pl.Series("ef_ned", [r["ef_ned_0"] for r in res]))
    return {r["method"]: {"ef_mfe_match_rate": r["ef_match_rate"], "ef_ned_mean": r["ef_ned_mean"]}
            for r in v2.group_by("method").agg(pl.col("ef_match").cast(pl.Float64).mean().alias("ef_match_rate"),
                                               pl.col("ef_ned").mean().alias("ef_ned_mean")).iter_rows(named=True)}


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--eternafold", action="store_true")
    p.add_argument("--interim", action="store_true", help="allow an incomplete benchmark; output labelled INTERIM")
    p.add_argument("--accept-errors", action="store_true",
                   help="after diagnosis, count remaining error units as unsolved (they are listed in the report)")
    args = p.parse_args()
    report, frames = {"audit": {}, "sets": {}, "status": "INTERIM (incomplete benchmark)" if args.interim else "FINAL"}, {}
    problems = []
    for s in SETS:
        if not (run_dir(s) / "run_config.json").exists():
            problems.append(f"{s}: run has not started")
            continue
        report["audit"][s] = audit(s)
        bad = {k: v for k, v in report["audit"][s]["validation"].items() if k != "valid"}
        if bad:
            problems.append(f"{s}: units not valid {bad}")
        errs = report["audit"][s]["error_units"]
        if errs and not args.accept_errors:
            problems.append(f"{s}: {len(errs)} units ended in error (diagnose; rerun implementation failures, or "
                            f"--accept-errors to count them as unsolved), e.g. {errs[0]}")
        zero_bad = [k for k in report["audit"][s]["zero_candidate_units"] if not k.endswith(":time_limit")]
        if zero_bad:
            problems.append(f"{s}: zero-candidate units that did not reach the time limit: {zero_bad}")
    if not RETRY_DONE.exists():
        problems.append("the corrective retry pass (data/repair_pilot/run_final_v2_retry.sh) has not completed")
    report["coverage_problems"] = problems
    if problems and not args.interim:
        raise SystemExit("refusing to report FINAL results:\n  " + "\n  ".join(problems))
    for s in SETS:
        if s not in report["audit"]:
            continue
        u = per_unit(s)
        frames[s] = u
        entry = {"solved_by_128s": solved_counts(u, 128).to_dicts(),
                 "curves": u.group_by(["method", "wall_s", "target_id"]).agg(pl.col("success_umfe").cast(pl.Float64).mean())
                 .group_by(["method", "wall_s"]).agg(pl.col("success_umfe").mean()).sort(["method", "wall_s"]).to_dicts(),
                 "quality_128s": u.filter(pl.col("wall_s") == 128).group_by("method").agg(
                     pl.col("best_ned").mean(), pl.col("best_log10_p").mean(), pl.col("evals_to_first").median(),
                     pl.col("seconds_to_first").median()).sort("method").to_dicts(),
                 "paired": [r for a, b in PAIRS for w in (16, 128) for m in ("success_umfe", "best_ned")
                            if (r := paired(u, a, b, w, m)) is not None]}
        report["sets"][s] = entry
    if "eterna100_v2" in frames and "eterna100_v1only" in frames:
        v2 = load_manifest(MANIFESTS_DIR / "final_eterna100_v2.json")["targets"]
        v1only_numbers = {t["id"].split(":")[1] for t in load_manifest(MANIFESTS_DIR / "final_eterna100_v1only.json")["targets"]}
        shared = [t["id"] for t in v2 if t["id"].split(":")[1] not in v1only_numbers]
        a = solved_counts(frames["eterna100_v2"].filter(pl.col("target_id").is_in(shared)), 128)
        b = solved_counts(frames["eterna100_v1only"], 128)
        v1 = a.join(b, on="method", suffix="_19").select(
            "method", (pl.col("solved_any_seed") + pl.col("solved_any_seed_19")).alias("solved_any_seed"),
            (pl.col("solved_mean_over_seeds") + pl.col("solved_mean_over_seeds_19")).alias("solved_mean_over_seeds"),
            (pl.col("targets") + pl.col("targets_19")).alias("targets"))
        report["sets"]["eterna100_v1_combined"] = {"solved_by_128s": v1.to_dicts(), "shared_structures": len(shared)}
    if args.eternafold and "eterna100_v2" in frames:
        report["eternafold_v2_best_designs"] = eternafold_check(frames)
    out = PILOT_DIR / ("final_v2_report_INTERIM.json" if args.interim else "final_v2_report.json")
    out.write_text(json.dumps(report, indent=1, default=float))
    print(f"[{report['status']}] written to {out}")
    for s, e in report["sets"].items():
        print(f"## {s}")
        for r in e["solved_by_128s"]:
            print(f"  {r['method']:24s} solved (any seed) {r['solved_any_seed']:3d} / {r['targets']}   mean over seeds {r['solved_mean_over_seeds']:.1f}")
    print(json.dumps(report["audit"], indent=1))


if __name__ == "__main__":
    main()
