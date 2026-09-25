"""Shared helpers for hyperparameter sweeps (D-011, D-012): run, resume, read results.

Divergence (D-011 amendment, 2026-09-25, made before any Mamba run): if a
run's training loss stops being a finite number, scripts/train.py leaves a
DIVERGED file in the run's folder and exits with DIVERGED_EXIT. Such a run did
not complete its schedule, so in a sweep it ranks last (its value is +inf),
whatever it reached before, and the sweep carries on instead of crashing.
"""

import csv
import subprocess
import sys

from ribomamba.paths import REPO_ROOT

DIVERGED_EXIT = 3              # train.py's exit code when the training loss became inf or nan
DIVERGED_MARKER = "DIVERGED"   # the file it leaves in checkpoints/<run>/, recording the step


def diverged(run_name: str) -> bool:
    return (REPO_ROOT / "checkpoints" / run_name / DIVERGED_MARKER).exists()


def eval_rows(run_name: str) -> list[dict]:
    """The validation rows of a run's log.csv (empty if the run hasn't evaluated yet)."""
    log = REPO_ROOT / "checkpoints" / run_name / "log.csv"
    if not log.exists():
        return []
    with open(log) as f:
        return [r for r in csv.DictReader(f) if r["val_bits_ema"]]


def final_val_ema(run_name: str) -> float:
    if diverged(run_name):
        return float("inf")
    return float(eval_rows(run_name)[-1]["val_bits_ema"])


def best_val_ema(run_name: str) -> float:
    if diverged(run_name):
        return float("inf")
    return min(float(r["val_bits_ema"]) for r in eval_rows(run_name))


def next_candidate(best, tried: list, grid: list, extend_down: bool = True):
    """Rule 2b (D-011, D-012): the next value to try, or None when the winner is interior.

    While the winner is the largest value tried, try the next grid value above it; while it is the
    smallest (and extend_down), the next below. Running off either end of the grid raises instead of
    stopping quietly: the written rule says "repeat until the winner is interior", and a silent stop
    at the grid's end would break it (amendment A2, 2026-09-26: the first grids ended at 1e-2 and 0.4).
    """
    i = grid.index(best)
    if extend_down and best == min(tried):                  # winner on the lower edge
        if i == 0:
            raise RuntimeError(f"winner {best} is the bottom of the grid {grid}: extend the grid, don't stop")
        return grid[i - 1]
    if best == max(tried):                                  # winner on the upper edge
        if i == len(grid) - 1:
            raise RuntimeError(f"winner {best} is the top of the grid {grid}: extend the grid, don't stop")
        return grid[i + 1]
    return None                                             # interior: the rule is satisfied


def pick_lowest(results: dict) -> object:
    """The setting with the lowest value; refuse if every candidate diverged (nothing to choose)."""
    if all(v == float("inf") for v in results.values()):
        raise RuntimeError(f"every candidate diverged: {results}")
    return min(results, key=results.get)


# The config keys that define a training recipe, i.e. everything train.py accepts except
# the run's name, seed, length and bookkeeping. Copying a run = passing these back verbatim.
RECIPE_KEYS = ["arch", "d_model", "n_layers", "n_heads", "d_state", "expand", "headdim", "dropout", "lr",
               "min_lr_ratio", "warmup_steps", "weight_decay", "beta2", "grad_clip", "ema_decay", "max_tokens",
               "eval_every"]


def settings_from_config(cfg: dict) -> list[str]:
    """train.py arguments that reproduce a run's recipe, read from its config.json (nothing retyped by hand).

    Keys absent from older configs (e.g. "arch" before Phase 4) are skipped, so
    train.py's defaults apply, which are the values those runs used.
    """
    args = []
    for key in RECIPE_KEYS:
        if key in cfg:
            args += ["--" + key.replace("_", "-"), str(cfg[key])]
    return args


def train(*args: str) -> None:
    subprocess.run([sys.executable, str(REPO_ROOT / "scripts" / "train.py"), *args], check=True)


def run_to_completion(name: str, steps: int, *new_run_args: str) -> None:
    """Skip a finished run; resume an interrupted one; otherwise start it.

    "Finished" means its log has an evaluation at the final step. A last.pt
    alone is not enough: an interrupted run has one too, and choosing a
    setting from a half-trained run would break the protocol.
    """
    if diverged(name):
        return
    rows = eval_rows(name)
    if rows and int(rows[-1]["step"]) >= steps:
        return
    last = REPO_ROOT / "checkpoints" / name / "last.pt"
    try:
        if last.exists():
            train("--resume", str(last))
        else:
            train("--run-name", name, "--max-steps", str(steps), *new_run_args)
    except subprocess.CalledProcessError as error:
        if error.returncode != DIVERGED_EXIT:          # a real crash: stop and show it
            raise
        print(f"{name}: diverged, ranks last ({(REPO_ROOT / 'checkpoints' / name / DIVERGED_MARKER).read_text().strip()})",
              flush=True)
