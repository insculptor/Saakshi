# A floor that refuses four fifths of every real book · 2026-08-20

> ⭐⭐⭐ **A FLOOR FITTED ON WHOLE BOOKS WAS APPLIED TO COPIES OF ANY SIZE, AND BELOW A
> MEASURED EXTENT IT IS A TEST OF SIZE RATHER THAN OF LANGUAGE — WHILE PUBLISHING THE
> LANGUAGE CAUSE.** Read two hundred characters at a time, `LEAST_RECURRENCE` refuses
> **7 036 of 8 555** blocks of the very books it was fitted to, and it refused them saying
> *"It is a machine reading that returned noise."* ⛔ Nothing had measured that.

⚠ Local date 2026-08-19 evening; the artifact's own stamp is UTC and reads **2026-08-20**.

---

## 0. Where this came from

The previous session armed `refuse_a_rendering_that_does_not_repeat` at nine resolutions
across eight instruments and closed with a warning about its own constant:

> ⚠ *The floor is fitted to seven renderings. A real copy recurring below 0.01 would be
> refused by an instrument that should accept it, and only the published number would say so.*

That warning names the wrong axis. The copies it was fitted to are a quarter of a million
characters each; the risk is not that some **book** recurs low, it is that a copy of any
other **size** does — and the floor says nothing about size at all.

---

## 1. The measurement

Each copy is tiled into **consecutive disjoint blocks** — every character of every copy in
exactly one block, no sample and no overlap — and the floor is asked of every block. The
remainder shorter than one block is dropped and reported on the row, because measuring it
would answer at an extent other than the one being asked about.

`blocks_this_floor_refuses(edition, block=...)`, over the same seven renderings
`LEAST_RECURRENCE` itself is fitted to — six real copies and the machine reading that
returned noise:

| block | the six real copies refused | the rendering of noise |
|---|---|---|
| 200 | **7 036 of 8 555** (82%) | 1 233 of 1 233 |
| 300 | 3 930 of 5 704 | ⛔ 821 of **822** |
| 500 | 1 651 of 3 421 | 493 of 493 |
| 1 000 | 398 of 1 709 | 246 of 246 |
| 2 000 | 84 of 853 | 123 of 123 |
| 3 000 | 21 of 568 | 82 of 82 |
| 4 000 | 7 of 426 | 61 of 61 |
| 5 000 | 3 of 339 | 49 of 49 |
| **6 000** | **0 of 283** | 41 of 41 |
| 7 000 – 20 000 | 0 of 241 … 0 of 83 | every block |

⭐ **6 000 characters** is the smallest point on the grid at which no block of any real copy
is refused. At five thousand two of the least legible readings still are.

> ⚠ **A block of a book is the best proxy available for a short copy, not the same thing as
> one.** And the number is fitted exactly as the floor is — to the copies held, on the grid
> published beside it.

⭐ An **eighth** rendering held here, of a different work, is corroboration outside the fit
and behaves the same: 5 302 of 7 008 blocks refused at two hundred characters, 0 of 233 at
six thousand.

---

## 2. What the defect actually was

The refusal published, for **any** copy under the floor:

> ⚠ *This copy is NOT mute and NOT out of extent … and it is not the alphabet that is wrong
> either. It is a machine reading that returned noise, and noise answers every question
> exactly once.*

For a copy of four hundred characters that sentence is **an unmeasured claim**. Nothing in
the measurement distinguishes a page of a real book from a page of noise at that extent —
both fail, and only one of them is noise.

> ⭐⭐⭐ **A refusal that states an unmeasured cause has agreed with a claim for reasons
> unrelated to it.** That is the defect this file found in its own census two sessions ago —
> an offer refused for *no script* when the control was aimed at something else — and it has
> now been made by the guard that census was written to measure.

⛔ The copy is **still refused**, and must be: a resolution in a copy that small is free for
exactly the reason it is free in noise. What changes is that the refusal now names the
extent, in terms, and says that nothing here measured the rendering.

---

## 3. ⛔⛔⛔ The fixtures had the defect. Again.

`A_RENDERING_OF_NOISE`, the copy standing in for the library scan in the suite, was **1 799
characters**. At that extent a real book fails the same floor. ⇒ **Every test certifying
*the instruments refuse the rendering of noise* was certifying a refusal the fixture's SIZE
had earned**, and five of them failed the moment the extent was measured.

