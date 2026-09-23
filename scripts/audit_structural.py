"""Structure-aware leakage audit of the split (Phase 1, D-009).

Question: would Rfam itself call any held-out sequence a MEMBER of a TRAINING
family? Letter-based search (audit_leakage.py) can miss relatives whose
letters drifted apart by covariation; Rfam's covariance models cannot,
because they score base pairs.

Every val and test sequence is scanned with Infernal's cmscan against all
4,178 Rfam 15.0 models. Checks:
  A. positive control: is each held-out sequence's OWN family found (score >= GA)?
     If not, a clean result below could just mean a blind detector.
  B. leakage: held-out sequences scoring >= GA against a family that is in TRAIN.
     Zero BY CONSTRUCTION with the fast filters, because prepare_data.py step 11
     removed exactly these (same scan, same cache); check D is the independent test.
  C. weak resemblance: held-out sequences with any E <= 1e-3 hit to a train
     family, next to a NEGATIVE control (the same sequences, dinucleotide-shuffled)
     that shows how often such hits happen by chance.
  D. filter sensitivity: on a sample, Rfam's fast pre-filters (--rfam, used for A-C)
     versus Infernal's slower default filters, counted at the GA level.

Usage:  python scripts/audit_structural.py      (~2.2 hours on 20 threads; results cached)
Output: data/processed/audit_structural.json, printed summary for docs/RESULTS.md
"""

import json

import numpy as np
import polars as pl

from ribomamba.data.structure_search import cmscan, dinucleotide_shuffle, gathering_thresholds
from ribomamba.paths import PROCESSED_DIR

SAMPLE_SIZE = 2000        # for checks C (negative control) and D
WEAK_EVALUE = 1e-3        # check C threshold
SEED = 0


def share(k: int, n: int) -> list[float]:
    """[proportion, 95% confidence half-width] (normal approximation)."""
    p = k / n
    return [round(p, 5), round(1.96 * np.sqrt(p * (1 - p) / n), 5)]


def classify(hits: pl.DataFrame, queries: pl.DataFrame, ga: dict, train_families: set) -> pl.DataFrame:
    """Per hit: is it a member-level hit (>= GA)? to the query's own family? to a train family?"""
    return (hits.join(queries.select("query", pl.col("family").alias("own_family")), on="query")
            .with_columns(
                member=pl.col("score") >= pl.col("family").replace_strict(ga, return_dtype=pl.Float64),
                own=pl.col("family") == pl.col("own_family"),
                to_train=pl.col("family").is_in(list(train_families)),
            ))


def main() -> None:
    rng = np.random.default_rng(SEED)
    ga = gathering_thresholds()
    train_families = set(pl.read_parquet(PROCESSED_DIR / "train.parquet", columns=["family"])["family"])
    held_out = pl.concat([
        pl.read_parquet(PROCESSED_DIR / f"{s}.parquet").with_columns(split=pl.lit(s)) for s in ("val", "test")
    ]).with_row_index("query").with_columns(pl.col("query").cast(pl.Int64))
    n = held_out.height
    audit = {"config": dict(SAMPLE_SIZE=SAMPLE_SIZE, WEAK_EVALUE=WEAK_EVALUE, SEED=SEED,
                            models="Rfam 15.0", n_held_out=n)}

    # --- Full scan: every held-out sequence (checks A, B, C) ---
    hits = classify(cmscan(held_out["sequence"].to_list()), held_out, ga, train_families)
    own_found = hits.filter("member", "own")["query"].unique()
    member_of_train = hits.filter("member", "to_train")
    weak_to_train = hits.filter("to_train", pl.col("evalue") <= WEAK_EVALUE)
    audit["A_own_family_found_at_GA"] = share(own_found.len(), n)
    audit["B_member_of_a_train_family"] = {
        "all": share(member_of_train["query"].n_unique(), n),
        **{s: share(member_of_train.join(held_out.select("query", "split"), on="query")
                    .filter(pl.col("split") == s)["query"].n_unique(),
                    (held_out["split"] == s).sum()) for s in ("val", "test")},
        "pairs": (member_of_train.group_by("own_family", "family").agg(pl.col("query").n_unique().alias("n"))
                  .sort("n", descending=True).rename({"family": "train_family"}).head(25).to_dicts()),
    }
    audit["C_weak_hit_to_a_train_family_all"] = share(weak_to_train["query"].n_unique(), n)

    # --- Sample for the controls (checks C and D) ---
    sample = held_out.sample(SAMPLE_SIZE, seed=SEED).with_row_index("sample_query").with_columns(
        pl.col("sample_query").cast(pl.Int64))
    in_sample = set(sample["query"].to_list())
    audit["C_weak_hit_to_a_train_family_sample_real"] = share(
        weak_to_train.filter(pl.col("query").is_in(in_sample))["query"].n_unique(), SAMPLE_SIZE)

    shuffled = [dinucleotide_shuffle(s, rng) for s in sample["sequence"].to_list()]
    shuffled_queries = sample.select(pl.col("sample_query").alias("query"), "family")
    sh = classify(cmscan(shuffled), shuffled_queries, ga, train_families)
    audit["C_negative_control_shuffled"] = {
        "weak_hit_to_a_train_family": share(sh.filter("to_train", pl.col("evalue") <= WEAK_EVALUE)["query"].n_unique(), SAMPLE_SIZE),
        "member_of_any_family": share(sh.filter("member")["query"].n_unique(), SAMPLE_SIZE),
    }

    sample_queries = sample.select(pl.col("sample_query").alias("query"), "family")
    fast = classify(cmscan(sample["sequence"].to_list()), sample_queries, ga, train_families)
    slow = classify(cmscan(sample["sequence"].to_list(), sensitive_filters=True), sample_queries, ga, train_families)
    audit["D_filter_sensitivity_sample"] = {
        name: {"own_family_found_at_GA": share(d.filter("member", "own")["query"].n_unique(), SAMPLE_SIZE),
               "member_of_a_train_family": share(d.filter("member", "to_train")["query"].n_unique(), SAMPLE_SIZE),
               "weak_hit_to_a_train_family": share(d.filter("to_train", pl.col("evalue") <= WEAK_EVALUE)["query"].n_unique(), SAMPLE_SIZE)}
        for name, d in (("rfam_filters", fast), ("default_filters", slow))
    }

    with open(PROCESSED_DIR / "audit_structural.json", "w") as f:
        json.dump(audit, f, indent=2)
    print(json.dumps(audit, indent=2))


if __name__ == "__main__":
    main()
