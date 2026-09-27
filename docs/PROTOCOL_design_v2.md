# Final design-benchmark protocol v2 (repair project)

**Status: FROZEN on 2026-09-27**
The old Phase 3/4 protocol in RESULTS.md is a different study and is not modified. Once frozen
(a `**Status: FROZEN on YYYY-MM-DD**` line replaces the one above), `scripts/repair_pilot.py run`
accepts the final manifests; before that it refuses them (ribomamba/design/final_manifest.py).
After freezing only dated amendments are allowed; no method, budget, seed or endpoint changes.

## Questions (each answered separately; no single headline)
Q1 (non-neural method): does pre-screening SAMFEO's mutations by target energy (K = 8) improve
    uMFE success and ensemble quality per unit of method time over unmodified SAMFEO, and where
    does it sit relative to DesiRNA, RNAinverse and SamplingDesign on the quality-time frontier?
Q2 (model adaptation): does the target-conditioned masked-diffusion denoiser (TCD) generate
    designs that solve more puzzles than targeted random designs at matched sample count
    (conditioning), and do TCD proposals inside SAMFEO change quality at matched time?
Neither is presented as a diffusion contribution unless Q2's own endpoints show it.

## Oracle (fixed)
ViennaRNA 2.7.2, Turner 2004, 37 C, dangles 2, lonely pairs allowed; ribomamba/design/scoring.py.
Success = unique MFE (uMFE, primary); MFE-any and backtracked MFE also reported.
Independent robustness check (never used for any choice): EternaFold on each method's best-P
design per puzzle and seed (ribomamba/eval/eternafold.py), reported separately.

## Benchmarks (built, hashed in manifests/; never used for development)
- final_eterna100_v2 — all 100 Eterna100 V2 puzzles (19-400 nt). PRIMARY.
- final_eterna100_v1only — the 19 puzzles whose V1 structure differs from V2. V1 results =
  V2 results on the 81 identical structures + these 19 (no puzzle designed twice).
- final_rfam_taneda27 — Rfam-Taneda-27 (natural; possible family overlap with Rfam TRAIN data
  used by the TCD, disclosed; secondary).
Leakage: every development, training and TCD training structure is > 0.2 normalized edit distance
from all of these (hard_manifest.py, training_pool.py, scripts/tcd_data.py).

## Methods (fixed; settings chosen on development data only; commit recorded per run)
1. samfeo — SAMFEO e78b4b5 defaults (baseline).
2. samfeo_efilter — SAMFEO + target-energy pre-screen, K = 8 (Q1 method).
3. samfeo_tcdprop_efilter — SAMFEO sites, TCD letters, energy screen K = 8 (Q2).
   (samfeo_tcdprop_only was evaluated on development and is dominated by method 3: D-028.)
5. tcd_sample — TCD sampling, 32 steps, batch 32 (Q2).
6. random_pairs — targeted random designs (Q2 control).
7. desirna — DesiRNA bdb4908, Turner 2004, 10 replicas pinned to one core.
8. rnainverse — ViennaRNA RNAinverse restarts (shared start, then targeted init).
9. samplingdesign — SamplingDesign f0283c49 defaults, 1 thread (disclosed as under-budgeted
   relative to its published 64-core runs).

## Budgets
Every unit (method x puzzle x seed): method-time limit 128 s on one core
(--unit-time-limit 128; harness re-scoring excluded for self-scoring methods; wall-clock tools
inherit the limit; units that span a machine suspend are rerun) and at most 5,010 candidates
(SAMFEO's published step budget). Seeds 0, 1, 2. GPU shared by the TCD methods; hardware,
concurrency and all model-time/oracle counts disclosed.

## Endpoints and statistics
Primary (V2): puzzles solved (uMFE) by 128 s — (a) by any of the 3 seeds, (b) mean over seeds.
Secondary: uMFE at 1/4/16/64/128 s method time; best NED; best log10 P; evaluations to first
solution; V1 and Rfam-Taneda-27 counts; EternaFold agreement of best designs.
Paired per puzzle (method vs samfeo; method vs samfeo_efilter; tcd_sample vs random_pairs):
seeds averaged within puzzle, bootstrap 95 % intervals over puzzles; every error, timeout,
early stop and time-limit outcome reported.

## Claims allowed
Only what these numbers show under this oracle and budget. Published numbers of other methods
(SamplingDesign 79/78, DesiRNA 97/100 V2 in 24 h, Montparnasse 100/100 V1 with Turner 1999)
are quoted separately with their settings, never mixed with ours. No SOTA, wet-lab,
generalisation or speed claim beyond the measured frontier.

## Freeze record
Frozen 2026-09-27 (~21:45 IST) after the development runs ew_dev_frontier_v1, ew_dev_tcd_v1,
ew_dev_tcdprop_v1 and ew_dev_tcdprop_v2 (decision D-028). Final manifests and SHA-256 (content):
final_eterna100_v2 33c65b95..., final_eterna100_v1only 2ef59009..., final_rfam_taneda27 a8016910...
Commands (one runner invocation per manifest, all methods in the same batch):
  python scripts/repair_pilot.py run --run final_v2_<set> --manifest <final manifest> --subset all
    --budget 5010 --seeds 0 1 2 --unit-time-limit 128 --workers 10 --gpu
    --methods samfeo samfeo_efilter samfeo_tcdprop_efilter tcd_sample random_pairs desirna
              rnainverse samplingdesign

## Amendment 1 (2026-09-27 ~22:30 IST) — operational only
After 43 final units, host memory neared exhaustion (10 workers x ~1 GB: each worker kept a CUDA
context once it had run a TCD unit). The chain was stopped by process group (completed units are
atomic and kept; in-flight units rerun) and resumed with `--recycle-workers --workers 8` (a fresh
process per unit). Methods, settings, budgets (128 s method time, <= 5,010 candidates), seeds,
manifests and endpoints are unchanged; each unit is independent and seeded by name, so results do
not depend on the worker count. Side effect disclosed: every unit now pays its own imports and, for
TCD units, a model load (~2-3 s) inside its method time.
