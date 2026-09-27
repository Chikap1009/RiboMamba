# RiboMamba
Research code for RNA sequence generation and efficient inverse folding.

**Status (2026-09-27):** the user approved a pivot to coordinated, folding-guided
sequence repair. The new method is not implemented or validated yet. The earlier
Transformer/BiMamba training study is paused; its checkpoints and results remain
available. No SOTA result is claimed.

Start with [the handoff](docs/HANDOFF.md), [research plan](docs/RESEARCH_PLAN.md),
and [agent instructions](CLAUDE.md).

## Existing implementation
- Rfam preparation, family/clan splits and sequence/structure leakage auditing.
- Transformer masked diffusion, BiMamba-2 diffusion and autoregressive Mamba.
- Training/checkpointing and ViennaRNA/EternaFold evaluation.
- Historical protocol and measurements in [RESULTS](docs/RESULTS.md).

## Local environment
Inside WSL:
```bash
cd /home/chirag/projects/RiboMamba
source /home/chirag/miniforge3/etc/profile.d/conda.sh
conda activate ribomamba
```
Dependencies are recorded in environment.yml and environment.lock.yml.
The existing environment is already installed. Large data and model artifacts
are ignored by Git; a fresh clone does not contain them. The old Phase 4 queue
is intentionally paused; do not use it as the default entry point.

See the handoff for a verified CPU smoke-test command and the exact first task.
