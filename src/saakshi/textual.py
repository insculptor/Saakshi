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
import unicodedata
from collections import Counter
from dataclasses import dataclass
from functools import lru_cache
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
# Which script a rendering is written in, and which script a search term needs
# --------------------------------------------------------------------------------------

#: The script buckets this repository distinguishes. ⚠ Deliberately coarse: the question
#: being asked is *could this rendering express the words being searched for at all*, and a
#: finer classification would answer a question nobody here has.
_SCRIPT_RANGES: tuple[tuple[str, int, int], ...] = (
    ("latin", 0x0041, 0x024F),
    ("devanagari", 0x0900, 0x097F),
    ("greek", 0x0370, 0x03FF),
    ("cyrillic", 0x0400, 0x04FF),
    ("telugu", 0x0C00, 0x0C7F),
    ("kannada", 0x0C80, 0x0CFF),
    ("tamil", 0x0B80, 0x0BFF),
)


def script_of(character: str) -> str | None:
    """Which bucket a character's script falls in, or `None` if it carries no script.

    ⚠ Digits, punctuation and whitespace return `None` rather than a bucket, and that is the
    load-bearing part: an alphabet made only of marks names no script, so it cannot be
    checked against a rendering, and the check below says so instead of passing it.

    ⛔⛔ **THE `isalpha` TEST IS NOT TIDINESS, IT IS THE WHOLE MEASUREMENT.** Written as a
    bare code-point range this function reported **6 077 Latin characters** in the copy it
    was built to catch — a machine reading of an English book containing not one Latin
    letter. Every one of the 6 077 was a brace, a bracket or a sign that happens to sit
    inside the Latin block. ⭐ *A bucket that counts a rendering's punctuation as its script
    answers yes for exactly the copy the question was asked about.*
    """
    if not character.isalpha():
        return None
    code = ord(character)
    for name, first, last in _SCRIPT_RANGES:
        if first <= code <= last:
            return name
    return None


def scripts_in(text: str) -> dict[str, int]:
    """How many code points of each script a string carries. ⛔ Only scripts it actually has."""
    counts: dict[str, int] = {}
    for character in text:
        name = script_of(character)
        if name is not None:
            counts[name] = counts.get(name, 0) + 1
    return counts


