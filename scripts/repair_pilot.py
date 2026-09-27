"""Repair pilot, Stage A (RESEARCH_PLAN.md): manifest, resumable runs, summaries. Validation only.

  python scripts/repair_pilot.py manifest [--which rfam|eternaweb]
      rfam:      manifests/repair_pilot_val_v1.json from data/targets/rfam_val.parquet (easy tier)
      eternaweb: manifests/eternaweb_dev_v1.json, hard Eterna web puzzles (ribomamba/design/hard_manifest.py)
      (written once; rebuilding must reproduce it exactly)
  python scripts/repair_pilot.py run --run smoke64 --manifest eternaweb_dev_v1 --subset smoke --budget 64 --seeds 0 1 2 \\
      --methods random_pairs random_pair_edits feedback_pair_edits samfeo --workers 4 --max-hours 1
      resumable: rerunning the same command skips finished units; a changed
      configuration needs a new --run name. Confirmation targets need --confirmation-look.
  python scripts/repair_pilot.py summarize --run smoke64
      writes summary.json and summary.md into the run directory

CPU only unless --gpu (Stage B neural proposals): CUDA is otherwise hidden; workers are
capped at 4 and one OpenMP thread each.
"""

import argparse
import json
import os
import sys

if "--gpu" not in sys.argv:
    os.environ["CUDA_VISIBLE_DEVICES"] = ""
os.environ.setdefault("OMP_NUM_THREADS", "1")

from ribomamba.design import manifest as mf                       # noqa: E402
from ribomamba.design import runner, summary                      # noqa: E402
from ribomamba.design.baselines import samfeo_checkout_problem    # noqa: E402
from ribomamba.design import hard_manifest as hm                  # noqa: E402
from ribomamba.paths import MANIFESTS_DIR, PILOT_DIR              # noqa: E402

DEFAULT_WORKERS = 4
DEFAULT_METHODS = ["random_pairs", "random_pair_edits", "feedback_pair_edits", "samfeo"]


def manifest_path(name: str):
    return MANIFESTS_DIR / f"{name}.json"


def cmd_manifest(args) -> None:
    if args.which == "final":
        from ribomamba.design.final_manifest import build_all
        print(json.dumps(build_all(), indent=1))
        return
    if args.which == "eternaweb":
        hm.check_source()
        manifest = hm.build(workers=args.workers)
        outcome = mf.write_manifest(manifest, hm.PATH)
        print(json.dumps({"manifest": str(hm.PATH), "outcome": outcome, "content_sha256": manifest["content_sha256"],
                          "funnel": manifest["funnel"]}, indent=1))
        return
    manifest = mf.build_manifest()
    natives = [t["native_control"] for t in manifest["targets"]]
    control = {"native_mfe_backtrack": sum(c["mfe_backtrack"] for c in natives),
               "native_umfe": sum(c["umfe"] for c in natives), "n": len(natives)}
    if control["native_mfe_backtrack"] != control["n"]:
        raise SystemExit(f"positive control failed: {control}")
    outcome = mf.write_manifest(manifest)
    print(json.dumps({"manifest": str(mf.MANIFEST_PATH), "outcome": outcome,
                      "content_sha256": manifest["content_sha256"], "funnel": manifest["funnel"],
                      "exclusions": len(manifest["exclusions"]), "native_control": control}, indent=1))


def cmd_run(args) -> None:
    if args.workers < 1:
        raise SystemExit("--workers must be positive")
    if "samfeo" in args.methods and (problem := samfeo_checkout_problem()):
        raise SystemExit(problem)
    if args.manifest.startswith("final_"):
        from ribomamba.design.final_manifest import require_protocol_frozen
        print(f"protocol frozen on {require_protocol_frozen()}; final manifest {args.manifest}", flush=True)
    manifest = mf.load_manifest(manifest_path(args.manifest))
    targets = mf.select(manifest, args.subset)
    config = runner.make_config(manifest, args.subset, targets, args.methods, args.seeds, args.budget,
                                unit_time_limit_s=args.unit_time_limit)
    if any(t["subset"] == "confirmation" for t in targets):
        runner.log_confirmation_look(args.run, args.subset, args.confirmation_look, config)
    design_targets = [{"id": t["id"], "structure": t["structure"]} for t in targets]    # no native sequences
    counts = runner.run(PILOT_DIR / args.run, config, design_targets, workers=args.workers,
                        max_hours=args.max_hours, retry_errors=args.retry_errors)
    print(json.dumps(counts))


