"""Sampling an ephemeris *service*, and the one question that has to be answered first.

A published file and a published service are not two sizes of the same thing. The file can
be fetched again and hashed to the same value forever; the service answers with a
**rendering**, produced now, carrying material that exists because a request happened
rather than because an answer did. ⛔ **Byte-for-byte reproducibility is a write-time
guarantee in this repository**, so a recorder that digests a service response as though it
were a file emits a fixture that cannot regenerate, and discovers it one run later.

⭐ **THE DESIGN QUESTION, AND THE ANSWER IS NOT THE OBVIOUS TWO-WAY ONE.** The obvious split
is *request* against *resource*: keep what a reader could ask again, discard what moved.
Measured against the service this module records, that split is wrong, because a response
has **three** parts and not two:

1. **The request.** What was asked. We hold it, it is written down verbatim, and a reader
   re-issues it. Nothing here is at risk.
2. **The transaction envelope.** Material that moves on *every* request and belongs to the
   call rather than the answer — for this service, a single generation-stamp line. ⛔ Never
   recorded. It is the response `Date` header's problem arriving inside the body, where no
   header allow-list can reach it.
3. ⭐ **The service's own state.** Which solution answered, which auxiliary files were
   loaded, which interface version replied. This moves on the **service's** schedule, not
   the caller's — and it is the part the naive split gets fatally wrong in *both*
   directions. Discard it as "volatile" and the file no longer says what answered. Digest it
   as "the resource" and the artifact stops regenerating the day the service updates a file
   nobody here controls.
4. **The resource.** What is left: the numbers, and the request the service echoed back.

⭐ **So the resolution is that service state is recorded as DATA and excluded from the
DIGEST**, and the reproducibility claim becomes conditional and says its condition out
loud: *these bytes regenerate for as long as the recorded service state holds*. ⚠ That is
the same shape of claim the acquisition record already makes about a machine — reproducible
here, not everywhere — and it is honest for the same reason: the condition is written into
the file, so a reader can check it rather than discover it.

⛔ **A conditional guarantee needs something to watch the condition, or it is a guarantee
nobody checks.** That is the drift job, and it is why the two arrive together.

⚠ **The split is asserted per run, never assumed.** Every field this module classifies must
be *present* in the response; a classified field that has gone missing means the format
moved and the classification is stale, so the run is refused rather than quietly digesting
a volatile region as a stable one.

⛔ **Recorder, never explainer.** Nothing here describes how the service computes anything.
It locates named regions of a text, records what they said, and hashes the rest.
"""

from __future__ import annotations

import json
import re
import urllib.parse
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from .acquisition import AcquisitionError

#: The service's documented entry point.
ENDPOINT = "https://ssd.jpl.nasa.gov/api/horizons.api"


class ServiceFormatError(AcquisitionError):
    """The response is not shaped the way this module classifies it.

    ⛔ A subclass of :class:`AcquisitionError` on purpose: a classification that no longer
    matches the thing classified is an acquisition failure, not a parsing inconvenience.
    Everything downstream of it would be a statement about regions this instrument can no
    longer identify.
    """


# --------------------------------------------------------------------------------------
# Part 2 — the transaction envelope. ⛔ Located so it can be excluded, never recorded.
# --------------------------------------------------------------------------------------

#: ⚠ Matched **structurally**, by the shape of the line, not by the timestamp it contains:
#: a pattern written against the timestamp would silently stop matching the first time the
#: service formatted one differently, and a stamp that stops being excluded is a stamp that
#: starts being digested.
_ENVELOPE_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("generation_stamp", re.compile(r"^Ephemeris / .+ / Horizons[ \t]*$", re.M)),
)

#: What an excluded region is replaced by. ⭐ A marker rather than a deletion, so the
#: canonical form still shows that something was taken out and where — a digest over a text
#: with a hole silently equals a digest over a text that never had the field.
_EXCLUDED = "<excluded:{name}>"


