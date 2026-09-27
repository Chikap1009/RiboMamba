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

### Probability of a structure, P(target)
- **Definition:** The share of time a sequence spends in one particular structure s: P(s) = e^(−ΔG(s)/RT) / Z, the structure's Boltzmann weight divided by the partition function. It counts only the *exact* structure: a variant differing by a single pair counts as "not the target".
- **Analogy:** A frame error rate: the probability that *every* bit of a frame arrives correct.
- **Where it appears:** Phase 3 harness. `GGGAAACCC` 0.507, `GGGAAACCA` (own MFE) 0.939. Real validation RNAs of 74–223 nt: 0.000–0.069 for their own MFE structure, because probability spreads over many near-identical variants.
- **First explained:** session 02 (as "frequency in the ensemble"); at real lengths, session 04.

### Base-pair probability (matrix)
- **Definition:** For every pair of positions (i, j), the probability that i is paired with j, summed over the whole Boltzmann ensemble. Out of the same partition-function calculation; P(i unpaired) = 1 − Σ_j P(i, j).
- **Analogy:** A per-bit reliability map instead of a single pass/fail for the whole word.
- **Where it appears:** The input to the ensemble defect; also what EternaFold outputs (Phase 3).
- **First explained:** session 04.

### Ensemble defect (NED, normalised ensemble defect)
- **Definition:** The expected number of nucleotides in the wrong state relative to a target (paired with the wrong partner, paired when they should be free, or free when they should be paired), averaged over the ensemble; divided by the length N it becomes NED, between 0 (perfect) and 1. NED = 1 − (1/N) Σ_i P(i is in its target state). Standard in nucleic-acid design (NUPACK; Dirks et al. 2004, Zadeh et al. 2011; verify before citing).
- **Analogy:** A bit error rate, where P(target) is the frame error rate. With a 2 % error per nucleotide, NED = 0.02 but P(all 100 correct) = 0.98¹⁰⁰ ≈ 0.13.
- **Where it appears:** Phase 3 harness, the graded structural measure. `GGGAAACCC` 0.316 (about 3 of 9 nucleotides wrong on average), `GGGAAACCA` 0.028; real validation RNAs 0.08–0.22 (session 04 sample).
- **First explained:** session 04.

### MFE z-score (against dinucleotide shuffles)
- **Definition:** z = (MFE of the sequence − mean MFE of k dinucleotide shuffles) / standard deviation of those k shuffle MFEs. Negative = more stable than its own rearrangements, measured in units of their spread. It separates stability that comes from the *arrangement* of letters (real structure) from stability that comes from *composition* (GC-richness). Clote et al. 2005; Rivas & Eddy 2000 on why composition must be controlled (verify before citing).
- **Analogy:** "How many sigma below the process mean" for a measured delay.
- **Where it appears:** Phase 3 harness. A random 80-mer with 70 % GC: MFE −26.0 but z = +1.46 (*less* stable than its shuffles); real mir-221 (84 nt): MFE −31.9, z = −4.3; real validation RNAs −1.1 to −13.3.
- **First explained:** session 04 (the one-shuffle version in session 03).

### Target structure; native recovery
- **Definition:** In design, the **target** is the dot-bracket structure the generated sequence must fold into. When a target comes from a real RNA, that RNA's own sequence (the **native**) is a known answer; checking how the native scores is a positive control for the target and the metric.
- **Analogy:** A reference design that is known to meet the spec, run through the same sign-off flow.
- **Where it appears:** Phase 3 target sets for the Phase 5 design evaluation.
- **First explained:** session 04.

### Non-canonical pair
- **Definition:** A base pair other than G–C, A–U and G–U (e.g. A–G, G–G). Real structures contain some, but ViennaRNA's energy model cannot form them, so a target containing one is unreachable for our oracle.
- **Analogy:** A connection your routing tool has no rule for: it can exist on silicon, but the tool will never produce it.
- **Where it appears:** bpRNA structures must be screened for them before becoming targets.
- **First explained:** session 04.

### EternaFold (and CONTRAfold)
- **Definition:** A secondary-structure predictor whose parameters were *learned from experimental data*: CONTRAfold's statistical model, retrained on tens of thousands of chemical-mapping measurements of RNAs designed by Eterna players (Wayment-Steele et al., Nature Methods 2022). Outputs base-pair probabilities and a predicted structure; its scores are not kcal/mol.
- **Analogy:** An independent sign-off tool from a different vendor, calibrated on silicon measurements rather than on the same device models.
- **Where it appears:** The second, independent oracle (Phase 3). bioconda `eternafold` 1.3.1.
- **First explained:** session 04.

### Eterna100
- **Definition:** A benchmark of 100 target structures ("puzzles") from the Eterna game, graded by difficulty, widely used to compare RNA design methods (Anderson-Lee et al., J. Mol. Biol. 2016; verify before citing). Synthetic shapes, some longer than our 256-nt cap.
- **Analogy:** A standard benchmark suite (like ISCAS circuits) that lets different tools be compared on identical problems.
- **Where it appears:** Candidate external target set for Phase 5 (decided in Phase 3).
- **First explained:** session 04.

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

### Autoregressive generation
- **Definition:** Producing a sequence one token at a time, left to right, each choice conditioned on everything written so far (how GPT works). Based on the chain rule, so it can represent any distribution in principle; awkward for RNA because a letter is chosen before its pairing partner exists.
- **Analogy:** A shift register being filled one bit per clock, each bit decided from the ones already in.
- **Where it appears:** The Phase 4 baseline; the reason `<bos>`/`<eos>` exist.
- **First explained:** session 03 (preview, then Phase 2 Part A).

