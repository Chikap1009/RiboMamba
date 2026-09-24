"""Known-answer tests for the evaluation statistics (Phase 3)."""

import numpy as np
import pytest

from ribomamba.eval.stats import (bootstrap_ci, cluster_bootstrap_ci, hierarchical_bootstrap, holm,
                                  paired_test, seed_permutation_test)


def test_bootstrap_matches_the_normal_formula_for_a_proportion():
    # 546 successes in 1,000: the formula gives 0.546 +- 1.96 * sqrt(0.546 * 0.454 / 1000) = +- 0.0309.
    x = np.r_[np.ones(546), np.zeros(454)]
    est, low, high = bootstrap_ci(x, seed=0)
    assert est == pytest.approx(0.546)
    assert low == pytest.approx(0.546 - 0.0309, abs=0.004)
    assert high == pytest.approx(0.546 + 0.0309, abs=0.004)


def test_bootstrap_intervals_cover_the_truth_about_95_percent_of_the_time():
    # Draw 300 datasets of 80 values from a distribution whose mean we know (exponential, mean 1).
    rng = np.random.default_rng(1)
    covered = [low <= 1.0 <= high
               for low, high in (bootstrap_ci(rng.exponential(1.0, 80), n_boot=2000, seed=s)[1:]
                                 for s in range(300))]
    assert 0.89 <= np.mean(covered) <= 0.98         # percentile intervals run slightly short on skewed data


def test_bootstrap_refuses_nan():
    with pytest.raises(ValueError):
        bootstrap_ci([1.0, np.nan, 2.0])


def test_cluster_bootstrap_counts_groups_not_items():
    # 40 families of 10 identical members: 400 items but only 40 independent values.
    rng = np.random.default_rng(2)
    family_values = rng.normal(0, 1, 40)
    items, groups = np.repeat(family_values, 10), np.repeat(np.arange(40), 10)
    _, lo_naive, hi_naive = bootstrap_ci(items, seed=0)
    _, lo_clust, hi_clust = cluster_bootstrap_ci(items, groups, seed=0)
    _, lo_fam, hi_fam = bootstrap_ci(family_values, seed=0)
    # Naive intervals pretend there are 400 independent items: about sqrt(10) = 3.2x too narrow.
    assert (hi_clust - lo_clust) / (hi_naive - lo_naive) == pytest.approx(np.sqrt(10), rel=0.15)
    assert (hi_clust - lo_clust) == pytest.approx(hi_fam - lo_fam, rel=0.1)


def test_cluster_bootstrap_ratio_estimate():
    # nats per nucleotide = total nats / total nucleotides, not the mean of per-sequence ratios.
    est, _, _ = cluster_bootstrap_ci([10.0, 30.0, 20.0], groups=["a", "a", "b"], denominators=[10, 10, 40])
    assert est == pytest.approx(60 / 60)


def test_paired_sign_flip_exact_p_values():
    # All differences positive: of the 2^n sign patterns, only "all +" and "all -" are as extreme.
    assert paired_test([2, 2, 2], [1, 1, 1])["p_value"] == pytest.approx(2 / 8)
    assert paired_test([2, 2, 2, 2], [1, 1, 1, 1])["p_value"] == pytest.approx(2 / 16)
    assert paired_test([1, 2, 3], [1, 2, 3])["p_value"] == pytest.approx(1.0)


def test_paired_test_sees_a_small_consistent_difference_that_item_difficulty_would_hide():
    # Item difficulty varies a lot (0.1 .. 0.9); model A is 0.02 better on every item, plus small noise.
    rng = np.random.default_rng(3)
    difficulty = rng.uniform(0.1, 0.9, 200)
    a = difficulty + 0.02 + rng.normal(0, 0.01, 200)
    b = difficulty + rng.normal(0, 0.01, 200)
    r = paired_test(a, b, seed=0)
    assert r["p_value"] < 0.001 and r["ci_low"] > 0
    # Ignoring the pairing (two separate intervals) the difference is invisible: they overlap.
    _, lo_a, hi_a = bootstrap_ci(a, seed=0)
    _, lo_b, hi_b = bootstrap_ci(b, seed=1)
    assert lo_a < hi_b


def test_paired_test_false_alarm_rate_is_about_5_percent():
    rng = np.random.default_rng(4)
    p = [paired_test(rng.normal(size=40), rng.normal(size=40), n_boot=200, n_perm=999, seed=s)["p_value"]
         for s in range(300)]
    assert 0.02 <= np.mean(np.array(p) < 0.05) <= 0.09


def test_hierarchical_bootstrap_includes_seed_to_seed_variation():
    # Three "training seeds" whose means differ (0, 0.3, 0.6), 500 samples each with little noise.
    rng = np.random.default_rng(5)
    units = [m + rng.normal(0, 0.05, 500) for m in (0.0, 0.3, 0.6)]
    reps = hierarchical_bootstrap(units, n_boot=2000, seed=0)
    pooled = np.concatenate(units)
    _, lo_pooled, hi_pooled = bootstrap_ci(pooled, seed=0)
    assert np.mean(reps) == pytest.approx(0.3, abs=0.03)
    assert np.percentile(reps, 97.5) - np.percentile(reps, 2.5) > 10 * (hi_pooled - lo_pooled)


def test_seed_permutation_test_exact_values():
    # Complete separation: only the real labelling and its mirror image are as extreme.
    r = seed_permutation_test([1.1, 1.2, 1.3], [1.0, 0.9, 0.8])
    assert r["p_value"] == pytest.approx(2 / 20) and r["min_possible_p"] == pytest.approx(0.1)
    r = seed_permutation_test([2, 2.1, 2.2, 2.3, 2.4], [1, 1.1, 1.2, 1.3, 1.4])
    assert r["p_value"] == pytest.approx(2 / 252)
    assert seed_permutation_test([1, 2, 3], [1, 2, 3])["p_value"] == pytest.approx(1.0)
    # One overlap (A's worst seed below B's best): no longer the most extreme labelling.
    assert seed_permutation_test([2, 2.1, 2.2, 2.3, 1.05], [1, 1.1, 1.2, 1.3, 1.4])["p_value"] > 2 / 252


def test_holm_textbook_example():
    # m = 4. Sorted: 0.005*4 = 0.02, 0.01*3 = 0.03, 0.03*2 = 0.06, 0.04*1 = 0.04 -> 0.06 (kept non-decreasing).
    adjusted, reject = holm([0.01, 0.04, 0.03, 0.005])
    assert adjusted == pytest.approx([0.03, 0.06, 0.06, 0.02])
    assert reject.tolist() == [True, False, False, True]
