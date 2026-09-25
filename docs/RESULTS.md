# Results — RiboMamba

Two rules govern this file (CLAUDE.md §3.5):

1. **Thresholds are frozen before results are seen.** The "Frozen evaluation
   protocol" section below is filled in and dated *before* any test-set
   evaluation runs. After that date it is never edited, only appended to with
   a dated, explained amendment.
2. **Every number is reproducible.** Next to every number goes the exact
   command, commit hash and random seed that produced it.

---

## Frozen evaluation protocol

**Status: FROZEN on 2026-09-24**

Drafted in session 04 from validation-only measurements, reviewed by
Chirag, who approved all five open recommendations (five seeds, a
replication split, Eterna100 as a secondary set, T = 1.0, 256 steps). The
freeze commit is the one that adds this line together with
`environment.lock.yml` (hash in the logbook, 2026-09-24 session 04). Until
that commit the test split was locked in code (`ribomamba/eval/protocol.py`)
and was never read. From here on this section is only appended to, with
dated amendments (P1.4).

### P1. Principles

1. **Validation for every choice, test for the final answer.** Every
   setting (sampling steps, thresholds, target rules, hyperparameters) is
   chosen on validation. The test split is used only to evaluate final
   models, with this protocol, once per model.
2. **Frozen before the competitors exist.** This protocol is frozen before
   any Phase 4 model (BiMamba, autoregressive Mamba) has been trained, so
   none of its choices can have been fitted to them.
3. **Everything is reported.** Every primary and secondary endpoint is
   reported for every model, whichever way it comes out, negative results
   included (CLAUDE.md §3.5). Example sequences shown anywhere are drawn at
   random (seeded), never picked.
4. **Changes after the freeze** are appended as dated amendments with a
   reason, never edits, and only if they are mechanical, apply identically
   to every model, and are made before the results they affect exist (the
   D-011 conditions).

### P2. Instruments (the oracles)

- **Primary oracle:** ViennaRNA **2.7.2** (Turner 2004 parameters), 37 °C,
  dangles = 2, lonely pairs allowed, as fixed in
  `ribomamba/eval/folding.py::model_details`. Known quirk: its dangles-2
  partition function weights structures closing on the last nucleotide
  0.017 kcal/mol differently from RNAeval (≤ 0.06 % effect on probabilities
  in our tests; session 04 logbook, 12:50).
- **Second oracle (robustness):** EternaFold **1.3.1**, parameters
  `EternaFoldParams.v1`, most probable (Viterbi) structure and base-pair
  probabilities (cutoff 10⁻⁵), run under `mpirun` (D-013). Used only for
  structure-level metrics; never for steering or selection.
- **Environment:** `environment.yml` plus a full lock file
  `environment.lock.yml` (`conda env export`) committed at the freeze.
- **Code:** metric definitions are the code in `ribomamba/eval/` at the
  freeze commit, pinned by known-answer tests (`tests/test_folding.py`,
  `test_stats.py`, `test_distributions.py`, `test_eternafold.py`,
  `test_harness.py`).

### P3. What is evaluated on the test split

- **Likelihood:** all 56,873 test sequences (399 families).
- **Unconditional generation:** a reference of n = 1,000 test sequences
  (`reference_sample("test", 1000, seed 0)`) with its four companion sets
  (`real2`, `train`, `shuffled`, `random`; `ribomamba/eval/reference.py`).
  Every model generates 1,000 sequences with exactly these lengths, in
  this order.
- **Design (Phase 5):** target sets `rfam_test` and `bprna_test`, built by
  `scripts/build_targets.py --split test --seed 0` (rule in its docstring,
  committed before any target set existed) right after the freeze; their
  SHA-256 checksums are appended here when built. Primary set: `rfam_test`.
  Secondary sets: `bprna_test`, and `eterna100_test`: the 75 Eterna100-V2
  puzzles of ≤ 256 nt (pinned in `scripts/download_data.py`), an external,
  evaluation-only set that is never used for tuning. Its positive control is
  the benchmark's ViennaRNA-2 sample solution: all 75 fold into their target
  under ViennaRNA 2.7.2 (checked 2026-09-24).

### P4. Models and fairness (Phase 4)

Three models: Transformer diffusion (Phase 2 baseline architecture),
BiMamba diffusion, autoregressive Mamba. Identical data, split, tokeniser,
`<bos>`/`<eos>` framing, batch size (16,384 tokens) and training length;
parameter counts within ±2 % of 14,174,976; each tuned by the same
protocol (D-011 learning-rate sweep with the boundary rule, then the D-012
dropout sweep over 30,000 steps, best-during-run EMA validation checkpoint).
**Five training seeds per model** for the final configuration (the sweep
run that won is seed 0). Reason for five: with three seeds per model the
smallest possible p-value of the seed-level test (P8) is 0.10, so no claim
could ever pass; with five it is 0.008.

**Replication split:** the whole pipeline is repeated once on a second
clan/family split (split seed 1: the hash prefix in `prepare_data.py`
changes from "0:" to "1:"; steps 10–11 rerun), with one training run per
model using the hyperparameters chosen on split 0, evaluated with this
protocol on split 1's own test set. Reported descriptively (does the
direction of each primary endpoint repeat?), with no significance test.

### P5. Sampling

