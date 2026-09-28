# Folding-guided RNA design repair with a target-conditioned diffusion denoiser: a completed benchmark with a null primary result

Technical project report, final version, 2026-09-29. RiboMamba repository (local; not published).
Status: COMPLETE as a technical project report. It is not a peer-reviewed paper; publication-specific
work that remains optional is listed in section 11. Reproduction: [REPRODUCE.md](REPRODUCE.md).

**One-paragraph summary.** We asked whether a small masked-diffusion model, adapted to condition on
a target RNA secondary structure and used to choose the letters of repair moves inside a strong
search method (SAMFEO), improves design success per unit of compute. In a prespecified, locally frozen final
benchmark (Eterna100 V2, 100 puzzles; 128 s of one-core method time per run; 3 seeds), no variant
developed here solved more puzzles than SAMFEO (71.0 of 100 puzzles, mean over seeds): SAMFEO plus a
target-energy pre-screen solved 70.7, the screen plus conditioned-model proposals 71.0, and RNAinverse
71.7. The conditioned-proposal variant reached the lowest mean best ensemble defect of the eight
methods (0.0400 versus 0.0459 for SAMFEO), a modest secondary ensemble-quality gain. On development
puzzles the conditioned model was a much better sampler than its unconditional base or targeted random
designs, but that advantage transferred only weakly to Eterna100. A later development study replaced
the model's forward pass, which carried a large fixed per-call cost, with CUDA-graph replay: proposal
overhead fell 2.5x and about twice as many candidates were evaluated within the time budget (4
concurrent runs on one laptop GPU), yet the conditioned variant still
solved fewer development puzzles than the energy screen. Reducing proposal overhead substantially did
not eliminate TCD's success-rate disadvantage against the non-neural energy screen within the tested
budgets. The research direction is closed.

## 1. Research question and claim boundaries
Question: can a small model that uses folding feedback make coordinated repairs that improve RNA
design quality per computational cost against strong existing methods?
Primary endpoint (final benchmark): Eterna100 V2 puzzles solved, where success means the target is
the unique minimum-free-energy (uMFE) structure of the design, within 128 s of method time.
Claims are limited to computational folding under one energy model (section 3.5) and to the budgets
and hardware described here. No state-of-the-art, novelty, generalisation, wet-lab or biological-
function claim is made. Numbers published by other groups use other budgets and hardware and are
quoted only as context (section 9), never mixed with ours. A null result on the primary endpoint is
not evidence of equivalence: no equivalence margin was specified.

