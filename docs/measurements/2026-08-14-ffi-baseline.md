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
| the loop, with no call in it | — | **0.36 – 0.43** |
| a Python function, one argument | 1 | 1.03 – 1.06 |
| a Python function, four arguments | 4 | 1.21 – 1.30 |
| a standard-library C function, no arguments | 0 | 0.96 – 1.12 |
| **the binding, no arguments** | 0 | **0.96 – 1.12** |
| **the binding, one argument** | 1 | **1.5 – 2.2** |
| **the binding, four arguments** | 4 | **2.4 – 3.5** |
| the binding, one body's position | 3 | **≈ 200** |
| the binding, a full set of house cusps | 4 | **≈ 130** |

The ranges are across the three call-site forms — see below, because that spread is a
finding rather than an error bar.

---

## 1. ⭐ The empty crossing is not the binding's cost

A binding call carrying **no arguments** costs **what a Python function call costs** —
0.96 to 1.12 anchors, and a standard-library C function of the same arity lands on the same
number to within the same spread.

⛔ **So the empty round trip is CPython's own call protocol.** A probe that reports it as
"the cost of the binding" has measured the interpreter and attributed the result to the
library. This is the reason the ladder carries a pure-Python rung *and* a C rung at every
arity a binding rung is measured at, and the reason that requirement is enforced as a control
rather than left to whoever assembles the list.

---

## 2. What *is* attributable is marshalling, and it grows with the argument count

| | against the same-arity Python function | against the binding's own zero-argument rung |
|---|---|---|
| one argument | **1.4 – 2.1** | **1.6 – 2.0** |
| four arguments | **1.9 – 2.9** | **2.4 – 3.4** |

The same comparison inside pure Python moves far less: one argument costs 1.03 anchors and
four cost about 1.25.

⚠ The C comparator is an **upper** bound on the interpreter's own share, never a floor: the
standard-library function used at those arities does a small amount of real arithmetic, which
is why it is quoted as a bound rather than subtracted.

---

## 3. A call that does work dwarfs the crossing

One body's position: **about 200 anchors.** A full set of house cusps: **about 130.**

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
| a Python function, one argument | 1.06 | 1.03 | 1.03 |
| a Python function, four arguments | 1.21 | 1.27 | 1.30 |
| **the binding, one argument** | **1.54** | **2.14** | **2.15** |
| **the binding, four arguments** | **2.35** | **3.43** | **3.45** |

⭐ **The pure-Python rungs barely notice; the binding rungs move by about 40 %** — comparable
to the entire cost of an empty crossing. The direction is worth reading: handing this binding
a pre-built tuple is the **cheapest** form, while for the anchor it is the dearest.

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
| the binding, one argument | 0.98 |
| the binding, four arguments | 1.00 |
| **the binding, one body's position** | **≈ 33** |
| the binding, a full set of house cusps | 1.01 |

⭐ **The position call answers a repeated request about thirty-three times more cheaply than a
new one.** Measured only the ordinary way, it reads as **six** times the crossing; measured
over distinct instants it is **about two hundred** times the crossing.

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
| the anchor against a second reading of itself | 1.0 | **0.993 – 1.002** |
| every arity a binding is measured at also has a pure-Python and a C rung | none missing | none missing |
| a pair built to perform the anchor a hundred times | ≥ 20 | **66 – 80** |
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

**What a re-run should reproduce**

* the ordering of the ladder, **for every pair the artifact reports as having held in every
  round**. That claim is made pair by pair rather than over the whole list, because rungs the
  harness cannot separate change places for no reason but noise — and the artifact publishes
  both sets, with each pair's own ratio, so the obvious hypothesis can be checked instead of
  taken. In the run recorded here, 75 to 89 of 91 pairs held in every round, and the ones that
  did not are the pairs whose ratio is one within its own spread;
* each ratio, within the spread stated on its own row;
* every verdict: the four controls, and each rung's repetition sensitivity.

**What a re-run will not reproduce** — any nanosecond figure, the exact digits of any ratio,
the spreads themselves, or the ordering of the pairs the file reports as changing places.

⛔ **A byte comparison of this file reports a difference every time and means nothing by it.**
Compare orderings and check that each ratio's interval overlaps.

⚠ **A write-up of a timing probe cannot quote the shipped artifact's own digits either**, and
the reason is worth stating rather than working around: committing this page moves the commit
the artifact is stamped with, and re-emitting to restore the stamp moves the digits. The
figures above are from the runs this page was written from; the shipped file carries a later
run's. What they share is every ordering, every verdict, and every factor to the precision
quoted here — which is exactly the claim the file makes about itself.

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
of argument tuples was measured at about **0.85** of the loop that calls with a fixed tuple,
on the same callee in the same rounds. So the artifact publishes that factor as its own row
and never divides a rung measured by one loop by a rung measured by the other.
