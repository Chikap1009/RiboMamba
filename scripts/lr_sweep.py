"""Learning-rate sweep with a selection rule fixed in advance, then the full run (D-011).

Protocol (identical for every backbone, so no architecture gets more tuning):
  1. For each candidate peak learning rate, train SWEEP_STEPS steps with a
     complete schedule (warmup, cosine decay), everything else identical.
  2. RULE: pick the learning rate with the lowest validation bits/nt of the
     EMA weights at the end of its run. Written here before any sweep result
     was seen.
  3. Optionally train the winner for the full budget.

Usage:
    python scripts/lr_sweep.py --prefix tf_M                  # sweep only
    python scripts/lr_sweep.py --prefix tf_M --then-full      # sweep, then the full run
"""

import argparse
import csv
import json
import subprocess
import sys

from ribomamba.paths import REPO_ROOT

CANDIDATE_LRS = [3e-4, 1e-3, 3e-3]
SWEEP_STEPS, SWEEP_WARMUP = 8000, 1000
FULL_STEPS, FULL_WARMUP, FULL_EVAL_EVERY = 200_000, 2000, 5000


def final_val_ema(run_name: str) -> float:
    with open(REPO_ROOT / "checkpoints" / run_name / "log.csv") as f:
        rows = [r for r in csv.DictReader(f) if r["val_bits_ema"]]
    return float(rows[-1]["val_bits_ema"])


def train(*args: str) -> None:
    subprocess.run([sys.executable, str(REPO_ROOT / "scripts" / "train.py"), *args], check=True)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--prefix", required=True, help="e.g. tf_M; runs are named <prefix>_sweep_lr<lr>")
    p.add_argument("--then-full", action="store_true")
    p.add_argument("extra", nargs="*", help="extra arguments passed to train.py (model size etc.)")
    args = p.parse_args()

    results = {}
    for lr in CANDIDATE_LRS:
        name = f"{args.prefix}_sweep_lr{lr:g}"
        if not (REPO_ROOT / "checkpoints" / name / "last.pt").exists():
            train("--run-name", name, "--lr", str(lr), "--max-steps", str(SWEEP_STEPS),
                  "--warmup-steps", str(SWEEP_WARMUP), "--eval-every", "2000", *args.extra)
        results[lr] = final_val_ema(name)
        print(f"lr {lr:g}: final validation {results[lr]:.4f} bits/nt (EMA)", flush=True)

    best = min(results, key=results.get)
    summary = {"rule": "lowest final validation bits/nt (EMA) after the sweep run",
               "sweep_steps": SWEEP_STEPS, "results": {f"{k:g}": v for k, v in results.items()},
               "chosen_lr": best}
    (REPO_ROOT / "checkpoints" / f"{args.prefix}_sweep_summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2), flush=True)

    if args.then_full:
        train("--run-name", f"{args.prefix}_full", "--lr", str(best), "--max-steps", str(FULL_STEPS),
              "--warmup-steps", str(FULL_WARMUP), "--eval-every", str(FULL_EVAL_EVERY), *args.extra)


if __name__ == "__main__":
    main()
