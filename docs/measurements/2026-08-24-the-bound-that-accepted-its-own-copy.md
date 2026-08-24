# The bound that accepted the copy it was read off — and the extent it was armed without

**2026-08-24 · `2b62c0f` → this session · 507 → 511 tests · artifact 66 → 68 rows**

The twenty-first session armed a refusing instrument made of presences and left, at the top
of its own list of what was open:

> ⛔ **The bound is a lower bound on itself.** It is a minimum over 21 copies; the copy that
> sets it is 53 290 characters and only 1.53× above the fitted midpoint. One further specimen
> at nine thousand would break the separation, and there is no argument here that one does
> not exist.

This session went looking for that specimen and did not need to find one. Asking the
instrument about its **own evidence** answered the item twice over, and neither answer is
about a copy nobody has.

---

## 0. What was measured, and against what

Every quantity below is taken over the 65 copies this repository holds, with the module's own
occurrence finder. Two of them are new closed forms, and ⭐ **both were pinned against the
module's existing binary search before anything was concluded from them**: the closed form
reproduces `least_flank_over_any_declared_language` on **all 65 copies, 0 disagreements**, and
on 119 sampled windows of which **92 had a boundary that cut a word** — the case that would
break a naive derivation, present in the control rather than argued away.

---

## 1. ⭐⭐⭐ The headline — the armed cap accepted the copy it was read off

`LEAST_FLANK_AT_WHICH_A_LOCAL_PRESENCE_IS_FREE_IN_A_RENDERING_OF_NOISE = 16642` is defined,
in its own entry, as

> the smallest flank at which every position of such a copy carries a declared word runs from
> **16 642** (`scienceandtheindiantradition…`, 53 290 characters) to 306 984 … **At or above
> 16 642**, a presence in the flanks of a locus is obtainable in a rendering that carries none
> of the work's words.

**At or above.** The comparison implementing it asked for a flank *strictly greater* than the
cap. So the copy the number was read off — certified a reading in a script its work cannot be
printed in, and the minimum the constant **is** — sat exactly on the cap and was **accepted**.

Measured, not inferred:

| the copy asked in | outcome | flank |
|---|---|---|
| `sa` | ⛔ **accepted** | 16 642 |
| `hi` | ⛔ **accepted** | 16 642 |
| `en` | refused | — (no English word at any flank) |

⚠ It refused under `en` for an unrelated reason — that copy carries no English word anywhere,
so the English list answers `None`. **The one language whose list actually answers to it is
the one under which it passed.**

⇒ the guard now asks at `cap - 1`, and over the census's own statistic:

| | certified wrong-script readings refused | certified readings refused |
|---|---|---|
| as armed | **20 of 21** | 0 of 26 |
| asked at `cap - 1` | ✅ **21 of 21** | 0 of 26 |

> ⭐⭐⭐ **A guard armed at the least value its refusal set takes must refuse AT that value.**
> A separation stated as a strict inequality between two sets is not implemented by a
> comparison that lets the extreme member of one of them through.

⚠ The separation itself is untouched: 8 828 < 16 642 either way. What was wrong is the arm.

### ⭐⭐⭐ And the same boundary, written twice in one session, was right the other time

`least_flank_at_which_a_passage_carries_a_declared_word` — the **passage**-level measurement,
three hundred lines away in the same module and written in the same session — searches
`low, high = 1, cap - 1` and returns `None` when the passage at `cap - 1` carries nothing. Its
docstring says *`None` at or above `cap`*, and it is **correct**.

⇒ the copy-level guard's boundary was not a decision taken and lost; it is an
**inconsistency between two implementations of one sentence**, and only the wrong one was
armed. ⚠ The passage-level number is deliberately left alone: no threshold is published on it
at all, so its boundary carries no claim — see section 4 of the twenty-first session's doc.

---

## 2. ⛔⛔⛔ And below the cap it cannot refuse at all — which is arithmetic, not evidence

The statistic is a **worst case over the copy's own positions**, so it is bounded above by the
copy's own length: the worst position of a copy of *L* characters carrying one declared word
anywhere needs at most *L*.

⇒ **no copy shorter than the cap can exceed the cap.** Below 16 642 characters the guard
accepts whatever carries one of the 69 declared words anywhere at all, and refuses only what
carries none — which is an **absence**, and this repository holds that an absence establishes
nothing. So below that extent its only available refusal is one it does not accept as
evidence.