# --------------------------------------------------------------------------------------
# Part 3 — the service's own state. ⭐ Recorded as data, excluded from the digest.
# --------------------------------------------------------------------------------------

#: `(name, pattern, required)`. The captured group is the value.
#:
#: ⚠ **`required` is the assertion, and it is the whole safety of the split.** A required
#: field that is absent means this module is classifying a response that no longer has the
#: shape it classifies — so the run stops. An optional field is one measured to be
#: genuinely conditional on the request (the Earth-orientation lines appear for an
#: Earth-referred query and not for a barycentric one), and its absence is recorded as
#: absence rather than treated as a failure.
_SERVICE_STATE_PATTERNS: tuple[tuple[str, re.Pattern[str], bool], ...] = (
    ("target_solution", re.compile(r"^Target body name:.*?\{source: *([^}]+?) *\}", re.M), True),
    ("center_solution", re.compile(r"^Center body name:.*?\{source: *([^}]+?) *\}", re.M), True),
    ("earth_orientation_file", re.compile(r"^EOP file +: *(\S+)", re.M), False),
    ("earth_orientation_coverage", re.compile(r"^EOP coverage +: *(.+?) *$", re.M), False),
)

#: The interface's own version, from the JSON envelope. ⭐ Service state like any other:
#: it moves on the service's schedule and it changes what a response means.
_SIGNATURE_KEYS: tuple[str, ...] = ("source", "version")


# --------------------------------------------------------------------------------------
# Part 4 — the resource
# --------------------------------------------------------------------------------------

_DATA_START, _DATA_END = "$$SOE", "$$EOE"

#: The column header the data block is asserted against. ⛔ Asserted, not assumed: a
#: positional parser that never checks its columns reads a re-ordered table confidently and
#: attributes the result to the ephemeris.
_EXPECTED_COLUMNS: tuple[str, ...] = (
    "JDTDB",
    "Calendar Date (TDB)",
    "X",
    "Y",
    "Z",
    "VX",
    "VY",
    "VZ",
)

_COLUMN_LINE = re.compile(r"^ *JDTDB,.*$", re.M)

#: Constants the service states about its own output. ⭐ Read out of the response and
#: resolved into the artifact, so a consumer converting units later needs nothing the
#: service holds. ⚠ Recorded as stated inputs; ⛔ never applied to an emitted pin.
_STATED_PATTERNS: tuple[tuple[str, re.Pattern[str], bool], ...] = (
    ("au_in_km", re.compile(r"1 au= *([0-9.]+) km", re.M), True),
    ("seconds_per_day", re.compile(r"1 day= *([0-9.]+) s", re.M), True),
    ("reference_frame", re.compile(r"^Reference frame *: *(.+?) *$", re.M), True),
    ("output_units", re.compile(r"^Output units *: *(.+?) *$", re.M), True),
    ("output_type", re.compile(r"^Output type *: *(.+?) *$", re.M), True),
    ("calendar_mode", re.compile(r"^Calendar mode *: *(.+?) *$", re.M), True),
)


@dataclass(frozen=True)
class ServiceResponse:
    """One response, split into the four parts above."""

    query: dict[str, str]
    #: ⭐ Part 3, recorded. Never in the digest.
    service_state: dict[str, str]
    #: ⛔ Part 2, by NAME only. The values were observed and are deliberately not here.
    envelope_excluded: tuple[str, ...]
    #: What the service stated about its own output, resolved into the artifact.
    stated: dict[str, str]
    #: Part 4, as text. The digest of this is what identifies the answer.
    resource_text: str
    #: One entry per epoch: the parsed data line, fields in `_EXPECTED_COLUMNS` order.
    data_rows: tuple[tuple[str, ...], ...]

    def state_signature(self) -> str:
        """The recorded service state, as one comparable string.

        ⭐ The condition the reproducibility claim is conditional on, in a form a drift
        report can hold up beside a later one.
        """
        return "; ".join(f"{k}={self.service_state[k]}" for k in sorted(self.service_state))


