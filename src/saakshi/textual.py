"""Textual authority: resolving a citation against a copy, rather than asserting it.

R6 is the reference for *what an identifiable source text states*. The three fixture kinds
that can only ever carry it — `textual_rule`, `textual_fork`, `worked_example` — had never
been emitted by a real artifact before this module existed, so the contract's most carefully
argued rules were exercised only by their own negative tests.

⛔ **A CITATION A READER CANNOT RESOLVE IS NOT A CITATION.** That is the whole of R6's
difficulty, and it is not solved by writing a chapter number down. Two editions of one text
differ; a translator's note is printed on the same page as the translation and is not the
same authority; and a copy that reached this machine as a scan has been read by a machine
before it was read by us. So a locus here is resolved *into a named copy* and the resolution
is recorded:

* the **witness** — the address the copy was asked for, on what date, and its digest;
* the **rendering** — how those bytes became searchable text, and by what;
* the **extent** — what the copy actually contains, ⭐ *measured*, never assumed from a title;
* the **resolution** — that the quoted words occur in that rendering, exactly once.

⭐ **Resolve what can be resolved; refuse the rest by name.** A claim this module cannot
locate is not quietly dropped: it becomes a refusal row carrying its subject and its reason.
⚠ A count with no names is a silent cap on what a reader can check, so the refusals are
enumerated rather than totalled.

⛔ **Recorder, never explainer — and the line falls in a different place here.** Restating
what a classical text states is the entire point of R6, and is not the thing the rule
forbids. What stays out is any account of how another *implementation* computes anything.
The one piece of arithmetic in this module is a reduction method read off a source's own
worked example, applied in order to check the source against itself.

⛔ **No licence determination is made anywhere.** Only what a citation needs is quoted.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Sequence

from .fixture import INTERPRETATION_STATUS, SOURCE_KINDS

# --------------------------------------------------------------------------------------
# Normalisation, and why a locus is resolved against a normalised form
# --------------------------------------------------------------------------------------

#: ⚠ Declared rather than described, because it is part of every resolution below. A scan
#: read by a machine breaks lines where the page broke them and pads them unevenly, so a
#: fragment quoted from one printing of the rendering would fail against the next. Collapsing
#: runs of whitespace is the smallest normalisation that survives that; ⛔ nothing else is
#: touched, so a spelling, a hyphen or a digit that differs still fails to resolve.
NORMALISATION = (
    "runs of whitespace collapsed to a single space, leading and trailing space removed; "
    "nothing else altered, so any difference in spelling, punctuation or digits still fails"
)

_WHITESPACE = re.compile(r"\s+")


def normalise(text: str) -> str:
    """The form every fragment and every rendering is compared in. See `NORMALISATION`."""
    return _WHITESPACE.sub(" ", text).strip()


def digest(text: str) -> str:
    """The digest of a rendering, over its normalised form.

    ⭐ Over the *normalised* form on purpose: it is the text a locus actually resolves
    against, and pinning the pre-normalisation bytes would pin something no claim here is
    made about. The copy's own digest is recorded separately, on the witness.
    """
    return hashlib.sha256(normalise(text).encode("utf-8")).hexdigest()


# --------------------------------------------------------------------------------------
# What a copy is, and how it got here
# --------------------------------------------------------------------------------------


class TextualError(Exception):
    """Raised when a locus cannot honestly be recorded. ⛔ There is no permissive mode."""


#: How a copy's bytes became text a locus can be resolved against. ⭐ It belongs on the
#: record because it is what tells a reader how to read a *failed* match: words missing from
#: a machine reading of a scan may be missing from the scan, and words missing from a text
#: layer the file itself carries are missing from the file.
RENDERING_KINDS = frozenset(
    {
        # a machine reading of a scanned page. ⚠ Has an error rate, and this module does not
        # measure it in general — it measures it where a claim depends on it.
        "optical_character_recognition",
        # text the file itself carries, extracted by a named tool at a named version
        "embedded_text_layer",
        # typed out by a person
        "transcription",
    }
)


@dataclass(frozen=True)
class Witness:
    """The copy a locus resolves into, and how it was obtained.

    ⛔ **The address that answered is deliberately not recorded**, and that is a measurement
    rather than a preference: asking one of these addresses twice was answered by two
    different hosts of a distribution network. A field that moves between two retrievals of
    one unchanged resource is a fact about the transaction, and writing it down makes a
    reproducibility claim false for the next reader.
    """

    address: str
    retrieved: str
    http_status: int
    copy_sha256: str
    copy_bytes: int

    def as_json(self) -> dict[str, Any]:
        return {
            "address": self.address,
            "retrieved": self.retrieved,
            "http_status": self.http_status,
            "copy_sha256": self.copy_sha256,
            "copy_bytes": self.copy_bytes,
            "the_address_that_answered_is_not_recorded_because": (
                "asked twice, this resource was served by two different hosts of one "
                "distribution network. The host is a property of the transaction and not "
                "of the copy, and recording it would make this record fail to reproduce"
            ),
            "what_this_establishes": (
                "what this instrument received from that address on that date. ⛔ It does "
                "not establish that anyone published it: a server answering an address is "
                "a different claim, and nothing available from outside closes that gap"
            ),
        }


@dataclass(frozen=True)
class Rendering:
    """How the copy became searchable text, and the digest of exactly what was searched."""

    kind: str
    produced_by: str
    sha256: str
    characters: int

    def as_json(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "produced_by": self.produced_by,
            "sha256": self.sha256,
            "characters": self.characters,
            "normalisation": NORMALISATION,
            "limit": (
                "a locus resolves into this rendering, not into the printed page. Where the "
                "rendering is a machine reading, words it lost are words no search here can "
                "find, and an absence measured over it is bounded by that"
            ),
        }


@dataclass(frozen=True)
class Edition:
    """One copy of one text, identified well enough for a reader to obtain the same one.

    ⭐ `extent` is **measured** — what the copy was observed to contain, established by
    finding the copy's own internal boundary markers. ⛔ A title is not an extent: the copy
    this module was first built against is titled as a part, and a claim of absence made
    over it is an absence in that part and nowhere else.
    """

    key: str
    identity: str
    language: str
    witness: Witness
    rendering: Rendering
    extent: Mapping[str, Any]
    text: str

    def __post_init__(self) -> None:
        if self.rendering.kind not in RENDERING_KINDS:
            raise TextualError(
                f"{self.key}: rendering kind {self.rendering.kind!r} is not declared; must "
                f"be one of {sorted(RENDERING_KINDS)}"
            )
        if self.rendering.sha256 != digest(self.text):
            raise TextualError(
                f"{self.key}: the rendering's recorded digest is not the digest of the text "
                "being searched. ⛔ Every locus below would then resolve into one document "
                "and be attributed to another"
            )

    @property
    def normalised(self) -> str:
        return normalise(self.text)

    def as_json(self) -> dict[str, Any]:
        return {
            "identity": self.identity,
            "language": self.language,
            "witness": self.witness.as_json(),
            "rendering": self.rendering.as_json(),
            "extent": dict(self.extent),
        }


def measured_extent(
    text: str,
    *,
    markers: Sequence[tuple[str, Sequence[str]]],
    describes: str,
    beyond: str,
) -> dict[str, Any]:
    """What a copy contains, established from its own internal boundary markers.

    Each marker is a label and the spellings it may be printed in. ⚠ The alternates are not
    slack: a copy read off a scan prints the same boundary with and without an article, and a
    single-spelling check would report a division missing that is plainly there — an extent
    that under-reports is as wrong as one that over-reports, and quieter.

    ⛔ `beyond` is required and is the honest half: it states what this copy establishes about
    the material it does *not* contain.
    """
    body = normalise(text)
    found: list[str] = []
    missing: list[str] = []
    for label, spellings in markers:
        hit = any(normalise(spelling) in body for spelling in spellings)
        (found if hit else missing).append(label)
    return {
        "describes": describes,
        "divisions_looked_for": [label for label, _ in markers],
        "divisions_found": found,
        "divisions_not_found": missing,
        "complete": not missing,
        "established_from": (
            "the copy's own internal boundary markers, in the spellings listed on this "
            "record. ⛔ Not from a title and not from a table of contents: a title claims, "
            "and a boundary marker is printed where the material actually ends"
        ),
        "beyond_this_extent_the_copy_establishes": beyond,
    }


# --------------------------------------------------------------------------------------
# Resolution
# --------------------------------------------------------------------------------------

#: Why a claim was not written down. ⭐ Every one of these is a state a reader can act on,
#: which is why the file carries them as rows instead of a total.
REFUSAL_REASONS = frozenset(
    {
        # the rule is known to us, and no copy of a text stating it is held
        "no_edition_in_hand",
        # a copy is held and the words are not in it
        "fragment_not_found",
        # ⛔ the words occur more than once, so they locate nothing
        "fragment_ambiguous",
        # the locus names a part of the work this copy does not contain
        "outside_the_extent_of_the_copy",
        # the locus lands in a table this rendering did not preserve
        "table_not_legible_in_this_rendering",
        # the locus lands in a script this rendering did not preserve at all
        "script_not_present_in_this_rendering",
    }
)


@dataclass(frozen=True)
class Resolution:
    """Whether a fragment locates exactly one place in a named rendering."""

    edition: str
    fragment: str
    occurrences: int

    @property
    def resolved(self) -> bool:
        return self.occurrences == 1

    def as_json(self) -> dict[str, Any]:
        return {
            "edition": self.edition,
            "occurrences": self.occurrences,
            "resolved": self.resolved,
            "characters_quoted": len(self.fragment),
        }


def resolve(edition: Edition, fragment: str) -> Resolution:
    """Locate `fragment` in `edition`'s rendering, under `NORMALISATION`.

    ⛔ **Two occurrences is a refusal, not a success.** A fragment that appears twice has not
    located anything — and it is the ordinary case rather than an exotic one, because a
    table of contents restates the words of the chapter it points at. A recorder that took
    the first hit would cite the contents page and call it the rule.
    """
    if not fragment.strip():
        raise TextualError(f"{edition.key}: an empty fragment resolves everywhere")
    return Resolution(
        edition=edition.key,
        fragment=fragment,
        occurrences=edition.normalised.count(normalise(fragment)),
    )


@dataclass(frozen=True)
class Locus:
    """The five fields the contract requires, plus the resolution that makes them checkable.

    ⭐ The contract requires the five and checks two of them against a value set. What it
    cannot check is whether the citation *points at anything*, because that needs the copy.
    This is where that is checked, and `as_json` refuses to emit a locus whose fragment did
    not resolve.
    """

    source_kind: str
    edition: Edition
    locus: str
    interpretation_status: str
    fragment: str
    #: The language of the located material, which need not be the edition's headline
    #: language: a translation prints the original beside the rendering of it.
    language: str | None = None

    def __post_init__(self) -> None:
        if self.source_kind not in SOURCE_KINDS:
            raise TextualError(f"{self.locus}: source kind {self.source_kind!r} undeclared")
        if self.interpretation_status not in INTERPRETATION_STATUS:
            raise TextualError(
                f"{self.locus}: interpretation status {self.interpretation_status!r} undeclared"
            )

    @property
    def resolution(self) -> Resolution:
        return resolve(self.edition, self.fragment)

    def as_json(self) -> dict[str, Any]:
        """The locus block. ⚠ `edition` is the **key** of an entry in the header's oracle.

        The full identification of a copy — its witness, its rendering and its measured
        extent — is a dozen fields, and repeating it on every row would put the same block in
        one file dozens of times. It is written once, in `oracle.editions`, and referenced
        here by key. ⛔ The key is resolvable only against the header of the same file, which
        is line one of it: a locus is never read apart from the fixture that carries it.
        """
        resolution = self.resolution
        if not resolution.resolved:
            raise TextualError(
                f"{self.locus}: the quoted fragment occurs {resolution.occurrences} time(s) "
                f"in {self.edition.key}. ⛔ A locus is written down only once it has been "
                "resolved; a citation that points at nothing, or at two things, is not a "
                "citation. Record it as a refusal instead"
            )
        return {
            "source_kind": self.source_kind,
            "language": self.language or self.edition.language,
            "edition": self.edition.key,
            "locus": self.locus,
            "interpretation_status": self.interpretation_status,
            "quoted": normalise(self.fragment),
            "resolution": resolution.as_json(),
        }


@dataclass(frozen=True)
class Refusal:
    """A claim that was considered and not written down, with its subject and its reason."""

    subject: str
    reason: str
    detail: str
    what_would_close_it: str

    def __post_init__(self) -> None:
        if self.reason not in REFUSAL_REASONS:
            raise TextualError(f"{self.subject}: refusal reason {self.reason!r} undeclared")

    def as_row(self) -> dict[str, Any]:
        return {
            "finding": "refused",
            "subject": self.subject,
            "reason": self.reason,
            "detail": self.detail,
            "what_would_close_it": self.what_would_close_it,
        }


def refusal_summary(refusals: Sequence[Refusal]) -> dict[str, Any]:
    """The refusals, counted **and named**.

    ⚠ A count with no names is a silent cap on what a reader can check: it says how much was
    left out and gives no way to tell whether the omission was the interesting part.
    """
    by_reason: dict[str, list[str]] = {}
    for refusal in refusals:
        by_reason.setdefault(refusal.reason, []).append(refusal.subject)
    return {
        "refused": len(refusals),
        "subjects_by_reason": {reason: sorted(v) for reason, v in sorted(by_reason.items())},
        "why_they_are_named": (
            "a count with no names is a silent cap on what a reader can check. Each refusal "
            "is also a row of its own, carrying what would close it"
        ),
    }


# --------------------------------------------------------------------------------------
# Absence
# --------------------------------------------------------------------------------------


@dataclass(frozen=True)
class AbsenceSearch:
    """That a located extent does **not** state something — as a measurement.

    ⭐ **A rule's absence from a located text is a statable, checkable claim**, and it is the
    claim most easily made too strongly. Two limits bound it, and both are on the record:

    * ⛔ **A scan is only as wide as its alphabet.** An absence established by searching one
      spelling is an absence of that spelling. Every spelling searched is listed, with its
      own hit count, so a reader can see what was not looked for.
    * ⛔ **And only as wide as the copy.** The extent searched is the extent of the copy in
      hand, which may be a part of the work.

    ⚠ Every hit is **located**, not merely counted: the claim is that none of them says the
    thing, and a reader cannot check that against a number.
    """

    claim: str
    alphabet: Sequence[str]
    edition: Edition
    #: Each hit, as `(spelling, what stands around it)`.
    occurrences: Sequence[tuple[str, str]]
    what_the_hits_do_say: Sequence[str]

    @property
    def hits(self) -> dict[str, int]:
        body = self.edition.normalised.lower()
        return {spelling: body.count(normalise(spelling).lower()) for spelling in self.alphabet}

    def as_row(self) -> dict[str, Any]:
        counts = self.hits
        return {
            "finding": "absence",
            "claim": self.claim,
            "edition": self.edition.key,
            "spellings_searched": list(self.alphabet),
            # ⚠ A list of objects rather than a map keyed by the spelling. A JSON key is a
            #   permanent identifier and these are search terms — data, which changes when
            #   the next reader thinks of a spelling nobody here did. The writer refuses a
            #   key that is not lower_snake_case, and it refused this one.
            "hits_by_spelling": [
                {"spelling": spelling, "hits": counts[spelling]} for spelling in self.alphabet
            ],
            "hits_in_total": sum(counts.values()),
            "every_hit_located": [
                {"spelling": spelling, "context": normalise(context)}
                for spelling, context in self.occurrences
            ],
            "what_the_hits_do_say": list(self.what_the_hits_do_say),
            "established_over": dict(self.edition.extent),
            "limit": (
                "⛔ this is an absence from the extent searched, in the spellings listed, in "
                "this rendering. A spelling not listed was not looked for; a part of the "
                "work this copy does not contain was not searched; and a machine reading of "
                "a scan can lose words the page carries"
            ),
        }


def collect_occurrences(
    edition: Edition, spelling: str, *, window: int = 200
) -> list[tuple[str, str]]:
    """Every occurrence of `spelling`, with the text around it. ⛔ Never a sample."""
    body = edition.normalised
    needle = normalise(spelling).lower()
    lowered = body.lower()
    out: list[tuple[str, str]] = []
    start = 0
    while True:
        found = lowered.find(needle, start)
        if found < 0:
            return out
        out.append((spelling, body[max(0, found - window) : found + window]))
        start = found + len(needle)


# --------------------------------------------------------------------------------------
# Reading a table out of a rendering, and knowing when you cannot
# --------------------------------------------------------------------------------------


@dataclass(frozen=True)
class TableReading:
    """Integers read out of a region of a rendering, against the count the region must hold.

    ⛔ **A table is where a machine reading of a scan fails, and it fails silently**: the
    cells that survive are still digits, still in order, and still look like a row. So the
    count is declared by the caller from the subject — a row over the twelve signs has twelve
    cells — and a short row is a refusal rather than a shorter answer.

    ⚠ **Legibility is a property of the table, not of the rendering.** Measured, not assumed:
    in the copy this was built against, one chapter's rows read complete and the next
    chapter's lost two cells each. Either observation alone licenses a wrong general rule.
    """

    label: str
    expected_cells: int
    values: tuple[int, ...]

    @property
    def legible(self) -> bool:
        return len(self.values) == self.expected_cells

    def as_json(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "cells_expected": self.expected_cells,
            "cells_read": len(self.values),
            "legible": self.legible,
            "values": list(self.values) if self.legible else None,
        }


def region(edition: Edition, *, label: str, after: str, before: str) -> str:
    """The text standing between two landmarks, each of which must resolve exactly once.

    ⛔ **A region delimited by an ambiguous landmark is not a region**, and the failure is not
    theoretical: two of the landmarks first tried for the tables this repository reads
    occurred twice apiece, and each opened a region other than the one it appeared to open.

    ⚠ **This refusal and a declared cell count are independent checks, and the pair is the
    finding.** Measured, on the two: the first ambiguous landmark opened a region of 548
    figures where 12 were required, so a cell count would have caught it too. The second
    opened *exactly the intended region* — it was ambiguous and harmless, and no count of any
    kind could have distinguished it from a landmark that resolves. ⛔ Judging the rule by
    either case alone gives the wrong answer: from the first, that counting is enough; from
    the second, that ambiguity does not matter. It is unsafe because on the next copy the two
    come apart, and nothing in the output says which case you are in.
    """
    for landmark in (after, before):
        found = resolve(edition, landmark)
        if not found.resolved:
            raise TextualError(
                f"{label}: the landmark {landmark!r} occurs {found.occurrences} time(s) in "
                f"{edition.key}, so it does not delimit a region. ⛔ A recorder taking the "
                "first hit would read a region it did not choose"
            )
    body = edition.normalised
    opening = normalise(after)
    start = body.index(opening) + len(opening)
    return body[start : body.index(normalise(before), start)]


def read_integer_cells(
    edition: Edition, *, label: str, after: str, before: str, cells: int
) -> TableReading:
    """Read whole numbers from a region, where the rendering kept the cells apart."""
    return TableReading(
        label=label,
        expected_cells=cells,
        values=tuple(
            int(v)
            for v in re.findall(r"\d+", region(edition, label=label, after=after, before=before))
        ),
    )


def read_integer_digits(
    edition: Edition, *, label: str, after: str, before: str, cells: int
) -> TableReading:
    """Read a region digit by digit, where the rendering lost the cell boundaries.

    ⚠ Only safe where every cell is a single digit **and** a second witness says what the row
    should hold. Read this way, a run of digits will always produce *some* row; it is the
    declared cell count and the second witness that decide whether it produced the right one.
    """
    return TableReading(
        label=label,
        expected_cells=cells,
        values=tuple(
            int(v)
            for v in re.findall(r"\d", region(edition, label=label, after=after, before=before))
        ),
    )


def agreement(label: str, first: Sequence[int], second: Sequence[int], *, first_is: str, second_is: str) -> dict[str, Any]:
    """Two independent transcriptions of one row of figures, compared cell by cell.

    ⭐ This is the control that makes a worked example *resolved* rather than *retyped*. A
    source that prints its example twice — once as a chart and once spelled out in the prose
    — has supplied its own second witness, and a rendering that mangled either would show up
    here as a disagreement instead of passing as evidence.
    """
    pairs = list(zip(first, second))
    agreed = [a == b for a, b in pairs]
    return {
        "label": label,
        "first_is": first_is,
        "second_is": second_is,
        "cells_compared": len(pairs),
        "cells_agreeing": sum(agreed),
        "lengths_match": len(first) == len(second),
        "disagreements": [
            {"index": i, "first": a, "second": b} for i, (a, b) in enumerate(pairs) if a != b
        ],
        "agrees": len(first) == len(second) and all(agreed),
    }


# --------------------------------------------------------------------------------------
# The one piece of arithmetic, and what licenses it
# --------------------------------------------------------------------------------------

#: The twelve signs, in the order a chart drawn from a starting sign runs. ⚠ Names only —
#: this module attaches no astronomy to them, and reads them purely as the twelve columns a
#: source's own row of figures is printed across.
SIGNS: tuple[str, ...] = (
    "aries", "taurus", "gemini", "cancer", "leo", "virgo",
    "libra", "scorpio", "sagittarius", "capricorn", "aquarius", "pisces",
)

#: Positions four apart share a group of three. Read off the source's own enumeration of
#: them, which it gives in full before it uses them.
TRINES: tuple[tuple[int, int, int], ...] = tuple(
    (i, i + 4, i + 8) for i in range(4)
)


def reduce_by_trine_minimum(values: Sequence[int]) -> tuple[int, ...]:
    """Subtract each group-of-three's smallest member from all three of its members.

    ⛔ **This is not a rule this repository holds.** It is the method a source's own worked
    example resolves to, applied in order to check that source against itself — which is
    exactly and only what a `worked_example` fixture may claim. The source's *stated* rule,
    read literally, is a different method, and the fixture that carries this says so.
    """
    if len(values) != len(SIGNS):
        raise TextualError(
            f"a row over the signs has {len(SIGNS)} cells and this one has {len(values)}"
        )
    out = list(values)
    for trine in TRINES:
        least = min(values[i] for i in trine)
        for i in trine:
            out[i] = values[i] - least
    return tuple(out)


def rotate_to(values: Sequence[int], *, first_sign: str) -> tuple[int, ...]:
    """Re-key a row printed from a starting sign onto the fixed order in `SIGNS`.

    ⚠ A source prints such a row beginning at whichever sign its subject occupies, so the
    row's first cell is not the first sign. Getting this wrong is invisible — the figures
    are all still there, in an order that looks deliberate.
    """
    offset = SIGNS.index(first_sign)
    return tuple(values[(i - offset) % len(SIGNS)] for i in range(len(SIGNS)))


def as_by_sign(values: Sequence[int]) -> dict[str, int]:
    return dict(zip(SIGNS, values))


# --------------------------------------------------------------------------------------
# Shared header material
# --------------------------------------------------------------------------------------

#: ⛔ The sentence every R6 artifact carries about what R6 is and is not.
R6_STANDING = (
    "R6 records what an identifiable source text states. ⛔ It is not a claim that the "
    "statement is correct, that this repository holds it, or that any consumer should "
    "implement it. A text is an authority about itself and about nothing else"
)

NO_LICENCE_DETERMINATION = (
    "no licence determination is made or implied. Only what a citation needs is quoted"
)


def source_oracle(editions: Iterable[Edition], *, resolved: int, refused: int) -> dict[str, Any]:
    """The `oracle` block of an R6 fixture: the copies the loci were resolved into."""
    listed = list(editions)
    return {
        "editions": {edition.key: edition.as_json() for edition in listed},
        "how_a_locus_is_resolved": (
            "the words quoted at the locus are searched for in the named rendering, under "
            "the declared normalisation, and must occur exactly once. ⛔ A fragment found "
            "twice locates nothing and is refused, because a table of contents restates the "
            "words of the chapter it points at"
        ),
        "claims_resolved": resolved,
        "claims_refused": refused,
        "standing": R6_STANDING,
        "licence": NO_LICENCE_DETERMINATION,
    }