⚠ **Two of the 26 copies certified as readings are shorter than the cap** —
`gov_in_notification_2022_99` at 1 345 characters and
`30776245teachingsofthesidhaspart3conductenglish…` at 15 365. They are counted as surviving a
refusal they were never at risk of. ⛔ **None of the 21 certified wrong-script copies is that
short**: the shortest is 53 290 and the next-shortest is 217 121, **four times it**. The two
certified sets are not comparable in extent at the bottom, and the bound has never been tested
where it cannot work.

⇒ the guard now returns `cannot_measure` below the cap — an **abstention**, spelled
differently from the refusal on purpose, exactly as the no-word-list case is.

---

## 3. ⛔⛔⛔ The extent the instrument was armed without

`LEAST_RECURRENCE` has two extent measurements standing beside it —
`LEAST_EXTENT_A_REFUSAL_DISCRIMINATES_AT` (below what extent that floor is a test of size) and
`GREATEST_EXTENT_AT_WHICH_A_WINDOW_OF_A_REFUSED_COPY_HAS_CLEARED` (over how long a stretch of
a copy it refuses it can be cleared anyway). Both were found by asking of **every window**, and
both moved a published number a long way — the second by **1 016×**.

**This guard shipped with neither.** Both are asked here, and the answer to a window question
is exact in closed form: a window is accepted exactly when its first occurrence ends within the
flank of its start, its last begins within the flank of its end, and every consecutive pair
inside it meets. Nothing is sampled and no window is skipped.

| | copy | characters | share of itself |
|---|---|---|---|
| longest stretch of a certified **rendering of noise** this guard **accepts** | `thetheoryofthesamdhis…1978` | ⛔ **270 896** | **81.8 %** |
| the same, second | `jaimini_sutras_rao_library_scan` — this repository's own control copy | 212 904 | **86.3 %** |
| longest stretch of a certified **reading** carrying **no declared word at all** | `ajitagamavolin_r_bhatt`, a real book throughout | **17 649** | at offset 2 308 |

Both extremes were verified with the module's **own binary search** on the actual substring,
and ⭐ **one character wider each is refused** — an expected difference, in the control, so a
function returning a one-character window could not have passed.

> ⭐⭐⭐ **17 649 IS ABOVE THE CAP AND 270 896 IS FIFTEEN TIMES ABOVE IT, SO THERE IS NO
> EXTENT BETWEEN THEM.** At every extent up to 270 896 characters both exist: a stretch of a
> certified rendering of noise this guard accepts, and a stretch of a certified reading it
> refuses. ⇒ below that extent the verdict is a fact about **where the copy was cut**, not
> about what the copy is.

### ⭐⭐⭐ And this is what answers the open item

**16 of the 21 certified renderings of noise hold an accepted stretch at least as long as the
whole copy that sets the cap** (53 290 characters):

| accepted stretch | share of the copy | copy |
|---|---|---|
| 270 896 | 81.8 % | `thetheoryofthesamdhis…` |
| 212 904 | 86.3 % | `jaimini_sutras_rao_library_scan` |
| 161 506 | 6.4 % | `encycreligethics_v2…1910` |
| 154 408 | 7.0 % | `encycreligethics_v7…1915` |
| 146 210 | 4.1 % | `encycreligethics_v10…1918` |
| 138 873 | 14.9 % | `annalsofeastindiacompany…1810` |
| 138 326 | 0.4 % | `encofphilosophy10vs` — the largest copy held |
| … | | ten more, down to 53 290 |

⇒ **the specimen whose existence would break the separation does not have to be looked for.**
The item asked whether a wrong-script copy at nine thousand exists and answered *nothing here
argues that none does*. One extent down, the certified evidence already contains sixteen
stretches of noise, at the bound-setter's own extent and far beyond it, that this guard
accepts.

⚠ **What this does and does not establish.** A window of a copy is not itself a certified
copy, and none is ever handed to the guard in this repository. What it establishes is what the
armed bound is a bound **over**: whole copies, of lengths that were never controlled for. A
shorter book read in the wrong script is a stretch, and a stretch is what these are.

---

## 4. ⛔⛔ The extent that would matter cannot be armed here

Refusing every copy shorter than 270 896 characters would refuse **`jaimini_sutras_rao` at
228 420** — the copy every locus in this repository resolves in.

⇒ this repository **cannot require the extent its own measurement says an acceptance needs**,
and it publishes that rather than choosing a number that hides it. What is armed is the
arithmetic threshold, which is derived and not fitted; what is published beside it is a
**measured maximum, not a bound**, in the same terms the recurrence floor's 320 000 is.

