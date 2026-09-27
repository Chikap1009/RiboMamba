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

## Results 1 (measured 2026-09-27): data and fine-tuning
Data (`python scripts/tcd_data.py --workers 6`, 574 s): 150,000 Rfam train sequences folded;
149,934 with >= 4 pairs; 4,769 (3.2 %) EXCLUDED as within normalized edit distance 0.2 of a
development/confirmation/final structure (210 exclusion structures); natural train 142,533,
natural val 2,632 (~2 % of families). Design pairs: 16,820 capped uMFE designs; train 14,567
(272 pool puzzles), val 2,253 (40 held-out pool puzzles); none excluded (pool pre-audited).
Fine-tuning (`python scripts/tcd_train.py --steps 8000`, 1,351 GPU-s, peak 2.85 GB; 15.36 M
parameters of which 1.19 M adapter): masked-diffusion NELBO on held-out DESIGN puzzles
0.801 bits/nt at step 1,000 (selected) vs 1.923 for the unconditional base on the same data;
natural held-out 1.407 vs 1.837. Design-val NELBO rose afterwards (0.84, 0.97, 0.99, 1.01, 1.02 at
steps 2k-6k) while natural-val kept improving (to 1.36): over-fitting to the 272 training
puzzles' designs; the step-1,000 checkpoint is used. A lower NELBO is not yet better designs.
Sanity (one smoke dev target, 111 nt, 64 samples each): best NED 0.031 conditioned vs 0.285
unconditional; mean GC 0.62 vs 0.44; no uMFE sample from either.
Development batch ew_dev_tcd_v1 launched (tcd_sample, uncond_sample, random_pairs,
samfeo_efilter_tcdinit, samfeo_efilter; 1,024 candidates; 32 dev targets x 3 seeds).

## Results 2 (measured 2026-09-27): development batch ew_dev_tcd_v1
480/480 units valid, all complete (3,282 s; 8 workers + GPU). 32 dev targets x 3 seeds.
uMFE at 16 / 64 / 256 / 1024 candidates: tcd_sample 10.4 / 25.0 / 34.4 / 42.7 %;
uncond_sample 0.0 / 0.0 / 1.0 / 3.1 %; random_pairs (targeted random) 13.5 / 13.5 / 15.6 / 15.6 %;
SAMFEO + energy 13.5 / 33.3 / 44.8 / 58.3 %; SAMFEO + energy with TCD initial designs
9.4 / 22.9 / 42.7 / 58.3 %. Best log10 P @1024: TCD -1.72, uncond -14.06, random -2.43,
SAMFEO+energy -0.81. TCD sampling cost 57 s model time per 1,024 samples (8 workers sharing
the GPU).
Paired @1024 (a - b): TCD - random +0.271 [0.125, 0.427] (10/1/21); TCD - uncond +0.396
[0.240, 0.562] (14/0/18); uncond - random -0.125 [-0.250, -0.031]; TCD - SAMFEO+energy -0.156
[-0.271, -0.062] (0/8/24), log10 P -0.91; TCD-init - SAMFEO+energy 0.000 [-0.052, +0.052];
@64: TCD - random +0.115 [0.021, 0.219]; TCD-init - SAMFEO+energy -0.104 [-0.208, -0.021].
By wall time: TCD - SAMFEO+energy about -0.19 to -0.22 at 4-64 s.

## Verdict (pre-registered criteria)
- CONDITIONING CRITERION MET: TCD generation beats targeted random sampling (+27 pp) and the
  unconditional model with the same sampler (+40 pp) at matched sample counts, intervals
  excluding 0. Adapting the diffusion model to the target structure turns it from useless
  (Stage B, 3 % uMFE when sampling) into a strong design prior (43 % with no search).
- METHOD CRITERION NOT MET: neither TCD sampling nor TCD-seeded SAMFEO beats SAMFEO + energy
  at matched wall time. Reported as a model-adaptation result, not a method improvement.
Next (D-027): the TCD as SAMFEO's PROPOSAL distribution (SAMFEO chooses the sites, the TCD the
letters), alone and with the energy screen, against SAMFEO and SAMFEO + energy; plus more
training-side design data if the proposal test shows the over-fitting seen in validation
limits it.

## Results 3 (measured 2026-09-27): TCD as SAMFEO's proposal model — run ew_dev_tcdprop_v1
384/384 units valid. IMPLEMENTATION SLIP (found in the analysis, fixed in 63631c0): the arm named
samfeo_tcdprop was registered through samfeo_efilter, whose defaults silently added the energy
screen, so BOTH TCD arms ran "TCD proposals + energy screen (K = 8)" and are identical on every
target (0/0/32 ties); the run config under-reports that arm's settings. Valid comparisons:
TCD+energy vs SAMFEO and vs SAMFEO+energy (same batch). uMFE @1024: SAMFEO 47.9 %,
SAMFEO+energy 58.3 %, TCD+energy 54.2 %. Best NED: 0.0685 / 0.0551 / 0.0495; best log10 P:
-1.20 / -0.81 / -0.78. Model time ~38 s per unit (1,024 evaluations).
Paired @1024: TCD+energy - SAMFEO+energy uMFE -0.042 [-0.094, 0.000] (0/3/29), NED -0.006
[-0.010, -0.001] (21/11), log10 P +0.025 [-0.087, +0.138]; at wall time -0.104 @16 s,
-0.052 @64 s (slower). TCD+energy - SAMFEO: uMFE +0.063 [-0.021, +0.146], NED -0.019
[-0.028, -0.011] (30/2), log10 P +0.415 [0.172, 0.706].
Reading: conditioned-model proposals give the best ensemble quality measured so far (NED,
P) but do not beat the energy screen on uMFE or at matched wall time. The clean "TCD
proposals alone vs SAMFEO" contrast is rerun as ew_dev_tcdprop_v2 (samfeo_tcdprop_only).

## Results 4 (measured 2026-09-27): clean "TCD proposals alone" — run ew_dev_tcdprop_v2
192/192 units valid; effective settings logged per unit (no filter). Same batch as SAMFEO.
@1024 evaluations: uMFE 47.9 vs 47.9 % (paired 0.000 [-0.104, +0.104], 3/3/26); best NED
0.0523 vs 0.0685 (-0.016 [-0.026, -0.008], 29/3); best log10 P -0.86 vs -1.20 (+0.337 [0.105,
0.604], 23/9). Cost: 82.5 s model time per unit (one TCD forward pass per SAMFEO step), wall
117 s vs 40 s; at 16 s wall uMFE -0.073 [-0.135, -0.010].
Reading: with identical mutation SITES, the conditioned denoiser's LETTERS causally improve
ensemble quality per evaluation (NED, P) but not uMFE success, at ~3x wall time. Dominated by
TCD + energy screen (NED 0.0495, log10 P -0.78, uMFE 54 %, 38 s model time), which is kept for the
final benchmark; "proposals alone" is not (D-028).
