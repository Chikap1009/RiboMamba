"""Stage C candidate (docs/experiments/2026-09-27-stageC-repair-critic.md): data, training, offline check.

  python scripts/repair_critic.py pool                 # manifests/eternaweb_trainpool_v1.json
  python scripts/repair_pilot.py run --run trainpool_samfeo_v1 --manifest eternaweb_trainpool_v1 \\
      --subset all --budget 512 --seeds 0 --methods samfeo --workers 4
  python scripts/repair_critic.py data --run trainpool_samfeo_v1     # transitions + parent defects
  python scripts/repair_critic.py train --out checkpoints/critic_v1  # GPU, held-out puzzles for selection
  python scripts/repair_critic.py offline --ckpt checkpoints/critic_v1/critic.pt

Only TRAINING-pool puzzles are read here. Development and confirmation targets are
used solely by repair_pilot.py to evaluate a frozen critic.
"""

import argparse
import json
import math
import os
import sys
import time
from multiprocessing import get_context

import numpy as np
import polars as pl

from ribomamba.design import training_pool as tp
from ribomamba.design.manifest import load_manifest, write_manifest
from ribomamba.design.runner import atomic_write_json
from ribomamba.paths import PILOT_DIR, REPO_ROOT

DATA_DIR = PILOT_DIR / "critic_data"


def cmd_pool(args) -> None:
    manifest = tp.build(workers=args.workers)
    print(json.dumps({"outcome": write_manifest(manifest, tp.PATH), "sha": manifest["content_sha256"],
                      "funnel": manifest["funnel"]}, indent=1))


def _defect(item):
    from ribomamba.design.scoring import score
    structure, parent = item
    s = score(parent, structure)
    return parent, structure, s.defect.astype(np.float32).tolist()


def cmd_data(args) -> None:
    from ribomamba.design.critic import transitions_from_traces
    from ribomamba.design.summary import load_run
    pool = load_manifest(tp.PATH)
    split = {t["id"]: t["subset"] for t in pool["targets"]}
    structure = {t["id"]: t["structure"] for t in pool["targets"]}
    config, statuses, traces = load_run(PILOT_DIR / args.run)
    if config["manifest"]["content_sha256"] != pool["content_sha256"]:
        raise SystemExit("run was not made on the training pool manifest")
    tr = transitions_from_traces(traces)
    tr = tr.with_columns(pl.col("target_id").replace_strict(split).alias("split"),
                         pl.col("target_id").replace_strict(structure).alias("structure"))
    pairs = sorted(set(zip(tr["structure"].to_list(), tr["parent"].to_list())))
    t0 = time.time()
    with get_context("spawn").Pool(args.workers) as p:
        defects = {(st, par): d for par, st, d in p.map(_defect, pairs, chunksize=32)}
    tr = tr.with_columns(pl.Series("defect", [defects[(st, par)] for st, par in
                                              zip(tr["structure"].to_list(), tr["parent"].to_list())]))
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    out = DATA_DIR / f"{args.run}.parquet"
    tr.write_parquet(out)
    info = {"run": args.run, "rows": tr.height, "distinct_parents": len(pairs), "defect_seconds": time.time() - t0,
            "improved_rate": float(tr["improved"].mean()), "by_split": dict(tr.group_by("split").len().rows())}
    atomic_write_json(DATA_DIR / f"{args.run}.json", info)
    print(json.dumps(info, indent=1))


def _examples(frame: pl.DataFrame):
    from ribomamba.design.critic import encode_example
    from ribomamba.eval.folding import pair_table
    cache = {}
    out = []
    for r in frame.iter_rows(named=True):
        pt = cache.setdefault(r["structure"], pair_table(r["structure"]))
        e = encode_example(r["structure"], r["parent"], r["child"], np.asarray(r["defect"]), r["delta_e"], pt)
        e["delta"], e["improved"] = np.float32(r["delta"]), np.float32(r["improved"])
        out.append(e)
    return out


def _predict(model, examples, device, batch_size=512):
    import torch

    from ribomamba.design.critic import collate
    preds = []
    model.eval()
    with torch.no_grad():
        for i in range(0, len(examples), batch_size):
            batch = collate(examples[i:i + batch_size], device)
            with torch.autocast("cuda", dtype=torch.bfloat16, enabled=device == "cuda"):
                preds.append(model(batch).float()[:, 0].cpu().numpy())
    return np.concatenate(preds)