### Masked language model (BERT)
- **Definition:** A model trained to predict hidden letters from the letters on both sides, at one fixed hiding rate (~15 %). Good at filling a few gaps; not a generator, because it never learned to start from nothing.
- **Analogy:** A crossword solver who needs most of the grid filled in first.
- **Where it appears:** The stepping stone to masked diffusion (Phase 2 Part A).
- **First explained:** session 03.

### Diffusion model; forward and reverse process
- **Definition:** A generative model built from two processes: a fixed **forward** process that gradually destroys data (for us: masking letters), and a learned **reverse** process that gradually rebuilds it. Generation runs the reverse process from fully destroyed.
- **Analogy:** Learning to restore a photo by practising on copies you damaged yourself at every level of damage.
- **Where it appears:** Phase 2, `ribomamba/diffusion` (to be built).
- **First explained:** session 03.

### Masked (absorbing-state) discrete diffusion
- **Definition:** Diffusion over letters where the noise is replacing letters with `<mask>`. `<mask>` is **absorbing**: once a position is masked it stays masked in the forward process, and once revealed in the reverse process it stays fixed.
- **Analogy:** A set-only sticky bit, or a blown fuse: you can enter the state, never leave it.
- **Where it appears:** The core of RiboMamba (Phase 2 onward).
- **First explained:** session 03.

### Noise schedule (α_t)
- **Definition:** α_t is the probability a position is still visible at time t, going from α₀ = 1 (clean) to α₁ = 0 (all masked). We use the linear schedule α_t = 1 − t, so at time t each position is masked with probability t.
- **Analogy:** A ramp generator setting how much damage is applied at each moment.
- **Where it appears:** Phase 2 forward process and sampler.
- **First explained:** session 03.

### Denoiser (backbone)
- **Definition:** The network inside the diffusion model: it takes a partly masked sequence and returns, for every position, probabilities over A, C, G, U. It sees both sides and gets no time input. Phase 2 uses a Transformer, Phase 4 a BiMamba, with everything else identical.
- **Analogy:** The plug-in module in a fixed test fixture: swap only the module, and any change in the measurement is the module's doing.
- **Where it appears:** Phases 2 and 4.
- **First explained:** session 03.

### Sampling steps (N)
- **Definition:** How many reverse steps generation takes. From time t to s, each masked position is revealed with probability (t − s)/t. More steps: each letter sees more already-written letters (better, slower). Fewer steps: letters chosen in the same step can't coordinate (two pairing partners might both become G).
- **Analogy:** Resolving a design in many small, informed decisions versus a few big simultaneous ones.
- **Where it appears:** Phase 2 sampler; a hyperparameter to evaluate in Phase 3.
- **First explained:** session 03.

### Bits per nucleotide
- **Definition:** The model's average "surprise" per letter on held-out data, measured in bits. 2.0 = knows nothing (uniform over 4 letters, log₂ 4 = 2); lower = more knowledge of RNA. For our diffusion models it's an upper bound (from the ELBO); for the autoregressive model it's exact.
- **Analogy:** Compression ratio: a model that understands the data can encode it in fewer bits.
- **Where it appears:** The Phase 2 validation metric (on families never seen in training).
- **First explained:** session 03.

### k-th order Markov model (counting baseline)
- **Definition:** A model that predicts each letter from the k letters before it, using counts from the training data (plus smoothing: add 0.5 to every count so nothing gets probability zero). Exact likelihood; a reference point for "how much is purely local".
- **Analogy:** A predictive text that only looks at the last few characters.
- **Where it appears:** `scripts/baselines_markov.py`; best on unseen families is k = 4 at 1.966 bits/nt.
- **First explained:** session 03.

### Overfitting
- **Definition:** Getting better on the training data while getting worse on new data, because the model memorises specifics instead of learning what transfers.
- **Analogy:** Memorising last year's exam answers: perfect on those papers, useless on a new one.
- **Where it appears:** Markov models with k ≥ 5 (train keeps improving, unseen-family validation worsens); watched in every training run via validation bits/nt.
- **First explained:** session 03.

### Regularisation, dropout, early stopping
- **Definition:** **Regularisation** is anything that makes memorising harder so the model learns what transfers. **Dropout** randomly switches off a fraction of the network's internal signals at each training step (off during evaluation). **Early stopping** keeps the checkpoint with the best validation score instead of the last one.
- **Analogy:** Studying with random pages of your notes missing (dropout); handing in the exam at your best moment rather than after you start second-guessing (early stopping).
- **Where it appears:** `TransformerConfig.dropout`, `scripts/dropout_sweep.py` (D-012; dropout did not help here); `best.pt` in every run.
- **First explained:** session 03.

### Structure beyond chance (MFE vs dinucleotide shuffle)
- **Definition:** Fold a sequence and a dinucleotide-shuffled copy of it (same letters, same neighbour statistics) and compare their minimum free energies. Real structural RNAs usually fold more stably than their shuffles; sequences whose stability comes only from composition don't.
- **Analogy:** Checking that a circuit's good timing comes from its design, not merely from using fast cells: re-randomise the netlist with the same cells and compare.
- **Where it appears:** `scripts/sanity_samples.py`: real validation RNA 79.4 % more stable than its shuffle, Phase 2 baseline samples 54.6 % (chance = 50 %).
- **First explained:** session 03.

### Hyperparameter sweep; boundary effect
- **Definition:** Training the same model with several values of a setting (e.g. learning rate) and picking the best by a fixed rule. If the winner is the smallest or largest value tried, the true optimum may lie outside the range, so the range is extended.
- **Analogy:** Sweeping a bias voltage to find the best operating point; if the best reading is at the end of your sweep, sweep further.
- **Where it appears:** `scripts/lr_sweep.py` (rule 2b, D-011 amendment).
- **First explained:** session 03.

