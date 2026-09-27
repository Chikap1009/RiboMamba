"""A HARD development manifest from Eterna web player puzzles (Stage A, revised 2026-09-27).

Why a second manifest. The natural-structure validation targets are at ceiling
for this question: on the 8 rfam_val smoke targets, the GC/CG-stem, A-loop
shared start ALONE met unique-MFE success on 5-6 of 8 before any search, and
64 independent such designs solved 75 % (smoke64_v1). bpRNA validation targets
(75 % solved by the start alone) and structures induced from random sequences
(62 %; RNAinverse 96.5 %) were no better. Hard benchmarks such as Eterna100
are hard because players designed them to be. Repair methods can only be told
apart where search is needed.

Source  Eterna web player puzzles released by Gautam et al. 2026 (arXiv:2602.12470,
        "Designing RNAs with Language Models"; code github.com/KuNyaa/RNA-Design-LM,
        MIT license), file data/YRL_raw/EternaWeb.jsonl of HuggingFace model repo
        Milanmg/LLM-RNA-Design-2026 at revision 609f573b. The authors describe it as
        Eterna web puzzles filtered to MFE-designable structures with normalized
        edit distance > 0.2 from their test sets; designability is their claim,
        not re-verified here.
Rules   (in order; every exclusion counted by reason)
          structure only ( ) . and balanced; 19-256 nt; >= 4 pairs; every pair
            encloses >= 3 nt; distinct structure
          leakage audit: excluded if its Eterna id is an Eterna100 puzzle id, or
            its normalized edit distance (Levenshtein / longer length) to ANY
            test-side structure is <= 0.2: Eterna100 V1 and V2 (pinned TSV and
            the LM paper's copies), Rfam-Taneda-27 and -29 (SAMFEO's copies),
            RNAsolo-764. These structures are read only for this exclusion.
          hardness probe: excluded if ANY of the three shared starts (seeds 0-2,
            search.shared_start, the same start every repair method gets) is
            already a unique-MFE solution. No search method is run.
Strata  4 equal-count length bins x 4 equal-count paired-fraction bins over the
        probed-hard pool; ties broken by id.
Select  per cell, visit a numpy default_rng(SEED) permutation and accept a puzzle
        unless its normalized edit distance to an already accepted target is
        <= 0.2 (no near-duplicates) or it fails the leakage audit; 4 per cell.
Split   2 development + 2 confirmation per cell (same generator); smoke = one
        development target per (length bin, paired-fraction half).
"""

import json
from multiprocessing import get_context

import numpy as np
import polars as pl

from ribomamba.design.manifest import (DEV_PER_CELL, LENGTH_BINS, MAX_LEN, MIN_PAIRS, PAIRED_BINS, PER_CELL,
                                       _equal_bins, content_hash, sha256_file)
from ribomamba.design.scoring import score
from ribomamba.design.search import Target, shared_start
from ribomamba.eval.folding import MIN_HAIRPIN, pair_table
from ribomamba.paths import EXTERNAL_DIR, MANIFESTS_DIR, RAW_DIR, REPO_ROOT

NAME = "eternaweb_dev_v1"
PATH = MANIFESTS_DIR / f"{NAME}.json"
EW_DIR = RAW_DIR / "eternaweb_rnadesignlm"
SOURCE = EW_DIR / "YRL_raw_EternaWeb.jsonl"
SOURCE_SHA256 = "5f6e0f5c515a8c4a41168b64fbe822dd1d0c4b2aef36711cfebad83f10c9a6ed"
SELECTED_RL = EW_DIR / "YRL_EternaWeb.jsonl"          # the authors' 2.8K RL subset: recorded as a flag only
PROVENANCE = {
    "url": "https://huggingface.co/Milanmg/LLM-RNA-Design-2026/resolve/main/data/YRL_raw/EternaWeb.jsonl",
    "hf_revision": "609f573b1a373a4f4e6748057c90dcca07e02294",
    "license": "MIT (github.com/KuNyaa/RNA-Design-LM)",
    "paper": "Gautam, Dai, Zhou, Xie, Mathews, Huang 2026, arXiv:2602.12470",
    "downloaded": "2026-09-27",
}
SEED = 20260928
MIN_LEN = 19
SIMILARITY_MAX = 0.2
PROBE_SEEDS = (0, 1, 2)
ID_PREFIX = "eternaweb:"


