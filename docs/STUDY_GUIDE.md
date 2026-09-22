# RiboMamba — Study Guide

> **Read this the night before the interview.** It is written for a version of
> you who has forgotten the details and has one evening to rebuild a confident,
> working understanding of the whole project, from "what is RNA" to "what our
> numbers mean and where they fall short".

**Status:** Parts 1–2 written in full (end of Phase 0 content, 2026-09-22).
Parts 3–10 are written at the end of their phases (CLAUDE.md §2.4), so this
guide grows with the work instead of being rushed at the end.

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

## Part 4 — Generating instead of searching: masked discrete diffusion  *(Phase 2)*

## Part 5 — How we evaluated honestly  *(Phase 3)*

## Part 6 — What Mamba is, and why we chose it  *(Phase 4)*

## Part 7 — Steering the model toward a target shape  *(Phase 5)*

## Part 8 — Results, and what they mean  *(Phases 4–5)*

## Part 9 — Limitations, and what we'd do with more compute

## Part 10 — Every design decision, with its alternatives
