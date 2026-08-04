# What an ephemeris library says about which ephemeris answered

**2026-08-04.** Taken while building `generators/r3_swiss.py`. Software: Swiss Ephemeris
2.10.03 through `pyswisseph` 2.10.3.2, with the publisher's `.se1` data files for the
1800–2399 block, pinned by SHA-256 and verified at read time.

⛔ **Recorder, never explainer.** Everything below is a return value observed under stated
conditions. Nothing here describes how any ephemeris is evaluated.

⚠ **Scope.** This is an observation of one release through one binding, on one machine, on
one date. It is not a claim about the software in general, and a later version may behave
differently — which is why every row of the fixture is dated and versioned.

---

## The starting rule, and why it was not enough

The rule this work began from was: *the library substitutes a different ephemeris when the
one requested is unavailable or does not cover the date, so assert the returned flag on
every call.*

Both halves of that are true. The substitution is real, silent, and returns an ordinary
value:

| requested | conditions | answered by |
|---|---|---|
| data files | no data-file path set | the analytical ephemeris |
| data files | path set, date inside the files' coverage | the data files |
| data files | path set, date outside their coverage | the analytical ephemeris |

No exception, no warning, no difference in the shape of the result.

⭐ **But "assert the returned flag" turns out to be necessary and not sufficient, for two
independent reasons.** Most entry points do not return one. And the flag has to be read per
call, because which ephemeris answers is not a function of the call's arguments.

---

## 1. Of four entry points, one reports the ephemeris that answered

| entry point | takes a flag | returns | reports the source? |
|---|---|---|---|
| `calc_ut` | yes | `(values, returned_flag)` | ✅ **yes** |
| `get_ayanamsa_ex_ut` | yes | `(returned_flag, value)` | ⛔ **no — it echoes** |
| `houses_ex` | yes | `(cusps, ascmc)` | ⛔ **no flag at all** |
| `rise_trans` | yes | `(return_code, times)` | ⛔ **no — that integer is a success code** |

⛔ **`get_ayanamsa_ex_ut` is the dangerous one, because it satisfies the rule.** With no
data-file path set at all — conditions under which `calc_ut` reports the analytical
ephemeris — it returned the data-file bit it had been handed. A caller that asserts *that*
flag gets a green light that carries no information.

⚠ **And the two that return nothing are the house cusps and the rise/set times** — which is
to say the ascendant and the sunrise, the two quantities a panchanga is built on. For those
there is no direct evidence of source available at all.

`rise_trans`'s integer is a success code, not a flag: it was `0` both where the requested
ephemeris answered and where it was substituted.

### The consequence: two kinds of assertion, and rows say which they used

* **`reported`** — the entry point said which ephemeris answered, and it was the one asked
  for.
* **`proxy_window`** — it said nothing, so the source was established at **both ends** of
  the interval the call may read, using an entry point that does report.

⚠ **The proxy is bounded, not sound, and the bound was measured rather than assumed.**
Sampled across a coverage edge, the two ends disagreed for every start instant in the half
day before the edge, while `rise_trans` went on returning a source-dependent answer — the
search had started outside coverage and found its event inside. So neither end alone
described what the call had done, and requiring both is what excludes that region.

⭐ In the fixture: **386 of 907** attributed rows in the data-file file are `reported`; the
other **521** are `proxy_window`, and each says so.

---

## 2. ⛔ Which ephemeris answers depends on the preceding call

This was not expected and it changes the design.

The boundary search returned a "last outside" instant that answered as *inside*, which
should have been impossible. It was not a bug in the search. Probed without resetting the
library's state, the predicate is not a function of the instant at all.

**One instant, one body, one set of flags, one process:**

| reading | answered by |
|---|---|
| fresh session | the data files |
| after one unrelated call 48 days outside coverage | ⛔ the analytical ephemeris |
| after one call well inside coverage | the data files again |

Nothing about the instant changed between those three readings.

**Sweeping the same 22 days in each direction:**

| sweep | first instant seen as substituted |
|---|---|
| ascending, warm | JD 2597651.353 |
| descending, warm | JD 2597642.353 |
| **cold — state reset before every probe** | JD 2597651.353 |

⚠ **Nine days of disagreement**, produced by nothing but the order the instants were visited
in. The cold sweep is reproducible: two identical sweeps agreed exactly.

### ⭐ The sharpest form: the comparison destroyed one of its own operands

At the measured upper edge, `2400-01-10T20:28:30Z`, comparing the two ephemerides the way
anyone would write it — call one, call the other, subtract:

```
  data-file request alone                ->  answered by the data files
  the same request after a Moshier call  ->  answered by the analytical ephemeris

  naive comparison  (one session, two calls)     ->  0.000000000 arcsec
  isolated comparison (each call from a reset)   ->  1.267041701 arcsec
```

