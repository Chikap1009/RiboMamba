> Current direction (2026-09-27): the user approved the repair-research pivot in RESEARCH_PLAN.md. Earlier phase gates and mandatory sweep completion are superseded; the material below remains historical reference. See HANDOFF.md for the next action.

# References — RiboMamba

Every work this project cites, what we use it for, and how the citation was
checked. **Rule:** a reference goes into the technical report only from this
file, and only if it is marked *verified* (title, authors, venue and identifier
checked against a publisher, arXiv, PubMed or proceedings page, not recalled
from memory).

Verification notes use the date of the check. "Search result" means the
details were read from a search result pointing at the publisher's or
arXiv's page, not from the full text; the report must re-read the relevant
section of any paper whose *content* (not only its existence) it relies on.

---

## Novelty check — 2026-09-25 (CLAUDE.md §3.3)

**The claim, stated precisely.** To the best of our knowledge (checked
2026-09-25), no published work trains a **bidirectional Mamba** as a **masked
discrete diffusion** model of **RNA sequences**, or compares such a model with
a parameter-matched Transformer diffusion model and a parameter-matched
autoregressive Mamba under an evaluation protocol frozen in advance, judged
by secondary-structure quality.

**The neighbours, by what each combines:**

| work | backbone | objective | data | how the combination differs from ours |
|---|---|---|---|---|
| DiffuMamba (Singh et al., 2025) | bidirectional Mamba (+ hybrid) | masked discrete diffusion | English text | no biological sequences |
| MDLM, DNA experiment (Sahoo et al., 2024) | Caduceus (bidirectional Mamba) fine-tuned | masked discrete diffusion | DNA (human genome) | DNA, judged by perplexity and genomic classification, not by the generated sequences' structure |
| Caduceus (Schiff et al., 2024) | BiMamba, reverse-complement equivariant | masked language model | DNA | not generative |
| DGRNA (bioRxiv 2024) | bidirectional Mamba-2 (+ attention), 100 M | masked language model (15 %) | RNA | an encoder, not generative |
| RDiffusion (bioRxiv 2026) | Transformer | discrete diffusion, conditioned (incl. secondary structure) | RNA | Transformer backbone |
| RIBOSPAN (Wang et al., 2026) | dense bidirectional attention, 1.61 B | foundation model + conditioned discrete diffusion | mRNA | Transformer backbone |
| RNAdiffusion (Huang et al., 2024) | Transformer (BERT-type encoder, Query Transformer) | continuous latent diffusion | ncRNA, 5′ UTRs | continuous latent, not masked discrete |
| Designing RNAs with Language Models (Gautam et al., 2026) | autoregressive language model | structure → sequence, reinforcement learning | RNA design | autoregressive, no Mamba, no diffusion |
| Montparnasse (Cazenave, 2026) | none (search) | Monte Carlo search (NRPA) | RNA design (Eterna100) | not a generative network |

Searched: arXiv, bioRxiv and general web for bidirectional Mamba + masked
diffusion + RNA; Mamba/state-space + diffusion + RNA design; the name
"RiboMamba" (no project or paper uses it). The two 2026 preprints the
session-04 handoff flagged (arXiv 2602.12470, 2606.07562) were read at
abstract level: neither uses Mamba or diffusion. **Re-check before
publishing**, as §3.3 requires: preprints move fast.

---

## Phase 0 — RNA folding and the oracle

| reference | used for | verified |
|---|---|---|
| Lorenz, R., Bernhart, S. H., Höner zu Siederdissen, C., Tafer, H., Flamm, C., Stadler, P. F., Hofacker, I. L. (2011). ViennaRNA Package 2.0. *Algorithms for Molecular Biology* 6, 26. doi:10.1186/1748-7188-6-26 | the primary folding oracle (we use 2.7.2) | 2026-09-25, search result → publisher page |
| Mathews, D. H., Disney, M. D., Childs, J. L., Schroeder, S. J., Zuker, M., Turner, D. H. (2004). Incorporating chemical modification constraints into a dynamic programming algorithm for prediction of RNA secondary structure. *PNAS* 101, 7287–7292. doi:10.1073/pnas.0401799101 | the "Turner 2004" nearest-neighbour energy parameters | 2026-09-25, search result → PNAS page |

## Phase 1 — data and leakage control

