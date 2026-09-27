# Current handoff — 2026-09-27

## User decision
The user approved the research pivot and repository updates. Research quality now
takes priority over teaching gates and completing the old architecture sweep.
Continue in Claude Code or a lighter Codex model. No need to request permission
again for the bounded validation pilot. Read CLAUDE.md and RESEARCH_PLAN.md.

## Exact next task
Implement Stage A's validation-only manifest, robust candidate scoring and resource
trace, with focused tests and an 8-target smoke run. Inspect the existing folding
and target-building code first. Then add the cheap repair controls and a strong
baseline adapter. Do not start new training, run final tests, or restart Phase 4.
Return measured smoke results and runtime estimates, not another broad plan.

The new repair method, harness and external baseline integrations are NOT built
yet. Do not mistake the plan for implementation.

## Execution environment
WSL Ubuntu-24.04:
```bash
cd /home/chirag/projects/RiboMamba
source /home/chirag/miniforge3/etc/profile.d/conda.sh
conda activate ribomamba
```
Conda prefix: /home/chirag/miniforge3/envs/ribomamba.
Host path: \\wsl.localhost\Ubuntu-24.04\home\chirag\projects\RiboMamba.
rg is unavailable inside WSL; use find/grep if still absent. GPU is an RTX 4060
Laptop 8 GB. Do not reinstall the environment or download data unnecessarily.

## Compute state
The Phase 4 group was deliberately stopped after the seed-2 checkpoint at step
27,500. See PHASE4_PAUSED.md. Existing best.pt/last.pt are retained.
The queue entry point is guarded by that marker. Historical process IDs must not
be reused. Always inspect live processes/GPU before launching work.

## Existing assets
- data/processed/{train,val,test}.parquet: 452867/57052/56873 sequences;
  family/clan-aware split plus sequence and Infernal overlap filtering.
- data/processed_split1: old replication split.
- data/targets/rfam_val.parquet and bprna_val.parquet: validation target sources.
- checkpoints/tf_M_do0/best.pt: initial Transformer EMA candidate.
  Inspect config.json and ribomamba/models/checkpoint.py to load it correctly.
- Transformer width384, 8layers, 6heads, ~14.17M parameters; 5 original-split
  seeds and one replication trained. Initial best validation bound 1.9040.
- BiMamba width384,14layers,~14.01M parameters; LR.01/dropout.1 selected.
  Seeds0/1 complete, seed2 interrupted at saved27500; remaining seeds/AR sweep
  not completed. Seed2 is not a completed 30k-step result.
- Prior observed throughput ~105k nt/s Transformer vs ~32-34k BiMamba for
  short sequences. Use Transformer first; no architectural superiority claimed.
- ribomamba/diffusion/masked.py: objective and monotone unmasking sampler.
- ribomamba/models/: backbones/build/checkpoint loading.
- ribomamba/eval/folding.py, eternafold.py, harness.py, protocol.py:
  existing scoring/instruments, including candidate-target validation caveat.
- scripts/build_targets.py: target provenance and construction.
- scripts/train.py: atomic checkpoint saves; resume does not reproduce exact
  batch/RNG cursor. No signal-triggered save is implemented.
- tests/: existing CPU, GPU and external-tool tests.

## Scientific cautions inherited from review
The ~1.9 plateau is not a proved floor. The old study matches parameters and
nominal steps/tokens, not wall-clock or FLOPs. Final three-way testing is incomplete.
Old protocol guards do not protect every historical direct data reader.
Old sample outputs use existence checks and can be partial after interruption.
Phase5 drafts are exploratory: GC-stem designs had 82.6% exact success versus
native100%, despite text claiming a win on both endpoints. Do not reuse that claim.
Current target scoring may raise on noncanonical candidate/target pairs.
Old study's final evaluation and the new design experiment must remain distinct.

## Tests already run during familiarisation
CPU-only, CUDA hidden:
```bash
CUDA_VISIBLE_DEVICES= OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 POLARS_MAX_THREADS=2 \
python -m pytest -q -p no:cacheprovider tests/test_tokenizer.py tests/test_dataset.py \
tests/test_structure_search.py tests/test_sweeps.py tests/test_autoregressive.py \
tests/test_transformer.py tests/test_diffusion.py tests/test_stats.py \
tests/test_distributions.py \
-k "not tiny_model_can_memorise_four_sequences and not novelty_and_internal_identity_with_mmseqs2"
```
68 passed, 2 deselected. Not a full-suite/GPU/folding integration certification.

## Usage-efficient collaboration
Use one implementation agent, one milestone at a time. Sol Medium is the suggested
Codex default; use the existing Claude Code setup if it better fits the user's
subscription. No exact account-limit savings were established. Use a stronger
model for novelty/protocol review, difficult failures and final claim checking,
not for waiting on training or rereading long logs. Shell jobs do not need a
continuously chatting assistant. Maintain this short handoff after each milestone.
Do not change account settings or buy plans on the user's behalf.

## Paste into Claude Code or a new Codex session
Read CLAUDE.md, docs/HANDOFF.md and docs/RESEARCH_PLAN.md. The user approved the
2026-09-27 pivot to efficient RNA repair and superseded the old teaching gates.
The old training queue is intentionally paused. Implement the exact next task in
HANDOFF.md, including focused tests and the validation smoke run. Use existing
data/environment/checkpoints; keep final tests untouched. Work within the stated
pilot budget, update the handoff with evidence, and do not restart broad training.
