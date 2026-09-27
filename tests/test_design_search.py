"""Budgeted evaluation and the cheap design controls: shared starts, legal moves, budgets, traces."""

import math

import numpy as np
import pytest

from ribomamba.design import search
from ribomamba.design.scoring import Score
from ribomamba.design.search import (CONTROLS, BudgetExhausted, DeadlineReached, Evaluator, Target,
                                     pick_feedback_sites, shared_start)
from ribomamba.eval.folding import CANONICAL_PAIRS

TARGET = Target("toy:two_stems", "((((....))))..((((....))))")


def run(method: str, seed: int = 0, budget: int = 40, target: Target = TARGET) -> Evaluator:
    ev = Evaluator(target, budget)
    with pytest.raises(BudgetExhausted):
        CONTROLS[method](target, seed, ev, {})
    return ev


def test_sites_cover_every_position_once():
    covered = sorted(p for site in TARGET.sites for p in site)
    assert covered == list(range(len(TARGET)))
    assert all(TARGET.site_of[p] == k for k, site in enumerate(TARGET.sites) for p in site)


@pytest.mark.parametrize("method", sorted(CONTROLS))
def test_budget_trace_and_legal_designs(method):
    ev = run(method)
    rows = ev.rows
    assert len(rows) == 40 and [r["eval_index"] for r in rows] == list(range(40))
    assert all(r["target_feasible"] for r in rows)              # every target pair stays canonical
    for r in rows:
        seq = r["sequence"]
        assert all(seq[i] + seq[j] in CANONICAL_PAIRS for i, j in enumerate(TARGET.pt) if j > i)
    misses = [r["cum_cache_misses"] for r in rows]
    for prev, r in zip([None] + rows, rows):
        grew = r["cum_cache_misses"] - (prev["cum_cache_misses"] if prev else 0)
        assert grew == (0 if r["cache_hit"] else 1)
        assert r["cum_oracle_pf"] == r["cum_cache_misses"]        # one partition function per miss
    assert misses[-1] == len({r["sequence"] for r in rows})
    assert rows[-1]["cum_internal_pf"] == 0                       # controls make no hidden calls


def test_all_methods_share_the_start_and_it_depends_on_the_seed():
    starts = {m: run(m, budget=1).rows[0]["sequence"] for m in CONTROLS}
    assert len(set(starts.values())) == 1
    assert starts["random_pairs"] == shared_start(TARGET, 0) != shared_start(TARGET, 1)
    start = starts["random_pairs"]
    assert all(start[i] + start[j] in ("GC", "CG") for i, j in enumerate(TARGET.pt) if j > i)
    assert all(start[i] == "A" for i, j in enumerate(TARGET.pt) if j < 0)


def test_runs_are_reproducible_per_seed():
    a, b, c = run("feedback_pair_edits", 3), run("feedback_pair_edits", 3), run("feedback_pair_edits", 4)
    assert [r["sequence"] for r in a.rows] == [r["sequence"] for r in b.rows]
    assert [r["sequence"] for r in a.rows] != [r["sequence"] for r in c.rows]


@pytest.mark.parametrize("method", ["random_pair_edits", "feedback_pair_edits"])
def test_edits_change_one_or_two_sites_of_the_accepted_parent(method):
    ev = run(method, budget=60)
    rows = ev.rows
    current = 0
    for r in rows[1:]:
        assert r["parent_index"] == current                     # always the currently accepted candidate
        parent = rows[r["parent_index"]]["sequence"]
        changed = [k for k, (x, y) in enumerate(zip(parent, r["sequence"])) if x != y]
        assert changed == r["changed_positions"]
        sites = {int(TARGET.site_of[p]) for p in changed}
        assert 1 <= len(sites) <= 2
        for k in sites:                                          # every chosen site actually changed
            assert all(parent[p] != r["sequence"][p] for p in TARGET.sites[k]) or len(TARGET.sites[k]) == 2
        if r["objective"] <= rows[current]["objective"]:
            current = r["eval_index"]


def test_accepted_objective_never_increases():
    ev = run("feedback_pair_edits", budget=60)
    accepted = [ev.rows[0]["objective"]]
    for r in ev.rows[1:]:
        if r["objective"] <= accepted[-1]:
            accepted.append(r["objective"])
    assert accepted == sorted(accepted, reverse=True) and accepted[-1] <= ev.rows[0]["objective"]


def _fake_score(n: int, defect: np.ndarray, competitor=None, competitor_p=None) -> Score:
    return Score(sequence="A" * n, ned=float(defect.mean()), defect=defect,
                 competitor=np.full(n, -1) if competitor is None else competitor,
                 competitor_p=np.zeros(n) if competitor_p is None else competitor_p)


def test_feedback_sites_follow_the_defect():
    t = Target("toy:hairpin", "((((....))))")                 # sites: 4 pairs + 4 loop positions
    defect = np.zeros(len(t))
    defect[[1, 10]] = 1.0                                      # only the pair (1, 10) is defective
    rng = np.random.default_rng(0)
    firsts = [pick_feedback_sites(t, _fake_score(len(t), defect), rng)[0] for _ in range(2000)]
    share = np.mean([f == t.site_of[1] for f in firsts])
    expected = 1.01 / (1.01 + 7 * search.FEEDBACK_FLOOR)       # weights: defect + floor
    assert share == pytest.approx(expected, abs=0.02)


def test_feedback_second_site_is_the_strongest_competitor():
    t = Target("toy:hairpin", "((((....))))")
    defect = np.zeros(len(t))
    defect[[1, 10]] = 1.0
    competitor, competitor_p = np.full(len(t), -1), np.zeros(len(t))
    competitor[1], competitor_p[1] = 6, 0.8                    # position 1 is drawn to loop position 6
    rng = np.random.default_rng(1)
    pairs = [pick_feedback_sites(t, _fake_score(len(t), defect, competitor, competitor_p), rng)
             for _ in range(400)]
    two = [p for p in pairs if len(p) == 2 and p[0] == t.site_of[1]]
    assert two and all(p[1] == t.site_of[6] for p in two)


def test_deadline_stops_a_unit():
    ev = Evaluator(TARGET, budget=10, deadline=0.0)
    with pytest.raises(DeadlineReached):
        ev("A" * len(TARGET))
    assert ev.count == 0


def test_cache_hits_spend_budget_but_no_oracle_calls():
    ev = Evaluator(TARGET, budget=3)
    seq = shared_start(TARGET, 0)
    ev(seq)
    ev(seq)
    assert ev.rows[1]["cache_hit"] and ev.rows[1]["cum_oracle_pf"] == 1 and ev.rows[1]["cum_proposals"] == 2
    assert math.isclose(ev.rows[0]["ned"], ev.rows[1]["ned"])
