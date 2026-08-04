# The conventions an ephemeris library applies without being asked

**2026-08-04.** Taken while building `generators/convention_probes.py`. Software: Swiss
Ephemeris 2.10.03 through `pyswisseph` 2.10.3.2, with the publisher's `.se1` data files for
the 1800–2399 block, pinned by SHA-256 and verified at read time.

⛔ **Recorder, never explainer.** Everything below is a return value observed under stated
conditions. Nothing here describes how any quantity is computed, and nothing here says an
answer is right — only that it is what this library, at this version, returned.

⚠ **Scope.** One release, one binding, one machine, one date. A later version may behave
differently, which is why every row of every fixture is dated and versioned.

Five questions were asked. ⭐ **Two of the five answers are the opposite of the assumption
a careful caller would have made**, and two more findings turned up that nobody had asked
for.

---

## 1. The time offset moves with an argument that is not about time

The entry point that converts a civil instant to the dynamical scale takes an **ephemeris
flag** — an argument naming a source of *positions* — and returns a duration.

| epoch | analytical | data files | spread |
|---|---|---|---|
| 1900-01-01 | −2.051326 s | −1.953326 s | **0.098 s** |
| 2000-01-01 | 63.828500 s | 63.828500 s | 0 |
| 2100-01-01 | 93.182046 s | 93.182046 s | 0 |

⭐ At the historical epoch the answer depends on which ephemeris was named, and the entry
point **reports nothing** about which one supplied the constants behind it. Two callers
converting the same civil instant, differing only in a flag chosen for unrelated reasons,
get instants 0.098 s apart with no notice.

⚠ **The entry point that takes no flag has still chosen one.** Its answer is bit-identical
to the data-file answer at every epoch measured — so "not passing a flag" is not neutral,
it is one of the three options taken silently.

⚠ The entry point returns **days**, not seconds. Both forms are written; the day value is
the authoritative one.

---

## 2. What a default position already carries, one term at a time

Each variant switches one term off; the difference from the default answer is that term's
size. Worst case over four epochs (1900, 2000, 2026, 2100) and three bodies:

| term removed | largest difference |
|---|---|
| the frame of date → a fixed frame | **5034.07″** |
| light-time and aberration together | 24.86″ |
| aberration | 20.86″ |
| nutation | 17.43″ |
| gravitational deflection | **0.0098″** |

⭐ **The grid is why the first row is not zero.** At the reference epoch the frame term is
identically zero; a sweep taken only there reports that the frame choice costs nothing. It
costs an arc-degree and a half a century away.

⚠ **A zero is not an absence.** The light source of the system reports exactly zero for
gravitational deflection at every epoch, while the distant planet in the same file reports
a real number — a body is not deflected by its own gravity. Reading that zero as
"deflection is off in the default" would be wrong, and the neighbouring row is what shows
it.

---

## 3. ⭐ The atmosphere nobody names, and it is not the one everybody assumes

A rise/set call takes a pressure and a temperature. The binding's declared default for both
is **zero**, so a caller who omits them has selected whatever the library does with a zero.

⭐ **Measured, as a bit-identity rather than an approximation:** omitting both arguments
returns **the very same double** as stating 1013.25 hPa at **0 °C** — at three sites and
three dates, every one identical.

So the pressure is the conventional sea-level one. ⛔ **The temperature is the trap.** The
temperature argument is taken *literally*: zero means zero degrees Celsius, a cold
atmosphere that refracts more than a temperate one. It is not a stand-in for a default.

The convention, expressed as the Sun's centre's true altitude at the instant the call calls
it a rising, at one temperate site:

| what was asked for | true altitude at the event | cost in time |
|---|---|---|
| **both arguments omitted** | **−36.592′** | — |
| 1013.25 hPa, 0 °C, stated | −36.592′ | **0.000 s (identical)** |
| 1013.25 hPa, 15 °C | −33.446′ | **+14.046 s** |
| 1013.25 hPa, −20 °C | −41.835′ | −23.404 s |
| 500 hPa, 0 °C | −16.387′ | +90.202 s |
| omitted, observer at 500 m | −34.283′ | +10.310 s |
| omitted, observer at 2000 m | −27.996′ | +38.378 s |
| centre, atmosphere off entirely | +0.147′ | +164.017 s |
| leading edge of the disc | −20.530′ | +71.707 s |
| the library's own named composite | +0.003′ | +163.375 s |

⚠ **The observer height is live even with the pressure argument at zero.** A site given an
elevation gets a different sunrise from the same site given none — 38 s different at
2000 m.

### ⭐ The cost of the wrong assumption is set by latitude and season, not by a number

Assuming 15 °C, in seconds of sunrise:

| site | equinox | June solstice | December solstice |
|---|---|---|---|
| within 2° of the equator | +12.59 | +13.72 | +13.73 |
| northern subtropics | +14.05 | +15.74 | +15.65 |
| southern mid-latitude | +15.74 | +18.04 | +18.22 |
| just below the polar circle | +28.79 | **+80.10** | +63.65 |
| above the polar circle | +61.36 | *no rising* | *no rising* |

⭐ A single-number rise/set budget across latitudes is set by its worst latitude, and its
worst season.

### ⚠ The same question has two different answers inside this one library

The entry point that converts an altitude to a refracted one treats a zero pressure as **no
atmosphere** and returns exactly **0.000′** of refraction. The rise/set entry point treats
the same zero as a real atmosphere. ⛔ **So calibrating the rise/set convention through the
refraction entry point returns the wrong answer, confidently and without a warning.**

---

## 4. The leap-second table has two ends, and the second one is not where anyone looks

The table was **extracted** by walking the conversion and differencing against the same
calendar instant read as a plain Julian day — which removes the smooth drift and leaves the
steps. ⚠ A first attempt differenced the wrong pair and reported a "step" at every scan
point, because the drift it had failed to remove is about half a second per scan interval.

* **27 whole-second steps**, first **1972-07-01**, last **2017-01-01**.
* Before the first: the offset moves by fractions of a second — a different regime, kept in
  the file rather than filtered out.
* After the last: the offset is held **exactly, to the bit**, for over sixteen years.

⭐ **And then it is not.** Bisected to the day: the held offset survives **2033-09-16** and
is gone by **2033-09-17**, where the conversion hands over to a smoothly drifting model. The
handover is a discontinuity of **1.000196 s**. ⚠ It is not a whole second and does not fall
on either of the two dates every insertion in this table falls on — both facts are recorded
on the row, so a reader can judge what it is without rerunning anything.

⛔ Nothing announces any of this. A civil instant on either side of that day converts with
about a second between them, and a long-dated calendar computation crosses it silently.

### ⭐ But it fails loudly in the one place it could fail quietly

Offered the sixty-first second of a minute:

| date | outcome |
|---|---|
| 2016-12-31 23:59:60 | accepted |
| 2015-06-30 23:59:60 | accepted |
| 2017-06-30 23:59:60 | ⛔ refused — *"invalid time (no leap second!)"* |
| 2026-06-30 23:59:60 | ⛔ refused — same |

The table is **enforced, not merely consulted**. So a real future insertion arrives in a
build whose table predates it as an **error**, not as a value that is silently one second
wrong. That is the better of the two available failures by a wide margin.

### Where a table can have come from

| configuration | offset at 2021-01-01 | changed? |
|---|---|---|
| a directory holding no such file | 69.184014 s | — |
| a file of the documented name in the directory the library was pointed at | **70.184009 s** | ⭐ **yes** |
| the same file in the process's working directory, no directory named | 69.184014 s | no |

⭐ The table is replaceable from disk, and **only** from the directory the library was
explicitly pointed at. So a caller that never names such a directory used the built-in one
— which makes the table a property of the **installed build**, recoverable from a version
pin alone, with no running machine required.

