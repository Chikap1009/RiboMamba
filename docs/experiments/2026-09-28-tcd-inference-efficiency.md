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

## Profile (measured 2026-09-28 ~19:45-20:00 IST; machine otherwise idle; OMP_NUM_THREADS = 1)
Commands: `python scripts/profile_tcd.py cold` (3 repeats x 2 targets, fresh processes) and
`python scripts/profile_tcd.py components` (warm, one process, 6 profiling targets, seed 0, 64 s
method-time units, CUDA-synchronised stage timers; the stage-timed copy of infill was first checked
to return exactly the production result). Latency probes: scratch scripts (forward vs batch size, vs
idle gaps, eager vs CUDA graph); JSON in data/repair_pilot/prof_tcd/.

Cold start (isolated, charged to every protocol-v2 TCD unit): import torch 1.06-1.26 s (2.6 s on the
first ever run), CUDA init 0.91-1.39 s, base checkpoint 0.31-0.48 s, build adapters 0.15-0.19 s, TCD
state 0.04-0.10 s, to GPU 0.02-0.03 s, FIRST infill 0.39-0.59 s (later calls ~15 ms): ~3.2 s in total,
peak RSS 1.48 GB, GPU 100-121 MB. SAMFEO's own setup: 0.006-0.014 s.

Warm steady state, samfeo_tcdprop_efilter, 64 s units (instrumented; proportions, not headline speeds):
| target (nt) | evals | proposal calls / eval | proposal ms / eval | forward ms / call | forward share of proposal | SAMFEO evaluation ms / eval | repeated (parent, mask) rows |
|---|---|---|---|---|---|---|---|
| 29 | 1,723 | 2.11 | 36.2 | 13.8 | 80 % | 0.7 | 95 % |
| 49 | 3,210 | 1.02 | 17.1 | 12.5 | 75 % | 2.7 | 72 % |
| 63 | 2,248 | 1.59 | 25.2 | 12.2 | 77 % | 3.1 | 86 % |
| 92 | 2,000 | 1.00 | 23.2 | 17.4 | 75 % | 8.5 | 28 % |
| 129 | 1,360 | 1.00 | 30.4 | 23.9 | 79 % | 16.4 | 25 % |
| 251 | 419 | 1.00 | 76.7 | 68.3 | 89 % | 75.9 | 6 % |
Proposal overhead takes 32-62 s of each 64 s unit; the forward pass is 75-89 % of it. Other infill
stages per call: on-device mask indexing ~1.2 ms, structure tensors rebuilt + copied 0.6-2.0 ms, ids
H2D 0.2-1.2 ms, softmax 0.1-0.4 ms, D2H 0.1-0.3 ms, numpy sampling 0.4-0.5 ms; drafts, dedup and the
energy screen are < 1 ms per evaluation. SAMFEO's history loop re-calls the proposal (up to 2.1 calls
per evaluated candidate on short puzzles).

Why the forward is slow (probes): eager latency is ~11-12 ms whether the batch is 1, 8 or 32 rows at
29-129 nt (a fixed per-call cost that does not grow with the batch, consistent with kernel-launch/
dispatch overhead [wording corrected at closeout]); 23 ms only for 32 rows at 251 nt.
A CUDA-graph replay of the same B = 8 forward takes 1.8 ms (29 nt), 3.6-4.6 ms (129 nt), 5.1-6.8 ms
(251 nt), after a one-off capture of 19-42 ms, and its nucleotide logits are BITWISE identical to
eager (251 nt case). When the GPU idles 100-300 ms between calls (sleep or real ViennaRNA work), both
eager and graphed forwards slowed to 23-72 ms (observed; graph replay did not remove it). Attributing
this to GPU/driver idle (power-state) behaviour on this laptop/WSL2 setup is an inference that was not
tested further [closeout correction: earlier wording stated it as fact]. It is the likely reason for the
68 ms forwards at 251 nt, where SAMFEO's own evaluation and harness scoring leave the GPU idle ~150 ms
between proposals.

