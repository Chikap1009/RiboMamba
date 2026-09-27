# Final design-benchmark protocol v2 (repair project)

**Status: DRAFT — not frozen.** Nothing below has been run on a final benchmark.
The old Phase 3/4 protocol in RESULTS.md is a different study and is not modified.
When frozen, a line `**Status: FROZEN on YYYY-MM-DD**` replaces the one above and
the final-run code refuses to start without it. After freezing, only additions
recorded as dated amendments are allowed; no method, budget or endpoint changes.

## Question
Does SAMFEO with pre-screened mutations (energy filter, and the learned critic if
it passed its development criterion) solve more hard RNA design puzzles, or reach
the same quality with fewer expensive evaluations / less wall time, than
unmodified SAMFEO and the other baselines, under identical oracle and budgets?

## Oracle (fixed)
ViennaRNA 2.7.2, Turner 2004, 37 C, dangles = 2, lonely pairs allowed;
ribomamba/design/scoring.py (D-017). Success = unique MFE (uMFE); also report
MFE (any tie) and backtracked MFE.

## Benchmarks (final test; untouched until the freeze)
1. Eterna100 V2, all 100 puzzles (19-400 nt) — PRIMARY (the version adapted to ViennaRNA 2).
2. Eterna100 V1, all 100 puzzles — secondary, for comparison with SAMFEO's
   published 77 MFE / 74 uMFE and Gautam et al.'s 75 / 73 (both ViennaRNA 2).
3. Rfam-Taneda-27 and RNAsolo-100 (the LM paper's copies) — secondary natural sets.
Leakage: every development and training puzzle is > 0.2 normalized edit distance
from all of these (hard_manifest.py, training_pool.py), and no Eterna100 id was
used. The critic never saw any of them.

## Methods (fixed list; settings chosen on development data only)
- SAMFEO (pinned e78b4b5, defaults)                     [strong baseline]
- SAMFEO + energy filter, K = <chosen on dev, recorded here before freeze>
- SAMFEO + learned critic, K = 8 — ONLY if it met the Stage C decision rule on dev
- RNAinverse restarts (ViennaRNA 2.7.2)                [fast-MFE baseline]
- SamplingDesign (f0283c49, defaults except a wall-time cap equal to the
  median SAMFEO wall time per puzzle at the same budget)   [second strong baseline]
- random_pair_edits                                   [simple control]

## Budgets
Per puzzle and seed: nested checkpoints at 256, 1,024 and 5,010 candidate
evaluations (5,010 = SAMFEO's published setting: 10 initial + 5,000 steps).
Wall-time checkpoints 1, 4, 16, 64, 256 s of method time. Seeds 0-4.
Hardware and concurrency disclosed; all compared methods run in the same batch
of jobs so machine load is comparable.

## Endpoints and statistics
Primary: number of Eterna100 V2 puzzles solved (uMFE) at 5,010 evaluations,
(a) by any of the 5 seeds (union) and (b) mean over seeds. Secondary: counts at
other budgets and wall times; mean best NED; mean best log10 P(target);
evaluations to first solve. Paired per puzzle (method vs SAMFEO): solved-by-one
counts and bootstrap 95 % intervals over puzzles (seeds averaged within puzzle).
Report every error, timeout and early stop; nothing is dropped.

## Claims allowed
Only what these numbers show under this oracle. No wet-lab, generalisation or
"state of the art" wording unless a method beats every re-run baseline AND the
published numbers under matching settings, with the budgets stated beside it.
