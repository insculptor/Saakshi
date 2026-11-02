# A second word that hands the request back · 2026-11-02

> ⭐⭐⭐ **THE LIBRARY'S NUTATION AND OBLIQUITY OUTPUT ECHOES THE REQUEST, AS THE MEAN NODE DOES.** Its
> pseudo-body was read 234 times in fresh processes, through `calc` and `calc_ut`, under every
> configuration of request and directory and both nutation words. It returned exactly the word it was
> handed **every time**, the 16 readings under a condition built so that the requested source cannot
> answer included, while the Moon's word, read beside it under the same conditions, named the source
> that did. ⇒ For this body the returned word cannot say which ephemeris answered. ⭐ Through `calc` its
> six values **did not move** with the request or the directory at any instant read, the ones centuries
> outside every data file included. Through `calc_ut` they moved at three of seven instants, and were
> bit-identical to `calc` at the universal day plus the library's offset at all 70.

---

## 0. What this session wrote

Two generator commits, each pushed with CI green, and from them two files:

| output | kind | rows | sha256 | written by |
|---|---|---|---|---|
| `nutation-obliquity-modes.jsonl` | R3 `provenance_record` — the pseudo-body under every configuration, beside the Moon | 293 | `17ecaa66…c86f` | `nutation_obliquity_modes.py` at `1a17fe9` (CI run 41467988144) |
| `swiss/r3-flag-reporting.jsonl` | R3 `provenance_record` — the survey, one body more | 189 | `5937280f…4dc2` | `r3_swiss.py` at `5a09a51` (CI run 41469584286) |

Each was generated twice from its commit and the two were **byte-identical**. The host is macOS arm64,
CPython 3.12.11, the library 2.10.03 through its binding 2.10.3.2; the data files are the three pinned
`.se1` files; the interval's ends are read from the `standard@1` data profile manifest
(`b68407a3…73ee`), as the mean node's record read them.

---

## 1. What was read

The library's documentation (section 3.2.4, *Obliquity and nutation*) gives the body a number of its own
and says what its six returned values are: the true obliquity of the ecliptic, the mean obliquity, the
nutation in longitude, the nutation in obliquity, and two zeros. The record carries those words beside
the values and checks nothing against them.

* **Three parts.** `calc` on a dynamical-time day; `calc_ut` on a universal-time day, with `deltat_ex`
  beside it and `calc` at the universal day plus that offset; and the Moon and the pseudo-body under six
  conditions, four built so that the request cannot answer.
* **Five configurations**: the analytical, the data-file and the JPL request, with the pinned files and
  with a verified-empty directory; the JPL request with no JPL file. ⛔ Never "no path set".
* **Both words**: the default and `FLG_NONUT`. ⛔ Never the speed or sidereal bit: a word carrying either
  is outside the two labels a reading here may carry.
* **Seven instants**, each the survey's own or the profile's:
  * the profile's two interval ends, 1849-12-26 and 2150-01-22;
  * J2000;
  * the survey's two years outside every measured edge, 1500 and 3000;
  * and the two ends of the range the survey searches for a body's edge, 1000-01-01 and 3000-01-01.
    ⭐ That range's middle is J2000 exactly, so it is read there and has no epoch of its own.
* Every reading is the one call of a fresh `-I` interpreter, every library call recorded inside the child
  and held to its row — the mean node's record's discipline, unchanged.

---

## 2. Echo or report

| entry point | where the request cannot answer (empty directory; JPL with no file; outside 1500 and 3000) | everywhere else |
|---|---|---|
| `calc`, both words | **the request, handed back** — 8 of 8 | the request — every reading |
| `calc_ut`, both words | **the request, handed back** — 8 of 8 | the request — every reading |
| the Moon, beside it | the source that answered — 16 of 16 | the request |

⭐ **No edge.** The data-file request with the files present came back as requested at both ends of the
survey's search range and at its middle, through both entry points and under both words, so the returned
word places no edge inside it. The record writes `measured_edge: null` and says why.

⚠ **The library's name for this body is the empty string**, and the record writes it as returned. Rows
and the survey name it by a label of their own, `nutation_obliquity`.

---

## 3. What moved and what did not

**Through `calc`**, all six values were bit-identical across the five configurations at **7 of 7**
instants, under both words.

**Through `calc_ut`** they moved at three instants and did not at four. The largest spread across the five
configurations, in arcseconds, for positions 0 to 3, under the default word:

| instant | position 0 | 1 | 2 | 3 |
|---|---|---|---|---|
| 1000-01-01 | 2.3047e-5 | 4.33e-7 | 4.9297e-5 | 2.348e-5 |
| 1500 | 2.905e-6 | 9.9e-8 | 8.708e-6 | 3.004e-6 |
| 1849-12-26 | 1.48e-7 | 5e-9 | 1.28e-7 | 1.42e-7 |
| J2000, 2150-01-22, 3000-01-01, 3000 | 0 | 0 | 0 | 0 |

At every one of 70 universal-time readings, `calc_ut` was bit-identical to `calc` at the universal day
plus `deltat_ex`'s offset under the same ephemeris bits. ⛔ That is recorded as numbers, not as a
mechanism.

**`FLG_NONUT`**, over 105 pairs of readings that differ only in the word:
* every nonut reading differs from its default twin at positions 0, 2 and 3, and the record refuses to
  exist if one does not;
