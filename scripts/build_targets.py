"""Design target sets for the Phase 5 evaluation, built by a rule fixed in Phase 3.

Two target sets per held-out split (logbook 2026-09-24 session 04, "target
rule"; STUDY_GUIDE Part 5):

  rfam   One native sequence per held-out family, chosen at random (seed);
         the target is that native's ViennaRNA MFE structure; kept if it has
         >= 4 base pairs. Solvable by construction: the native itself is a
         solution, so its scores are a positive control ("native recovery").
         No quality filter: picking natives that fold well would pick easy targets.

  bprna  bpRNA-1m structures (comparative / experimental annotations, not
         predicted by our oracle) that pass, in order:
           letters    A/C/G/U only; 19-256 nt (our training range); distinct;
                      not letter-for-letter in train
           structure  only '(' ')' '.' (no pseudoknot brackets); every pair
                      canonical (GC, AU, GU); hairpin loops >= 3; >= 4 pairs.
                      (A non-canonical pair can never be formed by ViennaRNA,
                      so such a target is unreachable.)
           family     a member (score >= GA, Rfam 15.0 cmscan, the step-11
                      flags) of at least one family of THIS split, and
             leakage  not a member of any TRAIN family, no family in a clan
                      that contains a train family, not a member of a family
                      dropped as too long (D-007: pieces of long RNAs), and no
                      MMseqs2 hit in train at >= 80 % identity over >= 80 %
                      coverage (step 10's rule)
         Sequences Rfam assigns to no family are dropped: their held-out
         status can't be defined at the level our split uses.
         Then one target per family (seeded), like the rfam set.

  eterna100  (test only: an external, evaluation-only set) the Eterna100 V2
         puzzles of <= 256 nt (75 of 100), pinned in scripts/download_data.py;
         the benchmark's ViennaRNA-2 sample solution is the "native".

Usage: python scripts/build_targets.py --split val    (test: refused until the protocol freeze)
Output: data/targets/{rfam,bprna}_<split>.parquet (+ eterna100_test.parquet) and
        <split>_funnel.json; SHA-256s printed.
"""

import argparse
import hashlib
import json

import numpy as np
import polars as pl

from ribomamba.data.similarity import best_identity, search
from ribomamba.data.structure_search import cmscan, gathering_thresholds
from ribomamba.eval.folding import check_target, fold_many
from ribomamba.eval.protocol import git_commit, require_frozen
from ribomamba.eval.reference import load_split
from ribomamba.paths import DATA_DIR, PROCESSED_DIR, RAW_DIR, REPO_ROOT

TARGETS_DIR = DATA_DIR / "targets"
MIN_PAIRS = 4
MIN_LEN, MAX_LEN = 19, 256          # the training split's range


def one_per_family(table: pl.DataFrame, seed: int) -> pl.DataFrame:
    """One random row per family: families visited in sorted order, rows sorted by sequence first."""
    rng = np.random.default_rng(seed)
    table = table.sort(["family", "sequence"])
    picks = [group.row(int(rng.integers(group.height)), named=True)
             for _, group in table.group_by("family", maintain_order=True)]
    return pl.DataFrame(picks, schema=table.schema)


def rfam_targets(split: str, seed: int) -> tuple[pl.DataFrame, dict]:
    natives = one_per_family(load_split(split, ["sequence", "family", "length"]), seed)
    folded = fold_many(natives["sequence"].to_list(), n_shuffles=0)
    table = natives.with_columns(pl.Series("target", folded["mfe_structure"].to_list()))
    table = table.with_columns(pl.col("target").str.count_matches(r"\(").alias("pairs"))
    funnel = {"families": natives.height}
    table = table.filter(pl.col("pairs") >= MIN_PAIRS)
    funnel[f">= {MIN_PAIRS} pairs"] = table.height
    return table, funnel


def _valid(sequence: str, structure: str) -> bool:
    try:
        check_target(sequence, structure)
        return True
    except ValueError:
        return False


