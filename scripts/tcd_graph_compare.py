"""Declared development comparison for the TCD proposal-overhead study (run ew_dev_tcdgraph_v1).

  python scripts/tcd_graph_compare.py [--run ew_dev_tcdgraph_v1]

Endpoints and gates exactly as fixed in docs/experiments/2026-09-28-tcd-inference-efficiency.md
("Criteria (final)") before any optimised outcome was measured:
  E1  median over targets of [reference / graph] proposal time per evaluated candidate >= 2.0
  E2  median over targets of [graph / reference] evaluations by 64 s >= 1.5 and by 16 s >= 1.2
  Q   unacceptable if graph - reference uMFE < -3 pp or best NED > +0.005 (point estimates, 16 or 64 s)
  S   graph - samfeo_efilter: success (uMFE >= +5 pp, interval above 0, at 16 or 64 s) or quality
      (best NED interval below 0 at BOTH 16 and 64 s and uMFE point >= -2 pp at both)
Seeds are averaged within targets; bootstrap 95 % intervals over targets. Writes <run>/compare.json.
"""

import argparse
import json
import math

import numpy as np
import polars as pl

from ribomamba.design import summary
from ribomamba.eval.stats import bootstrap_ci
from ribomamba.paths import PILOT_DIR

REF, GRAPH, SCREEN, SAMFEO = "samfeo_tcdprop_efilter", "samfeo_tcdprop_efilter_graph", "samfeo_efilter", "samfeo"
WALLS = (1, 4, 16, 64)


def unit_table(d) -> pl.DataFrame:
    """Per (method, target, seed, wall): success, best NED, best log10 P and evaluations within that method time."""
    _, statuses, traces = summary.load_run(d)
    rows = []
    for st in statuses:
        t = traces.filter((pl.col("method") == st["method"]) & (pl.col("target_id") == st["target_id"])
                          & (pl.col("seed") == st["seed"])).sort("eval_index")
        wall = summary.method_wall(t, st["method"]) if t.height else pl.Series([], dtype=pl.Float64)
        t = t.with_columns(wall.alias("mw")) if t.height else t
        for w in WALLS:
            pre = t.filter(pl.col("mw") <= w) if t.height else t
            if st["status"] == "error":                  # an error unit counts as unsolved with no design
                pre = pre.clear()
            ok = pre.filter(pl.col("ned").is_not_nan() & pl.col("valid")) if pre.height else pre
            rows.append({"method": st["method"], "target_id": st["target_id"], "seed": st["seed"], "wall_s": w,
                         "status": st["status"], "error": st["status"] == "error",
                         "evals": pre.height, "umfe": bool(pre["umfe"].any()) if pre.height else False,
                         "best_ned": float(ok["ned"].min()) if ok.height else math.nan,
                         "best_log10_p": float(pre["log_p_target"].max()) / math.log(10) if pre.height else math.nan,
                         "proposal_ms_per_eval": 1000 * st.get("proposal_wall_s", math.nan) / max(1, st["n_rows"]),
                         "proposal_calls_per_eval": st.get("proposal_calls", 0) / max(1, st["n_rows"]),
                         "model_calls": st.get("model_calls", 0), "model_wall_s": st.get("model_wall_s", 0.0),
                         "unit_evals": st["n_rows"], "peak_rss_mb": st.get("peak_rss_mb"),
                         "peak_gpu_mb": st.get("peak_gpu_mb")})
    return pl.DataFrame(rows)


def per_target(u: pl.DataFrame, method: str, wall: int, col: str) -> pl.DataFrame:
    x = u.filter((pl.col("method") == method) & (pl.col("wall_s") == wall))
    return x.group_by("target_id").agg(pl.col(col).cast(pl.Float64).mean().alias(col))


def paired(u, a, b, wall, col):
    j = per_target(u, a, wall, col).join(per_target(u, b, wall, col), on="target_id", suffix="_b")
    j = j.filter(pl.col(col).is_not_nan() & pl.col(f"{col}_b").is_not_nan())
    d = (j[col] - j[f"{col}_b"]).to_numpy()
    est, lo, hi = bootstrap_ci(d)
    better = (d < 0) if col == "best_ned" else (d > 0)
    worse = (d > 0) if col == "best_ned" else (d < 0)
    return {"a": a, "b": b, "wall_s": wall, "metric": col, "mean_diff": est, "low": lo, "high": hi,
            "a_better": int(better.sum()), "b_better": int(worse.sum()), "n": len(d)}


