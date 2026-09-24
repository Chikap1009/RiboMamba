"""Pre-registration, enforced in code (Phase 3; CLAUDE.md 3.5).

The rule: no test-set evaluation until the evaluation protocol is written,
dated and frozen in docs/RESULTS.md. Instead of relying on memory, every
function that reads the test split calls require_frozen("test"), which
refuses unless RESULTS.md contains the line

    **Status: FROZEN on YYYY-MM-DD**

in its "Frozen evaluation protocol" section.
"""

import re
import subprocess
from pathlib import Path

from ribomamba.paths import REPO_ROOT

RESULTS_MD = REPO_ROOT / "docs" / "RESULTS.md"
_MARKER = re.compile(r"^\*\*Status: FROZEN on (\d{4}-\d{2}-\d{2})\*\*", re.MULTILINE)


def frozen_date(results_md: Path = RESULTS_MD) -> str | None:
    """The date the protocol was frozen, or None if it hasn't been."""
    match = _MARKER.search(Path(results_md).read_text())
    return match.group(1) if match else None


def require_frozen(split: str, results_md: Path = RESULTS_MD) -> None:
    """Raise unless `split` may be read: train and val always; test only after the freeze."""
    if split not in ("train", "val", "test"):
        raise ValueError(f"unknown split {split!r}")
    if split == "test" and frozen_date(results_md) is None:
        raise PermissionError("the test split is locked until the evaluation protocol is frozen in "
                              f"{results_md} (a '**Status: FROZEN on YYYY-MM-DD**' line)")


def git_commit() -> str:
    """The exact code version, marked '-dirty' if tracked files have uncommitted edits (as in train.py)."""
    head = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=REPO_ROOT).stdout.strip()
    dirty = subprocess.run(["git", "status", "--porcelain", "--untracked-files=no"],
                           capture_output=True, text=True, cwd=REPO_ROOT).stdout.strip()
    return head + ("-dirty" if dirty else "")
