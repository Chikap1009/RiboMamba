"""Download the raw Phase 1 data: two HuggingFace datasets and Rfam's family models.

Each file is pinned to one exact version (a HuggingFace repository commit, or
a numbered Rfam release) and its SHA-256 checksum is compared with the value
recorded below. Together these guarantee that anyone who runs this script
gets the same bytes we used, even if the owners update their copies later
(D-005, D-009).

Usage (from the repository root, inside `conda activate ribomamba`):
    python scripts/download_data.py

Output:
    data/raw/rfam/data.parquet      20,051,822 Rfam family members (726 MB)
    data/raw/bprna/data.parquet     102,318 bpRNA-1m sequences with structures (5 MB)
    data/raw/rfam_cm/Rfam.cm.gz     4,178 Rfam 15.0 covariance models (45 MB)
    data/raw/rfam_clanin/Rfam.clanin  Rfam 15.0 clan membership, 146 clans (Phase 3)
    data/raw/eterna100/eterna100_puzzles.tsv  Eterna100 V1/V2 design targets (Phase 3)
"""

import hashlib
import shutil
import urllib.request
from pathlib import Path

from huggingface_hub import hf_hub_download

from ribomamba.paths import RAW_DIR

# name -> (HuggingFace repo, commit hash, file in the repo, expected SHA-256)
HF_DATASETS = {
    "rfam": (
        "multimolecule/rfam",
        "25e8aa866f647aefdd0777928ba3de6b98fd1d57",
        "data.parquet",
        "adaabe6bbc61eac141869ecc17fe81902c89c21b164008d5a4da164d7b684f43",
    ),
    "bprna": (
        "multimolecule/bprna",
        "423465bd00901bdb35030ccb0a0f8c9ba1282472",
        "data.parquet",
        "d0f5723641c1bfcb89ad341b49b302c8379d8a5f8fd2dcc6ead93c71c5956cd2",
    ),
}

# name -> (URL of a numbered, never-changing release, file name, expected SHA-256)
# Rfam 15.0 is the release the HF Rfam copy was built from: all 459 of its
# family->clan pairs match 15.0's Rfam.clanin exactly (checked in session 03).
# Rfam publishes no checksums, so this SHA-256 was recorded at our first
# download on 2026-09-23 ("trust on first use"): it guarantees later
# downloads are identical to ours, not that ours was untampered.
URL_FILES = {
    "rfam_cm": (
        "https://ftp.ebi.ac.uk/pub/databases/Rfam/15.0/Rfam.cm.gz",
        "Rfam.cm.gz",
        "f8885ee1bdf7a085c9a68af94be68d23e63da647d8f9f09835d22a218d2bfe9f",
    ),
    # Which families belong to which clan, for ALL Rfam 15.0 families (our data only
    # carries clans for the families it contains). Used to screen design targets at
    # the clan level, like the split (Phase 3). Recorded on first download 2026-09-24.
    "rfam_clanin": (
        "https://ftp.ebi.ac.uk/pub/databases/Rfam/15.0/Rfam.clanin",
        "Rfam.clanin",
        "7673c105ca4fea52eee19c01ba7ba9b5e76eed490ec126df09a039b2ae8f5d11",
    ),
    # Eterna100 design benchmark (Anderson-Lee et al. 2016; V2 structures redesigned for
    # ViennaRNA 2), pinned to a repository commit (MIT licence). An external, evaluation-only
    # target set for Phase 5 (frozen protocol P3). Recorded on first download 2026-09-24.
    "eterna100": (
        "https://raw.githubusercontent.com/eternagame/eterna100-benchmarking/"
        "e7a123076859865652de2a1b8be3bf2fcd5039c7/data/eterna100_puzzles.tsv",
        "eterna100_puzzles.tsv",
        "303da43d5404433bb4a006b421f73001ca9b90f43596e0ffad35d167dc806c61",
    ),
}


def sha256_of(path: Path) -> str:
    """Checksum a file in 1 MB chunks, so a large file never sits in memory whole."""
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(1 << 20):
            digest.update(chunk)
    return digest.hexdigest()


def verify(name: str, path: Path, expected: str) -> None:
    actual = sha256_of(path)
    if actual != expected:
        raise RuntimeError(
            f"{name}: checksum mismatch.\n  expected {expected}\n  got      {actual}\n"
            "The file is corrupted or not the version we pinned. Delete it and retry."
        )
    print(f"{name}: {path.stat().st_size:,} bytes, checksum OK -> {path}")


def main() -> None:
    for name, (repo, revision, filename, expected) in HF_DATASETS.items():
        target = RAW_DIR / name / filename
        if not (target.exists() and sha256_of(target) == expected):
            hf_hub_download(
                repo_id=repo,
                repo_type="dataset",
                filename=filename,
                revision=revision,        # the pin: this exact version, never "latest"
                local_dir=RAW_DIR / name, # straight into data/raw/, no second copy
            )
        verify(name, target, expected)

    for name, (url, filename, expected) in URL_FILES.items():
        target = RAW_DIR / name / filename
        if not (target.exists() and sha256_of(target) == expected):
            target.parent.mkdir(parents=True, exist_ok=True)
            with urllib.request.urlopen(url) as response, open(target, "wb") as out:
                shutil.copyfileobj(response, out)   # streams in chunks, never all in memory
        verify(name, target, expected)


if __name__ == "__main__":
    main()
