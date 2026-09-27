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


@needs_samfeo
def test_energy_filtered_samfeo_picks_the_most_stable_child_and_counts_it():
    target = Target("toy:hairpin", "(((((......)))))")
    ev = Evaluator(target, budget=40)
    with pytest.raises(BudgetExhausted):
        baselines.samfeo_efilter(target, 0, ev, {})
    assert len(ev.rows) == 40 and len({r["sequence"] for r in ev.rows}) == 40
    assert (ev.internal.subopt, ev.internal.pf) == (40, 40)            # still one SAMFEO evaluation each
    assert ev.internal.eval >= 40 + 30                                 # + filter evaluations for 30 mutations
    # On average, filtered children stabilise the target more than unfiltered SAMFEO's children do:
    unfiltered = Evaluator(target, budget=40)
    with pytest.raises(BudgetExhausted):
        baselines.samfeo(target, 0, unfiltered, {})
    e = lambda rows: np.mean([r["target_energy"] for r in rows[10:]])
    assert e(ev.rows) < e(unfiltered.rows)


@needs_samfeo
def test_residual_filter_counts_bank_and_rival_work(tmp_path):
    import json

    from ribomamba.design import baselines as b
    from ribomamba.design.residual_models import FEATURES
    model = {"kind": "ridge", "features": FEATURES, "w": [0.0] * (len(FEATURES) + 1),
             "mu": [0.0] * len(FEATURES), "sd": [1.0] * len(FEATURES)}
    (tmp_path / "zero.json").write_text(json.dumps(model))
    target = Target("toy:two", "((((((....))))))..((((((....))))))")
    ev = Evaluator(target, budget=30)
    with pytest.raises(BudgetExhausted):
        b.samfeo(target, 0, ev, {**b.SAMFEO_SETTINGS, "filter": "residual", "filter_k": 8,
                                 "residual_model": str(tmp_path / "zero.json")})
    assert len(ev.rows) == 30 and ev.model_calls > 0
    assert ev.internal.pf > 30                       # SAMFEO's 30 + at least one rival-bank partition function
    assert ev.internal.eval > 30 + 8 * ev.model_calls


@needs_samfeo
def test_zero_residual_model_ranks_like_the_energy_filter():
    # A residual model that predicts c_hat = 0 must pick the same children as the energy filter.
    from ribomamba.design import baselines as b
    from ribomamba.design.residual_filter import ResidualScorer
    target = Target("toy:two", "((((((....))))))..((((((....))))))")
    scorer = ResidualScorer.__new__(ResidualScorer)
    scorer.kind, scorer.features, scorer.banks = "ridge", ["a"], __import__("collections").OrderedDict()
    scorer.w, scorer.mu, scorer.sd = np.array([0.0, 0.0]), np.array([0.0]), np.array([1.0])
    ev = Evaluator(target, budget=5)
    parent = "GGGGGGAAAACCCCCCAAGGGGGGAAAACCCCCC"
    kids = ["GGGCGGAAAACCGCCCAAGGGGGGAAAACCCCCC", "GGGGGGAAAACCCCCCAAGGAGGGAAAACCUCCC", "AGGGGGAAAACCCCCUAAGGGGGGAAAACCCCCC"]
    energy = b.energy_scores(target, parent, kids, [0.1] * len(parent), ev)
    residual = scorer(target, parent, kids, [0.1] * len(parent), ev)
    assert list(np.argsort(energy)) == list(np.argsort(residual))


@pytest.mark.skipif(not (baselines.DESIRNA_DIR / "DesiRNA.py").exists(), reason="DesiRNA checkout absent")
def test_desirna_adapter_replays_its_trajectory_with_method_times():
    target = Target("toy", "((((((....))))))..((((((....))))))")
    ev = Evaluator(target, budget=500)
    baselines.desirna(target, 0, ev, {"time_limit_s": 3, "replicas": 2})
    assert ev.rows and ev.internal_available is False
    times = [r["elapsed_s"] for r in ev.rows]
    assert times == sorted(times) and 0 <= times[0] and times[-1] <= 3.0
    assert len({r["sequence"] for r in ev.rows}) == len(ev.rows)


@pytest.mark.skipif(not (baselines.SAMPLINGDESIGN_DIR / "bin" / "main").exists(), reason="SamplingDesign not built")
def test_samplingdesign_adapter_replays_steps_with_cumulative_times():
    target = Target("toy", "((((((....))))))..((((((....))))))")
    ev = Evaluator(target, budget=5000)
    baselines.samplingdesign(target, 0, ev, {"time_limit_s": 6, "sample_size": 200})
    assert ev.rows and ev.internal_available is False
    times = [r["elapsed_s"] for r in ev.rows]
    assert times == sorted(times) and times[-1] <= 6.5
