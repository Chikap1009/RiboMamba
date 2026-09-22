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

---

## D-004 — PyTorch 2.10 (CUDA 12.8 build) from pip, chosen for Phase 4's sake
**Date:** 2026-09-23   **Phase:** 1   **Logbook:** logbook/2026-09-23-session-03.md
**Status:** accepted

**Context.** Phase 1 needs PyTorch for its `Dataset`/`DataLoader`. Phase 4
needs `mamba-ssm` and `causal-conv1d`, which contain custom GPU code
(compiled CUDA kernels). Compiling them ourselves takes a long time and often
fails on laptops, so we want their **prebuilt wheels**, and a prebuilt wheel
only works with the exact PyTorch version it was compiled against. On
2026-09-23, the newest PyTorch was 2.14, but the newest `mamba-ssm`
(2.3.2.post1) and `causal-conv1d` (1.7.0) wheels for Python 3.12 on Linux
stop at **PyTorch 2.10** (CUDA 12 or 13).

**Decision.** Install `torch==2.10.0+cu128` with pip, from PyTorch's own
package index, inside the conda environment. Record it in the `pip:` section
of `environment.yml`.

**Alternatives rejected.**
- *Newest PyTorch (2.14) now, downgrade in Phase 4.* The Transformer
  baseline (Phase 2) and the Mamba models (Phase 4) would then be trained on
  different software. For a fair, compute-matched comparison we want one
  stack for all three models, fixed from the start.
- *PyTorch from conda-forge.* It works, but `mamba-ssm`'s wheels are built
  against the pip wheels (same C++ ABI, same bundled CUDA libraries). Mixing
  them risks import-time crashes that are hard to debug.
- *CUDA 13.0 build.* Our driver supports it (max CUDA 13.2), but CUDA 12.x
  is the more widely tested line for these kernels, and both wheel sets
  exist. CUDA 12.8 fully supports the RTX 4060 (Ada, compute capability 8.9).

**Consequences / trade-offs accepted.** We're four minor versions behind the
newest PyTorch. Nothing we need is missing, and we'll revisit only if a
newer `mamba-ssm` wheel appears. About 3 GB of disk for PyTorch plus its
bundled CUDA libraries.

---

## D-005 — Rfam is the training corpus; datasets are pinned to exact versions
**Date:** 2026-09-23   **Phase:** 1   **Logbook:** logbook/2026-09-23-session-03.md
**Status:** accepted

**Context.** We need many real RNA sequences to learn from. We also need to
know which family each belongs to, because an honest test set must contain
families the model has never seen (D-008). Two public sources are on
HuggingFace: `multimolecule/rfam` (20,051,822 sequences, **with** family and
clan labels, **without** structures) and `multimolecule/bprna` (102,318
sequences **with** structures, **without** family labels).

**Decision.**
1. Train on **Rfam**. Download bpRNA too and characterise it. Its possible
   role as a source of target structures is decided in Phase 3.
2. Download each dataset **at a pinned repository commit** and verify its
   **SHA-256 checksum** (`scripts/download_data.py`): Rfam at `25e8aa8…`,
   bpRNA at `423465b…`.
3. Fetch the raw Parquet files with `huggingface_hub.hf_hub_download` and
   process them with **polars**, instead of `datasets.load_dataset`.

**Alternatives rejected.**
- *Train on bpRNA.* It has no family labels, so no family-aware split is
  possible. The literature shows what happens then: models look good on
  bpRNA's identity-filtered test split (TS0) and drop on family-disjoint
  data (bpRNA-new).
- *Unpinned download ("latest").* Dataset repos change. Without a pin, a
  rerun months later could silently use different data, and our numbers
  would stop being reproducible (CLAUDE.md §3.5).
- *`datasets.load_dataset`.* It fetches the same files from the same Hub, but
  then converts them into its own 5.9 GB Arrow cache, and its `.filter` and
  `.map` run a Python function per row. Polars reads the Parquet file
  directly, only the columns asked for, using all CPU cores, which matters
  at 20 M rows on a machine where WSL sees 11 GB of RAM.

**Consequences / trade-offs accepted.**
- Rfam's per-sequence "structure" doesn't exist in this dataset. Any
  structure we need later (Phase 5 conditioning) is computed with our oracle,
  ViennaRNA.
