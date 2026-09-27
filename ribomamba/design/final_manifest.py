"""Final-benchmark manifests (protocol v2): built from pinned public sources; RUNS on them are refused
until docs/PROTOCOL_design_v2.md carries a '**Status: FROZEN on YYYY-MM-DD**' line.

  final_eterna100_v2   Eterna100 V2, all 100 puzzles (19-400 nt): data/raw/eterna100/eterna100_puzzles.tsv
  final_eterna100_v1   Eterna100 V1, all 100 puzzles (same file; 19 structures differ from V2)
  final_rfam_taneda27  Rfam-Taneda-27 (54-382 nt): SAMFEO's pinned copy, identical to the LM paper's copy
All structures are pseudoknot-free with every pair enclosing >= 3 nt (checked here).
Building a manifest reads structures only; no design method is run.
"""

import polars as pl

from ribomamba.design.manifest import content_hash, sha256_file, write_manifest
from ribomamba.eval.folding import MIN_HAIRPIN, pair_table
from ribomamba.eval.protocol import frozen_date
from ribomamba.paths import EXTERNAL_DIR, MANIFESTS_DIR, RAW_DIR, REPO_ROOT

PROTOCOL = REPO_ROOT / "docs" / "PROTOCOL_design_v2.md"
ETERNA_TSV = RAW_DIR / "eterna100" / "eterna100_puzzles.tsv"
RF27 = EXTERNAL_DIR / "SAMFEO" / "data" / "Rfam" / "rf27.txt"
NAMES = ("final_eterna100_v2", "final_eterna100_v1", "final_rfam_taneda27")


def require_protocol_frozen() -> str:
    date = frozen_date(PROTOCOL)
    if date is None:
        raise PermissionError(f"final-benchmark runs are locked until {PROTOCOL} is frozen "
                              "('**Status: FROZEN on YYYY-MM-DD**')")
    return date


def _check(structure: str) -> None:
    if set(structure) - set("()."):
        raise ValueError("non dot-bracket structure")
    pt = pair_table(structure)
    if any(j > i and j - i - 1 < MIN_HAIRPIN for i, j in enumerate(pt)):
        raise ValueError("a pair encloses fewer than 3 nt")


def build(name: str) -> dict:
    if name.startswith("final_eterna100"):
        version = name[-2:].upper()
        t = pl.read_csv(ETERNA_TSV, separator="\t")
        rows = [{"id": f"eterna100_{version.lower()}:{int(r['Puzzle #'])}", "name": r["Puzzle Name"],
                 "structure": r[f"Secondary Structure {version}"]} for r in t.iter_rows(named=True)]
        source = {"path": str(ETERNA_TSV.relative_to(REPO_ROOT)), "sha256": sha256_file(ETERNA_TSV),
                  "column": f"Secondary Structure {version}"}
    elif name == "final_rfam_taneda27":
        structures = [line.strip() for line in open(RF27) if line.strip()]
        rows = [{"id": f"rfam_taneda27:{k + 1}", "name": f"Rfam-Taneda {k + 1}", "structure": s}
                for k, s in enumerate(structures)]
        source = {"path": str(RF27.relative_to(REPO_ROOT)), "sha256": sha256_file(RF27),
                  "note": "SAMFEO pinned e78b4b5 copy; identical set to RNA-Design-LM data/test/Rfam27.jsonl"}
    else:
        raise ValueError(name)
    for r in rows:
        _check(r["structure"])
    targets = sorted(({**r, "length": len(r["structure"]), "pairs": r["structure"].count("("),
                       "subset": "final", "smoke": False} for r in rows), key=lambda t: t["id"])
    manifest = {"name": name, "purpose": "FINAL benchmark (protocol v2); runs require the frozen protocol.",
                "source": source, "funnel": {"targets": len(targets)}, "targets": targets}
    manifest["content_sha256"] = content_hash(manifest)
    return manifest


def build_all() -> dict:
    out = {}
    for name in NAMES:
        m = build(name)
        out[name] = {"outcome": write_manifest(m, MANIFESTS_DIR / f"{name}.json"), "sha": m["content_sha256"],
                     "targets": len(m["targets"])}
    return out
