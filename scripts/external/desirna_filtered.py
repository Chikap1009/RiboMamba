"""Run DesiRNA (unmodified checkout) with its mutation proposals pre-screened by target energy.

Executed with the `desirna` env's Python by ribomamba/design/baselines.py (method desirna_efilter).
DESIRNA_DIR and DESIRNA_FILTER_K come from the environment; all other arguments are DesiRNA's own.

The patch: DesiRNA's seq_utils.mutate_sequence draws one mutation (paired positions changed
together) and scores it with es.score_sequence (a partition function). Here it is called K times
with scoring replaced by a no-op, to draw K candidate strings with DesiRNA's own proposal logic;
the one with the lowest E(target) (ViennaRNA eval_structure, 37 C, dangles 2, the loaded Turner
parameters) is then scored for real and returned. Metropolis acceptance, replica exchange and
everything else are untouched. The patch is applied before DesiRNA's worker pool forks.
"""

import os
import runpy
import sys

DESIRNA_DIR = os.environ["DESIRNA_DIR"]
K = int(os.environ["DESIRNA_FILTER_K"])
sys.path.insert(0, DESIRNA_DIR)

import RNA  # noqa: E402

from utils import energy_scores as es  # noqa: E402
from utils import sequence_utils as seq_utils  # noqa: E402

_original_mutate = seq_utils.mutate_sequence
_original_score = es.score_sequence


class _Raw:
    def __init__(self, sequence):
        self.sequence = sequence

    def get_replica_num(self, _):
        pass

    def get_temp_shelf(self, _):
        pass


def _filtered_mutate(sequence_obj, nt_list, sim_options, input_file):
    seq_utils.es.score_sequence = lambda s, inp, opt: _Raw(s)
    try:
        candidates = [_original_mutate(sequence_obj, nt_list, sim_options, input_file).sequence for _ in range(K)]
    finally:
        seq_utils.es.score_sequence = _original_score
    target = input_file.sec_struct
    distinct = sorted(set(candidates))
    best = min(distinct, key=lambda s: (RNA.fold_compound(s).eval_structure(target), s))
    scored = _original_score(best, input_file, sim_options)
    scored.get_replica_num(sequence_obj.replica_num)
    scored.get_temp_shelf(sequence_obj.temp_shelf)
    return scored


seq_utils.mutate_sequence = _filtered_mutate
sys.argv = [os.path.join(DESIRNA_DIR, "DesiRNA.py")] + sys.argv[1:]
runpy.run_path(os.path.join(DESIRNA_DIR, "DesiRNA.py"), run_name="__main__")
