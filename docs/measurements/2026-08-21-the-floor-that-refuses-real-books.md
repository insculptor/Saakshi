# The floor refuses whole real books, and what it separates is languages

**2026-08-21 · eighteenth session · `e21e5d3` → `f5ede66`… · 462 tests**

> ⛔⛔⛔ **THE HEADLINE.** `LEAST_RECURRENCE = 0.01` refuses two whole books that carry the
> commonest words of their own language across **79 %** and **83 %** of themselves, and tells
> the caller *"It is a machine reading that returned noise."* One of them, at 0.00864, is
> **1.2 declared words per ten thousand** and **0.4 % of its own extent** away from a copy
> this same floor **accepts** at 0.01036.

---

## 1. The question, and why it could not be asked before

The seventeenth session disarmed the accepting side of this floor and, on the way, found two
copies straddling it that differ by far more than the floor does:

| copy | share | what it is |
|---|---|---|
| `TheTheoryOfTheSamdhis…` | 0.00967 | refused — read as *a rendering of noise* |
| `uchchatar-sanskrit-pathavali` | 0.01009 | accepted |

Four per cent apart across the floor, and nowhere near four per cent apart in what they are.
⇒ **The refusing side had never been measured against real copies near the floor.** The floor
was fitted to seven renderings whose real members all sit at 6.7× it or above, and the census
had already turned up accepted readings at 1.01× and 1.19×.

⛔⛔⛔ **AND THE EVIDENCE WAS ONE-SIDED BY CONSTRUCTION.** The two declared draws returned
**fifty-nine** readable copies. The thirty-four the floor refused were kept as specimens; the
**twenty-five it accepted were measured, printed to a log and deleted.** So every question
about this floor could only be asked from below it, and the one question that matters — *does
it refuse real books?* — needs the other side, because where real copies sit is a fact about
the accepted side.

Both sides are now held. ⭐ The draws are **not** re-run: a search over a live collection is
not a fixed function of its query, so re-running it would answer a different draw and the two
sides would no longer be the same sixty items. The copies are re-fetched from the addresses
the draws recorded, and what reproduces is checked instead — **all twenty-five return the same
normalised character count the draw wrote down.**

---

## 2. The instrument, and the four that failed first

The question *is this copy a real reading* needs an answer that does not come from the floor.
Four candidates were tried before one worked, and ⛔ **every one of them scored a certified
rendering of noise as high as, or higher than, a real book.** Each was caught only because a
known-noise control was inside the measurement from the first run:

| instrument | on a certified rendering of noise | on a real Sanskrit book |
|---|---|---|
| share of word tokens shared with a real copy of the same script | **0.86** | 0.21 |
| character-weighted version of the same | **0.74** | 0.05 |
| share of Devanagari dependent signs sitting legally | **0.95** | 0.96 |
| commonest-word rate, list unfiltered | **370.4** | 329.9 |

⚠ *This floor is one instrument of exactly that class, and it fails on the same copies.*

### 2.1 What works: words the copy did not supply

`COMMONEST_WORDS` declares the commonest words of two languages — Sanskrit-or-Hindi and
English — **fixed before any copy was measured and taken out of none of them.**

> ⛔⛔⛔ **THAT PROVENANCE IS THE ENTIRE INSTRUMENT.** A term drawn out of a copy resolves in
> that copy for free — it is the defect `refuse_a_rendering_that_does_not_repeat` exists to
> catch — so a word list harvested from these copies would reproduce it exactly.

⭐⭐⭐ And the asymmetry it rests on is the guard's own: *a reader can destroy the evidence of
a presence but cannot manufacture it.* **A presence establishes that the copy carries the
language; an absence establishes nothing** — a Devanagari astrology dictionary refused here
scores 21.1 against the certified noise copy's 14.7, because a dictionary is headwords and
glosses and the commonest words of running prose hardly occur in it. ⇒ Every count below is a
**lower bound**.

### 2.2 Two traps paid for on the way

⛔ **`script_of` cannot cut words.** That bucket asks `isalpha`, which is right for its own
question and wrong for this one: a Devanagari vowel sign is a combining mark, so `isalpha` is
`False` for it. Cutting on that rule reported a mean word length of **1.36 characters** for
the real Devanagari book this repository holds. With the marks kept it reads **4.23**, and
every measurement taken over the debris was a measurement of debris.