def cmd_summarize(args) -> None:
    run_dir = PILOT_DIR / args.run
    config, statuses, cp = summary.checkpoints(run_dir)
    traces = summary.load_run(run_dir)[2]
    agg = summary.aggregate(cp)
    budgets = sorted(cp["budget"].unique().to_list())
    methods = config["methods"]
    comparisons = []
    for b in budgets:
        for a, c in [("feedback_pair_edits", "random_pair_edits"), ("feedback_pair_edits", "random_pairs"),
                     ("samfeo", "feedback_pair_edits"), ("samfeo", "random_pair_edits")]:
            if a in methods and c in methods:
                for metric in ("success_umfe", "best_ned"):
                    if (result := summary.paired(cp, a, c, metric, b)) is not None:
                        comparisons.append(result)
    manifest = mf.load_manifest(manifest_path(config["manifest"]["name"]))
    per_eval = summary.per_eval_seconds(traces, statuses)
    lengths_all = [t["length"] for t in manifest["targets"]]
    estimates = {f"{len(lengths_all)} targets x {len(config['seeds'])} seeds x {b} evals": summary.runtime_estimate(
        per_eval, lengths_all, len(config["seeds"]), b, DEFAULT_WORKERS) for b in summary.BUDGETS}
    status_counts = {}
    for s in statuses:
        status_counts[f"{s['method']}:{s['status']}"] = status_counts.get(f"{s['method']}:{s['status']}", 0) + 1
    out = {"run": args.run, "config_hash": config["config_hash"], "status_counts": status_counts,
           "errors": [{"unit": s["unit"], "reason": s["reason"]} for s in statuses if s["status"] == "error"],
           "summary": agg, "paired": comparisons, "runtime_estimates": estimates,
           "per_eval_seconds": per_eval.to_dicts()}
    runner.atomic_write_json(run_dir / "summary.json", out)
    md = [f"# Pilot summary: {args.run}", "", f"config_hash `{config['config_hash']}`; subset `{config['subset']}`, "
          f"{len(config['target_ids'])} targets, seeds {config['seeds']}, budget {config['budget']}.",
          "Means over targets (seeds averaged within target first), 95% bootstrap intervals over targets.", ""]
    for b in budgets:
        md += [f"## Budget {b}", "", summary.markdown_table(agg, b), ""]
    md += ["## Paired per-target differences (a - b)", "",
           "| budget | a | b | metric | mean diff [95% CI] | a better / b better / ties |", "|---|---|---|---|---|---|"]
    md += [f"| {c['budget']} | {c['a']} | {c['b']} | {c['metric']} | {c['mean_diff']:.3f} "
           f"[{c['low']:.3f}, {c['high']:.3f}] | {c['a_better']} / {c['b_better']} / {c['ties']} |"
           for c in comparisons]
    walls = summary.wall_table(run_dir)
    out["wall_checkpoints"] = walls.to_dicts()
    runner.atomic_write_json(run_dir / "summary.json", out)
    md += ["", "## Success and best NED by method wall time per unit", "",
           "Harness re-scoring is subtracted for external baselines. truncated = share of units whose "
           "candidate budget ended before this wall time (they might have improved further).", "",
           "| wall s | method | uMFE success | best NED | truncated | mean evals |", "|---|---|---|---|---|---|"]
    md += [f"| {r['wall_s']} | {r['method']} | {100 * r['success_umfe']:.0f}% | {r['best_ned']:.4f} "
           f"| {r['truncated_share']:.2f} | {r['mean_evals']:.0f} |" for r in walls.to_dicts()]
    md += ["", "## Runtime estimates (CPU only, 4 workers)", "", "```", json.dumps(estimates, indent=1), "```", "",
           "## Unit statuses", "", "```", json.dumps(status_counts, indent=1), "```"]
    (run_dir / "summary.md").write_text("\n".join(md) + "\n")
    print("\n".join(md))


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="command", required=True)
    m = sub.add_parser("manifest")
    m.add_argument("--which", choices=["rfam", "eternaweb", "final"], default="rfam")
    m.add_argument("--workers", type=int, default=DEFAULT_WORKERS)
    r = sub.add_parser("run")
    r.add_argument("--run", required=True, help="run directory name under data/repair_pilot/")
    r.add_argument("--manifest", default=hm.NAME,
                   choices=sorted(p.stem for p in MANIFESTS_DIR.glob("*.json") if p.stem != "confirmation_looks"))
    r.add_argument("--unit-time-limit", type=float, default=None,
                   help="per-unit method-time limit in seconds (final protocol); omitted = none")
    r.add_argument("--subset", required=True, choices=mf.SUBSETS)
    r.add_argument("--budget", type=int, default=64)
    r.add_argument("--seeds", type=int, nargs="+", default=[0, 1, 2])
    r.add_argument("--methods", nargs="+", default=DEFAULT_METHODS)
    r.add_argument("--workers", type=int, default=DEFAULT_WORKERS)
    r.add_argument("--max-hours", type=float, default=None,
                   help="optional run wall-time limit; omitted means no time cap")
    r.add_argument("--retry-errors", action="store_true")
    r.add_argument("--gpu", action="store_true", help="let neural proposal methods use the GPU")
    r.add_argument("--confirmation-look", default="", help="declared candidate revision (required for confirmation)")
    s = sub.add_parser("summarize")
    s.add_argument("--run", required=True)
    args = p.parse_args()
    {"manifest": cmd_manifest, "run": cmd_run, "summarize": cmd_summarize}[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
