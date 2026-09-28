"""Build (or refresh) the local closeout preservation package (docs/REPRODUCE.md, docs/HANDOFF.md).

  python scripts/closeout_package.py --dest /home/chirag/projects/RiboMamba_closeout_2026-09-29

Never moves, deletes or modifies anything in the repository. Layout of the package:
  COMMIT.txt           code commit, branch, working-tree state at build time
  ribomamba.bundle     `git bundle create --all` (full committed history) + bundle_verify.txt
  restore/             category A copies, mirroring repository-relative paths (rsync onto the repo root)
  docs_snapshot/       readable copies of the reports, records, manifests and environment locks
  inventory.json       every essential artifact: category A (copied), B (referenced in place with
                       checksum) or C (obtain/rebuild separately), with path, size and SHA-256
  checks/              closeout verification outputs
  SHA256SUMS           SHA-256 of every package file except itself and VERIFY.txt
  VERIFY.txt           result of re-hashing the package against SHA256SUMS and of comparing each
                       restore/ copy with its original
A copy is refreshed only when missing or different from the original; a differing copy of an original
that itself has not changed is reported, not silently replaced.
"""

import argparse
import datetime as dt
import hashlib
import json
import shutil
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PACKAGE_README = """# RiboMamba closeout package (local; NOT redistributable)

Built by scripts/closeout_package.py (see COMMIT.txt for the code commit). It preserves what is needed
to inspect and regenerate the final technical report (docs_snapshot/docs/REPORT_repair_v2.md) outside
Git. This is a SECOND COPY ON THE SAME DISK as the repository: it protects against accidental edits or
deletions in the working tree, not against disk failure; copy the whole directory to separate storage
for an independent backup. It contains third-party DATA used locally (Eterna puzzle files; licences in
docs_snapshot/docs/DATA_CARD_design.md) and NO third-party code.

Contents
- COMMIT.txt, ribomamba.bundle (+ bundle_verify.txt): the committed history; restore the code with
  `git clone ribomamba.bundle RiboMamba && git -C RiboMamba checkout <commit>`.
- restore/: category A copies mirroring repository paths: data/repair_pilot (every run, the FINAL
  report and its history, efficiency-study runs and profiles), the base and TCD checkpoints (and the
  critic/residual checkpoints of the negative results), prepared data (data/processed, data/tcd_v1) and
  the target source files. Restore with `rsync -a restore/ <repository root>/`.
- docs_snapshot/: readable copies of reports, records, manifests, environment locks and chain scripts.
- inventory.json: every essential artifact with category A (copied), B (referenced in place: path,
  size, SHA-256; large public Rfam files and artifacts not needed for this report) or C (obtain or
  rebuild: third-party code with URL, commit and licence; conda environments from their lock files).
- checks/: closeout verification outputs (consistency checks, regeneration comparison).
- SHA256SUMS: SHA-256 of every file here except SHA256SUMS and VERIFY.txt; check with
  `sha256sum -c SHA256SUMS`. VERIFY.txt: the result of that check and of comparing restore/ copies
  with the originals' hashes at build time.
Reproduction steps: docs_snapshot/docs/REPRODUCE.md.
"""

# A: copied into restore/ (repository-relative; directories copied recursively)
COPY = ["data/repair_pilot", "checkpoints/tf_M_do0/best.pt", "checkpoints/tf_M_do0/config.json",
        "checkpoints/tf_M_do0/log.csv", "checkpoints/tcd_v1", "checkpoints/critic_v1", "checkpoints/residual_v1",
        "data/processed", "data/tcd_v1", "data/raw/eterna100", "data/raw/eternaweb_rnadesignlm"]
# B: referenced in place (checksummed, not copied): large, public and re-downloadable, or not needed here
REFERENCE = [("data/raw/rfam", "Rfam 15.0 sequences (multimolecule/rfam 25e8aa8); only to rebuild data/processed"),
             ("data/raw/rfam_cm", "Rfam 15.0 covariance models; only to rebuild data/processed"),
             ("data/raw/rfam_clanin", "Rfam clan membership; only to rebuild data/processed"),
             ("data/raw/bprna", "bpRNA (multimolecule/bprna 423465b); Phase 1-3 evaluation, not this report"),
             ("checkpoints/tf_M_do0/last.pt", "last (non-selected) weights of the base model run"),
             ("data/processed_split1", "replication split (Phase 3); not used by this report")]
