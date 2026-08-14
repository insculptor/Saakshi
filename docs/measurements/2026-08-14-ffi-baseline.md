# What it costs to cross into the ephemeris binding

**2026-08-14.** Taken while building `generators/probe6b_ffi.py` and `src/saakshi/timing.py`.
Software: Swiss Ephemeris 2.10.03 through `pyswisseph` 2.10.3.2, called from CPython 3.12 on
one Windows workstation. ⛔ No ephemeris data files are involved and none were available to
the process: the rungs that consult an ephemeris were answered by the library's analytical
source, asserted from the entry point's own returned flag before anything was timed.

⛔ **Recorder, never explainer.** Everything below is an elapsed span observed under stated
conditions. Nothing here describes how the library computes anything.

---

## The question had no answer in the form it was asked

*"What does one round trip through the binding cost?"* covers at least three quantities that
differ by more than two orders of magnitude: a crossing carrying nothing, a crossing carrying
four arguments, and a crossing that computes a position. A single figure quoted for "the
round trip" is therefore not a measurement that is slightly off — it is an answer to an
unspecified question, and which of the three it happens to be is decided by whichever call
the person measuring reached for.

So the answer is published as a **ladder**: rung by rung, each stating its arity, what its
callee does, and the form of its call site.

---

## ⛔ Three facts about the method, before any number

**1. The clock is coarser than the subject.** The finest clock this platform offers advances
in steps of **100 ns**, measured rather than read off documentation. The calls of interest
cost a few tens of nanoseconds. **No individual call was timed and none could be.** Every
figure is an elapsed span divided by a declared repetition count — a mean, with the count on
the row. A batch elapsing less than a hundred clock steps is **refused**, not recorded: below
one step it reads zero, and zero is indistinguishable afterwards from a call that costs
nothing.

**2. The absolute number moves with the method, so only ratios are published.** The same
do-nothing Python function measured **47 ns** under one way of writing the loop and **39 ns**
under another, in one process, minutes apart — and **24 ns** in a run taken an hour earlier
on the same machine. ⭐ A figure in nanoseconds is the wrong *shape* for a claim about a
binding, in the way that a band expressed in an absolute distance was the wrong shape for a
claim about a state vector. What survives is the **relationship** between two rungs measured
identically, in one interleaved process. Every nanosecond figure in the artifact sits inside
an object that states its own standing: environment context, the same standing as the host
record.

**3. Ratios are taken inside a round, never between two summaries.** Every rung, in every
form, is measured once per round; a ratio is computed from the two readings taken
milliseconds apart and only then summarised across rounds. Dividing one rung's median by
another's would let machine drift into the ratio instead of cancelling out of it.

---

## The ladder

Ratios against the **anchor**: a Python function taking no arguments and returning
immediately, measured in the same round and the same call-site form as whatever is divided by
it. ⚠ Every figure includes the loop the call sits in; that loop is measured as its own rung
(about 0.4 anchors) and is common to both terms of every ratio, so each ratio is biased
*toward* one.

| Rung | Arity | Against the anchor |
|---|---|---|
| the loop, with no call in it | — | **0.33 – 0.43** |
| a Python function, one argument | 1 | 1.02 – 1.06 |
| a Python function, four arguments | 4 | 1.17 – 1.30 |
| a standard-library C function, no arguments | 0 | 0.94 – 1.14 |
| **the binding, no arguments** | 0 | **0.93 – 1.14** |
| **the binding, one argument** | 1 | **1.44 – 2.20** |
| **the binding, four arguments** | 4 | **2.28 – 3.75** |
| the binding, one body's position | 3 | **190 – 210** |
| the binding, a full set of house cusps | 4 | **120 – 135** |

⛔ **These are ranges observed over the runs behind this page — not bounds a further run
must satisfy**, and the distinction is not a formality: an interval fitted to what has
already happened is an envelope, and a first draft of this page quoted one that the very next
emission fell outside in twelve places. What *is* measured, in the artifact itself, is the
movement: a ratio's median moved **1.3 % typically and 4.8 % at worst** between two
traversals at one commit.

⚠ **And the two kinds of width are kept apart rather than averaged.** A range across the
three **call-site forms** — which is what makes the binding rows wide — is a finding, and it
is section 4. A range across **runs** is noise. The artifact separates them too: a ratio's
spread across rounds sits on the ratio, and its spread across forms is a row of its own kind.

---

## 1. ⭐ The empty crossing is not the binding's cost

A binding call carrying **no arguments** costs **what a Python function call costs** —
0.95 to 1.12 anchors, and a standard-library C function of the same arity lands on the same
number to within the same spread, form for form.

⛔ **So the empty round trip is CPython's own call protocol.** A probe that reports it as
"the cost of the binding" has measured the interpreter and attributed the result to the
library. This is the reason the ladder carries a pure-Python rung *and* a C rung at every
arity a binding rung is measured at, and the reason that requirement is enforced as a control
rather than left to whoever assembles the list.

---

