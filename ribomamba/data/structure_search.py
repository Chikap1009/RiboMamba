"""Structure-aware homology search: Infernal's cmscan against Rfam 15.0's family models.

MMseqs2 (similarity.py) compares letters. A covariance model (CM) also knows
which positions must pair, and accepts any complementary pair there, so it
recognises relatives whose letters drifted apart by covariation. This is the
tool Rfam itself uses to decide family membership (D-009).
"""

import gzip
import hashlib
import shutil
import subprocess
import os
from pathlib import Path

import numpy as np
import polars as pl

from ribomamba.paths import PROCESSED_DIR, RAW_DIR

CM_GZ = RAW_DIR / "rfam_cm" / "Rfam.cm.gz"
CM = RAW_DIR / "rfam_cm" / "Rfam.cm"
CACHE_DIR = PROCESSED_DIR / "cmscan_cache"


def prepare_cm_database() -> None:
    """Decompress Rfam.cm and build cmscan's index files (.i1m/.i1i/.i1f/.i1p), once."""
    if not CM.exists():
        with gzip.open(CM_GZ, "rb") as src, open(CM, "wb") as dst:
            shutil.copyfileobj(src, dst)
    if not Path(f"{CM}.i1m").exists():
        subprocess.run(["cmpress", "-F", CM], check=True, stdout=subprocess.DEVNULL)


def gathering_thresholds() -> dict[str, float]:
    """Family name -> GA bit score, read from the model file.

    GA ("gathering") is the curator-set cutoff: Rfam's full member lists are
    exactly the hits scoring >= GA. So "scores >= GA against family F" means
    "Rfam would call this sequence a member of F".
    """
    ga, name = {}, None
    with open(CM) as f:
        for line in f:
            if line.startswith("NAME "):
                name = line.split()[1]
            elif line.startswith("GA ") and name is not None:
                ga[name] = float(line.split()[1])
                name = None     # each model has a CM part and an HMM part; take GA once
    return ga


# Explicit column types: a scan with zero hits (the expected outcome for
# shuffled sequences) must still give a table whose columns can be joined on.
HIT_SCHEMA = {"seq_hash": pl.String, "family": pl.String, "score": pl.Float64,
              "evalue": pl.Float64, "seq_from": pl.Int64, "seq_to": pl.Int64}
CHUNK = 2000   # sequences per cmscan call; each finished chunk is saved at once


def _sequence_hash(sequence: str) -> str:
    return hashlib.sha256(sequence.encode()).hexdigest()[:32]


def _run_cmscan(named: dict[str, str], flags: list[str], workdir: Path) -> pl.DataFrame:
    """One cmscan call on {name: sequence}; returns its hits as a table."""
    fasta, table = workdir / "chunk.fasta", workdir / "chunk.tbl"
    fasta.write_text("".join(f">{name}\n{seq}\n" for name, seq in named.items()))
    subprocess.run(["cmscan", "--cpu", str(os.cpu_count()), *flags, "--tblout", table,
                    "--fmt", "2", "-o", os.devnull, CM, fasta], check=True)
    rows = []
    with open(table) as f:
        for line in f:
            if line.startswith("#"):
                continue
            fields = line.split(maxsplit=26)
            # --fmt 2 columns used: 1 model name, 3 query name, 9/10 sequence
            # coordinates, 16 bit score, 17 E-value (see Infernal user guide, tblout)
            rows.append((fields[3], fields[1], float(fields[16]), float(fields[17]),
                         int(fields[9]), int(fields[10])))
    return pl.DataFrame(rows, schema=HIT_SCHEMA, orient="row")