def audit_structures() -> dict[str, list[str]]:
    """Test-side structures for the leakage audit, by source (read for exclusion only)."""
    out = {}
    tsv = pl.read_csv(RAW_DIR / "eterna100" / "eterna100_puzzles.tsv", separator="\t")
    out["eterna100_v1_tsv"] = tsv["Secondary Structure V1"].to_list()
    out["eterna100_v2_tsv"] = tsv["Secondary Structure V2"].to_list()
    for name in ("eterna100", "eterna100v2", "Rfam27", "RNAsolo"):
        out[f"rnadesignlm_{name}"] = [json.loads(line)["target_structure"]
                                     for line in open(EW_DIR / "audit" / f"{name}.jsonl")]
    for name in ("rf27", "rf29"):
        path = EXTERNAL_DIR / "SAMFEO" / "data" / "Rfam" / f"{name}.txt"
        out[f"samfeo_{name}"] = [line.strip() for line in open(path) if line.strip()]
    return out


def eterna100_ids() -> set[int]:
    tsv = pl.read_csv(RAW_DIR / "eterna100" / "eterna100_puzzles.tsv", separator="\t")
    ids = set()
    for col in [c for c in tsv.columns if c.startswith("Eterna ID")]:
        ids |= {int(x) for x in tsv[col].drop_nulls().to_list()}
    return ids


def edit_distance(a: str, b: str) -> int:
    """Levenshtein distance, one numpy row at a time (insertions resolved by a running minimum)."""
    if len(a) < len(b):
        a, b = b, a
    bb = np.frombuffer(b.encode(), dtype=np.uint8)
    idx = np.arange(len(b) + 1)
    row = idx.copy()
    for i, ch in enumerate(a.encode(), 1):
        sub = row[:-1] + (bb != ch)                     # substitution / match from the previous row
        cand = np.empty_like(row)
        cand[0] = i
        cand[1:] = np.minimum(sub, row[1:] + 1)         # deletion
        row = np.minimum.accumulate(cand - idx) + idx   # insertion: d[j] = min_k<=j cand[k] + (j - k)
    return int(row[-1])


def edit_distance_bits(a: str, b: str) -> int:
    """Levenshtein distance by Myers' bit-parallel algorithm (Hyyro 2001, global variant).

    One pass over b with |a|-bit integers as bit vectors: O(|b|) big-integer operations,
    ~50x faster than the numpy row version for structures of <= 256 characters.
    """
    m = len(a)
    if m == 0:
        return len(b)
    peq: dict[str, int] = {}
    for i, c in enumerate(a):
        peq[c] = peq.get(c, 0) | (1 << i)
    full, high = (1 << m) - 1, 1 << (m - 1)
    pv, mv, score = full, 0, m
    for c in b:
        eq = peq.get(c, 0)
        xv = eq | mv
        xh = (((eq & pv) + pv) ^ pv) | eq
        ph = mv | (~(xh | pv) & full)
        mh = pv & xh
        if ph & high:
            score += 1
        elif mh & high:
            score -= 1
        ph = ((ph << 1) | 1) & full
        mh = (mh << 1) & full
        pv = mh | (~(xv | ph) & full)
        mv = ph & xv
    return score


def normalized_distance(a: str, b: str) -> float:
    return edit_distance_bits(a, b) / max(len(a), len(b))


def too_similar(s: str, others: list[str], threshold: float = SIMILARITY_MAX) -> str | None:
    """The first structure within the threshold (length difference alone can rule most out), else None."""
    for o in others:
        if abs(len(s) - len(o)) / max(len(s), len(o)) > threshold:
            continue
        if normalized_distance(s, o) <= threshold:
            return o
    return None


