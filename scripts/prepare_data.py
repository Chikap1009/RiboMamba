"""Clean Rfam and split it into train / val / test by clan or family (Phase 1).

Pipeline (the row count after every step is printed and saved):
  1. drop the duplicated half of the HF copy (family == "No such family")
  2. normalise letters: T -> U (the data has no lower case; checked in explore_data.py)
  3. drop sequences containing any letter other than A, C, G, U
  4. drop whole families whose median length is over MAX_LEN (long RNAs,
     whose short members are mostly fragments), then single sequences over MAX_LEN
  5. drop likely fragments: shorter than FRAGMENT_FRACTION x their family's median
  6. remove exact duplicates within a family
  7. remove sequences filed under more than one family (ambiguous label)
  8. keep at most PER_FAMILY_CAP randomly chosen members of each family
  9. split: every clan (or, for a family in no clan, the family itself) goes
     WHOLE into exactly one of train / val / test
 10. remove from val/test every sequence with a near-identical training
     relative (MMseqs2: >= 80% identity over >= 80% of its length). Rfam does
     not link every pair of related families through a clan; this catches
     the related pairs it misses.
 11. remove from val/test every sequence that Rfam's own covariance model of a
     TRAINING family scores as a member (bit score >= that family's GA
     threshold; Infernal cmscan, Rfam 15.0). Catches structural relatives
     whose letters differ too much for step 10 (D-009).

Thresholds were chosen from the numbers printed by scripts/explore_data.py
(decisions D-007, D-008, D-009).

Usage:  python scripts/prepare_data.py
        (first run ~2 hours: step 11 scans every held-out sequence against
        4,178 models; results are cached per sequence, so reruns take seconds)
Output: data/processed/{train,val,test}.parquet   columns: sequence, family, clan, group, length
        data/processed/prepare_stats.json          every count printed below
        splits/rfam_split.tsv                      which family went where (committed to Git)
"""

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import polars as pl

from ribomamba.data.similarity import best_identity, search
from ribomamba.data.structure_search import cmscan, gathering_thresholds
from ribomamba.paths import PROCESSED_DIR, RAW_DIR, REPO_ROOT

MAX_LEN = 256             # D-007: longest sequence kept (VRAM, oracle cost; keeps 95% of families)
FRAGMENT_FRACTION = 0.5   # D-007: shorter than half the family's median length = probably a fragment
PER_FAMILY_CAP = 1000     # D-007: at most this many members per family (tRNA alone has 5.3 M)
VAL_FRACTION = 0.10       # D-008: share of sequences in validation ...
TEST_FRACTION = 0.10      # ... and in test; the rest (~80%) is train
NEAR_DUP_IDENTITY = 0.8   # D-008: step 10 thresholds (the conventional 80% used by e.g.
NEAR_DUP_COVERAGE = 0.8   #        CD-HIT-based RNA splits), applied on top of the family split
SEED = 0                  # every random choice below derives from this one number
SPLIT_SEED = SEED         # WHICH groups are held out (--split-seed); the cleaning and the
                          # per-family draw always use SEED, so every split sees the same corpus
                          # and only the held-out families change (frozen protocol P4's
                          # replication split). --split-seed 0 reproduces the frozen data.
PLACEHOLDER_FAMILY = "No such family"