- Rfam "full" members are found by a model (a covariance model with a
  score threshold), so a few family labels will be wrong. The leakage audit
  checks sequence similarity across splits independently of the labels.
- Both datasets are redistributions by MultiMolecule (AGPL-3.0) of CC0/public
  originals. Cite the original databases.

---

## D-006 — One nucleotide per token; a fixed 8-token vocabulary
**Date:** 2026-09-23   **Phase:** 1   **Logbook:** logbook/2026-09-23-session-03.md
**Status:** accepted

**Context.** Models consume integers, so sequences need a tokeniser. All
three models (diffusion Transformer, diffusion BiMamba, autoregressive
Mamba) must share one vocabulary for exact parameter matching.

**Decision.** Character level: `<pad>=0, <mask>=1, <bos>=2, <eos>=3, A=4,
C=5, G=6, U=7` (`ribomamba/data/tokenizer.py`). The ids are frozen by a test.
Sequences with any non-ACGU letter are removed during cleaning, so there is
no `<unk>` token.

**Alternatives rejected.**
- *k-mer tokens* (e.g. 3-mers, 64-token vocabulary): 3× shorter sequences,
  but base pairing and diffusion masking both act on single nucleotides. A
  3-mer token can straddle a stem and a loop.
- *BPE / learned subwords:* designed to shorten text over large alphabets.
  With 4 letters and sequences of a few hundred there's no need, and it
  would give up single-nucleotide resolution.
- *An `<unk>` token for N, R, Y…:* the generator could learn to emit
  "unknown", which isn't a molecule anyone can make.

**Consequences / trade-offs accepted.** Sequences are as long as the RNA
itself (no compression), which is what makes the length cap (D-007)
necessary. `<bos>`/`<eos>` are unused by the diffusion models in Phase 2.
They're reserved so the Phase 4 autoregressive baseline shares the table.

---

## D-007 — Cleaning: drop the duplicate copy, cap length at 256, cap each family at 1,000
**Date:** 2026-09-23   **Phase:** 1   **Logbook:** logbook/2026-09-23-session-03.md
**Status:** accepted

**Context.** Measured with `scripts/explore_data.py` on the raw download:
- The HF copy holds **every row twice**. Rows 10,025,911 onward repeat
  rows 0 to 10,025,910 with identical ids and sequences, but family =
  `"No such family"` (checked: 0 without a twin, 0 sequence mismatches).
- 0.45 % of sequences contain letters other than A/C/G/T (mostly `N`).
- Lengths: median 73, 90th percentile 148, 99th percentile 1,520, max 10,799.
- Family sizes are extremely skewed: median 31, but tRNA has 5,335,982.
- 83,525 sequences of ≤ 256 nt belong to families whose median is > 256
  (fragments of rRNA etc.). 13,326 more are under half their family's median.

**Decision** (`scripts/prepare_data.py`, steps 1 to 8):
1. Drop every `"No such family"` row.
2. T → U; drop any sequence with a non-ACGU letter.
3. **Length:** drop whole families with median length > **256**, then single
   sequences > 256, then sequences < **0.5 × their family's median**
   (likely fragments).
4. Remove exact duplicates within a family. Drop the 36 sequences filed
   under more than one family.
5. Keep at most **1,000** members per family, chosen with a seeded random
   draw (seed 0) over a sorted table, so the choice is reproducible.

Result: 10,025,911 → **567,579** sequences in **3,837** families.

**Alternatives rejected.**
- *Keep the placeholder rows.* Every sequence twice, and worse, a 10-million
  member pseudo-family containing a copy of every real family. The family
  split would have been 100 % leaky while looking perfectly clean.
- *Cap length at 512* (keeps 99.3 % of families instead of 95.4 %). Rough
  estimate for our planned Transformer baseline with naive attention:
  ~7.4 GB of activations at L = 512 versus ~2.7 GB at 256, on an 8 GB
  card. The oracle's O(N³) folding costs ~8× more at 512. MFE prediction
  is less reliable for long RNAs.
- *Per-sequence length filter only.* It would keep 83k short fragments of
  long RNAs (rRNA pieces cut off at contig edges), which aren't real
  molecules.
- *No family cap* (6.2 M unique sequences, dominated by tRNA and 5S rRNA):
  the model would mostly learn a handful of families. *Cap 100* (≈ 198k)
  throws away most of the variation inside large families. At 1,000, no
  family is more than 0.18 % of the data, and the corpus (≈ 60 M nt) fits
  an 8 GB laptop's training budget.