def build_url(query: Mapping[str, str]) -> str:
    """The full address for a query. ⚠ Deterministic: the parameters are sorted.

    An unordered mapping would put the address itself in the volatile set — two runs
    recording two different URLs for one request, with nothing having changed.
    """
    return ENDPOINT + "?" + urllib.parse.urlencode(sorted(query.items()))


def _locate(
    text: str, name: str, pattern: re.Pattern[str], *, required: bool, where: str
) -> tuple[int, int] | None:
    """The span of one classified value, refusing anything that is not exactly one match."""
    matches = list(pattern.finditer(text))
    if not matches:
        if required:
            raise ServiceFormatError(
                f"{where}: the response carries no {name!r}, which this instrument "
                "classifies and therefore expects. ⛔ The format has moved out from under "
                "the classification, so the split between what is stable and what is not "
                "is no longer known to be drawn in the right place. Refusing rather than "
                "digesting a region whose contents are no longer identified."
            )
        return None
    if len(matches) > 1:
        raise ServiceFormatError(
            f"{where}: {name!r} matched {len(matches)} times and must match once. ⛔ A "
            "classification that matches more than one region cannot say which one it "
            "describes, and excluding only the first would leave the others in the digest."
        )
    match = matches[0]
    group = 1 if match.re.groups else 0
    return match.span(group)


def parse(payload: bytes, *, query: Mapping[str, str]) -> ServiceResponse:
    """Split one response into request echo, envelope, service state and resource.

    ⛔ Raises :class:`ServiceFormatError` if any classified region is absent or ambiguous.
    """
    where = query.get("COMMAND", "<no command>")
    try:
        document = json.loads(payload)
    except ValueError as exc:
        raise ServiceFormatError(f"{where}: the response is not JSON ({exc})") from exc

    if "result" not in document:
        raise ServiceFormatError(
            f"{where}: the response carries no 'result'. ⚠ The service reports a rejected "
            f"query this way too, so this is where a bad request surfaces: {document!r}"[:600]
        )
    text = str(document["result"])

    signature = document.get("signature") or {}
    service_state = {
        f"interface_{key}": str(signature[key]) for key in _SIGNATURE_KEYS if key in signature
    }
    if len(service_state) != len(_SIGNATURE_KEYS):
        raise ServiceFormatError(
            f"{where}: the response envelope names no interface version. ⛔ Which interface "
            "answered is service state, and a response that does not say is not one this "
            "instrument can file."
        )

    # ⭐ Collect every span first, then cut once from the end. Cutting as we go would move
    #    every span located after the first cut, and the resulting canonical text would
    #    depend on the order the patterns happen to be declared in.
    cuts: list[tuple[int, int, str]] = []

    excluded: list[str] = []
    for name, pattern in _ENVELOPE_PATTERNS:
        span = _locate(text, name, pattern, required=True, where=where)
        assert span is not None  # required=True never returns None
        cuts.append((*span, name))
        excluded.append(name)

    for name, pattern, required in _SERVICE_STATE_PATTERNS:
        span = _locate(text, name, pattern, required=required, where=where)
        if span is None:
            continue
        cuts.append((*span, name))
        service_state[name] = text[span[0] : span[1]]

    stated: dict[str, str] = {}
    for name, pattern, required in _STATED_PATTERNS:
        span = _locate(text, name, pattern, required=required, where=where)
        if span is None:
            continue
        stated[name] = text[span[0] : span[1]]

    resource_text = text
    for start, end, name in sorted(cuts, reverse=True):
        resource_text = resource_text[:start] + _EXCLUDED.format(name=name) + resource_text[end:]

    return ServiceResponse(
        query=dict(query),
        service_state=service_state,
        envelope_excluded=tuple(excluded),
        stated=stated,
        resource_text=resource_text,
        data_rows=_data_rows(text, where=where),
    )


