# A refusing instrument made of presences — and it separates the copies, not the passages

**2026-08-22 · `7b9b26f` → this session · 493 → 507 tests · sweep 19 of 19**

The twentieth session closed the recurrence floor as **unrepairable** and left one question
open: *what replaces a refusing instrument, given that nothing cheap is one.* Its own answer
was that no cheap statistic is, and that **an accepting instrument exists here and a refusing
one does not** — because the only thing that has ever worked is a **presence** of something
the copy did not supply, and a presence cannot refuse.

This session found one that can. And it found, in the same measurement, that what it
separates is **copies** and not **positions** — which matters, because a guard is applied at
a position.

---

## 1. The instrument

For a copy, and for the commonest words of a declared language fixed in `COMMONEST_WORDS`
before any copy was measured and taken out of none of them:

> **the smallest flank at which every position of the copy carries, within that many
> characters on one side or the other, one of those words.**

⭐ Complete over every position and **exact**: the covered set is the union of one interval
per occurrence, so nothing is sampled and nothing is assumed. It is asked over the **union**
of the declared lists rather than the smallest of them taken alone — a copy that prints an
English apparatus around a Sanskrit text is covered at a position by neither list alone and
by the two together, and a minimum would report such a copy as worse than it is, only for
the copies that carry two languages, which is a bias with a shape.

### ⭐⭐⭐ Why it can refuse when a presence cannot

**It is a maximum over presences, and a maximum can be exceeded.** Every observation feeding
it is a presence — a declared word, at a position, in a copy. The statistic is the worst of
them. The twentieth session's argument was sound about a presence *taken singly* and did not
consider one taken **at the copy's worst place**.

### ⛔ Why it is not the thirteenth failure

The twelve that failed are statistics of the copy's **own morphology** — recurrence, two- and
three-word shingles, mean word length, type–token, the floor at a fixed extent, the floor at
the copy's own words. A machine reading is a deterministic function of the printing, so a
repeated word yields the *same* garbage string and the printing's morphology survives into
the noise intact. This one is not a statistic of the copy at all: it is a **distance to words
the copy did not supply**.

---

## 2. The measurement — the two certified sets do not cross

| set | copies | least | greatest |
|---|---|---|---|
| certified **readings** | 26 | 163 (`gov_in_notification_2022_99`) | **8 828** (`ajitagamavolin_r_bhatt`) |
| certified **wrong-script readings** | 21 | **16 642** (`scienceandtheindiantradition…`) | 306 984, ⭐ and **two never at any flank** |

**8 828 < 16 642 — they do not cross, by 1.88×.** Twelve instruments of this class have
crossed; this is the thirteenth and the first that does not.

Both sets are certified as they always are here, and neither by this measurement: a reading
by a **presence** of the commonest words of its own language across at least three quarters
of its thousand-character blocks; a wrong-script reading by a **presence** of a script its
catalogued work cannot be printed in, **with no word list consulted at all**. ⛔ Both counts
are lower bounds — thirteen further copies are abstained from and named, and two declared
languages are all there are.

### The hold-out

⛔ *A floor fitted and evaluated on the same set repeats the original defect.* So a value was
fitted on **one draw alone** — the `specimens` draw, 17 wrong-script readings and 2 readings,
band **(5 129, 16 642)**, midpoint **10 885** — and applied to the **28 copies held out**: the
`copies-that-cleared` draw and the copies held by provenance.

> **0 of the 24 held-out readings refused. 0 of the 4 held-out wrong-script readings
> accepted.**

### ⭐ And the length confound is absent, measured rather than asserted

As a *share* of the copy the two ranges overlap (a 1 345-character notification needs 12 % of
itself). As an absolute number they do not, and at comparable extents the gap is stark:

| | characters | flank |
|---|---|---|
| `jaimini_sutras_rao` | 228 420 | **376** |
| `jaimini_sutras_rao_library_scan` — the same book, read in the wrong script | 246 777 | **47 146** |

⚠ That the absolute number separates and the normalised one does not is itself evidence about
what the quantity is: **a stretch of text, not a proportion of a copy.**

---

## 3. ⛔⛔⛔ What is armed, and what is refused

**The unfitted bound is armed. The fitted one is not.**

