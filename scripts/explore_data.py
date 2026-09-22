"""Measure the raw data before deciding how to clean it (Phase 1).

Every cleaning threshold in scripts/prepare_data.py (length cap, per-family
cap, what counts as a valid letter) was chosen from the numbers this prints.
Re-run it to reproduce them.

Usage:  python scripts/explore_data.py
"""

import polars as pl

from ribomamba.paths import RAW_DIR

QUANTILES = [0.01, 0.10, 0.50, 0.90, 0.99]


def length_summary(lengths: pl.Series) -> str:
    qs = ", ".join(f"p{int(q * 100)}={lengths.quantile(q):.0f}" for q in QUANTILES)
    return f"min={lengths.min()}, {qs}, max={lengths.max()}"


PLACEHOLDER_FAMILY = "No such family"


def check_rfam_duplication() -> None:
    """The HF copy of Rfam contains every row twice (found in session 03).

    The second copy has family = "No such family". This proves every such row
    has a twin with a real family and the identical sequence, so dropping the
    placeholder rows loses nothing.
    """
    lf = pl.scan_parquet(RAW_DIR / "rfam" / "data.parquet").select("id", "sequence", "family")
    real = lf.filter(pl.col("family") != PLACEHOLDER_FAMILY)
    placeholder = lf.filter(pl.col("family") == PLACEHOLDER_FAMILY)
    twins = placeholder.join(real, on="id", how="left").select(
        pl.len().alias("placeholder_rows_after_join"),
        pl.col("family_right").is_null().sum().alias("without_real_twin"),
        (pl.col("sequence") != pl.col("sequence_right")).sum().alias("sequence_differs_from_twin"),
    ).collect()
    print(f"'{PLACEHOLDER_FAMILY}' rows: {placeholder.select(pl.len()).collect().item():,}")
    print(f"  checked against their twins: {twins.to_dicts()[0]}")
    repeated = real.group_by("id").len().filter(pl.col("len") > 1).select(pl.len()).collect().item()
    print(f"genome regions filed under two real families: {repeated}")


def explore_rfam() -> None:
    print("=" * 70, "\nRfam (multimolecule/rfam, full regions)\n" + "=" * 70)
    check_rfam_duplication()
    print("--- everything below: placeholder rows removed ---")
    # Lazy scan: polars reads only the columns we name, not the 5.9 GB of text in `description`.
    # The original `sequence` column is dropped as soon as it has been
    # normalised, so only one ~3 GB copy of the text is ever in memory.
    df = (
        pl.scan_parquet(RAW_DIR / "rfam" / "data.parquet")
        .filter(pl.col("family") != PLACEHOLDER_FAMILY)
        .select(
            pl.col("sequence").str.contains("[a-z]").alias("had_lowercase"),
            pl.col("sequence").str.to_uppercase().str.replace_all("T", "U").alias("seq"),
            "family", "clan",
        )
        .with_columns(length=pl.col("seq").str.len_bytes())
        .collect(engine="streaming")
    )
    n = df.height
    print(f"rows: {n:,}")
    print(f"families: {df['family'].n_unique():,}   clans: {df['clan'].drop_nulls().n_unique():,}")
    fam_clan = df.select("family", "clan").unique()
    print(f"families belonging to a clan: {fam_clan['clan'].is_not_null().sum():,} of {fam_clan.height:,}")
    print(f"families listed under >1 clan: {(fam_clan.group_by('family').len()['len'] > 1).sum()}")
    print(f"sequences containing lowercase letters: {df['had_lowercase'].sum():,}")

    # Letters: after upper-casing and T->U, what is left besides A, C, G, U?
    non_acgu = df.filter(~pl.col("seq").str.contains("^[ACGU]+$"))
    print(f"sequences with any non-ACGU letter: {non_acgu.height:,} ({non_acgu.height / n:.3%})")
    other = (
        non_acgu.select(pl.col("seq").str.replace_all("[ACGU]", "").str.split("").explode(empty_as_null=True))
        .filter(pl.col("seq") != "")
        .group_by("seq").len().sort("len", descending=True)
    )
    print("  which other letters (count of occurrences):", dict(other.head(12).iter_rows()))

    print(f"lengths over all rows: {length_summary(df['length'])}")
    fam_len = df.group_by("family").agg(pl.col("length").median().alias("median_len"), pl.len().alias("n"))
    for cap in (128, 200, 256, 384, 512, 1024):
        fams = (fam_len["median_len"] <= cap).sum()
        rows = (df["length"] <= cap).sum()
        print(f"  cap {cap:>4}: keeps {fams / fam_len.height:6.1%} of families (by median length), "
              f"{rows / n:6.1%} of rows")

    sizes = fam_len["n"]
    print(f"family sizes: {length_summary(sizes)}")
    print("  largest families:", dict(fam_len.sort("n", descending=True).head(8).select("family", "n").iter_rows()))
    for k in (100, 500, 1000, 5000):
        kept = sizes.clip(upper_bound=k).sum()
        print(f"  cap {k:>5} per family -> at most {kept:,} rows")

    # Duplicates: identical sequences within a family, and the same sequence under two families.
    uniq = df.select("seq", "family").unique()
    print(f"unique (sequence, family) pairs: {uniq.height:,}  (exact duplicates removed: {n - uniq.height:,})")
    multi = uniq.group_by("seq").agg(pl.col("family").n_unique().alias("n_fam")).filter(pl.col("n_fam") > 1)
    print(f"distinct sequences filed under >1 family: {multi.height:,}")


def explore_bprna() -> None:
    print("=" * 70, "\nbpRNA-1m (multimolecule/bprna)\n" + "=" * 70)
    df = pl.read_parquet(RAW_DIR / "bprna" / "data.parquet").with_columns(
        length=pl.col("sequence").str.len_bytes(),
        source=pl.col("id").str.extract(r"^bpRNA_([A-Za-z]+)_"),
        pseudoknot=pl.col("secondary_structure").str.contains(r"[\[\]{}<>]"),
    )
    print(f"rows: {df.height:,}")
    print("by source database:", dict(df.group_by("source").len().sort("len", descending=True).iter_rows()))
    print(f"lengths: {length_summary(df['length'])}")
    print(f"non-ACGU sequences: {(~df['sequence'].str.contains('^[ACGU]+$')).sum():,}")
    print(f"structures containing pseudoknot brackets: {df['pseudoknot'].sum():,} ({df['pseudoknot'].mean():.1%})")
    print(f"length <= 256 and no pseudoknot: {df.filter((pl.col('length') <= 256) & ~pl.col('pseudoknot')).height:,}")


if __name__ == "__main__":
    explore_rfam()
    explore_bprna()
