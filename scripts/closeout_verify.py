"""Closeout consistency checks (2026-09-29): verify the recorded final state from saved artifacts.

  python scripts/closeout_verify.py --out <file.json>     # writes a JSON report; never modifies run data

Checks (read-only on data/repair_pilot, except that --replay runs a few seconds of search in memory):
  1. FINAL v2 report: status, provenance, coverage, superseded files; every expected unit re-validated
     (status, config hash, trace sha256, row consistency) and superseded units still preserved.
  2. Frozen v2 configurations: rebuilding each set's configuration from the CURRENT code gives the
     recorded config hash (methods, settings, targets, seeds, budget, time limit unchanged).
  3. Efficiency study: declared comparison and profiles re-validated; process identity per unit
     (cold = one process per unit; warm = one persistent process); saved gates in compare.json.
  4. The eager TCD reference is still the default of the historical method name.
  5. (--replay) Deterministic prefix replay: the first N candidates of deterministic v2 methods,
     re-run now with the current code, equal the first N candidates of the saved final traces.
"""

import argparse
import json
from pathlib import Path

import polars as pl

from ribomamba.design import runner
from ribomamba.design.manifest import MANIFESTS_DIR, load_manifest, select
from ribomamba.paths import PILOT_DIR

SETS = {"eterna100_v2": "final_eterna100_v2", "eterna100_v1only": "final_eterna100_v1only",
        "rfam_taneda27": "final_rfam_taneda27"}
EFFICIENCY_RUNS = {"ew_dev_tcdgraph_v1": "cold, 4 concurrent units (declared comparison)",
                   "prof_tcd_iso_cold_v1": "LABELLED cold but in fact warm (runner quirk fixed in 82361cc)",
                   "prof_tcd_iso_warm_v1": "warm, isolated", "prof_tcd_iso_cold_v2": "cold, isolated"}


def revalidate(d: Path) -> dict:
    cfg = json.loads((d / "run_config.json").read_text())
    reasons, pids, per_method_pids = {}, set(), {}
    for m in cfg["methods"]:
        for t in cfg["target_ids"]:
            for s in cfg["seeds"]:
                key = runner.unit_key(m, t, s)
                why = runner.validate_unit(d, key, cfg["config_hash"], cfg["budget"]) or "valid"
                reasons[why] = reasons.get(why, 0) + 1
                p = runner.unit_paths(d, key)[1]
                if p.exists():
                    pid = json.loads(p.read_text()).get("pid")
                    pids.add(pid)
                    per_method_pids.setdefault(m, set()).add(pid)
    n = len(cfg["methods"]) * len(cfg["target_ids"]) * len(cfg["seeds"])
    return {"config_hash": cfg["config_hash"], "expected_units": n, "validation": reasons,
            "distinct_worker_processes": len(pids),
            "distinct_processes_per_method": {m: len(v) for m, v in per_method_pids.items()}}


def rebuilt_hash(set_name: str, manifest_name: str) -> dict:
    d = PILOT_DIR / f"final_v2_{set_name}"
    cfg = json.loads((d / "run_config.json").read_text())
    manifest = load_manifest(MANIFESTS_DIR / f"{manifest_name}.json")
    targets = select(manifest, "all")
    rebuilt = runner.make_config(manifest, "all", targets, list(cfg["methods"]), cfg["seeds"], cfg["budget"],
                                 unit_time_limit_s=cfg.get("unit_time_limit_s"))
    return {"recorded": cfg["config_hash"], "rebuilt_from_current_code": rebuilt["config_hash"],
            "equal": cfg["config_hash"] == rebuilt["config_hash"]}


