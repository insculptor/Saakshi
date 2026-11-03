# A step chosen against the convention · 2026-11-03

> ⭐⭐⭐ **EVERY HALF DAY ACROSS THE INTERVAL, AND NOTHING MOVED.** The library's nutation and obliquity
> pseudo-body was read through `calc` at **219 205** instants: every half day from 1849-12-26 to 2150-01-22,
> and the modes record's four instants outside that interval. Each reading was the one call of a fresh
> process, under the data-file request with the pinned files and the default word. It returned the word it
> was handed in **241 185 of 241 185** readings. At **2 198** subset instants, read again under five
> configurations and both words, the six values were **one set per word at every instant**. At the modes
> record's seven instants, every reading here is that record's, **bit for bit**. ⚠ The step was chosen
> against a published convention about what a nutation model contains, ⛔ not against anything measured in
> the library.

---

## 0. What this session wrote

One generator commit, `f7a67d0` (pushed; CI `ci` green, run 41696141548), and from it one file:

| output | kind | rows | sha256 | written by |
|---|---|---|---|---|
| `nutation-obliquity-grid.jsonl` | R3 `provenance_record`: the pseudo-body through `calc` on a half-day grid, and under every request at a subset of it | 241 185 | `48a70a79…8be0` | `nutation_obliquity_grid.py` at `f7a67d0` |

It was generated twice from that commit, on one UTC day, and the two were **byte-identical** (102 193 436 bytes each).

The host is macOS arm64, CPython 3.12.11, the library 2.10.03 through its binding 2.10.3.2. The data files are
the three pinned `.se1` files. The interval is read from the `standard@1` data profile manifest
(`b68407a3…73ee`), as the modes record read it. The record ties to the modes record emitted on 2026-11-02
(`17ecaa66…c86f`, generator commit `1a17fe9`).

⭐ **The modes generator did not change.** It was run again at `f7a67d0`: its 293 rows are byte-identical to
`17ecaa66…`, in their order, and only its three stamps moved (`generator.commit`, `generated`, `record_date`).

---

## 1. What was read

* **The subject**: the pseudo-body for nutation and obliquity (body `-1`), through `calc` on a dynamical-time
  Julian day. The library's documentation names its six values: the true obliquity, the mean obliquity, the
  nutation in longitude, the nutation in obliquity, and two zeros. ⛔ `calc_ut` is not read here. The modes
  record measured it moving wherever its conversion moved.
* **The grid**: a lattice from the interval's start to its end, `jd = 2396752.5 + k × 0.5` for `k` from 0 to
  219 200, so its last instant is the interval's end exactly. The modes record's three instants inside the
  interval are lattice instants: the start (`k` = 0), J2000 (`k` = 109 585) and the end (`k` = 219 200). Its
  four instants outside (1000-01-01, 1500, 3000-01-01, 3000) are read as well. Every Julian day is written as
  a decimal and as its bits.
* **The configuration**: the data-file request with the pinned files on the path, under the modes record's
  default word (requested word `2`). All six values of a grid row come from that one word. ⛔ Never "no path
  set".
* **The subset**: every 100th lattice instant from the start (one every 50 days, both ends among them; 2 193),
  plus J2000 and the four instants outside, so 2 198 instants. At each, the five configurations of the modes
  record under both of its words: 21 980 readings.

---

## 2. The step, and why half a day

Its consumer will compare a periodic series, so no term may hide between samples.

* The library's documentation names IAU models of 2000 and 2006 for its nutation (section 5 below).
* The IERS Conventions (2010), chapter 5, section 5.3.2, state that under IAU 2000 Resolution B1.7 *"the celestial
  motion of the CIP (precession-nutation), includes all the terms with periods greater than 2 days in the
  GCRS"*.
* At half a day, every term with a period over two days is read more than four times per period. So in every
  period some sample falls within an eighth of a period of the term's extreme, and reads at least cos 45°,
  about 0.71, of its amplitude.
* ⛔ **A daily step is not enough under that convention.** It reads a two-day term twice per period, and both
  samples can fall on its zeros.
* ⭐ **And half a day puts J2000 on the lattice.** The interval starts at 0h and J2000 is at noon. A daily 0h
  lattice would have missed it, and the modes record's instant would have been an addition, not a member.

