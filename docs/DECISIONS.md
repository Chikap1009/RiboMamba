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

**Outcome (2026-09-25, session 04).** The pin paid off. `mamba-ssm`
2.3.2.post1 and `causal-conv1d` 1.7.0 install and run on this machine from
the authors' prebuilt wheels for exactly this stack (CUDA 12 / torch 2.10 /
C++11 ABI true / CPython 3.12 / x86_64), and a Mamba2 block runs on the
RTX 4060 under WSL2. Two details worth knowing:
- `pip install mamba-ssm` **fails** here. PyPI carries only source archives,
  and building them needs the CUDA compiler `nvcc`, which this environment
  does not have (PyTorch ships CUDA *runtime* libraries, not the compiler).
  The error is `NameError: name 'bare_metal_version' is not defined` from
  their setup script, which is really "no nvcc found". The fix is to install
  the release wheels by URL, as `environment.yml` now does.
- Installing them pulls in ~20 further packages (einops, transformers,
  tokenizers, tilelang, cutlass-dsl, z3-solver, …). Checked afterwards:
  torch 2.10.0+cu128, ViennaRNA 2.7.2, polars and numpy unchanged, and all
  79 tests still pass. `environment.lock.yml` is deliberately **not**
  regenerated: it is the snapshot of the environment at the Phase 3 protocol
  freeze, and rebuilding the evaluation oracles from it must stay possible.

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
- *Superseded in part by D-009:* the "structure-aware search not done"
  limitation above was an effort shortcut and has been removed (step 11).

---

## D-009 — Structure-aware leakage check with Rfam's own covariance models (step 11)
**Date:** 2026-09-23   **Phase:** 1   **Logbook:** logbook/2026-09-23-session-03.md
**Status:** accepted

**Context.** MMseqs2 compares letters. Covariation lets family relatives
drift far apart in letters while keeping every base pair, so a letters-only
check can miss real relatives across splits. D-008 listed "structure-aware
search not done" as a limitation. That was an effort shortcut, which
CLAUDE.md §1.3 (amended session 03) now rules out.

**Decision.**
1. Use **Infernal 1.1.5** `cmscan` with the **Rfam 15.0** covariance models:
   the release the HF dump was built from (all 459 of its family→clan pairs
   match 15.0's `Rfam.clanin`; 14.10 misses 14). Pinned URL + SHA-256
   recorded on first download (Rfam publishes no checksums).
2. **Leakage = membership.** A held-out sequence scoring ≥ the **GA
   (gathering) threshold** of a **training** family's model is one Rfam
   would call a member of that family. **Step 11** of `prepare_data.py`
   removes such sequences from val/test.
3. Flags follow Rfam's own recipe: `--nohmmonly` (score every model as a
   full CM), `--toponly` (each RNA in its own orientation), `--rfam` (Rfam's
   fast pre-filters), reporting E ≤ 0.01; GA applied by us from the model
   file.