def replay_prefix(n: int) -> list[dict]:
    """First n candidates of deterministic methods, re-run now, versus the saved final V2 traces."""
    from ribomamba.design.search import BudgetExhausted, Evaluator, Target
    d = PILOT_DIR / "final_v2_eterna100_v2"
    cfg = json.loads((d / "run_config.json").read_text())
    structures = {t["id"]: t["structure"] for t in load_manifest(MANIFESTS_DIR / "final_eterna100_v2.json")["targets"]}
    out = []
    for tid in ("eterna100_v2:12", "eterna100_v2:38"):
        for method in ("samfeo", "samfeo_efilter", "samfeo_tcdprop_efilter", "random_pairs", "tcd_sample"):
            saved = pl.read_parquet(runner.unit_paths(d, runner.unit_key(method, tid, 0))[0]).sort("eval_index")
            target = Target(tid, structures[tid])
            ev = Evaluator(target, budget=n)
            try:
                runner.METHODS[method](target, 0, ev, cfg["methods"][method])
            except BudgetExhausted:
                pass
            now = [r["sequence"] for r in ev.rows]
            then = saved["sequence"].head(n).to_list()
            out.append({"target": tid, "method": method, "n": len(now), "identical_prefix": now == then,
                        "first_mismatch": next((i for i, (a, b) in enumerate(zip(now, then)) if a != b), None)})
            print(json.dumps(out[-1]), flush=True)
    return out


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--out", required=True)
    p.add_argument("--replay", type=int, default=0, help="replay the first N candidates (0 = skip)")
    args = p.parse_args()
    rep: dict = {}
    fr = json.loads((PILOT_DIR / "final_v2_report.json").read_text())
    rep["final_report"] = {"status": fr["status"], "coverage_problems": fr["coverage_problems"],
                           "provenance": {k: fr["provenance"][k] for k in ("generated_utc", "git_commit",
                                          "tracked_changes_uncommitted", "retry_pass_done_utc")},
                           "audit_validation": {s: a["validation"] for s, a in fr["audit"].items()},
                           "error_units": {s: len(a["error_units"]) for s, a in fr["audit"].items()},
                           "pre_fix_units_in_place": {s: a.get("pre_fix_units_in_place") for s, a in fr["audit"].items()},
                           "superseded_report_files": [x["archived_to"] for x in fr["supersedes"]["all_superseded_files"]],
                           "superseded_files_present": all((PILOT_DIR.parent.parent / x["archived_to"]).exists()
                                                           for x in fr["supersedes"]["all_superseded_files"])}
    rep["final_units_now"] = {s: revalidate(PILOT_DIR / f"final_v2_{s}") for s in SETS}
    sup = PILOT_DIR / "final_v2_eterna100_v2" / "units_superseded"
    rep["superseded_units_preserved"] = {m.name: len(list(m.glob("*.json"))) for m in sorted(sup.iterdir())}
    rep["frozen_v2_config_hashes"] = {s: rebuilt_hash(s, m) for s, m in SETS.items()}
    rep["efficiency_runs"] = {r: {"label": lab, **revalidate(PILOT_DIR / r)} for r, lab in EFFICIENCY_RUNS.items()}
    cmp = json.loads((PILOT_DIR / "ew_dev_tcdgraph_v1" / "compare.json").read_text())
    rep["efficiency_gates_saved"] = {k: cmp["gates"][k] for k in ("E1_met", "E2_met", "Q_ok", "S_success", "S_quality",
                                                                  "continue_to_new_protocol")}
    rep["efficiency_ratios_saved"] = {k: cmp["gates"][k]["median_ratio"] for k in
                                      ("E1_proposal_overhead_ratio", "E2_evals_ratio_64s", "E2_evals_ratio_16s")}
    from ribomamba.design.baselines import BASELINE_SETTINGS
    rep["eager_reference_default"] = {
        "samfeo_tcdprop_efilter_tcd_forward": BASELINE_SETTINGS["samfeo_tcdprop_efilter"].get("tcd_forward", "eager (default)"),
        "samfeo_tcdprop_efilter_graph_tcd_forward": BASELINE_SETTINGS["samfeo_tcdprop_efilter_graph"].get("tcd_forward")}
    if args.replay:
        rep["deterministic_prefix_replay"] = replay_prefix(args.replay)
    Path(args.out).write_text(json.dumps(rep, indent=1, default=str))
    print(json.dumps({k: v for k, v in rep.items() if k != "deterministic_prefix_replay"}, indent=1, default=str))


if __name__ == "__main__":
    main()
