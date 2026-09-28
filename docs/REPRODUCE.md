# Reproducing the RiboMamba design results

Written 2026-09-29 at project closeout. It covers the technical report
[REPORT_repair_v2.md](REPORT_repair_v2.md): the protocol v2 final benchmark and the TCD
inference-efficiency study. Part A only reads saved results; Part B launches experiments and is
expensive and unnecessary for viewing or checking the report.

## 1. Platform assumed
- Linux x86-64. Measured on Windows 11 + WSL2 Ubuntu 24.04 (kernel 6.18), 20 logical CPUs, ~11 GB RAM
  allocated to WSL, NVIDIA RTX 4060 Laptop GPU (8 GB), driver 595.79.
- A GPU is needed only for TCD methods and model training; everything in Part A runs on the CPU
  (EternaFold uses MPI; see 5).
- Timings, speed-ups and GPU latency behaviour are specific to this machine (section 7).

## 2. Environments (conda; do not upgrade them for reproduction)
| name | lock file | used for |
|---|---|---|
| ribomamba | environment.design_v2.ribomamba.lock.yml | harness, SAMFEO, RNAinverse, TCD, ViennaRNA 2.7.2, EternaFold 1.3.1, tests |
| desirna | environment.design_v2.desirna.lock.yml | DesiRNA runs; also matplotlib for the figures |
| rmtools | environment.design_v2.rmtools.lock.yml | compiler used to build SamplingDesign |
environment.lock.yml is the older Phase 3 freeze record of the ribomamba environment; keep it for
history, and use the design_v2 files for this report. Rebuild an environment (only if it is missing):
`conda env create -n <name> -f <lock file>`, then `pip install -e .` inside ribomamba.
Activate: `source /home/chirag/miniforge3/etc/profile.d/conda.sh && conda activate ribomamba`.

## 3. Ignored assets (not in Git)
Required under the repository root (paths, sizes and SHA-256 are in the closeout package's
inventory.json; see docs/HANDOFF.md for the package location):
- data/repair_pilot/: all run directories (unit traces *.parquet, status *.json, logs), the FINAL
  report final_v2_report.json, report_history/, compare.json of ew_dev_tcdgraph_v1, prof_tcd/.
- checkpoints/tf_M_do0/best.pt (base model), checkpoints/tcd_v1/tcd.pt (TCD); critic_v1/ and
  residual_v1/ for the negative critic results.
- data/processed/ (Rfam splits), data/tcd_v1/ (TCD training pairs), data/raw/eterna100/ and
  data/raw/eternaweb_rnadesignlm/ (target sources); data/raw/rfam*/ only to rebuild the Rfam splits.
- external/ third-party code (NOT in the package; obtain as below).
Restore from the closeout package: copy its `restore/` tree over the repository root (it mirrors the
original relative paths), e.g. `rsync -a <package>/restore/ /home/chirag/projects/RiboMamba/`, then run
`sha256sum -c <package>/SHA256SUMS` from inside the package to check the package copies.
Obtain third-party code (never redistributed; SAMFEO has no licence file):
```bash
git clone https://github.com/shanry/SAMFEO.git external/SAMFEO && git -C external/SAMFEO checkout e78b4b5dc6082b0e832e0ed388f18d78e4bf7a5d
git clone https://github.com/fryzjergda/DesiRNA.git external/DesiRNA && git -C external/DesiRNA checkout bdb490839941daf30fe9119cbc4e2961d57f3a36
git clone https://github.com/weiyutang1010/SamplingDesign.git external/SamplingDesign && git -C external/SamplingDesign checkout f0283c495c1031c52d4d7ecd06975a2894f5865b
(cd external/SamplingDesign && conda activate rmtools && make CC=x86_64-conda-linux-gnu-g++)   # -> bin/main
```
Rebuild the Rfam splits instead of restoring them (hours): `python scripts/download_data.py`
(pinned files, checksums verified) then `python scripts/prepare_data.py` (byte-identical output).

## 4. Focused correctness tests (CPU; GPU tests skip without CUDA or the checkpoint)
```bash
export OMP_NUM_THREADS=1
python -m pytest -q tests/test_final_report.py tests/test_design_runner.py tests/test_design_baselines.py \
  tests/test_design_search.py tests/test_conditioned.py tests/test_tcd_graph.py
```
Success: all pass (54 tests at closeout, 2026-09-29, with the GPU; without CUDA or
checkpoints/tcd_v1/tcd.pt, four of the five tests in test_tcd_graph.py are skipped).

