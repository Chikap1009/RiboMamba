# Project history — RiboMamba (2026-09-22 to 2026-09-29)

An index of everything done in this project, in order, with pointers to the detailed records. It adds
no new results; every statement links to where it is recorded. The complete, fine-grained history is
the Git log (`git log --reverse`: 233 commits up to the closeout on 2026-09-29 02:52 IST, plus the final
documentation commits) and the twelve session logbooks in [docs/logbook/](logbook/).

**How the work was done.** Chirag Kapoor directed the project and made the research decisions recorded
as user instructions. Implementation, experiments and documentation were carried out by AI coding
agents working in the repository: Claude Code (sessions 01-05, 07, 09-12) and Codex (sessions 06 and 08,
review and recommendation). Commits made by agents carry a Co-Authored-By trailer. Every session keeps a
timestamped logbook of commands, outcomes and uncertainties; scientific choices are numbered decisions
(D-001 to D-031) in [DECISIONS.md](DECISIONS.md); measured numbers go to [RESULTS.md](RESULTS.md) only
after they are measured.

## Era I — an RNA sequence foundation-model study (sessions 01-05; paused)
| session | date | what happened | decisions |
|---|---|---|---|
| [01](logbook/2026-09-22-session-01.md) | 2026-09-22 | Phase 0: project contract, docs structure, scope (secondary structure, no pseudoknots); teaching session, no code | D-001 |
| [02](logbook/2026-09-22-session-02.md) | 2026-09-22 | WSL2 repaired; repository moved into WSL and put under Git (first commit f495772); conda environment | D-002, D-003 |
| [03](logbook/2026-09-23-session-03.md) | 2026-09-23/24 | Phase 1 data: pinned Rfam 15.0 downloads, tokeniser, cleaning, clan/family split, sequence and structure leakage audits; Phase 2: Transformer masked-diffusion denoiser, training recipe, learning-rate and dropout sweeps (the sweep finished 2026-09-24 08:49; base model tf_M_do0, 1.904 bits/nt on unseen families) | D-004 to D-012 |
| [04](logbook/2026-09-24-session-04.md) | 2026-09-24 | Phase 3 evaluation: folding metrics, statistics, EternaFold as a second oracle, harness and test-split lock, sampling ablation with a rule written before the results | D-013, D-014 |
| [05](logbook/2026-09-25-session-05.md) | 2026-09-25 | Phase 4: BiMamba and autoregressive Mamba models matched to the Transformer, replication-split training, architecture sweep queue | D-015, D-016 |
The Phase 4 queue was paused on 2026-09-27 when the user approved a pivot
([PHASE4_PAUSED.md](PHASE4_PAUSED.md)); its checkpoints are kept. Historical protocol and results:
[RESULTS.md](RESULTS.md) (P2/P3 protocol, splits, baselines, ablations).

## Era II — folding-guided RNA design repair (sessions 06-12; completed and closed)
| session | date | what happened | decisions |
|---|---|---|---|
| [06](logbook/2026-09-27-session-06.md) | 2026-09-27 | Codex: independent familiarisation with the project; research pivot adopted and handoff prepared | — |
| [07](logbook/2026-09-27-session-07.md) | 2026-09-27 | Stage A: design harness (robust scoring, budgets, traces, resumable runs), natural targets at ceiling, hard Eterna web development set with leakage audit, SAMFEO baseline; Stage B: unconditional model as repair proposer — negative | D-017 to D-020 |
| [08](logbook/2026-09-27-session-08.md) | 2026-09-27 | Codex: overnight review, compute-cap correction, competition-aware residual proposal ([CODEX_TO_CLAUDE_2026-09-27.md](CODEX_TO_CLAUDE_2026-09-27.md)) | D-021 |
| [09](logbook/2026-09-27-session-09.md) | 2026-09-27/28 | Residual experiment (negative), learned critics (negative online), energy screen confirmed once on sealed puzzles, local DesiRNA/SamplingDesign/RNAinverse baselines, target-conditioned denoiser (TCD) trained and tested, protocol v2 frozen, final benchmark launched; independent review fixes to external-tool timing | D-022 to D-028 |
| [10](logbook/2026-09-28-session-10.md) | 2026-09-28 | Final benchmark completed (3,504 valid units), corrective pass, FINAL report; null primary result; write-up, figures, model and data cards | D-029 |
| [11](logbook/2026-09-28-session-11.md) | 2026-09-28/29 | Bounded TCD inference-efficiency study: profile, CUDA-graph forward, one declared development comparison; engineering gates met, scientific gate not met; direction stopped | D-030 |
| [12](logbook/2026-09-29-session-12.md) | 2026-09-29 | Closeout: verification from saved artifacts, corrections, final technical report, reproduction guide, local preservation package; final documentation pass | D-031 |
Plans and protocols: [RESEARCH_PLAN.md](RESEARCH_PLAN.md) (historical plan), experiment records in
[experiments/](experiments/), the frozen final protocol [PROTOCOL_design_v2.md](PROTOCOL_design_v2.md)
with amendments 1-4f, the report [REPORT_repair_v2.md](REPORT_repair_v2.md), reproduction
[REPRODUCE.md](REPRODUCE.md).

