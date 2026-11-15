# The returned values as patterns alone · 2026-11-15

> ⭐⭐⭐ **A NESTED OBJECT IS WRITTEN IN THE SHAPE ITS READER TAKES, AND THE RULE IT LEAVES SAYS SO.**
> The nutation and obliquity section of 2026-11-14 carried every value the call returned in
> `returned_values` as bit patterns with the six decimals beside them, because this repository's
> contract refused a pattern with no value beside it. The reader of that object takes it with one
> member, `values_bits`, and refuses a second. So the decimals are no longer written there, and the
> contract states one exemption from its pairing rule for that key in that object, and for nothing
> else. ⛔ Emitted again, all four files together: every section row lost that one member and nothing
> else, and every other file moved only by its stamps and the survey's digest.

---

## 0. What this session wrote

One generator commit, `7c4decf` (pushed; CI `ci` green, run 43734628965), and from it, twice, the same
seven files. Four are outputs; three are controls of what the commit did not change.

| output | kind | rows | sha256 | written by |
|---|---|---|---|---|
| `nutation-obliquity-section/nutation-obliquity-section.jsonl` | R3 `numeric_pin` — the pseudo-body through `calc`, one section | 76 | `2531ecb6…252f` | `nutation_obliquity_section.py` |
| `nutation-obliquity-section/nutation-obliquity-section-controls.jsonl` | R3 `provenance_record` — its controls | 912 | `46ce2c57…5a73` | the same run |
| `survey/swiss/r3-flag-reporting.jsonl` | R3 `provenance_record` — the per-body survey | 189 | `b78daa40…12bf` | `r3_swiss.py` |
| `mean-node-section/mean-node-section-controls.jsonl` | R3 `provenance_record` — the mean node's controls, against that survey | 912 | `911417b7…8f11` | `mean_node_section.py` |

The two emissions were **byte-identical**, all seven files. Host, library, binding, data files and
data profile manifest are those of 2026-11-14 (macOS-27.0.1-arm64, CPython 3.12.11, library 2.10.03,
binding 2.10.3.2). The configuration still renders
`c893013badb8338ed6de303033a6862f0a0564b357da1523f61d6c663bb22ac7`, in the section's summary and on
all 912 rows of its controls.

⭐ **The four go together.** Both sets of controls read the Moon's edge from the survey and name its
digest. The survey's rows did not move, but its header stamps its commit, so its digest did, and both
sets of controls were emitted against it in the same run. ⛔ None of the four is handed over without
the other three.

---

## 1. The change

* **In the section.** Each row's `returned_values` is `{"values_bits": [six patterns]}`, in the order
  the call returned them, the first equal to the row's compared value. The section refuses to be
  written if any row's `returned_values` carries anything beside `values_bits` — tested with the
  decimals written back and with an unrelated member. Its row schema says so. ⛔ Nothing else in the
  generator changed: the compared value, every control and every reading are as before, and the
  digests this repository pins of its readings held.
* **In the fixture contract.** `UNPAIRED_PATTERNS` in `fixture.py` names the exemption once:
  `values_bits` in a row's own `returned_values` may name no value. It waives the partner and nothing
  else. The patterns are still checked, sixteen lowercase hex digits each; a `values` written beside
  them is still paired and verified; any other pattern key in that object still has to name its value.
  `docs/fixture-contract.md` states it.
* ⛔ **Held narrow by tests.** The same key without its values is still refused at a row's top level,
  in another object of the row, one level deeper, inside a list and in a header, and another pattern
  key beside it is still refused.

Written test first: 55 of the two files' tests red before the change, all 161 green after. Suite
**1009** (was 991); without the binding, **662 passed, 148 skipped** (was 644 and 148).

---

## 2. What moved, field by field

Against the emission of 2026-11-14, every field moved that was predicted, in writing, before the
change was made, and no other.

| file | rows byte-identical | what else moved |
|---|---|---|
| the section (was `b753a361…`) | **0 of 76** — and each earlier row with `returned_values.values` removed is the new row **byte for byte, 76 of 76**, in order | header: the commit, the day, and the row schema's line for `returned_values` |
| its controls (was `d5434e5a…`) | **912 of 912**, in order | header: the survey's digest (twice), the commit, the day, the record date |
| the survey (was `c1754cc3…`) | **189 of 189**, in order | header: the commit, the day, the record date |
| the mean node's controls (was `a0d94c7a…`) | **912 of 912**, in order | header: the survey's digest (twice), the commit, the day, the record date |
| the mean node's section, regenerated as a control | **76 of 76** | the commit, the day |
| the two value grids, regenerated as a control | **1329 of 1329 · 861 of 861** | the commit, the day |

Every new section row's `returned_values` is `values_bits` alone, six patterns, the first the row's
compared value: **76 of 76**.

⚠ Every header stamps the commit it was generated from and the UTC day, so no file is byte-identical
to its predecessor even where every row is.

---

## 3. Every check again, on the new output

| check | result |
|---|---|
| the generator's own, at every row | ① **380 of 380** subject readings bit-identical to their row at all six positions; the witness's word `4, 4, 2, 4, 2` by configuration, two answering sources 0.002482″ to 1.699093″ apart, at least 18 256 days inside the Moon's edge; ② **76 of 76**, six of six; ③ **76 of 76** for both clauses, the closest row `grid_2095` at 0.011026″ (862 087 134 doubles) from its twin — each as on 2026-11-14 |
| every refusal planted on the real output | **62 of 62** refused by their own check: the 61 of 2026-11-14 (the two that read the decimals beside the patterns now read the patterns), and the decimals written back beside them; the unplanted measurement passed before and after |
| every check removed from an exported copy of `7c4decf` | **55 of 55** turned the tests that guard it red: the 46 of 2026-11-14 (one re-anchored where the check was split), the section's one-member check and its row, and seven on the exemption — removed; not held to the row's own object; not held to its one key; its patterns not checked; an empty list let stand; a second pair of names; any object so named at any depth |
| the modes record (2026-11-02), at the three instants it shares | rows **15 of 15**, cold readings **15 of 15**, twins **3 of 3** and **12 of 12** |
| the half-day grid (2026-11-03), at the 34 rows on its lattice | **34 of 34**, six of six |

---

## 4. What is not established

* ⛔ **No judgment.** Nothing here compares any engine with these rows. The band is the consumer's.
* ⛔ **The consumer's reader was not run on these outputs.** That it takes `returned_values` with
  `values_bits` alone is read from its source, ⛔ not measured here.
* ⚠ **One host.** No other machine, library version or binding was read.
