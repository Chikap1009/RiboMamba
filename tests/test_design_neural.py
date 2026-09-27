"""Stage B neural proposals: legal, clamped, chain-rule decoded, counted. CPU only (CUDA hidden in tests)."""

import numpy as np
import pytest

from ribomamba.design import neural
from ribomamba.design.search import BudgetExhausted, Evaluator, Target, pick_random_sites, shared_start
from ribomamba.eval.folding import CANONICAL_PAIRS

needs_checkpoint = pytest.mark.skipif(not neural.CHECKPOINT.exists(), reason="Transformer checkpoint absent")
TARGET = Target("toy:two_stems", "((((....))))..((((....))))")


@pytest.fixture(scope="module")
def proposer():
    return neural.InfillProposer(Evaluator(TARGET, budget=10_000))


@needs_checkpoint
def test_proposals_change_only_the_chosen_sites_and_stay_legal(proposer):
    rng = np.random.default_rng(0)
    start = shared_start(TARGET, 0)
    for _ in range(40):
        sites = pick_random_sites(TARGET, None, rng)
        before = proposer.evaluate.model_calls
        child = proposer.propose(start, TARGET, sites, rng)
        chosen = {p for k in sites for p in TARGET.sites[k]}
        changed = {k for k, (a, b) in enumerate(zip(start, child)) if a != b}
        assert changed <= chosen                                     # everything else is clamped
        for k in sites:                                              # every chosen site really changes
            assert any(start[p] != child[p] for p in TARGET.sites[k])
        assert all(child[i] + child[j] in CANONICAL_PAIRS for i, j in enumerate(TARGET.pt) if j > i)
        assert proposer.evaluate.model_calls - before == len(chosen)  # one forward pass per masked position


@needs_checkpoint
def test_distribution_is_a_probability_over_nucleotides(proposer):
    import torch
    from ribomamba.data.tokenizer import BOS_ID, EOS_ID, MASK_ID, encode
    ids = torch.tensor([BOS_ID, *encode("GGGGAAAACCCC").tolist(), EOS_ID], device=proposer.device)[None]
    ids[0, 5] = MASK_ID
    p = proposer.distribution(ids, 4)
    assert p.shape == (4,) and np.isclose(p.sum(), 1.0) and (p >= 0).all()


@needs_checkpoint
def test_neural_method_runs_a_budgeted_unit_with_the_shared_start():
    ev = Evaluator(TARGET, budget=12)
    with pytest.raises(BudgetExhausted):
        neural.neural_feedback_edits(TARGET, 0, ev, {})
    assert ev.rows[0]["sequence"] == shared_start(TARGET, 0)
    assert len(ev.rows) == 12 and ev.rows[-1]["cum_model_calls"] == ev.model_calls > 0
    assert all(r["target_feasible"] for r in ev.rows)
