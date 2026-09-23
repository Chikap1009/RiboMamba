from collections import Counter

import numpy as np
import pytest

from ribomamba.data.structure_search import dinucleotide_shuffle


def dinucleotides(s: str) -> Counter:
    return Counter(s[i:i + 2] for i in range(len(s) - 1))


@pytest.mark.parametrize("seq", [
    "GGGAAACCC",
    "ACGUUGCAACGUAGGCUAGCUAGGAUCCAUGCAUUAGC",
    "AAAAAAAAAACGU",
    "GCGCGCGCAUAUAUAUGCGC" * 5,
])
def test_shuffle_keeps_dinucleotide_counts_and_ends(seq):
    rng = np.random.default_rng(0)
    for _ in range(50):
        shuffled = dinucleotide_shuffle(seq, rng)
        assert dinucleotides(shuffled) == dinucleotides(seq)
        assert shuffled[0] == seq[0] and shuffled[-1] == seq[-1]


def test_shuffle_actually_shuffles_and_is_reproducible():
    seq = "ACGUUGCAACGUAGGCUAGCUAGGAUCCAUGCAUUAGC"
    a = [dinucleotide_shuffle(seq, np.random.default_rng(1)) for _ in range(3)]
    b = [dinucleotide_shuffle(seq, np.random.default_rng(1)) for _ in range(3)]
    assert a == b                                            # same seed, same output
    rng = np.random.default_rng(2)
    outputs = {dinucleotide_shuffle(seq, rng) for _ in range(20)}
    assert len(outputs) > 10                                 # many different results
