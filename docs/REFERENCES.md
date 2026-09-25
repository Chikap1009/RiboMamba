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
| Zadeh, J. N., et al. (2011). NUPACK (analysis and design of nucleic acid systems), *J. Comput. Chem.*; and ensemble defect optimisation | NUPACK optimises the ensemble defect | **not yet verified** |
| Clote, P., Ferré, F., Kranakis, E., Krizanc, D. (2005). Structural RNA has lower folding energy than random RNA of the same dinucleotide frequency. *RNA* 11(5), 578–591 | the MFE z-score against dinucleotide shuffles (`beats_shuffles`, `mfe_z`) | 2026-09-25, search result → RNA journal, PubMed 15840812 |
| Altschul, S. F., Erickson, B. W. (1985). Significance of nucleotide sequence alignments: a method for random sequence permutation that preserves dinucleotide and codon usage. *Molecular Biology and Evolution* 2, 526–538 | the dinucleotide shuffle (random Eulerian walk) | 2026-09-25, search result → PubMed 3870875 |
| Wayment-Steele, H. K., Kladwang, W., Strom, A. I., Lee, J., Treuille, A., Becka, A., Eterna Participants, Das, R. (2022). RNA secondary structure packages evaluated and improved by high-throughput experiments. *Nature Methods*. doi:10.1038/s41592-022-01605-0 | EternaFold, the second oracle (D-013) | 2026-09-25, title and DOI from the Nature page; volume/pages (19, 1234–1242) from a search summary that also garbled the title: check against the DOI |
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
