"""Run DesiRNA (unmodified checkout) with REAL per-round timestamps, optionally energy-screened.

Executed with the `desirna` env's Python by ribomamba/design/baselines.py. Environment:
  DESIRNA_DIR        the pinned checkout
  DESIRNA_TIMELOG    file to append one line per replica per replica-exchange round:
                     "<seconds since launch>\t<replica>\t<sim_step>\t<score>\t<sequence>", flushed
  DESIRNA_T0         time.monotonic() at launch, taken by the parent (CLOCK_MONOTONIC is
                     system-wide on Linux and excludes suspend)
  DESIRNA_FILTER_K   optional: energy pre-screen of DesiRNA's own proposals (best of K by E(target))

Why: DesiRNA writes its trajectory only at the end and checks its time limit only between
rounds, so a nominal 128 s run can last ~240 s; stamping candidates by step fraction credited
post-deadline work (review of 2026-09-28). Here each round's replica states are logged when they
exist, and the parent kills the process group at the deadline, counting only rows logged by then.
The patch wraps remc.replica_exchange (called once per round in the parent process, after the
replicas' Monte Carlo moves); nothing else in DesiRNA changes.
"""

import os
import runpy
import sys
import time

DESIRNA_DIR = os.environ["DESIRNA_DIR"]
T0 = float(os.environ[os.environ.get("DESIRNA_T0_FROM", "DESIRNA_T0")])
LOG = open(os.environ["DESIRNA_TIMELOG"], "a", buffering=1)
sys.path.insert(0, DESIRNA_DIR)

import RNA  # noqa: E402

from utils import energy_scores as es  # noqa: E402
from utils import replica_exchange_monte_carlo as remc  # noqa: E402
from utils import sequence_utils as seq_utils  # noqa: E402

_original_exchange = remc.replica_exchange


def _timed_exchange(seq_score_list, stats_obj, sim_options):
    out = _original_exchange(seq_score_list, stats_obj, sim_options)
    lst = out[0]
    now = time.monotonic() - T0
    for s in lst:
        LOG.write(f"{now:.4f}\t{s.replica_num}\t{stats_obj.step}\t{s.scoring_function}\t{s.sequence}\n")
    LOG.flush()
    os.fsync(LOG.fileno())
    return out


remc.replica_exchange = _timed_exchange

K = int(os.environ.get("DESIRNA_FILTER_K", "0") or 0)
if K > 1:
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
        best = min(sorted(set(candidates)), key=lambda s: (RNA.fold_compound(s).eval_structure(target), s))
        scored = _original_score(best, input_file, sim_options)
        scored.get_replica_num(sequence_obj.replica_num)
        scored.get_temp_shelf(sequence_obj.temp_shelf)
        return scored

    seq_utils.mutate_sequence = _filtered_mutate

sys.argv = [os.path.join(DESIRNA_DIR, "DesiRNA.py")] + sys.argv[1:]
runpy.run_path(os.path.join(DESIRNA_DIR, "DesiRNA.py"), run_name="__main__")