- Diffusion models: temperature **T = 1.0** (the distribution the model
  learned, the one its likelihood measures; no per-model tuning).
  **Steps: N = 256 for every model.** The rule written before the
  ablation (logbook 13:39: the smallest grid value whose `beats_shuffles`
  and `ned_mfe` at T = 1.0 lie inside the 95 % intervals of the 512-step
  setting) returned N = 16 for the Transformer baseline. It was not used,
  for a stated reason: a step count that is cost-optimal for one backbone
  (whose samples don't benefit from more steps) could handicap a backbone
  that captures pairing and does benefit; 256 = the maximum length, about
  one letter revealed per step. The choice is result-neutral for the
  baseline (0.565 at 16 vs 0.570 at 256, inside each other's intervals)
  and costs ~100 s per 1,000 samples.
- Autoregressive model: T = 1.0, **length-constrained** (`<eos>` forbidden
  before the target length and forced at it), so it receives the same
  lengths as the diffusion models.
- Bf16 network, float64 letter sampling (as in Phase 2); sampling seed 0.
- Secondary: the temperature curve T ∈ {0.5, 0.6, …, 1.2} at N steps, for
  every model.

### P6. Metrics (definitions in code; the essential ones restated)

- `beats_shuffles`: probability that a sequence's MFE is lower than that of
  a random dinucleotide shuffle of itself (50 shuffles; ties count ½);
  0.5 = no structure beyond chance.
- `ned_mfe`: normalised ensemble defect of the sequence against its own MFE
  structure (0 = holds it perfectly).
- `ef_ned_vienna`: EternaFold's ensemble defect for ViennaRNA's MFE
  structure (the cross-oracle check of `ned_mfe`).
- `ned_target`, `p_target`, `mfe_match`, `energy_gap` (design, against a
  given target); `mean_pairwise_hamming` among designs.
- Test likelihood in **bits per nucleotide**: diffusion models, the
  1/t-weighted NELBO averaged over 4 fixed noise draws per sequence (seeds
  1234–1237, identical for every model); autoregressive model, the exact
  negative log-likelihood of the framed sequence.

### P7. Endpoints

**Phase 4 primary endpoints** (5 tests, Holm-corrected together):

| # | endpoint | direction | comparisons |
|---|---|---|---|
| E1 | test bits/nt | lower | BiMamba vs Transformer (both bounds; like for like) |
| E2 | mean `beats_shuffles` of 1,000 samples | higher | BiMamba vs Transformer; BiMamba vs AR Mamba |
| E3 | mean `ned_mfe` of 1,000 samples | lower | BiMamba vs Transformer; BiMamba vs AR Mamba |

**Robustness condition:** a primary-endpoint win on E3 counts as
oracle-robust only if `ef_ned_vienna` moves in the same direction;
otherwise it is reported as ViennaRNA-dependent.

**Guardrails** (checked for every model; a model failing one has its E2/E3
reported but flagged as not interpretable): ≤ 5 % of samples with a
≥ 80 %-identity training relative (copying); ≥ 95 % distinct samples
(collapse); mean GC within ±0.05 of the real reference (composition).

**Phase 5 primary endpoints** (targets `rfam_test`; K = 16 designs per
target per method; Holm-corrected together; the list of methods compared
is fixed by a dated amendment before their first test run):

| # | endpoint | direction |
|---|---|---|
| D1 | mean over targets of the best (lowest) `ned_target` among the K designs | lower |
| D2 | share of targets with ≥ 1 design whose MFE structure equals the target | higher |

Secondary (reported, not tested for claims): everything else the harness
computes, including AR vs diffusion likelihood (not like for like: an exact
likelihood against an upper bound), EternaFold versions of every endpoint,
`p_target`, energy gaps, diversity among successful designs, Wasserstein
and k-mer distances to real RNA, `bprna_test` and `eterna100_test`
results, the temperature curves, the replication split.

### P8. Statistics and decision rules

- **Architecture claims (Phase 4):** each trained model (seed) gives one
  score per endpoint; models are compared with the exact seed-level
  permutation test (`seed_permutation_test`, 5 vs 5, two-sided).
  The p-values of the 5 primary tests are Holm-adjusted; "X beats Y on E"
  requires an adjusted p ≤ 0.05. Otherwise the wording is "no detectable
  difference with 5 seeds", never "equal".
- **Effect sizes:** every difference is reported with a 95 % bootstrap
  interval (10,000 resamples): over families (cluster bootstrap) for
  anything computed on real test sequences, over samples for generated
  sets, over targets (paired) for design endpoints.
- **Design (Phase 5):** per-target paired comparisons (`paired_test`,
  sign-flip); seed handling as above if the compared methods are trained
  models.
- **Uncertainty of a single model's number:** bootstrap interval as above;
  proportions from ≥ 1,000 items; zero counts reported with the rule of
  three.

### P9. Order of operations after the freeze

1. Commit `environment.lock.yml`; add "FROZEN on <date>" here (this
   unlocks the test split in code).
2. Build `rfam_test` / `bprna_test`; append their checksums here.
3. Run the EternaFold training-data overlap check on test (as done for
   validation; session 04, 13:31); append.
4. Phase 4 trains and selects every model on validation; each final model
   is evaluated on test exactly once with this protocol.

### Post-freeze records (P9 steps 1–3; records, not amendments)

**Step 1 — 2026-09-24 19:24.** Freeze commit `67687ed` (this section's
status line + `environment.lock.yml`); `pytest` 79 passed at the frozen code.

**Step 2 — test target sets, 2026-09-24 19:24–19:25.** `python
scripts/build_targets.py --split test` at `67687ed` (clean tree), seed 0.

| set | targets | median length | native = target under ViennaRNA | native NED (median) | SHA-256 of `data/targets/<set>.parquet` |
|---|---|---|---|---|---|
| `rfam_test` (primary) | **397** (399 families; 2 with < 4 pairs dropped) | 87 | 100 % (by construction) | 0.113 | `2051aa7ca93e4e23f4ca95ccc73787dd2cef1df0f5bc775206831102e4a62051` |
| `bprna_test` | **141** | 98 | 4.3 % | 0.254 | `5509062b7a058b2c6774613ede77b3167fc545bc9b1c2f5dfb3b86c211d59068` |
| `eterna100_test` | **75** (of 100; ≤ 256 nt) | 97 | 100 % (sample solutions) | 0.104 | `65eb1b18a8a113a1dc70d074daccc5e919c4be068e2f66a7db2ac77eda973257` |

bpRNA funnel to `bprna_test`: 7,336 candidates → member of a test family
727 → no ≥ 80 % training hit 724 → one per family **141**.

**Step 3 — EternaFold training data vs test, 2026-09-24 19:25.** `python
scripts/check_oracle_overlap.py --split test` at `67687ed`: exact matches
0 (all four training files); MMseqs2 (≥ 80 % coverage) ≥ 50 % identity
**0 of 56,873** (validation: 0.30 %, all tRNA; tRNA sits in validation, not
test). The second oracle has seen nothing related to the test set.

### Amendment A1 — 2026-09-25: a diverged tuning run ranks last

**Why.** The tuning rules P4 refers to (D-011: lowest final validation
bits/nt; D-012: lowest best-during-run value) assume every candidate
finishes its schedule. A candidate learning rate can instead make training
diverge (the training loss becomes inf or nan). The code then stopped with
an error, which would halt an unattended Phase 4 queue, and the rules did
not say how such a candidate ranks.

**Amendment.** A run whose training loss becomes non-finite is recorded as
diverged (a `DIVERGED` file in its checkpoint folder, with the step) and
stops. In a sweep it ranks last (value +∞), whatever it reached before
diverging, because it did not complete its schedule; the sweep continues.
If every candidate of a sweep diverges, the sweep stops with an error.

**Conditions (P1.4).** Mechanical; identical for every model; made before
any Phase 4 (Mamba) training run exists; it changes no existing result,
since none of the Transformer's 13 training runs diverged. Code:
`ribomamba/sweeps.py` (`diverged`, `pick_lowest`, `run_to_completion`),
`scripts/train.py`; tests in `tests/test_sweeps.py`; checked end to end by a
deliberately diverging debug run (logbook 2026-09-25).

### Amendment A2 — 2026-09-26: the boundary rule may not stop at the end of a finite list

**Why.** Rule 2b (D-011, and the docstring of `scripts/lr_sweep.py`) says:
while the winner is the smallest or largest value tried, add the next value
on the half-decade grid in that direction and re-apply the rule, "repeat
until the winner is interior". The code held the grid as a finite list that
ended at 10⁻² (and the dropout grid at 0.4), and when a winner reached the
end of the list it stopped quietly. BiMamba's sweep hit exactly that:
3×10⁻⁴ 1.9265, 10⁻³ 1.9184, 3×10⁻³ 1.9124, then 10⁻² 1.9086, still the
largest value tried, and the code declared 10⁻² the winner and started the
dropout sweep. That contradicts the written rule, which requires 3×10⁻².

**Amendment.** The learning-rate grid now runs from 10⁻⁶ to 1 and the dropout
grid to 0.7, and reaching either end **raises an error** instead of stopping
(`ribomamba/sweeps.py`, `next_candidate`). The BiMamba sweep resumes with
3×10⁻² as the written rule requires. The dropout run that had started at
10⁻² (step 2,400, no checkpoint, no validation result) was stopped and set
aside (`checkpoints/bimamba_M_do0_aborted_lrcap`).

**Conditions (P1.4).** Mechanical (it restores the written rule; no
judgement); identical for every backbone; it changes no existing result:
replaying the Transformer's sweep through the new code gives the same
choice (tested), because its winner was at the lower edge far from the list's
end. Made after 10⁻² was seen to win, but the rule it enforces was written
on 2026-09-24, before any Mamba run, and it affects only results that did
not exist yet (the 3×10⁻² candidate and the dropout sweep). Tests:
`tests/test_sweeps.py` (4 new).

### Clarification C1 — 2026-09-25: which trained model gives each temperature curve

P5's secondary temperature curve is computed "for every model". In this
protocol "model" means architecture ("Three models: …", P4), so the curve is
computed once per architecture, from its **seed-0 model** (the dropout-sweep
winner), as the Phase 3 ablation did for the Transformer: T ∈ {0.5, 0.6, 0.7,
0.8, 0.9, 1.1, 1.2} at 256 steps (the AR model left to right,
length-constrained), plus the primary T = 1.0 already computed for all five
seeds. A reading, not a change: written before any Mamba model had finished
training, it selects nothing by results, and it is identical for the three
architectures. Implemented in `scripts/phase4_evaluate.py`.

---

## Train/test overlap audit

Recorded 2026-09-23, session 03 (final version after step 11, 22:08). Code
at commit `a58ab08` (cleaning, split, steps 10–11, both audits) and
`629c93e` (downloads). Data: `multimolecule/rfam` at `25e8aa8…`,
`multimolecule/bprna` at `423465b…`, Rfam 15.0 `Rfam.cm.gz` (SHA-256
verified, D-005, D-009). Tools: MMseqs2 18.8cc5c, Infernal 1.1.5. All seeds
= 0. Deterministic: rerunning `prepare_data.py` gives byte-identical files.

**Reproduce** (inside `conda activate ribomamba`, from the repo root):

```
python scripts/download_data.py      # pinned files, checksums verified
python scripts/explore_data.py       # raw-data numbers that set the thresholds
python scripts/prepare_data.py       # clean + split -> data/processed/, splits/rfam_split.tsv
                                     #   (first run ~2 h: step 11 scans 113,937 sequences; cached after)
python scripts/audit_leakage.py      # letter-based checks 1-4  -> data/processed/audit.json
python scripts/audit_structural.py   # structure-based checks A-D -> data/processed/audit_structural.json (~20 min)
```

Output checksums (SHA-256, `sha256sum data/processed/*.parquet splits/rfam_split.tsv`):

```
05d8a552b73cc559fb7e955ca14627cdae41112d1a060bbb53e385e4433439f3  data/processed/test.parquet
012c03a8a1b782daf5e0a64403bf3d8ac1b6ae8f2b7e50194acf6ad618eecd5d  data/processed/train.parquet
5bb7499bfa36e69ff3383af8413a4f766f340dc1ac258bc248b1be52044a7625  data/processed/val.parquet
1913c634f6f131a3cea18e8377ae5016bdea9649d027deeb05b9291cc3170b48  splits/rfam_split.tsv
```

### The data after cleaning (D-007) and splitting (D-008, D-009)

| | sequences | share | families | split units (clan or family) | median length |
|---|---|---|---|---|---|
| train | 452,867 | 79.9 % | 3,032 | 2,830 | 93 |
| val | 57,052 | 10.1 % | 406 | 371 | 92 |
| test | 56,873 | 10.0 % | 399 | 371 | 96 |

Cleaning funnel: 20,051,822 raw rows → 10,025,911 after removing the
duplicated `"No such family"` copy → 9,981,218 ACGU-only → 9,590,462 after
dropping 185 families with median length > 256 → 9,547,361 ≤ 256 nt →
9,534,330 after the fragment filter → 5,730,590 after exact-duplicate removal
→ 5,730,554 single-family → **567,579** after the 1,000-per-family cap →
566,804 after step 10 (letter-level near-twins of train: −200 val, −575
test) → **566,792** after step 11 (structural members of a train family:
−2 val, −10 test: snoR16→SNORD36 8, SNORD2→SNORD36 2, ceN109→SNORD36 1,
SNORA36→SNORA51 1).

### Letter-based leakage checks (`audit_leakage.py`)

**Checks 1–2 — shared labels or identical sequences between any two splits:
0 clans, 0 families, 0 sequences** (train–val, train–test, val–test). Also
enforced by an assertion in `prepare_data.py`.

**Check 3 — nearest training relative of held-out sequences.** 2,000
held-out sequences sampled per row (seed 0); each searched against **all**
training sequences with MMseqs2 (nucleotide, forward strand, E ≤ 10⁻³). A
hit counts toward an identity level only if it covers ≥ 80 % of the query.
± = 95 % confidence half-width (normal approximation).

| split scheme / held-out set | any detectable relative | median best identity | ≥ 50 % | ≥ 80 % | ≥ 90 % | ≥ 95 % | 100 % |
|---|---|---|---|---|---|---|---|
| **ours** / val | 1.40 % | 0 | 0.00 % | 0 * | 0 * | 0 * | 0 * |
| **ours** / test | 1.05 % | 0 | 0.40 % ± 0.28 | 0 * | 0 * | 0 * | 0 * |
| **random split (control)** / test | **96.5 %** | **0.960** | 93.3 % ± 1.1 | **90.3 % ± 1.3** | 76.2 % ± 1.9 | 56.0 % ± 2.2 | 5.9 % ± 1.0 † |

\* Zero **by construction**: step 10 removed every held-out sequence with a
≥ 80 %-identity, ≥ 80 %-coverage training hit, using the same search. Before
step 10 the family/clan split alone gave 1.2 % ± 0.5 of test at ≥ 80 % (775
of 114,712 held-out sequences, 17 families; D-008). The ≥ 50 % and "any
relative" columns are the informative ones for our split.
† Not exact duplicates (the pool has none): 100 % identity over ≥ 80 % of
the query, e.g. one sequence is the other plus a few letters at an end.
An earlier run on the pre-step-11 split (a different 2,000-sequence draw)
gave random-control ≥ 80 % = 89.6 % ± 1.3 and ours/test ≥ 50 % = 0.15 % ±
0.17: consistent within sampling error.

**Check 4 — bpRNA-1m sequences that occur letter for letter in our splits**
(of 70,035 distinct bpRNA sequences): train **17,086**, val 1,860, test
2,036. So any bpRNA structure used as a design target in Phase 3 must be
screened against our train split first.

### Structure-based leakage checks (`audit_structural.py`, D-009)

Every held-out sequence (**113,925**) scanned with Infernal `cmscan
--nohmmonly --toponly --rfam -E 0.01` against all **4,178 Rfam 15.0
covariance models**. "Member" = bit score ≥ that model's GA threshold (the
rule Rfam uses to define family membership). "Weak hit" = E ≤ 10⁻³ but not
necessarily ≥ GA. Controls on a 2,000-sequence sample (seed 0). ± = 95 %
half-width.

| check | result |
|---|---|
| **A. positive control:** own family found at GA (all 113,925) | **99.55 % ± 0.04** |
| **B. leakage:** member of a *train* family (all) | **0** (by construction: step 11 removed these, same scan) |
| **C. weak hit to a train family** (all) | 4.59 % ± 0.12 |
| C. — same, on the 2,000 sample | 4.55 % ± 0.91 |
| C. **negative control:** same 2,000, dinucleotide-shuffled — weak hit to a train family | **0.10 % ± 0.14** |
| C. negative control — member of *any* family | 0 |
| **D. filter sensitivity** (2,000 sample): member of a train family, Rfam's fast filters / Infernal's default filters | **0 / 0** (95 % upper bound ≈ 0.15 % by the rule of three) |
| D. own family found at GA, fast / default filters | 99.6 % / 99.7 % |
| D. weak hit to a train family, fast / default filters | 4.55 % / 9.1 % ‡ |

‡ The slower default filters find about twice as many *weak* hits (they're
more sensitive), but **no additional membership-level hits**, which is the
leakage criterion. The negative control was run with the fast filters, so
compare 4.55 % against 0.10 %.

**Interpretation.**
- The detector can see: it recovers held-out sequences' own family 99.55 %
  of the time (A).
- No held-out sequence is a member of a training family by Rfam's own rule
  (B), and slower, more sensitive filtering finds none either (D).
- About 4.6 % of held-out sequences weakly resemble some training family:
  ~45× the shuffled noise floor (C), so the resemblance is real. It's
  class-level ("also a hairpin-shaped microRNA"), below membership
  thresholds. That's knowledge a model *should* transfer to new families,
  and no split could remove it. It's reported, not filtered (D-009).

**What the `--nohmmonly` fix changed** (same 106,191 held-out sequences,
first scan without the flag vs final scan with it): own family found at GA
for zero-base-pair families (7,617 seqs) 87.93 % → **99.99 %**; families
with pairs (98,574 seqs) 99.54 % → 99.54 %; overall 98.70 % → 99.57 %.
Logbook 2026-09-23 session 03, 19:37 and 21:48.

**Known limits of these audits.** The test set is one draw (seed 0). Rfam
family labels and GA thresholds are curator- and model-assigned; the
structural check is as strict as Rfam's thresholds are. Weak class-level
resemblance remains by design.

---

## Phase 2 — reference points for bits per nucleotide

### Markov (counting) baselines

Recorded 2026-09-24, session 03. `python scripts/baselines_markov.py`
(deterministic; random-split control uses seed 0). A k-th order Markov
model predicts each nucleotide from the previous k, from training-split
counts with add-0.5 smoothing (fixed in advance). Exact likelihoods, bits per
nucleotide. "Ours" = the clan/family split (validation = unseen families);
"random" = the same sequences shuffled 80/10/10 ignoring families.

| order k | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 |
|---|---|---|---|---|---|---|---|---|---|
| ours: train | 1.9966 | 1.9805 | 1.9751 | 1.9708 | 1.9656 | 1.9571 | 1.9375 | 1.8899 | 1.7897 |
| **ours: validation** | 1.9962 | 1.9801 | 1.9737 | 1.9693 | **1.9663** | 1.9684 | 1.9803 | 2.0164 | 2.0790 |
| random: validation | 1.9964 | 1.9801 | 1.9748 | 1.9707 | 1.9657 | 1.9583 | 1.9422 | 1.9025 | **1.8170** |

**Reading it.**
- RNA letters are close to random locally: letter frequencies alone give
  1.996 bits, and the best counting model on unseen families reaches only
  **1.966 (k = 4)**.
- On our split, contexts longer than 4 **overfit**: training improves,
  validation worsens. Memorised training k-mers don't transfer to new
  families.
- On a random split the same memorisation is **rewarded**: k = 8 reaches
  1.817 bits, which would appear better than our Transformer's 1.914 after
  8,000 steps (sweep below). A random split would make a counting
  memoriser look like it beats the neural network. That's the leakage of
  Phase 1, measured on a model metric.

### Transformer learning-rate sweep (D-011)

`python scripts/lr_sweep.py --prefix tf_M --then-full` at commit
`6917362` (sweep) / `8b1c932` (extension); seed 0; size M (14,174,976
params); 8,000 steps × 16,384-token batches, warmup 1,000, cosine to 10 %.
Validation = full val split, fixed noise (seed 1234), EMA weights.

| peak LR | val bits/nt @2k | @4k | @6k | **@8k (rule)** |
|---|---|---|---|---|
| 3×10⁻⁴ | 1.9339 | 1.9165 | 1.9125 | **1.9138** |
| 10⁻³ | 1.9499 | 1.9393 | 1.9303 | 1.9252 |
| 3×10⁻³ | 1.9576 | 1.9587 | 1.9481 | 1.9441 |
| 10⁻⁴ (boundary extension) | 1.9389 | 1.9216 | 1.9163 | 1.9166 |

**Chosen: 3×10⁻⁴** (lowest at 8k, and now interior to the grid, so rule 2b is
satisfied). 10⁻⁴ and 3×10⁻⁴ differ by only 0.003 bits (one seed, fixed
validation noise), so the result is insensitive to the learning rate in that
range; 10⁻³ and above are clearly worse.

### The planned 200,000-step run overfit (stopped at step 46,100)

`tf_M_full`: lr 3×10⁻⁴, warmup 2,000, cosine planned over 200,000 steps,
commit `8b1c932`, seed 0. Stopped 2026-09-24 04:16 at step 46,100 (epoch 15);
`best.pt` = step 10,000, `last.pt` = step 45,000 (resumable).

| step | 5k | **10k** | 15k | 20k | 25k | 30k | 35k | 40k | 45k |
|---|---|---|---|---|---|---|---|---|---|
| val bits/nt (EMA) | 1.9141 | **1.9020** | 1.9044 | 1.9133 | 1.9214 | 1.9278 | 1.9303 | 1.9330 | 1.9348 |
| val bits/nt (live) | 1.9188 | 1.9177 | 1.9178 | 1.9373 | 1.9397 | 1.9384 | 1.9286 | 1.9330 | 1.9398 |

Training bits/nt (batch estimates) fell from ≈1.96 to **1.41** by step 46,000.
Validation on unseen families was best at step 10,000 (≈3.3 epochs) and
worsened steadily afterwards: **overfitting** to the training families.
Best so far: **1.9020 bits/nt**, 0.064 below the best counting model
(1.9663). The remaining ~150k steps were not run (they could only memorise
more). Response: D-012 (dropout sweep with full schedules over 30,000 steps).

### Dropout sweep (D-012) → the Phase 2 baseline

`python scripts/dropout_sweep.py --prefix tf_M` (lr 3×10⁻⁴ from the LR sweep;
30,000 steps, warmup 1,000, cosine to 10 %; eval every 2,500; seed 0; code
identical across runs: `d0fff97` for dropout 0, `094639b` (docs-only
difference) for 0.1 and 0.2). Finished 2026-09-24 08:49. Validation bits/nt,
EMA weights:

| dropout | 2.5k | 5k | 7.5k | 10k | 12.5k | 15k | 20k | 25k | 30k | **best** | train at 30k |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **0** | 1.9278 | 1.9126 | 1.9048 | **1.9040** | 1.9063 | 1.9099 | 1.9205 | 1.9294 | 1.9343 | **1.9040** | 1.615 |
| 0.1 | 1.9351 | 1.9199 | 1.9127 | 1.9091 | **1.9081** | 1.9096 | 1.9205 | 1.9343 | 1.9447 | 1.9081 | 1.719 |
| 0.2 | 1.9535 | 1.9326 | 1.9210 | 1.9179 | **1.9178** | 1.9197 | 1.9268 | 1.9344 | 1.9418 | 1.9178 | 1.800 |

**Rule result: dropout 0** (interior of the grid's lower end; 0 has no lower
neighbour). **Phase 2 baseline = `tf_M_do0/best.pt`, step 10,000, 1.9040
bits/nt** on unseen families: 0.062 bits below the best counting model
(1.9663). Dropout slowed learning but did not prevent overfitting; every run
peaks at 10–12.5k steps (≈ 3–4 epochs). With the long run's 1.9020 (a
different protocol, not used), the best reachable level for this model and
data sits at ≈ 1.90 bits/nt.