| reference | used for | verified |
|---|---|---|
| Ontiveros-Palacios, N., Cooke, E., Nawrocki, E. P., Triebel, S., Marz, M., Rivas, E., Griffiths-Jones, S., Petrov, A. I., Bateman, A., Sweeney, B. A. (2025). Rfam 15: RNA families database in 2025. *Nucleic Acids Research* 53(D1), D258–D267. doi:10.1093/nar/gkae1023 | the training corpus's families and clans; the covariance models of step 11 | 2026-09-25, search result → NAR page |
| Danaee, P., Rouches, M., Wiley, M., Deng, D., Huang, L., Hendrix, D. (2018). bpRNA: large-scale automated annotation and analysis of RNA secondary structure. *Nucleic Acids Research* 46(11), 5381–5394 | the bpRNA-1m structures (design targets, secondary set) | 2026-09-25, search result → NAR page |
| Steinegger, M., Söding, J. (2017). MMseqs2 enables sensitive protein sequence searching for the analysis of massive data sets. *Nature Biotechnology* 35(11), 1026–1028. doi:10.1038/nbt.3988 | the sequence-identity leakage search (step 10, audits) | 2026-09-25, search result → publisher page |
| Nawrocki, E. P., Eddy, S. R. (2013). Infernal 1.1: 100-fold faster RNA homology searches. *Bioinformatics* 29(22), 2933–2935. doi:10.1093/bioinformatics/btt509 | the structure-aware membership check (step 11, `cmscan`) | 2026-09-25, search result → publisher page |
| Szikszai, M., Wise, M., Datta, A., Ward, M., Mathews, D. H. (2022). Deep learning models for RNA secondary structure prediction (probably) do not generalize across families. *Bioinformatics* 38(16), 3892–3899. doi:10.1093/bioinformatics/btac415 | why the split must be by family, not by identity | 2026-09-25, search result → OUP page |
| Sato, K., Akiyama, M., Sakakibara, Y. (2021). RNA secondary structure prediction using deep learning with thermodynamic integration (MXfold2). *Nature Communications* 12, 941. doi:10.1038/s41467-021-21194-4 | the closest-to-generalising deep folding model in Szikszai et al. | 2026-09-25, search result → Nature page |

## Phase 2 — masked discrete diffusion

| reference | used for | verified |
|---|---|---|
| Sahoo, S. S., et al. (2024). Simple and Effective Masked Diffusion Language Models (MDLM). *NeurIPS 2024*. arXiv:2406.07524 | the 1/t-weighted NELBO and the absorbing-state framework we implement; its DNA experiment (see the novelty table) | 2026-09-25, search result (NeurIPS proceedings entry); full author list and the DNA section to re-read from the full text |
| Ou, J., Nie, S., Xue, K., Zhu, F., Sun, J., Li, Z., Li, C. (2024). Your Absorbing Discrete Diffusion Secretly Models the Conditional Distributions of Clean Data (RADD). *ICLR 2025*. arXiv:2406.03736 | why our denoiser needs no time input (D-010) | 2026-09-25, search result → arXiv, ICLR poster page |
| Zheng, K., Chen, Y., Mao, H., Liu, M.-Y., Zhu, J., Zhang, Q. (2024). Masked Diffusion Models are Secretly Time-Agnostic Masked Models and Exploit Inaccurate Categorical Sampling. arXiv:2409.02908 | why letters are sampled from float64 probabilities (32-bit Gumbel sampling reduces diversity) | 2026-09-25, search result → arXiv |

## Phase 3 — honest evaluation