⛔ **The step is chosen against the convention, not against the library.** Whether the library's output holds a
term of shorter period is not established here. Nothing between two samples is read.

---

## 3. Reading 241 185 children

* ⭐ **The reading is the modes generator's, by import, and never by copy.** The following are that generator's
  objects: the child program, its spec, the rule that admits a child (its recorded calls must be exactly the
  sequence its finished row declares), the epochs, the interval, the configurations, the directory checks and
  the data-file pins. A test holds that none of them is defined again here.
* **The rule is applied to the row as written.** It is applied together with the header's constants: every
  reading is `calc` of the pseudo-body, and the grid's directory is the data files'. A row whose instant, word
  or directory differs from what its child did is refused.
* **One child per reading, several at once.** Measured on this host, a fresh child costs about 35 ms one at a
  time and about 6 ms per reading with eight at once. So the modes record's discipline was kept for all
  241 185 readings, eight children at a time: each emission took 27½ to 28 minutes, about 7 ms a reading.
  * Each child is its own process, so no reading shares the library's state with another.
  * Rows are written in the grid's order, ⛔ never the order the children finished.
  * Each thread keeps its own children's nonces, and every nonce across them is held distinct afterwards.
* ⚠ **Found while building it.** Importing the modes generator wrote its bytecode beside it. In a tree that
  does not ignore bytecode, that untracked file made the tree dirty, and the record was refused. The generator
  now writes no bytecode, and a test holds the order.

---

## 4. What came back

| | measured |
|---|---|
| returned word = requested word | **241 185 of 241 185** readings (grid and subset) |
| one set of six values across the five configurations, default word | **2 198 of 2 198** subset instants |
| the same, nonut word | **2 198 of 2 198** subset instants |
| the grid's reading = its subset twin (another fresh child, the same configuration and word) | **2 198 of 2 198** |
| readings at the modes record's instants equal to that record's, bit for bit | **70 of 70** subset readings and **7 of 7** grid readings |
| the nutation-off relation held | **10 990** pairs |

* ⭐ **The echo held everywhere.** For this body the returned word is the request handed back (the modes
  record), so it says nothing about which ephemeris answered. ⛔ It is recorded, never read as a report.
* ⭐ **The relation the modes record measured for the nutation-off word held at every pair.** Under that word,
  position 1 is its default twin's, position 0 is position 1, and positions 2 and 3 are zero. Under the default
  word, positions 0, 2 and 3 differ from the nutation-off word's. Bit-identical across the two words at
  positions 0–5: 0, 10 990, 0, 0, 10 990 and 10 990 of 10 990. ⛔ Numbers, not a mechanism.
* **Read back beside each value, and counted** (`summary.read_back`): the tidal-acceleration constant before
  and after the call, and the library's report of its open files. The tidal constant was −25.936 before and after every reading with the data files on the path (the grid's 219 205, and 4 396 under each of three configurations), and −25.8 before and after every reading with the empty directory on the path (4 396 under each of two). The open-files report named `sepl_18.se1` and `semo_18.se1` with the files on the path; with the empty directory, its first slot named `sepl_18.se1` with a zero range and its second named nothing. ⚠ Recorded, never interpreted.

---

## 5. The library's documented models

From the library's published documentation only. ⛔ Nothing was read from, or about, its source.

| document | address | retrieved | sha256 | release |
|---|---|---|---|---|
| general documentation | `https://www.astro.com/swisseph/swisseph.htm` | 2026-11-03 | `7ca3f886…5aa2` | its release history ends at 2.10.03 (27-aug-2022) |
| programmer's documentation | `https://www.astro.com/swisseph/swephprg.htm` | 2026-11-03 | `8fe1629b…bff3` | its list of changes ends at 2.10.02 → 2.10.03 |

| model | where | the documentation's words |
|---|---|---|
| precession | general, 2.1.3, *Precession* | "(From Swiss Ephemeris 1.78 on, we use the precession model Vondrák/Capitaine/Wallace 2011.)" |
| precession | programmer's, 29.25 (1.77 → 1.78) | "precession is now calculated according to Vondrák, Capitaine, and Wallace 2011." |
| obliquity | general, 2.1.2 item 4 (1.78 and 1.77) | "Version 1.78 calculates precession and ecliptic obliquity according to Vondrák, Capitaine, and Wallace, “New precession expressions, valid for long time intervals”, A&A 534, A22 (2011), which is good for +- 200 millennia." |
| nutation | general, 2.1.3, *Nutation (true equinox of date)* | "(From Swiss Ephemeris 2.00, we use the nutation model IAU 2006. Since 1.70, we used nutation model IAU 2000. Older versions used the nutation model IAU 1980 (Wahr).)" |
| nutation | general, 2.1.2 item 3 (1.70 and older) | "Nutation IAU 2000B (could be switched to 2000A by the user);" |
| nutation | programmer's, 29.36 (1.67 → 1.70) | "the nutation model IAU2000B (can be switched to IAU2000A)" |

