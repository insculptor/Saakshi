# The second hand in the copy, and the printing that renders to nothing

**2026-08-16.** The standing refusal asked for **a second printing of the first translation**
— the only copy that could witness that translator's *notes* as his own words. The previous
session left a note beside it: the candidate that would close it had already been rejected,
against a question since replaced, so *a rejection recorded against a question that has been
replaced is not a rejection any more*. ⇒ The question was put again.

⛔⛔⛔ **Putting it again moved the obstacle rather than lifting it, and the reason is in the
copy this repository has been resolving into for three sessions.**

---

## 1. The first copy carries **two** commenting hands, and this file had counted one

R6 has always separated the sutras from the translator's notes, and says which is which on
every row, on the ground that a consumer taking one for the other implements a modern
commentator under a sutra's name. ⭐ **A translation with notes has two authorities. A
*revised* translation with notes has three, and the third is the one nobody counts.**

Measured in the held copy, each passage occurring exactly once:

| The copy says | Which establishes |
|---|---|
| "Though Suryanarain Rao has elucidated the abbreviations … **I propose to make some observations** for the benefit of the reader" | a hand writing *about* the translator |
| "**I have not meddled with the English rendering of this sutra by Prof. B. Suryanarain Rao.** … The rest is clear from **Prof. Rao's NOTES**" | that hand is not Rao, and distinguishes itself from Rao's notes |
| "This is a rather tough stanza and **Professor Rao's notes are not clear**" | that hand judges those notes |

⭐ A hand that writes *"Prof. Rao's NOTES"* is not Prof. Rao. The evidence is **internal** —
the copy speaking of the translator in the third person — which is the same move
`passage_fidelity` makes, and for the same reason: the alternative is an authority this
repository does not hold.

### ⛔⛔ And the hand cannot be named, which is recorded rather than repaired

It claims books of its own — "my book *Studies in Jaimini Astrology*", "my work *Manual of
Hindu Astrology*". ⛔ **Turning those titles into a name would mean supplying an authorship
from the recorder's own memory**, which is exactly the unsourced claim the locus discipline
exists to refuse, and this copy carries no title page, no imprint and no preface in its
rendering. ⇒ `named_within_this_copy` is **false**, and that is a complete finding:
*there is a second hand here and this copy does not say whose.*

## 2. What that does to the question that was re-put

The two rules this file files as **the translator's notes** stand in an 8 959-character
passage bounded by the founding sutra and the next — both landmarks resolving exactly once.
Measured over it: **none of the twelve spellings** by which this copy marks its second hand
occurs there. Every spelling read off the copy; all twelve attested elsewhere in it.

⛔⛔ **What that establishes is that the passage carries none of that hand's MARKS. It is not
that the passage carries the translator's words.** A reviser who rewrites silently leaves no
marker at all — and this copy's second hand says, in its own voice:

> I have not meddled with the English rendering of **this sutra**

⭐⭐⭐ *A disclaimer scoped to one sutra is worth making only by a hand that alters others.*

⇒ The refusal is rewritten a second time, under a new reason,
`revised_printing_cannot_witness_the_unrevised_words`: two printings that this hand revised
would agree with each other **about the revision**.

⭐ And what would close it is now a **test** rather than a hope: acquire a candidate, search
it for the twelve spellings, and require zero **over the whole copy**.

## 3. ⭐⭐⭐ The test is passed perfectly by a copy that was never read

A second printing **was** acquired this session: the right work, retrieved, digested,
13 905 548 bytes, **219 pages** — every one an image, with no text layer at all.

⛔ Every spelling returns zero over it. In any alphabet, at any length. It passes the
second-hand test more cleanly than any real copy could, and it establishes **nothing** — including its
own identity: the work, the translator and the printing are known only from the name the host
gives the file, which is a fact about a host and not about a book. ⚠ That is the same ground
an earlier candidate was rejected on for naming no translator, one step worse.

### ⚠⚠ And the number that should have caught it does not

| | |
|---|---|
| the rendering's own character count | **218** |
| characters a locus can resolve against | **0** |

