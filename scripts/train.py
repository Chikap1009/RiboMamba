"""Train a model on the Rfam training split (Phase 2, D-011; Phase 4 backbones, D-015, D-016).

--arch transformer | bimamba   masked-diffusion denoisers (loss: 1/t-weighted NELBO)
--arch ar_mamba                left-to-right model (loss: exact next-token cross-entropy)
Every run must hold 14,174,976 +- 2 % parameters (frozen protocol P4); --allow-any-size is for debugging.

Usage (inside `conda activate ribomamba`, from the repo root):
    python scripts/train.py --run-name tf_M_lr1e-3 --lr 1e-3 --max-steps 60000
    python scripts/train.py --run-name bimamba_M_x --arch bimamba --n-layers 14 --lr 1e-3 --max-steps 8000
    python scripts/train.py --resume checkpoints/tf_M_lr1e-3/last.pt     # continue after a crash or sleep

Writes checkpoints/<run-name>/ (ignored by Git):
    config.json   every setting, the git commit and the parameter count
    log.csv       one row per log interval (training) and per evaluation (validation)
    last.pt       latest state: weights, EMA weights, optimiser, step, epoch  (for resuming)
    best.pt       the state with the lowest validation bits/nt (EMA weights)

Per step: bf16 autocast forward + the architecture's loss, backward, gradient
clipping, AdamW with warmup + cosine learning rate, EMA update.
"""

import argparse
import copy
import csv
import json
import math
import subprocess
import time

import numpy as np
import torch

from ribomamba.data.dataset import make_dataloader
from ribomamba.data.tokenizer import is_nucleotide
from ribomamba.models.build import ARCHS, build_model, check_parameter_budget, objective
from ribomamba.models.transformer import count_parameters
from ribomamba.paths import REPO_ROOT


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--run-name")
    p.add_argument("--resume", help="path to a last.pt to continue from (all other settings come from it)")
    # model (D-010, D-011; Phase 4: D-015, D-016)
    p.add_argument("--arch", choices=ARCHS, default="transformer")
    p.add_argument("--d-model", type=int, default=384)
    p.add_argument("--n-layers", type=int, default=8)
    p.add_argument("--n-heads", type=int, default=6, help="Transformer only")
    p.add_argument("--d-state", type=int, default=128, help="Mamba only: state numbers per channel")
    p.add_argument("--expand", type=int, default=2, help="Mamba only: channels inside the mixer = expand x d")
    p.add_argument("--headdim", type=int, default=64, help="Mamba only: channels per head")
    p.add_argument("--dropout", type=float, default=0.0, help="D-012: dropout rate during training")
    p.add_argument("--allow-any-size", action="store_true", help="skip the +-2 %% parameter check (debug runs)")
    # optimisation (D-011)
    p.add_argument("--lr", type=float, default=1e-3, help="peak learning rate")
    p.add_argument("--min-lr-ratio", type=float, default=0.1, help="cosine decays to this fraction of the peak")
    p.add_argument("--warmup-steps", type=int, default=2000)
    p.add_argument("--max-steps", type=int, default=60000)
    p.add_argument("--weight-decay", type=float, default=0.1)
    p.add_argument("--beta2", type=float, default=0.98)
    p.add_argument("--grad-clip", type=float, default=1.0)
    p.add_argument("--ema-decay", type=float, default=0.9999)
    # data
    p.add_argument("--data-dir", default="data/processed",
                   help="split to train on, relative to the repo root (data/processed_split1 = replication split, P4)")
    p.add_argument("--max-tokens", type=int, default=16384, help="padded token slots per batch")
    p.add_argument("--num-workers", type=int, default=2)
    # bookkeeping
    p.add_argument("--log-every", type=int, default=100)
    p.add_argument("--eval-every", type=int, default=2500)
    p.add_argument("--seed", type=int, default=0)
    return p.parse_args()


def git_commit() -> str:
    """The exact code version, marked '-dirty' if there are uncommitted edits."""
    head = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=REPO_ROOT).stdout.strip()
    dirty = subprocess.run(["git", "status", "--porcelain", "--untracked-files=no"],
                           capture_output=True, text=True, cwd=REPO_ROOT).stdout.strip()
    return head + ("-dirty" if dirty else "")


