"""Sequence similarity search with MMseqs2 (used by the split and by its audit).

MMseqs2 is a fast relative of BLAST: for each query sequence it finds the
target sequences that share a statistically significant stretch of letters,
aligns them, and reports how similar they are.
"""

import os
import subprocess
import tempfile
from pathlib import Path

import numpy as np
import polars as pl


def _write_fasta(sequences: list[str], path: Path) -> None:
    """FASTA: the standard text format for sequences, a '>name' line then the letters.

    MMseqs2's nucleotide alphabet is DNA (A, C, G, T), so U is written as T.
    Nothing about similarity changes: it's the same letter renamed.
    """
    with open(path, "w") as f:
        for i, seq in enumerate(sequences):
            f.write(f">{i}\n{seq.replace('U', 'T')}\n")


def search(queries: list[str], targets: list[str]) -> pl.DataFrame:
    """Every significant hit (E-value <= 1e-3, MMseqs2's default) of each query among the targets.

    Returns one row per (query, target) hit:
        query, target  indices into the two input lists
        fident         fraction of identical letters in the aligned stretch (0-1)
        qcov           fraction of the query covered by the alignment (0-1)
        evalue         expected number of hits this good by pure chance
    """
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        _write_fasta(queries, tmp / "queries.fasta")
        _write_fasta(targets, tmp / "targets.fasta")
        subprocess.run(
            ["mmseqs", "easy-search", tmp / "queries.fasta", tmp / "targets.fasta",
             tmp / "hits.tsv", tmp / "work",
             "--search-type", "3",        # nucleotide vs nucleotide; forward strand only (the default),
                                          # because every RNA is stored in its own 5'->3' direction
             "--format-output", "query,target,fident,qcov,evalue",
             "--threads", str(os.cpu_count()), "-v", "1"],
            check=True,
        )
        schema = {"query": pl.Int64, "target": pl.Int64, "fident": pl.Float64,
                  "qcov": pl.Float64, "evalue": pl.Float64}
        if (tmp / "hits.tsv").stat().st_size == 0:          # no query had any hit: a valid result
            return pl.DataFrame(schema=schema)
        return pl.read_csv(tmp / "hits.tsv", separator="\t", has_header=False,
                           new_columns=list(schema), schema_overrides=schema)


def best_identity(hits: pl.DataFrame, n_queries: int, min_coverage: float = 0.8) -> np.ndarray:
    """Per query: identity of its best hit that covers >= min_coverage of it; 0.0 if none.

    The coverage condition stops a short shared motif (say 15 letters of a
    150-letter RNA) from counting as "the same sequence".
    """
    identity = np.zeros(n_queries)                                                      # (n_queries,)
    best = hits.filter(pl.col("qcov") >= min_coverage).group_by("query").agg(pl.col("fident").max())
    identity[best["query"].to_numpy()] = best["fident"].to_numpy()
    return identity
