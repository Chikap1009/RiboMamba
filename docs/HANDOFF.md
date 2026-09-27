# Current handoff — 2026-09-27 (session 07, overnight)

## User decision
The user approved the research pivot and, on 2026-09-27, standing approval to
make and document decisions overnight. Research quality over teaching gates.
Limits still apply: validation/development targets only, no final-test scoring,
no new large training, pilot cap 8 elapsed CPU-hours (<= 4 workers) and
2 GPU-hours, one GPU job at a time, no push, no paid services.

## Where things stand (measured, not planned)
Stage A is BUILT and RUN. Stage B probe is IN PROGRESS (see log for status).
Commits (local, not pushed): ec95f5c pivot docs; 8f3c81b Stage A harness;
19a8bee Stage B neural probe; e90fc09 MFE-repair control + comparisons.

- Code: ribomamba/design/{scoring,manifest,hard_manifest,search,baselines,neural,
  mfe_repair,runner,summary}.py; scripts/repair_pilot.py (manifest/run/summarize),
  scripts/repair_compare.py. Tests: tests/test_design_*.py (53 pass, CPU).
- Manifests (in Git): manifests/repair_pilot_val_v1.json (rfam_val, EASY tier,
  sha 58df4ac1...) and manifests/eternaweb_dev_v1.json (HARD Eterna web puzzles,
  sha 19f16b01...; 32 dev / 32 confirmation / 8 smoke). Confirmation targets
  have NOT been looked at (manifests/confirmation_looks.jsonl absent).
- External: external/SAMFEO at e78b4b5 (no license file: local use only);
  data/raw/eternaweb_rnadesignlm/ (MIT data from arXiv:2602.12470 + audit copies).
- Raw traces: data/repair_pilot/<run>/ (ignored by Git; summary.md per run,
  compare_dev_stageA.md across runs).

Key results, 32 hard dev targets x 3 seeds (uMFE success, target means):
| method | 64 evals | 1024 evals | by 1 s wall | by 64 s wall | best log10 P @1024 |
|---|---|---|---|---|---|
| random_pairs (no search) | 14% | 16% | 14% | 16% | -2.43 |
| random_pair_edits | 14% | 42% | 30% | 42% | -2.08 |
| feedback_pair_edits | 12% | 43% | 25% | 43% | -2.03 |
| mfe_repair (MFE-only, stops when solved) | - | 31% | 30% | 31% | - |
| SAMFEO (pinned, defaults) | 21% | 48% | 35% | 48% | -1.20 |
| RNAinverse (restarts, 64 max) | - | - | 46% | 59% | - |
Easy tier (rfam_val smoke): at ceiling; the shared start alone solves most.
Trace finding: late in search only ~2 % of proposals improve; feedback edits waste
~33 % of late proposals on repeats. Defect-weighted site choice = random sites.

## Exact next task
1. Finish Stage B: summarise data/repair_pilot/ew_dev1024_neural_v1 and run
   `python scripts/repair_compare.py --runs ew_dev1024_v1 ew_dev1024_neural_v1
   --name dev_stageB --pairs neural_feedback_edits:feedback_pair_edits
   neural_random_edits:random_pair_edits neural_feedback_edits:neural_random_edits`.
2. Record the Stage B decision (continuation criterion in RESEARCH_PLAN.md) in
   DECISIONS/RESULTS and this handoff. Then follow the decision recorded there.

## Execution environment
WSL Ubuntu-24.04:
```bash
cd /home/chirag/projects/RiboMamba
source /home/chirag/miniforge3/etc/profile.d/conda.sh
conda activate ribomamba
```
rg is unavailable; use find/grep. GPU RTX 4060 Laptop 8 GB. No C/C++ compiler
(SamplingDesign needs one; not installed). Do not reinstall the environment.
Use `python -u` for long runs (stdout is block-buffered under nohup).
Waiting on a run: never `pgrep -f`/`pkill -f` a pattern that also matches the
waiting shell's own command line.

## Compute ledger (pilot cap: 8 elapsed CPU-h, 2 GPU-h)
CPU elapsed so far ~0.7 h (diagnostics 5 min, manifests 3.4 min, smokes 1.6 min,
dev1024 20.5 min, mfe_repair 1.4 min, RNAinverse 7.2 min). GPU: Stage B run
started 06:27 IST (cap 0.9 h).

## Existing assets (older)
- data/processed/{train,val,test}.parquet; data/targets/*_val.parquet (validation).
- checkpoints/tf_M_do0/best.pt: Transformer EMA, 14.17 M params (unconditional).
- Phase 4 paused (PHASE4_PAUSED.md); BiMamba seed 2 interrupted at 27,500.

## Scientific cautions
- No SOTA, novelty or generalisation claim exists. Dev results are development
  evidence on 32 hard puzzles; confirmation and final tests are untouched.
- The ~1.9 unconditional bound is not a floor; conditional losses differ.
- RNAinverse's candidates are whole adaptive walks (internal calls uncountable);
  compare it on wall time only. SAMFEO's wall excludes harness re-scoring.
- Paired edits, defect-weighted mutation (NUPACK), hierarchical decomposition
  (RNAinverse, NUPACK), remasking, search distillation and RL are prior art.
