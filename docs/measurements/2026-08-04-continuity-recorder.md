# Sampling an implementation so its answers outlive it

**2026-08-04.** Generator `generators/r5_continuity.py`. What follows is what was measured
while building a continuity corpus — a recording of what one implementation answered, taken
while it still ran.

⛔ **Recorder, never explainer.** Nothing here describes how the sampled implementation
computes anything. Every finding below is about the *recorder*.

---

## Why this recorder has a deadline and the others do not

A kernel can be read again next year. A published table can be re-fetched. An
implementation cannot be sampled once it stops running, and **nobody gets to ask it a new
question afterwards**. That asymmetry is the whole design pressure:

⭐ **Every input a row leaves *unresolved* is a piece of the sampled service's state that the
row still depends on.** A local clock reading still needing a timezone database is not a
recorded input; it is a promise that some future reader will have the same database. A place
name still needing a geocoder is worse — a third-party service is not recoverable by
restarting the implementation you sampled.

So the recorder resolves them into the row: the **UTC offset** beside the local reading, the
**coordinate** instead of the name. Reading the corpus later needs no timezone database, no
place-name service, and nothing switched back on.

⭐ **This is enforced by a vocabulary, not by a convention.** A call surface may bind an
argument only to names in `surface.RESOLVED_FIELDS`, and there is deliberately **no name for
an unresolved input** — so a sampled call *cannot* be declared in a way that depends on
deployment-held state.

⚠ **The rule generalises past this corpus**: the set of things that must be captured before
a service goes away is not a property of the data. It is a property of the export format.

---

## 1. ⭐ THE CORPUS WAS NON-REPRODUCIBLE BY CONSTRUCTION, AND IT LOOKED FINE

The first regeneration in a clean environment differed from the original. Not a dependency
difference, not the platform: **a sampled call had an argument that defaulted to *"now"***.
Every row carried the moment of sampling, and — much worse than the visible timestamp — a
flag on every period was a function of *when the recorder ran* rather than of the input.

⚠ **A leaf-level diff understated it.** Two runs seconds apart move the timestamp and not
yet the flags, so the diff showed **1 leaf of 144**. A rerun next year would move both, and
every future comparison against this corpus would fail for a reason that has nothing to do
with either implementation.

⛔ **This is what a demonstration is for.** The argument that the corpus was reproducible had
been made, was reasonable, and was wrong — and nothing in the artifact showed it. An
assertion of reproducibility that nobody has executed is not evidence.

### The general guard that came out of it

A recorder cannot inspect a call for hidden state. It can **catch** it: sample one input
twice and refuse if the two disagree. One grid point buys detection of the entire class — a
clock read inside the callee, a random draw, an unordered iteration, a warm cache.

⚠ **And the first version of that guard was itself too weak.** Calling each section twice
back to back cleared **7 of 17** sections that were *all* clock-dependent, because both calls
landed inside the same microsecond. Sweeping every section before repeating any caught
**17 of 17**.

⭐ **A detector, not a proof**, and it says so: a section it clears is not thereby proven
stable; one section it reports is enough to refuse. There is no permissive mode — the remedy
is always to pin the varying input in the declaration, because **an input nobody wrote down
is an input nobody can reproduce**.

---

## 2. ⭐ An input is more determinism-bearing than an output

A recorded value only has to be **compared**. An input has to be **replayed**. A coordinate
that reparses one unit in the last place away regenerates a different result, and the
difference is then attributed to the implementation rather than to the reader.

⚠ Not hypothetical: a widely-used JSON library was measured mis-parsing **18.9 %** of
shortest-round-tripping doubles by up to **2 ULP**, and it corrupted an unrelated parity
measurement by four and a half orders of magnitude before anyone suspected the parser.

So every determinism-bearing double in these files — recorded values **and** the coordinate
inputs — carries a hex bit pattern, and the decimal beside it is display. Whole-second
offsets and ISO-8601 text cross a text boundary exactly and need no companion.

Two consequences that are easy to miss:

* ⭐ **The content digest is taken over the authoritative form.** Hashing the decimal would
  make the digest reproducible only by something that also reproduces this writer's float
  formatting — and checkable only through the one path that must never be load-bearing. A
  consumer with a mis-parsing reader could fail the digest while holding the correct value.
