"""Which ephemeris actually answered — the mechanism R3 rests on.

The Swiss Ephemeris accepts a flag naming which ephemeris to use, and **substitutes a
different one, silently, when the requested one is unavailable or does not cover the
requested date.** It returns a value that looks entirely ordinary. So a recorder that asks
for one ephemeris and writes down what came back, without checking *what came back from
where*, can record a file of values it has mislabelled — and a comparison between two such
files can be a comparison of one ephemeris against itself, reporting a reassuring row of
zeros that means only that the comparison did not happen.

⭐ **This module exists so that no value in an R3 fixture is ever attributed to an
ephemeris that did not produce it.** Every recorded value carries an assertion, and the
assertion names how it was obtained.

⛔ **Three kinds of assertion, and the differences are not cosmetic.**

* ``reported`` — the entry point returns a flag saying which ephemeris answered, and it was
  the one asked for. This is the only direct evidence available.
* ``proxy_window`` — the entry point **does not report**, so the source is asserted from a
  separate call that does, taken at both ends of the interval the non-reporting call may
  read. ⚠ A proxy is weaker than a report and is recorded as such on every row that uses
  one. It is *bounded*, not *sound*: see :func:`assert_window`.
* ``none`` — ⛔ **a refusal, not a weaker proxy.** A proxy asserts that a *request* was
  honoured; where the entry point takes no ephemeris argument there is no request to
  honour, and the honest field says so. Such a call consults an ephemeris all the same:
  see :func:`offset_attribution`, where the value moved by more than a hundredth of a
  second with nothing changed but a path handed to an unrelated call.

⚠ **Which entry points report is a measured fact, not a documented one** — see
:data:`ENTRY_POINTS`. One of them returns a flag that merely echoes the request; two return
a bare float with no flag, no code and no error channel at all.

⛔ **Recorder, never explainer.** This module records what the library returned and under
which flags. It contains no account of how any ephemeris is evaluated.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable

import swisseph as swe

from .kernels import PINS, KernelIdentityError, KernelPin, verify

#: The three ephemeris-source bits. ⛔ Only these are compared: a returned flag also carries
#: bits for speed, sidereal mode and coordinate system, and those legitimately differ from
#: the request. Masking to the source bits is what makes the assertion an assertion about
#: the *source* rather than about the whole call.
SOURCE_MASK = swe.FLG_JPLEPH | swe.FLG_SWIEPH | swe.FLG_MOSEPH

#: Source bit -> the name this repository uses for it. The library's own vocabulary, kept
#: as the library's, so a reader can map a fixture back to a flag without a table.
SOURCE_NAMES: dict[int, str] = {
    swe.FLG_JPLEPH: "jpl_file",
    swe.FLG_SWIEPH: "swiss_file",
    swe.FLG_MOSEPH: "moshier",
}


@dataclass(frozen=True)
class Mode:
    """One ephemeris source, as a thing that can be requested and then checked."""

    id: str
    flag: int
    label: str
    needs_data_files: bool

    @property
    def source(self) -> str:
        return SOURCE_NAMES[self.flag]


#: The two modes R3 records. ⚠ `moshier` needs no data file and therefore cannot be
#: substituted *away from*; `swiss_file` can, which is the whole reason this module exists.
MODES: dict[str, Mode] = {
    "moshier": Mode(
        id="moshier",
        flag=swe.FLG_MOSEPH,
        label="the library's built-in analytical ephemeris; no data file",
        needs_data_files=False,
    ),
    "swiss_file": Mode(
        id="swiss_file",
        flag=swe.FLG_SWIEPH,
        label="the library's own compressed data files, supplied on the command line",
        needs_data_files=True,
    ),
}


class EphemerisSubstitution(Exception):
    """A call was answered by an ephemeris other than the one requested.

    ⛔ Never caught and downgraded to a warning inside a value path. A substituted value is
    recorded as a substitution, never as a value of the requested ephemeris.
    """


def source_name(flag_value: int) -> str:
    """The source named by a returned flag, or an explicit statement that none is."""
    masked = flag_value & SOURCE_MASK
    return SOURCE_NAMES.get(masked, f"unnamed_source_bits_{masked}")


def assert_reported(mode: Mode, returned: int, *, where: str) -> dict[str, Any]:
    """Check a returned flag against the mode that was requested.

    ⛔ Raises rather than returning a verdict. A caller that receives a verdict may write
    the value anyway; a caller that receives an exception cannot.
    """
    answered = source_name(returned)
    if (returned & SOURCE_MASK) != mode.flag:
        raise EphemerisSubstitution(
            f"{where}: requested {mode.source}, answered by {answered}. "
            "The value is a valid value of the WRONG ephemeris."
        )
    return {
        "kind": "reported",
        "requested": mode.source,
        "answered": answered,
        "returned_flag": returned,
    }


def assert_window(
    mode: Mode,
    *,
    body: int,
    jd_start: float,
    jd_end: float,
    where: str,
    calc: Callable[[float, int, int], tuple[Any, int]] | None = None,
) -> dict[str, Any]:
    """Assert the source of a call that does not report one, from calls that do.

    Some entry points take an ephemeris flag, consult an ephemeris, and return **no flag at
    all** — house cusps and rise/set times among them, which is to say the lagna and the
    sunrise. There is no direct evidence available for those, so the source is asserted from
    a reporting call on the same body, at **both ends** of the interval the non-reporting
    call may read.

    ⚠ **Bounded, not sound, and the bound was measured rather than assumed.** Sampled
    across a data-file coverage edge, the two ends disagreed for every start instant within
    half a day before the edge, while the non-reporting call went on returning an answer
    that differed between the two modes — so at those instants neither end alone described
    what the call had done. Requiring *both* ends to report the requested source excludes
    exactly that region. ⛔ It does not establish that the non-reporting call read only
    within the window; it establishes that the whole window was covered by the requested
    ephemeris, which is the strongest statement the library's own reporting supports.
    """
    if jd_end < jd_start:
        raise ValueError(f"{where}: window ends before it starts")
    call = calc or (lambda jd, planet, flags: swe.calc_ut(jd, planet, flags))
    ends: list[dict[str, Any]] = []
    for label, jd in (("start", jd_start), ("end", jd_end)):
        _, returned = call(jd, body, mode.flag | swe.FLG_SPEED)
        answered = source_name(returned)
        ends.append({"end": label, "jd_ut": jd, "answered": answered})
        if (returned & SOURCE_MASK) != mode.flag:
            raise EphemerisSubstitution(
                f"{where}: no source report from this entry point; the proxy at the {label} "
                f"of its window was answered by {answered}, not {mode.source}. "
                "Refusing to attribute the value."
            )
    return {
        "kind": "proxy_window",
        "requested": mode.source,
        "answered": mode.source,
        "proxy_entry_point": "calc_ut",
        "proxy_body": body,
        "window_jd_ut": [jd_start, jd_end],
        "ends": ends,
        "strength": (
            "weaker than a report: the entry point returns no source flag, so both ends of "
            "the interval it may read were checked with one that does"
        ),
    }


# --------------------------------------------------------------------------------------
# What each entry point actually tells you — measured, not read off documentation
# --------------------------------------------------------------------------------------


#: The three assertions a recorder can make about where a value came from, weakest last.
#:
#: ⛔ **`none` is not a tidier spelling of `proxy_window`.** A proxy asserts that a *request*
#: was honoured over the interval the silent call may read. Where nothing was requested — an
#: entry point that takes no ephemeris argument at all — there is no request to honour and
#: the proxy has nothing to say. ⚠ Such a call still consults an ephemeris; it simply cannot
#: be asked which, so the honest field is a refusal and not a weaker claim.
ASSERTIONS: tuple[str, ...] = ("reported", "proxy_window", "none")

#: What a proxy costs, in the words `assert_window` already writes onto every row that uses
#: one. ⚠ Kept as one string so the caveat cannot drift row by row into something softer.
_WINDOW_CAVEAT = (
    "⚠ bounded, not sound: it establishes that the requested ephemeris covered the whole "
    "window, ⛔ not that the silent call read only inside it"
)


@dataclass(frozen=True)
class EntryPoint:
    """One library entry point, and whether it reports the ephemeris that answered."""

    name: str
    accepts_flag: bool
    reports_source: bool
    returns: str
    evidence: str
    #: ⭐ What the entry point returns a value **of**. Recorded because the proxy that
    #: stands in for a missing report is a call about a *position*, and two of these
    #: entry points do not return positions — see `assertion_caveat`.
    quantity: str
    #: ⛔ **Declared, never derived.** It was derived once — `reported` if the entry point
    #: reports and `proxy_window` otherwise — and that rule is wrong in both directions
    #: for the time-offset entry points below: one has a proxy that is about a different
    #: quantity, and the other has no proxy at all.
    assertion_available: str
    #: Why the available assertion is less than it looks, or empty where it is not.
    assertion_caveat: str = ""


class EntryPointDeclarationError(Exception):
    """A row of the audit table declares an assertion its own other fields deny."""


class SurveyRefusal(Exception):
    """A survey declines to publish a verdict its own subject cannot support.

    ⛔ Distinct from :class:`EphemerisSubstitution`, which says a value came from the
    wrong place. This says the *measurement* was not one -- the grid it ran on did not
    carry the property being surveyed, so its silence is a fact about the grid.
    """


#: ⭐ **The audit that makes the rest of R3 possible.** Every row of this table was
#: established by calling the entry point under conditions where the requested ephemeris was
#: known to be unavailable, and reading what came back.
#:
#: ⚠ Four of these take an ephemeris flag and return no source at all, one returns a source
#: that is not a source — it is the request, handed back — and one takes no flag and answers
#: anyway. A rule that says only "assert the returned flag" is satisfied by the echoing one
#: and learns nothing, and is not even applicable to the last.
ENTRY_POINTS: tuple[EntryPoint, ...] = (
    EntryPoint(
        name="calc_ut",
        accepts_flag=True,
        reports_source=True,
        returns="(values, returned_flag)",
        quantity="a position",
        evidence=(
            "with no data-file path set, a data-file request returned the analytical "
            "source bit; with the path set and an in-coverage date it returned the "
            "data-file bit; with the path set and an out-of-coverage date it returned the "
            "analytical bit again"
        ),
        assertion_available="reported",
    ),
    EntryPoint(
        name="get_ayanamsa_ex_ut",
        accepts_flag=True,
        reports_source=False,
        returns="(returned_flag, value)",
        quantity="an ayanamsha",
        evidence=(
            "⛔ the returned flag ECHOES the request. With no data-file path set at all — "
            "where calc_ut reports the analytical source — this entry point still returned "
            "the data-file bit it was handed. A flag that cannot report a substitution is "
            "not evidence of its absence"
        ),
        assertion_available="proxy_window",
        assertion_caveat=_WINDOW_CAVEAT,
    ),
    EntryPoint(
        name="houses_ex",
        accepts_flag=True,
        reports_source=False,
        returns="(cusps, ascmc)",
        quantity="house cusps",
        evidence="no flag is returned; the value carries no statement about its source",
        assertion_available="proxy_window",
        assertion_caveat=_WINDOW_CAVEAT,
    ),
    EntryPoint(
        name="rise_trans",
        accepts_flag=True,
        reports_source=False,
        returns="(return_code, times)",
        quantity="rise and set times",
        evidence=(
            "the integer returned is a success/failure code, not an ephemeris flag: it was "
            "0 both where the requested ephemeris answered and where it was substituted"
        ),
        assertion_available="proxy_window",
        assertion_caveat=_WINDOW_CAVEAT + (
            " ⭐ Of the silent entry points this is the one whose proxy is taken on the same "
            "body it was asked about"
        ),
    ),
    # ------------------------------------------------------------------------------
    # ⛔ The two the survey was extended to, and the pair the survey REFUSES to attribute.
    # ------------------------------------------------------------------------------
    EntryPoint(
        name="deltat_ex",
        accepts_flag=True,
        reports_source=False,
        returns="a bare float — no flag, no code, no error channel",
        quantity="the offset from civil to dynamical time",
        evidence=(
            "⛔ THE FLAG IS TAKEN AS A DECLARATION, NOT AS A REQUEST THAT CAN FAIL. Handed "
            "the JPL flag with no JPL file on the machine, this entry point computed on the "
            "JPL tidal constant and returned a number — while calc_ut, handed the SAME flag "
            "in the SAME session state, reported that the data files had answered instead. "
            "⚠ And handed the data-file flag with the data files removed, it moved silently "
            "to the library's default constant rather than to the analytical ephemeris's, "
            "which is the one calc_ut then reported as the answering source. ⛔ The binding "
            "documents that a call before any path is set 'will raise'; measured, it "
            "returns a value"
        ),
        assertion_available="proxy_window",
        assertion_caveat=(
            "⛔ THE PROXY IS ABOUT A DIFFERENT QUANTITY AND THE TWO WERE MEASURED COMING "
            "APART. calc_ut reports which ephemeris supplied a POSITION; this entry point "
            "returns a time offset computed from a tidal-acceleration constant, and the "
            "constant in force was measured disagreeing with the reported source under one "
            "unchanged flag. ⇒ the proxy bounds the window and establishes nothing about "
            "this value's basis, so no ephemeris_basis is written for it"
        ),
    ),
    EntryPoint(
        name="deltat",
        accepts_flag=False,
        reports_source=False,
        returns="a bare float — no flag, no code, no error channel",
        quantity="the offset from civil to dynamical time",
        evidence=(
            "⛔ IT TAKES NO EPHEMERIS ARGUMENT AND HAS AN EPHEMERIS ANYWAY. The same instant "
            "returned two different numbers — differing by more than a hundredth of a "
            "second — with nothing changed but a directory path handed to an unrelated "
            "call. It silently equalled the data-file answer where the files were present "
            "and the default answer where they were not, and said so neither time. ⚠ The "
            "binding's own documentation calls this 'an uncertain guess of what ephemeris "
            "is being used'"
        ),
        assertion_available="none",
        assertion_caveat=(
            "⛔ NOT A WEAKER CLAIM — NO CLAIM. Nothing was requested, so there is no request "
            "for a proxy to find honoured. The value's basis is whatever process-global "
            "state a prior unrelated call happened to leave behind"
        ),
    ),
)

#: The entry points whose own return value is sufficient evidence of source.
REPORTING = frozenset(e.name for e in ENTRY_POINTS if e.reports_source)

#: ⛔ **The entry points for which no source may be written down at all.** A row recording a
#: value from one of these carries the refusal itself where a lesser repository would carry
#: a plausible name.
REFUSES_ATTRIBUTION = frozenset(
    e.name for e in ENTRY_POINTS if e.assertion_available == "none"
)


def _check_declaration(e: EntryPoint) -> None:
    """Refuse a row whose declared assertion its own other fields deny.

    ⛔ The derivation this replaces was a rule with no exceptions and therefore no way to
    be wrong out loud. Making the field explicit puts the burden back on the editor, so the
    invariants that *are* universal are enforced here instead of assumed.
    """
    if e.assertion_available not in ASSERTIONS:
        raise EntryPointDeclarationError(
            f"{e.name}: assertion_available={e.assertion_available!r} is not one of "
            f"{list(ASSERTIONS)}"
        )
    if e.reports_source and e.assertion_available != "reported":
        raise EntryPointDeclarationError(
            f"{e.name}: it reports its own source, so the assertion available for it is "
            f"'reported' and not {e.assertion_available!r}"
        )
    if not e.reports_source and e.assertion_available == "reported":
        raise EntryPointDeclarationError(
            f"{e.name}: it returns no report, so 'reported' is not available for it"
        )
    if e.accepts_flag and e.assertion_available == "none":
        raise EntryPointDeclarationError(
            f"{e.name}: it takes an ephemeris flag, so a request exists and a proxy can be "
            "asked whether it was honoured. 'none' is for entry points with no request"
        )
    if not e.accepts_flag and e.assertion_available != "none":
        raise EntryPointDeclarationError(
            f"{e.name}: it takes no ephemeris flag, so there is no request for a proxy to "
            f"find honoured; {e.assertion_available!r} would assert about nothing"
        )
    if e.assertion_available != "reported" and not e.assertion_caveat:
        raise EntryPointDeclarationError(
            f"{e.name}: every assertion weaker than a report costs the reader something, "
            "and an uncaveated one reads as free"
        )


for _entry in ENTRY_POINTS:
    _check_declaration(_entry)
del _entry


def entry_point_records(
    entries: Iterable[EntryPoint] = ENTRY_POINTS,
) -> list[dict[str, Any]]:
    """The audit table, as fixture rows.

    ⛔ **Every row is re-checked on the way out, not only at import.** The import-time
    loop above is one statement, and deleting one statement is the cheapest way for this
    table to start lying; the check on the writing path is the one a disarming sweep can
    reach.
    """
    entries = list(entries)
    for entry in entries:
        _check_declaration(entry)
    return [
        {
            "finding": "flag_reporting",
            "entry_point": e.name,
            "quantity_returned": e.quantity,
            "accepts_ephemeris_flag": e.accepts_flag,
            "reports_answering_ephemeris": e.reports_source,
            "returns": e.returns,
            "evidence": e.evidence,
            "assertion_available": e.assertion_available,
            "assertion_caveat": e.assertion_caveat,
        }
        for e in entries
    ]


# --------------------------------------------------------------------------------------
# The data files, pinned by digest like every other acquired file
# --------------------------------------------------------------------------------------

#: The library's own data files, pinned. ⛔ Never committed here; a path is supplied on the
#: command line and every file in it is hashed before a single value is read.
#:
#: ⚠ These are added to the shared pin registry rather than kept separately, because the
#: property being enforced is identical: the right name is not the right file.
EPHE_PINS: dict[str, KernelPin] = {
    "seas_18.se1": KernelPin(
        dataset="seas_18.se1",
        profile="swiss_file@1",
        size_bytes=223_004,
        sha256="a2cd8fc33807c78ca9a700c91c2e042258b12fc4796519e00781440b5ad8b2e2",
        publisher="Astrodienst AG",
        pinned_on="2026-08-04",
    ),
    "semo_18.se1": KernelPin(
        dataset="semo_18.se1",
        profile="swiss_file@1",
        size_bytes=1_304_771,
        sha256="1ca07bd67c24374d77226180c20a4f9996cba013697894810518e7eb582ca4f7",
        publisher="Astrodienst AG",
        pinned_on="2026-08-04",
    ),
    "sepl_18.se1": KernelPin(
        dataset="sepl_18.se1",
        profile="swiss_file@1",
        size_bytes=484_061,
        sha256="ca1393ceab3a44fbc895887cf789c68819ae6a1cbc9b22225872dbe4ccd99a66",
        publisher="Astrodienst AG",
        pinned_on="2026-08-04",
    ),
}

PINS.update(EPHE_PINS)

#: The library reads whatever data files it finds in the directory it is given.
_DATA_SUFFIX = ".se1"


def verify_ephe_set(directory: Path) -> list[KernelPin]:
    """Verify every data file in the directory, and refuse one that is not pinned.

    ⛔ **The whole directory is the input, not the files anyone meant to use.** The library
    is handed a path and reads what it finds there; an unpinned extra file changes which
    data can answer, and it does so without changing anything a caller passes. So an
    unrecognised data file is a refusal, not something to skip.

    ⚠ An empty directory is refused too. It would leave every data-file request silently
    answered by the analytical ephemeris, which is precisely the substitution this
    repository exists to make visible.
    """
    directory = Path(directory)
    if not directory.is_dir():
        raise KernelIdentityError(f"{directory}: no such directory")
    found = sorted(p for p in directory.iterdir() if p.suffix.lower() == _DATA_SUFFIX)
    if not found:
        raise KernelIdentityError(
            f"{directory}: no {_DATA_SUFFIX} file here. Every data-file request would be "
            "answered by the analytical ephemeris instead, and would look ordinary."
        )
    pins: list[KernelPin] = []
    for path in found:
        pin = EPHE_PINS.get(path.name.lower())
        if pin is None:
            raise KernelIdentityError(
                f"{path.name}: an unpinned data file in the directory the library will read. "
                f"Known: {sorted(EPHE_PINS)}"
            )
        pins.append(verify(path, pin))
    return pins


def ephe_set_identity(directory: Path, pins: Iterable[KernelPin]) -> dict[str, Any]:
    """The data-file half of a fixture's `oracle` block."""
    return {
        "directory_contents_verified": True,
        "files": [
            {
                "dataset": pin.dataset,
                "profile": pin.profile,
                "size_bytes": pin.size_bytes,
                "sha256": pin.sha256,
                "publisher": pin.publisher,
                "pinned_on": pin.pinned_on,
            }
            for pin in pins
        ],
        "unpinned_file_policy": (
            "refused. The library reads the directory, so a file nobody passed can still "
            "answer"
        ),
    }


