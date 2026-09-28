# Current handoff — 2026-09-28 (sessions 07-10)

## User decision
The user approved the research pivot (efficient RNA inverse folding through coordinated repair;
research progress over teaching gates) and standing autonomy for routine decisions. Local CPU/GPU
use is not capped (lifted 2026-09-27 ~11:20 IST). Limits that still hold: no paid services, no push
or external messages, one GPU training job at a time, preserve all data/checkpoints/results, no
subagents, no SOTA/biological claims, record negative results.

## Where things stand (measured, 2026-09-28 ~16:30 IST)
The protocol v2 FINAL BENCHMARK IS COMPLETE and reported. Nothing is running.
- Protocol: docs/PROTOCOL_design_v2.md, frozen 2026-09-27; amendments 1-4f are operational,
  measurement or report-side fixes (no method, budget or endpoint changes; nothing tuned on
  final outcomes).
- Coverage: Eterna100 V2 2,400/2,400, V1-only 456/456, Rfam-Taneda-27 648/648 units valid; 0 errors;
  117 V2 DesiRNA/SamplingDesign units that ran pre-fix code were superseded (kept in
  data/repair_pilot/final_v2_eterna100_v2/units_superseded/) and rerun by the corrective pass.
- Report: data/repair_pilot/final_v2_report.json, status FINAL, generated 2026-09-28 10:09:58 UTC
  from commit 842124b (no uncommitted changes) after the corrective pass (10:01:37 UTC). It
  SUPERSEDES two earlier files, moved to data/repair_pilot/report_history/ (README there): an
  unlabelled smoke test of the report script (29/2,400 units, 2026-09-27 22:21 IST) and an INTERIM
  file. Neither is a result.
- Write-up: docs/RESULTS.md "FINAL BENCHMARK"; docs/REPORT_repair_v2.md (sections 1 and 4 filled);
  decision D-029; logbook docs/logbook/2026-09-28-session-10.md.

## Final results in one paragraph (Eterna100 V2, 128 s one-core method time, seeds 0-2)
Solved by 128 s (any seed / mean): RNAinverse 75 / 71.7; SAMFEO 74 / 71.0; SAMFEO + TCD proposals +
energy screen 73 / 71.0; SAMFEO + energy screen 73 / 70.7; DesiRNA 74 / 68.3; TCD sampling 62 / 61.3;
targeted random 56 / 56.0; SamplingDesign (1 thread) 48 / 43.7. PRIMARY ENDPOINT NULL for every
variant developed here (screen - SAMFEO uMFE -0.3 pp [-3.3, +2.0]). Ensemble quality improves
modestly: best NED screen - SAMFEO -0.0026 [-0.0047, -0.0005] (72/25 puzzles); TCD + screen has the
lowest NED of all methods (0.0400 vs SAMFEO 0.0459; -0.0059 [-0.0085, -0.0035], 82/14) but a slow start
(40 % at 4 s vs 63 %). TCD sampling - targeted random +5.3 pp [-1.7, +12.3]; exploratory matched-sample
view: -5.7 pp at 16 samples, +8.3 pp [0.0, +17.1] at 1,024 (72 puzzles) — the development
conditioning gain (+27 pp) largely did not transfer. V1-only: 0/19 for every method, as in SAMFEO's
own published V1 results (the puzzles V2 redesigned for the Vienna 2 energy model). Rfam-Taneda-27
near ceiling (24/27 for the top five). EternaFold folds 25-39 % of best designs to target.

## Confirmation and evaluation-set status (corrected; earlier "in progress" notes are obsolete)
- Development set (eternaweb_dev_v1, 32 hard Eterna web puzzles): used for all development runs.
- Confirmation set (same manifest, 32 sealed puzzles): COMPLETE — one look, logged before any data
  (manifests/confirmation_looks.jsonl; two log lines = one interrupted launch + resume with the same
  config hash d2e1f7a7). ew_conf1024_efilter_v1: 192/192 units valid; energy screen - SAMFEO +9.4 pp
  uMFE [1.0, 19.8] at 1,024 evaluations. It validated only the K = 8 screen and is now CONSUMED.
- Final sets (Eterna100 V2 / V1, Rfam-Taneda-27): SCORED under protocol v2 and now CONSUMED.
- Training pool (eternaweb_trainpool_v1, 700 puzzles): trainpool_samfeo_v1 COMPLETE, 700/700 units.
- Any new claim needs a NEW, unused evaluation set and a new frozen protocol (D-029).

