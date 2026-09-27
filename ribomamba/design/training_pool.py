"""Training-side puzzle pool for a Stage C repair model (built only if Stage C is justified).

From the same Eterna web source as eternaweb_dev_v1 (hard_manifest.py), with
the same structural eligibility and the same hardness probe, visited in a
numpy default_rng(SEED) order, a puzzle is accepted only if its normalized
edit distance is > 0.2 to EVERY development/confirmation target of
eternaweb_dev_v1 (so no near-copy of an evaluation target is trained on) and to
every test-side structure of the leakage audit, and > 0.2 to every puzzle
already accepted (no near-duplicates inside the pool). The first N_HOLDOUT
accepted puzzles form a puzzle-level held-out split for model selection; the
rest are for training. Development targets are never used for fitting.
The pool is written in the manifest format (subset "train" / "train_holdout").
"""

import json

import numpy as np

from ribomamba.design import hard_manifest as hm
from ribomamba.design.manifest import MANIFESTS_DIR, content_hash, sha256_file
from ribomamba.paths import REPO_ROOT

NAME = "eternaweb_trainpool_v1"
PATH = MANIFESTS_DIR / f"{NAME}.json"
SEED = 20260929
N_TOTAL = 700
N_HOLDOUT = 100


def build(n_total: int = N_TOTAL, n_holdout: int = N_HOLDOUT, seed: int = SEED, workers: int = 4) -> dict:
    from multiprocessing import get_context
    dev = json.loads(hm.PATH.read_text())
    evaluation = [t["structure"] for t in dev["targets"]]
    evaluation_ids = {t["eterna_id"] for t in dev["targets"]}
    audit = [s for v in hm.audit_structures().values() for s in v]
    banned = hm.eterna100_ids()
    rows = sorted((json.loads(line) for line in open(hm.SOURCE)), key=lambda r: r["id"])
    seen, pool = set(), []
    for r in rows:
        ss = r["target_structure"]
        if hm._structurally_ineligible(ss) or ss in seen or r["id"] in banned or r["id"] in evaluation_ids:
            continue
        seen.add(ss)
        pool.append({"id": f"{hm.ID_PREFIX}{r['id']}", "eterna_id": r["id"], "structure": ss})
    rng = np.random.default_rng(seed)
    order = rng.permutation(len(pool))
    accepted, counts = [], {"visited": 0, "probe_solved": 0, "near_evaluation_target": 0, "near_test_side": 0,
                            "near_duplicate": 0}
    with get_context("spawn").Pool(workers) as p:
        for start in range(0, len(order), 256):
            batch = [pool[int(k)] for k in order[start:start + 256]]
            probes = p.map(hm.probe, [(r["id"], r["structure"]) for r in batch])
            for r, pr in zip(batch, probes):
                counts["visited"] += 1
                if pr["start_solved"]:
                    counts["probe_solved"] += 1
                    continue
                if hm.too_similar(r["structure"], evaluation):
                    counts["near_evaluation_target"] += 1
                    continue
                if hm.too_similar(r["structure"], audit):
                    counts["near_test_side"] += 1
                    continue
                if hm.too_similar(r["structure"], [a["structure"] for a in accepted]):
                    counts["near_duplicate"] += 1
                    continue
                accepted.append({**r, "length": len(r["structure"]), "pairs": r["structure"].count("("),
                                 "probe_start_ned_mean": round(pr["start_ned_mean"], 6)})
                if len(accepted) == n_total:
                    break
            if len(accepted) == n_total:
                break
    for k, r in enumerate(accepted):
        r["subset"] = "train_holdout" if k < n_holdout else "train"
        r["smoke"] = False
    manifest = {
        "name": NAME,
        "purpose": "TRAINING-side puzzles for a Stage C repair model; disjoint from and dissimilar to every "
                   "eternaweb_dev_v1 target and every test-side audit structure.",
        "source": {"path": str(hm.SOURCE.relative_to(REPO_ROOT)), "sha256": sha256_file(hm.SOURCE), **hm.PROVENANCE},
        "evaluation_manifest": {"name": dev["name"], "content_sha256": dev["content_sha256"]},
        "seed": seed,
        "rules": {"eligibility": "as eternaweb_dev_v1 (structure, length, pairs, hairpins, distinct, not Eterna100 id)",
                  "hardness_probe": "as eternaweb_dev_v1", "exclusion": f"normalized edit distance <= "
                  f"{hm.SIMILARITY_MAX} to any evaluation target, test-side structure or accepted puzzle",
                  "split": f"first {n_holdout} accepted = train_holdout (puzzle level)"},
        "funnel": {**counts, "accepted": len(accepted)},
        "targets": sorted(accepted, key=lambda t: t["id"]),
    }
    manifest["content_sha256"] = content_hash(manifest)
    return manifest
