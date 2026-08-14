# The fixture contract

Every file this repository produces is evidence, and evidence that cannot be traced back
to what produced it is not evidence. So every fixture carries a provenance block, and the
writer refuses to emit one that does not.

Implemented in [`src/saakshi/fixture.py`](../src/saakshi/fixture.py); its refusals are
tested in [`tests/test_fixture.py`](../tests/test_fixture.py).

## Format

**JSONL.** Line 1 is the header; every later line is one row.

```
{"record":"header","schema_version":"1.0.0","fixture_kind":"numeric_pin", ...}
{"record":"row","section":"position","target":301,"centre":399, ...}
{"record":"row","section":"velocity","target":301,"centre":399, ...}
```

A single JSON document would have been simpler to load and worse to live with: a
regeneration has to show *which* rows moved, and a 3 000-row array re-indents as one
diff hunk.

⛔ **Plain text only** — JSON/JSONL for values, TOML for manifests. No binary, no LFS, no
compression. Evidence you need a tool to read is evidence nobody checks.

## The provenance block

| Field | What it records |
|---|---|
| `schema_version` | the version of this contract |
| `fixture_kind` | the discriminant — see below |
| `reference` | **exactly one** reference identifier |
| `generator` | repo, script path, and the **commit** the script was at |
| `generated` | the date |
| `oracle` | the identity of whatever produced the values: software version, service query, data-file digest, or a source text's locus |
| `request` | the full inputs, sufficient to regenerate |

⛔ **A dirty working tree cannot be stamped.** `generator.commit` promises the code that
produced these numbers is readable at that commit. If there are uncommitted changes the
promise is false, and a false provenance field is worse than a missing one because it
looks discharged. Commit first, then generate.

## The five kinds

Validation **dispatches on the kind**. It does not carry a list of exceptions, because an
exception list drifts away from the thing it excepts.

| `fixture_kind` | What it is | Requires | ⛔ Must not carry |
|---|---|---|---|
| `numeric_pin` | a value comparison | `classification`, a budget row, `request` | a source locus |
| `worked_example` | a number a **source text itself** resolves | the classification, a complete locus, `budget_basis = source_reproduction` | a mapping to an astronomical budget row |
| `textual_rule` | what an identifiable source **states** | a complete locus | **any numeric classification** |
| `textual_fork` | a rule on which identifiable sources differ | **≥2 readings**, each with its own locus | any numeric classification; fewer than two readings |
| `provenance_record` | evidence that is not a comparison | what it attests, the authority, a date | a locus it does not have |

Two of these deserve their reason spelled out.

⭐ **A rule is not a number and has no band.** The judgement vocabulary — `exact`,
`tolerance`, `reference_only` — is defined for numbers. Letting a cited rule carry one
would oblige prose to be judged by a scheme that cannot judge it, so its presence is a
load error rather than a tolerated extra.

⭐ **A worked example proves reproduction, not accuracy.** When a text resolves its own
example and we reproduce it, what is established is that we followed the text's method. A
6th-century text's own astronomy is historical. Mapping such a row to a modern accuracy
budget would launder one claim into another, so the schema forbids it outright.

## A locus, and the two fields that used to accept anything

The three textual kinds require a **complete locus**: `source_kind`, `language`, `edition`,
`locus`, `interpretation_status`. All five must be present, and two of them are now checked
against a value set.

⛔ **They were not, until R6 became the first artifact to stand on them.** Validation checked
presence and never what the field said, so a misspelling passed the writer and arrived
downstream as a group of one. This repository's own test suite was the proof: its shared
locus carried `interpretation_status: "settled"`, a value no registry has ever declared, and
every test using it passed. ⚠ **A field whose value set is "any string" reports a pass on
anything.**

| `source_kind` | what the material at the locus sits in |
|---|---|
| `primary_text` | the root text, in its own language |
| `translation` | a translation of a primary text, carrying the translator's numbering |
| `commentary` | exposition printed alongside a text, by its translator or a commentator |
| `worked_illustration` | a worked example the source resolves itself |
| `treatise` | a modern author's own work, not a translation of anything |

⭐ The distinction that earns the registry is **translation versus commentary**. They are
printed on the same page and are not the same authority. Filing one as the other implements a
modern commentator under the text's name — and that is not hypothetical: of five rules in the
first R6 artifact, two sit in the translator's notes and not in the sutras.

| `interpretation_status` | how far the recorded claim sits from the words |
|---|---|
| `quoted` | the recorded claim **is** the located words |
| `restated` | the located words state it; restated without inference |
| `read_from_worked_example` | not stated anywhere; read off an example the source resolves |
| `disputed_reading` | the located words admit more than one reading, and this is one |
| `absent` | the claim is that the located extent does **not** state this |

⭐ This is the field that separates *the text says this* from *we read this out of the text*.
Only one of the two can be checked by looking.

⭐ **`absent` still requires a complete locus.** An absence with no extent names nothing and
cannot be falsified. What bounds it is stated on the fixture: every spelling searched, with
its own hit count, and the measured extent of the copy searched.

