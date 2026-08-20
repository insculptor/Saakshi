# The word "complete" was true of the wrong noun · 2026-08-20

> ⭐⭐⭐ **THE BOUND ARMED LAST SESSION WAS READ OFF A FUNCTION THAT IS COMPLETE OVER A COPY'S
> CHARACTERS AND READS 0.017 % OF ITS SPECIMENS.** `LEAST_EXTENT_A_REFUSAL_DISCRIMINATES_AT`
> was taken from `blocks_this_floor_refuses`, which tiles each copy into consecutive disjoint
> blocks from offset zero — every character in exactly one block, no overlap, and the
> docstring says so truthfully. But the question a bound on the extent asks is *is there a
> specimen of real text this long that this floor refuses?*, and the specimens are the copy's
> **windows**. At six thousand characters one tiling phase reads **283 of 1 675 741** of them.
> ⇒ Asked of every window, 6 000 refuses **5 593**, and the bound is **7 686**.

---

## 0. Where this came from

The previous session closed with two open items and this is both of them.

> 1. ⬜ **Arm the accepting side, or leave it?** ⛔ It cannot be armed the way the refusing
>    side was — refusing every copy under 6 000 chars would refuse every fixture in the suite.
> 7. ⚠ **THREE constants now fitted to ONE set of copies** — the fragment length (12), the
>    floor (0.01) and the extent (6 000). A copy disagreeing with all three would look like
>    one disagreeing with none.

Answering item 1 meant measuring the accepting side, and measuring the accepting side meant
re-measuring the refusing one on the same instrument. That is where the constant came apart.

---

## 1. The measurement

`every_window_of(edition, extent=..., length=12)` asks the floor of **every window of one
extent, at every starting offset** — one fragment out, one fragment in, an incremental
counter over the whole copy. Both sides are counted, because which of them is the error
depends on what the copy is: for a real book a refusal is the error, for a rendering of noise
a clearance is.

Over the same seven renderings the constants were fitted to — six real copies and the machine
reading that returned noise:

| extent | windows of the six real copies refused | windows of the noise that CLEAR |
|---|---|---|
| 200 | 1 405 161 of 1 710 541 | 109 |
| 300 | 1 176 768 of 1 709 941 | 207 |
| **310** | 1 176 300-odd | **217** ← the accepting side's last failure |
| **315** | — | **0** |
| 1 000 | 406 896 of 1 705 741 | 0 |
| 5 000 | 16 021 of 1 681 741 | 0 |
| **6 000** | ⛔ **5 593** of 1 675 741 | 0 |
| 7 000 | 309 of 1 669 741 | 0 |
| **7 685** | **1** of 1 665 631 | 0 |
| **7 686** | **0** of 1 665 625 | 0 |

⭐ **A control first.** The new instrument reproduces the published tiling table exactly at
phase zero — 7 036 of 8 555 at 200, 3 930 of 5 704 at 300, **0 of 283 at 6 000**. So the old
table was not arithmetically wrong. It was right about a subject that was 0.017 % of the
question.

---

## 2. ⛔⛔ And it is not a threshold, because the count is not monotone

| extent | real windows refused |
|---|---|
| 7 350 | 3 |
| 7 430 | 1 |
| 7 450 | **0** |
| 7 500 | 42 |
| 7 550 | **0** |
| 7 650 | 36 |
| 7 685 | **1** |
| 7 686 | **0** |

⇒ *The smallest extent at which nothing is refused* — the rule 6 000 was picked by — is not a
bound at all. On this grid that rule would now pick **7 351**, and three separate bands above
it still refuse. What is published is the **supremum**: 7 685, checked at every extent to
7 780, every ten to 8 800, every fifty to 9 000 and every five hundred to 30 000.

---

## 3. ⛔⛔⛔ The fixture went back under the bound — the third session running

`A_RENDERING_OF_NOISE` was grown last session from 1 799 to **7 199** characters precisely so
it would clear a `LEAST_EXTENT_A_REFUSAL_DISCRIMINATES_AT` of 6 000 and be refused for what it
*is* rather than for its size. The moment the constant was re-measured to 7 686, that repair
was under the bound again — and every test certifying *the instruments refuse the rendering of
noise* was **again** certifying a refusal the fixture's size had earned.

> ⭐⭐⭐ **A FIXTURE SIZED TO A FITTED CONSTANT IS ONLY AS SOUND AS THE CONSTANT, AND IT FAILS
> SILENTLY IN THE DIRECTION THAT LOOKS LIKE SUCCESS.**

Both undersized copies — 1 799 and 7 199 — are rebuilt in the suite and shown to earn the
extent cause. The copy standing there now is shown to earn the *rendering's* cause, which is
the positive half: without it the test passes at any size.

* 14th session: every copy built in the test file repeated nothing.
* 15th session: the copy built to *be* noise was too small for that to mean anything.
* 16th session: the copy grown to fix that was sized to a constant that moved.

---

## 4. ✅ Item 1 — the accepting side is ARMED, at 315

The reason published for leaving it was:

> *refusing every copy shorter than six thousand characters outright would refuse every
> fixture the suite is built from*

That is **true, and it is about the refusing bound**. The accepting side has its own, and it
is the largest extent at which any window of the rendering of noise CLEARS the floor: **314**,
three of 286 fragments coming round twice for a share of 0.01049. Twenty-four times smaller.

> ⭐⭐⭐ **A DECISION NOT TO ARM ONE SIDE WAS TAKEN ON THE OTHER SIDE'S NUMBER.**

