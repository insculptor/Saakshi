"""The fixture contract, implemented fail-closed.

Every file this repository writes carries a provenance block: which reference answered,
which script asked, at which commit, on which date, and the identity of the software or
source that produced the value. This module is the writer's half of that contract.

⛔ **Nothing here is permissive.** A fixture missing a field its `fixture_kind` requires,
carrying a field its kind forbids, or naming an unknown kind or reference is refused *at
write time*, with an error naming the file, the kind and the field. Refusing at read time
would be enough to keep bad evidence out of a comparison; refusing at write time keeps it
out of a commit.

⚠ **The escape hatch for a rule this contract cannot yet express** — see
`REFERENCE_UNBOUND`. It is still here, and it is now *narrower*: a fixture that conforms
may not carry a deviation block, because a deviation nobody can act on reads as an open
question when the question is closed.
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
#: ⭐ Every other value in this registry names **a source**. This one names a
#: **relationship**, and it is the only one that constrains the shape of the `oracle` block
#: rather than merely labelling it — see `_SELF_CONSISTENCY_ARTIFACTS`.
#:
#: A publisher's own test-value file is its integration checked against its own exported
#: data. No outside reference judged it, so there is no outside source to name: filing it
#: under the ephemeris-service reference would widen that reference's authority to cover a
#: claim it was never given, and `instrument` is defined as a named harness, which this is
#: not. The honest label is the relationship itself.
PUBLISHER_SELF_CONSISTENCY = "publisher_self_consistency"

#: =================================  ================================================
#: ``R1``                             the ephemeris publisher's service and development ephemerides
#: ``R2``                             the SPICE Toolkit, with an independent pure-Python cross-check
#: ``R3``                             the Swiss Ephemeris, committed fixtures only
#: ``R4``                             published external values: almanacs, vendor exports, printed tables
#: ``R5``                             the predecessor engine, for continuity only
#: ``R6``                             textual authority — what an identifiable source text states
#: ``instrument``                     a harness with no authority of its own
#: ``publisher_self_consistency``     a publisher's own artifact checked against a second artifact of its own
#: =================================  ================================================
REFERENCES_CONTRACT = frozenset(
    {"R1", "R2", "R3", "R4", "R5", "R6", "instrument", PUBLISHER_SELF_CONSISTENCY}
)

#: ⚠ **The value for a claim this registry cannot yet express.**
#:
#: Every file carrying it must also carry a ``contract_deviation`` block naming the clause
#: it does not satisfy. A consumer trips over it, reads why, and a human decides — which is
#: the correct outcome for a gap in a contract neither side may quietly widen.
#:
#: ⭐ **This is the mechanism that produced `publisher_self_consistency`.** A generator
#: emitted `none`, the consumer's loader refused the file, and the value was admitted by a
#: reviewed change on the consumer's side. The hatch stays open for the next such gap.
#:
#: ⛔ But it may only ever appear on an artifact that is **actually** non-conforming: a
#: fixture whose reference is in the registry may not carry a deviation block. A recorded
#: deviation that no longer exists reads as an open question after it has been closed,
#: which sends a human to re-decide something already decided.
REFERENCE_UNBOUND = "none"

#: The comparison classes a numeric fixture may declare.
CLASSIFICATIONS = frozenset({"exact", "tolerance", "reference_only"})

#: What kind of source the material at a locus sits in.
#:
#: ⛔ **Minted because the field existed without one.** Until R6 stood on it, `_validate_locus`
#: checked that `source_kind` was *present* and never what it said, so a typo passed and a
#: reader downstream could not group on it. ⚠ A field whose value set is "any string" is a
#: field that reports a pass on anything — and this repository's own test file proved it:
#: its shared locus carried `interpretation_status = "settled"`, a value no registry has ever
#: declared, and the contract accepted it in every test that used it.
#:
#: ⭐ The distinction that earns the registry is **translation versus commentary**. A
#: translator's rendering of a text and a translator's note about it are printed on the same
#: page and are not the same authority, and a fixture that files one as the other has made a
#: claim the source does not support.
SOURCE_KINDS = frozenset(
    {
        # the root text in its own language
        "primary_text",
        # a translation of a primary text, carrying the translator's own numbering
        "translation",
        # exposition printed alongside a text, by its translator or a commentator
        "commentary",
        # a worked illustration the source resolves itself
        "worked_illustration",
        # a modern author's own work, not a translation of anything
        "treatise",
    }
)

#: How far the recorded claim sits from the words at the locus. ⭐ This is the field that
#: makes an R6 fixture auditable rather than merely cited: *the text says this* and *we read
#: this out of the text* are different claims, and only one of them can be checked by looking.
INTERPRETATION_STATUS = frozenset(
    {
        # the recorded claim IS the located words
        "quoted",
        # the located words state it; restated here without inference
        "restated",
        # not stated anywhere; read off a worked example the source resolves itself
        "read_from_worked_example",
        # the located words admit more than one reading, and this is one of them
        "disputed_reading",
        # ⭐ the claim is that the located extent does NOT state this. It still needs a
        # complete locus: an absence with no extent names nothing, and is unfalsifiable.
        "absent",
    }
)

#: ⚠ A **shape**, not a registry, and the difference is deliberate. The set of languages is
#: not this contract's to declare — that standard exists outside this repository. But
#: `English`, `english` and `Eng.` are three groups for one language, so the field is held to
#: a two- or three-letter lowercase code and a reader can group on it.
_LANGUAGE_RE = re.compile(r"^[a-z]{2,3}$")

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
    """The one line every generator prints before writing anything.

    ⚠ **ASCII only, deliberately.** This string is printed to a console, and a default
    Windows console encoding cannot encode the marker glyphs used elsewhere in this
    repository. A warning that raises `UnicodeEncodeError` instead of appearing does not
    merely fail to warn — it aborts the generator, and it does so *only* on the path where
    the local list is missing, which is the one path the warning exists for.
    """
    loaded = _config_path().is_file()
    count = len(reserved_names())
    if loaded:
        return f"reserved-name check: {count} names in force (local list loaded)"
    return (
        f"reserved-name check: WEAKENED - {count} name(s) in force; "
        "config/reserved-names.txt is absent, so only the built-in default applies"
    )


# --------------------------------------------------------------------------------------
# Absolute paths, and why a fixture may not carry one
# --------------------------------------------------------------------------------------

#: ⛔ **A THIRD PARTY'S ERROR MESSAGE IS UNTRUSTED TEXT THAT MAY QUOTE THE MACHINE.**
#:
#: Found by the working-tree scan, in a shipped artifact: a recorded library refusal read
#: ``SwissEph file 'sepl_12.se1' not found in PATH '<an absolute path>'``, and the path was
#: the temporary directory the recorder happened to be run from. Two defects in one field,
#: and neither is visible from the generator that wrote it:
#:
#: * the path contained a **reserved name**, which is how it was caught at all; and
#: * ⭐ it contained a **session-scoped directory**, so a file claiming byte-for-byte
#:   reproducibility could only ever reproduce inside the one dead session that wrote it.
#:
#: ⭐ **The generator had already decided not to record the directory.** The oracle block
#: names each data file by digest and deliberately carries no path. The path arrived anyway,
#: through the one field whose content is chosen by the library rather than by us — which is
#: why the rule below is enforced at write time over every string in the file, and is not a
#: note asking three generators to remember.
_ABSOLUTE_PATH_PATTERNS = (
    # A Windows drive-absolute path, either slash. Stops at whitespace or a quote.
    # ⛔ The lookbehind is not decoration. Without it this matched the tail of every
    #    recorded URL — `https://host/...` ends in a letter, a colon and a slash, so the
    #    pattern fired on `s://host/...` and would have refused four generators that record
    #    a publisher's address, which is evidence rather than environment.
    re.compile(r"(?<![A-Za-z0-9_])[A-Za-z]:[\\/][^\s'\"]*"),
    # A UNC share.
    re.compile(r"\\\\[^\s'\"]+"),
    # ⚠ A POSIX absolute path needs at least one interior separator, and the lookbehind is
    #   what keeps a URL out of it: in ``https://host/ftp/eph`` the ``/ftp`` is preceded by a
    #   letter and the ``//`` by a slash, so neither can start a match. A recorded URL is
    #   evidence about a publisher; an absolute path is a fact about this machine.
    re.compile(r"(?<![A-Za-z0-9:/._~-])/(?:[^/\s'\"]+/)+[^/\s'\"]*"),
)

#: What replaces one. ⚠ It names the *kind* of thing removed, so a reader of the fixture can
#: tell a redaction from a library that printed nothing.
REDACTED_PATH = "<absolute path removed: it names this machine, not the library>"


def redact_environment(text: str) -> str:
    """Strip absolute filesystem paths out of a message written by somebody else.

    ⭐ Everything that makes the message evidence survives — which entry point spoke, which
    file it wanted, what it refused. Only the part that describes the recorder's own machine
    is removed, and its removal is stated rather than silent.
    """
    for pattern in _ABSOLUTE_PATH_PATTERNS:
        text = pattern.sub(REDACTED_PATH, text)
    return text


def find_absolute_path(text: str) -> str | None:
    """The first absolute path in `text`, or `None`."""
    for pattern in _ABSOLUTE_PATH_PATTERNS:
        match = pattern.search(text)
        if match:
            return match.group(0)
    return None


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

#: ⭐ **A self-consistency claim is irreducibly about a PAIR**, so the reference value alone
#: does not say what was measured. It names no outside source; what it does name is that
#: one artifact of the publisher's reproduces another. Both must therefore be identified,
#: and each in the way that makes *it* checkable:
#:
#: * ``test_artifact`` — the published values. Identified, digested, dated at acquisition,
#:   and pointing at the ``provenance_record`` that attests how it was obtained. ⚠ That
#:   record cannot prove the publisher published anything; it attests what this instrument
#:   retrieved, from where, and when.
#: * ``subject_artifact`` — the published data those values reproduce from. Identified,
#:   digested, and carrying its **data profile**, because "the same ephemeris" is
#:   distributed as several files of different spans and a claim about one is not a claim
#:   about another.
#:
#: ⛔ Any absence is a refusal here, and a load error downstream. A pair claim missing half
#: its pair is not a weaker version of the claim — it is a different, unmade one.
_SELF_CONSISTENCY_ARTIFACTS: dict[str, tuple[str, ...]] = {
    "test_artifact": ("identity", "sha256", "acquired", "provenance_record"),
    "subject_artifact": ("identity", "data_profile", "sha256"),
}


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

    # ⚠ The hatch, and it may never be silent.
    if ref == REFERENCE_UNBOUND and not header.contract_deviation:
        _fail(
            where,
            kind,
            "reference",
            f"{REFERENCE_UNBOUND!r} is not in the reference registry; a fixture using it "
            "must carry a `contract_deviation` block naming the clause it does not satisfy",
        )

    # ⛔ ...and it may never be claimed by a file that conforms.
    if ref != REFERENCE_UNBOUND and header.contract_deviation:
        _fail(
            where,
            kind,
            "contract_deviation",
            f"reference {ref!r} is in the registry, so this fixture conforms and may not "
            "declare a deviation. A deviation that has been closed still reads as an open "
            f"question. ⭐ The block remains available on {REFERENCE_UNBOUND!r} for the next "
            "rule this contract cannot yet express",
        )

    if ref == PUBLISHER_SELF_CONSISTENCY:
        _validate_self_consistency_oracle(header.oracle, where=where, kind=kind)

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


def _validate_self_consistency_oracle(
    oracle: Mapping[str, Any], *, where: str, kind: str
) -> None:
    """Both halves of the pair, or it is not a self-consistency claim.

    ⭐ This is the one reference value whose *shape* is checked rather than only its
    spelling. Every other value names a source a reader can go and consult; this one names
    a relationship, and a relationship is only checkable if both of its terms are named.
    """
    if not oracle.get("publisher"):
        _fail(
            where,
            kind,
            "oracle.publisher",
            "a self-consistency claim is a claim about ONE party's two artifacts, so that "
            "party must be named",
        )
    for artifact, members in _SELF_CONSISTENCY_ARTIFACTS.items():
        block = oracle.get(artifact)
        if not isinstance(block, Mapping):
            _fail(
                where,
                kind,
                f"oracle.{artifact}",
                f"required by reference {PUBLISHER_SELF_CONSISTENCY!r} and absent — the "
                "claim is that one artifact reproduces the other, and half a pair states "
                "nothing",
            )
            return  # pragma: no cover - _fail always raises
        for member in members:
            if not block.get(member):
                _fail(
                    where,
                    kind,
                    f"oracle.{artifact}.{member}",
                    "required and absent or empty",
                )


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

    ⭐ **Two of the five fields are also checked against a value set**, which they were not
    until R6 became the first artifact to stand on them. Presence-only validation accepted
    any string, so a misspelling passed the writer and arrived downstream as a group of one.
    ⚠ The other three are left as free text on purpose: an `edition` and a `locus` are a
    proper name and a citation, and a registry of those is a registry of everything ever
    printed.
    """
    if not isinstance(locus, Mapping):
        _fail(where, kind, "locus", "absent or not an object")
    for name in ("source_kind", "language", "edition", "locus", "interpretation_status"):
        if not locus.get(name):
            _fail(where, kind, f"locus.{name}", "required for a textual kind and absent")

    source_kind = locus["source_kind"]
    if source_kind not in SOURCE_KINDS:
        _fail(
            where,
            kind,
            "locus.source_kind",
            f"{source_kind!r} is not a declared source kind; must be one of "
            f"{sorted(SOURCE_KINDS)}. ⛔ An undeclared value cannot be grouped on by a "
            "reader, so it reports a pass and carries no meaning",
        )

    status = locus["interpretation_status"]
    if status not in INTERPRETATION_STATUS:
        _fail(
            where,
            kind,
            "locus.interpretation_status",
            f"{status!r} is not a declared interpretation status; must be one of "
            f"{sorted(INTERPRETATION_STATUS)}. ⭐ This field is what separates *the text "
            "says this* from *we read this out of the text*, and an undeclared value "
            "collapses the two",
        )

    language = locus["language"]
    if not isinstance(language, str) or not _LANGUAGE_RE.match(language):
        _fail(
            where,
            kind,
            "locus.language",
            f"{language!r} is not a two- or three-letter lowercase code. ⚠ This is a shape "
            "rather than a registry — the set of languages is not this contract's to "
            "declare — but 'English', 'english' and 'Eng.' are three groups for one "
            "language, and a reader has to be able to group on it",
        )


def _scan_keys(
    node: Any, *, where: str, path: str, reserved: Sequence[str] | None = None
) -> None:
    """Reserved-name discipline over **keys**, and absolute-path discipline over **values**.

    ⚠ The two rules are different on purpose, and the difference is the point:

    * a reserved name in a **key** is refused, because a key is a permanent identifier;
    * a reserved name in a **value** is permitted — ``generator.repo`` must carry this
      repository's own name, and a value records origin;
    * ⛔ an **absolute path** in a value is refused whatever it names. It is not a claim
      about the subject, it is a description of the machine that ran the recorder, and it
      makes a reproducibility claim false on every other machine. Use
      :func:`redact_environment` on any text a third party wrote.
    """
    names = tuple(reserved) if reserved is not None else reserved_names()
    if isinstance(node, str):
        found = find_absolute_path(node)
        if found is not None:
            raise FixtureContractError(
                f"{where}: {path}: an absolute path ({found!r}) may never be written into a "
                "fixture — it describes the recorder's machine rather than the subject, and "
                "it makes the file's byte-for-byte claim false anywhere else. If this is a "
                "message a library wrote, pass it through redact_environment() first"
            )
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
