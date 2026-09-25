"""The reference sets every generated set is measured against (Phase 3).

A number like "NED 0.20" means nothing alone; it needs a scale. For a
reference of n real held-out sequences (REAL) we build four more sets with
the SAME lengths, in the same order, because every folding metric depends on
length:

  real      n random sequences of the split (unseen families)
  real2     n OTHER sequences of the same split, length-matched: two
            independent samples of real RNA; their distance is the noise floor
  train     n training sequences, length-matched: what the model was
            trained to imitate; its distance from `real` is the family shift
  shuffled  each real sequence, dinucleotide-shuffled once: same letters and
            neighbour counts, arrangement destroyed (the "looks like RNA" null)
  random    uniform random letters: the far end of the scale

Generated sequences are sampled with exactly real's lengths (scripts/sample.py
--lengths-from), so generated[i] and real[i] have equal length.
"""

import numpy as np
import polars as pl

from ribomamba.data.structure_search import dinucleotide_shuffle
from ribomamba.eval.protocol import require_frozen
from ribomamba.paths import PROCESSED_DIR


def load_split(split: str, columns: list[str] | None = None, data_dir=PROCESSED_DIR) -> pl.DataFrame:
    """One split of the frozen split (data/processed) or of a replication split (data/processed_split<k>)."""
    require_frozen(split)                           # the test split stays locked until the freeze
    return pl.read_parquet(data_dir / f"{split}.parquet", columns=columns)


def reference_sample(split: str, n: int, seed: int, data_dir=PROCESSED_DIR) -> pl.DataFrame:
    """n random sequences of `split` (columns: sequence, family, length). Same (split, n, seed) -> same rows."""
    return load_split(split, ["sequence", "family", "length"], data_dir).sample(n, seed=seed)


def length_matched(pool: list[str], lengths: list[int], seed: int, exclude: set[str] = frozenset()) -> list[str]:
    """For each requested length, a different random sequence from `pool` with that length.

    Falls back to the nearest available length (checked outward: L-1, L+1,
    L-2, ...) if a length runs out; never uses a sequence twice or one in
    `exclude`.
    """
    rng = np.random.default_rng(seed)
    by_length: dict[int, list[str]] = {}
    for s in pool:
        if s not in exclude:
            by_length.setdefault(len(s), []).append(s)
    for bucket in by_length.values():
        rng.shuffle(bucket)
    out = []
    for length in lengths:
        for offset in range(0, 1000):
            candidates = [c for c in (length - offset, length + offset) if by_length.get(c)]
            if candidates:
                out.append(by_length[candidates[0]].pop())
                break
        else:
            raise ValueError(f"no sequence left near length {length}")
    return out


def random_sequences(lengths: list[int], seed: int) -> list[str]:
    rng = np.random.default_rng(seed)
    return ["".join(rng.choice(list("ACGU"), size=n)) for n in lengths]


def shuffled_copies(sequences: list[str], seed: int) -> list[str]:
    rng = np.random.default_rng(seed)
    return [dinucleotide_shuffle(s, rng) for s in sequences]


def reference_sets(split: str, n: int, seed: int, data_dir=PROCESSED_DIR) -> dict[str, list[str]]:
    """The five sets described in the module docstring, each a list of n sequences in real's order."""
    real = reference_sample(split, n, seed, data_dir)
    lengths = real["length"].to_list()
    real_seqs = real["sequence"].to_list()
    split_pool = load_split(split, ["sequence"], data_dir)["sequence"].to_list()
    train_pool = load_split("train", ["sequence"], data_dir)["sequence"].to_list()
    return {
        "real": real_seqs,
        "real2": length_matched(split_pool, lengths, seed + 1, exclude=set(real_seqs)),
        "train": length_matched(train_pool, lengths, seed + 2),
        "shuffled": shuffled_copies(real_seqs, seed + 3),
        "random": random_sequences(lengths, seed + 4),
    }
