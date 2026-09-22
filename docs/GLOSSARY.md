# Glossary — RiboMamba

Every technical term used in this project, defined once. Format per entry:

- **Definition:** one plain-language sentence.
- **Analogy:** from everyday life or electronics.
- **Where it appears:** in our code or docs. ("Not yet in code" is fine early on.)
- **First explained:** logbook reference.

Sections: Biology · Machine learning · Maths · Software.

---

## Biology

### Molecule
- **Definition:** A group of atoms held together by chemical bonds, acting as one physical object.
- **Analogy:** A soldered assembly. Individual components (atoms) joined into one unit that behaves as a whole.
- **Where it appears:** Not yet in code.
- **First explained:** session 01.

### Polymer
- **Definition:** A long molecule made by linking many similar small units end to end in a chain.
- **Analogy:** A chain of beads, or a shift register made of identical flip-flop stages.
- **Where it appears:** Not yet in code.
- **First explained:** session 01.

### DNA (deoxyribonucleic acid)
- **Definition:** The cell's long-term storage molecule for genetic instructions. Usually two strands wound together; uses the letters A, C, G, T.
- **Analogy:** ROM. The master copy the cell never executes from directly.
- **Where it appears:** Not in code. Mentioned only to contrast with RNA.
- **First explained:** session 01.

### RNA (ribonucleic acid)
- **Definition:** A single-stranded chain molecule copied from DNA, written in the letters A, C, G, U. Some RNAs carry instructions to build proteins; others fold into shapes and do jobs themselves.
- **Analogy:** A working copy loaded from ROM into RAM. Some copies are read; some *become* little machines.
- **Where it appears:** Everything. Our model generates RNA sequences.
- **First explained:** session 01.

### Nucleotide
- **Definition:** One link in an RNA (or DNA) chain: a backbone piece (sugar + phosphate) with one base attached.
- **Analogy:** One stage of a shift register. Identical hardware, but it holds one symbol.
- **Where it appears:** Each nucleotide will become one *token* in our model (explained in Phase 1).
- **First explained:** session 01.

### Base (nucleobase)
- **Definition:** The variable part of a nucleotide. In RNA it is one of four: A (adenine), U (uracil), G (guanine), C (cytosine).
- **Analogy:** The value stored in a register stage. The stage is always the same; the value changes.
- **Where it appears:** Our vocabulary of 4 letters (plus special tokens later).
- **First explained:** session 01.

### Backbone (sugar-phosphate backbone)
- **Definition:** The repeating, identical chain of sugar and phosphate groups that holds the bases in order.
- **Analogy:** A PCB trace or bus that connects the stages. It carries no data itself; it only fixes the order.
- **Where it appears:** Not in code. We model only the sequence of bases.
- **First explained:** session 01.

### Sequence
- **Definition:** The ordered list of bases in an RNA, written as a string, e.g. `GGGAAACCC`.
- **Analogy:** A serial bitstream, where each symbol carries 2 bits (4 possibilities).
- **Where it appears:** The input and output of our model.
- **First explained:** session 01.

### 5′ end and 3′ end ("five-prime", "three-prime")
- **Definition:** The two ends of an RNA chain, which are chemically different, so the chain has a direction. Sequences are written 5′ → 3′, left to right, by convention.
- **Analogy:** MSB-first vs LSB-first in a serial protocol. Reading the same bits in the opposite order gives a different word.
- **Where it appears:** All our sequences are stored in 5′ → 3′ order.
- **First explained:** session 01.

### Protein
- **Definition:** A different kind of chain molecule (made of 20 kinds of "amino acids") that does most of the work in a cell. Built by reading certain RNAs.
- **Analogy:** The finished product the factory manufactures from the instruction sheet.
- **Where it appears:** Not in code. Mentioned for context only.
- **First explained:** session 01.

### Covalent bond
- **Definition:** A strong chemical bond where atoms share electrons. It does not break at body temperature. It is what links the RNA backbone.
- **Analogy:** A solder joint: permanent under normal operating conditions.
- **Where it appears:** Not in code. It is why the sequence *order* never changes.
- **First explained:** session 01.

### Hydrogen bond
- **Definition:** A weak attraction between specific atoms on two bases. Weak enough that random thermal jiggling can break it.
- **Analogy:** One hook of Velcro: it holds, but not firmly.
- **Where it appears:** Not in code. It is the physical reason base pairs exist.
- **First explained:** session 01.

### Base pair
- **Definition:** Two bases, at different positions in the chain, held together by hydrogen bonds. Allowed pairs: G–C, A–U, G–U.
- **Analogy:** A mated connector pair. Only matching plugs and sockets fit.
- **Where it appears:** The target structures our model is conditioned on (Phase 5) and the folding oracle's output (Phase 3).
- **First explained:** session 01.

### Watson–Crick pairs (canonical pairs)
- **Definition:** The two "standard" pairs: G–C (3 hydrogen bonds, strongest) and A–U (2 hydrogen bonds).
- **Analogy:** A 3-pin keyed connector (G–C) and a 2-pin one (A–U). The 3-pin one grips harder.
- **Where it appears:** Pairing rules inside folding software (ViennaRNA).
- **First explained:** session 01.

### Wobble pair (G–U)
- **Definition:** A weaker, slightly misaligned pair between G and U that RNA allows.
- **Analogy:** A connector that fits but a little loosely.
- **Where it appears:** Pairing rules inside folding software.
- **First explained:** session 01.

### Complementary
- **Definition:** Two stretches of sequence are complementary if their bases can pair position by position when lined up in opposite directions.
- **Analogy:** A plug and a socket strip whose pins all match.
- **Where it appears:** Not yet in code.
- **First explained:** session 01.

### Stacking
- **Definition:** Consecutive base pairs sit flat on top of each other like a stack of coins, and this stacking is what actually stabilises them. A lone pair is unstable.
- **Analogy:** One Velcro hook doesn't hold; a strip of hooks does.
- **Where it appears:** The energy model used by folding software (session 01, concept 4).
- **First explained:** session 01.

### Antiparallel
- **Definition:** When RNA folds back on itself, the two paired stretches run in opposite directions, so the first base pairs with the last, the second with the second-to-last, and so on.
- **Analogy:** Folding a strip of paper in half: the two ends meet.
- **Where it appears:** Dot-bracket notation (concept 3).
- **First explained:** session 01.

### Hairpin (stem-loop)
- **Definition:** The simplest RNA fold: a stretch pairs with a later stretch, making a paired "stem" capped by an unpaired "loop" at the turn.
- **Analogy:** A hairpin, literally: two parallel arms joined by a bend.
- **Where it appears:** Everywhere in RNA structures. Detailed in concept 3.
- **First explained:** session 01.

### Minimum hairpin loop size
- **Definition:** The turn of a hairpin must contain at least 3 unpaired bases, because the backbone cannot bend more tightly.
- **Analogy:** The minimum bend radius of a cable or PCB trace.
- **Where it appears:** A hard rule in folding software.
- **First explained:** session 01.

