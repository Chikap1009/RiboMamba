# Model card — target-conditioned masked-diffusion denoiser (TCD), `checkpoints/tcd_v1/tcd.pt`

Written 2026-09-28 from measured records only (docs/experiments/2026-09-28-target-conditioned-denoiser.md,
checkpoints/tcd_v1/train_log.json, docs/RESULTS.md). Research artifact; not a validated design tool.

## What it is
- A masked-diffusion (MDLM) Transformer over RNA sequences that generates or in-fills nucleotides
  **conditioned on a target secondary structure** (dot-bracket, pseudoknot-free).
- Base: the Phase 2 unconditional Transformer `checkpoints/tf_M_do0/best.pt` (EMA weights, 14.17 M
  parameters, trained on Rfam training sequences; sha256 a2c27a79...).
- Adaptation: zero-initialised adapters, so step 0 equals the base model exactly (tested):
  a target-bracket embedding ('.', '(', ')') added to the token embedding, and per-layer pair message
  passing between target-paired positions. 15.36 M parameters in total, 1.19 M of them adapters.
- Checkpoint: `checkpoints/tcd_v1/tcd.pt` (sha256 faa4ab68...), the step-1,000 weights, kept as the best
  by design-validation NELBO (scripts/tcd_train.py keeps only the best).
- Code: ribomamba/models/conditioned.py (model, `conditioned_nelbo`), ribomamba/design/tcd.py (sampling,
  in-filling, harness methods), scripts/tcd_data.py, scripts/tcd_train.py.

## Training
- Objective: the masked-diffusion NELBO with 1/t weighting, conditioned on the structure.
- Data (training side only; see docs/DATA_CARD_design.md): 142,533 natural pairs (Rfam training
  sequences <= 256 nt with their ViennaRNA 2.7.2 MFE structures) and 14,567 design pairs (capped uMFE
  designs found by SAMFEO on 272 training-pool Eterna web puzzles), mixed 50/50 per batch.
- Leakage filter: 4,769 natural pairs (3.2 %) removed for lying within normalised edit distance 0.2 of
  any development, confirmation or final-benchmark structure.
- Run: `python scripts/tcd_train.py --steps 8000` (batch 64, lr 1e-4 base / 1e-3 adapters, seed 0);
  1,351 GPU-s on an RTX 4060 Laptop GPU, peak 2.85 GB. Data preparation 574 s on 6 CPU workers.

## Measured behaviour
| measure | value |
|---|---|
| held-out design NELBO (bits/nt), step 1,000 | 0.801 (unconditional base 1.923) |
| held-out natural NELBO (bits/nt), step 1,000 | 1.407 (base 1.837) |
| over-fitting | design-validation NELBO rose after step 1,000 (0.84 at 2k, ~1.02 at 6-8k) |
| development sampling, 32 hard Eterna web puzzles, 1,024 samples | 42.7 % uMFE (targeted random 15.6 %, unconditional 3.1 %) |
| as SAMFEO's proposal model, development, 1,024 evaluations | uMFE unchanged; best NED -0.016, log10 P +0.34; ~3x wall time |
| final benchmark, Eterna100 V2, 128 s, sampling | 61.3 puzzles (mean over seeds) vs targeted random 56.0 (+5.3 pp [-1.7, +12.3]) |
| final benchmark, V2, SAMFEO + TCD proposals + energy screen | 71.0 puzzles (= SAMFEO); lowest best NED of all methods, 0.0400 vs SAMFEO 0.0459 |

Sampler: 32 unmasking steps, temperature 1.0; a paired position is revealed with its partner, the pair
drawn from the product of the two conditional marginals restricted to canonical pairs (an
approximation to the joint). Cost: one GPU forward pass per sampling step or proposal; ~57 s model time
per 1,024 samples with 8 processes sharing the GPU; a ~2-3 s model load per process.

## Inference paths and how to select them (added 2026-09-29)
- Default (reference): EAGER forward. Every frozen protocol-v2 method name uses it
  (samfeo_tcdprop_efilter, tcd_sample, samfeo_efilter_tcdinit), and those names keep this behaviour.
- CUDA graph (preferred on the validated configuration, opt-in): method samfeo_tcdprop_efilter_graph,
  i.e. settings key tcd_forward = "cuda_graph" (tcd.infill_graphed). The forward for one target and
  batch shape is captured once per process and replayed; one graph is held per process and recaptured
  when the target changes. It applies to SAMFEO proposals (infill) only; TCD sampling (tcd_sample) and
  TCD initial designs always run eager.
- Fallbacks: the model runs on CUDA when a GPU is visible, otherwise on the CPU (the runner hides CUDA
  unless --gpu is given). On the CPU, infill_graphed falls back to the eager path (tested). If CUDA is
  visible but graph capture fails, the unit fails with an error; there is no automatic fallback. CPU runs
  use float32 while GPU runs use bfloat16 autocast, so CPU and GPU results are not numerically identical.
  An unknown tcd_forward value raises an error.
- Validated configuration (only): RTX 4060 Laptop GPU, NVIDIA driver 595.79, WSL2 (kernel 6.18),
  PyTorch 2.10.0+cu128 (CUDA 12.8, cuDNN 9.10.2). There, graph and eager logits were bitwise identical
  and searches at a matched candidate budget were identical (tests/test_tcd_graph.py). This is not
  guaranteed on other GPUs, drivers, PyTorch versions or operating systems; at a matched TIME budget the
  graphed variant evaluates more candidates, so its runs differ by design.
- Measured effect (development; docs/experiments/2026-09-28-tcd-inference-efficiency.md): proposal
  overhead per candidate reduced 2.48x with 4 concurrent cold runs (1.51x cold, ~1.8x warm when run alone);
  ~2x more candidates within 16 s; still 5-6 uMFE points below SAMFEO + energy screen on the development
  puzzles. Setup before the first candidate (~3 s cold) is unchanged.

## Intended use and limits
- Intended: research on structure-conditioned sequence generation and on neural proposals inside
  design search, evaluated with the harness in this repository.
- The gain is a **model-adaptation** result on development puzzles; it transferred only weakly to
  Eterna100 and does not improve design success rate on the final benchmark. Not SOTA.
- Success is measured with one folding model (ViennaRNA 2.7.2, Turner 2004, 37 C). Under EternaFold only
  25-39 % of the best designs of any method fold to the target. No biological function, expression or
  wet-lab behaviour is claimed or tested.
- Trained on <= 256 nt sequences; Eterna100 targets up to 400 nt are outside that range.
- Rfam-Taneda-27 targets are Rfam-derived; family overlap with the Rfam training sequences is possible
  (structures within edit distance 0.2 were removed, families were not).
- Over-fits the ~270 design puzzles after ~1k steps; more design data is the stated next question.
