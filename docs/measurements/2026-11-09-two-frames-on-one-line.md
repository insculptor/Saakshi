# Two frames on one line · 2026-11-09

> ⭐ **One apparent direction, printed twice on the same line of the same response.** The publisher's ephemeris
> service was asked, from the geocentre, for observer quantities 2 and 31 together: apparent right ascension and
> declination in its true-equator and equinox-of-date coordinates, and ecliptic-of-date longitude and latitude.
> It was asked for five bodies, at ten instants inside a data profile's interval and at sixty-five more around one
> day, under every angle format and precision its interface offers, and once with every format parameter at its
> default. Sixteen requests, one at a time, answered by the interface version and the solutions this
> instrument's R1 sampler recorded. Emitted twice, and the two files were **byte-identical**.
> ⛔ This repository holds the generator and this note. **The readings are held outside it**: the terms under
> which the service's responses may be redistributed are quoted below, and have not been examined here.

---

## 0. What this session wrote

| commit | what | CI |
|---|---|---|
| `bdacc67` | `retrieve()` takes `user_agent`; its default is the name every generator already sent | `ci` green, run 42693809135 |
| `31b60f5` | `generators/r1_of_date_probe.py` and 62 tests | `ci` green, run 42693959626 |
| `ca27355` | every time list sent in time order (section 4) | `ci` green, run 42694859151 |

The probe was run twice from `ca27355` on one UTC day. It wrote one `provenance_record` under R1 each time,
with 16 request rows and 476 reading rows. The two files have the same sha256, `d505526d…3e54`. A field-by-field
comparison found no difference in any of 419 header leaves or 15 777 row leaves. The sixteen cached resources
were identical too.

The host is macOS arm64, CPython 3.12.11. The interval is read from the `standard@1` data profile manifest
(`b68407a3…73ee`) by the obliquity records' own reader, by import.

---

## 1. What was asked

* **The request and the service state are R1's, by import.** The following are `service.py`'s and
  `acquisition.py`'s, which `r1_horizons.py` reads through:
  * the address and the query encoding;
  * the retrieval, with its canonical form;
  * the generation stamp, cut out of the digest;
  * the rules for the interface, the target's and the centre's solution, and the Earth-orientation file and
    coverage.

  Over a vector response, the probe's split is `service.parse`'s, character for character, and a test holds it so.
* **The vector table** is `r1_horizons.py`'s own query, by import, with two parameters replaced: the geocentre,
  and `REF_PLANE='BODY'`, the only plane of date the interface offers a vector table. It is read by R1's own
  reader.
* **The observer tables.** These ask for quantities 2 and 31 together, in comma-separated form, with the time
  given and printed as a terrestrial-time Julian day. They come in four variants:
  * `ANG_FORMAT` `HMS` or `DEG`;
  * `EXTRA_PREC` `NO` or `YES`;

  and one more request with every format parameter left at the interface's default. Every parameter sent is
  recorded, sorted, on its request row.
* **The bodies**: the Sun, the Moon, Mars, and the Jupiter and Pluto system barycentres.
* **The instants**: ten named ones, and sixty-five at one-sixteenth of a day around 1962-01-20.
  * The named ones run from a day after the interval's start to a day before its end. They include J2000 at
    noon, instants before 1962, instants in recent years, and instants after the present.
  * The first and last are a day inside the ends. The manifest declares its coverage in one time scale and
    these instants are asked in another.
* **The client**: `saakshi/0.1 (+https://github.com/insculptor/Saakshi)`, one request at a time, two seconds
  apart. ⛔ No email address and no person's name.

---

## 2. What every row carries, and what is refused

* Every row carries the interface source and version, the target's and the centre's solution, and the
  Earth-orientation file and coverage. A row without them is not written.
* ⛔ **A stop, before anything is written**: an interface version or a solution other than the ones R1's
  acquisition record of 2026-08-04 (`6fc673e`) names. None occurred.
* ⛔ **Refused**, each tested beside a twin that is accepted:
  * a response without its generation stamp, its signature or a solution;
  * a solution named twice;
  * a table whose labels, line count, field count, value shapes or echoed instants are not as asked;
  * an observer response without its Earth-orientation lines;
  * an output or cache path inside this working tree;
  * a record that already exists.
* Each check was planted out of the source one at a time, the tests run, and the source restored and compared
  byte for byte: **46 of 46** were caught.
  * Three were applied again by hand, to confirm each was caught by the test written for it.
  * The first sweep showed two escapes, which were real test gaps and are now closed.
  * ⚠ It also showed that a planted run could write into this tree, because one test pointed there. The tests
    now point the probe at a stand-in tree, and the sweep refuses a baseline that does not pass and compares
    the tree, ignored paths included, before and after.
