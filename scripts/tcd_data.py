"""Training data for the target-conditioned denoiser (docs/experiments/2026-09-28-target-conditioned-denoiser.md).

  python scripts/tcd_data.py --workers 6

natural  N Rfam TRAIN sequences (seeded sample, <= 256 nt) with their ViennaRNA 2.7.2 MFE
         structures (>= 4 pairs kept); validation = 2 % of families (by stable hash).
design   distinct uMFE designs found by SAMFEO on TRAINING-pool puzzles (trainpool_samfeo_v1),
         at most 64 per puzzle; the pool's train_holdout puzzles form the design validation set.
Exclusion: any pair whose structure is within normalized edit distance <= 0.2 of any
eternaweb_dev_v1 target (development and confirmation) or any final-manifest structure.
Output: data/tcd_v1/{natural_train,natural_val,design_train,design_val}.parquet + info.json.
"""

import argparse
import hashlib
import json
import time
from multiprocessing import get_context

import numpy as np
import polars as pl

from ribomamba.design.hard_manifest import too_similar
from ribomamba.design.manifest import MANIFESTS_DIR, load_manifest
from ribomamba.paths import DATA_DIR, PILOT_DIR, PROCESSED_DIR

OUT = DATA_DIR / "tcd_v1"
SEED = 20260928
EXCLUDE = None


def exclusion_structures() -> list[str]:
    out = [t["structure"] for t in load_manifest(MANIFESTS_DIR / "eternaweb_dev_v1.json")["targets"]]
    for name in ("final_eterna100_v2", "final_eterna100_v1", "final_rfam_taneda27"):
        out += [t["structure"] for t in load_manifest(MANIFESTS_DIR / f"{name}.json")["targets"]]
    return sorted(set(out))


def _init(excl):
    global EXCLUDE
    EXCLUDE = excl


def _fold_and_check(item):
    import RNA

    from ribomamba.eval.folding import model_details
    seq, family = item
    structure, _ = RNA.fold_compound(seq, model_details()).mfe()
    if structure.count("(") < 4:
        return None
    return (seq, structure, family, too_similar(structure, EXCLUDE) is not None)


def _check(item):
    seq, structure, key = item
    return (seq, structure, key, too_similar(structure, EXCLUDE) is not None)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--natural", type=int, default=150_000)
    p.add_argument("--per-puzzle", type=int, default=64)
    p.add_argument("--workers", type=int, default=6)
    args = p.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    excl = exclusion_structures()
    info = {"exclusion_structures": len(excl), "seed": SEED, "args": vars(args)}
    t0 = time.time()

    train = pl.read_parquet(PROCESSED_DIR / "train.parquet", columns=["sequence", "family"])
    train = train.filter(pl.col("sequence").str.len_chars() <= 256)
    rng = np.random.default_rng(SEED)
    pick = train[np.sort(rng.choice(train.height, size=min(args.natural, train.height), replace=False)).tolist()]
    with get_context("spawn").Pool(args.workers, initializer=_init, initargs=(excl,)) as pool:
        nat = [r for r in pool.imap(_fold_and_check, list(zip(pick["sequence"], pick["family"])), chunksize=256) if r]
    info["natural_sampled"] = pick.height
    info["natural_with_4plus_pairs"] = len(nat)
    info["natural_excluded_similar"] = sum(r[3] for r in nat)
    nat = [r for r in nat if not r[3]]
    val_family = lambda f: int(hashlib.sha256(f.encode()).hexdigest(), 16) % 50 == 0      # ~2 % of families
    natural = pl.DataFrame({"sequence": [r[0] for r in nat], "structure": [r[1] for r in nat],
                            "key": [r[2] for r in nat], "source": ["natural"] * len(nat)})
    natural = natural.with_columns(pl.col("key").map_elements(val_family, return_dtype=pl.Boolean).alias("val"))
    natural.filter(~pl.col("val")).drop("val").write_parquet(OUT / "natural_train.parquet")
    natural.filter(pl.col("val")).drop("val").write_parquet(OUT / "natural_val.parquet")
    info["natural_train"] = natural.filter(~pl.col("val")).height
    info["natural_val"] = natural.filter(pl.col("val")).height
    info["natural_seconds"] = time.time() - t0

    pool_manifest = load_manifest(MANIFESTS_DIR / "eternaweb_trainpool_v1.json")
    split = {t["id"]: t["subset"] for t in pool_manifest["targets"]}
    structure = {t["id"]: t["structure"] for t in pool_manifest["targets"]}
    tr = pl.read_parquet(PILOT_DIR / "trainpool_samfeo_v1" / "units" / "samfeo" / "*.parquet",
                         columns=["target_id", "sequence", "umfe"]).filter(pl.col("umfe")).unique(["target_id", "sequence"])
    rows = []
    for (tid,), g in tr.sort(["target_id", "sequence"]).group_by(["target_id"], maintain_order=True):
        seqs = g["sequence"].to_list()
        keep = [seqs[k] for k in sorted(rng.choice(len(seqs), size=min(args.per_puzzle, len(seqs)), replace=False))]
        rows += [(s, structure[tid], tid) for s in keep]
    with get_context("spawn").Pool(args.workers, initializer=_init, initargs=(excl,)) as pool:
        des = list(pool.imap(_check, rows, chunksize=64))
    info["design_candidates"] = len(des)
    info["design_excluded_similar"] = sum(r[3] for r in des)
    design = pl.DataFrame({"sequence": [r[0] for r in des if not r[3]], "structure": [r[1] for r in des if not r[3]],
                           "key": [r[2] for r in des if not r[3]]}).with_columns(pl.lit("design").alias("source"))
    design = design.with_columns(pl.col("key").replace_strict(split).alias("split"))
    design.filter(pl.col("split") == "train").drop("split").write_parquet(OUT / "design_train.parquet")
    design.filter(pl.col("split") == "train_holdout").drop("split").write_parquet(OUT / "design_val.parquet")
    info["design_train"] = design.filter(pl.col("split") == "train").height
    info["design_val"] = design.filter(pl.col("split") == "train_holdout").height
    info["design_puzzles_train"] = design.filter(pl.col("split") == "train")["key"].n_unique()
    info["design_puzzles_val"] = design.filter(pl.col("split") == "train_holdout")["key"].n_unique()
    info["seconds"] = time.time() - t0
    (OUT / "info.json").write_text(json.dumps(info, indent=1))
    print(json.dumps(info, indent=1))


if __name__ == "__main__":
    main()