### Primary / secondary / tertiary structure
- **Definition:** Primary = the sequence of bases. Secondary = which bases are paired with which. Tertiary = the actual 3D shape in space.
- **Analogy:** Component list → netlist/schematic (what connects to what) → physical layout (where everything sits in space).
- **Where it appears:** We model primary (the output) and secondary (the target). Tertiary is out of scope.
- **First explained:** session 01.

### Stem (helix)
- **Definition:** A run of consecutive stacked base pairs.
- **Analogy:** A strip of Velcro, or a ladder whose rungs are the pairs.
- **Where it appears:** Runs of `(((` … `)))` in dot-bracket.
- **First explained:** session 01.

### Hairpin loop
- **Definition:** The unpaired bases at the tip of a hairpin, closed by one pair. Minimum 3 bases.
- **Analogy:** The bend of a hairpin.
- **Where it appears:** `(...)` patterns in dot-bracket.
- **First explained:** session 01.

### Bulge
- **Definition:** Unpaired bases on only one side of a stem, interrupting it.
- **Analogy:** A kink on one wire of a twisted pair.
- **Where it appears:** e.g. `((.((...))))`.
- **First explained:** session 01.

### Internal loop
- **Definition:** Unpaired bases on both sides of a stem, interrupting it.
- **Analogy:** A small gap in the middle of a zip, on both sides.
- **Where it appears:** e.g. `((..((...))..))`.
- **First explained:** session 01.

### Multiloop (junction)
- **Definition:** A loop from which three or more stems branch out.
- **Analogy:** A junction box where several cables meet.
- **Where it appears:** e.g. `((..(((...)))..(((...)))..))`.
- **First explained:** session 01.

### Pseudoknot
- **Definition:** Two base pairs that cross: (i, j) and (k, l) with i < k < j < l. Real, but excluded by standard secondary-structure tools and by this project.
- **Analogy:** Two wires that must cross on a single-layer board with no via.
- **Where it appears:** A known limitation of our evaluation (to be recorded in STUDY_GUIDE Part 9).
- **First explained:** session 01.

### Dot-bracket notation
- **Definition:** A string as long as the sequence, where `(` pairs with a later matching `)`, and `.` is unpaired.
- **Analogy:** Balanced parentheses in code.
- **Where it appears:** ViennaRNA's output format; the structure targets our model is conditioned on (Phase 5).
- **First explained:** session 01.

### Folding (the forward problem)
- **Definition:** Predicting which structure a given sequence adopts: sequence → structure.
- **Analogy:** Simulation. Given a circuit, compute what it does.
- **Where it appears:** Our evaluation oracle (Phase 3) folds every generated sequence.
- **First explained:** session 01.

### Free energy (ΔG)
- **Definition:** A single number scoring how stable a structure is, relative to the unfolded chain (which is 0). More negative = more stable. Defined as ΔG = ΔH − T·ΔS, where ΔH is the energy released by forming bonds (negative = favourable), T is absolute temperature in kelvin (body ≈ 310 K), and ΔS is the change in the chain's freedom of movement (folding reduces freedom, so ΔS < 0 and −T·ΔS is a positive cost).
- **Analogy:** The height of a valley in a landscape. A ball (the molecule) settles in low valleys while the ground shakes (thermal noise).
- **Where it appears:** ViennaRNA's output; MFE distributions in our evaluation (Phase 3).
- **First explained:** session 01.

### Enthalpy (ΔH) and entropy (ΔS)
- **Definition:** The two ingredients of free energy. Enthalpy is the energy gained from forming bonds (pairs, stacks). Entropy is the amount of freedom (number of possible arrangements) the molecule has; losing it is a cost that grows with temperature.
- **Analogy:** Enthalpy = the glue pulling a formation together; entropy = everyone's urge to wander off. Heat makes the urge stronger.
- **Where it appears:** Only inside the energy model. We never compute them directly.
- **First explained:** session 01.

### kcal/mol
- **Definition:** The unit of free energy used in RNA folding: kilocalories per mole, where a mole is a fixed, very large count of molecules (6 × 10²³). In practice only *differences* matter. Thermal noise at body temperature is worth ≈ 0.6 kcal/mol.
- **Analogy:** Volts on a logic rail: the absolute number matters less than the margin between levels.
- **Where it appears:** Every energy number in this project.
- **First explained:** session 01.

### Nearest-neighbour energy model
- **Definition:** A way to compute a structure's ΔG by adding up local pieces: each stack of two adjacent pairs contributes a (negative) bonus, each loop a (mostly positive) penalty, looked up from experimentally measured tables.
- **Analogy:** Estimating a chip's power by summing per-block contributions from a characterised cell library.
- **Where it appears:** Inside ViennaRNA (our folding oracle).
- **First explained:** session 01.

### Turner parameters
- **Definition:** The standard tables of experimentally measured energy values (stacks, loops, etc.) used by the nearest-neighbour model, named after the chemist Douglas Turner.
- **Analogy:** A standard-cell library's characterisation data (.lib files).
- **Where it appears:** ViennaRNA's default energy parameters.
- **First explained:** session 01.

### Minimum free energy (MFE) / MFE structure
- **Definition:** The MFE structure is the valid secondary structure with the lowest total ΔG for a given sequence; the MFE is that ΔG value. It is the model's best guess at the structure the RNA adopts.
- **Analogy:** The lowest valley in the landscape.
- **Where it appears:** Our designability metric checks whether a generated sequence's MFE structure equals the target (Phase 3).
- **First explained:** session 01.

### Energy gap (margin)
- **Definition:** How much lower the best structure's energy is than the next-best rival's. Rule of thumb: every ≈1.4 kcal/mol of gap means ≈10× more time spent in the better structure.
- **Analogy:** The noise margin of a logic gate. If the margin is smaller than the noise, the output flips.
- **Where it appears:** A likely extra evaluation criterion (Phase 3).
- **First explained:** session 01.

### Zuker algorithm
- **Definition:** The classic dynamic-programming algorithm that finds the MFE structure in O(N³) time. It relies on the no-crossing rule so that each sub-stretch can be solved independently.
- **Analogy:** Static timing analysis, which never lists every path but reuses per-node results.
- **Where it appears:** The core of ViennaRNA's `RNAfold`.
- **First explained:** session 01.

### Boltzmann distribution
- **Definition:** The physics rule for how a molecule divides its time among possible structures: probability ∝ e^(−ΔG/RT), where R is the gas constant (0.001987 kcal/(mol·K), a unit converter from temperature to energy), T is the temperature in kelvin, and RT ≈ 0.616 kcal/mol at 37 °C is the thermal noise level. For two structures, the time ratio is e^(gap/RT) = 10^(gap/1.42): every ≈1.42 kcal/mol of gap is a 10× preference.
- **Analogy:** MOSFET subthreshold swing (≈60 mV/decade at room temperature). The same physics, thermal energy × ln 10 per decade.
- **Where it appears:** Energy-gap reasoning; ensemble-based metrics (Phase 3).
- **First explained:** session 01.

### Dangling end
- **Definition:** An unpaired base right next to the end of a helix. It stacks onto the last pair and gives a small energy bonus (about −0.1 to −1.7 kcal/mol).
- **Analogy:** A loose coin resting on top of a stack. It doesn't belong to the stack, but it still helps hold it steady.
- **Where it appears:** Session 02: why ViennaRNA scored `.((...)).` at +1.10 instead of our toy +2.1, and part of why `GGGAAACCA` folds. Our toy model left it out.
- **First explained:** session 02.