## Chosen optimisation (from the profile) and alternatives not chosen
CHOSEN: graphed forward with static input buffers. Per unit (one target, fixed shape B = 8 x (L + 2)),
build the structure tensors once, capture the model's autocast forward once in a CUDA graph, and per
proposal copy the host-built token batch into the static buffer (one H2D copy) and replay. Mask
expansion, softmax, D2H and the numpy sampling are unchanged, so given bitwise-identical logits the
children, the random stream and therefore the whole search are unchanged at a matched CANDIDATE budget
(to be verified by tests and by identical trajectories at fixed budgets; at a matched time budget the
faster variant evaluates more candidates, so runs diverge [qualifier added at closeout]). The eager reference stays
available and is the comparison arm. Projected removable proposal overhead from the profile: ~2.6-3.2x
at 29-129 nt, only ~1.3-1.6x at 251 nt (post-idle slowdown).
Not chosen: (i) a resident model across units removes the ~3.2 s cold start (20 % of a 16 s budget, 5 %
of 64 s) but the steady-state forward costs 50-97 % of a 64 s unit, and it changes the execution model;
(ii) caching predictions for repeated (parent, mask) rows helps short puzzles only (95/72/86 % repeats
vs 6-28 % at >= 92 nt) and saves a forward only when all 8 rows repeat; (iii) nothing within scope
removes the post-idle slowdown at long lengths (keeping the GPU busy artificially is not a method).

