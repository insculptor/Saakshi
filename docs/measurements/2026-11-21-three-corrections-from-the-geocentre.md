# Three corrections from the geocentre · 2026-11-21

> ⭐ **The same ten bodies, from the geocentre, in the ICRF and in TDB, under each correction the publisher's
> vector interface offers.** The publisher's ephemeris service was asked for state vectors of the Sun, the Moon,
> Mercury, Venus and the system barycentres of Mars to Pluto, at 507 instants across a data profile's interval,
> under `VEC_CORR` `NONE`, `LT` and `LT+S`. That is 210 requests, one at a time, and 15 210 rows of nine printed
> values each, every value with its bit pattern. Every response named interface version 1.2 and DE441 for every
> body and for the centre. Every response stated its own corrections in words that agree with the interface's
> document, and was held to them. The grid was emitted twice, once from live requests and once from the copies
> those requests left; **the values file was byte-identical**, and the acquisition record differed only in naming
> which. ⛔ This repository holds the generators and this note. **The values are not committed here.**

---

## 0. What this session wrote

| commit | what | CI |
|---|---|---|
| `c6e0e89` | the leak check's word boundary spelled in POSIX classes, so it runs on the git that ships with macOS | `ci` green, run 44953009376 |
| `8316b7f` | the hidden flag that stamped a dirty tree as clean, removed | `ci` green, run 44953513242 |
| `d211173` | one User-Agent with product, version and contact on every request, recorded in every acquisition record | `ci` green, run 44954000424 |
| `0673506` | every source assertion passes its body, word and measured attestation; a reading that raises stops a generator before anything is written | `ci` green, run 44954924556 |
| `d1d4fe7` | `generators/r1_geocentric_vectors.py` and its tests | `ci` green, run 44956575340 |
| `3810df7` | at most 75 instants per request, after the service truncated a longer list (section 3) | `ci` green, run 44957526619 |
| `85bdf33` | `generators/r1_geocentric_drift.py` and its tests | `ci` green, run 44958908441 |

The grid was emitted from `3810df7`. The host is macOS arm64, CPython 3.12.11. The interval is read from the
`standard@1` data profile manifest (`b68407a3…73ee`) by the obliquity records' own reader, by import.

---

## 1. What was asked

* **The request and the service state are R1's, by import**: the address, the query encoding, the retrieval
  with its canonical form, the generation stamp cut out of the digest, and the rules for the interface, the
  target's and the centre's solution and the Earth-orientation file. Only this table's three extra columns, the
  echoes and the response's own two paragraphs are read in the new generator.
* **Every parameter that selects the reading is sent explicitly**: `EPHEM_TYPE 'VECTORS'`, `CENTER '500@399'`,
  `REF_PLANE 'FRAME'`, `REF_SYSTEM 'ICRF'`, `TIME_TYPE 'TDB'`, `TLIST_TYPE 'JD'`, `OUT_UNITS 'AU-D'`,
  `VEC_TABLE '3'` (the state vector, one-way light-time, range and range-rate), `VEC_LABELS 'NO'`,
  `VEC_DELTA_T 'NO'`, `CSV_FORMAT 'YES'`, `OBJ_DATA 'NO'`. `CENTER` and `VEC_CORR` are arguments of every
  function that builds a request.
* **The bodies**: the Sun 10, the Moon 301, Mercury 199 and Venus 299 by their centres, and the system
  barycentres 4 to 9. ⛔ No body centre of Mars to Pluto was asked: the service answers those from separate
  satellite solutions, and the short-span planetary kernel carries only the barycentres.
