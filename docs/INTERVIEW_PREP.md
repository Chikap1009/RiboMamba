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

---

## Phase 2 — Masked diffusion and the Transformer baseline

### Q: Why masked diffusion instead of generating left to right like GPT?
**Draft answer** *(Chirag's quiz answer, sharpened)*: A base can pair with
something on its left or its right, so the model needs information from both
sides. Left to right, if position 1 has to pair with position 9, position 9
hasn't been written yet when position 1 is chosen. Masked diffusion starts
with everything hidden and reveals letters gradually, and at every step the
model sees both sides of whatever is already written. It's awkward, not
impossible, to do it left to right, since the chain rule is exact. That's why
I keep an autoregressive Mamba as a baseline, to test it empirically.
**Source:** Phase 2 gate, Q1; STUDY_GUIDE §4.2.

### Q: Why do you put start and end markers around every sequence?
**Draft answer** *(Chirag's quiz answer, sharpened)*: When every position is
masked, which is exactly how generation starts, every position has the same
vector, so the Transformer gives every position the same output: it can't
tell position 3 from position 50. The start and end markers tell each
position how far it is from the start and the end, so it has something
position-specific to learn from. I measured it: 2.11 bits without markers,
1.58 with them, on a memorisation test.
**Source:** Phase 2 gate, Q5/Q7; DECISIONS D-010.

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
**Say it on the right scale** *(added session 05, after Chirag asked whether
1.9 "seems shit")*: read the gaps, not the value. Bits add up along the
sequence: 0.094 bits/nt below "know nothing" is 9.4 bits over a 100-letter
RNA, so the model finds a real, never-seen RNA about **2⁹·⁴ ≈ 670× more
probable than random letters**; the best counting model manages 2³·⁴ ≈ 10×.
That's **2.8× the information** of the k-mer model. The capacity is there:
on its own training families the same model reaches 1.615 bits (1.41 when
trained longer), so the limit is generalising to new families, not the
network. And a leaky random split would flatter a trivial 8-mer memoriser
to 1.817.
**Likely follow-up:** "Both of your architectures got about 1.9. So what?"
→ Then the backbone doesn't change how well letter statistics transfer to
new families, reported as "no detectable difference with 5 seeds". Likelihood
is one of three primary endpoints; the question that matters for design is
whether the RNA holds a shape (E2, E3), where the baseline is at
random-letter level. The honest limitation: ≈ 3,000 families is little
data; more families would likely lower the number.
**Source:** RESULTS.md, Phase 2 reference points; logbook 2026-09-25 session 05.

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

---

## Phase 3 — The evaluation harness

*(Drafts in Claude's words, written during the build; rewritten from
Chirag's own gate answers after the Phase 3 gate.)*

### Q: How do you know a generated RNA is "good"? Isn't lower folding energy better?
**Draft answer:** Lower energy on its own is a trap, because it mostly
measures composition. A random sequence with 70 % G and C has an MFE of
about −26 kcal/mol, but it's actually *less* stable than shuffled versions
of itself. So I compare every sequence with 50 dinucleotide shuffles of
itself, which keep the letters and their neighbour statistics and only
destroy the arrangement. Real validation RNA beats its own shuffles 79 % of
the time; shuffled and random sequences sit at exactly 50 %, as they
should. Then I measure how firmly a sequence holds its structure, with the
ensemble defect, and I check both against a second oracle.
**Likely follow-up:** "Why the ensemble defect and not the probability of
the structure?" → At real lengths the exact structure's probability is near
zero even for good RNA (0.000–0.07 on real 74–223-nt sequences), because
probability spreads over thousands of near-identical variants. It's a frame
error rate; the ensemble defect is the bit error rate.
**Source:** logbook/2026-09-24-session-04.md (12:37, 13:44).

### Q: Why use two folding programs?
**Draft answer:** Because the model will later be steered by one of them,
and anything optimised against an imperfect judge learns the judge's
quirks: Goodhart's law. EternaFold is a genuinely different model, with
parameters learned from chemical-mapping experiments rather than Turner's
energy tables, so if a result holds under both, it's less likely to be a
ViennaRNA artefact. I only compare structure-level outputs across the two,
because EternaFold's scores aren't in kcal/mol. And I checked that the
second oracle hadn't seen our held-out RNA in its own training data: only
0.3 % of validation sequences, all tRNAs, have a relative there.
**Likely follow-up:** "Why not RNAstructure?" → It uses the same Turner
parameters, so it shares ViennaRNA's blind spots.
**Source:** DECISIONS D-013.

### Q: How many training runs do you need to claim one architecture is better?
**Draft answer:** At least five per architecture, and I can show why. If
each trained model is one observation, the exact permutation test with
three versus three can never give p below 0.10, even if every run of one
architecture beats every run of the other, because there are only 20 ways
to split six runs into two groups of three. With five versus five there are
252, and complete separation gives p ≈ 0.008. I also correct for the five
primary tests I declared in advance, with Holm–Bonferroni. I'd actually
recommended three at first; writing the statistics showed that was wrong.
**Likely follow-up:** "Why not bootstrap over samples instead?" → A thousand
samples from one trained model tell you about that model, not about the
architecture. It's within-die versus die-to-die variation.
**Source:** RESULTS.md, frozen protocol P4/P8; `seed_permutation_test`.

### Q: What stops you from tuning the evaluation until your model wins?
**Draft answer:** Three things. The protocol, meaning metrics, primary
endpoints, sampling settings, targets and statistics, is written in
RESULTS.md and frozen before the test set is used, and before the Mamba
models even exist, so it can't have been fitted to them. The code enforces
it: the test split can't be loaded until the file says "FROZEN". And every
endpoint gets reported for every model, including losses.
**Source:** RESULTS.md; `ribomamba/eval/protocol.py`.

### Q: How do you know a generated RNA actually folds, rather than just looking stable?
**Draft answer (Chirag's words from the Phase 3 gate):** Folding energy mostly
comes from the letters, not the arrangement. G and C make strong pairs, so a
sequence full of G and C gets a very low energy even if you shuffle it into
random order. So I compare every sequence with dinucleotide shuffles of
itself: same letters, same neighbour statistics, arrangement destroyed. Real
validation RNA beats its own shuffles 79 % of the time, random sequences 50 %,
and our baseline only 56 %. That difference is the part that comes from
arrangement, which is what structure actually is.
**Likely follow-up:** "Why not just report the energy?" -> A random 80-mer at
70 % GC folds to -26 kcal/mol and is still *less* stable than its own
shuffles. The energy alone would call it structured.
**Source:** logbook 2026-09-25, gate batch 2 (Q5).

### Q: Your samples are far more diverse than real RNA. Isn't that good?
**Draft answer:** Not by itself. Among 1,000 real validation sequences, 57 %
have a near-twin in that same set, because RNA families are sets of
relatives. Our samples have none, and neither do random letters. Any number
that random letters maximise can't measure quality. So I use diversity as a
guardrail: if it collapsed, say a third of samples being near-copies of each
other, I'd stop trusting the quality numbers. Above that floor, more isn't
better.
**Source:** RESULTS.md reference scale; gate batch 3 (Q9).

### Q: Your audit reports zero test sequences with an 80 %-identical training relative. Convincing?
**Draft answer (his words):** On its own, no, and I'd point that out myself.
An earlier step removed exactly those sequences using the same search, so the
zero is there by construction: it's like deleting every bruised apple and then
reporting that no apples are bruised. The informative numbers are the ones
nothing was filtered on: 1.05 % of test sequences have any detectable relative
in training at all, 0.40 % at 50 % identity. And the control row, a
deliberately random split measured the same way, gives 96 %. That contrast is
the real evidence.
**Source:** gate batch 4 and 5 (Q12, Q14).

### Q: You steer generation with ViennaRNA. How do you know you're not just learning its quirks?
**Draft answer (his words):** That's exactly the risk, so I score everything
with a second program too. EternaFold is a different kind of model: its
parameters were learned from chemical-mapping experiments instead of taken
from measured energy tables, and it's never used for steering. If designs look
good under both, I trust them. If they look good only under ViennaRNA, the
likely explanation is that the model learned the patterns ViennaRNA prefers,
and the verdict to doubt is ViennaRNA's, not EternaFold's. I also checked that
EternaFold's own training data contains nothing related to our test set.
**Likely follow-up:** "Couldn't that just be memorisation of training RNA?" ->
No: memorised real RNA folds well under both programs. Memorisation shows up
in the novelty check instead, which reads 0 %.
**Source:** DECISIONS D-013; gate batches 6-7 (Q16, Q19).

### Q: You changed a tuning rule after seeing results. Isn't that cheating?
**Draft answer (his words):** It would be if the change applied to one model
only. The rule was "if the best learning rate is at the edge of the grid, test
the next value beyond it". It's mechanical, so there's no judgement call; it
applies identically to every backbone; it was added before any other backbone
was swept, so it can't have been shaped to favour one; it only ever touched
validation-based tuning, never the test set; and it's recorded as a dated
amendment rather than an edit. If I'd added it only for Mamba, it would have
been cheating.
**Source:** DECISIONS D-011 amendment; gate batches 6-7 (Q17, Q20).

### Q: Why keep only sequences from families whose typical member is short, instead of filtering by length?
**Draft answer (his words):** Because long families turn up in Rfam partly as
short fragments: pieces of a 2,000-letter ribosomal RNA cut off where the
sequenced stretch of genome ended. Those pieces are under 256 letters, so a
plain length filter keeps them, and we measured 83,525 of them. They have no
proper start or end, so they don't fold into anything meaningful and they
aren't molecules anyone could make. Dropping the family by its median length
removes the pieces with it.
**Source:** DECISIONS D-007; gate batch 8 (Q22).

---

## Phase 4 — Mamba (drafts from the concept block; rewritten in Chirag's words after the gate)

### Q: What is a state-space model, and what does "selective" add?
**Draft answer:** It reads the sequence once, left to right, and keeps a
fixed-size summary, the state, which it updates at every letter: new state =
keep factor × old state + what this letter writes. It's exactly the
state-space form from control theory, h′ = Ah + Bx, y = Ch + Dx, turned into
steps with a step size Δ. In the old version the keep factor was the same for
every letter, so it behaved like a fading echo that forgets every letter at
the same rate. Selective means Δ, B and C are computed from each letter, so
the model decides per letter what to keep and what to write. In my toy
example, after a 12-letter loop a fixed rule kept 0–25 % of the memory of
the G's and a selective rule kept 88 %.
**Likely follow-up:** "Then how does it stay parallel?" The update is
"multiply by a, add u", and two such steps combine into one of the same form,
in any grouping, so a GPU can combine them as a tree: 256 positions in 8
rounds.
**Source:** logbook 2026-09-25 (instalments 1–2); GLOSSARY.

### Q: Mamba is linear-time. Was it faster than your Transformer?
**Draft answer:** No, not at our lengths, and I measured it. One Mamba-2
block took 6.0 ms against 3.8 ms for a Transformer block at 256 letters; only
at 1,024 was Mamba faster (11.7 vs 21.7 ms). Big-O says how cost grows, not
what it costs at a given size, and a GPU is very good at the matrix
multiplications attention uses. So for my project Phase 4 is purely a
question of quality: every model gets the same number of training steps on
the same batches, and speed doesn't enter the comparison. Linear time would
matter for long RNAs like ribosomal RNA, which our 256-letter cap excludes.
**Source:** RESULTS.md, "Does Mamba run here"; instalment 1.

### Q: Why does a diffusion denoiser need a bidirectional Mamba, and how did you build it?
**Draft answer:** A hidden letter's best evidence is often its pairing
partner, and that can be on its right: in GGGAAACCC with the first G hidden,
the partner is the last C. A left-to-right scan at position 1 has seen
nothing yet. So each layer runs two scans, one each way, and adds them. The
two directions share the big input and output projections and each has its
own convolution, step-size bias, keep factors and skip, the pattern of Vision
Mamba and Caduceus, because RNA is directional (a GC stack is −3.4, a CG
stack −2.4 kcal/mol). One trap: batches are padded on the right, so flipping
a whole row puts padding first in the backward scan, and a scan has no mask,
so the padding would leak into every real position. I reverse each sequence
within its own length instead, and a test shows padding can't change any
real output.
**Likely follow-up:** "How do you know the fused kernels do what you think?"
A test compares them with a step-by-step loop of the textbook recurrence,
each sequence alone; and I broke the code on purpose twice to check the tests
catch it.
**Source:** instalment 3; DECISIONS D-016; tests/test_bimamba.py.

### Q: Why keep an autoregressive Mamba in the comparison?
**Draft answer:** Three models give two controlled comparisons. Transformer
vs BiMamba, both diffusion, changes only the backbone. BiMamba vs the
left-to-right Mamba, same kind of layers, changes only the generation order.
In Phase 2 I argued left to right is awkward for RNA, not impossible; this
tests it. It's also how Mamba is normally used. Two details: its likelihood is
exact while diffusion's is an upper bound, so that comparison is secondary;
and I give it the same lengths as the diffusion models by forbidding the end
token before the target length and forcing it there.
**Source:** instalment 3; protocol P5, P7.

### Q: Isn't attention better suited to base pairing?
**Draft answer:** That's the real question, and it's open. In
favour of attention: pairs are nested like brackets, checking brackets left
to right needs a stack, and attention can look a partner up directly, while
a scan must carry every open bracket in its state; published work shows
state-space models are weaker at exact recall and copying. But at our
lengths the state isn't small: one Mamba-2 direction holds 98,304 numbers
per layer, more than attention stores for a typical 95-letter RNA, so the
difference is how memory is used, not how much. And our Transformer barely
learned pairing anyway: its samples hold their shape no better than random
letters. So it's an empirical question, and the protocol was frozen before
any Mamba existed.
**Source:** instalment 3.
