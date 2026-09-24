# RiboMamba — Study Guide

> **Read this the night before the interview.** It is written for a version of
> you who has forgotten the details and has one evening to rebuild a confident,
> working understanding of the whole project, from "what is RNA" to "what our
> numbers mean and where they fall short".

**Status:** Parts 1–2 written in full (end of Phase 0 content, 2026-09-22).
Part 3 written at the end of the Phase 1 build (2026-09-23). Part 4 written
at the end of the Phase 2 build (2026-09-24; revised after its gate). Parts
5–10 are written at the end of their phases (CLAUDE.md §2.4), so this guide grows
with the work instead of being rushed at the end.

---

## If you only have thirty minutes

*(Phase 0 version. This section is extended at each phase boundary.)*

RNA is a chain molecule. Each link carries one of four letters, **A, C, G,
U**, so an RNA is a string over a four-letter alphabet. Unlike DNA it is
usually single-stranded, so it folds back onto itself: **G pairs with C**
(strongest), **A pairs with U**, and **G–U** is a weaker "wobble" pair. The
set of pairs a molecule forms is its **secondary structure**, and that shape
is what makes the molecule do its job.

Which shape does a given sequence adopt? Physics picks the one with the
lowest **free energy ΔG** (in kcal/mol; unfolded = 0; more negative = more
stable). Stacked pairs lower the energy; loops raise it. Energies add up from
small local pieces measured in the lab (the **nearest-neighbour model** with
**Turner parameters**), and because pairs are not allowed to cross, dynamic
programming finds the lowest-energy structure in **O(N³)** time (the **Zuker
algorithm**, implemented in **ViennaRNA**). That direction, sequence →
structure, is **folding**, and it's fast and solved-enough. It's like
simulation: given the circuit, compute what it does.

Our project is the opposite direction: **design**, also called **inverse
folding**: given a target shape, find sequences that fold into it. It's like
synthesis instead of simulation, and it is hard for four reasons. There are
**4^N** candidate sequences (for N = 50, about 10³⁰, so brute force is
hopeless by a factor of thousands of times the age of the universe). The
landscape is **rugged**, so changing one letter can throw away the whole
design. Being the best structure isn't enough: the target must beat every
rival **by a margin**, or the molecule flickers between shapes. And the
answer is a *set* of sequences, not one, because we want many diverse
solutions.

We measured all of that on a nine-letter example. `GGGAAACCC` does fold to
its intended hairpin `(((...)))` at **−1.20 kcal/mol**, but a rival shape
sits only **0.20 kcal/mol** away, so the molecule sits in the intended shape
just **50.7 %** of the time. It passes an "MFE equals target" test while
behaving like a coin flip. Change the last letter to get `GGGAAACCA` and the
whole pairing **slides over by one position** into a different hairpin, which
it then holds **93.9 %** of the time. Heat the first one to 70 °C and it
**melts** completely.

So the plan of the project: instead of searching for sequences one target at a
time, **learn** what real RNA sequences look like, then sample many candidates
quickly and check each one with the folding software (the **oracle**). Be
honest about the limits: success means *the oracle predicts the target*, not a
wet-lab result; we work only with nested secondary structures, not 3D shapes
and not **pseudoknots**; and "the MFE matches" is a weak test on its own, so
the target's **share of the ensemble** matters too.

*(Phase 1 addition.)* The training data is **Rfam**, a catalogue of about
4,000 RNA **families**. A family is a set of evolutionary relatives: different
letters, same structure, same job. Relatives are the whole problem with
testing. Split the data randomly and **about 90 %** of test sequences have a
≥ 80 %-identical relative in training (we measured it), so a test score
would measure memory. So we split by **clan** (a group of related families),
or by family when there's no clan: whole groups go to train, validation or
test. Then we removed the 775 held-out sequences that still had a close
training relative by letters, because Rfam doesn't link every related pair,
and the 12 that Rfam's own structure-aware family models would call members
of a training family. Result: **99 % of test sequences have no detectable
relative in training.** Along the
way we found that the HuggingFace copy of Rfam contains **every row twice**,
the second copy labelled "No such family". Left in, that one label would have
silently leaked every family into every split. After cleaning (T → U, only
A/C/G/U, families of typical length ≤ 256, fragments removed, duplicates
removed, at most 1,000 members per family) we have **452,867 / 57,052 /
56,873** sequences for train / val / test. Each nucleotide is one **token**
(vocabulary of 8: A, C, G, U plus pad, mask, begin, end), and batches group
similar lengths so only **1.1 %** of the GPU's work is padding instead of
54 %.

*(Phase 2 addition.)* The generator is a **masked diffusion model**:
training hides a random fraction t of the letters (from 0 % to 100 %) and
teaches a network to fill them back in; generating starts from all-hidden
and reveals letters step by step. The loss scores only the hidden letters,
weighted by 1/t, which makes it a bound on the true likelihood, reported in
**bits per nucleotide** (2.0 = knows nothing). The network is a standard
14-million-parameter Transformer. Every sequence is framed with start and
end markers, because without them the model provably can't tell positions
apart when everything is hidden. Settings were chosen by rules written in
advance, and those rules apply identically to Mamba later. The baseline
reaches **1.904 bits/nt** on families it has never seen, better than the
best counting model (1.966), and it overfits after about three passes over
the data (dropout didn't cure that). Its generated RNA is novel (no
copies of training sequences) and letter-realistic, but **barely more
structured than chance**: 55 % of samples fold better than their own
shuffles, against 79 % of real RNA. Closing that gap is what the rest of the
project is about.

---

## Part 1 — What RNA is, and what "folding" means  *(Phase 0)*

### 1.1 The molecule, and why it's fair to call it a string

RNA is a **polymer**: a long chain built from many copies of a similar small
unit, like a chain of beads, or a shift register made of identical stages.
Each unit is a **nucleotide**, and each nucleotide has two parts:

- a **backbone** piece (a sugar joined to a phosphate), which is *identical*
  in every nucleotide and simply holds the chain together in order;
- a **base**, which is one of four: **A** (adenine), **U** (uracil),
  **G** (guanine), **C** (cytosine).

Because the backbone never varies, it carries no information. Something that
is the same everywhere cannot tell one molecule apart from another. It's the
supply rail of the circuit: essential to operation, useless for
identification. All the information is in *which base sits at each position*,
so for our purposes:

> **An RNA molecule is a string over the alphabet {A, C, G, U}.** Two bits of
> information per position.

The chain has a direction, because its two ends are chemically different:
they're called **5′** ("five-prime") and **3′**. By convention sequences are
written 5′ → 3′, left to right, so `AUGC` and `CGUA` are different molecules.
It's the same as the MSB-first convention on a serial bus: the same bits in
the other order mean something else.

A useful check on whether you've understood why the string representation is
legitimate: *suppose there were three kinds of backbone instead of one.* Then
each position would have 4 × 3 = 12 possibilities, about 3.6 bits, and a
plain string over {A, C, G, U} would no longer describe the molecule. You'd
need a pair per position. The single-letter representation is a consequence of
a physical fact, not a convenience.

**How RNA relates to DNA and proteins.** DNA is the cell's long-term storage
copy of genetic information: think ROM, the master copy you never run directly
from. RNA is a working copy made from it, loaded into RAM. Some RNAs are read
as instructions to build **proteins** (the machines that do most of the work
in a cell). Others don't code for anything; they **fold into a shape and do a
job themselves**, and those are the interesting ones for design. Crucially,
DNA is usually double-stranded (two strands wound together, each protecting
the other), while RNA is usually **single-stranded**, which is exactly what
lets it fold back onto itself.

### 1.2 Why it folds: base pairing

Two very different kinds of connection hold an RNA together.

| | Bond type | Strength | What it decides |
|---|---|---|---|
| **Backbone links** | covalent | strong, permanent at body temperature | the **order** of bases |
| **Base pairs** | hydrogen bonds | weak, constantly forming and breaking | the **shape** |

Solder joints versus Velcro. The solder joints (backbone) fix the topology
once and for all; the Velcro (base pairs) can be pulled apart and re-formed.

Only certain pairs are allowed, and they differ in strength:

- **G–C**: three hydrogen bonds. The strongest.
- **A–U**: two hydrogen bonds.
- **G–U**: the "wobble" pair, weaker and slightly misaligned.

Everything else is treated as not pairing, and each base can have at most one
partner at a time. Think keyed connectors: a 3-pin (G–C) and a 2-pin (A–U)
plug, each of which only fits its matching socket.

When a strand folds back on itself, the two paired stretches run in opposite
directions (**antiparallel**), like folding a strip of paper in half. In
`GGGAAACCC`, position 1 pairs with 9, 2 with 8, 3 with 7. And the turn at the
fold can't be arbitrarily tight: a hairpin's loop needs **at least 3 unpaired
bases**, because the backbone has a minimum bend radius, exactly like a cable
or a PCB trace.

### 1.3 A single pair is useless; stacks are what hold

One hydrogen-bonded pair is far too weak to survive the constant thermal
jostling inside a cell. Pairs only become stable when several sit next to each
other and **stack** like a pile of coins, each one flat against the next. One
Velcro hook doesn't hold a jacket shut; a strip of them does.

This is why an RNA structure looks like runs of consecutive pairs (**stems**)
separated by unpaired regions (**loops**), rather than isolated pairs
scattered anywhere.

### 1.4 Secondary structure and dot-bracket notation

Three levels of description, and it's worth being precise about which one
we're working with:

