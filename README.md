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
> version. The name `Saakshi` appears in a fixture only as a **value** that records
> **origin** — the `generator` provenance field, and the client name an acquisition record
> writes down — never as **authority**, and never in a key or a filename.

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
   ⚠ Where the line falls: what a call returned, recorded as numbers, and what a library's
   own documentation says, quoted with its address and date and attributed to it, are
   records. An account of how the library arrives at what it returns is not. No test can
   check this rule; review does.
3. ⛔ **A fixture filename or JSON key never contains a project name** — not `saakshi`, not
   the name of any consumer. A permanent identifier must not encode a renameable name. The
   `generator` provenance *value* naming this repository is a recorded fact about origin,
   and is required. See `config/reserved-names.txt.example`.
   ⚠ The writer enforces this against a built-in default and against the names in your local
   `config/reserved-names.txt`. With no local list it enforces the default alone, and says so.
4. ⛔ **Fixtures are plain text and fail closed.** JSON/JSONL for values, TOML for
   manifests — no binary, no LFS, no compression. A file missing a field its kind requires,
   or carrying one its kind forbids, is refused *at write time*, so a malformed fixture
   never reaches a commit.
   ⚠ One stated exception. `mean_node_modes.py`, `nutation_obliquity_modes.py` and
   `nutation_obliquity_grid.py` must run with the standard library and the ephemeris binding
   alone, so they write their record without this package's writer. The suite holds each
   record to the same contract after it is written, in a test that needs the binding and the
   pinned data files.

## ⚠ What is not decided here

This repository **makes no licence determination and no legal conclusion.** It states
mechanical facts: what was called, what came back, and under what versions.

---

## Getting started

### Install

* **Python 3.11 or later** (`pyproject.toml`). Continuous integration runs 3.12.
* **git** on the path. Every generator that writes a fixture reads its own commit, several
  tests commit a temporary copy of the tree, and the leak check runs `git grep`.
* ⚠ **A virtual environment outside this working tree.** One inside it is git-ignored, so it
  never makes the tree dirty, but the leak check scans it like everything else (see
  *Before pushing*).

```bash
python3 -m venv <a directory outside this tree>
. <that directory>/bin/activate
python -m pip install -r requirements.txt
python -m pip install tzdata==2024.2     # the release continuous integration pins
```

`requirements.txt` pins exact versions, because a generator's versions enter the provenance
block of every fixture it writes, and several generators refuse a library at any other
version. What the code imports from it:

| package | what reads it |
|---|---|
| `pyswisseph` — the ephemeris binding, a compiled extension imported as `swisseph` | `r3_swiss.py`, `convention_probes.py`, `convention_grid.py`, the mean-node and nutation-obliquity generators, `probe6b_ffi.py`, `utc_conversion.py`, `deployment_capture.py` |
| `spiceypy` (it bundles the SPICE Toolkit), `jplephem`, `numpy` | the kernel readers: `r2_kernel_states.py`, `inter_de_states.py`, `publisher_testpo.py`. `spiceypy` also serves `r1_horizons.py` and `r1_geocentric_vectors.py`, which read a pinned kernel beside the service |
| `pypdf` | the textual generators (`r6_*`), where a copy arrives as a PDF and is rendered to text |
| `pytest` | the suite |
| `tzdata` (installed separately, above) | `r5_continuity.py`, which refuses to run without it, and the civil-time tests |

The package itself is never installed (`pyproject.toml` says why). Each generator puts
`src/` on its own path, and `pytest` reads it from `pyproject.toml`. **Run everything from the
repository root.** The default cache directories are relative to it.

`of_date_candidates.py` is the one exception: its libraries are not this repository's
requirements. See its section.

### Local configuration

Two files are copied from committed examples, and the copies are git-ignored:

```bash
cp config/reserved-names.txt.example config/reserved-names.txt              # then add every consumer's name
cp config/predecessor-surface.toml.example config/predecessor-surface.toml  # r5_continuity.py only; then fill in
```

Without `config/reserved-names.txt` the fixture writer enforces the built-in default only,
and most generators print `reserved-name check: WEAKENED` before they write.
`tools/check_public_tree.py` refuses to run at all, rather than pass over an empty list.

### Data files

Kernels and the library's data files are **never committed here, and this repository
downloads none of them.** Keep them anywhere, because a generator takes their path on the
command line. It checks each file's size and SHA-256 against a recorded pin before a single
value is read: a content-addressed *name* records what somebody intended, and anything that
can write to the directory can write a wrong file under a right-looking name.

| files | publisher | pinned in |
|---|---|---|
| `de440s.bsp`, `de440.bsp`, `de441_part-1.bsp`, `de441_part-2.bsp`, `de442s.bsp`, `de442.bsp` | NAIF / JPL Solar System Dynamics (`generic_kernels/spk/planets/`) | `src/saakshi/kernels.py` |
| `seas_18.se1`, `semo_18.se1`, `sepl_18.se1` | Astrodienst AG — the ephemeris library's own data files | `src/saakshi/swiss.py` |

* The generators that read one kernel are run against `de440s.bsp`. `inter_de_states.py`
  reads all six.
* ⛔ **A directory of data files is the whole input.** The library reads whatever it finds
  there, so a directory holding an unpinned `.se1` file, or none at all, is refused. The
  generators that read in child processes require exactly the three pinned files and nothing
  else.
* The kernel pins are over the publisher's unmodified files, so `sha256sum de440s.bsp`
  reproduces one. `kernels.py` also names the publisher's own MD5 list that each file was
  checked against when it was pinned.
* **The tests look in fixed places**, both git-ignored: `cache/ephe/` for the three data
  files, and `cache/kernels/de440s.bsp`. (`tests/test_convention_grid.py` also honours
  `CONVENTION_GRID_EPHE`.) A test whose files are not there skips and says why.

### Inputs that come from elsewhere

Some generators take inputs this repository does not produce, or does not choose.

* **A data profile manifest** (`--profile`): a TOML file stating the interval a consumer's
  data profile covers. The generators read only this much of it, and record its SHA-256:

  ```toml
  [identity]
  name = "<profile name>"
  version = "<profile version>"

  [[pinned.dataset]]
  logical_id = "<dataset id>"

  [pinned.dataset.declared_coverage]
  start = "YYYY-MM-DDTHH:MM:SS"   # no zone; must convert to a Julian day and back unchanged
  end   = "YYYY-MM-DDTHH:MM:SS"
  scale = "TDB"                   # recorded as given
  ```

  Exactly one dataset. `nutation_obliquity_grid.py` also refuses an interval whose end is not
  a whole number of half days after its start.
