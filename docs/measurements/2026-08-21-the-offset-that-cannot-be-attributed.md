# The offset that cannot be attributed · 2026-08-21

> ⭐⭐⭐ **THE R3 ENTRY-POINT SURVEY SURVEYED FOUR FUNCTIONS AND THE TWO THAT RETURN THE TIME
> OFFSET WERE NOT AMONG THEM.** They are now, and the finding is a **refusal**: `deltat_ex`
> and `deltat` consult an ephemeris — measurably, their answers move with one — and return a
> bare float. No flag, no return code, no error channel. The one channel carrying anything
> about the basis is the tidal-acceleration constant in force, and it is **not an
> identifier**: the library's own names give **one number to two different sources**, and the
> number an actual pinned data file puts in force is the named constant of **no source at
> all**. ⇒ No `ephemeris_basis` is written for either. **The impossibility is published as
> the finding**, and the proxy is recorded as a bound on a window rather than as a source.

---

## 0. Where this came from

A consumer's phase gate lists two checks in an order, and the order is the decision: a
survey of which entry points report the answering ephemeris stands textually **ahead** of
the check that pins the offset at fixed epochs. Measured here before anything was written:
`out/swiss/r3-flag-reporting.jsonl` surveyed **four** entry points — `calc_ut`,
`get_ayanamsa_ex_ut`, `houses_ex`, `rise_trans` — and the string `deltat` occurred in the
file **zero times**.

⚠ The other ground that gate has been waiting on was already discharged and is recorded so:
`out/conventions/time-offset.jsonl` carries `source_assertion` on all **22** `delta_t` rows,
as a `proxy_window` with both ends checked through a reporting call. What was missing was
the ordered prerequisite, not the assertion.

---

## 1. What the extension found

Six entry points now. Two were added and **four of the six return no usable source**: three
return no flag, one returns a flag that merely echoes the request, and one takes no
ephemeris argument in the first place.

| entry point | takes a flag | reports the answering ephemeris | returns | assertion available |
|---|---|---|---|---|
| `calc_ut` | ✅ | ✅ | `(values, returned_flag)` | `reported` |
| `get_ayanamsa_ex_ut` | ✅ | ⛔ echoes the request | `(returned_flag, value)` | `proxy_window` |
| `houses_ex` | ✅ | ⛔ | `(cusps, ascmc)` | `proxy_window` |
| `rise_trans` | ✅ | ⛔ a return code, not a flag | `(return_code, times)` | `proxy_window` |
| **`deltat_ex`** | ✅ | ⛔ | **a bare float** | `proxy_window` ⚠ *about a different quantity* |
| **`deltat`** | ⛔ **none** | ⛔ | **a bare float** | ⛔ **`none`** |

⛔ `none` is **not a tidier spelling of `proxy_window`**. A proxy asserts that a *request*
was honoured over the window a silent call may read. Where no ephemeris argument is taken
there is no request to honour, and the honest field is a refusal rather than a weaker claim.

---

## 2. ⛔ The flag is taken as a declaration, not as a request that can fail

One session, one instant, one flag — read through two entry points.

| what was asked | `calc_ut` reports | `deltat_ex` computed on | the library's name for that number |
|---|---|---|---|
| the JPL flag, **no JPL file on the machine** | **the data files** answered (substituted) | **−25.8** | `TIDAL_JPLEPH` — *and* `TIDAL_SWIEPH`, `TIDAL_DE431`, `TIDAL_DEFAULT` |

The reporting call says the request failed and names what answered instead. The offset call,
handed the same flag in the same state, computes on the JPL constant and returns a number.

And the mirror case, with the data files removed:

| what was asked | `calc_ut` reports | `deltat_ex` computed on |
|---|---|---|
| the data-file flag, **no data files** | **the analytical ephemeris** answered | **−25.8**, which is **not** the analytical ephemeris's −25.58 |