⛔⛔⛔ **A WORD LIST IS NOT A MEASUREMENT UNTIL THE SHORTEST THING IN IT IS LONGER THAN WHAT
NOISE MAKES BY ACCIDENT.** With the two-character particles left in, a machine reading of
*5000 Years of Kashmir* — an English book of 1993 read by a machine set to an Indic script,
carrying no Sanskrit whatever — scores **370.4** declared words per ten thousand, **above** a
Sanskrit commentary of 1933 read in its own script at 329.9. The whole of that reading is one
two-character word: `वा`, **744 times**, in a copy that contains no Sanskrit. Under the rule
the same copy scores **0.0**.

⚠ And the rule had been **stated in a comment and never applied**. It is now enforced in code
from the declared list, and the declared list still shows what was considered.

---

## 3. The measurement

Sixty-one copies — the fifty-seven held of the fifty-nine the two draws returned, plus four
held here — asked what language they carry.

### 3.1 The pair across the floor

| | copy | share | declared Sanskrit per 10 000 words | share of its 1 000-character blocks carrying one |
|---|---|---|---|---|
| ⛔ REFUSED | `bodhicaryavatarapanjika…1902` | 0.00864 | **249.1** | **82.6 %** |
| ✅ accepted | `haaralatabyaniruddhabhatta…` | 0.01036 | **247.9** | **83.0 %** |

⭐⭐⭐ **THE SAME LANGUAGE, AT THE SAME RATE, ACROSS THE SAME SHARE OF THE COPY — half a per
cent apart on both measurements, and opposite sides of this floor.** The refused one is a
Bibliotheca Indica edition of Prajñākaramati's commentary on the *Bodhicaryāvatāra*, read in
Devanagari, legible at every offset opened. It is 679 151 characters — eighty-eight times the
extent at which a refusal is known to discriminate — so it is refused for its **rendering**,
by name, with the noise cause attached.

⚠ And the verdict does not even track how much language a copy carries. Two rows above the
accepted `haaralata` sits `krsnakarnamrtam…` at 0.01379 with **67.6** — a quarter of the
refused copy's rate — and it passes.

### 3.2 What the floor actually separates

| carried across at least | English carriers | their range | refused | Sanskrit/Hindi carriers | their range | refused |
|---|---|---|---|---|---|---|
| a quarter of the copy | 12 | 0.0125 – 0.161 | **0** | 14 | 0.00687 – 0.0892 | **3** |
| half the copy | 12 | 0.0125 – 0.161 | **0** | 13 | 0.00687 – 0.0892 | **2** |
| three quarters | 11 | 0.0335 – 0.161 | **0** | 11 | 0.00687 – 0.0892 | **2** |

⭐ Three criteria, not one, so the reading is not the criterion's.

> ⛔⛔⛔ **THIS FLOOR SITS BELOW EVERY COPY CARRYING ENGLISH AND INSIDE THE RANGE OF THE COPIES
> CARRYING DEVANAGARI.** Twelve characters of English is about two words; twelve characters of
> a Devanagari compound is three or four syllables of one. The seven copies the floor was
> fitted to are six English renderings and one Devanagari rendering **of an English book**.
> ⇒ **It was fitted where it is loosest and applied where it is tightest.**

### 3.3 And the accepting side's own specimen carries language

`TheTheoryOfTheSamdhis…` — the copy `GREATEST_EXTENT_AT_WHICH_A_RENDERING_OF_NOISE_HAS_CLEARED
= 320000` was read off, published last session as *an English monograph carrying not one
English word* — carries declared Sanskrit across **48.8 %** of its thousand-character blocks
at **239.3** per ten thousand words, more than eight of the twenty-five copies this floor
accepts. It is an English monograph on the *Nāṭyaśāstra* whose Devanagari quotations the
wrong-script reader got **right**. One of them, in the clear:

> `चाणक्यः- भक्त्या कार्यधुरं वहन्ति बहवोऽसते दुर्लभास्त्वादृशाः।`

⇒ ⭐⭐⭐ **The specimen is not established to be a rendering of noise, so the old name asserted
the one thing the measurement could not.** The constant is renamed
`GREATEST_EXTENT_AT_WHICH_A_WINDOW_OF_A_REFUSED_COPY_HAS_CLEARED`. **The value does not move**
— 320 000 stands as what it always was, a window of a copy this floor refuses, clearing this
floor. `_NOISE_SPECIMENS` is renamed `_COPIES_THIS_FLOOR_REFUSES` for the same reason: the old
name asserted of thirty-two copies what is now measured to be false of five of them.

---

## 4. The repair