4. The audit (`scripts/audit_structural.py`) adds a **positive control**
   (is each held-out sequence's own family found?), a **negative control**
   (dinucleotide-shuffled sequences: the false-alarm rate), and a
   **filter-sensitivity check** (Infernal's slower default filters on a
   2,000 sample).
5. Results are **cached per sequence** (valid because a sequence's hits and
   E-values were shown to be independent of the rest of the batch), in
   chunks committed as they finish.

Result: step 11 removed **12** held-out sequences (val 2, test 10):
snoR16→SNORD36 8, SNORD2→SNORD36 2, ceN109→SNORD36 1, SNORA36→SNORA51 1.
Final split **452,867 / 57,052 / 56,873**.

**Alternatives rejected.**
- *Keep the letters-only audit and state the limitation.* Rejected under
  §1.3; the check is feasible (≈ 2 h CPU).
- *Weak resemblance (E ≤ 10⁻³ below GA) as leakage.* Such hits mostly mean
  "same kind of RNA" (e.g. microRNA precursors are all ~70-nt hairpins).
  That's class-level knowledge a model should be able to use on new
  families; no split can remove it. It's reported, next to the negative
  control, but not filtered.
- *Default (more sensitive) filters for the full scan.* ≈ 20 h of CPU
  (11× slower, measured). Replaced by check D, which measures on a sample
  whether the fast filters miss membership-level hits.
- *Scanning without `--nohmmonly`* (the first attempt): **wrong.** 347 of
  the 4,178 models have zero base pairs, and without the flag cmscan scores
  them with a letters-only HMM whose bit scores aren't on the scale their
  GA thresholds were set on. Measured on the same 106,191 sequences: own
  family found for zero-pair families **87.93 % → 99.99 %** with the flag;
  unchanged (99.54 %) for families with pairs.
- *Cache keyed by the whole input file.* Any change to the held-out set
  (e.g. removing 12 sequences) would force a new 2-hour scan.

**Consequences / trade-offs accepted.**
- `prepare_data.py`'s first run takes ≈ 2 h; later runs take ≈ 24 s
  (cache). The output is byte-identical either way.
- The GA criterion inherits Rfam's curation: families whose GA is set
  loosely or tightly make the check correspondingly looser or stricter.
- With the fast filters, check B (member of a train family) is zero by
  construction; check D is the independent evidence.

---

## D-010 — The Transformer denoiser, and framing every sequence with `<bos>`/`<eos>`
**Date:** 2026-09-24   **Phase:** 2   **Logbook:** logbook/2026-09-23-session-03.md (00:24)
**Status:** accepted (size provisional until the VRAM/throughput measurement, D-011)

**Context.** Masked diffusion needs a denoiser: partly masked sequence in,
a distribution over A/C/G/U per position out, looking both ways. Phase 4
swaps this box for BiMamba, so the interface must be backbone-agnostic and
the Transformer must be a strong, standard baseline, not a strawman.

**Decision.**
- **Architecture:** pre-norm Transformer encoder; multi-head
  self-attention via PyTorch's fused `scaled_dot_product_attention`;
  rotary position encoding (RoPE); GELU MLP ×4; no biases in linear
  layers; GPT-2 initialisation (std 0.02, residual output layers
  ÷ √(2N)). Starting size d = 384, 8 layers, 6 heads = 14.17 M parameters.
- **No time input**: the masks themselves show the noise level, and the
  optimal prediction for absorbing diffusion doesn't depend on t (Ou et al.
  2024).
- **Special tokens are never predicted**: their logits are −∞.
- **Every sequence is framed `<bos> x₁…x_L <eos>`**; markers are never
  masked or scored.

**Why the framing (measured, not assumed).** With an all-`<mask>` input,
every position holds the same vector, so every attention output is the
same, whatever the weights. RoPE only encodes relative offsets, and padding
is invisible to attention, so the model cannot know where the molecule
begins or ends. On a 4-sequence memorisation task, bits/nt at t = 1 were
2.11 without markers (no better than knowing nothing) versus 1.58 with them
(near the 1.6-bit optimum). Generation starts at 100 % masked, where the
blindness is total, and RNA has strongly end-dependent features (the ends
of a molecule often pair with each other; tRNAs end in CCA). The markers
cost no parameters: the tokens were reserved in Phase 1 (D-006).

**Alternatives rejected.**
- *Learned absolute position embeddings*: add L_max × d parameters (which
  complicates parameter matching with Mamba), give distance from the start
  but not distance to the end, and don't generalise past the table.
- *Sinusoidal absolute positions*: same end-blindness; RoPE's relative
  offsets suit motifs that mean the same thing anywhere.
- *A time-conditioned denoiser (as in image diffusion)*: extra machinery
  with no theoretical benefit for absorbing diffusion, and it would need a
  separate design for Mamba.