### Terminal mismatch (and why a 4-nt loop can be cheaper than a 3-nt loop)
- **Definition:** In a loop of 4 or more bases, the first unpaired bases next to the closing pair stack onto it and earn a bonus (a G·A first mismatch is especially good). Loops of exactly 3 are too tight to get this bonus.
- **Analogy:** A slightly wider cable bend that lets the connector seat properly, so it ends up more stable than the tightest bend.
- **Where it appears:** Session 02: in `GGGAAACCA`, the 4-nt hairpin loop cost +3.10, versus +5.40 for the 3-nt loop.
- **First explained:** session 02.

### Suboptimal structures (`RNAsubopt`)
- **Definition:** The structures just above the MFE in energy, i.e. the rivals. `RNAsubopt -e X` lists every structure within X kcal/mol of the best.
- **Analogy:** The second- and third-best timing paths, just behind the critical path.
- **Where it appears:** Session 02: `GGGAAACCC`'s nearest rival is only 0.20 kcal/mol above its MFE.
- **First explained:** session 02.

### `RNAeval`
- **Definition:** ViennaRNA's tool for computing the free energy of a structure *you choose* for a sequence (rather than the best one). With `-v` it lists the energy of every stack and loop, which is the nearest-neighbour sum written out.
- **Analogy:** Evaluating one specific path's delay, rather than searching for the worst path.
- **Where it appears:** Session 02, to check our hand calculations piece by piece.
- **First explained:** session 02.

### Ensemble and partition function
- **Definition:** The ensemble is every structure a sequence can take, each weighted by e^(−ΔG/RT). The partition function Z is the sum of all those weights. A structure's probability (its share of the time) is its weight divided by Z. ViennaRNA computes Z exactly with dynamic programming (`RNAfold -p`).
- **Analogy:** Occupancy statistics across all states of a noisy state machine, rather than just the most likely state.
- **Where it appears:** Session 02: `GGGAAACCC` spends 50.7 % of its time in its MFE shape; `GGGAAACCA` 93.9 %. It's a likely extra success metric in Phase 3.
- **First explained:** session 02.

### Energy units in ViennaRNA output
- **Definition:** `RNAfold` prints kcal/mol (e.g. −1.20). `RNAeval -v` prints per-loop values in units of 0.01 kcal/mol (e.g. −330 = −3.30).
- **Analogy:** The same quantity read in mV versus V.
- **Where it appears:** Session 02 outputs.
- **First explained:** session 02.

### Mutation
- **Definition:** A change of one letter (base) in a sequence, e.g. `GGGAAACCC` → `GGGAAACCA`.
- **Analogy:** A single bit flip.
- **Where it appears:** Local-search design methods; later, sequence-editing ideas in Phase 5.
- **First explained:** session 01.

### Inverse folding (RNA design)
- **Definition:** Finding a sequence whose MFE structure is a given target: structure → sequence. This is the problem our project attacks.
- **Analogy:** Synthesis. Given a spec, find a circuit that meets it.
- **Where it appears:** The whole project; conditional generation in Phase 5.
- **First explained:** session 01.

### Designability (preview)
- **Definition:** The fraction of generated sequences that actually fold (according to the oracle) into their intended target structure.
- **Analogy:** Yield: the fraction of manufactured chips that pass test.
- **Where it appears:** A headline metric in Phase 3. Defined precisely there.
- **First explained:** session 01 (preview only).

### Genome, contig, accession
- **Definition:** A **genome** is an organism's complete DNA. Sequencing produces it in pieces called **contigs**, and each stored piece gets an **accession**, a unique catalogue number such as `AAAA02036851.1`.
- **Analogy:** A genome is a whole library; contigs are loose chapters; the accession is the shelf mark.
- **Where it appears:** Rfam ids like `AAAA02036851.1/1-118` = accession, then positions 1–118 on it. Reversed coordinates (`12691-12604`) mean the RNA sits on the opposite DNA strand.
- **First explained:** session 03.

### Homologous (homology)
- **Definition:** Two sequences are homologous if they descend from a common ancestor sequence, however much they have changed since.
- **Analogy:** Two chip designs derived from the same original layout, even after years of independent revisions.
- **Where it appears:** The reason family members leak across a random split (D-008).
- **First explained:** session 03.

### RNA family
- **Definition:** A set of homologous RNAs: different letters, the same structure, the same job, because mutations that broke the shape were weeded out by evolution.
- **Analogy:** One circuit (say, a 4-bit adder) taped out by many fabs over decades: every layout differs, the schematic is the same.
- **Where it appears:** The `family` column of Rfam; the split unit (D-008); `splits/rfam_split.tsv`.
- **First explained:** session 03.

### Covariation (compensatory mutation)
- **Definition:** Both partners of a base pair mutate together so the pair survives (G–C → A–U). The sequence changes at two positions while the structure is untouched.
- **Analogy:** Changing a plug and its socket together to a different matching pair: the connection still works, but both parts look different.
- **Where it appears:** Why family members can be only ~50–60 % identical yet share a structure, and so why identity filters alone don't stop leakage (D-008).
- **First explained:** session 03.

### Clan (Rfam)
- **Definition:** A group of Rfam families that are themselves related, e.g. versions of one RNA from different kingdoms of life that Rfam curates as separate families.
- **Analogy:** Product lines descended from the same original design.
- **Where it appears:** The `clan` column; our split unit when present (D-008). 145 clans cover 459 of 4,023 families.
- **First explained:** session 03.

### Rfam
- **Definition:** A curated database of about 4,000 RNA families. Experts align a small **seed** set of members per family; a **covariance model** built from the seed then scans genomes, and every hit above a threshold becomes a **full** member.
- **Analogy:** A field guide with a hand-checked reference photo per species, plus an automatic camera-trap classifier that labels millions of new photos.
- **Where it appears:** Our training corpus (D-005); `data/raw/rfam/`.
- **First explained:** session 03.

### Seed alignment, covariance model, full region
- **Definition:** The **seed** is a hand-curated alignment of a few family members with their shared structure. A **covariance model** is a statistical model of the family's letters *and* its base pairs, built from the seed. **Full regions** are the genome hits the model finds.
- **Analogy:** Seed = the golden test vectors; covariance model = a pattern matcher trained on them; full regions = everything the matcher flags in the field (mostly right, occasionally wrong or partial).
- **Where it appears:** The HF Rfam copy contains full regions, which is why some members are fragments (D-007).
- **First explained:** session 03.

### Fragment (truncated hit)
- **Definition:** A partial copy of an RNA, e.g. because the sequenced contig ended mid-molecule. It isn't a whole, working molecule.
- **Analogy:** Half a netlist: it looks like the circuit but can't function.
- **Where it appears:** `prepare_data.py` steps 4–5: families with median > 256 are dropped whole; members under half their family's median are dropped (D-007).
- **First explained:** session 03.

