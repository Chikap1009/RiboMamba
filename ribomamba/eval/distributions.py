"""Comparing generated RNA with real RNA as whole distributions (Phase 3).

Means hide shape: two sets can share an average GC content while one is a
tight spike and the other a mix of GC-poor and GC-rich sequences. So we
compare distributions:

  wasserstein1        for one number per sequence (GC, MFE per nt, NED, z, ...)
  kmer_spectrum, js_divergence
                      for letter statistics: how often each k-letter word occurs
  structure_elements  what KIND of structure each sequence forms (stems,
                      hairpins, bulges, internal loops, multiloops), from its
                      dot-bracket MFE structure

A distance is only meaningful next to its calibration (logbook session 04):
the distance between two independent samples of real RNA is the noise
floor, and shuffled or random sequences show what "far" looks like.
"""

from collections import Counter
from itertools import product

import numpy as np

from ribomamba.eval.folding import pair_table

ALPHABET = "ACGU"


def gc_content(sequence: str) -> float:
    return (sequence.count("G") + sequence.count("C")) / len(sequence)


def wasserstein1(x, y) -> float:
    """Earth mover's distance between two samples of numbers, in the numbers' own units.

    The least average distance probability mass must travel to turn one
    histogram into the other. For one-dimensional data it equals the area
    between the two cumulative distribution functions: integral |F_x - F_y|.
    """
    x, y = np.sort(np.asarray(x, dtype=float)), np.sort(np.asarray(y, dtype=float))
    grid = np.concatenate([x, y])
    grid.sort()                                                        # every point where a CDF can jump
    cdf_x = np.searchsorted(x, grid[:-1], side="right") / len(x)       # F_x just right of each grid point
    cdf_y = np.searchsorted(y, grid[:-1], side="right") / len(y)
    return float(np.sum(np.abs(cdf_x - cdf_y) * np.diff(grid)))


def kmer_spectrum(sequences: list[str], k: int) -> np.ndarray:
    """Frequency of each of the 4^k words of length k, pooled over all sequences (sums to 1).

    Words are counted with overlap: 'GGGA' has 2-mers GG, GG, GA. Index order
    is alphabetical (AA..A, AA..C, ...), identical for every call.
    """
    index = {"".join(w): i for i, w in enumerate(product(ALPHABET, repeat=k))}
    counts = np.zeros(len(index))
    for s in sequences:
        for word, n in Counter(s[i:i + k] for i in range(len(s) - k + 1)).items():
            counts[index[word]] += n
    return counts / counts.sum()


def js_divergence(p, q) -> float:
    """Jensen-Shannon divergence in bits: 0 for identical distributions, at most 1.

    JSD = (KL(p || m) + KL(q || m)) / 2 with m the average of p and q. Unlike
    KL alone it is symmetric and finite when one side has a zero count.
    """
    p, q = np.asarray(p, dtype=float), np.asarray(q, dtype=float)
    m = (p + q) / 2

    def kl(a):
        nz = a > 0
        return float(np.sum(a[nz] * np.log2(a[nz] / m[nz])))
    return (kl(p) + kl(q)) / 2


def structure_elements(structure: str) -> dict:
    """Count the loop types of a nested dot-bracket structure.

    Every pair (i, j) closes one loop; what it encloses decides the type:
      no pair inside                -> hairpin loop
      one pair (k, l) inside, and the unpaired stretches i..k and l..j are
        both empty                  -> stack (part of a stem, not a loop)
        empty on exactly one side   -> bulge (one-sided)
        non-empty on both sides     -> internal loop (two-sided)
      two or more pairs inside      -> multiloop (junction)
    A stem is a maximal run of stacked pairs; it starts at a pair whose outer
    neighbour (i-1, j+1) is not a pair.
    """
    partner = pair_table(structure)
    n = len(structure)
    out = {"pairs": 0, "stems": 0, "hairpins": 0, "bulges": 0, "internal_loops": 0, "multiloops": 0}
    stem_lengths, hairpin_sizes = [], []
    for i, j in enumerate(partner):
        if j <= i:
            continue
        out["pairs"] += 1
        if not (i > 0 and j < n - 1 and partner[i - 1] == j + 1):      # nothing stacked outside: a stem starts
            out["stems"] += 1
            length, a, b = 1, i, j
            while partner[a + 1] == b - 1 and a + 1 < b - 1:
                length, a, b = length + 1, a + 1, b - 1
            stem_lengths.append(length)
        inside, k, unpaired = [], i + 1, 0
        while k < j:                                                   # walk the loop closed by (i, j)
            if partner[k] > k:
                inside.append((k, partner[k]))
                k = partner[k] + 1
            else:
                unpaired, k = unpaired + 1, k + 1
        if not inside:
            out["hairpins"] += 1
            hairpin_sizes.append(unpaired)
        elif len(inside) == 1:
            left, right = inside[0][0] - i - 1, j - inside[0][1] - 1
            if left and right:
                out["internal_loops"] += 1
            elif left or right:
                out["bulges"] += 1
        else:
            out["multiloops"] += 1
    out["mean_stem_length"] = float(np.mean(stem_lengths)) if stem_lengths else 0.0
    out["mean_hairpin_size"] = float(np.mean(hairpin_sizes)) if hairpin_sizes else 0.0
    return out
