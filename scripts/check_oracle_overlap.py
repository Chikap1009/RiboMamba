"""Has the second oracle (EternaFold) seen our held-out RNA in its own training data? (Phase 3, D-013)

EternaFold's parameters were learned partly from natural RNA structures. If
those included our held-out families, EternaFold would judge them with
"inside knowledge". The bioconda package ships its training FASTA files, so
we search our split against them: exact matches, then MMseqs2 identity at
>= 80 % coverage (the Phase 1 rule).

Usage:  python scripts/check_oracle_overlap.py --split val     (test: only after the protocol freeze)
Output: printed table; data/eval/oracle_overlap_<split>.json
"""

import argparse
import json
import os
from pathlib import Path

import polars as pl

from ribomamba.data.similarity import best_identity, search
from ribomamba.eval.reference import load_split
from ribomamba.paths import EVAL_DIR


def read_fasta_rna(path: Path) -> list[str]:
    seqs, current = [], []
    for line in open(path):
        line = line.strip()
        if line.startswith(">"):
            if current:
                seqs.append("".join(current))
            current = []
        elif line:
            current.append(line)
    if current:
        seqs.append("".join(current))
    return [s.upper().replace("T", "U") for s in seqs]


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--split", required=True, choices=["val", "test"])
    args = p.parse_args()
    held_out = load_split(args.split, ["sequence", "family"])          # refuses test before the freeze
    base = Path(os.environ["CONDA_PREFIX"]) / "lib/eternafold-lib/datasets_in_fasta_form/train_datasets"
    report = {"split": args.split, "exact_matches": {}}
    for f in sorted(base.glob("*.fasta")):
        report["exact_matches"][f.name] = int(held_out["sequence"].is_in(read_fasta_rna(f)).sum())
    oracle = sorted({s for s in read_fasta_rna(base / "All_EternaFold_training_data.fasta") if set(s) <= set("ACGU")})
    identity = best_identity(search(held_out["sequence"].to_list(), oracle), held_out.height, min_coverage=0.8)
    held_out = held_out.with_columns(pl.Series("identity", identity))
    report["n_held_out"], report["n_oracle_training"] = held_out.height, len(oracle)
    for level in (0.5, 0.8, 0.95):
        hit = held_out.filter(pl.col("identity") >= level)
        report[f"ge_{int(level * 100)}"] = {"share": hit.height / held_out.height,
                                            "families": dict(hit.group_by("family").len().rows())}
    EVAL_DIR.mkdir(parents=True, exist_ok=True)
    (EVAL_DIR / f"oracle_overlap_{args.split}.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
