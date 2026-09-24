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

---

## Phase 1 — Data

*(Draft answers written by Claude from session 03; to be rewritten in
Chirag's words after the Phase 1 quiz.)*

### Q: How did you split your data, and why not randomly?
**Draft answer:** RNAs come in families: relatives descended from one
ancestor, with different letters but the same structure. If you split
randomly, almost every test sequence has a sibling in training, so the test
measures whether the model can recall a relative, not whether it
generalises. I measured it: with a random split, about 90 % of test
sequences have a training relative that's at least 80 % identical, and the
median test sequence has a 96 %-identical one. So I split by Rfam **clan**,
or by **family** when there's no clan: whole groups go to train, val or
test. Then I removed any held-out sequence that still had an 80 %-identical
training relative, because Rfam doesn't link every related family. After
that, 99 % of test sequences have no detectable relative in training at all.
**Likely follow-up:** "Why not just filter by sequence identity, like
CD-HIT at 80 %?" → Because of covariation: family members can drift below
80 % identity while keeping the same structure, since both sides of a pair
mutate together. bpRNA's TS0 split was built that way, and published models
that look good on it drop on the family-disjoint bpRNA-new. Identity alone
lets families leak. I use both criteria.
**Source:** logbook/2026-09-23-session-03.md; DECISIONS D-008; RESULTS.md
leakage audit.

### Q: What's the most important thing you found in the data?
**Draft answer:** The HuggingFace copy of Rfam I downloaded contains every
row twice. The second copy's family label is a placeholder, "No such family".
I checked it properly: all 10 million placeholder rows have an identical twin
with a real label. If I'd treated the placeholder as a family, it would have
been one giant family containing a copy of every other family. Whichever
split it landed in would then share sequences with every other split, so the
family split would have been completely leaky while looking perfectly clean
by its labels. That's why I measure data before trusting it.
**Likely follow-up:** "How would you have noticed if you hadn't looked?" →
The leakage audit would have caught it (near-100 % identical hits across
splits), which is the point of having an audit that checks sequences, not
just labels.
**Source:** logbook/2026-09-23-session-03.md (~03:45); DECISIONS D-007.

### Q: Sequence identity misses covariation. How do you know no structural relatives leaked?
**Draft answer:** I checked with the tool Rfam itself uses to decide family
membership: covariance models, which score base pairs as well as letters,
so a relative that swapped G–C for A–U still fits. I scanned every
held-out sequence (about 114 thousand) against all 4,178 Rfam 15.0 models.
If one scored above a *training* family's gathering threshold, meaning
Rfam would call it a member of that family, I removed it. That was 12
sequences, almost all snoRNAs. The detector has a positive control: 99.6 %
of held-out sequences are found by their own family's model, so it can
see. It also has a negative control: shuffled sequences that keep the
neighbour statistics give the false-alarm rate. What remains is weak,
below-threshold resemblance, which is mostly "also a hairpin-shaped
microRNA". That's not leakage, and no split could remove it.
**Likely follow-up:** "Why not remove the weak hits too?" → Because they're
class-level similarity, the kind of general knowledge we *want* a model to
transfer to new families. Removing them would mean removing every hairpin
from the test set.
**Source:** DECISIONS D-009; RESULTS.md structural audit.

### Q: Tell me about a mistake you made in this project.
**Draft answer:** My first structure-aware scan left out one flag,
`--nohmmonly`. About 350 Rfam models have no base pairs, and for those the
tool silently switches to a letters-only scoring mode whose scores aren't
comparable to the family's threshold. So for those families I was comparing
two different kinds of number. The positive control gave it away: sequences
from those families found their own family only 88 % of the time, versus
99.5 % for the rest. I stopped the run, added the flag, and rescanned
everything; for those families recovery went to 99.99 %. What I took from it:
a control isn't a box to tick. When it looks slightly off, that's the
detector telling you it's broken.
**Source:** logbook/2026-09-23-session-03.md (19:37); DECISIONS D-009.

### Q: Your model gets ~1.9 bits per nucleotide. Is that good?
**Draft answer:** On its own the number means little, so I calibrated it.
Knowing nothing is exactly 2 bits for four letters. Letter frequencies alone
give 1.996, so RNA is almost uniform in composition. The best counting model
(predict each letter from the previous 4) gets 1.966 on unseen families, and
longer contexts get *worse* there because they memorise training k-mers. The
Transformer was at 1.914 after a short run, so it has learned something beyond
local statistics; most plausibly the long-range pairing correlations, which
no left-context count can see. And the random-split control is striking: an
8-letter counting model would score 1.817 on a random split, apparently
beating the neural network, purely by recognising relatives of the test
sequences.
**Likely follow-up:** "Why so close to 2?" → Different RNA families share
almost no sequence, and the information is mostly in which positions pair,
not in which letters appear. A model has to learn "grammar", not vocabulary.
**Source:** RESULTS.md, Phase 2 reference points.

### Q: Does your baseline actually generate RNA-like molecules?
**Draft answer:** Partly, and I measured exactly which part. The samples are
novel (none has even a 50 %-identical relative in training, so it's not
copying) and their letter composition matches real RNA. But real RNA folds
more stably than a shuffled version of itself about 79 % of the time, and
our baseline's samples only 55 %, barely above chance. So the Transformer
learned what RNA letters look like much better than how RNA folds. That's
the gap the rest of the project targets: whether Mamba captures pairing
better, and whether conditioning on a target structure fixes it.
**Likely follow-up:** "Why compare to shuffles instead of just looking at
the folding energy?" → Folding energy depends a lot on GC content. The
shuffle keeps the letters and their neighbour statistics, so any extra
stability must come from how the letters are arranged, which is the
structure.
**Source:** RESULTS.md, sanity preview.

### Q: Your training overfit. What did you do?
**Draft answer:** Validation on unseen families peaked after about three
passes over the data while training kept improving, so the model started
memorising training families. I stopped the long run (the best checkpoint
is always kept, so nothing was lost), then tested dropout under a rule
written in advance. Dropout slowed learning but didn't stop the overfitting;
every run still peaked around 3–4 passes at about 1.90 bits. So I report that
as a finding (the transferable signal between families seems limited at
this scale), use early stopping, and give the Mamba models the identical
protocol.
**Source:** DECISIONS D-012; RESULTS.md.

### Q: Why a maximum length of 256?
**Draft answer:** Three reasons. Memory: the Transformer baseline's
activation memory grows with length, and naive attention grows with length
squared. My rough estimate was ~2.7 GB at 256 versus ~7.4 GB at 512 on an
8 GB card. The oracle folds in O(N³), so 512-nt sequences cost ~8× more to
evaluate. And MFE prediction gets less reliable for long RNAs. The cost is
honest: 256 keeps 95 % of Rfam families, and the 185 dropped ones are the
long RNAs, the ribosomal RNAs, RNase P and tmRNA, which we don't claim to
design. I applied the cut per family (by median length) first, because
otherwise short fragments of ribosomal RNA would slip in as if they were
whole molecules.
**Likely follow-up:** "Doesn't that favour the Transformer, since Mamba's
advantage is at long lengths?" → Yes, it probably does, and I'd state it as
a limitation. It makes our comparison conservative for Mamba. If Mamba still
wins at ≤ 256, that's a stronger claim; if it loses, the length regime is
part of the explanation.
**Source:** DECISIONS D-007.

### Q: Why tokenise one nucleotide per token?
**Draft answer:** Base pairs link single nucleotides, and masked diffusion
hides and predicts whole tokens. With 3-letter tokens, one token could sit
half in a stem and half in a loop, so the model couldn't mask or predict
one base independently. The alphabet is only 4 letters and our sequences
are at most 256 long, so there's nothing to gain from compressing. The
vocabulary is 8 tokens: A, C, G, U plus pad, mask, begin and end. The
begin/end tokens are reserved now so the autoregressive baseline shares the
same embedding table, which keeps the parameter matching exact.
**Source:** DECISIONS D-006.

### Q: What is padding, and how did you handle its cost?
**Draft answer:** A GPU processes a batch as one rectangle, so shorter
sequences are padded to the longest one in the batch, and an attention mask
marks which positions are real so padding never influences the model or the
loss. Padding is wasted compute. With random batches, 54 % of all positions
in our training set were padding. I group similar lengths into the same
batch (shuffling within big pools, so batches stay random between epochs),
which brought it to 1.1 %, roughly halving the cost of an epoch.
**Source:** logbook/2026-09-23-session-03.md (04:27).