⚠ A maximum over 21 copies moves with the 22nd, exactly as the other one moved 1 016× when
its set grew from one member to thirty-three.

---

## 5. Two threads that did not go anywhere, recorded

* ⚠ **Union versus per-language, measured absent.** The census publishes the flank over the
  **union** of the declared lists; the guard reads the flank over the **one** list the locus's
  declared language calls for. These are different statistics, and the second is never smaller.
  Asked of all 65 copies: **no copy here answers to both lists** — every one has exactly one
  list returning a number and the other returning `None`, so the union equals it. ⇒ the two
  cannot be told apart on this evidence, and nothing in the census scores one against the
  other. ⛔ It is not established that they agree in general.
* ⚠ **57 of the 65 copies declare `und`**, so the guard, which routes on a declared language,
  would abstain on them. The bound is armed from copies the guard could not be asked about —
  which is consistent (a `Locus` declares, a census copy does not) and is worth saying once.

---

## 5a. The sweep — 11 of 11, and two of them were unreachable

Every branch added here was patched to a disarmed form and the suite required to fail. Green
baseline first, `sys.executable`, `PYTHONDONTWRITEBYTECODE=1`, every patch verified to have
reached the file and every file verified restored byte-for-byte. ⛔ An anchor not occurring
exactly once is an error, not a pass.

**First pass: 9 of 11.** The two that escaped were both clamps in
`largest_stretch_this_guard_accepts`, written so that opening a window could not re-admit the
gap that broke its run — *stop short of occurrence `p - 1`, stop short of `q + 1`*.

> ⭐⭐⭐ **THEY ESCAPED BECAUSE THEY CANNOT BIND.** A run breaks at `q` exactly when
> `e[q+1] - s[q] - 1 > 2 · cap`, and the window already stops at `s[q] + cap + 1`, which is
> smaller — so the neighbour is always further away than the flank reaches. ⇒ *a branch a
> disarm cannot reach is not a branch a test can hold*, and both were **removed** rather than
> covered. The three published numbers are unchanged by the removal, which is how it was
> checked.

⚠ The two clamps the function keeps — it must contain the whole occurrence it opens around —
are reachable only at a **cap shorter than a declared word**, which nothing here asks. They
are reached at a cap of 1, and that is the input the test uses. **Second pass: 11 of 11.**

---

## 6. The artifact

`out/textual/significator-series-rules.jsonl`, **66 → 68** rows, byte-identical on re-run.
**63 byte-identical · 4 changed · 2 added · 0 removed.**

* the header moves on `generated`, `generator` and `summary`;
* `the_three_constants…not_fitted_to` moves on this repository's own program text, which grew;
* the two censuses gain the two new fields on each of their rows and nothing else;
* the two added rows are `whether_the_armed_cap_refuses_the_copy_it_was_read_off` and
  `what_extent_this_guards_answer_is_a_fact_about_the_copy_at`.

Both new controls are computed from the **live census** rather than from a constant, so a
published number that drifted away from what it is a maximum over fails the row rather than a
document. ⛔ And both are held **in three directions**: the strict comparison must refuse all
21, the inclusive one must refuse exactly one fewer — *without that clause the row would pass
on a guard that never had the defect* — and neither may refuse a certified reading.

⚠ A count corrected in passing: the refusal message still said *46 certified copies* and *25
certified as a reading*. The census says 47 and 26, and has since the twenty-first session
corrected the survey. The prose a reader meets had not been corrected with it.

---

## 7. ⬜ Left

1. ⛔ **The bound is still a lower bound on itself**, and now with a second reason: it is
   bounded above by the length of the shortest copy anyone certifies. Nothing here raises it.
2. ⛔ **The honest extent is measured and not armed** (section 4), and the reason is this
   repository's own material. That is a limit, published, not repaired.
3. ⚠ **The positive side is still partly circular** and still says so on the row.
4. ⚠ **The old floor is unchanged at 0.01** and still errs in both directions.
5. ⛔ Both certified counts remain **lower bounds** — 13 named abstentions, two declared
   languages, one archive, one reading pipeline.
6. ⚠ Union versus per-language is **measured absent, not measured equal** (section 5).
7. ⚠ Prior items unmoved: second reading of the fifth edition · no earlier printing · the
   registry-row pair is the owner's · R4 has no generator · S4–S6 need the sampled tree · one
   disarm from the nineteenth session escapes the suite, caught one layer out.
8. ⚠ `.se1` still nowhere durable — ⛔ this session never opened R3 and never needed it.
