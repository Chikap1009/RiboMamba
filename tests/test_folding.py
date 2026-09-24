"""Known-answer tests for the folding metrics (Phase 3).

Three kinds of check:
  1. Phase 0 numbers, measured with RNAfold/RNAsubopt by hand in session 02.
     If the oracle or its settings ever change, these fail.
  2. Brute force: list EVERY possible structure of a short sequence ourselves,
     score each with RNAeval's energy, and compute the probability and the
     ensemble defect straight from their definitions. No dynamic programming,
     so this independently checks how we use ViennaRNA's partition function.
  3. Statistical properties with a known expectation (a random sequence beats
     its own shuffles half the time) and reproducibility across processes.
"""

import math

import numpy as np
import pytest
import RNA

from ribomamba.eval.folding import (CANONICAL_PAIRS, check_target, fold_many, fold_one, model_details,
                                    pair_table)

KT = (37 + 273.15) * 1.98717 / 1000           # RT at 37 C in kcal/mol (R = 1.98717 cal/(mol K))


def all_structures(seq: str, i: int = 0, j: int | None = None) -> list[str]:
    """Every nested secondary structure of seq[i..j] (canonical pairs, hairpin loops >= 3)."""
    j = len(seq) - 1 if j is None else j
    if i > j:
        return [""]
    out = ["." + rest for rest in all_structures(seq, i + 1, j)]          # i unpaired
    for k in range(i + 4, j + 1):                                          # i paired with k
        if seq[i] + seq[k] in CANONICAL_PAIRS:
            for inner in all_structures(seq, i + 1, k - 1):
                for rest in all_structures(seq, k + 1, j):
                    out.append("(" + inner + ")" + rest)
    return out


def brute_force(seq: str, target: str) -> tuple[float, float]:
    """(P(target), NED against target) from the definitions, over an explicit list of structures."""
    fc = RNA.fold_compound(seq, model_details())
    structures = all_structures(seq)
    weights = np.array([math.exp(-fc.eval_structure(s) / KT) for s in structures])   # Boltzmann weights
    probs = weights / weights.sum()                                                  # divide by Z
    want = pair_table(target)
    wrong = np.array([sum(a != b for a, b in zip(pair_table(s), want)) for s in structures])
    return float(probs[structures.index(target)]), float(probs @ wrong / len(seq))


# ---- 1. Phase 0 known answers (RESULTS.md, "Phase 0 - oracle sanity checks") --------------------

def test_phase0_hairpin_numbers():
    r = fold_one("GGGAAACCC", target="(((...)))", n_shuffles=0)
    assert r["mfe_structure"] == "(((...)))" and r["mfe"] == -1.20
    assert r["mfe_match"] and r["bp_distance"] == 0
    assert r["p_target"] == pytest.approx(0.5065, abs=1e-4)      # RNAfold -p: 0.5065
    assert r["energy_gap"] == pytest.approx(0.20)                # rival ((....)). at -1.00
    assert r["paired_fraction"] == pytest.approx(6 / 9)


def test_phase0_shifted_register():
    r = fold_one("GGGAAACCA", n_shuffles=0)
    assert r["mfe_structure"] == "((....))." and r["mfe"] == -1.90
    assert r["p_mfe"] == pytest.approx(0.9386, abs=1e-4)          # RNAfold -p: 0.9386


def test_energy_gap_sign():
    # Target is the MFE: gap = rival - target > 0. Target is not the MFE: gap <= 0.
    assert fold_one("GGGAAACCA", target="((....)).", n_shuffles=0)["energy_gap"] == pytest.approx(1.90)
    r = fold_one("GGGAAACCC", target="((....)).", n_shuffles=0)
    assert not r["mfe_match"] and r["energy_gap"] == pytest.approx(-0.20)
    assert r["bp_distance"] == 5                                  # 3 pairs vs 2 pairs, none shared


# ---- 2. Brute force: probability and ensemble defect from their definitions ---------------------

@pytest.mark.parametrize("seq", ["GGGAAACCC", "GGGAAACCA", "GCGGAUUAGCUCAG", "ACGUGCAUGCGCAUG"])
def test_probability_and_ensemble_defect_match_brute_force(seq):
    r = fold_one(seq, n_shuffles=0)
    p, ned = brute_force(seq, r["mfe_structure"])
    # Tolerance 1e-3: with dangles = 2, ViennaRNA 2.7.2's partition function weights structures
    # whose outer pair closes on the LAST nucleotide 0.017 kcal/mol more favourably than RNAeval
    # does (found in session 04; 0.06 % on GGGAAACCC). The other sequences agree to ~1e-9.
    assert r["p_mfe"] == pytest.approx(p, abs=1e-3)
    assert r["ned_mfe"] == pytest.approx(ned, abs=1e-3)


def test_ensemble_defect_of_a_non_mfe_target_matches_brute_force():
    seq, target = "ACGUGCAUGCGCAUG", "..((((....))))."      # the runner-up; MFE is .(((((....)))))
    check_target(seq, target)
    r = fold_one(seq, target=target, n_shuffles=0)
    p, ned = brute_force(seq, target)
    assert r["p_target"] == pytest.approx(p, abs=1e-3)
    assert r["ned_target"] == pytest.approx(ned, abs=1e-3)


# ---- 3. Invalid targets are refused, not silently scored 0 -------------------------------------

@pytest.mark.parametrize("seq, target, message", [
    ("GGGAAACCC", "(((...))", "length mismatch"),
    ("GGGAAACCC", "((((..)))", "unbalanced"),
    ("GGGAAAACC", "(((...)))", "non-canonical"),        # G-A at (2, 6) can't pair
    ("GGGACCCC", "(((.))).", "hairpin loop of 1"),
])
def test_invalid_targets_raise(seq, target, message):
    with pytest.raises(ValueError, match=message):
        check_target(seq, target)


# ---- 4. Structure beyond chance: a known expectation --------------------------------------------

def test_random_sequences_beat_their_shuffles_half_the_time():
    # A uniformly random sequence and its dinucleotide shuffle are equally likely arrangements of
    # the same neighbour counts, so neither is more stable on average: beats_shuffles averages
    # exactly 0.5 in expectation (ties counted half). 120 sequences: standard error ~0.02.
    rng = np.random.default_rng(0)
    seqs = ["".join(rng.choice(list("ACGU"), size=60)) for _ in range(120)]
    df = fold_many(seqs, n_shuffles=20, seed=0, processes=4)
    assert abs(df["beats_shuffles"].mean() - 0.5) < 0.07
    assert abs(df["mfe_z"].drop_nans().mean()) < 0.3


def test_parallel_result_is_identical_to_serial_and_seeded():
    seqs = ["GGGAAACCC", "GCGGAUUUAGCUCAGUUGGGAGAGCGCCAGACUGAAGAUCUGGAGGUCCUGUGUUCGAUCCACAGAAUUCGCACCA",
            "ACGUGCAUGCGCAUG", "AUAUAUAUAUAUAUAUAUAU", "GGGGAAAACCCCUUUUGGGGAAAACCCC"]
    serial = fold_many(seqs, n_shuffles=10, seed=7, processes=1)
    parallel = fold_many(seqs, n_shuffles=10, seed=7, processes=3)
    assert serial.equals(parallel, null_equal=True)
    assert serial["index"].to_list() == list(range(len(seqs)))          # input order kept
    other_seed = fold_many(seqs, n_shuffles=10, seed=8, processes=1)
    assert not serial["shuffle_mfe_mean"].equals(other_seed["shuffle_mfe_mean"])
