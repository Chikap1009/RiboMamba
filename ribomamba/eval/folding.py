"""Folding-based metrics for RNA sequences, with ViennaRNA as the oracle (Phase 3).

For every sequence we fold once, compute the partition function once, and read
off several numbers (STUDY_GUIDE Part 5; logbook session 04, concept block):

  mfe, mfe_structure   the minimum-free-energy structure and its energy (kcal/mol)
  paired_fraction      share of nucleotides paired in that structure
  p_mfe, ned_mfe       how firmly the sequence holds its OWN MFE structure:
                       its Boltzmann probability, and the normalised ensemble
                       defect (expected fraction of nucleotides in the wrong state)
  mfe_z, beats_shuffles  structure beyond chance: the MFE compared with k
                       dinucleotide shuffles of the same sequence

and, when a target structure is given (the design setting, Phase 5):

  mfe_match, bp_distance   does the MFE structure equal the target, and how many pairs differ
  p_target, ned_target     probability of the exact target, ensemble defect against it
  energy_gap               E(best structure that isn't the target) - E(target);
                           > 0: the target is the MFE, by that margin; <= 0: it isn't

The oracle's settings are fixed here, in one place, because every number in
the project depends on them: ViennaRNA 2.7.2 (environment.yml), Turner 2004
parameters, 37 C, dangles = 2 (ViennaRNA's default), lonely pairs allowed.
"""

import math
import multiprocessing as mp
import os
import sys

import numpy as np
import polars as pl
import RNA

from ribomamba.data.structure_search import dinucleotide_shuffle

TEMPERATURE_C = 37.0
DANGLES = 2
N_SHUFFLES = 50                 # shuffles per sequence for the z-score (k)
GAP_WINDOWS_DCAL = (50, 100, 200, 400)   # widening subopt windows (0.01 kcal/mol units) to find the nearest rival
GAP_CAP_KCAL = 4.0              # a rival > 4 kcal/mol away (> 600x less likely) is reported as exactly 4
CANONICAL_PAIRS = {"GC", "CG", "AU", "UA", "GU", "UG"}
MIN_HAIRPIN = 3                 # ViennaRNA's minimum hairpin loop size


def model_details() -> "RNA.md":
    """The oracle's settings, written out explicitly rather than trusted as defaults."""
    md = RNA.md()
    md.temperature = TEMPERATURE_C
    md.dangles = DANGLES
    md.noLP = 0          # lonely (isolated) pairs allowed, ViennaRNA's default
    md.uniq_ML = 1       # required by subopt (the energy-gap search); doesn't change any energy
    return md


def pair_table(structure: str) -> list[int]:
    """Dot-bracket -> partner index for every position (-1 = unpaired). '(((...)))' -> [8,7,6,-1,-1,-1,2,1,0]."""
    stack, partner = [], [-1] * len(structure)
    for i, c in enumerate(structure):
        if c == "(":
            stack.append(i)
        elif c == ")":
            if not stack:
                raise ValueError(f"unbalanced structure: ')' at {i} has no partner")
            j = stack.pop()
            partner[i], partner[j] = j, i
        elif c != ".":
            raise ValueError(f"unexpected character {c!r} in structure (only '(', ')', '.')")
    if stack:
        raise ValueError(f"unbalanced structure: '(' at {stack[-1]} is never closed")
    return partner


def check_target(sequence: str, target: str) -> None:
    """Raise if the oracle could never form this target on this sequence.

    Catches the mistakes that would otherwise show up as silent zeros:
    wrong length, unbalanced brackets, a non-canonical pair (e.g. A-G, which
    ViennaRNA can't form), or a hairpin loop shorter than 3.
    """
    if len(sequence) != len(target):
        raise ValueError(f"length mismatch: sequence {len(sequence)} vs target {len(target)}")
    for i, j in enumerate(pair_table(target)):
        if j > i:
            if sequence[i] + sequence[j] not in CANONICAL_PAIRS:
                raise ValueError(f"non-canonical pair {sequence[i]}-{sequence[j]} at ({i}, {j})")
            if j - i - 1 < MIN_HAIRPIN and all(target[k] == "." for k in range(i + 1, j)):
                raise ValueError(f"hairpin loop of {j - i - 1} at ({i}, {j}); minimum is {MIN_HAIRPIN}")


def _nearest_rival_gap(fc, structure: str, e_structure: float) -> float:
    """E(best structure other than `structure`) - E(structure), capped at GAP_CAP_KCAL.

    Enumerates suboptimal structures in widening energy windows above the MFE
    and stops at the first window containing a structure that isn't `structure`.
    Must be called after fc.mfe() (subopt reuses its tables).
    """
    for window in GAP_WINDOWS_DCAL:
        others = [s.energy for s in fc.subopt(window) if s.structure != structure]
        if others:
            return min(round(min(others) - e_structure, 2), GAP_CAP_KCAL)
    return GAP_CAP_KCAL


