# Experiment record — Stage C candidate: a learned repair critic for coordinated mutations

Date: 2026-09-27 (session 07). Status: PROPOSED, CONDITIONAL on the Stage B and
energy-filter results recorded in docs/HANDOFF.md. Nothing below has been run
unless the status line says so.

## Hypothesis
Late in search only ~2 % of coordinated proposals improve the objective
(ew_dev1024_v1 traces), so most expensive folds are spent on non-improving
proposals. If improving coordinated mutations are predictable from the target,
the current sequence and the folding feedback the search already has
(per-position ensemble defects), a small model that ranks K candidate mutations
and sends only the best to the partition-function fold should reach the same
quality with several-fold fewer expensive evaluations than (i) the unfiltered
search and (ii) a non-neural filter (best of K by target-structure energy).

## Design (fixed before any fitting)
- Search host: SAMFEO (pinned e78b4b5), unmodified; only its mutation call is
  wrapped: draw K = 8 children with SAMFEO's own structured mutation, score
  them, keep the best. Variants: none (SAMFEO), energy (min E(target)),
  critic (max predicted improvement). Same budgets, seeds, targets.
- Training data: SAMFEO trajectories (defaults, unfiltered) on the training pool
  manifests/eternaweb_trainpool_v1 (ribomamba/design/training_pool.py): Eterna
  web puzzles passing the same eligibility and hardness probe, each > 0.2
  normalized edit distance from every eternaweb_dev_v1 target (dev AND
  confirmation), every test-side audit structure and every other pool puzzle.
  600 train / 100 held-out puzzles (puzzle-level split). Example = (target,
  parent sequence, parent per-position defects, child sequence) -> label
  Delta log10 P(target) (child - parent), plus the improvement indicator.
- Model: small bidirectional Transformer (about 1 M parameters: 4 layers,
  width 128, 4 heads), per-position input embeddings for parent and child
  letters, target bracket, changed flag, partner letters (parent/child) and
  the parent defect; plus the child's Delta E(target) as a global feature so
  the critic can at least reproduce the energy filter. Output: predicted
  Delta log10 P from positions that changed and a global token. Trained from
  scratch (the unconditional Transformer's inputs do not include structure).
- Objective: Huber regression on clipped Delta log10 P + BCE on improvement.
- Selection: held-out puzzles only (Spearman within parent groups and
  top-1-of-K improvement precision versus the energy filter). Development
  targets are used only to evaluate the frozen critic online.
- Resources: no fixed CPU/GPU-hour cap; the user lifted the original pilot
  limits. Report actual data-generation, training and evaluation costs. Online
  evaluation remains 32 dev targets x 3 seeds x 1024 evals for comparability.
  Measure peak GPU memory before choosing batch size; the earlier <1 GB at
  batch 256 statement was an estimate, not a verified memory benchmark.
- Ablations: K = 8 random pick (= SAMFEO), energy filter, critic without the
  defect input, critic without Delta E input.
- Decision rule (RESEARCH_PLAN continuation criterion): critic must beat BOTH
  SAMFEO and the energy filter at comparable wall time (critic inference
  included) by >= 10 points uMFE or >= 3x fewer partition-function
  evaluations at comparable quality; otherwise record the negative result.

## Measured before training (2026-09-27, ~12:05 IST)
- Data: trainpool_samfeo_v1 (700 pool puzzles x 400 SAMFEO evals, seed 0,
  2,253 s + 918 s before the WSL restart); 273,000 transitions (234,000 train /
  39,000 held-out puzzles' transitions), 62,811 distinct parents (defects
  recomputed in 189 s on 8 workers). Base rate of improvement: 8.3 %.
- Critic: 825,602 parameters. Peak GPU memory at the worst-case shape
  (L = 256), training step with AdamW and bf16 autocast: 1,522 MiB at batch 256,
  3,010 MiB at batch 512 (RTX 4060 Laptop, 8 GB). Batch 256 chosen.

## Prior art to check before any novelty claim
Learned mutation/move policies (EternaBrain player moves; LEARNA / Meta-LEARNA
RL), surrogate-assisted and learned-filter local search, NUPACK defect-weighted
mutation, SAMFEO structured mutation, and search distillation into language
models (Gautam et al. 2026). The combination may not be new.
