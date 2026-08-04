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
  r2_kernel_states.py    geometric states from a pinned DE kernel, read twice
  publisher_testpo.py    the ephemeris publisher's own test-value set
src/saakshi/         the shared library
  fixture.py             the fixture contract, fail-closed, five discriminated kinds
  kernels.py             locate and hash-verify a kernel pinned by digest
  provenance.py          generator identity; ⛔ refuses to stamp a dirty tree
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
```

Data files are **never committed here** and are never fetched from an unpinned location.
A kernel path is supplied on the command line and the file's SHA-256 is checked against a
recorded pin before a single value is read: a content-addressed *name* records what
somebody intended, and anything that can write to the directory can write a wrong file
under a right-looking name.