def learning_rate(step: int, cfg: dict) -> float:
    """Linear warmup from ~0 to the peak, then half a cosine down to min_lr_ratio x peak."""
    peak, warmup, total = cfg["lr"], cfg["warmup_steps"], cfg["max_steps"]
    if step < warmup:
        return peak * (step + 1) / warmup
    progress = min(1.0, (step - warmup) / max(1, total - warmup))           # 0 -> 1 over the rest of training
    floor = cfg["min_lr_ratio"]
    return peak * (floor + (1 - floor) * 0.5 * (1 + math.cos(math.pi * progress)))


def make_optimizer(model: torch.nn.Module, cfg: dict) -> torch.optim.AdamW:
    """AdamW; weight decay on weight matrices and embeddings only, not on LayerNorm parameters."""
    decay = [p for p in model.parameters() if p.dim() >= 2]
    no_decay = [p for p in model.parameters() if p.dim() < 2]
    groups = [{"params": decay, "weight_decay": cfg["weight_decay"]},
              {"params": no_decay, "weight_decay": 0.0}]
    return torch.optim.AdamW(groups, lr=cfg["lr"], betas=(0.9, cfg["beta2"]), fused=True)


@torch.no_grad()
def update_ema(ema_model: torch.nn.Module, model: torch.nn.Module, step: int, decay: float) -> None:
    """ema <- ema + (1 - d) * (live - ema): a low-pass filter on the weights.

    d starts small and rises to `decay`, so the average isn't dragged for
    thousands of steps by the random initial weights.
    """
    d = min(decay, (1 + step) / (10 + step))
    torch._foreach_lerp_(list(ema_model.parameters()), list(model.parameters()), 1 - d)


@torch.no_grad()
def evaluate(model: torch.nn.Module, loader, device, loss_fn) -> float:
    """Validation bits per nucleotide, with the SAME noise every time.

    A fixed generator seed gives every evaluation identical t values and masks,
    so a change in the number reflects the model, not the dice. (The AR loss
    uses no noise, so for it the generator changes nothing.)
    """
    model.eval()
    g = torch.Generator(device=device).manual_seed(1234)
    total_nats, total_nt = 0.0, 0
    for batch in loader:
        ids = batch["input_ids"].to(device, non_blocking=True)
        att = batch["attention_mask"].to(device, non_blocking=True)
        with torch.autocast("cuda", dtype=torch.bfloat16):
            loss, _ = loss_fn(model, ids, att, g)                          # nats per nucleotide in this batch
        n = int(is_nucleotide(ids).sum())
        total_nats += loss.item() * n
        total_nt += n
    model.train()
    return total_nats / total_nt / math.log(2)


def save(path, model, ema_model, optimizer, step, epoch, best_val, cfg) -> None:
    tmp = path.with_suffix(".tmp")
    torch.save({"model": model.state_dict(), "ema": ema_model.state_dict(),
                "optimizer": optimizer.state_dict(), "step": step, "epoch": epoch,
                "best_val": best_val, "config": cfg}, tmp)
    tmp.rename(path)          # atomic: a crash mid-save never leaves a half-written checkpoint