### bpRNA-1m (and TS0, bpRNA-new)
- **Definition:** 102,318 RNAs **with** secondary structures, gathered from 7 databases (CRW, Rfam, tmRNA, SRP, SPR, RNase P, PDB), with **no** family labels. TS0 is a test split filtered at 80 % identity; bpRNA-new is 5,401 sequences from families added to Rfam later, so it's family-disjoint.
- **Analogy:** An answer key with solutions (structures) but no chapter headings (families).
- **Where it appears:** Downloaded and characterised (`explore_data.py`, audit check 4); its role is decided in Phase 3. Models scoring well on TS0 but dropping on bpRNA-new is the literature's own evidence of family leakage.
- **First explained:** session 03.

### Named RNA types that appear in our data
- **Definition:** **tRNA** (transfer RNA): the cloverleaf-shaped adaptor that brings amino acids to the protein-building machine. **rRNA** (ribosomal RNA): the long RNAs that form the protein-building machine itself (the **ribosome**); 5S rRNA is its small ~120-nt piece. **snoRNA** (small nucleolar RNA): guides that mark positions on other RNAs for chemical modification; SNORA/SNORD are its two main classes. **microRNA (miRNA)**: short RNAs that switch genes down; Rfam stores their ~60–100-nt hairpin precursors. **SRP RNA**: part of the machine that delivers new proteins to membranes. **U6**: part of the machine that cuts and rejoins gene messages (the spliceosome).
- **Analogy:** Different standard cells in a library: each has its own fixed shape and job.
- **Where it appears:** The largest families (tRNA 5.3 M members), the dropped long families (rRNAs), and the residual-similarity cases (SNORA52, snoR16, mir-1285).
- **First explained:** session 03.

