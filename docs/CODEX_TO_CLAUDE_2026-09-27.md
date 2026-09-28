> **SUPERSEDED — project closed 2026-09-29.** This document is kept as a historical record. The
> pilot and every follow-up are complete; see docs/HANDOFF.md and docs/REPORT_repair_v2.md. Nothing
> here is an instruction to start work.

# Research recommendation and message for Claude Code — 2026-09-27

User request: inspect overnight work, remove unrequested compute limits, and pursue
an original, interview-worthy research contribution on this laptop, aiming for SOTA.
This is a concrete research recommendation, not a claim that SOTA has been achieved.

## Overnight review

Reviewed current code, development comparison artifacts, git history, running
processes and confirmation-look log. Development energy-filter run completed all
96 units without errors. Reported uMFE: 58% vs SAMFEO 48%; paired difference
10.4 percentage points [3.1, 18.8], on 32 targets, seeds averaged within target.
RNAinverse remains competitive at 59% by 64 seconds. Thus the filter does not
establish overall superiority. Stage B's unconditional Transformer remains negative.
Ten scoring tests passed in this review, including infeasible targets and MFE ties.
The ViennaRNA finding is an input-validity/API pitfall reproduced locally;
do not call it a newly discovered upstream bug without checking API guarantees
and obtaining upstream confirmation.

HANDOFF was stale: confirmation was launched and logged at 01:58 UTC, resumed
05:51 UTC with the same config hash. At inspection it was still running. No
confirmation outcomes were used to select the recommendation below. Training-pool
collection was also running. Existing runs were not interrupted or restarted.
The 642-unit stdout count is pending work after resume, not proof the 700-target
manifest has shrunk. Check completed + pending units before declaring completion.

## Compute correction

The 8 CPU-hour / 2 GPU-hour / 4-worker limits originated in the initial agent
pilot plan, not an explicit user requirement. The user already lifted them.
Removed stale active-plan and Stage C prose limits; changed the pilot runner to
have no default wall-time cap and removed the CLI's hard four-worker rejection.
Four workers remains a default, not a maximum. Explicit --max-hours remains
available for individual experiments. Running processes retain the explicit
1.5-hour / 2-hour settings they were launched with; let their owner resume them
without these flags if capped. No global compute cap should be reintroduced.
Preserve checkpoints and data, zero paid services, and one GPU training job at a time.

## Recommended research bet: learning competition-aware repair residuals

Working description: a small RNA repair model that predicts when a coordinated
mutation helps the intended fold more than it helps competing folds.

Current energy screening rewards low target energy. But a mutation can stabilize
both the target and its rivals. The proposed model should learn this missing
competition effect, instead of relearning the cheap target energy or imitating
unconditional RNA sequences.

For a fixed oracle and temperature, the exact identity is:

    delta log P(target) = -delta E_target / RT - delta log Z

Compute delta E_target exactly. Learn the residual -delta log Z (equivalently,
change in ensemble free energy divided by RT). Use natural logarithms consistently;
the current critic uses log10 labels, so convert by ln(10). Do not subtract a
physics term from a clipped label: derive the residual from finite, unclipped
oracle outputs, then document any training transformation.

Inputs: parent and child sequence, target pairing graph, changed positions,
parent ensemble feedback, and a small bank of actual competing folds. Compare
parent and child energies on those folds; validate each fold on the child and
exclude incompatible structures rather than trusting finite invalid energies.
This is a mechanistic hypothesis: rival-aware residual prediction should rank
moves more accurately than target energy alone, especially where the latter
stabilizes the wrong fold. It is not yet a proven novel method.

Use a small graph or existing ~1M-parameter model first. Hardware feasibility is
plausible for <=256 nt and batched proposals on an 8 GB GPU; benchmark actual
memory and latency before promising a batch size or runtime. CPU-only linear/MLP
residual models are mandatory controls. Existing data are useful, but record any
additional parent-fold or ensemble calls needed for new features.

## Research sequence and meaningful success criteria

1. Let the existing energy-filter confirmation finish unchanged and record it.
   Its result validates only that fixed filter; it does not validate a new model.
2. On training-side puzzles, collect sibling candidate groups from the same
   parent and label every sibling. Existing trajectory regression alone does not
   ensure coverage of the best-of-eight selection distribution. Split by puzzle,
   retain failed moves, and sample both early and stalled search states.