Each quote occurs exactly once in its document as retrieved.

* ⚠ **The documentation names more than one nutation model, and nothing here reconciles them.** Which one is
  in force for this output is not established.
* ⛔ **The models in force were not read, and none was changed.**
  * No function the binding exports reads or sets a model: none of its 149 callables, or its submodule's, has
    a name that names one.
  * The programmer's documentation documents none either (searched for `astro_models`, `SEMOD`, `SE_MODEL`: no
    hits).
  * The binding does export integer constants under model names. For example `MOD_NUT_DEFAULT` has the value
    it exports as `MOD_NUT_IAU_2000B`, and `MOD_PREC_DEFAULT` the value of `MOD_PREC_VONDRAK_2011`. The record
    lists them as exported. ⚠ They are not a reading of what is in force, and nothing here is decided from
    them.

---

## 6. The record's shape

This instrument's own measurement file, JSONL, the fixture contract's `provenance_record`. ⛔ **It is not a consumer's
shape, and it is not offered as one.**

* **Line 1, the header**:
  * `generator`: the commit;
  * `oracle`: host, library and binding versions, the data-file pins, the session's isolation statement (the
    modes record's, character for character), the children at once, the environment variables removed;
  * `summary.interval`: the manifest's digest and coverage;
  * `summary.grid`: the configuration, the requested word, the step, its reason, the convention's words, and
    the lattice's rule and extent;
  * `summary.invariance`: the subset's rule, stride and counts, and what was measured over it;
  * `summary.nonut`, `summary.tie` (the modes record's digest, commit and host), `summary.documented_models`,
    `summary.binding` and `summary.read_back`;
  * `summary.readings`, `summary.children` and `summary.rows_by_part`: the row count.
* **Then one row per reading**:
  * `part`: `grid` or `invariance`;
  * `configuration`, `ephemeris_requested`, `path_state` and `nutation`: on subset rows only, because a grid
    row's are the header's;
  * `epoch_id`: only at one of the modes record's instants;
  * `lattice_index`: only on the lattice, where `jd = summary.grid.lattice.first_jd + lattice_index ×
    step_days`;
  * `jd` and `jd_bits`, and `in_supported_interval`;
  * `requested` and `returned`: whole words;
  * `values` and `values_bits`: all six, the bits being the values.

---

## 7. How the checks were shown to fire

* 61 tests. Every refusal is tested beside the record as written, which passes.
* Every row of a short emission (185 lattice instants, eight subset instants, 269 readings) is pinned by one
  digest (host-bound).
* Each check was planted out of the source one at a time, the tests run, and the source restored and compared
  byte for byte: **46 of 46** were caught. Among them, each clause of the nutation-off relation was caught on
  its own.
* Three of them were applied again by hand, to confirm each was caught by the test written for it and not by
  another.
* Suite 801 → **862**. The run with no ephemeris library went 508 / 97 → **528 passed, 138 skipped**.

---

## 8. What this does not establish

* ⛔ Nothing about the sky. It records what one release returned at declared instants, under declared
  configurations, on one host.
* ⛔ No band, no class, no unit and no budget row, and no claim that any reading can gate anything. Whether the
  library can serve as a comparand is its consumer's question.
* ⛔ Nothing between samples. The step bounds what a term of period over two days can hide, under the
  convention, ⛔ not what the library's output does between two instants.
* ⚠ Invariance was read at the subset only: the grid's other instants were read under one configuration and one
  word.
* ⚠ Not measured: `calc_ut`; the speed or sidereal words; any other entry point, library version or host; the
  models in force.
* ⚠ Honest error, not forgery, as in the modes record: a reference to the library bound before the wrapping, or
  a call through one of its classes, is outside every call record here.
