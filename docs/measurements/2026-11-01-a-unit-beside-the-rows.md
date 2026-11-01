# A unit beside the rows is not a unit on them · 2026-11-01

> ⭐⭐⭐ **A ROW IS READ ALONE.** The mean node's section declared its unit once, in its
> classification, and on none of its 76 rows. Its consumer reads the size of the circle a row is
> compared on from **that row's own unit**, never from a classification beside it, so it refused
> every row and judged nothing. The same observation, judged against the same section with
> `"unit": "degree"` on each row, was compared at all 76. ⛔ Measured in that consumer's own reader,
> in a throwaway copy, before this note was written. Nothing else in the section moved: not a value,
> not an instant, not the configuration or its identity.

---

## 0. What this session wrote

One generator commit, `1cc3d8c` (pushed; CI `ci` green, run 41324272366), and from it two files:

| output | kind | rows | sha256 | written by |
|---|---|---|---|---|
| `mean-node-section/mean-node-section.jsonl` | R3 `numeric_pin` — the mean node through `calc`, one section | 76 | `318920ed…321c` | `mean_node_section.py` at `1cc3d8c` |
| `mean-node-section/mean-node-section-controls.jsonl` | R3 `provenance_record` — its controls | 912 | `1b133540…5b5a` | the same run |

Each was generated twice from that commit and the two were **byte-identical**. The host, the
library, the binding and the data files are the ones of 2026-10-31's emission. The controls read the
witness's edge from **the survey emitted on 2026-10-31, unchanged** (`15a18bc6…271a`), and record its
digest.

The change, in the generator: every row carries `"unit": "degree"`, written from the one constant the
classification's unit is also written from; the section refuses to be written if any row carries no
unit or another spelling of it; and the header's `budget_row` is `BU03`, the id the consumer minted
for the row it compares this section against. That id replaces this file's earlier proposal,
`mean-node-convention-1`.

---

## 1. What moved, against the emission of 2026-10-31

The expected difference is the control. Read field by field, header and rows:

| file | rows byte-identical | header fields that moved |
|---|---|---|
| the section | **0 of 76**. Each row gained `unit`, and nothing else on any row moved | `budget_row`; the row schema's new `unit` line; the summary's `budget_row` sentence; `generator.commit`; `generated` |
| the controls | **912 of 912** | `generator.commit`; `generated`; `record_date` |
| the survey, regenerated as a control | **179 of 179** | `generator.commit`; `generated`; `record_date` |
| the two value grids written beside it | **1329 of 1329** · **861 of 861** | `generator.commit`; `generated` |

The section's values, their bit patterns, its instants, its classification (`tolerance`, band 0,
`degree`), its configuration and its identity
`bb60c5b3cf3d84612253cc3a984ae799fdf2db9280b9b31136c815e47ccf5be7` are all unchanged.

⚠ **Why the survey was regenerated but not handed over again.** Every header here stamps the commit it
was generated from and the day. A regeneration from a later commit, or on a later day, therefore
cannot be byte-identical to an earlier emission, even when every row is. The regeneration is a
control: its rows match the emitted survey's exactly, so nothing this commit touched reaches the
survey. The survey handed over on 2026-10-31 stands, and the new controls name its digest, so the
survey and the controls are still a pair.

---

## 2. In the consumer's reader

The consumer's code that reads a row's unit is not committed yet. Its rule is written down, and a
throwaway prototype of it existed. So this part is a **prediction** of how the section will be judged.
The judgment itself is the consumer's to make.

**Unchanged.** With the new controls in place of the old ones, the consumer's evidence constructs as
it did with the 2026-10-31 outputs, and every decision it prints about every body, entry point and
word is the same. Only the controls' digest differs. The consumer's own tests move exactly as they
did with the earlier outputs. The one exception is the refusal that named the earlier proposal for
the row id, which now names `BU03`. Given a registry holding that row, that test loads the section.

**Judged.** One observation, the section's own longitudes shifted, judged against a row in degrees
with a band of 0.001:

| the observation | section rows with no unit | section rows carrying `degree` |
|---|---|---|
| identical | ⛔ cannot judge: 76 of 76 refused for want of a unit | pass, 76 rows, every component bit-identical |
| + 0.0005° | ⛔ cannot judge: 76 refused | pass, worst arc 0.0005° |
| + 0.0011° | ⛔ **cannot judge**: 76 refused | **fail**, worst arc 0.0011° |
| + 360° | ⛔ cannot judge: 76 refused | pass, worst arc 5.7 × 10⁻¹⁴° |

⭐ The third line is the reason for the fix. A section that cannot be compared fails closed, so
nothing passed that should not have. But an observation that should fail did not fail either. A gate
that can only say *cannot judge* checks nothing.

---

## 3. The band

The section is still classified with the band this instrument measured between a row and every
other reading of it: 0. Its consumer applies a band of its own, and where the two differ it
**reports** the difference, as it did on every line above, and refuses nothing.
⛔ Copying the consumer's figure would make the declaration say what the consumer applies rather than
what was measured. The declared band is context, and that is all it claims.

---

## 4. How the checks were shown to fire

Red first, each against the generator as it stood. Five new tests:
* the static id;
* a section row with no unit, and one spelled `deg`, each refused beside the conforming twin, which
  passes;
* every emitted row's unit;
* the emitted header's id.

Each failed on its own value, not on a missing name: the mutations because nothing refused them, and
the rest because the old value was there. Then each new check was planted out of the source, one at a
time, the suite run, and the source restored and compared byte for byte. **5 of 5** were caught:
* the row's unit removed (generation refused);
* the refusal removed;
* the old id;
* another spelling of the unit;
* the schema's line removed.

Suite 732 → **737**. The reduced run, with no ephemeris library, went 482 / 58 → **485 passed, 60
skipped**.

---

## 5. What this does not establish

* ⛔ Nothing about the sky. It records what one release returned under one declared configuration, on
  one host.
* ⛔ No judgment. The rows above judge the section against itself, shifted, through a prototype; the
  consumer judges its own engine against this section.
* ⚠ The row `BU03` is the consumer's. This file names it, and nothing here asserts it exists.