**Consequences / trade-offs accepted.**
- **185 long families are out of scope:** all rRNAs, 7SK, tmRNA, RNase P,
  group I introns, plant SRP, and others (full list in
  `data/processed/prepare_stats.json`). We can't claim anything about
  designing them.
- Large families are down-sampled, so family frequency in our data isn't
  natural frequency. The model learns "what RNA families look like", not
  "how common each one is in genomes".
- Rfam members are genome hits found by a model, so a few are mislabelled
  or partial. The fragment filter removes the obvious partials only.

---

## D-008 — Split by clan (or family), then remove held-out near-duplicates of training
**Date:** 2026-09-23   **Phase:** 1   **Logbook:** logbook/2026-09-23-session-03.md
**Status:** accepted

**Context.** Members of one RNA family are evolutionary relatives. They
share a structure and often most of their letters. With a random split,
**89.6 % of test sequences have a ≥ 80 %-identical relative in training**
(measured, `scripts/audit_leakage.py`), so test scores would measure recall
of relatives, not generalisation. Sequence-identity filters alone aren't
enough either: covariation lets family members fall below 80 % identity
while keeping the same structure, which is why deep-learning models that
score well on bpRNA's identity-filtered TS0 drop on the family-disjoint
bpRNA-new.

**Decision** (`scripts/prepare_data.py`, steps 9 and 10):
1. The unit of splitting is the **clan** when a family has one, otherwise
   the **family**. Each unit goes whole into train, val or test.
2. Units are visited in the order of SHA-256(`"0:" + unit name`), a
   reproducible pseudo-random order. Test is filled to 10 % of sequences,
   then val to 10 %, and the rest is train.
3. **Step 10:** remove every val/test sequence whose best MMseqs2 hit in
   train has **≥ 80 % identity over ≥ 80 % of its length**. Rfam doesn't
   clan every related family pair: 775 such sequences were found, mostly in
   SNORA52 ↔ snopsi28S-1192, snoR16 ↔ SNORD36, SNORA57 ↔ ceN88,
   mir-1285 ↔ Metazoa_SRP.
4. The script **asserts** that no clan, family or identical sequence occurs
   in two splits, and refuses to write the files otherwise.
5. `splits/rfam_split.tsv` (committed) lists every family and its split.

Result: train 452,867 / val 57,054 / test 56,883 sequences; 3,032 / 406 /
399 families. Byte-identical output on rerun.

**Alternatives rejected.**
- *Random split by sequence:* the leak measured above.
- *Identity-only split (e.g. CD-HIT at 80 %), as in bpRNA's TS0:* misses
  family members that diverged below 80 % identity. The literature measured
  that failure.
- *Family-only split, no clan grouping:* Rfam's clans exist precisely to mark
  families that are related, e.g. versions of one RNA in different
  kingdoms.
- *Family/clan split without step 10:* leaves 0.68 % of held-out sequences
  with near-identical training relatives (above).
- *Linking families by all-vs-all similarity and splitting connected
  components:* more thorough, but the all-vs-all search over 567k
  sequences is dominated by within-family hits, which crowd out the
  cross-family ones we care about. Step 10 plus the audit is simpler, and
  the audit shows it's enough.
- *`hash(group) % 10` assignment:* reproducible, but sequence shares would
  drift from 80/10/10 whenever a large clan lands in val/test.

**Consequences / trade-offs accepted.**
- The ≥ 80 % audit level is clean **by construction**, because step 10 uses
  the same search. The informative audit numbers are the lower levels:
  0.15 % of test sequences have any relative ≥ 50 % identity, and 1.0 % any
  detectable relative at all.
- MMseqs2 finds sequence similarity only. Two families could share a
  structure with no detectable sequence similarity. That's not leakage of
  sequences, but a model could still have "seen the shape". Checking it
  would need structure-aware search (e.g. Infernal); not done.
- Which families land in test is set by the seed. A different seed gives a
  different test set; results should ideally be repeated over several
  seeds (Phase 3 decision).
- The tRNA family (clan CL00001) landed in **val**, so the most famous RNA
  shape is never trained on. That's honest, but worth knowing when reading
  validation curves.
