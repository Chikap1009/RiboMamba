# Current handoff — 2026-09-29 (project closed; sessions 07-12)

## User decision
The user approved the research pivot (efficient RNA inverse folding through coordinated repair;
research progress over teaching gates) and standing autonomy for routine decisions. Local CPU/GPU
use is not capped (lifted 2026-09-27 ~11:20 IST). Limits that still hold: no paid services, no push
or external messages, one GPU training job at a time, preserve all data/checkpoints/results, no
subagents, no SOTA/biological claims, record negative results.

## Status (2026-09-29): PROJECT CLOSED
The research direction is closed. No experiment, training run or evaluation is pending or scheduled,
and nothing is running. The final technical report is complete: docs/REPORT_repair_v2.md (limitations
in its section 9; optional publication work in section 11). Decisions: D-029 (final benchmark), D-030
(efficiency study, with a closeout correction), D-031 (closeout).

## Where everything is
- Report and reproduction: docs/REPORT_repair_v2.md, docs/REPRODUCE.md, docs/figures/ (drawn by
  scripts/final_figures.py from the FINAL report).
- Final benchmark (protocol v2, frozen 2026-09-27; docs/PROTOCOL_design_v2.md, amendments 1-4f):
  data/repair_pilot/final_v2_eterna100_v2/, final_v2_eterna100_v1only/, final_v2_rfam_taneda27/ (3,504
  valid units; 117 superseded V2 units kept in final_v2_eterna100_v2/units_superseded/); FINAL report
  data/repair_pilot/final_v2_report.json (commit 842124b) and its superseded predecessors in
  data/repair_pilot/report_history/ (with a README); chain scripts scripts/final_v2/.
- Efficiency study (development only): record docs/experiments/2026-09-28-tcd-inference-efficiency.md;
  declared comparison data/repair_pilot/ew_dev_tcdgraph_v1/ (compare.json); isolated profiles
  prof_tcd_iso_warm_v1/ (warm), prof_tcd_iso_cold_v1/ (LABELLED cold but warm in fact: runner quirk
  fixed in 82361cc; kept, see its LABEL.txt), prof_tcd_iso_cold_v2/ (cold); component profiles
  data/repair_pilot/prof_tcd/.
- Models: checkpoints/tf_M_do0/best.pt (base), checkpoints/tcd_v1/tcd.pt (TCD; model card
  docs/MODEL_CARD_tcd_v1.md); data card docs/DATA_CARD_design.md; manifests/.
- Records: docs/RESULTS.md (incl. "Closeout verification"), docs/DECISIONS.md, docs/logbook/ (latest
  2026-09-29-session-12.md), docs/REFERENCES.md.
- Local preservation package: /home/chirag/projects/RiboMamba_closeout_2026-09-29/ (built by
  scripts/closeout_package.py): COMMIT.txt, ribomamba.bundle, restore/ (copies of data/repair_pilot,
  essential checkpoints, prepared data, target sources), docs_snapshot/, inventory.json (A copied /
  B referenced in place / C obtain separately), checks/, SHA256SUMS, VERIFY.txt. It is a second copy on
  the same disk, not an independent backup; third-party code is not included (inventory gives URLs,
  commits, licences).

## Repository and backup status
- GitHub (github.com/Chikap1009/RiboMamba, public): at the start of the final documentation pass on
  2026-09-29, origin/main (5b33522, 2026-09-27 04:37 IST) was 89 commits behind local main (checked with
  `git fetch`). The user authorised pushing: on 2026-09-29 ~03:35 IST `git push origin main` fast-forwarded
  GitHub from 5b33522 to 5c93550 (90 commits, no force); this record's own commit was pushed after it.
  Only Git-tracked files are on GitHub (no data, checkpoints or third-party code).
- The preservation package (/home/chirag/projects/RiboMamba_closeout_2026-09-29/) is on the SAME DISK as
  the repository: a second copy, not an independent backup. Copy it to separate storage for protection
  against disk loss.
- Project history index: docs/PROJECT_HISTORY.md (sessions, decisions, register of mistakes).

## Final results in brief
Eterna100 V2, solved by 128 s (any seed / mean of 3 seeds, of 100): RNAinverse 75 / 71.7; SAMFEO 74 / 71.0;
SAMFEO + TCD proposals + screen 73 / 71.0; SAMFEO + screen 73 / 70.7; DesiRNA 74 / 68.3; TCD sampling
62 / 61.3; targeted random 56 / 56.0; SamplingDesign (1 thread) 48 / 43.7. Primary endpoint null (no
equivalence claim). Secondary: best NED TCD + screen 0.0400 vs SAMFEO 0.0459 (-0.0059 [-0.0085, -0.0035]).
Efficiency study (development): CUDA-graph proposals cut overhead 2.48x (4 concurrent cold runs; 1.5-1.8x
alone) and doubled candidates within 16 s, but TCD + screen still trailed SAMFEO + screen by 6.3 / 5.2
uMFE points at 16 / 64 s; reducing proposal overhead did not eliminate that disadvantage.

## Evaluation-set status
Development (eternaweb_dev_v1, 32 puzzles): used throughout development. Confirmation (32 sealed
puzzles): one look (+9.4 uMFE points for the screen), consumed. Final sets (Eterna100 V2/V1,
Rfam-Taneda-27): scored under protocol v2, consumed. Any future claim would need a new, unused
evaluation set and a newly frozen protocol; none is planned.

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
- No SOTA, novelty, generalisation or wet-lab claim exists, and no speed claim beyond the measured
  configuration (one laptop GPU under WSL2). The primary final endpoint is null.
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

## Public repository presentation — 2026-09-29

The user authorized repository improvements and GitHub publication in this chat. The public README
now leads with the completed study, all eight final success rates, a figure, and reproduction limits.
`docs/README.md` separates reader documentation from historical/maintenance records.
`docs/results/final_v2_summary.json` copies canonical aggregate fields and records the source SHA-256;
it excludes candidate-level EternaFold output and raw traces. Rendering it reproduces both figures.
`.github/workflows/checks.yml` runs 20 CPU tokenizer/statistics tests and parses the public result JSON;
this is distinct from the 54-test local integration suite. No experiment or inference method changed.
The original closeout preservation package remains a historical snapshot; subsequent presentation
changes are committed in Git and are not claimed to be part of that earlier package.