## 2. What *is* attributable is marshalling, and it grows with the argument count

| | against the same-arity Python function | against the binding's own zero-argument rung |
|---|---|---|
| one argument | **1.38 – 2.12** | **1.55 – 2.05** |
| four arguments | **1.94 – 2.95** | **2.40 – 3.40** |

The same comparison inside pure Python moves far less: one argument costs about 1.04 anchors
and four about 1.25.

⚠ The C comparator is an **upper** bound on the interpreter's own share, never a floor: the
standard-library function used at those arities does a small amount of real arithmetic, which
is why it is quoted as a bound rather than subtracted.

---

## 3. A call that does work dwarfs the crossing

One body's position, asked a different instant each time: **197 to 201 anchors.** A full set
of house cusps: **124 to 131.**

⭐ Both are two orders of magnitude above the crossing they sit on top of. A caller sizing
these calls is bounded by the work, not by the boundary — and the boundary's contribution is
smaller than the difference between two ways of writing the call site, which is the next
finding.

---

## 4. ⭐ The call-site form is part of the number

The same callee, the same argument values, three ways of writing the call:

* **unpacked** — the arguments are a tuple, built once and handed to the call site whole;
* **local names** — unpacked into locals before the loop, named at the call site;
* **literal** — compiled into the call site as literal constants.

| Rung | unpacked | local names | literal |
|---|---|---|---|
| a Python function, one argument | 1.03 – 1.06 | 1.03 – 1.04 | 1.02 – 1.04 |
| a Python function, four arguments | 1.17 – 1.23 | 1.25 – 1.27 | 1.27 – 1.30 |
| **the binding, one argument** | **1.44 – 1.58** | **2.13 – 2.16** | **2.12 – 2.16** |
| **the binding, four arguments** | **2.28 – 2.42** | **3.43 – 3.66** | **3.45 – 3.71** |

⭐ **The pure-Python rungs move by a few per cent across the three forms; the binding rungs by
about half again** — comparable to the entire cost of an empty crossing. ⚠ The intervals
inside each cell are across runs and are worth a few per cent; the finding is the gap
**between columns**, which is an order of magnitude larger than that.

The direction is worth reading: handing this binding a pre-built tuple is the **cheapest**
form, while for the anchor it is the dearest.

⛔ **So a figure quoted without its call-site form is under-specified**, and a harness that
picks one form and calls the result "the cost of the call" has measured its own convention.
This is the general case of a defect this repository has already paid for once, in a different
domain: **a recorder that transforms a value before handing it to the thing being measured has
made the transformation part of the measurement.** The form is on every row.

---

## 5. ⛔⛔ A repeated call is not a repeated computation

A timing loop asks one question many times. Some callees answer the second asking far more
cheaply than the first — and against such a callee a loop reports a floor that no caller
asking different questions will ever see, wearing the label of a measurement.

So every rung whose cost could depend on *which* request is asked is measured twice, over the
**identical compiled loop**, differing only in what the run of argument tuples holds: one
request repeated, or a distinct request every time.

| Rung | distinct requests ÷ one request repeated |
|---|---|
| a Python function, one / three / four arguments | 0.99 – 1.03 |
| the binding, one argument | 0.98 – 0.99 |
| the binding, four arguments | 1.00 – 1.02 |
| **the binding, one body's position** | **33 – 38** |
| the binding, a full set of house cusps | 1.01 – 1.03 |

⭐ **The position call answers a repeated request thirty-odd times more cheaply than a new
one.** Measured only the ordinary way, it reads as about **six** times the crossing; measured
over distinct instants it is **about two hundred** times it.

⭐⭐ **And the two rungs that do real astronomical work answer oppositely.** The house-cusp
call is indifferent to whether it has been asked before. Measuring either one alone would
have licensed a wrong general conclusion — *"a real call is cheap"* from one, *"repetition
sensitivity is what real calls do"* from the other. The pair is the finding; neither member
of it is.

⚠ **A negative verdict here is bounded in one direction only.** `false` means *not observable
by this harness at this run length*. It does not mean the callee keeps nothing between calls.

---

## The controls, and why a timing harness needs them

A timing harness cannot be checked against a known answer, because there is no known answer.
What it can be checked against is its own ability to report a difference that is there, and to
report none where there is none. ⛔ **The generator refuses to write if any control fails.**

| Control | Expected | Measured |
|---|---|---|
| the anchor against a second reading of itself | 1.0 | **0.98 – 1.01** |
| every arity a binding is measured at also has a pure-Python and a C rung | none missing | none missing |
| a pair built to perform the anchor a hundred times | ≥ 20 | **66 – 84** |
| distinct arguments cost nothing by themselves, where the callee cannot notice them | 1.0 | **0.99 – 1.03** |

⭐ **The third and fourth exist because the first two are satisfied by a harness that measures
nothing at all.** Report zero everywhere and every identical pair agrees perfectly. An
expected difference is the control — and the fourth is what makes finding 5 attributable: a
run of distinct tuples touches more memory than a run of one tuple repeated, so unless that
costs nothing where it cannot matter, a rung that *does* differ has not been shown to differ
for a reason of its own.

