"""Sampling designs from the target-conditioned denoiser, and harness methods that use it.

docs/experiments/2026-09-28-target-conditioned-denoiser.md, evaluation parts A and B.

Sampler: Phase 2's monotone unmasking, conditioned on the target structure. Units are single
unpaired positions and target PAIRS; at each step every still-masked unit is revealed with
probability (t - s) / t (all remaining at the last step). A pair (i, j) is drawn from
p_i(a) p_j(b) restricted to canonical pairs and renormalised: the product of the two conditional
marginals from the same forward pass, an approximation to their joint (stated, not hidden).
Every design therefore satisfies all target pairs canonically.

Methods (harness):
  tcd_sample      conditioned samples until the candidate budget is spent (each scored)
  uncond_sample   identical sampler on the BASE model (adapters zero, structure ignored)
  samfeo_efilter_tcdinit  SAMFEO + energy screen whose k = 10 initial designs are TCD samples
Model forward passes and time are counted (model_calls, model_wall_s).
"""

import time

import numpy as np
import torch

from ribomamba.data.tokenizer import BOS_ID, EOS_ID, FIRST_NUCLEOTIDE_ID, MASK_ID, NUCLEOTIDES
from ribomamba.design.search import Evaluator, Target, rng_for
from ribomamba.eval.folding import CANONICAL_PAIRS
from ribomamba.models.conditioned import ConditionedDenoiser, structure_inputs
from ribomamba.paths import REPO_ROOT

from ribomamba.design.lazy_methods import TCD_CHECKPOINT, TCD_SETTINGS  # noqa: E402  (single source of truth)
BASE_CHECKPOINT = REPO_ROOT / "checkpoints" / "tf_M_do0" / "best.pt"
CANON16 = torch.tensor([[1.0 if a + b in CANONICAL_PAIRS else 0.0 for b in NUCLEOTIDES] for a in NUCLEOTIDES]).flatten()
_MODELS: dict = {}


def load(which: str, device: str | None = None) -> tuple[ConditionedDenoiser, str]:
    """'base' = the unconditional model with zero adapters; otherwise a TCD checkpoint path."""
    device = device or ("cuda" if torch.cuda.is_available() else "cpu")
    if which not in _MODELS:
        from ribomamba.models.checkpoint import load_model
        base, _ = load_model(BASE_CHECKPOINT, weights="ema", device="cpu")
        model = ConditionedDenoiser.from_unconditional(base)
        if which != "base":
            state = torch.load(REPO_ROOT / which, map_location="cpu", weights_only=False)
            model.load_state_dict(state["state"])
        _MODELS[which] = model.to(device).eval()
    return _MODELS[which], device


@torch.no_grad()
def sample_designs(model: ConditionedDenoiser, structure: str, n: int, steps: int, generator: torch.Generator,
                   device: str, temperature: float = 1.0) -> list[str]:
    from ribomamba.eval.folding import pair_table
    L, W = len(structure), len(structure) + 2
    ids = torch.full((n, W), MASK_ID, dtype=torch.long, device=device)
    ids[:, 0], ids[:, L + 1] = BOS_ID, EOS_ID
    attn = torch.ones((n, W), dtype=torch.bool, device=device)
    bracket, partner = structure_inputs([structure] * n, W, device)
    pt = pair_table(structure)
    singles = torch.tensor([i + 1 for i, j in enumerate(pt) if j < 0], dtype=torch.long, device=device)
    pi = torch.tensor([i + 1 for i, j in enumerate(pt) if j > i], dtype=torch.long, device=device)
    pj = torch.tensor([j + 1 for i, j in enumerate(pt) if j > i], dtype=torch.long, device=device)
    s_open = torch.ones((n, len(singles)), dtype=torch.bool, device=device)
    p_open = torch.ones((n, len(pi)), dtype=torch.bool, device=device)
    canon = CANON16.to(device)
    times = torch.linspace(1.0, 0.0, steps + 1).tolist()
    for t, s in zip(times[:-1], times[1:]):
        with torch.autocast("cuda", dtype=torch.bfloat16, enabled=device == "cuda"):
            logits = model(ids, attn, bracket, partner)
        probs = torch.softmax(logits[..., FIRST_NUCLEOTIDE_ID:].double() / temperature, dim=-1)   # (n, W, 4)
        frac = 1.0 if s <= 0 else (t - s) / t
        if len(singles):
            reveal = s_open & (torch.rand(s_open.shape, device=device, generator=generator) < frac)
            draw = torch.multinomial(probs[:, singles].reshape(-1, 4), 1, generator=generator).view(n, -1)
            cur = ids[:, singles]
            ids[:, singles] = torch.where(reveal, draw + FIRST_NUCLEOTIDE_ID, cur)
            s_open &= ~reveal
        if len(pi):
            reveal = p_open & (torch.rand(p_open.shape, device=device, generator=generator) < frac)
            joint = (probs[:, pi, :, None] * probs[:, pj, None, :]).reshape(n, len(pi), 16) * canon
            joint = joint / joint.sum(-1, keepdim=True)
            k = torch.multinomial(joint.reshape(-1, 16), 1, generator=generator).view(n, -1)
            a, b = k // 4 + FIRST_NUCLEOTIDE_ID, k % 4 + FIRST_NUCLEOTIDE_ID
            ids[:, pi] = torch.where(reveal, a, ids[:, pi])
            ids[:, pj] = torch.where(reveal, b, ids[:, pj])
            p_open &= ~reveal
    letters = np.array(list("????ACGU"))
    return ["".join(letters[row[1:L + 1].cpu().numpy()]) for row in ids]