* position 1 is bit-identical in all 105;
* under the nonut word, position 0 was bit-identical to position 1 in 117 of 117 readings, and positions
  2 and 3 were both zero in 117.

---

## 4. Named by position, not by meaning

Its consumer reads a reading's first three returned values under three fixed names, `longitude`,
`latitude` and `distance`, whatever the body, and decides from them whether a value moved with its
configuration. A record whose values it could not see there would look, to it, like one in which
nothing moved.

So every reading carries all six values in `values` and the first three again under those names, and the
record refuses to be written if the names do not hold exactly the first three positions. ⚠ For this
body, position 0 is no longitude. ⚠ **Position 3, the nutation in obliquity, is in none of the three
names**, so a consumer reading the three names alone does not see it. Measured here, it never moved where
positions 0 to 2 did not.

---

## 5. The survey, one body more

`r3_swiss.py` now reads the pseudo-body in the per-body survey, from a tuple of its own.
* **Never in the value grid.** Its values are no body's position.
* **Under the survey's two words only.**
* **After every other body.** So every reading the survey already carried is taken exactly as it was.

Against the survey emitted on 2026-10-31 (`15a18bc6…271a`), read field by field:

| | |
|---|---|
| rows | **179 of 179 byte-identical, in their order**; 10 added, all the pseudo-body's, every one returning its request |
| header fields that moved | `generator.commit`, `generated`, `record_date`; the per-body summary (13 bodies, 130 readings; the pseudo-body beside the node among the bodies with no edge); the per-body note, which now names both bodies whose word echoed, read off the verdicts |
| the two value grids written beside it | 1329 of 1329 and 861 of 861 rows identical to that day's |

---

## 6. In its consumer's reader

Measured in a throwaway copy of the consumer at its published head, a target directory of its own, and
removed. Its loader and its evidence registry were run on the committed tree and with the outputs in
place.

| state | inputs | construction | what its registry decides |
|---|---|---|---|
| A | as committed | ✅ | — |
| B | + the modes record | ✅, and the record loads by shape | for bodies 0–11, A's decisions, one added (next) — the pseudo-body: an echo through both entry points; `calc_ut` moving inside the interval at 1849-12-26; `calc` not moving |
| C | the survey **in place of** the committed one | ✅ — no refusal for two surveys | A's decisions; the pseudo-body an echo through `calc_ut` |
| F | both | ✅ | B's, exactly |

* ⭐ **The node is still refused** through both entry points. The Moon is still admitted through
  `calc_ut` for both words, and `calc_ut` is still excluded for the node at the same three instants.
* ⭐ **One addition for the Moon.** The modes record reads the Moon through `calc` under the default
  word at every fixed condition, where the mean node's record read it under the nutation word only. So
  its consumer's per-body rule now admits the Moon through `calc` for that word too. Its survey has no
  row for `calc`, so nothing it compares is affected. The same readings add one moving group for the
  Moon through `calc`, at J2000 under that word, an instant at which it already moved.

⛔ **But the survey cannot replace the committed one alone.** The consumer pairs the mean node's section
controls with the survey they read the witness's edge from, by that survey's digest. Any regeneration of
the survey moves its header, and so its digest — and the pair is refused (state C). Re-emitted against
this survey, the controls' 912 rows are byte-identical and only the digest they name moves. With them in
place, the pair holds again (state E).

**What else moves in its tests** (each a count, a list or an anchor, ⛔ none a decision):
* With the modes record: the list of records the mean node section's admission consulted (the modes
  record now supplies words to the table it reads), the number of records, the number of readings, and
  what the mean node's record alone decides.
* With the survey: its census (120 → 130 readings, 179 → 189 rows), the number of bodies it declares
  (12 → 13), a test that re-stamps it by its old date, and one that expects every body but the Moon and
  the node to move through `calc_ut` at J2000. ⭐ That last one assumes an echoing body is the node, and
  this body echoes and does not move there.

---

## 7. How the checks were shown to fire

**The modes generator.** Each check was planted out of the source one at a time, its tests run, and the
source restored and compared byte for byte: **39 of 39** were caught.
* Three escaped at first:
  * the children's environment kept the library's variables;
  * a child ran without `-I`;
  * the working directory was not checked after the run.
* A test with a twin was written for each, and each then went red.
* Every refusal is tested beside the record as written, which passes.
* All rows are pinned by one digest (host-bound).

**The survey change.** Four tests, each red against the generator before the change, three on their
own values. Six pieces planted out were caught, 6 of 6.

⚠ **One existing test was re-pointed.** It asked for one edge per body over the speed words, and is now
asked it of the value grid's bodies, the only ones read under them. It is held to the true node's own
refusal, so it cannot pass on the pseudo-body's absence.

Suite 737 → **801**. The run with no ephemeris library went 485 / 60 → **508 passed, 97 skipped**.

---

## 8. What this does not establish

* ⛔ Nothing about the sky. It records what one release returned under declared configurations, on one
  host.
* ⛔ No band, no class, no row and no unit. Whether a reading can decide anything is its consumer's
  question.
* ⚠ Not measured:
  * the speed or sidereal words;
  * any entry point but `calc` and `calc_ut`;
  * any other library version or host.
  * ⚠ An earlier probe here calls this body with the binding's default word, which carries the speed bit,
    in a call history it builds. That word is not read here.
* ⚠ Honest error, not forgery: a reference to the library bound before the wrapping, or a call through
  one of its classes, is outside every call record here.