def clean(stats: dict) -> pl.DataFrame:
    """Steps 1-8. Returns one row per kept sequence: sequence, family, clan, length."""
    # Steps 1-3 run lazily while reading the file, so the 10 M dropped rows
    # (and the unused id/description columns) never occupy memory.
    df = (
        pl.scan_parquet(RAW_DIR / "rfam" / "data.parquet")
        .select("sequence", "family", "clan")
        .filter(pl.col("family") != PLACEHOLDER_FAMILY)                               # step 1
        .with_columns(pl.col("sequence").str.replace_all("T", "U"))                    # step 2
        .with_columns(acgu_only=pl.col("sequence").str.contains("^[ACGU]+$"))
        .collect(engine="streaming")
    )
    stats["1_after_dropping_placeholder_copy"] = df.height
    df = df.filter("acgu_only").drop("acgu_only")                                      # step 3
    stats["3_after_acgu_only"] = df.height

    df = df.with_columns(length=pl.col("sequence").str.len_bytes())
    df = df.with_columns(family_median=pl.col("length").median().over("family"))
    long_families = df.filter(pl.col("family_median") > MAX_LEN)["family"].unique().sort()
    stats["4_dropped_long_families"] = long_families.to_list()
    df = df.filter(pl.col("family_median") <= MAX_LEN)                                 # step 4a
    stats["4a_after_dropping_long_families"] = df.height
    df = df.filter(pl.col("length") <= MAX_LEN)                                        # step 4b
    stats["4b_after_length_cap"] = df.height
    df = df.filter(pl.col("length") >= FRAGMENT_FRACTION * pl.col("family_median"))    # step 5
    stats["5_after_fragment_filter"] = df.height

    df = df.unique(subset=["sequence", "family"])                                      # step 6
    stats["6_after_exact_dedup"] = df.height
    df = df.filter(pl.col("family").n_unique().over("sequence") == 1)                  # step 7
    stats["7_after_dropping_multi_family_sequences"] = df.height

    # Step 8. Sorting first makes the row order independent of how polars
    # scheduled its threads; then one seeded random number per row, and
    # each family keeps the rows holding its PER_FAMILY_CAP smallest numbers.
    df = df.sort("family", "sequence")
    df = df.with_columns(key=pl.Series(np.random.default_rng(SEED).random(df.height)))
    df = df.filter(pl.col("key").rank("ordinal").over("family") <= PER_FAMILY_CAP)
    stats["8_after_per_family_cap"] = df.height
    return df.select("sequence", "family", "clan", "length")


def stable_hash(text: str) -> str:
    """Same output on every machine and every run.

    Python's built-in hash() of a string is deliberately randomised per
    process, so it can't be used to make a reproducible split.
    """
    return hashlib.sha256(f"{SPLIT_SEED}:{text}".encode()).hexdigest()


def assign_splits(df: pl.DataFrame) -> pl.DataFrame:
    """Step 9: whole groups (clan, else family) go to test, then val, then train.

    Groups are visited in a pseudo-random order (sorted by stable_hash), and
    test is filled until it holds TEST_FRACTION of the sequences, then val;
    everything left is train. So the choice of groups is random, but the
    sizes come out close to the targets.
    """
    df = df.with_columns(group=pl.coalesce("clan", "family"))
    sizes = df.group_by("group").len().with_columns(
        order=pl.col("group").map_elements(stable_hash, return_dtype=pl.String)
    ).sort("order")

    total, filled = df.height, {"test": 0, "val": 0}
    targets = {"test": TEST_FRACTION * total, "val": VAL_FRACTION * total}
    split_of = {}
    for group, n in sizes.select("group", "len").iter_rows():
        if filled["test"] < targets["test"]:
            split_of[group] = "test"
        elif filled["val"] < targets["val"]:
            split_of[group] = "val"
        else:
            split_of[group] = "train"
        filled[split_of[group]] = filled.get(split_of[group], 0) + n
    return df.with_columns(split=pl.col("group").replace_strict(split_of))


def remove_near_duplicates_of_train(df: pl.DataFrame, stats: dict) -> pl.DataFrame:
    """Step 10: drop val/test sequences whose best training hit is >= 80% identical."""
    train = df.filter(pl.col("split") == "train")
    held_out = df.filter(pl.col("split") != "train")
    identity = best_identity(search(held_out["sequence"].to_list(), train["sequence"].to_list()),
                             held_out.height, min_coverage=NEAR_DUP_COVERAGE)
    near_dup = identity >= NEAR_DUP_IDENTITY                                  # (n_held_out,) bool
    removed = held_out.filter(pl.Series(near_dup))
    stats["10_removed_near_duplicates"] = {
        "val": int((removed["split"] == "val").sum()),
        "test": int((removed["split"] == "test").sum()),
        "by_family": dict(removed.group_by("family").len().sort("len", descending=True).iter_rows()),
    }
    return pl.concat([train, held_out.filter(pl.Series(~near_dup))])