| Level | What it says | VLSI analogy |
|---|---|---|
| **Primary** | the sequence of bases | the component list |
| **Secondary** | which position is paired with which | the netlist / schematic |
| **Tertiary** | the full 3D arrangement in space | the physical layout |

**This project works at the secondary level** (decision **D-001**), because
secondary structure captures most of what determines function and can be
predicted in milliseconds, while 3D prediction for RNA is far more expensive
and still much less reliable than it is for proteins. Our evaluation folds
tens of thousands of generated sequences on a laptop with a zero budget, so
that speed isn't a luxury.

A secondary structure is a set of pairs (i, j) with i < j. Two named parts
you should never mix up:

> **Stems are made of paired bases. Loops are made of unpaired bases.**

- **Stem (helix):** a run of consecutive stacked pairs.
- **Hairpin loop:** unpaired bases at the tip of a hairpin (minimum 3).
- **Bulge:** unpaired bases interrupting a stem on **one** side.
- **Internal loop:** unpaired bases interrupting a stem on **both** sides.
- **Multiloop (junction):** a loop with three or more stems branching off it.

**Dot-bracket notation** writes a structure as a string the same length as the
sequence: `(` means "paired with a later position", `)` means "paired with an
earlier one", `.` means unpaired. Because pairs never cross (next section),
brackets nest like parentheses in code and a **stack** (last-in, first-out)
recovers the pairs:

```
sequence   G G G A A A C C C
structure  ( ( ( . . . ) ) )
pairs      1–9, 2–8, 3–7        loop: positions 4,5,6
```

A slightly bigger one to practise on, `((..((...))..))`: the pairs are
(1,15), (2,14), (5,11), (6,10). That's an outer stem of 2 pairs, an inner
stem of 2 pairs, a hairpin loop at 7–9, and positions 3, 4, 12, 13 form an
**internal loop** (unpaired on both sides, between the two stems).

### 1.5 The no-crossing rule, and why pseudoknots are excluded

Standard secondary structure forbids **crossing** pairs, i.e. (i, j) and
(k, l) with i < k < j < l. A crossing pair is called a **pseudoknot**. Draw
the sequence as a line with arcs above it for pairs: no two arcs may cross,
like routing on a single metal layer with no vias.

Pseudoknots are real and biologically important, and **we exclude them
anyway**. The reason is computational, not notational, and that distinction
matters in an interview:

> If pairs never cross, then a pair (i, j) splits the problem cleanly into
> "inside" and "outside", which can be solved **independently**. That's what
> lets dynamic programming solve each sub-stretch once, store it, and reuse it
> — giving O(N³) instead of an exponential search. Once pairs may cross, the
> pieces are coupled, and exact prediction becomes dramatically more
> expensive.

The notation's limitation follows from that choice rather than causing it.
Single-bracket dot-bracket genuinely cannot express a pseudoknot, and worse,
if you try, the string **silently decodes into a different but perfectly
valid** nested structure. It's a bit error that lands on another legal
codeword, so nothing complains. (Extended notation adds a second bracket
type, `[ ]`, which is the second metal layer.)

**The honest limitation to state out loud:** any RNA whose function depends on
a pseudoknot is outside what this project can target or evaluate.

### 1.6 Free energy: why one structure wins

A sequence can fold in many legal ways. Which one does it actually adopt?
Every structure gets a **free energy ΔG**, measured in **kcal/mol**, relative
to the unfolded chain, which is defined as 0. More negative means more
stable. Picture a landscape of valleys; the molecule is a ball, and thermal
noise shakes the ground.

The formula behind it:

> **ΔG = ΔH − T·ΔS**
>
> - **ΔH** (enthalpy): energy released by forming bonds. Negative, so
>   favourable.
> - **T**: absolute temperature in kelvin (body temperature ≈ 310 K).
> - **ΔS** (entropy): the change in how much freedom the molecule has, in
>   how many arrangements it could take. Folding removes freedom, so ΔS is
>   negative, which makes **−T·ΔS positive**: a cost that grows with
>   temperature.

Enthalpy is the glue pulling a formation together; entropy is everyone's urge
to wander off, and heat makes that urge stronger. This single equation
explains the two rules of thumb — **stacks lower the energy, loops raise it**
— and why heating melts structures.

Energies are computed with the **nearest-neighbour model**: the total is a sum
of local contributions (each stack of two adjacent pairs, each loop), looked
up from tables of experimentally measured values (the **Turner parameters**).
It's the same idea as estimating a chip's power by adding per-block numbers
from a characterised standard-cell library.

A worked example, and these are the actual numbers ViennaRNA prints for
`GGGAAACCC` folded as `(((...)))`:

```
stack (1,9) on (2,8)   -3.30
stack (2,8) on (3,7)   -3.30
hairpin loop, 3 nt     +5.40
                      -------
total                  -1.20 kcal/mol
```

Two G–C stacks pay for a 3-base loop, with 1.2 kcal/mol left over. Remove one
pair's worth of stacking and the sum goes positive, meaning the molecule would
rather stay unfolded. That's exactly what happens with `GGGACCC`, whose only
possible hairpin scores **+2.10**, so its predicted structure is `.......`
(unfolded, 0.00).

**A rule worth burning in:** always compare a candidate structure against
doing nothing. Unfolded scores 0, and any structure with positive ΔG loses to
it.

### 1.7 Finding the best structure: the Zuker algorithm

There are exponentially many legal structures for a given sequence, so they
can't be enumerated. But thanks to the no-crossing rule, the problem
decomposes, and **dynamic programming** (the **Zuker algorithm**) finds the
**minimum free energy (MFE)** structure in **O(N³)** time. The mental model
that fits best from your own coursework: static timing analysis never lists
every path through a circuit; it computes the worst arrival time at each node
once and reuses it.

**ViennaRNA** is the standard implementation, and it's our **oracle**: the
trusted external checker that scores the model's output, like a golden
reference model in verification. We use version **2.7.2**, pinned exactly in
`environment.yml` (decision **D-003**), because a different version could
produce different energies and silently change our results.

Three commands worth knowing:
- `RNAfold` — give it a sequence, get the MFE structure and its energy.
- `RNAeval` — give it a sequence **and** a structure, get that structure's
  energy; with `-v` it prints the per-loop breakdown shown above.
- `RNAsubopt -e X` — list every structure within X kcal/mol of the best, i.e.
  the **rivals**.

### 1.8 Beyond the MFE: the ensemble, and why "best" isn't "certain"

The MFE structure is the single most likely shape, but a real molecule does
not sit in it permanently. It spends time in *every* possible structure,
weighted by energy, according to the **Boltzmann distribution**:

> **probability ∝ e^(−ΔG / RT)**
>
> with R = 0.001987 kcal/(mol·K), and **RT ≈ 0.616 kcal/mol at 37 °C**, which
> is the scale of thermal noise.

Consequently, for two structures, the ratio of time spent in them is
e^(gap/RT) = **10^(gap/1.42)**:

> **Every ≈1.42 kcal/mol of energy gap buys a 10× preference.**

If that feels familiar, it should: it's the same physics as a MOSFET's
subthreshold swing of ≈60 mV/decade at room temperature, which is thermal
energy × ln 10 per decade. The energy gap between the intended structure and
its nearest rival is a **noise margin**.

Summing e^(−ΔG/RT) over *all* structures gives the **partition function**,
and ViennaRNA computes it exactly (`RNAfold -p`), again by dynamic
programming. The useful output is the **fraction of time the molecule spends
in its MFE shape**.

Here is where Phase 0 produced its most important result. `GGGAAACCC` is the
textbook hairpin, and it *does* fold to the intended target:

```
RNAsubopt -e 4 -s  on GGGAAACCC:
  (((...)))   -1.20     ← the target
  ((....)).   -1.00     ← a rival, only 0.20 kcal/mol away
  .........    0.00     ← unfolded
  .((....))   +0.80
  ((.....))   +0.90
  .((...)).   +1.10
  ...
RNAfold -p:  frequency of MFE structure in ensemble = 0.5065
```

**The intended shape holds only 50.7 % of the time.** A gap of 0.2 kcal/mol
is roughly a coin flip, just as the 1.42 rule predicts. Verified by hand:
summing e^(−ΔG/0.6163) over the eight structures above gives 7.01/13.80 =
50.8 %, matching ViennaRNA's 50.65 %.

**So an "MFE equals target" test can pass while the design is barely
functional.** That single observation shapes how Phase 3 must be designed.

### 1.9 Temperature: the second effect people forget

Raising the temperature does **two** separate things, and the second one is
the bigger one.

1. **Thermal noise grows.** RT·ln 10 rises from 1.42 kcal/mol per decade at
   37 °C to about 1.57 at 70 °C, so the same energy gap buys a smaller
   preference (a 2.84 gap gives ≈65× instead of 100×).
2. **The energies themselves change**, because of the −T·ΔS term. Stacks get
   weaker and loops get costlier, so structures **melt**.

Measured on our hairpin:

| | 37 °C | 70 °C |
|---|---|---|
| each G–C/G–C stack | −3.30 | **−2.22** |
| 3-nt hairpin loop | +5.40 | **+5.83** |
| total for `(((...)))` | −1.20 | **+1.39** |
| predicted MFE | `(((...)))` | `.........` (unfolded) |

We can go further and recover the underlying ΔH and ΔS from just those two
temperatures, by fitting ΔG = ΔH − T·ΔS through the two points:

- **G–C/G–C stack:** ΔS = **−32.7 cal/(mol·K)**, ΔH = **−13.45 kcal/mol**.
  Both negative. The large favourable bond term pays for the lost freedom,
  which is why stacking is worth doing at all. (Turner's measured enthalpy for
  this stack is ≈ −13.3 kcal/mol, so the fit is right.)
