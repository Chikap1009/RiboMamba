"""Statistics for the evaluation harness (Phase 3): error bars and fair comparisons.

Every function answers one question (STUDY_GUIDE Part 5; logbook session 04):

  bootstrap_ci            how uncertain is a number measured on n independent items?
  cluster_bootstrap_ci    ... when items come in correlated groups (RNA families)?
  hierarchical_bootstrap  ... when there are several trained models (seeds), each with many items?
  paired_test             do two models differ, measured on the SAME items (targets, lengths)?
  seed_permutation_test   do two ARCHITECTURES differ, with each trained model (seed) as one observation?
  holm                    which of several tests survive the multiple-comparisons correction?

All randomness comes from an explicit seed, so every interval is reproducible.
Intervals are percentile bootstrap intervals (Efron 1979): resample, recompute,
read off the 2.5th and 97.5th percentiles.
"""

from itertools import combinations, product

import numpy as np

N_BOOT = 10_000
LEVEL = 0.95


def _interval(replicates: np.ndarray, level: float) -> tuple[float, float]:
    tail = (1 - level) / 2 * 100
    low, high = np.percentile(replicates, [tail, 100 - tail])
    return float(low), float(high)


def bootstrap_ci(values, statistic=np.mean, n_boot: int = N_BOOT, level: float = LEVEL,
                 seed: int = 0) -> tuple[float, float, float]:
    """(estimate, low, high) for statistic(values), items independent.

    `statistic` must accept an `axis` argument (np.mean, np.median, ...), so all
    n_boot resamples are computed in one vectorised call: (n_boot, n) -> (n_boot,).
    """
    x = np.asarray(values, dtype=float)
    if x.ndim != 1 or len(x) == 0 or np.isnan(x).any():
        raise ValueError("need a non-empty 1-D array without NaN (drop undefined values explicitly first)")
    rng = np.random.default_rng(seed)
    idx = rng.integers(len(x), size=(n_boot, len(x)))                 # (n_boot, n) resampled positions
    reps = statistic(x[idx], axis=1)                                  # (n_boot,)
    return (float(statistic(x)), *_interval(reps, level))


def cluster_bootstrap_ci(numerators, groups, denominators=None, n_boot: int = N_BOOT,
                         level: float = LEVEL, seed: int = 0) -> tuple[float, float, float]:
    """(estimate, low, high) for sum(numerators) / sum(denominators), resampling whole GROUPS.

    With denominators = 1 per item this is the mean over items; with per-sequence
    nats and lengths it is nats per nucleotide. Items in one group (one RNA
    family) are correlated, so the error bar must count groups, not items.
    """
    num = np.asarray(numerators, dtype=float)
    den = np.ones_like(num) if denominators is None else np.asarray(denominators, dtype=float)
    _, g = np.unique(np.asarray(groups), return_inverse=True)         # group labels -> 0..G-1
    n_groups = g.max() + 1
    num_g = np.bincount(g, weights=num, minlength=n_groups)            # (G,) per-group totals
    den_g = np.bincount(g, weights=den, minlength=n_groups)            # (G,)
    rng = np.random.default_rng(seed)
    idx = rng.integers(n_groups, size=(n_boot, n_groups))              # (n_boot, G) resampled groups
    reps = num_g[idx].sum(axis=1) / den_g[idx].sum(axis=1)             # (n_boot,)
    return (float(num.sum() / den.sum()), *_interval(reps, level))


def hierarchical_bootstrap(values_per_unit: list, n_boot: int = N_BOOT, seed: int = 0) -> np.ndarray:
    """Bootstrap replicates of the mean of unit means, resampling units AND items within them.

    A "unit" is one trained model (one training seed); its items are that
    model's per-sample scores. Resampling units captures seed-to-seed
    variation; resampling items within a unit captures sampling noise. Returns
    the (n_boot,) replicates, so two backbones can be compared by subtracting
    independently drawn replicate arrays.
    """
    units = [np.asarray(v, dtype=float) for v in values_per_unit]
    rng = np.random.default_rng(seed)
    reps = np.empty(n_boot)
    for b in range(n_boot):
        chosen = rng.integers(len(units), size=len(units))
        reps[b] = np.mean([units[u][rng.integers(len(units[u]), size=len(units[u]))].mean() for u in chosen])
    return reps


