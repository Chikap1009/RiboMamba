"""Stage C critic plumbing: features, padding, forward pass, filter interface. No trained weights needed."""

import numpy as np
import polars as pl
import torch

from ribomamba.design.critic import Critic, CriticConfig, CriticScorer, collate, encode_example, transitions_from_traces
from ribomamba.design.search import Evaluator, Target


def test_encoding_marks_changes_and_partner_letters():
    e = encode_example("((..))", "GCAAGC", "GUAAAC", np.zeros(6), -1.5)
    assert e["changed"].tolist() == [0, 1, 0, 0, 1, 0]
    assert e["p_partner"].tolist() == [1, 2, 4, 4, 1, 2]          # pairs (0,5) G-C and (1,4) C-G
    assert e["c_partner"].tolist() == [1, 0, 4, 4, 3, 2]          # child G..C, U..A
    assert e["delta_e"] == np.float32(-1.5)


def test_padding_does_not_change_a_prediction():
    torch.manual_seed(0)
    model = Critic(CriticConfig(d_model=32, n_layers=2, n_heads=2, dropout=0.0)).eval()
    short = encode_example("((..))", "GCAAGC", "GUAAAC", np.linspace(0, 1, 6), -1.0)
    long = encode_example("((((....))))", "GGGGAAAACCCC", "GGGAAAAACCCC", np.zeros(12), 0.5)
    alone = model(collate([short], "cpu"))
    padded = model(collate([short, long], "cpu"))[:1]
    assert torch.allclose(alone, padded, atol=1e-5)


def test_transitions_use_parent_links_and_log10_units():
    trace = pl.DataFrame({"target_id": ["t"] * 3, "seed": [0] * 3, "eval_index": [0, 1, 2],
                          "parent_index": [-1, 0, 0], "sequence": ["AA", "AC", "AG"],
                          "log_p_target": [np.log(0.1), np.log(0.2), np.log(0.05)],
                          "target_energy": [-1.0, -2.0, 0.5]})
    tr = transitions_from_traces(trace)
    assert tr.height == 2 and tr["parent"].to_list() == ["AA", "AA"]
    assert np.allclose(tr["delta"].to_list(), [np.log10(2), np.log10(0.5)])
    assert tr["improved"].to_list() == [True, False] and tr["delta_e"].to_list() == [-1.0, 1.5]


def test_scorer_interface_counts_its_work(tmp_path):
    cfg = CriticConfig(d_model=32, n_layers=2, n_heads=2)
    torch.save({"model": Critic(cfg).state_dict(), "config": cfg.__dict__}, tmp_path / "critic.pt")
    scorer = CriticScorer(tmp_path / "critic.pt", device="cpu")
    target = Target("toy", "((((....))))")
    ev = Evaluator(target, budget=5)
    scores = scorer(target, "GGGGAAAACCCC", ["GCGGAAAACCGC", "GGGGAAGACCCC"], [0.1] * 12, ev)
    assert len(scores) == 2 and all(np.isfinite(scores))
    assert ev.model_calls == 1 and ev.internal.eval == 3             # parent + 2 children energies
