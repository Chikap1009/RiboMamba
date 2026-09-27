"""MFE-feedback coordinated repair: a cheap-oracle, non-neural repair control (added 2026-09-27).

Motivation (ew_smoke64_v1): RNAinverse, an MFE-distance adaptive walk
(Hofacker et al. 1994), reached unique-MFE success on hard Eterna web puzzles
far sooner in wall time than the ensemble-defect searches. This control asks
whether the same cheap feedback, used with the project's coordinated paired
moves, closes that gap. It is built from established ideas (adaptive walks,
paired mutations, lexicographic objectives), not a contribution by itself.

Each candidate costs ONE MFE fold and one structure evaluation (no partition
function); a zero-band subopt is added only when the MFE already equals the
target, to test uniqueness. These calls are counted as the method's own
(internal) calls; the harness's full re-scoring of each candidate is
measurement only and is subtracted from its wall time, as for SAMFEO.

  start      the shared start (the same as every repair method)
  objective  (base-pair distance of the MFE structure to the target,
              E(target) - E(MFE)), lexicographic, lower is better; ties accepted
  sites      1st: the site of a position whose MFE pairing state is wrong
             (uniform over wrong positions); with probability 1/2 a 2nd: the
             site of that position's WRONG partner in the MFE (the competing
             interaction), else a sequence neighbour
  moves      the controls' legal resampling (a pair to a different canonical
             pair, an unpaired base to a different base)
  stop       when the target is the unique MFE structure (status early_stop)
"""

import numpy as np
import RNA

from ribomamba.design.scoring import Counters, unformable_pairs
from ribomamba.design.search import (TWO_SITE_PROB, Evaluator, Target, neighbour_site, pick_random_sites, resample,
                                     rng_for, shared_start)
from ribomamba.eval.folding import model_details, pair_table

MFE_REPAIR_SETTINGS = {"objective": "(bp distance, E(target) - E(MFE)) lexicographic", "two_site_prob": TWO_SITE_PROB,
                       "second_site": "MFE wrong partner, else sequence neighbour", "stop": "unique MFE"}


def mfe_feedback(sequence: str, target: Target, counters: Counters) -> tuple[list[int], tuple, bool]:
    """(MFE partner list, objective key, unique-MFE success) from one counted MFE fold."""
    fc = RNA.fold_compound(sequence, model_details())
    structure, mfe = fc.mfe()
    counters.mfe += 1
    if unformable_pairs(sequence, target.pt):
        return pair_table(structure), (RNA.bp_distance(structure, target.structure), float("inf")), False
    e_target = fc.eval_structure(target.structure)
    counters.eval += 1
    distance = RNA.bp_distance(structure, target.structure)
    solved = False
    if structure == target.structure:
        optimal = [o.structure for o in fc.subopt(0)]
        counters.subopt += 1
        solved = optimal == [target.structure]
    return pair_table(structure), (distance, round(e_target - mfe, 2)), solved


def pick_mfe_sites(target: Target, mfe_pt: list[int], rng: np.random.Generator) -> list[int]:
    wrong = [i for i, (a, b) in enumerate(zip(mfe_pt, target.pt)) if a != b]
    if not wrong:                                   # MFE matches but is not unique: move anywhere
        return pick_random_sites(target, None, rng)
    i = wrong[int(rng.integers(len(wrong)))]
    first = int(target.site_of[i])
    if rng.random() < TWO_SITE_PROB:
        k = mfe_pt[i]
        if k >= 0 and int(target.site_of[k]) != first:
            return [first, int(target.site_of[k])]
        second = neighbour_site(target, first, rng)
        if second is not None:
            return [first, second]
    return [first]


def mfe_repair(target: Target, seed: int, evaluate: Evaluator, settings: dict) -> None:
    rng = rng_for("mfe_repair", target.id, seed)
    sequence = shared_start(target, seed)
    evaluate.check()
    mfe_pt, key, solved = mfe_feedback(sequence, target, evaluate.internal)
    current = evaluate(sequence, objective=float(key[0]) + key[1] / 1000)
    while not solved:
        evaluate.check()
        child = resample(current.sequence, target, pick_mfe_sites(target, mfe_pt, rng), rng)
        child_pt, child_key, child_solved = mfe_feedback(child, target, evaluate.internal)
        proposal = evaluate(child, parent=current.index, objective=float(child_key[0]) + child_key[1] / 1000)
        if child_key <= key:
            current, mfe_pt, key, solved = proposal, child_pt, child_key, child_solved


MFE_METHODS = {"mfe_repair": mfe_repair}