## Exact next task
The core pilot question is answered (D-029). Remaining work is optional; pick with the user:
1. Paper-quality write-up of docs/REPORT_repair_v2.md. Done: figures (docs/figures/, drawn from the
   FINAL report by scripts/final_figures.py, rendered with the desirna env's matplotlib), model card
   docs/MODEL_CARD_tcd_v1.md, data card docs/DATA_CARD_design.md, prior-art list refreshed 2026-09-28
   (report section 6; REFERENCES session 10). Left: a longer methods section and, if publishing, a
   systematic literature review. Keep the framing: null uMFE, modest NED
   gain, TCD = model-adaptation result, careful negative results, harness/timing lessons.
2. Next model-adaptation question (docs/experiments/2026-09-28-target-conditioned-denoiser.md, "Next
   model-adaptation question", Q1-Q3; proposed, not frozen): Q1 amortised TCD proposals (cost), Q2 more
   training-side design data (over-fitting / transfer to Eterna100), Q3 search-aware fine-tuning.
   Needs a new unused evaluation set (e.g. leakage-audited Eterna web puzzles not in dev/confirmation/
   trainpool) and success criteria written before the first run.
3. Optional: finish the paused K ablation (ew_dev1024_kablation_v1, 77/384 units, resumable) as a
   labelled development sensitivity analysis only.
Do NOT rerun or re-analyse the final sets to look for a significant uMFE gain.

## Execution environment
WSL Ubuntu-24.04:
```bash
cd /home/chirag/projects/RiboMamba
source /home/chirag/miniforge3/etc/profile.d/conda.sh
conda activate ribomamba
```
rg is unavailable; use find/grep. GPU RTX 4060 Laptop 8 GB. SamplingDesign was built with the
separate rmtools compiler environment; DesiRNA runs in its own `desirna` env. Do not reinstall.
Use `python -u` for long runs. Never `pgrep -f`/`pkill -f` a pattern that also matches the waiting
shell's own command line. Final chain scripts: scripts/final_v2/ (fix times in fix_times.json).
Pinned environments for protocol v2: environment.design_v2.{ribomamba,desirna,rmtools}.lock.yml
(verified unchanged since the freeze); environment.lock.yml is the Phase 3 freeze record.

## Compute ledger (caps lifted 2026-09-27; disclosed, not limited)
Recorded per-unit time summed over all design runs in data/repair_pilot (units + superseded):
217.8 h unit wall, 160.8 h unit CPU (harness process; DesiRNA/SamplingDesign subprocess CPU not
included). Final benchmark: 139 h unit wall (V2 93.4, V1-only 18.1, Rfam 27.4) over ~17 h elapsed with
8 concurrent units; largest development run ew_dev_frontier_v1 31.6 h unit wall. GPU training:
Stage B probe ~0.6 h, critic_v1 13.6 min, three sibling critics ~20 min, TCD fine-tuning 1,351 s;
TCD inference inside units shares the one GPU. Earlier elapsed-x-workers ledger (to 2026-09-27
07:20 IST): CPU ~1.4 h, GPU ~0.62 h.

## Existing assets
- Checkpoints: checkpoints/tf_M_do0/best.pt (unconditional Transformer EMA, 14.17 M params);
  checkpoints/tcd_v1 (target-conditioned denoiser); checkpoints/critic_v1, checkpoints/residual_v1.
- Manifests: manifests/*.json (repair_pilot_val_v1, eternaweb_dev_v1, eternaweb_trainpool_v1,
  final_eterna100_v2 / _v1 / _v1only, final_rfam_taneda27); confirmation_looks.jsonl.
- External: external/SAMFEO at e78b4b5 (no license file: local use only, never redistribute);
  DesiRNA bdb4908 (Apache-2.0); SamplingDesign f0283c49.
- Raw traces: data/repair_pilot/<run>/ (ignored by Git). Phase 4 remains paused (PHASE4_PAUSED.md).

## Scientific cautions
- No SOTA, novelty, generalisation, wet-lab or speed claim exists. The primary final endpoint is null.
- The energy screen is non-neural and prior art in idea (INFO-RNA 2006); critics and the competition
  residual are negative online; the TCD is a model-adaptation result, not a benchmark-level gain.
- Development DesiRNA wall-time numbers are optimistic (RESULTS correction); final DesiRNA/
  SamplingDesign numbers use real timing. SamplingDesign at one thread is under-budgeted.
- Published numbers of other methods use other budgets/hardware; quote separately, never mix.
- The ~1.9 unconditional bound is not a floor; conditional losses differ.

## History note
docs/CODEX_TO_CLAUDE_2026-09-27.md (Codex review, 2026-09-27) proposed the competition-aware residual
experiment, since run (negative; docs/experiments/2026-09-27-competition-residual.md). Its status
notes about confirmation and the training pool being "in progress" are superseded by the section above.