### Sanity preview of generated sequences (not the Phase 3 protocol)

`python scripts/sample.py --checkpoint checkpoints/tf_M_do0/best.pt --n 1000
--steps 256 --out samples/tf_M_do0.fasta` (seed 0; bf16 forward, float64
letter sampling; commit `bd3c940`), then `python scripts/sanity_samples.py
--samples samples/tf_M_do0.fasta` (seed 0; commit `f13d60d`). Real = 1,000
random validation sequences (seed 0). MFE: ViennaRNA 2.7.2, 37 °C.

| | generated | real (validation) |
|---|---|---|
| distinct / total | 1000 / 1000 | 1000 / 1000 |
| median length | 93 | 90 |
| nearest training relative ≥ 50 % identity (≥ 80 % coverage) | **0 %** | 0 % |
| GC content | 0.463 | 0.479 |
| MFE per nucleotide (kcal/mol) | −0.238 | −0.311 |
| paired fraction of positions | 0.566 | 0.600 |
| MFE − MFE of own dinucleotide shuffle (mean, kcal/mol) | **−0.56** | **−6.97** |
| share more stable than own shuffle | **54.6 %** | **79.4 %** |

**Reading it.** Generated sequences are novel (no copying) and
composition-matched, but they are barely more structured than chance
(54.6 % vs 50 % for chance; real RNA 79.4 %). The baseline has mostly
learned local sequence statistics, not the pairing that makes RNA fold,
which is consistent with its modest gain over counting models. Sampling
temperature and step count were not varied here (1.0, 256 steps); that
ablation belongs to Phase 3.