def _structurally_ineligible(ss: str) -> str | None:
    if set(ss) - set("()."):
        return "structure has characters other than ( ) ."
    try:
        pt = pair_table(ss)
    except ValueError:
        return "unbalanced structure"
    if not MIN_LEN <= len(ss) <= MAX_LEN:
        return f"length outside {MIN_LEN}-{MAX_LEN}"
    if sum(j > i for i, j in enumerate(pt)) < MIN_PAIRS:
        return f"fewer than {MIN_PAIRS} base pairs"
    if any(j > i and j - i - 1 < MIN_HAIRPIN for i, j in enumerate(pt)):
        return f"a pair encloses fewer than {MIN_HAIRPIN} nucleotides"
    return None


def probe(item: tuple[str, str]) -> dict:
    """Does any seeded shared start already solve it (unique MFE)? Also its NED, for the record."""
    target_id, structure = item
    t = Target(target_id, structure)
    scores = [score(shared_start(t, s), structure, t.pt) for s in PROBE_SEEDS]
    return {"id": target_id, "start_solved": any(s.umfe for s in scores),
            "start_ned_mean": float(np.mean([s.ned for s in scores]))}


def build(workers: int = 4, seed: int = SEED) -> dict:
    rows = [json.loads(line) for line in open(SOURCE)]
    rl_ids = {json.loads(line)["id"] for line in open(SELECTED_RL)} if SELECTED_RL.exists() else set()
    funnel = {"source_rows": len(rows)}
    reasons: dict[str, int] = {}

    def drop(reason):
        reasons[reason] = reasons.get(reason, 0) + 1
    seen, pool = set(), []
    banned_ids = eterna100_ids()
    for r in sorted(rows, key=lambda r: r["id"]):
        ss = r["target_structure"]
        why = _structurally_ineligible(ss)
        if why is None and ss in seen:
            why = "duplicate structure"
        if why is None and r["id"] in banned_ids:
            why = "Eterna id is an Eterna100 puzzle id"
        if why:
            drop(why)
            continue
        seen.add(ss)
        pool.append({"id": f"{ID_PREFIX}{r['id']}", "eterna_id": r["id"], "structure": ss})
    funnel["structurally_eligible"] = len(pool)

    with get_context("spawn").Pool(workers) as p:
        probes = {x["id"]: x for x in p.map(probe, [(r["id"], r["structure"]) for r in pool], chunksize=64)}
    for r in pool:
        r.update(start_solved=probes[r["id"]]["start_solved"], start_ned_mean=probes[r["id"]]["start_ned_mean"])
    hard = [r for r in pool if not r["start_solved"]]
    funnel["probe_unsolved"] = len(hard)
    reasons["a shared start already solves it (probe)"] = len(pool) - len(hard)

    for r in hard:
        r["length"] = len(r["structure"])
        r["paired_fraction"] = 2 * r["structure"].count("(") / r["length"]
    ids = [r["id"] for r in hard]
    length_bin = _equal_bins([r["length"] for r in hard], ids, LENGTH_BINS)
    strata, cells = [], {}
    for lb in range(LENGTH_BINS):
        members = [k for k in range(len(hard)) if length_bin[k] == lb]
        pbins = _equal_bins([hard[k]["paired_fraction"] for k in members], [ids[k] for k in members], PAIRED_BINS)
        for k, pb in zip(members, pbins):
            hard[k]["length_bin"], hard[k]["paired_bin"] = lb, pb
            cells.setdefault((lb, pb), []).append(hard[k])
    audit = audit_structures()
    audit_all = [s for v in audit.values() for s in v]
    rng = np.random.default_rng(seed)
    chosen, rejected = [], {"similar to a test-side structure": 0, "near-duplicate of a selected target": 0}
    for lb in range(LENGTH_BINS):
        for pb in range(PAIRED_BINS):
            pool_cell = sorted(cells[(lb, pb)], key=lambda r: r["id"])
            accepted = []
            for k in rng.permutation(len(pool_cell)):
                r = pool_cell[int(k)]
                if too_similar(r["structure"], [c["structure"] for c in chosen + accepted]):
                    rejected["near-duplicate of a selected target"] += 1
                    continue
                if too_similar(r["structure"], audit_all):
                    rejected["similar to a test-side structure"] += 1
                    continue
                accepted.append(r)
                if len(accepted) == PER_CELL:
                    break
            if len(accepted) < PER_CELL:
                raise ValueError(f"cell {(lb, pb)} yielded only {len(accepted)} targets")
            dev = set(rng.choice(PER_CELL, size=DEV_PER_CELL, replace=False).tolist())
            for k, r in enumerate(accepted):
                r["subset"] = "development" if k in dev else "confirmation"
            strata.append({"length_bin": lb, "paired_bin": pb, "eligible": len(pool_cell),
                           "length_range": [min(r["length"] for r in pool_cell), max(r["length"] for r in pool_cell)],
                           "paired_fraction_range": [round(min(r["paired_fraction"] for r in pool_cell), 4),
                                                     round(max(r["paired_fraction"] for r in pool_cell), 4)]})
            chosen.extend(accepted)
    for r in chosen:
        r["smoke"] = False
    for lb in range(LENGTH_BINS):
        for half in (0, 1):
            cands = [r for r in chosen if r["subset"] == "development" and r["length_bin"] == lb
                     and r["paired_bin"] // (PAIRED_BINS // 2) == half]
            cands[int(rng.integers(len(cands)))]["smoke"] = True

    targets = sorted(({"id": r["id"], "eterna_id": r["eterna_id"], "length": r["length"],
                       "pairs": r["structure"].count("("), "paired_fraction": round(r["paired_fraction"], 6),
                       "length_bin": r["length_bin"], "paired_bin": r["paired_bin"], "subset": r["subset"],
                       "smoke": r["smoke"], "structure": r["structure"],
                       "probe_start_ned_mean": round(r["start_ned_mean"], 6),
                       "in_authors_rl_subset": r["eterna_id"] in rl_ids} for r in chosen), key=lambda t: t["id"])
    manifest = {
        "name": NAME,
        "purpose": "HARD development targets for the repair pilot (Eterna web player puzzles). Validation-style "
                   "development only; test-side benchmark structures were read solely for the leakage exclusion.",
        "source": {"path": str(SOURCE.relative_to(REPO_ROOT)), "sha256": sha256_file(SOURCE), **PROVENANCE},
        "audit_sources": {name: {"n": len(v)} for name, v in audit.items()},
        "audit_sha256": {p.name: sha256_file(p) for p in sorted((EW_DIR / "audit").glob("*.jsonl"))},
        "seed": seed,
        "rules": {"eligibility": [f"structure only ( ) . and balanced; {MIN_LEN}-{MAX_LEN} nt", f">= {MIN_PAIRS} pairs",
                                  f"every pair encloses >= {MIN_HAIRPIN} nt", "distinct structure",
                                  "Eterna id not an Eterna100 puzzle id"],
                  "leakage": f"normalized edit distance to every test-side structure > {SIMILARITY_MAX}",
                  "hardness_probe": f"no shared start (seeds {list(PROBE_SEEDS)}) is a unique-MFE solution",
                  "near_duplicates": f"normalized edit distance to every selected target > {SIMILARITY_MAX}",
                  "strata": f"{LENGTH_BINS} x {PAIRED_BINS} equal-count bins (length, then paired fraction)",
                  "split": f"{DEV_PER_CELL} development + {PER_CELL - DEV_PER_CELL} confirmation per cell",
                  "smoke": "one development target per (length bin, paired-fraction half)"},
        "funnel": {**funnel, "excluded_by_reason": reasons, "rejected_during_selection": rejected,
                   "selected": len(targets), "development": sum(t["subset"] == "development" for t in targets),
                   "confirmation": sum(t["subset"] == "confirmation" for t in targets),
                   "smoke": sum(t["smoke"] for t in targets)},
        "strata": strata,
        "targets": targets,
    }
    manifest["content_sha256"] = content_hash(manifest)
    return manifest


def check_source() -> None:
    if sha256_file(SOURCE) != SOURCE_SHA256:
        raise ValueError(f"{SOURCE} does not match the pinned SHA-256")


__all__ = ["NAME", "PATH", "build", "check_source", "edit_distance", "normalized_distance", "too_similar"]
