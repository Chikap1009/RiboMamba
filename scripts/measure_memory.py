"""Measure GPU memory and training speed for candidate models (Phase 2, D-011; Phase 4, D-015).

For each model and batch shape, runs a few real training steps (bf16 autocast,
AdamW, gradient clipping, the model's own loss) on random framed sequences, and
records peak GPU memory and nucleotides processed per second. The worst case is
every sequence at the maximum length (256 nt + 2 markers), because a
length-bucketed batch of long sequences can really look like that.

Run it on an otherwise idle GPU: another job's memory and compute would distort
both numbers.

Usage:
    python scripts/measure_memory.py                  # the Phase 2 Transformer sizes (the D-011 table)
    python scripts/measure_memory.py --group phase4   # the three Phase 4 models + the width-matched alternatives
"""

import argparse
import time

import torch

from ribomamba.data.tokenizer import BOS_ID, EOS_ID
from ribomamba.models.build import build_model, objective
from ribomamba.models.transformer import count_parameters

MAMBA = {"d_state": 128, "expand": 2, "headdim": 64}          # the library's Mamba-2 defaults
MODELS = {                    # name: the model part of a run's config.json
    "S": {"arch": "transformer", "d_model": 256, "n_layers": 6, "n_heads": 4},
    "M": {"arch": "transformer", "d_model": 384, "n_layers": 8, "n_heads": 6},
    "L": {"arch": "transformer", "d_model": 512, "n_layers": 8, "n_heads": 8},
    "XL": {"arch": "transformer", "d_model": 512, "n_layers": 12, "n_heads": 8},
    # D-015 option A (depth matching): width 384 as the Transformer, 14 layers
    "bimamba_M": {"arch": "bimamba", "d_model": 384, "n_layers": 14, **MAMBA},
    "ar_mamba_M": {"arch": "ar_mamba", "d_model": 384, "n_layers": 14, **MAMBA},
    # D-015 option B (width matching): 8 layers as the Transformer; needs non-default head/state sizes
    "bimamba_W": {"arch": "bimamba", "d_model": 512, "n_layers": 8, "d_state": 128, "expand": 2, "headdim": 32},
    "ar_mamba_W": {"arch": "ar_mamba", "d_model": 528, "n_layers": 8, "d_state": 64, "expand": 2, "headdim": 32},
}
GROUPS = {  # name: (models, token budgets)
    "phase2": (["S", "M", "L", "XL"], [8192, 16384, 32768]),
    "phase4": (["M", "bimamba_M", "ar_mamba_M", "bimamba_W", "ar_mamba_W"], [16384, 32768]),
}
LENGTHS = [256, 64]                      # nucleotides per sequence (+2 markers)


def framed_random(batch: int, length: int, device) -> tuple[torch.Tensor, torch.Tensor]:
    body = torch.randint(4, 8, (batch, length), device=device)
    ids = torch.cat([torch.full((batch, 1), BOS_ID, device=device), body,
                     torch.full((batch, 1), EOS_ID, device=device)], dim=1)       # (B, length + 2)
    return ids, torch.ones_like(ids, dtype=torch.bool)


def measure(cfg: dict, batch: int, length: int, steps: int = 10) -> dict:
    device = torch.device("cuda")
    torch.cuda.empty_cache()
    torch.cuda.reset_peak_memory_stats()
    model = build_model(cfg).to(device)
    loss_fn = objective(cfg["arch"])
    optimiser = torch.optim.AdamW(model.parameters(), lr=1e-4)
    ids, attention = framed_random(batch, length, device)
    try:
        for i in range(steps + 3):                           # 3 warm-up steps are not timed (and compile kernels)
            if i == 3:
                torch.cuda.synchronize()
                start = time.perf_counter()
            with torch.autocast("cuda", dtype=torch.bfloat16):
                loss, _ = loss_fn(model, ids, attention)
            optimiser.zero_grad(set_to_none=True)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimiser.step()
        torch.cuda.synchronize()
        seconds = (time.perf_counter() - start) / steps
        return {"peak_GB": torch.cuda.max_memory_allocated() / 1e9,
                "ms_per_step": 1000 * seconds, "knt_per_s": batch * length / seconds / 1000}
    except torch.OutOfMemoryError:
        return {"peak_GB": float("inf"), "ms_per_step": None, "knt_per_s": None}
    finally:
        del model, optimiser
        torch.cuda.empty_cache()


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--group", choices=GROUPS, default="phase2")
    args = p.parse_args()
    names, budgets = GROUPS[args.group]
    free, total = torch.cuda.mem_get_info()
    print(f"GPU: {torch.cuda.get_device_name(0)}  total {total / 1e9:.2f} GB, free now {free / 1e9:.2f} GB")
    print(f"{'model':11} {'params':>7} {'len':>4} {'batch':>5} {'tokens':>6} {'peak GB':>8} {'ms/step':>8} {'k nt/s':>7}")
    for name in names:
        cfg = MODELS[name]
        params = count_parameters(build_model(cfg)) / 1e6
        for length in LENGTHS:
            for budget in budgets:
                batch = budget // length
                r = measure(cfg, batch, length)
                ms = f"{r['ms_per_step']:8.1f}" if r["ms_per_step"] else "     OOM"
                kn = f"{r['knt_per_s']:7.0f}" if r["knt_per_s"] else "      -"
                print(f"{name:11} {params:6.2f}M {length:4} {batch:5} {budget:6} {r['peak_GB']:8.2f} {ms} {kn}",
                      flush=True)


if __name__ == "__main__":
    main()