---

## Phase 3 — the evaluation harness on validation

Everything in this section uses **validation data only** (unseen families);
the test split was locked in code throughout. Oracles: ViennaRNA 2.7.2
(37 °C, dangles 2), EternaFold 1.3.1 (D-013).

### The reference scale

`python scripts/evaluate_samples.py` (commit `24b99aa`; val, n = 1000,
seed 0; 5 min 44 s on 20 threads; output
`data/eval/reference_val_n1000_s0.{json,parquet}`). Five sets, all with the
lengths of `real`, in its order (`ribomamba/eval/reference.py`). Means with
95 % bootstrap intervals (10,000 resamples, seed 0).

| metric | real | real2 (noise floor) | train (length-matched) | shuffled real | random letters |
|---|---|---|---|---|---|
| beats_shuffles (0.5 = chance) | **0.792** [0.775, 0.810] | 0.800 [0.783, 0.816] | 0.828 [0.813, 0.844] | 0.496 [0.478, 0.514] | 0.503 [0.485, 0.521] |
| MFE z-score vs 50 shuffles | **−2.15** [−2.32, −1.99] | −2.20 [−2.37, −2.03] | −2.90 [−3.11, −2.69] | −0.01 [−0.07, 0.05] | −0.02 [−0.09, 0.04] |
| NED of own MFE structure | **0.175** [0.168, 0.182] | 0.168 [0.161, 0.175] | 0.163 [0.156, 0.171] | 0.248 [0.240, 0.256] | 0.242 [0.235, 0.250] |
| P(own MFE structure) | 0.110 [0.101, 0.119] | 0.115 | 0.118 | 0.079 | 0.078 |
| MFE per nt (kcal/mol) | −0.311 | −0.316 | −0.329 | −0.241 | −0.225 |
| paired fraction | 0.600 | 0.606 | 0.620 | 0.555 | 0.533 |
| EternaFold NED of ViennaRNA's MFE structure | 0.335 [0.325, 0.344] | 0.339 | 0.319 | 0.461 | 0.450 |
| the two oracles predict the identical structure | 0.134 [0.113, 0.155] | 0.123 | 0.141 | 0.059 | 0.049 |
| GC content | 0.479 | 0.481 | 0.469 | 0.479 | 0.499 |
| has a ≥ 80 %-identity sibling in the same set | 0.572 [0.541, 0.602] | 0.563 | 0.208 | 0 | 0 |
| has a ≥ 50 %-identity training relative | 0 | 0 | 1.000 † | 0 | 0 |

