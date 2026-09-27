"""Competition-residual experiment (docs/experiments/2026-09-27-competition-residual.md).

  python scripts/repair_residual.py collect --workers 12      # sibling groups on the TRAINING pool
  python scripts/repair_residual.py diagnose                  # do rival banks explain the residual?
  python scripts/repair_residual.py offline                   # held-out ranking/regret of every scorer

Only training-pool puzzles (manifests/eternaweb_trainpool_v1.json) are read here.
Output: data/repair_pilot/residual_siblings_v1/<puzzle>.parquet (one row per child),
written atomically per puzzle; rerunning skips finished puzzles.
"""

import argparse
import math
import json
import sys
import time
from multiprocessing import get_context

import numpy as np
import polars as pl

from ribomamba.design import training_pool as tp
from ribomamba.design.manifest import load_manifest
from ribomamba.design.search import rng_for
from ribomamba.paths import PILOT_DIR, REPO_ROOT as REPO

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


def load_all() -> pl.DataFrame:
    from ribomamba.design.residual_models import add_features
    files = sorted(OUT.glob("eternaweb_*.parquet"))           # sibling files only (not score tables)
    df = pl.concat([pl.read_parquet(f) for f in files], how="vertical")
    return add_features(df)


def cmd_diagnose(args) -> None:
    """Do rival banks explain the competition term c, and the pairs energy ranks wrongly?"""
    df = load_all()
    groups = df["group"].n_unique()
    out = {"children": df.height, "groups": groups, "puzzles": df["puzzle"].n_unique(),
           "by_split": dict(df.group_by("split").len().rows())}
    bank_ok = df.filter(pl.col("bank_missing") == 0)
    out["share_children_without_compatible_rival"] = 1 - bank_ok.height / df.height
    c, cb = bank_ok["c"].to_numpy(), bank_ok["c_bank"].to_numpy()
    a = bank_ok["a"].to_numpy()
    out["corr_c_cbank"] = float(np.corrcoef(c, cb)[0, 1])
    out["r2_c_by_cbank_fit"] = float(np.corrcoef(c, cb)[0, 1] ** 2)
    out["corr_a_c"] = float(np.corrcoef(a, c)[0, 1])
    out["corr_c_clin"] = float(np.corrcoef(c, bank_ok["c_lin"].to_numpy())[0, 1])
    # Pairs of siblings that energy ranks wrongly: how many does the rival bank put right?
    wrong = fixed = 0
    agree = {"a": [0, 0], "a+c_bank": [0, 0], "a+c_lin": [0, 0]}
    by_phase = {}
    for (_, phase), g in df.group_by(["group", "phase"]):
        y, aa, cc = g["y"].to_numpy(), g["a"].to_numpy(), g["c_bank_filled"].to_numpy()
        cl = g["c_lin"].to_numpy()
        i, j = np.triu_indices(len(y), 1)
        keep = (y[i] - y[j]) != 0
        for name, sc in (("a", aa), ("a+c_bank", aa + cc), ("a+c_lin", aa + cl)):
            agree[name][0] += int((np.sign(sc[i] - sc[j]) == np.sign(y[i] - y[j]))[keep].sum())
            agree[name][1] += int(keep.sum())
        dy, da, db = y[i] - y[j], aa[i] - aa[j], (aa + cc)[i] - (aa + cc)[j]
        w = (np.sign(da) != np.sign(dy)) & (dy != 0)
        wrong += int(w.sum())
        fixed += int((np.sign(db[w]) == np.sign(dy[w])).sum())
        ph = by_phase.setdefault(phase, [0, 0])
        ph[0] += int(w.sum())
        ph[1] += int((np.sign(db[w]) == np.sign(dy[w])).sum())
    out["pairwise_order_accuracy"] = {k: v[0] / max(v[1], 1) for k, v in agree.items()}
    out["energy_misordered_pairs"] = wrong
    out["share_fixed_by_rival_bank"] = fixed / max(wrong, 1)
    out["share_fixed_by_phase"] = {k: v[1] / max(v[0], 1) for k, v in by_phase.items()}
    print(json.dumps(out, indent=1))
    (OUT / "diagnose.json").write_text(json.dumps(out, indent=1))