### Pre-registration (frozen evaluation protocol)
- **Definition:** Writing down the metrics, thresholds and headline success criterion **before** running the test set, so the metric can't be chosen after seeing which model it favours.
- **Analogy:** Fixing the sign-off criteria before tape-out, not after looking at which chip passes.
- **Where it appears:** RESULTS.md "Frozen evaluation protocol" (Phase 3). Motivated by: an MFE-only metric and an ensemble-probability metric can crown different architectures.
- **First explained:** session 03 (Phase 1 gate, re-taught).

### Garden of forking paths
- **Definition:** The many small analysis choices (which metric, which temperature, which oracle, which target set, which threshold) that, if made after seeing results, let almost any model look like a winner, even with no deliberate cheating. 5 metrics × 5 temperatures × 2 oracles × 3 target sets = 150 possible headline numbers.
- **Analogy:** Choosing the sign-off corner after seeing which corner the chip passes.
- **Where it appears:** The reason for pre-registration (Phase 3).
- **First explained:** session 04.

### Primary vs secondary (exploratory) endpoint
- **Definition:** A **primary endpoint** is one of the few pre-declared measurements on which the headline claim rests, tested with a correction for multiple comparisons. Everything else is **secondary / exploratory**: reported, but not allowed to carry a claim on its own.
- **Analogy:** The few sign-off criteria that decide tape-out, versus the many diagnostic plots you also look at.
- **Where it appears:** The frozen evaluation protocol (Phase 3).
- **First explained:** session 04.

### Sampling temperature
- **Definition:** A number T that divides the model's logits before the softmax: p_i ∝ e^(logit_i / T), equivalently p_i ∝ p_i^(1/T). T < 1 sharpens the distribution toward the model's favourite letters; T > 1 flattens it. This is a Boltzmann distribution with energy = −logit, so it is the same maths as physical temperature in folding.
- **Analogy:** Cooling a molecule concentrates it on its MFE; cooling the sampler concentrates it on its most probable letters.
- **Where it appears:** `sample(..., temperature=…)` in `ribomamba/diffusion/masked.py`; the Phase 3 ablation. Example: (0.5, 0.3, 0.15, 0.05) becomes (0.685, 0.247, 0.062, 0.007) at T = 0.5 and (0.379, 0.294, 0.208, 0.120) at T = 2.
- **First explained:** session 04.

### Quality–diversity trade-off (Pareto frontier)
- **Definition:** Settings that make samples better-folded (lower temperature, more steps) usually make them less varied, and vice versa. A **Pareto frontier** is the curve of settings where you can't improve one without worsening the other. Honest reports give both numbers, or the whole curve, never quality alone.
- **Analogy:** A speed–power curve: comparing two chips at different supply voltages says nothing about the design unless you compare their curves.
- **Where it appears:** Phase 3 temperature × steps ablation.
- **First explained:** session 04.

### Novelty, diversity, mode collapse
- **Definition:** **Novelty**: how far each generated sequence is from its nearest *training* sequence (is it copying?). **Diversity**: how different the generated sequences are from *each other*. **Mode collapse**: a generator producing a few favourites over and over. Random letters score perfectly on novelty and diversity, so both only mean something next to quality.
- **Analogy:** Novelty is "not a copy of an existing design"; diversity is "the design team proposed many different architectures, not one with renamed signals".
- **Where it appears:** `sanity_samples.py` (novelty via MMseqs2); the Phase 3 harness.
- **First explained:** session 03 (novelty); session 04 (full set).

### Guardrail (in an evaluation)
- **Definition:** A pass/fail condition that must hold for a model's scores to be interpretable at all, without being a score itself. Ours: ≤ 5 % of samples copying a training sequence (≥ 80 % identity), ≥ 95 % distinct samples, mean GC within ±0.05 of real RNA.
- **Analogy:** A power-on self-test: if it fails, you don't bother reading the benchmark numbers.
- **Where it appears:** The frozen protocol, P7.
- **First explained:** session 04.

### Winner's curse
- **Definition:** When you pick the best of several candidates using a noisy measurement, the chosen one's measured value is, on average, better than its true value, because it partly won by luck.
- **Analogy:** The fastest chip in a quick speed test partly got a lucky measurement; retest it and it looks slightly slower.
- **Where it appears:** The baseline checkpoint was chosen on one fixed noise draw (1.9040); averaging 4 draws gives 1.9061.
- **First explained:** session 04.

### Common random numbers
- **Definition:** Giving every setting or model being compared the same random numbers (same lengths, same sampling seed, same noise draws), so that differences come from the settings, not from the dice.
- **Analogy:** Testing two circuits with the same input vectors rather than two different random vector sets.
- **Where it appears:** The sampling ablation (seed 0 for all 48 settings); E1 (noise seeds 1234–1237 for every model); length-matched samples.
- **First explained:** session 04.

### Goodhart's law (oracle exploitation)
- **Definition:** "When a measure becomes a target, it ceases to be a good measure." A generator steered or selected by one imperfect oracle can learn that oracle's quirks and score well without being good.
- **Analogy:** A design tuned against a SPICE model with a bug looks perfect in simulation and fails on silicon.
- **Where it appears:** Why Phase 3 adds a second, independent oracle; the risk in Phase 5's reward-guided steering.
- **First explained:** session 02 (as a risk, STUDY_GUIDE §1.10); by name, session 04.

*The next eleven entries were taught in Phase 2 (session 03, STUDY_GUIDE §4.5 and §4.7) but never entered here; added in session 05, when Phase 4 started to depend on them.*

### Logits, softmax
- **Definition:** **Logits** are a model's raw scores, one per possible token, any real number. **Softmax** turns them into probabilities: p_i = e^{logit_i} / Σ_j e^{logit_j}, all positive, summing to 1. A logit of −∞ gives probability exactly 0, which is how our models forbid special tokens.
- **Analogy:** Raw marks in an exam turned into each student's share of a prize pot: the bigger your mark relative to the others, the bigger your share, and everyone's shares add up to the whole pot.
- **Where it appears:** Every model's head outputs (B, L, 8) logits; `masked_fill(forbidden, -inf)`; the samplers' `torch.softmax`.
- **First explained:** session 03 (Phase 2); entry added session 05.

