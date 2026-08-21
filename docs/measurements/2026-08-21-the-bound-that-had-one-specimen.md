# The bound that had one specimen · 2026-08-21

> ⭐⭐⭐ **THE ACCEPTING BOUND ARMED LAST SESSION WAS THE SUPREMUM OVER THE ONE RENDERING OF
> NOISE THIS REPOSITORY HELD, AND THE SECOND SPECIMEN MOVED IT BY THREE ORDERS OF MAGNITUDE.**
> `LEAST_EXTENT_AN_ACCEPTANCE_DISCRIMINATES_AT = 315` said *at or above this extent, clearing
> the recurrence floor says something about a copy*. Thirty-two further renderings of noise,
> drawn from the same public collection by two declared draws, say otherwise: one of them
> carries no language at all and **clears the floor over windows of 320 000 characters** —
> 96.69 % of itself. ⇒ The number is **1 016× higher**, it is a **maximum and not a bound**,
> and the guard has been **disarmed** rather than raised.

---

## 0. Where this came from

The previous session closed with this as its top open item:

> 1. ⚠ **The accepting bound has n = 1.** Nothing held out speaks to it — everything held out
>    is language. **A second rendering of noise is the measurement.** ⇐ the top open item.

It was the right item and it was under-stated. The answer is not that the number needed
another data point; it is that the quantity the number claims to bound is not controlled by
the extent at all.

---

## 1. Where a second rendering of noise comes from

The one this repository holds is `in.ernet.dli.2015.486584` — a Digital Library of India item
whose archive.org DjVu reading was produced by a reader set to an Indic script over a book
printed in English, and returned a quarter of a million characters carrying no Latin letter.

⭐ So the specimen is not a thing to be constructed. It is a **failure mode of a public
archive**, and the archive is full of it. Two draws were declared before either was read:

| draw | shape |
|---|---|
| **first** | the head of the collection, ascending identifier order, 20 identifiers |
| **second** | for each of the 36 leading characters an identifier may start with, the item at positions 1, 500 and 1000 of that bucket |

⛔ **THE FIRST DRAW'S SHAPE WAS ITS ANSWER.** Identifiers are adjacent because items were
uploaded together, so its seven noise copies were three works in three batches — an
*Encyclopaedia of Religion and Ethics*, a *Collected Works of Korean Buddhism*, and one other.
A rate read off that draw is a rate about three batches. The second draw partitions instead.
⭐ Both are published; discarding the first after seeing its numbers would be selection.

| | first draw | second draw |
|---|---|---|
| drawn | 20 | 106 |
| position beyond the bucket | — | 46 |
| no machine reading published | 0 | 3 |
| the archive would not serve it | 12 | 6 |
| **read** | **8** | **51** |
| below the floor | 7 (88 %) | **27 (53 %)** |
| — of those, refused for their EXTENT | 0 | 2 |
| **certified renderings of noise** | **7** | **25** |

⇒ **32 new specimens**, and with the copy already held, **33**.

> ⭐⭐ **THE CENSUS IS ITSELF A FINDING.** On the scattered draw, *more than half* of this
> archive's published machine readings fall below the floor this repository refuses copies
> with. A rendering of noise is not an exotic failure; it is the common case in this
> collection.

### 1.1 ⛔ The two the guard threw out, and why that matters

Two copies fell below the floor and are **not** in the specimen set: a 220-character
photograph caption and a 4 932-character fragment. Both are under
`LEAST_EXTENT_A_REFUSAL_DISCRIMINATES_AT`, so the floor refuses them **for their extent**, and
a copy refused for its extent is not certified noise. That is the distinction the fifteenth
session's bound exists to draw, and the census made exactly the error it exists to prevent on
its first pass.

> ⛔⛔ **AND THE ERROR WAS A SUBSTRING MATCH THAT READ A DENIAL AS A VERDICT.** The census
> classified a refusal by looking for *"a machine reading that returned noise"* in the message
> — and the **extent** branch's message contains that exact phrase, negated: *"Nothing measured
> says this is a machine reading that returned noise."* ⇒ ⭐⭐⭐ *A check that matches on a
> substring will match the sentence that denies it.* The extent branch is now tested first,
> in the generator and in the census both.

---

## 2. What the specimens say

For each specimen: the largest extent at which **any window of it still CLEARS** the floor —
every offset, not a sample, on a declared grid.