# --------------------------------------------------------------------------------------
# ⛔ The answering ephemeris is not a function of the call's arguments
# --------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Session:
    """The library's global state, and the means of putting it back to a known one.

    ⛔ **This exists because which ephemeris answers a call was measured to depend on what
    was computed before it.** Not on a monotone history — on the immediately preceding call:
    the same instant answered by the data files in a fresh process was answered by the
    substituted ephemeris after one unrelated call fifty days outside coverage, and by the
    data files again after one call well inside. Sweeping a range upwards and downwards put
    the boundary ten days apart.

    ⭐ So a recorded value is only a function of its own request if the state is put back
    first. Resetting before each recorded call group costs about 0.08 ms and buys a fixture
    whose rows do not depend on the order the generator happened to visit them in.

    ⚠ **Closing the library resets the sidereal mode too**, and silently: an ayanamsha read
    after a reset that did not re-apply it was measured 0.88 degrees away, which is a
    plausible-looking number in the same range as the right one. Every field this class
    holds is re-applied on every reset for that reason — a reset that restores some of the
    state is worse than none, because the part it drops is invisible.
    """

    ephe_path: str
    sidereal_mode: int

    def reset(self) -> None:
        swe.close()
        swe.set_ephe_path(self.ephe_path)
        swe.set_sid_mode(self.sidereal_mode, 0, 0)

    def identity(self) -> dict[str, Any]:
        return {
            "isolation": (
                "the library's state is closed and re-established before each recorded call "
                "group"
            ),
            "why": (
                "⛔ which ephemeris answers a call was measured to depend on the preceding "
                "call, not only on the call's own arguments"
            ),
            "state_re_applied": ["data file path", "sidereal mode"],
            "sidereal_mode_number": self.sidereal_mode,
            "note": (
                "closing the library resets the sidereal mode as well; a reset that does not "
                "re-apply it moves every sidereal value by about 0.88 degrees"
            ),
        }


