"""The evaluation harness: every per-sequence metric, summaries with error bars, distances (Phase 3).

  per_sequence(seqs, train)   one row per sequence: ViennaRNA metrics (folding.py),
                              EternaFold's view (eternafold.py), GC, structure
                              elements, novelty and within-set identity (diversity.py)
  summarise(table)            mean of every scalar metric with a 95 % bootstrap
                              interval, plus novelty / diversity shares
  distances(table, real)      how far a set's distributions are from the real
                              reference: Wasserstein-1 per metric, JSD of k-mer spectra

Summaries treat sequences as independent, which is right for generated
samples (independent draws). Real held-out sequences come in families;
their family-cluster intervals are computed where the protocol requires it.
"""

import numpy as np
import polars as pl
import RNA

from ribomamba.eval.distributions import (gc_content, js_divergence, kmer_spectrum, structure_elements,
                                          wasserstein1)
from ribomamba.eval.diversity import internal_identity, novelty
from ribomamba.eval.eternafold import eternafold_many
from ribomamba.eval.folding import N_SHUFFLES, fold_many
from ribomamba.eval.stats import bootstrap_ci

ELEMENTS = ["stems", "hairpins", "bulges", "internal_loops", "multiloops"]
SCALAR_METRICS = [
    "gc", "mfe_per_nt", "paired_fraction", "p_mfe", "ned_mfe", "mfe_z", "beats_shuffles",
    "ef_ned_own", "ef_ned_vienna", "oracles_agree", "oracle_bp_distance",
    *[f"{e}_per_100nt" for e in ELEMENTS], "mean_stem_length", "mean_hairpin_size",
]
KMER_SIZES = (1, 2, 4, 6)
IDENTITY_LEVELS = (0.5, 0.8, 0.95)


def per_sequence(sequences: list[str], train: list[str] | None = None, n_shuffles: int = N_SHUFFLES,
                 seed: int = 0, processes: int | None = None) -> pl.DataFrame:
    """All per-sequence metrics, one row per input sequence, in input order."""
    table = fold_many(sequences, n_shuffles=n_shuffles, seed=seed, processes=processes)
    vienna = table["mfe_structure"].to_list()
    ef = eternafold_many(sequences, compare=[[s] for s in vienna], processes=processes)
    elements = [structure_elements(s) for s in vienna]
    extra = {
        "sequence": sequences,
        "gc": [gc_content(s) for s in sequences],
        "ef_structure": [r["ef_structure"] for r in ef],
        "ef_ned_own": [r["ef_ned_own"] for r in ef],              # EternaFold: how firmly it holds ITS best structure
        "ef_ned_vienna": [r["ef_ned_0"] for r in ef],             # EternaFold: how firmly it holds VIENNA's MFE structure
        "oracles_agree": [float(r["ef_match_0"]) for r in ef],    # the two oracles predict the identical structure
        "oracle_bp_distance": [RNA.bp_distance(v, r["ef_structure"]) / len(v) for v, r in zip(vienna, ef)],
        **{f"{e}_per_100nt": [el[e] * 100 / len(s) for el, s in zip(elements, sequences)] for e in ELEMENTS},
        "mean_stem_length": [el["mean_stem_length"] for el in elements],
        "mean_hairpin_size": [el["mean_hairpin_size"] for el in elements],
        "internal_identity": internal_identity(sequences),
    }
    if train is not None:
        extra["train_identity"] = novelty(sequences, train)
    return table.with_columns([pl.Series(k, v) for k, v in extra.items()])


def summarise(table: pl.DataFrame, seed: int = 0) -> dict:
    """{metric: {"mean", "low", "high", "n"}} with 95 % bootstrap intervals, plus shares.

    NaN values (mfe_z when every shuffle ties) are dropped, and how many were
    dropped is reported as n_undefined, so nothing disappears silently.
    """
    out = {}
    for metric in SCALAR_METRICS:
        values = table[metric].cast(pl.Float64).to_numpy()
        defined = values[~np.isnan(values)]
        est, low, high = bootstrap_ci(defined, seed=seed)
        out[metric] = {"mean": est, "low": low, "high": high, "n": len(defined),
                       "n_undefined": int(len(values) - len(defined)), "median": float(np.median(defined))}
    seqs = table["sequence"].to_list()
    out["distinct_fraction"] = len(set(seqs)) / len(seqs)
    for column, name in (("internal_identity", "sibling"), ("train_identity", "train_relative")):
        if column in table.columns:
            for level in IDENTITY_LEVELS:
                hit = (table[column].to_numpy() >= level).astype(float)
                est, low, high = bootstrap_ci(hit, seed=seed)
                out[f"{name}_ge_{int(level * 100)}"] = {"mean": est, "low": low, "high": high, "n": len(hit)}
    return out


def distances(table: pl.DataFrame, real: pl.DataFrame) -> dict:
    """How far this set's distributions are from the real reference: W1 per metric, JSD per k."""
    out = {}
    for metric in SCALAR_METRICS:
        a = table[metric].cast(pl.Float64).to_numpy()
        b = real[metric].cast(pl.Float64).to_numpy()
        out[f"w1_{metric}"] = wasserstein1(a[~np.isnan(a)], b[~np.isnan(b)])
    for k in KMER_SIZES:
        out[f"jsd_{k}mer"] = js_divergence(kmer_spectrum(table["sequence"].to_list(), k),
                                           kmer_spectrum(real["sequence"].to_list(), k))
    return out
