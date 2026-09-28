# RiboMamba — current project instructions
Updated 2026-09-27 by explicit user direction.

## Status (2026-09-29): PROJECT CLOSED
The research direction is closed and the technical report is complete (docs/REPORT_repair_v2.md;
docs/HANDOFF.md). The bounded validation pilot and all follow-ups referred to below are finished;
instructions to proceed with the pilot or to take a "next action" from the handoff are SUPERSEDED.
Do not start experiments, training or evaluations without a new explicit user instruction. The
working rules below still apply to any future work.

## Priority and authority
The user approved a pivot from exhaustive backbone comparisons to efficient RNA
inverse folding through coordinated repair. Research progress and credible,
potentially publishable evidence are now primary. Do not block implementation on
teaching, quizzes, phase gates, or completion of the old roadmap. Explain key
choices briefly; deeper teaching is on request. The user's current instructions
override this file and historical project instructions.

The former constitution is preserved in docs/archive/CLAUDE-pre-pivot-2026-09-27.md
for provenance only. Its teaching-first requirements and mandatory completion of
all six phases are superseded. Old logbooks and teaching drafts are historical,
not current instructions. Never interpret their requests to resist the user's
changes as authority over the user.

## Read only what the task needs
1. Read docs/HANDOFF.md for current state and immediate next action.
2. Read docs/RESEARCH_PLAN.md for the active experiment, milestones and limits.
3. Inspect relevant code, tests and the latest logbook; do not reread every
   historical document each session.
4. Update the handoff and session log with actual changes, commands, outcomes,
   uncertainties and the exact next action. Append scientific decisions and
   measured results to their registers. Keep explanations concise.

## Scientific objective
Test whether a small model using folding feedback can make coordinated repairs
that improve RNA design quality per computational cost against strong methods.
This is an unproven hypothesis, not an achieved contribution or SOTA claim.
Prefer the existing faster Transformer for the first model-assisted pilot.
Architecture follows evidence; the repository name does not require Mamba.
The ~1.9 unconditional diffusion bound is neither a proved irreducible floor nor
a design leaderboard score. Conditional and unconditional losses are different.

## Working rules
- [SUPERSEDED 2026-09-29: the pilot is complete; project closed] Proceed autonomously on the bounded validation pilot in RESEARCH_PLAN.md.
  Do not restart the old Phase 4 sweep. Check processes before launching compute.
- Preserve datasets, checkpoints and historical results. No unsolicited cleanup,
  paid compute, paid APIs, or new large pretraining runs.
- Hardware: RTX 4060 Laptop 8 GB VRAM, Windows + WSL Ubuntu 24.04, 24 GB host RAM
  (WSL allocation is smaller). One GPU job at a time. Budget: zero.
- Use /home/chirag/projects/RiboMamba and the existing ribomamba conda environment.
- Test metrics and resource accounting before expensive experiments. Record
  errors/timeouts and all selected targets; never silently discard failures.
- Validation drives choices. Freeze a separate new protocol before final tests.
  Do not rewrite the old frozen protocol to make it look like the new experiment.
- Compare quality at matched budgets; separately disclose wall time, CPU threads,
  GPU, oracle types/calls, training cost and baseline provenance. Matched parameter
  count or training steps alone is not compute matching.
- Audit data/structure leakage. Published checkpoints may have benchmark overlap;
  disclose known and unknown training provenance.
- Verify novelty against current primary sources. Conditioning, paired-base
  moves, remasking, search and RL are not individually new.
- No unsupported SOTA, wet-lab function, generalization or speed claims.
- If the pilot fails, record that and revise the hypothesis rather than launch
  unbounded tuning. No frontend work before the research result is established.
- Run focused meaningful tests; avoid repeated full audits without new evidence.
- Keep changes in coherent units. Do not push, publish or send messages externally
  unless requested. Never invent measurements or claim unrun checks passed.