def cmd_offline(args) -> None:
    import torch

    from ribomamba.design import residual_models as rm
    df = load_all()
    fit, val, hold = splits(df)
    X = lambda d, cols: d.select(cols).to_numpy().astype(float)
    no_rival = [f for f in rm.FEATURES if f not in ("c_bank_filled", "bank_missing", "c_lin", "broken_weight")]
    scores = {"energy": hold["a"].to_numpy(), "bank": (hold["a"] + hold["c_bank_filled"]).to_numpy(),
              "oracle": hold["y"].to_numpy()}
    timing = {}
    model_dir = REPO / "checkpoints" / "residual_v1"
    model_dir.mkdir(parents=True, exist_ok=True)
    for name, cols in (("linear_rivals", rm.FEATURES), ("linear_no_rivals", no_rival)):
        t0 = time.perf_counter()
        model = rm.fit_ridge(X(fit, cols), fit["c"].to_numpy(), lam=1.0)
        timing[f"{name}_fit_s"] = time.perf_counter() - t0
        scores[name] = hold["a"].to_numpy() + rm.predict_ridge(model, X(hold, cols))
        w, mu, sd = model
        (model_dir / f"{name}.json").write_text(json.dumps({"kind": "ridge", "features": cols, "w": w.tolist(),
                                                            "mu": mu.tolist(), "sd": sd.tolist(), "target": "c"}))
    for name, cols in (("mlp_rivals", rm.FEATURES), ("mlp_no_rivals", no_rival)):
        t0 = time.perf_counter()
        model, log = rm.fit_mlp(X(fit, cols), fit["c"].to_numpy(), X(val, cols), val["c"].to_numpy())
        timing[f"{name}_fit_s"] = time.perf_counter() - t0
        net, mu, sd = model
        torch.save({"kind": "mlp", "features": cols, "state": net.state_dict(), "mu": mu, "sd": sd, "hidden": 64,
                    "val_huber_log": log, "target": "c"}, model_dir / f"{name}.pt")
        t1 = time.perf_counter()
        scores[name] = hold["a"].to_numpy() + rm.predict_mlp(model, X(hold, cols))
        timing[f"{name}_predict_us_per_child"] = (time.perf_counter() - t1) / hold.height * 1e6
    # Existing generic critic (predicts Delta log10 P; order is what matters).
    from ribomamba.design.critic import CriticScorer, collate, encode_example
    from ribomamba.eval.folding import pair_table
    critic = CriticScorer(REPO / "checkpoints" / "critic_v1" / "critic.pt")
    preds, t1 = [], time.perf_counter()
    rows = hold.select("structure", "parent", "child", "parent_defect", "target_energy",
                       "parent_target_energy").iter_rows(named=True)
    cache, batch = {}, []
    for r in rows:
        pt = cache.setdefault(r["structure"], pair_table(r["structure"]))
        batch.append(encode_example(r["structure"], r["parent"], r["child"], np.asarray(r["parent_defect"]),
                                    r["target_energy"] - r["parent_target_energy"], pt))
        if len(batch) == 512:
            with torch.no_grad():
                preds.append(critic.model(collate(batch, critic.device)).float()[:, 0].cpu().numpy())
            batch = []
    if batch:
        with torch.no_grad():
            preds.append(critic.model(collate(batch, critic.device)).float()[:, 0].cpu().numpy())
    scores["critic_v1"] = np.concatenate(preds)
    timing["critic_v1_predict_us_per_child"] = (time.perf_counter() - t1) / hold.height * 1e6
    hold.select("puzzle", "group", "phase", "child", "y", "a", "c").with_columns(
        [pl.Series(f"score_{k}", v) for k, v in scores.items()]).write_parquet(OUT / "holdout_scores.parquet")
    results, per_group = {}, {}
    for name, s in scores.items():
        g = rm.group_metrics(hold.with_columns(pl.Series("score", s)), "score")
        per_group[name] = g
        by_p = g.group_by("puzzle").agg(pl.col("regret_k").mean())
        mean, lo, hi = rm.puzzle_bootstrap(dict(by_p.rows()))
        results[name] = {"spearman_median": float(g["spearman"].drop_nans().median()),
                         "regret_mean": float(g["regret"].mean()), "regret_median": float(g["regret"].median()),
                         "share_regret_gt_ln2": float((g["regret"] > math.log(2)).mean()),
                         "top1_best": float(g["top1_best"].mean()),
                         "best_of_8_regret": {"mean": mean, "low": lo, "high": hi},
                         "best_of_8_regret_by_phase": {p: float(v) for p, v in g.group_by("phase").agg(
                             pl.col("regret_k").mean()).rows()}}
    diffs = {}
    for a_, b_ in (("bank", "energy"), ("linear_rivals", "energy"), ("linear_rivals", "linear_no_rivals"),
                   ("mlp_rivals", "mlp_no_rivals"), ("mlp_rivals", "energy"), ("mlp_rivals", "critic_v1"),
                   ("linear_rivals", "critic_v1"), ("critic_v1", "energy")):
        ga = per_group[a_].group_by("puzzle").agg(pl.col("regret_k").mean())
        gb = per_group[b_].group_by("puzzle").agg(pl.col("regret_k").mean())
        j = ga.join(gb, on="puzzle", suffix="_b")
        diffs[f"{a_} - {b_}"] = rm.puzzle_bootstrap(dict(zip(j["puzzle"], (j["regret_k"] - j["regret_k_b"]).to_list())))
    report = {"train_children": fit.height, "val_children": val.height, "holdout_children": hold.height,
              "holdout_groups": hold["group"].n_unique(), "holdout_puzzles": hold["puzzle"].n_unique(),
              "results": results, "best_of_8_regret_differences (a - b, lower is better)": diffs, "timing": timing}
    (OUT / "offline.json").write_text(json.dumps(report, indent=1))
    print(json.dumps(report, indent=1))


