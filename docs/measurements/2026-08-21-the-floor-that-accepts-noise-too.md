# The floor accepts renderings of noise too, and neither named repair can be made

**2026-08-21 · `25f1a8a` → this session · 483 → 493 tests · sweep 21 of 21**

Last session established that `LEAST_RECURRENCE = 0.01` **refuses whole real books**, that
what it separates is **languages**, and that the repair is therefore either a **per-language
value** or a **different statistic**. It named both and measured neither. This session
measured both, and **both are refused** — with a defect found on the way that changes what
the floor is.

---

## 1. The headline — it accepts a rendering of noise, and that had never been measurable

Three of the twenty-five copies this floor **accepts** are certified readings in a script
their catalogued work cannot be printed in:

| copy | what the catalogue names | characters | share | this floor |
|---|---|---|---|---|
| `00bhagavatainkannada1stskandha` | a **Kannada** Bhāgavata | 411 925 | 0.011922 | ✅ accepts |
| `iabu2012buddhasenlightenment…` | an **English** conference proceedings | 217 121 | 0.013917 | ✅ accepts |
| `0415073103encofphilosophy10vs` | the Routledge **Encyclopedia of Philosophy**, ten volumes, English | **39 129 518** | **0.030511** | ⛔ ✅ accepts |

Every one of them is rendered wholly in Devanagari and carries not one word of the language
its work is written in. The last is the **largest copy this repository holds** and clears the
floor by **3.05×**.

> ⚠ **Nothing could have caught this until this year.** The census that drew these copies
> measured the twenty-five it accepted, printed them to a log and **deleted** them, so every
> question about this floor could only be asked from below it. Last session recovered them —
> and asked them **one** question, *what language do you carry*, not *is any of you noise*.
> ⭐ **A recovered set is not the same thing as a measured one, and the question that had
> never been put to it was the one it was recovered to answer.**

## 2. How a rendering of noise is certified here — by a presence, never by an absence

The rendering carries, at essentially every one of its letters, **a script the catalogued
work cannot be printed in**. That is a presence of the *wrong* script: it establishes that
the reader was set to a script the printing does not use, so whatever it returned is not the
words of the work. ⛔ No word list is consulted, which is what keeps this measurement from
scoring the language instrument against itself.

Twenty-one copies are certified this way, and **thirteen more are abstained from and named**
— the commemoration and felicitation volumes, which print English articles and Sanskrit ones
between the same covers, and the copies read in a script that is *not* wrong. ⚠ Several of
those are almost certainly wrong-script readings too. **The count is a lower bound**, as
every count in this repository is.

The other side is certified by the other presence: **26 copies** carrying the commonest words
of a declared language across at least three quarters of their thousand-character blocks —
words fixed before any copy was measured and taken out of none of them.

## 3. The two ranges cross, so no value of this statistic separates them

| | copy | share |
|---|---|---|
| lowest copy carrying its own language | `mimansakaustubha…1933`, Sanskrit across 79 % of itself | **0.006873** |
| highest wrong-script reading | the Routledge encyclopaedia | **0.030511** |

**Crossed, by 4.4×, and the published floor sits between them.** Asked at every value the two
sets take — complete, because a threshold's behaviour changes only at an observed value:

| value | real books refused | wrong-script readings accepted | total |
|---|---|---|---|
| 0.005765 | 0 | 7 | 7 |
| **0.006873** | **0** | **5** | **5** |
| 0.008640 | 1 | 4 | 5 |
| **0.01** ← published | **2** | **3** | **5** |
| 0.016443 | 4 | 1 | 5 |
| 0.030511 | 7 | 1 | 8 |
| **0.033480** | ⛔ **7** | **0** | 7 |
| 0.161061 | 25 | 0 | 25 |

> ⭐⭐⭐ **MOVING THE FLOOR TRADES A REFUSED BOOK FOR AN ACCEPTED RENDERING OF NOISE, ONE FOR
> ONE, AND THE TOTAL NEVER FALLS BELOW FIVE — which is what the published value already
> costs.** To refuse every wrong-script reading it must stand at **0.033480** and refuse
> **7 of the 26** real books, every one of them a copy carrying Sanskrit.

⚠ And the total is **not monotone** in the value: 5 at 0.006873, 6 at 0.007367, 5 at 0.008640,
7 at 0.011922, 5 again at 0.016443. *The smallest value at which the total stops falling* is
not the minimum — the same rule put `LEAST_EXTENT_A_REFUSAL_DISCRIMINATES_AT` 1 686 characters
wrong two sessions ago. So the **whole** forty-seven-point curve travels on the row.