- *Post-norm blocks* (the original 2017 Transformer): less stable to train
  at depth without careful warmup.
- *Naive attention* (store the L × L grid): memory grows with L²; the fused
  kernel computes the same thing in tiles.

**Consequences / trade-offs accepted.**
- Two extra tokens per sequence (≈ 2 % more compute at a median length of 93).
- The BiMamba and autoregressive Mamba must use the same framing, so the
  comparison stays like-for-like (the AR model needs `<bos>`/`<eos>`
  anyway).

---

## D-011 — Model size, token-budget batches, training recipe, and a pre-registered LR sweep
**Date:** 2026-09-24   **Phase:** 2   **Logbook:** logbook/2026-09-23-session-03.md (00:40)
**Status:** accepted (size revisit condition below)

**Context.** Measured with `scripts/measure_memory.py` (bf16, AdamW,
worst-case length 256 + 2): 7.44 of 8.59 GB free (the Windows display uses
the rest). Peak memory at a 16,384-token batch: S 4.7 M params 1.2 GB,
**M 14.2 M 2.4 GB**, L 25.2 M 3.3 GB, XL 37.8 M 4.9 GB. Throughput ≈ 270 /
**105–125** / 68 / 46 thousand nucleotides/s. Throughput barely depends on
sequence length (64 vs 256). **XL at 32k tokens needed 9.05 GB: WSL spilled
into system RAM and a step took 6.2 s instead of 0.36 s**, with no error
raised.

**Decision.**
1. **Size M** (d 384, 8 layers, 6 heads, 14.17 M parameters) for the
   Phase 2 baseline, and as the parameter target for the Phase 4 models.
2. **Batches by token budget:** 16,384 padded slots per batch (median 140
   sequences, 3,015 batches per epoch, 0.9 % padding), not a fixed number
   of sequences, so every step costs about the same memory and time.
3. **Recipe:** AdamW (β = 0.9/0.98, weight decay 0.1 on matrices and
   embeddings only), linear warmup then cosine decay to 10 % of the peak,
   bf16 autocast, gradient-norm clipping at 1.0, EMA of the weights (0.9999,
   with a warm-up), validation bits/nt on the full validation set with fixed
   noise, atomic checkpoints with config and git commit, resumable.
4. **Learning rate from a pre-registered sweep** (`scripts/lr_sweep.py`):
   3×10⁻⁴, 10⁻³, 3×10⁻³, 8,000 steps each with a full schedule; the lowest
   final EMA validation bits/nt wins. The rule was written before any sweep
   result existed. The same protocol is applied to every backbone in
   Phase 4.
5. **Full run: 200,000 steps** (≈ 3.3 B nucleotide-tokens, ≈ 66 epochs,
   ≈ 9 h at 105k nt/s), evaluated every 5,000 steps; `best.pt` keeps the
   best EMA validation state.

**Alternatives rejected.**
- *S*: likely capacity-limited for ~3,000 families. *L/XL*: 1.6–2.4× the
  cost per run, multiplied by the ~9–12 runs Phase 4 needs, and XL's
  headroom is gone at larger batches.
- *Fixed sequences per batch*: a batch of short sequences uses the GPU
  poorly, and a batch of long ones sets the memory ceiling.
- *32k-token batches*: fits for M (4.5 GB), but halves the number of
  updates per epoch; 16k is a conventional small-model batch, revisitable.
- *Hand-picking the learning rate*, or tuning it longer for one backbone
  than another: either would weaken or bias the comparison.
- *`torch.compile`*: could speed training, but it adds compile-time
  failure modes and would have to be verified for the Mamba kernels too;
  not needed at this throughput.

**Consequences / trade-offs accepted.**
- The best learning rate for 8,000 steps may be slightly higher than the
  best for 200,000; standard practice, stated as a limitation.