def paired_test(a, b, n_boot: int = N_BOOT, n_perm: int = N_BOOT, level: float = LEVEL,
                seed: int = 0) -> dict:
    """Compare two models on the same items: mean of (a - b), its bootstrap CI, and a p-value.

    The p-value is a sign-flip permutation test: if the two models were
    interchangeable, each item's difference would be equally likely to be
    positive or negative, so we flip signs at random and ask how often the
    mean difference is at least as far from 0 as the one observed. Exact
    (all 2^n sign patterns) for n <= 16, Monte Carlo otherwise.
    """
    d = np.asarray(a, dtype=float) - np.asarray(b, dtype=float)
    if len(d) == 0 or np.isnan(d).any():
        raise ValueError("need paired, non-empty values without NaN")
    observed = abs(d.mean())
    if len(d) <= 16:
        signs = np.array(list(product([1.0, -1.0], repeat=len(d))))     # (2^n, n) every sign pattern
        p = float(np.mean(np.abs((signs * d).mean(axis=1)) >= observed - 1e-12))
    else:
        rng = np.random.default_rng(seed + 1)
        signs = rng.choice([1.0, -1.0], size=(n_perm, len(d)))          # (n_perm, n)
        hits = np.sum(np.abs((signs * d).mean(axis=1)) >= observed - 1e-12)
        p = float((hits + 1) / (n_perm + 1))                            # +1: the observed pattern itself
    est, low, high = bootstrap_ci(d, n_boot=n_boot, level=level, seed=seed)
    return {"mean_diff": est, "ci_low": low, "ci_high": high, "p_value": p, "n": len(d)}


def seed_permutation_test(scores_a, scores_b) -> dict:
    """Exact two-sided permutation test on per-seed scores (one number per trained model).

    If the architecture made no difference, the labels "A" and "B" on the
    n_a + n_b trained models would be interchangeable. We try EVERY way of
    relabelling them and count how often the difference of means is at least
    as large (in absolute value) as the real one. The smallest possible p is
    2 / C(n_a + n_b, n_a): 0.10 for 3 vs 3 seeds (so 3 seeds can never reach
    0.05), 0.0079 for 5 vs 5.
    """
    a, b = np.asarray(scores_a, dtype=float), np.asarray(scores_b, dtype=float)
    pooled = np.concatenate([a, b])
    observed = abs(a.mean() - b.mean())
    count = total = 0
    for chosen in combinations(range(len(pooled)), len(a)):
        mask = np.zeros(len(pooled), dtype=bool)
        mask[list(chosen)] = True
        total += 1
        count += abs(pooled[mask].mean() - pooled[~mask].mean()) >= observed - 1e-12
    return {"mean_diff": float(a.mean() - b.mean()), "p_value": count / total,
            "min_possible_p": 2 / total if len(a) == len(b) else 1 / total, "n_a": len(a), "n_b": len(b)}


def holm(p_values, alpha: float = 0.05) -> tuple[np.ndarray, np.ndarray]:
    """Holm-Bonferroni: (adjusted p-values, reject?) in the original order.

    Sort the m p-values; the k-th smallest (k = 0, 1, ...) is multiplied by
    (m - k); adjusted values are made non-decreasing in sorted order; reject
    where adjusted p <= alpha. Controls the chance of ANY false "win" across
    the m tests at alpha.
    """
    p = np.asarray(p_values, dtype=float)
    m = len(p)
    order = np.argsort(p)
    scaled = np.minimum(1.0, (m - np.arange(m)) * p[order])           # (m,) in sorted order
    adjusted_sorted = np.maximum.accumulate(scaled)
    adjusted = np.empty(m)
    adjusted[order] = adjusted_sorted
    return adjusted, adjusted <= alpha