def bprna_targets(split: str, seed: int) -> tuple[pl.DataFrame, dict]:
    b = pl.read_parquet(RAW_DIR / "bprna" / "data.parquet").with_columns(
        pl.col("sequence").str.to_uppercase().str.replace_all("T", "U"),
        pl.col("id").str.extract(r"bpRNA_([A-Za-z]+)_", 1).alias("source"),
        pl.col("secondary_structure").alias("target"))
    funnel = {"bpRNA-1m": b.height}

    def step(name, table):
        funnel[name] = table.height
        return table
    b = step("A/C/G/U only", b.filter(pl.col("sequence").str.contains(r"^[ACGU]+$")))
    b = step(f"{MIN_LEN}-{MAX_LEN} nt", b.filter(pl.col("sequence").str.len_chars().is_between(MIN_LEN, MAX_LEN)))
    b = step("no pseudoknot brackets", b.filter(~pl.col("target").str.contains(r"[^().]")))
    b = step("canonical pairs, hairpins >= 3", b.filter(
        pl.struct(["sequence", "target"]).map_elements(lambda r: _valid(r["sequence"], r["target"]),
                                                       return_dtype=pl.Boolean)))
    b = step(f">= {MIN_PAIRS} pairs", b.filter(pl.col("target").str.count_matches(r"\(") >= MIN_PAIRS))
    b = step("distinct sequences", b.sort("id").unique("sequence", keep="first", maintain_order=True))
    train = load_split("train", ["sequence", "family", "clan"])
    b = step("not letter-for-letter in train", b.filter(~pl.col("sequence").is_in(train["sequence"].implode())))

    # Family membership by Rfam's own models (same flags and GA rule as step 11).
    ga = gathering_thresholds()
    hits = cmscan(b["sequence"].to_list())
    members = (hits.filter(pl.col("score") >= pl.col("family").replace_strict(ga, return_dtype=pl.Float64))
               .group_by("query").agg(pl.col("family").sort_by("score", descending=True)))
    b = b.with_row_index("query").join(members, on="query", how="left").drop("query")
    b = b.with_columns(pl.col("family").fill_null([]))

    split_table = pl.read_csv(REPO_ROOT / "splits" / "rfam_split.tsv", separator="\t")
    family_split = dict(zip(split_table["family"], split_table["split"]))
    clan_of = {}
    for line in open(RAW_DIR / "rfam_clanin" / "Rfam.clanin"):
        clan, *families = line.rstrip("\n").split("\t")
        clan_of.update({f: clan for f in families})
    train_families = set(train["family"].unique())
    train_clans = {clan_of[f] for f in train_families if f in clan_of}
    long_families = set(json.loads((PROCESSED_DIR / "prepare_stats.json").read_text())["4_dropped_long_families"])

    def verdict(families) -> str:
        families = list(families)                  # polars passes each row's list as a Series
        if not families:
            return "no family"
        if any(f in train_families for f in families):
            return "member of a train family"
        if any(clan_of.get(f) in train_clans for f in families):
            return "family in a train clan"
        if any(f in long_families for f in families):
            return "long family (fragment)"
        splits = {family_split.get(f) for f in families} - {None}
        if len(splits) > 1:
            return "families in two splits"
        return splits.pop() if splits else "family outside our data"
    b = b.with_columns(pl.col("family").map_elements(verdict, return_dtype=pl.String).alias("verdict"))
    funnel["verdicts"] = dict(b.group_by("verdict").len().sort("verdict").rows())
    b = step(f"member of a {split} family", b.filter(pl.col("verdict") == split))

    identity = best_identity(search(b["sequence"].to_list(), train["sequence"].to_list()), b.height)
    b = step("no >= 80 % identity train hit", b.filter(pl.Series(identity < 0.8)))
    b = b.with_columns(pl.col("family").list.first(), pl.col("sequence").str.len_chars().alias("length"))
    b = step("one per family", one_per_family(b, seed))
    return b.select(["id", "source", "family", "sequence", "length", "target"]), funnel


def eterna100_targets(split: str, seed: int) -> tuple[pl.DataFrame, dict]:
    """Eterna100 V2 puzzles of <= 256 nt: an external, EVALUATION-ONLY set (never used for tuning),
    so it is built together with the test sets. Its 'native' is the benchmark's sample solution for
    ViennaRNA 2 (a known answer: all 75 fold to their target under ViennaRNA 2.7.2)."""
    t = pl.read_csv(RAW_DIR / "eterna100" / "eterna100_puzzles.tsv", separator="\t")
    funnel = {"Eterna100": t.height}
    t = t.select(pl.col("Puzzle #").cast(pl.String).alias("id"), pl.col("Puzzle Name").alias("family"),
                 pl.col("Sample Solution (V2/Vienna2)").alias("sequence"),
                 pl.col("Secondary Structure V2").alias("target"))
    t = t.filter(pl.col("target").str.len_chars() <= MAX_LEN)
    funnel[f"<= {MAX_LEN} nt"] = t.height
    for s, target in zip(t["sequence"], t["target"]):
        check_target(s, target)                    # every target reachable (its sample solution proves it)
    return t.with_columns(pl.col("sequence").str.len_chars().alias("length")), funnel


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--split", required=True, choices=["val", "test"])
    p.add_argument("--seed", type=int, default=0)
    args = p.parse_args()
    require_frozen(args.split)                      # test targets are built only after the freeze

    TARGETS_DIR.mkdir(parents=True, exist_ok=True)
    report = {"command": f"python scripts/build_targets.py --split {args.split} --seed {args.seed}",
              "git_commit": git_commit()}
    sets = [("rfam", rfam_targets), ("bprna", bprna_targets)]
    if args.split == "test":
        sets.append(("eterna100", eterna100_targets))
    for name, build in sets:
        table, funnel = build(args.split, args.seed)
        # The native sequence scored against its own target: the positive control.
        native = fold_many(table["sequence"].to_list(), targets=table["target"].to_list(), n_shuffles=0)
        table = table.with_columns([pl.Series(f"native_{c}", native[c].to_list())
                                    for c in ("mfe_match", "p_target", "ned_target", "energy_gap")])
        path = TARGETS_DIR / f"{name}_{args.split}.parquet"
        table.write_parquet(path)
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        report[name] = {"funnel": funnel, "n_targets": table.height, "sha256": digest,
                        "native_mfe_match": float(table["native_mfe_match"].mean()),
                        "native_ned_median": float(table["native_ned_target"].median()),
                        "length_median": float(table["length"].median())}
        print(f"{name}_{args.split}: {table.height} targets, sha256 {digest}")
        print(json.dumps(report[name], indent=2))
    (TARGETS_DIR / f"{args.split}_funnel.json").write_text(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