* **A geocentric values file** (`--grid-values`, with `--grid-values-sha256`): a values file
  of the shape `r1_geocentric_vectors.py` writes (`service/r1-geocentric-vectors.jsonl`).
  What is read from it is the distinct `jd_tdb` of its rows, each checked against its
  `jd_tdb_bits`. The file is refused unless its digest is the one given.
* **A budget row** (`--budget-row`): the id of the row a consumer compares a file against.
  It is the consumer's, written into the header as given — ⛔ never chosen here — and it is
  refused unless given exactly, with no surrounding space. Six generators take it, and all but
  one require it: `r1_geocentric_vectors.py` has a default. ⚠ Six others take no such argument
  and fix their row in code: `r1_horizons.py`, `r2_kernel_states.py`, `r3_swiss.py`,
  `r5_continuity.py`, `publisher_testpo.py` and `convention_probes.py` (two rows).
* **An empty directory** (`--empty-dir`): the "no data files" condition. It is verified
  empty before and after the run.

---

## Layout

```
generators/              one script per record; each is a recorder
  r1_horizons.py             geometric states from the publisher's live service
  r1_drift.py                whether that service still answers as a fixture says; ⛔ never gates
  r1_of_date_probe.py        one apparent direction as that service prints it in two of-date frames,
                             on one line, under every format; ⛔ derives nothing, and writes nothing
                             inside this tree
  r1_geocentric_vectors.py   geocentric ICRF states in TDB from that service under each of its three
                             vector corrections, every response held to its own statement of them;
                             read live or from the copies it kept; ⛔ derives nothing
  r1_geocentric_drift.py     whether that service still answers a stated sample of that grid's own
                             queries as it recorded; ⛔ never gates
  r2_kernel_states.py        geometric states from a pinned DE kernel, read by two readers
  inter_de_states.py         three fits side by side in their six files, read by two readers; both
                             files of one fit recorded where they share days, ⛔ neither chosen
  publisher_testpo.py        the ephemeris publisher's own test-value set
  r3_swiss.py                the same grid under each ephemeris source, source asserted per row and
                             per body; and the survey of which entry points report
  convention_probes.py       five conventions the library applies without being asked
  convention_grid.py         three conventions read across a grid — the ayanamsha, house cusps by two
                             entry points, rising and setting — one call per process
  mean_node_modes.py         the mean lunar node under every request and both nutation settings, the
                             Moon's word beside its own
  mean_node_section.py       the mean node through calc as a comparison section, read warm, and its
                             three controls at every row
  nutation_obliquity_modes.py    the nutation and obliquity pseudo-body under every request, both
                             words and both entry points, its word beside the Moon's
  nutation_obliquity_grid.py     the same pseudo-body through calc every half day across an
                             interval, under every request at a subset, tied to the modes record
  nutation_obliquity_section.py  the same pseudo-body's first value through calc as a comparison
                             section, every value carried and read, its three controls at every row
  of_date_candidates.py      the frame of date by three implementations of one model set, and the
                             apparent place by two on one kernel; ⛔ a feasibility measurement
  r5_continuity.py           what an earlier implementation answered, before it stops running
  deployment_capture.py      what a deployment's library resolves, captured on its own host;
                             ⛔ imports nothing from here and writes no fixture
  utc_conversion.py          the civil-time conversion read on the universal value a caller keeps;
                             ⛔ imports nothing from here and writes no fixture
  probe6b_ffi.py             what crossing into the ephemeris binding costs, as ratios
  r6_karaka_rules.py         what two located copies state, rule by rule, and a rule neither states
  r6_reduction_fork.py       a rule one chapter disagrees with its own illustrations about
  r6_reduction_example.py    a source's own worked figures, reproduced from what it printed
  native/supernovas_of_date.c    the C driver of_date_candidates.py builds for one candidate
src/saakshi/             the shared library (five generators import none of it, by design)
  fixture.py                 the fixture contract, fail-closed, five discriminated kinds
  provenance.py              generator identity; ⛔ refuses to stamp a dirty tree
  acquisition.py             retrieval as evidence; ⛔ a cache read is not an acquisition
  service.py                 what a service response is made of; ⛔ a resource is not its payload
  kernels.py                 the kernel pins, and a file checked against its pin by size and SHA-256
  swiss.py                   which ephemeris actually answered; ⛔ refuses to attribute a value
  conventions.py             the conventions a value carries without saying so, read by asking
  civil.py                   resolved instants and coordinates; ⛔ refuses a half-resolved row
  leaves.py                  flatten a returned object to addressed leaves
  surface.py                 a sampled engine's call surface, declared as local data
  timing.py                  a timing ladder and its controls; ⛔ publishes ratios, never durations
  textual.py                 the locus discipline; ⛔ a citation that does not resolve is refused
  texts.py                   the copies a locus resolves into; ⛔ presence of a script is not fidelity
tests/                   the contract's refusals and the generators' own checks; the half that
                         calls an ephemeris library skips where it is absent
tools/check_public_tree.py   the leak check run before a push
config/                  the committed *.example files; their filled-in copies are local, git-ignored
docs/                    the fixture contract, and the measurements taken here
.github/workflows/ci.yml what continuous integration runs
out/                     generated fixtures (git-ignored; they are consumed elsewhere)
cache/                   acquired material, and the data files the tests read (git-ignored)
```

A generator's `r1_`…`r6_` prefix names the reference its values are recorded under. The
references are `R1` (the ephemeris publisher's service and development ephemerides), `R2` (the
SPICE Toolkit, with an independent pure-Python cross-check), `R3` (the Swiss Ephemeris), `R5`
(the predecessor engine, for continuity only) and `R6` (textual authority). The full registry is
in `src/saakshi/fixture.py`. A generator without a prefix names its reference in its own header.
Drift reports and acquisition records are filed under `instrument`, a harness with no authority
of its own. The contract they all write to is [`docs/fixture-contract.md`](docs/fixture-contract.md).

## Running a generator

⛔ **Commit first, then generate.** Every generator that writes a fixture refuses to run against
a dirty or commitless working tree, because `generator.commit` in the provenance block would
otherwise name a state that does not exist. *Dirty* includes an untracked file that is not
git-ignored. ⛔ No flag overrides this, hidden or otherwise: a dirty tree stamped like a clean one
is a provenance field that looks discharged and is not. Three cases write nothing a commit could
be wrong about, so they are not checked: `deployment_capture.py` and `utc_conversion.py`, which
print an observation and write no fixture, and `r1_geocentric_vectors.py --plan-only`, which
sends and writes nothing.

