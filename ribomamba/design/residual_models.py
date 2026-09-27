"""Scoring rules and small models for the competition-residual experiment (offline part).

Every scorer returns, per child, a number whose ORDER within a sibling group is the
predicted order of y = Delta ln P (equivalently of a + c). Controls and models:

  energy       a                                   (target-energy screening)
  bank         a + c_bank                          (rival-bank physics, no learning)
  linear       a + ridge(features) -> c            (CPU)
  mlp          a + MLP(features) -> c              (CPU/GPU, tiny)
  critic_v1    existing generic critic's Delta log10 P (baseline)

Metrics per group: Spearman(score, y), top-1 regret in ln P, whether top-1 is the true
best, and best-of-8 regret over random 8-subsets (the online filter's task).
"""

import math

import numpy as np
import polars as pl

from ribomamba.design.scoring import KT

FEATURES = ["a", "c_bank_filled", "bank_missing", "c_lin", "broken_weight", "n_changed", "n_pair_changes",
            "n_unpaired_changes", "d_gc", "defect_changed", "parent_logit", "log_length"]


def load_siblings(path) -> pl.DataFrame:
    return pl.read_parquet(path)


def child_features(structure: str, parent: str, child: str, parent_defect, parent_ln_p: float, a: float,
                   parent_rival_energy, rival_energy) -> dict:
    """The scalar features of one child; shared by offline fitting and the online filter."""
    pr = np.asarray(parent_rival_energy, dtype=float)
    cr = np.asarray(rival_energy, dtype=float)
    if len(pr):
        w = np.exp(-(pr - pr.min()) / KT)
        w /= w.sum()
        ok = np.isfinite(cr)
        # First-order Delta ln Z_rest = -sum w dE / RT, so c = -Delta ln Z_rest ~ +sum w dE / RT.
        c_lin = float((w[ok] * (cr[ok] - pr[ok])).sum() / KT) if ok.any() else 0.0
        broken = float(w[~ok].sum())
        rest_c = -cr[ok] / KT
        rest_p = -pr / KT
        c_bank = (-(np.logaddexp.reduce(rest_c) - np.logaddexp.reduce(rest_p))) if ok.any() else math.nan
    else:
        c_lin, broken, c_bank = 0.0, 0.0, math.nan
    changed = [i for i, (x, z) in enumerate(zip(parent, child)) if x != z]
    pairs_changed = sum(1 for i in changed if structure[i] != ".")
    d_gc = sum(child.count(x) for x in "GC") - sum(parent.count(x) for x in "GC")
    defect = np.asarray(parent_defect, dtype=float)
    return {"a": a, "c_bank_filled": float(c_bank) if math.isfinite(c_bank) else 0.0,
            "bank_missing": 0.0 if math.isfinite(c_bank) else 1.0,
            "c_lin": c_lin, "broken_weight": broken, "n_changed": float(len(changed)),
            "n_pair_changes": pairs_changed / 2, "n_unpaired_changes": float(len(changed) - pairs_changed),
            "d_gc": float(d_gc), "defect_changed": float(defect[changed].mean()) if changed else 0.0,
            "parent_logit": parent_ln_p - math.log(-math.expm1(parent_ln_p)) if parent_ln_p < 0 else 30.0,
            "log_length": math.log(len(structure))}


def add_features(df: pl.DataFrame) -> pl.DataFrame:
    """Scalar features from stored sibling data; no oracle calls beyond those already counted."""
    rows = [child_features(r["structure"], r["parent"], r["child"], r["parent_defect"], r["parent_ln_p"], r["a"],
                           r["parent_rival_energy"], r["rival_energy"]) for r in df.iter_rows(named=True)]
    cols = [k for k in rows[0] if k != "a"]
    return df.with_columns([pl.Series(k, [x[k] for x in rows]) for k in cols])


def spearman(x: np.ndarray, y: np.ndarray) -> float:
    if len(x) < 3:
        return math.nan
    rx, ry = x.argsort().argsort(), y.argsort().argsort()
    if rx.std() == 0 or ry.std() == 0:
        return math.nan
    return float(np.corrcoef(rx, ry)[0, 1])