# C: obtain or rebuild separately (third-party code or environments; never copied)
EXTERNAL = [("external/SAMFEO", "https://github.com/shanry/SAMFEO.git", "no licence file: local use only, never redistribute"),
            ("external/DesiRNA", "https://github.com/fryzjergda/DesiRNA.git", "Apache-2.0"),
            ("external/SamplingDesign", "https://github.com/weiyutang1010/SamplingDesign.git",
             "Apache-2.0; build: conda activate rmtools && make CC=x86_64-conda-linux-gnu-g++")]
DOCS = ["README.md", "docs/REPORT_repair_v2.md", "docs/REPRODUCE.md", "docs/HANDOFF.md", "docs/RESULTS.md",
        "docs/DECISIONS.md", "docs/PROTOCOL_design_v2.md", "docs/REFERENCES.md", "docs/MODEL_CARD_tcd_v1.md",
        "docs/DATA_CARD_design.md", "docs/INTERVIEW_PREP.md", "docs/RESEARCH_PLAN.md", "docs/figures", "docs/experiments",
        "docs/logbook/2026-09-27-session-09.md", "docs/logbook/2026-09-28-session-10.md",
        "docs/logbook/2026-09-28-session-11.md", "docs/logbook/2026-09-29-session-12.md", "manifests",
        "environment.yml", "environment.lock.yml", "environment.design_v2.ribomamba.lock.yml",
        "environment.design_v2.desirna.lock.yml", "environment.design_v2.rmtools.lock.yml", "scripts/final_v2"]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def files_under(root: Path) -> list[Path]:
    return [root] if root.is_file() else sorted(p for p in root.rglob("*") if p.is_file())


def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=REPO, capture_output=True, text=True, check=True).stdout.strip()


