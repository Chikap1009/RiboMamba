# Data card — design targets and training data for the repair / design study

Written 2026-09-28 from the manifests and experiment records. Every target set is a versioned JSON
manifest in `manifests/` with a content SHA-256; building a manifest reads structures only.

## Target sets
| manifest (sha256 prefix) | targets | source | role and status |
|---|---|---|---|
| repair_pilot_val_v1 (58df4ac1) | 64 | Rfam validation split (data/targets/rfam_val.parquet), natural structures | Stage A smoke/validation; at ceiling (too easy) |
| eternaweb_dev_v1 (19f16b01) | 64 = 32 development + 32 confirmation | Eterna web player puzzles from Gautam et al. 2026 (arXiv:2602.12470; github.com/KuNyaa/RNA-Design-LM, MIT; HF rev 609f573b) | development runs; confirmation had ONE look (consumed) |
| eternaweb_trainpool_v1 (a67a5c36) | 700 | same source as above | training side only (SAMFEO trajectories, TCD design pairs, critics) |
| final_eterna100_v2 (33c65b95) | 100 | Eterna100 V2 structures, data/raw/eterna100/eterna100_puzzles.tsv (Anderson-Lee et al. 2016; V2: Koodli et al. 2021, bioRxiv 10.1101/2021.08.26.457839) | protocol v2 primary; consumed |
| final_eterna100_v1only (2ef59009) | 19 | same file, V1 column, rows whose V1 structure differs from V2 | protocol v2 secondary; consumed |
| final_rfam_taneda27 (a8016910) | 27 | SAMFEO's pinned copy (external/SAMFEO/data/Rfam/rf27.txt), identical to RNA-Design-LM's Rfam27 | protocol v2 secondary; consumed |

Selection and leakage (eternaweb sets): hard puzzles chosen by a method-free hardness probe; every
development/confirmation target is > 0.2 normalised edit distance from Eterna100 V1/V2, Rfam-Taneda-27/29
and RNAsolo-764 structures. Building the training pool, the same audit rejected 95 puzzles near a
test-side structure (the source's own filter was incomplete for this audit set), 20 near a
development/confirmation target and 54 near-duplicates (2,524 visited, 700 accepted). All structures
are pseudoknot-free with every pair enclosing >= 3 nt (checked when manifests are built).

## Training data (training side only)
- Natural pairs for the TCD: Rfam training sequences (data/processed/train.parquet, <= 256 nt) with
  their ViennaRNA 2.7.2 MFE structures; 150,000 folded, 142,533 kept for training and 2,632 for
  validation after removing 4,769 within edit distance 0.2 of any development, confirmation or final
  structure.
- Design pairs: distinct uMFE designs found by SAMFEO (pinned e78b4b5) on the 700 training-pool
  puzzles (50,649 designs for 312 puzzles, capped per puzzle to 16,820): 14,567 train (272 puzzles) and
  2,253 validation (40 held-out puzzles).
- Critic and residual data: SAMFEO trajectories on the training pool (trainpool_samfeo_v1, 700 units,
  280,000 rows) and 5,600 sibling groups x 16 scored children (89,600).

## Labels and oracle
All success and quality labels come from ViennaRNA 2.7.2 (Turner 2004, 37 C, dangles 2, lonely pairs
allowed): uMFE success (primary), MFE with ties (two variants), NED, log P(target). Unformable targets
are scored as p = 0 explicitly. EternaFold 1.3.1 is used only as an independent check, never as an
optimisation target.

## Known issues and disclosures
- Eterna100 is public and widely used; published checkpoints and data may overlap it. The TCD was not
  trained on Eterna100 structures (edit-distance filter), but its design pairs come from the same
  Eterna web source as the development set.
- Rfam-Taneda-27 is Rfam-derived; family-level overlap with the Rfam training sequences is possible.
- The 19 V1-only Eterna100 puzzles are solved by no method under Turner 2004, as in SAMFEO's published
  V1 results; Koodli et al. (2021) report these 19 as unsolvable in Vienna 2, which is why V2 redesigned
  them. They are kept and reported, not dropped.
- SAMFEO's repository has no license file: it is used locally only and never redistributed. The
  Rfam-Taneda-27 manifest stores structures (public Rfam-derived data), not SAMFEO code.
- Raw traces live in data/repair_pilot/ (ignored by Git) and are preserved, including superseded units
  and report files (data/repair_pilot/report_history/). A checksummed local copy of the results, the
  prepared data and these target files is in the closeout package (docs/HANDOFF.md); the large Rfam raw
  files are referenced there by checksum, not copied.
