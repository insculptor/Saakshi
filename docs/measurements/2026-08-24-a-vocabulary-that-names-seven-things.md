# A vocabulary that names seven things — and the clause nobody had measured

**2026-08-24 · `8f4a79d` → this session · 511 → 517 tests · artifact 69 → 71 rows · disarm 6 of 6**

The twenty-second session left, at the top of its own list of what was open:

> ⚠ One archive, one reading pipeline; the wrong-script certification is a **declaration**
> from the catalogue title, audited by a reader, and is not itself measured.

That sentence is about twenty-one copies. Exactly one of them had ever had a measurable
channel agree with what its certification says, and the agreement was found by accident. This
session widened the audit to all twenty-one. The audit succeeded, and on the way it found the
instrument doing the measuring answering nothing at all about three other copies.

---

## 0. What the certification actually claims

`READINGS_IN_A_SCRIPT_THE_WORK_CANNOT_BE_PRINTED_IN` certifies a copy by a **presence**:

> The rendering carries, at essentially every one of its letters, a script the catalogued
> work cannot be printed in.

Two clauses, and they are not the same kind of statement:

| | clause | kind |
|---|---|---|
| **C1** | the rendering carries, at essentially every one of its letters, script *R* | a **measurement over the copy** |
| **C2** | the catalogued work cannot be printed in *R* | a **declaration** from the catalogue title |

C2 needs a catalogue and there is nothing in this repository that can check it. C1 needs
nothing but the copy — and it had never been asked. Twenty of the twenty-one entries rest on
the phrase *essentially every one*, which is a reader's summary of a number nobody wrote down.

---

## 1. ⭐⭐⭐ C1, measured, over every copy this repository holds

`scripts_in` counts the letters of each script a rendering carries. Asked of all **66** copies
`SOURCES` declares:

| set | copies | carrying exactly one script | letters of any other script |
|---|---|---|---|
| certified **wrong-script** | 21 | **21** | **0** |

Not *essentially* every letter — **every** letter. The twenty-one run from **10 530** letters
(`cleared_copy_iabu2012buddhasenlightenment…`) to **6 977 964** (the Routledge *Encyclopedia
of Philosophy* in ten volumes), all Devanagari, and not one Latin, Greek, Cyrillic, Telugu,
Kannada or Tamil letter between them.

⇒ **the audit of that declaration widens from one copy to twenty-one, and C1 holds exactly.**

### ⛔ And it discriminates nothing

The same census over the other side: every copy certified as a **reading** is single-script
too, in its own script. Only **3 of the 66** copies held here carry two scripts at all —

| copy | scripts |
|---|---|
| `jaimini_sutram_mishra` (a real Devanagari book) | devanagari 196 380 · latin 8 959 |
| `cleared_copy_in_ernet_dli_2015_101106` | latin 1 781 296 · cyrillic 10 |
| `cleared_copy_facetofacewithsriramanamaharshi…` | latin 866 810 · cyrillic 2 |

— and the first of them is a certified reading, not a rendering of noise. So a measurement of
purity puts the two certified sets in the same place.

⭐⭐⭐ **C1 is confirmed for all twenty-one and carries no separating power whatever. Every
bit of the certification's power sits in the clause that reads a catalogue.** That is the
honest result of the audit: the half that can be measured is true and is not the half that
does the work.

---

## 2. ⛔⛔⛔ And the census found the instrument answering nothing about three copies

`_SCRIPT_RANGES` named seven scripts: latin, devanagari, greek, cyrillic, telugu, kannada,
tamil. This repository holds copies in two more.

| copy | searchable characters | letters | `scripts_in` answered |
|---|---|---|---|
| `cleared_copy_dli_bengal_10689_10312` | 659 015 | **272 820** Bengali | `{}` |
| `refused_copy_paar_pare_urdu_novel_joginder_paul` | 115 923 | **81 476** Arabic | `{}` |
| `refused_copy_wafatnamah_anhazrat_kashmiri…` | 38 918 | **23 239** Arabic | `{}` |

**377 535 letters, and the instrument reported no script at all** — which is the same answer
it gives for a copy carrying no letters whatever. And that answer is not private: the emitted
record prints

```
"scripts_this_rendering_carries": [],
"carries_searchable_text": true,
```

for each of them, under prose that reads exactly that pair as *the machine reading was set to
the wrong script and every word searched in it will return zero*.

⭐⭐⭐ **A vocabulary that names seven things answers about the eighth exactly as it answers
about nothing.**

### ⚠ And four published sentences call those copies legible

> *Bengali, Tamil, Urdu and Kashmiri copies held here carry a declared word at no flank
> whatever, and every one of them is legible.*