| specimen | its own share | how far below the floor | largest extent that clears |
|---|---|---|---|
| `biharthehomelandofbuddhism` | 0.00006 | 167× | — none |
| `m.hiriyannacommemorationvolume` | 0.00002 | 500× | 500 |
| **the copy already held** | **0.00018** | 56× | **314** |
| `06kssayingsoflalleshwari` | 0.00042 | 24× | 1 000 |
| `01wonhyoweb…koreanbuddhism` | 0.00473 | 2.1× | 5 000 |
| `60yearsofchinesemisrule…` | 0.00577 | 1.7× | 50 000 |
| `02chinulweb…koreanbuddhism` | 0.00630 | 1.6× | 100 000 |
| `04hwaomiweb…koreanbuddhism` | 0.00737 | 1.4× | 150 000 |
| **`TheTheoryOfTheSamdhis…`** | **0.00967** | **1.03×** | ⛔ **320 000** |

⭐ **A control first.** Three independent instruments — a standalone sweep, a one-per-cent
grid search, and the module's own new `largest_extent_at_which_a_window_clears` — all return
**314** for the copy already held. The old number reproduces exactly. What changed is the set
it is a maximum over.

### 2.1 ⭐⭐⭐ What the number is a function of — and it is not the floor

Read the table down the middle column. **The extent at which a specimen stops clearing rises
with how close that specimen's own share sits to the floor**, across all thirty-three. That is
not a fact about how long a window has to be before it means something; it is arithmetic. A
copy sitting 1.03× under the floor has windows above it nearly everywhere; a copy sitting 500×
under has them nearly nowhere.

> ⇒ ⭐⭐⭐ **THE ACCEPTING SIDE IS BOUNDED ONLY BY THE SIZE OF THE NOISIEST COPY ANYONE
> HAPPENS TO HOLD.** 320 000 is a lower bound on itself. A larger copy sitting at 0.0099 would
> move it again, and nothing rules one out.

### 2.2 The mechanism — why noise repeats at all

A machine reading is a **deterministic function of the printing**. A word the printing repeats
meets the same broken reader every time and produces the *same* garbage string, so the
printing's own recurrence survives into the noise. Two mechanisms were read directly out of
the clearing windows:

* in `04hwaomi`, the fragments recurring across a clearing window are **garbled body text**,
  the same twelve characters ten times over — a technical term the book repeats;
* in `02chinul`, they are `', 106, 286, '` and `'1.55, 286 7.'` — **the page numbers of a
  bibliography**, which the wrong-script reader got right because digits survived it.

⛔ So "a rendering of noise" is not uniformly noise, and the floor's binary has no third
category for *a reading that got the digits and none of the words*.

### 2.3 ⚠ And the two sides of the floor meet at copies that differ by far more than 4 %

`TheTheoryOfTheSamdhis` sits at **0.00967** and is refused as noise: an English monograph of
1978 — *"PRICE Rs. 45.00"*, *"No part of this book may be reproduced"* — read by a Devanagari
OCR, carrying no English at all. `uchchatar-sanskrit-pathavali` sits at **0.01009** and is
**accepted**: a Devanagari textbook read in Devanagari, half its words right and half
destroyed. ⚠ The two are 4 % apart across the floor and are not 4 % apart in what they are.
⛔ This is not a claim that the floor is wrong — the second copy does contain real repeated
language. It is the margin, stated.

### 2.4 ✅ Not a decode artifact

Every one of the 33 specimens is **valid UTF-8 with zero replacement characters**. A run of
`U+FFFD` would have inflated recurrence exactly where it matters, and there is none.

---

## 3. The repair

### 3.1 The constant is renamed to what it is

`LEAST_EXTENT_AN_ACCEPTANCE_DISCRIMINATES_AT = 315` →
`GREATEST_EXTENT_AT_WHICH_A_RENDERING_OF_NOISE_HAS_CLEARED = 320000`.

⛔ The old name asserted a bound. Nothing establishes one. The new name asserts a **measured
maximum**, and the docstring says at the point of reading that it is a lower bound on itself.

### 3.2 The guard is disarmed on the accepting side

⛔⛔⛔ **ARMED AT 315 IT WAS WORSE THAN ABSENT.** A caller reads what a guard passes as
checked. Firing at 315 it refused copies under 315 and passed everything above — which
certified the entire band from 315 to 320 000, and that band is where every copy anyone would
offer lives.