### IUPAC ambiguity codes (N, R, Y, …)
- **Definition:** Letters meaning "not sure which base": N = any, R = A or G, Y = C or U, and so on. They come from sequencing uncertainty.
- **Analogy:** An 'X' (don't-care or unknown) value in a logic simulation.
- **Where it appears:** 0.45 % of Rfam sequences contain them (mostly N); those sequences are dropped, so the vocabulary needs no `<unk>` (D-006, D-007).
- **First explained:** session 03.

---

## Machine learning

### Generative model
- **Definition:** A model that learns the distribution of its training data (which sequences are likely and which aren't), so you can draw new, different samples from it.
- **Analogy:** An experienced designer who has seen thousands of circuits and can propose plausible new ones on demand, versus a random-netlist generator.
- **Where it appears:** The whole project: RiboMamba is a generative model of RNA sequences.
- **First explained:** session 01 (intuition only; formal treatment in Phase 2).

### Oracle
- **Definition:** A trusted external checker used to score the model's outputs. For us it is folding software, which predicts each generated sequence's structure.
- **Analogy:** The golden reference model in verification: the testbench compares the design under test against it.
- **Where it appears:** The evaluation harness (Phase 3).
- **First explained:** session 01.

### Train / validation / test split
- **Definition:** Dividing the data into three disjoint parts: **train** (the model learns from it), **validation** (checked during development to choose settings and when to stop), **test** (touched once at the end to report the final number).
- **Analogy:** Homework, mock exams, and the final exam. Studying the final's questions in advance makes the grade meaningless.
- **Where it appears:** `data/processed/{train,val,test}.parquet`; 452,867 / 57,054 / 56,883 sequences (D-008).
- **First explained:** session 03.

### Data leakage
- **Definition:** Information about the test data reaching the model during training, so test scores come out better than the model's real ability.
- **Analogy:** Exam questions that are reworded homework problems: 95 % without being able to solve anything new.
- **Where it appears:** The leakage audit (`audit_leakage.py`, RESULTS.md): a random split gives 89.6 % of test sequences a ≥ 80 %-identical training relative.
- **First explained:** session 03.

### Family-aware (clan-aware) split
- **Definition:** A split in which every family (or whole clan) goes entirely into one of train / val / test, so held-out RNAs have no relatives in training.
- **Analogy:** Holding out whole chapters of a textbook for the exam, instead of random questions from every chapter.
- **Where it appears:** `prepare_data.py` step 9 (D-008).
- **First explained:** session 03.

### Token, tokenisation, vocabulary, token id
- **Definition:** **Tokenisation** chops a string into units (**tokens**); the **vocabulary** is the list of all possible tokens; each token's position in that list is its **id**, the integer the model actually sees.
- **Analogy:** An instruction set's opcode table: each mnemonic maps to a fixed binary code.
- **Where it appears:** `ribomamba/data/tokenizer.py`: `<pad>=0 <mask>=1 <bos>=2 <eos>=3 A=4 C=5 G=6 U=7` (D-006).
- **First explained:** session 03.

### Special tokens (`<pad>`, `<mask>`, `<bos>`, `<eos>`)
- **Definition:** Vocabulary entries that aren't nucleotides. `<pad>` fills unused positions; `<mask>` marks a hidden letter (the "absorbing state" of masked diffusion, Phase 2); `<bos>`/`<eos>` mark the beginning and end of a sequence, so a left-to-right model knows where to start and can decide when to stop.
- **Analogy:** Control characters in a serial protocol (start bit, stop bit, idle fill), as opposed to data bits.
- **Where it appears:** `tokenizer.py`; `RNADataset(add_bos=…, add_eos=…)`.
- **First explained:** session 03.

### k-mer, BPE (rejected tokenisations)
- **Definition:** A **k-mer** is a run of k letters used as one token (3-mers → 64 tokens). **BPE** (byte-pair encoding) learns frequent letter groups as tokens; it's how LLMs tokenise text.
- **Analogy:** Reading a bus 3 bits at a time, versus a compression dictionary of common patterns.
- **Where it appears:** Rejected in D-006: pairing and masking act on single nucleotides.
- **First explained:** session 03.

### Embedding (preview)
- **Definition:** A learned table with one vector (list of numbers) per token id; the model's first step replaces each id by its vector.
- **Analogy:** A lookup ROM whose contents are learned during training.
- **Where it appears:** Phase 2. Its size is vocabulary × width, which is why all three models must share one vocabulary (D-006).
- **First explained:** session 03 (preview).

### Tensor, batch
- **Definition:** A **tensor** is a multi-dimensional block of numbers (a 2-D tensor is a matrix). A **batch** is B examples processed together as one tensor, shape `(B, L)` for B sequences of length L.
- **Analogy:** A SIMD vector unit or a wide bus: every lane is processed at once, and every lane has the same width.
- **Where it appears:** `collate()` returns `input_ids` of shape `(B, L_max)`.
- **First explained:** session 03.

### Padding, attention (padding) mask
- **Definition:** **Padding** appends `<pad>` so all sequences in a batch reach the same length. The **attention mask** is a `(B, L)` true/false tensor saying which positions are real, so the model ignores filler and the loss isn't computed on it.
- **Analogy:** Stuffing bytes plus a byte-enable signal: the enable says which bytes on the bus are valid.
- **Where it appears:** `collate()` in `ribomamba/data/dataset.py`.
- **First explained:** session 03.

### "Mask": three different meanings
- **Definition:** (1) the **padding/attention mask**, which positions are real; (2) the **`<mask>` token**, diffusion's "hidden letter" symbol (id 1); (3) **masking** as an operation, e.g. `masked_fill`, overwriting chosen entries.
- **Analogy:** "Clock" meaning the oscillator, the net, or the timing constraint, depending on who's talking.
- **Where it appears:** (1) Phase 1 `collate()`; (2) and (3) Phase 2.
- **First explained:** session 03.

### Dynamic padding, length bucketing
- **Definition:** **Dynamic padding** pads only to the longest sequence *in this batch*. **Length bucketing** puts similar-length sequences into the same batch, so there's almost nothing to pad.
- **Analogy:** Sorting parcels by size before packing trucks, instead of loading them randomly and shipping mostly air.
- **Where it appears:** `BucketBatchSampler`. Measured on train with batch 64: padding 54.4 % of positions (random) → 1.1 % (bucketed).
- **First explained:** session 03.

### Epoch
- **Definition:** One full pass of training over every example in the training set.
- **Analogy:** One complete regression run through the whole test suite.
- **Where it appears:** `BucketBatchSampler.set_epoch()` reshuffles differently (but reproducibly) each epoch. One epoch = 7,077 batches of 64.
- **First explained:** session 03.

### Activations, gradients, optimiser state, backpropagation
- **Definition:** **Activations** are the intermediate results of the forward pass, which training must keep. **Backpropagation** walks back through them to compute **gradients** (how much each weight should change). The **optimiser state** is Adam's two running averages per weight.
- **Analogy:** Activations are the waveform dump you keep so you can trace a failure backward; gradients are the blame assigned to each gate.
- **Where it appears:** The VRAM estimate: weights + gradients + Adam ≈ 16 bytes/parameter (small), while activations grow with batch × length and dominate.
- **First explained:** session 03 (memory view only; the mechanics come in Phase 2).

### VRAM
- **Definition:** The GPU's own memory. Everything a training step touches must fit in it: 8 GB on the RTX 4060 (8.59 × 10⁹ bytes).
- **Analogy:** On-chip SRAM: fast, but a hard size limit.
- **Where it appears:** The length cap (D-007).
- **First explained:** session 03.

### Autoregressive generation (preview)
- **Definition:** Producing a sequence one token at a time, left to right, each choice conditioned on everything written so far (how GPT works).
- **Analogy:** A shift register being filled one bit per clock, each bit decided from the ones already in.
- **Where it appears:** The Phase 4 baseline; the reason `<bos>`/`<eos>` exist.
- **First explained:** session 03 (preview).

---

## Maths

### Search space
- **Definition:** The set of all candidate solutions. For RNA of length N it contains 4^N sequences (N = 50 → about 1.3 × 10³⁰).
- **Analogy:** Every possible truth table for a circuit with many inputs: exhaustive testing is impossible.
- **Where it appears:** Why we generate rather than search (STUDY_GUIDE Part 2).
- **First explained:** session 01.

### Big-O notation (e.g. O(N³))
- **Definition:** A way of saying how a computation's cost grows with input size N, ignoring constant factors. O(N³) means doubling N makes it about 8× slower.
- **Analogy:** How a circuit's area scales with bit-width (a ripple-carry adder is O(N); an array multiplier is O(N²)).
- **Where it appears:** Folding cost (O(N³)); later, Transformer attention O(N²) vs Mamba O(N) in Phase 4.
- **First explained:** session 01.

### Dynamic programming
- **Definition:** Solving a big problem by splitting it into smaller overlapping sub-problems, solving each once, storing the answer, and reusing it.
- **Analogy:** Static timing analysis computes the worst arrival time at each node once and reuses it, instead of enumerating exponentially many paths.
- **Where it appears:** Inside the folding software (Zuker algorithm).
- **First explained:** session 01.

### Local search and local minima
- **Definition:** Local search improves a solution by small changes (e.g. mutate one letter, keep it if better). A local minimum is a point where every small change makes things worse, even though a better solution exists elsewhere.
- **Analogy:** A ball stuck in a small dip on a hillside, unable to reach the deep valley beyond the next ridge.
- **Where it appears:** Why classical design tools (e.g. RNAinverse) struggle; the contrast that motivates generative models.
- **First explained:** session 01.

### Simulated annealing
- **Definition:** A local-search variant that sometimes accepts a *worse* step on purpose, more often early on and less often later, so it can climb out of local minima.
- **Analogy:** Annealing metal (or annealing in wafer processing): heat it so atoms can escape bad arrangements, then cool slowly so they settle into a good one.
- **Where it appears:** Mentioned only as a patch that classical design tools use.
- **First explained:** session 01.

### Percentile (p50, p90, p99), median
- **Definition:** The p-th percentile is the value below which p % of the data falls. The **median** is p50, the middle value.
- **Analogy:** "90 % of paths meet timing below this delay."
- **Where it appears:** Rfam lengths: p50 = 73, p90 = 148, p99 = 1,520 (`explore_data.py`).
- **First explained:** session 03.

### Sequence identity, query coverage
- **Definition:** **Identity** is the fraction of aligned positions where two sequences have the same letter. **Coverage** is the fraction of the query's length that the alignment spans. Both matter: 100 % identity over 15 letters of a 150-letter RNA isn't "the same sequence".
- **Analogy:** Bit-error rate over the matched part of a packet, and how much of the packet was matched at all.
- **Where it appears:** Step 10 and the audit: a hit counts if identity ≥ 80 % over ≥ 80 % coverage.
- **First explained:** session 03.

### E-value
- **Definition:** The number of hits this good you'd expect to find by pure chance in a database this size. Smaller = more surely real. MMseqs2 reports hits with E ≤ 10⁻³.
- **Analogy:** A false-alarm rate: how often random noise alone would trip the detector.
- **Where it appears:** "Any detectable relative" in the audit = any hit with E ≤ 10⁻³.
- **First explained:** session 03.

### 95 % confidence interval (for a proportion)
- **Definition:** A range that, over repeated sampling, contains the true value 95 % of the time. For a proportion p from n samples it's roughly p ± 1.96·√(p(1−p)/n).
- **Analogy:** Error bars on a measured yield from a sample of dies rather than the whole wafer.
- **Where it appears:** The audit samples 2,000 sequences, so e.g. 89.6 % ± 1.3 %.
- **First explained:** session 03.

---

## Software

### Operating system (OS)
- **Definition:** The base software that sits between programs and the hardware. It decides which program gets the CPU when, hands out memory, manages files on disk, and talks to devices such as the GPU. Windows and Linux are two different operating systems.
- **Analogy:** A bus arbiter plus memory controller on a chip. Many masters (programs) want shared resources (CPU, RAM, disk), and one controller keeps them from trampling each other.
- **Where it appears:** We develop on Linux (inside WSL2) running on a Windows machine.
- **First explained:** session 02.

### Kernel
- **Definition:** The core of an operating system: the part that directly controls the hardware. Everything else (the terminal, the tools) is ordinary programs asking the kernel for services.
- **Analogy:** The firmware/microcode layer of a processor. Programs never touch the silicon directly; they go through it.
- **Where it appears:** WSL2 runs a real Linux kernel (WSL1 did not).
- **First explained:** session 02.

### Linux, and Linux distribution ("distro")
- **Definition:** Linux is a free operating system (strictly, a kernel) that almost all scientific computing, servers and cloud GPUs run on. A distribution packages the Linux kernel with a standard set of tools and a package manager. Ubuntu is one popular distribution.
- **Analogy:** The kernel is the processor core; a distribution is a complete dev board built around it, with peripherals and a toolchain already fitted.
- **Where it appears:** Our environment is Ubuntu, running in WSL2.
- **First explained:** session 02.

### Virtual machine (VM) and hypervisor
- **Definition:** A virtual machine is a complete computer simulated in software, with its own OS, running on real hardware alongside the main OS. The hypervisor is the layer that shares out the real CPU, memory and devices so each OS believes it owns the machine.
- **Analogy:** Partitioning one chip so two independent systems share the silicon, with an arbiter giving each the illusion of exclusive access.
- **Where it appears:** WSL2 is a lightweight VM managed by Windows.
- **First explained:** session 02.

### WSL2 (Windows Subsystem for Linux, version 2)
- **Definition:** A Microsoft feature that runs a real Linux kernel inside a lightweight, tightly integrated virtual machine, so Linux tools run on a Windows PC without rebooting. It can also use the NVIDIA GPU through the Windows driver ("GPU passthrough").
- **Analogy:** A second, fully independent processor on the same board running different firmware, with a bridge that lets both see each other's files and share the GPU.
- **Where it appears:** Our whole development environment. Checked with `wsl --status` and `wsl --list --verbose` in session 02 (already installed: Ubuntu, version 2).
- **First explained:** session 02.

### WSL1 vs WSL2
- **Definition:** WSL1 had no Linux kernel. It translated each Linux request into an equivalent Windows request on the fly. WSL2 runs a genuine Linux kernel, so it is fully compatible and much faster on Linux-side files, but slower when reaching into Windows files.
- **Analogy:** WSL1 is a protocol translator (converts every packet); WSL2 is a native second device with a bridge between them.
- **Where it appears:** Our machine uses WSL2 (the `VERSION 2` column).
- **First explained:** session 02.

### Terminal, shell, PowerShell, bash
- **Definition:** A terminal is the text window. A shell is the program inside it that reads a typed command, runs it and prints the result. PowerShell is the Windows shell; bash is the standard Linux shell. They use different command syntax.
- **Analogy:** A shell is a command interpreter like a JTAG console or UART monitor: you type an instruction, it executes it on the device and replies.
- **Where it appears:** Every command in the logbook says which shell it ran in.
- **First explained:** session 02.

### Character encoding (UTF-8, UTF-16)
- **Definition:** The rule for turning text characters into bytes. UTF-16 uses 2 bytes per plain English letter (the second one is 0x00); UTF-8 uses 1. Decoding with the wrong rule gives garbled text.
- **Analogy:** Reading a 16-bit bus as if it were 8 bits wide: every other byte you see is a meaningless zero.
- **Where it appears:** Why `wsl --status` printed `D e f a u l t` with gaps in session 02.
- **First explained:** session 02.

### Virtual disk (`.vhdx`) and file system (ext4)
- **Definition:** A virtual disk is one ordinary Windows file that contains an entire disk drive inside it. WSL2 keeps each Linux distro's whole disk in a file called `ext4.vhdx`. ext4 is the file-system format Linux uses inside it, meaning the rules for how files and folders are laid out on a disk.
- **Analogy:** An SD-card image for a Raspberry Pi, or a ROM image loaded into an emulator: one file that *is* a whole drive.
- **Where it appears:** Session 02: Ubuntu wouldn't start because its `ext4.vhdx` had been deleted.
- **First explained:** session 02.

### Windows registry
- **Definition:** Windows' central database of settings. WSL stores its list of installed distros there, including where each one's disk file lives.
- **Analogy:** A configuration register map, or a phone book. It says where something *should* be, not whether it's still there.
- **Where it appears:** Session 02 diagnosis: the registry still listed Ubuntu after its disk was deleted.
- **First explained:** session 02.

### Dangling reference (dangling pointer)
- **Definition:** A reference that still exists after the thing it points to has been deleted. Using it fails.
- **Analogy:** A netlist that instantiates a cell whose layout file has been deleted, or a C pointer to freed memory.
- **Where it appears:** Session 02: the broken Ubuntu registration.
- **First explained:** session 02.

### LTS (Long-Term Support)
- **Definition:** A software release that gets security and bug fixes for several years (Ubuntu LTS: 5 years standard). Preferred when you want a stable, reproducible base rather than the newest features.
- **Analogy:** A mature, fully characterised process node versus a brand-new one: fewer surprises, better tool support.
- **Where it appears:** We plan to install Ubuntu 24.04 LTS.
- **First explained:** session 02.

### root, user accounts, and sudo
- **Definition:** Linux has one all-powerful administrator account, `root`, and ordinary user accounts that can only change their own files. `sudo` ("superuser do") lets an ordinary user run a single command as root, after typing their password.
- **Analogy:** Normal operation versus test mode with write access to fuses. You want the dangerous mode only for the one command that needs it.
- **Where it appears:** Our Linux user is `chirag` (member of the `sudo` group). Setup commands in session 02 ran as `root` via `wsl -u root`.
- **First explained:** session 02.

### `/mnt/c` (mount point)
- **Definition:** The folder through which Linux inside WSL sees the Windows C: drive. `C:\Users\chira\...` appears as `/mnt/c/Users/chira/...`. Every access through it crosses the Windows↔Linux bridge.
- **Analogy:** A window in the address map that points off-chip, through a bus bridge.
- **Where it appears:** Session 02: a WSL shell started in `/mnt/c/Users/chira/OneDrive/Desktop/RiboMamba`, the reason for decision D-002.
- **First explained:** session 02.

### GPU driver, `nvidia-smi`, "CUDA Version"
- **Definition:** The driver is the software that lets the OS talk to the GPU. `nvidia-smi` is NVIDIA's status tool: it shows the GPU model, memory and running jobs. Its "CUDA Version" is the *newest* CUDA the driver supports, not an installed toolkit. CUDA itself (NVIDIA's GPU programming platform) is explained properly when PyTorch is installed.
- **Analogy:** The driver is the device's firmware interface; `nvidia-smi` is its status register dump.
- **Where it appears:** Session 02: RTX 4060 Laptop, 8188 MiB (8 GB) VRAM, driver 595.79, CUDA ≤ 13.2, visible from inside WSL.
- **First explained:** session 02.

### Git, repository, commit
- **Definition:** Git is a version-control system: it records snapshots of your project over time. The repository is the project folder plus Git's hidden database (`.git/`). A commit is one saved snapshot, with an author, a time and a message explaining why it was made.
- **Analogy:** Tape-out revisions with a change log. Every revision is kept, and you can always return to any earlier one.
- **Where it appears:** `~/projects/RiboMamba` is a Git repository. First commit `f495772`, session 02.
- **First explained:** session 02.

### Staging area (`git add`)
- **Definition:** The waiting room between editing files and committing them. `git add` puts chosen changes in it; `git commit` turns exactly those into a snapshot.
- **Analogy:** Choosing which modified cells go into this revision before signing it off.
- **Where it appears:** Every commit.
- **First explained:** session 02.

### Commit hash
- **Definition:** A 40-hex-digit fingerprint that identifies a commit, calculated from its contents and its parent commit. Change anything in history and every later hash changes, so tampering is visible. Usually shortened to the first 7 digits (e.g. `f495772`).
- **Analogy:** A CRC/checksum over the whole history chain.
- **Where it appears:** RESULTS.md records the commit hash next to every number, for reproducibility.
- **First explained:** session 02.

### Branch (`main`)
- **Definition:** A named line of commits. A new repository starts with one; we call it `main`.
- **Analogy:** A named design revision track.
- **Where it appears:** Our only branch so far.
- **First explained:** session 02 (briefly; more when we need a second branch).

### Remote, push, GitHub
- **Definition:** A remote is another copy of the repository, somewhere else. GitHub is a website that hosts remotes. `git push` sends your new commits to the remote.
- **Analogy:** An off-site backup of the design database, updated whenever you choose.
- **Where it appears:** `Chikap1009/RiboMamba` on GitHub (public). Pushed at the end of every session (D-002).
- **First explained:** session 02.

### `gh` (GitHub CLI)
- **Definition:** GitHub's command-line tool. It logs you in to GitHub and can create repositories, among other things, without opening the website.
- **Analogy:** A command-line interface to a web service, instead of clicking through its GUI.
- **Where it appears:** Installed in Ubuntu (version 2.45.0), session 02.
- **First explained:** session 02.

### Noreply email
- **Definition:** A private address GitHub gives each user (`ID+username@users.noreply.github.com`). Commits made with it are linked to your profile without exposing your real email in a public repository.
- **Analogy:** A PO box instead of your home address.
- **Where it appears:** Our Git author email.
- **First explained:** session 02.

### apt (package manager)
- **Definition:** Ubuntu's tool for installing system software from Ubuntu's official collection. `apt-get update` refreshes the catalogue; `apt-get install X` installs X. It needs root.
- **Analogy:** An app store for the command line.
- **Where it appears:** Installed `gh` in session 02. (Python packages will come from conda instead, explained at step 4.)
- **First explained:** session 02.

### Shell script
- **Definition:** A text file containing shell commands, run in order with `bash file.sh`. We use them to avoid typing long Linux commands through PowerShell, which rewrites quotes and `$` signs.
- **Analogy:** A test vector file you replay, instead of typing every stimulus by hand.
- **Where it appears:** One-off setup scripts in session 02 (kept outside the repo).
- **First explained:** session 02.

### Time zone vs. clock
- **Definition:** A computer's clock counts one universal time (UTC). The time zone only controls how that time is *displayed* (IST = UTC + 5:30).
- **Analogy:** The same voltage shown on two meters with different offsets.
- **Where it appears:** Ubuntu was showing UTC; set to Asia/Kolkata in session 02. Git records the offset with every commit.
- **First explained:** session 02.

### Package and package manager
- **Definition:** A package is a ready-built piece of software plus a note of what it depends on. A package manager downloads packages, works out which versions of everything fit together (this is called "solving"), and installs them.
- **Analogy:** A parts distributor with a compatibility checker: order one IC, and it also ships the matching regulator and passives in versions that work together.
- **Where it appears:** apt (system software), conda (our project software), pip (pure-Python packages).
- **First explained:** session 02.

### conda, Miniforge, and `mamba` (the installer)
- **Definition:** conda is a package manager that can install *any* software (Python, C libraries, CUDA runtimes), not only Python, into isolated environments. Miniforge is a small installer that gives you conda, set up to use the free conda-forge channel. It also includes `mamba`, a faster conda-compatible installer. **That mamba has nothing to do with the Mamba neural network.**
- **Analogy:** A toolchain manager that can install several compiler versions side by side, each in its own sandbox.
- **Where it appears:** Installed at `~/miniforge3` (conda 26.7.2), session 02. D-003.
- **First explained:** session 02.

### Environment (conda environment)
- **Definition:** A self-contained folder holding one specific Python version and one specific set of packages, separate from every other environment. "Activating" it (`conda activate ribomamba`) makes the terminal use its tools.
- **Analogy:** A separate EDA install per project: project A can stay on tool version 2021 while project B uses 2024, without breaking each other.
- **Where it appears:** `ribomamba`, defined in `environment.yml`.
- **First explained:** session 02.

### Channel (conda-forge, bioconda)
- **Definition:** A channel is an online collection of conda packages. conda-forge is the large free community channel; bioconda is a channel for bioinformatics software, built on top of conda-forge. Channel order sets priority when both offer a package.
- **Analogy:** Different component distributors. You list your preferred one first.
- **Where it appears:** `environment.yml` lists conda-forge, then bioconda.
- **First explained:** session 02.

### Bioconda
- **Definition:** A community collection of ready-to-install bioinformatics software packages (ViennaRNA is one), distributed through conda. It builds packages for Linux and macOS only, not Windows.
- **Analogy:** A vendor's IP catalogue that only ships for certain process nodes.
- **Where it appears:** Source of our ViennaRNA package (`environment.yml`).
- **First explained:** session 02.

### `environment.yml` (and YAML)
- **Definition:** A text file listing an environment's name, channels and packages, from which conda can rebuild it anywhere. YAML is the simple "key: value" and "- list item" text format it's written in.
- **Analogy:** A bill of materials: anyone can rebuild the same board from it.
- **Where it appears:** Repo root. Rebuild with `conda env create -f environment.yml`.
- **First explained:** session 02.

### Version pinning
- **Definition:** Writing an exact version (e.g. `viennarna=2.7.2`) instead of "whatever is newest", so every rebuild installs the same software.
- **Analogy:** Specifying an exact part number on a BOM, not "any 10k resistor".
- **Where it appears:** `environment.yml`. It matters most for the folding oracle, because a different ViennaRNA version could give different energies.
- **First explained:** session 02.

### Checksum (SHA-256)
- **Definition:** A fixed-length fingerprint computed from a file's bytes. If even one byte changes, the fingerprint changes completely. Comparing it with the publisher's value proves the download is intact and unaltered.
- **Analogy:** A CRC check on a received packet, but cryptographically strong.
- **Where it appears:** Verifying the Miniforge installer, session 02.
- **First explained:** session 02.

### Python bindings
- **Definition:** A bridge that lets Python code call a library written in another language (here, ViennaRNA's C code). `import RNA` gives Python access to the same folding engine as the `RNAfold` command.
- **Analogy:** A driver API that lets high-level software call into firmware.
- **Where it appears:** Our evaluation code (Phase 3) will call ViennaRNA via `import RNA`.
- **First explained:** session 02.

### Stack (data structure)
- **Definition:** A list where you can only add to the top (push) or remove from the top (pop): last in, first out.
- **Analogy:** A stack of plates, or a hardware return-address stack.
- **Where it appears:** Decoding dot-bracket into base pairs.
- **First explained:** session 01.

### PyTorch, CUDA
- **Definition:** **PyTorch** is the Python library we build and train neural networks with; it runs tensor maths on the GPU. **CUDA** is NVIDIA's platform for running general computations on its GPUs; PyTorch ships its own CUDA libraries.
- **Analogy:** PyTorch is the HDL plus simulator; CUDA is the vendor toolchain that maps it onto the actual silicon.
- **Where it appears:** `torch==2.10.0+cu128` in `environment.yml` (D-004).
- **First explained:** session 03.

### Wheel, prebuilt wheel, ABI
- **Definition:** A **wheel** is a ready-to-install Python package file. A **prebuilt** wheel contains already-compiled code, so installing it needs no compiler. The **ABI** (application binary interface) is the exact binary-level contract between compiled pieces; a compiled extension only works with the library build it was compiled against.
- **Analogy:** A hard IP block characterised for one specific process node: drop it into a different node and it won't work, even if the RTL is the same.
- **Where it appears:** Why we pin torch 2.10: `mamba-ssm` wheels exist only up to it (D-004).
- **First explained:** session 03.

### Package index (`--extra-index-url`)
- **Definition:** A server pip downloads packages from. PyPI is the default; PyTorch runs its own index with CUDA-specific builds, added with `--extra-index-url`.
- **Analogy:** A second distributor you order a specific part variant from.
- **Where it appears:** The `pip:` section of `environment.yml`.
- **First explained:** session 03.

### HuggingFace Hub, dataset revision
- **Definition:** A public site hosting models and datasets as Git repositories. A **revision** is one commit of such a repository; downloading "at a revision" fetches exactly that version.
- **Analogy:** GitHub for datasets; the revision is the tape-out tag.
- **Where it appears:** `scripts/download_data.py` pins `multimolecule/rfam@25e8aa8…` and `multimolecule/bprna@423465b…` (D-005).
- **First explained:** session 03.

### Parquet
- **Definition:** A compressed file format for tables that stores each column separately, so a program can read only the columns it needs.
- **Analogy:** A memory organised by field rather than by record, so fetching one field doesn't drag in the others.
- **Where it appears:** Every data file in `data/raw/` and `data/processed/`.
- **First explained:** session 03.

### polars, DataFrame, lazy evaluation, streaming
- **Definition:** A **DataFrame** is a table in memory (named columns, many rows). **polars** is a fast DataFrame library. **Lazy** mode (`scan_parquet`) builds a query plan first and runs it only on `.collect()`, so it can skip unneeded columns and rows. **Streaming** processes the file in chunks to cap memory.
- **Analogy:** Synthesis before execution: describe the whole computation, let the tool optimise it, then run it.
- **Where it appears:** `explore_data.py`, `prepare_data.py` (4.6 s, 4.4 GB peak for 10 M rows).
- **First explained:** session 03.

### FASTA
- **Definition:** The standard text format for sequences: a line `>name`, then the letters.
- **Analogy:** The netlist exchange format everyone's tools read.
- **Where it appears:** Written temporarily by `ribomamba/data/similarity.py` for MMseqs2 (with U written as T).
- **First explained:** session 03.

### MMseqs2
- **Definition:** A fast sequence-search tool (a modern relative of BLAST): for each query it finds similar target sequences and reports identity, coverage and E-value.
- **Analogy:** A fast approximate pattern-matcher over a huge database, like a content-addressable memory with fuzzy matching.
- **Where it appears:** Step 10 of the split and the leakage audit (`ribomamba/data/similarity.py`); version 18.8cc5c.
- **First explained:** session 03.

### Seed, random number generator (RNG), stable hash
- **Definition:** An **RNG** produces numbers that look random but are computed; the **seed** is its starting value, so the same seed gives the same "random" choices. A **stable hash** (SHA-256) gives the same output everywhere. Python's built-in `hash()` of a string is deliberately randomised per process, so it's unusable for reproducible splits.
- **Analogy:** An LFSR: fully deterministic from its initial state, random-looking in output.
- **Where it appears:** `SEED = 0` in the scripts; `stable_hash()` orders the split units.
- **First explained:** session 03.

### Lookup table (LUT)
- **Definition:** A precomputed array where the answer for input x is stored at position x, so converting is one indexing step.
- **Analogy:** A ROM, or an FPGA LUT.
- **Where it appears:** `_BYTE_TO_ID` in `tokenizer.py`: ASCII byte → token id for a whole sequence at once.
- **First explained:** session 03.

### dtype (int8, int64, bool)
- **Definition:** The number type of a tensor's elements: int8 = 1-byte integers (−128…127), int64 = 8-byte integers, bool = true/false.
- **Analogy:** Bus width.
- **Where it appears:** Token ids stored as int8 (1 byte per nucleotide), converted to int64 ("long") when handed to PyTorch, since embedding lookups expect that; the attention mask is bool.
- **First explained:** session 03.

### Flat array + offsets
- **Definition:** Storing many variable-length items end-to-end in one array, plus an `offsets` array where item i occupies `flat[offsets[i]:offsets[i+1]]`.
- **Analogy:** A memory plus a table of base addresses.
- **Where it appears:** `RNADataset`: 452,867 training sequences in one 47.7 MB array.
- **First explained:** session 03.

### Broadcasting
- **Definition:** A rule by which tensor operations on different shapes stretch size-1 dimensions to match. `(1, L) < (B, 1)` compares every position with every row's length, giving `(B, L)`.
- **Analogy:** Fanning one signal out to every lane of a bus instead of copying it by hand.
- **Where it appears:** Building the attention mask in `collate()`.
- **First explained:** session 03.

### `Dataset`, `DataLoader`, collate function, sampler
- **Definition:** PyTorch's data pipeline. A **Dataset** answers "give me item i". A **sampler** decides which indices form each batch. The **collate function** merges a list of items into one batch tensor. The **DataLoader** runs all of this, optionally in background **worker processes**, with **pinned memory** (page-locked RAM) for faster copies to the GPU.
- **Analogy:** A memory (Dataset), an address generator (sampler), a packer that builds bus words (collate), and a DMA engine that runs them (DataLoader).
- **Where it appears:** `ribomamba/data/dataset.py`, `make_dataloader()`.
- **First explained:** session 03.

### `pyproject.toml`, editable install
- **Definition:** `pyproject.toml` describes a Python project so it can be installed as a package. An **editable** install (`pip install -e .`) makes `import ribomamba` point at the live source folder, so edits take effect without reinstalling.
- **Analogy:** A symbolic link into your working directory rather than a copied snapshot.
- **Where it appears:** `pyproject.toml`; `-e .` in `environment.yml`.
- **First explained:** session 03.

### Unit test, pytest, assertion
- **Definition:** A **unit test** is a small program that checks one piece of code gives a known answer; **pytest** finds and runs them (`python -m pytest`). An **assertion** is a check inside code that stops the program if a condition is false.
- **Analogy:** A self-checking testbench with golden vectors; an assertion is an SVA assertion firing in simulation.
- **Where it appears:** `tests/` (15 tests); `check_no_leakage_by_construction()` in `prepare_data.py`.
- **First explained:** session 03.

### `.gitignore` (and anchored patterns)
- **Definition:** A list of path patterns Git should not track. A pattern with a leading `/` matches only at the repository root; without it, `data/` matches a `data` folder at any depth.
- **Analogy:** A mask on which nets get dumped to the waveform file; without anchoring, the wildcard catches more than intended.
- **Where it appears:** `/data/`, `/checkpoints/`. Unanchored `data/` briefly hid the code folder `ribomamba/data/` (session 03).
- **First explained:** session 03.