⚠ `language` is held to a **shape** — a two- or three-letter lowercase code — rather than a
registry. The set of languages is not this contract's to declare, but `English`, `english`
and `Eng.` are three groups for one language. `edition` and `locus` stay free text: they are
a proper name and a citation, and a registry of those is a registry of everything ever
printed.

## Classification

`numeric_pin` and `worked_example` declare, per section:

* `exact` — bit-for-bit;
* `tolerance` — **band and unit both required**; a tolerance without a unit is not a
  tolerance;
* `reference_only` — committed, not yet compared.

`reference_only` is not a weaker fixture. It is the honest state of evidence that has been
collected before anyone has measured what band applies to it — and a band invented to look
comfortable is exactly the failure the whole contract exists to prevent.

⚠ **But it is not a resting place either.** A file classified `reference_only` cannot pass
whatever band is later set for it, so leaving it there once a band *has* been measured
turns "not yet compared" into "never compared".

⭐ **A declared band is generation context, never an instruction.** It records what the
generating instrument measured; the band a consumer applies comes from that consumer's own
budget. A disagreement between the two is a line to report, ⛔ never a reason to refuse the
file — so a later tightening on the consumer's side can never make an emitted fixture
unloadable, and declaring a measured band here adopts nothing on anyone's behalf.

⭐ **A band's shape is part of the measurement.** The R2 state fixture declares its band per
section, relative to the norm of that section's three components — not in kilometres, which
scales wrongly, and not relative to the component, which a near-zero component inflates.
Where the norm is zero the relative disagreement is emitted as `null` and the row is
excluded from the band, because a relative band cannot judge a quantity with no scale.

## A bit pattern is for a measurement, and a count is not a measurement

A recorded value that is a double is written twice — as a decimal, and as the IEEE-754 bit
pattern beside it. ⭐ **The pattern is the value and the decimal is display.** The reason is
itself a measurement: a widely-used JSON library was measured mis-parsing 18.9 % of
shortest-round-tripping doubles by up to 2 ULP, so a reader on that path holds a different
number from the one written and has no way to notice. A reader that disagrees on the decimal
and agrees on the pattern has a formatting bug; one that disagrees on the pattern has a
numeric one; and the two are worth telling apart at a glance.

⭐ **The rule is bounded by that reason.** A decimal *approximates* a double, and the pattern
is what settles which double was meant. A count is not approximated by its own digits, so
there is nothing left for a pattern to settle. Packing one into an f64 pattern would state
that a counted quantity had been measured on a real-number scale — the same class of false
claim as a band nobody measured, and harder to see, because the result is sixteen
well-formed hex digits.

So:

* a recorded **double** carries its pattern beside it — `X` and `X_bits`, or `number` and
  `bits` in the leaf model;
* an **integer** — a count, an index, a body number — is written **bare**, and `bits()`
  refuses one at the point where the mistake would be made;
* ⛔ an integer past **2<sup>53</sup>** is refused at write time, in a row or in a header.

⚠ **That last clause is what keeps the second one honest.** JSON declares no integer type. A
reader that parses every number into a double holds a different value past 2<sup>53</sup>, and
there is no pattern beside it to disagree with — the exact hazard the rule exists for,
reopened by its own exemption. Measured when this was written: the largest integer in any
**row** of any fixture this repository has produced is **858 238**, and the largest in any
**header** is **119 799 808**. The refusal costs nothing today; it is what makes the exemption
still true when something counts something bigger.

⭐⭐ **The exemption is not attached to a fixture kind, and that was the decision.** A
`worked_example` raised the question — every one of the 123 numbers in the first such
artifact is a count: printed figures, cells read, cells agreeing, occurrences of a quoted
fragment. But the corpus `r5_continuity.py` writes is a `numeric_pin`, the kind the pattern
rule was written for, and it carries **123 428** integer leaves with no pattern, by the same
branch of the same walker. ⛔ An exemption written for the kind would have left that file
refused for a reason that was never about it. **The question a number answers is what the
rule turns on, not the kind of file it arrived in.**

⚠ **And this section does not claim that every double carries a pattern, because that is
measured false.** Of the floats in the fixtures produced so far, **42 830** in value rows
carry none — derived comparisons, declared inputs and environment context.

⛔ **There is no rule behind that, and the one previously offered for it is retired.** *"The
pattern accompanies the value a fixture is evidence of"* was measured against the artifacts
and they contradict it, most sharply where it matters most: in `publisher-test-values` the
**patterned** number is the one copied out of the publisher's file, while
`reproduction_abs_delta` — the residual this instrument established, and the only trace in the
file of what it computed — is written **bare**, 14 453 times. Two arguments of one call in one
row are also split, `latitude` patterned and `atpress` not.

⭐ **The pattern's own reason reaches every double.** A decimal approximates a double whether
that double is a measurement, a derivative or an input, so nothing in the stated purpose
distinguishes them. What actually decided each case was whether the value passed through a
`bits()` call site — a fact about the writing code, not about the numbers. ⚠ **A rule this
repository's own artifacts do not satisfy is not this repository's rule**, so none is declared
here; arming one would refuse thirteen emitted artifacts, six of whose generators cannot be
run. See [`docs/measurements/2026-08-14-pattern-convention.md`](measurements/2026-08-14-pattern-convention.md).