def group_choice_metrics(frame: pl.DataFrame, score: np.ndarray, seed: int = 0) -> dict:
    """Among children of the same parent (>= 2), pick the top-scored; report the chosen child's mean
    true Delta log10 P and improvement rate, versus lowest Delta E and a uniformly random pick."""
    df = frame.with_columns(pl.Series("score", score), pl.int_range(pl.len()).alias("row"))
    groups = [g for _, g in df.group_by(["target_id", "seed", "parent"]) if g.height >= 2]
    rng = np.random.default_rng(seed)
    res = {"critic": [], "energy": [], "random": [], "oracle": []}
    for g in groups:
        res["critic"].append(g.row(int(np.argmax(g["score"].to_numpy())), named=True))
        res["energy"].append(g.row(int(np.argmin(g["delta_e"].to_numpy())), named=True))
        res["random"].append(g.row(int(rng.integers(g.height)), named=True))
        res["oracle"].append(g.row(int(np.argmax(g["delta"].to_numpy())), named=True))
    return {"groups": len(groups), **{k: {"mean_delta": float(np.mean([r["delta"] for r in v])),
                                         "improved_rate": float(np.mean([r["improved"] for r in v]))}
                                      for k, v in res.items()}}


def cmd_train(args) -> None:
    import torch

    from ribomamba.design.critic import Critic, CriticConfig, collate, loss_fn
    torch.manual_seed(args.seed)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    frame = pl.read_parquet(DATA_DIR / f"{args.data}.parquet")
    train_f, hold_f = frame.filter(pl.col("split") == "train"), frame.filter(pl.col("split") == "train_holdout")
    train, hold = _examples(train_f), _examples(hold_f)
    cfg = CriticConfig()
    model = Critic(cfg).to(device)
    n_params = sum(p.numel() for p in model.parameters())
    opt = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=0.01)
    steps_per_epoch = math.ceil(len(train) / args.batch)
    total = steps_per_epoch * args.epochs
    sched = torch.optim.lr_scheduler.OneCycleLR(opt, max_lr=args.lr, total_steps=total, pct_start=0.05)
    rng = np.random.default_rng(args.seed)
    log, best, t0 = [], None, time.time()
    os.makedirs(args.out, exist_ok=True)
    for epoch in range(args.epochs):
        model.train()
        order = rng.permutation(len(train))
        losses = []
        for i in range(steps_per_epoch):
            batch_ex = [train[k] for k in order[i * args.batch:(i + 1) * args.batch]]
            batch = collate(batch_ex, device)
            delta = torch.tensor([e["delta"] for e in batch_ex], device=device)
            improved = torch.tensor([e["improved"] for e in batch_ex], device=device)
            with torch.autocast("cuda", dtype=torch.bfloat16, enabled=device == "cuda"):
                out = model(batch).float()
            loss = loss_fn(out, delta, improved)
            opt.zero_grad(set_to_none=True)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            opt.step()
            sched.step()
            losses.append(loss.item())
        pred = _predict(model, hold, device)
        metrics = group_choice_metrics(hold_f, pred)
        spearman = float(pl.DataFrame({"a": pred, "b": hold_f["delta"]}).select(
            pl.corr("a", "b", method="spearman")).item())
        entry = {"epoch": epoch, "train_loss": float(np.mean(losses)), "holdout_spearman": spearman,
                 "holdout_choice": metrics, "elapsed_s": time.time() - t0}
        log.append(entry)
        print(json.dumps({k: entry[k] for k in ("epoch", "train_loss", "holdout_spearman", "elapsed_s")}),
              json.dumps({k: v for k, v in metrics.items() if k != "groups"}), flush=True)
        score = metrics["critic"]["mean_delta"]
        if best is None or score > best:
            best = score
            torch.save({"model": model.state_dict(), "config": cfg.__dict__, "epoch": epoch, "data": args.data,
                        "n_params": n_params, "holdout": entry}, os.path.join(args.out, "critic.pt"))
    atomic_write_json(REPO_ROOT / args.out / "train_log.json",
                      {"args": vars(args), "n_params": n_params, "n_train": len(train), "n_holdout": len(hold),
                       "device": device, "log": log, "best_holdout_mean_delta": best})


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="command", required=True)
    a = sub.add_parser("pool")
    a.add_argument("--workers", type=int, default=4)
    d = sub.add_parser("data")
    d.add_argument("--run", required=True)
    d.add_argument("--workers", type=int, default=4)
    t = sub.add_parser("train")
    t.add_argument("--data", required=True)
    t.add_argument("--out", default="checkpoints/critic_v1")
    t.add_argument("--epochs", type=int, default=6)
    t.add_argument("--batch", type=int, default=256)
    t.add_argument("--lr", type=float, default=1e-3)
    t.add_argument("--seed", type=int, default=0)
    args = p.parse_args()
    {"pool": cmd_pool, "data": cmd_data, "train": cmd_train}[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
