"""Fine-tune the target-conditioned denoiser (docs/experiments/2026-09-28-target-conditioned-denoiser.md).

  python scripts/tcd_train.py --steps 8000 --out checkpoints/tcd_v1

Starts from checkpoints/tf_M_do0/best.pt (EMA) with zero-initialised adapters, so step 0 IS the
unconditional model. Batches mix natural (Rfam train, MFE structures) and design (training-pool
uMFE designs) pairs. Validation reports conditioned NELBO (bits/nt) on held-out design puzzles and
held-out natural families, next to the unconditional base model's NELBO on the same data.
The best checkpoint by design-validation NELBO is kept. One GPU job.
"""

import argparse
import json
import math
import time

import numpy as np
import polars as pl
import torch

from ribomamba.data.tokenizer import BOS_ID, EOS_ID, PAD_ID, encode
from ribomamba.models.checkpoint import load_model
from ribomamba.models.conditioned import ConditionedDenoiser, conditioned_nelbo, structure_inputs
from ribomamba.paths import DATA_DIR, REPO_ROOT

DATA = DATA_DIR / "tcd_v1"
BASE = REPO_ROOT / "checkpoints" / "tf_M_do0" / "best.pt"


def batch_tensors(seqs: list[str], structs: list[str], device):
    W = max(map(len, seqs)) + 2
    ids = torch.full((len(seqs), W), PAD_ID, dtype=torch.long)
    mask = torch.zeros((len(seqs), W), dtype=torch.bool)
    for k, s in enumerate(seqs):
        ids[k, :len(s) + 2] = torch.tensor([BOS_ID, *encode(s).tolist(), EOS_ID])
        mask[k, :len(s) + 2] = True
    bracket, partner = structure_inputs(structs, W, device)
    return ids.to(device), mask.to(device), bracket, partner


@torch.no_grad()
def evaluate(model, frame: pl.DataFrame, device, n: int, seed: int, conditioned: bool = True) -> float:
    """Mean NELBO in bits/nt over up to n sequences, with a fixed masking generator (comparable across calls)."""
    model.eval()
    rows = frame.sample(n=min(n, frame.height), seed=seed)
    gen = torch.Generator(device=device).manual_seed(seed)
    total, count = 0.0, 0
    for i in range(0, rows.height, 64):
        chunk = rows[i:i + 64]
        ids, mask, bracket, partner = batch_tensors(chunk["sequence"].to_list(), chunk["structure"].to_list(), device)
        if not conditioned:
            partner = torch.full_like(partner, -1)
            bracket = torch.full_like(bracket, 3)
        with torch.autocast("cuda", dtype=torch.bfloat16, enabled=device == "cuda"):
            loss, _ = conditioned_nelbo(model, ids, mask, bracket, partner, gen)
        n_nt = int(mask.sum() - 2 * len(chunk))
        total += loss.item() * n_nt
        count += n_nt
    model.train()
    return total / count / math.log(2)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--steps", type=int, default=8000)
    p.add_argument("--batch", type=int, default=64)
    p.add_argument("--design-fraction", type=float, default=0.5)
    p.add_argument("--lr-base", type=float, default=1e-4)
    p.add_argument("--lr-adapter", type=float, default=1e-3)
    p.add_argument("--eval-every", type=int, default=1000)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--out", default="checkpoints/tcd_v1")
    args = p.parse_args()
    torch.manual_seed(args.seed)
    device = "cuda"
    base, _ = load_model(BASE, weights="ema", device="cpu")
    model = ConditionedDenoiser.from_unconditional(base).to(device)
    reference = ConditionedDenoiser.from_unconditional(base).to(device)      # adapters stay zero: the base model
    nat_tr, des_tr = pl.read_parquet(DATA / "natural_train.parquet"), pl.read_parquet(DATA / "design_train.parquet")
    nat_va, des_va = pl.read_parquet(DATA / "natural_val.parquet"), pl.read_parquet(DATA / "design_val.parquet")
    adapter_ids = {id(q) for q in model.adapter_parameters()}
    groups = [{"params": [q for q in model.parameters() if id(q) not in adapter_ids], "lr": args.lr_base},
              {"params": model.adapter_parameters(), "lr": args.lr_adapter}]
    opt = torch.optim.AdamW(groups, weight_decay=0.01, betas=(0.9, 0.98))
    sched = torch.optim.lr_scheduler.OneCycleLR(opt, max_lr=[args.lr_base, args.lr_adapter], total_steps=args.steps,
                                                pct_start=0.05)
    rng = np.random.default_rng(args.seed)
    n_des = int(round(args.batch * args.design_fraction))
    nat_seq, nat_st = nat_tr["sequence"].to_list(), nat_tr["structure"].to_list()
    des_seq, des_st = des_tr["sequence"].to_list(), des_tr["structure"].to_list()
    out = REPO_ROOT / args.out
    out.mkdir(parents=True, exist_ok=True)
    ref = {"design_val_bits_uncond_base": evaluate(reference, des_va, device, 4000, 1, conditioned=False),
           "natural_val_bits_uncond_base": evaluate(reference, nat_va, device, 4000, 2, conditioned=False)}
    print(json.dumps(ref), flush=True)
    log, best = [], None
    torch.cuda.reset_peak_memory_stats()
    t0 = time.time()
    for step in range(1, args.steps + 1):
        di = rng.integers(len(des_seq), size=n_des)
        ni = rng.integers(len(nat_seq), size=args.batch - n_des)
        seqs = [des_seq[k] for k in di] + [nat_seq[k] for k in ni]
        structs = [des_st[k] for k in di] + [nat_st[k] for k in ni]
        ids, mask, bracket, partner = batch_tensors(seqs, structs, device)
        with torch.autocast("cuda", dtype=torch.bfloat16):
            loss, _ = conditioned_nelbo(model, ids, mask, bracket, partner)
        opt.zero_grad(set_to_none=True)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        opt.step()
        sched.step()
        if step % args.eval_every == 0 or step == args.steps:
            entry = {"step": step, "train_bits": loss.item() / math.log(2),
                     "design_val_bits": evaluate(model, des_va, device, 4000, 1),
                     "natural_val_bits": evaluate(model, nat_va, device, 4000, 2),
                     "elapsed_s": time.time() - t0}
            log.append(entry)
            print(json.dumps(entry), flush=True)
            if best is None or entry["design_val_bits"] < best:
                best = entry["design_val_bits"]
                torch.save({"state": model.state_dict(), "config": base.cfg.__dict__, "step": step,
                            "base": str(BASE.relative_to(REPO_ROOT)), "args": vars(args)}, out / "tcd.pt")
    info = {"args": vars(args), "reference": ref, "log": log, "best_design_val_bits": best,
            "train_s": time.time() - t0, "peak_gpu_mib": torch.cuda.max_memory_allocated() / 2**20,
            "n_params": sum(q.numel() for q in model.parameters()),
            "n_adapter_params": sum(q.numel() for q in model.adapter_parameters()),
            "data": json.loads((DATA / "info.json").read_text())}
    (out / "train_log.json").write_text(json.dumps(info, indent=1))
    print(json.dumps({k: v for k, v in info.items() if k not in ("log", "data")}, indent=1))


if __name__ == "__main__":
    main()
