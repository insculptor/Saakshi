# Saakshi — साक्षी, *the witness*

**A measurement instrument.** Saakshi calls ephemeris software and external data services
and writes down what they said. Its **output** — plain-text fixture files carrying a full
provenance block — is the only thing that travels.

**Licence: AGPL-3.0-or-later.** See [`LICENSE`](LICENSE).

---

## What this is

Astronomy and astrology software is only as trustworthy as the outside evidence it is
checked against. Saakshi is where that evidence is collected: it queries reference
implementations, published services and printed sources, and records each answer together
with everything needed to reproduce it — the exact query, the software version, the data
file's digest, the date, and the commit of the script that asked.

The fixtures it writes are consumed elsewhere, as committed data. **Saakshi is never a
dependency of anything and is never a runtime service.** Only files move.

> **Saakshi is a *recorder*, not an *oracle*.** The Swiss Ephemeris is an authority;
> Saakshi is how we write down what Swiss said. A fixture cites the ephemeris and its
> version. The name `Saakshi` appears in exactly one place in a fixture — the `generator`
> provenance field, which records **origin**, never **authority**.

---

## ⛔ The four rules this repository must not break

1. ⛔ **Never a dependency, never a runtime provider.** Nothing links Saakshi, imports it,
   or calls it over a network. Only its output travels, as committed files.
2. ⛔ **A recorder, never an explainer.** Saakshi calls a piece of software and records what
   came back. It must contain **no code, no notes and no documentation that explain *how*
   any of the software it calls computes anything.**
   ⭐ This is the rule most worth understanding, because it is not about licences. Code
   that consumes these fixtures is written clean-room, from published specification. A
   note in *this* repository describing another implementation's internals would become an
   *implementation source* for that code — contamination no dependency scanner can see.
   ⚠ It matters more here than anywhere, because this repository is public and may attract
   contributions. **A pull request that transcribes or explains another implementation's
   algorithm will be declined, however correct it is.**
3. ⛔ **A fixture filename or JSON key never contains a project name** — not `saakshi`, not
   the name of any consumer. A permanent identifier must not encode a renameable name. The
   `generator` provenance *value* naming this repository is a recorded fact about origin,
   and is required. See `config/reserved-names.txt.example`.
4. ⛔ **Fixtures are plain text and fail closed.** JSON/JSONL for values, TOML for
   manifests — no binary, no LFS, no compression. A file missing a field its kind requires,
   or carrying one its kind forbids, is refused *at write time*, so a malformed fixture
   never reaches a commit.

## ⚠ What is not decided here

This repository **makes no licence determination and no legal conclusion.** It states
mechanical facts: what was called, what came back, and under what versions.

---

## Layout

```
generators/          one script per fixture set; each is a recorder
  r1_horizons.py         geometric states from the publisher's live service
  r1_drift.py            whether that service still answers as a fixture says; ⛔ never gates
  r2_kernel_states.py    geometric states from a pinned DE kernel, read twice
  publisher_testpo.py    the ephemeris publisher's own test-value set
  r3_swiss.py            the same grid under each ephemeris source, source asserted per row
  r5_continuity.py       what an earlier implementation answered, before it stops running
  probe6b_ffi.py         what crossing into the ephemeris binding costs, as ratios
  r6_karaka_rules.py     what one located translation states, and one rule it does not
  r6_reduction_fork.py   a rule one chapter disagrees with its own illustrations about
  r6_reduction_example.py  a source's own worked figures, reproduced from what it printed
src/saakshi/         the shared library
  fixture.py             the fixture contract, fail-closed, five discriminated kinds
  acquisition.py         retrieval as evidence; ⛔ a cache read is not an acquisition
  service.py             what a service response is made of; ⛔ a resource is not its payload
  kernels.py             locate and hash-verify a kernel pinned by digest
  provenance.py          generator identity; ⛔ refuses to stamp a dirty tree
  civil.py               resolved instants and coordinates; ⛔ refuses a half-resolved row
  leaves.py              flatten a returned object to addressed leaves
  surface.py             a sampled engine's call surface, declared as local data
  swiss.py               which ephemeris actually answered; ⛔ refuses to attribute a value
  timing.py              a timing ladder and its controls; ⛔ publishes ratios, never durations
  textual.py             the locus discipline; ⛔ a citation that does not resolve is refused
  texts.py               the copies a locus resolves into; ⛔ emission never acquires
tests/               the contract's own negative tests
config/              reserved names (local, not committed)
out/                 generated fixtures (not committed; they are consumed elsewhere)
docs/                the fixture contract, and the measurements taken here
```

## Running a generator

Every generator refuses to run against a dirty or commitless working tree, because
`generator.commit` in the provenance block would otherwise name a state that does not
exist. **Commit first, then generate.**

