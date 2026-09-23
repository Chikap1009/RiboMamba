"""Dropout sweep with a selection rule fixed in advance (D-012).

Why: the 200,000-step run at the chosen learning rate overfit. Validation
bits/nt (unseen families) was best at step 10,000 (1.902) and worsened
steadily to 1.935 at step 45,000 while training fell to 1.41. Dropout makes
memorising harder; a full cosine schedule over a shorter run lets the
learning rate anneal before overfitting sets in.

Protocol (identical for every backbone):
  1. Learning rate = the one chosen by scripts/lr_sweep.py for this prefix.
  2. For each dropout rate, train STEPS steps with a complete schedule
     (warmup, cosine decay to 10 %), evaluating every EVAL_EVERY steps; the
     best checkpoint by EMA validation is kept (early stopping).
  3. RULE: pick the dropout with the lowest BEST EMA validation bits/nt
     reached during its run. If the winner is the largest rate tried, add
     the next grid value and re-apply (0 has no lower neighbour).
     Written here before any dropout run existed.

Usage:
    python scripts/dropout_sweep.py --prefix tf_M
"""

import argparse
import json

from ribomamba.paths import REPO_ROOT
from ribomamba.sweeps import best_val_ema, run_to_completion

GRID = [0.0, 0.1, 0.2, 0.3, 0.4]
CANDIDATES = [0.0, 0.1, 0.2]
STEPS, WARMUP, EVAL_EVERY = 30_000, 1000, 2500


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--prefix", required=True, help="e.g. tf_M; must have <prefix>_sweep_summary.json")
    p.add_argument("extra", nargs="*", help="extra arguments passed to train.py (model size etc.)")
    args = p.parse_args()
    lr = json.loads((REPO_ROOT / "checkpoints" / f"{args.prefix}_sweep_summary.json").read_text())["chosen_lr"]

    results, tried = {}, list(CANDIDATES)
    while True:
        for rate in tried:
            if rate in results:
                continue
            name = f"{args.prefix}_do{rate:g}"
            run_to_completion(name, STEPS, "--lr", str(lr), "--dropout", str(rate), "--warmup-steps",
                              str(WARMUP), "--eval-every", str(EVAL_EVERY), *args.extra)
            results[rate] = best_val_ema(name)
            print(f"dropout {rate:g}: best validation {results[rate]:.4f} bits/nt (EMA)", flush=True)
        best = min(results, key=results.get)
        i = GRID.index(best)
        if best == max(tried) and i < len(GRID) - 1:       # winner on the upper edge: extend
            tried.append(GRID[i + 1])
        else:
            break

    summary = {"rule": "lowest best-during-run validation bits/nt (EMA); extend while the winner is the largest rate",
               "lr": lr, "steps": STEPS, "results": {f"{k:g}": results[k] for k in sorted(results)},
               "chosen_dropout": best, "chosen_run": f"{args.prefix}_do{best:g}"}
    (REPO_ROOT / "checkpoints" / f"{args.prefix}_dropout_summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2), flush=True)


if __name__ == "__main__":
    main()
