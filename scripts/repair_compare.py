"""Compare methods across pilot run directories that share targets, seeds and manifest.

  python scripts/repair_compare.py --runs ew_dev1024_v1 ew_dev1024_neural_v1 --name dev_stageB \\
      --pairs neural_feedback_edits:feedback_pair_edits neural_feedback_edits:neural_random_edits

Refuses to combine runs whose manifest hash, subset, target list or seeds differ.
Candidate budgets may differ (checkpoints are taken at every budget <= each run's own).
Writes data/repair_pilot/compare_<name>.{json,md}.
"""

import argparse
import json

import polars as pl

from ribomamba.design import summary
from ribomamba.design.runner import atomic_write_json
from ribomamba.paths import PILOT_DIR


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--runs", nargs="+", required=True)
    p.add_argument("--name", required=True)
    p.add_argument("--pairs", nargs="*", default=[], help="a:b method pairs for paired per-target differences")
    args = p.parse_args()

    frames, walls, configs = [], [], []
    for run in args.runs:
        config, _, cp = summary.checkpoints(PILOT_DIR / run)
        configs.append(config)
        frames.append(cp.with_columns(pl.lit(run).alias("run")))
        walls.append(summary.wall_table(PILOT_DIR / run).with_columns(pl.lit(run).alias("run")))
    ref = configs[0]
    for c in configs[1:]:
        for key in ("subset", "target_ids", "seeds"):
            if c[key] != ref[key]:
                raise SystemExit(f"runs differ in {key}; refusing to compare")
        if c["manifest"]["content_sha256"] != ref["manifest"]["content_sha256"]:
            raise SystemExit("runs use different manifests; refusing to compare")
    cp = pl.concat(frames, how="diagonal_relaxed")
    dup = cp.group_by(["method", "target_id", "seed", "budget"]).len().filter(pl.col("len") > 1)
    if dup.height:
        raise SystemExit(f"a method appears in more than one run: {dup['method'].unique().to_list()}")
    agg = summary.aggregate(cp)
    comparisons = []
    for pair in args.pairs:
        a, b = pair.split(":")
        for budget in sorted(cp["budget"].unique().to_list()):
            for metric in ("success_umfe", "best_ned", "best_log10_p"):
                result = summary.paired(cp, a, b, metric, budget)
                if result is not None:
                    comparisons.append(result)
    wall = pl.concat(walls, how="diagonal_relaxed").sort(["wall_s", "method"])
    out = {"runs": args.runs, "manifest": ref["manifest"], "subset": ref["subset"], "seeds": ref["seeds"],
           "n_targets": len(ref["target_ids"]), "summary": agg, "paired": comparisons, "wall": wall.to_dicts()}
    atomic_write_json(PILOT_DIR / f"compare_{args.name}.json", out)
    md = [f"# Comparison {args.name}", "", f"Runs: {', '.join(args.runs)}; manifest {ref['manifest']['name']} "
          f"({ref['manifest']['content_sha256'][:12]}); subset {ref['subset']}, {len(ref['target_ids'])} targets, "
          f"seeds {ref['seeds']}. Target-level means (seeds averaged within target), 95% bootstrap over targets.", ""]
    for budget in sorted(cp["budget"].unique().to_list()):
        md += [f"## Budget {budget} candidate evaluations", "", summary.markdown_table(agg, budget), ""]
    md += ["## Paired per-target differences (a - b)", "",
           "| budget | a | b | metric | mean diff [95% CI] | a better / b better / ties |", "|---|---|---|---|---|---|"]
    md += [f"| {c['budget']} | {c['a']} | {c['b']} | {c['metric']} | {c['mean_diff']:.4f} "
           f"[{c['low']:.4f}, {c['high']:.4f}] | {c['a_better']} / {c['b_better']} / {c['ties']} |" for c in comparisons]
    md += ["", "## By method wall time per unit (harness re-scoring subtracted for self-scored methods)", "",
           "| wall s | method | uMFE success | best NED | truncated | mean evals |", "|---|---|---|---|---|---|"]
    md += [f"| {r['wall_s']} | {r['method']} | {100 * r['success_umfe']:.0f}% | {r['best_ned']:.4f} "
           f"| {r['truncated_share']:.2f} | {r['mean_evals']:.0f} |" for r in wall.to_dicts()]
    (PILOT_DIR / f"compare_{args.name}.md").write_text("\n".join(md) + "\n")
    print("\n".join(md))


if __name__ == "__main__":
    main()