# --------------------------------------------------------------------------------------
# Where the data files stop answering — measured, never assumed
# --------------------------------------------------------------------------------------


def coverage_edges(
    mode: Mode, *, body: int, jd_low: float, jd_high: float, session: Session
) -> dict[str, Any]:
    """Find where the requested ephemeris stops answering, from a reset state each time.

    ⭐ The returned flag is used here as an *instrument*: the boundary is located by asking
    the library which ephemeris answered, not by reading a published coverage range. A
    different data-file set therefore yields different edges, which is correct — the edge is
    a property of the files supplied, and hard-coding one would outlive the file it
    describes.

    ⛔ **Every probe is taken from a reset state, and this is not a refinement.** Probed
    warm, the predicate is not a function of the instant at all: bisecting it converged on
    different answers in different runs, and one of them returned a "last outside" point
    that answered as inside. A bisection needs a predicate; without the reset there is none.

    ⚠ The postcondition is checked rather than assumed. A boundary search that reports an
    interval it has not re-verified is the same defect as a fixture that records a value
    without recording where it came from.
    """

    def answered(jd: float) -> bool:
        session.reset()
        try:
            _, returned = swe.calc_ut(jd, body, mode.flag | swe.FLG_SPEED)
        except Exception:
            return False
        return (returned & SOURCE_MASK) == mode.flag

    def bisect(outside: float, inside: float) -> tuple[float, float]:
        for _ in range(200):
            mid = (outside + inside) / 2.0
            if mid == outside or mid == inside:
                break
            if answered(mid):
                inside = mid
            else:
                outside = mid
        return outside, inside

    middle = (jd_low + jd_high) / 2.0
    if not answered(middle):
        raise EphemerisSubstitution(
            "the midpoint of the search range is not answered by the requested ephemeris, "
            "so there is no covered interval to find edges of"
        )
    low_out, low_in = bisect(jd_low, middle)
    high_out, high_in = bisect(jd_high, middle)

    # ⛔ Re-verify. Each of these four points is a claim, and each is cheap to check.
    for jd, expected, name in (
        (low_in, True, "lower_edge_first_inside"),
        (low_out, False, "lower_edge_last_outside"),
        (high_in, True, "upper_edge_first_inside"),
        (high_out, False, "upper_edge_last_outside"),
    ):
        if answered(jd) != expected:
            raise EphemerisSubstitution(
                f"{name} at jd {jd!r} does not have the property the search assigned it "
                f"(expected answered={expected}). The predicate is not stable, so no "
                "boundary may be reported from it."
            )

    return {
        "body": body,
        "located_by": (
            "bisection on the returned ephemeris flag, every probe taken from a reset "
            "library state, endpoints re-verified"
        ),
        "lower_edge_last_outside_jd_ut": low_out,
        "lower_edge_first_inside_jd_ut": low_in,
        "upper_edge_first_inside_jd_ut": high_in,
        "upper_edge_last_outside_jd_ut": high_out,
        "lower_edge_calendar_ut": calendar_ut(low_in),
        "upper_edge_calendar_ut": calendar_ut(high_in),
        "search_range_jd_ut": [jd_low, jd_high],
        "scope": (
            "this edge is the one body's. The data files do not share a boundary, so a "
            "different body has a different edge"
        ),
    }


