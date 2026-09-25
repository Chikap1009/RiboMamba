"""The Phase 4 verdicts: the frozen protocol's primary endpoints, tests and guardrails (RESULTS.md P7, P8).

Reads what scripts/phase4_evaluate.py wrote (one likelihood file and one harness evaluation per trained
model) and reports, for the three architectures (roles tf, bimamba, ar):

  per trained model   E1 test bits/nt (diffusion models; the AR value is exact and secondary),
                      E2 mean beats_shuffles, E3 mean ned_mfe, EternaFold's ef_ned_vienna, guardrails
  primary tests       E1 BiMamba vs Transformer; E2 and E3 BiMamba vs Transformer and vs AR Mamba:
                      the exact seed-level permutation test (5 vs 5), Holm-adjusted together
  effect sizes        E1: difference in bits/nt, 95 % cluster bootstrap over test FAMILIES (per-sequence
                      differences of the seed-averaged nats, paired by sequence); E2/E3: difference of
                      means, 95 % hierarchical bootstrap over trained models and their samples
  robustness          an E3 win counts as oracle-robust only if ef_ned_vienna moves the same way
  guardrails          <= 5 % samples with a >= 80 %-identity training relative; >= 95 % distinct;
                      mean GC within +-0.05 of the real reference. A model failing one has its E2/E3
                      flagged as not interpretable.

Wording (P8): "X beats Y on E" needs a Holm-adjusted p <= 0.05; otherwise "no detectable difference
with 5 seeds", never "equal".

Usage:
    python scripts/phase4_statistics.py                                  # test split, runs from the summaries
    python scripts/phase4_statistics.py --split val --runs tf=a,b bimamba=c,d   # explicit runs (checks)
"""

import argparse
import json
import math
import sys

import numpy as np
import polars as pl

from ribomamba.eval.stats import cluster_bootstrap_ci, hierarchical_bootstrap, holm, seed_permutation_test
from ribomamba.paths import EVAL_DIR, REPO_ROOT

sys.path.insert(0, str(REPO_ROOT / "scripts"))
from phase4_evaluate import final_runs, likelihood_output, sample_tag  # noqa: E402  (same names as the driver)

ROLES = {"tf": "tf_M", "bimamba": "bimamba_M", "ar": "ar_mamba_M"}
PRIMARY = [("E1", "bimamba", "tf"), ("E2", "bimamba", "tf"), ("E2", "bimamba", "ar"),
           ("E3", "bimamba", "tf"), ("E3", "bimamba", "ar")]
METRIC = {"E2": "beats_shuffles", "E3": "ned_mfe"}
HIGHER_IS_BETTER = {"E1": False, "E2": True, "E3": False}


def harness_name(run: str, split: str) -> str:
    return f"{split}_{run}_{sample_tag(run, 1.0)}"


def per_model(run: str, split: str) -> dict:
    """Everything the tests need from one trained model's evaluation outputs."""
    out = {"run": run}
    lik = likelihood_output(run, "", split)
    if lik.exists():
        table = pl.read_parquet(lik)
        out["nats"] = table["nats_mean"].to_numpy()                       # per test sequence, in split order
        out["families"], out["lengths"] = table["family"].to_list(), table["length"].to_numpy()
        out["E1"] = float(out["nats"].sum() / out["lengths"].sum() / math.log(2))
    samples = pl.read_parquet(EVAL_DIR / f"{harness_name(run, split)}.parquet")
    report = json.loads((EVAL_DIR / f"{harness_name(run, split)}.json").read_text())
    for endpoint, metric in METRIC.items():
        out[f"{endpoint}_values"] = samples[metric].cast(pl.Float64).to_numpy()
        out[endpoint] = float(np.nanmean(out[f"{endpoint}_values"]))
    out["ef_ned_vienna"] = float(np.nanmean(samples["ef_ned_vienna"].cast(pl.Float64).to_numpy()))
    summary, real = report["samples"]["summary"], report["reference"]["real"]["summary"]
    out["guardrails"] = {
        "copying (share with a >= 80 % training relative <= 0.05)": summary["train_relative_ge_80"]["mean"] <= 0.05,
        "collapse (distinct share >= 0.95)": summary["distinct_fraction"] >= 0.95,
        "composition (|GC - real GC| <= 0.05)": abs(summary["gc"]["mean"] - real["gc"]["mean"]) <= 0.05,
    }
    out["guardrail_values"] = {"train_relative_ge_80": summary["train_relative_ge_80"]["mean"],
                               "distinct_fraction": summary["distinct_fraction"],
                               "gc": summary["gc"]["mean"], "real_gc": real["gc"]["mean"]}
    return out