† The training set's own members: the novelty detector's positive control.

**Reading it.** Shuffled and random sequences sit at 0.5 and z ≈ 0, as
theory predicts (a letter order without structure is exchangeable with its
shuffles). The two independent real samples agree within their intervals:
that is the noise floor for any comparison at n = 1000. Training families
are somewhat more structured than validation families (the family shift).
EternaFold ranks real above shuffled/random on its own terms. Real RNA has
many near-twins within a sample (families of relatives), so diversity is
read against this reference, not maximised.

### Likelihood estimator for endpoint E1 (Phase 2 baseline)

`python scripts/eval_likelihood.py --checkpoint checkpoints/tf_M_do0/best.pt
--split val --draws 4` (code at commit `38f7c48`; the run recorded
`38f7c48-dirty` because of an uncommitted logbook edit, docs only; noise
seeds 1234–1237; 2026-09-24 14:40, 90 s on the GPU).

| | bits/nt |
|---|---|
| value recorded in the checkpoint during training (`best_val`) | 1.90399 |
| draw 0 (seed 1234, identical batches and noise to training's evaluation) | **1.9040** (reproduced exactly) |
| draws 1, 2, 3 | 1.9071, 1.9058, 1.9076 |
| **mean of 4 draws** | **1.9061**, family-cluster 95 % CI [1.8910, 1.9213] (406 families) |
| spread between draws (sd) | 0.0016 |

**Reading it.** The estimator reproduces training's number exactly (the
known-answer check). Averaging draws matters little: the draw-to-draw noise
(0.0016) is about ten times smaller than the uncertainty from *which
families* are held out (± 0.015), so 4 draws suffice. Draw 0 is 0.002 lower
than the average: selecting the best checkpoint on a single fixed draw
carries a small optimistic bias ("winner's curse"), which is why the
protocol averages 4 draws for the final number.

### Sampling temperature × steps ablation (Phase 2 baseline)

Grid and rule written before any result (logbook 13:39). `python
scripts/sampling_ablation.py --checkpoint checkpoints/tf_M_do0/best.pt
--prefix tf_M_do0 --stage all` (sampling 13:45–14:39, driver at commit
`4691d19`, `sample.py` logic unchanged through `0e502e8`; evaluation
14:41–15:42, harness code unchanged from `24b99aa` to `0e502e8`, checked
with `git diff`). 1,000 samples per setting, lengths = the validation
reference's (n 1000, seed 0), sampling seed 0 for every setting (common
random numbers). Full table: `data/eval/ablation_tf_M_do0.csv`.

**beats_shuffles** (95 % intervals ≈ ± 0.018; real 0.792, random 0.503):

