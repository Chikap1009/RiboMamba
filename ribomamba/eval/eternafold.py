"""EternaFold: the second, independent folding oracle (Phase 3, D-013).

ViennaRNA scores structures with Turner's measured energy tables. EternaFold
(Wayment-Steele et al., Nature Methods 2022) is a different kind of model:
CONTRAfold's statistical model with parameters LEARNED from Eterna's
chemical-mapping experiments on designed RNAs. A result both oracles agree on
is less likely to be one oracle's quirk (Goodhart's law; logbook session 04).

Its scores are not kcal/mol, so we only take structure-level outputs:
  ef_structure   the single most probable structure (--viterbi): the same
                 kind of estimate as ViennaRNA's MFE structure
  pair probabilities (--posteriors) -> ensemble defects against any structure

How it is run. The bioconda build (eternafold 1.3.1) was compiled for MPI: its
main process only hands work to worker processes. Started on its own it has
no workers and spins at 100 % CPU forever (found in session 04). So it is
always launched as `mpirun -np P eternafold predict file1 file2 ...`: one MPI
start-up (~2 s) for a whole batch of sequences, spread over P processes.
"""

import os
import subprocess
import tempfile
from pathlib import Path

import numpy as np

from ribomamba.eval.folding import pair_table

POSTERIOR_CUTOFF = 1e-5          # pair probabilities below this are not written (error <= N * 1e-5 per base)
CHUNK = 2000                     # sequences per mpirun call (keeps the command line short)


def _params() -> str:
    path = os.environ.get("ETERNAFOLD_PARAMETERS")     # set by the conda package's activation script
    if not path or not Path(path).exists():
        raise RuntimeError("ETERNAFOLD_PARAMETERS is not set: run inside `conda activate ribomamba`")
    return path


def output_target(files: list[Path], directory: Path) -> str:
    """Where --parens / --posteriors should write: a DIRECTORY for several inputs, but a FILE
    (directory/<input name>) for a single input; given a directory then, EternaFold exits
    with an error. Either way the result for input f ends up at directory / f.name."""
    return str(directory / files[0].name) if len(files) == 1 else str(directory)


def run_eternafold(files: list[Path], args: list[str], processes: int | None = None) -> None:
    """One `mpirun ... eternafold predict <files> --params <EternaFold> <args>` call.

    At least 2 MPI processes: 1 coordinator + >= 1 worker (with 1 it never finishes).
    """
    n = max(2, min(processes or os.cpu_count() or 2, len(files) + 1))
    cmd = ["mpirun", "-np", str(n), "--oversubscribe",
           "eternafold", "predict", *map(str, files), "--params", _params(), *args]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=3600)


def _read_structure(path: Path) -> str:
    lines = [line.strip() for line in open(path) if line.strip()]
    return lines[lines.index(">structure") + 1]


def _read_posteriors(path: Path, length: int) -> tuple[dict, np.ndarray]:
    """Pair probabilities {(i, j): p} with i < j (0-based), and P(i paired) for every i.

    The file lists, for each position i (1-based), only partners j > i
    ("i BASE j:p j:p ..."), so P(i paired) adds i's own line AND every line
    where i appears as a partner.
    """
    pairs, paired = {}, np.zeros(length)
    for line in open(path):
        fields = line.split()
        i = int(fields[0]) - 1
        for token in fields[2:]:
            j, p = token.split(":")
            j, p = int(j) - 1, float(p)
            pairs[(i, j)] = p
            paired[i] += p
            paired[j] += p
    return pairs, paired


def ensemble_defect(pairs: dict, paired: np.ndarray, structure: str) -> float:
    """NED of `structure` under an ensemble given by pair probabilities.

    NED = 1 - (1/N) * sum_i P(i is in its state in `structure`), where that
    probability is P(i pairs with its partner) or P(i unpaired) = 1 - P(i paired).
    """
    partner = pair_table(structure)
    correct = [pairs.get((min(i, j), max(i, j)), 0.0) if j >= 0 else 1.0 - paired[i]
               for i, j in enumerate(partner)]
    return float(1.0 - np.mean(correct))


def eternafold_many(sequences: list[str], compare: list[list[str]] | None = None,
                    processes: int | None = None) -> list[dict]:
    """EternaFold's view of each sequence.

    Returns per sequence: ef_structure (most probable), ef_ned_own (how firmly
    it holds that structure), and, for each structure s in compare[k] (one
    list per sequence, e.g. [ViennaRNA's MFE structure, a design target]),
    ef_ned_k = NED of s under EternaFold's ensemble and ef_match_k = (s == ef_structure).
    """
    out = []
    for start in range(0, len(sequences), CHUNK):
        chunk = sequences[start:start + CHUNK]
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            (tmp / "in").mkdir()
            (tmp / "viterbi").mkdir()
            (tmp / "post").mkdir()
            files = []
            for i, s in enumerate(chunk):
                files.append(tmp / "in" / f"{i:06d}.fasta")
                files[-1].write_text(f">{i}\n{s}\n")
            run_eternafold(files, ["--viterbi", "--parens", output_target(files, tmp / "viterbi")], processes)
            run_eternafold(files, ["--posteriors", str(POSTERIOR_CUTOFF), output_target(files, tmp / "post")],
                           processes)
            for i, s in enumerate(chunk):
                structure = _read_structure(tmp / "viterbi" / files[i].name)
                pairs, paired = _read_posteriors(tmp / "post" / files[i].name, len(s))
                row = {"ef_structure": structure, "ef_ned_own": ensemble_defect(pairs, paired, structure)}
                for k, other in enumerate(compare[start + i] if compare is not None else []):
                    row[f"ef_ned_{k}"] = ensemble_defect(pairs, paired, other)
                    row[f"ef_match_{k}"] = other == structure
                out.append(row)
    return out