* **The instants, by one written rule** (`EPOCH_RULE` in the generator), 507 in all, in TDB:

  | stratum | rule | instants |
  |---|---|---|
  | interval ends | the profile's declared coverage, one day inside each end | 2 |
  | sparse | from 1850-01-01, every 1000 days, to the interval's end | 110 |
  | dense | from 1900-01-01 to 2050-01-01, every 200 days | 274 |
  | goldens with a year or a date and no fixed instant | 1855: its first instant; 2145: the first instant of each quarter; 1995-10-24: every sixteenth of a day from 00:00 to 12:00 | 1 + 4 + 9 |
  | conjunctions with the Sun | per body, the first lattice days after 1900, 1950, 2000 and 2050 on which the angle between its and the Sun's geometric geocentric directions is a local minimum: two each for the Moon, Mercury and Venus, one for each barycentre | 48 |
  | stations | per planet, the first two lattice days after each anchor after which the sign of its geometric geocentric ecliptic-J2000 longitude rate changes | 64 |

  ⚠ The conjunctions and stations are **selected** on a one-day lattice of the pinned short-span kernel, read
  with CSPICE. Nothing that search computes is written anywhere: it chooses where to ask, and every value
  recorded is the service's. ⚠ The selected days were not checked against any published table here; the rule,
  not the dates, is what this note states. ⛔ Two goldens are not sampled: an LMT-era chart of 1885 and a
  published station, which are to be sampled only where an instant is fixed, and no instant is fixed for either.
  ⚠ The emitted header's wording of clause (4) of the rule predates this sentence and reads as though it covered
  every golden named with a year; read it with the list of instants it names.
* Every instant is asked of every body under every correction: 10 × 3 × 507 = 15 210 rows.

---

## 2. What every response was held to, and what the service said

Every response was held, before the next request was sent, to:

* the interface `NASA/JPL Horizons API`, at a version it is allowed to name (below), and the same version for
  the whole run;
* `DE441` named for the target and for the centre;
* the body and the centre echoed (`Center-site name: BODY CENTER`);
* the columns `JDTDB, Calendar Date (TDB), X, Y, Z, VX, VY, VZ, LT, RG, RR`;
* `Reference frame : ICRF`, `Output units : AU-D`,
  `Output format : 3 (position, velocity, LT, range, range-rate)`, and `1 au= 149597870.700 km, 1 day= 86400.0 s`;
* the sentence *"Barycentric Dynamical Time ("TDB" or T_eph) output was requested."*;
* one line per instant asked, each instant echoed and equal to the one asked, bit for bit;
* the response's own output type and its own paragraph under ABERRATIONS AND CORRECTIONS, character for
  character.

The service's own statements, read on six responses on 2026-11-21 before they were pinned, and the interface
document's words for the same correction:

| `VEC_CORR` | the document | the response's output type | the response's paragraph |
|---|---|---|---|
| `NONE` | *"geometric states"* | `GEOMETRIC cartesian states` | *"Geometric state vectors have NO corrections or aberrations applied."* |
| `LT` | *"astrometric light-time corrected states"* | `LT CORRECTED cartesian states` | *"States have been corrected for Newtonian down-leg (receive) light-time displacement."* |
| `LT+S` | *"astrometric states corrected for stellar aberration"* | `LT+S CORRECTED cartesian states` | *"States have been corrected for Newtonian down-leg  (receive) light-time displacement and relativistic stellar aberration."* |

⭐ The two agree, on every response: neither names a deflection of light for any vector correction. The manual
names that deflection among what makes coordinates *"apparent"*: *"light-time, the deflection of light due to
large or nearby masses, and stellar aberration"*. ⛔ Recorded, not interpreted: this note does not say how the
service applies any of them.

**Every one of the 210 responses held.** One interface version (`1.2`), one solution (`DE441`) for every body
and for the centre, and one Earth-orientation file named throughout (`eop.261120.p270216`, coverage
`DATA-BASED 1962-JAN-20 TO 2026-NOV-20. PREDICTS-> 2027-FEB-15`). No printed state under `NONE` equals its
state under `LT` at any of the 5 070 instant-body pairs, and none under `LT` equals its state under `LT+S`.
Every value is printed with fifteen decimals of mantissa.

---

## 3. What was measured about the service itself

* ⛔ **A long time list is not answered whole, and the service does not say so.** For this vector query a list
  of 200 instants was answered `HTTP 502 Bad Gateway`, three times; the back-off waited 30 s and then 120 s and
  the run stopped with nothing written. A list of 100 instants was answered `HTTP 200` with its **first 80
  instants only**; its own `Stop time` was the 80th, and nothing else in the response marked the omission. The
  line-count check refused it. The interface's document allows *"up to 10,000 discrete output times, though URL
  length limits may impose smaller limits"*; the longest address sent was 2 818 characters. ⭐ The requests are
  now cut at 75 instants, the size R1's of-date probe's lists were answered whole at on two days; 75 was
  answered whole 210 times here. ⚠ Where between 75 and 100 the cut lies was not measured.