def fold_one(sequence: str, target: str | None = None, n_shuffles: int = N_SHUFFLES,
             seed=0) -> dict:
    """All ViennaRNA metrics for one sequence (see the module docstring). Energies in kcal/mol."""
    fc = RNA.fold_compound(sequence, model_details())
    mfe_structure, mfe = fc.mfe()
    mfe = round(mfe, 2)                              # energies are whole 0.01 kcal/mol; drop float32 noise
    row = {
        "length": len(sequence),
        "mfe_structure": mfe_structure,
        "mfe": mfe,
        "mfe_per_nt": mfe / len(sequence),
        "paired_fraction": 1 - mfe_structure.count(".") / len(sequence),
    }
    if target is not None:
        check_target(sequence, target)
        e_target = round(fc.eval_structure(target), 2)
        row["energy_gap"] = _nearest_rival_gap(fc, target, e_target)      # before pf: subopt uses the MFE tables
        row["mfe_match"] = mfe_structure == target
        row["bp_distance"] = RNA.bp_distance(mfe_structure, target)

    fc.exp_params_rescale(mfe)                       # scale Boltzmann factors so long sequences don't overflow
    fc.pf()                                          # partition function Z and base-pair probabilities
    row["p_mfe"] = fc.pr_structure(mfe_structure)    # e^(-E/RT) / Z
    row["ned_mfe"] = fc.ensemble_defect(mfe_structure)
    if target is not None:
        row["p_target"] = fc.pr_structure(target)
        row["ned_target"] = fc.ensemble_defect(target)

    if n_shuffles:
        rng = np.random.default_rng(seed)
        md = model_details()
        shuffled = np.array([round(RNA.fold_compound(dinucleotide_shuffle(sequence, rng), md).mfe()[1], 2)
                             for _ in range(n_shuffles)])                  # (k,) kcal/mol
        sd = float(shuffled.std(ddof=1)) if n_shuffles > 1 else 0.0
        row["shuffle_mfe_mean"] = float(shuffled.mean())
        row["shuffle_mfe_sd"] = sd
        # z < 0: more stable than its own rearrangements. Undefined when every shuffle ties (sd = 0).
        row["mfe_z"] = (mfe - shuffled.mean()) / sd if sd > 0 else math.nan
        # P(sequence more stable than a random shuffle of itself), ties counted half,
        # so it is exactly 0.5 in expectation when the order of letters carries no structure.
        row["beats_shuffles"] = float(np.mean(mfe < shuffled) + 0.5 * np.mean(mfe == shuffled))
    return row


def _fold_job(job: tuple) -> dict:
    index, sequence, target, n_shuffles, seed = job
    row = fold_one(sequence, target, n_shuffles, seed=(seed, index))   # per-sequence seed: independent of chunking
    row["index"] = index
    return row


def fold_many(sequences: list[str], targets: list[str] | None = None, n_shuffles: int = N_SHUFFLES,
              seed: int = 0, processes: int | None = None) -> pl.DataFrame:
    """fold_one for every sequence, in parallel; one row per sequence, in input order.

    Each sequence's shuffles are seeded by (seed, its index), so the result is
    identical whatever the number of processes or how the work is chunked.
    """
    if targets is not None and len(targets) != len(sequences):
        raise ValueError("need exactly one target per sequence")
    jobs = [(i, s, targets[i] if targets is not None else None, n_shuffles, seed)
            for i, s in enumerate(sequences)]
    processes = processes or os.cpu_count() or 1
    if processes == 1:
        rows = [_fold_job(j) for j in jobs]
    else:
        # "spawn" starts clean worker processes: safe even if the parent has already used the GPU,
        # and unlike "fork" it can't deadlock on locks held by polars' threads. Each worker
        # re-imports the main program from its file. If that file doesn't exist (a script piped
        # in as `python - <<EOF`), every worker dies at start-up and Pool silently restarts it
        # forever (session 04: 179,339 crashes in 10 minutes, no error raised). Refuse instead.
        main_file = getattr(sys.modules["__main__"], "__file__", None)
        if main_file is not None and not os.path.exists(main_file):
            raise RuntimeError(f"fold_many(processes>1) needs the main program in a real file, not {main_file!r}; "
                               "save the script to a .py file or pass processes=1")
        with mp.get_context("spawn").Pool(processes) as pool:
            rows = pool.map(_fold_job, jobs, chunksize=max(1, len(jobs) // (processes * 8)))
    return pl.DataFrame(rows).sort("index")