def state_dependence(
    mode: Mode, *, body: int, jd_first_outside: float, session: Session, span_days: int = 22
) -> list[dict[str, Any]]:
    """Measure how far the answering ephemeris moves with call order alone.

    ⭐ Three sweeps over the same instants, differing only in the order they are visited and
    whether the state is reset — plus a three-call demonstration that a single unrelated
    call flips the answer for an instant that did not change.

    ⛔ This is the measurement that makes the per-row assertion non-negotiable. A recorder
    that decides once which instants are covered, and then trusts that decision, is wrong
    for every instant inside the interval these three sweeps disagree on.
    """
    start = jd_first_outside - span_days / 2.0
    instants = [start + float(i) for i in range(span_days)]

    def warm(jd: float) -> bool:
        try:
            _, returned = swe.calc_ut(jd, body, mode.flag | swe.FLG_SPEED)
        except Exception:
            return False
        return (returned & SOURCE_MASK) == mode.flag

    def first_substituted(values: list[tuple[float, bool]]) -> float | None:
        for jd, ok in values:
            if not ok:
                return jd
        return None

    session.reset()
    ascending = [(jd, warm(jd)) for jd in instants]
    session.reset()
    descending = list(reversed([(jd, warm(jd)) for jd in reversed(instants)]))
    cold: list[tuple[float, bool]] = []
    for jd in instants:
        session.reset()
        cold.append((jd, warm(jd)))

    rows: list[dict[str, Any]] = []
    for label, values in (
        ("ascending_warm", ascending),
        ("descending_warm", descending),
        ("cold_per_call", cold),
    ):
        edge = first_substituted(values)
        rows.append(
            {
                "finding": "state_dependence",
                "sweep": label,
                "body": body,
                "instants": len(values),
                "first_substituted_jd_ut": edge,
                "first_substituted_calendar_ut": calendar_ut(edge) if edge else None,
                "answered_by_request": sum(1 for _, ok in values if ok),
            }
        )

    # ⭐ The three-call demonstration. One instant, three readings, nothing about the
    #    instant changing between them.
    probe = jd_first_outside - 2.0
    session.reset()
    fresh = warm(probe)
    warm(jd_first_outside + 48.0)
    after_far = warm(probe)
    warm(2451545.0)
    after_near = warm(probe)
    rows.append(
        {
            "finding": "state_dependence",
            "sweep": "single_intervening_call",
            "body": body,
            "probe_jd_ut": probe,
            "probe_calendar_ut": calendar_ut(probe),
            "answered_by_request_when_fresh": fresh,
            "answered_by_request_after_a_call_outside_coverage": after_far,
            "answered_by_request_after_a_call_inside_coverage": after_near,
            "meaning": (
                "⛔ the same instant, the same body, the same flags, three different "
                "sessions of one process. The ephemeris that answers is not a function of "
                "the call's arguments"
            ),
        }
    )
    return rows


