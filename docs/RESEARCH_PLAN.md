# Active research plan — approved direction, 2026-09-27

## Goal and claim boundary
Investigate whether coordinated RNA sequence repair, informed by folding-ensemble
feedback and a small denoiser, improves target-structure design quality per unit
of computational cost. This plan is a development plan, not a frozen final-test
protocol. No gain, novelty or SOTA status has yet been demonstrated.
Keep the old Phase 4 study as incomplete supporting work, not the main claim.

A successful contribution requires an advantage over strong existing designers,
an explanation of which component causes it, and a defensible current-literature
comparison. A smaller conditional loss is not improvement on the old unconditional
~1.9 bound. Computational folding success does not demonstrate biological function.

## Stage A — make the experiment trustworthy, without new training
Deliver a validation-only pilot harness and baseline adapters.

1. Inspect data/targets/rfam_val.parquet and its construction in
   scripts/build_targets.py. Select 64 targets deterministically (seed 20260927),
   stratified by length and paired-base fraction, before scoring candidates.
   Use only supported pseudoknot-free targets of length <=256; record all
   eligibility rules, exclusions, IDs, target strings and a manifest hash.
   Use 8 of those targets for implementation smoke checks, then all 64.
   Do not load final test targets to tune selection or methods.
2. Split the selected targets deterministically into 32 development and 32
   confirmation targets before experiments. Tune on development; use confirmation
   once per declared candidate revision and log every look. This is still
   validation, not a substitute for a held-out final benchmark.
3. Reuse ViennaRNA 2.7.2 / Turner04 / 37 C / dangles=2 from the current folding
   module. Test candidate validity and scoring. The current check_target path
   can raise for noncanonical candidate pairs: score such designs as failures,
   while retaining useful candidate folding feedback; do not drop them.
   Verify target probability=0 for an impossible target and define its ensemble
   defect from the candidate's pairing probabilities where mathematically valid.
4. Log a resumable per-candidate trace: target/seed/method, sequence, parent,
   changed positions, objective, MFE result, target probability, normalized
   ensemble defect, cumulative resource counters, elapsed time and error status.
   Write results atomically and validate manifests/completeness on resume.
5. Implement cheap controls: independent random canonical-pair designs;
   random coordinated pair/stem edits; feedback-directed paired edits without
   a neural network. Preserve shared starting candidates for repair comparisons.
6. Integrate at least one strong available search baseline (SAMFEO or
   SamplingDesign). RNAinverse is a useful sanity control, not the only serious
   competitor. Pin upstream source, license, build and settings. Do not claim
   equal oracle budgets unless internal calls can be instrumented faithfully;
   otherwise compare explicit wall-time curves and mark call counts unavailable.

## Stage B — minimal model-assisted repair probe
Use the existing Transformer EMA checkpoint first, not a new backbone sweep.
It is an unconditional model: do not pretend it already understands target
structure. Inspect its loader and diffusion code before implementing infilling.

- Mask selected erroneous interacting regions and resample while clamping all
  other nucleotides. An explicit paired sampling rule must enforce allowed pairs;
  independently selecting two nucleotide logits is not a joint pair model.
- Keep BOS/EOS, padding, length and nucleotide-only constraints correct.
- Contrast model proposals with identical masks using random legal proposals,
  and feedback-selected masks with random masks. Match start states and budgets.
- Current trained loss used random masking. Repair masking is distribution shift;
  treat failure to help as evidence, not justification for indefinite training.
- Use full pairing-probability feedback where available: identify intended pairs
  lacking support and competing partners. Define the mask-selection rule before
  running it. Negative design and paired updates have prior art; novelty is open.

Resource settings for the first pilot:
- Seeds 0, 1, 2; checkpoints on nested budgets 64, 256, 1024 candidate evaluations
  per target/seed, including the initial candidate. Cache repeated sequences,
  recording both proposals and cache misses.
- Count MFE and partition-function calls separately, including proposal/selection
  feedback and internal baseline calls. A candidate evaluation is NOT inherently
  equal compute across methods. Report CPU/GPU wall time and hardware too.
- Start with a smoke run and estimate runtime before expansion. Local CPU/GPU
  use has no user-imposed hour or worker cap (reaffirmed 2026-09-27).
  Choose concurrency to fit available memory; retain one GPU job at a time.
  Candidate budgets are experimental comparison settings, not total compute limits.
  Explicit per-run timeouts remain optional operational settings; disclose them.
  No new neural training within Stage B; specialized training belongs in Stage C.

