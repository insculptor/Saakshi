# The same questions under a newer file · 2026-11-12

> ⭐ **The of-date probe, asked again and unchanged, after the Earth-orientation file named by the publisher's
> service had changed.** One request first read that file's name from a response header. It had changed since
> the earlier record, `2026-11-09-two-frames-on-one-line.md`. The probe then ran twice from an unchanged tree,
> sixteen requests each, answered by the interface version and the solutions this instrument's R1 sampler
> recorded. The two emissions were **byte-identical** to each other.
> * **Against the earlier emission, printed values moved at three instants only**: the three after the end of
>   both files' predictions. Nothing printed moved before the data, inside it, or at the predicted instant.
> * Beside the stamps every regeneration moves and the Earth-orientation lines themselves, one header line moved
>   in every observer response.
>
> ⛔ This repository holds the generator and this note. **The readings are held outside it**, as before. No value
> the service printed is written here.

---

## 0. What this session wrote

This note, and nothing else. The generator is the earlier record's, unchanged:
`generators/r1_of_date_probe.py` and everything it imports are byte-identical between the commit that emitted
the earlier readings and the commit that emitted these.

The probe was run twice from `8ed0555` on one UTC day. It wrote one `provenance_record` under R1 each time,
with 16 request rows and 476 reading rows, as before.
* The two files have the same sha256, `67064e3d…8d48`.
* A field-by-field comparison of the two found no difference in any of 419 header leaves or 15 777 row leaves.
* The sixteen cached resources were identical too.

The host, the interpreter and the data profile manifest (`b68407a3…73ee`) were the earlier record's.

---

## 1. What was read

* **One request first**, for the Earth-orientation lines in its header. It sent the same query as one of the
  earlier session's exploratory requests: the Sun, one instant inside the predicted interval, both quantities,
  degrees with extra precision.
  * The file the header named had changed since the earlier record.
  * So had its coverage: its data and its prediction both ended later.
* **Then the probe, twice.** The bodies, instants, variants, client and pause between requests were all the
  earlier record's.
* **Thirty-three requests in all**, one at a time, under the earlier record's client name.
* **No stop.** Every response named the interface version R1 recorded, and the solution R1 recorded for every
  body read and for the centre.

---

## 2. What moved, against the earlier emission

The two emissions were compared field by field: header leaves, and rows keyed by finding, request, instant and
Julian day. Both have 419 header leaves, 492 rows and 15 777 row leaves. **1 117 leaves moved**:

| where | leaves moved | which |
|---|---|---|
| header | 10 of 419 | the 4 stamps every regeneration moves (the generator's commit, the generation date, the query date, the record date), and the Earth-orientation file and coverage of each of the 3 service states observed |
| request rows | 62 | the Earth-orientation file and coverage on 16 of 16 requests; the resource's digest and length on 15 of 16 (every observer request; the vector request's resource did not move) |
| reading rows, service state | 952 | the Earth-orientation file and coverage on 476 of 476 readings |
| reading rows, printed fields | 93 | below |

**Printed fields, by quantity and instant class.** Each instant is classed against the newer file's coverage.
No instant changed class between the two files.

| instant class | instants | observer readings | quantity 2 fields moved | quantity 31 longitude moved | quantity 31 latitude moved |
|---|---|---|---|---|---|
| before the data | 3 named, and 33 of the window | 210 | 0 | 0 | 0 |
| inside the data | 3 named, and 32 of the window | 205 | 0 | 0 | 0 |
| predicted | 1 | 15 | 0 | 0 | 0 |
| after the prediction | 3 | 45 | **48**, on 24 readings | **45** of 45 | 0 |

* **Quantity 2** moved at every after-prediction reading whose format prints its extra-precision digits: 15 of 15
  readings in degrees and 9 of 9 in hours. That is right ascension and declination on each of those 24, for 48
  fields. Under the three formats that print fewer digits, it moved on none of 21 readings.
* **Quantity 31's longitude** moved on every after-prediction reading, under every format: 45 of 45. Its latitude
  moved on none of the 475 observer readings.
* **The vector reading** did not move.
* **Digits.** No field's count of printed decimals changed, and every value kept its printed shape.

**The response text**, compared line by line over the sixteen cached resources, with the stamp and the service
state cut out by R1's rule:
* In each of the 15 observer responses, four lines changed:
  * the three data lines of the after-prediction instants;
  * one header line, the step size. It read `0 steps` on 2026-11-09 and now reads `DISCRETE TIME-LIST`, the form
    the vector response printed on both days.
* The vector response did not change.
* The first, single-instant request changed in the same step-size line. It also changed in its stop-time line:
  printed half a second after the start before, and now printed equal to it.
* ⚠ No check of this probe reads either line, and none refused. The interface version named was the same.

---

## 3. What this does not establish

* ⛔ **Nothing is derived here.** Nothing in this repository relates the two frames, or says whether anything
  computed from them moved with the file. The fields that moved are counted; nothing is computed from them.
* ⛔ No band, no class, no unit for a comparison and no budget row, and no claim that any reading can gate
  anything.
* ⚠ **One pair of files, each read on one day.** What a later file moves is not established by this one.
* ⚠ The predicted instant did not move. Whether the two files differ there below the printed digits is not
  established.
* ⚠ Why the step-size and stop-time lines changed is not established. The interface version was the same, and
  the interface document was not re-read this session.
* ⚠ Reproducible only while the recorded service state holds, as before.
