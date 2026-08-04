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