* Suite 862 → **928**. The run with no ephemeris library went 528 / 138 → **593 passed, 139 skipped**; the one
  new skip needs the SPICE binding that R1's sampler imports.

---

## 3. What the documents state

The service's published pages, retrieved 2026-11-09. The manual and the API document are byte-identical to copies
retrieved on 2026-11-03.

| document | address | sha256 |
|---|---|---|
| the manual | `https://ssd.jpl.nasa.gov/horizons/manual.html` | `be45b013…2a81` |
| the API document | `https://ssd-api.jpl.nasa.gov/doc/horizons.html` | `6ca45d9c…cfe4` |
| the API landing page | `https://ssd-api.jpl.nasa.gov/` | `a91502a7…896d` |
| the FAQ | `https://ssd.jpl.nasa.gov/faq.html` | `d48ba84a…bfef` |

* **Quantity 2**, for Earth-based sites: *"Apparent coordinates are with respect to the true-equator and Earth
  equinox of-date coordinate system (EOP-corrected IAU76/80 precession and nutation of the spin-pole) and
  adjusted to model light-time, the gravitational deflection of light, and stellar aberration, with an optional
  (approximate) correction for atmospheric yellow-light refraction."*
* **Quantity 31**: *"Observer-centered IAU76/80 ecliptic-of-date longitude and latitude of the target centers'
  apparent position with light-time, gravitational deflection of light, stellar aberration, and optional
  atmospheric refraction correction."*
* **The ecliptic of date**: *"Used for some observer table quantities, this dynamic frame uses the IAU76/80
  time-varying Earth obliquity model to construct the ecliptic x-y plane of-date over modern eras and the
  long-term IAU76/80-compatible model of Owen, a long-term integration of Kinoshita’s polar equations of motion,
  for times more than 200 years from the year 2000."*
* **The vector and element tables** offer three reference planes: *"frame ("equatorial" ICRF)"*, *"ecliptic"*,
  and *"body (central body equator and node of date)"*. The ecliptic is the standard epoch's.
* **The Earth-orientation data**: *"The EOP file provides data from 1962 to the present, with predictions about
  78 days into the future from the date of file release. For future times outside the available EOP data-fit or
  prediction intervals, Horizons uses the last predicted values available in the EOP file as constants."*
* **The interface's version.** The API document heads itself *"Version: 1.3 (2025 June)"* and says *"If the
  version does not match the version in this document (at the top), there is no guarantee that the format has
  not changed."* ⚠ Every response named the version R1 recorded in August, which the document's own change log
  dates to 2022. Recorded, ⛔ not reconciled.

### The publisher's stated terms — ⛔ quoted, never interpreted

* The API landing page, under *"SSD API Service - Fair Use Policy"*:
  * *"You agree to submit only one API request at a time (no simultaneous requests)."*
  * *"Applications making automated connections must provide a valid, application-specific User-Agent request
    header that includes correct product name, version, and contact information."*
* The FAQ: *"No permissions are needed. The data provided on this site are considered public domain. However, use
  of information from this site does not imply NASA/Caltech/JPL endorsement."*
* ⚠ The two notice pages the manual's footer links to, on `www.jpl.nasa.gov`, answered 403 to this client. They
  were not read.

⛔ No legal conclusion is drawn from any of these.

---

## 4. Found while running it

* **The service answers a time list in time order, whatever order it is sent in.** The first live run sent the
  window after the named instants. The response put the window's lines before J2000's, and the probe refused it
  at its first line, before anything was written. Every list is now sent in time order. The tests' synthetic
  service answers the same way, and a test holds every list sorted.
* ⚠ **On this host the interpreter's TLS library did not trust the chain the service presents.**
  * The system's certificate file lacks the root the chain ends in. The system's own tools verified it; this
    interpreter's did not.
  * The runs set `SSL_CERT_FILE` to the certificate bundle installed with this repository's requirements.
    Verification stayed on. ⛔ No code changed for it.

---

## 5. What this does not establish

* ⛔ **Nothing is derived here.** Nothing in this repository relates the two frames, computes an angle between
  them, or says how the service computes either. The digits printed are counted; nothing is computed from them.
* ⛔ No band, no class, no unit for a comparison and no budget row, and no claim that any reading can gate
  anything. Whether the readings can serve as a comparand is their consumer's question.
* ⛔ Nothing about the sky. It records what one service printed, on one day, for sixteen queries.
* ⚠ Reproducible only while the recorded service state holds. The Earth-orientation file in force is service
  state, and it moves on the publisher's schedule.
* ⚠ Not read: any other observer quantity, centre, site or time scale; refraction; any element table; the
  notice pages that refused this client.