That was a reader's say-so — and the only channel this repository has for it answered with an
empty mapping. It is a measurement now for three of the four. ⛔ **It is the same evidential
shape as the wrong-script certification with the sign flipped** — a presence of the script the
catalogue says the work is printed in — and it establishes that the reader was set to that
script, **not** that it returned the right words. A wrong-script reading of a Bengali printing
would answer identically.

---

## 3. ⛔⛔ The second consequence, which was in code and not only in prose

`scripts_required_by` builds the set of scripts a search alphabet is written in, and its own
entry says why a term may contribute nothing:

> A term carrying no script contributes nothing, which is how the one spelling that is a
> printed mark rather than a word stops standing in for eleven that are words.

A term in a script this file does not name contributes nothing **in exactly the same way**,
and the drop leaves no trace in the result. Measured:

```python
alphabet = (*[f"{gujarati}{n}" for n in range(11)], "Professor")
scripts_required_by(alphabet)   # -> {"latin"}
```

⇒ eleven spellings in one script and one in another ask for `{"latin"}`, the copy carries
Latin, and every check passes. **A twelve-spelling absence would have been reported, measured
on one spelling.** That is the precise failure `AbsenceSearch` and `PassageAbsence` exist to
catch, arriving through the door those checks are built on.

And when the alphabet is *entirely* in an unnamed script, the refusal that did fire said:

> the alphabet searched is written in no script at all — **every spelling in it is punctuation
> or digits**

which is false of a Bengali word, and sends a reader to repair an alphabet that is not the
problem.

⭐⭐⭐ *A fix that names the right cause was written for one cause, and the wrong cause has
more than one* — this file's own sentence, third instance.

---

## 4. What was repaired

* **`bengali` (U+0980–U+09FF) and `arabic` (U+0600–U+06FF) are named.** Measured, not guessed:
  the Bengali copy's letters occupy U+0985–U+09F0 and the two Arabic-script copies' U+0621–
  U+06D5, so each sits inside its base block. ⚠ Arabic Supplement (U+0750) and Extended-A
  (U+08A0) are **not** covered, and naming two more does not make the list complete — nothing
  published here claims it does.
* **`letters_in_a_script_this_file_does_not_name`**, and `Edition.letters_no_script_is_named_for`
  emitted beside the script list on every record. ⇒ **zero there with an empty list is a copy
  with no letters; nonzero there is this file's vocabulary and never the copy.** The two
  states are spelled differently, exactly as the twenty-second session's two abstentions are.
* **Both call sites ask about the unnamed letters first**, and refuse naming *that* cause. The
  older refusal survives underneath it and is now true when it fires, because the check above
  has already established that no spelling carries a letter of an unnamed script.

⚠ And the counter is not idle on the copies that were already fine: `jaimini_sutram_mishra`
reports **14** letters no script is named for, in 205 339 it does name. That is the residue the
seven-name list was hiding at a scale nobody would have looked for — modifier letters, a few
per copy — and it is now on the record rather than folded into the same silence as 272 820.

### The disarm

Six mutations, each applied to the tree and reverted:

| mutation | |
|---|---|
| `AbsenceSearch` drops the unnameable branch | CAUGHT |
| `PassageAbsence` drops the unnameable branch | CAUGHT |
| the unnamed-letter counter always answers zero | CAUGHT |
| `bengali` is not named | CAUGHT |
| `arabic` is not named | CAUGHT |
| the record stops carrying the counter beside the list | CAUGHT |

**6 of 6.** ⚠ The branches are reachable because the test alphabet is written in a script that
is **still** unnamed — a branch a disarm cannot reach is not a branch a test can hold.

---

## 5. ⬜ Left

1. ⛔ **C2 is still a declaration and there is still no channel for it.** What widened is C1.
   The one measurable channel that spoke to C2 — the per-locus flank putting
   `thetheoryofthesamdhis…` eight times above the next, exactly as its own entry predicted —
   is still one channel on one copy.
2. ⛔ **The script list is still not complete**, and the next gap will be found the same way
   this one was: by a census, not by a guard. What changed is that it now reports itself.
3. ⚠ The legibility of the **Tamil** copy is still a reader's say-so: it is measured 100 %
   Latin, so whatever is legible in it is not Tamil script.
4. ⚠ Unmoved: the bound is still a lower bound on itself · the honest extent is measured and
   not armed · the positive side is still partly circular · `LEAST_RECURRENCE` still 0.01 and
   measured unimprovable · both certified counts remain lower bounds · 2nd reading of the 5th
   edition · no earlier printing · registry-row pair is the owner's · R4 has no generator ·
   S4–S6 need the sampled tree · the 19th's one disarm still escapes the suite.
