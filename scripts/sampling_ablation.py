"""Sampling temperature x number of steps, for one checkpoint, on VALIDATION (Phase 3).

Grid, fixed before any result (logbook 2026-09-24 session 04, "ablation
pre-registration"): temperature in {0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 1.1, 1.2}
x steps in {16, 32, 64, 128, 256, 512}; 1,000 samples per setting with the
lengths of the validation reference (n = 1000, seed 0); sampling seed 0 for
every setting ("common random numbers": the same dice for every setting, so
differences come from the settings).

Stages (each skips work already done, so an interrupted run resumes):
    sample     GPU: scripts/sample.py for every setting -> samples/eval/<prefix>_T<t>_S<steps>.fasta
    evaluate   CPU: scripts/evaluate_samples.py for every sample file -> data/eval/<name>.json
    table      one row per setting -> data/eval/ablation_<prefix>.csv

Usage:
    python scripts/sampling_ablation.py --checkpoint checkpoints/tf_M_do0/best.pt --prefix tf_M_do0 --stage all
"""

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

import polars as pl

from ribomamba.paths import EVAL_DIR, REPO_ROOT

TEMPERATURES = (0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 1.1, 1.2)
STEPS = (16, 32, 64, 128, 256, 512)
SAMPLES_DIR = REPO_ROOT / "samples" / "eval"
TABLE_METRICS = ["beats_shuffles", "mfe_z", "ned_mfe", "p_mfe", "ef_ned_vienna", "oracles_agree", "gc",
                 "paired_fraction", "stems_per_100nt", "sibling_ge_80", "train_relative_ge_50"]
TABLE_DISTANCES = ["w1_mfe_z", "w1_ned_mfe", "w1_gc", "w1_beats_shuffles", "jsd_4mer"]


def name(prefix: str, t: float, steps: int) -> str:
    return f"{prefix}_T{t:.1f}_S{steps}"


def stage_sample(args) -> None:
    timings_path = EVAL_DIR / f"ablation_{args.prefix}_timings.json"
    timings = json.loads(timings_path.read_text()) if timings_path.exists() else {}
    SAMPLES_DIR.mkdir(parents=True, exist_ok=True)
    for t in TEMPERATURES:
        for steps in STEPS:
            out = SAMPLES_DIR / f"{name(args.prefix, t, steps)}.fasta"
            if out.exists():
                continue
            start = time.time()
            subprocess.run([sys.executable, "scripts/sample.py", "--checkpoint", args.checkpoint,
                            "--lengths-from", "val", "--lengths-n", "1000", "--lengths-seed", "0",
                            "--steps", str(steps), "--temperature", str(t), "--seed", "0",
                            "--out", str(out.with_suffix(".tmp"))], check=True, cwd=REPO_ROOT)
            out.with_suffix(".tmp").rename(out)                       # only complete files get the real name
            timings[out.stem] = round(time.time() - start, 1)
            EVAL_DIR.mkdir(parents=True, exist_ok=True)
            timings_path.write_text(json.dumps(timings, indent=2))
            print(f"sampled {out.stem} in {timings[out.stem]} s", flush=True)


def stage_evaluate(args) -> None:
    for t in TEMPERATURES:
        for steps in STEPS:
            n = name(args.prefix, t, steps)
            fasta = SAMPLES_DIR / f"{n}.fasta"
            if (EVAL_DIR / f"{n}.json").exists() or not fasta.exists():
                continue
            subprocess.run([sys.executable, "scripts/evaluate_samples.py", "--samples", str(fasta)],
                           check=True, cwd=REPO_ROOT, stdout=subprocess.DEVNULL)
            print(f"evaluated {n}", flush=True)


def stage_table(args) -> None:
    timings_path = EVAL_DIR / f"ablation_{args.prefix}_timings.json"
    timings = json.loads(timings_path.read_text()) if timings_path.exists() else {}
    rows = []
    for t in TEMPERATURES:
        for steps in STEPS:
            n = name(args.prefix, t, steps)
            path = EVAL_DIR / f"{n}.json"
            if not path.exists():
                continue
            report = json.loads(path.read_text())["samples"]
            row = {"temperature": t, "steps": steps, "sampling_seconds": timings.get(n)}
            for m in TABLE_METRICS:
                s = report["summary"][m]
                row[m], row[f"{m}_low"], row[f"{m}_high"] = s["mean"], s["low"], s["high"]
            row["distinct_fraction"] = report["summary"]["distinct_fraction"]
            row.update({d: report["distance_to_real"][d] for d in TABLE_DISTANCES})
            rows.append(row)
    table = pl.DataFrame(rows)
    table.write_csv(EVAL_DIR / f"ablation_{args.prefix}.csv")
    with pl.Config(tbl_rows=100, tbl_cols=30, tbl_width_chars=250):
        print(table.select(["temperature", "steps", "sampling_seconds", *TABLE_METRICS, "distinct_fraction",
                            *TABLE_DISTANCES]))
    print(f"steps rule (fixed 13:39, before any result): N = {steps_rule(table)}")


def steps_rule(table: pl.DataFrame, temperature: float = 1.0) -> int | None:
    """The pre-registered rule: the smallest grid N whose beats_shuffles AND ned_mfe at T = 1.0
    lie inside the 95 % intervals of the 512-step setting (more steps can only help; this finds
    where the gain has stopped)."""
    at_t = table.filter(pl.col("temperature") == temperature).sort("steps")
    if at_t.filter(pl.col("steps") == max(STEPS)).is_empty():
        return None
    ref = at_t.filter(pl.col("steps") == max(STEPS)).row(0, named=True)
    for row in at_t.iter_rows(named=True):
        if all(ref[f"{m}_low"] <= row[m] <= ref[f"{m}_high"] for m in ("beats_shuffles", "ned_mfe")):
            return int(row["steps"])
    return None


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--checkpoint", required=True)
    p.add_argument("--prefix", required=True)
    p.add_argument("--stage", choices=["sample", "evaluate", "table", "all"], default="all")
    args = p.parse_args()
    if args.stage in ("sample", "all"):
        stage_sample(args)
    if args.stage in ("evaluate", "all"):
        stage_evaluate(args)
    if args.stage in ("table", "all"):
        stage_table(args)


if __name__ == "__main__":
    main()
