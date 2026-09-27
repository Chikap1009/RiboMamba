"""External baseline adapters: SAMFEO runs unmodified, counted, and agrees with the harness's scorer."""

import numpy as np
import pytest
import RNA

from ribomamba.design import baselines
from ribomamba.design.search import BudgetExhausted, Evaluator, Target
from ribomamba.eval.folding import model_details

needs_samfeo = pytest.mark.skipif(baselines.samfeo_checkout_problem() is not None,
                                  reason="pinned SAMFEO checkout not present in external/")


def test_explicit_model_details_equal_viennas_defaults():
    # SAMFEO and RNAinverse would otherwise use ViennaRNA's global defaults; the proxy forces ours.
    ours, default = model_details(), RNA.md()
    assert (ours.temperature, ours.dangles, ours.noLP) == (default.temperature, default.dangles, default.noLP)


@needs_samfeo
def test_samfeo_trace_counts_and_agreement():
    target = Target("toy:hairpin", "(((((......)))))")
    ev = Evaluator(target, budget=30)
    with pytest.raises(BudgetExhausted):
        baselines.samfeo(target, 0, ev, {})
    rows = ev.rows
    assert len(rows) == 30
    # Exact internal accounting: SAMFEO never re-evaluates, one subopt + pf + probability per candidate.
    assert (ev.internal.subopt, ev.internal.pf, ev.internal.eval, ev.internal.mfe) == (30, 30, 30, 0)
    # Its objective is -P(target); the harness's P must agree to float precision.
    assert max(abs(-r["objective"] - r["p_target"]) for r in rows) < 1e-12
    assert all(r["parent_index"] == -1 for r in rows[:10])       # k = 10 initial designs
    for r in rows[10:]:
        assert 0 <= r["parent_index"] < r["eval_index"] and r["changed_positions"]
    assert len({r["sequence"] for r in rows}) == 30


@needs_samfeo
def test_samfeo_reproduces_its_own_reference_test_through_the_proxy():
    # SAMFEO's test_design: seed 2020, k 10, 100 steps on this hairpin -> best GCCCCGAAAAAGGGGC.
    target = Target("toy:hairpin", "(((((......)))))")
    ev = Evaluator(target, budget=110)
    with pytest.raises(BudgetExhausted):
        baselines.samfeo(target, 0, ev, {})
    best = max(ev.rows, key=lambda r: r["p_target"])
    assert best["sequence"] == "GCCCCGAAAAAGGGGC"


def test_rnainverse_is_recorded_without_internal_counts():
    target = Target("toy:hairpin", "(((((......)))))")
    ev = Evaluator(target, budget=3)
    with pytest.raises(BudgetExhausted):
        baselines.rnainverse(target, 0, ev, {})
    assert len(ev.rows) == 3 and all(r["cum_internal_pf"] is None for r in ev.rows)
    assert np.isfinite(ev.rows[0]["ned"])