`refuse_a_rendering_that_does_not_repeat` now refuses a copy that *clears* the floor while
carrying fewer than 315 searchable characters, naming that cause and not borrowing the
refusing side's. The cost was two fixtures, which grew:

| | was | is | bound |
|---|---|---|---|
| `SECOND_TRANSLATION` (the attesting copy) | 225 | **381** | 315 |
| `A_COPY_THAT_REPEATS_BUT_LACKS_THE_PASSAGE` | 117 | **342** | 315 |
| `A_RENDERING_OF_NOISE` | 7 199 | **8 399** | 7 686 |

⭐ Grown with **new prose**, not with more repetitions of the line the fixture already
repeats: padding a copy with its own refrain raises the recurrence share by making it *less*
like a book, which would be the measurement pointing at its own fixture.

⇒ **Between 315 and 7 686 characters a pass means something and a failure does not.** Neither
constant alone describes that band, and it is most of the interesting range.

⚠ The accepting bound is fitted to **one** copy — the single rendering of noise held here —
where the refusing bound has six. It is the weaker of the two numbers and the constant says so
at the point of reading.

---

## 5. ✅ Item 7 — the three constants, measured against text they were not fitted to

The worry was an argument, so the answer is a held-out measurement. Four bodies this generator
has never loaded, spanning a second real book of this genre, English legal prose, English
technical prose and program text:

| body | characters | share at n=12 | × the floor | largest extent refused |
|---|---|---|---|---|
| a second real book, never loaded here | 1 401 753 | 0.13879 | 13.9× | 5 000 |
| this repository's licence | 33 690 | 0.10867 | 10.9× | none |
| its documentation | 462 477 | 0.21623 | 21.6× | 7 000 |
| its own program text | 373 568 | 0.15894 | 15.9× | — |
| **its README** | 22 510 | **0.04832** | **4.8×** | 4 000 |
| *the lowest **fitted** copy* | 253 529 | *0.06784* | *6.8×* | *7 685* |
| *the rendering of noise* | 246 777 | *0.00018* | *0.018×* | — |

**All three transfer.** Every held-out body clears the floor at the fitted fragment length,
and each is refused only up to a *smaller* extent than the six fitted copies are — so the
refusing bound is not tight either.

⛔ **But the fitted set is the flattering one.** The closest held-out body stands at 4.8× the
floor where the lowest fitted copy stands at 6.8×: a margin read off the seven alone
overstates the headroom by a third.

⛔⛔⛔ **And it leaves the weakest number untouched.** Every held-out body is *language*, so
every one of them speaks to the floor and to the refusing extent and **none of them speaks to
314**. A second rendering of noise is the measurement that would, and this repository holds
one. Nor is any of these a copy in a third script, or a machine reading by a different reader.

---

## 6. ⛔⛔⛔ Two of ten disarms escaped, and they were the two that mattered

Every guard armed this session was disarmed in turn, with `sys.executable` and
`PYTHONDONTWRITEBYTECODE=1`, against a baseline checked green first. **8 of 10.**

* **`every_window_of` corrupted back into a sampler — NOT CAUGHT.** The instrument that
  replaced a sampler had nothing measuring that it had. The miniature test demonstrating the
  sampling defect still saw a refused region, and still passed, because it only ever asked
  whether *something* was refused. ⇒ It is now checked against a second, **naive** reading of
  its own definition — recounted from scratch at every offset, no shared state, written out in
  the test rather than imported.
* **`windows_cleared` hard-wired to zero — NOT CAUGHT.** The test asserting the two counts sum
  to the total asked it of the rendering of *noise*, where every window is refused and the
  cleared count is zero anyway.

> ⭐⭐⭐ **A CONTROL THAT CANNOT COME OUT WRONG — WRITTEN THIS SESSION, AGAINST EXACTLY THAT
> DEFECT.** It is the fixture-shaped mistake this repository has now made in three consecutive
> sessions, and this time it was made *inside the repair*.

Both repaired; **10 of 10**.

---

## 7. What was emitted

`out/textual/significator-series-rules.jsonl`, **58 → 59** rows, accounted by row identity and
never by position:

**48 byte-identical · 10 changed · 1 added · 0 removed**, byte-identical on re-run.

* header — `generator.commit` and the row count;
* 2 attestation rows, 1 absence row and 5 controls — all carrying `recurrence_of` output,
  which gained the two acceptance-bound fields;
* `below_a_measured_extent_this_floor_refuses_real_books_too` — rewritten on the window
  measurement, publishing both grids and what the tiling actually saw;
* **added**: `the_three_constants_measured_against_text_they_were_not_fitted_to`.

⭐ Rules, refusals, corroborations, alignment, hands, naming and foreword rows **untouched**.

---

## 8. What is still open

1. ⚠ **The accepting bound has n = 1.** Nothing held out speaks to it, because everything held
   out is language. A second rendering of noise is the measurement.
2. ⬜ A **second machine reading of the fifth edition** — priced only.
3. ⬜ **No earlier printing reached** — every digitised printing carries the same foreword.
4. ⬜ **The registry-row pair** is the owner's; `R3-convention` being band-less is an inference.
5. ⬜ **R4 has no generator**; extended-kernel pair undecided; S4–S6 need the sampled tree.
6. ⬜ **Arm the locus, or leave it an address?** Still a test, not a defect.
7. ⚠ **A block of a book is still a proxy for a short copy**, and a window of a book is too.
   Neither is the same thing as a copy that is only that long.