def splits(df: pl.DataFrame):
    """The fixed puzzle-level split: fit / val (10 % of train puzzles, seed 0) / held-out."""
    train = df.filter(pl.col("split") == "train")
    hold = df.filter(pl.col("split") == "train_holdout")
    puzzles = sorted(train["puzzle"].unique().to_list())
    val_puzzles = set(np.random.default_rng(0).choice(puzzles, size=len(puzzles) // 10, replace=False).tolist())
    fit = train.filter(~pl.col("puzzle").is_in(list(val_puzzles)))
    val = train.filter(pl.col("puzzle").is_in(list(val_puzzles)))
    return fit, val, hold


def cmd_train_critic(args) -> None:
    import torch

    from ribomamba.design import residual_models as rm
    from ribomamba.design.critic import CriticConfig
    from ribomamba.design.residual_critic import SiblingCritic, collate_sibling, encode_sibling
    torch.manual_seed(args.seed)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    fit, val, hold = splits(load_all())
    label = "y" if args.variant == "generic" else "c"
    cache = {}
    enc = lambda d: [encode_sibling(r, args.variant, cache) for r in d.iter_rows(named=True)]
    t0 = time.time()
    fit_x, val_x, hold_x = enc(fit), enc(val), enc(hold)
    fit_t = torch.tensor(fit[label].to_numpy(), dtype=torch.float32)
    encode_s = time.time() - t0
    model = SiblingCritic(CriticConfig(), use_rivals=args.variant == "rival").to(device)
    n_params = sum(p.numel() for p in model.parameters())
    opt = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=0.01)
    steps = (len(fit_x) + args.batch - 1) // args.batch
    sched = torch.optim.lr_scheduler.OneCycleLR(opt, max_lr=args.lr, total_steps=steps * args.epochs, pct_start=0.05)

    def predict(xs):
        model.eval()
        out = []
        with torch.no_grad():
            for i in range(0, len(xs), 512):
                with torch.autocast("cuda", dtype=torch.bfloat16, enabled=device == "cuda"):
                    out.append(model(collate_sibling(xs[i:i + 512], device)).float().cpu().numpy())
        return np.concatenate(out)

    def task_score(d, pred):
        return pred if args.variant == "generic" else d["a"].to_numpy() + pred

    rng = np.random.default_rng(args.seed)
    best, log = None, []
    torch.cuda.reset_peak_memory_stats() if device == "cuda" else None
    train_t0 = time.time()
    for epoch in range(args.epochs):
        model.train()
        order = rng.permutation(len(fit_x))
        losses = []
        for i in range(steps):
            idx = order[i * args.batch:(i + 1) * args.batch]
            batch = collate_sibling([fit_x[k] for k in idx], device)
            with torch.autocast("cuda", dtype=torch.bfloat16, enabled=device == "cuda"):
                out = model(batch).float()
            loss = torch.nn.functional.huber_loss(out, fit_t[idx].to(device))
            opt.zero_grad(set_to_none=True)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            opt.step()
            sched.step()
            losses.append(loss.item())
        vs = task_score(val, predict(val_x))
        vg = rm.group_metrics(val.with_columns(pl.Series("score", vs)), "score")
        entry = {"epoch": epoch, "train_huber": float(np.mean(losses)), "val_best_of_8_regret": float(vg["regret_k"].mean()),
                 "val_spearman": float(vg["spearman"].drop_nans().median()), "elapsed_s": time.time() - train_t0}
        log.append(entry)
        print(json.dumps(entry), flush=True)
        if best is None or entry["val_best_of_8_regret"] < best[0]:
            best = (entry["val_best_of_8_regret"], {k: v.detach().clone() for k, v in model.state_dict().items()}, epoch)
    model.load_state_dict(best[1])
    t1 = time.time()
    hs = task_score(hold, predict(hold_x))
    predict_us = (time.time() - t1) / len(hold_x) * 1e6
    out_dir = REPO / "checkpoints" / "residual_v1"
    out_dir.mkdir(parents=True, exist_ok=True)
    torch.save({"state": model.state_dict(), "variant": args.variant, "config": CriticConfig().__dict__,
                "epoch": best[2], "n_params": n_params, "label": label}, out_dir / f"sibling_{args.variant}.pt")
    scores = pl.read_parquet(OUT / "holdout_scores.parquet")
    assert scores["child"].to_list() == hold["child"].to_list()
    scores.with_columns(pl.Series(f"score_sib_{args.variant}", hs)).write_parquet(OUT / "holdout_scores.parquet")
    info = {"variant": args.variant, "label": label, "n_params": n_params, "fit": len(fit_x), "val": len(val_x),
            "holdout": len(hold_x), "best_epoch": best[2], "encode_s": encode_s, "train_s": time.time() - train_t0,
            "predict_us_per_child": predict_us, "device": device, "log": log,
            "peak_gpu_mib": torch.cuda.max_memory_allocated() / 2**20 if device == "cuda" else None}
    (out_dir / f"sibling_{args.variant}.json").write_text(json.dumps(info, indent=1))
    print(json.dumps({k: v for k, v in info.items() if k != "log"}, indent=1))


def cmd_compare(args) -> None:
    from ribomamba.design import residual_models as rm
    scores = pl.read_parquet(OUT / "holdout_scores.parquet")
    names = [c[len("score_"):] for c in scores.columns if c.startswith("score_")]
    per, table = {}, {}
    for n in names:
        g = rm.group_metrics(scores.with_columns(pl.col(f"score_{n}").alias("score")), "score")
        per[n] = g.group_by("puzzle").agg(pl.col("regret_k").mean())
        m, lo, hi = rm.puzzle_bootstrap(dict(per[n].rows()))
        table[n] = {"best_of_8_regret": [m, lo, hi], "spearman_median": float(g["spearman"].drop_nans().median()),
                    "top1_best": float(g["top1_best"].mean()), "share_regret_gt_ln2": float((g["regret"] > math.log(2)).mean())}
    diffs = {}
    for pair in args.pairs:
        a_, b_ = pair.split(":")
        j = per[a_].join(per[b_], on="puzzle", suffix="_b")
        diffs[pair] = rm.puzzle_bootstrap(dict(zip(j["puzzle"], (j["regret_k"] - j["regret_k_b"]).to_list())))
    out = {"table": table, "differences (a - b; negative = a better)": diffs}
    (OUT / "compare.json").write_text(json.dumps(out, indent=1))
    for n, r in sorted(table.items(), key=lambda kv: kv[1]["best_of_8_regret"][0]):
        b = r["best_of_8_regret"]
        print(f"{n:18s} best-of-8 regret {b[0]:.3f} [{b[1]:.3f}, {b[2]:.3f}]  spearman {r['spearman_median']:.3f}  top1 {r['top1_best']:.3f}")
    for k, v in diffs.items():
        print(f"  {k:40s} {v[0]:+.3f} [{v[1]:+.3f}, {v[2]:+.3f}]")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="command", required=True)
    c = sub.add_parser("collect")
    c.add_argument("--workers", type=int, default=8)
    sub.add_parser("diagnose")
    sub.add_parser("offline")
    t = sub.add_parser("train-critic")
    t.add_argument("--variant", required=True, choices=["generic", "norival", "rival"])
    t.add_argument("--epochs", type=int, default=10)
    t.add_argument("--batch", type=int, default=256)
    t.add_argument("--lr", type=float, default=1e-3)
    t.add_argument("--seed", type=int, default=0)
    c = sub.add_parser("compare")
    c.add_argument("--pairs", nargs="*", default=[])
    args = p.parse_args()
    {"collect": cmd_collect, "diagnose": cmd_diagnose, "offline": cmd_offline, "train-critic": cmd_train_critic,
     "compare": cmd_compare}[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
