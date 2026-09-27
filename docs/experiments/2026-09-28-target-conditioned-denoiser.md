# Experiment specification — target-conditioned masked-diffusion denoiser (TCD)

Date: 2026-09-27/28 (session 09). Status: SPECIFIED before any training (D-026).
This is the project's explicit model-adaptation question. Nothing here is yet a result.

## Question
Does adapting the Phase 2 masked-diffusion Transformer (checkpoints/tf_M_do0/best.pt, EMA,
14.17 M parameters, trained unconditionally on Rfam) to condition on the TARGET STRUCTURE turn
it into a useful designer or repair proposer, at matched compute, compared with the
non-neural methods (targeted random sampling, SAMFEO, SAMFEO + energy pre-screen)?
Stage B showed the UNCONDITIONAL model adds nothing to repair (D-020); this tests whether the
missing ingredient was conditioning.

## Model (adaptation, not retraining from scratch)
- Base: TransformerDenoiser with the EMA weights, unchanged.
- Adapters, all ZERO-INITIALISED so the adapted model starts as exactly the base model:
  (1) a target-bracket embedding ('.', '(', ')') added to the token embedding;
  (2) pair message passing after every block: h_i += W_l LayerNorm(h_partner(i)) for target-
      paired positions (W_l zero-initialised, one per layer).
- Everything trains (base included) with a lower learning rate for base weights; ablation
  with the base frozen if time allows.
- Objective: the same masked-diffusion NELBO (MDLM, 1/t weighting) as Phase 2, conditioned on
  the structure. Sampling: the same monotone unmasking sampler; a paired position is revealed
  together with its partner, the pair drawn from the product of the two conditional marginals
  RESTRICTED to canonical pairs (an approximation to the joint, stated as such).

## Training data (training side only; leakage-audited)
- Natural pairs: Rfam TRAIN sequences (data/processed/train.parquet, <= 256 nt) with their
  ViennaRNA 2.7.2 MFE structures (backtracked MFE: the native solves its own structure).
- Design pairs: distinct uMFE solutions found by SAMFEO on the 700 TRAINING-pool puzzles
  (manifests/eternaweb_trainpool_v1.json; 50,649 designs for 312 puzzles), capped per puzzle
  to avoid a few puzzles dominating.
- Exclusion: any training pair whose structure is within normalized edit distance <= 0.2 of any
  eternaweb_dev_v1 target (development AND confirmation) or any final-manifest structure
  (Eterna100 V1/V2, Rfam-Taneda-27). Rfam-Taneda-27 is natural Rfam-derived: residual family
  overlap with Rfam training is possible and will be disclosed; its results are secondary.
- Model selection on held-out training-pool puzzles and a held-out slice of natural pairs.

## Evaluation (32 development targets x seeds 0-2; confirmation and final sets untouched)
A. Generation: N conditioned samples per target (checkpoints at 16/64/256/1024), each scored by
   the harness: uMFE success, best NED, best log10 P versus samples and wall time (GPU
   included). Controls: targeted random designs (random_pairs), the UNCONDITIONAL base model
   with the same sampler and pair restriction (isolates conditioning), SAMFEO + energy.
B. Seeding: SAMFEO + energy with its k = 10 initial designs drawn from TCD instead of its
   targeted random initialisation (sampling cost charged).
Endpoints and statistics as in the online batch (paired per target, bootstrap over targets).

## Success and failure criteria (fixed now)
- Conditioning works (a model-adaptation result) if TCD generation beats BOTH targeted random
  sampling and the unconditional model with the same sampler by >= 10 pp uMFE at matched
  sample count, intervals excluding 0.
- A method result only if TCD (generation or seeding) beats SAMFEO + energy at matched wall time
  by >= 5 pp uMFE or >= 0.3 log10 P. Otherwise the TCD is reported as a conditioning result (or
  a negative one), not as an improvement over the non-neural method.

## Costs reported
Structure folding for natural pairs (CPU), leakage audit (CPU), fine-tuning GPU time and peak
memory, sampling throughput (designs/s on this GPU), and break-even queries versus search.