Every command runs from the repository root, in the environment set up in *Install*.

```bash
python generators/r2_kernel_states.py --kernel <path to de440s.bsp> --out out/
python generators/inter_de_states.py --kernels <the directory of the six pinned files> \
    --kernel-terms <the publisher's terms page, as read> --grid-values <a geocentric values file> \
    --grid-values-sha256 <its digest> --budget-row <the consumer's row id> --out <a new directory>
python generators/publisher_testpo.py --kernel <path to de440s.bsp> --out out/
python generators/r1_horizons.py --kernel <path to de440s.bsp> --out out/
python generators/r1_of_date_probe.py --profile <a data profile manifest> \
    --cache <a directory outside this tree> --out <a file outside this tree>
python generators/r1_geocentric_vectors.py --profile <a data profile manifest> \
    --kernel <path to de440s.bsp> --out out/ [--plan-only | --from-cache]
python generators/r3_swiss.py --ephe-path <directory of .se1 files> --out out/
python generators/convention_probes.py --ephe-path <directory of .se1 files> --out out/
python generators/convention_grid.py --ephe-path <directory of .se1 files> \
    --grid-values <a geocentric values file> --grid-values-sha256 <its digest> \
    --budget-row <the consumer's row id> --out <a new directory> [--workers N]
python generators/mean_node_modes.py --ephe-path <directory of .se1 files> \
    --empty-dir <an empty directory> --profile <a data profile manifest> \
    --out out/mean-node-modes.jsonl
python generators/mean_node_section.py --ephe-path <directory of .se1 files> \
    --empty-dir <an empty directory> --profile <a data profile manifest> \
    --survey out/swiss/r3-flag-reporting.jsonl --budget-row <the consumer's row id> \
    --out-dir out/mean-node-section/
python generators/nutation_obliquity_modes.py --ephe-path <directory of .se1 files> \
    --empty-dir <an empty directory> --profile <a data profile manifest> \
    --out out/nutation-obliquity-modes.jsonl
python generators/nutation_obliquity_grid.py --ephe-path <directory of .se1 files> \
    --empty-dir <an empty directory> --profile <a data profile manifest> \
    --modes-record out/nutation-obliquity-modes.jsonl --out out/nutation-obliquity-grid.jsonl
python generators/nutation_obliquity_section.py --ephe-path <directory of .se1 files> \
    --empty-dir <an empty directory> --profile <a data profile manifest> \
    --survey out/swiss/r3-flag-reporting.jsonl --budget-row <the consumer's row id> \
    --out-dir out/nutation-obliquity-section/
python generators/probe6b_ffi.py --ephe-path <directory of .se1 files> --out out/
python generators/utc_conversion.py [--ephe-path <directory of .se1 files>] [--full] > observation.txt

python generators/r6_karaka_rules.py --acquire --out out/
python generators/r6_reduction_fork.py --acquire --out out/
python generators/r6_reduction_example.py --out out/     # reads the copy the line above acquired
```

`of_date_candidates.py`, `r5_continuity.py`, `deployment_capture.py` and the two drift jobs
are shown in their own sections below.

**Order.** Some generators read what another one wrote:

* `r3_swiss.py` writes the survey (`out/swiss/r3-flag-reporting.jsonl`) that
  `mean_node_section.py` and `nutation_obliquity_section.py` take as `--survey`;
* `nutation_obliquity_modes.py` writes the record that `nutation_obliquity_grid.py` takes as
  `--modes-record`;
* `r1_geocentric_vectors.py` writes the values file that `inter_de_states.py`,
  `convention_grid.py` and `of_date_candidates.py` take as `--grid-values`;
* `r1_horizons.py` writes what `r1_drift.py` watches, and `r1_geocentric_vectors.py` writes what
  `r1_geocentric_drift.py` watches;
* `r6_reduction_fork.py --acquire` fetches the copy `r6_reduction_example.py` reads.

`--kernel-terms` is a saved copy of the kernel publisher's terms page, as named in
`inter_de_states.py`. It is refused unless its SHA-256 is the one pinned there.

⚠ **The `r6_*` generators separate acquiring a text from citing it.** `--acquire` goes to the
network and writes the retrieval beside the copy; every later run reads what is on disk and
refuses to fetch. ⛔ A generator that acquired at emit time would stamp today's date on a
copy obtained months ago, and would need the network to reproduce its own output.

⚠ **`probe6b_ffi.py` takes one path, and records none.** `--ephe-path` is handed only to the
child process that attests which ephemeris answered the position rung; the timing process
itself sets no data-file path. The record carries the interpreter, the binding, the library
version and the platform, and ⛔ never a filesystem path. A path describes the machine that
ran the recorder rather than the subject, and the writer refuses one in any value of any
fixture.

⚠ **`publisher_testpo.py` needs the network on every run, and there is no offline path.**
Beside the value fixture it writes an *acquisition record* attesting where the published
test file came from, and ⛔ a cache read is not an acquisition — returning cached bytes and
stamping today's date on them produces a record that is false in the one field it exists to
establish. A retained copy is used as a **second** observation to check the first against;
if the two disagree the run is refused, because one address having served two artifacts is
not something a recorder may resolve on its own.

## Running the tests

```bash
python -m pytest -q -rs                             # -rs prints the reason for every skip
ORACLE_LIBRARIES=present python -m pytest -q -rs    # declare what you expect; a run that disagrees is refused
```

The suite has two halves. One exercises the fixture contract and needs only Python, `pytest`,
`tzdata` and git. The other calls the ephemeris libraries and the pinned data files, and wherever
they are absent it skips and says so:

* without `pyswisseph`, every test that calls the library skips; the report header says
  `oracle libraries: ABSENT`, and the summary repeats it as a **reduced run**;
* without `spiceypy`, `jplephem` or `numpy`, the tests of the kernel and service readers that
  need them skip;
* without `tzdata`, a civil-time test skips;
* without the three data files in `cache/ephe/`, or `de440s.bsp` in `cache/kernels/`, the
  end-to-end runs that read them skip.

