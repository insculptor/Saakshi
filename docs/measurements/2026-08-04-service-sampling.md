# A service is not a file — what a response is made of, and what may be written down

> Date: **2026-08-04** · Generators: `r1_horizons.py`, `r1_drift.py`
> Host: one workstation, `x86_64` Windows, CPython 3.12.11
> ⚠ **One host, one platform, one day.** Everything below is a measurement taken here.

Every other fixture set in this repository is sampled from something that holds still: a
kernel pinned by digest, a published test file, a library at a pinned version. This one is
sampled from a **live service**, and that difference turned out to be the whole design
problem rather than a detail of it.

---

## 1. ⛔ The refusal that had to be answered first

`acquisition.py` has always refused a retrieval that disagrees with a retained copy:

> *One address has served two different artifacts; which one a fixture should pin is not
> this recorder's decision.*

That refusal is correct for a published file and it is **unusable against a service** — not
awkward, unusable. Pointed at one unchanged it fires on the **second** request, every time,
and reports that the service contradicted itself when nothing about the answer moved at all.

The wrong fix is to weaken the refusal for service callers. The right one is to say what the
**resource** is, so that the digest, the cache and the refusal all run over the answer rather
than over the transaction that delivered it. So `retrieve()` grew one parameter, a canonical
form, and `Retrieval` grew a companion field:

```python
resource_sha256          # over the answer
sha256                   # over the bytes received
payload_is_the_resource  # ⭐ their equality, recorded as a fact rather than assumed
```

⭐ For every published file this repository reads, the two digests are equal and nothing
changes. `payload_is_the_resource` being **true** is the statement *this acquisition needed
no split* — worth a field, because the two cases differ in what may be written down at all.

---

## 2. ⭐ A response has three parts, not two

The obvious split is *request* against *resource*: keep what a reader could ask again,
discard what moved. Measured against this service, that split is wrong, because a response
has three parts:

| Part | Moves on | Recorded? | In the digest? |
|---|---|---|---|
| **the request** | never | ✅ verbatim | ✅ (echoed by the service) |
| **the transaction envelope** | every request | ⛔ **never** | ⛔ no |
| ⭐ **the service's own state** | the *service's* schedule | ✅ **as data** | ⛔ no |
| **the resource** | when the answer changes | ✅ | ✅ |

**Measured**: two identical requests three seconds apart differ in exactly **one line** — a
generation stamp. Nothing else in a response of ~7 KB moves. That is the envelope, and it is
the response `Date` header's problem arriving *inside the body*, where no header allow-list
reaches it.

⛔ **The third part is the one a two-way split gets wrong in both directions at once.** Which
solution answered, which auxiliary files were loaded, which interface version replied — this
moves on the service's schedule, not the caller's.

* Discard it as volatile, and the file no longer says **what answered it**.
* Digest it as resource, and the artifact stops regenerating the day the service updates a
  file nobody here controls.

⭐ **So service state is recorded as data and excluded from the digest, and the
reproducibility claim becomes conditional and says its condition out loud:** *these bytes
regenerate for as long as the recorded service state holds.* That is the same shape of claim
the acquisition record already makes about a machine — reproducible here, not everywhere —
and it is honest for the same reason: the condition is **written into the file**, so a reader
can check it instead of discovering it.

⛔ A conditional guarantee with nothing watching the condition is a guarantee nobody checks.
That is the drift job, and it is why the two arrived together.

### ⚠ Even the byte count is not a property of the answer

The acquisition record for a published file carries the payload's size and digest. This one
carries neither, and the omission is the record. The generation stamp is a
human-formatted date — `Tue Aug  4` against `Wed Aug 12` — so the **width** of the response
moves with the day of the month. A recorded `size_bytes` would have failed its own
reproducibility check on the second Tuesday of a month, for a reason nobody would ever guess
from the field name.

### ⚠ The split is asserted every run, never assumed

Every region the recorder classifies must be **present**. A classified field that has gone
missing means the format moved and the classification is stale, so the run is refused rather
than quietly digesting a volatile region as a stable one. Eight refusals are exercised in
`tests/test_service.py`, all without a network.

---

## 3. ⭐ The finding: the service does not answer from one ephemeris

