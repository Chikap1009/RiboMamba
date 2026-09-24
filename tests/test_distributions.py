"""Known-answer tests for distribution distances, structure elements and diversity (Phase 3)."""

import numpy as np
import pytest

from ribomamba.eval.distributions import (gc_content, js_divergence, kmer_spectrum, structure_elements,
                                          wasserstein1)
from ribomamba.eval.diversity import internal_identity, mean_pairwise_hamming, novelty


def test_wasserstein_known_answers():
    assert wasserstein1([0, 1, 2], [0, 1, 2]) == 0.0
    assert wasserstein1([0, 1, 2], [5, 6, 7]) == pytest.approx(5.0)          # every unit of mass moves 5
    assert wasserstein1([0, 0], [0, 1]) == pytest.approx(0.5)                # half the mass moves 1
    assert wasserstein1([1, 2, 3], [3, 1, 2]) == 0.0                         # order doesn't matter
    rng = np.random.default_rng(0)                                           # different sample sizes work
    assert wasserstein1(rng.normal(0, 1, 4000), rng.normal(2, 1, 3000)) == pytest.approx(2.0, abs=0.08)


def test_kmer_spectrum_and_jsd():
    p = kmer_spectrum(["GGGA"], k=2)                                         # GG, GG, GA
    assert p.sum() == pytest.approx(1.0) and len(p) == 16
    assert p[10] == pytest.approx(2 / 3) and p[8] == pytest.approx(1 / 3)   # GG = index 10, GA = index 8
    assert js_divergence(p, p) == 0.0
    a, b = np.array([1.0, 0, 0, 0]), np.array([0, 1.0, 0, 0])
    assert js_divergence(a, b) == pytest.approx(1.0)                         # disjoint: the maximum, 1 bit
    assert js_divergence(a, b) == js_divergence(b, a)


def test_gc_content():
    assert gc_content("GGGAAACCC") == pytest.approx(6 / 9)


@pytest.mark.parametrize("structure, expected", [
    ("(((...)))", dict(pairs=3, stems=1, hairpins=1, bulges=0, internal_loops=0, multiloops=0,
                       mean_stem_length=3.0, mean_hairpin_size=3.0)),
    # one unpaired base on ONE side between two stems: a bulge
    ("((.((...))))", dict(pairs=4, stems=2, hairpins=1, bulges=1, internal_loops=0, multiloops=0)),
    # unpaired bases on BOTH sides between the same two stems: one internal loop, not two bulges
    ("((..((...))...))", dict(pairs=4, stems=2, hairpins=1, bulges=0, internal_loops=1, multiloops=0)),
    # one pair enclosing two stems: a multiloop (junction)
    ("(((...))((...)))", dict(pairs=5, stems=3, hairpins=2, bulges=0, internal_loops=0, multiloops=1,
                              mean_hairpin_size=3.0)),
    ("........", dict(pairs=0, stems=0, hairpins=0, mean_stem_length=0.0)),
    ("((...))((...))", dict(pairs=4, stems=2, hairpins=2, multiloops=0)),   # two stems in the exterior loop
])
def test_structure_elements(structure, expected):
    got = structure_elements(structure)
    for key, value in expected.items():
        assert got[key] == pytest.approx(value), key


def test_mean_pairwise_hamming():
    assert mean_pairwise_hamming(["GGGAAACC", "GGGAAACC", "GCGAAAGC"]) == pytest.approx((0 + 2 + 2) / 3 / 8)
    with pytest.raises(ValueError):
        mean_pairwise_hamming(["GGG", "GGGA"])


def test_novelty_and_internal_identity_with_mmseqs2():
    rng = np.random.default_rng(1)
    rand = lambda n: "".join(rng.choice(list("ACGU"), size=n))              # noqa: E731
    train = [rand(80) for _ in range(20)]
    copy_of_train, unrelated = train[3], rand(80)
    samples = [copy_of_train, unrelated, unrelated]                          # the last two are duplicates
    nov = novelty(samples, train)
    assert nov[0] == pytest.approx(1.0) and nov[1] == 0.0                    # copy found; random has no relative
    inner = internal_identity(samples)
    assert inner[0] == 0.0 and inner[1] == pytest.approx(1.0) and inner[2] == pytest.approx(1.0)
