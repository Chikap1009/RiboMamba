"""Known-answer tests for the EternaFold wrapper (the second oracle, Phase 3)."""

import os
import subprocess

import numpy as np
import pytest

from ribomamba.eval.eternafold import (_params, _read_posteriors, _read_structure, ensemble_defect,
                                       eternafold_many, output_target, run_eternafold)
from ribomamba.eval.folding import pair_table

pytestmark = pytest.mark.skipif("ETERNAFOLD_PARAMETERS" not in os.environ,
                                reason="needs the ribomamba conda env (EternaFold)")

TRNA = "GCGGAUUUAGCUCAGUUGGGAGAGCGCCAGACUGAAGAUCUGGAGGUCCUGUGUUCGAUCCACAGAAUUCGCACCA"   # yeast tRNA-Phe


def test_readme_example_reproduced(tmp_path):
    # EternaFold's README: this hammerhead ribozyme's MEA structure (default estimator, gamma 6).
    seq = "CGCUGUCUGUACUUGUAUCAGUACACUGACGAGUCCCUAAAGGACGAAACAGCG"
    (tmp_path / "in.fasta").write_text(f">t\n{seq}\n")
    (tmp_path / "out").mkdir()
    files = [tmp_path / "in.fasta"]
    run_eternafold(files, ["--parens", output_target(files, tmp_path / "out")], processes=2)
    assert _read_structure(tmp_path / "out" / "in.fasta") == "(((((((((((((......))))))..)....((((.....))))...))))))"


def test_one_sequence_and_several_sequences_give_the_same_answer():
    # A single input needs an output FILE, several need a DIRECTORY (EternaFold's rule); both paths
    # must work and agree.
    alone = eternafold_many([TRNA], processes=2)[0]
    together = eternafold_many(["GGGGAAAACCCC", TRNA], processes=2)[1]
    assert alone == together


def test_probabilities_are_valid_and_agree_with_the_most_probable_structure():
    rows = eternafold_many(["GGGGAAAACCCC", TRNA], compare=[["((((....))))"], ["." * len(TRNA)]], processes=4)
    assert rows[0]["ef_structure"] == "((((....))))" and rows[0]["ef_match_0"]
    assert rows[0]["ef_ned_0"] == rows[0]["ef_ned_own"] < 0.2
    assert 0.0 <= rows[1]["ef_ned_own"] <= 1.0
    assert rows[1]["ef_ned_0"] > rows[1]["ef_ned_own"]           # "all unpaired" fits tRNA worse than its best guess


def test_ensemble_defect_matches_monte_carlo_over_eternafolds_own_samples(tmp_path):
    # NED from pair probabilities must equal the average fraction of wrong nucleotides over
    # structures SAMPLED from the same ensemble (2,000 samples: standard error ~0.005).
    (tmp_path / "t.fasta").write_text(f">t\n{TRNA}\n")
    (tmp_path / "post").mkdir()
    files = [tmp_path / "t.fasta"]
    run_eternafold(files, ["--posteriors", "0.00001", output_target(files, tmp_path / "post")], processes=2)
    pairs, paired = _read_posteriors(tmp_path / "post" / "t.fasta", len(TRNA))
    assert paired.max() <= 1.0 + 1e-6
    reference = eternafold_many([TRNA], processes=2)[0]["ef_structure"]
    sampled = subprocess.run(["mpirun", "-np", "2", "--oversubscribe", "eternafold", "sample",
                              str(tmp_path / "t.fasta"), "--params", _params(), "--nsamples", "2000"],
                             check=True, capture_output=True, text=True).stdout.split()
    sampled = [s for s in sampled if len(s) == len(TRNA) and set(s) <= set("().")]
    assert len(sampled) == 2000
    want = np.array(pair_table(reference))
    monte_carlo = np.mean([np.mean(np.array(pair_table(s)) != want) for s in sampled])
    assert ensemble_defect(pairs, paired, reference) == pytest.approx(monte_carlo, abs=0.02)
