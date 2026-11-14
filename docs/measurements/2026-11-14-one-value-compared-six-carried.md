# One value compared, six carried · 2026-11-14

> ⭐⭐⭐ **A ROW THAT COMPARES ONE VALUE CAN STILL CARRY EVERY VALUE ITS CONTROLS READ.** The library
> returns six values for its nutation and obliquity pseudo-body. Its consumer compares the first and
> nothing else, and asks the controls to read all six: a move of the mean obliquity and of the nutation
> in obliquity that cancelled in the first value, or a move of the fourth alone, would pass a control
> that read the first. So each row of this section compares one value and carries all six beside it,
> nested where nothing compares them, and every reading of the pseudo-body in its controls carries all
> six too. ⛔ At every one of its 76 rows, none of the six moved with the request, the regeneration in
> another order read all six again, and the twin read with `FLG_NONUT` added was the mean obliquity.

---

## 0. What this session wrote

One generator commit, `5f001bf` (pushed; CI `ci` green, run 43551301648), and from it, twice, the same
seven files. Four of them are outputs; three are controls of what the commit did not change. One test
commit after it, `363a3bb`, changes no generator (section 5).

| output | kind | rows | sha256 | written by |
|---|---|---|---|---|
| `nutation-obliquity-section/nutation-obliquity-section.jsonl` | R3 `numeric_pin` — the pseudo-body through `calc`, one section | 76 | `b753a361…bfa1` | `nutation_obliquity_section.py` |
| `nutation-obliquity-section/nutation-obliquity-section-controls.jsonl` | R3 `provenance_record` — its controls | 912 | `d5434e5a…b8d4` | the same run |
| `survey/swiss/r3-flag-reporting.jsonl` | R3 `provenance_record` — the per-body survey | 189 | `c1754cc3…e276` | `r3_swiss.py` |
| `mean-node-section/mean-node-section-controls.jsonl` | R3 `provenance_record` — the mean node's controls, against that survey | 912 | `a0d94c7a…e049` | `mean_node_section.py` |

The two emissions were **byte-identical**, all seven files. Host macOS-27.0.1-arm64, CPython 3.12.11,
library 2.10.03, binding 2.10.3.2, the three pinned data files, and the data profile manifest of every
earlier section (sha256 `b68407a3…73ee`, coverage 1849-12-26 … 2150-01-22).

⭐ **The survey and the mean node's controls are a pair.** The controls read the Moon's edge from the
survey and name its digest. The survey changed, so the controls were emitted again against it, in the
same run; neither is handed over without the other.

---

## 1. The section

* **Subject**: the pseudo-body through `calc`, at a dynamical-time Julian day.
* **The word**: `2` — the data-file request's ephemeris bit and nothing else, ⛔ no `FLG_NONUT`. The
  configuration is the data-file request with the three pinned files on an explicit path, every
  process-wide state reset. Its identity renders
  `c893013badb8338ed6de303033a6862f0a0564b357da1523f61d6c663bb22ac7`, the literal its consumer names it
  by; ⛔ the section refuses to be written under any other, and the renderer this repository shares
  must agree with the section's own on every line but the word's before the literal is compared.
* **The rows**: the mean node's section's 76 instants, by import of that generator — a grid every five
  years at four times of day, J2000, the profile's two ends, and instants where the node's argument
  passes 0/360°. Read warm, every row in one fresh process in row order, the calls recorded inside it
  and held to the rows.
* **Each row**: one compared value, the call's first, under `"unit": "degree"`; all six returned values
  in `returned_values`; the tidal-acceleration constant read back; `none`, reason `request_invariant`.
* **The band in its classification** is its consumer's — 0.05 arcsecond as 1/72000 degree, rounded
  once, bits `3eed208a5a912e32` — declared because the consumer asked for it. ⛔ It is not a
  measurement, and nothing here judges against it.
* **The row id** is a parameter. ⛔ It is the consumer's to register; the emission passed the consumer's
  working name for the row, and a different id is one more run.

---

## 2. The controls, at every row

| control | what was read | result |
|---|---|---|
| ① invariance | the pseudo-body under the five configurations, no non-ephemeris bit, each the one call of a fresh process | **380 of 380** bit-identical to their row at **all six** positions |
| ① witness | the Moon at the same instant under the same five | word by configuration `4, 4, 2, 4, 2` (analytical, analytical, data files, substituted, substituted) at every row; at each row the closest two answering sources were 0.002482″ to 1.699093″ apart; every reading the files answered at least 18 256 days inside the Moon's edge as the survey measures it |
| ② sufficiency | the section read again warm, in the reverse order | **76 of 76**, six of six; ⛔ no reading's fields on any row |
| ③ nutation twin | the row with `FLG_NONUT` added, in a fresh process | first value differs from the row's **76 of 76**; equals its own second and the row's second **76 of 76** |