## 5. Part A — regenerate tables and figures from saved results (read-only; minutes)
Never regenerate onto the canonical files; write to a scratch directory:
```bash
OUT=$(mktemp -d)
# FINAL v2 report (tables of report sections 5-6); ~10 min with EternaFold, ~1 min without --eternafold.
python scripts/final_report.py --eternafold --out $OUT/final_v2_report.json
# Figures 1-2 (matplotlib lives in the desirna env; this script needs only json + matplotlib)
/home/chirag/miniforge3/envs/desirna/bin/python scripts/final_figures.py --out-dir $OUT/figs
# Efficiency comparison (report section 8) and its gates
python scripts/tcd_graph_compare.py --out $OUT/compare.json
# Closeout consistency checks (re-validates every unit; --replay N re-runs N candidates in memory)
python scripts/closeout_verify.py --out $OUT/verify.json --replay 40
```
Expected: `final_report.py` prints `[FINAL] written to $OUT/...` and refuses (exit 1) if any unit is
missing, invalid or in error; its status/coverage/audit sections equal the canonical
data/repair_pilot/final_v2_report.json. Figures are byte-identical to docs/figures/*.png. Point
estimates reproduce exactly; bootstrap interval bounds can move by one discrete step (up to 0.0123 for
uMFE fractions, 0.0008 for NED) because per-puzzle rows are not sorted before the seeded bootstrap. Using
`final_report.py` without `--out` would archive the canonical report into report_history/ and replace
it; do not do that to check a result.

## 6. Part B — experiments (EXPENSIVE; not needed to read or check the report)
All write into data/repair_pilot/<run>/ and are resumable; a finished run is skipped unit by unit.
New run names avoid touching the originals.
- Protocol v2 final benchmark (~17 h on the machine above, 8 concurrent units, GPU for TCD units):
  `bash scripts/final_v2/run_final_v2.sh` then `bash scripts/final_v2/run_final_v2_retry.sh`
  (corrective pass; fix times in scripts/final_v2/fix_times.json), then
  `python scripts/final_report.py --eternafold`. Final manifests are refused unless the protocol is
  frozen (it is). To rerun rather than resume, edit the run names in those scripts first.
- Efficiency comparison (~2 h, 4 concurrent units, GPU):
  `python -u scripts/repair_pilot.py run --run <new name> --manifest eternaweb_dev_v1 --subset development
  --budget 5010 --seeds 0 1 2 --unit-time-limit 64 --workers 4 --recycle-workers --gpu --methods samfeo
  samfeo_efilter samfeo_tcdprop_efilter samfeo_tcdprop_efilter_graph`, then
  `python scripts/tcd_graph_compare.py --run <new name> --out <file>`.
- Isolated speed profiles (~50 min each; 1 worker): add `--target-ids eternaweb:7567037 eternaweb:13344845
  eternaweb:13385974 eternaweb:2624571 eternaweb:5654857 eternaweb:4819207 --workers 1` to the command
  above with the two TCD methods; `--recycle-workers` gives the cold variant (fixed in 82361cc; before
  that fix a one-worker run was always warm). Component profile: `python scripts/profile_tcd.py cold`
  and `python scripts/profile_tcd.py components`.
- TCD training data and fine-tuning (~10 min CPU + ~23 min GPU): `python scripts/tcd_data.py --workers 6`
  then `python scripts/tcd_train.py --steps 8000` (writes checkpoints/tcd_v1/; move the existing one
  aside first; it is kept as the best design-validation step).
- Base model (Phase 2; ~1.4 GPU-hours per run): `python scripts/dropout_sweep.py --prefix tf_M` trains
  the dropout sweep whose dropout-0 run is checkpoints/tf_M_do0.

## 7. Known limitations of reproduction
- Wall-clock budgets make results machine-dependent: other hardware, load or concurrency changes how
  many candidates fit in 128 s (or 16 / 64 s) and therefore the outcomes.
- DesiRNA, SamplingDesign and RNAinverse are timed by the wall clock and are not bit-reproducible;
  SAMFEO-hosted methods, targeted random and TCD sampling replay identically at a fixed candidate budget
  on the same machine (checked for the first 40 candidates at closeout).
- CUDA-graph and eager TCD forwards were bitwise identical only on the configuration in section 1; CPU
  runs use float32 instead of bfloat16 and differ numerically from GPU runs.
- The first 43 final V2 units ran in persistent workers (protocol amendment 1); a rerun with the current
  scripts would run every unit in a fresh process.
- WSL2: a laptop suspend or WSL restart kills running jobs; resume with the same command (the runner
  also rejects wall-clock-limited units that spanned a suspend).