### Attention (query, key, value)
- **Definition:** A way for every position to gather information from every other position. Each position makes a **query** (what am I looking for?), a **key** (what do I contain?) and a **value** (what I hand over). Query·key scores every pair (an L × L grid), a softmax turns each row into weights, and each position receives the weighted average of the values. Worked: scores 1, 0, 2, ÷√2, give weights 0.284, 0.140, 0.576.
- **Analogy:** In a meeting, everyone states what they need, looks round the whole table, and listens mostly to the people whose expertise matches.
- **Where it appears:** `SelfAttention` in `ribomamba/models/transformer.py`; the thing BiMamba replaces in Phase 4.
- **First explained:** session 03 (Phase 2); entry added session 05.

### Residual connection (residual stream)
- **Definition:** Each block adds its output to its input (x + f(x)) instead of replacing it, so information and gradients can pass straight through a deep stack; the running x is the "residual stream".
- **Analogy:** Editing a document with tracked suggestions instead of retyping it: every editor adds changes, and the original text is never lost.
- **Where it appears:** Every Transformer block and every Mamba block (`x + Dropout(Mixer(LayerNorm(x)))`).
- **First explained:** session 03 (Phase 2); entry added session 05.

### LayerNorm, RMSNorm
- **Definition:** **LayerNorm** rescales each position's vector to mean 0 and spread 1, then applies a learned scale and shift; it keeps numbers in a healthy range through deep networks. **RMSNorm** is the simpler cousin that only divides by the root-mean-square (no mean subtraction, no shift); Mamba-2 uses a gated RMSNorm inside its layer.
- **Analogy:** Automatic volume control on each speaker's microphone before mixing, so no one voice drowns the others.
- **Where it appears:** Pre-norm blocks in both backbones (LayerNorm, D-016); the gate-normalisation inside every Mamba-2 mixer (RMSNorm).
- **First explained:** session 03 (Phase 2); RMSNorm session 05.

### MLP; activation functions (GELU, SiLU)
- **Definition:** The **MLP** is a small two-layer network applied to each position separately (d → 4d → d in our Transformer), the "thinking within a position" step. Between its layers sits a smooth on/off function: **GELU** in the Transformer; **SiLU** (z · sigmoid(z)) in Mamba.
- **Analogy:** After a meeting (attention), each person goes back to their own desk to think over what they heard.
- **Where it appears:** `Block.mlp` in the Transformer. Mamba layers have no separate MLP: their expansion to 768 channels and the SiLU gate do that job.
- **First explained:** session 03 (Phase 2); SiLU session 05.

### Rotary position encoding (RoPE)
- **Definition:** Positions enter attention by rotating pairs of numbers in the query and key by an angle proportional to position, so a score depends only on the distance between two positions. No parameters.
- **Analogy:** Two clock hands turned by amounts set by where each person sits: the angle between them tells how far apart they sit, wherever they are at the table.
- **Where it appears:** `RotaryEmbedding` in the Transformer. Mamba needs none: a scan reads positions in order, so order is built in.
- **First explained:** session 03 (Phase 2); entry added session 05.

### AdamW; learning rate; warmup and cosine decay
- **Definition:** **AdamW** is the optimiser: it gives every weight its own step size from running averages of its gradients, and shrinks weight matrices slightly each step (weight decay). The **learning rate** sets the overall step size; we raise it linearly from ~0 (**warmup**, 1,000 steps) and then lower it along half a cosine to 10 % of the peak.
- **Analogy:** Learning to drive: start slowly in the car park, go at full speed on the open road, slow down again as you approach the destination.
- **Where it appears:** `make_optimizer` and `learning_rate` in `scripts/train.py`; the learning-rate sweep (D-011) chooses the peak.
- **First explained:** session 03 (Phase 2); entry added session 05.

### bf16 mixed precision
- **Definition:** Doing most arithmetic in bfloat16, a 16-bit number format with float32's range but less precision, while keeping the weights in float32. About twice as fast and half the memory; sampling probabilities are then formed in float64 on purpose.
- **Analogy:** Rough working in pencil on scrap paper, with the final answers copied neatly into the notebook.
- **Where it appears:** `torch.autocast("cuda", dtype=torch.bfloat16)` in training, evaluation and sampling.
- **First explained:** session 03 (Phase 2); entry added session 05.

### Gradient clipping
- **Definition:** If the gradient's overall size (norm) exceeds a limit (1.0 for us), it is scaled down to that limit before the step, so one unusual batch cannot throw the weights far off.
- **Analogy:** A speed limiter on a car: you can still go anywhere, just never dangerously fast.
- **Where it appears:** `clip_grad_norm_(..., 1.0)` in `scripts/train.py`.
- **First explained:** session 03 (Phase 2); entry added session 05.

### EMA of the weights
- **Definition:** An exponential moving average of the weights, updated every step: ema ← 0.9999 · ema + 0.0001 · weights. It smooths out step-to-step jitter; evaluation and sampling use it. It is itself a one-number state-space model with keep factor 0.9999, remembering roughly the last 10,000 steps.
- **Analogy:** Your running impression of a restaurant: each new meal nudges it a little, and old meals fade slowly.
- **Where it appears:** `update_ema` in `scripts/train.py`; the `ema` weights in every checkpoint; the first example in Phase 4's concept block.
- **First explained:** session 03 (Phase 2); entry added session 05.

### Early stopping by best checkpoint
- **Definition:** Evaluate on validation every 2,500 steps and keep the state with the lowest validation bits/nt (`best.pt`), whatever happens afterwards.
- **Analogy:** Keeping your best practice-exam paper rather than your last one.
- **Where it appears:** `best.pt` in every run; "best-during-run" in the protocol (P4).
- **First explained:** session 03; entry added session 05.