def main() -> None:
    args = parse_args()
    device = torch.device("cuda")
    state = None
    if args.resume:
        state = torch.load(args.resume, map_location="cpu", weights_only=False)
        cfg = state["config"]
        cfg["resumed_at_commit"] = git_commit()
    else:
        assert args.run_name, "--run-name is required for a new run"
        cfg = {k: v for k, v in vars(args).items() if k != "resume"}
        # record only the settings the chosen architecture actually uses
        unused = ("d_state", "expand", "headdim") if cfg["arch"] == "transformer" else ("n_heads",)
        cfg = {k: v for k, v in cfg.items() if k not in unused}
        cfg["git_commit"] = git_commit()
    run_dir = REPO_ROOT / "checkpoints" / cfg["run_name"]

    torch.manual_seed(cfg["seed"])
    np.random.seed(cfg["seed"])
    model = build_model(cfg).to(device)          # configs without "arch" (before Phase 4) are Transformers
    cfg["parameters"] = count_parameters(model) if cfg.get("allow_any_size") else check_parameter_budget(model)
    run_dir.mkdir(parents=True, exist_ok=True)           # only after the size check: a refused run leaves nothing
    loss_fn = objective(cfg.get("arch", "transformer"))
    ema_model = copy.deepcopy(model).requires_grad_(False)
    optimizer = make_optimizer(model, cfg)

    step, epoch, best_val = 0, 0, float("inf")
    if state is not None:
        model.load_state_dict(state["model"])
        ema_model.load_state_dict(state["ema"])
        optimizer.load_state_dict(state["optimizer"])
        step, epoch, best_val = state["step"], state["epoch"], state["best_val"]
        print(f"resumed from step {step}, epoch {epoch} (the epoch restarts from its first batch)")
    else:
        (run_dir / "config.json").write_text(json.dumps(cfg, indent=2))
    print(json.dumps(cfg, indent=2))

    data_dir = REPO_ROOT / cfg.get("data_dir", "data/processed")          # runs before Phase 4 had no choice
    train_loader = make_dataloader("train", max_tokens=cfg["max_tokens"], shuffle=True, add_bos=True,
                                   add_eos=True, num_workers=cfg["num_workers"], seed=cfg["seed"], data_dir=data_dir)
    val_loader = make_dataloader("val", max_tokens=cfg["max_tokens"], shuffle=False, add_bos=True,
                                 add_eos=True, num_workers=cfg["num_workers"], seed=cfg["seed"], data_dir=data_dir)
    g = torch.Generator(device=device).manual_seed(cfg["seed"] + step)   # masks and t during training

    log_file = open(run_dir / "log.csv", "a", newline="")
    log = csv.writer(log_file)
    if step == 0:
        log.writerow(["step", "epoch", "lr", "train_bits", "grad_norm", "val_bits_live", "val_bits_ema",
                      "knt_per_s", "peak_GB", "hours"])
    start, window = time.time(), {"bits": [], "grad": [], "nt": 0, "t0": time.time()}
    torch.cuda.reset_peak_memory_stats()

    while step < cfg["max_steps"]:
        train_loader.batch_sampler.set_epoch(epoch)
        for batch in train_loader:
            if step >= cfg["max_steps"]:
                break
            ids = batch["input_ids"].to(device, non_blocking=True)            # (B, L+2)
            att = batch["attention_mask"].to(device, non_blocking=True)      # (B, L+2)
            lr = learning_rate(step, cfg)
            for group in optimizer.param_groups:
                group["lr"] = lr
            with torch.autocast("cuda", dtype=torch.bfloat16):
                loss, stats = loss_fn(model, ids, att, g)
            if not torch.isfinite(loss):
                raise RuntimeError(f"loss became {loss.item()} at step {step}; last good state is last.pt")
            optimizer.zero_grad(set_to_none=True)
            loss.backward()
            grad_norm = torch.nn.utils.clip_grad_norm_(model.parameters(), cfg["grad_clip"])
            optimizer.step()
            update_ema(ema_model, model, step, cfg["ema_decay"])
            step += 1

            window["bits"].append(stats["bits_per_nt"])
            window["grad"].append(grad_norm)
            window["nt"] += int(is_nucleotide(ids).sum())
            if step % cfg["log_every"] == 0:
                elapsed = time.time() - window["t0"]
                bits = torch.stack(window["bits"]).mean().item()
                grad = torch.stack(window["grad"]).mean().item()
                row = [step, epoch, f"{lr:.3e}", f"{bits:.4f}", f"{grad:.3f}", "", "",
                       f"{window['nt'] / elapsed / 1000:.0f}", f"{torch.cuda.max_memory_allocated() / 1e9:.2f}",
                       f"{(time.time() - start) / 3600:.3f}"]
                log.writerow(row)
                log_file.flush()
                window = {"bits": [], "grad": [], "nt": 0, "t0": time.time()}

            if step % cfg["eval_every"] == 0 or step == cfg["max_steps"]:
                val_live = evaluate(model, val_loader, device, loss_fn)
                val_ema = evaluate(ema_model, val_loader, device, loss_fn)
                log.writerow([step, epoch, f"{lr:.3e}", "", "", f"{val_live:.4f}", f"{val_ema:.4f}", "", "",
                              f"{(time.time() - start) / 3600:.3f}"])
                log_file.flush()
                print(f"step {step:>7}  epoch {epoch:>3}  lr {lr:.2e}  val bits/nt: live {val_live:.4f}  "
                      f"ema {val_ema:.4f}", flush=True)
                if val_ema < best_val:
                    best_val = val_ema
                    save(run_dir / "best.pt", model, ema_model, optimizer, step, epoch, best_val, cfg)
                save(run_dir / "last.pt", model, ema_model, optimizer, step, epoch, best_val, cfg)
                window["t0"] = time.time()           # don't count evaluation time as training time
                window["nt"] = 0
        epoch += 1
    log_file.close()
    print(f"done: {step} steps, best validation {best_val:.4f} bits/nt (EMA)")


if __name__ == "__main__":
    main()