---

## ⛔⛔ This artifact does not regenerate byte for byte

Every other file this repository writes does. This one cannot: its subject is a duration, and
a duration is not a property of the callee alone. It is declared in the file itself — a
`reproducibility` row and the first header note — rather than left for a consumer to discover
from a diff.

⭐ **So the generator traverses the whole ladder twice and publishes the comparison.** A
statement about what a file reproduces is a claim like any other, and made in prose it is
untested. The second traversal exists only to test it.

**Measured, in the file, by the same instrument on the same day** (one busy machine; the
figures below are that comparison, not a bound):

| | |
|---|---|
| published ratios re-measured | **98** — every one the file carries |
| ratios whose second median fell inside the first traversal's per-round interval | **91 to 98**, run depending |
| median movement of a ratio between traversals | **a few per cent** (1.3 to 4.3 observed) |
| largest movement of a ratio between traversals | **ten to fifteen per cent**, always a ratio near one |
| repetition-sensitivity verdicts that agreed | **7 of 7, every time** |

⚠ **The first two rows move a great deal with how busy the machine is, and the last does
not.** That contrast is the useful one: the digits are noise and the verdicts are not.

⚠ The ratios that fell outside are **named** on the row, not merely counted; every one of
them is a ratio near one, where a movement of a fraction of a nanosecond is a large fraction
of the ratio.

⛔⛔ **Two ordering claims were written here and the second traversal disposed of both.** The
first — *"the order of every pair that held in every round"* — sounds like a claim about a
re-run and is not one: several pairs per call-site form that held in every round of the first
traversal changed places in the second, all of them pairs whose ratio is one within its own
spread. The second was a fix by constant: *"pairs separated by at least 10 %"*. That failed
the same way, losing four pairs in one form and seven in another.

⭐ **So the file stopped choosing a number and measured one.** It publishes three nested sets
per form — every pair compared, the pairs that held in every round, and the pairs separated by
the declared 10 % — and beside them the figure that is actually the claim: **the smallest
separation such that every pair the first traversal separated by at least that much was still
in the same order in the second.** On this machine it came out between **1.08 and 1.72**,
varying by form and by how busy the machine was — so a factor of two apart is safe to read off
this ladder and a few per cent is not. ⛔ It too is a measurement, not a guarantee; a run on
another day may need a larger one, and the row says so. Where it reads exactly **1.0**, the
whole ordering for that form reproduced.

**What a re-run will not reproduce** — any nanosecond figure, the exact digits of any ratio,
the spreads themselves, and the ordering of any pair closer together than the measured
separation.

⛔ **A byte comparison of this file reports a difference every time and means nothing by it.**
For each ratio, check that the other run's median falls inside this file's per-round interval;
then compare the orderings of the pairs that clear the measured separation, and the verdicts.

⚠ **Two traversals minutes apart on one machine is the weakest form of this check**, and the
artifact says so on the row. It cannot speak for a different day, a different load or a
different interpreter build. A consumer re-running the generator is performing the stronger
version of the same comparison — which is why the file publishes the intervals it would be
compared against.

⚠ **A write-up of a timing probe cannot quote the shipped artifact's own digits either**, and
the reason is worth stating rather than working around. Committing this page moves the commit
the artifact is stamped with; re-emitting to restore the stamp moves the digits; correcting
the page to match moves the commit again.

⭐ **What terminates the regress is not quoting intervals — it is saying what the intervals
are.** A first draft of this page quoted the envelope of the runs it was drafted from, as
though a further run would fall inside it; the very next emission fell outside in twelve
places, by one to five per cent. Every figure here is now labelled as the **range observed so
far**, beside the **measured** run-to-run movement, and a shipped number a few per cent
outside one of these ranges is what this page predicts rather than a discrepancy with it.

---

## What this cannot say

⛔ **These are not published performance figures and no consumer may adopt one as a budget, a
threshold or a guarantee.** One interpreter, one binding, one build of the library, one
machine, one date. What the file supports is a comparison: which of two operations is larger,
and by roughly what factor.

⭐ **To use a ratio elsewhere, measure the anchor there and multiply.** A Python function that
takes no arguments and returns immediately, called in a loop, is reproducible on any machine
in a few lines. A ratio published here with an anchor measured there is the only form of this
measurement that transfers — and it is the reason the anchor is a rung of the ladder rather
than an implementation detail of the harness.

⚠ **The two halves of the ladder are not one scale.** The loop that iterates a pre-built run
of argument tuples was measured at **0.81 to 0.90** of the loop that calls with a fixed tuple,
on the same callee in the same rounds — a real difference, not a rounding one. So the
artifact publishes that factor as its own row, and never divides a rung measured by one loop
by a rung measured by the other. ⭐ That row was written expecting to read one; it does not,
and that is precisely why it is a row rather than an assumption.
