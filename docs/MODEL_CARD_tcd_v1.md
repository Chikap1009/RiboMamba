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
