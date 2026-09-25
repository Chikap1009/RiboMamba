"""Shared helpers for hyperparameter sweeps (D-011, D-012): run, resume, read results."""

import csv
import subprocess
import sys

from ribomamba.paths import REPO_ROOT


def eval_rows(run_name: str) -> list[dict]:
    """The validation rows of a run's log.csv (empty if the run hasn't evaluated yet)."""
    log = REPO_ROOT / "checkpoints" / run_name / "log.csv"
    if not log.exists():
        return []
    with open(log) as f:
        return [r for r in csv.DictReader(f) if r["val_bits_ema"]]


def final_val_ema(run_name: str) -> float:
    return float(eval_rows(run_name)[-1]["val_bits_ema"])


def best_val_ema(run_name: str) -> float:
    return min(float(r["val_bits_ema"]) for r in eval_rows(run_name))


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
    rows = eval_rows(name)
    if rows and int(rows[-1]["step"]) >= steps:
        return
    last = REPO_ROOT / "checkpoints" / name / "last.pt"
    if last.exists():
        train("--resume", str(last))
    else:
        train("--run-name", name, "--max-steps", str(steps), *new_run_args)