⚠ `ORACLE_LIBRARIES` (`absent` or `present`) is checked against the four oracle modules the
tests skip without: `swisseph`, `spiceypy`, `jplephem` and `numpy`. `present` means all four,
`absent` means none, and an environment holding some of them is `partial`, which both
declarations refuse. `tzdata` is not among them, so a run declared either way can still skip a
civil-time test, and `-rs` is what shows it.

Several tests commit a temporary copy of the tree and run a generator in it, so a generator's
refusals are tested by running the generator, not by reading it.

## What continuous integration proves, and what it does not

`.github/workflows/ci.yml` runs on every push to `main` and on every pull request, on Ubuntu with
Python 3.12. It installs **only** `pytest` and `tzdata`, and deliberately not `requirements.txt`,
so that a green run can only mean *the schema is sound*, never *the oracles happened to be
installed*. It has three steps:

1. the suite, with `ORACLE_LIBRARIES=absent` declared: the contract half runs, the oracle half
   skips, and the run is refused if an ephemeris library is ever present;
2. `python tools/check_public_tree.py --self-test`: the leak check's matcher, run with no name
   list;
3. an assertion that, with no local `config/reserved-names.txt`, the reserved-name tooling still
   holds its built-in default and says the check is reduced.

⛔ **It proves nothing else.** It calls no ephemeris library, sends no request, downloads no data
file, runs no generator and checks no fixture for regeneration. Because the names are private,
it scans for no reserved name. Nothing mechanical checks rule 2 anywhere. Those things are
checked by a person, on a machine that holds the libraries and the data.

## Before pushing

```bash
python -m pytest -q -rs                  # the contract's refusals, and whatever this machine can run of the rest
python tools/check_public_tree.py        # no reserved name or internal identifier reaches a commit, or waits to
```

⚠ The second needs `config/reserved-names.txt`, and exits non-zero when it is missing rather
than passing on an empty list. It proves its own matcher first (`--self-test`). It then looks,
case-insensitively, for every reserved name except this repository's own, and for three
identifier shapes: `adr-` or `rfc-` followed by a digit, and a section sign followed by a
digit. It looks in:

* every tracked file at HEAD, and **every reachable commit**, because a name removed in a later
  commit is still published by the earlier one;
* ⭐ **the working tree**: every path, tracked or not, **ignored or not**, and the contents of
  every file git reads as text (binary files are skipped). A name that is only on disk has not
  been published, so deleting the path is the whole fix. But an untracked path is invisible to
  a scan of commits, and a single `git add -A` publishes it permanently. ⛔ Being git-ignored
  buys a path nothing here, deliberately: ignoring one is how the same failure comes back under
  a different name in a different path.

Two kinds of path are exempt, and every run prints both. The short list of paths that exist *to
hold* private material is exempt entirely: the local name list, the local continuity surface and
`docs/local/`. `cache/` is exempt in its **contents** only, because its acquired third-party
texts were written by their authors; its paths are still scanned.

⚠ It reads file contents, never commit messages, and it knows only the shapes above. It cannot
see another kind of internal identifier, a private path written in prose, or an attribution in
a commit message. Review those by hand.

⚠ **A virtual environment inside the tree is scanned like everything else**, and the
packages in one quote other people's protocol numbers and section signs — 40-odd hits on a
plain test environment, none of them ours. They are not exempted, because an exemption is
how a real leak gets waved through. Keep the environment outside the tree, or move it out for
the run and back afterwards (never while a test suite is running in it).

⭐ The check runs on whatever git is installed. Its identifier patterns are POSIX extended
regular expressions with no backslash escapes, because `\b` and its kin are honoured by
one regex library and ignored by another: the git that ships with macOS ignores `\b`, and
on it the earlier patterns matched nothing, so the self-test refused every run there.
`--self-test` now refuses any such escape before it asks git anything.

---

## What each generator records

### Sampling a service, where the resource is not the response

⛔ **A published file can be fetched again byte-identically. A service cannot.** Its response
is a *rendering*, carrying material that exists because a request happened rather than
because an answer did — and byte-for-byte reproducibility is a write-time guarantee here.

⚠ This is sharper than it sounds. The *"one address has served two different artifacts"*
refusal above, pointed at a service that has not changed, fires on the **second** request every
time. So the fix is not to weaken the refusal. It is to say what the **resource** is, and let
the digest, the cache and the refusal all run over that.

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
python generators/r1_geocentric_drift.py --values out/service/r1-geocentric-vectors.jsonl --out out/ \
    [--sample first_chunk|all]
```

The geocentric grid's three corrections, what each response stated about them, the service's
silent truncation of a long time list, and the drift control's first run are in
`docs/measurements/2026-11-21-three-corrections-from-the-geocentre.md`.

⛔ **It detects and proposes. It never gates.** It exits 0 on every outcome of the comparison,
adopts no band and edits no fixture. (Like every generator that writes a fixture, it is refused
on a dirty tree before it asks anything.) A job that failed a build the day a public service
updated a data file is a job somebody switches off, and the fixture it would have failed is
still exactly good evidence of what the service said when it was asked.

⭐ The finding it exists for is the one the numbers cannot show: a response whose values are
unchanged and whose **solution identifier** has moved. The rows still verify, and they are a
different claim. See `docs/measurements/2026-08-04-service-sampling.md`.

### One direction, two frames of date, three implementations

`r1_of_date_probe.py` asks the publisher's service, from the geocentre, for the apparent
direction of a few bodies at a few instants in two of-date frames on one line of one response.
It asks under every angle format and precision the interface offers, and once at the defaults,
and writes what came back character for character. Its request and service-state rules are
the ones `r1_horizons.py` reads through (`src/saakshi/service.py`, `src/saakshi/acquisition.py`),
by import, and a service answering otherwise than R1 recorded it is a stop, not a row. ⛔ Its output and its retrieval cache are refused inside this working
tree: the terms under which the service's responses may be redistributed are quoted beside the
readings, and have not been examined here. See
`docs/measurements/2026-11-09-two-frames-on-one-line.md` and
`docs/measurements/2026-11-12-the-same-questions-under-a-newer-file.md`.

`of_date_candidates.py` asks three independently written libraries for the same quantities at
the same instants. The libraries are ERFA (through `pyerfa`), Skyfield, and SuperNOVAS (built
from its source, with the SPICE Toolkit reading the kernel). The quantities are:

* the mean obliquity;
* nutation in longitude and in obliquity;
* the true obliquity, where a library returns one;
* the bias-precession-nutation matrix;
* the geocentric apparent place of date on `de440s`, Skyfield against SuperNOVAS;
* ERFA's IAU 1980 mean obliquity beside its IAU 2006 one.

The instants are a sweep of 20 001 across DE440's span, the distinct instants of a geocentric
values file, and one civil instant converted through ERFA's own entry points. It writes each
library's own return with its bit pattern, and the pairwise differences beside them. A
conversion into arcseconds is the one arithmetic applied before a difference, and both forms
are written.

* ⛔ **A feasibility measurement, not a reference.** No band, no class but `reference_only`, no
  verdict. The file carries `reference: none` with a `contract_deviation` naming the gap: the
  registry has no value for an independent implementation of these models, and which candidate,
  if any, may become one is the consumer's decision, not this file's.
* ⚠ **Its libraries are not this repository's requirements.** It needs a dedicated environment
  holding:
  * `pyerfa` 2.0.1.5, `skyfield` 1.55, `jplephem` 2.23 and `numpy` 2.5.1;
  * the SuperNOVAS 1.8.0 source, its release tarball, the built static archive, and that
    build's JSON record naming the archive by SHA-256. ⚠ Nothing in this tree writes the
    record: it is made where the library is built. The generator requires two of its fields,
    `archive_sha256` (the archive's digest, checked) and `sources` (each source file's name
    mapped to its SHA-256), and carries every other field into the record as it stands;
  * the CSPICE toolkit N0067 and its package;
  * ERFA's licence text;
  * a C compiler on the path as `cc`, which builds `generators/native/supernovas_of_date.c`.

  Every version, archive and licence text is pinned in the generator, and anything else is
  refused before a value is read.

```bash
<python> generators/of_date_candidates.py --kernel <path to de440s.bsp> \
    --grid-values <a geocentric values file> --grid-values-sha256 <its digest> \
    --supernovas-source <dir> --supernovas-tarball <file> --supernovas-archive <file> \
    --supernovas-build-record <file> --cspice-toolkit <dir> --cspice-package <file> \
    --erfa-licence <file> --budget-row <the consumer's row id> --out <a new directory>
