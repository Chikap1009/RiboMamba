"""Evaluate every final Phase 4 model with the frozen protocol (RESULTS.md P3, P5-P8; P9 step 4).

For each final model (architecture x training seed), on the test split:
  1. likelihood of every held-out sequence (scripts/eval_likelihood.py: 4 fixed noise draws for the
     diffusion models, exact for the AR model)                                           -> E1
  2. 1,000 samples with the test reference's lengths, T = 1.0, 256 steps, sampling seed 0
     (scripts/sample.py)
  3. the harness on those samples, next to the five reference sets (scripts/evaluate_samples.py)
                                                                                         -> E2, E3, guardrails
Then, secondary: the replication split (the three <chosen_run>_split1 models, steps 1-3 on split 1's
own test set, P4) and the temperature curve (T = 0.5 ... 1.2 for each architecture's seed-0 model, P5;
clarification C1 in RESULTS.md).

Which runs are final is read from checkpoints/<prefix>_seeds_summary.json (seed 0 = the dropout-sweep
winner, seeds 1-4 its replicates), never typed by hand.

"Exactly once per final model" (P1.1) is enforced by the outputs: a step whose output file exists is
skipped, never recomputed, so rerunning after an interruption continues where it stopped.

Memory: the harness peaks at ~10.6 GB of the 11.8 GB WSL sees, so this refuses to start while any
training process runs (handoff, session 04); --allow-during-training is for small plumbing checks only.

Usage:
    python scripts/phase4_evaluate.py --dry-run          # print the plan, run nothing
    python scripts/phase4_evaluate.py                    # the whole protocol, test split
    python scripts/phase4_evaluate.py --split val --n 50 --only samples harness --prefixes tf_M \
        --allow-during-training                           # plumbing check on validation
"""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

from ribomamba.paths import EVAL_DIR, REPO_ROOT

PREFIXES = ["tf_M", "bimamba_M", "ar_mamba_M"]
TEMPERATURES = [0.5, 0.6, 0.7, 0.8, 0.9, 1.1, 1.2]          # T = 1.0 is the primary setting, done in step 2
STEPS, SAMPLING_SEED, REFERENCE_SEED, DRAWS = 256, 0, 0, 4
REPLICATION_DIR = "data/processed_split1"


def arch_of(run: str) -> str:
    cfg = json.loads((REPO_ROOT / "checkpoints" / run / "config.json").read_text())
    return cfg.get("arch", "transformer")


def sample_tag(run: str, temperature: float) -> str:
    """T1.0_S256 for the diffusion models; T1.0_LR (left to right, length-constrained) for the AR model."""
    return f"T{temperature:.1f}_" + ("LR" if arch_of(run) == "ar_mamba" else f"S{STEPS}")


def final_runs(prefix: str) -> list[str]:
    """The five trained models of an architecture: the dropout winner (seed 0) and its seeds 1-4."""
    summary = json.loads((REPO_ROOT / "checkpoints" / f"{prefix}_seeds_summary.json").read_text())
    base = summary["base_run"]
    return [base if s == "0" else f"{base}_seed{s}" for s in sorted(summary["best_val_ema_by_seed"], key=int)]


def likelihood_output(run: str, where: str, split: str) -> Path:
    """eval_likelihood.py's output for this run, or a placeholder that doesn't exist yet.

    The file is named likelihood_<run>@<checkpoint step>_<where><split>.parquet; the step is only known from
    the checkpoint, so match it exactly with a pattern instead of loading 200 MB to read one number.
    """
    pattern = re.compile(rf"likelihood_{re.escape(run)}@\d+_{re.escape(where + split)}\.parquet")
    found = [f for f in EVAL_DIR.glob(f"likelihood_{run}@*.parquet") if pattern.fullmatch(f.name)]
    return found[0] if found else EVAL_DIR / f"likelihood_{run}@(pending)_{where}{split}.parquet"


def replication_run(prefix: str) -> str:
    summary = json.loads((REPO_ROOT / "checkpoints" / f"{prefix}_dropout_summary.json").read_text())
    return f"{summary['chosen_run']}_split1"