- **3-nt hairpin loop:** ΔS = **−13.0 cal/(mol·K)**, ΔH = **+1.36 kcal/mol**,
  which is almost nothing. **A loop's cost is essentially pure entropy**, with
  no compensating bond energy — which is exactly why heat punishes loops.

Note that **both** entropies are negative. Anything that orders the molecule
removes freedom; the difference between a stack and a loop is the enthalpy,
not the sign of the entropy. Cross-check: predicting the 50 °C values from
that fit gives stack −2.87 and loop +5.57, total −0.17, and ViennaRNA returns
exactly −2.87, +5.57, −0.17.

### 1.10 What the oracle is, and what it is not

Keep this distinction sharp, because interviewers probe it:

- ViennaRNA's prediction is **a model's output**, not the truth. It uses
  measured parameters with real uncertainty, assumes standard salt and
  temperature conditions, ignores pseudoknots, ignores 3D contacts, and
  ignores the possibility that the molecule never reaches equilibrium in a
  cell.
- Folding is **fast** (milliseconds for short sequences). The limitation is
  accuracy, not speed. Saying "checking with software takes too long" would
  be wrong.
- Therefore, when this project reports success, it means **"ViennaRNA
  predicts the target structure"**, never "this molecule folds that way in a
  test tube". There is no wet-lab validation in this work.
- A further risk to name unprompted: a model that is *steered* by the oracle
  can learn to exploit the oracle's mistakes. Adversarial pressure on an
  imperfect scorer is a real failure mode, relevant to Phases 3 and 5.

---

## Part 2 — Why designing RNA is hard  *(Phase 0)*

### 2.1 Two directions: simulation versus synthesis

- **Folding** (sequence → structure) is the **forward** problem. One dynamic
  programming run. Solved well enough to use as a tool. This is simulation:
  given the circuit, compute the behaviour.
- **Design**, also called **inverse folding** (structure → sequence), is the
  **inverse** problem: given a target shape, find sequences that fold into
  it. This is synthesis: given a spec, produce a circuit that meets it.

Everyone's intuition is that if the forward problem is easy, the inverse must
be easy too. It isn't, and the rest of Part 2 is the reason why. This is the
problem RiboMamba attacks.

### 2.2 The search space is absurd

For length N there are **4^N** possible sequences. For a modest N = 50:

> 4^50 ≈ 1.3 × 10³⁰ sequences. At a billion foldings per second, checking them
> all takes about 10²¹ seconds, which is roughly **3,000 times the age of the
> universe**.

Quote the number, not just "a lot": it's far more convincing. Exhaustive
search is off the table forever, for any interesting length.

### 2.3 The landscape is rugged: one letter can change everything

The obvious fix is local search: start somewhere, change one letter, refold,
keep the change if the structure got closer to the target. This is what
classical tools like **RNAinverse** do. Two things go wrong.

**(a) The "closer?" signal is jumpy and untrustworthy.** We saw this
concretely. `GGGAAACCC` folds to the target `(((...)))` at −1.20. Change the
final C to A, giving `GGGAAACCA`, and the target is unreachable, because
position 1 can no longer pair with position 9. But the sequence does not
simply unfold, which is what our hand-made model predicted. ViennaRNA says:

```
GGGAAACCA
((....)).   -1.90 kcal/mol      ← and it holds this shape 93.9 % of the time
```

**The entire pairing slid over by one position** (G1–C8, G2–C7) and closed a
4-base loop instead of a 3-base loop. Two energy terms our simplified hand
model had omitted are responsible:

- a **dangling end** (−1.70): the leftover A9 sits next to the end of the
  helix and stacks onto it. Not paired, but stabilising. Like a loose coin
  resting on top of a stack of coins.
- a **terminal mismatch**: in loops of 4 or more, the first unpaired bases
  stack onto the closing pair and earn a bonus (G·A is especially good), so
  the 4-base loop costs only **+3.10** versus **+5.40** for a 3-base loop,
  which is too tight to get the bonus. Sometimes a slightly *wider* bend
  seats better.

So a single mutation produced a *different, more stable, more reliable*
structure. A search method that assumes small edits cause small effects is
working against the physics.

**(b) Local minima.** Suppose a design needs a G–C pair flipped to C–G. That
requires changing two letters at once, and every single-letter route passes
through a broken pair (C–C or G–G) that scores worse. A method that only
accepts improvements rejects every path there and gets stuck. Picture a ball
in a shallow dip, unable to reach the deep valley beyond the next ridge.
Classical tools patch this — mutating paired positions together, or
occasionally accepting worse moves as in **simulated annealing** (heat the
metal so atoms can escape bad arrangements, then cool slowly) — but the
patches are partial, and every new target still starts from zero.

### 2.4 Being the best isn't enough: the margin matters

This is the point most people miss, and Phase 0 gave us a memorable example.
For a design to be *useful*, its target must not merely be the lowest-energy
structure; it must win **by a margin** larger than thermal noise. Otherwise
the molecule flickers between shapes and does its job only part of the time.

Our own "textbook" design `GGGAAACCC` fails this test: its nearest rival is
0.2 kcal/mol away and it occupies the target just **50.7 %** of the time,
while the "broken" mutant `GGGAAACCA` sits in *its* structure **93.9 %** of
the time. By an MFE-match criterion, the first is a success and the second is
a failure. By any sensible physical criterion, the second molecule is the far
better-behaved one.

**Consequence for our evaluation, and this is a genuine interview answer:** a
metric that only asks "does the predicted MFE equal the target?" rewards
flimsy designs. A model producing many barely-stable 50 % designs would score
*higher* than a model producing fewer, rock-solid 95 % designs. Since the
entire point of this project is a fair comparison between architectures, a
metric that rewards the wrong thing doesn't just mis-score one sequence — **it
can reverse the headline conclusion.** So Phase 3 must also consider the
target's probability in the Boltzmann ensemble, or the energy gap to the
nearest rival.

### 2.5 The answer is a set, not a point

For a given target structure there may be many valid sequences, or none. We
want **many diverse** ones, for two reasons: a biologist needs alternatives to
test, and diversity is the honest way to show a generative model hasn't simply
memorised one answer. Classical local search returns one sequence per run and
learns nothing transferable between runs.

### 2.6 Why a generative model instead

A **generative model** learns the distribution of its training data: which
sequences look like real RNA and which don't. Once trained, you can sample
from it repeatedly and cheaply, producing many candidates, each of which the
oracle folds and checks.

The contrast with search, in one line: **local search starts from zero for
every new target; a trained model carries what it learned from all of nature
into every new target.** It's the difference between an experienced designer
who has seen thousands of circuits and can propose plausible ones on demand,
versus random trial and error with a simulator in the loop.

Note carefully what flows where, because this is easy to garble under
pressure:

```
   target structure ──▶ [ model ] ──▶ candidate SEQUENCES
                                            │
                                            ▼
                                     [ ViennaRNA oracle ]
                                            │
                                            ▼
                              predicted structure for each
                                            │
                                            ▼
                    compare with the target: does it MATCH?
```

**The model outputs sequences. The oracle outputs structures.** The model
never folds anything. And the test is not "is the result a valid structure" —
every sequence folds into *some* valid structure, even the unfolded one. The
test is "does the predicted structure **match the target**".

### 2.7 What Phase 0 settled, and what it left open

**Settled:**
- We work with nested secondary structures predicted by ViennaRNA 2.7.2, no
  pseudoknots, no 3D (D-001, D-003).
- "Designability" will mean the oracle's prediction matching the target, and
  it needs a companion measure of *how dominant* the target is.
- Our tooling lives in Linux (WSL2) with a conda environment rebuildable from
  one file, and the repository is backed up to GitHub, because during Phase 0
  a disk cleanup destroyed an entire Linux installation (D-002, D-003).

**Left open, honestly:**
- We have not yet looked at real RNA data, only hand-made nine-letter
  examples. Everything above about margins and rugged landscapes needs
  re-checking at realistic lengths (Phase 1 onward).
- No metric thresholds are frozen yet. That happens in Phase 3, *before* any
  test-set numbers are seen (CLAUDE.md §3.5).
- Whether an energy-gap or ensemble-probability criterion is practical to
  compute at our scale is an open question: `RNAfold -p` costs more than
  plain MFE folding, and we will fold tens of thousands of sequences.

---

## Part 3 — The data, and how we kept the test set honest  *(Phase 1)*

### 3.1 What this phase is for

A generative model knows only what its examples show it. Phase 1 settles
three questions, and the third is the one that decides whether any later
number means anything:

1. **Which examples** the model learns from.
2. **In what form** it sees them: numbers, not letters.
3. **How we hold some back** so the final exam is honest.

Get the third one wrong and every result in Phases 2–5 is inflated, and
nobody can tell by looking at the numbers.

### 3.2 RNA families: why relatives are the whole problem

Take one useful RNA, say the **tRNA** that every cell uses while building
proteins. Over billions of years that RNA was copied into every branch of
life, and each copy accumulated mutations. Today the human and bacterial
versions differ at many positions, yet both still fold into the same
cloverleaf and do the same job. Any copy that stopped folding correctly
stopped working, and the organism carrying it lost out. **Evolution let the
letters drift and held the shape fixed.**

A set of such relatives is an **RNA family**: different letters, same
structure, same function, common ancestor. In chip terms, it's the same
schematic taped out by many fabs over decades, every layout different.