| reference | used for | verified |
|---|---|---|
| Dirks, R. M., Lin, M., Winfree, E., Pierce, N. A. (2004). Paradigms for computational nucleic acid design. *Nucleic Acids Research* 32(4), 1392–1403 | the ensemble defect as a design objective (NED) | 2026-09-25, search result → OUP, PubMed 14990744 |
| Zadeh, J. N., Steenberg, C. D., Bois, J. S., Wolfe, B. R., Pierce, M. B., Khan, A. R., Dirks, R. M., Pierce, N. A. (2011). NUPACK: Analysis and design of nucleic acid systems. *Journal of Computational Chemistry* 32(1), 170–173. doi:10.1002/jcc.21596 | NUPACK designs sequences for target structures by the ensemble defect | 2026-09-26, search result → Wiley page, Caltech repository |
| Clote, P., Ferré, F., Kranakis, E., Krizanc, D. (2005). Structural RNA has lower folding energy than random RNA of the same dinucleotide frequency. *RNA* 11(5), 578–591 | the MFE z-score against dinucleotide shuffles (`beats_shuffles`, `mfe_z`) | 2026-09-25, search result → RNA journal, PubMed 15840812 |
| Altschul, S. F., Erickson, B. W. (1985). Significance of nucleotide sequence alignments: a method for random sequence permutation that preserves dinucleotide and codon usage. *Molecular Biology and Evolution* 2, 526–538 | the dinucleotide shuffle (random Eulerian walk) | 2026-09-25, search result → PubMed 3870875 |
| Wayment-Steele, H. K., Kladwang, W., Strom, A. I., Lee, J., Treuille, A., Becka, A., Eterna Participants, Das, R. (2022). RNA secondary structure packages evaluated and improved by high-throughput experiments. *Nature Methods*. doi:10.1038/s41592-022-01605-0 | EternaFold, the second oracle (D-013) | 2026-09-25 (title, DOI from the Nature page); volume/pages *Nat. Methods* 19, 1234–1242 confirmed 2026-09-26 from a citing paper's reference |
| Anderson-Lee, J., et al. (2016). Principles for Predicting RNA Secondary Structure Design Difficulty. *Journal of Molecular Biology* 428(5), 748–757 | the Eterna100 benchmark (`eterna100_test`) | 2026-09-25, search result → PubMed 26902426 |

## Phase 4 — state-space models and Mamba

| reference | used for | verified |
|---|---|---|
| Gu, A., Goel, K., Ré, C. (2022). Efficiently Modeling Long Sequences with Structured State Spaces (S4). *ICLR 2022*. arXiv:2111.00396 | the time-invariant state-space model trained as a convolution (instalment 1) | 2026-09-25, search result → arXiv, ML Anthology |
| Gu, A., Dao, T. (2023). Mamba: Linear-Time Sequence Modeling with Selective State Spaces. *COLM 2024*. arXiv:2312.00752 | selection, the parallel scan, the hardware-aware kernel; layers without MLP blocks | 2026-09-25, search result → arXiv; COLM 2024 (Outstanding Paper) from a search summary |
| Dao, T., Gu, A. (2024). Transformers are SSMs: Generalized Models and Efficient Algorithms Through Structured State Space Duality (Mamba-2). *ICML 2024*. arXiv:2405.21060 | Mamba-2: one keep factor per head, state-space duality, chunked algorithm | 2026-09-25, search result → arXiv, ICML listing |
| Zhu, L., Liao, B., Zhang, Q., Wang, X., Liu, W., Wang, X. (2024). Vision Mamba: Efficient Visual Representation Learning with Bidirectional State Space Model. *ICML 2024*. arXiv:2401.09417 | precedent for BiMamba's sharing pattern (D-016) | 2026-09-25, search result → dblp, ICML poster page; the sharing detail itself to re-read from the full text |
| Schiff, Y., Kao, C.-H., Gokaslan, A., Dao, T., Gu, A., Kuleshov, V. (2024). Caduceus: Bi-Directional Equivariant Long-Range DNA Sequence Modeling. *ICML 2024*. arXiv:2403.03234 | BiMamba precedent (tied projections, D-016); bidirectional Mamba on DNA | 2026-09-25, search result → arXiv, ICML page; the weight-tying detail to re-read from the full text |
| Hwang, S., Lahoti, A., Dao, T., Gu, A. (2024). Hydra: Bidirectional State Space Models Through Generalized Matrix Mixers. arXiv:2407.09941 | the principled bidirectional alternative we did not use (D-016) | 2026-09-25, search result → arXiv, dblp |
| Jelassi, S., Brandfonbrener, D., Kakade, S. M., Malach, E. (2024). Repeat After Me: Transformers are Better than State Space Models at Copying. *ICML 2024*, PMLR 235, 21502–21521. arXiv:2402.01032 | the fixed-size state limits copying from context: why base pairing is an open question for Mamba | 2026-09-25, search result → PMLR page |
| Arora, S., Eyuboglu, S., Timalsina, A., Johnson, I., Poli, M., Zou, J., Rudra, A., Ré, C. (2023). Zoology: Measuring and Improving Recall in Efficient Language Models. arXiv:2312.04927 | attention-free *gated-convolution* models lag attention mostly on in-context recall. Cite for that family, not as a Mamba result (Jelassi et al. test Mamba directly) | 2026-09-25, search result → arXiv |
| Singh, V., Ostapenko, O., Noël, P.-A., Belilovsky, E., Scholak, T. (2025). DiffuMamba: High-Throughput Diffusion LMs with Mamba Backbone. arXiv:2511.15927 | the text-domain precedent for BiMamba + masked diffusion (CLAUDE.md §3.3) | 2026-09-25, arXiv abstract page |
| DGRNA: a long-context RNA foundation model with bidirectional attention Mamba2. *bioRxiv* (2024). doi:10.1101/2024.10.31.621427 | the RNA-encoder precedent (CLAUDE.md §3.3) | 2026-09-25, search result → bioRxiv; author list to add |