> ⭐⭐ The previous session found that every copy built in the test file **repeated nothing** —
> the property of noise itself. This one finds the copy built to *be* noise was too small for
> that property to mean anything. Twice in two sessions the test bed was the subject.

The fixture is rebuilt at 7 199 characters from the same prefix-stable generator, so every
offset quoted out of it elsewhere still resolves — and the copy **as it stood** is rebuilt in
the suite and shown to earn the extent cause, so growing it is a correction and not a
decoration.

---

## 4. ⛔ The control refuted the sentence this bound was written with

The bound went in reading *a pass is sound at any extent and a refusal is not*, on the
strength of the noise copy being refused in every block at every size that had been printed.
The generator's own `held` condition — noise refused in **every** block at **every** point of
the grid — came back **FAILED** on the first run that measured all sixteen points.

> ⛔⛔⛔ At **three hundred** characters, **one block of the rendering of noise in 822 clears
> this floor**: three of its 286 fragments come round twice, a share of **0.0105** against
> the 0.01 required.

⇒ Below the extent the measurement is unsound in **both** directions. Only the refusing one
is bounded here, and that is a **decision**: refusing every copy shorter than six thousand
characters outright would refuse every fixture the suite is built from, and every caller in
this repository passes a copy of a quarter of a million characters. ⚠ It is written where a
reader will find it and pinned by the numbers that make it a finding, so arming it later is
something somebody chooses.

> ⭐⭐⭐ *A control is worth having only where it can come back FAILED, and this one did — on
> the author's own sentence, before it reached a reader.*

---

## 5. What was armed, and what it cost

* `LEAST_EXTENT_A_REFUSAL_DISCRIMINATES_AT = 6000`, with the table it was fitted from.
* `blocks_this_floor_refuses` — the tiling, in the library so it is testable, so the
  generator can re-measure it on every run rather than quoting a number nobody can check.
* The refusal splits by extent. **Only the message changes** for a caller: both branches
  raise, so nothing that used to be accepted is refused and nothing refused is accepted.
* Every row that carries a recurrence now carries `characters_measured`,
  `the_extent_a_low_share_means_anything_at` and `a_low_share_here_is_about_the_copy`,
  because *a share alone cannot be read*.
* A new control in `generators/r6_karaka_rules.py`, whose `held` requires the effect to be
  **shown to exist** at two hundred characters as well as gone at six thousand. ⛔ A bound
  with nothing under it would hold just as well with the whole thing deleted.

**Disarmed and re-run, five ways, all caught**: the branch deleted (2 tests), the extent set
to zero (4), the fixture put back at 1 500 (6, including the roster), the extent field
dropped from the row (1), the qualification removed from the published sentence (1).

> ⛔⛔ **And the sweep lied first — a second time, in a new costume.** It reported **0 of 5**
> caught, for every variant, because `subprocess.run(["python", ...])` resolved to an
> interpreter with no pytest installed. The run said *no failures*, which reads as *these
> tests do not depend on the guard*. With `sys.executable` it is 5 of 5.
> ⇒ ⭐⭐⭐ *A measurement whose subject is the wrong thing has measured nothing* — last
> session it was a stale `.pyc`, this session the wrong interpreter, and both times the
> false reading was the reassuring one.

---

## 6. The re-emission

`out/textual/significator-series-rules.jsonl`, **57 → 58** rows:
**48 byte-identical · 9 changed · 1 added · 0 removed**, by row identity and never position,
**byte-identical on re-run**. Every change accounted for at key level:

| changed | why |
|---|---|
| the header | `generator.commit`, and the new control in the summary |
| 6 rows carrying a recurrence | the three new fields, and the corrected `what_a_share_near_zero_means` |
| the noise-copy roster, all 9 causes | the refusal now names the extent it cleared |
| the attestation's refusal note | the same sentence, one level down |

⛔ The five rules, five corroborations, twelve refusals, the alignment, the hands, the naming
and foreword rows and every earlier correction are **untouched**.

---

## 7. What this does not settle

1. ⛔ **The accepting side is not guarded**, and is measurably unsound below the extent.
2. ⚠ **The extent is fitted** to seven renderings on a sixteen-point grid, exactly as the
   floor is. A real short document is not a block of a book.
3. ⛔ **No copy was acquired and no reading produced here.** Every measurement is over copies
   already held.
4. ⚠ Both numbers in the pair — `RECURRENCE_MEASURED_AT`, `LEAST_RECURRENCE` — and the extent
   are three constants fitted to **one** set of copies. A copy that disagreed with all three
   would look exactly like a copy that disagreed with none.
