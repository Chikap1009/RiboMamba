#!/bin/bash
# Phase 4 GPU queue: every training run the frozen protocol (P4) asks of the two Mamba models,
# one job at a time. Order and rules fixed 2026-09-25, before any Mamba training run existed.
#
#   per model: learning-rate sweep (D-011, boundary rule, amendment A1)
#              -> dropout sweep over 30,000-step runs (D-012, best-during-run)
#              -> training seeds 1-4 of the winner (the winner is seed 0)
#   then:      one run per model on the replication split (hyperparameters from split 0)
#
# Every step resumes where it stopped (ribomamba/sweeps.py: run_to_completion), so after a
# crash, a reboot or `kill`, relaunching this script continues the queue. Test-set evaluation is
# NOT here: it runs after all training, for all three models with the same code (P9 step 4).
#
# Model sizes: D-015 (parameters matched by depth: width 384 as the Transformer, 14 layers).
#
# Usage: setsid nohup scripts/phase4_queue.sh > checkpoints/phase4_queue.log 2>&1 &
set -euo pipefail
cd "$(dirname "$0")/.."

# User-approved research pivot; retain the historical queue for reproducibility.
if [[ -f docs/PHASE4_PAUSED.md ]]; then
    echo "Phase 4 is intentionally paused. Read docs/HANDOFF.md." >&2
    exit 2
fi

BIMAMBA=(--arch bimamba --n-layers 14)
AR_MAMBA=(--arch ar_mamba --n-layers 14)

for spec in "bimamba_M:BIMAMBA" "ar_mamba_M:AR_MAMBA"; do
    prefix=${spec%%:*}
    declare -n arch_args=${spec##*:}
    echo "=== $(date '+%F %T') $prefix: learning-rate sweep"
    python scripts/lr_sweep.py --prefix "$prefix" -- "${arch_args[@]}"
    echo "=== $(date '+%F %T') $prefix: dropout sweep"
    python scripts/dropout_sweep.py --prefix "$prefix" -- "${arch_args[@]}"
    echo "=== $(date '+%F %T') $prefix: training seeds 1-4"
    python scripts/seed_replicates.py --prefix "$prefix" --seeds 1 2 3 4
    unset -n arch_args
done
for prefix in bimamba_M ar_mamba_M; do
    echo "=== $(date '+%F %T') $prefix: replication split"
    python scripts/replication_run.py --prefix "$prefix"
done
echo "=== $(date '+%F %T') PHASE 4 QUEUE COMPLETE"