| T \ steps | 16 | 32 | 64 | 128 | 256 | 512 |
|---|---|---|---|---|---|---|
| 0.5 | 0.609 | 0.623 | 0.635 | 0.645 | 0.634 | 0.631 |
| 0.6 | 0.598 | 0.597 | 0.629 | 0.612 | 0.624 | 0.622 |
| 0.7 | 0.593 | 0.594 | 0.607 | 0.581 | 0.610 | 0.610 |
| 0.8 | 0.580 | 0.571 | 0.595 | 0.561 | 0.606 | 0.593 |
| 0.9 | 0.568 | 0.560 | 0.586 | 0.558 | 0.583 | 0.574 |
| **1.0** | 0.565 | 0.544 | 0.575 | 0.561 | **0.570** | 0.572 |
| 1.1 | 0.559 | 0.542 | 0.563 | 0.557 | 0.564 | 0.560 |
| 1.2 | 0.546 | 0.539 | 0.555 | 0.553 | 0.548 | 0.552 |

**At 256 steps, by temperature** (reference values from the table above):

| T | 0.5 | 0.6 | 0.7 | 0.8 | 0.9 | 1.0 | 1.1 | 1.2 | real | random |
|---|---|---|---|---|---|---|---|---|---|---|
| MFE z-score | −0.66 | −0.61 | −0.52 | −0.46 | −0.37 | −0.29 | −0.27 | −0.21 | −2.15 | −0.02 |
| NED (own MFE) | 0.250 | 0.249 | 0.254 | 0.242 | 0.247 | 0.249 | 0.245 | 0.249 | 0.175 | 0.242 |
| EternaFold NED of ViennaRNA's structure | 0.465 | 0.455 | 0.458 | 0.452 | 0.454 | 0.453 | 0.451 | 0.452 | 0.335 | 0.450 |
| GC content | 0.403 | 0.425 | 0.440 | 0.451 | 0.459 | 0.465 | 0.471 | 0.474 | 0.479 | 0.499 |
| JSD of 4-mer spectrum to real (floor 0.0008; random 0.024) | 0.038 | 0.020 | 0.011 | 0.006 | 0.004 | 0.003 | 0.003 | 0.004 | — | 0.024 |

Across all 48 settings: distinct samples 100 %; samples with a ≥ 80 %
sibling in the set 0 % (real RNA 57 %); samples with a ≥ 50 % training
relative ≤ 0.1 %; the two oracles agree on the exact structure 3–6 % of the
time (random 5 %, real 13 %).

**Reading it.**
1. **Steps make no measurable difference** for this model: at T = 1.0 the
   six step counts span 0.544–0.575, all inside each other's intervals.
   Letters revealed together can't coordinate, but this model has little
   pairing to coordinate.
2. **Lower temperature trades realism for a little "structure beyond
   chance".** From T = 1.2 to 0.5, beats_shuffles rises 0.548 → 0.634 and
   the z-score −0.21 → −0.66, but the composition drifts AU-rich (GC 0.474
   → 0.403) and the 4-letter-word statistics end up further from real RNA
   than random letters are (JSD 0.038 vs 0.024). T ≤ 0.6 fails the GC
   guardrail (± 0.05 of 0.479).
3. **No setting makes the folds better defined than random letters.** NED
   stays at 0.24–0.26 in all 48 settings (random 0.242, real 0.175), and
   EternaFold agrees (0.45–0.47 vs random 0.450, real 0.335). The sampling
   knobs can't substitute for a model that hasn't learned pairing, which
   sharpens Phase 2's finding: the baseline generates novel, diverse,
   letter-realistic RNA whose folding is close to that of shuffled RNA.
4. Consistency with the Phase 2 preview (T 1.0, 256 steps: 54.6 % beat one
   shuffle): 0.570 here. The two differ in lengths (training lengths then,
   validation lengths now) and ties (counted as losses then, half now).

**Checks on the ablation** (`data/eval/seed_calibration.sh`, commit
`d01f3e9`–`654d838`, docs-only difference; 15:43–15:56):
- *Reproducibility:* regenerating T 1.0 / 16 steps / seed 0 with the final
  code gives a **byte-identical** FASTA (`cmp`).
- *Are the bootstrap intervals honest?* Four more sampling seeds (1–4) at
  T 1.0 / 256 steps, same lengths:

  | metric | means for seeds 0–4 | sd across seeds | sd implied by the bootstrap interval (half-width / 1.96) |
  |---|---|---|---|
  | beats_shuffles | 0.570, 0.561, 0.554, 0.571, 0.567 | 0.0073 | 0.0094 |
  | ned_mfe | 0.249, 0.252, 0.254, 0.241, 0.246 | 0.0052 | 0.0041 |
  | mfe_z | −0.291, −0.266, −0.238, −0.295, −0.297 | 0.025 | 0.037 |
  | gc | 0.465, 0.465, 0.466, 0.464, 0.469 | 0.0020 | 0.0032 |
  | ef_ned_vienna | 0.453, 0.460, 0.466, 0.454, 0.465 | 0.0058 | 0.0041 |

  Ratios 0.63–1.41. An sd from 5 values has 4 degrees of freedom, so its
  95 % range relative to the truth is about 0.35–1.67 (√(χ²₄/4)); all five
  fall inside. **The bootstrap intervals match the real sampling-seed
  variation.** This covers sampling randomness only; training-seed
  variation is measured in Phase 4 (5 seeds per architecture).

**The pre-registered steps rule returns N = 16** (`--stage table`,
`steps_rule`). Not adopted as the cross-backbone setting: the frozen
protocol uses 256 steps for every model, for the reason stated in P5.

### Design target sets (validation)

`python scripts/build_targets.py --split val` (commit `0e502e8`, clean;
seed 0; 2026-09-24 15:42). Rule: docstring of `scripts/build_targets.py`,
committed (`a1017ec`) before any target set existed.

| set | targets | median length | native = target under ViennaRNA | native NED (median) | SHA-256 |
|---|---|---|---|---|---|
| `rfam_val` | **402** (406 families; 4 with < 4 pairs dropped) | 85 | 100 % (by construction) | 0.115 | `8691cbdc…7e045` |
| `bprna_val` | **183** (182 Rfam-seed comparative structures, 1 tRNA) | 91 | **6.6 %** | 0.238 | `d94db068…ea56a` |

bpRNA funnel: 102,318 → 97,254 ACGU → 76,711 at 19–256 nt → 74,103 no
pseudoknot brackets → 21,054 canonical pairs and hairpins ≥ 3 → 18,493
≥ 4 pairs → 12,862 distinct → 7,336 not letter-for-letter in train → Rfam
verdicts: train-family member 2,609, long-family fragment 260, family in a
train clan 8, family outside our data 38, no family 942, validation family
2,752, test family 727 → 2,752 with no ≥ 80 % training hit → **183** (one
per family).

**Reading it.** ViennaRNA reproduces the comparatively derived bpRNA
structure for only 6.6 % of the natural sequences that carry it: the
oracle and the annotations disagree for most natural RNAs. So `bprna`
targets ask for structures the oracle does not predict for the native
sequence; natives there are a reference point, not a ceiling. `rfam`
targets are oracle-consistent by construction and remain the primary set.

### Does the second oracle's training data overlap ours?

EternaFold's training FASTA files (shipped with bioconda `eternafold`
1.3.1) against our validation split: exact matches 0 (40 against train);
MMseqs2 at ≥ 80 % coverage: ≥ 50 % identity **0.30 %** of validation
sequences (170 tRNA, 1 tRNA-Sec), ≥ 80 % 0.23 %, ≥ 95 % 0.02 %. Command: `python
scripts/check_oracle_overlap.py --split val` (commit after `654d838`;
reproduces the first, scratchpad measurement of 13:31 exactly). The test
version runs right after the freeze (protocol P9).

