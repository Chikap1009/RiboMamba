> **SUPERSEDED — project closed 2026-09-29.** This document is kept as a historical record. The
> pilot and every follow-up are complete; see docs/HANDOFF.md and docs/REPORT_repair_v2.md. Nothing
> here is an instruction to start work.

# Phase 4 queue paused — 2026-09-27
The user approved moving to the RNA repair research plan. The verified live queue
process group 38913 was terminated after the BiMamba seed-2 checkpoint at step
27,500 was saved. last.pt and best.pt remain on disk. Work after that checkpoint
is not guaranteed preserved. This is an intentional interruption, not completion.

Do not launch remaining seeds, the AR-Mamba sweep or replication runs by default.
scripts/phase4_queue.sh refuses to start while this file exists.
scripts/watch_queue.sh treats this marker as an intentional pause and exits.
Remove this marker only after a deliberate decision to resume the old study;
record that decision. PIDs above are historical: never reuse them without checks.
