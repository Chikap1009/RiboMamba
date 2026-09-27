"""Robust candidate scoring for the repair pilot: known answers, impossible targets, tie policies.

The brute-force helpers from test_folding enumerate every structure of a short
sequence, so probabilities and ensemble defects are checked against their
definitions, including for targets the sequence cannot form.
"""

import math

import numpy as np
import pytest
import RNA

from ribomamba.design.scoring import Counters, positional_defect, score, unformable_pairs
from ribomamba.eval.folding import fold_one, model_details, pair_table
from test_folding import KT, all_structures    # tests/ is on sys.path under pytest's default import mode


def brute_force(seq: str, target: str) -> tuple[float, float]:
    """(P(target), NED against target) from the definitions, over every structure of seq.

    Unlike test_folding's version, the target need not be formable: then it is not
    among the enumerated structures and its probability is 0 by definition.
    """
    fc = RNA.fold_compound(seq, model_details())
    structures = all_structures(seq)
    weights = np.array([math.exp(-fc.eval_structure(s) / KT) for s in structures])
    probs = weights / weights.sum()
    want = pair_table(target)
    wrong = np.array([sum(a != b for a, b in zip(pair_table(s), want)) for s in structures])
    p = float(probs[structures.index(target)]) if target in structures else 0.0
    return p, float(probs @ wrong / len(seq))


def test_feasible_target_agrees_with_fold_one_and_counts_calls():
    c = Counters()
    s = score("GGGAAACCC", "(((...)))", counters=c)
    r = fold_one("GGGAAACCC", target="(((...)))", n_shuffles=0)
    assert s.target_feasible and s.mfe_backtrack and s.mfe_any and s.umfe and s.mfe_ties == 1
    assert s.p_target == pytest.approx(r["p_target"], abs=1e-12)
    assert s.ned == pytest.approx(r["ned_target"], abs=1e-9)
    assert s.log_p_target == pytest.approx(math.log(s.p_target), abs=1e-5)      # exact where p is representable
    assert (c.mfe, c.pf, c.subopt, c.eval) == (1, 1, 1, 1)


@pytest.mark.parametrize("seq, target", [("ACGUGCAUGCGCAUG", "..((((....))))."),
                                         ("GCGGAUUAGCUCAG", "((((.....)))).")])
def test_ned_matches_viennas_ensemble_defect_and_brute_force(seq, target):
    s = score(seq, target)
    fc = RNA.fold_compound(seq, model_details())
    fc.exp_params_rescale(fc.mfe()[1])
    fc.pf()
    assert s.ned == pytest.approx(fc.ensemble_defect(target), abs=1e-9)
    p, ned = brute_force(seq, target)
    assert s.ned == pytest.approx(ned, abs=1e-3)          # 1e-3: the dangles=2 end-pair quirk (test_folding)
    assert s.p_target == pytest.approx(p, abs=1e-3)       # 0 for the unformable second target


def test_viennarna_gives_an_impossible_target_nonzero_probability():
    # The reason scoring.py sets p_target itself: ViennaRNA 2.7.2 evaluates a target
    # containing a G-A pair without complaint. If this ever starts raising or returning
    # 0, the explicit handling is still correct, but the documented pitfall has changed.
    fc = RNA.fold_compound("GGGAAAACC", model_details())
    fc.exp_params_rescale(fc.mfe()[1])
    fc.pf()
    assert fc.pr_structure("(((...)))") > 0.01


def test_impossible_target_scores_zero_probability_and_keeps_feedback():
    seq, target = "GGGAAAACC", "(((...)))"                 # G-A at (2, 6) cannot pair
    c = Counters()
    s = score(seq, target, counters=c)                     # must not raise
    assert s.valid and s.error is None
    assert not s.target_feasible and s.infeasible_pairs == 1
    assert s.p_target == 0.0 and s.log_p_target == -math.inf
    assert not (s.mfe_backtrack or s.mfe_any or s.umfe)
    assert s.mfe_structure == "((.....))" and s.bp_distance == 1
    _, ned = brute_force(seq, target)                      # NED from the definition, over every structure
    assert s.ned == pytest.approx(ned, abs=1e-3)
    assert s.defect[2] == pytest.approx(1.0) and s.defect[6] == pytest.approx(1.0)   # the unformable pair
    assert c.subopt == 0 and c.eval == 0 and c.mfe == 1 and c.pf == 1


def test_pair_enclosing_too_few_nucleotides_is_unformable_even_with_canonical_letters():
    seq, target = "GGGACCC", "(((.)))"                     # (2, 4) encloses one nucleotide
    assert unformable_pairs(seq, pair_table(target)) == [(2, 4)]
    s = score(seq, target)
    assert not s.target_feasible and s.p_target == 0.0 and s.log_p_target == -math.inf


def test_three_tie_policies_on_a_degenerate_mfe():
    # CGCGUCCCUGCUCC has two optimal structures at -0.90 kcal/mol; ViennaRNA backtracks the first.
    seq, backtracked, tied = "CGCGUCCCUGCUCC", ".((......))...", ".(((....)))..."
    a = score(seq, backtracked)
    assert a.mfe_backtrack and a.mfe_any and not a.umfe and a.mfe_ties == 2
    b = score(seq, tied)
    assert not b.mfe_backtrack and b.mfe_any and not b.umfe and b.mfe_ties == 2
    c = score(seq, "..............")                       # open chain: not optimal at all
    assert not (c.mfe_backtrack or c.mfe_any or c.umfe) and c.mfe_ties == 0


@pytest.mark.parametrize("seq, message", [("GGGTAACCC", "letters outside"), ("GGGAAACC", "length")])
def test_invalid_candidates_are_failures_without_oracle_calls(seq, message):
    c = Counters()
    s = score(seq, "(((...)))", counters=c)
    assert not s.valid and message in s.error and s.objective == math.inf
    assert s.p_target == 0.0 and math.isnan(s.ned) and not s.umfe
    assert (c.mfe, c.pf, c.subopt, c.eval) == (0, 0, 0, 0)


def test_positional_defect_and_competitors_from_a_known_matrix():
    # 4 positions, target (0,3) paired, 1 and 2 unpaired. P(0,3)=0.6, P(1,3)=0.3, P(1,2)=0.
    P = np.zeros((4, 4))
    P[0, 3] = P[3, 0] = 0.6
    P[1, 3] = P[3, 1] = 0.3
    d = positional_defect(P, [3, -1, -1, 0])
    assert d == pytest.approx([0.4, 0.3, 0.0, 0.4])       # paired: 1 - P(i,t_i); unpaired: sum_j P(i,j)
    s = score("GGGGAAACCCC", "((((...))))")
    pt = pair_table("((((...))))")
    for i, j in enumerate(pt):                             # a competitor is never the target partner
        assert s.competitor[i] != j or s.competitor_p[i] == 0
    assert (s.competitor_p >= 0).all() and (s.competitor_p <= 1 + 1e-9).all()