def _generator(target: Target, seed: int, device: str, tag: str) -> torch.Generator:
    g = torch.Generator(device=device)
    g.manual_seed(int(rng_for(tag, target.id, seed).integers(2**62)))
    return g


def _sample_loop(which: str, target: Target, seed: int, evaluate: Evaluator, settings: dict, tag: str) -> None:
    model, device = load(which)
    gen = _generator(target, seed, device, tag)
    while True:
        evaluate.check()
        start = time.perf_counter()
        batch = sample_designs(model, target.structure, settings.get("batch", 32), settings.get("steps", 32), gen,
                               device, settings.get("temperature", 1.0))
        evaluate.model_calls += settings.get("steps", 32)
        evaluate.model_wall_s += time.perf_counter() - start
        for seq in batch:
            evaluate(seq)


def tcd_sample(target: Target, seed: int, evaluate: Evaluator, settings: dict) -> None:
    _sample_loop(settings.get("checkpoint", TCD_CHECKPOINT), target, seed, evaluate, settings, "tcd_sample")


def uncond_sample(target: Target, seed: int, evaluate: Evaluator, settings: dict) -> None:
    _sample_loop("base", target, seed, evaluate, settings, "uncond_sample")


def tcd_initial_designs(target: Target, seed: int, k: int, evaluate: Evaluator, settings: dict) -> list[str]:
    """k distinct TCD samples for SAMFEO's initial frontier (sampling cost charged to the method)."""
    model, device = load(settings.get("checkpoint", TCD_CHECKPOINT))
    gen = _generator(target, seed, device, "tcd_init")
    out, start = [], time.perf_counter()
    for _ in range(8):
        for seq in sample_designs(model, target.structure, 2 * k, settings.get("steps", 32), gen, device):
            if seq not in out:
                out.append(seq)
        evaluate.model_calls += settings.get("steps", 32)
        if len(out) >= k:
            break
    evaluate.model_wall_s += time.perf_counter() - start
    return out[:k]


TCD_METHODS = {"tcd_sample": tcd_sample, "uncond_sample": uncond_sample}
TCD_METHOD_SETTINGS = {"tcd_sample": TCD_SETTINGS, "uncond_sample": {**TCD_SETTINGS, "checkpoint": "base"}}


@torch.no_grad()
def infill(model: ConditionedDenoiser, device: str, structure: str, pt: list[int], parent: str,
           masks: list[list[int]], rng: np.random.Generator) -> list[str]:
    """Refill each mask's positions of `parent` with the TCD (one batched forward pass).

    A target pair with either end masked is refilled as a unit (both ends masked, drawn from the
    canonical-restricted product of the two conditional marginals); unpaired positions are drawn
    from their marginal. Everything outside the mask is clamped to the parent.
    """
    L, W = len(structure), len(structure) + 2
    full = _expand_masks(masks, pt)
    base = torch.tensor([BOS_ID, *[FIRST_NUCLEOTIDE_ID + NUCLEOTIDES.index(c) for c in parent], EOS_ID],
                        device=device)
    ids = base.repeat(len(masks), 1)
    for b, m in enumerate(full):
        ids[b, [p + 1 for p in m]] = MASK_ID
    attn = torch.ones_like(ids, dtype=torch.bool)
    bracket, partner = structure_inputs([structure] * len(masks), W, device)
    with torch.autocast("cuda", dtype=torch.bfloat16, enabled=device == "cuda"):
        logits = model(ids, attn, bracket, partner)
    probs = torch.softmax(logits[..., FIRST_NUCLEOTIDE_ID:].double(), dim=-1).cpu().numpy()   # (B, W, 4)
    return _draw_children(probs, full, parent, pt, rng)


