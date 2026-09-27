# Experiment specification — competition-aware residual repair (2026-09-27, session 09)

Status: SPECIFIED before any fitting. Proposed by the session-08 review
(docs/CODEX_TO_CLAUDE_2026-09-27.md); adopted by the user's instruction.
Novelty is NOT established; see "Closest prior art".

## Hypothesis and mechanism
For a fixed oracle (ViennaRNA 2.7.2, Turner 2004, 37 C, dangles 2), a mutation
parent -> child changes the target's log probability exactly by

    y = Delta ln P(target) = a + r,   a = -Delta E_target / RT,   r = -Delta ln Z,

natural logarithms, RT = 0.61633 kcal/mol (R = 1.98717 cal/(mol K), 310.15 K,
scoring.KT). Target-energy screening ranks siblings by a only. Hypothesis:
r (ensemble competition) is large, systematically cancels a, and is predictable
from the parent's actual rival folds; ranking by a + r_hat should reduce
best-of-K selection regret and, inside search, give more quality per wall
second than energy screening and the generic critic.

## Evidence before this experiment (measured, training-side only)
trainpool_samfeo_v1 transitions (273,000; 700 training-pool puzzles; children
of the same parent across SAMFEO steps, NOT true sibling groups):
identity max error 1.6e-4 (stored-energy rounding); var(y) 7.09, var(a) 7.53,
var(r) 9.01, corr(a, r) = -0.573; R^2(y ~ a) = 0.147. Within 27,713 parent
groups: median Spearman(a, y) 0.543; median corr(a, r) -0.678, median slope of
r on a -0.630; energy's top-1 pick is not the best in 58 % of groups and is
worse than the best by more than ln 2 in 25 %. Not yet shown: that rival folds
explain r.

## Closest prior art (primary sources checked 2026-09-27) and what this adds
- LinearDecompose / RNA-Undesign (Zhou, Mathews, Huang, arXiv:2602.13610): rival
  structures and probability BOUNDS for designability; explicitly not integrated
  into design search ("future work"). Closest overlap on rivals.
- SAMFEO (Zhou et al. 2023) and SamplingDesign (Tang et al., Nat. Commun. 2026;
  Eterna100 79/78 MFE/uMFE, geometric-mean P 0.502, NED 0.035): optimise
  P(target) directly; no learned proposal ranking.
- DesiRNA (REMC with ensemble/negative-design objectives; Eterna100 V2 97/100
  in 24 h, 85 in < 1 min); Montparnasse (NRPA; V1/Turner 1999 100/100).
- FMQA (arXiv:2602.16643): generic surrogate-assisted optimisation for inverse
  folding. dFX (FoldX residual correction, proteins): learned residuals over
  physics energies. EternaBrain/LEARNA: learned move policies.
- Our generic critic (critic_v1): learns Delta log10 P directly, without
  separating the exact energy term or seeing rivals.
What this experiment adds, IF it works: a learned, rival-conditioned estimate
of the mutation-level competition term -Delta ln Z, used to rank coordinated
mutations inside a design search, with causal ablations isolating the rivals.
A missing search hit is not proof of novelty.

## Data (training side only; development/confirmation/test never used for fitting)
- Puzzles: manifests/eternaweb_trainpool_v1 (700; 600 train / 100 held-out, split
  by puzzle; every puzzle > 0.2 normalized edit distance from every other pool
  puzzle, every eternaweb_dev_v1 target and every test-side audit structure).
- Parent states: from trainpool_samfeo_v1 traces, P = 8 parents per puzzle,
  stratified by the eval index at which SAMFEO first mutated them: early
  (< 32), mid (32-159), late (>= 160, stalled search); all phases kept.