## 4. Repair one — a per-language value. Measured, and self-defeating

A per-language floor needs a **routing rule**, and the only language instrument here is
`COMMONEST_WORDS`, **whose absence establishes nothing**. Routed at each of the three criteria
the census publishes:

| carried across ≥ | english | sanskrit_or_hindi | no declared language |
|---|---|---|---|
| **¾** | 15 readings, **0 wrong-script** | 11 readings, **0 wrong-script** | **0 readings, 21 wrong-script** |
| **½** | 15, 0 | 11, 0 | 0, 21 |
| **¼** | 15, 0 | 11, **1** | 0, 20 |

> ⛔⛔⛔ **THE ROUTING SORTS THE TWO SIDES INTO DIFFERENT BUCKETS.** At a half and at three
> quarters **no bucket holds both sides at all**: every wrong-script reading answers to no
> word list and lands where no language is declared, beside **no certified reading**. A floor
> fitted in a language bucket is therefore fitted with **nothing below it** — which is this
> floor's own original defect, one bucket at a time.

⭐ And the loosest criterion is the control on that, because it comes out the other way: at a
quarter, `TheTheoryOfTheSamdhis…` — an English monograph whose Sanskrit quotations the
wrong-script reader got *right* — **does** land in the Sanskrit bucket. A value fitted there
**still does not separate**: the Sanskrit readings run 0.006873–0.089183 and it sits at
**0.009675**, inside them.

⚠ Routing the undeclared bucket straight to a refusal is not available either. The copies
there that are *not* certified wrong-script include legible **Bengali**, **Tamil**, **Urdu**
and **Kashmiri** — refused for a fact about the word list rather than about themselves.

## 5. Repair two — a different statistic. Eight measured, none separates

⛔ Every candidate is scored against the certified wrong-script readings **and** both sides of
the floor before its number is read, because four instruments failed that way last session.

| statistic | least over the 26 real books | greatest over the 21 wrong-script readings |
|---|---|---|
| the floor as it stands, at 12 characters | 0.00687 | ⛔ **0.03051** |
| share of distinct **words** that recur | 0.0763 | ⛔ **0.3697** |
| share of distinct **two-word** shingles that recur | 0.0094 | ⛔ **0.1388** |
| share of distinct **three-word** shingles that recur | 0.00078 | ⛔ **0.0444** |
| mean word length | 3.45 | ⛔ **4.62** |
| distinct words ÷ words *(low is language)* | 0.727 | ⛔ **0.0889** |
| the floor at a **fixed extent** of 200 000 characters | 0.00497 | ⛔ **0.01248** |
| the floor at **two of the copy's own words** of characters | 0.0011 | ⛔ **0.3726** |

⚠ The fixed-extent one is the nearest miss and fails twice: inverted by 2.5×, and it cannot be
measured at all on 7 of the 26 real books, which are shorter than one window.

⛔ A ninth was offered and is **degenerate**: the copy against a shuffle of itself. A shuffle
repeats nothing at twelve characters in **50 of the 51** copies long enough to test, so the
ratio is unbounded for a wrong-script reading exactly as it is for a book.

> ⭐⭐⭐ **TWELVE INSTRUMENTS OF THIS CLASS HAVE NOW FAILED IN THE SAME DIRECTION**, four last
> session and eight this one, and each one scored a rendering of noise as high as or higher
> than a real book.

## 6. The reason, which is the finding

A machine reading is a **deterministic function of the printing**: a word the printing repeats
produces the *same* garbage string every time it is met. So a wrong-script reader carries the
printing's repetition across **intact**.

> ⭐⭐⭐ **REPETITION MEASURES THE MORPHOLOGY OF WHAT WAS PRINTED, NOT WHETHER THE READER COULD
> READ IT. The axis is wrong, not the value on it.**

Which is why the one instrument that does work — `COMMONEST_WORDS` — is not a statistic of the
copy at all: it is a **presence of something the copy did not supply**. ⛔ And it is not a
guard, because its absence establishes nothing: asked in its *rate* form rather than its block
form it does not separate these sets either, `TheTheoryOfTheSamdhis…` scoring **239.3** per ten
thousand words against the lowest real book's **187.0**.

⇒ **An accepting instrument exists here and a refusing one does not.**

## 7. What is published, and what is not

⛔ **No repaired value.** None was fitted, so nothing is held out — the discipline is
discharged by there being no number, not by a split.

What is published instead:

* `GREATEST_SHARE_A_WRONG_SCRIPT_READING_REACHES = 0.030511` and
  `LEAST_SHARE_A_COPY_CARRYING_ITS_OWN_LANGUAGE_REACHES = 0.006873`, which cross;
* `LEAST_COPIES_THIS_FLOOR_MISCLASSIFIES_AT_ANY_VALUE = 5`;
* `STATISTICS_MEASURED_AGAINST_THIS_FLOOR`, all nine named — a count with no names is a silent
  cap on what a reader can check;
* `least_error_a_single_value_can_reach` and `how_a_per_language_floor_would_be_fitted`, so
  both refusals are reproducible rather than described;
* in `texts.py`, `READINGS_IN_A_SCRIPT_THE_WORK_CANNOT_BE_PRINTED_IN` with its 13 named
  abstentions;
* and on **every** row `recurrence_of` returns, the value-side withdrawal beside the
  extent-side one: `a_high_share_here_is_about_the_copy` now begins *"⛔ NOT ESTABLISHED, AT
  ANY EXTENT OR ANY VALUE"*.

## 8. The controls, and the sweep

* **Both directions, inside the measurement.** The control refuses a census in which the floor
  errs only one way — a one-sided result would look exactly like the one-sided evidence this
  session exists to replace — and refuses one in which the certified wrong-script set sits
  wholly under the floor, which would make the finding an artefact of which copies were
  certified.
* **The loosest criterion answers as well as refuses**, putting one wrong-script reading
  *inside* a language bucket, so the routing finding is not an artefact of a criterion picked
  to produce it.
* **A positive control on the separation instrument**: on two sets that *do* separate it says
  so, reports zero misclassified, and reports the published value already at the minimum.
  Every other fixture crosses, so a verdict that could only say *no* would satisfy them all.

⛔⛔⛔ **AND THE SWEEP FOUND THAT THE HEADLINE FIELD HAD NOTHING BEHIND IT.**
`the_published_value_is_already_least` reads `True` over the real evidence and the generator's
control asserts exactly that — so **hard-wiring it `True` passed both**.

> ⭐⭐⭐ **A CONTROL THAT ASSERTS A FIELD IS TRUE IS SATISFIED BY A FIELD THAT IS ALWAYS TRUE**
> — last session's lesson about refusals, in the other polarity, on the field carrying this
> session's headline.

The second escape was the sweep's own: it appended a key to a dict that already held it, so
Python overwrote the entry and **nothing was disarmed**. ⚠ Third session running that a disarm
which does not disarm scored as an escape and read as a gap in the suite. Rewritten to
**rename** a certified key to one already abstained from, so both length assertions still hold
and only the disjointness branch can fire.

**Sweep: 21 of 21 caught** (first pass 19 of 21), green baseline first, `sys.executable`,
`PYTHONDONTWRITEBYTECODE=1`, every patch verified to have reached the file and every file
verified restored.

## 9. The artifact

`out/textual/significator-series-rules.jsonl`, **62 → 64** rows, byte-identical on re-run.
**53 byte-identical · 9 changed · 3 added · 0 removed.**

Every change accounted for: the header gains two controls and a new commit stamp; six rows
carrying a `recurrence_of` output gain the two new fields and the reworded withdrawal, and
nothing else on them moves; `the_three_constants_measured_against_text_they_were_not_fitted_to`
moves on **one** held-out body only — this repository's own program text, 427 762 → 478 033
characters, exactly as that body's own entry says it will; and the language census grows from
**61 to 65** copies, because it had been reporting four of the nine copies held here and a
census that leaves out copies it holds reports a range narrower than the evidence.

## 10. ⬜ Left

1. ⛔ **Both certified counts are LOWER BOUNDS.** 13 named abstentions on the wrong-script
   side; two declared languages and no more on the reading side.
2. ⛔ **The floor still stands at 0.01 and is still wrong in both directions.** What has
   changed is that its value is now measured to be unimprovable and its accepting side is
   withdrawn in terms. ⬜ *What replaces a refusing instrument* is not answered here.
3. ⚠ **One archive, one reading pipeline.** Every certified wrong-script reading comes from
   the same digitiser; a different one's failures are unrepresented.
4. ⚠ The wrong-script certification is a **declaration** from the catalogue's title, audited
   by a reader. It consults no measurement, which is the point — and it is not itself measured.
5. ⚠ Prior items unmoved: second reading of the fifth edition · no earlier printing ·
   registry-row pair is the owner's · R4 has no generator · S4–S6 need the sampled tree · one
   disarm from last session escapes the suite, caught one layer out · kernels and `.se1` still
   under a session temp dir.