*Phase 4 vocabulary (session 05, concept instalments 1–3).*

### State-space model (SSM)
- **Definition:** A model that reads a sequence once, carrying a fixed-size summary (the **state**) that it updates at every position: h_t = a·h_{t−1} + b·x_t, output y_t = c·h_t. In continuous time, h′ = Ah + Bx, y = Ch + Dx: the same equations as in Control Systems (where the state is called x and the input u).
- **Analogy:** A bank balance: one number summing every transaction, updated with each one; it never grows, but you cannot recover a single transaction from it.
- **Where it appears:** The core of every Mamba layer (`ribomamba/models/bimamba.py`).
- **First explained:** session 05, instalment 1.

### Keep factor (decay)
- **Definition:** The number a (between 0 and 1) that multiplies the old state at each step. A state remembers roughly the last 1/(1 − a) steps: a = 0.5 about 2, 0.9 about 10, 0.9999 about 10,000.
- **Analogy:** How much of yesterday's gossip you still remember today.
- **Where it appears:** `exp(Δ·A)` inside the Mamba-2 kernel; one A per head, always negative (A = −exp(A_log)), so the model stays stable.
- **First explained:** session 05, instalment 1.

### Step size Δ (discretisation)
- **Definition:** Converting the continuous h′ = Ah + Bx into steps with step size Δ gives keep factor a = e^{ΔA} (zero-order hold) and write strength b ≈ Δ·B. Small Δ: keep the memory, barely write the letter; large Δ: wipe the memory, write the letter strongly. One dial controls both.
- **Analogy:** How long you look at something: a glance leaves your thoughts as they were; a long look replaces them.
- **Where it appears:** `dt` in Mamba-2 (softplus of a learned projection plus `dt_bias`, one per head per position).
- **First explained:** session 05, instalment 2.

### Selective (selection mechanism)
- **Definition:** Mamba's key idea: Δ, B and C are computed from each position's own features, so the model decides per letter how much to remember and what to write and read. Measured example: after a 12-letter loop, fixed keep factors retain 0–25 % of the memory of the G's; a selective rule retains 88 %.
- **Analogy:** Taking notes in a lecture: you write down the important points, skip the jokes, and the choice depends on what is being said.
- **Where it appears:** Every Mamba-2 layer (the `dt`, `B`, `C` parts of `in_proj`).
- **First explained:** session 05, instalment 2.

### Scan (parallel scan)
- **Definition:** Computing all the running states of a recurrence. Each step "multiply by a, add u" is a pair (a, u); two steps combine into one pair, (a₂a₁, a₂u₁ + u₂), and the combination is associative, so a GPU can combine in a tree: 256 positions in 8 rounds instead of 256 sequential steps.
- **Analogy:** Totalling a long receipt: one cashier goes line by line; a team splits it, adds pairs of lines at once, then pairs of pairs.
- **Where it appears:** Inside `mamba_split_conv1d_scan_combined` (the fused kernel we call).
- **First explained:** session 05, instalment 2.

### Mamba, Mamba-2, state-space duality
- **Definition:** **Mamba** (Gu & Dao 2023): a sequence model built from selective state-space layers, linear in length, with fused GPU kernels. **Mamba-2** (Dao & Gu 2024): one keep factor per head, which makes the layer equal to an attention-like grid (**state-space duality**): y_t = Σ_{s≤t} (C_t·B_s)(a_{s+1}⋯a_t) Δ_s x_s. It is computed in chunks with fast matrix multiplications, allows larger states (128 vs 16), but the grid is constrained: one direction, no softmax, fading through whatever lies between, built from a fixed-size state.
- **Analogy:** A single pass through a book with an index card per chapter (the state), versus attention's spreading every page on a table.
- **Where it appears:** `mamba-ssm` 2.3.2.post1's `Mamba2`; our BiMamba and AR Mamba.
- **First explained:** session 05, instalment 2.

### Head (in Mamba-2)
- **Definition:** A group of 64 channels that share one keep factor at each letter; a d = 384 layer has 12 heads, each channel carrying a 128-number state (98,304 state numbers per layer).
- **Analogy:** A team whose members all get the same "how much to forget" instruction but take different notes.
- **Where it appears:** `headdim=64`, `nheads = 768 / 64 = 12` in `Mamba2`.
- **First explained:** session 05, instalment 2.

### Gate (gating)
- **Definition:** Multiplying a signal by a learned value between about 0 and 1 (here SiLU of another projection, z) so the network can open or close each channel per position.
- **Analogy:** A tap on each pipe that the network turns per letter.
- **Where it appears:** `y · SiLU(z)` before the gate-normalisation in every Mamba-2 mixer.
- **First explained:** session 05, instalment 2.

### Short causal convolution (in Mamba)
- **Definition:** Before the scan, each channel mixes each position with its 3 previous positions (width 4), looking only backwards. It gives the scan immediate local context.
- **Analogy:** Reading each word together with the three words before it.
- **Where it appears:** `conv1d` in `Mamba2` (per direction in BiMamba).
- **First explained:** session 05, instalment 2.

### BiMamba (bidirectional Mamba)
- **Definition:** Two scans per layer, left to right and right to left, outputs added, so every position summarises both sides. Ours shares `in_proj`/`out_proj` between directions and gives each its own convolution, Δ bias, A, D and gate-norm (D-016); each sequence is reversed within its own length so padding never enters a real position.
- **Analogy:** Proof-reading a sentence forwards and then backwards, and combining both readings.
- **Where it appears:** `BiMamba2Mixer` in `ribomamba/models/bimamba.py`: the Phase 4 denoiser.
- **First explained:** session 05, instalment 3.