The extractor returned an empty string for each of 219 image pages and joined them with a
newline apiece. ⛔ **The 218 is the page count minus one.** A guard written the obvious way —
`rendering.characters == 0` — passes this copy. ⭐ *A summary that collapses many values into
one has stopped measuring the thing it names*, this time on the header field a reader is most
likely to trust.

## 4. What is armed

* **`AbsenceSearch` refuses a copy with no searchable text**, and now requires a
  `positive_control` — words the copy is expected to contain, resolving **exactly once** —
  before any zero is written down. ⛔ Nothing else in an absence row distinguishes a copy
  silent about the rule from a copy silent about everything, and both print the same
  reassuring zero.
* **`PassageAbsence` checks the same thing *before* attestation.** ⭐ It refused the mute copy
  before this change too — and blamed the **alphabet**, because over a mute copy every
  spelling is unattested. ⛔ A refusal that names the wrong cause sends the next reader to fix
  a vocabulary that was never the problem. A test holds the two causes apart.
* **`SecondHand`** refuses unless the copy speaks of the translator in the third person, in a
  passage that resolves exactly once. ⛔ Without one, a second hand is a reader's impression
  of a change in voice.
* **`Edition` publishes `searchable` beside the rendering**, because the pair is the finding:
  one number can be large while the other is zero.

## 5. ⚠ A prerequisite nobody had stated, and it is unmet

⛔⛔ **The held copy does not say which printing it is.** Measured over its rendering:
*edition*, *Preface*, *Copyright*, *Publisher*, *Published* and *Printed* occur **zero**
times; there is no title page and no imprint. ⚠ Its only date-like number is a Samvat era
count standing inside the translator's own preliminary observations — *"counts now as
1988"* — which dates the **writing** rather than the printing, and stands in an era this copy
does not convert.

⭐ So *"a **second** printing"* is a claim that cannot be made from this side of the
comparison, however good the other copy is. Two copies could be one printing digitised twice,
and every rule would come back *corroborated across printings* for what was one printing read
twice. ⚠ The same shape as two addresses serving one scan.

## 6. The re-emission, and its controls

The held file was copied aside and digest-verified **first** — `out/` is git-ignored, so a
copy made first is the only diff baseline that exists. Compared by **row identity**, never by
position: five rows were added, and a positional diff would report every row after the first
insertion as changed.

* **23 rows byte-identical** — all five rule rows, all five corroborations, the correction,
  the alignment, and every standing refusal and control. ⭐ **No value drifted anywhere else.**
* **2 changed** — the absence row, which gained its positive control; and the
  translator's-notes refusal, rewritten under the new reason.
* **5 added** — the second-hand finding, two refusals, two controls. **0 removed.**

⭐ The comparator was then driven off its own value rather than trusted:

| Control | Result |
|---|---|
| the new file against itself | 0 changed, 30 identical |
| the held file against itself | 0 changed, 25 identical |
| one **untouched** rule row perturbed | changed 2 → **3** |
| ⚠ revert **only** the absence row | changed 2 → **1** |
| ⚠ revert **only** the rewritten refusal | changed 2 → **1** |
| one row dropped | removed 0 → **1** |

**6/6.** ⭐ The last two are what make each change load-bearing rather than vacuous: either
one reverted alone moves the count, so neither is riding on the other. Byte-identical on
re-run; all **7** controls in the artifact held, including the two new ones.

## 7. What this does not settle

* ⛔ The **first translator's notes as his own words** are still not witnessed, and the
  obstacle has changed: it is no longer that no second printing is held, but that the copy
  held is one a second hand worked over.
* ⚠ **A second printing on a public archive was identified and could not be retrieved** — the
  host was unreachable for the whole session. ⛔ Its copies are the right shape, because the
  machine reading would be the distributor's rather than this instrument's.
* ⛔ **No rendering of the mute printing was produced here.** Running our own machine reading
  over it would make its errors ours, and an absence measured over our own OCR would be
  measured over our own mistakes.
* ⛔ The **second hand is not named**, and this copy cannot name it.
* ⚠ The second hand disturbs neither the five rules nor the five corroborations — all twenty-three
  untouched rows are byte-identical. What it disturbs is the **authority label** on two of
  them, and that is recorded as a refusal rather than a correction, because the rows are
  still located and still say what they say.