⛔ **And the table is read once per process.** It is not re-read when the library is closed
and re-opened, so it survives the reset that puts other state back. Each row above was
therefore measured in a **fresh process**: a first attempt, taken in a process that had
already converted one instant, reported that no override mechanism existed at all.

---

## 5. The house methods that stop — and the one that answers to any name

### ⛔ This build accepts every name it is handed

A punctuation mark, a digit and a lower-case letter were each offered as a house method.
Each was **answered**, with cusps identical to one real method's, at all four samples.

⭐ So "which names does it accept" has the answer "all of them", and an inventory built by
calling names and seeing which work is a list of aliases presented as a list of methods.
The names were therefore **grouped by the numbers they return**, over four unrelated
instants and latitudes — and the names that could not possibly be methods are what identify
the fallback, with no documentation consulted:

* **30 names offered, 24 distinguishable classes.**
* The class holding every control name also holds one real method's letter. ⛔ **A name this
  build does not implement silently becomes that method** — so a typo, or a method a
  deployment expects and this build lacks, returns numbers that are correct for a method
  nobody asked for.

### The polar limit is exact, and it moves

Three methods refuse above a latitude. Bisected per epoch:

| epoch | last latitude answered | 90° − obliquity of date | difference |
|---|---|---|---|
| 1900 | 66.54834730042457 | 66.54834730042458 | −1.4e-14 |
| 2000 | 66.56232328394513 | 66.56232328394515 | −1.4e-14 |
| 2026 | 66.56158949979661 | 66.56158949979663 | −1.4e-14 |
| 2100 | 66.57135132612186 | 66.57135132612187 | −1.4e-14 |

⭐ The limit is 90° less the obliquity **of date**, to machine precision — so it is not a
property of the site. It moves 0.023° between 1900 and 2100, and it moves within a single
year as well. A place just inside it in one century is outside it in another, and the
method that answers there changes with no change to the place.

### ⛔ The substitution is real and visible from only one of the two entry points

At 78° N, for each of the three methods:

| entry point | outcome | what it said |
|---|---|---|
| the one that returns cusps | refused | `houses_ex: error` |
| the one that also returns a message | refused | ⭐ `within polar circle, switched to Porphyry` |

The first names neither the substitution nor the method that answered. ⚠ Through this
binding both raise, so no mislabelled value reaches a caller — but a caller using the first
cannot tell "undefined at this latitude" from any other failure, and the *name of what
happened* exists only in a sentence returned by something else.

---

## What was found that nobody asked for

⭐ **The library keeps four pieces of process-wide state, and closing it does four different
things to them.** Measured by setting each, closing, and reading it back:

| state | what a close does |
|---|---|
| the sidereal mode | dropped — reverts to the default |
| a user-defined time offset | ⛔ **survives** — one call redefines time for the whole process |
| the tidal acceleration | ⚠ **changed** — to neither the value it was set to nor the one it started at |
| the leap-second table | ⛔ **survives, and is never re-read** |

⛔ **A reset that restores some state is worse than no reset**, because the part it drops is
invisible in every value that follows. Two of these four are not restored at all, and one is
altered by the act of resetting.

---

## What the fixtures record

Six files in `out/conventions/`, 1 638 rows, regenerated byte-for-byte identical:
`time-offset.jsonl` · `apparent-position.jsonl` · `rise-refraction.jsonl` ·
`leap-seconds.jsonl` · `polar-houses.jsonl` (all `numeric_pin`) and `library-state.jsonl`
(a `provenance_record`).

⛔ **Every section is `reference_only`, and that is the honest class.** These are one
implementation's conventions. Nothing here has been compared against an authority, so there
is no band to declare — and a consumer that decides to adopt one of these conventions, or to
hold its own within some distance of one, is making a reviewed decision this repository has
no standing to make for it.

⚠ Every value carries its IEEE-754 bit pattern beside the decimal, and the inputs carry
theirs too. An output is compared; an input is *replayed*.