def group_metrics(df: pl.DataFrame, score_col: str, k_subset: int = 8, n_subsets: int = 20, seed: int = 0) -> pl.DataFrame:
    """One row per sibling group: Spearman, top-1 regret, top-1 is best, best-of-k regret (averaged)."""
    rng = np.random.default_rng(seed)
    out = []
    for (group, puzzle), g in df.group_by(["group", "puzzle"], maintain_order=True):
        y, s = g["y"].to_numpy(), g[score_col].to_numpy()
        if len(y) < 2:
            continue
        top = int(np.argmax(s))
        sub = []
        for _ in range(n_subsets):
            idx = rng.choice(len(y), size=min(k_subset, len(y)), replace=False)
            sub.append(y[idx].max() - y[idx][int(np.argmax(s[idx]))])
        out.append({"group": group, "puzzle": puzzle, "phase": g["phase"][0], "n": len(y),
                    "spearman": spearman(s, y), "regret": float(y.max() - y[top]),
                    "top1_best": float(y[top] == y.max()), "regret_k": float(np.mean(sub))})
    return pl.DataFrame(out)


def puzzle_bootstrap(values_by_puzzle: dict[str, float], n_boot: int = 5000, seed: int = 0) -> tuple[float, float, float]:
    keys = sorted(values_by_puzzle)
    x = np.array([values_by_puzzle[k] for k in keys])
    rng = np.random.default_rng(seed)
    idx = rng.integers(len(x), size=(n_boot, len(x)))
    reps = x[idx].mean(1)
    return float(x.mean()), float(np.percentile(reps, 2.5)), float(np.percentile(reps, 97.5))


def fit_ridge(X: np.ndarray, t: np.ndarray, lam: float = 1.0) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    mu, sd = X.mean(0), X.std(0) + 1e-9
    Z = np.c_[np.ones(len(X)), (X - mu) / sd]
    A = Z.T @ Z + lam * np.diag([0.0] + [1.0] * X.shape[1])
    w = np.linalg.solve(A, Z.T @ t)
    return w, mu, sd


def predict_ridge(model, X: np.ndarray) -> np.ndarray:
    w, mu, sd = model
    return np.c_[np.ones(len(X)), (X - mu) / sd] @ w


def fit_mlp(X: np.ndarray, t: np.ndarray, Xv: np.ndarray, tv: np.ndarray, epochs: int = 30, seed: int = 0,
            hidden: int = 64):
    import torch
    torch.manual_seed(seed)
    mu, sd = X.mean(0), X.std(0) + 1e-9
    xt = torch.tensor((X - mu) / sd, dtype=torch.float32)
    tt = torch.tensor(t, dtype=torch.float32)
    xv = torch.tensor((Xv - mu) / sd, dtype=torch.float32)
    tv_ = torch.tensor(tv, dtype=torch.float32)
    net = torch.nn.Sequential(torch.nn.Linear(X.shape[1], hidden), torch.nn.GELU(), torch.nn.Linear(hidden, hidden),
                              torch.nn.GELU(), torch.nn.Linear(hidden, 1))
    opt = torch.optim.AdamW(net.parameters(), lr=2e-3, weight_decay=1e-4)
    best, best_state, log = math.inf, None, []
    for epoch in range(epochs):
        perm = torch.randperm(len(xt))
        net.train()
        for i in range(0, len(xt), 1024):
            b = perm[i:i + 1024]
            loss = torch.nn.functional.huber_loss(net(xt[b]).squeeze(-1), tt[b])
            opt.zero_grad()
            loss.backward()
            opt.step()
        net.eval()
        with torch.no_grad():
            v = torch.nn.functional.huber_loss(net(xv).squeeze(-1), tv_).item()
        log.append(v)
        if v < best:
            best, best_state = v, {k: x.clone() for k, x in net.state_dict().items()}
    net.load_state_dict(best_state)
    return (net, mu, sd), log


def predict_mlp(model, X: np.ndarray) -> np.ndarray:
    import torch
    net, mu, sd = model
    with torch.no_grad():
        return net(torch.tensor((X - mu) / sd, dtype=torch.float32)).squeeze(-1).numpy()
