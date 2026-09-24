"""Generate RNA sequences from a trained masked-diffusion checkpoint (Phase 2).

Lengths are drawn from the training split's own length distribution, fixed
with --length, or (for evaluation, Phase 3) copied one-to-one from the
harness's real reference set with --lengths-from, so sample i has exactly the
length of reference sequence i. Uses the EMA weights by default, as
evaluation does.

Usage:
    python scripts/sample.py --checkpoint checkpoints/tf_M_full/best.pt --n 1000 --steps 256 \
        --out samples/tf_M_full.fasta
    python scripts/sample.py --checkpoint checkpoints/tf_M_do0/best.pt --lengths-from val \
        --steps 256 --temperature 1.0 --out samples/eval/tf_M_do0_T1.0_S256.fasta

Output: FASTA, one record per sequence, in the order the lengths were drawn:
    >sample_<i> length=<L> checkpoint=<run>@<step>
"""

import argparse
from pathlib import Path

import numpy as np
import polars as pl
import torch

from ribomamba.data.tokenizer import decode
from ribomamba.diffusion.masked import sample, sample_lengths
from ribomamba.eval.reference import reference_sample
from ribomamba.models.checkpoint import load_model
from ribomamba.paths import PROCESSED_DIR


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--checkpoint", required=True, type=Path)
    p.add_argument("--n", type=int, default=100, help="number of sequences")
    p.add_argument("--steps", type=int, default=256, help="reverse-process steps (N)")
    p.add_argument("--length", type=int, help="fixed length; default: drawn from the training lengths")
    p.add_argument("--lengths-from", choices=["val", "test"],
                   help="copy the lengths of the harness's real reference set (ribomamba/eval/reference.py)")
    p.add_argument("--lengths-n", type=int, default=1000, help="size of that reference set")
    p.add_argument("--lengths-seed", type=int, default=0, help="seed of that reference set")
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
    if args.lengths_from:
        lengths = torch.tensor(reference_sample(args.lengths_from, args.lengths_n, args.lengths_seed)["length"]
                               .to_list())
    elif args.length:
        lengths = torch.full((args.n,), args.length)
    else:
        train_lengths = torch.from_numpy(
            pl.read_parquet(PROCESSED_DIR / "train.parquet", columns=["length"])["length"].to_numpy().astype(np.int64))
        lengths = sample_lengths(args.n, train_lengths, g_cpu)
    n = len(lengths)
    # Generate in order of length so each batch holds similar lengths (little padding);
    # which length each sample gets was already decided above. Results are written back
    # in the original order, so sample i keeps the i-th length (pairing with the reference).
    lengths, order = lengths.sort(descending=True)

    tag = f"{state['config']['run_name']}@{state['step']}"
    generated = [""] * n
    for start in range(0, n, args.batch_size):
        batch_lengths = lengths[start:start + args.batch_size]
        ids = sample(model, batch_lengths, args.steps, generator=g, temperature=args.temperature)
        for i, row in enumerate(ids.cpu()):
            generated[int(order[start + i])] = decode(row)            # drops <bos>, <eos>, <pad>
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w") as f:
        for i, seq in enumerate(generated):
            f.write(f">sample_{i} length={len(seq)} checkpoint={tag}\n{seq}\n")
    print(f"wrote {n} sequences to {args.out} ({tag}, {args.steps} steps, T={args.temperature}, "
          f"{args.weights} weights)")


if __name__ == "__main__":
    main()