⇒ ⭐⭐⭐ **Under one unchanged flag, in one session, at one instant, the offset and the
position did not rest on the same ephemeris.** So a proxy taken from a reporting *position*
call bounds the window and establishes **nothing** about what the offset was computed from.
That is why the caveat on `deltat_ex`'s `proxy_window` says the proxy is about a different
quantity, and why the row's `ephemeris_basis` is a refusal.

---

## 3. ⛔ The constant is the only channel, and it is not an identifier

The library's own `TIDAL_*` table, read out of the library rather than typed here:

| number in force | the library's names for it | which of the three sources it could name |
|---|---|---|
| **−25.58** | `TIDAL_DE403`, `TIDAL_DE404`, `TIDAL_MOSEPH` | **one** — the analytical ephemeris |
| **−25.8** | `TIDAL_DE431`, `TIDAL_DEFAULT`, `TIDAL_JPLEPH`, `TIDAL_SWIEPH` | ⛔ **two** |
| **−25.936** | `TIDAL_DE441` | ⛔ **none** |

⭐ The third row is the sharpest. **−25.936 is what the pinned data files themselves put in
force**, and it is the named constant of no source in the library's vocabulary — the name
`TIDAL_SWIEPH` holds a different number. So the map from constant to source is neither
injective nor the one the flags suggest, in both directions at once.

⚠ **The instrument can answer as well as refuse**, and that is checked in the same run
rather than argued: over twelve flag-and-regime combinations it names exactly one source in
**four** of them and disagrees with the reporting call in **eight**. An instrument that only
ever returned the empty list would produce a file that looked identical and would be
measuring nothing.

---

## 4. ⛔ And the entry point that takes no ephemeris argument has an ephemeris anyway

`deltat` accepts a Julian day and nothing else. At 1900-01-01 it returned **two different
numbers** for that one instant:

| state | value | equals the flagged answer for | constant in force |
|---|---|---|---|
| the pinned data files present | `bef7b4c59a971c0d` | `swiss_file` | −25.936 |
| no data file anywhere | `bef82916b78c0694` | `jpl_file`, `swiss_file` | −25.8 |

**0.0374 s apart, with nothing changed but a directory path handed to an unrelated call.**
⭐ A caller who never passed a flag has still chosen one, and the fixture records which.

⚠ **A documented refusal that does not happen.** The binding states that calling `deltat_ex`
before any path has been set *will raise*. Measured: it returns a value, computed on the
default constant. A recorder relying on that documented refusal to notice that no ephemeris
was established gets a plausible number instead.

---

## 5. The controls, which sit inside the measurement

⭐⭐⭐ **A silence and a deaf reader are the same observation from outside, and only one of
them is a finding.** So one blind reader — which knows nothing about which entry point
produced what it is handed — is run over four returns in the same run:

| return | what the reader found |
|---|---|
| `calc_ut`'s | an integer masking to a named source ⇒ **a report exists and the reader sees it** |
| `rise_trans`'s | an integer that masks to **no** named source ⇒ the reader is not fooled by a return code |
| `deltat_ex`'s | **no integer at all** |
| `deltat`'s | **no integer at all** |

⛔ **The grid is a control too, in both directions.** At a tabulated instant all three flags
return one number, so a survey confined to such epochs would report *no dependence* and
would look exactly like one that had looked and found none. The survey therefore **refuses**
a grid on which the flag changes nothing — *"a verdict read off these rows would be a
statement about the grid and not about the entry point"* — and **refuses** one on which it
always does, because an instrument never observed saying *no* has not been shown able to.

⚠ The second regime is a state this repository otherwise **refuses to record in**: a
directory with no data file, which `verify_ephe_set` rejects precisely because every
data-file request would then be answered analytically without a word. It is constructed
deliberately, held in a temporary directory, never named in the fixture — and the library is
put back afterwards on two channels, with the restoration **measured** rather than assumed.

---

## 6. ⛔⛔ The base row was part of the test, and choosing it badly tested one branch six times

The declaration guard has six branches. Its test parametrised six cases over one base row —
`deltat`, which takes no ephemeris flag. That makes the flagless branch a **catch-all**: it
fires for every wrong value whatever else is disarmed.