## 2. Data
### 2.1 Pretraining data for the base model
Rfam 15.0 sequences (Hugging Face dataset multimolecule/rfam, revision 25e8aa8; Rfam 15.0 covariance
models Rfam.cm.gz, SHA-256 verified; provenance in docs/RESULTS.md), cleaned to A/C/G/U, one family per
sequence, at most 1,000 sequences per family, then
split by clan (or family when unclanned) into train / validation / test: 452,867 / 57,052 / 56,873
sequences (3,032 / 406 / 399 families; split seed 0). No clan, family or identical sequence occurs in
two splits (checked by assertion); letter-level near-twins of training sequences (MMseqs2 18.8cc5c)
and structural members of training families (Infernal 1.1.5) were removed from validation and test.
### 2.2 Design target sets
| set (manifest, content SHA-256 prefix) | puzzles | source | role |
|---|---|---|---|
| eternaweb_dev_v1 (19f16b01) | 32 development + 32 confirmation | Eterna web player puzzles released with Gautam et al. 2026 (github.com/KuNyaa/RNA-Design-LM, MIT) | development; confirmation (one look, consumed) |
| eternaweb_trainpool_v1 (a67a5c36) | 700 | same source | training side only |
| final_eterna100_v2 (33c65b95) | 100 (19-400 nt) | Eterna100 V2 (Anderson-Lee et al. 2016; V2: Koodli et al. 2021) | final, primary |
| final_eterna100_v1only (2ef59009) | 19 | Eterna100 V1 rows whose structure differs from V2 | final, secondary |
| final_rfam_taneda27 (a8016910) | 27 (54-382 nt) | Rfam-Taneda-27 (SAMFEO's pinned copy) | final, secondary |
Development and confirmation puzzles were chosen by a method-free hardness probe (no design method
was run to select them). Every development/confirmation puzzle lies more than 0.2 normalised edit
distance (dot-bracket strings) from every Eterna100 V1/V2, Rfam-Taneda-27/29 and RNAsolo-764
structure; building the training pool, the same audit rejected 95 puzzles near a test-side structure,
20 near a development/confirmation puzzle and 54 near-duplicates. Natural Rfam validation targets
(repair_pilot_val_v1) proved too easy (the starting design alone solved most) and were not used for
decisions. Manifests are versioned JSON files with content hashes; the runner refuses a manifest whose
content changed and refused final manifests until the protocol was frozen.
### 2.3 Training data for the conditioned model
Natural pairs: Rfam training sequences (<= 256 nt) with their ViennaRNA MFE structures (150,000
folded; 142,533 training and 2,632 validation pairs after removing 4,769 pairs whose structure lies
within normalised edit distance 0.2 of any development, confirmation or final structure). Design
pairs: distinct uMFE designs found by SAMFEO on the training pool, capped per puzzle: 14,567 training
pairs (272 puzzles) and 2,253 validation pairs (40 held-out puzzles). The edit-distance filter works at
the structure level; family-level overlap between Rfam training sequences and Rfam-Taneda-27 is
possible, and the design pairs share the Eterna web source of the development puzzles.

## 3. Methods
### 3.1 Base model
A masked (absorbing-state) diffusion Transformer trained with the MDLM negative ELBO (1/t weighting):
8 layers, width 384, 6 heads, 14.17 M parameters, one token per nucleotide with begin/end markers.
Trained 30,000 steps (1.41 GPU-hours, RTX 4060 Laptop); the EMA weights at step 10,000 were selected
on validation families (1.904 bits per nucleotide on unseen families; checkpoints/tf_M_do0/best.pt).
### 3.2 Target-conditioned denoiser (TCD)
The base model plus zero-initialised adapters, so that at initialisation the conditioned model equals
the base model exactly (tested): a target-bracket embedding ('.', '(', ')') added to the token
embedding, and, after every block, a pair message h_i += W_l LayerNorm(h_partner(i)) for positions
paired in the target. 15.36 M parameters (1.19 M adapter). Fine-tuned with the same objective,
conditioned on the structure, batches mixing natural and design pairs 50/50 (batch 64, learning rate
1e-4 for base weights and 1e-3 for adapters, seed 0), 8,000 steps in 1,351 GPU-seconds. Model
selection: the checkpoint with the lowest design-validation NELBO (step 1,000: 0.80 bits/nt versus
1.92 for the base model on the same data; design-validation loss rose afterwards, i.e. over-fitting
to the training puzzles' designs). Sampling reveals single positions and target pairs over 32
unmasking steps; a pair is drawn from the product of its two conditional marginals restricted to
canonical pairs (an approximation to the joint), so every design satisfies all target pairs.
### 3.3 Search integration and the energy screen
Host: SAMFEO (Zhou et al. 2023), pinned commit e78b4b5, unmodified source, run with its defaults
(probability-defect objective, frontier k = 10, T = 1, targeted G-C initialisation, structured
mutation, its stop rule P(target) > 0.99). Two plug-ins replace only its mutation step:
- Energy screen (non-neural): draw K = 8 of SAMFEO's own mutations, skip already-evaluated ones,
  keep the one with the lowest free energy of the target structure (one O(n) evaluation each).
  K was fixed before any data and not tuned. The idea is prior art (INFO-RNA orders moves by
  target-energy change).
- TCD proposals: SAMFEO chooses the sites (K = 8 drafts); the positions each draft changed become a
  mask; one batched TCD forward pass refills all 8 masks (pairs refilled as canonical units, all
  other positions clamped to the parent); duplicates and already-evaluated sequences are removed;
  the energy screen picks the child. SAMFEO asks again while a child is already in its history.
### 3.4 Baselines and controls (final benchmark)
| method | source / revision | settings |
|---|---|---|
| SAMFEO | github.com/shanry/SAMFEO e78b4b5 (no licence file: local use only) | defaults above; numpy seed 2020 + 2021 x seed |
| SAMFEO + energy screen | as above | K = 8 |
| SAMFEO + TCD proposals + screen | as above + checkpoints/tcd_v1/tcd.pt | K = 8 |
| TCD sampling | this work | 32 steps, 32 samples per batch, temperature 1 |
| targeted random | this work | target pairs G-C/C-G at random, unpaired positions A; no search |
| DesiRNA | github.com/fryzjergda/DesiRNA bdb4908 (Apache-2.0), own conda env | Turner 2004 parameters, 10 replicas pinned to one core, -t 128, stop-when-solved off, seed = seed + 1; per-round timestamps via a wrapper |
| RNAinverse | ViennaRNA 2.7.2 RNA.inverse_fold | restarts: shared start, then targeted random starts |
| SamplingDesign | github.com/weiyutang1010/SamplingDesign f0283c49 (Apache-2.0), built with the rmtools env | upstream defaults, 1 thread (its published runs use many cores: under-budgeted here) |
### 3.5 Folding oracle and success definitions
ViennaRNA 2.7.2, Turner 2004 parameters, 37 C, dangles 2, lonely pairs allowed, for every method.
uMFE (primary): the target is the unique optimal structure (zero-band suboptimal enumeration).
Also recorded, never merged: the backtracked MFE equals the target; the target is an optimal
structure (ties allowed). Ensemble defect (NED): the mean over positions of 1 minus the probability
that the position is in its target state. log P(target): the target's Boltzmann probability. A design
that cannot form a target pair is given P = 0 explicitly (ViennaRNA otherwise returns a non-zero
value). EternaFold 1.3.1 is used only as an independent check, never as an objective.
### 3.6 Timing, resources and missing designs
Method time: monotonic wall clock from the start of each run (unit), including imports and model
loading; the harness's own re-scoring of candidates is excluded for methods that score candidates
themselves (SAMFEO-hosted methods, RNAinverse). DesiRNA and SamplingDesign run as subprocesses whose
candidates carry their real arrival time; the process group is killed at the limit and only
candidates produced by then count. Budget per unit: 128 s of method time and at most 5,010 candidates.
Resources: one CPU core per unit (OMP_NUM_THREADS = 1; DesiRNA pinned with taskset), 8 concurrent units
on a 20-thread laptop CPU (WSL2, ~11 GB RAM allocation), one RTX 4060 Laptop GPU (8 GB) shared by the
TCD units. GPU-assisted and CPU-only methods are therefore not equal-compute despite equal time limits.
After amendment 1 every unit ran in a fresh process, so TCD units paid torch import, CUDA
initialisation and model loading inside their method time (their first model-generated candidate
came after ~3 s when run alone; median ~5 s for TCD sampling during the final benchmark).
Wall-clock-limited units that spanned a machine suspend were detected by a clock-gap check and rerun.
Missing designs: a unit with no candidate within 128 s (a legitimate time-limit outcome, e.g.
RNAinverse's first design on 358-400 nt puzzles took 132-676 s) counts as unsolved; quality means use
units with a design and report how many lack one; error units would count as unsolved with no design
(none remained).
### 3.7 Statistics
The statistical unit is the puzzle. Seeds are averaged within each puzzle; paired differences between
methods are averaged over puzzles with percentile bootstrap 95 % intervals (10,000 resamples, seed 0).
"Any seed" counts a puzzle as solved if at least one of three seeds solved it. 32 paired comparisons
(8 pairs x 2 checkpoints x 2 metrics) are reported without multiplicity correction. V1 results combine
V2 results on the 81 shared structures with the 19 V1-only puzzles.

## 4. Protocol status
Development used only the development puzzles; the confirmation half had one pre-declared look,
which confirmed the energy screen (below). Protocol v2 (docs/PROTOCOL_design_v2.md) was frozen on
2026-09-27 with the methods, budgets, seeds, endpoints and final manifests above, before any final
unit ran. Amendments were operational, measurement or report-side fixes; none changed a method,
budget or endpoint, and none was tuned on final outcomes: (1, 1b) worker memory: fresh process per
unit and lazy model imports, after the first 43 units had run in 10 persistent workers (kept);
(2) DesiRNA time-limit argument type; (3) replayed external candidates judged on their own time;
(4, 4b) real per-candidate timing and hard kills for DesiRNA and SamplingDesign, including DesiRNA's
initial population, with every unit that ran pre-fix code superseded (kept) and rerun (117 units);
(4c-4f) the report refuses incomplete coverage, error units and pre-fix units, handles missing designs
as above, and records provenance and every superseded report file. The FINAL report
(data/repair_pilot/final_v2_report.json) was generated from commit 842124b after the corrective pass,
with all 3,504 units valid (Eterna100 V2 2,400; V1-only 456; Rfam-Taneda-27 648), no error units and no
pre-fix units in place. The efficiency study of section 8 came later, used development puzzles only,
and is not part of the final evaluation.

## 5. Primary result: no success-rate improvement (final benchmark)
Eterna100 V2, puzzles solved by 128 s (any seed / mean over seeds, of 100) and seed-mean uMFE at 1 / 16 s:
| method | any seed | mean | 1 s | 16 s |
|---|---|---|---|---|
| RNAinverse | 75 | 71.7 | 59 % | 67 % |
| SAMFEO | 74 | 71.0 | 54 % | 66 % |
| SAMFEO + TCD proposals + screen | 73 | 71.0 | 1 % | 66 % |
| SAMFEO + energy screen | 73 | 70.7 | 58 % | 69 % |
| DesiRNA | 74 | 68.3 | 17 % | 52 % |
| TCD sampling (no search) | 62 | 61.3 | 0 % | 54 % |
| targeted random (no search) | 56 | 56.0 | 49 % | 55 % |
| SamplingDesign (1 thread) | 48 | 43.7 | 7 % | 21 % |
Paired at 128 s: screen - SAMFEO -0.3 percentage points [-3.3, +2.0] (5 puzzles better, 4 worse);
TCD proposals + screen - SAMFEO 0.0 [-3.7, +3.7] (5/5); versus the screen alone +0.3 [-3.0, +3.3];
RNAinverse - screen +1.0 [-4.0, +6.0]. In practical terms the four leading methods differ by at most
one puzzle in 100, and the intervals exclude gains larger than about 2-6 points; this is not a
demonstration of equivalence. The conditioned variant starts slowly (1 % at 1 s, 40 % at 4 s versus
58 % and 62 % for the screen) because its setup and forward passes are charged to its time.

![Eight small panels, one per method, of the share of Eterna100 V2 puzzles solved against method time from 1 to 128 s. RNAinverse, SAMFEO and SAMFEO + screen start near 55-59 % at 1 s and reach 71-72 %; SAMFEO + TCD + screen starts at 1 % and catches up to 71 % by 16-128 s; DesiRNA rises from 17 % to 68 %; TCD sampling from 0 % to 61 %; targeted random stays near 49-56 %; SamplingDesign rises from 7 % to 44 %.](figures/final_v2_umfe_time.png)
*Figure 1. Eterna100 V2 puzzles solved (uMFE, mean over 3 seeds) against method time; each panel
highlights one method with the other seven in gray. Drawn from the FINAL report by scripts/final_figures.py.*

Secondary sets. Rfam-Taneda-27 is near ceiling: RNAinverse, SAMFEO, both screened variants and DesiRNA
solve 24 of 27 puzzles (any seed). Eterna100 V1-only: 0 of 19 for every method, as in SAMFEO's own
published per-puzzle V1 results (external/SAMFEO/data/results/eterna_samfeo.csv: none solved by uMFE);
Koodli et al. (2021) report these 19 V1 puzzles as unsolvable in Vienna 2, which is why V2 redesigned
them. V1 combined (any seed, of 100): RNAinverse 72, SAMFEO 71, both screened variants 69, DesiRNA 68.

## 6. Secondary result: modest ensemble-quality gains
Best ensemble defect at 128 s on Eterna100 V2 (mean over units with a design; median in brackets):
TCD proposals + screen 0.0400 (0.0110); screen 0.0434 (0.0133); SAMFEO 0.0459 (0.0151); RNAinverse
0.0510 (0.0190; 21 of 300 units without a design). Paired: TCD + screen - SAMFEO -0.0059 [-0.0085,
-0.0035] (82 puzzles better, 14 worse); screen - SAMFEO -0.0026 [-0.0047, -0.0005] (72/25); TCD +
screen - screen -0.0033 [-0.0055, -0.0015] (61/33). Practical size: -0.0059 is a 13 % relative
reduction and, for a typical 160-nt puzzle, about one nucleotide fewer in its non-target state in
expectation. Median best log10 P(target): -0.16 (TCD + screen), -0.18 (screen), -0.21 (SAMFEO), i.e.
target probabilities of about 0.69, 0.66 and 0.61. These are pre-specified secondary endpoints,
reported without multiplicity correction; they concern the computational ensemble under one energy
model and say nothing about biological function. Under EternaFold, an independent model, only 25-39 %
of the best designs of any method fold to the target (TCD + screen 39 %, SAMFEO 38 %; descriptive).

![Forest plot of paired per-puzzle differences at 128 s with 95 % bootstrap intervals. Left, success: every interval for SAMFEO + screen, SAMFEO + TCD + screen and RNAinverse contains zero; TCD sampling minus targeted random is +5.3 points with an interval from -1.7 to +12.3. Right, best NED times 1000: SAMFEO + screen minus SAMFEO is -2.6, SAMFEO + TCD + screen minus SAMFEO is -5.9 and minus SAMFEO + screen is -3.3, all intervals below zero; RNAinverse is +17 (worse, n = 91); TCD sampling minus random is +1.6 with an interval containing zero.](figures/final_v2_paired_effects.png)
*Figure 2. Paired differences on Eterna100 V2 at 128 s (seeds averaged per puzzle; bootstrap 95 %
intervals over 100 puzzles; no multiplicity correction). All success intervals include zero; the NED
gains of the screen and of TCD proposals with the screen exclude it.*

## 7. Development results: model adaptation and negative results
All on the 32 development puzzles x 3 seeds unless stated; development evidence, not final claims.
- Energy screen: uMFE 48 % -> 58 % at 1,024 evaluations over SAMFEO, replicated three times, and
  +9.4 points [1.0, 19.8] on the 32 sealed confirmation puzzles (one pre-declared look). It did not
  transfer to Eterna100 at 128 s (section 5).
- Conditioning: TCD sampling solved 42.7 % of development puzzles within 1,024 samples, versus 15.6 %
  for targeted random designs (+27 points [12.5, 42.7]) and 3.1 % for the unconditional base with the
  same sampler (+40 points [24, 56]). On Eterna100 V2 the gain over targeted random designs was small:
  +5.3 points [-1.7, +12.3] by time, and in an exploratory matched-sample view -5.7 points at 16
  samples and +8.3 [0.0, +17.1] at 1,024 samples on the 72 puzzles with that many samples. Why it
  transferred weakly was not tested (strong targeted-random baselines on easy puzzles and a shift from
  the Eterna web training source are hypotheses).
- As SAMFEO's proposal model with identical mutation sites, the TCD improved ensemble quality per
  evaluation (NED -0.016 [-0.026, -0.008]; log10 P +0.34 [0.11, 0.60]) but not uMFE (0.0 [-10.4,
  +10.4]), at about 3x the wall time.
- Negative results: the unconditional model as a repair proposer added nothing and was 4-5x slower;
  learned critics that rank mutations cut offline best-of-8 regret by about 70 % yet did not beat the
  energy screen online (52-55 % versus 58 % at 1,024 evaluations); a physics-informed rival-structure
  ("competition") residual added nothing to a per-position critic.
- Development baselines (one core, 32 puzzles): SAMFEO + screen gave the best ensemble quality at
  every budget and RNAinverse the fastest first solutions. Development DesiRNA times were stamped by
  step fraction while DesiRNA overran its limit, so its development curve is optimistic; the final
  benchmark used real timing.

## 8. The efficiency intervention and why it did not justify continuation
A bounded study after the final benchmark (docs/experiments/2026-09-28-tcd-inference-efficiency.md;
decision D-030) asked whether cutting TCD proposal overhead would improve the conditioned variant's
quality/time trade-off. Its question, targets, timing definitions, criteria and stopping rule were
recorded before any profiling; the chosen optimisation and final thresholds were committed before any
optimised result existed. Development puzzles only; no new confirmatory claim.
Profile (6 development puzzles, 29-251 nt). Inside SAMFEO + TCD + screen, proposals took 32-62 s of
each 64 s run; the eager forward pass was 75-89 % of proposal time and took ~11-12 ms per call whether
the batch held 1, 8 or 32 rows (a fixed per-call cost, consistent with kernel-launch/dispatch overhead;
CUDA-graph replay cut the same forward to 1.8-6.8 ms). Every cold run also spent ~3.1-3.2 s on setup.
After the GPU sat idle for 100-300 ms between calls (as on long puzzles, where each candidate's folding
takes longer), both eager and graphed forwards slowed to 23-72 ms; this was observed, and attributing
it to GPU/driver power-state behaviour is an inference that was not tested further.
Intervention. The same forward replayed from a CUDA graph with static input buffers
(samfeo_tcdprop_efilter_graph). On the tested laptop/WSL2 configuration the logits were bitwise
identical to the eager forward, and at a fixed candidate budget the search evaluated exactly the same
candidates in the same order (unit tests, including a full SAMFEO run of 120 candidates; 50/50
identical proposal calls on 10 development puzzles). At a fixed TIME budget the graphed
variant evaluates more candidates, so its trajectories and outcomes differ from the eager variant's.
Declared comparison (32 development puzzles x 3 seeds, 64 s runs, fresh process per run with setup
charged, 4 concurrent runs, 384/384 units valid):
| | eager (reference) | CUDA graph |
|---|---|---|
| proposal time per evaluated candidate (median over runs) | 24.7 ms | 10.2 ms |
| candidates evaluated by 16 s / 64 s (median) | 504 / 1,920 | 1,096 / 3,661 |
| seed-mean uMFE at 16 s / 64 s | 46.9 % / 56.2 % | 50.0 % / 56.2 % |
| mean best NED at 16 s / 64 s | 0.0536 / 0.0476 | 0.0505 / 0.0457 |
SAMFEO + screen in the same batch: 56.2 % / 61.5 % uMFE and 0.0528 / 0.0490 NED at 16 / 64 s.
Speed-up scope. Per puzzle, proposal overhead fell by a median 2.48x (1.34-3.50; 1.74x above 130 nt)
and candidates evaluated rose 2.05x by 16 s and 1.90x by 64 s in this concurrent, cold setting. Run
one at a time the gains were smaller: overhead 1.51x cold and about 1.8x with the model kept resident
(warm); candidates by 16 s 1.9-2.1x; by 64 s 1.39x cold and 1.55x warm (6 puzzles, two of them long).
The graph does not shorten a run (budgets are fixed) or the ~3 s setup before the first candidate; it
raises throughput of candidates within a run.
Prespecified gates (committed before the run). Engineering, versus the eager implementation: proposal overhead >= 2x (met,
2.48x); candidates >= 1.5x by 64 s and >= 1.2x by 16 s (met); no unacceptable quality drop versus the
eager implementation (met: graph - eager uMFE +3.1 points [0.0, +6.3] at 16 s and 0.0 at 64 s; best
NED -0.0031 [-0.0051, -0.0015] at 16 s, better on 28 puzzles and worse on none). Scientific, versus
SAMFEO + screen: not met. The graphed variant was worse on uMFE by 6.3 points [-14.6, -1.0] at 16 s
and 5.2 points [-10.4, -1.0] at 64 s; its NED was lower at 64 s (-0.0033 [-0.0057, -0.0011]) but not
clearly at 16 s (-0.0024 [-0.0054, +0.0008]). The declared stopping rule was followed: no new
evaluation set or protocol was prepared. Proposal cost mattered (removing much of it improved the
conditioned variant against its own eager version), but reducing proposal overhead substantially did
not eliminate TCD's success-rate disadvantage against the non-neural energy screen within the tested
budgets.

## 9. Limitations
- Budget and hardware: 128 s on one core (final) and 16/64 s (efficiency study) favour fast restarts;
  longer budgets or more cores could order methods differently. One laptop (WSL2, RTX 4060 Laptop GPU);
  launch and idle-latency behaviour, and the bitwise identity of graph and eager logits, were verified
  only on this hardware/driver/PyTorch configuration.
- Statistics: 32 uncorrected comparisons in the final report; development results rest on 32 puzzles
  used throughout development. Bootstrap intervals are seeded, but per-puzzle rows were not sorted
  before resampling, so the intervals are not bit-reproducible. In one closeout regeneration from the
  saved traces every point estimate reproduced exactly, while interval bounds moved by up to 1.2 points
  for uMFE and 0.0008 for NED and no interval changed which side of zero it lies on. That is the
  variation observed in a single rerun, not an established bound; other reruns could differ more.
- Execution details: the first 43 final units (amendment 1) ran in 10 persistent workers; 7 of them were
  TCD units that ran with the model already loaded (Eterna100 V2 puzzles 22 and 53), so their ~3 s setup
  was not charged and they ran under the first launch's heavier 10-worker concurrency. Two are TCD-proposal
  units on puzzle 22 solved by SAMFEO's first candidate (0.14-0.16 s), which the setup would not have
  changed. For the other five, a cold start could have moved checkpoints: TCD sampling on puzzle 22 (seeds
  0-2) first solved at 2.5-3.1 s, so its 4 s points may be affected; TCD sampling on puzzle 53 (seed 0)
  first solved at 7.4 s; TCD proposals on puzzle 53 (seed 0) first solved at 15.9 s, so its 16 s point may
  be affected. All five were solved well before 128 s, so the 128 s counts are unlikely to change, but no
  unit was rerun and the size of the effect was not measured. SamplingDesign at one thread is under-budgeted; DesiRNA ran 10
  replicas on one core.
- Data: the TCD's design data share the Eterna web source of the development puzzles; family overlap
  between Rfam training sequences and Rfam-Taneda-27 is possible; Eterna100 is public and may overlap
  with data behind other published tools.
- Scope: computational folding under ViennaRNA's Turner 2004 model only; no biological function,
  expression or wet-lab behaviour is claimed.
- Literature: section 10 lists verified related work; it is not a systematic review.

## 10. Related work (verified sources; no novelty claim)
Energy-guided proposals: INFO-RNA (Busch and Backofen 2006). Rival structures and designability bounds:
LinearDecompose / probabilistic designability (Zhou, Mathews and Huang 2026). Search methods: SAMFEO
(Zhou et al. 2023), SamplingDesign (Tang et al. 2026), DesiRNA (Kozyra et al.), Montparnasse (Cazenave
2025/2026). Learned design: LEARNA; EternaBrain (Koodli et al. 2019); language models trained on
SAMFEO designs and conditioned on the dot-bracket target (Gautam et al. 2026); deep Q-learning
conditioned on secondary structure and SHAPE (Struct2SeQ, He and Sun 2026); latent diffusion with
reward optimisation of secondary-structure consistency and MFE (SOLD, Si et al. 2026); diffusion
conditioned on 3D backbones (RiboDiffusion, Huang et al. 2024); masked discrete diffusion for ncRNA
conditioned on RNA type, with inpainting (RNA-MDLM, Upadhyay et al. 2026; not target-structure
conditioned). Structure-conditioned neural design is established; adapting a pretrained unconditional
masked-diffusion model with zero-initialised structure adapters is one variant among these. Full
citations and what was accessed: docs/REFERENCES.md. Published results of other methods (e.g.
SamplingDesign 79 MFE / 78 uMFE on Eterna100 with Turner 2004; DesiRNA 97 of Eterna100 V2 within 24 h)
use other budgets and hardware and are not comparable with the numbers above.

## 11. Reproducibility, artifacts and publication status
Reproduction: [REPRODUCE.md](REPRODUCE.md) (environments, tests, regeneration of these tables and
figures from saved traces, and the expensive experiment commands). Records: docs/RESULTS.md,
docs/DECISIONS.md (D-017 to D-031), docs/PROTOCOL_design_v2.md, docs/experiments/, docs/logbook/,
[model card](MODEL_CARD_tcd_v1.md), [data card](DATA_CARD_design.md). A local preservation package
(closeout 2026-09-29) records the code commit, a Git bundle, copies of reports, manifests, results and
essential checkpoints, and checksums; its location and contents are listed in docs/HANDOFF.md.
This document is complete as a technical project report. Optional work that a particular venue might
require: a systematic literature review, a longer methods section with pseudocode, per-puzzle tables,
and permission from the SAMFEO authors before any code release (its repository has no licence).
