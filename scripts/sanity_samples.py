"""Quick sanity checks on generated sequences (end of Phase 2; NOT the Phase 3 protocol).

Compares N generated sequences with N real VALIDATION sequences (unseen
families) on four questions:
  1. copying:     how close is each sequence to its nearest TRAINING sequence (MMseqs2)?
  2. composition: GC content, and exact duplicates among the generated set.
  3. foldability: minimum free energy per nucleotide (ViennaRNA) and the
                  fraction of paired positions.
  4. "more structured than chance?": each sequence's MFE minus the MFE of
                  a dinucleotide-shuffled copy of itself. Real structural
                  RNAs tend to fold more stably than their shuffles
                  (negative difference); random sequences don't.
Everything here is a preview on validation data; thresholds and the real
evaluation are frozen in Phase 3 before any test-set use.

Usage:  python scripts/sanity_samples.py --samples samples/tf_M_do0.fasta
Output: printed table + data/processed/sanity_<name>.json
"""

import argparse
import json
from pathlib import Path

import numpy as np
import polars as pl
import RNA

from ribomamba.data.similarity import best_identity, search
from ribomamba.data.structure_search import dinucleotide_shuffle
from ribomamba.paths import PROCESSED_DIR


def read_fasta(path: Path) -> list[str]:
    return [line.strip() for line in open(path) if line.strip() and not line.startswith(">")]


def describe(seqs: list[str], train: list[str], rng: np.random.Generator) -> dict:
    identity = best_identity(search(seqs, train), len(seqs), min_coverage=0.8)            # (n,)
    folds = [RNA.fold(s) for s in seqs]                                                    # (structure, mfe)
    mfe_per_nt = np.array([mfe / len(s) for (_, mfe), s in zip(folds, seqs)])
    paired = np.array([1 - st.count(".") / len(st) for st, _ in folds])
    shuffled_mfe = np.array([RNA.fold(dinucleotide_shuffle(s, rng))[1] for s in seqs])
    delta = np.array([mfe for _, mfe in folds]) - shuffled_mfe                              # kcal/mol
    gc = np.array([(s.count("G") + s.count("C")) / len(s) for s in seqs])
    return {
        "n": len(seqs),
        "distinct_sequences": len(set(seqs)),
        "median_length": float(np.median([len(s) for s in seqs])),
        "train_relative_ge_50pct_identity": round(float((identity >= 0.5).mean()), 4),
        "train_relative_ge_90pct_identity": round(float((identity >= 0.9).mean()), 4),
        "train_relative_ge_99pct_identity": round(float((identity >= 0.99).mean()), 4),
        "gc_content_mean": round(float(gc.mean()), 4),
        "mfe_per_nt_mean": round(float(mfe_per_nt.mean()), 4),
        "paired_fraction_mean": round(float(paired.mean()), 4),
        "mfe_minus_shuffled_mean_kcal": round(float(delta.mean()), 3),
        "share_more_stable_than_shuffle": round(float((delta < 0).mean()), 4),
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--samples", required=True, type=Path)
    p.add_argument("--seed", type=int, default=0)
    args = p.parse_args()
    rng = np.random.default_rng(args.seed)

    generated = read_fasta(args.samples)
    train = pl.read_parquet(PROCESSED_DIR / "train.parquet", columns=["sequence"])["sequence"].to_list()
    val = pl.read_parquet(PROCESSED_DIR / "val.parquet", columns=["sequence"])["sequence"]
    real = val.sample(len(generated), seed=args.seed).to_list()

    report = {"generated": describe(generated, train, rng), "real_validation": describe(real, train, rng)}
    out = PROCESSED_DIR / f"sanity_{args.samples.stem}.json"
    out.write_text(json.dumps(report, indent=2))
    keys = report["generated"].keys()
    print(f"{'':36}{'generated':>12}{'real (val)':>12}")
    for k in keys:
        print(f"{k:36}{report['generated'][k]:>12}{report['real_validation'][k]:>12}")
    print(f"-> {out}")


if __name__ == "__main__":
    main()
