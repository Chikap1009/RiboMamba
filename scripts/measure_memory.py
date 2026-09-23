"""Measure GPU memory and training speed for candidate denoiser sizes (Phase 2, D-011).

For each model size and batch shape, runs a few real training steps (bf16
autocast, AdamW, gradient clipping, the diffusion loss) on random framed
sequences, and records peak GPU memory and nucleotides processed per second.
The worst case is every sequence at the maximum length (256 nt + 2 markers),
because a length-bucketed batch of long sequences can really look like that.

Usage:  python scripts/measure_memory.py
"""

import time

import torch

from ribomamba.data.tokenizer import BOS_ID, EOS_ID
from ribomamba.diffusion.masked import diffusion_loss
from ribomamba.models.transformer import TransformerConfig, TransformerDenoiser, count_parameters

SIZES = {                     # name: (d_model, n_layers, n_heads)
    "S": (256, 6, 4),
    "M": (384, 8, 6),
    "L": (512, 8, 8),
    "XL": (512, 12, 8),
}
TOKEN_BUDGETS = [8192, 16384, 32768]     # nucleotides per batch
LENGTHS = [256, 64]                      # nucleotides per sequence (+2 markers)


def framed_random(batch: int, length: int, device) -> tuple[torch.Tensor, torch.Tensor]:
    body = torch.randint(4, 8, (batch, length), device=device)
    ids = torch.cat([torch.full((batch, 1), BOS_ID, device=device), body,
                     torch.full((batch, 1), EOS_ID, device=device)], dim=1)       # (B, length + 2)
    return ids, torch.ones_like(ids, dtype=torch.bool)


def measure(cfg: TransformerConfig, batch: int, length: int, steps: int = 10) -> dict:
    device = torch.device("cuda")
    torch.cuda.empty_cache()
    torch.cuda.reset_peak_memory_stats()
    model = TransformerDenoiser(cfg).to(device)
    optimiser = torch.optim.AdamW(model.parameters(), lr=1e-4)
    ids, attention = framed_random(batch, length, device)
    try:
        for i in range(steps + 3):                           # 3 warm-up steps are not timed
            if i == 3:
                torch.cuda.synchronize()
                start = time.perf_counter()
            with torch.autocast("cuda", dtype=torch.bfloat16):
                loss, _ = diffusion_loss(model, ids, attention)
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
    free, total = torch.cuda.mem_get_info()
    print(f"GPU: {torch.cuda.get_device_name(0)}  total {total / 1e9:.2f} GB, free now {free / 1e9:.2f} GB")
    print(f"{'size':4} {'params':>7} {'len':>4} {'batch':>5} {'tokens':>6} {'peak GB':>8} {'ms/step':>8} {'k nt/s':>7}")
    for name, (d, n, h) in SIZES.items():
        cfg = TransformerConfig(d_model=d, n_layers=n, n_heads=h)
        params = count_parameters(TransformerDenoiser(cfg)) / 1e6
        for length in LENGTHS:
            for budget in TOKEN_BUDGETS:
                batch = budget // length
                r = measure(cfg, batch, length)
                ms = f"{r['ms_per_step']:8.1f}" if r["ms_per_step"] else "     OOM"
                kn = f"{r['knt_per_s']:7.0f}" if r["knt_per_s"] else "      -"
                print(f"{name:4} {params:6.1f}M {length:4} {batch:5} {budget:6} {r['peak_GB']:8.2f} {ms} {kn}", flush=True)


if __name__ == "__main__":
    main()
