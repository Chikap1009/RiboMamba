# Decisions — RiboMamba

Each entry records one non-trivial choice. These are written so they can be
spoken aloud in an interview: *"We chose X because…, we considered Y and Z but
rejected them because…, and the price we paid is…"*

Entries are numbered and never deleted. If a decision is reversed, add a new
entry that says so and points back to the old one. The history of changing your
mind is itself valuable.

## Template

```
## D-NNN — <short title>
**Date:** YYYY-MM-DD   **Phase:** N   **Logbook:** logbook/<file>.md
**Status:** accepted | superseded by D-MMM

**Context.** What problem forced a choice? What constraints applied
(8 GB VRAM, zero budget, …)?

**Decision.** What we chose, in one or two sentences.

**Alternatives rejected.**
- Option A — why not.
- Option B — why not.

**Consequences / trade-offs accepted.** What this costs us, and what we'd
revisit with more compute or time.
```

---

## D-001 — Work at the secondary-structure level, without pseudoknots
**Date:** 2026-09-22   **Phase:** 0   **Logbook:** logbook/2026-09-22-session-01.md
**Status:** accepted (provisional; revisit when choosing the folding oracle in Phase 3)

**Context.** An RNA's shape can be described at three levels: the sequence
(primary), which bases pair with which (secondary), and the full 3D shape
(tertiary). Our project needs to *check* tens of thousands of generated
sequences, so whatever structure we target has to be predictable quickly,
cheaply and reproducibly on a laptop with zero budget.

**Decision.** We define "structure" as a nested secondary structure (a
dot-bracket string), predicted by standard minimum-free-energy folding
software (ViennaRNA). Crossing pairs (pseudoknots) are excluded.

**Alternatives rejected.**
- *3D structure.* 3D prediction is far more expensive, needs much more
  compute than 8 GB of VRAM comfortably allows at our scale, and is still
  much less reliable for RNA than for proteins. It also isn't needed to answer
  our research question, which compares generative backbones under the *same*
  evaluation.
- *Secondary structure with pseudoknots.* Pseudoknots are real, but allowing
  crossing pairs destroys the property that makes folding fast: nested pairs
  split the problem into independent sub-stretches, which lets dynamic
  programming find the MFE in O(N³). Pseudoknot-aware tools exist, but they
  are slower, handle only restricted kinds of crossings, and are less standard
  as evaluation oracles, which would make our numbers harder to compare with
  other work.

**Consequences / trade-offs accepted.**
- Any RNA whose function depends on a pseudoknot is outside what we can
  target or evaluate. We state this limitation openly.
- "Success" means *the folding software predicts* the target structure. It
  does not mean a verified 3D shape, and it is not a wet-lab result.
- With more compute or time: evaluate a subset with a pseudoknot-aware folder
  or with a second, independent oracle, to check that conclusions don't depend
  on one tool's quirks.

---

## D-002 — The repository lives inside WSL2's Linux file system, backed up to GitHub
**Date:** 2026-09-22   **Phase:** 0   **Logbook:** logbook/2026-09-22-session-02.md
**Status:** accepted

**Context.** The project started in `C:\Users\chira\OneDrive\Desktop\RiboMamba`,
a Windows folder that OneDrive syncs to the cloud. All our tools (Git,
Python, conda, ViennaRNA, later PyTorch and `mamba-ssm`) run inside Linux
(WSL2), which sees that folder only through the Windows↔Linux bridge
(`/mnt/c/...`). The project will produce many small files that change
constantly: Git's history database, datasets, checkpoints.

**Decision.** The working copy lives at `~/projects/RiboMamba` on Ubuntu's own
disk inside WSL2. The Git history is pushed to a public GitHub repository
(`Chikap1009/RiboMamba`) at the end of every session. Datasets and model
checkpoints are *not* stored in Git: datasets are re-downloadable by
design (CLAUDE.md §3.4), and checkpoints can be retrained or published
separately.