def _data_rows(text: str, *, where: str) -> tuple[tuple[str, ...], ...]:
    """The delimited data block, with its column header asserted rather than assumed."""
    columns = _COLUMN_LINE.search(text)
    if columns is None:
        raise ServiceFormatError(f"{where}: no column header line in the response")
    found = tuple(part.strip() for part in columns.group(0).split(",") if part.strip())
    if found != _EXPECTED_COLUMNS:
        raise ServiceFormatError(
            f"{where}: columns {found} are not {_EXPECTED_COLUMNS}. ⛔ This parser reads by "
            "position, so a re-ordered or re-labelled table would be read confidently and "
            "wrongly, and the difference would be attributed to the ephemeris."
        )

    if text.count(_DATA_START) != 1 or text.count(_DATA_END) != 1:
        raise ServiceFormatError(f"{where}: the data block delimiters are not a single pair")
    block = text.split(_DATA_START, 1)[1].split(_DATA_END, 1)[0]

    rows: list[tuple[str, ...]] = []
    for line in block.splitlines():
        if not line.strip():
            continue
        fields = tuple(part.strip() for part in line.split(","))
        # ⚠ The service emits a trailing separator; the count is asserted against the
        #   header rather than against a number written here.
        while fields and not fields[-1]:
            fields = fields[:-1]
        if len(fields) != len(_EXPECTED_COLUMNS):
            raise ServiceFormatError(
                f"{where}: a data line has {len(fields)} fields, not "
                f"{len(_EXPECTED_COLUMNS)}: {line!r}"
            )
        rows.append(fields)

    if not rows:
        raise ServiceFormatError(
            f"{where}: the data block is empty. ⛔ An empty answer read as an answer is the "
            "failure this whole repository exists to prevent."
        )
    return tuple(rows)


def canonical_form(query: Mapping[str, str]):
    """A :data:`~saakshi.acquisition.CanonicalForm` for this service, bound to one query.

    ⭐ This is what lets `retrieve()` keep its *"one address has served two artifacts"*
    refusal pointed at a service. Unbound, that refusal fires on the second request every
    time and reports a contradiction the service never made.
    """

    def canonical(payload: bytes) -> bytes:
        return parse(payload, query=query).resource_text.encode("utf-8")

    return canonical


# --------------------------------------------------------------------------------------
# What a reader has to be told about all of this
# --------------------------------------------------------------------------------------

#: ⛔ The limit, stated where a reader of the record will meet it. Reused verbatim by the
#: sampler and by the drift job, because a limit restated in two places drifts into two
#: different limits.
ACQUISITION_LIMIT = (
    "⛔ THE LIMIT, STATED RATHER THAN IMPLIED, AND IT IS WEAKER THAN A FILE'S. For a "
    "published file, this instrument can attest that an address returned exactly these "
    "bytes. For a service it cannot: the bytes are not reproducible, and what is attested "
    "is that an address, on this date, returned a response from which THIS resource was "
    "extracted BY A RULE WRITTEN IN THIS INSTRUMENT. ⚠ So the record attests this "
    "instrument's reading of the response as much as the response itself, and a reader who "
    "would draw the line between transaction and answer somewhere else is disagreeing with "
    "the recorder, not with the service. The rule is written down in full, and every region "
    "it classifies is asserted present on every run, precisely so that disagreement is "
    "possible."
)