## Related RNA generation and design (for Phases 5–6)

| reference | relevance | verified |
|---|---|---|
| RDiffusion: Unlocking Programmable and Creative RNA Sequence Design with RDiffusion. *bioRxiv* (2026). doi:10.64898/2026.06.13.732023 | Transformer discrete diffusion for RNA, conditioned on structure, family, function: the closest Phase 5 comparison | 2026-09-25, search result → bioRxiv; authors to add |
| Wang, Z., Tang, B., Zhang, F., Han, S., Liu, P. (2026). RIBOSPAN: A Long-Context RNA Foundation Model for Versatile RNA Modeling. arXiv:2608.22849 | large Transformer RNA model with conditioned discrete-diffusion generation | 2026-09-25, arXiv abstract page |
| Huang, K., Yang, Y., Fu, K., Chu, Y., Cong, L., Wang, M. (2024). Latent Diffusion Models for Controllable RNA Sequence Generation. arXiv:2409.09828 | continuous latent diffusion for RNA (a different family) | 2026-09-25, arXiv abstract page |
| Gautam, M., Dai, N., Zhou, T., Xie, B., Mathews, D., Huang, L. (2026). Designing RNAs with Language Models. arXiv:2602.12470 | structure-to-sequence design by an autoregressive model + reinforcement learning: a Phase 5 baseline class | 2026-09-25, arXiv abstract page |
| Cazenave, T. (2026). The Montparnasse Algorithm for RNA Design. arXiv:2606.07562 | Monte Carlo search design (Eterna100): a Phase 5 baseline class | 2026-09-25, arXiv abstract page |

## Phase 5 — guidance and steering (candidates, not decisions)

Found 2026-09-25 while preparing Phase 5; the methods compared in Phase 5 are
fixed by a dated protocol amendment after the Phase 5 concept block.

| reference | relevance | verified |
|---|---|---|
| Ho, J., Salimans, T. (2022). Classifier-Free Diffusion Guidance. arXiv:2207.12598 | classifier-free guidance: train with the condition sometimes dropped, mix conditional and unconditional predictions at sampling | 2026-09-25, search result → arXiv |
| Schiff, Y., et al. (2025). Simple Guidance Mechanisms for Discrete Diffusion Models. *ICLR 2025*. arXiv:2412.10193 | classifier-free and classifier-based guidance derived for discrete (incl. masked) diffusion | 2026-09-25, search result → ICLR proceedings page |
| Nisonoff, H., Xiong, J., Allenspach, S., Listgarten, J. (2024). Unlocking Guidance for Discrete State-Space Diffusion and Flow Models. arXiv:2406.01572 | principled guidance for discrete state spaces (continuous-time Markov chains); DNA and protein examples | 2026-09-25, search result → arXiv |
| Li, X., et al. (2024). Derivative-Free Guidance in Continuous and Discrete Diffusion Models with Soft Value-Based Decoding (SVDD). arXiv:2408.08252 | steering a pretrained diffusion model with a non-differentiable reward, no fine-tuning; demonstrated on DNA/RNA | 2026-09-25, search result → arXiv |
| Reward-Guided Discrete Diffusion via Clean-Sample Markov Chain for Molecule and Biological Sequence Design (2026). arXiv:2602.09424 | Metropolis–Hastings over clean samples; masked diffusion; needs only rewards of complete sequences | 2026-09-25, search result → arXiv; authors to add |
| Self-Rewarding Sequential Monte Carlo for Masked Diffusion Language Models (2026). arXiv:2602.01849 | particle filtering (SMC) for masked diffusion | 2026-09-25, search result → arXiv; authors to add |
| Commitment Before Realization: When Classifier-Free Guidance Becomes Unnecessary in Masked Diffusion Language Models (2026). arXiv:2608.08082 | a caution about classifier-free guidance in masked diffusion, to read before choosing it | 2026-09-25, title from a search result only; to read |

