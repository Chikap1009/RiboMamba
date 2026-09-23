"""Learning-rate sweep with a selection rule fixed in advance, then the full run (D-011).

Protocol (identical for every backbone, so no architecture gets more tuning):
  1. For each candidate peak learning rate, train SWEEP_STEPS steps with a
     complete schedule (warmup, cosine decay), everything else identical.
  2. RULE: pick the learning rate with the lowest validation bits/nt of the
     EMA weights at the end of its run. Written here before any sweep result
     was seen.
  2b. BOUNDARY RULE (amendment, 2026-09-24 01:50, D-011): if the winner is
     the smallest or largest value tried, the optimum may lie outside the
     grid, so add the next value on the same half-decade grid in that
     direction and apply rule 2 again; repeat until the winner is interior.
     Added after the Transformer sweep (winner 3e-4 = the grid's lower
     edge), before any other backbone was swept; it applies to all of them.
  3. Optionally train the winner for the full budget. SUPERSEDED 2026-09-24
     (D-012): the 200k-step run overfit after ~10k steps; training length and
     dropout are now chosen by scripts/dropout_sweep.py.

Usage:
    python scripts/lr_sweep.py --prefix tf_M                  # sweep only
    python scripts/lr_sweep.py --prefix tf_M --then-full      # sweep, then the full run
"""

import argparse
import json

from ribomamba.paths import REPO_ROOT
from ribomamba.sweeps import final_val_ema, run_to_completion

GRID = [3e-5, 1e-4, 3e-4, 1e-3, 3e-3, 1e-2]     # half-decade steps (x ~3.16 between neighbours)
CANDIDATE_LRS = [3e-4, 1e-3, 3e-3]              # where every sweep starts
SWEEP_STEPS, SWEEP_WARMUP = 8000, 1000
FULL_STEPS, FULL_WARMUP, FULL_EVAL_EVERY = 200_000, 2000, 5000


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--prefix", required=True, help="e.g. tf_M; runs are named <prefix>_sweep_lr<lr>")
    p.add_argument("--then-full", action="store_true")
    p.add_argument("extra", nargs="*", help="extra arguments passed to train.py (model size etc.)")
    args = p.parse_args()

    results, tried = {}, list(CANDIDATE_LRS)
    while True:
        for lr in tried:
            if lr in results:
                continue
            name = f"{args.prefix}_sweep_lr{lr:g}"
            run_to_completion(name, SWEEP_STEPS, "--lr", str(lr), "--warmup-steps", str(SWEEP_WARMUP),
                              "--eval-every", "2000", *args.extra)
            results[lr] = final_val_ema(name)
            print(f"lr {lr:g}: final validation {results[lr]:.4f} bits/nt (EMA)", flush=True)
        best = min(results, key=results.get)
        i = GRID.index(best)
        if best == min(tried) and i > 0:                  # rule 2b: winner on the lower edge
            tried.insert(0, GRID[i - 1])
        elif best == max(tried) and i < len(GRID) - 1:    # rule 2b: winner on the upper edge
            tried.append(GRID[i + 1])
        else:
            break

    summary = {"rule": "lowest final validation bits/nt (EMA) after the sweep run; "
                       "extend the grid while the winner is on its edge",
               "sweep_steps": SWEEP_STEPS,
               "results": {f"{k:g}": results[k] for k in sorted(results)},
               "chosen_lr": best}
    (REPO_ROOT / "checkpoints" / f"{args.prefix}_sweep_summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2), flush=True)

    if args.then_full:
        run_to_completion(f"{args.prefix}_full", FULL_STEPS, "--lr", str(best), "--warmup-steps",
                          str(FULL_WARMUP), "--eval-every", str(FULL_EVAL_EVERY), *args.extra)


if __name__ == "__main__":
    main()