```bash
python -m pip install -r requirements.txt
cp config/reserved-names.txt.example config/reserved-names.txt   # then add your own

python generators/r2_kernel_states.py --kernel <path to de440s.bsp> --out out/
python generators/publisher_testpo.py --kernel <path to de440s.bsp> --out out/
python generators/r1_horizons.py --kernel <path to de440s.bsp> --out out/
python generators/r3_swiss.py --ephe-path <directory of .se1 files> --out out/
python generators/convention_probes.py --ephe-path <directory of .se1 files> --out out/
python generators/probe6b_ffi.py --out out/

python generators/r6_karaka_rules.py --acquire --out out/
python generators/r6_reduction_fork.py --acquire --out out/
python generators/r6_reduction_example.py --out out/
```

⚠ **The `r6_*` generators separate acquiring a text from citing it.** `--acquire` goes to the
network once and writes the retrieval beside the copy; every later run reads what is on disk
and refuses to fetch. ⛔ A generator that acquired at emit time would stamp today's date on a
copy obtained months ago, and would need the network to reproduce its own output.

⚠ **`probe6b_ffi.py` takes no path at all, and that is deliberate** — see the section on
timing below. It records the interpreter, the binding, the library version and the platform,
and ⛔ never a filesystem path: a path describes the machine that ran the recorder rather than
the subject, and the writer refuses one in any value of any fixture.

⚠ **`publisher_testpo.py` needs the network on every run, and there is no offline path.**
Beside the value fixture it writes an *acquisition record* attesting where the published
test file came from, and ⛔ a cache read is not an acquisition — returning cached bytes and
stamping today's date on them produces a record that is false in the one field it exists to
establish. A retained copy is used as a **second** observation to check the first against;
if the two disagree the run is refused, because one address having served two artifacts is
not something a recorder may resolve on its own.

### Sampling a service, where the resource is not the response

⛔ **A published file can be fetched again byte-identically. A service cannot.** Its response
is a *rendering*, carrying material that exists because a request happened rather than
because an answer did — and byte-for-byte reproducibility is a write-time guarantee here.

⚠ This is sharper than it sounds: the *"one address has served two different artifacts"*
refusal above, pointed at a service unchanged, fires on the **second** request every time. So
the fix is not to weaken it. It is to say what the **resource** is, and let the digest, the
cache and the refusal all run over that.

⭐ **A response turns out to have three parts, not two**, and the middle one is what a
two-way split gets wrong in both directions:

* **the transaction envelope** — moves on every request. Measured: two identical requests
  differ in exactly one line. ⛔ Never recorded. This is the response `Date` header's problem
  arriving *inside the body*, where no header allow-list reaches it.
* ⭐ **the service's own state** — which solution answered, which auxiliary files were
  loaded, which interface replied. Moves on the *service's* schedule. Discard it as volatile
  and the file no longer says what answered; digest it as resource and the artifact stops
  regenerating the day the service updates a file nobody here controls. So it is recorded
  **as data** and excluded from the **digest**.
* **the resource** — what is left, and what the digest is over.

⭐ The reproducibility claim therefore becomes conditional and states its condition:
*these bytes regenerate for as long as the recorded service state holds.* ⛔ A conditional
guarantee with nothing watching the condition is a guarantee nobody checks — which is the
drift job:

```bash
python generators/r1_drift.py --fixture out/service/r1-values.jsonl --out out/
```

⛔ **It detects and proposes. It never gates** — it exits 0 on every outcome, adopts no band
and edits no fixture. A job that failed a build the day a public service updated a data file
is a job somebody switches off, and the fixture it would have failed is still exactly good
evidence of what the service said when it was asked.

⭐ The finding it exists for is the one the numbers cannot show: a response whose values are
unchanged and whose **solution identifier** has moved. The rows still verify, and they are a
different claim. See `docs/measurements/2026-08-04-service-sampling.md`.

### Asking what a library assumes when nobody says

`convention_probes.py` asks five questions whose answers a caller inherits without passing
anything: the offset applied to reach the dynamical time scale, what a default position
already has applied to it, **which atmosphere a rise/set call uses when both atmospheric
arguments are zero**, which leap seconds the conversion knows and where its table ends, and
which house methods refuse above the polar circle.

⭐ **Two of the five answers are the opposite of the assumption a careful caller would
make**, so each is established by interrogation rather than by reading documentation — and
the decisive one is settled as a **bit-identity** between a call that passes nothing and a
call that states an atmosphere explicitly, rather than as an approximate agreement. See
`docs/measurements/2026-08-04-conventions.md`.

### Asking which ephemeris answered

⛔ **An ephemeris library may substitute a different ephemeris than the one requested —
silently, successfully, and returning an entirely ordinary value.** It does so when the
requested one is unavailable or does not cover the date. So a recorder that writes down
what came back, without establishing where it came from, produces a file that is
well-formed and mislabelled; and a comparison between two such files reports exact zeros,
which reads as agreement and means only that both sides were the same ephemeris.