def plan(args) -> list[tuple[str, Path, list[str]]]:
    """(description, output that proves the step is done, command) for every step, in running order."""
    split, n = args.split, args.n
    scope = f"{split}" if n == 1000 else f"{split}_n{n}"                      # output folder / name prefix
    steps = []

    def add_model(run: str, data_dir: str, where: str, temperatures: list[float], do_likelihood: bool):
        checkpoint = str(REPO_ROOT / "checkpoints" / run / "best.pt")
        extra = [] if data_dir == "data/processed" else ["--data-dir", data_dir]
        if do_likelihood and "likelihood" in args.only:
            steps.append((f"likelihood {run} on {where}{split}", likelihood_output(run, where, split),
                          ["scripts/eval_likelihood.py", "--checkpoint", checkpoint, "--split", split,
                           "--draws", str(args.draws), *extra]))
        for temperature in temperatures:
            name = f"{where}{scope}_{run}_{sample_tag(run, temperature)}"
            fasta = REPO_ROOT / "samples" / f"{where}{scope}" / f"{run}_{sample_tag(run, temperature)}.fasta"
            if "samples" in args.only:
                steps.append((f"sample {name}", fasta,
                              ["scripts/sample.py", "--checkpoint", checkpoint, "--lengths-from", split,
                               "--lengths-n", str(n), "--lengths-seed", str(REFERENCE_SEED), "--steps", str(STEPS),
                               "--temperature", str(temperature), "--seed", str(SAMPLING_SEED), "--out", str(fasta),
                               *extra]))
            if "harness" in args.only:
                steps.append((f"harness {name}", EVAL_DIR / f"{name}.json",
                              ["scripts/evaluate_samples.py", "--samples", str(fasta), "--name", name, "--split",
                               split, "--n", str(n), "--seed", str(REFERENCE_SEED), *extra]))

    for prefix in args.prefixes:                                               # primary: every seed, T = 1.0
        for run in final_runs(prefix):
            add_model(run, "data/processed", "", [1.0], do_likelihood=True)
    if "replication" in args.only:                                             # secondary: split 1, T = 1.0
        for prefix in args.prefixes:
            add_model(replication_run(prefix), REPLICATION_DIR, "processed_split1_", [1.0], do_likelihood=True)
    if "temperature" in args.only:                                             # secondary: seed-0 model, T curve
        for prefix in args.prefixes:
            add_model(final_runs(prefix)[0], "data/processed", "", TEMPERATURES, do_likelihood=False)
    return steps


def training_running() -> bool:
    out = subprocess.run(["ps", "-eo", "args"], capture_output=True, text=True).stdout
    return any("scripts/train.py" in line for line in out.splitlines())


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--split", default="test", choices=["val", "test"])
    p.add_argument("--n", type=int, default=1000, help="reference size (the protocol: 1,000)")
    p.add_argument("--draws", type=int, default=DRAWS, help="likelihood noise draws (the protocol: 4)")
    p.add_argument("--prefixes", nargs="+", default=PREFIXES)
    p.add_argument("--only", nargs="+", default=["likelihood", "samples", "harness", "replication", "temperature"],
                   choices=["likelihood", "samples", "harness", "replication", "temperature"])
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--allow-during-training", action="store_true")
    args = p.parse_args()
    if args.split == "test" and (args.n != 1000 or args.draws != DRAWS):
        sys.exit("the test split is evaluated only with the protocol's settings (n 1000, 4 draws)")

    steps = plan(args)
    todo = [s for s in steps if not s[1].exists()]
    print(f"{len(steps)} steps, {len(steps) - len(todo)} already done, {len(todo)} to run", flush=True)
    for description, output, command in steps:
        print(f"  {'done' if output.exists() else 'todo'}  {description}")
    if args.dry_run or not todo:
        return
    if training_running() and not args.allow_during_training:
        sys.exit("a training process is running: evaluation would compete for memory (wait for the queue)")
    for description, output, command in todo:
        if output.exists():                          # a likelihood step's output name is known only afterwards
            continue
        print(f"=== {description}", flush=True)
        subprocess.run([sys.executable, str(REPO_ROOT / command[0]), *command[1:]], check=True, cwd=REPO_ROOT)
    print("all steps done", flush=True)


if __name__ == "__main__":
    main()