# --------------------------------------------------------------------------------------
# ⛔ The time offset: an entry point that cannot be asked, surveyed live
# --------------------------------------------------------------------------------------

#: The library's own tidal-acceleration vocabulary, read out of the library rather than
#: typed here. ⭐ **The whole finding below is a statement about this table**, so the table
#: has to be the library's; a hand-copied one could be made to say anything.
TIDAL_CONSTANTS: dict[str, float] = {
    name: float(getattr(swe, name)) for name in dir(swe) if name.startswith("TIDAL_")
}

#: The three entries of that table that name an ephemeris *source* rather than a data set.
#: ⛔ Two of them hold the same number, which is the reason the survey below refuses.
TIDAL_BY_SOURCE: dict[str, float] = {
    "moshier": TIDAL_CONSTANTS["TIDAL_MOSEPH"],
    "swiss_file": TIDAL_CONSTANTS["TIDAL_SWIEPH"],
    "jpl_file": TIDAL_CONSTANTS["TIDAL_JPLEPH"],
}


def bits_of(value: float) -> str:
    """The bit pattern of a double. ⛔ Deferred so there is one writer, never two."""
    from .fixture import bits

    return bits(value)


def tidal_constant_names(value: float) -> list[str]:
    """Every name the library gives to a tidal-acceleration value. Often more than one."""
    return sorted(name for name, held in TIDAL_CONSTANTS.items() if held == value)


