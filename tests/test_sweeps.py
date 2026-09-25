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
