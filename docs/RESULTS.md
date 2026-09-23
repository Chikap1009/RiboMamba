# Results — RiboMamba

Two rules govern this file (CLAUDE.md §3.5):

1. **Thresholds are frozen before results are seen.** The "Frozen evaluation
   protocol" section below is filled in and dated *before* any test-set
   evaluation runs. After that date it is never edited, only appended to with
   a dated, explained amendment.
2. **Every number is reproducible.** Next to every number goes the exact
   command, commit hash and random seed that produced it.

---

## Frozen evaluation protocol

*(Not yet written. To be completed in Phase 3, before any test-set evaluation.)*

---

## Train/test overlap audit

Recorded 2026-09-23, session 03 (final version after step 11, 22:08). Code
at commit `a58ab08` (cleaning, split, steps 10–11, both audits) and
`629c93e` (downloads). Data: `multimolecule/rfam` at `25e8aa8…`,
`multimolecule/bprna` at `423465b…`, Rfam 15.0 `Rfam.cm.gz` (SHA-256
verified, D-005, D-009). Tools: MMseqs2 18.8cc5c, Infernal 1.1.5. All seeds
= 0. Deterministic: rerunning `prepare_data.py` gives byte-identical files.

**Reproduce** (inside `conda activate ribomamba`, from the repo root):

```
python scripts/download_data.py      # pinned files, checksums verified
python scripts/explore_data.py       # raw-data numbers that set the thresholds
python scripts/prepare_data.py       # clean + split -> data/processed/, splits/rfam_split.tsv
                                     #   (first run ~2 h: step 11 scans 113,937 sequences; cached after)
python scripts/audit_leakage.py      # letter-based checks 1-4  -> data/processed/audit.json
python scripts/audit_structural.py   # structure-based checks A-D -> data/processed/audit_structural.json (~20 min)
```

Output checksums (SHA-256, `sha256sum data/processed/*.parquet splits/rfam_split.tsv`):

```
05d8a552b73cc559fb7e955ca14627cdae41112d1a060bbb53e385e4433439f3  data/processed/test.parquet
012c03a8a1b782daf5e0a64403bf3d8ac1b6ae8f2b7e50194acf6ad618eecd5d  data/processed/train.parquet
5bb7499bfa36e69ff3383af8413a4f766f340dc1ac258bc248b1be52044a7625  data/processed/val.parquet
1913c634f6f131a3cea18e8377ae5016bdea9649d027deeb05b9291cc3170b48  splits/rfam_split.tsv
```

### The data after cleaning (D-007) and splitting (D-008, D-009)

| | sequences | share | families | split units (clan or family) | median length |
|---|---|---|---|---|---|
| train | 452,867 | 79.9 % | 3,032 | 2,830 | 93 |
| val | 57,052 | 10.1 % | 406 | 371 | 92 |
| test | 56,873 | 10.0 % | 399 | 371 | 96 |

Cleaning funnel: 20,051,822 raw rows → 10,025,911 after removing the
duplicated `"No such family"` copy → 9,981,218 ACGU-only → 9,590,462 after
dropping 185 families with median length > 256 → 9,547,361 ≤ 256 nt →
9,534,330 after the fragment filter → 5,730,590 after exact-duplicate removal
→ 5,730,554 single-family → **567,579** after the 1,000-per-family cap →
566,804 after step 10 (letter-level near-twins of train: −200 val, −575
test) → **566,792** after step 11 (structural members of a train family:
−2 val, −10 test: snoR16→SNORD36 8, SNORD2→SNORD36 2, ceN109→SNORD36 1,
SNORA36→SNORA51 1).

### Letter-based leakage checks (`audit_leakage.py`)

**Checks 1–2 — shared labels or identical sequences between any two splits:
0 clans, 0 families, 0 sequences** (train–val, train–test, val–test). Also
enforced by an assertion in `prepare_data.py`.

**Check 3 — nearest training relative of held-out sequences.** 2,000
held-out sequences sampled per row (seed 0); each searched against **all**
training sequences with MMseqs2 (nucleotide, forward strand, E ≤ 10⁻³). A
hit counts toward an identity level only if it covers ≥ 80 % of the query.
± = 95 % confidence half-width (normal approximation).

| split scheme / held-out set | any detectable relative | median best identity | ≥ 50 % | ≥ 80 % | ≥ 90 % | ≥ 95 % | 100 % |
|---|---|---|---|---|---|---|---|
| **ours** / val | 1.40 % | 0 | 0.00 % | 0 * | 0 * | 0 * | 0 * |
| **ours** / test | 1.05 % | 0 | 0.40 % ± 0.28 | 0 * | 0 * | 0 * | 0 * |
| **random split (control)** / test | **96.5 %** | **0.960** | 93.3 % ± 1.1 | **90.3 % ± 1.3** | 76.2 % ± 1.9 | 56.0 % ± 2.2 | 5.9 % ± 1.0 † |

\* Zero **by construction**: step 10 removed every held-out sequence with a
≥ 80 %-identity, ≥ 80 %-coverage training hit, using the same search. Before
step 10 the family/clan split alone gave 1.2 % ± 0.5 of test at ≥ 80 % (775
of 114,712 held-out sequences, 17 families; D-008). The ≥ 50 % and "any
relative" columns are the informative ones for our split.
† Not exact duplicates (the pool has none): 100 % identity over ≥ 80 % of
the query, e.g. one sequence is the other plus a few letters at an end.
An earlier run on the pre-step-11 split (a different 2,000-sequence draw)
gave random-control ≥ 80 % = 89.6 % ± 1.3 and ours/test ≥ 50 % = 0.15 % ±
0.17: consistent within sampling error.

