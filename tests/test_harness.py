"""Tests for the pre-registration lock, the reference sets and the harness (Phase 3)."""

import os

import numpy as np
import pytest

from ribomamba.eval.protocol import frozen_date, require_frozen
from ribomamba.eval.reference import length_matched, random_sequences


def test_test_split_is_locked_until_the_protocol_is_frozen(tmp_path):
    results = tmp_path / "RESULTS.md"
    results.write_text("## Frozen evaluation protocol\n\n*(Not yet written.)*\n")
    require_frozen("val", results)                                     # validation: always allowed
    require_frozen("train", results)
    with pytest.raises(PermissionError):
        require_frozen("test", results)
    with pytest.raises(ValueError):
        require_frozen("tset", results)
    results.write_text("## Frozen evaluation protocol\n\n**Status: FROZEN on 2026-09-24**\n")
    assert frozen_date(results) == "2026-09-24"
    require_frozen("test", results)                                    # now allowed


def test_length_matching_gives_equal_lengths_without_reuse():
    pool = ["A" * 10, "C" * 10, "G" * 10, "U" * 12, "A" * 15]
    out = length_matched(pool, [10, 10, 12], seed=0)
    assert [len(s) for s in out] == [10, 10, 12] and len(set(out)) == 3
    out = length_matched(pool, [10, 10, 10, 10], seed=0)               # 3 of length 10, then the nearest (12)
    assert sorted(len(s) for s in out) == [10, 10, 10, 12]
    out = length_matched(pool, [10], seed=0, exclude={"A" * 10, "C" * 10})
    assert out == ["G" * 10]
    with pytest.raises(ValueError):
        length_matched(["A" * 10], [10, 10], seed=0)                   # pool exhausted


def test_random_sequences_have_the_requested_lengths_and_are_reproducible():
    a, b = random_sequences([5, 50], seed=3), random_sequences([5, 50], seed=3)
    assert a == b and [len(s) for s in a] == [5, 50] and set("".join(a)) <= set("ACGU")


@pytest.mark.skipif("ETERNAFOLD_PARAMETERS" not in os.environ, reason="needs the ribomamba conda env (EternaFold)")
def test_harness_end_to_end_on_a_few_sequences():
    from ribomamba.eval.harness import SCALAR_METRICS, distances, per_sequence, summarise
    rng = np.random.default_rng(0)
    seqs = ["GGGGAAAACCCC" + "".join(rng.choice(list("ACGU"), size=40)) for _ in range(6)]
    train = ["".join(rng.choice(list("ACGU"), size=60)) for _ in range(10)] + [seqs[0]]
    table = per_sequence(seqs, train, n_shuffles=5, processes=2)
    assert table.height == 6 and table["sequence"].to_list() == seqs
    assert set(SCALAR_METRICS) <= set(table.columns)
    assert table["train_identity"][0] == pytest.approx(1.0)            # seqs[0] was planted in train
    summary = summarise(table)
    for metric in SCALAR_METRICS:
        s = summary[metric]
        assert s["low"] - 1e-12 <= s["mean"] <= s["high"] + 1e-12, metric
    assert summary["distinct_fraction"] == 1.0
    assert all(v == 0.0 for v in distances(table, table).values())    # a set is at distance 0 from itself