**Alternatives rejected.**
- *Stay in OneDrive.* Three problems. (1) Every file access from Linux
  crosses the bridge, and the cost is paid per access, so thousands of small
  files make it slow (like off-chip memory behind a bus bridge). (2) OneDrive
  would try to upload every change to datasets and checkpoints, eating quota
  and locking files mid-write. (3) Git and OneDrive would both act as the
  "source of truth" for the same files with no coordination between them,
  like two caches with no coherence protocol, which risks corrupting Git's
  history.
- *A Windows folder outside OneDrive (e.g. `C:\dev`).* Removes (2) and (3),
  but not (1). Linux tools would still pay the bridge cost on every access.

**Consequences / trade-offs accepted.**
- The project now lives inside one virtual-disk file (`ext4.vhdx`).
  Uninstalling the Linux distro deletes it. This really happened on this
  machine in session 02 (the old Ubuntu's disk was deleted during a
  cleanup). **Mitigation: `git push` to GitHub at the end of every session.**
  Anything not pushed is at risk.
- Windows programs reach the files via
  `\\wsl.localhost\Ubuntu-24.04\home\chirag\projects\RiboMamba`, and VS Code
  opens the folder "in WSL". Slightly less convenient than a Desktop folder.
- The repository is **private during the build and goes public at the end of
  the project**, after a final pass over the contents (Chirag's decision,
  2026-09-22). The reason for not publishing immediately: CLAUDE.md §0 is
  personal (it names the target lab and describes past AI-written projects),
  and publishing cannot be undone, while private → public is one command.
  Even so, nothing secret (tokens, passwords, private data) may ever be
  committed, since every commit stays in history after the flip.

---

## D-003 — Software environment: Miniforge (conda) with a committed `environment.yml`
**Date:** 2026-09-22   **Phase:** 0   **Logbook:** logbook/2026-09-22-session-02.md
**Status:** accepted

**Context.** The project needs Python plus compiled scientific software that
isn't pure Python: ViennaRNA (C code with Python bindings) now, and PyTorch
with CUDA and `mamba-ssm` later. Versions must be pinned so that the
evaluation oracle gives the same answers every time (CLAUDE.md §3.5), and
the whole setup must be rebuildable from one file after a wipe (which
happened this session). Zero budget: no commercial licences.

**Decision.** Install **Miniforge** (version 26.7.2-0, checksum-verified),
which provides `conda` and uses the free, community-run **conda-forge**
channel by default. Keep the project's dependencies in an isolated
environment named `ribomamba`, defined by `environment.yml` in the repo
(channels: conda-forge, then bioconda; Python 3.12; ViennaRNA). Rebuild with
`conda env create -f environment.yml`.

**Alternatives rejected.**
- *Anaconda / Miniconda with the `defaults` channel.* The `defaults` channel
  has commercial terms-of-service restrictions for some organisations.
  Miniforge is the same tool, pointed at the free community channel, and
  bioconda is built against conda-forge anyway.
- *pip + venv only.* Fine for pure-Python packages, but ViennaRNA's official
  binary builds come through bioconda. pip can't manage non-Python pieces
  (C libraries, CUDA runtimes) as cleanly.
- *Ubuntu's `apt` packages.* System-wide (one version for the whole machine),
  often older, and not reproducible on Kaggle/Colab.
- *Installing into conda's `base` environment.* `base` runs conda itself.
  Filling it with project packages risks breaking the tool that manages
  everything else, and can't be deleted and recreated cleanly.

**Consequences / trade-offs accepted.**
- About 0.7 GB for Miniforge plus the environment's size on disk.
- Environment creation depends on download servers. In session 02 the
  ViennaRNA package downloaded at about 30 KB/s from bioconda's servers.
- `environment.yml` pins Python's minor version. ViennaRNA is pinned to the
  exact version that got installed, because it is the folding oracle and
  a different version could give different energies.
- Naming clash to remember: **mamba** the package installer (it ships with
  Miniforge) has nothing to do with **Mamba** the neural network.