## Pivot literature review — 2026-09-27
These are leads and verified content notes, not a completed novelty exclusion.
The older backbone-combination claim above is no longer the project's main claim.

- Designing RNAs with Language Models (Gautam et al., arXiv:2602.12470v1):
  primary full text inspected at https://arxiv.org/html/2602.12470v1 .
  Structure conditioning, constrained generation, supervised training and RL
  already coexist. Check its evaluation budgets and settings before comparison.
- SamplingDesign: official implementation inspected at
  https://github.com/weiyutang1010/SamplingDesign .
  Dependency-aware distribution optimization is existing work; source/build
  available. Full default benchmarks can be expensive. Pin a commit and read
  the paper before reproducing or quoting exact performance.
- The Montparnasse Algorithm for RNA Design, arXiv:2606.07562v1:
  primary full text inspected at https://arxiv.org/html/2606.07562v1 .
  Reports 100/100 Eterna100 V1 solutions with parallel search. This is an author
  report, not independently reproduced here. Match versions/budgets before claims.
- Conditional Generation And Inpainting Of Non-coding RNA Sequences With Masked
  Discrete Diffusion, bioRxiv 10.64898/2026.09.17.752279:
  https://www.biorxiv.org/content/10.64898/2026.09.17.752279v1 .
  Indexed abstract only; full-text access failed. Detailed architectural overlap
  and novelty remain unresolved.
- Additional required prior-art checks: RNA negative design, dependency-component
  resampling, learned local search, repair/search distillation and targeted
  diffusion remasking. Do not call paired moves or iterative repairs novel alone.

Assistant choice reference (not RNA science):
https://developers.openai.com/api/docs/guides/model-selection opened 2026-09-27.
Sol Medium is suggested for everyday coding/research and Luna for lighter work.
This does not establish exact Codex subscription-limit savings or Claude pricing.

## Repair pilot sources and baselines — 2026-09-27 (session 07)
Checked from primary pages this session; notes are what was read, not a novelty exclusion.

| reference | relevance | verified |
|---|---|---|
| Zhou, T., Dai, N., Li, S., Ward, M., Mathews, D.H., Huang, L. (2023). RNA design via structure-aware multifrontier ensemble optimization (SAMFEO). *Bioinformatics* 39(S1):i563. Code https://github.com/shanry/SAMFEO | strong ensemble-objective baseline; structured (coordinated) mutations; pinned main@e78b4b5; NO license file (GitHub API: none) — local use only | 2026-09-27, repository cloned, code read, own test reproduced |
| Hofacker, I.L. et al. (1994). Fast folding and comparison of RNA secondary structures. *Monatsh. Chem.* 125:167 (RNAinverse) | MFE adaptive walk with hierarchical decomposition; the strongest uMFE-per-second method on our hard dev set | 2026-09-27, ViennaRNA 2.7.2 binary and Python API used; paper not re-read |
| Zadeh, J.N., Wolfe, B.R., Pierce, N.A. (2011). Nucleic acid sequence design via efficient ensemble defect optimization. *J. Comput. Chem.* 32:439 (NUPACK design) | defect-weighted mutation + hierarchical decomposition: prior art for feedback-directed edits | from memory; to re-read before any comparison |
| Gautam, M., Dai, N., Zhou, T., Xie, B., Mathews, D., Huang, L. (2026). Designing RNAs with Language Models. arXiv:2602.12470. Code/data https://github.com/KuNyaa/RNA-Design-LM (MIT); HF Milanmg/LLM-RNA-Design-2026 rev 609f573b | Qwen2.5-0.5B, SL on 10M SAMFEO designs + RL on Eterna web puzzles (~113 H100-h); Eterna100 MFE/uMFE 75/73; best-of-10^4 mean P 0.586 vs SAMFEO 0.580. Source of our Eterna web puzzles (YRL_raw, 18,364) and audit copies of Eterna100/v2, Rfam27, RNAsolo-764 | 2026-09-27, arXiv HTML + repo + HF file listing |
| The Montparnasse Algorithm for RNA Design (2026). arXiv:2606.07562 | GNRPA + structural prior; Eterna100 V1 (Turner 1999): 81 @10 s, 99 @10,240 s, 100 @81,920 s with 50 threads on a 256-core server; DesiRNA 25/96/100 | 2026-09-27, arXiv HTML |
| Tang, W.Y., Dai, N., Zhou, T., Mathews, D.H., Huang, L. SamplingDesign. https://github.com/weiyutang1010/SamplingDesign (Apache-2.0) | sampling-based continuous optimisation; defaults 2,000 steps x 2,500 LinearPartition-V samples; cloned f0283c49 and built (separate g++ env), not yet run | 2026-09-27, repository README + build |
| Koodli, R.V. et al. (2019). EternaBrain. *PLoS Comput. Biol.* 15:e1007059; https://github.com/eternagame/EternaBrain (MIT) | learning player moves (repairs) — prior art for learned move policies | 2026-09-27, repository listing |
| Runge, F. et al. (2019). Learning to Design RNA (LEARNA). *ICLR 2019* | RL design; Rfam-Learn sets | from memory |
| Factorization Machine with Quadratic-Optimization Annealing for RNA Inverse Folding (2026). arXiv:2602.16643 | surrogate-assisted black-box optimisation to cut expensive evaluations: prior art for filtering/surrogates | 2026-09-27, search result only; to read |
| Struct2SeQ: RNA inverse folding with Deep Q-Learning (2026). bioRxiv 10.64898/2026.01.16.700031 | learned RL policy for design | 2026-09-27, search result only |
| RIFT-VAE: grammar-conditioned pretraining and latent-space optimization for RNA inverse folding (2026). bioRxiv 10.64898/2026.08.12.744415 | latent-space optimisation for design | 2026-09-27, search result only |