def sources_named_by_constant(value: float) -> list[str]:
    """The ephemeris sources a tidal constant could be the constant *of*, per the library.

    ⭐ **The instrument that must be able to answer as well as refuse.** For the analytical
    ephemeris's constant this returns one name; for the number two of the library's own
    source constants share, it returns two; for the constant an actual data file puts in
    force it returns none, because that number is not any source's named constant at all.
    ⇒ a survey that only ever returned an empty list would be measuring nothing, and this
    is checked in the same run rather than argued.
    """
    return sorted(name for name, held in TIDAL_BY_SOURCE.items() if held == value)


def source_bits_in_return(returned: Any) -> dict[str, Any]:
    """Read a return value for a source report **without knowing what produced it**.

    ⛔ **This is the control on the reader, not on the library.** "No flag came back" and
    "this harness does not look at flags" are the same observation from the outside, and
    only one of them is a finding. So the same blind procedure is run over the return of an
    entry point known to report, over the returns of the two that are the subject here, and
    over one that returns an integer which is *not* a flag — and the three answers are
    recorded together.
    """
    integers: list[int] = []

    def walk(value: Any) -> None:
        if isinstance(value, bool):
            return
        if isinstance(value, int):
            integers.append(value)
        elif isinstance(value, (tuple, list)):
            for item in value:
                walk(item)

    walk(returned)
    named = sorted({SOURCE_NAMES[i & SOURCE_MASK] for i in integers if (i & SOURCE_MASK) in SOURCE_NAMES})
    return {
        "integers_in_return": integers,
        "named_sources_readable": named,
        "carries_a_source": bool(named),
    }


def _harness_control(session: Session, jd: float) -> dict[str, Any]:
    """One row: the blind reader, run over four returns whose answers are known to differ."""
    session.reset()
    calc = swe.calc_ut(jd, swe.SUN, swe.FLG_SWIEPH | swe.FLG_SPEED)
    session.reset()
    rise = swe.rise_trans(
        jd, swe.SUN, swe.CALC_RISE | swe.BIT_DISC_CENTER,
        (0.0, 0.0, 0.0), 0.0, 0.0, swe.FLG_SWIEPH,
    )
    session.reset()
    ex = swe.deltat_ex(jd, swe.FLG_SWIEPH)
    session.reset()
    plain = swe.deltat(jd)
    readings = {
        "calc_ut": source_bits_in_return(calc),
        "rise_trans": source_bits_in_return(rise),
        "deltat_ex": source_bits_in_return(ex),
        "deltat": source_bits_in_return(plain),
    }
    return {
        "finding": "offset_attribution",
        "row": "harness_control",
        "purpose": (
            "⭐ THE CONTROL SITS INSIDE THE MEASUREMENT. The same blind reader is run over "
            "four returns before any conclusion is drawn from a silence"
        ),
        "readings": readings,
        "reader_can_see_a_report_where_one_exists": readings["calc_ut"]["carries_a_source"],
        "reader_is_not_fooled_by_an_integer_that_is_not_a_flag": (
            not readings["rise_trans"]["carries_a_source"]
            and bool(readings["rise_trans"]["integers_in_return"])
        ),
        "the_two_offset_entry_points_return_no_integer_at_all": (
            not readings["deltat_ex"]["integers_in_return"]
            and not readings["deltat"]["integers_in_return"]
        ),
        "meaning": (
            "⛔ the offset entry points return a bare float. There is no flag to assert, no "
            "code to check and no error channel to read — the binding drops the library's "
            "own message buffer for these two"
        ),
    }


