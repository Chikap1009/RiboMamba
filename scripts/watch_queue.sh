#!/bin/bash
# Watch a long training queue and EXIT when something needs a person's attention (operations tool,
# not part of any experiment). Run it in the background; whoever launched it is notified when it exits.
#
# Exits with: 0 queue finished ("PHASE 4 QUEUE COMPLETE" in the queue log, checked first, because a
#               finished queue's process is gone too; checking the process first gave false alarms in
#               session 04)
#             1 the queue's processes are gone WITHOUT the completion line (crash, kill, reboot)
#             2 two checks in a row below 10 k nucleotides/s (another GPU user, battery power, a spill)
#             3 a training run finished (a new "done:" line): time to record its result
#             4 a new stage summary (*_summary.json) appeared
#             5 a run diverged (a new DIVERGED marker, amendment A1)
# Anything already present when it starts counts as seen, so restarting it never re-reports old events.
#
# Usage: scripts/watch_queue.sh <queue process group id>
#   find the group id with:  ps -eo pid,pgid,args | grep '[p]hase4_queue'
PGID=$1
cd "$(dirname "$0")/.." || exit 1
if [ -f docs/PHASE4_PAUSED.md ]; then echo "QUEUE INTENTIONALLY PAUSED"; exit 0; fi
LOG=checkpoints/phase4_queue.log
DONE_LINE="PHASE 4 QUEUE COMPLETE"
count_done() { local n; n=$(grep -c "^done:" "$LOG" 2>/dev/null); echo "${n:-0}"; }   # grep -c prints 0 AND fails on no match
list() { ls $1 2>/dev/null | sort | tr '\n' ' '; }
seen_done=$(count_done)
seen_sum=$(list 'checkpoints/*mamba*_summary.json')
seen_div=$(list 'checkpoints/*mamba*/DIVERGED')
slow=0
while true; do
  sleep 300
  if [ -f docs/PHASE4_PAUSED.md ]; then echo "QUEUE INTENTIONALLY PAUSED"; exit 0; fi
  if grep -q "$DONE_LINE" "$LOG"; then echo "QUEUE COMPLETE $(date '+%F %T')"; tail -5 "$LOG"; exit 0; fi
  if ! ps -eo pgid= | grep -qw "$PGID"; then
    sleep 5
    if grep -q "$DONE_LINE" "$LOG"; then echo "QUEUE COMPLETE $(date '+%F %T')"; exit 0; fi
    echo "QUEUE GONE WITHOUT COMPLETION $(date '+%F %T')"; grep -vE "Warning|cutlass|layout_c" "$LOG" | tail -25; exit 1
  fi
  if [ "$(count_done)" -gt "$seen_done" ]; then
    echo "RUN FINISHED $(date '+%F %T')"; grep -E "^done:|^lr |^dropout |^seed |^=== " "$LOG" | tail -6; exit 3
  fi
  if [ "$(list 'checkpoints/*mamba*_summary.json')" != "$seen_sum" ]; then
    echo "STAGE SUMMARY $(date '+%F %T'): $(list 'checkpoints/*mamba*_summary.json')"; exit 4
  fi
  if [ "$(list 'checkpoints/*mamba*/DIVERGED')" != "$seen_div" ]; then
    echo "DIVERGED $(date '+%F %T')"; cat checkpoints/*mamba*/DIVERGED; exit 5
  fi
  csv=$(ls -t checkpoints/*mamba*/log.csv 2>/dev/null | head -1)
  last=$(grep -E '^[0-9]+,[0-9]+,[^,]+,[0-9.]+,' "$csv" 2>/dev/null | tail -1)
  knt=$(echo "$last" | cut -d, -f8)
  if [ -n "$knt" ] && [ "$knt" -lt 10 ] 2>/dev/null; then slow=$((slow + 1)); else slow=0; fi
  if [ "$slow" -ge 2 ]; then echo "SLOW $(date '+%F %T'): $csv last row $last"; exit 2; fi
done