```

### Asking what a library assumes when nobody says

`convention_probes.py` asks five questions whose answers a caller inherits without passing
anything:

* the offset applied to reach the dynamical time scale;
* what a default position already has applied to it;
* **which atmosphere a rise/set call uses when both atmospheric arguments are zero**;
* which leap seconds the conversion knows, and where its table ends;
* which house methods refuse above the polar circle.

⭐ **Two of the five answers are the opposite of the assumption a careful caller would
make**, so each is established by interrogation rather than by reading documentation. The
decisive one is settled as a **bit-identity** between a call that passes nothing and a call
that states an atmosphere explicitly, rather than as an approximate agreement. See
`docs/measurements/2026-08-04-conventions.md`.

### The same conventions, across a grid

`convention_grid.py` reads three conventions across a stated grid. Every reading is one call in
its own fresh `-I` interpreter, admitted only if the calls that child made into the library —
recorded inside it, with the arguments it received — are exactly the ones its row declares. So
the library's process-wide state cannot carry from one reading to the next. It writes three
files:

* `convention-ayanamsha.jsonl` covers eleven sidereal modes: three defined by a reference epoch,
  and eight anchored to a star or to the galactic centre, with no star catalogue anywhere on the
  path. For each it records the value the entry point without a flag returns, the value the
  entry point with a flag returns with and without the no-nutation bit, and the tropical and
  sidereal longitudes of the Sun and the Moon with and without that bit.
* `convention-houses.jsonl` covers twenty-one house methods at ten sites, five of them at high
  latitude. It records the cusps of the entry point that takes an instant, tropical and under
  three sidereal modes, beside the cusps of the entry point that takes a sidereal angle and an
  obliquity, with the inputs read at the same instant.
* `convention-rise-set.jsonl` covers the Sun and the Moon at the same ten sites on every day of
  a year. It records the disc-centre rise and set under a stated atmosphere, beside the library's
  other disc definitions and atmospheres, and beside the same call with the atmosphere left to
  the binding's defaults.

Wherever both apply, each is read under two conditions: an empty directory with the analytical
ephemeris requested, and the pinned data files with the data files requested.

* ⛔ **No band, no class but `reference_only`, no verdict.** A difference between two forms is
  recorded as a difference between two conventions, ⛔ not as an error in either.
* ⚠ What the library raises — a method undefined at a latitude, a rise that does not happen —
  is recorded, never refused.
* ⛔ A binding or library other than the pinned version, and a data directory other than
  exactly the three pinned files, are refused before any reading.

### Asking which ephemeris answered

⛔ **An ephemeris library may substitute a different ephemeris than the one requested —
silently, successfully, and returning an entirely ordinary value.** It does so when the
requested one is unavailable or does not cover the date. So a recorder that writes down
what came back, without establishing where it came from, produces a file that is
well-formed and mislabelled; and a comparison between two such files reports exact zeros,
which reads as agreement and means only that both sides were the same ephemeris.

⚠ **"Assert the returned flag" is necessary and not sufficient.** Measured on the library
this repository records, across the six entry points its survey covers (`ENTRY_POINTS` in
`src/saakshi/swiss.py`):

* **one** reports the ephemeris that answered;
* one returns a flag that is the request handed back — it was observed returning a data-file
  flag with no data file available at all;
* three return no statement of source whatsoever: the house cusps, the rise/set times, and one
  form of the time offset;
* one takes no ephemeris argument at all, and answers anyway.

So `src/saakshi/swiss.py` distinguishes the assertions a recorder can actually make, and every
row records which one it relied on:

* `reported` — the entry point said which ephemeris answered, and it was the one asked for.
* `proxy_window` — it said nothing, so the source was established at **both ends** of the
  interval the call may read, using an entry point that does report. ⚠ Bounded, not sound,
  and weaker than a report; rows say so rather than presenting the two as equivalent.
* `none` — a refusal, for a quantity **no ephemeris answers**. The time offset is not read from
  an ephemeris at all; what one contributes enters only through a library state (the
  tidal-acceleration constant), which every such row reads back instead. ⛔ It is not a weaker
  proxy: a position call under the same flag answers a different quantity, so none is asserted.
  Each such section declares its whole configuration (the data directory and every process-wide
  state), with one entry point under one request per section. The one section classified for
  comparison has its two controls in a provenance record of their own: forcing the state to
  another constant moves the value, and regenerating the section under other call histories
  does not.

⭐ **A row whose source cannot be established is not written.** It is listed in the header
as a substitution. That exclusion is the mechanism: it is what keeps an uncovered epoch
from contributing a zero that would read as agreement.

⛔ **And a reporting entry point does not report for every body.** Under every condition
built so that the requested source cannot answer — a verified-empty directory, a JPL request
with no JPL file, an instant outside the body's own coverage edge — every body's returned word
named the source that did answer, except the mean lunar node's and the nutation and obliquity
pseudo-body's, which handed the request back. So a flag is read as a report only per body and
per word. The survey reads each body under each condition, each reading the one call of a fresh
process, and writes each body's edge as adjacent bits for the words its readings use (one body's
edge moves with the speed bit). A value row of a body not shown reporting under its own word is
recorded as unattested and not written.

⚠ **A reader of words can only read the words somebody asked for.** A consumer that looks a
returned word up through the words readings *requested*, never decoding its bits, could not read
the analytical source's word when no reading had requested it. It refused every body under every
key over it, including one it had admitted before. This was measured before anything was
emitted. The survey now reads the analytical request beside each body's conditions, and refuses
readings that return a word none of them requested. See
`docs/measurements/2026-08-04-ephemeris-substitution.md` and
`docs/measurements/2026-10-31-the-word-nobody-requested.md`.

### The mean node under every request

`mean_node_modes.py` reads the library's mean lunar node black-box, every reading the one call
of a fresh child process, in five parts:

* **mode_invariance** — `calc` on a dynamical-time Julian day under five configurations, each
  with the library's default nutation and with `FLG_NONUT`, at every epoch. The configurations
  are the analytical, the data-file and the JPL request, with the pinned data files on the path
  and with a verified-empty directory, and the JPL request with no JPL file anywhere;
* **cause** — the tidal-acceleration constant forced to two library-named values before the
  call, and read back after;
* **universal_time** — at seven epochs, `calc_ut`, the library's time offset under the same
  ephemeris bits, and `calc` at the universal day plus that offset;
* **universal_time_cause** — the same forcing, through `calc_ut`;
* **returned_flag_by_body** — seven conditions, five of them built so the requested ephemeris
  cannot answer, and the returned word of the Moon and of the node through both entry points.

⛔ **The record is refused unless the Moon reports the substitution exactly where one was
built**, because a reader that cannot see a substitution reads an echo as agreement. It is
refused, too, when a `FLG_NONUT` request moved no reading, and when any child's recorded calls
into the library are not exactly the ones its row declares.

The interval's ends are a data profile manifest's declared coverage. The instants where the node
passes 0°/360° are located with the published IERS Conventions (2010) Eq. (5.43) row for the
fifth Delaunay argument, used to find those instants and for nothing else. The record is one
`provenance_record` under R3, written with the standard library and the binding alone.

### A convention value that does not move with the request

`mean_node_section.py` writes a comparison section whose rows assert `none` and are meant to be
compared anyway: the mean lunar node through `calc`, under the data-file
request with the whole word, `FLG_NONUT` included. Its claim is not about which source answered
— the node's word cannot say — but that the value **did not move with the request**. Three
controls committed beside it carry that claim, at **every** row:

* ① **invariance** — the node under five configurations of request and directory, each reading
  the only call of a fresh process, bit-identical to the row. Beside it is a **witness**: the
  Moon at the same instant under the same five, whose word reports where the request cannot
  answer, whose value differs between two answering sources, and which the section's own request
  answers;
* ② **sufficiency** — the section, read warm, read again warm in the reverse order. ⛔ Never
  cold: a cold reading under the section's configuration is already ①'s, and would repeat it;
* ③ **a nutation twin** — the row without `FLG_NONUT`, which must differ.

Every control is checked before either file is written, each part held to exactly the section's
own epochs and instants. ⚠ The section is classified `tolerance` with the band this instrument
measured between a row and every other reading of it — none — and that band is context: the band
a comparison applies is its consumer's.

⭐ Every row carries its own unit, `degree`. A consumer reads a row's unit from the row, ⛔ never
from the classification beside it, so the section refuses to be written with a row that carries
no unit or another spelling of it. The header names the row its consumer compares the section
against. That id is the consumer's, fixed in the generator, ⛔ never chosen here. See
`docs/measurements/2026-11-01-a-unit-beside-the-rows.md`.

### A body that is not a body

The library returns its obliquity of the ecliptic and its nutation through the same call as a
position, for a body number of its own. `nutation_obliquity_modes.py` reads that pseudo-body the
way `mean_node_modes.py` read the node: five configurations of request and directory, both
words, through `calc` and `calc_ut`, every reading the one call of a fresh process, and the
Moon's word beside its own under every condition built so that the request cannot answer.

* ⛔ **Its word hands the request back**, in every reading, whatever answered — as the mean
  node's does. So the survey reads it as well, and a reader of the survey sees it echo.
* ⭐ **Through `calc` its six values did not move** with the request or the directory, at any
  instant read, including the ones outside every data file. Through `calc_ut` they moved at
  three instants of seven, and were bit-identical to `calc` at the universal day plus the offset
  every time.
* ⚠ **Every value is written, and the first three twice.** A consumer reads a reading's first
  three returned values under three fixed names, whatever the body. The record writes them
  there, held bit for bit to the positions, so that consumer can see a value move. ⛔ Those names
  are not what the values are, and the fourth is in none of them.

See `docs/measurements/2026-11-02-a-second-word-that-hands-the-request-back.md`.

### The same body, every half day

`nutation_obliquity_grid.py` reads the same pseudo-body through `calc` every half day across a
data profile's interval, under the data-file request with the pinned files and the default word.
For the interval it was first run on, that is 219 205 instants, each reading the one call of a
fresh process. At a stated subset of those instants it reads the body again under all five
configurations and both words.

* ⭐ **The reading is the modes record's, by import.** Its child program, its admission rule, its
  epochs, its directory checks and its pins are all that generator's. Nothing about a reading is
  written twice, and its children run several at once, each its own process.
* ⭐ **Half a day, so that no term hides between samples.** Under the published convention that a
  nutation model holds terms of periods over two days, half a day reads every such term more than
  four times per period. A daily step would read a two-day term twice, possibly at its zeros, and
  would miss J2000, which falls at noon. ⛔ The step is chosen against the convention, not against
  the library.
* ⛔ **Four findings refuse the record rather than being written into it**:
  * a returned word other than the request;
  * six values that move across configurations at a subset instant;
  * a reading at the modes record's instants that is not that record's, bit for bit;
  * a broken clause of the relation that record measured for the nutation-off word.
* ⚠ **The library's models are quoted, not read.** Its documentation is quoted for its
  precession, obliquity and nutation models, by address, day and digest, ⛔ not reconciled where
  it names more than one. The binding offers no way to read or set the models in force, so none
  was read.

See `docs/measurements/2026-11-03-a-step-chosen-against-the-convention.md`.

### One value compared, six carried

`nutation_obliquity_section.py` writes the pseudo-body as a comparison section in the mean node's
section's shape, by import of that generator. It takes that generator's rows, child
program, admission rule, directories and configuration identity, and the controls a section of
that shape keeps whatever its body and word. What differs is the word, and what a row carries:

* ⭐ **The data-file request without `FLG_NONUT`.** Its configuration renders the identity its
  consumer names, and the section refuses to be written under any other.
* ⭐ **One value compared, six carried.** Each row compares the call's first returned value and
  carries all six beside it, nested, so that nothing compares the others. Every reading of the
  pseudo-body in the controls carries all six as well, and the first three again under the names
  a reading's first three are read by.
* ⛔ **The controls read every position, at every row:**
  * ① each configuration's six values must be bit-identical to the row's, with the Moon as the
    witness;
  * ② the section read again warm in another order must match six of six;
  * ③ the twin with `FLG_NONUT` added must have a first value that differs from the row's, and
    that equals both its own second value and the row's second.
* ⚠ Where the row's first value and its twin's agree to the bit, the twin control refuses the row.
  The instants are the mean node's section's, not chosen against that. How far apart the two were
  at the closest row is measured and written into the record.
* ⚠ The band in its classification is its consumer's, declared as it asked, ⛔ not a measurement.
  The row id is a parameter: it is the consumer's, ⛔ never chosen here.

The survey now writes every returned value on the pseudo-body's readings too, and on no other
body's: a reader that reads every position of that body's readings would otherwise hold only
three of them.

See `docs/measurements/2026-11-14-one-value-compared-six-carried.md`.

### The returned values as patterns alone

Each row's `returned_values` is written as `values_bits` alone — the six bit patterns, with no
decimals beside them — because the reader of that object takes it with that one member and
refuses a second. ⭐ The fixture contract states the one exemption from its pairing rule that this
needs: that key, in a row's own `returned_values`, and nowhere else. The patterns are still
checked as patterns. See `docs/measurements/2026-11-15-the-returned-values-as-patterns-alone.md`.

### Sampling an engine for continuity

One generator is different in kind: `r5_continuity.py` samples a *running implementation*
rather than a data file, so that its answers survive it being switched off.

```bash
cp config/predecessor-surface.toml.example config/predecessor-surface.toml   # then fill in

