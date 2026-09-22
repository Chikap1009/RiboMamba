# Interview Prep — RiboMamba

Questions an interviewer would plausibly ask, with draft answers **in Chirag's
own voice**. Where possible, answers are built from how Chirag explained the
idea back in a session, not from how Claude explained it.

Format:

```
### Q: <question>
**Draft answer:** …
**Likely follow-up:** …
**Source:** logbook/<file>.md
```

Sections will follow the phases.

---

## Phase 0 — RNA foundations

### Q: Why does your project work with secondary structure instead of 3D structure?
**Draft answer:** Secondary structure is basically the wiring diagram, which
bases pair with which, and like a netlist it captures most of what decides
behaviour. More importantly for us, it can be predicted in milliseconds by
standard software, and our evaluation has to fold tens of thousands of
generated sequences on a free-tier budget. 3D prediction for RNA is much more
expensive and still much less reliable than for proteins. So we deliberately
scoped it to secondary structure, and I'd say that's a limitation, not a
claim that 3D doesn't matter.
**Likely follow-up:** "So how do you know your designs would really work?" →
We don't, experimentally. Our success criterion is that the folding oracle
predicts the target. No wet lab. Checking with a second, independent oracle
would be the next step.
**Source:** logbook/2026-09-22-session-01.md (concepts 3, 5); DECISIONS D-001.

### Q: Why do standard folding tools ignore pseudoknots? Isn't that a big limitation?
**Draft answer:** It's a real limitation, and the reason is computational,
not notational. If pairs never cross, then everything inside a pair is
independent of everything outside it, so the folding problem splits into
sub-problems that dynamic programming solves once and reuses, which gives
O(N³). It's like static timing analysis reusing per-node results instead of
listing every path. Once pairs can cross, the sub-problems tangle together and
exact prediction gets dramatically more expensive. We accept the limitation
and say so: RNAs that depend on pseudoknots are outside our scope.
**Likely follow-up:** "Can dot-bracket even represent a pseudoknot?" → Not
with one bracket type. Worse, if you try, it silently decodes into a
*different valid* structure. Extended notation uses a second bracket type,
`[ ]`, like adding a second metal layer.
**Source:** logbook/2026-09-22-session-01.md (concepts 3, 4).

### Q: What is the minimum free energy structure, and is it enough for a design's target to be the MFE?
**Draft answer:** Every possible structure gets a free-energy score, where
stacked pairs lower it and loops raise it, and the MFE structure is the one
with the lowest score. But being the lowest isn't enough: the MFE has to be
the lowest by a good margin, or the molecule keeps switching between shapes.
The gap works like a noise margin. At body temperature every ~1.4 kcal/mol of
gap is about a 10× preference, so a design whose target beats its closest
rival by only 0.2 spends only about 58% of its time in the target, nearly a
coin flip.
**Likely follow-up:** "Where does the 1.4 come from?" → The Boltzmann
distribution: probability ∝ e^(−ΔG/RT), with RT ≈ 0.62 kcal/mol at 37 °C,
so one decade = RT·ln 10 ≈ 1.42. It's the same physics as the ~60 mV/decade
subthreshold swing of a MOSFET.
**Source:** logbook/2026-09-22-session-01.md (concept 4, Q1).

### Q: Why is RNA design hard? Why not search for a good sequence?
**Draft answer** *(from Chirag's explain-back and retry in session 01, with
corrections applied)*: There are 4^N possible
sequences, and for a 50-letter RNA that's about 10³⁰. Even folding a
billion per second, checking them all would take thousands of times the age of
the universe. The smarter approach, changing one letter and keeping it if it
gets closer, gets stuck in local minima. For example, flipping a G–C pair to
C–G means passing through G–G or C–C, which are broken pairs, so a method
that only accepts improvements rejects every route there. A generative model
learns from real RNA what sequences look like, so it doesn't start from
zero for every new target. It can output many different candidate
*sequences* quickly, and we fold each one with the software to check whether
its predicted structure matches the target.
**Likely follow-up:** "How do you know the designs really fold?" → Strictly,
we don't. The folding software is itself a model, so our success means "the
software predicts the target", not a wet-lab result.
**Source:** logbook/2026-09-22-session-01.md (concept 5, explain-back).

### Q: Is "the predicted MFE structure equals the target" a good enough success test?
**Draft answer** *(written by Claude from the session 02 results; to be
rewritten in Chirag's own words after his explain-back)*: Not on its own.
Our very first sanity check showed why. The textbook hairpin `GGGAAACCC`
does fold to the target as its MFE, at −1.20 kcal/mol, but ViennaRNA finds a
rival shape only 0.2 kcal/mol higher, so the molecule spends only about 51%
of its time in the target. It passes an MFE-match test while being close to
a coin flip in reality. Meanwhile a one-letter mutant, `GGGAAACCA`, refolds
into a *different* hairpin and holds it 94% of the time. So besides MFE
match I'd look at how dominant the target is: its probability in the
Boltzmann ensemble, or its energy gap to the nearest rival.
**Likely follow-up:** "How do you compute that probability?" → The partition
function: add up e^(−ΔG/RT) over all structures (ViennaRNA does this with
dynamic programming, `RNAfold -p`), then the target's share is its own term
divided by the total. I checked the 51% by hand from the eight lowest
structures and got 50.8%.
**Source:** logbook/2026-09-22-session-02.md (22:30); RESULTS.md, Phase 0
sanity checks.