⚠ The earlier figure for this was **48 122**, and it was wrong by exactly 5 294 — the count of
values whose pattern is spelled `et_bits` rather than `et_seconds_bits`, which the survey's
walker did not match. ⛔ **The pairing is by name and nothing enforced it**, which is how one
relationship acquired two spellings; `patterned()` now writes the pair so a third cannot
appear.

## A pattern that is written is checked

Wherever a pattern *is* written, it is verified at write time, in the same walk that enforces
the rules above. Three refusals:

* a pattern key that resolves to **no value key** — a pattern that names nothing is a pattern
  nobody checks, and it reads as though the value beside it were guarded;
* a pattern that is not sixteen lowercase hex digits;
* a pattern and a decimal that are **different numbers**, compared through `bits()` rather
  than `==` so that `-0.0` and `0.0` are told apart.

⭐ This reaches all three carrying forms — the flattened leaf model (`number`/`bits`), the
scalar sibling (`jd_ut`/`jd_ut_bits`) and the parallel array (`values`/`values_bits`). ⚠
`leaves.verify_bits` had only ever reached the first: **135 524** pairs checked, **108 768**
unchecked. A parallel array is read by index, so a length that does not match repatterns every
value after the gap. Measured over every fixture before the check was armed — 244 292 pairs,
zero unresolvable, zero malformed, zero disagreements, zero mismatched lengths.

⚠ One file departs furthest from the pattern convention: the timing fixture patterns **none**
of its 803 floats, and it is also the only artifact here that does not regenerate byte for
byte. ⭐ The measured cause is that `timing.py` and `probe6b_ffi.py` are the only
value-writing modules here that never import `bits` at all — so that is an **absence rather
than a decision**, which is a different fact from the one the previous note left open.

## Reserved names

⛔ A fixture **filename** or **JSON key** may never contain a project name. A key and a
filename are permanent identifiers; a project can be renamed; an identifier that encodes a
renameable name turns a rename into a data migration.

✅ Project names are permitted in **values** — `generator.repo` must name this repository,
because a value records origin and is not an identifier.

The list lives in `config/reserved-names.txt` and is not committed: the mechanism belongs
in the open, the names of unreleased consumers do not. See
[`config/reserved-names.txt.example`](../config/reserved-names.txt.example). Every
generator prints how many names are in force before it writes anything, so a list that is
not loaded is visible rather than silent.

## `reference` names a source — except once, where it names a relationship

`reference` admits `R1`–`R6`, `instrument` and `publisher_self_consistency`, and exactly
one of them.

⭐ **`publisher_self_consistency` is the only value that constrains the shape of `oracle`
rather than merely labelling it.** Every other value names a source a reader can go and
consult. This one names a *relationship* — one artifact of a publisher's reproducing
another — and a relationship is checkable only if both of its terms are named. So the
oracle must carry:

| Member | Requires | Why that field |
|---|---|---|
| `publisher` | — | a self-consistency claim is about **one party's** two artifacts |
| `test_artifact` | `identity`, `sha256`, `acquired`, `provenance_record` | the published values |
| `subject_artifact` | `identity`, `data_profile`, `sha256` | the published data they reproduce from |

⛔ Any absence is refused at write time and is a load error downstream. **Half a pair is not
a weaker claim; it is a different, unmade one.**

⚠ Two of those members earn their place against the obvious objection that the digest
already covers it.

* `provenance_record` — a digest says the bytes read hash to a value. It says nothing about
  where they came from, and a local file with the right name hashes just as convincingly.
  The record names the address, the date and the instrument. ⛔ And it still cannot
  establish that the publisher *published* anything: a server answering an address is a
  different claim, and the record says so in its own words rather than leaving it to be
  assumed away.
* `data_profile` — "the same ephemeris" is distributed as several files of different spans,
  and a self-consistency claim about one of them is not a claim about another.

## `reference` has an escape hatch, and it may not be left open

`"reference": "none"` is available for a claim the registry cannot yet express. A file
using it **must** carry a `contract_deviation` block naming the clause it does not satisfy
and what would close it. A consumer trips over the value, reads why, and a human decides.

⭐ **This is the mechanism that produced `publisher_self_consistency`.** A generator emitted
`none`, the consumer refused the file, and the value was minted by a reviewed change. The
hatch stays open for the next such gap.

⛔ **And it may only be claimed by a file that is actually non-conforming.** A fixture whose
reference is in the registry may not carry a deviation block: a deviation that has been
closed still reads as an open question, and it does so from the one block in the file that
exists to be trusted. The writer refuses both halves — `none` without a deviation, and a
deviation without `none`.

⭐ The alternative, at the start, was to pick the least-wrong existing value and move on.
That would have put a false statement in the one block whose entire purpose is to stop
false provenance claims — and it would have been invisible, which is what makes it worse
than the gap.
