"""Novelty and diversity of generated sequences (Phase 3).

  novelty            each sample's identity to its nearest TRAINING sequence
                     (is the model copying what it learned from?)
  internal_identity  each sample's identity to its nearest OTHER sample
                     (is the model repeating itself: mode collapse?)
  mean_pairwise_hamming
                     for designs of one target (all the same length): how
                     many letters differ between two designs, on average

Random letters are perfectly novel and diverse, so these numbers are only
reported next to quality (logbook session 04, concept block).
Identity comes from MMseqs2 (ribomamba/data/similarity.py), with the same
>= 80 % query-coverage rule as the Phase 1 audit; "no hit" counts as 0.
"""

import numpy as np

from ribomamba.data.similarity import best_identity, search

MIN_COVERAGE = 0.8


def novelty(samples: list[str], train: list[str]) -> np.ndarray:
    """(n,) best identity of each sample to any training sequence; 0 = no detectable relative."""
    return best_identity(search(samples, train), len(samples), min_coverage=MIN_COVERAGE)


def internal_identity(samples: list[str]) -> np.ndarray:
    """(n,) best identity of each sample to any OTHER sample in the same set.

    Exact duplicates count: two identical samples give each other identity 1.0.
    """
    hits = search(samples, samples)
    hits = hits.filter(hits["query"] != hits["target"])                # a sample always matches itself
    return best_identity(hits, len(samples), min_coverage=MIN_COVERAGE)


def mean_pairwise_hamming(designs: list[str]) -> float:
    """Average fraction of positions at which two designs differ (all designs the same length).

    'GGGAAACC', 'GGGAAACC', 'GCGAAAGC' -> distances 0, 2, 2 of 8 -> 0.1667.
    """
    if len({len(d) for d in designs}) != 1:
        raise ValueError("all designs must have the same length")
    if len(designs) < 2:
        return 0.0
    x = np.frombuffer("".join(designs).encode(), dtype=np.uint8).reshape(len(designs), -1)   # (n, L) letters
    diff = (x[:, None, :] != x[None, :, :]).mean(axis=2)                                   # (n, n) fraction differing
    return float(diff[np.triu_indices(len(designs), k=1)].mean())
