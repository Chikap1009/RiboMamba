#!/bin/bash
# Final benchmark, protocol v2 (frozen 2026-09-27, commit 35e0325). One runner batch per manifest.
source /home/chirag/miniforge3/etc/profile.d/conda.sh
conda activate ribomamba
export OMP_NUM_THREADS=1
cd /home/chirag/projects/RiboMamba
M="samfeo samfeo_efilter samfeo_tcdprop_efilter tcd_sample random_pairs desirna rnainverse samplingdesign"
for SET in eterna100_v2 eterna100_v1only rfam_taneda27; do
  python -u scripts/repair_pilot.py run --run final_v2_$SET --manifest final_$SET --subset all \
    --budget 5010 --seeds 0 1 2 --unit-time-limit 128 --workers 8 --recycle-workers --gpu --methods $M \
    > data/repair_pilot/final_v2_$SET.stdout 2>&1 || exit 1
done
echo FINAL_ALL_DONE > data/repair_pilot/final_v2.done
