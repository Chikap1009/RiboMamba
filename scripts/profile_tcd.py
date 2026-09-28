"""Diagnostic profile of TCD proposals inside SAMFEO (docs/experiments/2026-09-28-tcd-inference-efficiency.md).

  python scripts/profile_tcd.py cold        # fresh processes: imports, CUDA init, checkpoint load, first calls
  python scripts/profile_tcd.py components  # warm, one process: per-stage times of samfeo_tcdprop_efilter units

DIAGNOSTIC ONLY: stages are CUDA-synchronised, which slows the whole; headline speeds come from minimally
instrumented runner runs. `components` replaces tcd.infill with a stage-timed copy of the SAME steps and
first checks that the copy returns exactly what the production infill returns for identical inputs and
random state. Writes JSON to data/repair_pilot/prof_tcd/.
"""

import argparse
import json
import os
import subprocess
import sys
import time

from ribomamba.paths import PILOT_DIR, REPO_ROOT

OUT = PILOT_DIR / "prof_tcd"
PROFILE_TARGETS = ["eternaweb:7567037", "eternaweb:13344845", "eternaweb:13385974", "eternaweb:2624571",
                   "eternaweb:5654857", "eternaweb:4819207"]        # length ranks 0/6/12/19/25/31 of 32 dev targets

COLD_SCRIPT = r"""
import json, time, resource, sys
T = {}
t = time.perf_counter()
from ribomamba.design import baselines
T["import_harness"] = time.perf_counter() - t; t = time.perf_counter()
baselines.load_samfeo()
T["load_samfeo"] = time.perf_counter() - t; t = time.perf_counter()
import torch
T["import_torch"] = time.perf_counter() - t; t = time.perf_counter()
from ribomamba.design import tcd
from ribomamba.models.conditioned import ConditionedDenoiser
from ribomamba.models.checkpoint import load_model
T["import_tcd_code"] = time.perf_counter() - t; t = time.perf_counter()
torch.cuda.init(); torch.zeros(1, device="cuda"); torch.cuda.synchronize()
T["cuda_init"] = time.perf_counter() - t; t = time.perf_counter()
base, _ = load_model(tcd.BASE_CHECKPOINT, weights="ema", device="cpu")
T["load_base_checkpoint"] = time.perf_counter() - t; t = time.perf_counter()
model = ConditionedDenoiser.from_unconditional(base)
T["build_conditioned"] = time.perf_counter() - t; t = time.perf_counter()
state = torch.load(tcd.REPO_ROOT / tcd.TCD_CHECKPOINT, map_location="cpu", weights_only=False)
model.load_state_dict(state["state"])
T["load_tcd_state"] = time.perf_counter() - t; t = time.perf_counter()
model = model.to("cuda").eval(); torch.cuda.synchronize()
T["to_device"] = time.perf_counter() - t
import numpy as np
from ribomamba.eval.folding import pair_table
structure = sys.argv[1]
pt = pair_table(structure)
parent = "".join("G" if c == "(" else "C" if c == ")" else "A" for c in structure)
masks = [[i] for i in range(0, len(structure), max(1, len(structure) // 8))][:8]
rng = np.random.default_rng(0)
calls = []
for k in range(12):
    t = time.perf_counter()
    tcd.infill(model, "cuda", structure, pt, parent, masks, rng); torch.cuda.synchronize()
    calls.append(time.perf_counter() - t)
T["infill_first"] = calls[0]; T["infill_second"] = calls[1]; T["infill_warm_median"] = sorted(calls[2:])[5]
T["peak_rss_mb"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
T["peak_gpu_mb"] = torch.cuda.max_memory_allocated() / 2**20
print("JSON" + json.dumps(T))
"""