⚠ **"Assert the returned flag" is necessary and not sufficient.** Measured on the library
this repository records: of four entry points, **one** reports the ephemeris that answered.
One returns a flag that is the request handed back — it was observed returning a data-file
flag with no data file available at all. Two return no statement of source whatsoever, and
those two are the house cusps and the rise/set times.

So `src/saakshi/swiss.py` distinguishes the two assertions a recorder can actually make,
and every row records which one it relied on:

* `reported` — the entry point said which ephemeris answered, and it was the one asked for.
* `proxy_window` — it said nothing, so the source was established at **both ends** of the
  interval the call may read, using an entry point that does report. ⚠ Bounded, not sound,
  and weaker than a report; rows say so rather than presenting the two as equivalent.

⭐ **A row whose source cannot be established is not written.** It is listed in the header
as a substitution. That exclusion is the mechanism: it is what keeps an uncovered epoch
from contributing a zero that would read as agreement.

### Sampling an engine for continuity

One generator is different in kind: `r5_continuity.py` samples a *running implementation*
rather than a data file, so that its answers survive it being switched off.

```bash
cp config/predecessor-surface.toml.example config/predecessor-surface.toml   # then fill in

python generators/r5_continuity.py --natives 64 --report-only   # price the grid first
python generators/r5_continuity.py --natives 64 --out out/
```

⚠ Run it with an interpreter that can **import the tree being sampled** — that tree's own
dependencies are not this repository's and never will be.

⭐ **Why this one has a deadline and the others do not.** A kernel or a published table can
be read again next year. An implementation cannot be sampled once it stops running, and
nobody gets to ask it a new question afterwards. Everything the recorder can turn into a
number now, it does: each row carries the **resolved UTC offset** beside the local clock
reading and the **resolved coordinate** instead of a place name, so reading the corpus later
needs no timezone database, no place-name service, and nothing switched back on.

⛔ Every such fixture is `reference_only`. What an implementation answered is evidence about
that implementation — never about the sky, and never a tolerance anyone may adopt without
measuring it themselves.

### Timing a boundary, where the artifact cannot regenerate

⛔ **`probe6b_ffi.py` writes the only file this repository produces that does *not* regenerate
byte for byte**, and it says so in its own first note rather than leaving it to be discovered
from a diff. Its subject is a duration, and a duration is not a property of the callee alone.

⭐ **So it publishes ratios and records durations only as environment context**, with the same
standing as the host record. A figure in nanoseconds is the wrong *shape* for a claim about a
binding, in the way a band expressed in an absolute distance was the wrong shape for a claim
about a state vector — and the same do-nothing function was measured at 24, 39 and 47 ns on
one machine depending on when it was asked and how the loop around it was written.

Three things make the ratios worth having, and each is a rule in `src/saakshi/timing.py`:

* ⛔ **the clock is coarser than the subject** — 100 ns steps against calls costing tens of
  nanoseconds, so **no individual call is ever timed**. Every figure is a mean over a declared
  count, and a batch too short to clear a hundred clock steps is refused rather than recorded;
* ⭐ **the call-site form is part of the number.** Handing a callee a pre-built argument tuple
  is not the same act as compiling the arguments into the call site, and the difference was
  measured at about half again for this binding while vanishing for a Python function. Each
  rung is measured all three ways and the form is stated on every row;
* ⛔ **a repeated call is not a repeated computation.** A timing loop asks one question many
  times; a callee may answer the second asking far more cheaply. Every rung whose cost could
  depend on which question is asked is measured over one request repeated *and* over distinct
  requests — and of the two rungs here that do real work, one is sensitive by a factor of
  thirty-odd and the other is not.

⛔ **The generator refuses to write if any of its four controls fails.** A timing harness has
no known answer to check itself against, so what is checked is its ability to report a
difference that is there and none where there is none — including **a pair built to differ by
a stated factor**, because a null control alone is satisfied by a harness that measures
nothing at all. See `docs/measurements/2026-08-14-ffi-baseline.md`.

### Acquired data

Data files are **never committed here** and are never fetched from an unpinned location.
A kernel path is supplied on the command line and the file's SHA-256 is checked against a
recorded pin before a single value is read: a content-addressed *name* records what
somebody intended, and anything that can write to the directory can write a wrong file
under a right-looking name.

## Before pushing

```bash
python -m pytest -q                      # the contract's refusals
python tools/check_public_tree.py        # no reserved name reaches a commit, or waits to
```

⚠ The second scans **every reachable commit**, because a name removed in a later commit is
still published by the earlier one. It exits non-zero when `config/reserved-names.txt` is
missing rather than passing on an empty list.

⭐ It also scans **the working tree** — every path and every text file, tracked or not,
**ignored or not**. A name that is only on disk has not been published, so deleting the
path is the whole fix; but an untracked path is invisible to a scan of commits, and a
single `git add -A` publishes it permanently. ⛔ Being git-ignored buys a path nothing
here, deliberately: ignoring one is how the same failure comes back under a different name
in a different path. The short list of paths that exist *to hold* private material is
exempt, and every run prints it.