def _expand_masks(masks: list[list[int]], pt: list[int]) -> list[list[int]]:
    """Each mask plus the target partners of its positions, sorted (a pair is refilled as a unit)."""
    full = []
    for m in masks:
        s = set(m)
        s |= {pt[p] for p in m if pt[p] >= 0}
        full.append(sorted(s))
    return full


def _draw_children(probs: np.ndarray, full: list[list[int]], parent: str, pt: list[int],
                   rng: np.random.Generator) -> list[str]:
    """Sample each row's masked units from its (B, W, 4) probabilities, in mask order, with `rng`."""
    canon = CANON16.numpy().reshape(4, 4)
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
    return out


class GraphedForward:
    """The TCD forward for ONE target and batch shape, captured once in a CUDA graph and replayed.

    Static buffers hold the token batch and the (per-target, constant) structure inputs; each call
    copies a host-built token batch into the buffer (one H2D copy) and replays the captured kernels.
    Same model, same inputs, same kernels as the eager call: logits are expected to be bitwise
    identical (tested), so everything downstream (softmax, sampling, search) is unchanged.
    """

    def __init__(self, model: ConditionedDenoiser, structure: str, batch: int):
        W = len(structure) + 2
        self.key = (id(model), structure, batch)
        self.model = model
        self.ids = torch.full((batch, W), MASK_ID, dtype=torch.long, device="cuda")
        self.ids[:, 0], self.ids[:, -1] = BOS_ID, EOS_ID
        self.attn = torch.ones((batch, W), dtype=torch.bool, device="cuda")
        self.bracket, self.partner = structure_inputs([structure] * batch, W, "cuda")
        side = torch.cuda.Stream()
        side.wait_stream(torch.cuda.current_stream())
        with torch.cuda.stream(side):                      # warm-up before capture (required by CUDA graphs)
            for _ in range(3):
                self._forward()
        torch.cuda.current_stream().wait_stream(side)
        self.graph = torch.cuda.CUDAGraph()
        with torch.cuda.graph(self.graph):
            self.logits = self._forward()

    @torch.no_grad()
    def _forward(self) -> torch.Tensor:
        with torch.autocast("cuda", dtype=torch.bfloat16, cache_enabled=False):
            return self.model(self.ids, self.attn, self.bracket, self.partner)

    def __call__(self, host_ids: torch.Tensor) -> torch.Tensor:
        self.ids.copy_(host_ids)
        self.graph.replay()
        return self.logits


_GRAPHED: dict = {}                                        # at most ONE captured graph per process (bounded)


@torch.no_grad()
def infill_graphed(model: ConditionedDenoiser, device: str, structure: str, pt: list[int], parent: str,
                   masks: list[list[int]], rng: np.random.Generator) -> list[str]:
    """infill with the forward replayed from a CUDA graph (same inputs, logits, draws); eager off the GPU."""
    if device != "cuda":
        return infill(model, device, structure, pt, parent, masks, rng)
    key = (id(model), structure, len(masks))
    graphed = _GRAPHED.get("current")
    if graphed is None or graphed.key != key:
        _GRAPHED.clear()                                   # release the previous target's graph first
        graphed = _GRAPHED["current"] = GraphedForward(model, structure, len(masks))
    full = _expand_masks(masks, pt)
    host = torch.tensor([BOS_ID, *[FIRST_NUCLEOTIDE_ID + NUCLEOTIDES.index(c) for c in parent], EOS_ID])
    host_ids = host.repeat(len(masks), 1)
    for b, m in enumerate(full):
        host_ids[b, [p + 1 for p in m]] = MASK_ID
    logits = graphed(host_ids)
    probs = torch.softmax(logits[..., FIRST_NUCLEOTIDE_ID:].double(), dim=-1).cpu().numpy()   # (B, W, 4)
    return _draw_children(probs, full, parent, pt, rng)