How can letters change while a stem survives? **Covariation.** Suppose a stem
contains a G–C pair. A mutation turns the G into an A, and the pair breaks.
If a second mutation later turns the partner C into a U, the pair is back,
now as A–U. Two letters changed, the structure didn't:

```
ancestor      ...G...........C...     G–C pair
species X     ...A...........U...     A–U pair   ← both sides changed, pair kept
```

This matters twice over. Family members can end up sharing only 50–60 % of
their letters while having the same shape. So "these two sequences look
different" doesn't mean "these two RNAs are unrelated", and that's exactly
the trap in §3.7.

Families that are themselves related, such as the bacterial and eukaryotic
versions of one RNA that Rfam curates separately, are grouped into a **clan**.

### 3.3 The two databases, and what's actually in them

**Rfam** is the standard catalogue of RNA families. For each family, experts
hand-align a small **seed** set of members and annotate their shared
structure. From the seed, Rfam builds a **covariance model**, a statistical
model of the family's letters *and* its base pairs, and scans whole genomes
with it. Every hit above a threshold becomes a **full** member. The copy on
HuggingFace (`multimolecule/rfam`) is those full members: sequence, family
name, clan, and a description of the genome it came from. Three things to
know about it:
- it has **no per-sequence structure**;
- it uses **DNA letters** (T instead of U), because the hits were cut out of
  genome DNA;
- its members are found by a model, so a few are mislabelled or are
  **fragments**, partial copies cut off where a sequenced piece of genome
  ended.

**bpRNA-1m** is 102,318 RNAs *with* structures, pooled from seven
databases, but *without* family labels. About a fifth of its structures
(21.4 %) contain pseudoknots. It has a famous history. Its TS0 test split
was built by removing test sequences more than 80 % identical to training
ones. Later, bpRNA-new was assembled from Rfam families that didn't exist
when the training data was collected, so it's guaranteed family-disjoint.
Published deep-learning structure predictors that scored well on TS0
dropped sharply on bpRNA-new (reported in the MXfold2 paper, Sato et al.
2021, and by Szikszai et al. 2022, *"Deep learning models for RNA secondary
structure prediction (probably) do not generalize across families"*; verify
both before citing formally). The 80 % identity filter hadn't stopped
family leakage, and a family-disjoint test exposed it.

**Our choice (D-005):** train on Rfam, because its family and clan labels
are what make an honest split possible. bpRNA can't be split by family at
all. We download bpRNA too and characterise it; whether it supplies target
structures for evaluation is a Phase 3 decision. Both downloads are pinned to
an exact repository commit and checked against a SHA-256 checksum, so the
same bytes arrive on every machine, forever.

### 3.4 The surprise: Rfam, twice

The first thing the exploration script printed was odd. The largest "family"
wasn't tRNA; it was one called **"No such family"**, with **10,025,911**
members, exactly half of the 20,051,822 rows. Investigation showed that the
second half of the file is the first half again, with identical ids and
identical sequences, but with the family label replaced by that placeholder.
We checked every one of the ten million placeholder rows: each has a twin in
the labelled half, and not one differs in sequence.

Why this matters so much is the best single story from this phase. Dropping
the placeholder rows loses nothing. **Keeping** them would have been
catastrophic in a way that's invisible if you only look at labels. "No such
family" would have been treated as one enormous family, containing a copy of
*every* real family. A family-aware split would put that pseudo-family
wholly into one split, say test, and then **test would contain an exact
copy of every training sequence.** The split would look perfectly
family-disjoint on paper and be 100 % leaky in reality.

Two lessons worth saying out loud: measure data before trusting it, and
audit leakage with the *sequences* themselves, not just the labels, because
labels can lie.

### 3.5 Cleaning, with the numbers behind every threshold

Every threshold was set from a measured number (`scripts/explore_data.py`),
not picked in advance:

| Step | Rows after | Why |
|---|---|---|
| raw download | 20,051,822 | |
| drop the "No such family" copy | 10,025,911 | §3.4 |
| T → U; only A/C/G/U | 9,981,218 | 0.45 % contained `N` or other "unsure" letters; a generator must never learn to emit "unknown" |
| drop families whose median length > 256 | 9,590,462 | long RNAs; see §3.6 |
| drop single sequences > 256 | 9,547,361 | |
| drop members < half their family's median | 9,534,330 | likely fragments |
| remove exact duplicates within a family | 5,730,590 | 3.8 M copies, mostly of multi-copy genes |
| drop sequences filed under >1 family | 5,730,554 | ambiguous label, could straddle splits |
| keep ≤ 1,000 per family (seeded random draw) | **567,579** | tRNA alone had 5.3 M members |

Two of these deserve a sentence each, because they're where a careless
pipeline goes wrong.

**The length rule acts on families first.** Of the sequences under 256 nt,
83,525 belonged to families whose typical member is far longer: pieces of
ribosomal RNA, which is 1,500–3,000 nt in full. A plain "drop anything over
256" filter would keep those pieces as if they were whole molecules. So a
family is dropped whole if its *median* length exceeds 256, and only then are
individual long sequences removed.

**The per-family cap fixes imbalance.** The median family has 31 members;
tRNA has 5.3 million. Without a cap the model would mostly learn tRNA and 5S
rRNA. With a cap of 1,000, no family is more than 0.18 % of the data. Cap
100 was rejected because it throws away most of the variation inside large
families. The price: family frequencies in our data are not their natural
frequencies. The model learns what RNA families look like, not how common
each one is in genomes.

### 3.6 Why 256, and what it costs

Memory on the GPU during training holds four things. Weights, gradients and
the optimiser's running averages cost about 16 bytes per parameter, only
~0.2 GB for a model of 14 million parameters. The fourth thing,
**activations** (every intermediate result kept for the backward pass), grows
with batch size × length × width × layers. Naive attention, used by the
Transformer baseline, adds a term that grows with **length squared**. A rough
estimate for an 8-layer, width-384 Transformer at batch 64 is ~2.7 GB at
length 256, ~7.4 GB at 512, and ~23 GB at 1,024, on a card with 8 GB.
Doubling the length doubles one part of the bill and quadruples the other.

Two more reasons point the same way. The oracle folds in O(N³), so a
512-nt sequence costs about 8× more to check than a 256-nt one. And MFE
prediction is less reliable for long RNAs.

The honest cost: a cap of 256 keeps **95.4 %** of families. The 185 dropped
are the long RNAs: all ribosomal RNAs, 7SK, tmRNA, RNase P, group I
introns, plant SRP. We make no claims about designing those. And one
subtlety an interviewer may raise: Mamba's advantage is supposed to appear at
*long* lengths, so a 256 cap probably favours the Transformer. That makes our
comparison **conservative** for Mamba, which is the right direction to err in.

### 3.7 Leakage, and how the split prevents it

**Data leakage** means information about the test set reaches the model
during training, so test scores overstate its real ability. It's the exam
built from reworded homework problems.

For RNA the mechanism is families. Split randomly, sequence by sequence, and
almost every test sequence has siblings in training. The model can "design"
a test RNA's structure by recalling its relatives. We measured exactly how
bad this would be. For 2,000 randomly chosen test sequences under a random
split, we searched all training sequences with **MMseqs2**, a fast
sequence-search tool, and recorded the closest relative of each:

- **96.5 %** had a detectable relative in training;
- **90.3 %** had one at least 80 % identical;
- **56 %** had one at least 95 % identical;
- the median test sequence's closest training relative was **96 %** identical.

(These are from the final audit. An earlier run, on a slightly different
2,000-sequence sample, gave 89.6 % at ≥ 80 %: the same answer within the
±1.3-point sampling uncertainty.)

That test set would be a memory test.