3. Run offline controls: target energy; target energy plus linear residual;
   current critic; residual critic without rivals; residual critic with rivals.
   Measure within-parent ranking and top-choice regret, not only global MSE.
4. Evaluate frozen variants online on development: full timing including feature
   construction and GPU transfers, success and target probability, target-level
   uncertainty. Test whether adding rivals actually causes a gain. Keep an
   exploration path; a wrong ranker must not suppress all unusual moves.
5. Integrate SamplingDesign and current strong available solvers, including
   Montparnasse/DesiRNA where reproducible. Give baselines adequate runs on the
   same laptop. Match oracle settings or clearly separate incompatible protocols.
   Inspect length support before deciding the scope of the final benchmark.
6. Before final tests, freeze methods, seeds, data membership, tie policy,
   constraints and wall-time endpoints. Aim for a demonstrably better quality/time
   frontier against the strongest reproduced baselines, including longer budgets.
   An improvement only over unfiltered SAMFEO is insufficient for a SOTA claim.
   Include total training cost and break-even number of design queries.
7. Keep EternaFold for an independent final robustness check. Do not tune against
   it and later describe that same oracle as unseen. No wet-lab function claims.

The research target is a distinctive method with measurable generalization and
causal ablations. Efficient computation is an evaluation axis, not a restriction
on how many hours the user permits. If the residual is not predictable enough or
inference erases the gain, record that result and reassess the mechanism.

## Other directions considered

- Certified rival-based pruning: mathematically attractive but close prior art
  exists in RNA-Undesign/LinearDecompose. Do not sell competitor bounds as new.
  A bound rejecting an immediate improvement also does not prove a search path
  can be removed safely; stepping-stone mutations may matter.
- Robust design across energy models: useful secondary endpoint, but parameter
  uncertainty and multistate/negative design already exist; broad novelty is weak.
- Another Mamba-vs-Transformer sweep or conditional diffusion alone: insufficient
  differentiation and poor fit to the negative Stage B evidence.
- Generic learned filter: worthwhile baseline, too weak as the entire novelty story.

## Primary-source novelty map (checked 2026-09-27)

- SAMFEO: structured mutation and ensemble optimization already exist.
  https://pmc.ncbi.nlm.nih.gov/articles/PMC10311297/
- SamplingDesign: continuous optimization with coupled variables and sampling;
  essential strong ensemble-design comparator.
  https://www.nature.com/articles/s41467-025-67901-3
- Designing RNAs with Language Models: solver distillation, constrained generation
  and RL already exist. This rules out generic 'LLM learns RNA design' novelty.
  https://arxiv.org/html/2602.12470v1
- Montparnasse: current search competitor; published settings differ from ours.
  https://arxiv.org/html/2606.07562v1
- RNA-Undesign/LinearDecompose: rival ensembles and interpretable probability
  bounds already exist. Reviewed abstract/indexed primary text; full paper
  comparison still needed before claiming a distinct mathematical contribution.
  https://arxiv.org/abs/2602.13610
  https://github.com/shanry/RNA-Undesign
- DesiRNA: replica-exchange search with negative design is established.
  https://pmc.ncbi.nlm.nih.gov/articles/PMC11744100/
- RNA-MDLM: conditional generation/inpainting already exist. Full text could not
  be opened; indexed abstract describes RNA-type conditioning. Do not assume
  equivalence to target-secondary-structure repair from the title alone.
  https://www.biorxiv.org/content/10.64898/2026.09.17.752279v1
- GoForth: mixed structure, sequence and coding constraints are also being studied;
  abstract reviewed, detailed comparison outstanding.
  https://arxiv.org/abs/2605.07608

Searches did not establish that the precise residual-repair proposal is new.
A missing search hit is not proof of priority. This is the strongest recommended
hypothesis from this review, not an exhaustive literature clearance.

## Message delivery status

This file is the prepared reply for Claude Code in the shared repository and is
linked from HANDOFF.md. The active Claude session is a VS Code extension process,
not a Codex chat addressable by the available messaging tool. No supported live
message channel was found, so live delivery/read receipt is NOT claimed. Do not
inject text into its stdin or edit its conversation database. The user can ask
Claude to read this file; its next standard handoff read will also point here.