## Register of mistakes found and how they were handled
Recorded so that a reader can judge the process, not only the results.
| issue | found | handling | where recorded |
|---|---|---|---|
| ViennaRNA returns a non-zero probability for targets a sequence cannot form | Stage A | explicit P = 0 in the scorer, tested | D-017; scoring.py docstring |
| Natural validation targets too easy to discriminate methods | Stage A smoke run | hard, leakage-audited Eterna web development set | D-018; session 07 |
| A TCD arm silently inherited the energy screen (configuration slip) | analysis of ew_dev_tcdprop_v1 | fixed (63631c0), effective settings logged per unit, test added, clean rerun | TCD record, Results 3-4 |
| A throwaway commit and soft reset undid a commit | session 09 | recommitted unchanged (47d24fc) | session 09 log |
| Laptop suspend corrupted wall-clock-limited units | frontier run | clock-gap validation; affected units rerun | session 09 log |
| Memory near-exhaustion in the final run (10 workers) | first 43 final units | fresh process per unit, lazy model imports; completed units kept | protocol amendments 1, 1b |
| DesiRNA time limit passed as a float; replay judged on the wrong clock | final run | fixed; affected units superseded and rerun | amendments 2, 3 |
| DesiRNA credited post-deadline work; SamplingDesign output could be lost | independent review | real per-candidate timing, hard kills, initial population logged; 117 units superseded and rerun; development DesiRNA timings marked optimistic | amendments 4, 4b; RESULTS correction |
| An unlabelled smoke-test report sat under the final report's name | review | archived with checksum; FINAL report records provenance and what it supersedes | amendment 4f |
| Error units could have kept success credit; missing designs gave NaN means | review | policy implemented and tested; quality over units with designs | amendments 4c-4e |
| Runner ignored --recycle-workers at one worker; a "cold" profile was warm | efficiency study | runner fixed (82361cc, test); profile kept and relabelled; genuine cold rerun | efficiency record; LABEL.txt |
| Conclusion "cost does not explain the gap" overstated; latency causes stated as fact | closeout | narrowed conclusion; observations separated from inferences | D-030 correction; closeout notes |
| 7 TCD units of the first launch ran with the model already loaded | closeout verification | disclosed with first-success times; not rerun | report section 9; RESULTS closeout |
| Bootstrap intervals not bit-reproducible (unsorted rows) | closeout regeneration | disclosed as observed variation; canonical numbers kept | report section 9; D-031 |
| Stale "confirmation in progress" and pilot/next-step instructions | sessions 10 and 12 | corrected; superseded markers added | HANDOFF; CLAUDE.md status |
Earlier phases (sessions 01-05) record their own corrections in their logbooks and in RESULTS.md.

## Repository and backup status (2026-09-29)
- GitHub (github.com/Chikap1009/RiboMamba): at the start of the final documentation pass, origin/main
  (5b33522, 2026-09-27 04:37 IST) was 89 commits behind local main (confirmed with `git fetch`). With the
  user's authorisation, main was pushed on 2026-09-29 (~03:35 IST): 5b33522..5c93550, a fast-forward of 90
  commits; the commit recording this was pushed after it. GitHub holds only Git-tracked files.
- Large data, checkpoints and third-party code are not in Git. A local preservation package with a Git
  bundle, copies of the results and essential checkpoints, and a checksummed inventory is at
  /home/chirag/projects/RiboMamba_closeout_2026-09-29/. It is on the SAME DISK as the repository: a
  second copy, not an independent backup.
