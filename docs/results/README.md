# Aggregate benchmark results

[final_v2_summary.json](final_v2_summary.json) contains the final benchmark's aggregate tables, time curves, and paired effects. It copies the `status`, `provenance`, and `sets` fields from the canonical local report without recomputing statistics. The `snapshot` field records the source file's SHA-256.

The report was generated from commit `842124b` after corrective reruns. The final sets contain 3,504 method/target/seed units. See the [technical report](../REPORT_repair_v2.md) for interpretation and the [protocol](../PROTOCOL_design_v2.md) for endpoint definitions.

## Fields

- `solved_by_128s`: puzzles solved by any seed and mean solved over three seeds.
- `curves`: seed-mean uMFE success at each method-time checkpoint.
- `quality_128s`: quality over units with a design; missing-design counts are explicit.
- `paired`: target-level paired effects and bootstrap intervals; seeds are averaged within target.

The V1 combined table reuses V2 runs on the 81 shared structures. No new experiment or statistical analysis was performed for this snapshot.

## Render the saved results

From the repository root, with matplotlib available:

```bash
python scripts/final_figures.py --report docs/results/final_v2_summary.json --out-dir /tmp/ribomamba-figures
```

This renders the canonical aggregate estimates. It does not independently recompute them from raw traces. Historical bootstrap intervals can vary when regenerated from traces because the analysis did not sort target rows before seeded resampling; the canonical values are retained here.

The snapshot excludes raw traces, candidate sequences, checkpoints, and the independent EternaFold design-level output. Those local assets are described in the [reproduction guide](../REPRODUCE.md).