def assert_library_state_returned(
    *, before_constant: float, before_flag: int, after_constant: float, after_flag: int
) -> None:
    """Refuse to continue where a survey left the library pointed somewhere else.

    ⛔ **A survey that constructs a deliberately broken state owes the run its state
    back.** Left pointed at a directory with no data file, every later call is answered
    analytically -- successfully, plausibly and without a word, which is the exact failure
    this whole module exists to make visible. ⭐ So the restoration is measured on two
    channels rather than assumed from the fact that a reset was called.
    """
    if after_constant == before_constant and after_flag == before_flag:
        return
    raise EphemerisSubstitution(
        "the library did not come back. The tidal constant read "
        f"{before_constant!r} before the survey and {after_constant!r} after it, and a "
        f"data-file request was answered by {source_name(before_flag)} before and "
        f"{source_name(after_flag)} after. ⛔ Every later measurement in this run would "
        "have been taken against the wrong ephemeris, successfully and silently."
    )


def offset_attribution(
    *,
    epochs: Iterable[tuple[str, float]],
    with_files: Session,
    without_files: Session,
) -> list[dict[str, Any]]:
    """Survey what `deltat_ex` and `deltat` say about the ephemeris behind their answer.

    ⛔ **The expected result is a refusal, and the refusal is the finding.** These two
    entry points consult an ephemeris — measurably, in that their answers move with one —
    and neither returns any statement of which. The only channel that carries anything
    about the basis is the tidal-acceleration constant in force, and that constant was
    measured to be **not an identifier**: the library's own names for the data-file source
    and the JPL source hold the same number, and the number an actual data file puts in
    force is not either of them. ⇒ no `ephemeris_basis` is written.

    ⚠ **Two regimes, because an equality between two readings means nothing until a case
    exists where they differ.** One session has the pinned data files; the other has none,
    which is a state `verify_ephe_set` refuses for recording and which is constructed here
    deliberately, as the condition being surveyed.

    ⛔ **And two epochs, because the property under test is not present everywhere.** At a
    modern instant all three flags return the same offset, so a survey run only there would
    report no dependence and would have measured nothing. The epochs are checked for the
    property before any verdict is read off them.
    """
    epochs = list(epochs)
    rows: list[dict[str, Any]] = [_harness_control(with_files, epochs[0][1])]

    regimes = (
        ("data_files_present", with_files, True),
        ("data_files_absent", without_files, False),
    )
    flags = (("moshier", swe.FLG_MOSEPH), ("swiss_file", swe.FLG_SWIEPH), ("jpl_file", swe.FLG_JPLEPH))
    identifying = 0
    disagreements = 0

    for regime, session, files_present in regimes:
        for epoch_id, jd in epochs:
            readings: dict[str, float] = {}
            for requested, flag in flags:
                session.reset()
                _, returned = swe.calc_ut(jd, swe.SUN, flag | swe.FLG_SPEED)
                position_answered = source_name(returned)
                session.reset()
                offset = float(swe.deltat_ex(jd, flag))
                constant = float(swe.get_tid_acc())
                readings[requested] = offset
                candidates = sources_named_by_constant(constant)
                identifies = len(candidates) == 1
                identifying += int(identifies)
                agrees = identifies and candidates[0] == position_answered
                disagreements += int(not agrees)
                if agrees:
                    verdict = (
                        "the constant names one source and it is the one the position call "
                        "reported. ⭐ The instrument can return agreement, which is what "
                        "makes its refusals elsewhere worth reading"
                    )
                elif not candidates:
                    verdict = (
                        "⛔ THE CONSTANT NAMES NO SOURCE AT ALL. It is the value an actual "
                        "data file puts in force, and that number is not the library's "
                        "named constant for any of its three ephemeris sources"
                    )
                elif len(candidates) > 1:
                    verdict = (
                        "⛔ THE CONSTANT NAMES MORE THAN ONE SOURCE. Two of the library's "
                        "own source constants hold this same number, so it cannot "
                        "discriminate between them"
                    )
                else:
                    verdict = (
                        "⛔ THE CONSTANT NAMES A DIFFERENT SOURCE FROM THE ONE THE POSITION "
                        "CALL REPORTED. One flag, one session, one instant — and the offset "
                        "and the position do not rest on the same ephemeris"
                    )
                rows.append(
                    {
                        "finding": "offset_attribution",
                        "row": "per_flag",
                        "regime": regime,
                        "data_files_present": files_present,
                        "epoch_id": epoch_id,
                        "jd_ut": jd,
                        "jd_ut_bits": bits_of(jd),
                        "utc": calendar_ut(jd),
                        "entry_point": "deltat_ex",
                        "ephemeris_requested": requested,
                        "offset_days": offset,
                        "offset_days_bits": bits_of(offset),
                        "offset_seconds": offset * 86400.0,
                        "tidal_constant_in_force": constant,
                        "library_names_for_that_constant": tidal_constant_names(constant),
                        "sources_that_constant_could_name": candidates,
                        "constant_identifies_exactly_one_source": identifies,
                        "position_call_under_the_same_flag_answered_by": position_answered,
                        "constant_and_reported_source_agree": agrees,
                        "agreement_verdict": verdict,
                        "ephemeris_basis": (
                            "⛔ REFUSED. This entry point returns no report, and the tidal "
                            "constant behind its answer is not an identifier: see "
                            "`sources_that_constant_could_name`. ⚠ The neighbouring field "
                            "`position_call_under_the_same_flag_answered_by` is a fact "
                            "about a POSITION and is recorded as evidence, ⛔ never as this "
                            "value's basis"
                        ),
                    }
                )

            session.reset()
            unflagged = float(swe.deltat(jd))
            constant = float(swe.get_tid_acc())
            spread = (max(readings.values()) - min(readings.values())) * 86400.0
            rows.append(
                {
                    "finding": "offset_attribution",
                    "row": "unflagged",
                    "regime": regime,
                    "data_files_present": files_present,
                    "epoch_id": epoch_id,
                    "jd_ut": jd,
                    "jd_ut_bits": bits_of(jd),
                    "utc": calendar_ut(jd),
                    "entry_point": "deltat",
                    "accepts_ephemeris_flag": False,
                    "offset_days": unflagged,
                    "offset_days_bits": bits_of(unflagged),
                    "tidal_constant_in_force": constant,
                    "library_names_for_that_constant": tidal_constant_names(constant),
                    "equals_the_flagged_answer_for": sorted(
                        k for k, v in readings.items() if v == unflagged
                    ),
                    "spread_across_the_three_flags_seconds": spread,
                    "this_epoch_has_the_property_under_test": spread != 0.0,
                    "ephemeris_basis": (
                        "⛔ REFUSED, AND NOT FOR WANT OF A PROXY. Nothing was requested of "
                        "this entry point, so there is no request a proxy could find "
                        "honoured. It has an ephemeris anyway"
                    ),
                }
            )

    per_epoch: dict[str, dict[str, float]] = {}
    for row in rows:
        if row.get("row") == "unflagged":
            per_epoch.setdefault(str(row["epoch_id"]), {})[str(row["regime"])] = float(
                row["offset_days"]
            )
    moved = {
        epoch_id: (values["data_files_present"] - values["data_files_absent"]) * 86400.0
        for epoch_id, values in per_epoch.items()
        if len(values) == 2
    }
    with_property = sorted(
        {str(r["epoch_id"]) for r in rows if r.get("this_epoch_has_the_property_under_test")}
    )
    without_property = sorted(
        {
            str(r["epoch_id"])
            for r in rows
            if r.get("row") == "unflagged" and not r["this_epoch_has_the_property_under_test"]
        }
    )
    # ⛔ THE FIXTURE MUST HAVE THE PROPERTY UNDER TEST. At a modern instant the three flags
    #    return one number, so a run confined to such epochs would report "no dependence"
    #    and would look exactly like a run that found none. That is a silent pass in the
    #    direction of reassurance, so it is a refusal instead.
    if not with_property:
        raise SurveyRefusal(
            "offset_attribution: not one epoch surveyed carries the property under test — "
            "the flag changed nothing anywhere, so a verdict read off these rows would be "
            "a statement about the grid and not about the entry point. Refusing to publish "
            "it. ⚠ Include an epoch before the modern record, where the offset is "
            "extrapolated from the tidal constant rather than tabulated."
        )
    if not without_property:
        raise SurveyRefusal(
            "offset_attribution: every epoch surveyed carries the property, so the survey "
            "has no case in which it reports no dependence. Refusing: an instrument that "
            "was never observed saying no has not been shown able to."
        )
    rows.append(
        {
            "finding": "offset_attribution",
            "row": "verdict",
            "entry_points_surveyed": ["deltat_ex", "deltat"],
            "epochs_where_the_flag_changes_the_answer": with_property,
            "epochs_where_it_does_not": without_property,
            "both_lists_are_non_empty_and_the_survey_refuses_otherwise": True,
            "unflagged_entry_point_moved_between_the_two_regimes_seconds": moved,
            "combinations_where_the_constant_identifies_one_source": identifying,
            "combinations_where_it_and_the_position_report_disagree": disagreements,
            "documented_refusal_that_does_not_happen": (
                "⛔ the binding documents that calling deltat_ex before any path has been "
                "set 'will raise'. Measured: it returns a value, computed on the library's "
                "default constant. A recorder relying on that refusal to notice that no "
                "ephemeris was established gets a plausible number instead"
            ),
            "verdict": (
                "⛔ NO EPHEMERIS BASIS CAN BE SUPPLIED HONESTLY FOR EITHER ENTRY POINT, AND "
                "THAT IMPOSSIBILITY IS THIS ROW'S FINDING. Neither returns a report. The "
                "one channel that carries anything — the tidal-acceleration constant in "
                "force — names two different sources with one number and puts a third "
                "number in force that names no source at all. ⭐ What stands in its place "
                "for the flagged entry point is a proxy_window on a reporting call, "
                "recorded as a bound on the window and ⛔ not as this value's source; for "
                "the unflagged one nothing stands in its place, because nothing was asked"
            ),
        }
    )
    return rows


def calendar_ut(jd: float) -> str:
    """A Julian day as a readable UT calendar string. ⚠ Display; `jd_ut_bits` is the value."""
    year, month, day, hour = swe.revjul(jd)
    whole = int(hour)
    minute = int((hour - whole) * 60)
    second = ((hour - whole) * 60 - minute) * 60
    return f"{year:04d}-{month:02d}-{day:02d}T{whole:02d}:{minute:02d}:{second:06.3f}Z"