## Criteria (final; fixed 2026-09-28 before any optimised-variant outcome was measured)
Development comparison: runner, eternaweb_dev_v1 development subset (32 targets) x seeds 0-2, methods
samfeo, samfeo_efilter, samfeo_tcdprop_efilter (reference, eager) and samfeo_tcdprop_efilter_graph,
budget 5,010, unit time limit 64 s, COLD mode as protocol v2 (fresh process per unit; setup charged),
4 concurrent units (--workers 4 --recycle-workers --gpu). Checkpoints 16 and 64 s. Seeds averaged
within targets; paired bootstrap 95 % intervals over the 32 targets. Units without a design reported.
- E1 (engineering, proposal overhead): median over targets of [reference / graph] proposal time per
  evaluated candidate >= 2.0 (units' proposal_wall_s / evaluations, seed-averaged).
- E2 (end-to-end): median over targets of [graph / reference] evaluations completed by 64 s >= 1.5, and
  >= 1.2 by 16 s (the cold start is charged to both arms and is unchanged).
- Q (unacceptable quality regression, graph - reference, at 16 s and at 64 s): uMFE point estimate
  < -3 pp (about one puzzle's seed mean of 96 target-seeds) or best-NED point estimate > +0.005 (as
  large as the ensemble-quality gains reported under protocol v2) at either checkpoint.
- S (scientific continuation, graph - SAMFEO + screen, paired, at matched method time; GPU use disclosed):
  S-success: uMFE >= +5 pp with the 95 % interval above 0 at 16 or 64 s; or
  S-quality: best NED lower with the 95 % interval below 0 at BOTH 16 and 64 s AND uMFE point estimate
  >= -2 pp at both (supports only an ensemble-quality statement).
Decision: continue to a new unused-set protocol (Phase 4) only if E1, E2 and not-Q hold AND S-success or
S-quality holds; otherwise record the result and stop this direction. Secondary, descriptive only:
an isolated (1 worker) cold and warm end-to-end profile of reference vs graph on the 6 profiling
targets x seeds 0-2 (speed only; no quality inference).

## Outcome — development comparison ew_dev_tcdgraph_v1 (measured 2026-09-28 20:02-22:10 IST)
384/384 units valid (7,664 s; 4 concurrent units, fresh process per unit, setup charged; no errors;
no unit without a design by 64 s). Analysis: `python scripts/tcd_graph_compare.py` (declared script;
two plumbing fixes before its first successful output: polars schema inference over null peak_gpu_mb,
and printing NA for the undefined 1 s means; no endpoint or threshold changed) -> compare.json.
Many CPU-method units reached the 5,010-candidate cap before 64 s (samfeo 71/96, screen 66/96, graph
15/96 'complete'); endpoints are at matched method time under that cap, as in protocol v2.

Seed-mean uMFE / best NED / best log10 P (32 targets) and median evaluations:
| method | 4 s | 16 s | 64 s | evals by 16 s / 64 s |
|---|---|---|---|---|
| SAMFEO | 38.5 % / 0.0701 / -1.42 | 47.9 % / 0.0590 / -0.99 | 56.2 % / 0.0526 / -0.79 | 2,568 / 5,010 |
| SAMFEO + screen | 47.9 % / 0.0631 / -1.08 | 56.2 % / 0.0528 / -0.79 | 61.5 % / 0.0490 / -0.72 | 2,289 / 5,010 |
| TCD + screen, eager (reference) | 26.0 % / 0.0836 / -1.72 | 46.9 % / 0.0536 / -0.93 | 56.2 % / 0.0476 / -0.72 | 504 / 1,920 |
| TCD + screen, CUDA graph | 36.5 % / 0.0674 / -1.42 | 50.0 % / 0.0505 / -0.84 | 56.2 % / 0.0457 / -0.70 | 1,096 / 3,661 |
At 1 s neither TCD arm has a design (cold start ~3.2 s is charged to both and unchanged).

Speed (cold, 4 concurrent): proposal time per evaluated candidate 24.7 -> 10.2 ms (unit medians);
per-target ratio reference/graph median 2.48 (1.34-3.50): 2.51 (<= 60 nt, 12 targets), 2.53
(61-130 nt, 14), 1.74 (> 130 nt, 6; 1.34 at 251 nt, where the post-idle slowdown dominates). Evaluations by
64 s graph/reference median 1.90 (1.08-2.46; 1.21 above 130 nt), by 16 s 2.05. Proposal calls per
evaluation rose 1.07 -> 1.45 (the faster search reaches SAMFEO's history-collision phase more often).
Model time per 64 s unit: 49.5 -> 34.7 s (median) while model calls rose 2,262 -> 5,685. Peak host RSS
~1.2 GB for both TCD arms (0.17 GB for SAMFEO); peak GPU memory 120 -> 99 MB. GPU is used only by
the TCD arms; CPU-only and GPU-assisted arms are not equal-compute despite equal time limits.

Paired effects (seed-mean per target; bootstrap 95 % over 32 targets; a better / b better):
- graph - reference: uMFE +3.1 pp [0.0, +6.3] @16 (3/0), 0.0 @64 (0/0); best NED -0.0031 [-0.0051,
  -0.0015] @16 (28/0), -0.0019 [-0.0043, -0.0003] @64 (23/0); log10 P +0.090 [+0.038, +0.153] @16,
  +0.021 [+0.006, +0.040] @64.
- graph - SAMFEO + screen: uMFE -6.3 pp [-14.6, -1.0] @16 (0/4), -5.2 pp [-10.4, -1.0] @64 (0/4);
  best NED -0.0024 [-0.0054, +0.0008] @16 (19/13), -0.0033 [-0.0057, -0.0011] @64 (18/14); log10 P
  -0.049 [-0.179, +0.059] @16, +0.015 [-0.063, +0.090] @64.
- reference - SAMFEO + screen: uMFE -9.4 pp [-17.7, -3.1] @16, -5.2 pp [-10.4, -1.0] @64.
- graph - SAMFEO: uMFE +2.1 pp [-5.2, +10.4] @16, 0.0 [-6.3, +5.2] @64; best NED -0.0085 [-0.0149,
  -0.0030] @16, -0.0069 [-0.0113, -0.0031] @64.
- SAMFEO + screen - SAMFEO (context): uMFE +8.3 pp [0.0, +17.7] @16, +5.2 pp [+1.0, +9.4] @64.

## Gates and decision (as fixed before the run)
E1 MET (2.48 >= 2.0). E2 MET (1.90 >= 1.5 at 64 s; 2.05 >= 1.2 at 16 s). Q OK (no regression; the
graph arm is better than the eager reference on NED and P at matched time, as expected from identical
search semantics with more evaluations). S NOT MET: against SAMFEO + screen the optimised TCD arm is
WORSE on uMFE at both checkpoints (-6.3 and -5.2 pp, intervals below 0) and its NED advantage holds
only at 64 s (-0.0033) and not at 16 s (interval includes 0).
DECISION: the engineering optimisation works and is kept (a speed change that leaves the search
unchanged at matched CANDIDATE budgets; at matched TIME budgets it evaluates more candidates, so runs
diverge), but the scientific continuation criterion fails, so no new evaluation set or protocol is
prepared (Phase 4 not started) and this direction STOPS here, as the stopping rule requires. Proposal
cost mattered, but reducing proposal overhead substantially did not eliminate TCD's success-rate
disadvantage against the non-neural energy screen within the tested budgets. [Closeout correction: the
earlier sentence said the overhead was "not the reason" for the gap, which overstated the evidence.]
Limits: 32 development targets used throughout the project's development (not confirmation); one
laptop GPU under WSL2 (launch and wake latencies are platform-specific); bitwise identity of graph and
eager logits is verified empirically on this GPU/driver/torch build, not guaranteed in general.

## Secondary isolated speed profile (descriptive; speed only, no quality inference)
Runs prof_tcd_iso_warm_v1 and prof_tcd_iso_cold_v1 (6 profiling targets x seeds 0-2, reference vs
graph, --workers 1, 64 s units; 36/36 valid each; 22:10-23:54 IST). CORRECTION: the runner ran
--workers 1 in-process and ignored --recycle-workers, so prof_tcd_iso_cold_v1 was NOT cold: like the
warm run it used one persistent process (only the first unit paid setup: first candidate 2.1-2.2 s;
every later unit ~0.01-0.08 s). Both v1 runs are therefore WARM measurements and agree closely. The
runner was fixed (82361cc, with a test) and the genuine cold isolated profile rerun as
prof_tcd_iso_cold_v2; v1 is kept and labelled here. The development comparison was unaffected (4
workers: 96/96 distinct worker pids per method; TCD first candidates at median ~2.2-2.3 s, i.e. cold).
WARM, isolated (one process, model resident; setup paid once, excluded from later units):
| mode | reference proposal ms / eval | graph proposal ms / eval | overhead ratio (per-target median, range) | evals by 16 s ref -> graph | evals by 64 s ref -> graph |
|---|---|---|---|---|---|
| warm (v1 'warm') | 23.2 | 13.5 | 1.83 (1.18-2.70) | 624 -> 1,352 (x2.09) | 1,908 -> 3,182 (x1.55) |
| warm (v1 'cold', mislabelled) | 22.6 | 13.6 | 1.76 (1.18-2.64) | 632 -> 1,353 (x2.05) | 1,956 -> 3,196 (x1.54) |
These 6 targets include 2 of the 6 longest (> 130 nt), where the post-idle slowdown limits the gain, so
their median ratios are lower than the 32-target comparison's (2.48 overhead, 1.90 evaluations).
COLD, isolated (prof_tcd_iso_cold_v2, 2026-09-28 23:58 - 09-29 00:47 IST; --workers 1 --recycle-workers
after the fix; 36/36 valid, 36 distinct processes, no errors): both arms reach their first candidate
after the same setup (median 3.10 s; reference 2.96-6.00, graph 2.95-3.49 s). Proposal time per
evaluated candidate 26.3 -> 17.0 ms (unit medians); per-target overhead ratio median 1.51 (1.09-2.40);
evaluations graph/reference median x1.94 by 4 s, x1.90 by 16 s, x1.39 by 64 s.
Summary across modes (speed only): the graph forward cuts proposal overhead ~1.5x (cold, isolated),
~1.8x (warm, isolated) and ~2.5x (cold, 4 concurrent units: the declared comparison, where eager
launches also contend for the GPU); evaluations by 16 s roughly double in every mode; gains shrink on
the longest puzzles. None of this changes the decision above, which rests on the declared comparison.

## Closeout corrections (2026-09-29; no new experiment)
- Conclusion narrowed (see DECISION above): cost mattered, but reducing it did not eliminate the
  success-rate disadvantage against SAMFEO + screen within the tested budgets.
- "Launch-bound" and "wake latency" wording: the measurements show a fixed per-call cost independent
  of batch size that CUDA-graph replay largely removes, and a slowdown after idle periods that it does
  not; the hardware/driver causes are inferences, not established facts.
- Equivalence scope: bitwise-identical logits and identical search were verified at matched candidate
  budgets on one configuration (RTX 4060 Laptop GPU, driver 595.79, WSL2 kernel 6.18, PyTorch
  2.10.0+cu128, CUDA 12.8, cuDNN 9.10.2); not guaranteed on other GPUs, drivers, PyTorch versions or
  operating systems. At matched time budgets trajectories differ by design.
- Criterion Q ("no unacceptable quality drop") compares the graphed variant with the EAGER TCD
  implementation only; against SAMFEO + screen the graphed variant is worse on uMFE (criterion S).
- Speed-up scope: 2.48x (proposal overhead) and 1.9-2.05x (candidates within the budget) are for 4
  concurrent cold runs; isolated runs gained 1.51x (cold) and ~1.8x (warm) in overhead; the ~3 s setup
  before the first candidate and the run length (fixed budget) are unchanged.
- Regeneration check: re-running scripts/tcd_graph_compare.py once on the saved traces reproduced every
  point estimate and all gates; in that rerun bootstrap interval bounds moved by up to 0.0104 (uMFE)
  because per-target rows are not sorted before the seeded bootstrap (observed variation, not a bound);
  no interval changed which side of zero it lies on.