The pseudo-body's word handed the request back in every one of its readings (`4, 4, 2, 2, 1` by
configuration, `66` for every twin), and the Moon's named the substitution under both conditions built
so that the request could not answer, at every row.

⚠ **The twin is compared to the bit, and the instants were not chosen against that.** Where a row's
first value and its twin's agree to the last bit, the twin control refuses the row. They differ by the
nutation in obliquity, which changes sign over a hundred times across the profile's interval. The
closest row, `grid_2095`, has its first value **0.011026″ — 862 087 134 doubles — from its twin's**;
every other row is at least 0.52″ apart. Read against this instrument's half-day grid of the same
output, that row lies about a day from a sign change, and every other row at least 36 days. Agreement
to the bit would need the instant within a fraction of a millisecond of one. ⛔ This is measured and
written into the record, ⛔ not a floor.

---

## 3. What the survey change moved

The survey's child now hands back every value its call returned, and the survey writes them —
`values` and `values_bits`, beside the named three — on the pseudo-body's readings alone.

| against | rows byte-identical | what moved |
|---|---|---|
| the survey that first read the pseudo-body (2026-11-02) | **179 of 189**, in order | the pseudo-body's 10 rows each **gained** `values` and `values_bits`, and nothing else on them moved; header: the two new row-schema lines and the three stamps |
| the survey the mean node's committed controls name (2026-10-31) | **179 of 179**, plus the pseudo-body's 10 | header: the pseudo-body's entries in the summary and its note, as recorded on 2026-11-02; the two new row-schema lines; the three stamps |
| the mean node's controls handed over on 2026-11-01 | **912 of 912** | header: the survey's digest (twice) and the three stamps |
| the mean node's section, regenerated as a control | **76 of 76** | the two stamps |
| the two value grids, regenerated as a control | **1329 of 1329 · 861 of 861** | the two stamps |

⚠ Every header stamps the commit it was generated from and the UTC day, so no regenerated file is
byte-identical to an earlier emission even where every row is. The regenerations are the control.

---

## 4. Tied to what this instrument already read

| against | result |
|---|---|
| the modes record (2026-11-02), at the three instants it shares with the section | the rows, warm: **15 of 15** of that record's cold readings under all five configurations, six of six; the controls' cold readings **15 of 15**; the twins **3 of 3** of its nutation-off readings under the same configuration, and **12 of 12** under the other four |
| the half-day grid (2026-11-03), at the 34 rows on its lattice | **34 of 34**, six of six, word 2 requested and returned |

---

## 5. Every refusal, planted

* **On the real output**: one real measurement, then each check given a planted failure — a subject
  reading one double away at each of the six positions under each of the five configurations; the
  regeneration one double away at each position; a twin equal to its row, a twin not its own second, a
  twin not the row's second, a twin without `FLG_NONUT`; the witness echoing under each absent-source
  configuration, the section's request not honoured, two answering sources not differing; a row outside
  the interval; five returned values; a row comparing its second value; a reading of three values; a
  sufficiency row carrying each of a reading's four fields; a same-order regeneration; a witness within a
  day of its edge; an edge for the pseudo-body; a returned word nobody requested; and the identity under
  word 66, word 4, another library version, another binding version and a fourth file. **61 of 61**
  refused by their own check, the unplanted measurement passing before and after.
* **In the generators**: each check removed, one at a time, from an exported copy of the commit, and the
  tests that guard it run — the section's own checks, the shared ones, and the survey's. At `5f001bf`,
  **45 of 46** turned the tests red. ⛔ The one that did not: removing the check that the section's
  renderer agrees with the shared one before the word line, because no test made them disagree. A test
  that does was added in `363a3bb`, which changes no generator; with it, **46 of 46**. The unplanted
  copy passed each time.

---

## 6. What is not established

* ⛔ **No judgment.** Nothing here compares any engine with these rows. The band is the consumer's.
* ⛔ **The consumer's reader was not run on these outputs.** Its code for the shapes these rows take
  lands on its own schedule; whether it reads them as written is its measurement.
* ⚠ **One shape was chosen here.** `returned_values` carries `values` beside `values_bits`: this
  repository's contract refuses a bit pattern with no value beside it, and the consumer's readers carry
  a decimal beside the bits elsewhere and check it against them. If its reader refuses the extra key,
  dropping it is one change and one run.
* ⚠ **The witness's readings carry the named three alone**, as the mean node's section's do.
* ⚠ **One host.** No other machine, library version or binding was read.