- 66 epochs is many passes over 452k sequences. Masked diffusion models are
  reported to keep benefiting from repeated data longer than
  autoregressive ones do, but validation is on unseen families, so
  overfitting will show directly; `best.pt` guards against it.
- **Revisit condition for size:** if validation is still falling steadily
  at the end of the full run, the model is capacity- or compute-limited and
  a larger size is warranted, for all backbones alike.
- Operational: keep peak memory well below the free VRAM and watch step
  time, because exceeding it under WSL slows everything silently.

**Amendment, 2026-09-24 01:50 — boundary rule for the learning-rate sweep.**
The Transformer sweep gave final EMA validation bits/nt 1.9138 (3×10⁻⁴),
1.9252 (10⁻³), 1.9441 (3×10⁻³). The winner sat on the **edge** of the
grid, so the true optimum may lie below it, and the pre-registered rule
had no provision for that (an oversight in the protocol). Added rule 2b:
while the winner is the smallest or largest value tried, add the next value
on the half-decade grid in that direction (…, 10⁻⁴, 3×10⁻⁴, 10⁻³, …) and
re-apply the same rule. The amendment was made **after** seeing the
Transformer sweep and **before** any other backbone's sweep, and it is a
symmetric, mechanical rule applied identically to every backbone, so it
cannot favour one architecture. The full run that had started with 3×10⁻⁴
was stopped at step ~500 (no checkpoint yet) and restarts with the winner
of the extended sweep.

**Amendment, 2026-09-25 (session 05) — diverged candidates rank last.** A
candidate whose training loss becomes inf or nan is recorded as diverged and
ranks last (+∞) in the learning-rate and dropout sweeps; the sweep carries
on; if all candidates diverge, it stops. Written before any Mamba run, for
the same reasons as the boundary rule: mechanical, symmetric, and it changes
no Transformer result (none diverged). Recorded in the frozen protocol as
amendment A1 (RESULTS.md).

**Amendment, 2026-09-26 (session 05) — rule 2b really repeats until the
winner is interior.** The code's grid ended at 10⁻², and when BiMamba's
winner reached it (10⁻² at 1.9086, the largest value tried) the sweep stopped
quietly instead of trying 3×10⁻² as this rule's text requires. The grids are
now wide (learning rate 10⁻⁶…1, dropout 0…0.7) and running off either end
raises. A bug fix that restores the written rule, identical for every
backbone, changing no Transformer result (tested by replaying its sweep).
Amendment A2 in RESULTS.md.

---

## D-012 — Regularise with dropout, chosen by a pre-registered sweep over shorter full schedules
**Date:** 2026-09-24   **Phase:** 2   **Logbook:** logbook/2026-09-23-session-03.md (04:15)
**Status:** accepted (written before any dropout run existed)