---

## Phase 4 preparation — Transformer training seeds (validation only)

The first compute of the frozen protocol's P4 (five seeds per model), run
during the Phase 3 gate because it needs no new code: the Transformer's
chosen configuration retrained with seeds 1–4 (`python
scripts/seed_replicates.py --prefix tf_M --seeds 1 2 3 4`, commit
`e65151c`, 2026-09-24 19:33 → 2026-09-25 01:18; settings read from
`tf_M_do0/config.json`). Seed 0 is the sweep winner `tf_M_do0`.

| training seed | 0 | 1 | 2 | 3 | 4 | mean | sd |
|---|---|---|---|---|---|---|---|
| best val bits/nt, 1 fixed draw (selection value) | 1.9040 | 1.9070 | 1.9041 | 1.9077 | 1.9102 | 1.9066 | 0.0026 |
| step of the best | 10,000 | 10,000 | 7,500 | 10,000 | 10,000 | | |
| **val bits/nt, mean of 4 draws** (E1's estimator) | 1.9061 | 1.9093 | 1.9064 | 1.9102 | 1.9124 | 1.9089 | **0.0026** |
| beats_shuffles (1,000 samples, T 1.0, 256 steps) | 0.570 | 0.560 | 0.548 | 0.558 | 0.583 | 0.564 | **0.0135** |
| ned_mfe (same samples) | 0.249 | 0.241 | 0.250 | 0.248 | 0.242 | 0.246 | **0.0043** |
| mfe_z | −0.29 | −0.25 | −0.17 | −0.23 | −0.31 | −0.25 | 0.055 |
| EternaFold NED of ViennaRNA's structure | 0.453 | 0.454 | 0.460 | 0.461 | 0.450 | 0.456 | 0.0047 |
| GC | 0.465 | 0.468 | 0.467 | 0.465 | 0.467 | 0.466 | 0.0016 |

Likelihoods: `python scripts/eval_likelihood.py --checkpoint
checkpoints/tf_M_do0_seed<k>/best.pt --split val --draws 4`; samples and
scores: `scripts/sample.py … --lengths-from val --steps 256 --temperature
1.0 --seed 0` then `scripts/evaluate_samples.py` (commit `6c88270`;
`data/eval/seed_variation.sh`, 01:19–01:36). Every seed's draw 0
reproduces its training-time value exactly. Guardrails pass for every seed
(0 % copying, 100 % distinct, GC within 0.015 of real).

**Reading it.**
- Every seed peaks at 7.5–10k steps and then overfits: the Phase 2
  pattern belongs to the model and data, not to one seed.
- The single-draw selection value is 0.002–0.003 lower than the 4-draw
  value for **every** seed: the winner's curse of choosing a checkpoint on
  one fixed noise draw, which is why E1 averages 4 draws.
- Retraining moves beats_shuffles more than sampling alone does (sd 0.0135
  between trained models vs ≈ 0.009 within one), so for E2 the training
  seed is a real source of variation; for NED it is mostly sampling noise
  (0.0043 vs ≈ 0.004).

**What the frozen 5-vs-5 test can detect** (`python
scripts/power_seed_test.py`, deterministic; power = chance of detecting a
real difference of Δ per-seed sd):

| Δ / sd | 1 | 1.5 | 2 | 2.5 | 3 | 4 |
|---|---|---|---|---|---|---|
| P(p ≤ 0.01), the first Holm threshold | 0.07 | 0.20 | 0.41 | 0.57 | 0.76 | 0.96 |
| P(p ≤ 0.05) | 0.28 | 0.53 | 0.78 | 0.91 | 0.98 | 1.00 |

With the Transformer's seed spread, ~80 % power needs Δ ≈ 3 sd: about
**0.008 bits/nt** on E1, **0.04** on E2 (baseline 0.56 → ~0.60; real RNA
0.79), **0.013** on E3 (baseline 0.246; real 0.175). Smaller real
improvements would be reported as "not detectable with 5 seeds", with
their effect sizes and intervals. Informational: this does not change the
frozen protocol, and a Mamba backbone's own seed spread may differ.

### The replication split (split seed 1)

Built 2026-09-25 04:46–11:33 (≈ 1 h 50 min of process time; the laptop slept
in between): `python scripts/prepare_data.py --split-seed 1` at commit
`7df3d40` → `data/processed_split1/`, `splits/rfam_split_seed1.tsv`. Only
`stable_hash`'s prefix changes, so the cleaned corpus is identical (567,579
sequences after the per-family cap, the same number as split 0) and only the
held-out groups differ. Verified before launching: `--split-seed 0`
reproduces the three frozen files byte for byte.

| | train | val | test |
|---|---|---|---|
| sequences | 452,177 (79.7 %) | 57,116 (10.1 %) | 57,836 (10.2 %) |
| families | 3,141 | 348 | 348 |
| median length | 95 | 87 | 88 |

Step 10 removed 449 letter-level near-twins of train (402 val, 47 test; led
by UnaL2 157, mir-1803 58, tRNA 55); step 11 removed 1 structural member
(snosnR61 → TtnuCD8). The same assertions as split 0 passed, so no clan,
family or identical sequence occurs in two splits.

**How independent is it?** Only **29 of 348** validation families and **30 of
348** test families are also held out in split 0 (8–9 %), and **95,104 of its
114,952 held-out sequences were in split 0's training set**. So a result that
repeats on this split is not repeating on nearly the same test families.

### The Transformer on the replication split (P4, validation only)

`python scripts/replication_run.py --prefix tf_M` at commit `e2809f8`
(clean), 2026-09-25 14:38 → 18:41 (1 h 31 min of process time; the laptop
slept ≈ 2.5 h in between). It copies `tf_M_do0`'s recipe from its
config.json (lr 3×10⁻⁴, dropout 0, 30,000 steps, warmup 1,000, 16,384-token
batches, EMA 0.9999, eval every 2,500) and changes only `--data-dir
data/processed_split1`; seed 0. Run `tf_M_do0_split1`. Validation =
split 1's own validation set (348 families), EMA weights, fixed noise
(seed 1234):

| step | 2.5k | 5k | 7.5k | 10k | **12.5k** | 15k | 20k | 25k | 30k |
|---|---|---|---|---|---|---|---|---|---|
| split-1 val bits/nt (EMA) | 1.9407 | 1.9239 | 1.9181 | 1.9152 | **1.9141** | 1.9151 | 1.9198 | 1.9235 | 1.9261 |

Best **1.9141** at step 12,500 (`best.pt`); split 0's baseline reached
1.9040 at step 10,000 on its own validation families. Same shape on both
splits: best after ≈ 4 epochs, then overfitting. The two numbers are on
different validation families, so their difference says nothing about the
model; split 1's test set is evaluated with the frozen protocol once every
model's replication run exists.

### Does Mamba run here, and how fast? (single-block micro-benchmark)

Run 2026-09-25 05:00 in the scratchpad (throwaway code, not part of the
repository; Phase 4 repeats it on the full models with
`scripts/measure_memory.py`). `Mamba2(d_model=384, d_state=128, d_conv=4,
expand=2)` from `mamba-ssm` 2.3.2.post1 vs one Phase 2 Transformer block
(d 384, 6 heads), bf16 autocast, forward + backward + AdamW step, 10 timed
steps after 2 warm-up steps, batch 16.