`LEAST_FLANK_AT_WHICH_A_LOCAL_PRESENCE_IS_FREE_IN_A_RENDERING_OF_NOISE = 16 642` — a minimum
over the certified set of noise, the same shape as every accepting bound in this repository,
and ⛔ **a lower bound on itself**: the next specimen moves it, exactly as
`LEAST_EXTENT_AN_ACCEPTANCE_DISCRIMINATES_AT` moved 1 016× when its set grew from one member
to thirty-three.

The fitted midpoint 10 885 passed its hold-out and is still **not** published as an arm:

> ⭐⭐⭐ **No copy certified either way falls between 8 828 and 10 885, so on this evidence
> the two are the SAME GUARD — and given two guards that agree on all the evidence, the one
> that is not fitted to the evidence is the one to arm.**

⚠ They differ on exactly **one** of the sixty-five copies held here — `pli_kerala_rare_14973`
at 15 968 — and it is a copy **neither channel speaks for**.

---

## 4. ⛔⛔⛔ The finding that cuts the other way — the copies separate and the positions do not

The same measurement at **one position** is what a guard actually reads: *how far from this
citation must a reader go before meeting a word of the language it declares?*

Swept over 200 positions of each copy, arithmetically and without looking at the answer
first:

| copy | p10 | median | worst |
|---|---|---|---|
| `jaimini_sutras_rao` — a real book | 5 | 14 | 256 |
| `mimansakaustubha…1933` — a certified reading | 30 | 214 | **1 633** |
| `bodhicaryavatarapanjika…1902` — a certified reading | 30 | 155 | **4 626** |
| `thetheoryofthesamdhis…` — a **certified rendering of noise** | **41** | 576 | 31 139 |
| `jaimini_sutras_rao_library_scan` — a certified rendering of noise | 556 | 4 268 | 47 026 |

> ⭐⭐⭐ **A LOCUS NEEDING FIVE HUNDRED CHARACTERS COULD HAVE COME FROM A REAL BOOK'S SPARSE
> PASSAGE OR FROM A RENDERING OF NOISE'S BEST ONE.** The per-position values **overlap
> outright**, and a value cutting between them would trade a refused citation for an accepted
> one exactly as `LEAST_RECURRENCE` does.

⇒ **No threshold on the per-locus number is published**, and every row carrying that number
says so in terms. The reason is structural rather than a shortage of copies: a citation sits
at **one** place and almost never at the copy's **worst** one, so the statistic that
discriminates and the statistic a guard reads are not the same statistic.

⚠ The one certified rendering of noise whose positions are hardest to tell apart is
`thetheoryofthesamdhis…` — and its certification **already says why**: it is an English
monograph that quotes the Nāṭyaśāstra's Sanskrit, and the wrong-script reader got those
quotations right. ⭐ **A measurement that consults no catalogue put exactly that copy 8×
above the next**, which is a channel agreeing with a declaration on the one copy where the
declaration predicted the disagreement.

---

## 5. What it costs, measured

**Nothing, on the loci this repository emits.** All **12** attest, the furthest at **196**
characters — 45× under the reading bound and 85× under the arm.

⛔ On the copies:

* **certified readings refused: 0** — and the generator's control asserts that list is empty,
  because it is the arm's whole claim to be free of the defect it replaces.
* the arm refuses the **library scan** at 47 146 — which is the copy the wrong-alphabet
  finding was made on, so that is the instrument working.
* it refuses **three copies neither channel speaks for**: a Tamil copy and a Bengali one that
  carry a declared word at **no flank whatever** because no list here covers their language,
  and a Sanskrit manuscript catalogue of 1871 whose long stretches of shelf marks carry no
  running prose.

### ⚠ And a `None` is unattributable from the measurement alone

A copy that declares no language and answers to no word list produces the same answer whether
it is a wrong-script reading or a legible book in a language `COMMONEST_WORDS` does not
cover. **Only the certification tells them apart, and that is a declaration and not a
measurement.** So the guard is asked with the language the **locus** declares, and a locus
whose language has no list gets a third outcome — `cannot_measure`, an **abstention**, spelled
differently from a refusal on purpose.

