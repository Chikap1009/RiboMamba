"""Leakage audit of the train / val / test split (Phase 1, D-008).

Question: how close is each held-out sequence to its closest TRAINING sequence?
If many are near-copies, the test set measures memory, not generalisation.

Checks:
  1. no clan or family in two splits            (re-checked from the files)
  2. no identical sequence in two splits
  3. near-duplicates: take N_QUERIES random held-out sequences, search each
     against ALL training sequences with MMseqs2, and record the identity of
     its best hit. Done for our split AND for a random split of the very same
     sequences: the control that shows what a naive split leaks.
     Note: at >= 80% identity our split is clean BY CONSTRUCTION (prepare_data.py
     step 10 uses the same search); the informative numbers are below 80%.
  4. bpRNA sequences that occur letter for letter in our splits (matters if
     bpRNA structures become design targets in Phase 3)

Usage:  python scripts/audit_leakage.py     (under a minute on 20 threads)
Output: data/processed/audit.json, and a summary printed for docs/RESULTS.md
"""

import json

import numpy as np
import polars as pl

from ribomamba.data.similarity import best_identity, search
from ribomamba.paths import PROCESSED_DIR, RAW_DIR

N_QUERIES = 2000               # held-out sequences sampled per check
SEED = 0
IDENTITY_LEVELS = [0.5, 0.8, 0.9, 0.95, 1.0]
MIN_QUERY_COVERAGE = 0.8       # a hit only counts if it aligns over >= 80% of the query


def best_training_hits(queries: list[str], train: list[str]) -> dict:
    """Summarise, over the queries, how close each one's best training relative is."""
    hits = search(queries, train)
    identity = best_identity(hits, len(queries), MIN_QUERY_COVERAGE)   # (n_queries,), 0 = no relative found
    any_hit = hits["query"].n_unique() / len(queries)                  # any significant hit, any coverage

    def share_with_ci(k: int) -> list[float]:
        # proportion and its 95% confidence half-width (normal approximation)
        p = k / len(queries)
        return [round(p, 4), round(1.96 * np.sqrt(p * (1 - p) / len(queries)), 4)]

    return {
        "n_queries": len(queries),
        "any_significant_hit": round(any_hit, 4),
        "median_best_identity": round(float(np.median(identity)), 3),
        "share_at_or_above_identity": {str(t): share_with_ci(int((identity >= t).sum())) for t in IDENTITY_LEVELS},
    }


def main() -> None:
    rng = np.random.default_rng(SEED)
    splits = {s: pl.read_parquet(PROCESSED_DIR / f"{s}.parquet") for s in ("train", "val", "test")}
    audit = {"config": dict(N_QUERIES=N_QUERIES, SEED=SEED, MIN_QUERY_COVERAGE=MIN_QUERY_COVERAGE)}

    # Check 1 and 2: label overlap and identical sequences, for every pair of splits.
    overlaps = {}
    for a, b in (("train", "val"), ("train", "test"), ("val", "test")):
        overlaps[f"{a}-{b}"] = {
            col: len(set(splits[a][col].drop_nulls()) & set(splits[b][col].drop_nulls()))
            for col in ("clan", "family", "sequence")
        }
    audit["check1_2_overlaps"] = overlaps

    # Check 3a: our split.
    train = splits["train"]["sequence"].to_list()
    audit["check3_ours"] = {}
    for held_out in ("val", "test"):
        pool = splits[held_out]["sequence"].to_list()
        queries = [pool[i] for i in rng.choice(len(pool), N_QUERIES, replace=False)]
        audit["check3_ours"][held_out] = best_training_hits(queries, train)

    # Check 3b: the control. Same sequences, shuffled into 80/10/10 ignoring families.
    everything = pl.concat(splits.values())["sequence"].to_list()
    order = rng.permutation(len(everything))
    n_test = len(splits["test"])
    random_test = [everything[i] for i in order[:n_test]]
    random_train = [everything[i] for i in order[n_test + len(splits["val"]):]]
    queries = [random_test[i] for i in rng.choice(len(random_test), N_QUERIES, replace=False)]
    audit["check3_random_split_control"] = {"test": best_training_hits(queries, random_train)}

    # Check 4: bpRNA sequences found letter for letter in our splits.
    bprna = set(
        pl.read_parquet(RAW_DIR / "bprna" / "data.parquet")["sequence"]
        .str.to_uppercase().str.replace_all("T", "U").to_list()
    )
    audit["check4_bprna_exact_matches"] = {
        "distinct_bprna_sequences": len(bprna),
        **{s: len(bprna & set(df["sequence"].to_list())) for s, df in splits.items()},
    }

    with open(PROCESSED_DIR / "audit.json", "w") as f:
        json.dump(audit, f, indent=2)
    print(json.dumps(audit, indent=2))


if __name__ == "__main__":
    main()