def remove_structural_members_of_train(df: pl.DataFrame, stats: dict) -> pl.DataFrame:
    """Step 11: drop val/test sequences scoring >= GA against a training family's model."""
    ga = gathering_thresholds()
    train = df.filter(pl.col("split") == "train")
    train_families = set(train["family"])
    held_out = df.filter(pl.col("split") != "train").with_row_index("query").with_columns(
        pl.col("query").cast(pl.Int64))
    hits = cmscan(held_out["sequence"].to_list())
    members = hits.filter(
        pl.col("family").is_in(list(train_families)),
        pl.col("score") >= pl.col("family").replace_strict(ga, return_dtype=pl.Float64),
    )
    removed = held_out.join(members.select("query").unique(), on="query", how="semi")
    stats["11_removed_structural_members_of_train"] = {
        "val": int((removed["split"] == "val").sum()),
        "test": int((removed["split"] == "test").sum()),
        "pairs": (removed.join(members, on="query")
                  .group_by(pl.col("family").alias("held_out_family"), pl.col("family_right").alias("train_family"))
                  .agg(pl.col("query").n_unique().alias("n")).sort("n", descending=True).to_dicts()),
    }
    kept = held_out.join(members.select("query").unique(), on="query", how="anti").drop("query")
    return pl.concat([train, kept])


def check_no_leakage_by_construction(df: pl.DataFrame) -> None:
    """Audit check 1 and 2, as hard assertions: the script refuses to write a leaky split."""
    for label in ("group", "family", "clan"):
        per_value = df.drop_nulls(label).group_by(label).agg(pl.col("split").n_unique())
        assert (per_value["split"] == 1).all(), f"some {label} appears in more than one split"
    per_seq = df.group_by("sequence").agg(pl.col("split").n_unique())
    assert (per_seq["split"] == 1).all(), "an identical sequence appears in two splits"


def main() -> None:
    global SPLIT_SEED
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--split-seed", type=int, default=SEED,
                   help="which groups are held out; 0 (default) reproduces the frozen split")
    p.add_argument("--out-dir", type=Path,
                   help="where to write (default: data/processed for seed 0, data/processed_split<k> otherwise)")
    args = p.parse_args()
    SPLIT_SEED = args.split_seed
    out_dir = args.out_dir or (PROCESSED_DIR if SPLIT_SEED == SEED
                               else PROCESSED_DIR.with_name(f"processed_split{SPLIT_SEED}"))
    split_table = "rfam_split.tsv" if SPLIT_SEED == SEED else f"rfam_split_seed{SPLIT_SEED}.tsv"

    stats = {"config": dict(MAX_LEN=MAX_LEN, FRAGMENT_FRACTION=FRAGMENT_FRACTION,
                            PER_FAMILY_CAP=PER_FAMILY_CAP, VAL_FRACTION=VAL_FRACTION,
                            TEST_FRACTION=TEST_FRACTION, SEED=SEED, SPLIT_SEED=SPLIT_SEED,
                            NEAR_DUP_IDENTITY=NEAR_DUP_IDENTITY, NEAR_DUP_COVERAGE=NEAR_DUP_COVERAGE,
                            STRUCTURAL_FILTER="Rfam 15.0 CMs, score >= GA, cmscan --nohmmonly --toponly --rfam")}
    df = remove_near_duplicates_of_train(assign_splits(clean(stats)), stats)
    df = remove_structural_members_of_train(df, stats)
    check_no_leakage_by_construction(df)

    out_dir.mkdir(parents=True, exist_ok=True)
    stats["splits"] = {}
    for split in ("train", "val", "test"):
        part = df.filter(pl.col("split") == split).drop("split").sort("family", "sequence")
        part.write_parquet(out_dir / f"{split}.parquet")
        stats["splits"][split] = dict(
            sequences=part.height, share=round(part.height / df.height, 4),
            families=part["family"].n_unique(), groups=part["group"].n_unique(),
            clans=part["clan"].drop_nulls().n_unique(),
            nucleotides=int(part["length"].sum()), mean_length=round(part["length"].mean(), 1),
            median_length=part["length"].median(),
        )

    table = (df.group_by("family", "clan", "group", "split").len("n_sequences")
             .sort("split", "group", "family"))
    (REPO_ROOT / "splits").mkdir(exist_ok=True)
    table.write_csv(REPO_ROOT / "splits" / split_table, separator="\t")
    largest = df.group_by("group", "split").len().sort("len", descending=True).head(10)
    stats["largest_groups"] = largest.to_dicts()

    with open(out_dir / "prepare_stats.json", "w") as f:
        json.dump(stats, f, indent=2)
    printable = {k: v for k, v in stats.items() if k != "4_dropped_long_families"}
    printable["4_dropped_long_families"] = f"{len(stats['4_dropped_long_families'])} families (list in JSON)"
    print(json.dumps(printable, indent=2))


if __name__ == "__main__":
    main()
