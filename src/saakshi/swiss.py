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

⛔ **Two kinds of assertion, and the difference is not cosmetic.**

* ``reported`` — the entry point returns a flag saying which ephemeris answered, and it was
  the one asked for. This is the only direct evidence available.
* ``proxy_window`` — the entry point **does not report**, so the source is asserted from a
  separate call that does, taken at both ends of the interval the non-reporting call may
  read. ⚠ A proxy is weaker than a report and is recorded as such on every row that uses
  one. It is *bounded*, not *sound*: see :func:`assert_window`.

⚠ **Which entry points report is a measured fact, not a documented one** — see
:data:`ENTRY_POINTS`. One of them returns a flag that merely echoes the request.

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


@dataclass(frozen=True)
class EntryPoint:
    """One library entry point, and whether it reports the ephemeris that answered."""

    name: str
    accepts_flag: bool
    reports_source: bool
    returns: str
    evidence: str


#: ⭐ **The audit that makes the rest of R3 possible.** Every row of this table was
#: established by calling the entry point under conditions where the requested ephemeris was
#: known to be unavailable, and reading what came back.
#:
#: ⚠ Two of these take an ephemeris flag and return no source at all, and one returns a
#: source that is not a source — it is the request, handed back. A rule that says only
#: "assert the returned flag" is satisfied by that third one and learns nothing.
ENTRY_POINTS: tuple[EntryPoint, ...] = (
    EntryPoint(
        name="calc_ut",
        accepts_flag=True,
        reports_source=True,
        returns="(values, returned_flag)",
        evidence=(
            "with no data-file path set, a data-file request returned the analytical "
            "source bit; with the path set and an in-coverage date it returned the "
            "data-file bit; with the path set and an out-of-coverage date it returned the "
            "analytical bit again"
        ),
    ),
    EntryPoint(
        name="get_ayanamsa_ex_ut",
        accepts_flag=True,
        reports_source=False,
        returns="(returned_flag, value)",
        evidence=(
            "⛔ the returned flag ECHOES the request. With no data-file path set at all — "
            "where calc_ut reports the analytical source — this entry point still returned "
            "the data-file bit it was handed. A flag that cannot report a substitution is "
            "not evidence of its absence"
        ),
    ),
    EntryPoint(
        name="houses_ex",
        accepts_flag=True,
        reports_source=False,
        returns="(cusps, ascmc)",
        evidence="no flag is returned; the value carries no statement about its source",
    ),
    EntryPoint(
        name="rise_trans",
        accepts_flag=True,
        reports_source=False,
        returns="(return_code, times)",
        evidence=(
            "the integer returned is a success/failure code, not an ephemeris flag: it was "
            "0 both where the requested ephemeris answered and where it was substituted"
        ),
    ),
)

#: The entry points whose own return value is sufficient evidence of source.
REPORTING = frozenset(e.name for e in ENTRY_POINTS if e.reports_source)


def entry_point_records() -> list[dict[str, Any]]:
    """The audit table, as fixture rows."""
    return [
        {
            "finding": "flag_reporting",
            "entry_point": e.name,
            "accepts_ephemeris_flag": e.accepts_flag,
            "reports_answering_ephemeris": e.reports_source,
            "returns": e.returns,
            "evidence": e.evidence,
            "assertion_available": "reported" if e.reports_source else "proxy_window",
        }
        for e in ENTRY_POINTS
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
# Where the data files stop answering — measured, never assumed
# --------------------------------------------------------------------------------------


def coverage_edges(mode: Mode, *, body: int, jd_low: float, jd_high: float) -> dict[str, Any]:
    """Find, by bisection on the returned flag, where the requested ephemeris stops answering.

    ⭐ The returned flag is used here as an *instrument*: the boundary is located by asking
    the library which ephemeris answered, not by reading a published coverage range. A
    different data-file set therefore yields different edges, which is correct — the edge is
    a property of the files supplied, and hard-coding one would be an assumption that
    outlives the file it describes.
    """

    def answered(jd: float) -> bool:
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
    return {
        "body": body,
        "located_by": "bisection on the returned ephemeris flag",
        "lower_edge_last_outside_jd_ut": low_out,
        "lower_edge_first_inside_jd_ut": low_in,
        "upper_edge_first_inside_jd_ut": high_in,
        "upper_edge_last_outside_jd_ut": high_out,
        "lower_edge_calendar_ut": calendar_ut(low_in),
        "upper_edge_calendar_ut": calendar_ut(high_in),
        "search_range_jd_ut": [jd_low, jd_high],
    }


def calendar_ut(jd: float) -> str:
    """A Julian day as a readable UT calendar string. ⚠ Display; `jd_ut_bits` is the value."""
    year, month, day, hour = swe.revjul(jd)
    whole = int(hour)
    minute = int((hour - whole) * 60)
    second = ((hour - whole) * 60 - minute) * 60
    return f"{year:04d}-{month:02d}-{day:02d}T{whole:02d}:{minute:02d}:{second:06.3f}Z"
