# The two generators that had never been run, and the refusals nothing had run against

> Date: **2026-08-15** · Generators: `publisher_testpo.py`, `r1_horizons.py`, `r1_drift.py`
> Host: one workstation, `x86_64` Windows, CPython 3.12.11
> ⚠ **One host, one platform, one day.** Everything below is a measurement taken here.

Both of this repository's network generators had been protected by static evidence and by
held artifacts nobody had regenerated. They are the last two that had never been executed
on this machine — and the argument for running them is the same one that has paid off every
time it has been applied here: ⭐ *a refusal nothing has ever run against is a refusal
nobody has tested.*

Running them produced one result about the artifacts, one about a design claim that had only
ever been asserted, and one defect in the recorder.

---

## 1. ✅ Both generators reproduce their held artifacts

| Generator | Rows | Against the held artifact |
|---|---|---|
| `publisher_testpo.py`, standard kernel | 3 099 | ✅ byte-identical |
| `publisher_testpo.py`, extended kernel | 11 354 | ✅ byte-identical |
| `r1_horizons.py`, the live service | 504 | ✅ byte-identical |

The header diffs were taken field by field rather than by eye. Across all five files
(three value fixtures and two acquisition records) exactly five keys moved, and each one is
a key that **must** move:

* `generated`, `record_date`, `retrieved_on`, `oracle.…acquired` / `oracle.queried_on` — the
  dates. A recorder that stamped an old date on a new retrieval would be false in the one
  field the record exists to establish.
* `generator.commit`.
* the value fixture's pointer at its own acquisition record's `sha256` — which moved
  **because** the record's date and commit moved. ⭐ That is the chain working: the pointer
  is a digest, so it could not have stayed still while the thing it points at moved.

⚠ **The reproduction is not the same claim in the two cases**, and the difference is the
whole subject of the service-sampling measurement. The published test file is a file: it was
fetched again and hashed to the same value. The service is not: what reproduced is the
**resource** this instrument extracts from the response by a rule written here — and it
reproduced across **eleven days**, with every recorded piece of the service's own state
unmoved.

⭐ **`reproduction_abs_delta` reproduced bit for bit, 14 453 of them across the two kernels.**
It is the largest class of doubles in this repository that carries no bit pattern, and it is
the only trace in its file of what this instrument computed rather than read. Nothing guards
it at write time; what was available was to regenerate it and compare, and it is identical.

---

## 2. ⭐ The claim the whole three-part split rests on, demonstrated rather than asserted

`acquisition.py` and `service.py` both rest on a sentence about what would happen without
the canonical form:

> *pointed at a service unchanged it fires on the **second** request, every time, and would
> report a service as having contradicted itself when nothing about the answer moved at all.*

That had never been run. Measured, live, against the service unchanged, both arms:

| Arm | Request 1 | Request 2 |
|---|---|---|
| no canonical form — the service sampled as though it were a file | accepted, `payload_is_the_resource=True` | ⛔ **refused**: *one address has served two different artifacts* |
| the canonical form — the resource said out loud | accepted, `payload_is_the_resource=False` | ✅ accepted, `prior_copy_agreed=True` |

⭐ The second row's detail is the design in one line: **the payload digest moved and the
resource digest did not.** The transaction moved; the answer did not.

⚠ The first arm is the control, and it is the one that makes the second arm mean anything.
A canonical form that is accepted proves nothing on its own — a refusal that never fires at
all would produce exactly the same accepting line.

---

## 3. ⛔ The defect: the one region read by position was the one allowed to be ambiguous

The service split's refusals *are* tested. They are tested against a hand-written twenty-line
response carrying one data row of `1.0 … 6.0`, written by the same hand as the rules it
exercises. So the real responses were replayed through the real split, one deliberate defect
at a time — the method that settled the write-time pattern check, applied to the other
recorder.

**32 of 32 defects refused**, across two real responses (one answered by the planetary
solution, one by a body-specific solution). **10 of 10 non-defects accepted, each moving
exactly what it should**:

| Change to a real response | Resource digest | Recorded state |
|---|---|---|
| nothing (the null control) | same | same |
| only the generation stamp | **same** — the envelope exclusion working on real text | same |
| the solution that answered | **same** | **moved** |
| a value | **moved** | same |
| a region this instrument does not classify | **moved** | same |

⭐ Rows two and three are the reproducibility condition itself, measured on a real response
instead of argued for in a docstring: the part that moves every request is out of the digest,
and the part that moves on the service's schedule is out of the digest **and written down**.

⛔ **One defect was not refused.** Every classified region in the module is located through
`_locate`, which refuses a pattern matching more than once —

> *A classification that matches more than one region cannot say which one it describes.*

— and the column header was not. It took the first match and said nothing. It is also the
one region the data block is read against **by position**, which makes it the region where
taking the wrong match is quietest: a response carrying a second, differing header was
accepted, and every data line read under a header that was not the one governing it.

⚠ **The first version of that mutation measured nothing.** It replaced a spelling with six
spaces in it; the real header has twenty-two. The mutation was a no-op, the "acceptance" was
a parse of the unmodified response, and it was indistinguishable in the output from the real
defect found next to it. ⭐ *A measurement whose subject is wrong has measured nothing* — the
mutations are now built by splitting the real line, and each asserts that the line changed.

**Fixed**: the header is located under the same rule as everything else. Measured **before**
arming it — the header matches exactly once in all twelve responses this repository has
sampled — because a rule that refuses the ambiguous case and the ordinary one too has not
tightened anything, it has stopped the instrument working. Both halves are tests.

---

## 4. ⚠ The drift job had only ever agreed

Run against the held fixture eleven days after it was written: **12 of 12 `no_drift`**. The
condition the service artifact is conditional on still holds, checked by the mechanism built
to check it rather than by a human reading two files.

⛔ **And that is the accepting run.** A job that compared nothing would print the same twelve
lines. So the held pair was copied — never modified in place — trimmed to one query, and
corrupted one defect at a time, against the live service:

| The held fixture, corrupted | Outcome reported | Wanted |
|---|---|---|
| nothing (the null control) | `no_drift` | ✅ |
| one recorded value | `values_moved` | ✅ |
| the recorded solution | `service_state_moved` | ✅ |
| only the recorded resource digest | `unclassified_region_moved` | ✅ |
| the record, with its pointer left unchanged | ⛔ refused: *not from one emission* | ✅ |

**5 of 5.** Four of the six outcomes are now observed rather than reasoned about, and the
fifth control is the one that had to be defeated to produce the middle three: the job refuses
a value fixture and an acquisition record that are not from one emission, so a corrupted
record cannot even be presented to it without re-stamping the digest that points at it.

⚠ `classification_stale` and `not_observed` were not produced live. The first is what the job
reports when the split refuses — the 32 refusals in section 3 are its raw material — and the
second needs the network taken away. Neither is claimed here as observed.

---

## 5. What this did not establish

* ⛔ **Nothing about the sky.** The publisher's set is the publisher on both sides; the
  service rows are `reference_only` and declare no band, for the reason that file states at
  length.
* ⛔ **Nothing about a third reader.** The band in the self-consistency file was measured
  between one toolkit and the publisher's printed values, and it says so.
* ⚠ **Nothing about tomorrow.** `no_drift` today is an observation, not a guarantee; that is
  why the job exists and why it never gates.