#: The outcomes a drift observation can have. ⭐ Four kinds of "it changed", not one:
#: a report that says *something moved* and stops leaves the reader to work out which of
#: four quite different things happened, and they call for four different responses.
DRIFT_OUTCOMES: dict[str, str] = {
    "no_drift": (
        "the service answered as it did when the fixture was written, in every region this "
        "instrument classifies"
    ),
    "values_moved": "a recorded value came back different",
    "service_state_moved": (
        "⭐ THE ONE THAT IS INVISIBLE IN THE NUMBERS — a different solution, or a different "
        "interface version, answered. ⚠ The values may be identical and the claim is still "
        "not the same claim"
    ),
    "unclassified_region_moved": (
        "⚠ the resource digest moved while every value and every recorded piece of service "
        "state stayed put. Something changed in a part of the response this instrument does "
        "not classify at all"
    ),
    "classification_stale": (
        "⛔ THE STRONGEST SIGNAL, AND IT IS ABOUT THIS INSTRUMENT RATHER THAN THE SERVICE. A "
        "region the recorder classifies is no longer there, so the split between what is "
        "stable and what is not can no longer be drawn where it was. Nothing was sampled"
    ),
    "not_observed": (
        "⚠ the query could not be issued at all. ⛔ Reported as its own state and never "
        "collapsed into `no_drift` — a check that did not happen is not a check that passed"
    ),
}

#: What each outcome proposes. ⛔ Addressed to a human. Nothing here is ever applied, and
#: ⛔ nothing here proposes adopting or widening a band.
DRIFT_PROPOSALS: dict[str, str] = {
    "no_drift": "nothing. ⭐ A quiet report is the report this job expects to produce",
    "values_moved": (
        "re-emit the value fixture, and diff it row by row before landing it. ⛔ Do NOT "
        "adjust any band to accommodate the move: a band widened to fit what arrived has "
        "stopped measuring anything"
    ),
    "service_state_moved": (
        "re-emit the value fixture, because the rows now name a solution that is no longer "
        "the one answering. ⚠ Check the values too, and expect them to be UNCHANGED for "
        "some rows — that combination is the finding, not evidence that nothing happened"
    ),
    "unclassified_region_moved": (
        "read the two responses side by side and decide which of the three parts the moved "
        "region belongs to, then classify it in this module. ⚠ Until it is classified it is "
        "being digested, so it can make the fixture unreproducible for a reason no reader "
        "could guess"
    ),
    "classification_stale": (
        "⛔ fix the recorder before sampling again. Sampling now would write a fixture whose "
        "digest covers a region this instrument can no longer identify"
    ),
    "not_observed": "run it again with the network available. ⛔ Nothing is concluded",
}


def classify_drift(
    *, values_changed: int, service_state_changed: int, resource_digest_moved: bool
) -> str:
    """One observation's outcome, from the three things that can have moved.

    ⭐ **The precedence is a decision, and it runs most-specific first.** A value change
    always moves the digest, and a service-state change usually accompanies one, so
    classifying on the digest first would collapse every finding into
    `unclassified_region_moved` and the report would say nothing useful ever again.

    ⚠ **`unclassified_region_moved` is therefore defined by what it is NOT** — the digest
    moved and nothing this instrument names did. That is precisely the case worth a human's
    attention, because it is the case where the recorder's model of the response is
    incomplete.
    """
    if values_changed:
        return "values_moved"
    if service_state_changed:
        return "service_state_moved"
    if resource_digest_moved:
        return "unclassified_region_moved"
    return "no_drift"


#: ⭐ The conditional-reproducibility statement. It is the whole reason the drift job exists.
REPRODUCIBILITY_CONDITION = (
    "⚠ THIS ARTIFACT REGENERATES BYTE-FOR-BYTE ONLY WHILE THE RECORDED SERVICE STATE HOLDS. "
    "A service response is not a file: which solution answered, which auxiliary files were "
    "loaded and which interface replied are the service's state, not the caller's, and they "
    "move on the service's schedule. ⛔ They are therefore recorded AS DATA and excluded "
    "from the resource digest — discarding them as volatile would leave a file that no "
    "longer says what answered it, and digesting them would make the artifact fail its own "
    "reproducibility check the day the service updates something nobody here controls. "
    "⭐ The condition is written into the file so it can be CHECKED rather than discovered: "
    "that check is the drift report, which detects and proposes and ⛔ never gates."
)
