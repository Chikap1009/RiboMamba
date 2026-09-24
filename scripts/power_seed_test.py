"""Power of the frozen Phase 4 seed-level test (exact permutation, 5 vs 5, two-sided).

"Power" = the chance that a test detects a difference that really exists.
We simulate per-seed scores for two architectures as normal with a true
difference of `delta` per-seed standard deviations, run the exact
permutation test, and count how often it reaches p <= 0.01 (the first Holm
threshold for 5 tests) and p <= 0.05 (a lone test). Multiplying the
answer's delta by a measured per-seed sd (RESULTS.md, Phase 4 preparation)
turns it into the smallest real difference Phase 4 can reliably detect.

Usage: python scripts/power_seed_test.py   (deterministic, seed 0; ~1 min)
"""

import numpy as np

from ribomamba.eval.stats import seed_permutation_test

DELTAS = (1, 1.5, 2, 2.5, 3, 4)
REPEATS = 1000
SEEDS_PER_MODEL = 5


def main() -> None:
    rng = np.random.default_rng(0)
    print("delta/sd  P(p<=0.01)  P(p<=0.05)")
    for d in DELTAS:
        ps = np.array([seed_permutation_test(rng.normal(d, 1, SEEDS_PER_MODEL),
                                             rng.normal(0, 1, SEEDS_PER_MODEL))["p_value"]
                       for _ in range(REPEATS)])
        print(f"{d:7.1f}  {np.mean(ps <= 0.01):10.2f}  {np.mean(ps <= 0.05):10.2f}")


if __name__ == "__main__":
    main()