def cold(args) -> None:
    from ribomamba.design.manifest import MANIFESTS_DIR, load_manifest
    structures = {t["id"]: t["structure"] for t in load_manifest(MANIFESTS_DIR / "eternaweb_dev_v1.json")["targets"]}
    rows = []
    for rep in range(args.repeats):
        for tid in (PROFILE_TARGETS[0], PROFILE_TARGETS[-1]):
            t = time.perf_counter()
            out = subprocess.run([sys.executable, "-c", COLD_SCRIPT, structures[tid]], capture_output=True, text=True,
                                 env={**os.environ, "OMP_NUM_THREADS": "1"}, cwd=REPO_ROOT)
            total = time.perf_counter() - t
            line = [x for x in out.stdout.splitlines() if x.startswith("JSON")]
            if not line:
                raise SystemExit(out.stderr[-3000:])
            rows.append({"repeat": rep, "target": tid, "length": len(structures[tid]), "process_total_s": total,
                         **json.loads(line[0][4:])})
            print(json.dumps({k: (round(v, 3) if isinstance(v, float) else v) for k, v in rows[-1].items()}), flush=True)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "cold.json").write_text(json.dumps(rows, indent=1))


def components(args) -> None:
    import numpy as np
    import torch

    from ribomamba.data.tokenizer import BOS_ID, EOS_ID, FIRST_NUCLEOTIDE_ID, MASK_ID, NUCLEOTIDES
    from ribomamba.design import baselines, tcd
    from ribomamba.design.manifest import MANIFESTS_DIR, load_manifest
    from ribomamba.design.search import (BudgetExhausted, DeadlineReached, Evaluator, Target, TimeLimitReached,
                                         shared_start)
    from ribomamba.models.conditioned import structure_inputs

    torch.set_num_threads(1)
    structures = {t["id"]: t["structure"] for t in load_manifest(MANIFESTS_DIR / "eternaweb_dev_v1.json")["targets"]}
    model, device = tcd.load(tcd.TCD_CHECKPOINT)
    production_infill = tcd.infill
    stage: dict = {}
    keys: list = []

    def sync():
        if device == "cuda":
            torch.cuda.synchronize()

    def tick(name, t0):
        sync()
        now = time.perf_counter()
        stage[name] = stage.get(name, 0.0) + now - t0
        return now

    @torch.no_grad()
    def timed_infill(model, device, structure, pt, parent, masks, rng):
        """Stage-timed copy of tcd.infill (same steps, same order, same random draws)."""
        sync()
        t = time.perf_counter()
        L, W = len(structure), len(structure) + 2
        full = []
        for m in masks:
            s = set(m)
            s |= {pt[p] for p in m if pt[p] >= 0}
            full.append(sorted(s))
        keys.extend((parent, tuple(m)) for m in full)
        t = tick("masks_expand", t)
        host = torch.tensor([BOS_ID, *[FIRST_NUCLEOTIDE_ID + NUCLEOTIDES.index(c) for c in parent], EOS_ID])
        t = tick("ids_host_build", t)
        base = host.to(device)
        t = tick("ids_h2d", t)
        ids = base.repeat(len(masks), 1)
        for b, m in enumerate(full):
            ids[b, [p + 1 for p in m]] = MASK_ID
        attn = torch.ones_like(ids, dtype=torch.bool)
        t = tick("ids_mask_on_device", t)
        bracket, partner = structure_inputs([structure] * len(masks), W, device)
        t = tick("structure_inputs_build_and_h2d", t)
        with torch.autocast("cuda", dtype=torch.bfloat16, enabled=device == "cuda"):
            logits = model(ids, attn, bracket, partner)
        t = tick("forward", t)
        probs = torch.softmax(logits[..., FIRST_NUCLEOTIDE_ID:].double(), dim=-1)
        t = tick("softmax_on_device", t)
        probs = probs.cpu().numpy()
        t = tick("d2h_probs", t)
        canon = tcd.CANON16.numpy().reshape(4, 4)
        out = []
        for b, m in enumerate(full):
            seq, done = list(parent), set()
            for p in m:
                if p in done:
                    continue
                q = pt[p]
                if q >= 0:
                    i, j = min(p, q), max(p, q)
                    joint = np.outer(probs[b, i + 1], probs[b, j + 1]) * canon
                    k = int(rng.choice(16, p=(joint / joint.sum()).ravel()))
                    seq[i], seq[j] = NUCLEOTIDES[k // 4], NUCLEOTIDES[k % 4]
                    done |= {i, j}
                else:
                    pr = probs[b, p + 1]
                    seq[p] = NUCLEOTIDES[int(rng.choice(4, p=pr / pr.sum()))]
                    done.add(p)
            out.append("".join(seq))
        tick("numpy_sampling", t)
        stage["infill_calls"] = stage.get("infill_calls", 0) + 1
        stage["infill_rows"] = stage.get("infill_rows", 0) + len(masks)
        return out

    def timed_hook(fn, name):
        def wrapped(*a, **k):
            t = time.perf_counter()
            try:
                return fn(*a, **k)
            finally:
                stage[name] = stage.get(name, 0.0) + time.perf_counter() - t
                stage[name + "_calls"] = stage.get(name + "_calls", 0) + 1
        return wrapped

    module, _ = baselines.load_samfeo()
    orig_mutate, orig_eval, orig_energy = module.mutate_structured, module.position_ed_pd_mfe, baselines.FILTERS["energy"]
    results = []
    try:
        for tid in PROFILE_TARGETS:
            target = Target(tid, structures[tid])
            # equivalence check: the timed copy returns exactly the production result
            parent = shared_start(target, 0)
            masks = [[p] for p in range(0, len(parent), max(1, len(parent) // 8))][:8]
            a = production_infill(model, device, target.structure, target.pt, parent, masks, np.random.default_rng(7))
            b = timed_infill(model, device, target.structure, target.pt, parent, masks, np.random.default_rng(7))
            assert a == b, f"timed infill differs from production on {tid}"
            stage.clear()
            keys.clear()
            tcd.infill = timed_infill
            module.mutate_structured = timed_hook(orig_mutate, "samfeo_draft")
            module.position_ed_pd_mfe = timed_hook(orig_eval, "samfeo_evaluation")
            baselines.FILTERS["energy"] = timed_hook(orig_energy, "energy_screen")
            ev = Evaluator(target, budget=args.budget, time_limit_s=args.time_limit, subtract_scoring=True)
            status = "early_stop"
            try:
                baselines.samfeo(target, 0, ev, baselines.BASELINE_SETTINGS["samfeo_tcdprop_efilter"])
            except BudgetExhausted:
                status = "complete"
            except (TimeLimitReached, DeadlineReached):
                status = "time_limit"
            finally:
                tcd.infill = production_infill
                module.mutate_structured, module.position_ed_pd_mfe = orig_mutate, orig_eval
                baselines.FILTERS["energy"] = orig_energy
            wall = time.perf_counter() - ev.t0
            distinct = len(set(keys))
            row = {"target": tid, "length": len(target), "status": status, "evaluations": ev.count,
                   "unit_wall_s": wall, "method_time_s": ev.method_time(), "harness_scoring_s": ev.score_wall_s,
                   "proposal_calls": ev.proposal_calls, "proposal_wall_s": ev.proposal_wall_s,
                   "model_calls": ev.model_calls, "model_wall_s": ev.model_wall_s,
                   "infill_rows": len(keys), "distinct_parent_mask_inputs": distinct,
                   "repeated_input_fraction": 1 - distinct / max(1, len(keys)), **stage}
            results.append(row)
            print(json.dumps({k: (round(v, 4) if isinstance(v, float) else v) for k, v in row.items()}), flush=True)
    finally:
        tcd.infill = production_infill
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "components.json").write_text(json.dumps(results, indent=1))


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("cold")
    c.add_argument("--repeats", type=int, default=3)
    k = sub.add_parser("components")
    k.add_argument("--budget", type=int, default=5010)
    k.add_argument("--time-limit", type=float, default=64.0)
    args = p.parse_args()
    {"cold": cold, "components": components}[args.cmd](args)


if __name__ == "__main__":
    main()