⭐ **The refusal keeps its measurement and loses its cause.** That little in the copy repeats
is measured, and it is enough to refuse: a presence is free wherever little repeats, whatever
made the copy that way. What is withdrawn is the diagnosis — and it is withdrawn **in terms**,
not by omission, because it is the verdict that must go and not the words.

* the branch now ends *"AND NOTHING HERE SAYS IT IS A MACHINE READING THAT RETURNED NOISE,
  WHICH THIS REFUSAL USED TO SAY AND WAS WRONG TO"*, carries the sixty-one-copy measurement,
  and points at `language_a_copy_carries`;
* *"NOTHING IN THIS COPY REPEATS"* became *"LITTLE"* — a copy refused here can have a share of
  0.008, and **nothing** was the wrong word;
* every recurrence row gained `a_low_share_here_is_about_the_reading`, beginning
  *"⛔ NOT ESTABLISHED"*, beside the high side that has said so since last session.

### 4.1 ⛔⛔⛔ And withdrawing the sentence broke the sort that keyed on it

Two branches refuse a copy under the floor. The extent branch **denies** the rendering
branch's sentence by quoting it, so every reader sorting the two had to test the extent branch
first — a trap pinned in the suite, and one the census had already fallen into, reporting a
220-character photograph caption as a certified rendering of noise.

> ⭐⭐⭐ **A STRING-MATCHED BRANCH DETECTOR FAILS SILENTLY IN WHICHEVER DIRECTION THE MESSAGE
> LAST MOVED.** With the sentence withdrawn, the old sort classifies **every** refused copy as
> nothing in particular — and the generator's specimen table and its nine-instrument census
> were both sorting exactly that way. ⭐ The census was caught by its own control, which
> counts the instruments that refused and holds only at nine of nine; ⚠ the specimen table
> was not caught by anything — it was corrected in the same edit that added the marker, and
> had the marker been added without touching it, thirty-two copies would have been reported
> as refused for no stated reason and the control asserting they were certified would have
> failed loudly. That is luck, not coverage.

⇒ **Neither branch is sorted by its prose any more. Each names itself** — the extent branch
with the marker it already had, the rendering branch with *"THE EXTENT IS NOT THE CAUSE"* —
and the test pins both markers, their exclusivity both ways, **and runs the old sort to show
it misreports both copies.**

---

## 5. Controls

* **The draw reproduced.** All twenty-five accepted copies return the character count the
  draw recorded, to the character.
* **The instrument, both ends.** A real book held here reads 99.6 % of its blocks carrying the
  language; the copy this floor was built to catch reads 8.9 %. Without both, the refused
  carriers measure only each other.
* **Not everything scores high.** Two of thirty-two refused copies carry a declared language
  across half of themselves. An instrument returning a high reading everywhere would fail this.
* **The English side has no exception.** Every copy carrying declared English clears the
  floor, at every criterion.
* **Twelve of twelve disarms caught**, green baseline first, `sys.executable`,
  `PYTHONDONTWRITEBYTECODE=1`, every patch verified to have changed the file before the suite
  ran. ⚠ One disarm could not be patched on the first pass and printed *"COULD NOT PATCH"*
  rather than scoring as an escape.

---

## 6. The artifact

**48 byte-identical · 11 changed · 3 added · 1 removed**, 60 → **62** rows, byte-identical on
re-run. Accounted at key level: the header (commit and the control roster), two attestation
rows and one absence row and four controls whose `recurrence_of` sub-rows gained the new
field, the nine refusal texts the instrument census quotes, and the renamed constant's field.
⭐ `held_out_bodies` moved again for the same reason it moved last session — one of them is
this repository's own program text, and `textual.py` grew by 26 083 characters; its largest
refused window rose from 4 000 to 5 000, still under the bound.

---

## 7. What is left

1. ⛔ **The count of refused real books is a lower bound**, and the instrument says so: an
   absence establishes nothing, and a legible copy that is not running prose scores low.
2. ⚠ **Two languages are declared and no more.** Two copies the draws returned are in the
   Arabic script and several accepted copies are in Kannada, Tamil, Bengali and Greek; they
   measure zero, and that is a fact about the list.
3. ⬜ **The floor itself is not repaired, only its cause.** A floor that separates languages
   wants either a per-language value or a different statistic, and neither is measured.
4. ⚠ Every copy is from **one archive** and one reading pipeline. A different digitiser's
   failures are unrepresented.
5. ⬜ A second machine reading of the fifth edition · no earlier printing reached · the
   registry-row pair is the owner's · R4 has no generator · S4–S6 need the sampled tree.
6. ⚠ Kernels and the `.se1` still sit under a session temp directory.