> ⭐⭐⭐ **THAT DECLARATION IS ALSO WHY THIS ESCAPES THE ROUTING THAT DEFEATED A PER-LANGUAGE
> FLOOR.** That repair failed because the only router available was the word list itself, so
> every wrong-script reading answered to no list and landed in a bucket with nothing below
> it. Here nothing is routed off the copy: a `Locus` **declares** its language, outside the
> copy, and the copy has no vote in the question.

---

## 6. The fragment is excluded from its own passage

⛔ A declared word inside the quotation was supplied by the **citation**, not by the copy —
the same defect that makes a word list harvested from a corpus resolve in that corpus for
free, one scale down. Including it would let a locus carry its own evidence, and **the longer
the quotation the freer the presence would be**. The isolating test is a fragment made
entirely of declared words sitting in a copy whose surroundings carry none; it must not
attest, and the same fragment must attest when the surroundings are what supply the words.

---

## 7. The sweep, and the escape it caught in the wording

**19 of 19 caught**, green baseline checked first, `sys.executable`,
`PYTHONDONTWRITEBYTECODE=1`, every patch verified to have reached the file and every file
verified restored byte-for-byte.

The first pass caught 16. Of the three that did not:

* ⛔⛔ **one escaped by a prefix.** The refusal ends *"AND NOTHING HERE SAYS THIS COPY IS A
  MACHINE READING THAT RETURNED NOISE…"*, and the test asserted that opening. A disarm that
  replaced everything **after** those words with the diagnosis itself left the prefix
  standing and the assertion passed. ⇒ the branch now **names its own limit** and the test is
  owed the marker, not the opening — *the words owed, not the words present.*
* one was a fixture that could not show the defect: the two never-covered lists were merged,
  and the fixture had a `None` on one side only, so the merge was invisible. Both sides carry
  one now.
* two were unpatchable because the anchor matched twice or not at all. ⚠ **COULD NOT PATCH IS
  NOT A PASS** — both were rewritten to anchors occurring exactly once and then run.

---

## 8. The artifact

`out/textual/significator-series-rules.jsonl`, **64 → 66** rows, byte-identical on re-run.
**61 byte-identical · 4 changed · 2 added · 0 removed.**

* the header moves on `generated`, `generator` and `summary`;
* `the_three_constants_measured_against_text_they_were_not_fitted_to` moves on **one** held-out
  body — this repository's own program text, 478 033 → 507 901 characters, exactly as that
  body's own entry predicts;
* the two censuses gain the new field on each of their rows and **nothing else**;
* the two added rows are the separation and the non-separation.

⭐ Stamps: 22 artifact files, 8 distinct commit stamps, 8 of 8 reachable from `HEAD`.

---

## 9. ⬜ Left

1. ⛔ **Both certified counts remain LOWER BOUNDS** — 13 named abstentions, two declared
   languages and no more, one archive and one reading pipeline.
2. ⛔ **The bound is a lower bound on itself.** It is a minimum over 21 copies; the copy that
   sets it is 53 290 characters and only 1.53× above the fitted midpoint. One further
   specimen at nine thousand would break the separation, and there is no argument here that
   one does not exist.
3. ⚠ **The positive side is partly circular and says so on the row.** A copy is certified a
   reading by carrying a declared word across three quarters of its thousand-character
   blocks, which near a flank of 500 is close to the statistic being scored. The wrong-script
   side is not circular, and the copies held by provenance are not either.
4. ⬜ **The per-locus number is published without a threshold**, which is a refusal and not a
   gap — see section 4.
5. ⚠ **The old floor is unchanged and still stands at 0.01.** Nothing here repairs it; this
   is a different instrument beside it, and `refuse_a_rendering_that_does_not_repeat` still
   errs in both directions exactly as last session measured.
6. ⚠ The wrong-script certification is still a **declaration** audited by a reader. ⭐ Section
   4 is the first measurable channel that agrees with it, and it agrees on the one copy where
   the declaration named its own exception — but it is one channel and one copy.
7. ⚠ Prior items unmoved: second reading of the fifth edition · no earlier printing · the
   registry-row pair is the owner's · R4 has no generator · S4–S6 need the sampled tree · one
   disarm from the nineteenth session escapes the suite, caught one layer out.
8. ⚠ `.se1` still nowhere durable — ⛔ this session never opened R3 and never needed it.
