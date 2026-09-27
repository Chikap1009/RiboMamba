"""The repair pilot's validation target manifest (RESEARCH_PLAN.md, Stage A, items 1-2).

Selection is fixed BEFORE any candidate is scored, from validation targets only:

  source       data/targets/rfam_val.parquet (scripts/build_targets.py --split val
               --seed 0): one native per held-out validation family; the target is
               that native's ViennaRNA MFE structure. Solvable by construction.
  eligibility  (applied in order, every exclusion recorded with its reason)
                 structure uses only '(' ')' '.' (pseudoknot-free) and is balanced
                 length <= 256 and equals the native's length
                 >= 4 base pairs
                 every pair encloses >= 3 nucleotides
                 native is A/C/G/U, forms every target pair canonically, and the
                   build recorded it folding to the target (positive control)
                 target structure not already taken by another family
  strata       4 equal-count length bins; inside each, 4 equal-count bins of
               paired-base fraction (2 * pairs / length): 16 cells. Ties are
               broken by family name, so the bins are deterministic.
  selection    4 targets per cell, drawn with numpy default_rng(20260927)
               -> 64 targets
  split        inside each cell, 2 development + 2 confirmation (same RNG)
               -> 32 + 32; tuning uses development only
  smoke        one development target per (length bin, paired-fraction half)
               -> 8, for implementation checks

The manifest stores each target's native sequence for positive controls and
provenance only; design methods receive the structure alone. native_control
scores the native with scoring.score AFTER selection: every native reproduces
its target as the backtracked MFE (by construction), but a native with tied
optimal structures does not prove the strict uMFE endpoint reachable.
content_sha256 is the SHA-256 of the canonical JSON of everything else.
"""

import hashlib
import json
from pathlib import Path

import numpy as np
import polars as pl

from ribomamba.design.scoring import score
from ribomamba.eval.folding import CANONICAL_PAIRS, MIN_HAIRPIN, pair_table
from ribomamba.paths import MANIFESTS_DIR, REPO_ROOT, TARGETS_DIR

MANIFEST_NAME = "repair_pilot_val_v1"
MANIFEST_PATH = MANIFESTS_DIR / f"{MANIFEST_NAME}.json"
LOOKS_PATH = MANIFESTS_DIR / "confirmation_looks.jsonl"
SOURCE = TARGETS_DIR / "rfam_val.parquet"
SOURCE_SHA256 = "8691cbdce49e22f4f237955884cf46f7c078f843959a3128ffdf76681817e045"   # data/targets/val_funnel.json
SEED = 20260927
MAX_LEN = 256
MIN_PAIRS = 4
LENGTH_BINS = 4
PAIRED_BINS = 4
PER_CELL = 4
DEV_PER_CELL = 2
SUBSETS = ("smoke", "development", "confirmation", "all")


def sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def canonical_json(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


def content_hash(manifest: dict) -> str:
    return hashlib.sha256(canonical_json({k: v for k, v in manifest.items() if k != "content_sha256"})).hexdigest()


def _ineligible(row: dict) -> str | None:
    """The first eligibility rule this source row fails, or None."""
    target, native = row["target"], row["sequence"]
    if set(target) - set("()."):
        return "structure has characters other than ( ) . (pseudoknot or annotation)"
    try:
        pt = pair_table(target)
    except ValueError:
        return "unbalanced structure"
    if len(target) > MAX_LEN:
        return f"length > {MAX_LEN}"
    if len(native) != len(target):
        return "native length differs from target length"
    if sum(j > i for i, j in enumerate(pt)) < MIN_PAIRS:
        return f"fewer than {MIN_PAIRS} base pairs"
    if any(j > i and j - i - 1 < MIN_HAIRPIN for i, j in enumerate(pt)):
        return f"a pair encloses fewer than {MIN_HAIRPIN} nucleotides"
    if set(native) - set("ACGU"):
        return "native has letters outside A/C/G/U"
    if any(j > i and native[i] + native[j] not in CANONICAL_PAIRS for i, j in enumerate(pt)):
        return "native cannot form a target pair"
    if not row["native_mfe_match"]:
        return "native does not fold to the target (build record)"
    return None


def _equal_bins(values: list[float], names: list[str], n_bins: int) -> list[int]:
    """Equal-count bins by rank; ties broken by name, so the assignment is deterministic."""
    order = sorted(range(len(values)), key=lambda k: (values[k], names[k]))
    bins = [0] * len(values)
    for rank, k in enumerate(order):
        bins[k] = rank * n_bins // len(values)
    return bins


def build_manifest(source: Path = SOURCE, seed: int = SEED) -> dict:
    """Select, split and describe the pilot targets. Reads the validation source only."""
    source = Path(source)
    if "test" in source.name:
        raise PermissionError("the repair pilot is validation-only; test targets may not be read")
    table = pl.read_parquet(source).sort("family")
    rows = table.to_dicts()
    exclusions, eligible, seen = [], [], {}
    for row in rows:
        reason = _ineligible(row)
        if reason is None and row["target"] in seen:
            reason = f"target structure duplicates family {seen[row['target']]}"
        if reason is not None:
            exclusions.append({"family": row["family"], "reason": reason})
            continue
        seen[row["target"]] = row["family"]
        eligible.append(row)
    if len(eligible) < LENGTH_BINS * PAIRED_BINS * PER_CELL:
        raise ValueError(f"only {len(eligible)} eligible targets")

    for row in eligible:
        row["paired_fraction"] = 2 * row["target"].count("(") / len(row["target"])
    names = [r["family"] for r in eligible]
    length_bin = _equal_bins([r["length"] for r in eligible], names, LENGTH_BINS)
    strata = []
    for lb in range(LENGTH_BINS):
        members = [k for k in range(len(eligible)) if length_bin[k] == lb]
        pbins = _equal_bins([eligible[k]["paired_fraction"] for k in members],
                            [names[k] for k in members], PAIRED_BINS)
        for k, pb in zip(members, pbins):
            eligible[k]["length_bin"], eligible[k]["paired_bin"] = lb, pb
        for pb in range(PAIRED_BINS):
            cell = [eligible[k] for k, b in zip(members, pbins) if b == pb]
            strata.append({"length_bin": lb, "paired_bin": pb, "eligible": len(cell),
                           "length_range": [min(r["length"] for r in cell), max(r["length"] for r in cell)],
                           "paired_fraction_range": [round(min(r["paired_fraction"] for r in cell), 4),
                                                     round(max(r["paired_fraction"] for r in cell), 4)]})

    rng = np.random.default_rng(seed)
    chosen = []
    for cell in strata:                                               # cells in (length_bin, paired_bin) order
        pool = [r for r in eligible if (r["length_bin"], r["paired_bin"]) == (cell["length_bin"], cell["paired_bin"])]
        picks = [pool[k] for k in sorted(rng.choice(len(pool), size=PER_CELL, replace=False))]
        dev = set(rng.choice(PER_CELL, size=DEV_PER_CELL, replace=False).tolist())
        for k, r in enumerate(picks):
            r["subset"] = "development" if k in dev else "confirmation"
        chosen.extend(picks)
    for r in chosen:
        r["smoke"] = False
    for lb in range(LENGTH_BINS):
        for half in (0, 1):
            pool = [r for r in chosen if r["subset"] == "development" and r["length_bin"] == lb
                    and r["paired_bin"] // (PAIRED_BINS // 2) == half]
            pool[int(rng.integers(len(pool)))]["smoke"] = True

    targets = sorted(({"id": f"rfam_val:{r['family']}", "family": r["family"], "length": r["length"],
                       "pairs": r["target"].count("("), "paired_fraction": round(r["paired_fraction"], 6),
                       "length_bin": r["length_bin"], "paired_bin": r["paired_bin"], "subset": r["subset"],
                       "smoke": r["smoke"], "structure": r["target"], "native_sequence": r["sequence"]}
                      for r in chosen), key=lambda t: t["id"])
    for t in targets:                                                 # positive control, after selection
        native = score(t["native_sequence"], t["structure"])
        t["native_control"] = {"mfe_backtrack": native.mfe_backtrack, "umfe": native.umfe,
                               "mfe_ties": native.mfe_ties, "ned": round(native.ned, 6)}
    manifest = {
        "name": MANIFEST_NAME,
        "purpose": "Repair pilot (RESEARCH_PLAN.md Stage A): VALIDATION targets only. "
                   "Not a final benchmark; test targets were not read.",
        "source": {"path": str(source.relative_to(REPO_ROOT)) if source.is_relative_to(REPO_ROOT) else str(source),
                   "sha256": sha256_file(source),
                   "built_by": "python scripts/build_targets.py --split val --seed 0"},
        "seed": seed,
        "rules": {"eligibility": ["structure only ( ) . and balanced", f"length <= {MAX_LEN}, equal to native",
                                  f">= {MIN_PAIRS} base pairs", f"every pair encloses >= {MIN_HAIRPIN} nt",
                                  "native A/C/G/U, forms every target pair canonically, recorded native MFE match",
                                  "distinct target structure"],
                  "strata": f"{LENGTH_BINS} equal-count length bins x {PAIRED_BINS} equal-count paired-fraction "
                            "bins within each; ties broken by family name",
                  "selection": f"{PER_CELL} per cell, numpy default_rng({seed}), cells in order",
                  "split": f"{DEV_PER_CELL} development + {PER_CELL - DEV_PER_CELL} confirmation per cell",
                  "smoke": "one development target per (length bin, paired-fraction half)"},
        "funnel": {"source_rows": len(rows), "eligible": len(eligible), "selected": len(targets),
                   "development": sum(t["subset"] == "development" for t in targets),
                   "confirmation": sum(t["subset"] == "confirmation" for t in targets),
                   "smoke": sum(t["smoke"] for t in targets)},
        "exclusions": exclusions,
        "strata": strata,
        "targets": targets,
    }
    manifest["content_sha256"] = content_hash(manifest)
    return manifest


def load_manifest(path: Path = MANIFEST_PATH, check_source: bool = True) -> dict:
    """Read a manifest and refuse it if its content hash (or its source file, when present) has changed."""
    manifest = json.loads(Path(path).read_text())
    if content_hash(manifest) != manifest.get("content_sha256"):
        raise ValueError(f"{path}: content hash mismatch; the manifest was edited after it was built")
    source = REPO_ROOT / manifest["source"]["path"]
    if check_source and source.exists() and sha256_file(source) != manifest["source"]["sha256"]:
        raise ValueError(f"{source} no longer matches the manifest's recorded SHA-256")
    return manifest


def select(manifest: dict, subset: str) -> list[dict]:
    """The targets of one subset, in manifest (id) order."""
    if subset not in SUBSETS:
        raise ValueError(f"unknown subset {subset!r}; choose from {SUBSETS}")
    targets = manifest["targets"]
    if subset == "smoke":
        return [t for t in targets if t["smoke"]]
    if subset == "all":
        return list(targets)
    return [t for t in targets if t["subset"] == subset]


def write_manifest(manifest: dict, path: Path = MANIFEST_PATH) -> str:
    """Write once. Rewriting the identical manifest is a no-op; a different one is refused."""
    path = Path(path)
    text = json.dumps(manifest, indent=1, sort_keys=True) + "\n"
    if path.exists():
        if json.loads(path.read_text()) == json.loads(text):
            return "unchanged"
        raise FileExistsError(f"{path} exists with different content; version a new manifest instead")
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(text)
    tmp.replace(path)
    return "written"