⚠ **And it cannot be raised.** Measured, not argued: setting the constant to a true value and
running the suite fails **44 of 452 tests**, and the copies it refuses include every fixture
every attestation and absence in the module is built on. The largest of them is 8 399
characters — thirty-eight times under the number. Growing a fixture is not a route to arming
this side.

> ⭐⭐⭐ **THE FIFTEENTH SESSION'S REASON WAS RIGHT AND THE NUMBER IT WAS ARGUED WITH WAS
> WRONG.** It declined to arm this side saying *refusing every copy shorter than six thousand
> characters would refuse every fixture the suite is built from*. The sixteenth overturned
> that as having used the **refusing** side's number, and armed at 315. The accepting side's
> own number says the same thing the fifteenth session said, **1 016× louder**.

### 3.3 What replaces the refusal is not silence

Every row `recurrence_of` returns carries:

* `the_greatest_extent_at_which_noise_has_cleared_this_floor` — 320 000;
* `this_copy_is_longer_than_that` — a boolean;
* `a_high_share_here_is_about_the_copy` — which **used to be `True`** for every real copy and
  is now a sentence beginning *"⛔ NOT ESTABLISHED AT ANY EXTENT"*.

⭐ That last field is the whole of the correction in one place: it is exactly the shape of row
that certified something nothing measured.

---

## 4. The specimens are held, and the guard certifies them

All 32 are registered in `texts.py` and acquired like every other copy — to the network, with
the retrieval written down beside the bytes. ⛔ They are **not held as texts**: nothing
resolves a locus in them, no claim is attributed to them, and their extent is nothing. A
`Source` with a shared `_a_specimen_of_noise_extent` says so in its own words.

⭐ **And the generator does not take this file's word for what they are.** Each specimen is
offered to `refuse_a_rendering_that_does_not_repeat`, and the control holds only if **every
one** comes back refused *for its rendering*.

⚠ 14 of the 32 acquisitions failed on the first pass with HTTP 500 — the same intermittent
rate the draws saw. `acquire` refused to write a record for a retrieval that did not happen,
which is why the failures were visible rather than silent. Three retry rounds cleared them.

---

## 5. The new measurements, and the control that tells two rules apart

`largest_extent_at_which_a_window_clears(edition, *, grid)` and `one_per_cent_grid(length)` are
in `textual.py`, so the generator re-measures rather than quoting.

⛔⛔⛔ **THE SUPREMUM, NOT THE FIRST EXTENT THAT CLEARS NOTHING.** That rule put the *refusing*
bound 1 686 characters wrong, and the count is not monotone on this side either — one specimen
clears 21 850 windows at 100 000 and 25 497 at 150 000.

⭐ The two rules are told apart by a fixture built from the real mechanism: two copies of one
passage separated by a stretch that repeats nothing are invisible to every window shorter than
that stretch. The copy clears at 300–1 200, **refuses across a 6 600-character band**, clears
again at 8 500–19 000, and refuses above 20 000.

| rule | answer |
|---|---|
| *the smallest extent at which nothing clears* | 1 400 |
| **the supremum** | **19 000** |

⇒ **13.6× apart**, and the wrong rule is the one that looks safe. ⭐ The losing rule is
computed in the test rather than described, because a rule nobody computes is a rule nobody
has checked.

---

## 6. The disarming sweep, and two gaps it found in itself

Ten disarms, each applied to the module, the suite run with `sys.executable` and
`PYTHONDONTWRITEBYTECODE=1`, and **a green baseline checked first** — so a "caught" reading
cannot be a pre-existing failure.

✅ **10 of 10 caught.** ⛔ But **the first pass read 8 of 10, and both misses were defects in
the sweep rather than in the suite**:

* one disarm's target string did not match at all, and the sweep printed *"could not disarm"*
  — ⭐ which is the right thing to print, and is the only reason it was not silently scored;
* the other *claimed* to truncate the specimen table and actually **prepended a decoy and kept
  all thirty-three entries**, so the suite passed because nothing had been disarmed.

> ⚠ **A DISARM THAT DOES NOT DISARM SCORES AS AN ESCAPE, AND AN ESCAPE IS READ AS A GAP IN
> THE SUITE.** Both readings pointed at the tests when the fault was in the instrument
> measuring them. That is the fourth session running in which something measuring this
> repository was itself the subject.

