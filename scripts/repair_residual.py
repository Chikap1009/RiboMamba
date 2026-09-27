"""Competition-residual experiment (docs/experiments/2026-09-27-competition-residual.md).

  python scripts/repair_residual.py collect --workers 12      # sibling groups on the TRAINING pool
  python scripts/repair_residual.py diagnose                  # do rival banks explain the residual?

Only training-pool puzzles (manifests/eternaweb_trainpool_v1.json) are read here.
Output: data/repair_pilot/residual_siblings_v1/<puzzle>.parquet (one row per child),
written atomically per puzzle; rerunning skips finished puzzles.
"""

import argparse
import json
import sys
import time
from multiprocessing import get_context

import numpy as np
import polars as pl

from ribomamba.design import training_pool as tp
from ribomamba.design.manifest import load_manifest
from ribomamba.design.search import rng_for
from ribomamba.paths import PILOT_DIR

OUT = PILOT_DIR / "residual_siblings_v1"
SOURCE_RUN = "trainpool_samfeo_v1"
PHASES = (("early", 0, 32), ("mid", 32, 160), ("late", 160, 10**9))
QUOTA = {"early": 3, "mid": 3, "late": 2}


def choose_parents(trace: pl.DataFrame, puzzle_id: str) -> list[tuple[str, str, int]]:
    """(phase, parent sequence, first use) for up to 8 parents, stratified by when SAMFEO first mutated them."""
    trace = trace.sort("eval_index")
    seqs = trace["sequence"].to_list()
    first_use: dict[int, int] = {}
    for idx, par in zip(trace["eval_index"].to_list(), trace["parent_index"].to_list()):
        if par >= 0 and par not in first_use:
            first_use[par] = idx
    by_phase = {name: sorted(p for p, u in first_use.items() if lo <= u < hi) for name, lo, hi in PHASES}
    rng = rng_for("residual_parents", puzzle_id)
    chosen, leftovers = [], []
    for name, _, _ in PHASES:
        pool = by_phase[name]
        order = [pool[k] for k in rng.permutation(len(pool))]
        chosen += [(name, p) for p in order[:QUOTA[name]]]
        leftovers += [(name, p) for p in order[QUOTA[name]:]]
    short = sum(QUOTA.values()) - len(chosen)
    if short > 0 and leftovers:
        chosen += [leftovers[k] for k in rng.permutation(len(leftovers))[:short]]
    seen, out = set(), []
    for phase, p in chosen:
        if seqs[p] not in seen:
            seen.add(seqs[p])
            out.append((phase, seqs[p], first_use[p]))
    return out


def collect_puzzle(job: dict) -> dict:
    from ribomamba.design.baselines import load_samfeo
    from ribomamba.design.runner import atomic_write_bytes
    from ribomamba.design.siblings import sibling_group
    module, _ = load_samfeo()
    pairs = module.pairs_match(job["structure"])
    rows, costs, t0 = [], [], time.time()
    for g, (phase, parent, first_use) in enumerate(job["parents"]):
        seed = int(rng_for("residual_group", job["id"], g).integers(2**31 - 1))
        group = sibling_group(job["structure"], parent, module.mutate_structured, pairs, seed)
        costs.append({**group["cost"], "draws": group["draws"]})
        base = {k: v for k, v in group.items() if k not in ("children", "cost", "draws")}
        for child in group["children"]:
            rows.append({"puzzle": job["id"], "split": job["split"], "group": f"{job['id']}#{g}", "phase": phase,
                         "first_use": first_use, "structure": job["structure"], **base, **child})
    path = OUT / f"{job['id'].replace(':', '_')}.parquet"
    tmp = path.with_suffix(".tmp")
    pl.DataFrame(rows).write_parquet(tmp)
    tmp.replace(path)
    return {"puzzle": job["id"], "groups": len(job["parents"]), "children": len(rows), "seconds": time.time() - t0,
            "costs": costs}


def cmd_collect(args) -> None:
    pool = load_manifest(tp.PATH)
    OUT.mkdir(parents=True, exist_ok=True)
    traces = pl.read_parquet(PILOT_DIR / SOURCE_RUN / "units" / "samfeo" / "*.parquet")
    jobs = []
    for t in pool["targets"]:
        if (OUT / f"{t['id'].replace(':', '_')}.parquet").exists():
            continue
        parents = choose_parents(traces.filter(pl.col("target_id") == t["id"]), t["id"])
        jobs.append({"id": t["id"], "split": t["subset"], "structure": t["structure"], "parents": parents})
    jobs.sort(key=lambda j: -len(j["structure"]))
    print(f"{len(jobs)} puzzles to collect ({len(pool['targets']) - len(jobs)} done); {args.workers} workers", flush=True)
    t0 = time.time()
    log = open(OUT / "collect_log.jsonl", "a")
    with get_context("spawn").Pool(args.workers) as p:
        for k, res in enumerate(p.imap_unordered(collect_puzzle, jobs), 1):
            log.write(json.dumps(res) + "\n")
            log.flush()
            if k % 50 == 0 or k == len(jobs):
                print(f"  {k}/{len(jobs)} puzzles, {time.time() - t0:.0f} s", flush=True)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="command", required=True)
    c = sub.add_parser("collect")
    c.add_argument("--workers", type=int, default=8)
    args = p.parse_args()
    {"collect": cmd_collect}[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
