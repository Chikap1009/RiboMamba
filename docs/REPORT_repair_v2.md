# Efficient RNA inverse folding: energy-screened search, learned critics, and a target-conditioned diffusion denoiser

Technical report draft — 2026-09-27. Development results are final; FINAL-BENCHMARK results are
pending (protocol v2 frozen 2026-09-27, docs/PROTOCOL_design_v2.md) and are marked [PENDING].
All numbers use ViennaRNA 2.7.2, Turner 2004, 37 C, dangles 2; success = unique MFE (uMFE).

## 1. Summary
- A cheap target-energy pre-screen of SAMFEO's own mutations (best of K = 8 by E(target))
  raises uMFE success on hard development puzzles from 48 % to 58 % at 1,024 evaluations,
  replicated three times and confirmed once on sealed puzzles (+9.4 pp [1.0, 19.8]), and gives
  the best ensemble quality at every time budget of a one-core frontier. It is non-neural and not
  new as an idea (INFO-RNA orders moves by target-energy change); the contribution is measured.
- Neural results: an unconditional masked-diffusion model (14 M parameters, Rfam) proposing repairs
  adds nothing; learned critics that rank mutations cut offline ranking regret ~70 % yet do not
  beat the energy screen online; a physics-informed "competition residual" adds nothing to a
  per-position critic.
- A target-conditioned version of the same diffusion model (zero-initialised adapters, 23 GPU-min
  of fine-tuning on training-side data) turns sampling from 3 % to 43 % uMFE on hard development
  puzzles without any search (targeted random: 16 %). Used as SAMFEO's proposal model it improves
  ensemble quality per evaluation causally, but not uMFE, and costs 2-3x wall time.
- Final benchmark (Eterna100 V2/V1, Rfam-Taneda-27): [PENDING].

## 2. Setup
Hard development set: 64 Eterna web player puzzles (32 development + 32 sealed confirmation),
leakage-audited (> 0.2 normalized edit distance from Eterna100 V1/V2, Rfam-Taneda-27/29,
RNAsolo-764) and chosen by a method-free hardness probe; natural Rfam validation targets were at
ceiling (the starting design alone solved most). Harness: per-candidate traces with per-kind
oracle counts, monotone method-time clocks, resumable units, and wall-clock-limited baselines
invalidated if the machine slept. Baselines reproduced locally: SAMFEO (pinned), RNAinverse,
DesiRNA (own env), SamplingDesign (built; one thread, under-budgeted vs its 64-core defaults).

## 3. Development results (32 hard puzzles x 3 seeds)
One-core quality-time frontier (uMFE at 1 / 16 / 64 / 256 s; final best log10 P):
SAMFEO 29/45/52/58 %, -0.74; SAMFEO + energy 33/54/60/64 %, -0.70; RNAinverse 43/55/62/62 %,
-1.10; DesiRNA 13/34/57/71 %, -0.76; SamplingDesign 0/25/33/38 %, -2.09. No method dominates:
the screen gives the best ensemble quality at every budget; RNAinverse is fastest to a first
solution; DesiRNA leads uMFE at 256 s.

Learned filters (online, 1,024 evals): energy screen 58 %; critic_v1 52 %; sibling critics
53-55 %; linear residual 54 %. Offline, per-position critics reduce best-of-8 regret from 1.00 to
0.28-0.31 ln P, but the gain does not survive search dynamics; critics produce more solutions per
evaluation on puzzles they can already solve and solve fewer distinct puzzles.

Target-conditioned denoiser (TCD): held-out design NELBO 0.80 vs 1.92 bits/nt for the
unconditional base. Sampling at 1,024 samples: 42.7 % uMFE vs targeted random 15.6 % (+27 pp
[12.5, 42.7]) and unconditional 3.1 % (+40 pp [24, 56]). As SAMFEO's proposal model with identical
mutation sites: uMFE unchanged (0.0 [-10.4, +10.4]), NED -0.016 [-0.026, -0.008], log10 P +0.34
[0.11, 0.60], ~3x wall time; with the energy screen: NED 0.050, log10 P -0.78 (best measured
quality), uMFE 54 % (vs 58 % screen alone).

## 4. Final benchmark (protocol v2, frozen)
[PENDING — filled only from final_v2_* runs by scripts/final_report.py.]

## 5. Limitations
32-puzzle development sets; one laptop (8 GB GPU, 20 logical CPUs) with heavy contention during
batches (all compared methods share each batch); SamplingDesign under-budgeted; DesiRNA's time
limit is wall-clock; the TCD is trained on ~270 design puzzles and over-fits them after 1k steps;
Rfam-Taneda-27 may share families with the Rfam data used by the TCD. Computational folding only;
no biological function is claimed.

## 6. Prior art and novelty
Energy-guided proposals: INFO-RNA (2006). Rival structures/bounds: LinearDecompose (2026).
Search baselines: SAMFEO (2023), SamplingDesign (2026), DesiRNA, Montparnasse (2025/26).
Learned design: LEARNA, EternaBrain, language models distilled from SAMFEO (Gautam et al. 2026),
conditional RNA diffusion (RNA-MDLM, 2026). Nothing here is claimed as SOTA or as a new idea;
contributions are measured efficiency/quality results and careful negative results.