⇒ **Three of the six cases went on passing with their own branch deleted**, and the suite
could not see it because each case asserted only that *some* refusal came back.

> ⭐⭐⭐ **A GUARD TEST THAT ACCEPTS ANY REFUSAL IS SATISFIED BY A DIFFERENT GUARD THAN THE ONE
> IT WAS WRITTEN FOR, AND REPORTS FULL COVERAGE WHILE A BRANCH SITS DEAD.**

Each case now names the row that **isolates** its branch and the words of the refusal it is
owed; a further test asserts no two cases are owed the same words, so none can stand in for
another. ⚠ Found by the disarming sweep, not by the suite.

### The fourth escape, and the ordering defect it uncovered

The remaining escape was the generator's own sequencing, which the suite does not run.
Pulling on it found a real defect: the *before* reading of the library's state was taken
from whatever state the run happened to be in, while the *after* reading was taken from a
reset — so the two were not comparable and the check worked by luck. Both now go through one
helper.

Two disarms of that helper were then **measured at generator runtime** rather than argued
about:

| disarm | suite | generator |
|---|---|---|
| delete the reset the readings depend on | ⛔ escapes | ✅ **caught** — the refusal fires, naming the constant |
| copy the *after* reading from the *before* one | ⛔ escapes | ⛔ **escapes** — the check becomes tautological |

The second is caught **nowhere**: the suite has no ephemeris data files and so cannot make
two states differ, and the generator's refusal fires only on a real divergence. ⇒ It is
closed with a seam the suite drives **both ways** — a run whose state comes back is let
through, one whose state does not is refused. ⚠ The first is left as a recorded escape,
bounded by the runtime measurement above.

**19 of 20 disarms caught**, green baseline checked first, `sys.executable`,
`PYTHONDONTWRITEBYTECODE=1`, every patch verified to have changed the file before the suite
ran and the file verified restored after.

---

## 7. The artifact

`out/swiss/r3-flag-reporting.jsonl`, **29 → 49** rows, byte-identical on re-run. Accounted at
key level:

**25 byte-identical · 4 changed · 20 added · 0 removed**

* **25 identical** — one coverage edge, four state-dependence rows, twenty substitution
  demonstrations. Untouched.
* **4 changed** — the four entry-point rows that were already there, each gaining
  `quantity_returned` and `assertion_caveat`.
* **20 added** — two entry-point rows (`deltat_ex`, `deltat`) and eighteen
  `offset_attribution` rows: one harness control, twelve per-flag readings over two regimes
  and two epochs, four unflagged readings, one verdict.

⭐ **The two value fixtures are the control on the restoration.** `out/swiss/moshier/` and
`out/swiss/swiss_file/` were regenerated in the same run: **1 375 and 907 rows, every one
byte-identical**, with exactly two header fields moved (`generated`, `generator.commit`).
A survey that had left the library pointed elsewhere would have moved them.

⚠ `assertion_available` is now **declared per entry point rather than derived**. The
derivation — *reported if it reports, proxy_window otherwise* — had no exceptions and
therefore no way to be wrong out loud; run over the current table it hands `deltat` a proxy
over a request nobody made, and a test pins it doing exactly that.

---

## 8. ⬜ What this does not establish

1. ⛔ **One release, one binding.** Every row here is dated and versioned for that reason.
   A later version may report differently, and this file is not a claim about the software
   in general.
2. ⛔ **The refusal is not a defect report.** That the library uses a data file's own
   inherent constant is reasonable; what is measured is that a *recorder* cannot recover
   which ephemeris a returned offset rests on, from anything the library hands back.
3. ⚠ **Two epochs and two regimes.** The grid carries the property under test and a case
   without it, which is what makes the verdict readable — it is not a survey of where the
   flag dependence begins and ends.
4. ⚠ **No JPL file was present.** So the JPL branch was measured only in the state where it
   cannot be honoured, and what an honoured JPL request would put in force is unmeasured.
5. ⬜ **One disarm escapes the suite** — deleting the reset the state readings depend on. It
   is caught at generator runtime, measured, and recorded rather than argued away.