PYTHONTZPATH= python generators/r5_continuity.py --natives 64 --report-only   # the write's checks, nothing written
PYTHONTZPATH= python generators/r5_continuity.py --natives 64 --out out/
```

⚠ Run it with an interpreter that can **import the tree being sampled** — that tree's own
dependencies are not this repository's and never will be — and that also holds `tzdata`. ⛔ The
sampled tree must itself be a clean git working tree, because its commit is recorded beside the
values. `--surface` names a declaration other than `config/predecessor-surface.toml`.

⭐ `--report-only` is a prediction of the write. It runs every check the writer makes —
filename, header, classification coverage, every row — over the exact bytes a write would
produce, prints their size and sha256, and exits non-zero exactly where the write would be
refused. On a dirty tree it is refused as the write is, after pricing the grid. It builds no
stand-in identity, and nothing is stamped either way.

⛔ `PYTHONTZPATH=` (set, and empty) is required, and a run without it is refused before
anything resolves a zone. `zoneinfo` consults every directory on its search path before the
packaged rules and never says which answered. The sampled implementation resolves zones inside
its own calls, so the rule set has to be fixed for the whole process before it starts. With the
path empty, only the installed `tzdata` wheel can answer, and the header records which release.

⭐ **Why this one has a deadline and the others do not.** A kernel or a published table can
be read again next year. An implementation cannot be sampled once it stops running, and
nobody gets to ask it a new question afterwards. Everything the recorder can turn into a
number now, it does: each row carries the **resolved UTC offset** beside the local clock
reading and the **resolved coordinate** instead of a place name, so reading the corpus later
needs no timezone database, no place-name service, and nothing switched back on.

⛔ Every such fixture is `reference_only`. What an implementation answered is evidence about
that implementation — never about the sky, and never a tolerance anyone may adopt without
measuring it themselves. See `docs/measurements/2026-08-04-continuity-recorder.md`.

### Capturing a deployment, where the instrument is not installed

`deployment_capture.py` is the one generator that runs **somewhere else**: on the host whose
deployment it records, where this repository is not installed and must never be. So it imports
nothing from here — the standard library and the binding only, which a test asserts. It prints
one JSON document and that document's SHA-256 on a second line, and writes nothing but a
temporary directory it removes. A fixture is made from the observation afterwards, here.

```bash
python deployment_capture.py > observation.txt          # on the host; bring both lines back
python deployment_capture.py --full > observation.txt   # every bit pattern of the leap grid as well
```

* ⛔ **A reported data-file path is not resolution.** Measured here: with no data file on the
  default path, a position call that requests one returns the analytical flag, and a file path
  is still reported afterwards — a path that does not exist. The returned flag decides; every
  reported path is checked on disk, and every file found is hashed.
* ⚠ **The compiled default-path constant is not the list searched.** Measured here, a refusal
  names a different one. Both are listed, with every data file and leap-second file in them.
* ⭐ **The leap table is answered as a difference**: the deployment's default state against the
  same build pointed at an empty directory, both returned values bit for bit at every half-year
  boundary from 1972, each state in a fresh process. A planted table is the control that must
  show up as one.
* ⛔ **The environment is read through an allowlist** — `SE_` names and the host's commit
  variable. A serving process's environment holds credentials.

### The conversion a caller keeps

`utc_conversion.py` reads the library's civil-to-dynamical conversion on the value a caller may
keep alone — the **universal** Julian day. It records both returned values on every reading,
because the two differ by the library's time offset, and only a record of both can separate a
leap step from a change in that offset or in library state. Five parts, each called the way that
caller calls it:

* **state** — the same 115-instant grid as `deployment_capture.py`, and eight instants across
  eras, under up to six recorded library states;
* **steps** — a one-day bracket at every 1 January and 1 July from 1961 to 2060;
* **end** — the day the dynamical value stops holding the table's last offset, located by
  bisection;
* **second_sixty** — 23:59:59, 23:59:60 and the next 00:00:00, on the day before every
  whole-second step found and on six days without one;
* **override** — one file of the documented name holding one invented insertion, in three
  placements.

⛔ Every reading set is taken in a fresh child process, with every `SE_` environment variable
removed, and the removal is recorded. Like `deployment_capture.py`, it imports nothing from here,
prints one JSON line and a line carrying its SHA-256, and writes nothing but temporary
directories it removes. `--ephe-path` adds the pinned-data-files state to part 1; `--full` adds
every bit pattern of parts 1 and 2.

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

### Corroborating a rule, where a second copy is a different kind of object

⛔ **A rule resolved against one edition is *resolved*, not *corroborated*** — and the fix is
not to run the same search over another file. A different translator, in a different
language, does not print the first one's sentence, so each copy carries **its own locus and
its own fragment**, and what is compared is what each copy *states*.

⭐ Doing this once produced three findings worth stating in general:

* **Agreement across languages is a stronger claim than agreement across printings.** All five
  rules are stated by both copies. ⚠ Two of them are the first copy's translator's *notes*,
  which a second edition was expected to be unable to speak to at all. It establishes that a
  rule is attested by two commentators — ⛔ never that the first translator's note says what
  was recorded, which only another copy of *that* translation could witness.
* ⛔ **A different reason found is not the absence of the reason you were looking for.** The
  ascending node's rule was first published from this file as a *fork*: the second copy, it was
  read, gave the rule only at a later, narrower determination. That copy states the rule where
  the series is founded, two paragraphs below the passage the reading was formed from. The fork
  is withdrawn by a row rather than by a silent edit, and a fork is now refused at write time
  unless its absence half has been measured over a bounded passage. See
  `docs/measurements/2026-08-16-the-fork-that-was-not-there.md`.
* ⭐⭐ **Presence of a script is not fidelity of a script.** A copy carrying the original in
  quantity makes a presence check answer *yes* while its machine reading has damaged the very
  lines a primary locus would quote. `passage_fidelity` asks the second question, and asks it
  **internally**: the copy's own commentary names a word as occurring in a passage, and the
  rendered passage either contains it or does not. ⛔ Supplying a "correct" wording from
  outside would be the unsourced claim this whole discipline refuses.

⛔ **And an extent is a lower bound unless something establishes the alphabet is complete.**
Three detectors over one copy's boundary markers found 9, 10 and 12 divisions; the union is
14, and every miss was a different corruption of the same printed sentence. ⚠ Reported from
the first detector alone, *"six divisions not found"* would have been published as a fact
about the book when it was a fact about a regular expression — so no absence is measured over
that copy at all. See `docs/measurements/2026-08-15-second-witness.md`.

⛔⛔⛔ **AND A COPY THAT WAS READ IN THE WRONG ALPHABET IS MORE DANGEROUS THAN A COPY THAT WAS
NEVER READ.** A blank copy fails every check that asks whether anything was read. A scan of
an English printing whose machine reading was set to an Indic script carries **246 777
searchable characters and not one Latin letter**: it passes all of them, and returns zero for
every English word in the book.

⭐ **The guard that was supposed to catch this does not.** An absence here requires a
*positive control* — words the copy is expected to contain, resolving **exactly once**. In a
rendering of noise nothing repeats, so every candidate fragment resolves exactly once —
measured, 1 188 of 1 188 (`discrimination_of_resolving_once` in `src/saakshi/textual.py`). The
hardest-looking condition in the instrument becomes the easiest to satisfy, and a control
quoted from the copy's own noise is free. ⇒ A rendering must now carry the script the alphabet
is written in, and a control must be written in that same script.

⭐⭐⭐ **The next guard was that language repeats and noise does not** — the share of a copy's
own distinct twelve-character fragments that occur more than once, over the whole rendering.
The machine reading that returned noise recurs at **0.00018**, and the least legible real
reading then held at **0.068**.

⛔⛔⛔ **Measured further, no value of that share separates the two.** Over sixty-one copies,
the floor (`LEAST_RECURRENCE`, 0.01) refuses whole real books and accepts readings made in the
wrong script. The largest of those is an encyclopaedia read in a script it is not printed in,
which clears the floor three times over. So clearing it is recorded as a **measurement, not a
certificate**, and every row it travels on says what it does not establish. Below **7 686**
characters (`LEAST_EXTENT_A_REFUSAL_DISCRIMINATES_AT`) a refusal names the extent rather than
the language. The earlier figure of 6 000 came from tiling each copy at one phase, which
covers every character and almost none of the windows. See
`docs/measurements/2026-08-20-a-floor-that-refuses-real-books.md`,
`docs/measurements/2026-08-20-the-word-complete-was-true-of-the-wrong-noun.md` and
`docs/measurements/2026-08-21-the-floor-that-accepts-noise-too.md`.

⭐ **The candidate that replaces it asks for a presence, not a share**: the commonest words of
the language a locus declares (`COMMONEST_WORDS`, fixed before any copy was measured), found at
the passage the locus resolves in. A reader can destroy the evidence of a presence but cannot
manufacture it. Its answer is one of three:

* *attested*;
* *cannot attest* — an abstention, ⛔ never a diagnosis of the copy;
* *cannot measure* — a language no list covers.

See `docs/measurements/2026-08-22-a-refusing-instrument-made-of-presences.md`.

⚠ **The bucket that measures a script had to be defined over letters, and that is not
tidiness.** As a bare code-point range it reported **6 077 Latin characters in the copy that
contains no Latin letter** — braces, brackets and signs that live inside the block — so the
guard built to catch that copy passed it. See
`docs/measurements/2026-08-18-the-candidate-that-named-the-hand.md`.

### Acquired data

Data files are **never committed here**, and nothing is fetched from an address the code does
not name. A file that was acquired is identified by its digest, and the retrieval itself — the
address asked for, the address that answered, the status and the digest — is written down
beside it (`src/saakshi/acquisition.py`).

⭐ Every request this repository sends names its client the same way:
`saakshi/0.1 (+https://github.com/insculptor/Saakshi)`. That is the product, its version and a
public contact, as the publisher's API Fair Use Policy asks of automated clients. There is no
per-call override, and every acquisition record writes the string down. ⛔ No email address and
no person's name goes into it.
