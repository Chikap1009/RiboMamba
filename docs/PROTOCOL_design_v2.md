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
Amendment 1b (same evening): recycling alone left ~1.2 GB per worker because every worker imported
torch's CUDA build via the method registry; model methods are now registered lazily
(ribomamba/design/lazy_methods.py), so CPU-method workers never import torch. Method settings and
the run's config hash are unchanged (verified); the chain was stopped and resumed again.
Amendment 2 (2026-09-27 ~22:45 IST) — operational bug fix: the runner passes the unit time limit
as a float (128.0) and DesiRNA's -t option accepts only integers, so the first 15 DesiRNA units
errored immediately (recorded, not dropped). The adapter now passes int(round(limit)) (b46f71d;
same 128 s budget). Recycled workers pick up the fix for new units; errored units are rerun with
--retry-errors after the chain (data/repair_pilot/run_final_v2_retry.sh). Settings and config
hash unchanged.
Amendment 3 (2026-09-27 ~23:05 IST) — operational bug fix (commit a420dc2, fix time
2026-09-27T17:30:21+00:00): replayed external candidates (DesiRNA, SamplingDesign) were checked against the harness
clock, which already included the whole external run, so their replays stopped at the first candidate
(0 rows). The check now uses each candidate's stamped method time. After the chain, EVERY desirna and
samplingdesign unit finished before the fix time is moved to units_superseded/ (kept, not deleted) and
rerun under the same configuration; budgets and settings are unchanged.
Amendment 4 (2026-09-28 ~01:05 IST) — measurement-validity fixes from an independent review (no
method, setting, budget or endpoint changes; nothing tuned on final outcomes):
(a) DesiRNA: its trajectory is written only at the end and its limit is checked only between rounds
    (nominal 128 s runs lasted ~240 s, 238-239 CPU-s), and candidates had been stamped by step
    fraction, crediting post-deadline work. Now scripts/external/desirna_wrapped.py logs every
    replica state per round with real seconds since launch; the process group is killed at 128 s;
    only rows logged by then count (commit 74ec5f1).
(b) SamplingDesign: all early traces were empty. Measured: one default step (2,500 samples, one
    thread) takes ~119-125 s at 180 nt on this machine, so on long puzzles no step finishes within
    128 s (a genuine budget outcome). Output is now line-buffered (stdbuf) so a finished step is never
    lost at the kill, candidates carry their real arrival time, and raw stdout/stderr are kept.
(c) A kill at the limit is status time_limit (not early_stop); a time_limit unit with zero candidates
    is a valid unsolved outcome, not rerun.
(d) Every desirna / samplingdesign unit that started before the fix time
    (data/repair_pilot/final_v2_replay_fix_time.txt) is moved to units_superseded/ and rerun by
    data/repair_pilot/run_final_v2_retry.sh.
(e) scripts/final_report.py refuses FINAL output unless all expected units of all three sets are valid
    and the retry pass is done; best-P designs, first successes and EternaFold inputs are selected
    only among candidates within 128 s of method time (same rule as the success curves).
Amendment 4b (2026-09-27T19:45:05+00:00 UTC): the DesiRNA wrapper also logs the states ENTERING each round, so its
initial population (present from start-up, step 0 of its own trajectory) is counted even when the
first round outlasts 128 s (e.g. 337-400 nt with 10 replicas on one core). The fix time for
superseding DesiRNA/SamplingDesign units moves to this commit (bda4884).
Amendment 4c (2026-09-28 ~01:30 IST, report side only; 035c439): final_report.py lists zero-candidate
units per method and refuses FINAL while any unit ended in `error` (implementation failures until
diagnosed; `--accept-errors` then counts them as unsolved and lists them) or while a zero-candidate
unit has any status other than time_limit. The corrective pass supersedes by per-method fix time
(scripts/final_v2/run_final_v2_retry.sh, 9d91eea). Methods, budgets and endpoints unchanged.
Amendment 4d (2026-09-28 ~01:45 IST, report side only, fixed before any final outcome was read):
a unit with no design within 128 s has no NED or P. Quality summaries (best NED, best log10 P) are
means and medians over units WITH a design, reported with the number of units without one; paired NED
comparisons use puzzles where both methods have a design in every seed (n reported); uMFE success is
defined for every unit (no design = unsolved). EternaFold agreement is a rate over ALL units
(no design = no match). Commits a9ea5b1 and the one adding this text.
Amendment 4e (2026-09-28, report side only; correction from a review): 4c said error units accepted
with --accept-errors count as unsolved, but success curves were still derived from their partial
traces, so an errored unit with a successful partial trace would have been credited. Now
final_report.per_unit applies the policy to every figure (success under all tie policies, best NED,
best P/design, first success, paired comparisons, EternaFold): an `error` unit is unsolved with no
design at every wall budget (apply_error_policy; tests/test_final_report.py, which fails without it).
The default FINAL path still refuses while error units remain.
Amendment 4f (2026-09-28 ~11:15 IST, report side only): (i) the pre-fix supersede rule has one source,
scripts/final_v2/fix_times.json, read by the corrective pass and by final_report.py, which now REFUSES
FINAL while any desirna/samplingdesign unit that started before its fix (+60 s) is still in place
(117 V2 units at 11:10 IST, all queued for the corrective pass); (ii) the FINAL report carries
provenance (generation time, commit, uncommitted-changes flag, retry-pass completion time, fix times)
and a "supersedes" record: every earlier report file is moved to data/repair_pilot/report_history/
(never overwritten or deleted) and described there by checksum, label and coverage. The unlabelled
final_v2_report.json written 2026-09-27 22:21 IST as a smoke test of the report script (29/2400 V2
units, before the review fixes; sha256 23be60d4...) was moved there at 11:05 IST; it is not a result.