### Next-token prediction (shift by one); length-constrained sampling
- **Definition:** How the autoregressive model trains: the output at position i predicts the token at position i + 1 (`<bos> G C A` → `G C A <eos>`), cross-entropy everywhere, exact likelihood. **Length-constrained sampling** forbids `<eos>` before the target length and forces it there, so the AR model receives the same lengths as the diffusion models (protocol P5).
- **Analogy:** Predictive text on a phone, told how many words the message must have.
- **Where it appears:** `ribomamba/autoregressive.py` (`next_token_targets`, `ar_loss`, `sample_ar`).
- **First explained:** Phase 2 (chain rule); code session 05, instalment 3.

### Parameter matching (by depth or by width)
- **Definition:** Giving every compared model the same number of learnable parameters (the protocol allows ±2 %), so a difference can't come from size. A Mamba-2 layer holds 56 % of a Transformer block, so Mamba must be matched **by depth** (same width 384, more layers: 14) or **by width** (same 8 layers, each wider).
- **Analogy:** A fixed kitchen budget: more cooks of the same kind (depth), or the same number of cooks at bigger stations (width).
- **Where it appears:** D-015; `check_parameter_budget` in `ribomamba/models/build.py` refuses any run outside ±2 %.
- **First explained:** session 05, instalment 3.

### Associative recall
- **Definition:** Finding the item that was stored together with a cue seen earlier ("which letter sat opposite this one?"). Models with a fixed-size state are provably limited at copying from context, and Mamba is measurably weaker at it than attention (Jelassi et al. 2024); attention-free gated-convolution models lose to attention mostly on this kind of recall (Arora et al. 2023, "Zoology"). References: docs/REFERENCES.md.
- **Analogy:** Remembering which coat belongs to which cloakroom ticket.
- **Where it appears:** Why Phase 4's question is open: base pairing looks like recall.
- **First explained:** session 05, instalment 3.

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

### Rule of three
- **Definition:** If an event happened 0 times in n independent trials, its true rate is below about 3/n with 95 % confidence. "0 out of 2,000" means "below ~0.15 %", not "exactly zero".
- **Analogy:** Zero failures in a short burn-in doesn't prove a zero failure rate, only an upper bound.
- **Where it appears:** Check D of the structural audit (0 membership-level hits in a 2,000 sample).
- **First explained:** session 03.

### Probability distribution, sampling
- **Definition:** A **distribution** assigns every possible outcome a probability between 0 and 1, all summing to 1. **Sampling** draws an outcome at random so that likely outcomes come up often.
- **Analogy:** A loaded die, and rolling it.
- **Where it appears:** A generative model *is* a distribution over sequences; generation is sampling.
- **First explained:** session 03.

### Chain rule of probability
- **Definition:** p(x₁ … x_L) = p(x₁) · p(x₂ | x₁) · … · p(x_L | x₁ … x_{L−1}). Exact for any distribution; the basis of autoregressive models.
- **Analogy:** Computing the probability of a whole bit string one bit at a time, each bit given the ones before it.
- **Where it appears:** Phase 2 Part A; the Phase 4 autoregressive baseline.
- **First explained:** session 03.

### Cross-entropy; nats and bits
- **Definition:** The loss −log p for the probability p the model gave to the true answer: 0 when certain and right, large when confident and wrong. With the natural log the unit is **nats**; divide by ln 2 ≈ 0.693 to get **bits**.
- **Analogy:** A penalty that grows steeply the more confidently you bet on the wrong outcome.
- **Where it appears:** The diffusion loss (masked positions only); bits per nucleotide.
- **First explained:** session 03.

### ELBO / NELBO (evidence lower bound)
- **Definition:** A quantity guaranteed to be ≤ log p(x) (its negative, the NELBO, is ≥ −log p(x)). For masked diffusion, the weighted loss E_t[(1/t) Σ_masked −log p_θ] is exactly a NELBO, which is why it can be reported as a likelihood.
- **Analogy:** A guaranteed worst-case timing bound: you may be faster in reality, never slower.
- **Where it appears:** Why the 1/t weight; bits per nucleotide for diffusion models.
- **First explained:** session 03.

### Positive control, negative control
- **Definition:** A **positive control** runs a detector on a case where the answer is known to be *yes*, measuring sensitivity (can it see?). A **negative control** runs it where the answer is known to be *no*, measuring the false-alarm rate (noise floor).
- **Analogy:** Fault injection to measure fault coverage (positive); measuring with the input grounded to see the noise floor (negative).
- **Where it appears:** `audit_structural.py`: own family found (positive); dinucleotide-shuffled sequences (negative).
- **First explained:** session 03 (re-taught at the Phase 1 gate).

### Dinucleotide shuffle
- **Definition:** A random rearrangement of a sequence that keeps exactly how often each letter is followed by each other letter (Altschul & Erickson 1985). The standard "looks like RNA but isn't real" null model, because stacking energies depend on neighbours.
- **Analogy:** A random walk that uses every road of a map exactly once, starting from the same town.
- **Where it appears:** `dinucleotide_shuffle()` in `ribomamba/data/structure_search.py` (tested).
- **First explained:** session 03.

### 95 % confidence interval (for a proportion)
- **Definition:** A range that, over repeated sampling, contains the true value 95 % of the time. For a proportion p from n samples it's roughly p ± 1.96·√(p(1−p)/n).
- **Analogy:** Error bars on a measured yield from a sample of dies rather than the whole wafer.
- **Where it appears:** The audit samples 2,000 sequences, so e.g. 89.6 % ± 1.3 %.
- **First explained:** session 03.