- Sibling groups: for each parent, K = 16 children drawn with SAMFEO's own
  mutate_structured (T = 1, the parent's positional defects), seeded; children
  equal to the parent or duplicated are dropped and counted. EVERY child is
  scored with scoring.score (full partition function). Failed or non-improving
  moves are kept.
- Rival bank per parent: after the parent's partition function, 200 stochastic
  Boltzmann samples (pbacktrack); distinct structures other than the target;
  keep the R = 16 lowest-energy on the parent, plus the parent's MFE structure
  if distinct. For each child, a rival counts only if every one of its pairs is
  canonical on the child (hairpin rule is sequence-independent); incompatible
  rivals get weight exactly 0 and are flagged. Finite eval energies of
  incompatible folds are never used.
- Labels: y from stored ln P = (G - E_target)/RT (finite, unclipped); a exact;
  r := y - a. Any training transform (Huber loss) is on unclipped r.

## Variants (smallest first; larger models only after a diagnosed limitation)
1. energy: score = a.
2. rival-bank physics (no learning): r_bank = -(LSE_child - LSE_parent), LSE over
   {target} U compatible rivals of -E/RT; score = a + r_bank.
3. linear residual (ridge, CPU): r ~ scalar features (a, r_bank, rival Delta E
   summary, changed pair/unpaired counts, GC change, parent defects at changed
   positions, phase-free).
4. small MLP residual (CPU), same features.
5. critic_v1 (existing generic critic; Delta log10 P * ln 10), baseline.
6. residual Transformer WITHOUT rivals (critic architecture, target r).
7. residual Transformer WITH rivals (6 + per-position rival bracket/compatibility
   channels for the top rivals + rival Delta E globals).
6 and 7 are trained only if 3/4 leave a diagnosed, rival-related limitation
(e.g. held-out regret concentrated where r_bank is badly calibrated).

## Offline evaluation (100 held-out puzzles)
Within-group Spearman(score, y); top-1 regret in ln P (mean, median, share >
ln 2); P(top-1 is the true best); best-of-8 regret over random 8-subsets of each
16-sibling group (matches the online filter). Bootstrap over puzzles.
Selection rule: lowest mean held-out best-of-8 regret; ties -> simpler variant.
Rival claim requires BOTH 2 < 1 and (7 < 6 or rival features carrying the gain in
3/4 ablations) with puzzle-bootstrap intervals excluding 0.

## Online evaluation (frozen variants, development targets only)
SAMFEO filtered mutation, K = 8 (and the energy filter's best K from the
development K ablation as a second control), 32 dev targets x seeds 0-2 x 1024
evaluations. All costs counted: rival banks (one extra partition function +
sampling per DISTINCT parent, cached, counted as internal calls), feature
construction, GPU transfer and inference (model_wall_s), harness re-scoring
subtracted as measurement. Exploration: SAMFEO's frontier and parent sampling
are unchanged; an epsilon = 0.125 random-sibling variant tests whether strict
top-1 selection suppresses useful paths. Endpoints: uMFE success, best log10 P,
best NED at 64/256/1024 evaluations and 1/4/16/64 s wall; paired per-target
bootstrap intervals; failures and early stops reported.

## Failure criteria (decided now)
- Mechanism unsupported if rival physics (2) does not reduce held-out best-of-8
  regret vs energy (1), AND rival features do not improve learned residuals.
- Not worth adopting if the best frozen variant does not beat the energy filter
  online by >= 5 pp uMFE or >= 0.3 log10 P at matched wall time (all costs in).
Either outcome is recorded as negative; the next experiment then follows from
the diagnosed failure, not from an architecture sweep.

## Cost reporting
Data generation CPU time and oracle calls; training GPU time and peak memory;
inference cost per candidate; break-even number of design queries =
training cost / per-query time saved at equal quality.

## Amendment 1 (2026-09-27, before any collection or fitting): the rival-only term
Diagnostic finding: r = -Delta ln Z contains the target's own Boltzmann weight,
so r -> -a mechanically as P -> 1 (saturation), inflating the a-r
anti-correlation. Define Z_rest = Z - exp(-E_target/RT) and
c = -Delta ln Z_rest = Delta logit P - a (computed from stored ln P and E_target
only). Since logit P_child = logit P_parent + a + c and ln P is monotone in
logit P, ranking siblings by y equals ranking by a + c EXACTLY (checked: within
27,713 trajectory groups, Spearman(a + c, y) = 1.000). The learning target
becomes c; r is still recorded. Trajectory evidence that c is real competition,
not saturation: corr(a, c) = -0.549 overall, -0.415 for parents with P < 0.01,
median -0.638 within parents; slope of c on a -0.44 to -0.69 by P stratum.
The rival-bank physics control becomes c_bank = -(LSE_child - LSE_parent) over
compatible rivals only (target excluded); NaN if a child has no compatible rival.
