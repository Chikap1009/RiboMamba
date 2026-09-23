"""Reference points for bits per nucleotide: k-th order Markov models (Phase 2).

A k-th order Markov model predicts each nucleotide from the k nucleotides
before it, using counts from the training split:

    p(x_i | x_{i-k} ... x_{i-1}) = (count(context, x_i) + a) / (count(context) + 4a)

with add-a smoothing (a = 0.5, fixed in advance, not tuned on validation).
Positions near the start use a shorter context padded with a "start"
symbol. These are exact likelihoods, in bits per nucleotide, on the same
validation split (unseen families) the diffusion models are scored on.
k = 0 is letter frequencies alone; a model that can't beat the best k has
learned nothing beyond local statistics.

Note the diffusion models' number is an upper bound (NELBO) and they are told
the length; the Markov models aren't. Both favour neither side by much.

Usage:  python scripts/baselines_markov.py
Output: data/processed/markov_baselines.json + a printed table for RESULTS.md
"""

import json
import math

import numpy as np
import polars as pl

from ribomamba.paths import PROCESSED_DIR

ORDERS = range(0, 9)
SMOOTHING = 0.5
START = 4                      # the "before the sequence" symbol; nucleotides are 0..3


def to_int_arrays(split: str) -> list[np.ndarray]:
    table = str.maketrans("ACGU", "0123")
    seqs = pl.read_parquet(PROCESSED_DIR / f"{split}.parquet", columns=["sequence"])["sequence"]
    return [np.frombuffer(s.translate(table).encode(), dtype=np.uint8) - ord("0") for s in seqs]


def contexts_and_targets(seqs: list[np.ndarray], k: int) -> tuple[np.ndarray, np.ndarray]:
    """For every nucleotide: its context id (base-5 number of the k previous symbols) and itself."""
    ctx_all, tgt_all = [], []
    for s in seqs:
        padded = np.concatenate([np.full(k, START, dtype=np.int64), s.astype(np.int64)])
        ctx = np.zeros(len(s), dtype=np.int64)
        for j in range(k):                                   # previous symbol j+1 positions back
            ctx = ctx * 5 + padded[k - 1 - j: k - 1 - j + len(s)]
        ctx_all.append(ctx)
        tgt_all.append(s.astype(np.int64))
    return np.concatenate(ctx_all), np.concatenate(tgt_all)


def evaluate_orders(train: list[np.ndarray], val: list[np.ndarray]) -> dict:
    results = {}
    for k in ORDERS:
        n_ctx = 5 ** k
        ctx, tgt = contexts_and_targets(train, k)
        counts = np.bincount(ctx * 4 + tgt, minlength=n_ctx * 4).reshape(n_ctx, 4).astype(np.float64)
        probs = (counts + SMOOTHING) / (counts.sum(axis=1, keepdims=True) + 4 * SMOOTHING)
        vctx, vtgt = contexts_and_targets(val, k)
        bits = -np.log2(probs[vctx, vtgt]).mean()
        train_bits = -np.log2(probs[ctx, tgt]).mean()
        results[k] = {"val_bits_per_nt": round(float(bits), 4), "train_bits_per_nt": round(float(train_bits), 4)}
        print(f"  order {k}: train {train_bits:.4f}  val {bits:.4f} bits/nt", flush=True)
    return results


def main() -> None:
    train, val, test = to_int_arrays("train"), to_int_arrays("val"), to_int_arrays("test")
    print("our clan/family split:")
    ours = evaluate_orders(train, val)

    # Control: the same sequences split randomly 80/10/10, ignoring families (as in audit_leakage.py).
    pool = train + val + test
    order = np.random.default_rng(0).permutation(len(pool))
    n_val = len(val)
    random_val = [pool[i] for i in order[:n_val]]
    random_train = [pool[i] for i in order[2 * n_val:]]
    print("random split (control):")
    control = evaluate_orders(random_train, random_val)

    best = min(ours, key=lambda k: ours[k]["val_bits_per_nt"])
    out = {"smoothing": SMOOTHING, "ours": ours, "random_split_control": control, "best_order_on_val": best}
    (PROCESSED_DIR / "markov_baselines.json").write_text(json.dumps(out, indent=2))
    print(f"best order on our validation split: {best} ({ours[best]['val_bits_per_nt']} bits/nt)")


if __name__ == "__main__":
    main()
