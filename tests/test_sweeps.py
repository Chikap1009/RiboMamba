import math
import subprocess

import pytest

import ribomamba.sweeps as sweeps
from ribomamba.sweeps import settings_from_config

# tf_M_do0's config.json (the Phase 2 baseline), minus bookkeeping keys that must not be copied
TF_M_DO0 = {"run_name": "tf_M_do0", "d_model": 384, "n_layers": 8, "n_heads": 6, "dropout": 0.0, "lr": 0.0003,
            "min_lr_ratio": 0.1, "warmup_steps": 1000, "max_steps": 30000, "weight_decay": 0.1, "beta2": 0.98,
            "grad_clip": 1.0, "ema_decay": 0.9999, "max_tokens": 16384, "num_workers": 2, "log_every": 100,
            "eval_every": 2500, "seed": 0, "git_commit": "d0fff97f11e5d6ff23df5b0dd45f922f21970663",
            "parameters": 14174976}


def pairs(args: list[str]) -> dict[str, str]:
    return dict(zip(args[0::2], args[1::2]))


def test_recipe_copy_matches_the_list_the_transformer_seeds_were_trained_with():
    # The explicit list scripts/seed_replicates.py used for tf_M seeds 1-4 (commit e65151c).
    historic = ["--lr", "0.0003", "--dropout", "0.0", "--warmup-steps", "1000", "--eval-every", "2500",
                "--d-model", "384", "--n-layers", "8", "--n-heads", "6", "--min-lr-ratio", "0.1",
                "--weight-decay", "0.1", "--beta2", "0.98", "--grad-clip", "1.0", "--ema-decay", "0.9999",
                "--max-tokens", "16384"]
    assert pairs(settings_from_config(TF_M_DO0)) == pairs(historic)


def test_recipe_copy_never_carries_identity_or_bookkeeping():
    copied = pairs(settings_from_config(TF_M_DO0))
    for flag in ("--run-name", "--seed", "--max-steps", "--data-dir", "--git-commit", "--parameters"):
        assert flag not in copied


def fake_run(root, name: str, val_values: list[float], diverged_at: int | None = None) -> None:
    """A run folder with a log.csv holding validation rows (and a DIVERGED marker if asked)."""
    folder = root / "checkpoints" / name
    folder.mkdir(parents=True)
    rows = ["step,epoch,lr,train_bits,grad_norm,val_bits_live,val_bits_ema,knt_per_s,peak_GB,hours"]
    rows += [f"{2000 * (i + 1)},0,1e-3,,,{v},{v},,,0.1" for i, v in enumerate(val_values)]
    (folder / "log.csv").write_text("\n".join(rows) + "\n")
    if diverged_at is not None:
        (folder / sweeps.DIVERGED_MARKER).write_text(f"step {diverged_at}: training loss nan\n")


def test_a_diverged_run_ranks_last_even_if_it_was_good_before(tmp_path, monkeypatch):
    monkeypatch.setattr(sweeps, "REPO_ROOT", tmp_path)
    fake_run(tmp_path, "steady", [1.95, 1.93, 1.92])
    fake_run(tmp_path, "blew_up", [1.94, 1.90], diverged_at=5000)       # better so far, then nan
    assert sweeps.best_val_ema("steady") == 1.92 and sweeps.final_val_ema("steady") == 1.92
    assert math.isinf(sweeps.best_val_ema("blew_up")) and math.isinf(sweeps.final_val_ema("blew_up"))
    results = {1e-3: sweeps.final_val_ema("steady"), 3e-3: sweeps.final_val_ema("blew_up")}
    assert sweeps.pick_lowest(results) == 1e-3
    with pytest.raises(RuntimeError, match="every candidate diverged"):
        sweeps.pick_lowest({1e-3: math.inf, 3e-3: math.inf})


def test_divergence_does_not_stop_a_sweep_but_a_crash_does(tmp_path, monkeypatch):
    monkeypatch.setattr(sweeps, "REPO_ROOT", tmp_path)

    def train_that_fails(code):
        def train(*args):
            name = args[args.index("--run-name") + 1]
            folder = tmp_path / "checkpoints" / name
            folder.mkdir(parents=True, exist_ok=True)
            if code == sweeps.DIVERGED_EXIT:
                (folder / sweeps.DIVERGED_MARKER).write_text("step 7: training loss nan\n")
            raise subprocess.CalledProcessError(code, "train.py")
        return train

    monkeypatch.setattr(sweeps, "train", train_that_fails(sweeps.DIVERGED_EXIT))
    sweeps.run_to_completion("nan_run", 8000, "--lr", "1e-2")                   # returns quietly
    assert sweeps.diverged("nan_run")
    sweeps.run_to_completion("nan_run", 8000, "--lr", "1e-2")                   # a rerun skips it
    monkeypatch.setattr(sweeps, "train", train_that_fails(1))
    with pytest.raises(subprocess.CalledProcessError):
        sweeps.run_to_completion("crash_run", 8000, "--lr", "1e-3")