### Bootstrap (percentile bootstrap confidence interval)
- **Definition:** A way to get error bars for *any* statistic without a formula (Efron 1979): treat your n measurements as a stand-in for the population, draw n of them *with replacement* many times (e.g. 10,000), recompute the statistic each time, and take the 2.5th and 97.5th percentiles of the results as the 95 % interval. Example: outcomes 1,0,1,1,0,1,1,1,0,1 (70 %) → interval ≈ [40 %, 100 %]; 546 of 1,000 → [51.7 %, 57.9 %].
- **Analogy:** Estimating clock jitter from one long captured trace by re-cutting it into many pseudo-traces.
- **Where it appears:** Every number in the Phase 3 harness.
- **First explained:** session 04.

### Cluster bootstrap
- **Definition:** A bootstrap that resamples whole groups (here: RNA families) instead of individual items, because items in one group are correlated and don't count as independent evidence.
- **Analogy:** Measuring 1,000 transistors from 10 wafers: the error bar must count wafers, because wafer-to-wafer variation dominates.
- **Where it appears:** Phase 3 statistics for anything computed over real held-out sequences (e.g. test bits/nt).
- **First explained:** session 04.

### Two sources of randomness (sampling vs training seed)
- **Definition:** A model's score varies because of *which samples were drawn* (the bootstrap measures this) and because of *which random seed it was trained with* (only retraining with other seeds measures this). A claim about an architecture needs the second.
- **Analogy:** Many transistors on one die tell you about that die (within-die variation); a claim about the process needs several dies (die-to-die variation).
- **Where it appears:** Phase 4: several training seeds per backbone (number fixed in the Phase 3 protocol).
- **First explained:** session 04.

### Paired comparison
- **Definition:** Evaluate both models on the *same* items (same targets, same lengths, same random numbers) and analyse the per-item differences. Item difficulty cancels, so much smaller real differences become visible.
- **Analogy:** Common-mode rejection in a differential pair: noise common to both inputs cancels, the difference survives.
- **Where it appears:** Phase 3 statistics; Phase 4–5 comparisons.
- **First explained:** session 04.

### Multiple comparisons; family-wise error; Holm–Bonferroni
- **Definition:** Each test at the 5 % level has a 5 % false-alarm chance; with 20 independent tests the chance of at least one false "win" is 1 − 0.95²⁰ ≈ 64 % (the **family-wise error**). **Holm–Bonferroni** (Holm 1979) controls it: sort the m p-values from smallest up, compare the smallest with 0.05/m, the next with 0.05/(m−1), and so on, and stop at the first that fails.
- **Analogy:** Check 20 timing paths with a noisy measurement and one will "fail" by chance most of the time.
- **Where it appears:** The frozen protocol's primary endpoints.
- **First explained:** session 04.

### Permutation test (exact, seed-level)
- **Definition:** A test that asks how often a difference at least as large as the observed one would appear if the group labels were meaningless: try every way of relabelling the observations and count. With each trained model as one observation, 3 vs 3 models allow C(6,3) = 20 relabellings, so the smallest possible two-sided p is 2/20 = 0.10; 5 vs 5 allow 252, smallest p ≈ 0.008.
- **Analogy:** Shuffling the name tags on the dies and checking whether the "fast process" still looks fast.
- **Where it appears:** `seed_permutation_test` in `ribomamba/eval/stats.py`; the reason the protocol asks for five seeds per architecture.
- **First explained:** session 04.

### z-score
- **Definition:** How many standard deviations a value lies from a reference mean: z = (value − mean) / sd.
- **Analogy:** "A 3σ corner."
- **Where it appears:** The MFE z-score against shuffles.
- **First explained:** session 04.

### Hamming distance
- **Definition:** The number of positions at which two equal-length strings differ. `GGGAAACC` vs `GCGAAAGC` → 2.
- **Analogy:** The number of bit flips between two codewords.
- **Where it appears:** Diversity among designs for the same target (Phase 3/5).
- **First explained:** session 04.

### Wasserstein-1 distance; Jensen–Shannon divergence
- **Definition:** Two ways to measure how different two distributions are. **Wasserstein-1** ("earth mover's distance", for numbers like GC content): the least average distance you must move probability mass to turn one histogram into the other, in the units of the quantity. **Jensen–Shannon divergence** (for frequency tables like k-mer counts): an entropy-based difference, 0 for identical tables, at most 1 bit. Neither means anything without a calibration: the distance between two independent samples of *real* RNA (the noise floor).
- **Analogy:** Wasserstein: the work to reshape one sand pile into another. Calibration: measuring the scope's noise floor with the probe grounded before trusting a small reading.
- **Where it appears:** Phase 3 distributional comparison of generated vs real RNA.
- **First explained:** session 04.

### Impulse response; linear time-invariant (LTI) system; convolution
- **Definition:** For a system that applies the same rule at every step (time-invariant) and adds contributions linearly, the output is the input **convolved** with the **impulse response** (its reaction to a single unit input). For the one-number state h_t = a·h_{t−1} + x_t with a = 0.5 the impulse response is 1, 0.5, 0.25, …; a letter 4 steps back contributes 0.0625.
- **Analogy:** A clap in a hall: you hear it, then fainter and fainter echoes, and every sound gets the same echo.
- **Where it appears:** Why a non-selective state-space model can be trained as one big convolution (S4), and why it treats every letter alike; selection breaks it.
- **First explained:** session 05, instalment 1.

### Linear vs quadratic time
- **Definition:** How cost grows with length L: a scan costs proportional to L; attention compares every pair, proportional to L² (256 → 65,536 pairs). Big-O says how cost *grows*, not the price at a given size: at L = 256 one Mamba-2 block measured 6.0 ms against the Transformer block's 3.8 ms, and only at L = 1,024 was it faster (11.7 vs 21.7 ms).
- **Analogy:** Shaking hands with everyone at a party (grows with the square of the guests) versus greeting each guest once at the door (grows with the number of guests); for a small party the handshakes can still be quicker.
- **Where it appears:** RESULTS.md, "Does Mamba run here"; why linear time buys no speed at our 256-letter cap.
- **First explained:** session 05, instalment 1 (Big-O itself: session 01).

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

