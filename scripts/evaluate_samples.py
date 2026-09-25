"""Evaluate generated sequences against the reference sets: the Phase 3 harness.

Every generated set is measured next to five reference sets of the same
lengths (ribomamba/eval/reference.py): real held-out RNA, a second real
sample (noise floor), length-matched training RNA, dinucleotide-shuffled
real RNA, and uniform random letters. The reference sets are computed once
per (split, n, seed) and cached.

Usage:
    python scripts/evaluate_samples.py                        # build + print the validation references
    python scripts/evaluate_samples.py --samples samples/x.fasta
Generate matching samples first with
    python scripts/sample.py ... --lengths-from val --lengths-n 1000 --lengths-seed 0

Outputs (data/eval/, not in Git):
    reference_<split>_n<n>_s<seed>.parquet   per-sequence metrics of the reference sets
    <name>.parquet                           per-sequence metrics of the samples
    <name>.json                              summaries with 95 % intervals, distances to `real`, provenance
The test split refuses to load until the protocol is frozen (ribomamba/eval/protocol.py).
"""

import argparse
import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path

import polars as pl

from ribomamba.eval.harness import distances, per_sequence, summarise
from ribomamba.eval.protocol import frozen_date, git_commit
from ribomamba.eval.reference import load_split, reference_sets
from ribomamba.paths import EVAL_DIR, PROCESSED_DIR, REPO_ROOT

SHOW = ["gc", "mfe_per_nt", "paired_fraction", "p_mfe", "ned_mfe", "mfe_z", "beats_shuffles",
        "ef_ned_own", "ef_ned_vienna", "oracles_agree", "stems_per_100nt", "multiloops_per_100nt",
        "sibling_ge_80", "train_relative_ge_50"]


def read_fasta(path: Path) -> list[str]:
    return [line.strip() for line in open(path) if line.strip() and not line.startswith(">")]


def sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def reference_name(split: str, n: int, seed: int, data_dir: Path) -> str:
    """reference_<split>_n<n>_s<seed> for the frozen split; the data folder's name is added for any other."""
    where = "" if data_dir == PROCESSED_DIR else f"{data_dir.name}_"
    return f"reference_{where}{split}_n{n}_s{seed}"


def reference_tables(split: str, n: int, seed: int, train: list[str], processes, data_dir: Path) -> pl.DataFrame:
    path = EVAL_DIR / f"{reference_name(split, n, seed, data_dir)}.parquet"
    if path.exists():
        return pl.read_parquet(path)
    tables = []
    for name, seqs in reference_sets(split, n, seed, data_dir).items():
        print(f"  reference set {name}: {len(seqs)} sequences", flush=True)
        tables.append(per_sequence(seqs, train, seed=seed, processes=processes).with_columns(pl.lit(name).alias("set")))
    table = pl.concat(tables)
    EVAL_DIR.mkdir(parents=True, exist_ok=True)
    table.write_parquet(path)
    return table


def fmt(entry) -> str:
    if isinstance(entry, dict):
        return f"{entry['mean']:.3f} [{entry['low']:.3f}, {entry['high']:.3f}]"
    return f"{entry:.3f}"


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--samples", type=Path, help="FASTA of generated sequences (omit to build references only)")
    p.add_argument("--name", help="output name (default: the FASTA's file name)")
    p.add_argument("--split", default="val", choices=["val", "test"])
    p.add_argument("--n", type=int, default=1000, help="reference sequences per set")
    p.add_argument("--seed", type=int, default=0, help="reference selection, shuffles, bootstrap")
    p.add_argument("--processes", type=int)
    p.add_argument("--data-dir", default="data/processed",
                   help="split folder, relative to the repo root (data/processed_split1 = replication split, P4)")
    args = p.parse_args()
    data_dir = (REPO_ROOT / args.data_dir).resolve()

    train = load_split("train", ["sequence"], data_dir)["sequence"].to_list()     # novelty is judged against THIS train
    ref = reference_tables(args.split, args.n, args.seed, train, args.processes, data_dir)
    real = ref.filter(pl.col("set") == "real")
    report = {
        "provenance": {"command": " ".join(sys.argv), "git_commit": git_commit(), "date": datetime.now().isoformat(
            timespec="seconds"), "split": args.split, "n": args.n, "seed": args.seed,
            "data_dir": args.data_dir, "protocol_frozen_on": frozen_date()},
        "reference": {},
    }
    columns = {}
    for name in ["real", "real2", "train", "shuffled", "random"]:
        t = ref.filter(pl.col("set") == name)
        report["reference"][name] = {"summary": summarise(t, args.seed), "distance_to_real": distances(t, real)}
        columns[name] = report["reference"][name]["summary"]

    if args.samples:
        name = args.name or args.samples.stem
        generated = read_fasta(args.samples)
        lengths_match = [len(s) for s in generated] == real["length"].to_list()
        if not lengths_match:
            print("WARNING: sample lengths are not matched to the real reference, so length confounds every "
                  "comparison; generate with scripts/sample.py --lengths-from", args.split)
        table = per_sequence(generated, train, seed=args.seed, processes=args.processes)
        EVAL_DIR.mkdir(parents=True, exist_ok=True)
        table.write_parquet(EVAL_DIR / f"{name}.parquet")
        report["samples"] = {"name": name, "file": str(args.samples), "sha256": sha256(args.samples),
                             "length_matched_to_real": lengths_match,
                             "summary": summarise(table, args.seed), "distance_to_real": distances(table, real)}
        columns[name] = report["samples"]["summary"]
        out = EVAL_DIR / f"{name}.json"
    else:
        out = EVAL_DIR / f"{reference_name(args.split, args.n, args.seed, data_dir)}.json"
    out.write_text(json.dumps(report, indent=2))

    width = 28
    print(f"{'metric (mean [95% CI])':24}" + "".join(f"{c:>{width}}" for c in columns))
    for metric in SHOW:
        print(f"{metric:24}" + "".join(f"{fmt(columns[c][metric]):>{width}}" if metric in columns[c] else " " * width
                                       for c in columns))
    print(f"-> {out}")


if __name__ == "__main__":
    main()