def ratio_median(u, num, den, wall, col):
    j = per_target(u, num, wall, col).join(per_target(u, den, wall, col), on="target_id", suffix="_d")
    r = (j[col] / j[f"{col}_d"]).to_numpy()
    return {"median_ratio": float(np.median(r)), "min": float(r.min()), "max": float(r.max()), "n": len(r)}


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--run", default="ew_dev_tcdgraph_v1")
    p.add_argument("--names", nargs=4, metavar=("REF", "GRAPH", "SCREEN", "SAMFEO"), default=None,
                   help="method names (only for dry runs of this script on older runs)")
    args = p.parse_args()
    global REF, GRAPH, SCREEN, SAMFEO
    if args.names:
        REF, GRAPH, SCREEN, SAMFEO = args.names
    d = PILOT_DIR / args.run
    u = unit_table(d)
    out = {"run": args.run, "units": u.filter(pl.col("wall_s") == 64).height,
           "status_counts": {f"{m}:{s}": n for m, s, n in u.filter(pl.col("wall_s") == 64)
                             .group_by("method", "status").len().iter_rows()},
           "units_without_design_64s": {m: n for m, n in u.filter((pl.col("wall_s") == 64) & (pl.col("evals") == 0))
                                        .group_by("method").len().iter_rows()}}
    means = (u.group_by("method", "wall_s").agg(
        pl.col("umfe").cast(pl.Float64).mean().alias("umfe"), pl.col("best_ned").fill_nan(None).mean().alias("best_ned"),
        pl.col("best_log10_p").fill_nan(None).mean().alias("best_log10_p"), pl.col("evals").median().alias("median_evals"),
        pl.col("proposal_ms_per_eval").median().alias("median_proposal_ms_per_eval"),
        pl.col("proposal_calls_per_eval").median().alias("median_proposal_calls_per_eval"),
        pl.col("peak_rss_mb").max().alias("max_peak_rss_mb"), pl.col("peak_gpu_mb").max().alias("max_peak_gpu_mb"))
        .sort("method", "wall_s"))
    out["means"] = means.to_dicts()
    e1 = ratio_median(u, REF, GRAPH, 64, "proposal_ms_per_eval")
    e2_64, e2_16 = ratio_median(u, GRAPH, REF, 64, "evals"), ratio_median(u, GRAPH, REF, 16, "evals")
    pairs = [paired(u, a, b, w, c) for a, b in ((GRAPH, REF), (GRAPH, SCREEN), (REF, SCREEN), (GRAPH, SAMFEO),
                                                (SCREEN, SAMFEO)) for w in (16, 64)
             for c in ("umfe", "best_ned", "best_log10_p")]
    get = {(r["a"], r["b"], r["wall_s"], r["metric"]): r for r in pairs}
    q_bad = [w for w in (16, 64) if get[(GRAPH, REF, w, "umfe")]["mean_diff"] < -0.03
             or get[(GRAPH, REF, w, "best_ned")]["mean_diff"] > 0.005]
    s_success = any(get[(GRAPH, SCREEN, w, "umfe")]["mean_diff"] >= 0.05 and get[(GRAPH, SCREEN, w, "umfe")]["low"] > 0
                    for w in (16, 64))
    s_quality = all(get[(GRAPH, SCREEN, w, "best_ned")]["high"] < 0 and get[(GRAPH, SCREEN, w, "umfe")]["mean_diff"] >= -0.02
                    for w in (16, 64))
    gates = {"E1_proposal_overhead_ratio": e1, "E1_met": e1["median_ratio"] >= 2.0,
             "E2_evals_ratio_64s": e2_64, "E2_evals_ratio_16s": e2_16,
             "E2_met": e2_64["median_ratio"] >= 1.5 and e2_16["median_ratio"] >= 1.2,
             "Q_unacceptable_regression_at": q_bad, "Q_ok": not q_bad,
             "S_success": s_success, "S_quality": s_quality}
    gates["continue_to_new_protocol"] = gates["E1_met"] and gates["E2_met"] and gates["Q_ok"] and (s_success or s_quality)
    out["gates"], out["paired"] = gates, pairs
    (d / "compare.json").write_text(json.dumps(out, indent=1, default=float))
    print(json.dumps({k: out[k] for k in ("units", "status_counts", "units_without_design_64s")}, indent=1))
    for r in out["means"]:
        print(f"  {r['method']:30s} {r['wall_s']:3d}s uMFE {100*r['umfe']:5.1f} % NED {r['best_ned']:.4f} "
              f"log10P {r['best_log10_p']:.2f} evals(med) {r['median_evals']:.0f} "
              f"prop ms/eval(med) {r['median_proposal_ms_per_eval']:.1f} calls/eval {r['median_proposal_calls_per_eval']:.2f}")
    for r in pairs:
        print(f"  {r['a']:30s} - {r['b']:24s} {r['metric']:12s} @{r['wall_s']:2d}s {r['mean_diff']:+.4f} "
              f"[{r['low']:+.4f}, {r['high']:+.4f}] a better {r['a_better']} / b better {r['b_better']} (n {r['n']})")
    print(json.dumps(gates, indent=1, default=float))


if __name__ == "__main__":
    main()
