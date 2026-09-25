"""Train a backbone's chosen configuration once on the replication split (frozen protocol P4).

The protocol repeats the whole pipeline on a second clan/family split
(split seed 1, data/processed_split1), with ONE training run per model and
the hyperparameters chosen on split 0: nothing is re-tuned on split 1. So
this script copies the recipe of the dropout sweep's winning run (read from
<prefix>_dropout_summary.json and that run's config.json, nothing retyped)
and changes only the data directory. The seed stays 0, like the sweep winner.
Best-during-run selection uses split 1's own validation set.

The run is named <chosen_run>_split<k>; an interrupted run resumes.

Usage:
    python scripts/replication_run.py --prefix tf_M
"""

import argparse
import json

from ribomamba.paths import REPO_ROOT
from ribomamba.sweeps import best_val_ema, run_to_completion, settings_from_config


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--prefix", required=True, help="e.g. tf_M; needs checkpoints/<prefix>_dropout_summary.json")
    p.add_argument("--split-seed", type=int, default=1, help="which replication split (data/processed_split<k>)")
    args = p.parse_args()
    summary = json.loads((REPO_ROOT / "checkpoints" / f"{args.prefix}_dropout_summary.json").read_text())
    base = summary["chosen_run"]
    cfg = json.loads((REPO_ROOT / "checkpoints" / base / "config.json").read_text())
    data_dir = f"data/processed_split{args.split_seed}"
    assert (REPO_ROOT / data_dir / "train.parquet").exists(), f"{data_dir} not built (scripts/prepare_data.py)"

    name = f"{base}_split{args.split_seed}"
    run_to_completion(name, cfg["max_steps"], *settings_from_config(cfg), "--data-dir", data_dir, "--seed", "0")
    print(f"{name}: best validation on split {args.split_seed}'s own val set {best_val_ema(name):.4f} bits/nt "
          f"(EMA); split 0's winner {base}: {best_val_ema(base):.4f}", flush=True)


if __name__ == "__main__":
    main()