def scripts_required_by(terms: Sequence[str]) -> set[str]:
    """The scripts a set of search terms is written in.

    ⛔ **A term carrying no script contributes nothing**, which is how the one spelling that
    is a printed mark rather than a word stops standing in for eleven that are words.
    """
    required: set[str] = set()
    for term in terms:
        required.update(scripts_in(term))
    return required


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

    @property
    def searchable_characters(self) -> int:
        """How much text a locus can actually be resolved against. ⛔ Not `rendering.characters`.

        ⭐⭐⭐ **MEASURED, BECAUSE THE TWO CAME APART ON A REAL COPY AND THE DIFFERENCE WAS
        THE WHOLE STORY.** A printing acquired by this repository is 219 pages of scanned
        page images with no text layer at all. Its extractor returned one empty string per
        page and joined them with newlines, so `rendering.characters` reports **218** — the
        page count minus one, and nothing else — while the searchable text is **empty**.
        ⛔ A guard written the obvious way, `rendering.characters == 0`, does not fire on it.
        ⚠ *A summary that collapses many values into one has stopped measuring the thing it
        names* — this time on the header field a reader is most likely to trust.
        """
        return len(self.normalised)

    @property
    def carries_searchable_text(self) -> bool:
        return self.searchable_characters > 0

    @property
    def scripts(self) -> dict[str, int]:
        """Which scripts this rendering carries, and how much of each. ⭐ Measured.

        ⛔⛔⛔ **BECAUSE `carries_searchable_text` IS NOT ENOUGH, AND A REAL COPY PROVED IT.**
        A library scan of an English printing in this repository's cache renders to 246 777
        searchable characters and **not one letter of the Latin alphabet**: the machine
        reading was set to an Indic script and returned a quarter of a million characters of
        noise. ⚠ Every guard asking *was this copy read* answers yes for it, and every
        English word searched in it answers zero. ⇒ *A rendering that cannot express the
        alphabet has not been searched in it*, and the only thing that says so is this.
        """
        return scripts_in(self.normalised)

    def carries_script(self, script: str) -> bool:
        """Whether a locus or a search term written in `script` could resolve here at all."""
        return self.scripts.get(script, 0) > 0

    def as_json(self) -> dict[str, Any]:
        return {
            "identity": self.identity,
            "language": self.language,
            "witness": self.witness.as_json(),
            "rendering": self.rendering.as_json(),
            "extent": dict(self.extent),
            # ⭐ Emitted beside the rendering rather than folded into it, because the pair is
            #   the finding: one number can be large while the other is zero.
            "searchable": {
                "characters_a_locus_can_resolve_against": self.searchable_characters,
                "carries_searchable_text": self.carries_searchable_text,
                "why_this_is_not_the_renderings_character_count": (
                    "⛔ they came apart on a copy in this repository's own cache. A PDF of "
                    "219 scanned page images yields one empty string per page; joined with a "
                    "newline apiece the rendering reports 218 characters, which is the page "
                    "count minus one and is not text. ⚠ A check written against the "
                    "rendering's count would pass a copy nothing can be searched in"
                ),
                # ⭐⭐⭐ Published beside the count for the same reason the count is published
                #   beside the rendering's: the pair is the finding, one level down. A second
                #   copy in this cache carries a quarter of a million searchable characters
                #   and zero of the script its own book is printed in.
                "scripts_this_rendering_carries": [
                    {"script": name, "code_points": count}
                    for name, count in sorted(self.scripts.items())
                ],
                "why_the_scripts_are_here": (
                    "⛔ a large searchable count still does not mean a word can be found. A "
                    "library scan of an English printing, held in this repository's cache, "
                    "renders to 246 777 characters and NO LATIN AT ALL - the machine reading "
                    "was set to an Indic script. ⚠ Every English spelling returns zero over "
                    "it and every guard asking whether the copy was read answers yes"
                ),
            },
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
        # ⭐ the script IS present, in quantity, and the passage is still not citable: the
        # copy's own prose names a word as being in it that the rendered passage lacks.
        # ⛔ Distinct from the reason above on purpose - a presence check answers yes here,
        # and a recorder that owned only the one category would read that yes as licence.
        "script_present_but_passage_not_faithful",
        # ⭐ the extent this claim would be measured over is a lower bound rather than a
        # measurement, so the claim cannot be sized. ⛔ Absences fail this way, and they fail
        # silently: an absence over an unknown extent still prints a confident zero.
        "extent_of_the_copy_is_a_lower_bound",
        # ⭐ two copies locate the same rule and it cannot be established that they locate it
        # at the same PLACE in the work. ⛔ Not a disagreement about the rule: a limit on what
        # comparing two copies' own numbering can settle, when they order the sutras
        # differently and no offset describes the pair.
        "place_in_the_work_not_established_across_copies",
        # ⭐⭐ A COPY IS HELD, IT IS THE RIGHT WORK, AND NOTHING IN IT CAN BE SEARCHED. Its
        # pages are images and its rendering carries no text. ⛔ Distinct from every reason
        # above because the copy is not missing, not out of extent and not unfaithful: it is
        # present and mute. ⚠ This is the state in which every absence looks established, so
        # it is named rather than left to be inferred from a row of zeroes.
        "rendering_carries_no_searchable_text",
        # ⭐⭐⭐ THE COPY CARRIES A SECOND COMMENTING HAND, AND A PRINTING THAT ONE HAND
        # REVISED CANNOT WITNESS THE OTHER HAND'S OWN WORDS. ⛔ Not a doubt about whether the
        # words are located - they are - but about whom they belong to: a reviser who
        # rewrites silently leaves no mark, so agreement between two revised printings
        # attests the revision and not the translator.
        "revised_printing_cannot_witness_the_unrevised_words",
        # ⭐⭐⭐ THE COPY WAS READ, AND NOT IN THE ALPHABET THE CLAIM IS WRITTEN IN. A machine
        # reading of an English printing that carries a quarter of a million characters and
        # no Latin script at all. ⛔ Distinct from the mute copy above and strictly more
        # dangerous: the mute copy fails every check that asks whether anything was read, and
        # this one passes all of them while returning zero for every word in the book.
        "rendering_carries_none_of_the_searched_script",
        # ⭐⭐ AND THE GUARD AGAINST THE ABOVE HAS ITS OWN FAILURE MODE. A positive control is
        # only evidence for the search it accompanies: one chosen in a script the alphabet is
        # not written in resolves happily over a rendering the alphabet cannot touch. ⛔ Worse
        # on a noise rendering, where nothing repeats and so EVERY candidate resolves exactly
        # once - the condition meant to be the hardest becomes the easiest in the file.
        "positive_control_is_not_in_the_searched_script",
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


# --------------------------------------------------------------------------------------
# Whether a rendering repeats itself, and what a resolution in it is worth
# --------------------------------------------------------------------------------------

#: The fragment length recurrence is measured at, in characters of the normalised rendering.
#: ⚠ The **pair** (this length, `LEAST_RECURRENCE`) is what refuses, never either alone: at
#: SIX characters that same floor passes the rendering of noise this guard exists for.
RECURRENCE_MEASURED_AT = 12

#: The least share of a rendering's own distinct fragments that must occur **more than
#: once**, before a resolution in it is allowed to stand as evidence of anything.
#:
#: ⭐⭐⭐ **LANGUAGE REPEATS AND A RENDERING OF NOISE DOES NOT, AND THAT IS THE WHOLE
#: MEASUREMENT.** Taken at twelve characters over every copy this repository holds — complete,
#: at every position of the rendering, not a sample:
#:
#: * a machine reading that returned noise — **0.00018** (44 of 246 689);
#: * the least legible of three readings of one printing — 0.068;
#: * a real book printed in the script that noise is written in — 0.089;
#: * every other copy held — 0.105 to 0.139.
#:
#: ⛔ Every real copy held stands at least **6.7×** above this floor and the rendering of
#: noise **56×** below it. ⚠ And the number is fitted to those copies — seven renderings, one
#: of them noise. It is **not a law about renderings**; it is a place to stand that seven
#: measured copies agree on, and a copy refused by it is being compared to those seven.
#: ⭐ What it stands on is not fitted: at every length from eight to twenty the noise
#: rendering sits below every real copy, by 30× at eight characters and 1 900× at twenty.
#:
#: ⭐⭐ **AND IT TRANSFERS, BUT THE FITTED SET IS THE FLATTERING ONE.** Measured over four
#: bodies used to fit nothing — a second real book of this genre, this repository's licence,
#: its documentation and its own program text — every one of them clears this floor at twelve
#: characters. ⛔ The closest stands at **4.8×** it, where the lowest of the seven FITTED
#: copies stands at 6.8×, so a margin read off the seven alone overstates the headroom by a
#: third. ⚠ Every held-out body is language; none of them is a second rendering of noise, so
#: none of them measures the other side of this floor.
#:
#: ⛔⛔⛔ **AND IT REFUSES WHOLE REAL BOOKS. MEASURED, NOT ARGUED.** Sixty-one copies — the
#: fifty-seven held of the fifty-nine two declared draws over a public archive returned, both
#: sides kept this time, plus the four held here — asked what language they carry, with words
#: declared in `COMMONEST_WORDS` before any copy was measured and taken out of none of them:
#:
#: | copy | share | declared Sanskrit per 10 000 words | share of its 1 000-character blocks carrying one | this floor |
#: |---|---|---|---|---|
#: | `bodhicaryavatarapanjika…1902` | 0.00864 | **249.1** | **82.6 %** | ⛔ REFUSED |
#: | `haaralatabyaniruddhabhatta…` | 0.01036 | **247.9** | **83.0 %** | ✅ accepted |
#:
#: ⭐⭐⭐ **THE SAME LANGUAGE, AT THE SAME RATE, ACROSS THE SAME SHARE OF THE COPY — 0.5 %
#: APART ON BOTH MEASUREMENTS, AND OPPOSITE SIDES OF THIS FLOOR.** The refused one is told
#: it is a machine reading that returned noise. It is a Bibliotheca Indica edition of a
#: Sanskrit commentary, read in Devanagari, legible at every offset opened.
#: ⚠ And the verdict does not even track how much language a copy carries: two rows above
#: the accepted `haaralata` sits `krsnakarnamrtam…` at 0.01379 with **67.6** — a quarter of
#: the refused copy's rate — and it passes.
#:
#: ⛔⛔⛔ **BECAUSE WHAT THIS FLOOR SEPARATES IS LANGUAGES.** Of the sixty-one, the twelve
#: carrying declared English across at least a quarter of their thousand-character blocks run
#: **0.0125 to 0.161** and every one of them clears. The fourteen carrying declared
#: Sanskrit or Hindi run **0.00687 to 0.0892** and **straddle** it, three of them below.
#: ⭐ The same at every criterion published — a quarter, a half, three quarters of the copy —
#: so the reading is not the criterion's. Twelve characters of
#: English is about two words; twelve characters of a Devanagari compound is three or four
#: syllables of one, so the same floor asks a far harder question of the second. ⚠ The seven
#: copies it was fitted to are six English renderings and one Devanagari rendering *of an
#: English book* — ⇒ **it was fitted where it is loosest and applied where it is tightest.**
#:
#: ⚠ Read the two sides asymmetrically, as `COMMONEST_WORDS` says: a copy that answers to
#: those words carries the language, and a copy that does not may still be legible — a
#: Devanagari astrology dictionary refused here scores 21.1 because a dictionary is headwords
#: and glosses. So the count of refused real books is a **lower bound**.
#:
#: ⛔⛔⛔ **AND IT ERRS IN THE OTHER DIRECTION TOO, WHICH WAS UNMEASURABLE UNTIL THE COPIES
#: IT ACCEPTS WERE HELD.** Three of the twenty-five copies it accepts are certified readings
#: in a script their catalogued work cannot be printed in — a **Kannada** work read in
#: Devanagari at 0.011922, an English conference proceedings at 0.013917, and the Routledge
#: *Encyclopedia of Philosophy* in ten volumes at **0.030511**, three times this floor, over
#: 39 129 518 characters. See `GREATEST_SHARE_A_WRONG_SCRIPT_READING_REACHES`.
#:
#: ⛔⛔⛔ **SO NO VALUE OF THIS STATISTIC SEPARATES THE TWO, AND THE TWO NAMED REPAIRS ARE
#: BOTH MEASURED AND BOTH REFUSED.** The lowest copy carrying its own language sits at
#: 0.006873 and the highest wrong-script reading at 0.030511 — crossed, by 4.4×:
#:
#: * **A PER-LANGUAGE VALUE.** Routed by `COMMONEST_WORDS` — the only language instrument
#:   here — at each of the three criteria that census published: at a half and at three
#:   quarters **no bucket holds both sides at all**, because every one of the 21 wrong-script
#:   readings answers to no word list and lands where no language is declared, beside 0
#:   certified readings. At a quarter exactly one bucket holds both, and a value fitted in it
#:   **does not separate**: the Sanskrit readings run 0.006873–0.089183 and the wrong-script
#:   reading sits at 0.009675, inside them. ⇒ ⭐⭐⭐ *the routing sorts the two sides into
#:   different buckets, so a per-language floor is fitted with nothing below it — this
#:   floor's original defect, one bucket at a time.*
#: * **A DIFFERENT STATISTIC.** Eight were measured and a ninth was degenerate; every one
#:   scored a wrong-script reading as high as or higher than a real book. See
#:   `STATISTICS_MEASURED_AGAINST_THIS_FLOOR`.
#:
#: ⭐⭐⭐ **THE REASON IS THAT THE AXIS IS WRONG.** A machine reading is a deterministic
#: function of the printing, so a word the printing repeats produces the same garbage string
#: every time it is met and the printing's own recurrence survives into the noise intact.
#: **Repetition measures the morphology of what was printed, not whether the reader could
#: read it.** ⇒ What separates a reading from a wrong-script reading is a PRESENCE of
#: something outside the copy, and this floor consults nothing outside the copy.
#:
#: ⚠ ⛔ **WHAT IS NOT PUBLISHED IS A REPAIRED VALUE.** None was fitted, so none is held out;
#: the refusal keeps its measurement and every row it travels on now says, in both
#: directions, what it does not establish.
LEAST_RECURRENCE = 0.01

#: The least **extent** at which a copy's failure to clear `LEAST_RECURRENCE` says anything
#: about *that copy*, in characters of the normalised rendering.
#:
#: ⛔⛔⛔ **BELOW THIS THE FLOOR IS A TEST OF SIZE AND NOT OF LANGUAGE, AND IT PUBLISHES THE
#: LANGUAGE CAUSE.** Measured by asking the floor of **every window** of one extent in every
#: copy this repository holds — every starting offset, not a sample — and taking the largest
#: extent at which any window of any real copy is still refused. That supremum is **7 685**,
#: one window of the least legible reading of the third edition; this constant is one above
#: it.
#:
#: ⛔⛔⛔ **IT READ 6 000 FOR A SESSION, AND THE ERROR WAS THE TILING PHASE.** The bound was
#: first taken from `blocks_this_floor_refuses`, which tiles a copy into consecutive disjoint
#: blocks starting at offset zero. That is complete coverage of the copy's *characters* and
#: it is **283 of 1 675 741** of the windows of 6 000 characters the copies actually contain
#: — 0.017 % of them. ⭐⭐⭐ *The word "complete" was true of the wrong noun.* Asked of every
#: window instead of one phase, 6 000 refuses **5 593** windows of real books, and 7 000
#: still refuses 309.
#:
#: | extent | windows of the six real copies refused | windows of the noise that clear |
#: |---|---|---|
#: | 200 | 1 405 161 of 1 710 541 | 109 |
#: | 300 | 1 176 768 of 1 709 941 | 207 |
#: | 315 | — | **0** |
#: | 1 000 | 406 896 of 1 705 741 | 0 |
#: | 5 000 | 16 021 of 1 681 741 | 0 |
#: | 6 000 | ⛔ **5 593** of 1 675 741 | 0 |
#: | 7 000 | 309 of 1 669 741 | 0 |
#: | 7 685 | **1** of 1 665 631 | 0 |
#: | **7 686** | **0** of 1 665 625 | 0 |
#:
#: ⛔⛔ **AND IT IS NOT A THRESHOLD, BECAUSE THE COUNT IS NOT MONOTONE IN THE EXTENT.** 7 450
#: refuses nothing, 7 500 refuses 42, 7 550 refuses nothing, 7 650 refuses 36. So *the
#: smallest extent at which nothing is refused* is not a bound at all — it was the rule the
#: 6 000 was picked by, and on this grid it would pick 7 351. The bound published here is the
#: **supremum**: above it nothing is refused, checked at every extent to 7 780, every ten to
#: 8 800, every fifty to 9 000 and every five hundred to 30 000.
#:
#: ⚠ Fitted, exactly as `LEAST_RECURRENCE` is: to the six real renderings held. ⭐ Measured
#: against four bodies it was **not** fitted to, the largest extent at which any window is
#: refused is 5 000 (a second real book, 1.4 M characters), 4 000 (this repository's README),
#: 7 000 (its documentation) and none at all (the licence) — all under this bound, so on the
#: held-out evidence it transfers and is not tight.
LEAST_EXTENT_A_REFUSAL_DISCRIMINATES_AT = 7686

#: The greatest extent at which a window of a copy **this floor refuses** has been measured
#: to CLEAR it anyway, over every refused copy this repository holds.
#:
#: ⛔⛔⛔ **RENAMED A SECOND TIME, AND THE VALUE DID NOT MOVE — WHAT MOVED IS WHAT IT IS A
#: MEASUREMENT OF.** It was published as the greatest extent at which *a rendering of noise*
#: has cleared this floor. The copy it is read off, `TheTheoryOfTheSamdhis…`, is measured to
#: carry declared Sanskrit words in **48.8 %** of its thousand-character blocks, at **239.3**
#: per ten thousand words — more than eight of the twenty-five copies this floor ACCEPTED.
#: It is an English monograph on the Nāṭyaśāstra whose Devanagari quotations the wrong-script
#: reader got *right*, and one of them reads, in the clear, `चाणक्यः- भक्त्या कार्यधुरं …`.
#: ⇒ ⭐⭐⭐ **THE SPECIMEN IS NOT ESTABLISHED TO BE A RENDERING OF NOISE, SO THE OLD NAME
#: ASSERTED THE ONE THING THE MEASUREMENT COULD NOT.** The 320 000 stands as what it always
#: was: a window of a copy this floor refuses, clearing this floor.
#:
#: ⛔⛔⛔ **A MEASURED MAXIMUM, NOT A BOUND, AND THE DIFFERENCE IS THE WHOLE ENTRY.** A bound
#: would say *at or above this extent, clearing this floor says something about the copy*.
#: **Nothing here establishes that**, and the name of the constant this replaces claimed it.
#: What is established is the opposite: a specimen of 330 970 characters — an English
#: monograph of 1978 read by a machine set to an Indic script, carrying not one English word
#: — has windows of **320 000 characters that clear this floor**, which is 96.69 % of itself,
#: and it clears at **2 721 of the 2 731** extents it was asked at.
#:
#: ⛔⛔⛔ **IT READ 315 FOR A SESSION, AND THE DEFECT WAS THAT IT HAD ONE SPECIMEN.** The 315
#: was the supremum over *the single rendering of noise this repository then held*, and every
#: body ever held out against these constants was language, so nothing held out spoke to it
#: at all. Thirty-two more specimens — drawn from the same public collection the held one came
#: from, by two declared draws, every copy either draw returned that the floor refuses — put
#: the number **1 016× higher**.
#:
#: | specimen | its own share | largest extent at which a window of it clears |
#: |---|---|---|
#: | the copy this repository already held | 0.00018 | **314** |
#: | `m.hiriyannacommemorationvolume` | 0.00002 | 500 |
#: | `06kssayingsoflalleshwari` | 0.00042 | 1 000 |
#: | `01wonhyoweb…koreanbuddhism` | 0.00473 | 5 000 |
#: | `60yearsofchinesemisrule…` | 0.00577 | 50 000 |
#: | `02chinulweb…koreanbuddhism` | 0.00630 | 100 000 |
#: | `04hwaomiweb…koreanbuddhism` | 0.00737 | 150 000 |
#: | `TheTheoryOfTheSamdhis…` | **0.00967** | ⛔ **320 000** |
#:
#: ⭐⭐⭐ **AND THE TABLE SAYS WHAT THE NUMBER IS A FUNCTION OF, WHICH IS NOT THE FLOOR.** The
#: extent at which a specimen stops clearing rises with **how close that specimen's own share
#: sits to the floor** — across all thirty-three, with no inversion of consequence. That is
#: not a fact about how long a window has to be; it is arithmetic. A copy sitting 1.03× below
#: the floor has windows above it almost everywhere, and a copy sitting 500× below has them
#: almost nowhere. ⇒ **The accepting side is bounded only by the size of the noisiest copy
#: anyone happens to hold, so this number is a lower bound on itself and will rise again with
#: the next specimen.**
#:
#: ⛔⛔ **WHICH IS WHY THE GUARD BELOW NO LONGER FIRES ON IT — see
#: `refuse_a_rendering_that_does_not_repeat`.** Armed at 315 it certified the band from 315
#: to 320 000 as safe, and that band is where every copy anyone would offer lives. ⚠ *A guard
#: that fires at a hundredth of the true value is worse than no guard, because a caller reads
#: the copies it passes as having been checked.*
#:
#: ⚠ The mechanism, for a reader who wants to know why noise repeats at all: a machine
#: reading is a **deterministic function of the printing**, so a word the printing repeats
#: produces the *same* garbage string every time it is met, and the printing's own recurrence
#: survives into the noise. In one specimen the fragments that recur across a clearing window
#: are garbled body text repeated ten times; in another they are the page numbers of a
#: bibliography, which the wrong-script reader got right because digits survived it.
GREATEST_EXTENT_AT_WHICH_A_WINDOW_OF_A_REFUSED_COPY_HAS_CLEARED = 320000


#: The greatest share **a reading in a script the work cannot be printed in** reaches, over
#: every such reading this repository holds.
#:
#: ⛔⛔⛔ **THE FLOOR ACCEPTS IT, AND IT IS THREE TIMES THE FLOOR.** The copy is the
#: Routledge *Encyclopedia of Philosophy* in ten volumes — ISBN 0415073103, an English work
#: — read by a machine set to an Indic script: **39 129 518** normalised characters of
#: Devanagari carrying not one English word. `LEAST_RECURRENCE` passes it.
#:
#: ⚠ Certified by a **presence, never by an absence**: the rendering carries, at essentially
#: all of its letters, a script the catalogued work cannot be printed in. That establishes
#: the reader was set to a script the printing does not use. ⛔ It is not certified by the
#: copy failing to answer to a word list, which would establish nothing.
#:
#: ⛔⛔⛔ **AND UNTIL THIS SESSION THIS FLOOR WAS ONLY EVER KNOWN TO ERR IN ONE DIRECTION.**
#: The twenty-five copies it ACCEPTS were measured and deleted by the census that drew them,
#: recovered only in the session before this one, and then asked one question — *what
#: language do you carry* — and not the other. Three of them are readings in a script their
#: work cannot be printed in, and this floor passes all three: 0.011922 (a **Kannada** work
#: read in Devanagari), 0.013917 (an English conference proceedings), and this one.
GREATEST_SHARE_A_WRONG_SCRIPT_READING_REACHES = 0.030511

#: The least share reached by a copy carrying the commonest words of its own language across
#: **at least three quarters** of its thousand-character blocks.
#:
#: ⚠ The criterion travels with the number for the reason every criterion in this file does.
#: The copy is `99999990320058mimansakaustubha…devotionalsanskrit1933`, a Sanskrit
#: commentary of 1933 read in Devanagari, carrying declared Sanskrit across **79 %** of
#: itself — and this floor **refuses** it.
LEAST_SHARE_A_COPY_CARRYING_ITS_OWN_LANGUAGE_REACHES = 0.006873

#: ⛔⛔⛔ **THE TWO NUMBERS ABOVE CROSS, SO NO VALUE OF THIS STATISTIC SEPARATES THE TWO
#: SETS — AND THIS IS THE SMALLEST NUMBER OF COPIES ANY VALUE OF IT MISCLASSIFIES.**
#:
#: Measured by asking every value the two sets take, over 26 copies certified to carry their
#: own language and 21 certified to be read in a script their work cannot be printed in:
#:
#: | value | real books refused | wrong-script readings accepted | total |
#: |---|---|---|---|
#: | 0.005765 | 0 | 7 | 7 |
#: | **0.006873** | **0** | **5** | **5** |
#: | 0.008640 | 1 | 4 | 5 |
#: | **0.01** ← published, and not a value either set takes | **2** | **3** | **5** |
#: | 0.016443 | 4 | 1 | 5 |
#: | 0.023635 | 5 | 1 | 6 |
#: | 0.030511 | 7 | 1 | 8 |
#: | **0.033480** | ⛔ **7** | **0** | 7 |
#: | 0.161061 | 25 | 0 | 25 |
#:
#: ⚠ Nine of the forty-seven points the curve has; the whole of it travels on the row
#: `least_error_a_single_value_can_reach` returns, because a curve quoted at nine points
#: reads as monotone and this one is not.
#:
#: ⭐⭐⭐ **MOVING THE FLOOR TRADES A REFUSED BOOK FOR AN ACCEPTED RENDERING OF NOISE, ONE
#: FOR ONE, AND THE TOTAL NEVER FALLS BELOW FIVE.** `LEAST_RECURRENCE` already stands at
#: that minimum, so ⛔ **the published value cannot be improved by moving it** — the two
#: named repairs were a per-language value and a different statistic, and this is the
#: measurement that says the first of them cannot be a better value of *this* statistic.
#:
#: ⛔⛔⛔ **AND TO REFUSE EVERY WRONG-SCRIPT READING IT MUST STAND AT 0.033480 AND REFUSE
#: SEVEN OF THE TWENTY-SIX REAL BOOKS** — better than a quarter of them, and every one of
#: the seven is a copy carrying declared Sanskrit across at least three quarters of itself.
#:
#: ⚠ **AND THE TOTAL IS NOT MONOTONE IN THE VALUE**, which is why the whole curve is
#: published rather than a bound read off it: it reaches five at 0.006873, rises to six at
#: 0.007367, falls back to five at 0.008640, rises to seven at 0.011922 and is five again at
#: 0.016443. ⭐ *The smallest value at which the total stops falling* is not the minimum —
#: the same rule put `LEAST_EXTENT_A_REFUSAL_DISCRIMINATES_AT` 1 686 characters wrong.
LEAST_COPIES_THIS_FLOOR_MISCLASSIFIES_AT_ANY_VALUE = 5

#: Every statistic offered as a replacement for `LEAST_RECURRENCE`, with the worst copy of
#: each certified set under it. ⛔ **NONE OF THEM SEPARATES THE TWO SETS.**
#:
#: ⭐⭐⭐ **TWELVE INSTRUMENTS OF THIS CLASS HAVE NOW FAILED IN THE SAME DIRECTION.** Four
#: were measured in the session before this one — token overlap 0.86 against 0.21,
#: character-weighted 0.74 against 0.05, Devanagari well-formedness 0.95 against 0.96,
#: unfiltered word rate 370.4 against 329.9. Eight more are below. Every one of them scores
#: a reading in a script the work cannot be printed in **as high as or higher than a real
#: book**.
#:
#: | statistic | least over the 26 real books | greatest over the 21 wrong-script readings |
#: |---|---|---|
#: | the floor as it stands, at 12 characters | 0.00687 | ⛔ **0.03051** |
#: | share of distinct **words** that recur | 0.0763 | ⛔ **0.3697** |
#: | share of distinct **two-word** shingles that recur | 0.0094 | ⛔ **0.1388** |
#: | share of distinct **three-word** shingles that recur | 0.00078 | ⛔ **0.0444** |
#: | mean word length | 3.45 | ⛔ **4.62** |
#: | distinct words ÷ words (low is language) | 0.727 | ⛔ **0.0889** |
#: | the floor at a **fixed extent** of 200 000 characters | 0.00497 | ⛔ **0.01248** |
#: | the floor at **two of the copy's own words** of characters | 0.0011 | ⛔ **0.3726** |
#:
#: ⚠ The fixed-extent one is the nearest miss and it fails twice over: inverted by 2.5×, and
#: it cannot be measured at all on 7 of the 26 real books, which are shorter than one window.
#:
#: ⛔ A ninth was offered and is **degenerate**: the copy against a shuffle of itself. A
#: shuffle repeats nothing at twelve characters in **50 of the 51** copies long enough to
#: test, so the ratio is unbounded for a wrong-script reading exactly as it is for a book.
#:
#: ⭐⭐⭐ **THE REASON IS ONE SENTENCE, AND IT IS ALREADY WRITTEN IN THIS FILE.** A machine
#: reading is a **deterministic function of the printing**: a word the printing repeats
#: produces the *same* garbage string every time it is met. So a wrong-script reader carries
#: the printing's repetition across **intact**, and every statistic of a copy's own
#: repetition is measuring the morphology of what was printed rather than whether the reader
#: could read it. ⇒ **The axis is wrong, not the value on it.**
STATISTICS_MEASURED_AGAINST_THIS_FLOOR = (
    "share_of_distinct_12_character_fragments_that_recur",
    "share_of_distinct_words_that_recur",
    "share_of_distinct_two_word_shingles_that_recur",
    "share_of_distinct_three_word_shingles_that_recur",
    "mean_word_length",
    "distinct_words_over_words",
    "share_of_distinct_12_character_fragments_that_recur_at_a_fixed_extent",
    "share_that_recurs_at_two_of_this_copy_s_own_words_of_characters",
    "the_copy_against_a_shuffle_of_itself",
)


@lru_cache(maxsize=16)
def _recurrence(body: str, length: int) -> tuple[int, int, int]:
    """`(distinct fragments, how many recur, the most frequent one's count)`.

    ⛔ Case-sensitive and over `normalised` text, because that is exactly the body `resolve`
    searches. ⚠ *A measurement whose subject is not the thing being claimed about has
    measured nothing* — a recurrence taken over a lower-cased copy would describe a document
    no locus in this file resolves against.
    """
    if len(body) < length:
        return 0, 0, 0
    counts = Counter(body[at : at + length] for at in range(len(body) - length + 1))
    recurring = sum(1 for seen in counts.values() if seen > 1)
    return len(counts), recurring, max(counts.values())


def recurrence_of(edition: Edition, *, length: int = RECURRENCE_MEASURED_AT) -> dict[str, Any]:
    """How much of a rendering repeats itself. ⭐ Complete — every position, never a sample.

    ⚠ A cap nobody states reads as complete coverage, so this one takes no cap: the count is
    over every fragment of `length` characters in the copy.
    """
    body = edition.normalised
    distinct, recurring, most = _recurrence(body, length)
    return {
        "edition": edition.key,
        "fragment_length": length,
        "distinct_fragments": distinct,
        "fragments_that_recur": recurring,
        "share_that_recurs": (round(recurring / distinct, 6) if distinct else None),
        "the_most_frequent_fragment_occurs": most,
        "measured_over": "every position of the rendering, not a sample",
        # ⭐⭐ Published on every row beside the share, because the share alone cannot be read:
        #   below this extent a real book fails this measurement as surely as a rendering of
        #   noise does, and only this number on the row would say so.
        "characters_measured": len(body),
        "the_extent_a_low_share_means_anything_at": LEAST_EXTENT_A_REFUSAL_DISCRIMINATES_AT,
        "a_low_share_here_is_about_the_copy": len(body) >= LEAST_EXTENT_A_REFUSAL_DISCRIMINATES_AT,
        # ⛔⛔⛔ AND THE OTHER SIDE HAS NO BOUND TO PUBLISH, WHICH THE ROW MUST SAY RATHER
        #   THAN OMIT. This field used to carry a number and the boolean beside it read
        #   `True` for every real copy, which is exactly how a row certifies something
        #   nothing measured. There is no extent at which clearing this floor is known to
        #   mean anything, so what travels is the largest extent at which a rendering of
        #   noise has cleared it anyway, and whether this copy is even that long.
        "the_greatest_extent_at_which_a_window_of_a_refused_copy_has_cleared": (
            GREATEST_EXTENT_AT_WHICH_A_WINDOW_OF_A_REFUSED_COPY_HAS_CLEARED
        ),
        "this_copy_is_longer_than_that": (
            len(body) > GREATEST_EXTENT_AT_WHICH_A_WINDOW_OF_A_REFUSED_COPY_HAS_CLEARED
        ),
        # ⛔⛔⛔ AND THE ACCEPTING SIDE NOW HAS A WHOLE COPY AGAINST IT, NOT A WINDOW.
        #   For four sessions the strongest thing that could be said here was that a WINDOW
        #   of a refused copy clears this floor. The twenty-five copies this floor ACCEPTS
        #   were measured and deleted by the census that drew them and were recovered only
        #   last session, and three of them are readings in a script their work cannot be
        #   printed in - the largest 39 129 518 characters, clearing this floor by 3.05x.
        "the_greatest_share_a_wrong_script_reading_reaches": (
            GREATEST_SHARE_A_WRONG_SCRIPT_READING_REACHES
        ),
        "this_copy_repeats_more_than_that": (
            (recurring / distinct if distinct else 0.0)
            > GREATEST_SHARE_A_WRONG_SCRIPT_READING_REACHES
        ),
        "a_high_share_here_is_about_the_copy": (
            "⛔ NOT ESTABLISHED, AT ANY EXTENT OR ANY VALUE. Three copies this floor "
            "ACCEPTS are certified readings in a script their work cannot be printed in, at "
            "0.011922, 0.013917 and "
            f"{GREATEST_SHARE_A_WRONG_SCRIPT_READING_REACHES} - the last of them an English "
            "encyclopaedia of 39 129 518 characters read in Devanagari, which clears this "
            "floor by more than three times. ⛔ And no value repairs it: over 26 copies "
            "certified to carry their own language and 21 certified wrong-script, the least "
            f"any value of this statistic misclassifies is "
            f"{LEAST_COPIES_THIS_FLOOR_MISCLASSIFIES_AT_ANY_VALUE}, which is what the "
            "published value already misclassifies. ⚠ A copy above the number on this row "
            "has been shown only to repeat more than the noisiest reading held"
        ),
        # ⛔⛔⛔ AND THE LOW SIDE IS NOT ABOUT THE READING EITHER, WHICH THIS ROW SAID FOR
        #   THREE SESSIONS BY NAMING A CAUSE. Measured over sixty copies of one public
        #   archive: below this floor sit two whole books carrying the commonest words of
        #   their own language across 79 % and 83 % of themselves.
        "a_low_share_here_is_about_the_reading": (
            "⛔ NOT ESTABLISHED. This floor was fitted to six English renderings and one "
            "Devanagari rendering of an English book. Asked of sixty-one copies it sits BELOW "
            "every one of the twelve carrying English (0.0125 to 0.161) and INSIDE the "
            "range of the fourteen carrying Sanskrit or Hindi (0.00687 to 0.0892), which "
            "straddle it. ⚠ Twelve characters of English is about two words and twelve characters of "
            "a Devanagari compound is part of one, so what a low share here is about may be "
            "the LANGUAGE. Ask `language_a_copy_carries`"
        ),
        "what_a_share_near_zero_means": (
            "⛔ that NOTHING IN THIS COPY REPEATS, so every fragment of it resolves exactly "
            "once and resolving exactly once establishes nothing here. ⚠ Both a zero and a "
            "presence are then free to obtain: a spelling searched returns zero because the "
            "rendering cannot express it, and a passage quoted out of the copy's own noise "
            "resolves once and attests whatever it is said to state. ⛔⛔ AND ONLY WHERE THE "
            "COPY IS LARGE ENOUGH FOR IT TO MEAN THAT: asked of every window of two hundred "
            "characters in the real books held here, this floor refuses 1 405 161 of "
            "1 710 541 of them, so under "
            f"{LEAST_EXTENT_A_REFUSAL_DISCRIMINATES_AT} characters a near-zero share is a "
            "fact about the extent and not about the rendering. ⚠ And a share near the floor "
            "from ABOVE is free at EVERY extent this repository has been able to test: a "
            "rendering of noise it holds clears this floor over windows of "
            f"{GREATEST_EXTENT_AT_WHICH_A_WINDOW_OF_A_REFUSED_COPY_HAS_CLEARED} characters"
        ),
    }


def blocks_this_floor_refuses(
    edition: Edition, *, block: int, length: int = RECURRENCE_MEASURED_AT
) -> dict[str, Any]:
    """How much of one copy `LEAST_RECURRENCE` refuses, when the copy is read `block` at a time.

    ⭐ **Complete and disjoint over the copy's characters** — consecutive blocks from offset
    zero, every character in exactly one of them, no overlap. ⚠ The remainder shorter than one
    block is dropped and *reported*.

    ⛔⛔⛔ **AND THAT COMPLETENESS IS OVER THE WRONG NOUN, WHICH COST A CONSTANT.** The
    question a bound on the extent asks is *is there a specimen of real text this long that
    this floor refuses?* — and the specimens are the copy's **windows**, of which this tiling
    reads one phase: at six thousand characters, 283 of the 1 675 741 windows the copies
    actually contain, 0.017 % of them. `LEAST_EXTENT_A_REFUSAL_DISCRIMINATES_AT` was read off
    this function and came out **6 000**; asked of every window by `every_window_of` the same
    copies refuse 5 593 windows at 6 000 and the bound is **7 686**. ⇒ Use `every_window_of`
    to bound an extent. This function is kept because the published table was measured with
    it and a reader must be able to reproduce that table.

    ⚠ *A measurement can be complete over what it counts and a sample of what it is about.*
    """
    body = edition.normalised
    blocks = len(body) // block
    refused = 0
    for at in range(blocks):
        distinct, recurring, _ = _recurrence(body[at * block : (at + 1) * block], length)
        if distinct == 0 or recurring / distinct < LEAST_RECURRENCE:
            refused += 1
    return {
        "edition": edition.key,
        "block_characters": block,
        "fragment_length": length,
        "blocks": blocks,
        "blocks_refused": refused,
        "share_of_blocks_refused": (round(refused / blocks, 4) if blocks else None),
        "characters_in_no_block": len(body) - blocks * block,
        "measured_over": "consecutive disjoint blocks, every character in exactly one",
    }


def every_window_of(
    edition: Edition, *, extent: int, length: int = RECURRENCE_MEASURED_AT
) -> dict[str, Any]:
    """Ask `LEAST_RECURRENCE` of **every window** of `extent` characters in one copy.

    ⭐⭐⭐ **EVERY STARTING OFFSET, NOT A TILING PHASE.** A bound on the extent is an
    existential claim — *no specimen of real text this long is refused* — and every contiguous
    run of `extent` characters in a real book is such a specimen. `blocks_this_floor_refuses`
    reads one phase of them, which at six thousand characters is 283 of 1 675 741; this reads
    all of them, and the two bounds it produces differ by 1 686 characters.

    ⚠ The windows overlap, so `windows_refused` is not a count of independent specimens and
    must not be read as a rate. `refused_regions` — maximal runs of consecutive refused
    offsets — is published beside it, because a thousand overlapping windows of one bad
    passage and a thousand scattered ones are different findings and the count alone cannot
    tell them apart.

    ⛔ Both sides are counted. A copy is refused below the floor and cleared at or above it,
    and which of the two is the error depends on what the copy is: for a real book a refusal
    is the error, for a rendering of noise a clearance is. Publishing only one of them is how
    the accepting side went a session unmeasured.
    """
    body = edition.normalised
    per = extent - length + 1
    fragments = [body[at : at + length] for at in range(len(body) - length + 1)]
    if per <= 0 or len(fragments) < per:
        return {
            "edition": edition.key,
            "extent": extent,
            "fragment_length": length,
            "windows": 0,
            "windows_refused": 0,
            "windows_cleared": 0,
            "refused_regions": 0,
            "least_share": None,
            "greatest_share": None,
            "measured_over": "every window of this extent, at every offset",
            "why_there_are_none": (
                f"this copy carries {len(body)} normalised characters, fewer than the "
                f"{extent} one window needs"
            ),
        }
    seen: Counter[str] = Counter()
    distinct = 0
    recurring = 0
    for at in range(per):
        fragment = fragments[at]
        count = seen.get(fragment, 0)
        if count == 0:
            distinct += 1
        elif count == 1:
            recurring += 1
        seen[fragment] = count + 1
    windows = len(fragments) - per + 1
    refused = 0
    regions = 0
    previous_was_refused = False
    least = 2.0
    greatest = -1.0
    for at in range(windows):
        share = recurring / distinct if distinct else 0.0
        if share < least:
            least = share
        if share > greatest:
            greatest = share
        if share < LEAST_RECURRENCE:
            refused += 1
            if not previous_was_refused:
                regions += 1
            previous_was_refused = True
        else:
            previous_was_refused = False
        if at + 1 < windows:
            leaving = fragments[at]
            count = seen[leaving]
            if count == 1:
                distinct -= 1
                del seen[leaving]
            else:
                if count == 2:
                    recurring -= 1
                seen[leaving] = count - 1
            entering = fragments[at + per]
            count = seen.get(entering, 0)
            if count == 0:
                distinct += 1
            elif count == 1:
                recurring += 1
            seen[entering] = count + 1
    return {
        "edition": edition.key,
        "extent": extent,
        "fragment_length": length,
        "windows": windows,
        "windows_refused": refused,
        "windows_cleared": windows - refused,
        "refused_regions": regions,
        "least_share": round(least, 6),
        "greatest_share": round(greatest, 6),
        "measured_over": "every window of this extent, at every offset",
    }


def one_per_cent_grid(length: int, *, start: int = 300) -> tuple[int, ...]:
    """Extents to ask a bound of: one per cent resolution at every scale, `start` upward.

    ⭐ **A BOUND QUOTED WITHOUT ITS GRID READS AS EXACT, AND EVERY BOUND HERE IS A GRID
    POINT.** The refusing side's first published value for one held-out body was 2 000 only
    because the grid it was taken on jumped 2 000 → 5 000. So the grid is a named thing that
    travels with the number, rather than a literal buried in whichever caller took it: step 1
    from 300 to 1 000, 10 to 10 000, 100 to 100 000, and so on, which locates a bound to
    within one per cent of itself wherever on the scale it lands.

    ⚠ It is still a grid. Nothing here rules out a clearance strictly between two of its
    points, and a value read off it is the largest **grid point** that clears.
    """
    points: list[int] = []
    at, step = start, 1
    while at <= length:
        points.append(at)
        at += step
        if at >= step * 1000:
            step *= 10
    return tuple(points)


def largest_extent_at_which_a_window_clears(
    edition: Edition,
    *,
    grid: Sequence[int] | None = None,
    length: int = RECURRENCE_MEASURED_AT,
) -> dict[str, Any]:
    """The accepting side's number for ONE copy, measured rather than quoted.

    The largest extent on `grid` at which **any** window of this copy still CLEARS
    `LEAST_RECURRENCE`. Asked of a rendering the floor refuses, it says how long a stretch of
    that rendering passes the floor anyway — which is the entire content of
    `GREATEST_EXTENT_AT_WHICH_A_WINDOW_OF_A_REFUSED_COPY_HAS_CLEARED`.

    ⛔⛔⛔ **THE SUPREMUM, NOT THE FIRST EXTENT THAT CLEARS NOTHING.** The count is not
    monotone in the extent on this side either: one specimen clears 21 850 windows at 100 000
    and 25 497 at 150 000. *The smallest extent at which nothing clears* is the rule that put
    the refusing bound 1 686 characters wrong, and it is wrong here for the same reason.

    ⭐ Termination is not an accident of the grid. A copy whose own share is under the floor
    must refuse the one window that is the whole copy, so the value is bounded by the copy's
    own length.
    """
    body = edition.normalised
    points = tuple(grid) if grid is not None else one_per_cent_grid(len(body))
    distinct, recurring, _ = _recurrence(body, length)
    highest: int | None = None
    clearing = 0
    checked = 0
    for extent in points:
        measured = every_window_of(edition, extent=extent, length=length)
        if not measured["windows"]:
            continue
        checked += 1
        if measured["windows_cleared"]:
            highest = extent
            clearing += 1
    return {
        "edition": edition.key,
        "characters": len(body),
        "fragment_length": length,
        "share_that_recurs": (recurring / distinct if distinct else None),
        "largest_extent_at_which_a_window_clears": highest,
        "the_accepting_bound_this_copy_alone_would_set": (
            highest + 1 if highest is not None else None
        ),
        "extents_checked": checked,
        "extents_at_which_some_window_clears": clearing,
        "the_grid_it_was_taken_on": {
            "least": points[0] if points else None,
            "greatest": points[-1] if points else None,
            "points": len(points),
            "resolution": "one per cent of the extent, at every scale",
        },
        "measured_over": "every window of each extent, at every offset",
    }


# --------------------------------------------------------------------------------------
# What language a copy carries, asked with words declared OUTSIDE it
# --------------------------------------------------------------------------------------

#: A word of a rendering: a maximal run of letters and the marks that attach to them.
#:
#: ⛔⛔⛔ **`script_of` CANNOT BE USED TO CUT WORDS, AND THE REASON IS THE WHOLE FUNCTION.**
#: That bucket asks `isalpha`, which is right for the question it answers and wrong for this
#: one: a Devanagari vowel sign is a combining mark, not a letter, so `isalpha` is `False`
#: for it. ⚠ Cutting on that rule shreds real Devanagari into consonant runs — measured on
#: the real Devanagari book this repository holds, it reported a mean word length of **1.36
#: characters**, and every measurement taken over those pieces was a measurement of debris.
#: ⭐ With the marks kept, the same copy reads **4.23**.
#:
#: ⚠ A run must still carry at least one letter, so a bare string of marks is not a word.
def words_of(text: str) -> tuple[str, ...]:
    """Every word of `text`, in order. ⭐ Complete — every position, never a sample."""
    words: list[str] = []
    current: list[str] = []
    for character in text:
        if character.isalpha() or unicodedata.category(character) in _WORD_MARKS:
            current.append(character)
            continue
        if current:
            words.append("".join(current))
            current = []
    if current:
        words.append("".join(current))
    return tuple(word for word in words if any(c.isalpha() for c in word))


#: Combining marks and format characters that belong **inside** a word: `Mn` and `Mc` are the
#: vowel signs, the virama and the nukta; `Cf` is the zero-width joiner, which the archive's
#: reader emits inside conjuncts and which would otherwise cut a word in half.
_WORD_MARKS = frozenset({"Mn", "Mc", "Cf"})

#: ⛔ **THE SHORTEST THING A DECLARED WORD LIST MAY CONTAIN, AND IT IS NOT A CONVENIENCE.**
#:
#: ⭐⭐⭐ **A WORD LIST IS NOT A MEASUREMENT UNTIL THE SHORTEST THING IN IT IS LONGER THAN
#: WHAT NOISE MAKES BY ACCIDENT.** Measured, not argued: with the two-character particles
#: left in — `वा`, `हि`, `एव` — a machine reading of *5000 Years of Kashmir*, an English book
#: read by a machine set to an Indic script and carrying no Sanskrit whatever, scores **370.4
#: declared words per ten thousand**, which is ABOVE the 329.9 of a Sanskrit commentary of
#: 1933 read in its own script. ⛔ The whole of that reading is one two-character word: `वा`
#: occurs **744** times in a copy that contains no Sanskrit. Under the rule below the same
#: copy scores **0.0**.
#:
#: ⚠ Three *characters*, not three letters, and the difference was measured too: a rule of
#: three letters drops `इति`, which occurs 466 times in one refused copy and twice in an
#: English book of 1810 read the same wrong way. Both rules are enforced from the same raw
#: list rather than applied by hand — ⛔ the reading above was produced by a list whose
#: length rule was stated in a comment and never applied.
LEAST_LENGTH_A_DECLARED_WORD_CARRIES = 3

#: The commonest words of a language, **declared here and taken from outside every copy this
#: repository holds** — from grammars and from ordinary knowledge of the language, not read
#: off any rendering measured with them.
#:
#: ⛔⛔⛔ **THAT PROVENANCE IS THE ENTIRE INSTRUMENT.** A term drawn out of a copy resolves in
#: that copy for free — it is the defect `refuse_a_rendering_that_does_not_repeat` exists to
#: catch, and a word list harvested from the corpus would reproduce it exactly. These words
#: were fixed before any copy was measured with them, so a copy that answers to them is
#: answering to something it did not supply.
#:
#: ⭐⭐⭐ **A PRESENCE ESTABLISHES SOMETHING AND AN ABSENCE ESTABLISHES NOTHING**, which is
#: the same asymmetry the guard below is built on: a reader can destroy the evidence of a
#: presence but cannot manufacture it. ⚠ And the absence side is not hypothetical —
#: `dictionaryofastrologybhansin`, a Devanagari astrology dictionary read in Devanagari and
#: legible at any offset opened, scores **21.1** per ten thousand, barely above the
#: certified rendering of noise at 14.7, because a dictionary is headwords and glosses and
#: the commonest words of running prose hardly occur in it.
#:
#: ⚠ Two languages are declared and no more. Two copies the draws returned are in the Arabic
#: script; `words_of` cuts them into words and no list here can meet them, so they measure
#: zero — ⛔ a fact about this list and not about those copies.
COMMONEST_WORDS: Mapping[str, tuple[str, ...]] = {
    "sanskrit_or_hindi": (
        "इति", "एव", "अपि", "यत्", "तत्", "तस्य", "तत्र", "तथा", "यथा", "किन्तु",
        "स्यात्", "चैव", "नाम", "अस्ति", "भवति", "अत्र", "सर्व", "अथ", "वा", "हि",
        "एतत्", "तेन", "एवं", "पुनः", "सह", "यदि", "लिए", "नहीं", "करने", "किया",
        "गया", "उनके", "उसके", "होता", "होती", "कहा", "अपने", "बहुत", "साथ", "जाता",
        "रहा", "करता", "इसके", "जिस", "सकता", "चाहिए", "अनुसार", "प्रकार", "स्थान",
    ),
    "english": (
        "the", "and", "that", "for", "with", "this", "are", "not", "from", "have",
        "which", "was", "his", "but", "they", "were", "been", "their", "would",
        "when", "there", "said", "into", "more", "other",
    ),
}

#: The grid the block measurement below is published on. ⚠ Travelling with the row for the
#: reason every grid in this file does: a share quoted without the block it was taken over
#: reads as a property of the copy, and it is not one — the same copy reads 49 % at a
#: thousand characters and 88 % at twenty thousand.
LANGUAGE_MEASURED_OVER_BLOCKS_OF = (1000, 5000, 20000)


def declared_words_of(language: str) -> tuple[str, ...]:
    """The declared list for `language`, with the length rule **enforced here**, not by hand."""
    if language not in COMMONEST_WORDS:
        raise TextualError(
            f"no word list is declared for {language!r}; declared: "
            f"{sorted(COMMONEST_WORDS)}"
        )
    return tuple(
        word
        for word in COMMONEST_WORDS[language]
        if len(word) >= LEAST_LENGTH_A_DECLARED_WORD_CARRIES
    )


def declared_words_that_occur(edition: Edition, *, language: str) -> dict[str, Any]:
    """How often a copy uses the commonest words of a language it did not supply.

    ⭐ Complete over the copy's words — every one of them, counted once, never a sample.
    ⛔ The rate is per ten thousand words and it is a **rank, not a verdict**: no threshold
    is published here, because any number separating these copies would be fitted to the
    thirty-three this repository happens to hold, and the copies do not fall into two piles.
    """
    terms = declared_words_of(language)
    counts = Counter(words_of(edition.normalised))
    total = sum(counts.values())
    occurrences = {term: counts[term] for term in terms if counts[term]}
    found = sum(occurrences.values())
    return {
        "edition": edition.key,
        "language": language,
        "words_in_the_copy": total,
        "declared_words": len(terms),
        "declared_words_that_occur": len(occurrences),
        "occurrences": found,
        "per_ten_thousand_words": (round(found / total * 10000, 1) if total else None),
        "which_ones": dict(
            sorted(occurrences.items(), key=lambda pair: -pair[1])
        ),
        "where_the_words_came_from": (
            "declared in COMMONEST_WORDS before any copy was measured with them, from "
            "grammars and ordinary knowledge of the language. ⛔ NOT read off any copy: a "
            "term drawn out of a rendering resolves in it for free"
        ),
        "how_to_read_this": (
            "⭐ AS A RANK AND NOT AS A VERDICT. A presence establishes that the copy carries "
            "the language; an absence establishes nothing, because a copy can be legible and "
            "still not be running prose - a Devanagari astrology dictionary held here scores "
            "21.1 against a certified rendering of noise at 14.7. ⛔ No threshold is "
            "published because none is measured"
        ),
    }


def blocks_that_carry_declared_words(
    edition: Edition, *, language: str, block: int
) -> dict[str, Any]:
    """How much **of** a copy carries the language — consecutive disjoint blocks from zero.

    ⭐ **Complete over the copy's characters**, every one in exactly one block, the remainder
    shorter than a block dropped and reported.

    ⛔⛔ **AND THAT IS THE RIGHT NOUN HERE, WHICH IS EXACTLY WHY IT MUST BE SAID.** The same
    completeness was true of the wrong noun once in this file and cost a constant: a bound on
    an *extent* asks whether any specimen of that size exists, and the specimens are the
    copy's windows, of which one tiling phase is a vanishing fraction. The question here is
    different — *how much of this copy is language* — and a tiling answers it exactly,
    because what it partitions is the copy itself.
    """
    if block <= 0:
        raise TextualError("a block must be at least one character")
    terms = frozenset(declared_words_of(language))
    body = edition.normalised
    blocks = len(body) // block
    carrying = 0
    for index in range(blocks):
        piece = body[index * block : (index + 1) * block]
        if terms & set(words_of(piece)):
            carrying += 1
    return {
        "edition": edition.key,
        "language": language,
        "block": block,
        "blocks": blocks,
        "blocks_carrying_a_declared_word": carrying,
        "share_of_the_copy": (round(carrying / blocks, 4) if blocks else None),
        "characters_left_over": len(body) - blocks * block,
        "measured_over": (
            "consecutive disjoint blocks from offset zero - complete over the copy's "
            "characters, which is the noun this question is about"
        ),
    }


def language_a_copy_carries(
    edition: Edition, *, grid: Sequence[int] = LANGUAGE_MEASURED_OVER_BLOCKS_OF
) -> dict[str, Any]:
    """Every declared language, asked of one copy, with the block grid on the row."""
    return {
        "edition": edition.key,
        "characters": edition.searchable_characters,
        "languages": [
            {
                **declared_words_that_occur(edition, language=language),
                "how_much_of_the_copy_carries_them": [
                    blocks_that_carry_declared_words(
                        edition, language=language, block=block
                    )
                    for block in grid
                ],
            }
            for language in sorted(COMMONEST_WORDS)
        ],
        "what_this_does_not_establish": (
            "⛔ THAT THE COPY IS A GOOD READING, OR THAT ITS CATALOGUE ENTRY IS RIGHT. It "
            "establishes that words nobody took out of this copy occur in it, and how much "
            "of it they occur across. ⚠ A copy can carry a language and still have lost most "
            "of what the printing said"
        ),
    }


def least_error_a_single_value_can_reach(
    *,
    carrying_their_own_language: Mapping[str, float],
    read_in_a_script_the_work_cannot_be_printed_in: Mapping[str, float],
    published: float = LEAST_RECURRENCE,
) -> dict[str, Any]:
    """Whether **any** value of one statistic separates the two certified sets, and at what cost.

    ⭐ Complete over the values the two sets take — every distinct one, never a grid. A
    threshold's behaviour changes only at an observed value, so this is the whole curve and
    not a sample of it, and no bound quoted from here needs a grid to travel with it.

    ⛔ **BOTH SIDES ARE REQUIRED AND THE DISJOINTNESS IS ASSERTED, NOT ASSUMED.** A maximum
    over an empty set is how `LEAST_EXTENT_AN_ACCEPTANCE_DISCRIMINATES_AT` came to be
    published off one specimen; a copy in both sets would make the error counts meaningless
    and nothing here would say so.

    ⚠ *Refused* means `share < value`, which is the convention
    `refuse_a_rendering_that_does_not_repeat` uses, so the counts describe that guard and not
    a differently-signed one.
    """
    both = set(carrying_their_own_language) & set(
        read_in_a_script_the_work_cannot_be_printed_in
    )
    if both:
        raise TextualError(
            "the two certified sets share "
            f"{len(both)} copy or copies - {sorted(both)}. ⛔ A copy certified as a reading "
            "and as a wrong-script reading at once makes every error count below a number "
            "about nothing, and a scoring that did not check would report it as a result"
        )
    if not carrying_their_own_language or not read_in_a_script_the_work_cannot_be_printed_in:
        raise TextualError(
            "both certified sets are required and one is empty. ⛔ A separation measured "
            "against nothing is the defect that put an accepting bound 1 016x wrong: a "
            "maximum over a set with no members is not a maximum"
        )
    readings = dict(carrying_their_own_language)
    wrong_script = dict(read_in_a_script_the_work_cannot_be_printed_in)
    curve = []
    for value in sorted(set(readings.values()) | set(wrong_script.values())):
        refused = sorted(key for key, share in readings.items() if share < value)
        accepted = sorted(key for key, share in wrong_script.items() if share >= value)
        curve.append(
            {
                "value": value,
                "real_books_refused": len(refused),
                "wrong_script_readings_accepted": len(accepted),
                "copies_misclassified": len(refused) + len(accepted),
            }
        )
    best = min(curve, key=lambda point: point["copies_misclassified"])
    at_published = {
        "value": published,
        "real_books_refused": sorted(
            key for key, share in readings.items() if share < published
        ),
        "wrong_script_readings_accepted": sorted(
            key for key, share in wrong_script.items() if share >= published
        ),
    }
    at_published["copies_misclassified"] = len(
        at_published["real_books_refused"]
    ) + len(at_published["wrong_script_readings_accepted"])
    least_reading = min(readings, key=lambda key: readings[key])
    greatest_wrong = max(wrong_script, key=lambda key: wrong_script[key])
    return {
        "copies_carrying_their_own_language": len(readings),
        "copies_read_in_a_script_the_work_cannot_be_printed_in": len(wrong_script),
        "the_lowest_real_book": {
            "copy": least_reading,
            "share": readings[least_reading],
        },
        "the_highest_wrong_script_reading": {
            "copy": greatest_wrong,
            "share": wrong_script[greatest_wrong],
        },
        "any_value_separates_them": readings[least_reading] > wrong_script[greatest_wrong],
        "least_copies_any_value_misclassifies": best["copies_misclassified"],
        "the_value_that_reaches_it": best["value"],
        "at_the_published_value": at_published,
        "the_published_value_is_already_least": (
            at_published["copies_misclassified"] == best["copies_misclassified"]
        ),
        "the_least_value_that_refuses_every_wrong_script_reading": next(
            (
                point["value"]
                for point in curve
                if point["wrong_script_readings_accepted"] == 0
            ),
            None,
        ),
        "what_that_value_costs": next(
            (
                point["real_books_refused"]
                for point in curve
                if point["wrong_script_readings_accepted"] == 0
            ),
            None,
        ),
        "the_whole_curve": curve,
        "measured_over": (
            "every distinct value the two sets take - complete, because a threshold's "
            "behaviour changes only at an observed value"
        ),
        "how_to_read_this": (
            "⛔ AS A FACT ABOUT THIS STATISTIC AND THESE COPIES. Both sets are LOWER BOUNDS: "
            "a copy is certified as a reading only by a PRESENCE - the commonest words of a "
            "language nobody took out of it - and as a wrong-script reading only by a "
            "PRESENCE - a script the catalogued work cannot be printed in. ⚠ Every copy "
            "neither channel speaks for is abstained from and counts against nothing"
        ),
    }


def how_a_per_language_floor_would_be_fitted(
    *,
    by_copy: Sequence[Mapping[str, Any]],
    criterion: float,
    block: int = LANGUAGE_MEASURED_OVER_BLOCKS_OF[0],
) -> dict[str, Any]:
    """Sort the certified copies into the buckets a **per-language** floor would be fitted in.

    ⭐⭐⭐ **THIS IS THE FIRST OF THE TWO NAMED REPAIRS, MEASURED RATHER THAN ARGUED.** A
    per-language floor needs a routing rule, and the only language instrument this repository
    has is `COMMONEST_WORDS`, whose **absence establishes nothing**. What the routing does
    with the evidence is a measurement, and it is this one.

    Each row carries `copy`, `share_that_recurs`, `certified` — one of `a_reading`,
    `a_wrong_script_reading`, `not_certified` — and `carries`, a mapping from each declared
    language to the share of the copy's blocks carrying one of its commonest words.

    ⛔ `criterion` and `block` travel on the result. A bucket boundary quoted without them
    reads as a property of the copies and is not one.
    """
    if not by_copy:
        raise TextualError("no copies were offered to route")
    languages = sorted(COMMONEST_WORDS)
    buckets: dict[str, list[Mapping[str, Any]]] = {
        **{language: [] for language in languages},
        "no_declared_language": [],
    }
    for row in by_copy:
        carries = row["carries"]
        landed = "no_declared_language"
        for language in languages:
            if (carries.get(language) or 0) >= criterion:
                landed = language
                break
        buckets[landed].append(row)

    def _summarise(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
        readings = [r for r in rows if r["certified"] == "a_reading"]
        wrong = [r for r in rows if r["certified"] == "a_wrong_script_reading"]
        return {
            "copies": len(rows),
            "certified_readings": len(readings),
            "certified_wrong_script_readings": len(wrong),
            "not_certified": len(rows) - len(readings) - len(wrong),
            "readings_run": (
                [
                    min(r["share_that_recurs"] for r in readings),
                    max(r["share_that_recurs"] for r in readings),
                ]
                if readings
                else None
            ),
            "wrong_script_readings_run": (
                [
                    min(r["share_that_recurs"] for r in wrong),
                    max(r["share_that_recurs"] for r in wrong),
                ]
                if wrong
                else None
            ),
            # ⛔ A value can be fitted in a bucket only if the bucket holds BOTH sides. One
            #   side alone is the original defect of this floor exactly - fitted where it is
            #   loosest, applied where it is tightest - repeated one bucket at a time.
            "a_value_can_be_fitted_here": bool(readings and wrong),
            "and_it_would_separate_them": bool(
                readings
                and wrong
                and min(r["share_that_recurs"] for r in readings)
                > max(r["share_that_recurs"] for r in wrong)
            ),
        }

    summary = {name: _summarise(rows) for name, rows in buckets.items()}
    fittable = [name for name, cell in summary.items() if cell["a_value_can_be_fitted_here"]]
    separating = [name for name in fittable if summary[name]["and_it_would_separate_them"]]
    return {
        "criterion": criterion,
        "block": block,
        "by_bucket": summary,
        "buckets_holding_both_sides": fittable,
        "buckets_where_a_value_would_separate": separating,
        "every_wrong_script_reading_landed_in": sorted(
            {
                name
                for name, rows in buckets.items()
                if any(r["certified"] == "a_wrong_script_reading" for r in rows)
            }
        ),
        "the_bucket_holding_the_wrong_script_readings_holds_no_reading": all(
            summary[name]["certified_readings"] == 0
            for name, rows in buckets.items()
            if any(r["certified"] == "a_wrong_script_reading" for r in rows)
        ),
        "what_this_establishes": (
            "⛔⛔⛔ A PER-LANGUAGE FLOOR IS SORTED BY THE ONE INSTRUMENT WHOSE ABSENCE "
            "ESTABLISHES NOTHING, AND THE SORT PUTS THE TWO SIDES IN DIFFERENT BUCKETS. A "
            "reading in a script the work cannot be printed in answers to no word list, so "
            "it lands where no language is declared - and a floor fitted in a language "
            "bucket is fitted with no copy below it, which is this floor's original defect "
            "one bucket at a time. ⚠ Routing the undeclared bucket to a refusal is not "
            "available either: the copies there that are NOT certified wrong-script include "
            "legible Bengali, Tamil, Urdu and Kashmiri, refused for a fact about the word "
            "list rather than about themselves"
        ),
    }



# --------------------------------------------------------------------------------------
# A LOCAL presence — the passage a locus resolves in, rather than the copy it sits in
# --------------------------------------------------------------------------------------
#
# ⛔⛔⛔ **WHY A LOCAL ONE, WHEN THE GLOBAL FLOOR IS MEASURED UNREPAIRABLE.**
#    `refuse_a_rendering_that_does_not_repeat` gates an attestation by a property of the
#    WHOLE copy, and every statistic of that shape has failed the same way: twelve of them
#    now score a certified rendering of noise as high as or higher than a real book, because
#    a machine reading is a deterministic function of the printing, so the printing's
#    morphology survives into the noise intact.
#
#    ⭐⭐⭐ **AND A COPY CAN CARRY ITS DECLARED LANGUAGE ACROSS FOUR FIFTHS OF ITSELF AND BE
#    GARBAGE AT THE PASSAGE A LOCUS RESOLVES IN.** A share taken over a copy says nothing
#    about one place in it. What an attestation rests on is one passage, so that is what
#    this asks about.
#
# ⭐ REQUIRED, NOT REFUSED, and the polarity is the whole design. The only instrument that
#    has ever worked here is a PRESENCE of something the copy did not supply — the commonest
#    words of a language, fixed in `COMMONEST_WORDS` before any copy was measured. A reader
#    can destroy the evidence of a presence but cannot manufacture it. So this asks for that
#    presence AT THE PASSAGE, and where it is absent the answer is *I cannot attest here* —
#    ⛔ never *this copy is noise*, which is the diagnosis the 18th session withdrew.

#: ⛔⛔⛔ **THE FRAGMENT'S OWN CHARACTERS ARE EXCLUDED FROM THE PASSAGE, AND THAT IS NOT A
#: DETAIL.** A declared word inside the quotation was supplied by the CITATION, not by the
#: copy — the same defect `COMMONEST_WORDS` is declared out-of-corpus to avoid, one scale
#: down. A window that contained the fragment would let a locus carry its own evidence, and
#: the longer the quotation the freer the presence would be.
FLANK_EXCLUDES_THE_FRAGMENT = True

#: The flanks the census below is published on. ⚠ Travelling with the row for the reason
#: every grid in this file does: a share quoted without the flank it was taken over reads as
#: a property of the copy and is not one — the same copy carries a declared word within 50
#: characters of a quarter of its positions and within 2 500 of every one of them.
LOCAL_PRESENCE_MEASURED_AT_FLANKS = (25, 50, 100, 250, 500, 1000, 2500, 5000, 10000, 25000)

#: What word list a locus's **declared** language calls for.
#:
#: ⭐⭐⭐ **THIS IS WHY A LOCAL PRESENCE ESCAPES THE ROUTING THAT DEFEATED A PER-LANGUAGE
#: FLOOR.** `how_a_per_language_floor_would_be_fitted` fails because the only router
#: available is the word list itself, so every wrong-script reading answers to no list and
#: lands in a bucket with no copy below it. Here nothing is routed off the copy: a `Locus`
#: DECLARES its language, and the declaration is made outside the copy by whoever wrote the
#: citation. ⇒ the instrument asks *does this passage carry the language this citation says
#: it is in*, and the copy has no vote in the question.
#:
#: ⛔ A language with no list is an ABSTENTION and not a refusal, and the two must not be
#: spelled the same. Bengali, Tamil, Urdu and Kashmiri copies held here carry a declared
#: word at no flank whatever — measured, all four at 0.0 — and that is a fact about this
#: list, not about those copies.
THE_LANGUAGE_A_LOCUS_DECLARES: Mapping[str, str] = {
    "en": "english",
    "eng": "english",
    "hi": "sanskrit_or_hindi",
    "sa": "sanskrit_or_hindi",
}

#: ⭐⭐⭐ **THE GREATEST FLANK A COPY CERTIFIED AS A READING HAS EVER NEEDED — a maximum over
#: the certified set, and ⛔ therefore a LOWER BOUND ON ITSELF.**
#:
#: Measured over the 25 copies certified as readings by a presence of their own language:
#: the smallest flank at which EVERY position of the copy carries a declared word within it
#: runs from **163** (`gov_in_notification_2022_99`) to **8 828** (`ajitagamavolin_r_bhatt`).
#: ⚠ The next specimen moves it, exactly as `LEAST_EXTENT_AN_ACCEPTANCE_DISCRIMINATES_AT`
#: moved 1 016× when the set it was a maximum over grew from one member to thirty-three.
GREATEST_FLANK_A_CERTIFIED_READING_HAS_NEEDED = 8828

#: ⛔⛔⛔ **THE FLANK AT WHICH A LOCAL PRESENCE BECOMES FREE IN A CERTIFIED RENDERING OF
#: NOISE, AND THE ONE BOUND THIS INSTRUMENT IS ARMED WITH.**
#:
#: Measured over the 21 copies certified — by a presence of a script their catalogued work
#: cannot be printed in, with no word list consulted — to be readings in the wrong script:
#: the smallest flank at which every position of such a copy carries a declared word runs
#: from **16 642** (`scienceandtheindiantradition…`, 53 290 characters) to **306 984**, and
#: ⭐ two of them never reach it at any flank at all. At or above 16 642, a presence in the
#: flanks of a locus is obtainable in a rendering that carries none of the work's words.
#:
#: ⭐⭐⭐ **AND 8 828 < 16 642, SO THE TWO CERTIFIED SETS DO NOT CROSS.** Twelve instruments
#: of this class have crossed; this is the thirteenth and the first that does not. The gap
#: is 1.88×, and a value fitted inside it on ONE of the two draws — the `specimens` draw
#: alone, band (5 129, 16 642), midpoint 10 885 — refuses **0** of the 23 held-out readings
#: and accepts **0** of the 4 held-out wrong-script readings.
#:
#: ⛔ **THE FITTED VALUE IS NOT PUBLISHED AND NOT ARMED, BECAUSE ON THIS EVIDENCE IT IS THE
#: SAME GUARD.** No copy certified either way falls between 8 828 and 10 885, so arming the
#: fitted midpoint would classify all 46 certified copies exactly as the measured bound
#: does, while being a number fitted to them. ⚠ The two differ on exactly ONE of the 65
#: copies held here — `pli_kerala_rare_14973` at 15 968 — and it is a copy NEITHER channel
#: speaks for. ⇒ *given two guards that agree on all the evidence, the one that is not
#: fitted to the evidence is the one to arm.*
LEAST_FLANK_AT_WHICH_A_LOCAL_PRESENCE_IS_FREE_IN_A_RENDERING_OF_NOISE = 16642

#: ⚠ How the two numbers above were measured, carried on every row that quotes them so that
#: a reader never meets one without its provenance.
HOW_THE_FLANK_BOUNDS_WERE_MEASURED = (
    "over 46 certified copies - 25 certified as readings by a PRESENCE of the commonest "
    "words of their own language across at least three quarters of their 1000-character "
    "blocks, and 21 certified as readings in a script their catalogued work cannot be "
    "printed in by a PRESENCE of that script, with no word list consulted. ⛔ Both counts "
    "are LOWER BOUNDS: 13 further copies are abstained from and named, and two declared "
    "languages are all there are. ⚠ The statistic is the smallest flank at which EVERY "
    "position of the copy carries a declared word within it, so it is a worst case over the "
    "copy and is moved by one long stretch of index, table or plate"
)


def word_list_a_locus_calls_for(language: str) -> str | None:
    """The declared list for a locus's language, or `None` — ⛔ which is an ABSTENTION.

    ⭐ `None` says *this instrument cannot speak here*, and a caller that spells it the same
    way as an absence has turned a fact about a word list into a verdict about a copy.
    """
    return THE_LANGUAGE_A_LOCUS_DECLARES.get(language)


def the_passage_a_locus_resolves_in(
    edition: Edition, fragment: str, *, flank: int
) -> dict[str, Any]:
    """The `flank` characters each side of `fragment`, ⛔ the fragment itself excluded.

    ⛔ **The fragment must resolve exactly once**, for the reason `resolve` gives: a passage
    taken around the first of two hits is a passage around whichever the copy happens to
    print first, and a table of contents restates the words of the chapter it points at.
    """
    if flank <= 0:
        raise TextualError(
            f"a flank of {flank} characters reads nothing either side of the fragment. ⛔ A "
            "presence measured over no text is not a presence"
        )
    resolution = resolve(edition, fragment)
    if not resolution.resolved:
        raise TextualError(
            f"{edition.key}: the fragment occurs {resolution.occurrences} time(s), so there "
            "is no one passage it resolves in. ⛔ A local presence is measured around a "
            "located citation or not at all"
        )
    body = edition.normalised
    quoted = normalise(fragment)
    start = body.index(quoted)
    end = start + len(quoted)
    before = body[max(0, start - flank) : start]
    after = body[end : end + flank]
    return {
        "flank": flank,
        "characters_before": len(before),
        "characters_after": len(after),
        "characters_read": len(before) + len(after),
        "the_fragment_is_excluded": FLANK_EXCLUDES_THE_FRAGMENT,
        "why_the_fragment_is_excluded": (
            "⛔ A DECLARED WORD INSIDE THE QUOTATION WAS SUPPLIED BY THE CITATION AND NOT BY "
            "THE COPY. Including it would let a locus carry its own evidence, and the longer "
            "the quotation the freer the presence would be - the same defect that makes a "
            "word list harvested from a corpus resolve in that corpus for free"
        ),
        "passage": before + "\n" + after,
    }


def declared_words_the_passage_carries(
    edition: Edition, fragment: str, *, language: str, flank: int
) -> dict[str, Any]:
    """Which commonest words of `language` occur in the flanks of a located fragment.

    ⭐ Complete over the flanks' words — every one of them, never a sample. ⛔ A count of
    zero is an ABSENCE and establishes nothing about the copy; see `how_to_read_this`.
    """
    terms = frozenset(declared_words_of(language))
    passage = the_passage_a_locus_resolves_in(edition, fragment, flank=flank)
    counts = Counter(word for word in words_of(passage["passage"]) if word in terms)
    return {
        "edition": edition.key,
        "language": language,
        "flank": flank,
        "characters_read": passage["characters_read"],
        "declared_words_that_occur": len(counts),
        "occurrences": sum(counts.values()),
        "carries_the_declared_language": bool(counts),
        "which_ones": dict(sorted(counts.items(), key=lambda pair: -pair[1])),
        "how_to_read_this": (
            "⭐ A PRESENCE ESTABLISHES AND AN ABSENCE DOES NOT. Words nobody took out of "
            "this copy occur in the passage this citation resolves in, which is what an "
            "attestation here rests on. ⛔ Zero of them says only that this instrument "
            "cannot attest at this place - never that the copy is a machine reading that "
            "returned noise, which is a diagnosis this repository has withdrawn"
        ),
    }


def least_flank_at_which_a_passage_carries_a_declared_word(
    edition: Edition,
    fragment: str,
    *,
    language: str,
    cap: int = LEAST_FLANK_AT_WHICH_A_LOCAL_PRESENCE_IS_FREE_IN_A_RENDERING_OF_NOISE,
) -> int | None:
    """The smallest flank at which the passage carries one — ⛔ `None` at or above `cap`.

    ⭐⭐⭐ **A NUMBER, NOT A VERDICT, AND THAT IS WHY IT NEEDS NO FITTED THRESHOLD.** How far
    a reader must look from a citation before meeting a word of the language it declares is
    a measurement of the passage. The two published bounds say how to read it and neither
    was fitted to it: below `GREATEST_FLANK_A_CERTIFIED_READING_HAS_NEEDED` it is inside the
    range every certified reading's *worst* position falls in, and at `cap` a presence is
    free in a certified rendering of noise, so nothing at or above it is reported.
    """
    if cap <= 0:
        raise TextualError("a cap of zero or less admits no flank at all")
    terms = frozenset(declared_words_of(language))
    low, high = 1, cap - 1
    if not (
        terms
        & set(
            words_of(
                the_passage_a_locus_resolves_in(edition, fragment, flank=high)["passage"]
            )
        )
    ):
        return None
    while low < high:
        middle = (low + high) // 2
        passage = the_passage_a_locus_resolves_in(edition, fragment, flank=middle)
        if terms & set(words_of(passage["passage"])):
            high = middle
        else:
            low = middle + 1
    return low


def require_the_passage_to_carry_the_language_the_locus_declares(
    locus: Locus,
    *,
    cap: int = LEAST_FLANK_AT_WHICH_A_LOCAL_PRESENCE_IS_FREE_IN_A_RENDERING_OF_NOISE,
) -> dict[str, Any]:
    """⛔ The candidate successor to a refusing instrument: a **required LOCAL presence**.

    Three outcomes, and ⭐ they are three because collapsing them to two is the defect:

    * **attested** — the passage carries words of the language the locus declares, and the
      row says how far from the citation the nearest one was;
    * **cannot_attest** — no declared word within `cap` characters either side. ⛔ This is
      an ABSTENTION, not a diagnosis: it says this instrument has no positive evidence here,
      and says in terms that nothing follows about the copy.
    * **cannot_measure** — the locus declares a language no list here covers. ⚠ Measured and
      not hypothetical: Bengali, Tamil, Urdu and Kashmiri copies held here carry a declared
      word at NO flank, which is a fact about `COMMONEST_WORDS` and not about them.

    ⛔⛔ **THE CAP IS THE ONLY BOUND AND IT IS NOT FITTED.** See
    `LEAST_FLANK_AT_WHICH_A_LOCAL_PRESENCE_IS_FREE_IN_A_RENDERING_OF_NOISE`: it is a minimum
    over the certified set of noise, of the same shape as every accepting bound here, and
    ⛔ a lower bound on itself.

    ⛔⛔⛔ **AND THE NUMBER THIS RETURNS IS NOT A VERDICT AND MUST NOT BE THRESHOLDED — IT IS
    MEASURED NOT TO SEPARATE.** Over 200 positions swept arithmetically through each copy:
    the certified readings put **47.5 %–100 %** of their positions within 196 characters of a
    declared word, and the certified wrong-script readings put **0 %–32.5 %** — so the COPIES
    separate. But the per-position values overlap outright: a certified reading of 1933
    reaches **1 633** at its worst position and a Bibliotheca Indica commentary **4 626**,
    while a certified rendering of noise reaches **41** at its tenth percentile. ⇒ *a locus
    needing five hundred characters could have come from either*, and a value cutting between
    them would trade a refused citation for an accepted one exactly as `LEAST_RECURRENCE`
    does. ⭐ What separates is `refuse_a_rendering_that_goes_too_far_without_its_declared_language`,
    which asks the same question of the copy's WORST position rather than of this one.
    """
    declared = locus.language or locus.edition.language
    language = word_list_a_locus_calls_for(declared)
    common = {
        "locus": locus.locus,
        "edition": locus.edition.key,
        "declared_language": declared,
        "cap": cap,
        "the_two_bounds": {
            "greatest_flank_a_certified_reading_has_needed": (
                GREATEST_FLANK_A_CERTIFIED_READING_HAS_NEEDED
            ),
            "least_flank_at_which_a_presence_is_free_in_a_rendering_of_noise": cap,
            "how_they_were_measured": HOW_THE_FLANK_BOUNDS_WERE_MEASURED,
        },
    }
    if language is None:
        return {
            **common,
            "outcome": "cannot_measure",
            "word_list": None,
            "what_this_establishes": (
                "⛔ NOTHING ABOUT THIS COPY OR THIS PASSAGE. No list of commonest words is "
                f"declared for {declared!r}, so the instrument has no question to ask here. "
                "⚠ THIS IS AN ABSTENTION AND NOT A REFUSAL, and the difference is the whole "
                "of it: copies in Bengali, Tamil, Urdu and Kashmiri held here carry a "
                "declared word at no flank whatever, and every one of them is legible"
            ),
        }
    least = least_flank_at_which_a_passage_carries_a_declared_word(
        locus.edition, locus.fragment, language=language, cap=cap
    )
    if least is None:
        return {
            **common,
            "outcome": "cannot_attest",
            "word_list": language,
            "what_this_establishes": (
                "⛔ THAT THIS INSTRUMENT HAS NO POSITIVE EVIDENCE AT THIS PLACE, AND NOTHING "
                f"ELSE. Not one of the commonest words of {language} occurs within {cap} "
                "characters either side of the quoted fragment. ⭐ A presence establishes "
                "and an ABSENCE DOES NOT: this says nothing about whether the copy is a "
                "machine reading that returned noise, nothing about whether the passage is "
                "legible, and nothing about whether the citation is right. It says only "
                "that an attestation resting on it would rest on nothing this instrument "
                "can see. ⚠ Quoting a longer passage does not help - the fragment's own "
                "characters are excluded on purpose"
            ),
        }
    return {
        **common,
        "outcome": "attested",
        "word_list": language,
        "least_flank_at_which_the_passage_carries_a_declared_word": least,
        "inside_the_range_every_certified_reading_falls_in": (
            least <= GREATEST_FLANK_A_CERTIFIED_READING_HAS_NEEDED
        ),
        "this_number_does_not_separate_a_reading_from_a_rendering_of_noise": (
            "⛔⛔⛔ AND IT MUST NOT BE THRESHOLDED. Swept over 200 positions of each copy, a "
            "certified reading of 1933 reaches 1 633 at its worst position and a certified "
            "rendering of noise reaches 41 at its tenth percentile: the per-position ranges "
            "OVERLAP. ⭐ The copies separate and the positions do not, because a citation "
            "sits at one place and almost never at the copy's worst one. Ask "
            "`refuse_a_rendering_that_goes_too_far_without_its_declared_language` of the "
            "copy; read this number as a measurement of this passage and nothing more"
        ),
        "what_this_establishes": (
            f"⭐ THAT WORDS NOBODY TOOK OUT OF THIS COPY OCCUR WITHIN {least} CHARACTERS OF "
            "THIS CITATION. The words are fixed in COMMONEST_WORDS before any copy was "
            "measured and are taken out of none of them, so a passage that answers to them "
            "is answering to something it did not supply. ⛔ It does NOT establish that the "
            "passage says what the citation says it says, nor that the copy is a good "
            "reading anywhere else in itself"
        ),
    }


def least_flank_at_which_every_position_carries_a_declared_word(
    edition: Edition, *, language: str, cap: int
) -> int | None:
    """The copy's **worst** position: the smallest flank at which they all carry one.

    ⭐ Complete over every position of the copy, and exact — the covered set is the union of
    one interval per occurrence, so no position is sampled and none is assumed.

    ⛔ A worst case, which is what makes it comparable across copies of very different sizes
    and ⚠ also what makes it movable by a single long stretch of index or plate.
    """
    return _least_flank_covering_every_position(
        edition, terms=frozenset(declared_words_of(language)), cap=cap
    )


def least_flank_over_any_declared_language(
    edition: Edition,
    *,
    cap: int = LEAST_FLANK_AT_WHICH_A_LOCAL_PRESENCE_IS_FREE_IN_A_RENDERING_OF_NOISE,
) -> int | None:
    """The same, over **every** declared list at once — ⛔ a union, not a minimum.

    ⭐ The census below is published on this rather than on the per-language answers,
    because a copy that prints an English apparatus around a Sanskrit text is covered at a
    position by neither list alone and by the two together. ⚠ Taking the smallest of the
    per-language numbers would report a copy as worse than it is, and would do it only for
    the copies that carry two languages — which is a bias with a shape.
    """
    terms: set[str] = set()
    for name in sorted(COMMONEST_WORDS):
        terms.update(declared_words_of(name))
    return _least_flank_covering_every_position(
        edition, terms=frozenset(terms), cap=cap
    )


def _least_flank_covering_every_position(
    edition: Edition, *, terms: frozenset[str], cap: int
) -> int | None:
    body = edition.normalised
    length = len(body)
    if not length:
        return None
    found = _positions_of(body, terms)
    if not found:
        return None

    def covered(flank: int) -> int:
        intervals = []
        for start, end in found:
            low = max(0, end - flank)
            high = min(length - 1, start + flank)
            if low <= high:
                intervals.append((low, high))
        if not intervals:
            return 0
        total = 0
        current_low, current_high = intervals[0]
        for low, high in intervals[1:]:
            if low <= current_high + 1:
                current_high = max(current_high, high)
            else:
                total += current_high - current_low + 1
                current_low, current_high = low, high
        return total + current_high - current_low + 1

    if covered(cap) < length:
        return None
    low, high = 0, cap
    while low < high:
        middle = (low + high) // 2
        if covered(middle) >= length:
            high = middle
        else:
            low = middle + 1
    return low


def _positions_of(body: str, terms: frozenset[str]) -> list[tuple[int, int]]:
    """Every occurrence of a declared term, with its span. ⛔ Cut exactly as `words_of` cuts.

    ⚠ Written out rather than reusing `words_of` because the positions are the point, and
    ⛔ `script_of` CANNOT be used to cut words at all: it asks `isalpha`, and a Devanagari
    vowel sign is a combining mark, so cutting on it read a mean word length of 1.36 for a
    real book that reads 4.23.
    """
    found: list[tuple[int, int]] = []
    current: list[str] = []
    start = 0
    for index, character in enumerate(body):
        if character.isalpha() or unicodedata.category(character) in _WORD_MARKS:
            if not current:
                start = index
            current.append(character)
            continue
        if current:
            if "".join(current) in terms:
                found.append((start, index))
            current = []
    if current and "".join(current) in terms:
        found.append((start, len(body)))
    return found


def whether_a_local_presence_separates(
    *,
    carrying_their_own_language: Mapping[str, int | None],
    read_in_a_script_the_work_cannot_be_printed_in: Mapping[str, int | None],
) -> dict[str, Any]:
    """Score the LOCAL presence against **both** certified sets — ⛔ the noise control is in.

    ⭐⭐⭐ **THE KNOWN-NOISE CONTROL SITS INSIDE THE MEASUREMENT FROM THE FIRST RUN, WHICH IS
    THE ONLY REASON TWELVE EARLIER INSTRUMENTS WERE CAUGHT.** Every one of them scored a
    certified rendering of noise as high as or higher than a real book, and each was found
    because it was never measured on one side alone.

    Each value is the smallest flank at which every position of that copy carries a declared
    word, or `None` where no flank does. ⛔ `None` on the **wrong-script** side is the
    instrument working — that copy never carries one — while `None` on the reading side
    would be a copy in a language no list covers, so the two are counted apart and named.
    """
    both = set(carrying_their_own_language) & set(
        read_in_a_script_the_work_cannot_be_printed_in
    )
    if both:
        raise TextualError(
            f"the two certified sets share {len(both)} copy or copies - {sorted(both)}. ⛔ A "
            "copy certified as a reading and as a wrong-script reading at once makes every "
            "count below a number about nothing"
        )
    if not carrying_their_own_language or not read_in_a_script_the_work_cannot_be_printed_in:
        raise TextualError(
            "both certified sets are required and one is empty. ⛔ A separation measured "
            "against nothing is the defect that put an accepting bound 1 016x wrong"
        )
    readings = {
        key: value
        for key, value in carrying_their_own_language.items()
        if value is not None
    }
    silent_readings = sorted(
        key for key, value in carrying_their_own_language.items() if value is None
    )
    wrong = {
        key: value
        for key, value in read_in_a_script_the_work_cannot_be_printed_in.items()
        if value is not None
    }
    never_wrong = sorted(
        key
        for key, value in read_in_a_script_the_work_cannot_be_printed_in.items()
        if value is None
    )
    greatest_reading = max(readings, key=lambda key: readings[key]) if readings else None
    least_wrong = min(wrong, key=lambda key: wrong[key]) if wrong else None
    separates = bool(
        readings and wrong and readings[greatest_reading] < wrong[least_wrong]
    )
    return {
        "copies_carrying_their_own_language": len(carrying_their_own_language),
        "copies_read_in_a_script_the_work_cannot_be_printed_in": len(
            read_in_a_script_the_work_cannot_be_printed_in
        ),
        "the_greatest_flank_a_reading_needs": (
            {"copy": greatest_reading, "flank": readings[greatest_reading]}
            if greatest_reading
            else None
        ),
        "the_least_flank_a_wrong_script_reading_needs": (
            {"copy": least_wrong, "flank": wrong[least_wrong]} if least_wrong else None
        ),
        "the_two_sets_do_not_cross": separates,
        "how_far_apart": (
            round(wrong[least_wrong] / readings[greatest_reading], 4)
            if separates
            else None
        ),
        "wrong_script_readings_that_carry_a_declared_word_at_no_flank": never_wrong,
        "readings_that_carry_a_declared_word_at_no_flank": silent_readings,
        "why_those_two_lists_are_counted_apart": (
            "⭐ ON THE WRONG-SCRIPT SIDE IT IS THE INSTRUMENT WORKING - a rendering carrying "
            "none of a declared language never answers at any flank. ⛔ On the reading side "
            "it would be a copy in a language no list here covers, which is a fact about "
            "COMMONEST_WORDS and about nothing else, so it is named rather than counted "
            "against the instrument"
        ),
        "how_to_read_this": (
            "⛔ AS A FACT ABOUT THIS STATISTIC AND THESE COPIES, both of whose sets are "
            "LOWER BOUNDS. ⚠ And the positive side is PARTLY CIRCULAR and says so: a copy "
            "is certified a reading by carrying a declared word across three quarters of "
            "its 1000-character blocks, which at a flank near 500 is close to the statistic "
            "being scored. The wrong-script side is NOT circular - it is certified by a "
            "presence of the wrong SCRIPT with no word list consulted - and the copies held "
            "by provenance are not circular either"
        ),
    }

def refuse_a_rendering_that_goes_too_far_without_its_declared_language(
    edition: Edition,
    *,
    language: str,
    what_it_would_make_free: str,
    cap: int = LEAST_FLANK_AT_WHICH_A_LOCAL_PRESENCE_IS_FREE_IN_A_RENDERING_OF_NOISE,
) -> dict[str, Any]:
    """⛔ Refuse a copy whose WORST place is further from its language than noise's is.

    ⭐⭐⭐ **A REFUSING INSTRUMENT BUILT ENTIRELY OUT OF PRESENCES, WHICH THE TWENTIETH
    SESSION CONCLUDED DOES NOT EXIST HERE.** Its conclusion was *an accepting instrument
    exists here and a refusing one does not*, on the ground that the only thing that works is
    a presence of something outside the copy and a presence cannot refuse. What it did not
    consider is a presence measured at the copy's **worst position**: *how far must a reader
    go from ANY point of this copy before meeting one of the commonest words of the language
    it is claimed to be in.* Every observation feeding it is a presence; the statistic is a
    maximum over them; and a maximum can be exceeded, so it refuses.

    ⛔⛔ **WHY IT IS NOT THE THIRTEENTH FAILURE.** The twelve that failed are statistics of
    the copy's own morphology — recurrence, shingles, word length, type-token — and a machine
    reading is a deterministic function of the printing, so the printing's morphology
    survives into the noise intact and every one of them scored a certified rendering of
    noise as high as or higher than a real book. This one is not a statistic of the copy at
    all: it is a distance to words the copy did not supply, fixed in `COMMONEST_WORDS` before
    any copy was measured.

    Measured over both certified sets:

    | | copies | least | greatest |
    |---|---|---|---|
    | certified readings | 25 | 163 | **8 828** |
    | certified wrong-script readings | 21 | **16 642** | 306 984, ⭐ two never |

    ⇒ **the two sets do not cross**, by 1.88×, and a value fitted on the `specimens` draw
    alone — band (5 129, 16 642), midpoint 10 885 — refuses **0** of the 23 held-out readings
    and accepts **0** of the 4 held-out wrong-script readings. ⛔ That fitted value is not
    what is armed: see the cap's own note for why the unfitted bound is the one to arm.

    ⚠ **WHAT IT COSTS, MEASURED.** Of the copies held here it refuses the library scan
    (47 146 — which is the copy the wrong-alphabet finding was made on, so this is the
    instrument working), and it is SILENT over Bengali, Tamil, Urdu and Kashmiri copies that
    are perfectly legible, because no list here covers them. ⛔ That silence is an
    **abstention** — `word_list_a_locus_calls_for` returns `None` and no refusal is raised —
    and it is a fact about `COMMONEST_WORDS`, never about those copies.

    ⚠ It is a **worst case over the copy**, so one long stretch of index, table or plate
    moves it; `cleared_copy_ajitagamavolin_r_bhatt` reaches 8 828 that way and is a real book
    throughout. ⇒ the number returned is the finding, not the boolean.
    """
    list_name = word_list_a_locus_calls_for(language) or language
    if list_name not in COMMONEST_WORDS:
        # ⛔ AN ABSTENTION AND NOT A REFUSAL, and they must not be spelled the same: this
        #    says the instrument has no question to ask, not that the copy failed one.
        return {
            "edition": edition.key,
            "declared_language": language,
            "outcome": "cannot_measure",
            "word_list": None,
            "cap": cap,
            "what_this_establishes": (
                "⛔ NOTHING ABOUT THIS COPY. No list of commonest words is declared for "
                f"{language!r}. ⚠ Bengali, Tamil, Urdu and Kashmiri copies held here carry a "
                "declared word at no flank whatever and every one of them is legible - a "
                "fact about the word list and about nothing else"
            ),
        }
    reached = least_flank_at_which_every_position_carries_a_declared_word(
        edition, language=list_name, cap=cap
    )
    measured = {
        "edition": edition.key,
        "declared_language": language,
        "word_list": list_name,
        "cap": cap,
        "least_flank_at_which_every_position_carries_a_declared_word": reached,
        "greatest_flank_a_certified_reading_has_needed": (
            GREATEST_FLANK_A_CERTIFIED_READING_HAS_NEEDED
        ),
        "how_the_bounds_were_measured": HOW_THE_FLANK_BOUNDS_WERE_MEASURED,
    }
    if reached is None:
        raise TextualError(
            f"{edition.key}: there is a place in this rendering from which not one of the "
            f"commonest words of {list_name} occurs within {cap} characters either side, so "
            f"{what_it_would_make_free} is free to obtain there - a passage quoted around it "
            "carries no evidence that the copy is in the language the citation claims. ⛔⛔⛔ "
            "THE CAUSE IS THE DISTANCE TO A DECLARED WORD AND NOT THE RECURRENCE: this "
            "refusal names itself so that nothing downstream has to sort it from "
            "`refuse_a_rendering_that_does_not_repeat` by its prose. ⚠ Measured over 46 "
            f"certified copies, every one of the 25 certified as a reading reaches a declared "
            f"word within {GREATEST_FLANK_A_CERTIFIED_READING_HAS_NEEDED} characters of every "
            f"one of its positions, and the least any of the 21 certified as a reading in a "
            f"script its work cannot be printed in needs is {cap}. ⛔ AND NOTHING HERE SAYS "
            "THIS COPY IS A MACHINE READING THAT RETURNED NOISE - NO DIAGNOSIS IS MADE HERE AND "
            "THAT IS THIS REFUSAL NAMING ITS OWN LIMIT. It says this instrument has no "
            "positive evidence at one place in it, and an absence establishes nothing. "
            "⚠ Ask `language_a_copy_carries` before believing anything about WHY"
        )
    return {
        **measured,
        "outcome": "accepted",
        "inside_the_range_every_certified_reading_falls_in": (
            reached <= GREATEST_FLANK_A_CERTIFIED_READING_HAS_NEEDED
        ),
        "what_this_establishes": (
            "⭐ THAT FROM EVERY POSITION OF THIS COPY A READER MEETS A WORD THE COPY DID NOT "
            f"SUPPLY WITHIN {reached} CHARACTERS. ⛔ It does not establish that any particular "
            "passage says what a citation says it says, and it does not establish that a "
            "locus in this copy is a good one: the per-POSITION value is measured NOT to "
            "separate a reading from a rendering of noise, only the per-copy worst case is"
        ),
    }


def refuse_a_rendering_that_does_not_repeat(
    edition: Edition, *, what_it_would_make_free: str, length: int = RECURRENCE_MEASURED_AT
) -> dict[str, Any]:
    """⛔ Refuse a copy in which resolving exactly once is free. Returns the measurement.

    ⭐⭐⭐ **A RENDERING IN WHICH NOTHING REPEATS ANSWERS EVERY QUESTION EXACTLY ONCE, AND
    THAT DEFEATS AN ABSENCE AND A PRESENCE ALIKE.** The second-printing test was retired
    because its verdict was a zero — under an absence every way a reader can fail turns a hit
    into a zero, and a zero is a pass. The replacement requires a **presence**, on the ground
    that a reader can destroy the evidence of a presence but cannot manufacture it.

    ⛔⛔⛔ **THAT IS TRUE OF A READER THAT LOSES TEXT AND FALSE OF ONE THAT INVENTS IT.**
    Measured over a library scan in this repository's cache, whose machine reading returned a
    quarter of a million characters of noise: **44 of 246 689** distinct twelve-character
    fragments recur. So a passage quoted out of that copy's own noise resolves **exactly
    once**, carries as many letters of an Indic script as any bound requires, and *attests a
    rule nobody has ever stated*. ⇒ **A presence is free wherever nothing repeats**, and the
    verdict shape does not save an instrument from a rendering that repeats nothing.

    ⚠ This is the guard both absence instruments were missing and the attestation instrument
    was armed without: every guard before it asks whether the copy was **read**, and a copy
    read in the wrong alphabet answers yes to all of them.

    ⛔⛔⛔ **AND ITS OWN PRINCIPLE FALSIFIED ITS OWN DIAGNOSIS.** *A reader can destroy the
    evidence of a presence but cannot manufacture it* — so words fixed in `COMMONEST_WORDS`
    before any copy was measured, and taken out of none of them, resolve in a copy only
    because the copy has them. Asked that way, copies this refusal used to call machine
    readings that returned noise turn out to carry the commonest words of their own language
    across four fifths of themselves. ⇒ The refusal stands on what it measures; ⛔ the cause
    it named is gone.
    """
    measured = recurrence_of(edition, length=length)
    share = measured["share_that_recurs"]
    if share is None:
        raise TextualError(
            f"{edition.key}: this rendering is shorter than the {length} characters "
            "recurrence is measured at, so nothing can be established about what a "
            "resolution in it is worth. ⛔ A copy too small to repeat cannot witness"
        )
    if share < LEAST_RECURRENCE and (
        edition.searchable_characters < LEAST_EXTENT_A_REFUSAL_DISCRIMINATES_AT
    ):
        # ⛔⛔⛔ STILL A REFUSAL — a resolution in a copy this small is free for exactly the
        #    reason it is free in noise — but NOT the refusal below, which names a cause this
        #    measurement did not take. ⭐ *A refusal that states an unmeasured cause has
        #    agreed with a claim for reasons unrelated to it.*
        raise TextualError(
            f"{edition.key}: {measured['fragments_that_recur']} of "
            f"{measured['distinct_fragments']} distinct {length}-character fragments of this "
            f"rendering occur more than once - a share of {share}, under the "
            f"{LEAST_RECURRENCE} required, so {what_it_would_make_free} is free to obtain "
            "here and this is a refusal. ⛔⛔⛔ BUT THE CAUSE IS THE EXTENT AND NOT THE "
            f"RENDERING: this copy carries {edition.searchable_characters} searchable "
            f"characters, under the {LEAST_EXTENT_A_REFUSAL_DISCRIMINATES_AT} this floor was "
            "measured to discriminate at, and at that size REAL BOOKS FAIL IT TOO - asked of "
            "every window of this extent, 5 593 windows of the real copies held here are "
            "refused at six thousand characters and one is still refused at 7 685. ⚠ Nothing "
            "measured says this is a machine reading that returned noise, and nothing here "
            "says it is not"
        )
    if share < LEAST_RECURRENCE:
        # ⛔⛔⛔ THE REFUSAL STANDS AND THE CAUSE IT USED TO NAME DOES NOT. What is measured
        #    is that little in this copy repeats, and that is enough to refuse: a presence is
        #    free wherever nothing repeats, whatever made the copy that way. ⚠ What this
        #    message asserted for three sessions - *it is a machine reading that returned
        #    noise* - is a DIAGNOSIS, and it is now measured to be false of copies it fires
        #    on. See `LEAST_RECURRENCE`: a Bibliotheca Indica edition of a Sanskrit
        #    commentary, refused here, carries declared Sanskrit across 82.6 % of itself at
        #    a rate 0.5 % from a copy this same floor accepts.
        raise TextualError(
            f"{edition.key}: {measured['fragments_that_recur']} of "
            f"{measured['distinct_fragments']} distinct {length}-character fragments of this "
            f"rendering occur more than once - a share of {share}, against the {LEAST_RECURRENCE} "
            f"required. ⛔⛔⛔ LITTLE IN THIS COPY REPEATS, so {what_it_would_make_free} is "
            "free to obtain: a fragment of it resolves exactly once whether or not the copy "
            "says anything, and that is the whole of this refusal. ⭐ THE EXTENT IS NOT THE "
            "CAUSE - this refusal names itself so that nothing downstream has to sort these "
            "two branches by their prose. ⚠ This copy is NOT mute "
            f"and NOT out of extent - it carries {edition.searchable_characters} searchable "
            f"characters, over the {LEAST_EXTENT_A_REFUSAL_DISCRIMINATES_AT} at which every "
            "window of every real copy held clears this floor - and it is not the alphabet "
            "that is wrong either. ⛔⛔⛔ AND NOTHING HERE SAYS IT IS A MACHINE READING THAT "
            "RETURNED NOISE, WHICH THIS REFUSAL USED TO SAY AND WAS WRONG TO. Measured over "
            "sixty-one copies, fifty-seven of them from one public archive, this floor sits "
            "BELOW every copy carrying English and INSIDE the range of the copies carrying "
            "Devanagari, and two whole books it refuses carry the commonest words of their "
            "own language across 79 % and 83 % of themselves. ⚠ Ask `language_a_copy_carries` before believing "
            "anything about WHY this copy does not repeat"
        )
    # ⛔⛔⛔ THE ACCEPTING SIDE IS NOT ARMED, AND THAT IS A DECISION WITH A MEASUREMENT
    #    UNDER IT RATHER THAN A CONVENIENCE.
    #
    #    It WAS armed, at 315 - the supremum over the one rendering of noise this repository
    #    then held. Thirty-two further specimens, drawn from the same public collection by two
    #    declared draws, put that number at 320 000: a copy carrying no language at all clears
    #    this floor over windows spanning 96.69 % of itself.
    #
    #    ⛔ At 320 000 the arm refuses every copy anyone would offer. Measured, not argued: it
    #    fails 44 of this suite's own tests, and the copies it would refuse include every
    #    fixture every attestation and absence in this file is built on. ⭐ And there is no
    #    honest smaller value, because the extent at which a specimen stops clearing tracks
    #    how close its own share sits to the floor - not the extent - so the next specimen
    #    moves it again.
    #
    #    ⇒ ⭐⭐⭐ **ARMED AT 315 THIS GUARD WAS WORSE THAN ABSENT.** It refused copies under 315
    #    and passed everything above, and a caller reads what a guard passes as checked - so it
    #    certified the whole band from 315 to 320 000, which is where every real copy lives, on
    #    the strength of a number a thousand times too small. The fifteenth session declined to
    #    arm this side saying it *would refuse every fixture the suite is built from*; the
    #    sixteenth overturned that as having used the refusing side's number. ⛔ The reason was
    #    right and the number it was argued with was wrong, and the accepting side's OWN number
    #    says the same thing 1 016× louder.
    #
    #    ⚠ What replaces the refusal is not silence: every row `recurrence_of` returns carries
    #    the 320 000 and says in terms that no extent has been established at which clearing
    #    this floor means anything.
    #
    # ⛔⛔⛔ **AND CLEARING THIS FLOOR IS NOW MEASURED TO ESTABLISH NOTHING AT ALL, WHICH IS
    #    A STRONGER STATEMENT THAN THE ONE ABOVE AND WAS MADE ON EVIDENCE THAT DID NOT EXIST
    #    WHEN THE ONE ABOVE WAS WRITTEN.** The paragraphs above reason from a WINDOW of a
    #    refused copy. Three WHOLE copies this floor accepts are certified - by a presence of
    #    a script their catalogued work cannot be printed in, never by a word count - to be
    #    readings in the wrong script, and the largest is 39 129 518 characters of Devanagari
    #    produced by a machine set to the wrong script over an English encyclopaedia. It
    #    clears this floor by 3.05x. See `GREATEST_SHARE_A_WRONG_SCRIPT_READING_REACHES`.
    #
    # ⛔ So the return below is a MEASUREMENT and not a certificate, and the row it returns
    #    says so on two fields. A caller reads what a guard passes as checked - that is the
    #    reason the accepting side is not armed, and it is now the reason it must not be.
    return measured


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

    ⭐⭐⭐ **AND A THIRD LIMIT, WHICH IS THE ONE THAT LOOKS LIKE SUCCESS: THE COPY MUST HAVE
    BEEN SHOWN TO SAY ANYTHING AT ALL.** An absence over a copy that rendered to nothing
    returns zero for every spelling, over any alphabet, at any length — the strongest-looking
    absence this module can produce and the emptiest. ⛔ It is not hypothetical: a printing
    of the right work, retrieved and digested by this repository, is 219 pages of page images
    whose rendering carries no text, and its extractor still reports 218 characters because
    it joined the empty pages with newlines. ⇒ `positive_control` is a fragment the copy is
    expected to contain, and it must resolve **exactly once** before any zero here is
    written down.
    """

    claim: str
    alphabet: Sequence[str]
    edition: Edition
    #: Each hit, as `(spelling, what stands around it)`.
    occurrences: Sequence[tuple[str, str]]
    what_the_hits_do_say: Sequence[str]
    #: ⛔ Words this copy must be shown to contain, so that a zero elsewhere in it means
    #: something. ⚠ Required, and required to resolve exactly once: an absence is a claim
    #: about a copy that was read, and nothing else in this row distinguishes a copy that is
    #: silent about the rule from a copy that is silent about everything.
    positive_control: str = ""

    def __post_init__(self) -> None:
        """⛔ Refuse an absence over a copy that has not been shown to speak."""
        if not self.edition.carries_searchable_text:
            raise TextualError(
                f"{self.edition.key}: an absence may not be measured over a copy whose "
                "rendering carries no searchable text. ⛔ Every spelling returns zero because "
                "nothing was ever read, and the row would be indistinguishable from a copy "
                "that genuinely does not state the rule. ⚠ Note the rendering's own character "
                f"count is {self.edition.rendering.characters}, which is not zero and is not "
                "text"
            )
        # ⛔⛔ CHECKED BEFORE THE CONTROL, BECAUSE A CONTROL CANNOT REPAIR THIS. Measured on a
        #    real copy: a library scan of an English printing whose machine reading carries
        #    246 777 characters and no Latin at all. Every guard above passes it.
        required = scripts_required_by(self.alphabet)
        if not required:
            raise TextualError(
                f"{self.edition.key}: the alphabet searched is written in no script at all - "
                "every spelling in it is punctuation or digits. ⛔ Nothing can establish that "
                "this rendering could have expressed it, so the zeroes cannot be read"
            )
        missing = sorted(s_ for s_ in required if not self.edition.carries_script(s_))
        if missing:
            raise TextualError(
                f"{self.edition.key}: the alphabet is written in {sorted(required)} and this "
                f"rendering carries no {missing} at all, though it carries "
                f"{self.edition.searchable_characters} searchable characters. ⛔ Every "
                "spelling returns zero because the machine reading cannot express one of "
                "them, not because the copy is silent - and this copy passes every check "
                "that asks whether it was read"
            )
        if not self.positive_control.strip():
            raise TextualError(
                f"{self.edition.key}: an absence needs a positive control - words this copy "
                "is expected to contain, resolved in it. ⛔ Without one the row cannot tell a "
                "copy that is silent about the rule from a copy that is silent about "
                "everything, and both print the same reassuring zero"
            )
        # ⭐⭐⭐ AND THE CONTROL MUST BE IN THE ALPHABET'S OWN SCRIPT. A control proves the
        #    copy was read; it proves the copy was read IN THE SCRIPT IT IS WRITTEN IN, and
        #    nothing more. ⛔ Over the library scan above, a control quoted from the copy's
        #    own noise resolves exactly once - as 1 188 of 1 188 candidate fragments do,
        #    because nothing in a noise rendering repeats - and would license a perfect
        #    twelve-spelling absence in an alphabet the rendering contains none of.
        control_scripts = scripts_in(self.positive_control)
        if not required & set(control_scripts):
            raise TextualError(
                f"{self.edition.key}: the positive control is written in "
                f"{sorted(control_scripts) or 'no script'} and the alphabet in "
                f"{sorted(required)}. ⛔ A control in another script shows only that the copy "
                "was read in THAT script, which is exactly the state this guard exists to "
                "catch: it resolves, the row is written, and every zero in it is a property "
                "of the machine reading"
            )
        # ⛔⛔⛔ AND CHECKED BEFORE THE CONTROL IS RESOLVED, BECAUSE IN A COPY THAT
        #    REPEATS NOTHING THE RESOLUTION BELOW IS FREE. Every guard above asks
        #    whether the copy was READ; none asks what a resolution in it is WORTH.
        #    ⚠ Over the library scan held here, 44 of 246 689 distinct fragments recur,
        #    so a control quoted out of its own noise resolves exactly once and licenses
        #    a whole alphabet of zeroes.
        refuse_a_rendering_that_does_not_repeat(
            self.edition,
            what_it_would_make_free="the positive control's resolution below",
        )
        found = resolve(self.edition, self.positive_control)
        if not found.resolved:
            raise TextualError(
                f"{self.edition.key}: the positive control occurs {found.occurrences} "
                "time(s), so it does not show this copy was read. ⛔ An absence measured "
                "beside a control that did not resolve is an absence over an unknown document"
            )

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
            # ⭐ The proof that the zeroes above were measured over a copy that speaks.
            "the_copy_was_shown_to_be_readable_by": {
                "quoted": normalise(self.positive_control),
                "occurrences": resolve(self.edition, self.positive_control).occurrences,
                "why_this_is_here": (
                    "⛔ an absence over a copy that rendered to nothing returns zero for every "
                    "spelling and is the strongest-looking absence this instrument can print. "
                    "A copy in this repository's cache is 219 pages of page images whose "
                    "rendering carries no text at all, so the guard is not hypothetical"
                ),
            },
            # ⭐⭐⭐ What the control above is WORTH, which is a property of the copy and
            #   not of the control. A copy that repeats nothing resolves every fragment
            #   of itself exactly once, so the reassurance one line up is free there.
            "and_resolving_exactly_once_is_not_free_here": {
                **recurrence_of(self.edition),
                "the_floor_this_had_to_clear": LEAST_RECURRENCE,
            },
            "established_over": dict(self.edition.extent),
            "limit": (
                "⛔ this is an absence from the extent searched, in the spellings listed, in "
                "this rendering. A spelling not listed was not looked for; a part of the "
                "work this copy does not contain was not searched; and a machine reading of "
                "a scan can lose words the page carries"
            ),
        }


# --------------------------------------------------------------------------------------
# Whether an alphabet marks the hand it claims to mark, and whether a zero survives a
# second reader
# --------------------------------------------------------------------------------------


def alphabet_contamination(
    alphabet: Sequence[str],
    edition: "Edition",
    must_not_mark: Sequence[tuple[str, str]],
) -> list[dict[str, Any]]:
    """Which spellings of a marker alphabet fire on material the marker does not mark.

    ⛔ **A SPELLING THAT OCCURS IN THE OTHER HAND'S WORDS MARKS NEITHER HAND.** `must_not_mark`
    is a sequence of `(what it is, the passage)`; each passage must resolve exactly once, and
    any spelling occurring inside one is reported here with the passage that refutes it.

    ⚠ Returned rather than raised, because the contamination is the measurement. The refusal
    is `MarkerAlphabet`, which will not construct while this is non-empty.
    """
    found: list[dict[str, Any]] = []
    for spelling in alphabet:
        needle = normalise(spelling).lower()
        if not needle:
            continue
        for what, passage in must_not_mark:
            body = normalise(passage).lower()
            if needle in body:
                found.append(
                    {
                        "spelling": spelling,
                        "also_marks": what,
                        "the_passage_that_refutes_it": normalise(passage),
                        "that_passage_occurs_in_the_copy": resolve(edition, passage).occurrences,
                    }
                )
    return found


@dataclass(frozen=True)
class MarkerAlphabet:
    """The spellings by which a copy marks ONE hand's material, checked for discrimination.

    ⭐⭐⭐ **AN ALPHABET READ OFF A COPY THAT CARRIES TWO HANDS INHERITS BOTH OF THEM.** The
    twelve spellings this repository marks a second commenting hand by were read off a copy in
    which that hand and the translator are printed on the same pages, and three of the twelve
    turn out to fire on things every printing of the work necessarily has:

    * the honorific by which the **translator himself** is named on his own title page, so a
      zero could only be reached by a printing that does not name its translator;
    * the footnote mark, which is typography and not a word at all;
    * and a phrase in the translation of **the first sutra** - *I shall now explain my work* -
      which is the primary text speaking, located and resolving exactly once in every copy
      held here.

    ⛔⛔⛔ *THE TEST WOULD HAVE REJECTED THE PRINTING IT WAS BUILT TO FIND.* A search for a
    printing free of the second hand, scored on this alphabet, must fail over an unrevised
    printing too - because an unrevised printing still contains sutra 1 and still names its
    translator. ⇒ Three candidate printings failed this test in three different ways, and
    none of the three failures was the presence of the hand.

    ⚠ This class refuses to construct while any spelling is contaminated, so a contaminated
    alphabet cannot license an absence. The measurement itself is
    `alphabet_contamination`, which is always computable and is what gets published.
    """

    #: What the alphabet claims to mark. ⚠ A description of a hand, never a name.
    marks: str
    alphabet: Sequence[str]
    edition: Edition
    #: `(what it is, the passage)` for material this alphabet must NOT mark. ⛔ Each passage
    #: must resolve exactly once in the copy, or it locates nothing and refutes nothing.
    must_not_mark: Sequence[tuple[str, str]]

    def __post_init__(self) -> None:
        if not self.edition.carries_searchable_text:
            raise TextualError(
                f"{self.edition.key}: an alphabet cannot be checked for discrimination "
                "against a copy that renders to no searchable text. ⛔ Every passage would "
                "resolve zero times and every spelling would look clean"
            )
        # ⛔ A resolution here is EVIDENCE, not an address, and a rendering that
        #   repeats nothing resolves every fragment of itself exactly once - see
        #   `refuse_a_rendering_that_does_not_repeat`, which carries the measurement.
        refuse_a_rendering_that_does_not_repeat(
            self.edition,
            what_it_would_make_free=(
                "every passage of the material this alphabet must not mark"
            ),
        )
        if not self.must_not_mark:
            raise TextualError(
                f"{self.edition.key}: an alphabet that marks {self.marks!r} is discriminating "
                "only against something. ⛔ No passage of the material it must NOT mark was "
                "given, so nothing was checked and the check would report success"
            )
        for what, passage in self.must_not_mark:
            found = resolve(self.edition, passage)
            if not found.resolved:
                raise TextualError(
                    f"{self.edition.key}: the passage given for {what!r} occurs "
                    f"{found.occurrences} time(s), so it locates nothing. ⛔ A spelling can "
                    "only be refuted by words shown to be in the copy"
                )
        contamination = alphabet_contamination(self.alphabet, self.edition, self.must_not_mark)
        if contamination:
            named = ", ".join(sorted({str(c["spelling"]) for c in contamination}))
            raise TextualError(
                f"{self.edition.key}: the alphabet claims to mark {self.marks}, and "
                f"{len(contamination)} of its spelling(s) occur in material it must not mark "
                f"- {named}. ⛔⛔⛔ AN ABSENCE SCORED ON THIS ALPHABET IS UNREACHABLE BY ANY "
                "COPY OF THIS WORK, INCLUDING THE ONE IT WAS BUILT TO FIND: the contaminated "
                "spellings are the translator's own honorific, the printer's footnote mark "
                "and a phrase of the first sutra, and a printing free of the second hand "
                "carries all three"
            )

    def as_row(self) -> dict[str, Any]:
        return {
            "finding": "alphabet_discriminates",
            "marks": self.marks,
            "edition": self.edition.key,
            "spellings": list(self.alphabet),
            "checked_against": [
                {
                    "what_it_is": what,
                    "quoted": normalise(passage),
                    "occurrences": resolve(self.edition, passage).occurrences,
                }
                for what, passage in self.must_not_mark
            ],
            "contaminated_spellings": [],
            "limit": (
                "⛔ discriminating against the passages listed, and against nothing else. A "
                "spelling that fires on material nobody thought to check here is a spelling "
                "this row does not catch, which is why the passages are quoted rather than "
                "summarised"
            ),
        }


def reading_disagreement(
    alphabet: Sequence[str], readings: Sequence["Edition"]
) -> list[dict[str, Any]]:
    """The spellings whose zero / not-zero verdict differs between readings of one edition.

    ⛔ **A ZERO IS A PROPERTY OF A READING UNTIL A SECOND READER AGREES WITH IT.** Returned
    rather than raised: the disagreement is the measurement, and `AbsenceAcrossReadings` is
    the refusal built on it.
    """
    out: list[dict[str, Any]] = []
    for spelling in alphabet:
        needle = normalise(spelling).lower()
        counts = [reading.normalised.lower().count(needle) for reading in readings]
        if (min(counts) == 0) != (max(counts) == 0):
            out.append(
                {
                    "spelling": spelling,
                    "hits_by_reading": [
                        {"reading": reading.key, "hits": count}
                        for reading, count in zip(readings, counts)
                    ],
                    "verdict": (
                        "⛔ present on the page and lost by at least one reader. A zero here "
                        "is a fact about that reader"
                    ),
                }
            )
    return out


@dataclass(frozen=True)
class AbsenceAcrossReadings:
    """An absence claimed of a PRINTING, checked against every held reading of that printing.

    ⭐⭐⭐ **THE SAME EDITION, READ THREE TIMES, GIVES THREE DIFFERENT ANSWERS.** Four of the
    twelve spellings marking the second commenting hand flip between zero and not-zero across
    three machine readings of one edition - among them the hand's own claim of a book, which
    is printed on the page and which two of the three readers lose. ⛔ So a *clean pass* on
    the standing second-printing test, had one ever been obtained, would have measured the
    reader and not the printing; and this is measured on copies held, not argued.

    ⚠ **The readings must be shown to be of one edition**, by a fragment resolving exactly
    once in every one of them. Without that tie this class would be comparing two books and
    calling their difference an OCR error - which is the mirror image of the mistake it
    exists to catch.
    """

    claim: str
    alphabet: Sequence[str]
    #: ⛔ Every held rendering of the one printing. At least two, or nothing is checked.
    readings: Sequence[Edition]
    #: ⛔ A fragment resolving EXACTLY ONCE in every reading. It is what makes them one
    #: edition rather than two books.
    the_readings_are_of_one_edition_because: str

    def __post_init__(self) -> None:
        if len(self.readings) < 2:
            raise TextualError(
                "an absence over a printing is checked by disagreement between readings of "
                f"it, and {len(self.readings)} reading(s) were given. ⛔ One reading agrees "
                "with itself perfectly, and that is the state this guard exists to refuse"
            )
        for reading in self.readings:
            if not reading.carries_searchable_text:
                raise TextualError(
                    f"{reading.key}: a reading that carries no searchable text agrees with "
                    "every absence. ⛔ It cannot stand as a check on one"
                )
            # ⛔ A resolution here is EVIDENCE, not an address, and a rendering that
            #   repeats nothing resolves every fragment of itself exactly once - see
            #   `refuse_a_rendering_that_does_not_repeat`, which carries the measurement.
            refuse_a_rendering_that_does_not_repeat(
                reading,
                what_it_would_make_free=(
                    "the fragment tying these readings to one edition, and every "
                    "zero this reading is being asked to confirm"
                ),
            )
            found = resolve(reading, self.the_readings_are_of_one_edition_because)
            if not found.resolved:
                raise TextualError(
                    f"{reading.key}: the fragment tying these readings to one edition occurs "
                    f"{found.occurrences} time(s) here. ⛔ Without it these are two books, and "
                    "their disagreement would be a difference between printings misread as a "
                    "difference between readers"
                )
        disagreement = reading_disagreement(self.alphabet, self.readings)
        if disagreement:
            named = ", ".join(str(d["spelling"]) for d in disagreement)
            raise TextualError(
                f"{len(disagreement)} spelling(s) of this alphabet are found by one reading "
                f"of this edition and lost by another - {named}. ⛔⛔ AN ABSENCE OVER ANY ONE "
                "OF THESE READINGS WOULD BE A PROPERTY OF THAT READING. The marks are on the "
                "page; which of them a search returns depends on which machine read the scan"
            )

    def as_row(self) -> dict[str, Any]:
        return {
            "finding": "absence_survives_a_second_reader",
            "claim": self.claim,
            "readings": [reading.key for reading in self.readings],
            "the_readings_are_of_one_edition_because": {
                "quoted": normalise(self.the_readings_are_of_one_edition_because),
                "occurrences_by_reading": [
                    {
                        "reading": reading.key,
                        "occurrences": resolve(
                            reading, self.the_readings_are_of_one_edition_because
                        ).occurrences,
                    }
                    for reading in self.readings
                ],
            },
            "spellings_whose_verdict_differs_between_readings": [],
            "limit": (
                "⛔ agreement between the readings held, and nothing more. A fourth reader "
                "may lose a word all three of these found, so this row bounds a zero rather "
                "than establishing one"
            ),
        }


#: ⛔ The shortest passage that may stand as an attestation, in letters of its own script.
#:
#: ⭐⭐⭐ **AND IT IS NOT A DEFENCE AGAINST CHANCE RESOLUTION, BECAUSE NO LENGTH BOUND CAN
#: BE.** The first version of this constant was justified as *three times the length at which
#: resolution is free* — and that reasoning is **backwards**. Measured over the copies held,
#: the share of fragments resolving **exactly once** RISES with length, in a real book and in
#: a rendering of noise alike:
#:
#: | letters | a real book | a rendering of noise |
#: |---|---|---|
#: | 8 | 0.460 | 0.993 |
#: | 12 | 0.707 | 1.000 |
#: | 16 | 0.943 | 0.993 |
#: | 24 | 0.993 | 1.000 |
#:
#: ⇒ A **longer** passage resolves exactly once MORE often, not less. Lengthening the bound
#: makes a resolution *cheaper* to obtain, and at 24 letters a real book and pure noise are
#: indistinguishable. ⛔ So this constant does exactly one thing: it refuses a fragment too
#: short to **state a rule at all** — a word or two offered as an attestation. ⭐ What actually
#: makes a resolution mean something is that the passage STATES THE RULE and is quoted in
#: full, so a reader can check it; that is a reader's job and no threshold can do it.
SHORTEST_ATTESTING_PASSAGE = 12


@dataclass(frozen=True)
class IndependentHandAttestation:
    """A rule filed as one HAND's words, found again in a copy that hand could not have touched.

    ⭐⭐⭐ **THE TEST THIS REPLACES ASKED FOR A ZERO, AND A ZERO IS THE ONE MEASUREMENT A
    BROKEN READER PRODUCES FOR FREE.** The retired second-printing test required a candidate
    printing to carry **none** of twelve spellings marking a second commenting hand. It was
    retired for two defects — four of the twelve mark the translator, the translated first
    sutra and the reader's own damage, so no copy of the work can pass; and the same edition
    read three times gives three answers, so a pass would have measured the reader. ⛔ Both
    defects are the same defect: **the verdict was an absence**. Under an absence every way a
    reader can fail turns a hit into a zero, and a zero is a *pass* — so the instrument's
    errors all point at success. ⇒ This class requires a **presence**, and its errors are
    refusals.

    ⛔⛔⛔ **AND ITS ERRORS ARE REFUSALS ONLY ABOVE A FLOOR NOBODY HAD MEASURED.** A reader
    that loses text cannot manufacture a presence; a reader that returns **noise** does —
    every fragment of a rendering that repeats nothing resolves exactly once, so a passage
    quoted out of a copy's own noise attested a rule nobody has ever stated, in a row this
    class constructed without complaint. ⇒ `refuse_a_rendering_that_does_not_repeat` is what
    the verdict shape was resting on, and it was armed a session later than the verdict.

    ⭐⭐ **Discrimination is structural here, not lexical, so there is no alphabet to
    contaminate.** The hand at issue is a reviser of **one translation**; a different
    translator working from the original into another language is outside that reach **by
    construction**, not by survey. ⛔ The translator's own honorific, the translated first
    sutra and the reader's stray asterisk — the four spellings that broke the old alphabet —
    are simply not being scored on, because nothing is being scored on a spelling.

    ⛔⛔ **AND IT DOES NOT DISCHARGE `revised_printing_cannot_witness_the_unrevised_words`.**
    That refusal stands, and it is *restated here as an entry condition*: an attesting copy
    must be a different **translation**, not another printing of the same one, because two
    printings one hand revised agree about the revision. The condition is measured — the
    attesting copy must carry the **original's** script, which a copy of the English
    translation does not.

    ⚠ **What a passing row establishes is smaller than it looks, and the row says so.** It
    establishes that the **rule** was in the work before the hand's reach, not that the
    English **words** are the translator's; and the second translator is himself a modern
    commentator, so two copies agreeing establishes that a rule is not *one* hand's invention
    and nothing more.
    """

    rule: str
    #: What this file publishes the rule as stating.
    the_rule_as_published: str
    #: ⛔ How the rule is filed. The test means nothing over a row filed as the TEXT: a sutra
    #: is not attributed to a hand, so no hand's reach is at issue.
    filed_as: str
    #: The copy the rule is resolved into — the one carrying the hand whose reach is at issue.
    filed_in: Edition
    #: The hand whose reach is at issue. ⚠ A description of a hand, never a name.
    the_hand_whose_reach_is_at_issue: str
    #: What bounds that reach, read off a copy's own page rather than supplied by a recorder.
    the_reach_is_bounded_by: str
    #: The copy outside the reach.
    attested_in: Edition
    #: ⛔ Passages of that copy stating the rule. Each must resolve EXACTLY ONCE there.
    the_attesting_passages: Sequence[str]
    #: Where in the attesting copy, in that copy's own divisions.
    the_locus_there: str
    #: ⛔ The script the ORIGINAL work is written in. The reach condition is measured on it.
    the_original_is_written_in: str
    what_this_does_not_establish: str

    def __post_init__(self) -> None:
        if self.filed_as != "commentary":
            raise TextualError(
                f"{self.rule}: this row is filed as {self.filed_as!r}, so it is attributed to "
                "the TEXT rather than to a hand. ⛔ No hand's reach is at issue and this test "
                "measures nothing over it - a passing row here would read as evidence about a "
                "sutra, which is the confusion the whole file exists to prevent"
            )
        if self.attested_in.key == self.filed_in.key:
            raise TextualError(
                f"{self.filed_in.key}: a copy cannot be the one a hand revised and the one "
                "outside its reach. ⛔ That is not an independent attestation, it is a "
                "re-reading of the copy the question was asked about"
            )
        for where in (self.filed_in, self.attested_in):
            if not where.carries_searchable_text:
                raise TextualError(
                    f"{where.key}: a copy whose rendering carries no searchable text can "
                    "neither raise this question nor answer it. ⛔ Every passage would resolve "
                    "zero times"
                )
        # ⛔⛔⛔ P1 - THE REACH, AND IT IS `revised_printing_cannot_witness_the_unrevised_words`
        #    AS AN ENTRY CONDITION. A second printing of the SAME translation is inside the
        #    hand's reach, and two printings it revised agree about the revision. What puts a
        #    copy outside is that it renders the ORIGINAL rather than the translation - so the
        #    condition is measured on the original's script, in both directions.
        if not self.attested_in.carries_script(self.the_original_is_written_in):
            raise TextualError(
                f"{self.attested_in.key}: this copy carries no {self.the_original_is_written_in} "
                f"at all, though it carries {self.attested_in.searchable_characters} searchable "
                "characters. ⛔ Nothing shows it works from the original rather than from the "
                "translation the hand revised, and a second printing of that translation is "
                "INSIDE the reach: two printings one hand revised agree about the revision. "
                "⚠ This is `revised_printing_cannot_witness_the_unrevised_words` refusing at "
                "the door, and it is not discharged by anything below"
            )
        if self.filed_in.carries_script(self.the_original_is_written_in):
            raise TextualError(
                f"{self.filed_in.key}: the copy the rule is filed in carries "
                f"{self.filed_in.scripts.get(self.the_original_is_written_in, 0)} letters of "
                f"{self.the_original_is_written_in}, so the original's script does not "
                "separate the two copies. ⛔ Then the reach condition is measuring nothing, "
                "and a second printing of one translation could satisfy it"
            )
        # ⛔⛔⛔ P2 - AND IT IS THE ONE THIS CLASS WAS ARMED WITHOUT. Its own limit reads
        #    *a reader can destroy the evidence of a presence but cannot manufacture it*,
        #    which is true of a reader that LOSES text and false of one that INVENTS it.
        #    Measured: in the library scan whose machine reading returned noise, a
        #    fifteen-letter run of that noise resolves exactly once, clears the passage
        #    length floor, carries the original's script - and attested a rule nobody has
        #    ever stated, in a row this class constructed without complaint.
        refuse_a_rendering_that_does_not_repeat(
            self.attested_in,
            what_it_would_make_free="the attesting passage's resolution below",
        )
        if not self.the_attesting_passages:
            raise TextualError(
                f"{self.rule}: no attesting passage was given. ⛔ An attestation is a located "
                "presence or it is a recorder's recollection that he has seen the rule "
                "somewhere else"
            )
        for passage in self.the_attesting_passages:
            # ⛔ A floor on what may be offered as an attestation at all. ⚠ It refuses a
            #   fragment too short to state a rule; it does NOT make a longer one safer, and
            #   the constant's own note carries the measurement that says so.
            letters = sum(
                1 for c in normalise(passage) if script_of(c) == self.the_original_is_written_in
            )
            if letters < SHORTEST_ATTESTING_PASSAGE:
                raise TextualError(
                    f"{self.attested_in.key}: the attesting passage carries {letters} letter(s) "
                    f"of {self.the_original_is_written_in} and at least "
                    f"{SHORTEST_ATTESTING_PASSAGE} are required. ⛔ A fragment this short "
                    "cannot STATE a rule, so its resolving establishes nothing about one. "
                    "⚠ And this bound is not a defence against chance resolution: measured "
                    "over the copies held, the share of fragments resolving exactly once RISES "
                    "with length - 0.460 at eight letters in a real book against 0.993 at "
                    "twenty-four, where a book and pure noise become indistinguishable. ⭐ What "
                    "makes a resolution mean anything is that the passage states the rule and "
                    "is quoted in full for a reader to check"
                )
            # ⛔ P3 - the presence itself, and it is the whole verdict. A copy that was never
            #   read resolves nothing and FAILS here, which is the difference from the test
            #   this replaces: a noise rendering passed that one perfectly.
            found = resolve(self.attested_in, passage)
            if not found.resolved:
                raise TextualError(
                    f"{self.attested_in.key}: the attesting passage occurs "
                    f"{found.occurrences} time(s), so it locates nothing. ⭐ A rule is "
                    "attested by being FOUND - and a copy that cannot be read fails here "
                    "rather than passing, which is why the verdict is a presence"
                )
        if not self.the_reach_is_bounded_by.strip():
            raise TextualError(
                f"{self.rule}: the hand's reach is not bounded by anything. ⛔ *Outside its "
                "reach* is not a measurement until what the hand is known to have worked over "
                "is stated, and stated from a copy's own page rather than from what the "
                "recorder happens to know"
            )
        if not self.what_this_does_not_establish.strip():
            raise TextualError(
                f"{self.rule}: an attestation that does not say what it fails to establish "
                "reads as an attribution. ⛔ It shows the RULE predates the hand's reach, "
                "never that the words in the revised copy are the translator's"
            )

    def as_row(self) -> dict[str, Any]:
        return {
            "finding": "rule_attested_outside_one_hands_reach",
            "rule": self.rule,
            "the_rule_as_published": self.the_rule_as_published,
            "filed_as": self.filed_as,
            "filed_in": self.filed_in.key,
            "the_hand_whose_reach_is_at_issue": self.the_hand_whose_reach_is_at_issue,
            "the_reach_is_bounded_by": self.the_reach_is_bounded_by,
            "attested_in": self.attested_in.key,
            "the_locus_there": self.the_locus_there,
            "the_attesting_passages": [
                {
                    "quoted": normalise(passage),
                    "occurrences": resolve(self.attested_in, passage).occurrences,
                    "letters_of_the_originals_script": sum(
                        1
                        for c in normalise(passage)
                        if script_of(c) == self.the_original_is_written_in
                    ),
                }
                for passage in self.the_attesting_passages
            ],
            # ⛔⛔ A PRESENCE IS FREE WHEREVER NOTHING REPEATS, so the attesting copy
            #   carries its own recurrence here. ⚠ This row's limit says a reader can
            #   destroy the evidence of a presence but cannot manufacture it - true of a
            #   reader that loses text, false of one that returns noise.
            "the_attesting_copy_repeats_itself": {
                **recurrence_of(self.attested_in),
                "the_floor_this_had_to_clear": LEAST_RECURRENCE,
            },
            "the_attesting_copy_is_outside_the_reach_because": {
                "the_original_is_written_in": self.the_original_is_written_in,
                "letters_of_it_in_the_attesting_copy": self.attested_in.scripts.get(
                    self.the_original_is_written_in, 0
                ),
                "letters_of_it_in_the_copy_the_rule_is_filed_in": self.filed_in.scripts.get(
                    self.the_original_is_written_in, 0
                ),
                "why_this_is_the_condition": (
                    "⛔ a second printing of the SAME translation is INSIDE the reach, and two "
                    "printings one hand revised agree about the revision. A copy carrying the "
                    "original's script is working from the original rather than from the "
                    "translation that hand worked over. ⚠ This is "
                    "`revised_printing_cannot_witness_the_unrevised_words` as an entry "
                    "condition; the refusal is NOT discharged by this row"
                ),
            },
            "the_verdict_is_a_presence_not_an_absence": (
                "⭐⭐⭐ the rule had to be FOUND. The test this replaces required a ZERO over a "
                "candidate copy, and a zero is the one measurement a broken reader produces "
                "for free: a library scan of this work whose machine reading carries no Latin "
                "letters at all scores a PERFECT pass on the eleven spellings that are words. "
                "⛔⛔ The same copy scores nothing here - and NOT because it can state "
                "nothing, which is what this row said before it was measured. Quoted against "
                "itself that copy states whatever it is asked to: 44 of its 246 689 distinct "
                "fragments recur, so any run of its noise resolves exactly once. It scores "
                "nothing here because a rendering that does not repeat is refused outright, "
                "and that refusal was armed a session AFTER this verdict shape was"
            ),
            "what_this_does_not_establish": self.what_this_does_not_establish,
            "limit": (
                "⛔ one attesting copy, in the passages quoted, in this rendering of it. ⚠ A "
                "reader that LOSES text can destroy the evidence of a presence but cannot "
                "manufacture one, so a presence found in ONE reading needs no second reader - "
                "which is the asymmetry that made the retired test need a guard against every "
                "way a reader can fail. ⛔⛔⛔ A READER THAT RETURNS NOISE MANUFACTURES ONE, "
                "AND THAT CORRECTS THE SENTENCE THIS ROW CARRIED BEFORE: where nothing "
                "repeats every fragment resolves exactly once, and a passage quoted out of a "
                "copy's own noise attested a rule nobody has ever stated. ⇒ What stands in "
                "the second reader's place is `the_attesting_copy_repeats_itself` above; the "
                "asymmetry holds only above that floor. ⭐ This row is weaker than it looks, "
                "not stronger: it bounds an invention, it does not attribute a sentence"
            ),
        }


@dataclass(frozen=True)
class PassageAbsence:
    """That a **located passage** does not state something — bounded by the passage.

    ⭐⭐ **THE BOUND IS THE PASSAGE, NOT THE EXTENT, AND THAT IS THE WHOLE DIFFERENCE.**
    `AbsenceSearch` above is bounded by how much of the work the copy contains, so it cannot
    honestly be run over a copy whose extent is a *lower bound*: an absence over an unknown
    quantity still prints a confident zero. A passage delimited by two landmarks that each
    resolve exactly once is bounded by something measured — the region between them — and a
    copy's extent being unknown does not make the region between two located landmarks
    unknown. ⇒ This is the one absence that may be taken over such a copy.

    ⛔ **What it does NOT escape is the alphabet.** An absence established by searching one
    spelling is an absence of that spelling, in a passage or in a work alike, and a machine
    reading of a scan damages the same word differently at every occurrence. So every
    spelling is listed with its own hit count, and where each was *read off the copy* is
    recorded — ⛔ a guessed spelling that matches nothing is indistinguishable, in the
    output, from a passage that genuinely does not contain the thing.

    ⭐⭐⭐ **AND IT EXISTS BECAUSE ITS ABSENCE COST THIS REPOSITORY A PUBLISHED FINDING.** A
    fork was recorded on the strength of one copy stating something *else* at a locus, and
    "it says X here" was read as "it does not say Y here". The rule said to be missing stood
    two paragraphs further down the same commentary. ⛔ *A different reason found is not the
    absence of the reason you were looking for* — and nothing in the file said the region had
    never been searched, because nothing had required it to be.
    """

    claim: str
    edition: Edition
    passage_label: str
    #: The landmarks delimiting the passage. ⛔ Each must resolve exactly once, or the region
    #: is not a region — see `region`.
    after: str
    before: str
    alphabet: Sequence[str]
    #: Where each spelling in the alphabet was read off the copy. ⚠ Free text, and required:
    #: it is the only thing in the row that distinguishes a searched alphabet from a guessed
    #: one, and the two look identical when both return zero.
    alphabet_read_from: str

    def __post_init__(self) -> None:
        """⛔ Every spelling must be attested somewhere in this copy, or it was guessed.

        ⭐ A spelling that occurs **zero** times in the whole rendering cannot distinguish
        *the passage does not say this* from *the recorder does not know how this copy spells
        it*, and it contributes a reassuring zero to the row either way. This repository has
        already been burnt by exactly that: seven boundary-marker spellings were written by
        guessing the regular form, six matched nothing at all, and the one that matched was
        right by luck. ⚠ Attestation is the cheapest available proof that an alphabet was
        read off the copy rather than out of the reader's head — and it is not proof that the
        alphabet is *complete*, which nothing here claims.
        """
        if not self.alphabet:
            raise TextualError(
                f"{self.passage_label}: an absence with no alphabet searched nothing"
            )
        # ⛔⛔ CHECKED BEFORE ATTESTATION, BECAUSE OTHERWISE THE RIGHT REFUSAL CARRIES THE
        #    WRONG CAUSE. Over a copy that rendered to nothing every spelling is unattested,
        #    so the attestation rule below fires and reports that the recorder GUESSED the
        #    alphabet - sending the next reader to fix a vocabulary that was never the
        #    problem. ⭐ Measured on a real copy in this repository's cache: 219 pages of page
        #    images, rendering `characters` 218, searchable text empty.
        if not self.edition.carries_searchable_text:
            raise TextualError(
                f"{self.passage_label}: {self.edition.key} renders to no searchable text, so "
                "no passage in it can be bounded and no absence over it means anything. ⛔ "
                "This is NOT an alphabet that was guessed - the alphabet was never given "
                f"anything to match against. ⚠ Its rendering reports "
                f"{self.edition.rendering.characters} characters, which is not zero and is "
                "not text"
            )
        # ⛔⛔⛔ AND CHECKED BEFORE ATTESTATION FOR THE SAME REASON, AGAINST A SECOND CAUSE THE
        #    FIRST FIX DID NOT COVER. The mute-copy check above was moved ahead of attestation
        #    because over a blank copy the attestation rule fires and blames the recorder for
        #    GUESSING. ⚠ A copy that renders to noise in the wrong script does it again: every
        #    Latin spelling is unattested in it, and the cause is the machine reading, not the
        #    vocabulary. ⭐ *A fix that names the right cause was written for one cause, and
        #    the wrong cause has more than one.*
        required = scripts_required_by(self.alphabet)
        if not required:
            raise TextualError(
                f"{self.passage_label}: every spelling in this alphabet is punctuation or "
                "digits, so it is written in no script and nothing can establish that this "
                "rendering could express it"
            )
        missing = sorted(s_ for s_ in required if not self.edition.carries_script(s_))
        if missing:
            raise TextualError(
                f"{self.passage_label}: {self.edition.key} carries no {missing} at all, "
                f"though its rendering is {self.edition.searchable_characters} searchable "
                f"characters long, and this alphabet is written in {sorted(required)}. ⛔ "
                "This is NOT a guessed alphabet and NOT a silent copy - it is a machine "
                "reading in the wrong script, which passes every check that asks whether the "
                "copy was read and returns zero for every word in the book"
            )
        # ⛔⛔⛔ AND A THIRD CAUSE, CHECKED BEFORE ATTESTATION FOR THE THIRD TIME. A copy
        #    that repeats nothing attests every spelling quoted out of it and bounds a
        #    region between two landmarks that each resolve exactly once - so the
        #    attestation rule below passes, the region is *measured*, and the zeroes in
        #    it are the machine reading's. ⚠ The cause is neither the vocabulary nor the
        #    script: both landmarks and every spelling can be the copy's own noise.
        refuse_a_rendering_that_does_not_repeat(
            self.edition,
            what_it_would_make_free=(
                "the two landmarks that bound the passage, each of which must resolve "
                "exactly once, and the attestation of every spelling below"
            ),
        )
        body = self.edition.normalised
        unattested = [s for s in self.alphabet if normalise(s) not in body]
        if unattested:
            raise TextualError(
                f"{self.passage_label}: {unattested} occur nowhere in "
                f"{self.edition.key}, so they were guessed rather than read off it. ⛔ A "
                "spelling absent from the whole copy reports the recorder's vocabulary as "
                "the passage's silence, and it does so with a zero that looks like evidence"
            )

    @property
    def passage(self) -> str:
        return region(
            self.edition, label=self.passage_label, after=self.after, before=self.before
        )

    @property
    def hits(self) -> dict[str, int]:
        body = self.passage
        return {spelling: body.count(normalise(spelling)) for spelling in self.alphabet}

    @property
    def established(self) -> bool:
        """⛔ True only when every listed spelling is absent from the passage."""
        return not any(self.hits.values())

    def as_row(self) -> dict[str, Any]:
        counts = self.hits
        passage = self.passage
        return {
            "finding": "passage_absence",
            "claim": self.claim,
            "edition": self.edition.key,
            "passage": self.passage_label,
            "passage_characters": len(passage),
            "spellings_searched": list(self.alphabet),
            "hits_by_spelling": [
                {"spelling": spelling, "hits": counts[spelling]} for spelling in self.alphabet
            ],
            "hits_in_total": sum(counts.values()),
            "established": self.established,
            # ⭐ The bound below is measured, and this is what makes it worth measuring:
            #   two landmarks resolving exactly once bound nothing in a copy where every
            #   fragment resolves exactly once.
            "and_resolving_exactly_once_is_not_free_here": {
                **recurrence_of(self.edition),
                "the_floor_this_had_to_clear": LEAST_RECURRENCE,
            },
            "where_the_spellings_came_from": self.alphabet_read_from,
            "bounded_by": (
                "the region between two landmarks that each resolve exactly once in this "
                "rendering. ⭐ That bound is measured, so this absence does NOT depend on how "
                "much of the work the copy contains - which is why it may be taken over a "
                "copy whose extent is a lower bound, where an absence over the work may not"
            ),
            "limit": (
                "⛔ still only as wide as its alphabet. A spelling not listed was not looked "
                "for, and a machine reading of a scan can damage the same word differently "
                "at every occurrence - so a zero here is a zero for these spellings in this "
                "region of this rendering, and is not the passage's silence"
            ),
        }


@dataclass(frozen=True)
class SecondHand:
    """That one copy carries a commenting hand **other** than the one its notes are credited to.

    ⭐⭐⭐ **A TRANSLATION WITH NOTES HAS TWO AUTHORITIES; A REVISED TRANSLATION WITH NOTES
    HAS THREE, AND THE THIRD IS THE ONE NOBODY COUNTS.** This repository already separates
    the text from the translator's notes and says so on every row, on the ground that a
    consumer taking one for the other implements a modern commentator under a sutra's name.
    ⛔ The copy those rows are resolved into carries a *further* hand: one that refers to the
    translator by name in the third person, comments on his notes, and claims books of its
    own. A file that counts two authorities where the copy has three attributes one hand's
    words to another with exactly the confidence it attributes a sutra to the text.

    ⭐ **Established from the copy, never from outside it.** The evidence is the copy
    referring to the translator in the third person: a hand that writes *"Prof. Rao's
    NOTES"* is not Prof. Rao. Each such passage must resolve exactly once, or the second hand
    is a reader's impression rather than a located fact.

    ⛔⛔ **AND THE HAND CANNOT BE NAMED, WHICH IS RECORDED RATHER THAN REPAIRED.** It claims
    other works as its own, and turning those titles into a name would mean supplying an
    authorship this repository does not hold — from the recorder's own memory, which is
    precisely the unsourced claim the locus discipline exists to refuse. ⚠ So `named` is a
    measurement over the copy and it is allowed to be false: *there is a second hand here and
    this copy does not say whose it is* is a complete and checkable finding.
    """

    edition: Edition
    #: The hand the notes are credited to, as this copy spells the name.
    the_notes_are_credited_to: str
    #: ⛔ Passages in which the copy speaks of that translator in the THIRD PERSON. Each must
    #: resolve exactly once. Without one of these there is no second hand, only a reading.
    speaks_of_the_translator_in_the_third_person: Sequence[str]
    #: Passages in which the second hand claims work of its own. ⚠ Evidence that it is an
    #: author rather than a compositor — and ⛔ never evidence of *which* author.
    claims_work_of_its_own: Sequence[str]
    #: The spellings by which this copy marks the second hand's material. ⚠ Read off the copy.
    marked_by: Sequence[str]
    #: Whether the second hand can be NAMED from this copy alone. ⛔ Measured, and false here.
    named_within_this_copy: bool

    def __post_init__(self) -> None:
        if not self.edition.carries_searchable_text:
            raise TextualError(
                f"{self.edition.key}: a second hand cannot be established in a copy that "
                "renders to no searchable text"
            )
        # ⛔ A resolution here is EVIDENCE, not an address, and a rendering that
        #   repeats nothing resolves every fragment of itself exactly once - see
        #   `refuse_a_rendering_that_does_not_repeat`, which carries the measurement.
        refuse_a_rendering_that_does_not_repeat(
            self.edition,
            what_it_would_make_free="every passage said to locate the second hand",
        )
        if not self.speaks_of_the_translator_in_the_third_person:
            raise TextualError(
                f"{self.edition.key}: a second hand is established by the copy speaking of "
                "the translator in the third person, and no such passage was given. ⛔ "
                "Without one this is a reader's impression of a change in voice"
            )
        for fragment in (
            *self.speaks_of_the_translator_in_the_third_person,
            *self.claims_work_of_its_own,
        ):
            found = resolve(self.edition, fragment)
            if not found.resolved:
                raise TextualError(
                    f"{self.edition.key}: the passage {fragment[:60]!r} occurs "
                    f"{found.occurrences} time(s), so it locates nothing. ⛔ A second hand is "
                    "established from located passages or it is not established"
                )

    def as_row(self) -> dict[str, Any]:
        return {
            "finding": "hands_in_the_copy",
            "edition": self.edition.key,
            "the_notes_are_credited_to": self.the_notes_are_credited_to,
            "how_many_commenting_hands_this_copy_carries": 2,
            "the_copy_speaks_of_the_translator_in_the_third_person": [
                {
                    "quoted": normalise(f),
                    "occurrences": resolve(self.edition, f).occurrences,
                }
                for f in self.speaks_of_the_translator_in_the_third_person
            ],
            "the_second_hand_claims_work_of_its_own": [
                {
                    "quoted": normalise(f),
                    "occurrences": resolve(self.edition, f).occurrences,
                }
                for f in self.claims_work_of_its_own
            ],
            "the_second_hands_material_is_marked_by": list(self.marked_by),
            "the_second_hand_is_named_within_this_copy": self.named_within_this_copy,
            "why_it_is_not_named": (
                "⛔ this copy carries no title page, no imprint and no preface in its "
                "rendering. The second hand claims other works as its own, and turning those "
                "titles into a name would mean supplying an authorship from the recorder's "
                "own memory - the unsourced claim the whole locus discipline refuses. ⭐ *There "
                "is a second hand here and this copy does not say whose* is the finding"
            ),
            "why_this_matters": (
                "⭐⭐⭐ A TRANSLATION WITH NOTES HAS TWO AUTHORITIES AND A REVISED ONE HAS "
                "THREE. Rows filed as *the translator's notes* claim a hand, not merely a "
                "page - and in a copy carrying a second commentator that claim needs "
                "measuring rather than assuming. ⛔ It also bounds what a further printing "
                "could ever settle: a reviser who rewrites silently leaves no mark, so two "
                "revised printings agreeing attest the revision and not the translator"
            ),
        }


@dataclass(frozen=True)
class NamedInAnotherCopy:
    """A hand one copy cannot name, named by a different copy of the same translation.

    ⭐⭐⭐ **THE ANSWER TO *THIS COPY DOES NOT SAY WHOSE* IS ANOTHER COPY THAT DOES.** A
    previous session established that the printing every rule here resolves into carries a
    second commenting hand and cannot name it: no title page, no imprint, no preface. ⛔ The
    refusal at the time was not *we do not know who it is* — it was that naming it from the
    books it claims would supply an authorship **out of the recorder's memory**. ⚠ That
    refusal is discharged only by a copy that prints the name itself, and this is the shape
    that discharge has to take.

    ⛔ **A name found in one copy is not automatically the hand in the other**, and the tie
    is the hard part. It is required here, and required to be *located on both sides*: a
    fragment that resolves exactly once in each copy. The tie this was built for is the second
    hand's own claim of a book, printed in both — ⭐ the very claim the earlier session refused
    to turn into a name, now doing the work honestly, because the naming comes from the other
    copy's page rather than from what the recorder happens to know about the book.

    ⚠ **And the unnamed copy is re-checked.** If the name occurs in it after all, the earlier
    *cannot be named from this copy* was wrong, and this class refuses rather than quietly
    building on it.
    """

    #: What the hand is, as the unnamed copy shows it. ⚠ A description, never a name.
    the_hand: str
    unnamed_in: Edition
    named_in: Edition
    #: The name exactly as the naming copy prints it.
    the_name_as_that_copy_prints_it: str
    #: The passage in which that copy names it. ⛔ Must resolve exactly once there.
    the_passage_that_names_it: str
    #: What that copy says its own printing is. ⛔ Must resolve exactly once there.
    the_printing_that_copy_declares: str
    #: Fragments resolving **exactly once in BOTH copies**, tying one hand to the other.
    #: ⛔ Without one of these, two copies have been read and nothing has been connected.
    tied_to_the_unnamed_hand_by: Sequence[str]
    what_this_does_not_establish: str

    def __post_init__(self) -> None:
        if self.unnamed_in.key == self.named_in.key:
            raise TextualError(
                f"{self.unnamed_in.key}: a copy cannot be the one that fails to name a hand "
                "and the one that names it. ⛔ That is not a second copy, it is a re-reading"
            )
        # ⛔ A resolution here is EVIDENCE, not an address, and a rendering that
        #   repeats nothing resolves every fragment of itself exactly once - see
        #   `refuse_a_rendering_that_does_not_repeat`, which carries the measurement.
        refuse_a_rendering_that_does_not_repeat(
            self.named_in,
            what_it_would_make_free="the passage naming the hand and the printing that copy declares",
        )
        # ⚠ And the copy said NOT to name it: an absence measured over a rendering that
        #   repeats nothing is the reassuring zero this repository keeps finding.
        refuse_a_rendering_that_does_not_repeat(
            self.unnamed_in,
            what_it_would_make_free="the re-measured absence of the name from the copy that does not name it",
        )
        for fragment, where in (
            (self.the_passage_that_names_it, self.named_in),
            (self.the_printing_that_copy_declares, self.named_in),
        ):
            found = resolve(where, fragment)
            if not found.resolved:
                raise TextualError(
                    f"{where.key}: {fragment[:60]!r} occurs {found.occurrences} time(s), so "
                    "it locates nothing. ⛔ A name and a printing are read off a page or they "
                    "are supplied by the recorder"
                )
        # ⛔ The earlier finding is re-measured rather than trusted: if the name is in the
        #    copy said not to name it, that copy was under-read and this row would build a
        #    correct-looking attribution on a wrong absence.
        occurrences = self.unnamed_in.normalised.count(
            normalise(self.the_name_as_that_copy_prints_it)
        )
        if occurrences:
            raise TextualError(
                f"{self.unnamed_in.key}: the name occurs {occurrences} time(s) in the copy "
                "said not to name the hand. ⛔ Then it was not unnamed there, and the finding "
                "this row rests on is the thing that needs correcting"
            )
        if not self.tied_to_the_unnamed_hand_by:
            raise TextualError(
                f"{self.named_in.key}: a name in one copy is not the hand in another until "
                "something located ties them. ⛔ Give a fragment resolving exactly once in "
                "BOTH copies, or this row names a hand in a book nobody has connected to "
                "this one"
            )
        for fragment in self.tied_to_the_unnamed_hand_by:
            here = resolve(self.unnamed_in, fragment)
            there = resolve(self.named_in, fragment)
            if not (here.resolved and there.resolved):
                raise TextualError(
                    f"the tie {fragment[:50]!r} occurs {here.occurrences} time(s) in "
                    f"{self.unnamed_in.key} and {there.occurrences} in {self.named_in.key}. "
                    "⛔ A tie resolves on BOTH sides or it ties nothing - and two machine "
                    "readings of one sentence differ, so a tie that fails here may be a fact "
                    "about the readings rather than about the hands"
                )

    def as_row(self) -> dict[str, Any]:
        return {
            "finding": "hand_named_in_another_copy",
            "the_hand": self.the_hand,
            "unnamed_in": self.unnamed_in.key,
            "named_in": self.named_in.key,
            "the_name_as_that_copy_prints_it": self.the_name_as_that_copy_prints_it,
            "the_passage_that_names_it": {
                "quoted": normalise(self.the_passage_that_names_it),
                "occurrences": resolve(
                    self.named_in, self.the_passage_that_names_it
                ).occurrences,
            },
            "the_printing_that_copy_declares": {
                "quoted": normalise(self.the_printing_that_copy_declares),
                "occurrences": resolve(
                    self.named_in, self.the_printing_that_copy_declares
                ).occurrences,
            },
            "the_name_occurs_in_the_unnamed_copy": 0,
            "tied_to_the_unnamed_hand_by": [
                {
                    "quoted": normalise(f),
                    "occurrences_in_the_unnamed_copy": resolve(
                        self.unnamed_in, f
                    ).occurrences,
                    "occurrences_in_the_naming_copy": resolve(self.named_in, f).occurrences,
                }
                for f in self.tied_to_the_unnamed_hand_by
            ],
            "what_this_does_not_establish": self.what_this_does_not_establish,
            "why_it_took_a_second_copy": (
                "⛔ the earlier refusal was never *we cannot guess who this is*. It was that "
                "turning the books the hand claims into a name would supply an authorship "
                "from the recorder's own memory - the unsourced claim this discipline exists "
                "to refuse. ⭐ A copy that prints the name on its own page discharges that "
                "refusal and nothing else does, however obvious the guess"
            ),
        }


@dataclass(frozen=True)
class SelfContradiction:
    """Two statements by one hand, in one copy, that cannot both be relied on.

    ⭐⭐⭐ **THE MOST TEMPTING EVIDENCE IN A REVISED PRINTING IS THE REVISER SAYING HE
    CHANGED NOTHING, AND THIS IS WHAT THAT IS WORTH.** A signed foreword acquired for this
    repository states, in one paragraph, both *"I have not meddled with either the
    translation or the notes"* and *"The translation herewith presented has been thoroughly
    revised by me"*. ⛔ Neither is doubted here and neither is adopted: both are located,
    both are quoted, and the pair is what is published — because a recorder who took the
    first sentence would have retired a standing refusal on the strength of a claim the same
    hand contradicts two sentences later.

    ⚠ **This does not say the hand was dishonest**, and the row says so. It says that this
    copy does not settle what was altered — which is a smaller and checkable claim, and the
    only one the copy supports.
    """

    edition: Edition
    the_hand: str
    #: `(what it claims, the words that claim it)`. ⛔ Each fragment resolves exactly once.
    statements: Sequence[tuple[str, str]]
    why_they_cannot_both_be_relied_on: str
    what_it_settles: str

    def __post_init__(self) -> None:
        if len(self.statements) < 2:
            raise TextualError(
                f"{self.edition.key}: one statement is not a contradiction. ⛔ Two located "
                "statements, or this is a reader's unease about a sentence"
            )
        # ⛔ A resolution here is EVIDENCE, not an address, and a rendering that
        #   repeats nothing resolves every fragment of itself exactly once - see
        #   `refuse_a_rendering_that_does_not_repeat`, which carries the measurement.
        refuse_a_rendering_that_does_not_repeat(
            self.edition,
            what_it_would_make_free="both statements this copy is said to make",
        )
        for _, fragment in self.statements:
            found = resolve(self.edition, fragment)
            if not found.resolved:
                raise TextualError(
                    f"{self.edition.key}: {fragment[:60]!r} occurs {found.occurrences} "
                    "time(s), so it locates nothing. ⛔ A contradiction is between two things "
                    "the copy was shown to say"
                )

    def as_row(self) -> dict[str, Any]:
        return {
            "finding": "the_copy_disagrees_with_itself",
            "edition": self.edition.key,
            "the_hand": self.the_hand,
            "statements": [
                {
                    "claims": claims,
                    "quoted": normalise(fragment),
                    "occurrences": resolve(self.edition, fragment).occurrences,
                }
                for claims, fragment in self.statements
            ],
            "why_they_cannot_both_be_relied_on": self.why_they_cannot_both_be_relied_on,
            "what_it_settles": self.what_it_settles,
            "what_it_does_not_settle": (
                "⛔ nothing about the hand's honesty, and nothing about which words were "
                "changed. ⚠ A copy that disagrees with itself has told a reader that it is "
                "not the authority for the question - which is a smaller claim than either "
                "sentence taken alone, and is the only one the copy supports"
            ),
        }


def discrimination_of_resolving_once(
    edition: Edition, candidates: Sequence[str]
) -> dict[str, Any]:
    """How many of `candidates` resolve **exactly once** here. ⭐ A control on the controls.

    ⭐⭐⭐ **"RESOLVES EXACTLY ONCE" IS THE CONDITION THIS REPOSITORY LEANS ON HARDEST, AND
    ON ONE REAL COPY IT FILTERS NOTHING.** In an ordinary book a fragment resolving once is
    evidence, because most short strings either recur or do not appear at all. In a machine
    reading that returned noise nothing recurs — measured, 1 188 of 1 188 candidate fragments
    resolved exactly once — so the hardest-looking condition in the file becomes the easiest,
    and it is satisfied by a positive control that establishes nothing whatever.

    ⛔ This measures that rather than asserting it: the number is what tells a reader whether
    a resolution in a given copy is worth anything.
    """
    counts = [resolve(edition, c).occurrences for c in candidates if c.strip()]
    once = sum(1 for c in counts if c == 1)
    return {
        "edition": edition.key,
        "candidate_fragments_tried": len(counts),
        "resolving_exactly_once": once,
        "resolving_more_than_once": sum(1 for c in counts if c > 1),
        "resolving_not_at_all": sum(1 for c in counts if c == 0),
        "share_resolving_exactly_once": (round(once / len(counts), 6) if counts else None),
        "what_a_share_near_one_means": (
            "⛔ that resolving exactly once distinguishes nothing in this copy. It is the "
            "expected state of a rendering in which nothing repeats - a machine reading that "
            "returned noise - and it makes a positive control free to obtain and worthless "
            "to hold"
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
# Comparing two copies: alignment first, disagreement only after
# --------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Alignment:
    """That a locus in one copy and a locus in another are **the same place in the work**.

    ⭐⭐ **TWO COPIES NUMBER THE SUTRAS DIFFERENTLY, AND A DIFFERENCE OF NUMBER READS
    EXACTLY LIKE A DIFFERENCE OF PLACE.** Where one copy prints a rule at "sutra 50" and
    another prints it at "sutra 53", a recorder comparing the two by their numbers concludes
    that they attach the rule to different sutras governing different determinations. ⛔ That
    conclusion is available without anyone having checked, it is entirely plausible, and it
    is what this repository published.

    ⭐ So the offset is **measured against an anchor**: a *neighbouring* sutra whose words
    both copies print, located in each. The anchor's two numbers give the offset; the offset
    then says whether the two loci under comparison are one place or two. ⛔ Nothing here
    infers an offset from position, from proximity or from subject matter — an anchor is a
    passage located in both copies or there is no alignment.
    """

    label: str
    anchor_in_first: Locus
    anchor_first_number: int
    anchor_in_second: Locus
    anchor_second_number: int
    first_number: int
    second_number: int

    @property
    def offset_at_the_anchor(self) -> int:
        """How much higher the second copy's numbering runs, measured at the anchor."""
        return self.anchor_second_number - self.anchor_first_number

    @property
    def offset_at_these_loci(self) -> int:
        return self.second_number - self.first_number

    @property
    def offset_holds(self) -> bool:
        """⛔ Whether the anchor's offset carries to the loci. A measurement, not a verdict.

        ⚠ **False does not mean the two loci are different places, and true would not mean
        they are the same one.** It means arithmetic on sutra numbers does not settle the
        question — which is the only thing this class is entitled to say.
        """
        return self.offset_at_these_loci == self.offset_at_the_anchor

    def as_json(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "anchor": {
                "why_an_anchor": (
                    "a sutra NEIGHBOURING the two under comparison, whose words both copies "
                    "print, located in each. ⛔ Without one, a difference of sutra number "
                    "cannot be told from a difference of place in the work"
                ),
                "in_the_first_copy": self.anchor_in_first.as_json(),
                "numbered_in_the_first_copy": self.anchor_first_number,
                "in_the_second_copy": self.anchor_in_second.as_json(),
                "numbered_in_the_second_copy": self.anchor_second_number,
            },
            "offset_measured_at_the_anchor": self.offset_at_the_anchor,
            "numbered_in_the_first_copy": self.first_number,
            "numbered_in_the_second_copy": self.second_number,
            "offset_at_these_loci": self.offset_at_these_loci,
            "the_anchors_offset_holds_at_these_loci": self.offset_holds,
            "what_a_false_result_means": (
                "⛔ that the two copies do not merely NUMBER the sutras differently - they "
                "ORDER them differently, so no single offset describes the pair and identity "
                "of place cannot be settled by arithmetic on sutra numbers at all. ⚠ It does "
                "NOT mean the two loci are different places in the work"
            ),
            "limit": (
                "⛔ measured at ONE anchor, in this pair of renderings. An offset that holds "
                "here may not be carried elsewhere without its own anchor - and in this pair "
                "it demonstrably does not: the offset is the same on either side of the "
                "sutra under comparison and different at it"
            ),
        }


@dataclass(frozen=True)
class Fork:
    """Two copies disagreeing — where **both halves** of the disagreement are measured.

    ⭐⭐⭐ **A FORK IS A PRESENCE AND AN ABSENCE, AND ONLY THE PRESENCE EVER GETS
    MEASURED.** One copy states the rule: that half resolves, occurs exactly once, and
    passes every control this module owns. The other copy is said not to state it — ⛔ and
    that half is an *absence*, which is the harder claim, and it is the one a recorder makes
    by reading a page and forming an impression.

    ⛔ **This class refuses to be written unless the absence was measured**, over a passage
    bounded by two located landmarks, in an alphabet read off the copy. It is armed because
    the unarmed version failed: a fork published by this repository asserted that the second
    copy did not invoke a rule where the series is founded, and the rule stood two paragraphs
    below, in the same commentary, in the passage nobody had searched. ⭐ *The accepting run
    is not the evidence* — five fragments each resolving exactly once said nothing whatever
    about the claim built on top of them.

    ⚠ Refusing here is not a shortfall. A disagreement that cannot be measured on both sides
    is a disagreement this instrument has not established, and recording it as one would
    publish a recorder's impression wearing a citation's clothes.
    """

    rule: str
    subject: str
    #: The copy that states the rule, at the locus it states it.
    stated_by: Locus
    #: ⛔ The copy said NOT to state it — as a measured absence over a bounded passage.
    absent_from: PassageAbsence

    def __post_init__(self) -> None:
        if self.stated_by.edition.key == self.absent_from.edition.key:
            raise TextualError(
                f"{self.rule}: a fork is between two copies, and both sides of this one name "
                f"{self.stated_by.edition.key!r}. ⛔ A copy disagreeing with itself is a "
                "different finding and is not recorded as a fork"
            )
        if not self.absent_from.established:
            hits = {k: v for k, v in self.absent_from.hits.items() if v}
            raise TextualError(
                f"{self.rule}: the copy this fork says is silent is NOT silent - "
                f"{self.absent_from.passage_label!r} in {self.absent_from.edition.key} "
                f"contains {hits}. ⛔ A fork is a presence AND an absence, and the absence "
                "half was not established. Record what the second copy actually states, as a "
                "corroboration or as its own located reading; do not record a disagreement "
                "the passage refutes"
            )

    def as_row(self) -> dict[str, Any]:
        return {
            "finding": "fork",
            "rule": self.rule,
            "subject": self.subject,
            "stated_by": self.stated_by.as_json(),
            "and_measured_absent_from": self.absent_from.as_row(),
            "what_makes_this_a_fork_rather_than_an_impression": (
                "⭐ both halves are measured. The stating copy's words are located and occur "
                "exactly once; the silent copy's silence is measured over a passage bounded "
                "by two located landmarks, in spellings read off that copy. ⛔ A fork whose "
                "absence half is not established is refused at write time"
            ),
        }


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