Twelve bodies, twenty-one epochs a decade apart from 1900 to 2100, geometric states
relative to the solar-system barycentre.

Eleven of the twelve were answered from the **planetary solution**. One was not:

| Request | differs by | Solution the service named |
|---|---|---|
| `COMMAND='4'` — Mars system barycentre | — | `DE441` |
| `COMMAND='499'` — Mars | the body number, and nothing else | ⭐ **`mar099`** |

Same instant, same frame, same centre, same units, same request in every other respect.
⛔ **Nothing in the numbers says so.** The only thing that says so is the identifier the
service prints beside the body name — which is why this recorder classifies it as service
state, writes it on **every row**, and refuses a response that omits it.

⭐ This is the same failure this repository already met on the library side — a source
substituted silently, successfully, returning an entirely ordinary value — arriving from a
completely different direction. A recorder that writes down what came back without
establishing what answered produces a file that is well-formed and mislabelled.

⚠ It lands from the file's side too: the pinned kernel **does not carry body 499 at all**, so
those 42 rows have no cross-reference and say so. That is not a gap in the evidence. It is
the finding, stated by the other party.

---

## 4. ⛔ Why this fixture declares no band, and why that is a refusal rather than an omission

The rows are `reference_only`. The contract warns that this is *"not a resting place"* — that
leaving it there once a band **has** been measured turns "not yet compared" into "never
compared". So the warning is met head on: a per-row disagreement against the pinned kernel
**is** measured, on every row the file can answer, and it is still not offered as a band.

Three measurements say why, all computed on the run rather than argued for.

**The disagreement is concentrated, not distributed.** Worst disagreement per body, position:

| Body | worst | | Body | worst |
|---|---|---|---|---|
| Moon | **5.40 × 10⁻¹¹ au** | | Saturn bary. | 1.78 × 10⁻¹⁵ au |
| Earth | 6.64 × 10⁻¹³ au | | Jupiter bary. | 8.88 × 10⁻¹⁶ au |
| Uranus bary. | 7.11 × 10⁻¹⁵ au | | Mars bary. | 6.66 × 10⁻¹⁶ au |
| Neptune bary. | 7.11 × 10⁻¹⁵ au | | Venus | 1.11 × 10⁻¹⁶ au |
| Pluto bary. | 7.11 × 10⁻¹⁵ au | | Mercury | 5.55 × 10⁻¹⁷ au |
| | | | Sun | 8.67 × 10⁻¹⁹ au |

**1.** ⭐ **Nine of the eleven bodies show no disagreement observable in the value the
service printed.** Held against the spacing between representable values at the disagreeing
component's own magnitude, nine bodies sit within *four* last places over the whole grid.
⛔ A band cut from a set of measurements most of which are the resolution of the printed
number would be measuring the number format.

**2.** **The spread is 6.2 × 10⁷ in position and 2.0 × 10⁸ in velocity.** One band would be
cut from the Moon and applied to the Sun — that many times looser than the Sun was ever
observed to be, and every one of its rows would pass without having been checked.

**3.** ⭐ **The two orderings disagree, so neither is *the* ordering.** The Sun has the
**smallest** absolute disagreement of the eleven and ranks **third largest** by last places,
because its velocity components are near zero and the spacing between representable values
there is minute. ⛔ Where the orderings conflict there is no single ordering to cut a band
from. This is the companion state fixture's denominator argument arriving through the
magnitude of a whole quantity rather than of one component.

⭐ And the underlying reason a band would be the wrong instrument at all: the companion
self-consistency file's band is a **floor** because both of its sides are the same ephemeris
read two ways, so what remains is reader noise. Here the two sides are **different named
solutions** — the service says so, per row. A band cut from that would declare the difference
between two ephemerides to be the tolerance of a reader.

### ⭐ The small numbers are what license reading the large one

A misaligned frame, or an epoch handed over in the wrong time scale, would displace **every**
body at once and most visibly the fast ones. Mercury's largest disagreement anywhere on this
grid is 5.6 × 10⁻¹⁷ au — about 8 nanometres. That agreement is the evidence that the grid,
the frame and the epochs line up, and it is what leaves the Earth–Moon residual as a
difference between solutions rather than a defect in the recorder.