## Decision after the pilot
Compare per-target paired outcomes and show the distribution, not just one mean.
Report exact MFE success with tie policy explicit, normalized ensemble defect,
target probability, quality/budget curves, timeouts and failures. Aggregate seeds
within target before target-level uncertainty estimates; seeds are not independent
targets. Include composition/diversity and obvious degenerate-design diagnostics.

Provisional continuation criterion (a development decision, not a significance
test or a predicted result): a credible >=10 percentage-point success advantage
at comparable cost OR >=3x fewer expensive evaluations at comparable quality,
without a compensating wall-time or quality regression. Compare with the strongest
applicable baseline, and require evidence that model guidance adds value over
non-neural repair. Record uncertainty; 64 targets cannot establish universal SOTA.
Do not move the criterion retrospectively without documenting why.

If neural proposals add nothing, investigate once using failure traces and a
specific hypothesis. Either justify Stage C with evidence or pivot to the better
non-neural method / different defensible research question. No endless sweeps.

## Stage C — specialized training, conditional on evidence
Build a separate target-aware repair model initialized from the Transformer.
Candidate inputs: sequence, target pairing graph and localized failure/ensemble
feedback. Training examples: failed candidates paired with improved repairs,
generated only from training-side targets. Keep unsuccessful trajectories too.
Mask/base-pair moves, graph conditioning, search distillation and iterative
remasking are established ideas; determine what, if anything, is new here.

Before launching: specify training-data provenance, split/structure overlap audit,
objective, architecture delta, memory benchmark, time budget and ablations in a
dated experiment record. Start small; do not automatically launch 30k steps,
five seeds or a large pretrained-model retrain.

## Stage D — final benchmark and research artifact
Freeze a NEW protocol before final test evaluation, with dataset membership,
length limits, oracle versions, tie conventions, constraints, budgets, competitors,
seeds, endpoints and uncertainty calculations. Preserve the old frozen record.

Use full Eterna100 V1/V2 only if supported; label every filtered subset precisely
(the existing <=256 V2 set has 75 targets). Include held-out natural structures
with leakage auditing. Public benchmark exposure and unknown pretrained-model
overlap must be disclosed. Reproduce published methods under comparable settings;
do not compare our laptop timing directly with their server table.

Retain EternaFold as an independent robustness check rather than an optimization
oracle. Track biological-composition constraints separately and equally across
methods; do not change them after seeing a winner.

Completion means: reproducible code and baseline adapters, pinned environment,
versioned target manifests, raw traces and failure logs, meaningful tests,
ablations and uncertainty, current novelty assessment, technical report and
model/data documentation. An optional demo follows evidence. If the hypothesis
fails, report that accurately; the project is not complete as a SOTA contribution
merely because software runs.

**Status 2026-09-28 (D-029):** protocol v2 frozen and the final benchmark run to completion (3,504
units valid; FINAL report data/repair_pilot/final_v2_report.json). The hypothesis as a SUCCESS-RATE
claim failed: no variant beats SAMFEO or RNAinverse on uMFE at 128 s; ensemble quality (NED) improves
modestly with the energy screen and most with conditioned-denoiser proposals. Done: code and adapters,
tests, versioned manifests, raw traces and failure logs (local), pinned environments
(environment.design_v2.*.lock.yml), ablations with uncertainty, technical report draft
(docs/REPORT_repair_v2.md, with figures from scripts/final_figures.py), model card
(docs/MODEL_CARD_tcd_v1.md) and data card (docs/DATA_CARD_design.md). Remaining for a complete
artifact: a refreshed novelty/prior-art assessment against current primary sources (the report
claims no novelty; the section 6 prior-art list dates from 2026-09-27).

## Literature tasks before any novelty claim
- Designing RNAs with Language Models: https://arxiv.org/html/2602.12470v1
- SamplingDesign: https://github.com/weiyutang1010/SamplingDesign
- Montparnasse: https://arxiv.org/html/2606.07562v1
- RNA-MDLM / conditional inpainting:
  https://www.biorxiv.org/content/10.64898/2026.09.17.752279v1
  Full text was inaccessible in this review; obtain and read it before claiming
  novelty. The indexed abstract is insufficient for a detailed exclusion.
- Check targeted remasking, RNA negative design, dependency-aware local search,
  and learned search/repair. The initial review did not settle these overlaps.

## Amendment — 2026-09-27 (user instruction, session 07)
The user lifted the pilot compute caps ("use as much of both as you want") and
asked for the strongest achievable results. Local CPU/GPU use is no longer
capped at 8 CPU-hours / 2 GPU-hours or 4 workers. Unchanged: zero paid compute
or services, validation/development before a newly frozen protocol, no final
test scoring before that freeze, honest reporting of budgets and failures.
Budgets used must still be disclosed with every comparison.
