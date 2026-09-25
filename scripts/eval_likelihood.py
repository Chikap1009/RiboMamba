"""Likelihood of every sequence of a held-out split: the protocol's endpoint E1 (Phase 3).

For a masked-diffusion checkpoint, the 1/t-weighted NELBO (an upper bound on
-log p, in nats) of every sequence, averaged over K fixed noise draws. Draw k
uses generator seed 1234 + k, and the batches are the split in its stored
order cut into 16,384-token length buckets, exactly as scripts/train.py
evaluates validation. So every model sees the same t and masks for every
sequence, and draw 0 reproduces the checkpoint's recorded validation value:
a built-in check that this script computes the same thing training did.

Why several draws: one draw gives each sequence one random t and one random
set of masks, so a per-sequence value is noisy. Averaging K draws shrinks
that noise; the spread between draws shows how large it is.

For an autoregressive checkpoint (arch ar_mamba) the likelihood is EXACT and
involves no noise, so there are no draws: one pass gives each sequence's
negative log-likelihood of the framed sequence including <eos> (the protocol's
P6 definition, column nats_mean) and without the <eos> term (nats_letters).
Not like-for-like with the diffusion bound, hence secondary (P7).

Usage:
    python scripts/eval_likelihood.py --checkpoint checkpoints/tf_M_do0/best.pt --split val --draws 4
Output:
    data/eval/likelihood_<run>@<step>_<split>.parquet   per sequence: family, length, nats per draw, mean
    printed: bits/nt per draw and averaged, with a family-cluster 95 % interval
"""

import argparse
import math

import numpy as np
import polars as pl
import torch

from ribomamba.autoregressive import ar_nll_per_sequence
from ribomamba.data.dataset import BucketBatchSampler, RNADataset, collate
from ribomamba.diffusion.masked import mask_tokens, masked_nelbo, sample_times
from ribomamba.eval.protocol import git_commit, require_frozen
from ribomamba.eval.stats import cluster_bootstrap_ci
from ribomamba.models.checkpoint import load_model
from ribomamba.paths import EVAL_DIR, PROCESSED_DIR

BASE_SEED = 1234           # train.py's validation noise seed; draw k uses BASE_SEED + k


@torch.no_grad()
def nelbo_per_sequence(model, dataset: RNADataset, max_tokens: int, seed: int, device) -> np.ndarray:
    """(N,) NELBO in nats of every sequence of `dataset`, for one fixed noise draw."""
    sampler = BucketBatchSampler(dataset.token_lengths(), max_tokens=max_tokens, shuffle=False, seed=0)
    g = torch.Generator(device=device).manual_seed(seed)
    nats = np.full(len(dataset), np.nan)
    for indices in sampler:
        batch = collate([dataset[i] for i in indices])
        ids = batch["input_ids"].to(device)                                  # (B, L)
        att = batch["attention_mask"].to(device)                             # (B, L)
        t = sample_times(ids.shape[0], device, g)                            # (B,) same call order as training
        z, is_masked = mask_tokens(ids, t, g)                                # (B, L)
        with torch.autocast("cuda", dtype=torch.bfloat16):
            logits = model(z, att)                                           # (B, L, V)
        nats[indices] = masked_nelbo(logits, ids, is_masked, t).cpu().numpy()   # (B,) nats per sequence
    return nats


@torch.no_grad()
def exact_nll_per_sequence(model, dataset: RNADataset, max_tokens: int, device) -> tuple[np.ndarray, np.ndarray]:
    """AR models: (N,) exact NLL in nats of every framed sequence, and (N,) without the <eos> term."""
    sampler = BucketBatchSampler(dataset.token_lengths(), max_tokens=max_tokens, shuffle=False, seed=0)
    framed, letters = np.full(len(dataset), np.nan), np.full(len(dataset), np.nan)
    for indices in sampler:
        batch = collate([dataset[i] for i in indices])
        ids = batch["input_ids"].to(device)                                  # (B, L)
        with torch.autocast("cuda", dtype=torch.bfloat16):
            logits = model(ids, batch["attention_mask"].to(device))          # (B, L, V)
        total, letters_only = ar_nll_per_sequence(logits, ids)               # (B,), (B,)
        framed[indices], letters[indices] = total.cpu().numpy(), letters_only.cpu().numpy()
    return framed, letters


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--checkpoint", required=True)
    p.add_argument("--split", default="val", choices=["val", "test"])
    p.add_argument("--draws", type=int, default=4)
    p.add_argument("--weights", choices=["ema", "live"], default="ema")
    args = p.parse_args()
    require_frozen(args.split)

    device = torch.device("cuda")
    model, state = load_model(args.checkpoint, args.weights, device)
    dataset = RNADataset(args.split, add_bos=True, add_eos=True)
    table = pl.read_parquet(PROCESSED_DIR / f"{args.split}.parquet", columns=["family", "length"])
    tag = f"{state['config']['run_name']}@{state['step']}"
    if state["config"].get("arch") == "ar_mamba":
        framed, letters = exact_nll_per_sequence(model, dataset, state["config"]["max_tokens"], device)
        table = table.with_columns(pl.Series("nats_mean", framed), pl.Series("nats_letters", letters))
        length = table["length"].to_numpy()
        print(f"{tag} on {args.split} ({args.weights} weights, commit {git_commit()}): exact, no noise draws")
        print(f"  recorded best validation value in the checkpoint: {state.get('best_val')}")
        for column, label in (("nats_mean", "framed sequence incl. <eos> (P6)"), ("nats_letters", "letters only")):
            est, low, high = cluster_bootstrap_ci(table[column].to_numpy() / math.log(2),
                                                  table["family"].to_list(), denominators=length)
            print(f"  {label}: {est:.4f} bits/nt, family-cluster 95 % CI [{low:.4f}, {high:.4f}]")
        EVAL_DIR.mkdir(parents=True, exist_ok=True)
        table.write_parquet(EVAL_DIR / f"likelihood_{tag}_{args.split}.parquet")
        return
    for k in range(args.draws):
        table = table.with_columns(pl.Series(f"nats_{k}", nelbo_per_sequence(
            model, dataset, state["config"]["max_tokens"], BASE_SEED + k, device)))
    draws = [f"nats_{k}" for k in range(args.draws)]
    table = table.with_columns(pl.mean_horizontal(draws).alias("nats_mean"))

    length = table["length"].to_numpy()
    per_draw = [table[c].sum() / length.sum() / math.log(2) for c in draws]
    est, low, high = cluster_bootstrap_ci(table["nats_mean"].to_numpy() / math.log(2), table["family"].to_list(),
                                          denominators=length)
    EVAL_DIR.mkdir(parents=True, exist_ok=True)
    table.write_parquet(EVAL_DIR / f"likelihood_{tag}_{args.split}.parquet")
    print(f"{tag} on {args.split} ({args.weights} weights, commit {git_commit()}):")
    print(f"  recorded best validation value in the checkpoint: {state.get('best_val')}")
    for k, v in enumerate(per_draw):
        print(f"  draw {k} (seed {BASE_SEED + k}): {v:.4f} bits/nt")
    print(f"  mean of {args.draws} draws: {est:.4f} bits/nt, family-cluster 95 % CI [{low:.4f}, {high:.4f}] "
          f"({table['family'].n_unique()} families); spread between draws (sd) {np.std(per_draw, ddof=1):.4f}")


if __name__ == "__main__":
    main()