⛔ **The first call of the pair changed which ephemeris answered the second, so the
comparison reported perfect agreement between an ephemeris and itself.** The zero is not a
result. It is the measurement not having happened, in a form indistinguishable from success.

⚠ The effect is not confined to the boundary. At **3 of the 12 in-coverage epochs** the naive
and isolated comparisons disagreed about the *size* of the difference — e.g. 0.685″ against
0.571″ — with the flag honoured on both sides in both cases. So the ordering perturbs the
value as well as the choice of ephemeris, and the flag alone does not detect that.

### What that forced

* **The library's state is reset before every recorded call group**, so a row is a function
  of its own request rather than of where the generator had reached. Cost: ~0.08 ms per
  group, which buys an artifact that does not depend on loop order.
* Within a group the calls share one session on purpose — a proxy must observe the same
  state as the call it stands for.
* **The boundary search probes cold and re-verifies all four endpoints** instead of trusting
  the interval it just derived.
* ⚠ **Closing the library also drops the sidereal mode, silently.** An ayanamsha read after
  a reset that restored only the data path was **0.88°** away — a plausible-looking number in
  the same range as the right one. So the session object holds both and re-applies both: a
  reset that restores part of the state is worse than none, because the part it drops is
  invisible.

---

## 3. The library is loud at the boundary and silent far past it

| distance outside coverage | `rise_trans`, Moon, data files requested |
|---|---|
| half a day | ⛔ **raises** — "data file not found" |
| a century | returns quietly, substituted |
| three centuries | returns quietly, substituted |

⭐ **So probing "does it error outside coverage?" with a date near the edge concludes it is
safe, and that conclusion is wrong for every date further out.** The noisy region is the
narrow one; the silent region is unbounded. Both paths are recorded and neither is fatal to
a run.

## 4. Two more things a caller can get wrong invisibly

* ⛔ **Where no rising occurs — above the polar circle — the return code is `-2` and the
  time slot is `0.0`, not a sentinel.** A caller that reads the value without reading the
  code gets a Julian day in 4713 BC that looks like any other float.
* ⭐ **"Outside coverage" and "unattributable" are not the same set.** One body needs no data
  file and reports the requested source at *every* epoch, including those where all eleven
  others report a substitution. In the fixture, the `outside_coverage` stratum has 8 written
  rows against 238 substitutions, and all 8 are that one body.

---

## 5. What the two ephemerides actually differ by, once the comparison is honest

Over the 907 rows attributable on both sides. ⛔ **Not a tolerance and not an error bound** —
it is the difference between two sources, neither of which is an authority over the other.

| section | identical | compared | worst difference |
|---|---|---|---|
| `longitude_tropical` | 14 | 193 | **0.00778°  = 28.0″** (true node) |
| `longitude_sidereal` | 14 | 193 | 0.00778° = 28.0″ (true node) |
| `rise_set` | 3 | 236 | 2.94e-5 d = **2.54 s** (Moon, polar site) |
| `house_cusps` | 119 | 135 | 9.45e-10° |
| `house_angles` | 99 | 135 | 9.45e-10° |
| `ayanamsha` | 11 | 15 | 4.20e-10° |

⭐ **The true node dominates**, by more than an order of magnitude over any other body — the
worst row in both longitude sections is the same body.

⚠ **The worst rise/set row is at a polar site**, not a temperate one: near the polar circle
the body approaches the horizon at a shallow angle, so a small difference in position
becomes a large difference in *time*. A rise/set budget stated as a single number across
latitudes would be set by its worst latitude and be far too loose everywhere else.

⭐ **House cusps barely move at all** — 9.45e-10° — while positions move 28″. The flag is
accepted by `houses_ex` and, in coverage, the two sources produced identical cusps at 119 of
135 sampled points.

---

## What the fixtures record

| file | kind | rows |
|---|---|---|
| `out/swiss/moshier/r3-values.jsonl` | `numeric_pin` | 1 375 |
| `out/swiss/swiss_file/r3-values.jsonl` | `numeric_pin` | 907 |
| `out/swiss/r3-flag-reporting.jsonl` | `provenance_record` | 29 |

All sections are `reference_only` — committed, not yet compared. These are values one
implementation returned under stated flags; ⛔ no band exists to declare, and inventing one
is the failure the whole contract exists to prevent.

⭐ **460 calls in the data-file run were answered by an ephemeris nobody asked for, and none
of their values was written.** They are listed in the header as substitutions. That exclusion
is the mechanism: it is what stops an uncovered epoch from contributing a zero that would
read as agreement.

Regenerated twice: **byte-for-byte identical**.
