#!/bin/bash
# Corrective pass after run_final_v2.sh (protocol v2 amendments 2, 3, 4 and 4b):
#  1. move every desirna / samplingdesign unit that STARTED before its method's last replay/timing fix
#     (+60 s margin for in-flight units) to units_superseded/ (kept for the record, not deleted);
#     the rule depends only on start times and commit times, never on outcomes;
#  2. resume each set with --retry-errors: only errored, invalid or moved units run again.
# Fix times (commit times, UTC):
#   desirna         bda4884  2026-09-27T19:45:05  per-round timing + initial population logged
#   samplingdesign  74ec5f1  2026-09-27T19:35:08  line-buffered output with arrival-time stamps
# Run as data/repair_pilot/run_final_v2_retry.sh (a one-line wrapper) after data/repair_pilot/final_v2.done.
source /home/chirag/miniforge3/etc/profile.d/conda.sh
conda activate ribomamba
export OMP_NUM_THREADS=1
cd /home/chirag/projects/RiboMamba
python - <<'PY' || exit 1
import datetime as dt, json, shutil
from pathlib import Path
FIX = {"desirna": "2026-09-27T19:45:05+00:00", "samplingdesign": "2026-09-27T19:35:08+00:00"}
moved = {}
for run in sorted(Path("data/repair_pilot").glob("final_v2_*")):
    if not run.is_dir():
        continue
    for method, when in FIX.items():
        cutoff = dt.datetime.fromisoformat(when) + dt.timedelta(seconds=60)
        for status in (run / "units" / method).glob("*.json"):
            s = json.loads(status.read_text())
            if dt.datetime.fromisoformat(s["started_utc"]) <= cutoff:
                dest = run / "units_superseded" / method
                dest.mkdir(parents=True, exist_ok=True)
                for suffix in (".json", ".parquet", ".log"):
                    f = status.with_suffix(suffix)
                    if f.exists():
                        shutil.move(str(f), dest / f.name)
                moved[f"{run.name}/{method}"] = moved.get(f"{run.name}/{method}", 0) + 1
print("moved (superseded) units:", json.dumps(moved))
PY
M="samfeo samfeo_efilter samfeo_tcdprop_efilter tcd_sample random_pairs desirna rnainverse samplingdesign"
for SET in eterna100_v2 eterna100_v1only rfam_taneda27; do
  python -u scripts/repair_pilot.py run --run final_v2_$SET --manifest final_$SET --subset all \
    --budget 5010 --seeds 0 1 2 --unit-time-limit 128 --workers 8 --recycle-workers --gpu --retry-errors \
    --methods $M > data/repair_pilot/final_v2_${SET}.retry.stdout 2>&1 || exit 1
done
echo RETRY_DONE > data/repair_pilot/final_v2_retry.done
