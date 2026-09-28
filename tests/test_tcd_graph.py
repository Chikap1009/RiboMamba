"""CUDA-graph TCD forward (docs/experiments/2026-09-28-tcd-inference-efficiency.md): a speed change only.

The risks are semantic: different logits, different children or random draws, a different search
trajectory, stale graphs reused across targets, unbounded graph memory, and lost resource counts.
Tests needing the real checkpoint and a GPU are skipped without them.
"""

import numpy as np
import pytest
import torch

from ribomamba.design import tcd
from ribomamba.eval.folding import CANONICAL_PAIRS, pair_table
from ribomamba.models.conditioned import ConditionedDenoiser
from ribomamba.models.transformer import TransformerConfig
from ribomamba.paths import REPO_ROOT

needs_gpu = pytest.mark.skipif(not torch.cuda.is_available() or not (REPO_ROOT / tcd.TCD_CHECKPOINT).exists(),
                               reason="needs CUDA and the TCD checkpoint")
TARGETS = ["((((....))))..(((...)))", "..((((((...((((....))))..(((...))))))))).....((((....))))" * 2]


def _masks(rng, n, L):
    return [sorted(set(rng.choice(L, size=int(rng.integers(1, 5)), replace=False).tolist())) for _ in range(n)]


def test_cpu_falls_back_to_the_eager_path():
    torch.manual_seed(0)
    model = ConditionedDenoiser(TransformerConfig(d_model=32, n_layers=2, n_heads=2)).eval()
    target = TARGETS[0]
    pt, parent = pair_table(target), "GGGGAAAACCCCAAGGGAAACCC"
    masks = _masks(np.random.default_rng(0), 8, len(target))
    a = tcd.infill(model, "cpu", target, pt, parent, masks, np.random.default_rng(3))
    b = tcd.infill_graphed(model, "cpu", target, pt, parent, masks, np.random.default_rng(3))
    assert a == b and not tcd._GRAPHED


@needs_gpu
def test_graph_replay_gives_bitwise_identical_logits():
    model, _ = tcd.load(tcd.TCD_CHECKPOINT)
    for target in TARGETS:
        g = tcd.GraphedForward(model, target, 8)
        rng = np.random.default_rng(1)
        for _ in range(3):
            ids = torch.randint(tcd.FIRST_NUCLEOTIDE_ID, tcd.FIRST_NUCLEOTIDE_ID + 4, (8, len(target) + 2))
            ids[:, 0], ids[:, -1] = tcd.BOS_ID, tcd.EOS_ID
            ids[torch.from_numpy(rng.random((8, len(target) + 2)) < 0.1)] = tcd.MASK_ID
            graphed = g(ids).clone()
            with torch.no_grad(), torch.autocast("cuda", dtype=torch.bfloat16):
                eager = model(ids.cuda(), g.attn, g.bracket, g.partner)
            nuc = slice(tcd.FIRST_NUCLEOTIDE_ID, None)
            assert torch.equal(graphed[..., nuc], eager[..., nuc])


@needs_gpu
def test_graphed_infill_matches_eager_draws_clamps_and_pairs():
    model, device = tcd.load(tcd.TCD_CHECKPOINT)
    for target in TARGETS:
        pt = pair_table(target)
        rng = np.random.default_rng(2)
        for rep in range(4):
            parent = "".join("G" if c == "(" else "C" if c == ")" else "ACGU"[int(rng.integers(4))] for c in target)
            masks = _masks(rng, 8, len(target))
            a = tcd.infill(model, device, target, pt, parent, masks, np.random.default_rng(rep))
            b = tcd.infill_graphed(model, device, target, pt, parent, masks, np.random.default_rng(rep))
            assert a == b
            for kid, m in zip(b, masks):
                free = set(m) | {pt[p] for p in m if pt[p] >= 0}
                assert all(kid[i] == parent[i] for i in range(len(target)) if i not in free)
                assert all(kid[i] + kid[j] in CANONICAL_PAIRS for i, j in enumerate(pt) if j > i)


@needs_gpu
def test_one_graph_per_process_and_switching_targets_recaptures():
    model, device = tcd.load(tcd.TCD_CHECKPOINT)
    outs = {}
    for target in TARGETS + TARGETS[:1]:                      # back to the first target: must recapture
        pt = pair_table(target)
        parent = "".join("G" if c == "(" else "C" if c == ")" else "A" for c in target)
        masks = [[p] for p in range(0, len(target), max(1, len(target) // 8))][:8]
        kids = tcd.infill_graphed(model, device, target, pt, parent, masks, np.random.default_rng(0))
        assert len(tcd._GRAPHED) == 1 and tcd._GRAPHED["current"].key[1] == target
        assert kids == tcd.infill(model, device, target, pt, parent, masks, np.random.default_rng(0))
        outs.setdefault(target, kids)
        assert outs[target] == kids


@needs_gpu
def test_whole_search_trajectory_is_unchanged_and_counted():
    from ribomamba.design import baselines
    from ribomamba.design.search import BudgetExhausted, Evaluator, Target
    if baselines.samfeo_checkout_problem():
        pytest.skip("SAMFEO absent")
    target = Target("toy", "((((((....))))))..((((((....))))))...((((....))))")
    runs = {}
    for name in ("samfeo_tcdprop_efilter", "samfeo_tcdprop_efilter_graph"):
        ev = Evaluator(target, budget=120)
        with pytest.raises(BudgetExhausted):
            baselines.samfeo(target, 1, ev, baselines.BASELINE_SETTINGS[name])
        runs[name] = ev
    ref, fast = runs.values()
    assert [r["sequence"] for r in ref.rows] == [r["sequence"] for r in fast.rows]
    assert [r["parent_index"] for r in ref.rows] == [r["parent_index"] for r in fast.rows]
    assert ref.model_calls == fast.model_calls > 0 and ref.proposal_calls == fast.proposal_calls > 0
    assert fast.proposal_wall_s > 0 and fast.model_wall_s > 0
    assert baselines.BASELINE_SETTINGS["samfeo_tcdprop_efilter_graph"]["tcd_forward"] == "cuda_graph"
