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

Recorded 2026-09-23, session 03. Code at commit `1bf678e` (split + audit)
and `32fa079` (download). Data: `multimolecule/rfam` at `25e8aa8…`,
`multimolecule/bprna` at `423465b…` (SHA-256 verified). All seeds = 0.
Deterministic: rerunning `prepare_data.py` gives byte-identical files.

**Reproduce** (inside `conda activate ribomamba`, from the repo root):

```
python scripts/download_data.py      # pinned revisions, checksums verified
python scripts/explore_data.py       # raw-data numbers that set the thresholds
python scripts/prepare_data.py       # clean + split  -> data/processed/, splits/rfam_split.tsv
python scripts/audit_leakage.py      # this table     -> data/processed/audit.json
```

Output checksums (SHA-256, `sha256sum data/processed/*.parquet splits/rfam_split.tsv`):

```
23905bf3594827f9c252307c51d8e81433859d3948631cf224ba0e64e1477641  data/processed/test.parquet
012c03a8a1b782daf5e0a64403bf3d8ac1b6ae8f2b7e50194acf6ad618eecd5d  data/processed/train.parquet
d188b5c73bde630bfac74418f9837805d6640e1bc8816a636a3cc6b059b7b36a  data/processed/val.parquet
3d526092bdd9562741beb90527c4c99bdc8994afaa0801e7721eab6a79ffda88  splits/rfam_split.tsv
```

### The data after cleaning (D-007) and splitting (D-008)

| | sequences | share | families | split units (clan or family) | median length |
|---|---|---|---|---|---|
| train | 452,867 | 79.9 % | 3,032 | 2,830 | 93 |
| val | 57,054 | 10.1 % | 406 | 371 | 92 |
| test | 56,883 | 10.0 % | 399 | 371 | 96 |

Cleaning funnel: 20,051,822 raw rows → 10,025,911 after removing the
duplicated `"No such family"` copy → 9,981,218 ACGU-only → 9,590,462 after
dropping 185 families with median length > 256 → 9,547,361 ≤ 256 nt →
9,534,330 after the fragment filter → 5,730,590 after exact-duplicate removal
→ 5,730,554 single-family → **567,579** after the 1,000-per-family cap →
566,804 after step 10 (−200 val, −575 test).

### Leakage checks

**Checks 1–2 — shared labels or identical sequences between any two splits:
0 clans, 0 families, 0 sequences** (train–val, train–test, val–test). Also
enforced by an assertion in `prepare_data.py`.

**Check 3 — nearest training relative of held-out sequences.** 2,000
held-out sequences sampled per row (seed 0); each searched against **all**
training sequences with MMseqs2 18.8cc5c (nucleotide, forward strand,
E ≤ 10⁻³). A hit counts toward an identity level only if it covers ≥ 80 %
of the query. ± = 95 % confidence half-width (normal approximation).

| split scheme / held-out set | any detectable relative | median best identity | ≥ 50 % | ≥ 80 % | ≥ 90 % | ≥ 95 % | 100 % |
|---|---|---|---|---|---|---|---|
| **ours** / val | 1.40 % | 0 | 0.05 % ± 0.10 | 0 * | 0 * | 0 * | 0 * |
| **ours** / test | 1.00 % | 0 | 0.15 % ± 0.17 | 0 * | 0 * | 0 * | 0 * |
| **random split (control)** / test | **96.0 %** | **0.961** | 93.0 % ± 1.1 | **89.6 % ± 1.3** | 73.7 % ± 1.9 | 56.2 % ± 2.2 | 7.7 % ± 1.2 † |

\* Zero **by construction**: step 10 of `prepare_data.py` removed every
held-out sequence with a ≥ 80 %-identity, ≥ 80 %-coverage training hit,
using the same search. Before step 10 the family/clan split alone gave
1.2 % ± 0.5 of test at ≥ 80 % (775 of 114,712 held-out sequences, 17
families; see D-008). The ≥ 50 % and "any relative" columns are the
informative ones for our split.
† Not exact duplicates (the pool has none): 100 % identity over ≥ 80 % of
the query, e.g. one sequence is the other plus a few letters at an end.

**Interpretation.** Under a random split, the typical test sequence has a
96 %-identical relative in training, so a model could score well by
recalling relatives. Under our split, 99 % of test sequences have no
detectable sequence relative in training at all.

**Check 4 — bpRNA-1m sequences that occur letter for letter in our splits**
(of 70,035 distinct bpRNA sequences): train **17,086**, val 1,860, test
2,036. So any bpRNA structure used as a design target in Phase 3 must be
screened against our train split first.

**Known limits of this audit.** Sequence similarity only: two families with
the same structure but no detectable sequence similarity would pass. The
test set is one draw (seed 0). Rfam family labels are themselves
model-assigned.

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