def cmscan(sequences: list[str], sensitive_filters: bool = False) -> pl.DataFrame:
    """Score every sequence against every Rfam model; return hits with E-value <= 0.01.

    Flags, following Rfam's own genome-annotation recipe:
      --nohmmonly  score EVERY model as a full covariance model. Without it,
                   cmscan quietly scores the 347 models that have zero base
                   pairs with a letters-only HMM, whose bit scores are not on
                   the scale their GA thresholds were set on (session 03 bug).
      --toponly    search each RNA only in its own 5'->3' direction.
      --rfam       Rfam's faster pre-filters (default here). With
                   sensitive_filters=True, Infernal's default filters are
                   used instead: ~11x slower, more sensitive to weak hits.

    Cache: a sequence's hits depend only on that sequence (checked: its
    E-values are identical whether scanned alone or in a batch), so results
    are stored PER SEQUENCE under data/processed/cmscan_cache/<flags>/. Only
    sequences never scanned before with these flags are sent to cmscan, in
    chunks of CHUNK, and each chunk is saved as soon as it finishes: an
    interrupted multi-hour run loses at most one chunk.

    Returns one row per hit: query (index into `sequences`), family, score
    (bits), evalue, seq_from, seq_to.
    """
    prepare_cm_database()
    flags = ["--nohmmonly", "--toponly", "-E", "0.01"] + ([] if sensitive_filters else ["--rfam"])
    flags_key = hashlib.sha256((" ".join(flags) + CM_GZ.name + str(CM_GZ.stat().st_size))
                               .encode()).hexdigest()[:12]
    cache = CACHE_DIR / flags_key
    cache.mkdir(parents=True, exist_ok=True)
    scanned_file, hits_file = cache / "scanned.parquet", cache / "hits.parquet"
    (cache / "flags.txt").write_text(" ".join(flags) + "\n")   # human-readable record of the key

    scanned = (set(pl.read_parquet(scanned_file)["seq_hash"]) if scanned_file.exists() else set())
    hashes = [_sequence_hash(s) for s in sequences]
    todo = {h: s for h, s in zip(hashes, sequences) if h not in scanned}   # dict: also de-duplicates
    todo_items = list(todo.items())
    for start in range(0, len(todo_items), CHUNK):
        chunk = dict(todo_items[start:start + CHUNK])
        new_hits = _run_cmscan(chunk, flags, cache)
        old_hits = pl.read_parquet(hits_file) if hits_file.exists() else pl.DataFrame(schema=HIT_SCHEMA)
        scanned |= set(chunk)
        # write to temporary files, then rename: a crash mid-write can't corrupt the cache
        pl.concat([old_hits, new_hits]).write_parquet(cache / "hits.tmp")
        pl.DataFrame({"seq_hash": sorted(scanned)}).write_parquet(cache / "scanned.tmp")
        (cache / "hits.tmp").rename(hits_file)
        (cache / "scanned.tmp").rename(scanned_file)
        print(f"  cmscan {flags_key}: {min(start + CHUNK, len(todo_items)):,}/{len(todo_items):,} "
              f"new sequences scanned", flush=True)
    for leftover in ("chunk.fasta", "chunk.tbl"):
        (cache / leftover).unlink(missing_ok=True)

    hits = pl.read_parquet(hits_file) if hits_file.exists() else pl.DataFrame(schema=HIT_SCHEMA)
    queries = pl.DataFrame({"query": range(len(sequences)), "seq_hash": hashes},
                           schema={"query": pl.Int64, "seq_hash": pl.String})
    return queries.join(hits, on="seq_hash", how="inner").drop("seq_hash").sort("query")


def dinucleotide_shuffle(sequence: str, rng: np.random.Generator) -> str:
    """Random sequence with exactly the same dinucleotide counts (Altschul & Erickson 1985).

    Why dinucleotides: RNA folding energy comes from stacking of NEIGHBOURING
    pairs, so a null model must keep which letter follows which, or it would
    be unrealistically easy to tell real sequences from shuffled ones.

    How: treat each letter as a node and each adjacent pair (x -> y) as an
    edge. The sequence is a walk that uses every edge exactly once. Any
    other such walk from the same first letter has the same dinucleotide
    counts. We pick one at random:
      1. for every letter except the final one, choose at random which of its
         outgoing edges it uses LAST; these "last edges" must lead, letter by
         letter, to the final letter (otherwise the walk would get stuck), so
         retry until they do;
      2. shuffle each letter's other outgoing edges, put its last edge at the end;
      3. walk from the first letter, always taking the next unused edge.
    """
    if len(sequence) < 3:
        return sequence
    first, final = sequence[0], sequence[-1]
    edges: dict[str, list[str]] = {}
    for x, y in zip(sequence, sequence[1:]):
        edges.setdefault(x, []).append(y)

    while True:
        last = {x: out[rng.integers(len(out))] for x, out in edges.items() if x != final}
        ok = True
        for x in last:                              # does following last edges from x reach `final`?
            seen, node = set(), x
            while node != final:
                if node in seen:                    # went round in a circle: invalid choice
                    ok = False
                    break
                seen.add(node)
                node = last[node]
            if not ok:
                break
        if ok:
            break

    order = {}
    for x, out in edges.items():
        rest = list(out)
        if x in last:
            rest.remove(last[x])
        rest = [rest[i] for i in rng.permutation(len(rest))]
        order[x] = rest + ([last[x]] if x in last else [])

    walk, node, used = [first], first, {x: 0 for x in order}
    for _ in range(len(sequence) - 1):
        nxt = order[node][used[node]]
        used[node] += 1
        walk.append(nxt)
        node = nxt
    return "".join(walk)
