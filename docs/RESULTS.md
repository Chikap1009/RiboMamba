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

*(Phase 1.)*

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
