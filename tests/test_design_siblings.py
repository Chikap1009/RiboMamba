"""Sibling groups for the competition-residual experiment: exact labels, rival validity, rank identity."""

import math

import numpy as np
import pytest

from ribomamba.design import baselines
from ribomamba.design.scoring import KT, score
from ribomamba.design.search import Target, shared_start
from ribomamba.design.siblings import log_sum_exp_bank, logit_from_ln_p, rival_energies, sibling_group
from ribomamba.eval.folding import pair_table

TARGET = "((((((....))))))..((((((....))))))...((((....))))"
needs_samfeo = pytest.mark.skipif(baselines.samfeo_checkout_problem() is not None, reason="no SAMFEO checkout")


def test_incompatible_rivals_get_nan_not_a_finite_energy():
    seq = "GGGGAAACCCC"
    rivals = ["((((...))))", "(((.....)))", "(...)......"]      # last needs a G-A pair at (0, 4): unformable
    e = rival_energies(seq, rivals, [pair_table(s) for s in rivals])
    assert np.isfinite(e[0]) and np.isfinite(e[1]) and np.isnan(e[2])


def test_log_sum_exp_bank_and_logit():
    assert log_sum_exp_bank(None, np.array([np.nan])) == -math.inf
    two = log_sum_exp_bank(None, np.array([-1.0, -1.0]))
    assert two == pytest.approx(1.0 / KT + math.log(2))
    assert logit_from_ln_p(math.log(0.25)) == pytest.approx(math.log(1 / 3))


@needs_samfeo
def test_group_labels_are_exact_and_rank_identity_holds():
    module, _ = baselines.load_samfeo()
    parent = shared_start(Target("toy", TARGET), 2)
    g = sibling_group(TARGET, parent, module.mutate_structured, module.pairs_match(TARGET), 11)
    kids = g["children"]
    assert 1 <= len(kids) <= 16 and len({k["child"] for k in kids}) == len(kids)
    assert all(k["child"] != parent for k in kids)
    p = score(parent, TARGET)
    for k in kids:
        c = score(k["child"], TARGET)
        assert k["y"] == pytest.approx(c.log_p_target - p.log_p_target, abs=1e-12)
        assert k["a"] == pytest.approx(-(c.target_energy - p.target_energy) / KT, abs=1e-12)
        assert k["y"] - k["a"] == pytest.approx(k["r"], abs=1e-12)
        lhs = logit_from_ln_p(c.log_p_target) - logit_from_ln_p(p.log_p_target)
        assert lhs == pytest.approx(k["a"] + k["c"], abs=1e-9)             # log-odds identity
    by_y = [k["child"] for k in sorted(kids, key=lambda k: k["y"])]
    by_ac = [k["child"] for k in sorted(kids, key=lambda k: k["a"] + k["c"])]
    assert by_y == by_ac
    assert g["rivals"] and TARGET not in g["rivals"]
    assert all(np.isfinite(g["parent_rival_energy"]))                   # sampled from the parent: all formable