**Check 4 — bpRNA-1m sequences that occur letter for letter in our splits**
(of 70,035 distinct bpRNA sequences): train **17,086**, val 1,860, test
2,036. So any bpRNA structure used as a design target in Phase 3 must be
screened against our train split first.

### Structure-based leakage checks (`audit_structural.py`, D-009)

Every held-out sequence (**113,925**) scanned with Infernal `cmscan
--nohmmonly --toponly --rfam -E 0.01` against all **4,178 Rfam 15.0
covariance models**. "Member" = bit score ≥ that model's GA threshold (the
rule Rfam uses to define family membership). "Weak hit" = E ≤ 10⁻³ but not
necessarily ≥ GA. Controls on a 2,000-sequence sample (seed 0). ± = 95 %
half-width.

| check | result |
|---|---|
| **A. positive control:** own family found at GA (all 113,925) | **99.55 % ± 0.04** |
| **B. leakage:** member of a *train* family (all) | **0** (by construction: step 11 removed these, same scan) |
| **C. weak hit to a train family** (all) | 4.59 % ± 0.12 |
| C. — same, on the 2,000 sample | 4.55 % ± 0.91 |
| C. **negative control:** same 2,000, dinucleotide-shuffled — weak hit to a train family | **0.10 % ± 0.14** |
| C. negative control — member of *any* family | 0 |
| **D. filter sensitivity** (2,000 sample): member of a train family, Rfam's fast filters / Infernal's default filters | **0 / 0** (95 % upper bound ≈ 0.15 % by the rule of three) |
| D. own family found at GA, fast / default filters | 99.6 % / 99.7 % |
| D. weak hit to a train family, fast / default filters | 4.55 % / 9.1 % ‡ |

‡ The slower default filters find about twice as many *weak* hits (they're
more sensitive), but **no additional membership-level hits**, which is the
leakage criterion. The negative control was run with the fast filters, so
compare 4.55 % against 0.10 %.

**Interpretation.**
- The detector can see: it recovers held-out sequences' own family 99.55 %
  of the time (A).
- No held-out sequence is a member of a training family by Rfam's own rule
  (B), and slower, more sensitive filtering finds none either (D).
- About 4.6 % of held-out sequences weakly resemble some training family:
  ~45× the shuffled noise floor (C), so the resemblance is real. It's
  class-level ("also a hairpin-shaped microRNA"), below membership
  thresholds. That's knowledge a model *should* transfer to new families,
  and no split could remove it. It's reported, not filtered (D-009).

**What the `--nohmmonly` fix changed** (same 106,191 held-out sequences,
first scan without the flag vs final scan with it): own family found at GA
for zero-base-pair families (7,617 seqs) 87.93 % → **99.99 %**; families
with pairs (98,574 seqs) 99.54 % → 99.54 %; overall 98.70 % → 99.57 %.
Logbook 2026-09-23 session 03, 19:37 and 21:48.

**Known limits of these audits.** The test set is one draw (seed 0). Rfam
family labels and GA thresholds are curator- and model-assigned; the
structural check is as strict as Rfam's thresholds are. Weak class-level
resemblance remains by design.

---

## Phase 0 — oracle sanity checks (not experiments)

Hand-calculated predictions from session 01, checked against ViennaRNA.
Deterministic (no randomness, so no seed). No project code is involved; the
numbers depend only on ViennaRNA **2.7.2** as pinned in `environment.yml`
(default Turner 2004 parameters). Run inside `conda activate ribomamba`.
Recorded 2026-09-22, session 02.

| Sequence | Condition | Result | Command |
|---|---|---|---|
| `GGGAAACCC` | 37 °C | MFE `(((...)))` −1.20 kcal/mol | `echo GGGAAACCC \| RNAfold --noPS` |
| `GGGACCC` | 37 °C | MFE `.......` 0.00 | `echo GGGACCC \| RNAfold --noPS` |
| `GGGAAACCA` | 37 °C | MFE `((....)).` −1.90 | `echo GGGAAACCA \| RNAfold --noPS` |
| `GGGAAACCC` | 37 °C | nearest rival `((....)).` −1.00 (gap 0.20) | `echo GGGAAACCC \| RNAsubopt -e 4 -s` |
| `GGGAAACCC` | 37 °C | MFE shape frequency in ensemble 0.5065 | `echo GGGAAACCC \| RNAfold --noPS -p` |
| `GGGAAACCA` | 37 °C | MFE shape frequency in ensemble 0.9386 | `echo GGGAAACCA \| RNAfold --noPS -p` |
| `GGGAAACCC` | 70 °C | MFE `.........` 0.00; `(((...)))` = +1.39 | `echo GGGAAACCC \| RNAfold --noPS -T 70`; `printf 'GGGAAACCC\n(((...)))\n' \| RNAeval -v -T 70` |

Interpretation: logbook/2026-09-22-session-02.md, entry 22:30.

---

## Experimental results

*(None yet.)*

| Date | Experiment | Metric | Value | Command | Commit | Seed |
|---|---|---|---|---|---|---|
