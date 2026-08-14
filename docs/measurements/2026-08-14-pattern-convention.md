# Which values carry a bit pattern, and whether that is a rule

**2026-08-14.** Taken over every fixture this repository has produced — 22 files, all three
`out/` subtrees, header lines and value rows alike. ⛔ No generator was run and no artifact
was changed: this is a survey of files already on disk.

The question it was taken to answer was left open by the previous session's contract note:
a bit pattern travels beside *some* doubles here and not others, the narrower convention was
described as *"the pattern accompanies the value a fixture is evidence of"*, and that sentence
had never been written down as a rule anywhere. ⭐ **The answer is that it is not a rule, and
the sentence is not what the artifacts do.**

---

## ⛔ The first finding is that the previous measurement was wrong, and why

The carried figure was **48 122** doubles carrying no pattern. It is reproduced here exactly,
and it is an artifact of the walker rather than of the files.

A pattern is paired to its value **by name**, and this repository grew **three carrying
forms** — a fourth if the spellings are counted separately:

| Form | Shape | Pairs |
|---|---|---|
| flattened leaf model | `{"path": …, "number": x, "bits": "…"}` | 135 524 |
| scalar sibling | `"jd_ut": x, "jd_ut_bits": "…"` | 67 192 |
| parallel array | `"values": [x, y, z], "values_bits": ["…", "…", "…"]` | 41 576 |
| | **total** | **244 292** |

⭐ **And one value key has two spellings for its own pattern.** `r2_kernel_states.py` writes
`et_seconds` and names its pattern **`et_bits`**; `publisher_testpo.py` writes the same
quantity and names it **`et_seconds_bits`**. Counted: 5 294 of the first, 14 957 of the
second. The abbreviated one is documented in its own file's `row_schema`, so it is a local
choice rather than a defect.

A walker that matches only `<key>_bits` therefore misses 5 294 patterned values and reports
them as bare. Restricting to value rows and switching that one assumption reproduces the
carried number to the unit:

| Walker assumption | Bare doubles |
|---|---|
| rows only, abbreviated stem **not** recognised | **48 122** ← the carried figure |
| rows only, abbreviated stem recognised | **42 830** ← correct |
| rows and headers, abbreviated stem recognised | 43 253 |

⛔ **A convention no code enforces is a convention that drifts, and the drift is invisible
until something counts.** It cost a wrong number on the contract page, which is a cheap
outcome; the same drift in a consumer's loader would silently unguard 5 294 decimals.

---

## The stated convention, tested against the artifacts

*"The pattern accompanies the value a fixture is evidence **of**."* Three measurements, and
the sentence does not survive any of them.

### 1. ⭐⭐ In the largest bare class, the pattern accompanies the value that was **copied**, and the value the instrument **established** is bare

`publisher-test-values.jsonl` reproduces a publisher's own test values from a pinned kernel.
Its rows carry:

* `value` / `value_bits` — the number **read out of the publisher's file**;
* `value_printed` — the same number, as the publisher printed it;
* `reproduction_abs_delta` — `abs(reproduced − value)`, **bare**. 14 453 of them.

⛔ **`reproduced` is never written to the file at all.** So the residual is the only trace in
the artifact of what this instrument computed, it is the entire finding of the fixture, and
it is the one number in the row with no pattern beside it. Confirmed against
`generators/publisher_testpo.py`, not inferred from the shape of the row.

The same inversion in R2: `values` / `values_bits` are CSPICE's, patterned; the independent
`jplephem` cross-check's numbers are never recorded, and their only trace —
`cross_check_max_abs_delta`, 5 796 values — is bare.

### 2. ⛔ Two arguments of the same call, in one row, are treated differently

One `horizon_depression` row of `rise-refraction.jsonl`, five declared inputs to a single
rise/set call:

| Field | Value | Pattern |
|---|---|---|
| `latitude` | 26.4499 | ✅ `latitude_bits` |
| `longitude` | 80.3319 | ✅ `longitude_bits` |
| `atpress` | 1013.25 | ⛔ none |
| `attemp` | 15.0 | ⛔ none |
| `observer_height_m` | 0.0 | ⛔ none |

No reading of "what the fixture is evidence of" separates these five. They are five arguments
to one call, in one row.

### 3. Five leaf names are written **both** ways — and this part is coherent

| Name | Patterned | Bare | Where the bare ones sit |
|---|---|---|---|
| `jd_ut` | 3 899 | 3 480 | `source_assertion.ends[].jd_ut` |
| `jd_tdb` | 504 | 26 | `summary.cross_reference.…` |
| `latitude` | 6 813 | 19 | `request.sites[].latitude` |
| `longitude` | 6 810 | 16 | `request.sites[].longitude` |
| `value` | 15 965 | 4 | `oracle.au_in_km.value` |

⭐ **Every bare instance is a restatement, inside a `request`, `oracle`, `summary` or
`source_assertion` block, of a value that is patterned elsewhere in the same file.** This is
the one part of the habit that survives inspection: a second copy of a guarded number does
not need its own guard.

---

## Is a bare derived value recomputable from the patterned ones beside it?

