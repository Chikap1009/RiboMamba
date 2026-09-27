"""Where things live on disk. One place, so no script hard-codes a path."""

from pathlib import Path

# This file is ribomamba/paths.py, so the repository root is two levels up.
REPO_ROOT = Path(__file__).resolve().parents[1]

DATA_DIR = REPO_ROOT / "data"            # ignored by Git (.gitignore, D-002)
RAW_DIR = DATA_DIR / "raw"               # downloads, exactly as published
PROCESSED_DIR = DATA_DIR / "processed"   # cleaned + split, what training reads
EVAL_DIR = DATA_DIR / "eval"             # evaluation harness outputs (re-creatable, Phase 3)
TARGETS_DIR = DATA_DIR / "targets"       # design target sets (scripts/build_targets.py)
PILOT_DIR = DATA_DIR / "repair_pilot"    # repair-pilot run directories: raw traces (re-creatable)
MANIFESTS_DIR = REPO_ROOT / "manifests"  # versioned target manifests and the confirmation-look log (in Git)
EXTERNAL_DIR = REPO_ROOT / "external"    # pinned third-party baseline checkouts (ignored by Git)