**Our split** works on groups instead of sequences. The group is the clan,
or the family if it belongs to no clan. Groups are put in a pseudo-random
order (sorted by a SHA-256 hash of their name, which is identical on every
machine; Python's own `hash()` is deliberately randomised per run, so it
can't be used). Then whole groups fill test up to 10 % of the sequences,
then validation to 10 %, and the rest is training.

That alone wasn't airtight, and finding that was part of the job. Searching
every held-out sequence against training found **775 (0.68 %)** with a
≥ 80 %-identical relative, concentrated in 17 families. Rfam simply doesn't
link these families through a clan: SNORA52 and snopsi28S-1192 look like the
same snoRNA under two names, and mir-1285 derives from an SRP-like repeat.
So step 10 removes every held-out sequence with a ≥ 80 % identity / ≥ 80 %
coverage relative in training. Family labels catch low-identity relatives,
which is what identity filters miss (covariation, §3.2). The identity check
catches relatives the labels miss. **Each criterion covers the other's blind
spot.**

There's a third kind of relative that neither catches reliably: one whose
letters drifted far apart by covariation, but whose **structure** is still
recognisably the same family. The right detector for that is the one Rfam
itself uses to decide membership: its **covariance models** (§3.8b). Step 11
scans every held-out sequence with them and removes any that Rfam would call
a member of a *training* family. It found 12.

The final split: **452,867 / 57,052 / 56,873** sequences, **3,032 / 406 /
399** families. Rerunning the whole pipeline produces byte-identical files.

### 3.8 The audit, and what its numbers mean

`scripts/audit_leakage.py` runs four letter-based checks, and
`scripts/audit_structural.py` runs the structure-based ones (§3.8b). The
full tables are in `RESULTS.md`.

1. **No clan and no family appears in two splits.** Also enforced by an
   assertion: the preparation script refuses to write a split that violates it.
2. **No identical sequence appears in two splits.**
3. **Nearest training relative of held-out sequences**, with the random
   split as a **control**:

| | any detectable relative | ≥ 50 % identical | ≥ 80 % identical |
|---|---|---|---|
| our split, test | 1.05 % | 0.40 % | 0 (by construction) |
| random split, test | 96.5 % | 93.3 % | 90.3 % |

   Read it carefully. The ≥ 80 % column is zero *because step 10 removed
   those sequences with the same search*, so it isn't independent evidence.
   The informative columns are the lower ones: 99 % of our test sequences
   have **no detectable sequence relative in training at all**. The control
   row turns "a random split would leak" from a claim into a measured number.
4. **bpRNA overlap:** 17,086 bpRNA sequences appear letter for letter in our
   training set. If bpRNA structures ever become design targets, they must
   be screened against training first.

Each proportion comes from 2,000 samples, so it carries a 95 % confidence
interval of roughly ±1–2 percentage points for the large values. That's why
the table in `RESULTS.md` prints "90.3 % ± 1.3".

### 3.8b The structure-aware audit: asking Rfam's own models

**The idea.** A covariance model (CM) is Rfam's statistical description of
one family. It scores single positions ("position 12 is usually G"), but
also *pairs* of positions that must base-pair ("positions 3 and 20 must be
complementary, whatever the letters"). So a relative that swapped G–C for
A–U still fits perfectly. Scoring a sequence against a family's CM gives a
**bit score**: how much more likely the sequence is as a family member than
as random RNA. Each family has a curator-set pass mark, the **gathering (GA)
threshold**, and Rfam's member lists are exactly the hits at or above it.
So "scores ≥ GA against family F" means **"Rfam would call this a member of
F"**. That's our definition of structural leakage.

**The scan.** Infernal's `cmscan` scored all 113,937 held-out sequences
against all 4,178 models of Rfam 15.0 (the release our data came from),
using the flags Rfam itself uses. It took about two hours on the laptop's 20
threads. Twelve held-out sequences scored as members of a training family,
almost all snoRNAs, which step 11 then removed.

**A mistake worth telling.** The first scan omitted one flag,
`--nohmmonly`. 347 Rfam models have *no* base pairs, and for those `cmscan`
quietly switches to a cheaper letters-only scoring whose bit scores aren't
on the scale the GA thresholds were set on. The positive control (below)
exposed it: sequences from zero-pair families found their own family only
**87.9 %** of the time. With the flag: **99.99 %**, while families with pairs
stayed at 99.54 %. The fix was to add the flag and rescan everything. The
lesson: a control that looks slightly off is worth chasing, because that's
how the detector tells you it's broken.

**Why the controls matter.** A report of "zero leakage found" is only as
good as the detector.
- The **positive control** tests it where the answer is known to be *yes*:
  every held-out sequence belongs to its own family, so its own family's
  model should find it. It did, for **99.55 %** of all 113,925 held-out
  sequences, so the detector can see.
- The **negative control** tests it where the answer is known to be *no*:
  each sequence's letters are shuffled, keeping which letter follows which,
  so the result looks like RNA but belongs to no family. Any hits are false
  alarms, and their rate is the noise floor.

The final numbers:

| | result |
|---|---|
| held-out sequences that are *members* of a training family | **0** (after step 11 removed 12) |
| same check with Infernal's slower, more sensitive filters (2,000 sample) | **0** |
| held-out sequences *weakly* resembling some training family | 4.6 % |
| shuffled sequences weakly resembling some training family (noise floor) | **0.1 %** |

The noise floor is what makes the 4.6 % readable: it's about 45 times what
chance produces, so the resemblance is real. But it's below the membership
threshold, and mostly "the same *kind* of RNA", e.g. every microRNA
precursor is a ~70-nt hairpin. It isn't leakage, because a model *should*
be able to use what it learned about hairpins on a new family, and no split
could remove it anyway.

One statistical footnote worth knowing: "0 hits in 2,000" does **not** mean
the true rate is exactly zero. The **rule of three** says that with zero
events in n trials, the true rate is below about 3/n with 95 % confidence,
so here below 0.15 %.

### 3.9 Turning letters into batches

**Tokenisation.** A network does arithmetic, so each nucleotide becomes an
integer. We use one token per nucleotide, with a fixed vocabulary:

```
id:     0      1       2      3      4  5  6  7
token:  <pad>  <mask>  <bos>  <eos>  A  C  G  U

"GGGAAACCC"  →  [6, 6, 6, 4, 4, 4, 5, 5, 5]
```

`<mask>` is the "hidden letter" symbol that masked diffusion is built on
(Part 4). `<bos>`/`<eos>` ("begin"/"end") are for the autoregressive
baseline in Phase 4, which writes left to right and has to know where to
start and when it's done. They're reserved now so all three compared models
share one vocabulary, and therefore one embedding table of exactly the same
size. The ids are frozen by a test, because renumbering them would silently
scramble every saved model. Bigger tokens (3-letter "k-mers", or the learned
word pieces LLMs use) were rejected: base pairs and diffusion masking both act
on single nucleotides, and a 3-letter token can sit half in a stem and half
in a loop.

**Batches and padding.** The GPU processes a **batch** of B sequences as one
rectangle of shape `(B, L)`, like a vector unit whose lanes all have the same
width. Real sequences differ in length, so shorter ones are **padded** with
`<pad>`, and an **attention mask** of the same shape records which positions
are real (1) and which are filler (0):

```
input_ids       = [[6,6,6,4,4,4,5,5,5],
                   [4,5,6,7,0,0,0,0,0]]        (B=2, L=9)
attention_mask  = [[1,1,1,1,1,1,1,1,1],
                   [1,1,1,1,0,0,0,0,0]]
```

Without the mask, the model would treat filler as RNA and the loss would
reward predicting filler. Beware the word "mask": it means three different
things in this project. There's the **padding mask** above, the **`<mask>`
token** of diffusion, and **masking** as an operation (overwriting chosen
entries of a tensor). Interviewers notice when you keep them apart.

**Padding is wasted compute**, and we measured how much. With batches of 64
drawn at random from our training set, **54.4 %** of all positions were
padding. The GPU spent more than half its effort multiplying filler. The fix
is **length bucketing**: shuffle, cut the data into pools of 100 batches,
sort each pool by length, cut it into batches, then shuffle the order of the
batches. Similar lengths travel together, while batches stay random from
epoch to epoch. Padding fell to **1.1 %**, making each epoch roughly 2.2×
cheaper.

Two implementation details worth being able to explain:
- The training set is stored as **one flat array of 47.7 million bytes**
  plus an array of start positions, not as 452,867 separate objects. It
  loads in 0.3 s and is cheap to share with background loader processes.
- Encoding uses a 256-entry **lookup table** (a ROM, in hardware terms) from
  byte value to token id, so a whole sequence converts in one step, and any
  letter outside A/C/G/U raises an error instead of becoming a wrong number.

### 3.10 What Phase 1 settled, and what it left open

**Settled:**
- Training corpus: Rfam, pinned and checksummed; 566,792 sequences after
  cleaning and both leakage filters.
- A clan/family split, audited at two levels. By letters (MMseqs2), the
  control shows a random split would give 90 % of test sequences a
  near-twin in training. By structure (Rfam's covariance models), held-out
  sequences that Rfam would call members of a training family were found
  (12) and removed, with a positive control showing the detector finds
  99.55 % of true memberships.
- A frozen 8-token vocabulary, and a loader with 1.1 % padding waste.

**Left open, honestly:**
- The structure-aware audit inherits Rfam's curation: it uses Rfam's GA
  thresholds, so a family whose threshold is set loosely or tightly makes
  the check correspondingly looser or stricter. Weak, sub-threshold
  resemblance between held-out and training families remains (class-level,
  e.g. hairpin-shaped microRNAs) and is reported, not removed.
- The test set is one random draw (seed 0). Which families land in test
  changes with the seed. The most famous RNA, tRNA, happens to sit in
  validation, not training. Repeating key results over several seeds is a
  Phase 3 decision.
- 185 long families (all ribosomal RNAs among them) are out of scope.
- The 256 cap probably favours the Transformer over Mamba; the comparison is
  conservative for Mamba.
- The VRAM figures are estimates; the real ones get measured in Phase 2.

## Part 4 — Generating instead of searching: masked discrete diffusion  *(Phase 2)*

*(Drafted during the Phase 2 build, 2026-09-24; §4.10 is completed when the
full training run finishes, and the section is revised after the Phase 2
gate.)*

### 4.1 What this phase is for

The scientific question compares backbones: does a Mamba denoiser beat a
Transformer one, when everything else is equal? That question only means
something if the Transformer is a **strong, standard, working** baseline,
built and debugged first. So Phase 2 builds the whole generative machinery
(the diffusion process, the loss, the sampler, the training loop) around a
conventional Transformer. Phase 4 then swaps out that one box.

### 4.2 What a generative model is, and why not left-to-right

A generative model is a probability distribution over sequences that you
can **sample** from. For RNA a lookup table is impossible (4¹⁰⁰ ≈ 10⁶⁰
entries for length 100), so the distribution must be computed by a network
from learnable pieces.

The GPT way is the **chain rule**: p(x) = p(x₁)·p(x₂|x₁)·…, written left to
right. It's exact in principle, but awkward for RNA:
- when the model writes position 1, its pairing partner (say position 9)
  doesn't exist yet, so pairing, which is two-directional and long-range,
  must be planned silently;
- filling in the middle of an existing design, or imposing a whole target
  structure, doesn't fit a left-to-right process;
- generation takes L sequential steps, and early mistakes can't be revised.

Say "awkward", never "impossible": that's why the autoregressive Mamba stays
in the Phase 4 comparison as an empirical test.

### 4.3 Masked diffusion

BERT-style models predict hidden letters from **both** sides, but only ever
see ~15 % hidden, so they can't generate from scratch. **Masked diffusion**
trains at every hiding level from 0 % to 100 %, then generates by starting
fully hidden and revealing letters step by step.

- **Forward process** (fixed): at time t ∈ (0, 1], each nucleotide is
  replaced by `<mask>` with probability t (linear schedule α_t = 1 − t).
- **Absorbing state**: once masked, a position stays masked in the forward
  process; once revealed during generation, a letter is never changed.
- **Why masking rather than other noise:** random letter swaps would plant
  wrong letters (and fake base pairs) that look like real ones; continuous
  noise on vectors fits letters badly. Masking says honestly "unknown here".
- **Reverse process (sampling):** start from `<bos> <mask>…<mask> <eos>`.
  Stepping from time t to s, each masked position is revealed with
  probability (t − s)/t, its letter drawn from the model's prediction. With
  4 steps the reveal probabilities are 1/4, 1/3, 1/2, 1, so about a quarter
  of the positions are revealed per step. **Few steps** means many letters
  are chosen at once, unable to see each other: two pairing partners
  revealed together can't coordinate. **Many steps** means each letter sees
  more already-written context: better, but slower.
- A subtle implementation detail worth knowing: letters are sampled from
  **float64** probabilities, because low-precision sampling has been shown
  to quietly sharpen the distribution and reduce diversity (Zheng et al. 2024).

### 4.4 The loss, and two exact checks on it

For each training sequence: pick t, mask, predict, and score
**cross-entropy only at the masked positions, weighted by 1/t**:

> Loss = average over t and masks of (1/t) · Σ_{masked i} −log p_θ(x_i | z_t)

- Cross-entropy −log p is 0 for a certain, correct prediction and large for
  a confident mistake.
- Only masked positions count: the rest are given in the input, and
  predicting them would reward copying. That's the same lesson as padding.
- The **1/t** weight: about t·L positions are masked, so the sum is about
  t·L × (average loss per blank); multiplying by 1/t leaves L × (average),
  whatever t was, so every noise level counts equally. Formally, exactly
  this weighting makes the loss an **upper bound on −log p(x)** (a negative
  ELBO), so it can be reported as a likelihood: **bits per nucleotide**. 2.0
  bits means knowing nothing about four letters.

Two tests pin this down exactly, and they're worth quoting:
1. A hand-worked example (`GGGAAACCC`, t = 1/3, masks at positions 2, 5, 9,
   predicted probabilities 0.6, 0.5, 0.9) must give 3·(0.511 + 0.693 +
   0.105) = **3.928 nats = 0.630 bits/nt**. It does.
2. A model that knows nothing (equal odds on A, C, G, U) must score
   **exactly 2 bits** on average. That only happens if the 1/t weighting is
   right: each masked position costs ln 4, about t·L are masked, and 1/t
   cancels the t. It does (2.00 within 0.03 over 40 batches).

### 4.5 The Transformer denoiser

The denoiser takes the partly masked sequence and returns, for every
position, scores over the 8 tokens. The 4 special tokens are forced to −∞,
so only A/C/G/U can ever be predicted. Shapes: (B, L) ids → embedding
(B, L, d) → N blocks → (B, L, 8).

**Attention** lets each position gather information from every other. Each
position makes a query, a key and a value. The scores q·k/√d_h go through
softmax into weights summing to 1, and the output is the weighted sum of
values. Worked numbers: scores 1, 0, 2 → ÷√2 → softmax → weights 0.284,
0.140, 0.576 → output [2.012, 0.564]. The √d_h keeps scores from
saturating the softmax. The L × L grid of scores has the shape of a
base-pairing matrix: attention can connect position i straight to its
partner j in one step. Mamba has no such grid; that's the scientific
question of Phase 4. PyTorch's fused attention computes it in tiles without
storing the grid, so memory grows roughly linearly with L (compute is still
quadratic).

**Rotary position encoding (RoPE)**: pairs of numbers in q and k are
treated as phasors and rotated by an angle proportional to position; the
score then depends only on the offset m − n, because e^{jmθ}·conj(e^{jnθ})
= e^{j(m−n)θ}. It has no parameters (clean parameter matching with Mamba) and
treats a motif the same wherever it sits.

**Block** (pre-norm): x + Attention(LayerNorm(x)), then x + MLP(LayerNorm(x)).
LayerNorm is per-position standardisation (like automatic gain control);
the MLP (d → 4d → GELU → d) is per-position "thinking"; the residual "+" is a
bypass that lets gradients through deep stacks. About 12d² parameters per
block: d = 384 and 8 blocks gives **14,174,976** parameters (tested against
the formula).

### 4.6 A real design flaw, found by a test: position blindness

The standard sanity check, "can a tiny model memorise four sequences?",
**failed**. Reasoning from the maths found the cause. If every position
holds `<mask>`, every position has the same vector, so every value vector
is the same, and any attention-weighted average of identical vectors is that
same vector: **every position gets an identical output**, whatever the
weights. RoPE only knows relative offsets, and padding is invisible to
attention, so the model had no way to know where the molecule starts or
ends. Measured per noise level: at t = 1 the model scored **2.11 bits**
(knowing nothing) without markers, and **1.58** (near the 1.6-bit optimum)
with them.

This matters exactly where generation begins (100 % masked), and RNA has
strongly end-dependent features: the two ends of a molecule often pair,
tRNAs end in CCA. The fix uses two tokens reserved back in Phase 1: every
sequence is framed **`<bos> … <eos>`**. The markers are never masked or
scored, and together with RoPE they give every position its distance from
both ends, at zero parameter cost. A permanent test now shows identical
outputs without markers and varied outputs with them (D-010).

The interview lesson: a failing sanity test was the *model* telling us
something true about the architecture, not a test to be loosened.

### 4.7 Training machinery, and what the GPU actually allows

**Measured, not assumed** (`scripts/measure_memory.py`). At a 16,384-token
batch the 14.2 M-parameter model needs 2.4 GB and processes about 105,000
nucleotides per second. Speed per nucleotide barely depends on sequence
length, so batches are sized by **nucleotides, not sequences** (median 140
sequences per batch, 0.9 % padding): every step costs the same.

A trap worth telling: a 38 M-parameter model at a 32k-token batch needed
9.05 GB of a card with 7.44 GB free. Under WSL there was **no out-of-memory
error**. The driver spilled into system RAM and each step took 6.2 s
instead of ~0.36 s. Silent slowdowns are worse than crashes, so we keep
headroom and log step time.

The recipe (D-011): AdamW (per-weight adaptive step sizes, weight decay on
matrices only); learning rate warmup, then cosine decay to 10 %; bf16 mixed
precision; gradient clipping at norm 1.0 (a limiter); an exponential moving
average of the weights (a low-pass filter; used for evaluation and
sampling); validation on all 57,052 held-out-family sequences with
**fixed** noise, so changes reflect the model, not the dice; atomic,
resumable checkpoints recording the git commit.

### 4.8 Choosing the learning rate honestly

The learning rate was chosen by a **sweep with a rule written in advance**:
three values, 8,000 steps each, lowest final validation bits/nt wins. The
same protocol will be applied to every backbone, so no architecture gets
more tuning than another.

Result: 3×10⁻⁴ → 1.914, 10⁻³ → 1.925, 3×10⁻³ → 1.944. The winner sat on
the **edge** of the grid, so the optimum might lie below it, and the
rule had no clause for that. So the protocol was **amended, openly and
before any other backbone was swept**: extend the grid while the winner is
on its edge. 10⁻⁴ scored 1.917, making 3×10⁻⁴ an interior winner. The two
differ by only 0.003 bits, so the choice isn't sensitive in that range.
Being able to say "our protocol had a gap, here's the dated amendment, and
here's why it can't favour either model" is a strong answer in its own right.

### 4.9 Is ~1.9 bits good? Reference points

A number needs a scale. Counting models (predict each letter from the
previous k letters, from training counts) give, on unseen families:
1.996 bits (k = 0, letter frequencies alone), falling to a best of
**1.966 (k = 4)**. Longer contexts get *worse* on validation while
improving on training: they memorise training k-mers that don't transfer to
new families. The Transformer beat the best of them after only 8,000 steps
(1.914), so it learns something beyond local statistics, most plausibly the
long-range pairing correlations that no left-context count can see.

And the control makes Phase 1's point on a model metric. On a **random**
split, the 8-letter counting model scores **1.817**, which would look
*better* than the Transformer, purely by recognising k-mers from the test
sequences' relatives in training. Under a leaky split, a trivial memoriser
appears to beat a neural network.

### 4.10 Training for real: overfitting, dropout, and the baseline

**The plan was wrong, and the validation curve said so.** The first "full"
run was planned for 200,000 steps (about 66 passes over the data).
Validation on unseen families was best at step **10,000 (1.902 bits)** and
then got steadily worse (1.935 by step 45,000), while training kept
improving (down to 1.41 bits). That's **overfitting**: the model began
memorising the training families instead of learning what transfers to new
ones. The run was stopped. Nothing was lost, since the best checkpoint is
always kept, and about seven hours of GPU time were saved.

**The standard remedy is dropout.** During training, a random fraction of
the network's internal signals is switched off at each step, so no single
memorised pathway can be relied on. It's off during evaluation. It was
tested with the same honesty as the learning rate: a rule written in
advance, dropout 0 / 0.1 / 0.2, 30,000 steps each on a fully decaying
schedule, best validation wins.

| dropout | best validation bits/nt | reached at step |
|---|---|---|
| **0** | **1.9040** | 10,000 |
| 0.1 | 1.9081 | 12,500 |
| 0.2 | 1.9178 | 12,500 |

**Dropout didn't help.** It slowed learning, but every run still peaked
after 3–4 passes and then declined. The floor of about **1.90 bits/nt** on
unseen families held across schedules and dropout rates. It looks like a
property of how much transfers *between* RNA families with this data and
model, not a tuning failure. The Phase 2 baseline is therefore the dropout-0
run at step 10,000 (**1.904**), chosen by the rule. We did *not* swap in the
long run's marginally better 1.902, because it came from a different
protocol, and the Mamba models must be given exactly the same one.

**What the baseline generates.** 1,000 sequences, compared with 1,000 real
validation sequences:
- **Novel**: none has even a 50 %-identical relative in training, so it
  isn't copying.
- **Realistic composition**: GC content 0.46 against 0.48.
- **But barely more structured than chance.** Real RNA folds more stably
  than a letter-shuffled version of itself (keeping neighbour statistics)
  **79 %** of the time. The generated sequences manage **55 %**, against 50 %
  for pure chance. On average real RNA beats its shuffle by 7 kcal/mol, the
  generated sequences by 0.6.

So the baseline has learned what RNA *letters* look like far better than
how RNA *folds*. That's consistent with its modest gain over the counting
models (1.904 vs 1.966), and it's the most important finding to carry
forward.

### 4.11 What Phase 2 settles, and what it leaves open

**Settled:**
- A working masked-diffusion pipeline (forward masking, 1/t-weighted loss,
  sampler), verified by exact tests: the hand-worked loss example, and the
  2-bit "knows nothing" check.
- A standard Transformer denoiser behind a backbone-agnostic interface,
  with `<bos>`/`<eos>` framing (D-010), which fixes a measured
  position-blindness problem.
- A tuning protocol with rules fixed in advance (learning rate, then
  dropout), which every Phase 4 backbone gets identically.
- The baseline: 14.2 M parameters, **1.904 bits/nt** on unseen families,
  against a best counting model of 1.966 and a know-nothing 2.000.

**Left open, honestly:**
- **Generated RNA is barely more structured than chance (55 % vs real
  79 %).** Phase 3 must measure this properly (with confidence intervals,
  sampling temperature and step count). Phase 4 asks whether a Mamba
  backbone captures pairing better. Phase 5's structure conditioning may be
  essential for design.
- Overfitting after ~3 passes, and the ≈ 1.90 floor. Larger models, other
  regularisers and more data per family were not tried; the limiting factor
  seems to be the number of distinct families.
- One seed so far. Differences of a few thousandths of a bit (e.g. 1.9020 vs
  1.9040) are within run-to-run noise until seeds say otherwise.
- The diffusion loss is an upper bound on the true likelihood, so the true
  bits/nt may be somewhat lower.

### 4.12 Easy mix-ups (from the Phase 2 quiz; reread these)

- **Nats vs bits.** −ln(0.25) = **1.386 nats**; −log₂(0.25) = **2 bits**.
  Same quantity, different log base; divide nats by ln 2 ≈ 0.693 to get
  bits. "Knows nothing" is 2 bits = 1.386 nats per nucleotide.
- **Dropout did *not* fix the overfitting.** All three settings peaked after
  about 3 passes; the rule chose dropout 0. What protects the baseline is
  **early stopping**: we keep the best checkpoint (step 10,000), not the
  last.
- **Why validation gets *worse* on unseen families:** what the model
  memorises is family-specific (particular letter chunks) and none of it
  transfers to a new family. The 8-letter counting model does the same:
  2.08 bits, worse than guessing, because confident wrong predictions cost
  more than uniform guesses (the penalty −ln p grows without bound as p → 0).
- **A counting model** (k-th order Markov) just counts, in the training
  data, which letter follows each k-letter context, and predicts with those
  frequencies. k = 4 captures RNA's general local habits; k = 8 memorises
  families.
- **"More stable than its own shuffle" reads on a scale from 50 % to 79 %.**
  Random letters: 50 % (a sequence and its shuffle are both random
  arrangements, a coin flip). Real RNA: 79 % (evolution arranged the
  letters to pair). Our baseline: 55 %, so novel but barely structured.
  Copies of training RNA would score ~79 % *and* show training relatives;
  the other sanity number (0 % relatives) rules copying out.
- **Mamba is not blind to the right-hand side.** Plain Mamba scans left to
  right; **BiMamba also scans right to left**, so it sees both sides, but
  through a compressed running summary rather than attention's direct
  i → j lookup. That difference is the Phase 4 question.
- **A fair backbone comparison** keeps identical: the diffusion process,
  data and split, tokenisation, **parameter count, compute (steps/tokens),
  tuning protocol and evaluation**. Then any difference can only come
  from the backbone.
- **Why a winner on the edge of a sweep isn't final:** the optimum may lie
  beyond the edge, so test the next value. **Why adding that rule late was
  legitimate:** it's mechanical, identical for every backbone, added before
  any other backbone was tuned, recorded with its date, and it only touched
  validation-based tuning, never the test set.

## Part 5 — How we evaluated honestly  *(Phase 3)*

*(Drafted during the Phase 3 build, 2026-09-24. The sampling ablation's
results and the frozen protocol are added when they exist; the section is
revised after the Phase 3 gate.)*

### 5.1 What this phase is for

By the end of Phase 2 we had a model that generates RNA and one worrying
number: its samples beat their own shuffles only 55 % of the time, against
79 % for real RNA. Before building anything else, we need an evaluation we
can trust, because Phase 4's entire question ("is Mamba better?") will be
answered by it. An evaluation that can be fooled will be fooled, usually
by accident, and usually in the direction the researcher hopes for.

So Phase 3 builds the **harness** (the code that scores generated RNA),
measures what real RNA scores on it, and writes down, in advance, exactly
how the final comparison will be run. Only then is the test set unlocked.

### 5.2 A testbench the design didn't write

In chip design you would never let the design under test write its own
testbench, and a testbench written *after* looking at which vectors pass
is worthless. An evaluation is a testbench for a model. It is honest if:
it measures what we care about; it has a scale (reference points above and
below); a trivial cheat can't win it; it comes with error bars; it was
fixed before the results; and it doesn't hinge on one instrument's quirks.

The most useful question to ask of any metric is: **what is the dumbest
generator that would score well on it?**

| metric | the trivial cheat that wins it |
|---|---|
| low MFE ("stable") | GC-rich random letters |
| novelty (unlike training) | random letters |
| diversity | random letters |
| "folds well" | copying training sequences |
| realistic letter statistics | a 4-letter counting model |
| MFE = target | flimsy designs that hold the target half the time |
| a metric chosen after seeing results | whichever model you prefer |
| one oracle as judge | a model that learns the oracle's quirks |

No metric is honest alone. They are chosen so that each covers another's
blind spot, exactly like the three leakage checks of Phase 1.

### 5.3 Two settings

The harness serves two situations. In the **unconditional** setting
(Phases 2 and 4) the model receives no target; it should produce good RNA,
and each sample's *own* MFE structure plays the role of the target. In the
**design** setting (Phase 5) the model receives a target structure and must
produce sequences that fold into it. Both use the same metrics; only the
reference structure differs.

### 5.4 From "does it fold?" to "how firmly?"

The field's standard design test is **MFE match**: does the oracle's
predicted structure equal the target? It is pass/fail, like "slack ≥ 0" in
timing, and Phase 0 showed its flaw: `GGGAAACCC` passes while holding its
target only 50.7 % of the time. Worse, it can reverse a comparison: a model
with many flimsy passes beats a model with fewer rock-solid ones.

The fix is to look at the whole **ensemble**, the Boltzmann distribution
over all structures from Phase 0. The obvious measure is the probability of
the exact target, P(target) = e^(−ΔG/RT)/Z. On nine-letter hairpins it works
beautifully (0.507 vs 0.939). But on real RNA it collapses. We measured six
real validation RNAs of 74–223 nucleotides: the probability of each one's
exact MFE structure was between 0.000 and 0.069, and the "nearest rival"
was, in five of six, the same structure with one end pair frayed, at an
energy difference of 0.00 kcal/mol. With a hundred nucleotides there are
thousands of near-copies of any structure, and the probability spreads
across them.

The analogy that makes this click comes from communications. P(target) is
a **frame error rate**: the chance that every bit of a packet is right. If
each of 100 nucleotides is independently right 98 % of the time, the whole
frame is right only 0.98¹⁰⁰ ≈ 13 % of the time, though the molecule is 98 %
correct. What we want is a **bit error rate**. That is the **ensemble
defect**: the expected number of nucleotides in the wrong state (paired to
the wrong partner, or paired when they should be free, or free when they
should be paired), divided by the length.

> NED = 1 − (1/N) · Σᵢ P(nucleotide i is in its target state)

Tiny example: a 10-nucleotide target, and a molecule that spends 60 % of its
time exactly in it and 40 % in a variant with the end pair open (2
nucleotides wrong). Expected wrong nucleotides = 0.4 × 2 = 0.8, so NED =
0.08, while P(target) = 0.6. Measured: `GGGAAACCC` has NED 0.316 (about three
of its nine nucleotides wrong on average), `GGGAAACCA` 0.028, real RNAs
0.08–0.22. The nucleic-acid design field (NUPACK) optimises exactly this
quantity for exactly this reason.

The **energy gap** to the nearest rival, Phase 0's noise margin, has the
same problem as P(target) at real lengths (the rival is a trivial variant,
gap ≈ 0), so it is recorded but never carries a claim.

We check the ensemble defect independently of ViennaRNA's clever
algorithm: for short sequences our test lists *every* possible structure
by brute force, scores each, and computes probability and NED from their
definitions. They agree, to about one part in a billion, except for one
sequence where they differed by 0.06 %. Chasing that found a genuine
boundary inconsistency inside ViennaRNA 2.7.2: with its default dangling-end
model, its partition function treats structures whose outer pair closes on
the last nucleotide 0.017 kcal/mol more favourably than its own energy
evaluator does. Far below the precision of the energy tables, so we keep
the standard settings and note it, but it is a good example of why a
second, independent route to the same number is worth building.

### 5.5 Structure beyond chance, and the composition trap

"Lower MFE is better" is a trap. A random 80-letter sequence with 70 % G+C
has an MFE of −26.0 kcal/mol, which looks impressively stable. Yet its own
dinucleotide shuffles average −29.3: it is *less* stable than its own
rearrangements. All of its stability comes from composition (G–C pairs are
strong), none from the arrangement of the letters.

The dinucleotide shuffle (Phase 1) keeps the letter counts and which letter
follows which, the raw ingredients of stacking energy, and destroys the
arrangement. Comparing a sequence with 50 shuffles of itself gives two
numbers:

- the **z-score**, (MFE − mean of shuffles) / spread of shuffles: how many
  sigma below its own rearrangements the sequence is. The GC-rich random
  sequence scores +1.46; a real microRNA hairpin −4.3.
- **beats_shuffles**, the chance that the sequence beats a random shuffle
  of itself, with ties counted as half. For any sequence whose letter
  order carries no structure this is exactly 0.5 on average, because the
  sequence and its shuffle are then equally likely arrangements of the
  same pieces (a test checks this on random sequences).

### 5.6 The scale: what real RNA scores

A number without a scale is not a result. For every evaluation the harness
scores five reference sets alongside the generated one, all with *exactly*
the same lengths, because every folding metric depends on length: real
held-out RNA; a second, independent real sample (the noise floor); training
RNA (the family shift); shuffled real RNA; and random letters. Generated
samples are drawn with those same lengths, one to one. On validation:

| | real | second real sample | training RNA | shuffled | random |
|---|---|---|---|---|---|
| beats its shuffles | **0.792** | 0.800 | 0.828 | 0.496 | 0.503 |
| MFE z-score | **−2.15** | −2.20 | −2.90 | −0.01 | −0.02 |
| ensemble defect (own MFE) | **0.175** | 0.168 | 0.163 | 0.248 | 0.242 |
| has a ≥ 80 % twin in the same set | 0.57 | 0.56 | 0.21 | 0 | 0 |

Read it like a calibrated instrument. Shuffled and random sequences land on
0.5 and z ≈ 0, exactly as theory says. The two real samples agree within
their error bars, which tells us how much two honest measurements of the
same thing differ. Training families are somewhat more structured than the
validation families: the family shift from Phase 1, visible in a new metric.

### 5.7 Novelty, diversity, and why real RNA isn't "diverse"

**Novelty** asks whether a sample copies its teachers: its identity to the
nearest *training* sequence. **Diversity** asks whether the model repeats
itself: how similar samples are to *each other*. Random letters score
perfectly on both, so both are only ever reported next to quality.

The reference table holds a surprise worth quoting: **57 % of real
validation sequences have a near-twin (≥ 80 % identical) among 1,000 real
validation sequences.** Real RNA comes in families of close relatives. A
generator that perfectly imitated real RNA would *also* produce near-twins.
So "more diverse" cannot be read as "better" without this reference, and
the protocol uses diversity as a guardrail against collapse (≥ 95 %
distinct samples), not as a score to maximise.

### 5.8 A second oracle, and why one judge isn't enough

Everything above comes from ViennaRNA, a model with quirks. Phase 5 will
steer generation using it, and **Goodhart's law** warns what happens: when
a measure becomes a target, it stops being a good measure. A generator
optimised against an imperfect judge learns the judge's blind spots, like
a circuit tuned against a buggy SPICE model that fails on silicon.

The second judge is **EternaFold**, chosen because it is a *different kind*
of model: not hand-measured energy tables but a statistical model whose
parameters were *learned* from tens of thousands of chemical-mapping
experiments on RNAs designed by players of the Eterna game. Its scores are
not in kcal/mol, so we compare only what both can say: predicted
structures and ensemble defects. A result both judges agree on is more
credible; one only the steering judge likes is suspect. Both still share
blind spots (neither sees pseudoknots or 3D contacts), so agreement is
evidence, not truth.

Two practical surprises, both worth telling. First, the conda build of
EternaFold never finished a prediction, even for a 9-letter sequence: it
was compiled for MPI (parallel computing), where the main process only
hands work to workers, and started alone it has no workers and spins
forever. Launched through `mpirun` it works, and our tests reproduce the
exact example structure from its documentation. Second, EternaFold ships
its own training data, so we checked whether *the judge* had seen our
held-out RNA: 0.30 % of validation sequences have a relative in it, all
tRNAs.

On the reference sets, EternaFold agrees with the ranking on its own terms
(its ensemble defect for ViennaRNA's structures: 0.335 for real RNA, 0.46
for shuffled and random), although the two judges predict the *identical*
structure only 13 % of the time even for real RNA, a reminder of how
uncertain structure prediction itself is.

### 5.9 Statistics: error bars that count the right thing

- **Bootstrap.** Treat the sample as a stand-in for the population,
  resample it with replacement 10,000 times, recompute the number, and read
  off the middle 95 %. Ten outcomes of which seven succeed give an interval
  of 40–100 %; 546 of 1,000 give 51.7–57.9 %. It works for any statistic,
  which is its point.
- **Count the right unit.** Real test sequences come in families, and
  relatives behave alike. Measuring 1,000 transistors from 10 wafers tells
  you about 10 wafers, not 1,000 independent devices. So intervals on real
  data resample *families* (a cluster bootstrap); our test shows that
  ignoring this makes intervals about √10 too narrow when families have 10
  identical members.
- **Two kinds of randomness.** A thousand samples from one trained model
  describe *that model*. Retrain with another random seed and the numbers
  move. An architecture claim needs several trained models per
  architecture, and here the numbers bite: the exact test that treats each
  trained model as one observation can **never** reach p < 0.05 with three
  seeds per architecture (the smallest possible p is 2/20 = 0.10), while
  with five it can (2/252 ≈ 0.008). So the protocol uses five seeds, for a
  mathematical reason, not a stylistic one.
- **Pairing.** Evaluate both models on the same targets, lengths and random
  numbers and compare per item: target difficulty cancels, like
  common-mode noise in a differential pair. Our test shows a +0.02 effect
  that is invisible unpaired and unmistakable paired.
- **Multiple comparisons.** Twenty tests at the 5 % level give a 64 % chance
  of at least one false "win". The protocol names five primary tests in
  advance and corrects them together (Holm–Bonferroni); everything else is
  reported as exploratory.

### 5.10 Pre-registration, enforced in code

The evaluation protocol is written into `RESULTS.md` before the test set is
touched, and, unusually, **before the competing models exist**, so none of
its choices can have been fitted to them. The code enforces it: every
function that reads the test split refuses to run until `RESULTS.md`
contains the line "Status: FROZEN on <date>". The rule that design
targets are chosen by was likewise committed before any target set was
built, and the grid of the sampling ablation was written in the logbook
before its first sample.

### 5.11 Design targets, and a surprise in bpRNA

Targets for Phase 5 come from two places. The primary set takes one real
sequence from each held-out family and uses its predicted structure as the
target: every target is solvable (the real sequence solves it), which gives
a built-in positive control, and there is no quality filter, because
choosing natives that fold nicely would choose easy targets. The second set
takes structures annotated in bpRNA by comparative analysis or experiment,
after a strict screen: no pseudoknots, only pairs our oracle can form,
nothing from a training family or clan (Rfam's own models decide), no
near-copy of a training sequence. The screen found that **72 % of bpRNA's
pseudoknot-free structures contain a pair ViennaRNA can never form** (a
non-canonical pair, or a hairpin loop shorter than three), so they can't be
design targets for our oracle at all.

### 5.12 Mistakes and surprises in this phase

- **A pool that never finished and never failed.** The first large folding
  run was started by piping a script into Python. Its worker processes each
  tried to re-import a script file that didn't exist, died, and were
  silently restarted: 179,339 times in ten minutes, with no error shown. The
  code now refuses to start in that situation. Lesson: a job that neither
  finishes nor fails needs a guard in the code, not only in habits.
- **One file versus many.** EternaFold wants an output *directory* for
  several sequences but an output *file* for one; a batch that happened to
  contain a single sequence would have crashed. Found by a test.
- **My seed recommendation was wrong.** The concept block suggested three
  training seeds per architecture; writing the statistics showed three can
  never support a claim (5.9), so the protocol asks for five.

## Part 6 — What Mamba is, and why we chose it  *(Phase 4)*

## Part 7 — Steering the model toward a target shape  *(Phase 5)*

## Part 8 — Results, and what they mean  *(Phases 4–5)*

## Part 9 — Limitations, and what we'd do with more compute

## Part 10 — Every design decision, with its alternatives