* ⛔ **The two forms are checked against each other per row, at write time**, and the check
  compares through the *pattern*, not through `==`: `-0.0 == 0.0` is true, and preserving the
  sign of zero is one of the reasons the hex form exists. If the forms ever disagreed, a
  consumer reading the decimal and one reading the bits would hold different numbers from the
  same row and neither could tell — worse than a missing value, because both look correct.

---

## 3. ⭐ A bounded sample that is the right size and the wrong shape

The grid is bounded by a requested count. The first selection cut a year-major enumeration
at that count and **aliased against the site count**: it returned exactly the requested
number of rows while covering **4 of 16 sites**, and the two it lost were the polar and
equatorial ones — the two places behaviour differs most.

⭐ **Nothing in the output said so. A row count reads as coverage.** This is the failure mode
that bounding a corpus by a count invites, and it is the reason the selection is now explicit
about the property it owes: round-robin across strata, each drawn in low-discrepancy order,
pinned by property tests over the grid rather than by an example.

---

## 4. The sampled implementation's own names must not become the fixture's keys

Returned objects are flattened to `{"path": ..., "number": ..., "bits": ...}` records, which
puts the sampled tree's field names on the **value** side.

Serialising a returned object as-is copies those names straight into the evidence: they
become permanent identifiers, they break a `lower_snake_case` key rule the moment one is
capitalised or numeric — both occur — and a rename in the sampled tree silently renames the
evidence. As leaf *paths* they are simply data about what was sampled.

⚠ It is also the only shape a continuity comparison can use. Continuity is asked one leaf at
a time — *"did this number move?"* — so a corpus that must be re-walked before it can be
diffed answers the question later and more expensively than one that is already a list of
addressed values.

---

## 5. A refusal by the sampled implementation is evidence, not an error

**56 calls were declined**, every one of them a house calculation above the polar circle, and
only for the sections that need houses — other sections at the identical instants answered
normally. It is correct behaviour, and it is now **recorded in the artifact as a fact about
that implementation** rather than lost.

⭐ A later implementation that *returns* something at those latitudes is a behavioural
difference this corpus captures. A recorder that swallowed the refusal, or dropped the row,
would have destroyed exactly that.

⛔ For the same reason a refusal is never fatal and never silently skipped: a dropped row is
a hole in a corpus that reports its own coverage by counting.

---

## 6. Transition readings are refused, not folded

A local clock reading inside a daylight-saving transition is either **two instants or none**.
Choosing a fold is a decision the recorder is not entitled to make, and one chosen silently
would be invisible in the fixture forever. So `resolve()` refuses it, the grid moves to an
unambiguous reading, and the row **says by how much it moved**.

---

## 7. Which timezone rule set answered is not knowable, so the offset is what travels

`zoneinfo` searches a filesystem path first and falls back to a packaged rule set only if the
key is not found there — and **it does not report which one answered**.

⭐ **Measured on the recording host: the search path was empty**, so the packaged rules (IANA
**2024b**) supplied every zone. A deployment on another operating system would have used its
own system database. **Same pinned requirements, two different rule sets.**

⚠ Which is precisely why the *offset* is the authority on each row and the database identity
is recorded only as context. A later run that disagrees with a recorded offset has found a
rule change — a finding, not a reason to prefer the fresher answer.

---

## 8. The demonstration

| | |
|---|---|
| Grid | 224 points — 14 epochs × 16 sites, strata: general, historical offset, far future, polar, equatorial |
| Rows | 4 200 over 19 sections, **all 4 200 row digests distinct** |
| Leaves | 845 442 addressed values |
| Size | **53 968 120 bytes**, plain text, **0 non-ASCII bytes** |
| Wall clock | **~5 s** |
| Refusals | 56, all recorded |

**Regenerated in a clean environment built from the pinned requirement set** — a separate
interpreter and a separate set of installed packages, sharing no state with the development
environment:

> ⭐ **Byte for byte identical.** 53 968 120 bytes, `cmp` clean.

⚠ **What that does and does not establish.** It establishes that the corpus does not depend
on accumulated local state, and that a fresh resolution of the pinned requirements produces
the same values. It does **not** establish platform independence: the host block records the
operating system by design, so a run elsewhere differs there — and this is the demonstration
that had already failed once, before the clock-dependent input was pinned.