If it were, the omission would have a defence — a reader who mis-parses it can rebuild it and
notice. Each candidate was recomputed from its own row and compared to the last bit.

| Bare value | Count | Recomputable from the row? |
|---|---|---|
| `cross_check_max_rel_delta` | 5 362 | ✅ exact, all of them — `abs_delta / norm` |
| `state_vector_norm` | 5 796 | ✅ 5 167 exact, 629 within 1 ULP |
| `delta_arcseconds` | 144 | ✅ 104 exact, 40 exactly negated (a sign convention) |
| `seconds_apart` | 12 | ✅ exact |
| `cross_check_max_abs_delta` | 5 796 | ⛔ **no** — the second reader's values are not in the file |
| `reproduction_abs_delta` | 14 453 | ⛔ **no** — the reproduced value is not in the file |
| `true_altitude_arcminutes` | 374 | ⛔ **no** — a separate measurement |
| `atpress`, `attemp`, `observer_height_m` | 2 366 | ⛔ **no** — declared inputs |

⇒ The defence covers **11 314** of the 42 830 and fails on the rest, including the two
largest classes. ⛔ **Recomputability is not the rule either.**

---

## ⭐ The timing artifact's "none of 803" is an absence, not a decision

The previous note recorded that `binding/ffi-round-trip.jsonl` patterns **0 of its 803**
row-level doubles and that no reason for it was on the record. Measured cause:

⛔ **`src/saakshi/timing.py` and `generators/probe6b_ffi.py` never import `bits`.** The
string does not occur in either file. Every other value-writing module in this repository
imports it.

So there is no reason on the record because no decision was taken. That is a different
answer from *"it was decided differently"*, and it is worth having: the ratios that artifact
exists to publish are unguarded because the discipline was never applied to that path, not
because anyone weighed it and declined.

---

## What the pattern is FOR, and what follows

The pattern exists because **a decimal approximates a double**, and a widely-used JSON
library was measured mis-parsing 18.9 % of shortest-round-tripping doubles by up to 2 ULP.
The pattern settles which double was meant.

⭐ **That reason reaches every double without exception.** It does not distinguish a measured
value from a derived one, an input from an output, or evidence from context. A mis-parsed
`reproduction_abs_delta` is exactly as wrong as a mis-parsed `value` — and by the measurement
above it is *more* consequential, because it is the number the fixture was written to carry.

⛔ **So the honest finding is that there is no rule here, and none can be read off this
tree.** What exists is a habit whose real shape is *a value that happened to pass through a
`bits()` call site got a pattern* — a fact about the writing code, not about the numbers. It
is not defensible on the pattern's own stated purpose, and the artifacts contradict the one
sentence that has been offered for it.

⚠ **A rule this repository's own artifacts do not satisfy is not this repository's rule**, so
none is declared. Naming a rule that 42 830 emitted values break would put a false statement
in the contract, which is the failure the contract exists to prevent.

### ⛔ What was deliberately not done

Arming *"every double carries a pattern"* would refuse **13 numeric artifacts** that are
already emitted and consumed. Six of the generators that would have to re-emit them cannot be
run here at all — they need a kernel, an ephemeris directory, the network or the sampled tree.
⛔ **Changing an output shape that cannot be executed is exactly the move this repository
refuses elsewhere**, so the decision is left where it belongs and is stated with its cost
rather than taken quietly.

---

## What was armed, because it refuses nothing

Two mechanisms, both additive, both measured against every artifact on disk before being
turned on.

**1. A pattern is verified wherever it is written.** `_verify_pattern_pairs` runs inside the
walk `write_jsonl` already performs over the header and every row, and refuses three things
that all look fine in a diff:

* a pattern key resolving to **no value key** — *a pattern that names nothing is a pattern
  nobody checks*, and in the file it reads as though the value beside it were guarded;
* a pattern that is not sixteen lowercase hex digits;
* a pattern and a decimal that are **different numbers** — compared through `bits()` rather
  than `==`, because `-0.0 == 0.0` is true and the sign of zero is one of the reasons the hex
  form exists.

⭐ **This closes a real gap rather than restating one.** `leaves.verify_bits` reached only the
flattened leaf model — **135 524** pairs. The scalar-sibling and parallel-array forms, another
**108 768** pairs, had never been checked by anything. A parallel array is read by index, so a
length that does not match repatterns every value after the gap, silently.

**2. The pair has one spelling.** `patterned("jd_ut", x)` returns both entries, in scalar or
parallel-array form, and refuses an integer for the same reason `bits()` does. Every generator
here hand-writes the pair, which is how a second spelling got in; a third now cannot.

⚠ The abbreviated `et_bits` spelling is **resolved rather than refused**, and only when it is
unambiguous — exactly one non-pattern key extends the stem. Two candidates is not a near miss
and is refused. ⛔ Unifying it would change an artifact whose generator cannot be run here.

⭐ **Measured before arming, over all 22 files and 244 292 pairs: zero unresolvable pattern
keys, zero malformed patterns, zero disagreements between a decimal and its pattern, zero
parallel arrays of mismatched length.** Nothing already written is refused — and that those
108 768 previously unguarded pairs are all correct is itself the first evidence anyone has
that they are.
