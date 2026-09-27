# Current handoff — 2026-09-27 (sessions 07-09)

## User decision
The user approved the research pivot and, on 2026-09-27, standing approval to
make and document decisions overnight. Research quality over teaching gates.
Limits: validation/development targets only until a new protocol is frozen,
no final-test scoring before that, no push, no paid services. The user LIFTED
the pilot compute caps (2026-09-27 ~11:20 IST): local CPU/GPU use is not capped.
WSL restarted ~07:30 IST and killed two runs; both were resumed at 11:17 IST.

## Where things stand (measured, not planned)
Stage A is BUILT and RUN. Stage B is DONE and NEGATIVE.
Commits (local, not pushed): ec95f5c pivot docs; 8f3c81b Stage A harness;
19a8bee Stage B neural probe; e90fc09 MFE-repair control + comparisons.

- Code: ribomamba/design/{scoring,manifest,hard_manifest,search,baselines,neural,
  mfe_repair,runner,summary}.py; scripts/repair_pilot.py (manifest/run/summarize),
  scripts/repair_compare.py. Tests: tests/test_design_*.py (53 pass, CPU).
- Manifests (in Git): manifests/repair_pilot_val_v1.json (rfam_val, EASY tier,
  sha 58df4ac1...) and manifests/eternaweb_dev_v1.json (HARD Eterna web puzzles,
  sha 19f16b01...; 32 dev / 32 confirmation / 8 smoke). Confirmation evaluation has started; see manifests/confirmation_looks.jsonl.
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

## Exact next task (session 09, updated ~22:25 IST 2026-09-27)
PROTOCOL v2 IS FROZEN (docs/PROTOCOL_design_v2.md, commit 35e0325, D-028). The FINAL benchmark
is RUNNING: data/repair_pilot/run_final_v2.sh (nohup) runs, in order, final_v2_eterna100_v2
(2,400 units), final_v2_eterna100_v1only, final_v2_rfam_taneda27; 8 methods x 3 seeds, 128 s
method time per unit, 10 workers + GPU. Completion marker: data/repair_pilot/final_v2.done.
If interrupted (sleep / WSL restart): rerun data/repair_pilot/run_final_v2.sh — finished units
are skipped; wall-limited units that spanned a suspend are rerun automatically.
Afterwards: `python scripts/final_report.py --eternafold` (frozen endpoints, V1 combination,
EternaFold check), then write the technical report. Do NOT change methods, budgets or endpoints.
Framing (D-026): Q1 non-neural energy screen; Q2 target-conditioned denoiser (conditioning
criterion met on development; method criterion not met); negative neural results recorded.

## Execution environment
WSL Ubuntu-24.04:
```bash
cd /home/chirag/projects/RiboMamba
source /home/chirag/miniforge3/etc/profile.d/conda.sh
conda activate ribomamba
```
rg is unavailable; use find/grep. GPU RTX 4060 Laptop 8 GB. SamplingDesign was built using the separate rmtools compiler environment. Do not reinstall the environment.
Use `python -u` for long runs (stdout is block-buffered under nohup).
Waiting on a run: never `pgrep -f`/`pkill -f` a pattern that also matches the
waiting shell's own command line.

## Compute ledger (caps LIFTED by the user on 2026-09-27 ~11:20 IST; keep disclosing usage)
Counted as elapsed hours x (workers / 4). Through 07:20 IST: CPU ~1.4 h
(diagnostics 0.1, manifests 0.06, smokes 0.03, dev1024 0.34, mfe_repair 0.02,
RNAinverse 0.12, Stage B neural 0.62, pool 0.01, build of SamplingDesign ~0).
GPU ~0.62 h (Stage B). In flight: efilter (2 workers) + training data (2 workers).

## Existing assets (older)
- data/processed/{train,val,test}.parquet; data/targets/*_val.parquet (validation).
- checkpoints/tf_M_do0/best.pt: Transformer EMA, 14.17 M params (unconditional).
- Phase 4 paused (PHASE4_PAUSED.md); BiMamba seed 2 interrupted at 27,500.

## Scientific cautions
- No SOTA, novelty or generalisation claim exists. Dev results are development
  evidence on 32 hard puzzles; confirmation is in progress; final tests remain unscored in this review.
- The ~1.9 unconditional bound is not a floor; conditional losses differ.
- RNAinverse's candidates are whole adaptive walks (internal calls uncountable);
  compare it on wall time only. SAMFEO's wall excludes harness re-scoring.
- Paired edits, defect-weighted mutation (NUPACK), hierarchical decomposition
  (RNAinverse, NUPACK), remasking, search distillation and RL are prior art.

## 2026-09-27 Codex review — read before continuing
The user reaffirmed uncapped local compute and asked for original, SOTA-directed
research on this laptop. Read docs/CODEX_TO_CLAUDE_2026-09-27.md for the prepared
reply, novelty map, and competition-aware residual repair proposal. This is a
recommendation, not an achieved result or frozen new experiment.
Correction to earlier status: confirmation HAS been launched; see the two records
in manifests/confirmation_looks.jsonl (same configuration). At review it remained
in progress along with trainpool_samfeo_v1. Do not call confirmation untouched.
Runner now defaults to no wall cap; CLI no longer enforces four workers maximum.
Live processes still retain their explicit launch timeouts; resume without those
if needed. No live Claude message/read receipt is claimed; this is shared-file
handoff. Do not start concurrent implementing agents.
