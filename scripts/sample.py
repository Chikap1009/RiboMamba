"""Generate RNA sequences from a trained masked-diffusion checkpoint (Phase 2).

Lengths are drawn from the training split's own length distribution (or
fixed with --length). Uses the EMA weights by default, as evaluation does.

Usage:
    python scripts/sample.py --checkpoint checkpoints/tf_M_full/best.pt --n 1000 --steps 256 \
        --out samples/tf_M_full.fasta

Output: FASTA, one record per sequence: >sample_<i> length=<L> checkpoint=<run>@<step>
"""

import argparse
from pathlib import Path

import numpy as np
import polars as pl
import torch

from ribomamba.data.tokenizer import decode
from ribomamba.diffusion.masked import sample, sample_lengths
from ribomamba.models.transformer import TransformerConfig, TransformerDenoiser
from ribomamba.paths import PROCESSED_DIR


def load_model(checkpoint: Path, weights: str, device) -> tuple[torch.nn.Module, dict]:
    state = torch.load(checkpoint, map_location="cpu", weights_only=False)
    cfg = state["config"]
    model = TransformerDenoiser(TransformerConfig(d_model=cfg["d_model"], n_layers=cfg["n_layers"],
                                                  n_heads=cfg["n_heads"]))
    model.load_state_dict(state["ema" if weights == "ema" else "model"])
    return model.to(device).eval(), state


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--checkpoint", required=True, type=Path)
    p.add_argument("--n", type=int, default=100, help="number of sequences")
    p.add_argument("--steps", type=int, default=256, help="reverse-process steps (N)")
    p.add_argument("--length", type=int, help="fixed length; default: drawn from the training lengths")
    p.add_argument("--weights", choices=["ema", "live"], default="ema")
    p.add_argument("--temperature", type=float, default=1.0)
    p.add_argument("--batch-size", type=int, default=128)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()

    device = torch.device("cuda")
    model, state = load_model(args.checkpoint, args.weights, device)
    g_cpu = torch.Generator().manual_seed(args.seed)                  # lengths
    g = torch.Generator(device=device).manual_seed(args.seed)         # masks and letters
    if args.length:
        lengths = torch.full((args.n,), args.length)
    else:
        train_lengths = torch.from_numpy(
            pl.read_parquet(PROCESSED_DIR / "train.parquet", columns=["length"])["length"].to_numpy().astype(np.int64))
        lengths = sample_lengths(args.n, train_lengths, g_cpu)

    tag = f"{state['config']['run_name']}@{state['step']}"
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w") as f:
        for start in range(0, args.n, args.batch_size):
            batch_lengths = lengths[start:start + args.batch_size]
            ids = sample(model, batch_lengths, args.steps, generator=g, temperature=args.temperature)
            for i, row in enumerate(ids.cpu()):
                seq = decode(row)                                     # drops <bos>, <eos>, <pad>
                f.write(f">sample_{start + i} length={len(seq)} checkpoint={tag}\n{seq}\n")
    print(f"wrote {args.n} sequences to {args.out} ({tag}, {args.steps} steps, {args.weights} weights)")


if __name__ == "__main__":
    main()