def copy_tree(rel_items: list[str], dest_root: Path, report: list) -> list[dict]:
    """Copy each file (mirroring its relative path); return inventory rows for category A."""
    rows = []
    for rel in rel_items:
        src_root = REPO / rel
        if not src_root.exists():
            rows.append({"path": rel, "category": "A", "missing": True})
            continue
        for src in files_under(src_root):
            relp = src.relative_to(REPO).as_posix()
            dst = dest_root / relp
            digest = sha256(src)
            if dst.exists() and sha256(dst) != digest:
                report.append(f"DIFFERS (not replaced): {relp}")
            elif not dst.exists():
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
            rows.append({"path": relp, "category": "A", "bytes": src.stat().st_size, "sha256": digest})
    return rows


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--dest", required=True)
    p.add_argument("--checks", default=None, help="directory of closeout check outputs to copy into checks/")
    args = p.parse_args()
    dest = Path(args.dest)
    dest.mkdir(parents=True, exist_ok=True)
    notes: list[str] = []
    (dest / "README.md").write_text(PACKAGE_README)
    if args.checks:
        for f in files_under(Path(args.checks)):
            out = dest / "checks" / f.relative_to(args.checks)
            out.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(f, out)
    head, dirty = git("rev-parse", "HEAD"), git("status", "--porcelain")
    (dest / "COMMIT.txt").write_text(
        f"commit {head}\nbranch {git('rev-parse', '--abbrev-ref', 'HEAD')}\nsubject {git('log', '-1', '--format=%s')}\n"
        f"built_utc {dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')}\n"
        f"working_tree {'CLEAN' if not dirty else 'UNCOMMITTED CHANGES:\\n' + dirty}\n")
    bundle = dest / "ribomamba.bundle"
    if bundle.exists():
        bundle.unlink()                                    # the bundle is regenerated from Git, not an original
    subprocess.run(["git", "bundle", "create", str(bundle), "--all"], cwd=REPO, check=True, capture_output=True)
    verify = subprocess.run(["git", "bundle", "verify", str(bundle)], cwd=REPO, capture_output=True, text=True)
    (dest / "bundle_verify.txt").write_text(verify.stdout + verify.stderr + f"\nexit {verify.returncode}\n")
    inventory = copy_tree(COPY, dest / "restore", notes)
    snap = dest / "docs_snapshot"
    for rel in DOCS:                                     # readable copies; always refreshed from the working tree
        src = REPO / rel
        if not src.exists():
            notes.append(f"doc missing: {rel}")
            continue
        for f in files_under(src):
            out = snap / f.relative_to(REPO)
            out.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(f, out)
    for rel, note in REFERENCE:
        for f in files_under(REPO / rel) if (REPO / rel).exists() else []:
            inventory.append({"path": f.relative_to(REPO).as_posix(), "category": "B", "bytes": f.stat().st_size,
                              "sha256": sha256(f), "note": note})
    for rel, url, lic in EXTERNAL:
        commit = subprocess.run(["git", "-C", str(REPO / rel), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
        inventory.append({"path": rel, "category": "C", "source": url, "commit": commit, "licence": lic,
                          "how": f"git clone {url} {rel} && git -C {rel} checkout {commit}"})
    for env in ("ribomamba", "desirna", "rmtools"):
        inventory.append({"path": f"conda env {env}", "category": "C",
                          "how": f"conda env create -n {env} -f environment.design_v2.{env}.lock.yml"})
    inventory.append({"path": "EternaFold 1.3.1, ViennaRNA 2.7.2", "category": "C",
                      "how": "installed by the ribomamba environment lock (bioconda packages)"})
    (dest / "inventory.json").write_text(json.dumps({"commit": head, "items": inventory}, indent=1))
    # checksums of every package file except SHA256SUMS and VERIFY.txt (the manifest never hashes itself)
    listed = sorted(f for f in dest.rglob("*") if f.is_file() and f.name not in ("SHA256SUMS", "VERIFY.txt"))
    (dest / "SHA256SUMS").write_text("".join(f"{sha256(f)}  {f.relative_to(dest).as_posix()}\n" for f in listed))
    # verification: re-hash the package, and compare every restore/ copy with its original's recorded hash
    check = subprocess.run(["sha256sum", "--quiet", "-c", "SHA256SUMS"], cwd=dest, capture_output=True, text=True)
    by_path = {line.split("  ", 1)[1].strip(): line.split("  ", 1)[0] for line in (dest / "SHA256SUMS").read_text().splitlines()}
    mismatch = [r["path"] for r in inventory if r["category"] == "A" and not r.get("missing")
                and by_path.get(f"restore/{r['path']}") != r["sha256"]]
    a_rows = [r for r in inventory if r["category"] == "A" and not r.get("missing")]
    summary = (f"package {dest}\ncommit {head} ({'clean' if not dirty else 'UNCOMMITTED CHANGES'})\n"
               f"sha256sum -c SHA256SUMS: {'ALL OK' if check.returncode == 0 else 'FAILED'} ({len(listed)} files)\n"
               f"{check.stdout}{check.stderr}"
               f"restore/ copies equal to originals: {len(a_rows) - len(mismatch)} / {len(a_rows)}\n"
               + "".join(f"  MISMATCH {m}\n" for m in mismatch)
               + f"git bundle verify: exit {verify.returncode}\n"
               + f"category A files {len(a_rows)} ({sum(r['bytes'] for r in a_rows) / 2**30:.2f} GiB); "
               f"category B files {sum(r['category'] == 'B' for r in inventory)} "
               f"({sum(r.get('bytes', 0) for r in inventory if r['category'] == 'B') / 2**30:.2f} GiB); "
               f"category C items {sum(r['category'] == 'C' for r in inventory)}\n"
               + "".join(f"NOTE {n}\n" for n in notes))
    (dest / "VERIFY.txt").write_text(summary)
    print(summary)


if __name__ == "__main__":
    main()
