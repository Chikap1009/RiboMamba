"""Stage B probe: the existing unconditional Transformer as a repair PROPOSAL model (no training).

The model (checkpoints/tf_M_do0/best.pt, EMA weights, 14.17 M parameters,
masked diffusion on Rfam training sequences) knows nothing about the target
structure. Here it only fills the positions that a control would have edited,
with everything else clamped:

  input      <bos> x_1 .. x_L <eos>, the chosen sites' positions set to <mask>
  decoding   one position at a time, in site order (for a pair: i, then j),
             one forward pass per position, each conditioned on the letters
             already filled (the chain rule, so a pair is sampled JOINTLY
             under the model's own conditionals, not as two independent
             marginals);
  legality   a pair's second letter is restricted to canonical partners of
             the first; the first is restricted to letters that have at least
             one partner giving a pair different from the current one; an
             unpaired position must change. These are exactly the moves the
             random-proposal controls make, so the ONLY difference between
             neural_* and the matching control is who picks among legal moves.

Methods (same shared start, objective, acceptance and site rules as the controls):
  neural_feedback_edits  feedback-selected sites (pick_feedback_sites), model proposals
  neural_random_edits    random sites (pick_random_sites), model proposals
Contrasts: neural_feedback_edits vs feedback_pair_edits (proposal source with
identical mask rule); neural_feedback_edits vs neural_random_edits (mask rule
with identical proposal source).

The model's forward passes are counted (cum_model_calls) and timed
(model_wall_s); training was already paid in Phase 2 and is disclosed separately.
"""

import os
import time

import numpy as np
import torch

from ribomamba.data.tokenizer import BOS_ID, EOS_ID, FIRST_NUCLEOTIDE_ID, MASK_ID, NUCLEOTIDES, encode
from ribomamba.design.search import (PAIRS, Evaluator, Target, pick_feedback_sites, pick_random_sites, rng_for,
                                     shared_start)
from ribomamba.eval.folding import CANONICAL_PAIRS
from ribomamba.paths import REPO_ROOT

CHECKPOINT = REPO_ROOT / "checkpoints" / "tf_M_do0" / "best.pt"
from ribomamba.design.lazy_methods import NEURAL_SETTINGS  # noqa: E402  (single source of truth)
_MODEL = {}


def load(checkpoint=CHECKPOINT, device: str | None = None):
    """The EMA model, once per process; GPU when visible."""
    key = str(checkpoint)
    if key not in _MODEL:
        from ribomamba.models.checkpoint import load_model
        device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        if device == "cpu":
            torch.set_num_threads(int(os.environ.get("OMP_NUM_THREADS", "1")))
        model, state = load_model(checkpoint, weights="ema", device=device)
        _MODEL[key] = (model, device)
    return _MODEL[key]


class InfillProposer:
    def __init__(self, evaluate: Evaluator, temperature: float = 1.0, checkpoint=CHECKPOINT):
        self.model, self.device = load(checkpoint)
        self.evaluate, self.temperature = evaluate, temperature

    @torch.no_grad()
    def distribution(self, ids: torch.Tensor, position: int) -> np.ndarray:
        """P(letter at `position` | the unmasked letters), float64 over A, C, G, U."""
        start = time.perf_counter()
        attention = torch.ones_like(ids, dtype=torch.bool)
        with torch.autocast("cuda", dtype=torch.bfloat16, enabled=self.device == "cuda"):
            logits = self.model(ids, attention)                              # (1, L + 2, V)
        row = logits[0, position + 1, FIRST_NUCLEOTIDE_ID:].double() / self.temperature
        p = torch.softmax(row, dim=-1).cpu().numpy()
        self.evaluate.model_calls += 1
        self.evaluate.model_wall_s += time.perf_counter() - start
        return p

    def propose(self, sequence: str, target: Target, site_indices: list[int], rng: np.random.Generator) -> str:
        seq = list(sequence)
        ids = torch.tensor([BOS_ID, *encode(sequence).tolist(), EOS_ID], device=self.device)[None, :]
        order = [p for k in site_indices for p in target.sites[k]]
        ids[0, [p + 1 for p in order]] = MASK_ID
        for k in site_indices:
            site = target.sites[k]
            if len(site) == 1:
                (i,) = site
                allowed = [b != sequence[i] for b in NUCLEOTIDES]
                seq[i] = self._draw(ids, i, allowed, rng)
                ids[0, i + 1] = FIRST_NUCLEOTIDE_ID + NUCLEOTIDES.index(seq[i])
                continue
            i, j = site
            current = sequence[i] + sequence[j]
            partners = {a: [b for b in NUCLEOTIDES if a + b in CANONICAL_PAIRS and a + b != current]
                        for a in NUCLEOTIDES}
            seq[i] = self._draw(ids, i, [bool(partners[a]) for a in NUCLEOTIDES], rng)
            ids[0, i + 1] = FIRST_NUCLEOTIDE_ID + NUCLEOTIDES.index(seq[i])
            seq[j] = self._draw(ids, j, [b in partners[seq[i]] for b in NUCLEOTIDES], rng)
            ids[0, j + 1] = FIRST_NUCLEOTIDE_ID + NUCLEOTIDES.index(seq[j])
        out = "".join(seq)
        assert all(out[i] + out[j] in PAIRS for i, j in (s for s in target.sites if len(s) == 2))
        return out

    def _draw(self, ids, position: int, allowed: list[bool], rng: np.random.Generator) -> str:
        p = self.distribution(ids, position) * np.asarray(allowed, dtype=float)
        if p.sum() <= 0:                                       # the model puts no mass on any legal letter
            p = np.asarray(allowed, dtype=float)
        return NUCLEOTIDES[int(rng.choice(4, p=p / p.sum()))]


def _neural_search(target: Target, seed: int, evaluate: Evaluator, settings: dict, pick, name: str) -> None:
    proposer = InfillProposer(evaluate, settings.get("temperature", 1.0))
    current = evaluate(shared_start(target, seed))
    rng = rng_for(name, target.id, seed)
    while True:
        evaluate.check()
        child = proposer.propose(current.sequence, target, pick(target, current.score, rng), rng)
        proposal = evaluate(child, parent=current.index)
        if proposal.objective <= current.objective:
            current = proposal


def neural_feedback_edits(target: Target, seed: int, evaluate: Evaluator, settings: dict) -> None:
    _neural_search(target, seed, evaluate, settings, pick_feedback_sites, "neural_feedback_edits")


def neural_random_edits(target: Target, seed: int, evaluate: Evaluator, settings: dict) -> None:
    _neural_search(target, seed, evaluate, settings, pick_random_sites, "neural_random_edits")


NEURAL = {"neural_feedback_edits": neural_feedback_edits, "neural_random_edits": neural_random_edits}
NEURAL_METHOD_SETTINGS = {name: dict(NEURAL_SETTINGS) for name in NEURAL}
