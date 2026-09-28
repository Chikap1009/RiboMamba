# Efficient RNA inverse folding: energy-screened search, learned critics, and a target-conditioned diffusion denoiser

Technical report draft — updated 2026-09-28 with the FINAL benchmark (protocol v2, frozen 2026-09-27,
docs/PROTOCOL_design_v2.md; report data/repair_pilot/final_v2_report.json, status FINAL, commit 842124b).
All numbers use ViennaRNA 2.7.2, Turner 2004, 37 C, dangles 2; success = unique MFE (uMFE).

## 1. Summary
- Final benchmark (Eterna100 V2, 100 puzzles, 128 s of one-core method time, 3 seeds): no variant
  developed here improves uMFE success. SAMFEO solves 74 puzzles (71.0 mean over seeds), SAMFEO with
  a target-energy pre-screen 73 (70.7), the screen plus target-conditioned diffusion proposals 73
  (71.0), RNAinverse 75 (71.7); all are within one puzzle and statistically indistinguishable.
- Ensemble quality does improve, modestly and consistently: the screen lowers the best ensemble
  defect (NED) on 72 of 100 puzzles, and conditioned-denoiser proposals with the screen give the
  lowest NED of all methods (0.040 vs SAMFEO 0.046; better on 82, worse on 14) at equal uMFE by
  128 s, but start slowly (40 % at 4 s vs 63 %).
- On hard development puzzles the screen had raised uMFE from 48 % to 58 % at 1,024 evaluations
  (confirmed once on sealed puzzles, +9.4 pp); that gain did not transfer to Eterna100 at 128 s. The
  screen is non-neural and not new as an idea (INFO-RNA orders moves by target-energy change).
- Model adaptation: a target-conditioned version of a 14 M-parameter masked-diffusion model
  (zero-initialised adapters, 23 GPU-min of fine-tuning) raised sampling success on hard development
  puzzles from 3 % (unconditional) and 16 % (targeted random) to 43 %. On Eterna100 its gain over
  targeted random designs is small (+5.3 pp [-1.7, +12.3] by time; +8.3 pp at 1,024 samples, 72
  puzzles, exploratory). It is a development model-adaptation result, not a benchmark-level gain.
- Negative results: an unconditional diffusion model proposing repairs adds nothing; learned critics
  cut offline ranking regret ~70 % yet lose to the energy screen online; a physics-informed
  "competition residual" adds nothing to a per-position critic.

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
solution. CORRECTION (2026-09-28 review): development DesiRNA times were stamped by step fraction
while DesiRNA overshoots its limit (~240 s for a nominal 128 s), so its development curve is
optimistic and "DesiRNA leads at 256 s" is unverified; SamplingDesign's may be pessimistic (output
lost at the kill). The final benchmark uses real per-candidate timing for both (amendment 4).

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
Sets: Eterna100 V2 (primary, 100 puzzles, 19-400 nt), Eterna100 V1 (V2 results on the 81 shared
structures + the 19 V1-only puzzles), Rfam-Taneda-27. Eight methods, seeds 0-2, 128 s method time on
one core and <= 5,010 candidates per unit; 3,504 units, all valid, no errors. Wall-clock baselines use
real per-candidate timestamps and hard kills (amendments 4, 4b); units that ran pre-fix code were
superseded and rerun. Every figure is from the FINAL report (filled from it, not recomputed).

Eterna100 V2, solved by 128 s (any seed / mean over seeds) and seed-mean uMFE at 1 / 16 s:
RNAinverse 75 / 71.7 (59 / 67 %); SAMFEO 74 / 71.0 (54 / 66 %); SAMFEO + TCD proposals + screen
73 / 71.0 (1 / 66 %); SAMFEO + screen 73 / 70.7 (58 / 69 %); DesiRNA 74 / 68.3 (17 / 52 %); TCD
sampling 62 / 61.3 (0 / 54 %); targeted random 56 / 56.0 (49 / 55 %); SamplingDesign (1 thread)
48 / 43.7 (7 / 21 %).
Paired @128 s (bootstrap over puzzles): screen - SAMFEO uMFE -0.3 pp [-3.3, +2.0], NED -0.0026
[-0.0047, -0.0005]; TCD + screen - SAMFEO uMFE 0.0 [-3.7, +3.7], NED -0.0059 [-0.0085, -0.0035];
TCD + screen - screen NED -0.0033 [-0.0055, -0.0015]; TCD sampling - random uMFE +5.3 pp [-1.7,
+12.3]. Best NED (mean over units with a design): TCD + screen 0.0400, screen 0.0434, SAMFEO
0.0459, RNAinverse 0.0510.
Rfam-Taneda-27: near ceiling (24/27 for RNAinverse, SAMFEO, both screened variants and DesiRNA).
Eterna100 V1-only: 0/19 for every method; SAMFEO's own published V1 results also solve none of these
19 by uMFE (they are the puzzles V2 redesigned for the Vienna 2 energy model). V1 combined: RNAinverse
72, SAMFEO 71, screened variants 69, DesiRNA 68 (any seed).
EternaFold (independent model) folds 25-39 % of the best V2 designs to the target (TCD + screen 39 %,
SAMFEO 38 %). Published results of other methods use other budgets and hardware and are not comparable
with these numbers (SamplingDesign 79/78 on Eterna100 with Turner 2004; DesiRNA 97 of V2 in 24 h).

## 5. Limitations
The final budget is short (128 s, one core) and favours fast restarts; longer budgets could order
methods differently. 32 paired comparisons are reported without multiplicity correction. TCD units
pay a model load (~2-3 s) and share one GPU among 8 concurrent units inside their method time.
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