Two controls were added because the sweep showed nothing would have caught them:

* **`test_the_extent_refusal_contains_the_noise_sentence_negated`** — the ordering that the
  census got wrong (the two copies the guard threw out) is invisible to every other test, because every specimen held is far
  above the refusing bound and on that set the two orders agree.
* **`test_the_specimens_the_accepting_side_rests_on_are_still_there`** — the constant is a
  literal and the specimens live in another module, so silently losing them would leave the
  number standing on the one copy it stood on before, with nothing noticing.

---

## 7. ⛔⛔⛔ And the leak check was disarmed by a pipe

The publication guard, `tools/check_public_tree.py`, found a reserved pattern in **this
document** — three `§`-plus-number section references, which are the shape of a citation into
a private specification. That is the guard doing its job on prose written this session.

⛔⛔⛔ **BUT IT WAS RUN AS `python tools/check_public_tree.py 2>&1 | tail -3 && git commit`,
AND A PIPELINE'S EXIT STATUS IS THE LAST COMMAND'S.** `tail` succeeded, so `&&` proceeded and
the commit landed with the pattern in it. The failure text was printed and read as ordinary
output.

> ⭐⭐⭐ **A CHECK WHOSE VERDICT IS CARRIED BY AN EXIT CODE IS DISARMED BY ANYTHING
> DOWNSTREAM OF IT.** The guard was not weakened, misconfigured or skipped. It ran, it was
> right, and its answer was thrown away by the shell one character at a time.

⭐ Recovered as the guard's own text prescribes: nothing had been pushed, so the three
commits were rewritten rather than corrected forward, the reflog expired and the objects
pruned — because ⛔ **the check scans reflog-reachable objects too**, and reported the pattern
still present in the dangling commits until they were gone. It is right to: an unreachable
commit is still in the repository.

⚠ The rewrite folded three commits into two. The middle one was a one-line fix to a sort key
naming a field its own row does not carry — a defect in the first commit, so folding it in is
the more accurate history, not a loss.

---

## 8. The re-emission

**39 byte-identical · 9 changed · 1 added · 0 removed**, 59 → **60** rows, accounted by row
identity rather than position, and **byte-identical on re-run**.

At key level, every field that moved:

| row | what moved |
|---|---|
| header | `generator.commit`, `generated`, and the new control's name in the roster |
| 6 rows carrying a recurrence measurement | the five fields of the recurrence row |
| `resolving_exactly_once_is_free_in_a_rendering_that_repeats_nothing` | the same five, across seven copies |
| `below_a_measured_extent_this_floor_refuses_real_books_too` | the constant swap, and its `meaning` |
| `the_three_constants_measured_against_text_they_were_not_fitted_to` | its `meaning`, its `what_this_does_not_measure`, and ⭐ **`held_out_bodies[3]`** |
| **added** | `the_accepting_side_measured_over_more_than_one_rendering_of_noise` |

⭐ `held_out_bodies[3]` is *this repository's own program text*, and it moved because
`textual.py` and `texts.py` moved. Its own entry says it grows whenever that file does, so the
change is the docstring being right rather than a measurement drifting.

⛔ Rules, refusals, corroborations, alignment, hands, naming and foreword rows are **untouched**.

---

## 9. What this leaves open

1. ⚠ **320 000 is a lower bound on itself.** Every specimen is from **one archive** and one
   OCR pipeline. A different digitiser's failures are not represented.
2. ⚠ **A window of a copy is still a proxy for a short copy**, as a block was and as it was
   last session. Neither is the same thing as a copy that is only that long — ⭐ though the
   proxy is now far less flattering: the highest specimen's clearing window is 96.69 % of the
   whole copy, which is nearly the copy itself.
3. ⬜ **The floor's own boundary is untested in the neighbourhood found here.** The margin measured above puts a
   certified rendering of noise at 0.00967 and an accepted real reading at 0.01009. Nothing
   measures how many real copies live under 0.01.
4. ⬜ The scattered draw reaches **positions 1, 500, 1000** of each bucket only; buckets with
   fewer items yielded fewer specimens, and 46 of 106 draws fell beyond their bucket.
5. ⬜ Carried forward unchanged: a second machine reading of the fifth edition (priced only),
   no earlier printing reached, the registry-row pair, R4 has no generator, and the kernels
   still under a session scratch directory.