**Context.** The planned 200,000-step run (D-011, lr 3×10⁻⁴) **overfit**:
validation bits/nt on unseen families was best at step 10,000 (1.9020,
≈ 3.3 epochs) and worsened steadily to 1.9348 at step 45,000, while
training fell from ≈ 1.96 to 1.41. The model memorises training families
instead of learning what transfers. D-011 had flagged the risk ("66 epochs
is many passes"), but the run length was set too long, a planning error
caught by the validation curve. The run was stopped at step 46,100
(resumable). Its `best.pt` (1.9020) is kept as a reference.

**Decision.**
1. Add **dropout** to the Transformer: on the attention weights and on the
   output of each residual branch (attention, MLP), active only in
   training (`TransformerConfig.dropout`, `--dropout`).
2. **Pre-registered sweep** (`scripts/dropout_sweep.py`): dropout ∈ {0,
   0.1, 0.2} at the learning rate chosen in D-011 (3×10⁻⁴); **30,000
   steps** each (≈ 10 epochs) with a complete warmup + cosine schedule;
   evaluation every 2,500 steps; early stopping via `best.pt`.
   **Rule:** lowest *best-during-run* EMA validation bits/nt; if the winner
   is the largest rate tried, extend the grid (0.3, 0.4).
3. The dropout-0 run doubles as a control: it separates the effect of the
   shorter, fully annealed schedule from the effect of dropout.
4. **The identical protocol (LR sweep → dropout sweep, same steps and rules)
   applies to every backbone in Phase 4.**

**Alternatives rejected.**
- *Early stopping on the long run alone* (use its step-10k checkpoint):
  that checkpoint was taken with the learning rate still near its peak,
  never annealed; a schedule that fully decays by the best point usually
  does better, and the comparison needs a principled, repeatable recipe.
- *Smaller model* (S, 4.7 M): capacity reduction is a blunter tool, and it
  changes the parameter target for Phase 4; kept in reserve if dropout
  doesn't close the gap.
- *More weight decay*: a second knob to sweep; dropout is the standard first
  regulariser for Transformers of this size.
- *More data*: the limit is the number of **families** (3,032 in train), not
  sequences; raising the per-family cap adds relatives of families already
  memorised.

**Consequences / trade-offs accepted.**
- ≈ 4.5 h of GPU for the sweep (replacing ≈ 7 h the long run would still
  have spent overfitting).
- The large train–validation gap may partly be irreducible (unseen
  families genuinely differ); the sweep measures how much regularisation
  can recover. That gap is itself a result worth reporting.

**Outcome (2026-09-24 08:49).** Best-during-run EMA validation bits/nt:
dropout 0 → **1.9040** (step 10k), 0.1 → 1.9081 (12.5k), 0.2 → 1.9178
(12.5k). **Dropout 0 chosen by the rule.** Dropout slowed learning but did
not stop overfitting: every run peaks at ≈ 3–4 epochs. The Phase 2
baseline is `tf_M_do0/best.pt` (step 10,000). For Phase 4 the same
protocol stands (LR sweep, then dropout sweep {0, 0.1, 0.2} × 30k steps,
best-during-run), because a Mamba backbone may respond to dropout
differently; only the rule is fixed, not the answer.


---

## D-013 — A second, independent folding oracle: EternaFold, used for structure-level checks only
**Date:** 2026-09-24   **Phase:** 3   **Logbook:** logbook/2026-09-24-session-04.md (13:18)
**Status:** accepted

**Context.** Every structural number in this project comes from one
oracle, ViennaRNA 2.7.2 with Turner 2004 parameters. The oracle is a model
with quirks (special bonuses for particular hairpin loops, approximations
for dangling ends, no pseudoknots). Phase 5 will *steer* generation with
it, and a generator optimised against one imperfect scorer can learn its
quirks and score well without being good (Goodhart's law). We need a way to
tell "good RNA" from "good at pleasing ViennaRNA".

**Decision.** Add **EternaFold 1.3.1** (bioconda; Wayment-Steele et al.,
Nature Methods 2022) as a second oracle, pinned in `environment.yml`, and:
1. use it only for **structure-level** outputs: its single most probable
   structure (`--viterbi`, the same kind of estimate as an MFE structure)
   and its base-pair probabilities, from which we compute ensemble defects;
   never its raw scores, which are not kcal/mol;
2. ViennaRNA remains the primary oracle and the only one used for steering
   or selection; results are *reported* under both, with their agreement;
3. run it through `mpirun` (≥ 2 processes) in batches, because the bioconda
   build is compiled for MPI and otherwise never finishes.

**Alternatives rejected.**
- *RNAstructure:* a different program, but built on the same Turner
  nearest-neighbour parameters, so it shares ViennaRNA's blind spots; weak
  independence.
- *CONTRAfold:* EternaFold's predecessor (same model class), trained on
  far less data, mostly natural structures.
- *LinearPartition / LinearFold:* faster approximate algorithms, not a
  different model (they run with ViennaRNA's or CONTRAfold's parameters).
- *A 3D or deep-learning predictor:* much more expensive, less reliable for
  RNA, and deep-learning structure predictors are known to generalise
  poorly across families, which is exactly our test condition.
- *EternaFold's default MEA estimator for "predicted structure":* a
  different estimator (maximises expected accuracy, and allows isolated
  pairs with gamma = 6); the Viterbi structure is the like-for-like
  counterpart of an MFE structure.

**Consequences / trade-offs accepted.**
- EternaFold was trained partly on natural structures. Its training data
  overlaps our validation set only for tRNA (0.30 % of validation sequences
  have a ≥ 50 %-identical relative in it); the test-set version of this
  check runs after the protocol freeze.
- Two oracles can still share blind spots (both are secondary-structure
  only, both ignore pseudoknots and 3D contacts). Agreement is evidence, not
  truth; there is still no wet-lab validation.
- ~221 MB of extra packages (EternaFold pulls in a C++ toolchain and
  OpenMPI).

---

## D-014 — How the harness measures, and how architectures will be compared
**Date:** 2026-09-24   **Phase:** 3   **Logbook:** logbook/2026-09-24-session-04.md
**Status:** accepted 2026-09-24 with the protocol freeze (Chirag approved all
five open recommendations: five seeds, a replication split, Eterna100 as a
secondary set, T = 1.0, and 256 steps rather than the rule's 16)

**Context.** Phase 4's question, whether a BiMamba backbone generates more
designable RNA than a Transformer or an autoregressive Mamba, will be
answered by whatever the harness measures. Common metrics can be won by
trivial cheats (low MFE by GC-rich letters, novelty and diversity by random
letters, MFE match by flimsy designs), and a single trained model per
architecture says nothing about the architecture.

**Decision.**
1. **Graded ensemble measures, not exact-structure ones.** The ensemble
   defect (NED) is the headline structural measure; P(target), MFE match and
   the energy gap are reported but carry no unconditional claim. Measured
   reason: on real 74–223-nt RNAs the exact structure's probability is
   0.000–0.07 and the nearest rival is a one-pair variant at ≈ 0 kcal/mol.
2. **Structure beyond chance** by 50 dinucleotide shuffles per sequence
   (`beats_shuffles`, ties counted half, so chance is exactly 0.5).
3. **Every number on a calibrated scale:** five length-matched reference
   sets (real, a second real sample, training, shuffled, random), and
   generated samples drawn with the reference's lengths one-to-one.
4. **Two oracles:** ViennaRNA primary; EternaFold as the robustness check
   (D-013).
5. **Architecture claims at the level of trained models:** five training
   seeds per architecture, exact seed-level permutation test, Holm across
   the five primary tests; bootstrap intervals (family-cluster for real
   sequences) for effect sizes.
6. **Sampling at T = 1.0** for the primary comparison (no per-model
   tuning), **256 steps for every model**. The rule written before the
   ablation returned 16 for the Transformer; it was not adopted because a
   step count at which one backbone has plateaued could handicap a
   backbone that benefits from more steps, and 16 vs 256 is result-neutral
   for the baseline (0.565 vs 0.570).
7. **Pre-registration enforced in code**: the test split cannot be loaded
   until RESULTS.md carries "Status: FROZEN on <date>".

**Alternatives rejected.**
- *Raw MFE or MFE per nucleotide as quality:* rewards composition (a
  GC-rich random 80-mer: −26.0 kcal/mol but z = +1.46 against its shuffles).
- *P(target) or MFE match as the headline:* a frame error rate where a bit
  error rate is needed; can reverse architecture rankings.
- *Three training seeds:* the exact seed-level test can then never reach
  p < 0.05 (minimum 2/20 = 0.10). This was my first recommendation, and it
  was wrong.
- *Bootstrap over one model's samples as evidence about an architecture:*
  captures sampling noise, not training-seed variation.
- *Choosing the best temperature per model:* a tuning knob that could
  favour one architecture; T = 1.0 is the distribution each model actually
  learned. The full temperature curve is reported for all as secondary.
- *Fréchet-style distances in a pretrained RNA language model's embedding
  space:* their scale depends on a model that may have been trained on our
  held-out families; replaced by calibrated Wasserstein and k-mer distances
  on interpretable quantities.
- *Diversity as a score to maximise:* 57 % of real validation sequences
  have a ≥ 80 % sibling among 1,000; diversity is a guardrail against
  collapse instead.

**Consequences / trade-offs accepted.**
- Five seeds per architecture costs ≈ 4 extra 30,000-step runs per
  backbone (≈ 5–6 GPU-hours each at Transformer speed).
- The seed-level exact test is conservative: with five seeds and Holm over
  five tests, a claim needs near-complete separation of the seeds. A "no
  detectable difference" outcome would be a limit of five seeds, and effect
  sizes with intervals are reported regardless.
- Validation numbers depend on one split draw (seed 0); the proposed
  replication split addresses this descriptively.

---

## D-015 — Match the Mamba models' parameters to the Transformer by depth, not by width
**Date:** 2026-09-25   **Phase:** 4   **Logbook:** logbook/2026-09-25-session-05.md (14:40, 19:18)
**Status:** accepted (Chirag's decision, after concept instalment 3 and the measurements)

**Context.** The frozen protocol (P4) requires every compared model to hold
14,174,976 ± 2 % parameters. A Mamba-2 layer at the Transformer's width (384)
holds 993,572 parameters, 56 % of a Transformer block (1,771,008), so the
Mamba models must be deeper or wider than the Transformer.

**Decision.** Match by depth: width 384 as the Transformer, 14 Mamba layers
for both Mamba models, library-default Mamba-2 settings (head size 64, state
128, expansion 2, convolution width 4). BiMamba 14,010,608 parameters
(−1.16 %), AR Mamba 13,927,672 (−1.74 %). Enforced in code: `train.py`
refuses any run outside ±2 % (`check_parameter_budget`).

**Alternatives rejected.**
- *Match by width* (keep 8 layers, widen each). No standard setting lands
  inside ±2 %: widths move in steps of about 5.8 % of the target when heads
  must stay whole. BiMamba fits only at d 512 with head size 32 (−1.94 %);
  the AR model only at d 528 with head size 32 **and** state 64 (−0.27 %). The
  two Mamba models would end up with different state sizes, and both would
  differ from the Transformer in width as well as in mixing: two changes at
  once. Measured advantage: 15–25 % faster for BiMamba, 6–8 % for AR Mamba.
- *Exact matching by fractional tricks* (e.g. a non-integer expansion or an
  extra partial layer): non-standard architectures no one else uses, for a
  gain inside the tolerance the protocol already allows.

**Why depth** (the reasons given with the recommendation, which Chirag chose over width). It fits the ±2 % window
at standard settings for both Mamba models; it changes one thing only (same
width, embedding, head and per-position vector as the Transformer); it
follows the Mamba papers' own convention (two Mamba layers per Transformer
block at equal width), so our numbers compare with published ones.

**Consequences / trade-offs accepted.** Slower training per step:
depth-matched BiMamba 465 ms vs the Transformer's 162 ms at L 256 (646 vs
153 at L 64), AR Mamba 239 ms (RESULTS.md, "Memory and speed of the full
Phase 4 models"). The protocol matches steps and tokens, not wall-clock, so
this costs time, not fairness: ≈ 70 GPU-hours for the Mamba models' part
of P4. Fourteen layers mean fourteen chances for information to cross the
sequence, against the Transformer's eight; that difference is part of what
"a Mamba backbone at matched size" means, and is reported as such.

---

## D-016 — How the Mamba models are built: shared projections, per-direction scans, everything else as the Transformer
**Date:** 2026-09-25   **Phase:** 4   **Logbook:** logbook/2026-09-25-session-05.md (14:40, 14:50–15:32)
**Status:** accepted (my choice within the build, explained to Chirag in concept instalment 3; open to his veto)

**Context.** Phase 4 swaps the Transformer denoiser for a Mamba-2 one and adds
a left-to-right Mamba. A Mamba-2 layer reads in one direction only, but a
masked-diffusion denoiser needs both sides of a hidden letter (its pairing
partner is often to its right). Several ways to make Mamba bidirectional
exist, they differ in parameters per layer (so in depth at matched size), and
everything around the mixer must be settled so that only the mixing differs
between the compared models.

**Decision.**
1. **BiMamba layer:** one shared `in_proj` (d → z, x, B, C, Δ) and one shared
   `out_proj` (768 → d); each direction has its own short causal convolution,
   Δ bias, A (keep factors), D (skip) and gate-normalisation weight. The
   forward scan reads the sequence; the backward scan reads each sequence
   reversed **within its own length** (padding stays last); the two outputs
   are added, then projected once. 1,000,264 parameters per layer at d = 384.
2. **AR Mamba layer:** the library's `Mamba2` unchanged (one direction).
3. **Around the mixer, copy the Transformer:** the same embedding, pre-norm
   residual blocks with LayerNorm, final LayerNorm, untied linear head,
   residual-branch dropout (D-012's knob), `<bos>`/`<eos>` framing (D-010).
   No separate MLP (the standard Mamba layer has none).
4. **Initialisation:** the library's own (Mamba2's constructor; its GPT-2-style
   `out_proj` rescale by 1/√n_layers); embedding and head normal(0, 0.02) as
   the Transformer.
5. **Forbidden outputs:** BiMamba never predicts a special token (as the
   Transformer); the AR model may predict `<eos>` (it must end sequences).

**Alternatives rejected.**
- *Two complete Mamba-2 mixers per layer* (1,987,912 parameters): at matched
  size only 7 layers, half the depth of the other designs.
- *One mixer used for both directions:* no direction-specific parameters, but
  RNA is directional: the stack 5′-GC-3′/3′-CG-5′ is −3.40 kcal/mol, the
  same letters as 5′-CG-3′/3′-GC-5′ −2.40 (ViennaRNA 2.7.2, checked).
- *Alternating directions by layer:* right-hand context reaches a position
  only every other layer; the two directions are treated unequally.
- *Hydra (Hwang et al. 2024), a principled bidirectional Mamba-2:* not in the
  installed library; it would mean new, unvalidated kernel code.
- *Flipping whole padded rows* (the obvious implementation): puts padding
  first in the backward scan, which has no mask, so padding would write into
  every real position's state. A test pins that padding cannot change any
  real output, and a deliberately broken version fails it.
- *RMSNorm in the residual blocks* (Mamba's usual choice): LayerNorm keeps
  everything outside the mixer identical to the Transformer.
- *Calling `Mamba2.forward` twice per layer:* computes the 384 → 1,804 input
  projection twice; since it acts per position, one projection reversed is
  identical and cheaper.

**Precedent.** The sharing pattern is that of Vision Mamba (Zhu et al. 2024)
and Caduceus (Schiff et al. 2024), both Mamba-1 models. Adapted to Mamba-2,
where the B, C and Δ projections sit inside `in_proj`, those projections are
shared too; each direction still convolves x, B and C with its own weights.

**Consequences / trade-offs accepted.**
- Per layer, BiMamba runs two scans; its cost per step exceeds the AR
  model's (measured before the long runs, RESULTS.md).
- The direction-specific part is small (5,924 parameters per layer). If
  BiMamba underperforms, "too little direction-specific capacity" is one
  hypothesis we cannot rule out; the two-full-mixers design would test it.
- Correctness rests on a test that compares the fused kernels with a
  step-by-step loop of the textbook recurrence, each sequence processed alone.