| | parameters per block | L = 64 | L = 256 | L = 1024 |
|---|---|---|---|---|
| Mamba2 block | 993,572 | 5.6 ms | 6.0 ms | **11.7 ms** |
| Transformer block | 1,771,008 | 3.6 ms | **3.8 ms** | 21.7 ms |
| peak memory, either | | 0.06–0.08 GB | 0.13–0.14 GB | 0.44–0.45 GB |

**Reading it.**
- **The kernels work** on the RTX 4060 under WSL2. This was the largest
  technical risk in the project (D-004) and it is now cleared.
- **The crossover is real and sits above our data.** At 1,024 nucleotides the
  Mamba block is 1.9× *faster* than attention; at our 256-nucleotide cap it
  is 1.6× *slower* per block. This is the measured version of the note in
  STUDY_GUIDE §3.6: the length cap chosen for the 8 GB card favours the
  Transformer, so the Phase 4 comparison is **conservative for Mamba**.
- **At equal parameters the gap widens**, because a Mamba2 block holds fewer
  parameters than a Transformer block of the same width: matching 14.17 M
  needs ≈ 14 Mamba blocks against 8 Transformer blocks, so ≈ 84 ms vs
  ≈ 30 ms per step at L = 256, i.e. **≈ 2.8× the training time**. A 30,000-step
  run would take ≈ 3.7 h instead of 1.35 h, putting Phase 4's GPU budget at
  ≈ 60–70 h rather than the 33–58 h estimated before this measurement.
- Caveats: one block in isolation, fixed batch, no data loading; `d_state`
  is Mamba2's default 128 and a smaller state would be cheaper. Whether to
  match parameters by depth or by width is a Phase 4 design decision, taught
  before it is made. The honest number for the protocol's compute-matching
  comes from the full models.

### Memory and speed of the full Phase 4 models

`python scripts/measure_memory.py --group phase4` at commit `9a2fee4`,
2026-09-25 18:44–18:56, idle GPU (7.44 GB free of 8.59), bf16 autocast,
forward + backward + AdamW on random framed sequences, 10 timed steps after
3 warm-up steps; raw output `checkpoints/measure_memory_phase4.log`. The
training setting is the 16,384-token batch:

| model | parameters | L = 256: peak GB | ms/step | k nt/s | L = 64: peak GB | ms/step | k nt/s |
|---|---|---|---|---|---|---|---|
| Transformer M (baseline) | 14,174,976 | 2.38 | 161.6 | 101 | 2.44 | 153.4 | 107 |
| **BiMamba, depth-matched** (14 × d 384) | 14,010,608 | 4.39 | 465.4 | 35 | 4.60 | 645.8 | 25 |
| **AR Mamba, depth-matched** (14 × d 384) | 13,927,672 | 2.40 | 238.5 | 69 | 2.71 | 329.5 | 50 |
| BiMamba, width-matched (8 × d 512, head 32) | 13,900,288 | 3.61 | 353.4 | 46 | 3.87 | 551.8 | 30 |
| AR Mamba, width-matched (8 × d 528, head 32, state 64) | 14,136,248 | 2.17 | 219.8 | 75 | 2.30 | 310.2 | 53 |

At 32,768 tokens (headroom only, not a training setting) the Transformer
needs 4.5–4.6 GB and the AR models 3.8–5.2 GB, but both BiMamba sizes
exceed the free memory at L = 64 (7.51 and 8.96 GB) and depth-matched
BiMamba at L = 256 too (8.27 GB): WSL then spills into system RAM with no
error, and a step takes 4–15 s instead of < 1 s.

**Reading it.**
- Every Phase 4 model fits the 16,384-token batch with ≥ 2.8 GB to spare, so
  the protocol's batch size needs no change (no gradient accumulation).
- Per step, depth-matched BiMamba costs ≈ 2.9× (L 256) to 4.2× (L 64) the
  Transformer; AR Mamba ≈ 1.5–2.2×. Width matching would be ≈ 15–25 %
  faster for BiMamba, ≈ 6–8 % for AR Mamba.
- **Mamba gets slower per token as sequences get shorter**, the opposite of
  intuition: at a fixed token budget, 256 sequences of 64 letters carry 256
  full-size states (98,304 numbers per layer each), 64 sequences of 256
  carry 64. A state-space model pays per sequence as well as per letter.
- **Chunk size checked and left at the default.** Mamba-2 computes its scan in
  chunks (default 256 positions). Scratchpad `chunk_test.py`: chunk sizes
  128, 64, 32 give the same outputs as 256 to ≤ 3.3 × 10⁻⁵ (float32, 2-layer
  BiMamba, lengths 40–258), as the algorithm is exact for any chunking.
  Speed at 16,384 tokens, BiMamba full size, ms/step for chunks
  256 / 128 / 64 / 32: L 64: 635 / 501 / 623 / 752; L 96: 526 / 427 / 506 /
  688; L 128: 466 / 508 / 537 / 667; L 256: 462 / 438 / 472 / 600 (8 timed
  steps each). At most ≈ 20 % and not consistent, so the library default is
  kept.
- Estimated GPU time for the protocol with depth matching (30,000-step runs
  at ≈ 0.5 s/step for BiMamba and ≈ 0.3 s for AR Mamba at typical lengths,
  plus validation passes): BiMamba ≈ 42–47 h (LR sweep, dropout sweep, 4
  seeds, replication run), AR Mamba ≈ 25 h; **≈ 70 GPU-hours** in all, before
  test-set sampling and evaluation.

---

## Phase 0 — oracle sanity checks (not experiments)

Hand-calculated predictions from session 01, checked against ViennaRNA.
Deterministic (no randomness, so no seed). No project code is involved; the
numbers depend only on ViennaRNA **2.7.2** as pinned in `environment.yml`
(default Turner 2004 parameters). Run inside `conda activate ribomamba`.
Recorded 2026-09-22, session 02.

| Sequence | Condition | Result | Command |
|---|---|---|---|
| `GGGAAACCC` | 37 °C | MFE `(((...)))` −1.20 kcal/mol | `echo GGGAAACCC \| RNAfold --noPS` |
| `GGGACCC` | 37 °C | MFE `.......` 0.00 | `echo GGGACCC \| RNAfold --noPS` |
| `GGGAAACCA` | 37 °C | MFE `((....)).` −1.90 | `echo GGGAAACCA \| RNAfold --noPS` |
| `GGGAAACCC` | 37 °C | nearest rival `((....)).` −1.00 (gap 0.20) | `echo GGGAAACCC \| RNAsubopt -e 4 -s` |
| `GGGAAACCC` | 37 °C | MFE shape frequency in ensemble 0.5065 | `echo GGGAAACCC \| RNAfold --noPS -p` |
| `GGGAAACCA` | 37 °C | MFE shape frequency in ensemble 0.9386 | `echo GGGAAACCA \| RNAfold --noPS -p` |
| `GGGAAACCC` | 70 °C | MFE `.........` 0.00; `(((...)))` = +1.39 | `echo GGGAAACCC \| RNAfold --noPS -T 70`; `printf 'GGGAAACCC\n(((...)))\n' \| RNAeval -v -T 70` |

Interpretation: logbook/2026-09-22-session-02.md, entry 22:30.

---

## Experimental results

*(None yet.)*

| Date | Experiment | Metric | Value | Command | Commit | Seed |
|---|---|---|---|---|---|---|
