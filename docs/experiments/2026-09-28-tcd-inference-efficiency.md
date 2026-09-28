# Experiment record — TCD proposal overhead inside SAMFEO (bounded inference-efficiency study)

Date: 2026-09-28 (session 10, evening). Status: SPECIFIED before any profiling or optimisation run.
Scope: development targets only; no training; one profile-driven optimisation; one declared
development comparison. Protocol v2 (docs/PROTOCOL_design_v2.md) and its results are frozen and are
neither rerun nor re-analysed here.

## Starting facts (verified in code before this record)
- samfeo_tcdprop_efilter = SAMFEO (pinned e78b4b5) whose structured mutation is replaced by
  `tcd_mutation` (ribomamba/design/baselines.py): K = 8 SAMFEO drafts -> 8 masks (positions each draft
  changed) -> ONE batched `tcd.infill` call (one forward pass over the 8 masks) -> dedup against
  already-evaluated sequences -> energy screen (lowest E(target)) -> child. Candidate batching across
  K therefore ALREADY exists and is not a new optimisation (code review, confirmed here).
- SAMFEO re-calls its mutation while the child is already in its history set, so one evaluated
  candidate can cost several proposal calls (several forward passes).
- `evaluate.model_wall_s` currently spans drafts + masks + infill (tensor construction, forward, D2H,
  numpy sampling); the energy screen after it is not included.
- The Evaluator clock starts before the method runs, so importing torch, CUDA initialisation and the
  checkpoint load are charged to method time; protocol v2 ran one fresh process per unit
  (--recycle-workers), so every TCD unit paid them (final V2: 0.7 % uMFE at 1 s, 40 % at 4 s vs 58 / 62 %
  for SAMFEO + screen). What dominates that slow start, and the steady-state cost, is NOT assumed.

## Question and hypothesis
Q: Which components dominate TCD proposal overhead (cold start and per proposal), and does ONE
profile-driven optimisation that preserves the proposal distribution reduce it enough to improve the
end-to-end quality/time trade-off at 16 and 64 s of method time, against (1) the existing TCD + screen
implementation, (2) SAMFEO + energy screen, and (3) SAMFEO as reference?
H (to be tested): proposal overhead has >= 2x removable headroom without changing search semantics,
and removing it moves TCD + screen's quality/time curve toward or past SAMFEO + screen at 16-64 s.
A faster forward pass alone is not a method result.

## Targets and seeds
- Profiling subset (fixed rule, chosen before any run): the 32 eternaweb_dev_v1 DEVELOPMENT targets
  sorted by (length, id), ranks 0, 6, 12, 19, 25, 31: eternaweb:7567037 (29 nt, 7 pairs, 7 helices),
  13344845 (49, 18, 4), 13385974 (63, 17, 9), 2624571 (92, 26, 11), 5654857 (129, 38, 13), 4819207
  (251, 79, 22). Seed 0 for component profiles; seeds 0-2 for end-to-end profiles.
- Development comparison: all 32 development targets x seeds 0-2 (paired). The confirmation half of
  eternaweb_dev_v1 (one look used) and all final-benchmark sets are NOT used.

## Methods (exact settings)
- samfeo: SAMFEO defaults (pd objective, k = 10, T = 1, cg init, structured mutation, STAY 2000).
- samfeo_efilter: + energy screen, best of K = 8 by E(target).
- samfeo_tcdprop_efilter (REFERENCE, unchanged code): + TCD letters (checkpoints/tcd_v1/tcd.pt, step
  1,000), K = 8, energy screen.
- the optimised variant: identical settings; only the implementation change chosen in Phase 2.

## Timing definitions and resource accounting
- Method time: as protocol v2 (monotonic clock from unit start; harness re-scoring excluded for
  SAMFEO-hosted methods). Budgets checkpointed at 1 / 4 / 16 / 64 s.
- Proposal overhead: wall time inside the mutation hook per EVALUATED candidate (for TCD: drafts,
  masks, infill incl. transfers and sampling, dedup, energy screen; summed over SAMFEO's re-calls).
  For samfeo_efilter the same quantity is the time inside its filtered mutation.
- Component profile (diagnostic only, CUDA synchronised around each stage): imports, CUDA init,
  checkpoint load, first forward, input/structure construction, H2D, forward, softmax + D2H, numpy
  sampling, drafts/masks, dedup, energy screen, SAMFEO's evaluation (subopt + pf + prob), harness
  scoring, remainder. Headline speed numbers come from minimally instrumented end-to-end runs.
- Modes kept separate: COLD (fresh process per unit, all loading charged, as protocol v2) vs WARM
  (model resident before the unit clock; load cost reported separately and explicitly amortised);
  ISOLATED (one unit on the GPU) vs CONCURRENT (several processes sharing the one GPU).
- Reported per unit: evaluations, proposal calls, model calls, model/proposal time, oracle calls
  (SAMFEO internal + harness), wall time, peak host RSS, peak GPU memory; OMP_NUM_THREADS = 1 and one
  torch CPU thread per process. GPU-assisted and CPU-only methods are NOT equal-compute because their
  time limits match: GPU use is reported alongside.

## Criteria (proposed now; FINALISED in "Criteria (final)" below after the profile, before any
## optimised-variant outcome is examined)
- Engineering gate: >= 2x reduction in proposal overhead per evaluated candidate (median over the
  profiling units) in the mode the optimisation targets, measured end to end with minimal
  instrumentation, AND an end-to-end benefit (more evaluations per second of method time).
- Quality: no unacceptable regression versus the reference implementation (threshold fixed below).
- Scientific continuation (toward a new protocol): only if the optimised variant also improves the
  paired quality/time comparison against SAMFEO + screen at 16 or 64 s; a success-rate claim needs
  uMFE evidence; an ensemble-quality claim stays about NED / P.

## Bounded scope and stopping rule
One optimisation, one development comparison. If the profile shows < 2x removable headroom, or the
optimisation fails the engineering gate or the end-to-end comparison, the negative result is recorded
and the direction stops (no further tuning, no architecture or hyperparameter search, no training).