* ⚠ **The interface names 1.2; its document names 1.3.** The document's heading reads *"Version: 1.3 (2025
  June)"*, and every response here, as on 2026-08-04, 2026-11-09 and 2026-11-12, named `1.2`. The generator
  accepts either and refuses a third, or two in one run.
* ⭐ **A geocentric vector response names an Earth-orientation file.** It is recorded on every row as service
  state, as R1's of-date probe records it, and excluded from the digest.

---

## 4. Two emissions

* **Live**, 2026-11-21 22:36–22:44 UTC: 210 requests, two seconds apart, no back-off needed. Values file
  sha256 `75f6427b…f752`, 15 210 rows, 16 567 127 bytes. Acquisition record `d90e39be…3c17`.
* **From the copies kept**, through the generator's cache-read path: each kept response's address, its kept
  resource and its recorded digest checked before it was read; no request sent. Values file **byte-identical**,
  `75f6427b…f752`. Acquisition record `30bc476d…625d`, which differs from the live one in four leaves and no
  others: the header's `retrieval_kind` and its meaning, the summary's `retrieval_kind`, and each row's
  `retrieval_kind` — `live_request` against `cache_read`.

The cache is keyed on the target, the centre, the correction and the instant set as chunked, in its own
subdirectory, so no earlier response — R1's barycentric ones above all — can stand in for one of these.

---

## 5. What this grid does not establish

* ⛔ **No band and no judgment.** Every section is `reference_only`. A consumer applies its own band, in its own
  tree, as a reviewed change.
* ⛔ **No deflection of light.** By the service's own statement, `LT+S` is light-time and stellar aberration;
  a comparison against a stage that also applies a deflection has to remove it first, or compare elsewhere.
* ⛔ **No solution but DE441.** A comparison against any other planetary solution carries the difference between
  the two solutions, which this grid does not measure. That characterisation is owed separately.
* ⚠ **TDB, asked explicitly.** Every instant was sent and echoed in TDB. Nothing here is converted from or to
  any other time scale.
* ⛔ **Nothing of date.** The frame is the ICRF throughout. No precession, nutation, obliquity, sidereal time or
  frame of date is sampled, and nothing here bears on one.
* ⛔ **No derived value.** No row is related to another, no correction is differenced against another, and the
  values the conjunction and station search computed are not recorded.

---

## 6. The drift control

`generators/r1_geocentric_drift.py` re-asks a stated sample of the grid's own recorded queries — by default the
first chunk of every body under every correction, 30 requests — rebuilt from the values file's `request` block,
and compares the interface and solutions named (these classify), the Earth-orientation file named (listed, not
classifying), the resource digest, every printed value and the response's own statement of its corrections. It
detects and proposes; it exits 0 on every outcome.

**First run, 2026-11-21 22:53–22:54 UTC, from `85bdf33`: 30 of 30 `no_drift`**, 2 250 instants compared, no
digest moved, the Earth-orientation file unchanged. Report sha256 `09185851…3515`. ⚠ It is not scheduled. A
schedule needs a decision this repository does not make.

---

## 7. The client, and the terms it was sent under

* **Client**: `saakshi/0.1 (+https://github.com/insculptor/Saakshi)` — product, version and this repository's
  public address — on every request, and written into every acquisition record. ⛔ No email address and no
  person's name.
* **Requests sent this session**: 251 in all. Six to read the three corrections' statements, three that met the
  `502`, two diagnostics, 210 for the grid, 30 for the drift control's first run. Never two at once.
* **The publisher's stated terms, quoted** (read 2026-11-21; ⛔ no legal conclusion is drawn here):
  * *"You agree to submit only one API request at a time (no simultaneous requests)."*
  * *"Applications making automated connections must provide a valid, application-specific User-Agent request
    header that includes correct product name, version, and contact information."*
  * *"No permissions are needed. The data provided on this site are considered public domain. However, use of
    information from this site does not imply NASA/Caltech/JPL endorsement."*

The pages read, by sha256 on 2026-11-21: the manual `be45b013…2a81`, the API document `6ca45d9c…cfe4` and the
Fair Use Policy `a91502a7…896d` (each byte-identical to its copy of 2026-11-09), and the FAQ `2480fefc…da66`
(its bytes moved since 2026-11-09).