## Session 09 additions — 2026-09-27 (closest prior art for the energy pre-screen and residual idea)
| reference | relevance | verified |
|---|---|---|
| Busch, A., Backofen, R. (2006). INFO-RNA — a fast approach to inverse RNA folding. *Bioinformatics* 22:1823; INFO-RNA server, *NAR* 35:W310 (2007), doi:10.1093/nar/gkm218 | its stochastic local search examines sequence neighbours in order of the energy difference when folding into the TARGET structure (largest improvement first), after an energy-minimising DP initialisation: direct prior art for target-energy-guided proposals. Our energy pre-screen (best-of-K by E_target inside SAMFEO/DesiRNA) is an application of this idea to ensemble optimisers, not a new heuristic | 2026-09-27, NAR server paper abstract/search result; full text to read |
| Zhou, T., Mathews, D.H., Huang, L. (2026). Probabilistic RNA designability via interpretable ensemble approximation and dynamic decomposition (LinearDecompose / RNA-Undesign). arXiv:2602.13610; https://github.com/shanry/RNA-Undesign (CC BY-NC-ND 4.0 per page) | rival structures and probability bounds for designability; not integrated into design search (future work per authors). Closest overlap for the rival-residual idea | 2026-09-27, arXiv abstract + HTML |
| Tang, W.Y., Dai, N., Zhou, T., Mathews, D.H., Huang, L. SamplingDesign, *Nat. Commun.* (2026); PMC13031908; arXiv:2412.08751 | Eterna100 (Turner 2004): 79 MFE / 78 uMFE vs SAMFEO 76/76, NEMO 78/79; geometric-mean P 0.502 vs 0.239; NED 0.035 vs 0.041; 79 designable, 18 proven undesignable, 3 unresolved | 2026-09-27, PMC full text |
| Kozyra, T. et al. DesiRNA (replica-exchange MC RNA design), PMC11744100; https://github.com/fryzjergda/DesiRNA (Apache-2.0, pinned bdb4908) | Eterna100 V2 (Turner 2004): 85 < 1 min, 95 < 1 h, 97 in 24 h (10 threads/simulation); V1 (Turner 1999) all 100 in 24 h | 2026-09-27, PMC text; author list to verify |
| Cazenave, T. (2025). Eterna is Solved. arXiv:2505.02110; and The Montparnasse Algorithm for RNA Design, arXiv:2606.07562 | GNRPA-based search; no public code found | 2026-09-27, arXiv abstracts |
| dFX: Leveraging neural networks to correct FoldX free energy estimates (ACS Omega 2026; bioRxiv 2024.09.23.614615) | learned residual over physics energy terms (proteins): prior art for "physics + learned residual" | 2026-09-27, search result |