⚠ The Moon's disagreement is also **not a constant offset**: it is smallest around 1970 and
grows in both directions, reaching 5.4 × 10⁻¹¹ au at 2100. A single number sampled at one
epoch would have described none of that.

---

## 5. The drift job — ⛔ detect and propose, never gate

It re-asks the questions the fixture recorded and reports what came back differently. ⚠ **It
exits 0 on every outcome it can reach**, deliberately:

* ⭐ A job that fails a build on drift is a job somebody switches off. It would fire the day
  a public service updated a data file — an event nobody here controls, at a time nobody here
  chose — and the fixture it fired about would still be perfectly good evidence of what the
  service said when it was asked.
* ⛔ Drift is not a defect. A service answering from a newer solution has not malfunctioned
  and the recorded rows have not become wrong. They have become a record of a *past* state,
  which is a thing to know and not a thing to fail.

⚠ Detect-**only** would be the opposite mistake: "something moved" leaves the reader to work
out which of several quite different things happened. So there are six outcomes, each with
the proposal that fits it, and ⛔ no proposal ever proposes adopting or widening a band —
which is asserted in the test suite rather than left to good intentions.

| Outcome | What it means |
|---|---|
| `no_drift` | every classified region answered as recorded |
| `values_moved` | a recorded value came back different |
| ⭐ `service_state_moved` | **the one that is invisible in the numbers** — a different solution answered. The values may be identical and the claim is still not the same claim |
| `unclassified_region_moved` | the resource digest moved while every value and every named piece of state stayed put — something changed in a part of the response nobody classified |
| ⛔ `classification_stale` | a region the recorder classifies is gone. **This one is about the instrument, not the service** |
| ⚠ `not_observed` | the query could not be issued. ⛔ Never collapsed into `no_drift` — a check that did not happen is not a check that passed |

⭐ **The precedence is a decision, and it runs most-specific first.** A value change always
moves the digest and a state change usually accompanies one, so classifying on the digest
first would collapse every finding into `unclassified_region_moved` and the report would stop
saying anything useful. `unclassified_region_moved` is therefore defined by what it is *not*
— which is exactly the case worth a human's attention, because it is the case where the
recorder's model of the response is incomplete.

⭐ **The job rebuilds each query from the fixture's own `request` block**, never from a
constant of its own. `request` in this contract means *sufficient to regenerate*; a job that
rebuilt the query from its own copy would not be testing that claim. It also follows the
value fixture's pointer at its acquisition record and checks the digest — the same resolution
a consuming loader performs, exercised on every run.

**Verified against a deliberately damaged copy**, one live pass, three defects in three
different queries: `values_moved`, `service_state_moved` and `unclassified_region_moved` were
each reported for the right query, the other nine returned `no_drift`, and the process exited
**0**.

---

## 6. ⛔ What the acquisition record cannot say, and says so

The published-file record already carries a limit: it cannot establish that the publisher
published anything, only that an address returned these bytes to this instrument on this
date. **The service record's limit is weaker still**, and it is written into the record:

> For a published file, this instrument can attest that an address returned exactly these
> bytes. For a service it cannot: the bytes are not reproducible, and what is attested is
> that an address, on this date, returned a response from which **this** resource was
> extracted **by a rule written in this instrument**.

⚠ So the record attests this instrument's *reading* of the response as much as the response.
A reader who would draw the line between transaction and answer somewhere else is disagreeing
with the recorder, not with the service — and the rule is written down in full, with every
region it classifies asserted present on every run, precisely so that disagreement is
possible.

---

## 7. Two things the fixture contract caught, again

Both were caught at **write time**, before anything reached a commit.

* ⛔ **An object keyed by a body number.** `{"199": {...}}` — refused, because a key must be
  `lower_snake_case`. The companion published-file fixture learned the identical lesson from
  the identical refusal. A body number is *data*, and data hiding in a schema diffs badly and
  reads as structure.
* ⭐ **A query recorded as an object.** The service's parameters are `UPPERCASE` and are the
  *service's* — putting them in JSON keys would make a third party's naming into this
  schema's permanent identifiers. Recorded as a sorted list of `{parameter, value}` records
  instead, which also gives one query exactly one recorded form.
