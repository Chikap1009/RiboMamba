"""Where things live on disk. One place, so no script hard-codes a path."""

from pathlib import Path

# This file is ribomamba/paths.py, so the repository root is two levels up.
REPO_ROOT = Path(__file__).resolve().parents[1]

DATA_DIR = REPO_ROOT / "data"            # ignored by Git (.gitignore, D-002)
RAW_DIR = DATA_DIR / "raw"               # downloads, exactly as published
PROCESSED_DIR = DATA_DIR / "processed"   # cleaned + split, what training reads
