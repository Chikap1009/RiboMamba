"""Download the raw Phase 1 datasets from the HuggingFace Hub.

Each dataset is pinned to one exact commit of its HuggingFace repository, and
the downloaded file's SHA-256 checksum is compared with the value recorded
below. Together these guarantee that anyone who runs this script gets the same
bytes we trained on, even if the dataset's owners update it later (D-005).

Usage (from the repository root, inside `conda activate ribomamba`):
    python scripts/download_data.py

Output:
    data/raw/rfam/data.parquet    20,051,822 Rfam family members (726 MB)
    data/raw/bprna/data.parquet   102,318 bpRNA-1m sequences with structures (5 MB)
"""

import hashlib
from pathlib import Path

from huggingface_hub import hf_hub_download

from ribomamba.paths import RAW_DIR

# name -> (HuggingFace repo, commit hash, file in the repo, expected SHA-256)
DATASETS = {
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


def sha256_of(path: Path) -> str:
    """Checksum a file in 1 MB chunks, so a large file never sits in memory whole."""
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(1 << 20):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    for name, (repo, revision, filename, expected) in DATASETS.items():
        local_dir = RAW_DIR / name
        target = local_dir / filename
        if target.exists() and sha256_of(target) == expected:
            print(f"{name}: already downloaded, checksum OK")
            continue

        path = Path(hf_hub_download(
            repo_id=repo,
            repo_type="dataset",
            filename=filename,
            revision=revision,      # the pin: this exact version, never "latest"
            local_dir=local_dir,    # straight into data/raw/, no second copy
        ))
        actual = sha256_of(path)
        if actual != expected:
            raise RuntimeError(
                f"{name}: checksum mismatch.\n  expected {expected}\n  got      {actual}\n"
                "The file is corrupted or not the version we pinned. Delete it and retry."
            )
        print(f"{name}: downloaded {path.stat().st_size:,} bytes, checksum OK -> {path}")


if __name__ == "__main__":
    main()
