"""The fixture contract, implemented fail-closed.

Every file this repository writes carries a provenance block: which reference answered,
which script asked, at which commit, on which date, and the identity of the software or
source that produced the value. This module is the writer's half of that contract.

⛔ **Nothing here is permissive.** A fixture missing a field its `fixture_kind` requires,
carrying a field its kind forbids, or naming an unknown kind or reference is refused *at
write time*, with an error naming the file, the kind and the field. Refusing at read time
would be enough to keep bad evidence out of a comparison; refusing at write time keeps it
out of a commit.

⚠ **One deliberate hole, flagged rather than papered over** — see `REFERENCE_UNBOUND`.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field as dc_field
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

#: The version of *this contract*, recorded in every file it writes.
SCHEMA_VERSION = "1.0.0"

# --------------------------------------------------------------------------------------
# The vocabulary
# --------------------------------------------------------------------------------------

#: The five discriminated kinds. Validation dispatches on the kind rather than carrying a
#: list of exceptions, so a rule-level record can never be mistaken for a number.
FIXTURE_KINDS = frozenset(
    {"numeric_pin", "worked_example", "textual_rule", "textual_fork", "provenance_record"}
)

#: The reference registry. ⛔ Exactly one per fixture — that single-valued field is what
#: stops evidence of one kind being filed as authority of another.
#:
#: =============  ==================================================================
#: ``R1``         the ephemeris publisher's service and development ephemerides
#: ``R2``         the SPICE Toolkit, with an independent pure-Python cross-check
#: ``R3``         the Swiss Ephemeris, committed fixtures only
#: ``R4``         published external values: almanacs, vendor exports, printed tables
#: ``R5``         the predecessor engine, for continuity only
#: ``R6``         textual authority — what an identifiable source text states
#: ``instrument`` a harness with no authority of its own
#: =============  ==================================================================
REFERENCES_CONTRACT = frozenset({"R1", "R2", "R3", "R4", "R5", "R6", "instrument"})

#: ⚠ **A value the contract does not contain, admitted only under protest.**
#:
#: A publisher's own test-value file — its integration checked against its own exported
#: data — is a *self-consistency measurement*, not a comparison against an outside
#: reference. Filing it under `R1` would widen that reference's authority to cover a claim
#: it was never given; but `instrument` is defined as a named harness, which this is not
#: either. ⛔ Writing `instrument` would be a **false statement about origin** in the one
#: block whose entire purpose is to stop false provenance claims.
#:
#: So the honest value is emitted, and every file carrying it must also carry a
#: ``contract_deviation`` block naming the clause it does not satisfy. A consumer will then
#: trip over it and a human will decide, which is the correct outcome for a gap in a
#: contract neither side may quietly widen.
REFERENCE_UNBOUND = "none"

#: The comparison classes a numeric fixture may declare.
CLASSIFICATIONS = frozenset({"exact", "tolerance", "reference_only"})

#: ⛔ Never in a fixture filename, never in a JSON *key*: a permanent identifier must not
#: encode a renameable project name. ✅ Permitted in *values* — `generator.repo` must name
#: this repository, because that is a recorded fact about origin.
#:
#: The list is extended from ``config/reserved-names.txt`` (one name per line, ``#`` for
#: comments), which is deliberately **not committed**: the mechanism belongs in the open,
#: and the names of unreleased consumers do not.
DEFAULT_RESERVED_NAMES: tuple[str, ...] = ("saakshi",)

_KEY_RE = re.compile(r"^[a-z][a-z0-9_]*$")


class FixtureContractError(Exception):
    """Raised when a fixture would violate the contract. ⛔ There is no permissive mode."""


def _fail(where: str, kind: str, field: str, why: str) -> None:
    raise FixtureContractError(f"{where}: fixture_kind={kind!r} field={field!r} — {why}")


def _config_path() -> Path:
    return Path(__file__).resolve().parents[2] / "config" / "reserved-names.txt"


@lru_cache(maxsize=1)
def reserved_names() -> tuple[str, ...]:
    """The names forbidden in fixture keys and filenames, lowercased.

    ⚠ If the local list is absent only the built-in default applies. That is a real
    weakening, so `describe_reserved_names()` says so out loud and every generator prints
    it before writing anything — a check that quietly protects less than you think is
    worse than one that is visibly off.
    """
    names = set(DEFAULT_RESERVED_NAMES)
    path = _config_path()
    if path.is_file():
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.split("#", 1)[0].strip().lower()
            if line:
                names.add(line)
    return tuple(sorted(names))


def describe_reserved_names() -> str:
    loaded = _config_path().is_file()
    count = len(reserved_names())
    if loaded:
        return f"reserved-name check: {count} names in force (local list loaded)"
    return (
        f"reserved-name check: {count} name(s) in force — ⚠ config/reserved-names.txt is "
        "absent, so only the built-in default applies"
    )


# --------------------------------------------------------------------------------------
# Per-kind field law
# --------------------------------------------------------------------------------------

# For each kind: fields the header MUST carry, and fields it MUST NOT.
_REQUIRED: dict[str, tuple[str, ...]] = {
    "numeric_pin": ("classification", "budget_row", "request"),
    "worked_example": ("classification", "locus", "budget_basis", "request"),
    "textual_rule": ("locus",),
    "textual_fork": ("readings",),
    "provenance_record": ("attests", "authority", "record_date"),
}

_FORBIDDEN: dict[str, tuple[str, ...]] = {
    # A number compared against an outside reference has no source text.
    "numeric_pin": ("locus",),
    # ⛔ A number a text resolves proves that we reproduced the text's own example. It
    #    proves nothing about modern accuracy, so it may never be mapped to an
    #    astronomical budget row.
    "worked_example": ("budget_row",),
    # ⛔ A rule is not a number and has no band. Its presence is a load error, not a
    #    tolerated extra — a judgment vocabulary defined for numbers cannot judge prose.
    "textual_rule": ("classification", "budget_row"),
    "textual_fork": ("classification", "budget_row"),
    "provenance_record": ("classification", "locus", "budget_row"),
}

#: Kinds that can only ever carry textual authority.
_R6_ONLY = frozenset({"worked_example", "textual_rule", "textual_fork"})


# --------------------------------------------------------------------------------------
# The header
# --------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Generator:
    """`generator` — repo, script path and commit.

    ⭐ Naming this repository here is *required*, and is the only place its name may appear
    in a fixture. It records origin, never authority.
    """

    repo: str
    script: str
    commit: str
    dirty: bool = False

    def as_json(self) -> dict[str, Any]:
        if self.dirty:
            raise FixtureContractError(
                "generator.commit would name a state that does not exist: the working tree "
                "is dirty. Commit the generator, then generate."
            )
        return {"repo": self.repo, "script": self.script, "commit": self.commit}


@dataclass
class Header:
    """The provenance block, plus the per-kind fields the contract requires."""

    fixture_kind: str
    reference: str
    generator: Generator
    generated: str  # ISO date
    oracle: Mapping[str, Any]  # the per-reference identity object
    # per-kind fields — presence is checked, never assumed
    request: Mapping[str, Any] | None = None
    classification: Mapping[str, Mapping[str, Any]] | None = None
    budget_row: str | None = None
    budget_basis: str | None = None
    locus: Mapping[str, Any] | None = None
    readings: Sequence[Mapping[str, Any]] | None = None
    attests: str | None = None
    authority: Mapping[str, Any] | None = None
    record_date: str | None = None
    # free-form, always permitted
    title: str | None = None
    notes: Sequence[str] = dc_field(default_factory=tuple)
    summary: Mapping[str, Any] | None = None
    row_schema: Mapping[str, str] | None = None
    contract_deviation: Sequence[Mapping[str, str]] | None = None

    def as_json(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "record": "header",
            "schema_version": SCHEMA_VERSION,
            "fixture_kind": self.fixture_kind,
            "reference": self.reference,
            "generator": self.generator.as_json(),
            "generated": self.generated,
            "oracle": dict(self.oracle),
        }
        for name in (
            "title",
            "request",
            "classification",
            "budget_row",
            "budget_basis",
            "locus",
            "readings",
            "attests",
            "authority",
            "record_date",
            "row_schema",
            "summary",
            "contract_deviation",
        ):
            value = getattr(self, name)
            if value is not None:
                out[name] = value
        if self.notes:
            out["notes"] = list(self.notes)
        return out


# --------------------------------------------------------------------------------------
# Validation
# --------------------------------------------------------------------------------------


def validate_header(
    header: Header, *, where: str, reserved: Sequence[str] | None = None
) -> None:
    """Refuse anything the contract refuses. ⛔ No legacy path, no waiver."""
    kind = header.fixture_kind
    if kind not in FIXTURE_KINDS:
        _fail(where, kind, "fixture_kind", f"unknown; must be one of {sorted(FIXTURE_KINDS)}")

    ref = header.reference
    if ref not in REFERENCES_CONTRACT and ref != REFERENCE_UNBOUND:
        _fail(where, kind, "reference", f"unknown; must be one of {sorted(REFERENCES_CONTRACT)}")

    # ⚠ The one hole, and it may never be silent.
    if ref == REFERENCE_UNBOUND and not header.contract_deviation:
        _fail(
            where,
            kind,
            "reference",
            f"{REFERENCE_UNBOUND!r} is not in the reference registry; a fixture using it "
            "must carry a `contract_deviation` block naming the clause it does not satisfy",
        )

    if kind in _R6_ONLY and ref not in ("R6", REFERENCE_UNBOUND):
        _fail(where, kind, "reference", f"kind {kind!r} is R6-only, got {ref!r}")

    for name in _REQUIRED[kind]:
        if getattr(header, name) is None:
            _fail(where, kind, name, "required by this kind and absent")
    for name in _FORBIDDEN[kind]:
        if getattr(header, name) is not None:
            _fail(where, kind, name, "forbidden for this kind; its presence is a load error")

    if header.classification is not None:
        _validate_classification(header.classification, where=where, kind=kind)

    if kind == "worked_example" and header.budget_basis != "source_reproduction":
        _fail(where, kind, "budget_basis", "must be 'source_reproduction'")

    if kind == "textual_fork":
        readings = header.readings or ()
        if len(readings) < 2:
            _fail(where, kind, "readings", "fewer than two independently-located readings")
        for i, reading in enumerate(readings):
            _validate_locus(reading.get("locus"), where=f"{where} readings[{i}]", kind=kind)

    if kind in ("textual_rule", "worked_example"):
        _validate_locus(header.locus, where=where, kind=kind)

    _scan_keys(header.as_json(), where=where, path="header", reserved=reserved)


def _validate_classification(
    classification: Mapping[str, Mapping[str, Any]], *, where: str, kind: str
) -> None:
    if not classification:
        _fail(where, kind, "classification", "present but empty")
    for section, spec in classification.items():
        label = f"classification.{section}"
        cls = spec.get("class")
        if cls not in CLASSIFICATIONS:
            _fail(where, kind, label, f"class {cls!r} must be one of {sorted(CLASSIFICATIONS)}")
        if cls == "tolerance":
            # ⛔ A tolerance without a band and a unit is a tolerance nobody can apply.
            if spec.get("band") in (None, ""):
                _fail(where, kind, label, "class 'tolerance' without a band")
            if spec.get("unit") in (None, ""):
                _fail(where, kind, label, "class 'tolerance' without a unit")
        else:
            for extra in ("band", "unit"):
                if extra in spec and spec[extra] not in (None, ""):
                    _fail(where, kind, label, f"class {cls!r} may not carry a {extra}")


def _validate_locus(locus: Any, *, where: str, kind: str) -> None:
    """A locus is complete or it is not a locus.

    ⛔ A citation a reader cannot resolve without access to a private repository is not a
    citation: it makes the claim auditable only by us, which is the same defect as no
    audit at all.
    """
    if not isinstance(locus, Mapping):
        _fail(where, kind, "locus", "absent or not an object")
    for name in ("source_kind", "language", "edition", "locus", "interpretation_status"):
        if not locus.get(name):
            _fail(where, kind, f"locus.{name}", "required for a textual kind and absent")


def _scan_keys(
    node: Any, *, where: str, path: str, reserved: Sequence[str] | None = None
) -> None:
    """Reserved-name discipline, over **keys** only."""
    names = tuple(reserved) if reserved is not None else reserved_names()
    if isinstance(node, Mapping):
        for key, value in node.items():
            if not isinstance(key, str):
                raise FixtureContractError(f"{where}: {path}: non-string key {key!r}")
            lowered = key.lower()
            for name in names:
                if name in lowered:
                    raise FixtureContractError(
                        f"{where}: {path}.{key}: a JSON key may never contain {name!r} — a "
                        "permanent identifier must not encode a renameable project name"
                    )
            if not _KEY_RE.match(key):
                raise FixtureContractError(
                    f"{where}: {path}.{key}: keys are lower_snake_case, so a key never "
                    "carries a capitalised product name by accident"
                )
            _scan_keys(value, where=where, path=f"{path}.{key}", reserved=names)
    elif isinstance(node, (list, tuple)):
        for i, item in enumerate(node):
            _scan_keys(item, where=where, path=f"{path}[{i}]", reserved=names)


def validate_filename(path: Path, *, reserved: Sequence[str] | None = None) -> None:
    names = tuple(reserved) if reserved is not None else reserved_names()
    lowered = path.name.lower()
    for name in names:
        if name in lowered:
            raise FixtureContractError(
                f"{path}: a fixture filename may never contain {name!r}"
            )
    if path.suffix not in (".json", ".jsonl", ".toml"):
        raise FixtureContractError(
            f"{path}: plain text only — JSON/JSONL for values, TOML for manifests. "
            "⛔ No binary, no LFS, no compression."
        )


# --------------------------------------------------------------------------------------
# Writing
# --------------------------------------------------------------------------------------


def write_jsonl(
    path: Path,
    header: Header,
    rows: Iterable[Mapping[str, Any]],
    *,
    declared_sections: Sequence[str] | None = None,
    reserved: Sequence[str] | None = None,
) -> int:
    """Write a fixture as JSONL: line 1 is the header, every later line is one row.

    JSONL is chosen over a single JSON document for the same reason a diff report is a
    table rather than a bit: a row set of this size has to diff per row, so a
    regeneration shows *which* values moved.

    Returns the number of rows written.
    """
    validate_filename(path, reserved=reserved)
    validate_header(header, where=str(path), reserved=reserved)

    if header.classification is not None and declared_sections is not None:
        missing = set(declared_sections) - set(header.classification)
        if missing:
            _fail(
                str(path),
                header.fixture_kind,
                "classification",
                f"no classification for section(s) {sorted(missing)}",
            )

    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open("w", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(header.as_json(), ensure_ascii=True, sort_keys=False) + "\n")
        for row in rows:
            _scan_keys(row, where=str(path), path=f"row[{count}]", reserved=reserved)
            if header.classification is not None:
                section = row.get("section")
                if section is None:
                    _fail(str(path), header.fixture_kind, f"row[{count}].section", "absent")
                if section not in header.classification:
                    _fail(
                        str(path),
                        header.fixture_kind,
                        f"row[{count}].section",
                        f"{section!r} has no entry in `classification`",
                    )
            fh.write(
                json.dumps({"record": "row", **row}, ensure_ascii=True, sort_keys=False) + "\n"
            )
            count += 1

    if count == 0:
        path.unlink(missing_ok=True)
        raise FixtureContractError(
            f"{path}: refused to write a fixture with no rows — an empty evidence file reads "
            "as evidence, which is the failure this contract exists to prevent"
        )
    return count


def bits(value: float) -> str:
    """The IEEE-754 bit pattern of a double, as 16 lowercase hex digits.

    ⭐ Recorded beside every decimal value. A decimal round-trip through ``repr`` is exact
    for a double in CPython, but that is a property of *this* writer and *this* reader; the
    bit pattern is a property of the number. A consumer that disagrees on the decimal and
    agrees on the bits has a formatting bug, not a numeric one, and the two cases are worth
    telling apart at a glance.
    """
    import struct

    return struct.pack(">d", value).hex()
