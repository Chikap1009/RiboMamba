"""Train extra seeds of a backbone's chosen configuration (frozen protocol P4).

An architecture claim needs several trained models per architecture: with
the exact seed-level test, 3 seeds per model can never give p < 0.05, 5 can
(D-014). The winning run of the dropout sweep is seed 0; this script trains
seeds 1..4 with exactly its settings, read from <prefix>_dropout_summary.json
and that run's config.json (nothing retyped by hand). The seed changes
everything random in training: initial weights, batch order, t values and
masks. Validation noise stays fixed (seed 1234), so every seed is measured
on the same yardstick.

Runs are named <chosen_run>_seed<k>; interrupted runs resume (run_to_completion).

Usage:
    python scripts/seed_replicates.py --prefix tf_M --seeds 1 2 3 4
"""

import argparse
import json

from ribomamba.paths import REPO_ROOT
from ribomamba.sweeps import best_val_ema, run_to_completion, settings_from_config


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--prefix", required=True, help="e.g. tf_M; needs checkpoints/<prefix>_dropout_summary.json")
    p.add_argument("--seeds", type=int, nargs="+", default=[1, 2, 3, 4])
    args = p.parse_args()
    summary = json.loads((REPO_ROOT / "checkpoints" / f"{args.prefix}_dropout_summary.json").read_text())
    base = summary["chosen_run"]
    cfg = json.loads((REPO_ROOT / "checkpoints" / base / "config.json").read_text())
    settings = settings_from_config(cfg)     # the whole recipe, architecture included (Phase 4 backbones too)
    results = {0: best_val_ema(base)}
    for seed in args.seeds:
        name = f"{base}_seed{seed}"
        run_to_completion(name, cfg["max_steps"], *settings, "--seed", str(seed))
        results[seed] = best_val_ema(name)
        print(f"seed {seed}: best validation {results[seed]:.4f} bits/nt (EMA)", flush=True)
    out = {"base_run": base, "settings": settings, "max_steps": cfg["max_steps"],
           "best_val_ema_by_seed": {str(k): v for k, v in sorted(results.items())}}
    (REPO_ROOT / "checkpoints" / f"{args.prefix}_seeds_summary.json").write_text(json.dumps(out, indent=2))
    print(json.dumps(out, indent=2), flush=True)


if __name__ == "__main__":
    main()