def effect_size(endpoint: str, a: list[dict], b: list[dict]) -> tuple[float, float, float]:
    """(difference a - b, 95 % low, high) in the endpoint's units, by the protocol's bootstrap."""
    if endpoint == "E1":
        diff = np.mean([m["nats"] for m in a], axis=0) - np.mean([m["nats"] for m in b], axis=0)   # (N,) per sequence
        return cluster_bootstrap_ci(diff / math.log(2), a[0]["families"], denominators=a[0]["lengths"])
    reps_a = hierarchical_bootstrap([m[f"{endpoint}_values"][~np.isnan(m[f"{endpoint}_values"])] for m in a], seed=0)
    reps_b = hierarchical_bootstrap([m[f"{endpoint}_values"][~np.isnan(m[f"{endpoint}_values"])] for m in b], seed=1)
    d = reps_a - reps_b
    est = np.mean([m[endpoint] for m in a]) - np.mean([m[endpoint] for m in b])
    return float(est), float(np.percentile(d, 2.5)), float(np.percentile(d, 97.5))


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--split", default="test", choices=["val", "test"])
    p.add_argument("--runs", nargs="*", default=[], help="role=run1,run2,... overrides (roles: tf, bimamba, ar)")
    p.add_argument("--out", help="JSON output (default data/eval/phase4_statistics_<split>.json)")
    args = p.parse_args()

    runs = {role: final_runs(prefix) for role, prefix in ROLES.items()
            if (REPO_ROOT / "checkpoints" / f"{prefix}_seeds_summary.json").exists()}
    for item in args.runs:
        role, names = item.split("=")
        runs[role] = names.split(",")
    models = {role: [per_model(r, args.split) for r in names] for role, names in runs.items()}

    report = {"split": args.split, "runs": runs, "per_model": {}, "primary": [], "robustness": {}}
    print(f"{'role':8} {'run':28} {'E1 bits/nt':>10} {'E2 beats':>9} {'E3 ned':>7} {'ef_ned_v':>8}  guardrails")
    for role, ms in models.items():
        for m in ms:
            e1 = (f"{m['E1']:.4f}" + ("*" if role == "ar" else "")) if "E1" in m else "-"
            ok = "pass" if all(m["guardrails"].values()) else "FAIL: " + ", ".join(
                k.split(" (")[0] for k, v in m["guardrails"].items() if not v)
            print(f"{role:8} {m['run']:28} {e1:>10} {m['E2']:9.4f} {m['E3']:7.4f} {m['ef_ned_vienna']:8.4f}  {ok}")
            report["per_model"][m["run"]] = {k: m[k] for k in ("E1", "E2", "E3", "ef_ned_vienna") if k in m} | {
                "guardrails": m["guardrails"], "guardrail_values": m["guardrail_values"], "role": role}

    if "ar" in models:
        print("* AR model: exact likelihood of the framed sequence (incl. <eos>); secondary, not like-for-like (P7)")

    tests = [(e, a, b) for e, a, b in PRIMARY if a in models and b in models and (e != "E1" or all(
        "E1" in m for m in models[a] + models[b]))]
    raw = [seed_permutation_test([m[e] for m in models[a]], [m[e] for m in models[b]]) for e, a, b in tests]
    adjusted, reject = holm([r["p_value"] for r in raw]) if raw else ([], [])
    print(f"\n{'test':22} {'diff (95% CI)':>34} {'p':>7} {'Holm p':>7}  verdict")
    for (e, a, b), r, p_adj, rej in zip(tests, raw, adjusted, reject):
        est, low, high = effect_size(e, models[a], models[b])
        better = (est < 0) != HIGHER_IS_BETTER[e]                          # direction: is `a` the better one?
        flagged = [m["run"] for m in models[a] + models[b] if e != "E1" and not all(m["guardrails"].values())]
        if flagged:
            verdict = f"not interpretable (guardrail failed: {', '.join(flagged)})"
        elif rej:
            verdict = f"{a} {'beats' if better else 'loses to'} {b}"
        else:
            verdict = "no detectable difference with 5 seeds" if len(models[a]) == 5 else "no detectable difference"
        print(f"{e} {a} vs {b:9} {est:+.4f} [{low:+.4f}, {high:+.4f}] {r['p_value']:7.4f} {p_adj:7.4f}  {verdict}")
        report["primary"].append({"endpoint": e, "a": a, "b": b, "difference": est, "ci_low": low, "ci_high": high,
                                  "p_value": r["p_value"], "p_holm": float(p_adj), "verdict": verdict})
        if e == "E3":
            ef = np.mean([m["ef_ned_vienna"] for m in models[a]]) - np.mean([m["ef_ned_vienna"] for m in models[b]])
            same_way = bool(np.sign(ef) == np.sign(est))
            report["robustness"][f"E3 {a} vs {b}"] = {"ef_ned_vienna_difference": float(ef), "same_direction": same_way}
            print(f"   robustness: ef_ned_vienna difference {ef:+.4f} -> "
                  f"{'same direction (oracle-robust if a win)' if same_way else 'opposite: ViennaRNA-dependent'}")
    print("Intervals: E1 resamples test FAMILIES only (P8), so it cannot see training-seed variation and can\n"
          "exclude 0 between identical architectures (found in the validation check, 2026-09-25); E2/E3 resample\n"
          "trained models and samples. Claims rest on the seed-level test (Holm p), never on an interval alone.")
    out = args.out or EVAL_DIR / f"phase4_statistics_{args.split}.json"
    with open(out, "w") as f:
        json.dump(report, f, indent=2)
    print(f"-> {out}")


if __name__ == "__main__":
    main()