### MPI, `mpirun`
- **Definition:** MPI (Message Passing Interface) is a standard for running one program as several cooperating processes. `mpirun -np 4 prog` starts 4 copies that talk to each other. EternaFold's conda build is written this way: one coordinator process hands work to workers, so started alone it waits forever for workers that don't exist.
- **Analogy:** A foreman with no crew: started without `mpirun`, the job never gets done.
- **Where it appears:** `ribomamba/eval/eternafold.py` always launches EternaFold through `mpirun -np P` (P ≥ 2).
- **First explained:** session 04.

### Most probable (Viterbi) structure vs MEA structure
- **Definition:** Two ways to turn a folding model's ensemble into one predicted structure. **Viterbi** / most probable: the single structure with the highest probability (the same kind of answer as ViennaRNA's MFE). **MEA** (maximum expected accuracy): the structure whose base pairs have the highest expected overlap with the ensemble; it can differ, and EternaFold uses it by default.
- **Analogy:** The single most likely word sequence from a decoder versus the sequence that gets the most individual letters right on average.
- **Where it appears:** We take EternaFold's Viterbi structure (`--viterbi`), so it's comparable with ViennaRNA's MFE (D-013).
- **First explained:** session 04.

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

### Covariance model (CM), Infernal, cmscan
- **Definition:** A **covariance model** is a statistical model of an RNA family that scores single positions *and* pairs of positions that must base-pair (any complementary pair is accepted), so it recognises relatives whose letters changed by covariation. **Infernal** is the software for CMs; **cmscan** scores each sequence against every model in a database (Rfam 15.0: 4,178 models).
- **Analogy:** A pattern matcher with paired constraints, "positions 3 and 20 must be complementary, whatever the letters".
- **Where it appears:** `ribomamba/data/structure_search.py`; step 11 of `prepare_data.py`; `audit_structural.py` (D-009).
- **First explained:** session 03.

### Bit score, GA (gathering) threshold
- **Definition:** A CM's **bit score** says how much more likely a sequence is under "member of this family" than under "random RNA" (+1 bit = twice the odds). The **GA threshold** is a curator-set cutoff per family; Rfam's full member lists are exactly the hits scoring ≥ GA. So ≥ GA means "Rfam would call this a member".
- **Analogy:** A pass mark set per exam by the examiner.
- **Where it appears:** `gathering_thresholds()`; the leakage criterion of step 11.
- **First explained:** session 03.

### HMM-only mode and `--nohmmonly`
- **Definition:** For a model with **zero base pairs**, cmscan by default uses a cheaper letters-only model (a profile HMM), whose bit scores aren't on the scale the GA thresholds were set on. `--nohmmonly` forces full CM scoring for every model, as Rfam's own annotation does. 347 of 4,178 Rfam 15.0 models have zero pairs.
- **Analogy:** Comparing a reading in dB with a pass mark written in volts.
- **Where it appears:** A bug in the first scan (session 03): own-family recovery for zero-pair families went 87.93 % → 99.99 % once the flag was added.
- **First explained:** session 03.

### Trust on first use (TOFU)
- **Definition:** When a source publishes no checksum, recording the checksum of your first download. It guarantees that later downloads are identical to yours, not that yours was authentic.
- **Analogy:** Recording a device's fingerprint the first time you pair it.
- **Where it appears:** The Rfam 15.0 `Rfam.cm.gz` pin in `download_data.py`.
- **First explained:** session 03.

### Per-sequence (content-addressed) cache
- **Definition:** Storing results under a fingerprint (hash) of each input item, so any later request containing the same item reuses the stored result. Valid only if an item's result doesn't depend on the other items it was computed with (checked for cmscan).
- **Analogy:** A cache indexed by address: a hit doesn't care which program asked.
- **Where it appears:** `cmscan()` cache under `data/processed/cmscan_cache/<flags-hash>/`: prepare reruns take 24 s instead of 2 h.
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

### Fused GPU kernel; Triton
- **Definition:** A **kernel** is one program the GPU runs; a **fused** kernel does several steps (convolution, scan, gate, normalisation) in one go, keeping intermediate numbers in the GPU's small fast memory instead of writing them out. **Triton** is a language for writing such kernels in Python-like code; Mamba-2's are written in it and compiled on first use.
- **Analogy:** Cooking a whole dish at one station instead of carrying the pan to a different counter after every step.
- **Where it appears:** `mamba_split_conv1d_scan_combined` (called directly by `BiMamba2Mixer`); the reason the Mamba models run only on a GPU.
- **First explained:** session 05, instalment 2.

### Testing the tests (deliberate bugs)
- **Definition:** After tests pass, introduce a known bug on purpose and check that some test fails; a test that cannot fail proves nothing. The software version of a positive control.
- **Analogy:** Pressing the smoke alarm's test button: silence means the alarm is broken, not that there is no fire.
- **Where it appears:** Session 05: a whole-row flip and a swapped gate/normalisation order were each caught by `tests/test_bimamba.py`.
- **First explained:** session 05 (positive controls: session 03).

## Research pivot terms — 2026-09-27
- **Repair trajectory:** a recorded sequence of attempted changes to a candidate,
  including failures and scores; like a repair log for a circuit. Planned for
  the new pilot, not yet implemented.
- **Negative design:** changing a sequence to discourage unwanted competing folds,
  rather than only stabilizing the desired one. Like suppressing unwanted modes
  in a system. Proposed use: failure-feedback-guided repair.
- **Oracle budget:** counted calls to the folding software used to score designs.
  Like counting instrument measurements; MFE and partition-function calls have
  different costs and must be logged separately in the planned harness.
