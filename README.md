# RiboMamba
Research code for RNA sequence generation and efficient inverse folding.

**Status (2026-09-28):** the repair / inverse-folding study is implemented and its
pre-registered final benchmark (protocol v2: Eterna100 V2/V1, Rfam-Taneda-27; 128 s
of one-core method time per run; 3 seeds) is complete. Its PRIMARY RESULT IS NULL:
no variant developed here solves more Eterna100 V2 puzzles than SAMFEO (71.0 of 100,
mean over seeds; energy screen 70.7; SAMFEO + target-conditioned diffusion proposals
+ screen 71.0; RNAinverse 71.7). The conditioned-proposal variant has the lowest
ensemble defect (a modest ensemble-quality gain, not a success-rate gain). Details:
[technical report](docs/REPORT_repair_v2.md) and [results](docs/RESULTS.md). The
earlier Transformer/BiMamba training study is paused; its checkpoints and results
remain available. No SOTA, novelty or biological claim is made.

Start with [the handoff](docs/HANDOFF.md), [research plan](docs/RESEARCH_PLAN.md),
and [agent instructions](CLAUDE.md).

## Existing implementation
- Rfam preparation, family/clan splits and sequence/structure leakage auditing.
- Transformer masked diffusion, BiMamba-2 diffusion and autoregressive Mamba.
- Training/checkpointing and ViennaRNA/EternaFold evaluation.
- Design harness (ribomamba/design/): budgeted, resumable, traced design runs;
  SAMFEO, DesiRNA, RNAinverse and SamplingDesign adapters; energy screen; learned
  critics; the target-conditioned denoiser ([model card](docs/MODEL_CARD_tcd_v1.md),
  [data card](docs/DATA_CARD_design.md)); final-benchmark report and figures.
- Protocols and measurements in [RESULTS](docs/RESULTS.md) and
  [PROTOCOL_design_v2](docs/PROTOCOL_design_v2.md).

## Local environment
Inside WSL:
```bash
cd /home/chirag/projects/RiboMamba
source /home/chirag/miniforge3/etc/profile.d/conda.sh
conda activate ribomamba
```
Dependencies are recorded in environment.yml and environment.lock.yml (Phase 3 freeze);
the protocol v2 environments are pinned in environment.design_v2.*.lock.yml.
The existing environment is already installed. Large data and model artifacts
are ignored by Git; a fresh clone does not contain them. The old Phase 4 queue
is intentionally paused; do not use it as the default entry point.

See the handoff for a verified CPU smoke-test command and the exact first task.
