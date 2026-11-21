"""R1 — geocentric states in the ICRF under each correction the service's vector interface offers.

The publisher's ephemeris service is asked, from the geocentre, for the state of ten bodies in the ICRF, in TDB,
in astronomical units and days, under each of the three corrections its vector interface offers — in its own
words, *"NONE (geometric states), LT (astrometric light-time corrected states) or LT+S (astrometric states
corrected for stellar aberration)"* — and every value is written down as printed, with its bit pattern, beside
the service state that answered it.

* ⭐ **The request and the service state are R1's, by import.** The address, the query encoding, the retrieval,
  the generation stamp cut out of the digest, and the service-state rules (interface version, the target's and
  the centre's solution) are `src/saakshi/service.py`'s and `src/saakshi/acquisition.py`'s. Nothing is defined
  twice; only this table's three extra columns and the response's own statements are read here.
* ⭐ **The centre and the correction are parameters** of every function that builds a request, never constants
  of the module. The command line defaults them to the geocentre and all three corrections.
* ⛔ **Every response is held to what was asked and to what was last observed**: the interface and its version,
  the solution named for each body and for the centre, the body and centre echoed, the columns, the frame, the
  units, the output type, the time scale, every instant echoed, and the response's own paragraph stating which
  corrections it applied. A difference is a stop, before anything is written.
* ⭐ **Two ways to read, and the record names which.** Live: one request at a time, paced, backing off on a
  failure and never hammering. Or from the copies this generator keeps of the responses it received, through
  an explicit cache-read path, so a second emission needs no request at all. ⛔ A cache read is never an
  acquisition: the values file is byte-identical either way, and the acquisition record says which it was.
* ⛔ **No band and no derived value.** Every section is `reference_only`. Nothing here relates one correction to
  another, differences one against another, or says what any correction is worth.
* ⛔ **Recorder, never explainer.** Nothing here says how the service computes anything.

The instants are chosen by the rule written out in :data:`EPOCH_RULE` and nowhere else; ⛔ there is no
hand-picked list.

Usage:
    python generators/r1_geocentric_vectors.py --profile MANIFEST --kernel de440s.bsp --out DIR
        [--cache DIR] [--from-cache] [--plan-only] [--center 500@399] [--corrections NONE,LT,LT+S]
        [--budget-row ROW]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
import urllib.error
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

HERE = Path(__file__).resolve().parent
# ⛔ Importing a sibling generator must not write its bytecode beside it: an untracked file is a dirty tree.
sys.dont_write_bytecode = True
for _path in (str(HERE.parent / "src"), str(HERE)):
    if _path not in sys.path:
        sys.path.insert(0, _path)

from saakshi import service  # noqa: E402
from saakshi.acquisition import USER_AGENT, AcquisitionError, retrieve  # noqa: E402
from saakshi.fixture import Header, bits, describe_reserved_names, patterned, write_jsonl  # noqa: E402
from saakshi.kernels import oracle_identity, verify  # noqa: E402
from saakshi.provenance import generator_for, host_record, today  # noqa: E402
from saakshi.service import ServiceFormatError  # noqa: E402

# ⭐ The data profile's interval, and the civil rendering of a Julian day, by the readers the other records use.
import nutation_obliquity_modes as modes  # noqa: E402

SCRIPT = "generators/r1_geocentric_vectors.py"
VALUES_PATH = "service/r1-geocentric-vectors.jsonl"
ACQUISITION_PATH = "service/r1-geocentric-vectors-acquisition.jsonl"
CACHE_SUBDIRECTORY = "r1-geocentric-vectors"


class Refusal(Exception):
    """A condition under which nothing may be written."""


# ======================================================================================
# What the service must be, against which every response is a stop or not
# ======================================================================================

EXPECTED_INTERFACE_SOURCE = "NASA/JPL Horizons API"

#: ⚠ **Two interface versions are accepted, each for a stated reason, and no third.** Every response this
#: repository has recorded named the first; the interface's own document names the second. A run takes the
#: version its first response names and refuses any later response naming another, so one file never holds two.
ACCEPTED_INTERFACE_VERSIONS: dict[str, str] = {
    "1.2": "named by every response this repository recorded, 2026-08-04 to 2026-11-12",
    "1.3": "the heading of the interface's own document, 'Version: 1.3 (2025 June)', read 2026-11-21",
}

#: ⛔ The solution the service must name for every target asked here, and for the centre. ⭐ The service's
#: manual: "Horizons uses DE441 for the following objects: All planet barycenters 0,1,2,3,4,5,6,7,8,9 / Sun 10 /
#: Moon 301 / Mercury 199 / Venus 299 / Earth 399". A body centre of Mars to Pluto would be answered from a
#: separate satellite solution, which is why none is asked here.
EXPECTED_SOLUTION = "DE441"

#: The centres this generator can hold a response to: what the response must echo, and the solution it must name.
CENTERS: dict[str, dict[str, str]] = {
    "500@399": {"body": "399", "site": "BODY CENTER", "label": "the geocentre", "solution": EXPECTED_SOLUTION},
}

#: The bodies asked, as sent. ⭐ `point` says which point of the body the number names: the Sun, the Moon, Mercury
#: and Venus by their centres, and Mars to Pluto by their system barycentres — the point the service's planetary
#: solution carries, and the one a short-span planetary kernel carries too.
TARGETS: tuple[dict[str, str], ...] = (
    {"command": "10", "label": "Sun", "point": "body_centre"},
    {"command": "301", "label": "Moon", "point": "body_centre"},
    {"command": "199", "label": "Mercury", "point": "body_centre"},
    {"command": "299", "label": "Venus", "point": "body_centre"},
    {"command": "4", "label": "Mars system barycentre", "point": "system_barycentre"},
    {"command": "5", "label": "Jupiter system barycentre", "point": "system_barycentre"},
    {"command": "6", "label": "Saturn system barycentre", "point": "system_barycentre"},
    {"command": "7", "label": "Uranus system barycentre", "point": "system_barycentre"},
    {"command": "8", "label": "Neptune system barycentre", "point": "system_barycentre"},
    {"command": "9", "label": "Pluto system barycentre", "point": "system_barycentre"},
)

#: The three corrections, as sent, with the words the interface's document gives each. ⛔ Quoted, not explained.
CORRECTIONS: dict[str, str] = {
    "NONE": "geometric states",
    "LT": "astrometric light-time corrected states",
    "LT+S": "astrometric states corrected for stellar aberration",
}
CORRECTION_SLUGS: dict[str, str] = {"NONE": "none", "LT": "lt", "LT+S": "lt_s"}

#: The query every request shares. ⭐ Written out in full, every parameter that selects the reading stated
#: explicitly rather than left to a default: the frame, the reference system and the time scale above all.
COMMON_QUERY: dict[str, str] = {
    "format": "json",
    "EPHEM_TYPE": "'VECTORS'",
    "REF_PLANE": "'FRAME'",
    "REF_SYSTEM": "'ICRF'",
    "TIME_TYPE": "'TDB'",
    "TLIST_TYPE": "'JD'",
    "OUT_UNITS": "'AU-D'",
    "VEC_TABLE": "'3'",
    "VEC_LABELS": "'NO'",
    "VEC_DELTA_T": "'NO'",
    "CSV_FORMAT": "'YES'",
    "OBJ_DATA": "'NO'",
    "MAKE_EPHEM": "'YES'",
    "TIME_DIGITS": "'FRACSEC'",
}

#: ⛔ The table's columns, asserted: a positional reader that never checks its columns reads a re-ordered table
#: confidently and attributes the result to the ephemeris.
EXPECTED_COLUMNS: tuple[str, ...] = ("JDTDB", "Calendar Date (TDB)", "X", "Y", "Z", "VX", "VY", "VZ", "LT", "RG",
                                     "RR")
COMPONENTS: tuple[str, ...] = EXPECTED_COLUMNS[2:]
#: The unit of each component under `OUT_UNITS 'AU-D'`, as the response's own symbol list states it.
COMPONENT_UNITS: tuple[str, ...] = ("au", "au", "au", "au/day", "au/day", "au/day", "day", "au", "au/day")

#: ⛔ What every response must state about its own output, whatever the correction.
EXPECTED_STATED: dict[str, str] = {
    "reference_frame": "ICRF",
    "output_units": "AU-D",
    "output_format": "3 (position, velocity, LT, range, range-rate)",
    "au_in_km": "149597870.700",
    "seconds_per_day": "86400.0",
}
#: ⛔ The sentence the response's time section must carry: the time scale that was asked for.
EXPECTED_TIME_STATEMENT = 'Barycentric Dynamical Time ("TDB" or T_eph) output was requested.'

#: ⛔ Per correction: the output type the response must state, and its own paragraph under ABERRATIONS AND
#: CORRECTIONS, character for character (trailing spaces cut). ⭐ Pinned from the first responses read on
#: 2026-11-21, after each was held against the interface's document; a later response stating anything else
#: is a stop.
EXPECTED_CORRECTION_STATEMENTS: dict[str, dict[str, str]] = {
    "NONE": {
        "output_type": "GEOMETRIC cartesian states",
        "paragraph": "Geometric state vectors have NO corrections or aberrations applied.",
    },
    "LT": {
        "output_type": "LT CORRECTED cartesian states",
        "paragraph": "States have been corrected for Newtonian down-leg (receive) light-time\n displacement.",
    },
    "LT+S": {
        "output_type": "LT+S CORRECTED cartesian states",
        # ⚠ The two spaces after "down-leg" are the service's own, kept.
        "paragraph": ("States have been corrected for Newtonian down-leg  (receive) light-time\n displacement and "
                      "relativistic stellar aberration."),
    },
}

# ======================================================================================
# The epoch rule
# ======================================================================================

#: Every instant is a Julian day in TDB whose fraction is a multiple of a sixteenth of a day, so its decimal is
#: exact in binary and the service's nine-decimal echo of it can be held to the bit.
END_MARGIN_DAYS = 1.0
SPARSE_ORIGIN = "1850-01-01T00:00:00"
SPARSE_STEP_DAYS = 1000
DENSE_START = "1900-01-01T00:00:00"
DENSE_END = "2050-01-01T00:00:00"
DENSE_STEP_DAYS = 200
#: The goldens the consumer's accuracy specification names with a year or a date and no fixed instant.
#: ⭐ Sampled by rule because no instant is fixed; ⛔ the two named with neither (the LMT-era chart and the
#: published station) are not sampled at all, because an instant would have to be invented.
GOLDEN_INSTANTS: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    ("golden_1855", "the 1855 kernel-edge historical golden: the first instant of its year",
     ("1855-01-01T00:00:00",)),
    ("golden_2145", "the 2145 transit-sweep golden: the first instant of each quarter of its year",
     ("2145-01-01T00:00:00", "2145-04-01T00:00:00", "2145-07-01T00:00:00", "2145-10-01T00:00:00")),
    ("golden_1995_10_24", "the 1995-10-24 eclipse-day golden: every sixteenth of a day from 00:00 to 12:00 TDB",
     tuple(f"1995-10-24T{(minutes // 60):02d}:{(minutes % 60):02d}:00" for minutes in range(0, 12 * 60 + 1, 90))),
)
#: The years each search for a conjunction or a station starts at, 0 h TDB on 1 January.
EVENT_ANCHORS: tuple[str, ...] = ("1900-01-01T00:00:00", "1950-01-01T00:00:00", "2000-01-01T00:00:00",
                                  "2050-01-01T00:00:00")
#: How many conjunctions with the Sun are taken after each anchor, per body.
CONJUNCTIONS_PER_ANCHOR: dict[str, int] = {"301": 2, "199": 2, "299": 2, "4": 1, "5": 1, "6": 1, "7": 1, "8": 1,
                                           "9": 1}
#: How many stations are taken after each anchor, per body: one of each sense.
STATIONS_PER_ANCHOR: dict[str, int] = {"199": 2, "299": 2, "4": 2, "5": 2, "6": 2, "7": 2, "8": 2, "9": 2}
SCAN_DAYS = 1200

EPOCH_RULE = (
    "⭐ The instants, all in TDB, each a whole Julian day at 0 h unless stated, the union of: "
    "(1) the profile's interval ends, each one day inside; "
    f"(2) a sparse lattice from {SPARSE_ORIGIN} every {SPARSE_STEP_DAYS} days to the interval's end; "
    f"(3) a dense lattice from {DENSE_START} every {DENSE_STEP_DAYS} days to {DENSE_END}; "
    "(4) the goldens named with a year or a date and no fixed instant, each as stated; "
    "(5) per body, after each anchor year's first instant, the first lattice days on which the angle between the "
    "body's and the Sun's geometric geocentric directions is a local minimum (a conjunction with the Sun); "
    "(6) per planet, after each anchor, the first lattice days after which the sign of its geometric geocentric "
    "ecliptic-J2000 longitude rate changes (a station). "
    "⚠ (5) and (6) are SELECTED by reading the pinned short-span planetary kernel with CSPICE on a one-day lattice; "
    "nothing that search computes is written anywhere — it chooses where to ask, and every value recorded is the "
    "service's. Every instant is asked of every body under every correction."
)


@dataclass
class Epoch:
    """One instant asked, and every reason it was chosen."""

    jd_tdb: float
    reasons: list[str]

    def as_json(self) -> dict:
        return {**patterned("jd_tdb", self.jd_tdb), "civil_tdb": modes.civil(self.jd_tdb), "reasons": self.reasons}


def _exact(jd: float, *, what: str) -> float:
    """⛔ An instant whose fraction is not a sixteenth of a day cannot be held to the service's echo."""
    if (jd * 16.0) != int(jd * 16.0) or modes.julian_day(modes.civil(jd)) != jd:
        raise Refusal(f"{what}: JD {jd!r} is not an exact sixteenth of a day that converts back")
    return jd


def lattice_epochs(interval: dict) -> list[tuple[float, str]]:
    """Rules (1) to (4): the interval ends, the two lattices and the goldens."""
    start, end = interval["start"], interval["end"]
    out = [(start + END_MARGIN_DAYS, "interval_start_plus_one_day"), (end - END_MARGIN_DAYS, "interval_end_minus_one_day")]
    jd = modes.julian_day(SPARSE_ORIGIN)
    while jd <= end - END_MARGIN_DAYS:
        out.append((jd, "sparse_lattice"))
        jd += SPARSE_STEP_DAYS
    jd, dense_end = modes.julian_day(DENSE_START), modes.julian_day(DENSE_END)
    while jd <= dense_end:
        out.append((jd, "dense_lattice"))
        jd += DENSE_STEP_DAYS
    for name, _why, stamps in GOLDEN_INSTANTS:
        out += [(modes.julian_day(stamp), name) for stamp in stamps]
    for jd, reason in out:
        _exact(jd, what=reason)
        if not start < jd < end:
            raise Refusal(f"{reason}: JD {jd!r} is not inside the profile's interval")
    return out


def event_epochs(kernel: Path, interval: dict) -> list[tuple[float, str]]:
    """Rules (5) and (6), on the pinned kernel. ⚠ Imported here: the binding is not part of the contract's own
    environment. ⛔ Only the chosen lattice days leave this function."""
    import spiceypy as sp  # noqa: PLC0415

    def state(body: int, jd: float, frame: str) -> list[float]:
        value, _light_time = sp.spkgeo(body, (jd - 2451545.0) * 86400.0, frame, 399)
        return [float(v) for v in value]

    sp.furnsh(str(kernel))
    try:
        out: list[tuple[float, str]] = []
        for anchor in EVENT_ANCHORS:
            first, year = modes.julian_day(anchor), anchor[:4]
            days = [first + d for d in range(SCAN_DAYS + 2)]
            for command, wanted in CONJUNCTIONS_PER_ANCHOR.items():
                angle = [sp.vsep(state(int(command), jd, "J2000")[:3], state(10, jd, "J2000")[:3]) for jd in days]
                found = [days[i] for i in range(1, len(days) - 1) if angle[i] < angle[i - 1] and angle[i] <= angle[i + 1]]
                if len(found) < wanted:
                    raise Refusal(f"body {command}: {len(found)} conjunctions in {SCAN_DAYS} days from {anchor}")
                out += [(jd, f"conjunction_{command}_{year}_{n + 1}") for n, jd in enumerate(found[:wanted])]
            for command, wanted in STATIONS_PER_ANCHOR.items():
                sign = []
                for jd in days:
                    x, y, _z, vx, vy, _vz = state(int(command), jd, "ECLIPJ2000")
                    sign.append(x * vy - y * vx > 0.0)
                found = [days[i] for i in range(len(days) - 1) if sign[i] != sign[i + 1]]
                if len(found) < wanted:
                    raise Refusal(f"body {command}: {len(found)} stations in {SCAN_DAYS} days from {anchor}")
                out += [(jd, f"station_{command}_{year}_{n + 1}") for n, jd in enumerate(found[:wanted])]
    finally:
        sp.kclear()
    for jd, reason in out:
        _exact(jd, what=reason)
        if not interval["start"] < jd < interval["end"]:
            raise Refusal(f"{reason}: JD {jd!r} is not inside the profile's interval")
    return out


def epochs(chosen: list[tuple[float, str]]) -> list[Epoch]:
    """One instant per distinct Julian day, in time order, every reason kept."""
    by_jd: dict[float, Epoch] = {}
    for jd, reason in chosen:
        by_jd.setdefault(jd, Epoch(jd_tdb=jd, reasons=[])).reasons.append(reason)
    return [by_jd[jd] for jd in sorted(by_jd)]


def epoch_set_digest(instants: list[Epoch]) -> str:
    """The digest of the instants as bit patterns: what the cache is keyed on, besides target, centre and
    correction."""
    return hashlib.sha256(",".join(bits(e.jd_tdb) for e in instants).encode("ascii")).hexdigest()


# ======================================================================================
# The plan: every request, in the order it is sent
# ======================================================================================

#: The most instants in one request. ⚠ The interface allows ten thousand, "though URL length limits may impose
#: smaller limits"; this keeps every address a few kilobytes long.
CHUNK_SIZE = 200
#: ⚠ The pause between requests, in seconds. One request at a time, never two at once.
REQUEST_INTERVAL_SECONDS = 2.0
#: ⚠ After a failed request: wait this long, then try once more; after the last, stop. Never more.
BACKOFF_SECONDS: tuple[float, ...] = (30.0, 120.0)
#: For the estimate put before the first live request: a response's typical time, measured on 2026-11-09.
TYPICAL_RESPONSE_SECONDS = 2.0


def tlist(jds: list[float]) -> str:
    """The time list as R1 sends one: the instants' shortest decimals, comma-separated, in one quoted value."""
    return "'" + ",".join(repr(jd) for jd in jds) + "'"


def chunks(instants: list[Epoch]) -> list[list[Epoch]]:
    return [instants[i:i + CHUNK_SIZE] for i in range(0, len(instants), CHUNK_SIZE)]


def query_for(*, command: str, center: str, correction: str, instants: list[Epoch]) -> dict[str, str]:
    """One request. ⭐ The centre and the correction are its arguments."""
    if center not in CENTERS:
        raise Refusal(f"centre {center!r}: no expectation is recorded for it here")
    if correction not in CORRECTIONS:
        raise Refusal(f"correction {correction!r} is not one the interface's document names")
    return {**COMMON_QUERY, "CENTER": f"'{center}'", "VEC_CORR": f"'{correction}'", "COMMAND": f"'{command}'",
            "TLIST": tlist([e.jd_tdb for e in instants])}


def cache_stem(cache: Path, *, center: str, correction: str, digest: str, command: str, index: int) -> Path:
    """⭐ Keyed on the target, the centre, the correction and the instant set, in a subdirectory of its own, so no
    copy of an earlier query — the barycentric R1 responses above all — can stand in for one of these."""
    safe = lambda text: re.sub(r"[^A-Za-z0-9]+", "_", text)  # noqa: E731
    return (cache / CACHE_SUBDIRECTORY / f"center_{safe(center)}" / f"corr_{CORRECTION_SLUGS[correction]}"
            / f"epochs_{digest[:16]}" / f"{command}-c{index:02d}")


def plan(instants: list[Epoch], *, center: str, corrections: list[str]) -> list[dict]:
    pieces = chunks(instants)
    requests = []
    for correction in corrections:
        for target in TARGETS:
            for index, piece in enumerate(pieces):
                requests.append({
                    "request_id": f"{CORRECTION_SLUGS[correction]}-{target['command']}-c{index:02d}",
                    "correction": correction,
                    "target": target,
                    "chunk": index,
                    "instants": piece,
                    "query": query_for(command=target["command"], center=center, correction=correction,
                                       instants=piece),
                })
    return requests


def estimate(requests: list[dict]) -> dict:
    seconds = len(requests) * (REQUEST_INTERVAL_SECONDS + TYPICAL_RESPONSE_SECONDS)
    return {"requests": len(requests), "estimated_wall_seconds": seconds,
            "longest_address_characters": max(len(service.build_url(r["query"])) for r in requests)}


# ======================================================================================
# A response, split by R1's rules, and this table read
# ======================================================================================

_ECHO_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("target_echo", re.compile(r"^Target body name: .*?\((-?\d+)\)", re.M)),
    ("center_echo", re.compile(r"^Center body name: .*?\((-?\d+)\)", re.M)),
    ("center_site", re.compile(r"^Center-site name: *(.+?) *$", re.M)),
    ("output_format", re.compile(r"^Output format *: *(.+?) *$", re.M)),
)


def _section(text: str, heading: str, end: str, *, where: str) -> str:
    """The text under one heading of the response's own notes, trailing spaces cut. ⛔ Exactly one of each."""
    if text.count(f"\n{heading}\n") != 1 or text.count(end) != 1:
        raise ServiceFormatError(f"{where}: the section {heading!r} is not exactly one")
    body = text.split(f"\n{heading}\n", 1)[1].split(end, 1)[0]
    return "\n".join(line.rstrip() for line in body.strip("\n").splitlines()).strip()


@dataclass(frozen=True)
class Response:
    service_state: dict[str, str]
    envelope_excluded: tuple[str, ...]
    stated: dict[str, str]
    echo: dict[str, str]
    time_statement: str
    correction_paragraph: str
    resource_text: str
    columns: tuple[str, ...]
    data_rows: tuple[tuple[str, ...], ...]


def split(payload: bytes, *, query: dict[str, str]) -> Response:
    """R1's split of a response, over this table: the interface named, the stamp cut, the service state recorded.

    ⭐ Every rule of the split is `service.py`'s: its signature keys, its envelope and service-state patterns and
    their `required` flags, its one-match location, its marker, and the constants it reads the response for. What
    is added is this table's columns, the body and centre echoed, the output format, and the two paragraphs.
    """
    where = query.get("COMMAND", "<no command>") + " " + query.get("VEC_CORR", "")
    try:
        document = json.loads(payload)
    except ValueError as exc:
        raise ServiceFormatError(f"{where}: the response is not JSON ({exc})") from exc
    if "result" not in document:
        raise ServiceFormatError(f"{where}: the response carries no 'result': {document!r}"[:600])
    text = str(document["result"])
    signature = document.get("signature") or {}
    state = {f"interface_{key}": str(signature[key]) for key in service._SIGNATURE_KEYS if key in signature}
    if len(state) != len(service._SIGNATURE_KEYS):
        raise ServiceFormatError(f"{where}: the response envelope names no interface version")
    cuts: list[tuple[int, int, str]] = []
    excluded: list[str] = []
    for name, pattern in service._ENVELOPE_PATTERNS:
        span = service._locate(text, name, pattern, required=True, where=where)
        assert span is not None
        cuts.append((*span, name))
        excluded.append(name)
    for name, pattern, required in service._SERVICE_STATE_PATTERNS:
        span = service._locate(text, name, pattern, required=required, where=where)
        if span is None:
            continue
        cuts.append((*span, name))
        state[name] = text[span[0]:span[1]]
    stated: dict[str, str] = {}
    for name, pattern, required in service._STATED_PATTERNS:
        span = service._locate(text, name, pattern, required=required, where=where)
        if span is not None:
            stated[name] = text[span[0]:span[1]]
    echo: dict[str, str] = {}
    for name, pattern in _ECHO_PATTERNS:
        span = service._locate(text, name, pattern, required=True, where=where)
        assert span is not None
        echo[name] = text[span[0]:span[1]]
    stated["output_format"] = echo.pop("output_format")
    resource = text
    for start, end, name in sorted(cuts, reverse=True):
        resource = resource[:start] + service._EXCLUDED.format(name=name) + resource[end:]

    headers = list(re.finditer(r"^ *JDTDB,.*$", text, re.M))
    if len(headers) != 1:
        raise ServiceFormatError(f"{where}: the column header matched {len(headers)} times and must match once")
    columns = tuple(part.strip() for part in headers[0].group(0).split(",") if part.strip())
    if text.count("$$SOE") != 1 or text.count("$$EOE") != 1:
        raise ServiceFormatError(f"{where}: the data block delimiters are not a single pair")
    rows = []
    for line in text.split("$$SOE", 1)[1].split("$$EOE", 1)[0].splitlines():
        if not line.strip():
            continue
        fields = [part.strip() for part in line.split(",")]
        while fields and not fields[-1]:
            fields.pop()
        if len(fields) != len(columns):
            raise ServiceFormatError(f"{where}: a data line has {len(fields)} fields, not {len(columns)}: {line!r}")
        rows.append(tuple(fields))
    return Response(
        service_state=state, envelope_excluded=tuple(excluded), stated=stated, echo=echo,
        time_statement=_section(text, "TIME", "\nCALENDAR SYSTEM\n", where=where),
        correction_paragraph=_section(text, "ABERRATIONS AND CORRECTIONS", "\nComputations by", where=where),
        resource_text=resource, columns=columns, data_rows=tuple(rows),
    )


def canonical(query: dict[str, str]) -> Callable[[bytes], bytes]:
    """The canonical form `retrieve()` digests: the resource of :func:`split`."""
    return lambda payload: split(payload, query=query).resource_text.encode("utf-8")


def hold(response: Response, request: dict, *, center: str, version: str | None) -> str:
    """⛔ Every check a response is held to. Returns the interface version it named."""
    where = request["request_id"]
    state, correction, command = response.service_state, request["correction"], request["target"]["command"]
    if state.get("interface_source") != EXPECTED_INTERFACE_SOURCE:
        raise Refusal(f"⛔ STOP: {where}: interface {state.get('interface_source')!r}")
    named = state.get("interface_version")
    if named not in ACCEPTED_INTERFACE_VERSIONS:
        raise Refusal(f"⛔ STOP: {where}: interface version {named!r} is neither the document's nor the last "
                      "observed; ask before reading on")
    if version is not None and named != version:
        raise Refusal(f"⛔ STOP: {where}: interface version {named!r} after {version!r} earlier in this run")
    expected_center = CENTERS[center]
    for key, wanted in (("target_solution", EXPECTED_SOLUTION), ("center_solution", expected_center["solution"])):
        if state.get(key) != wanted:
            raise Refusal(f"⛔ STOP: {where}: {key} is {state.get(key)!r}, not {wanted!r}")
    for key, wanted in (("target_echo", command), ("center_echo", expected_center["body"]),
                        ("center_site", expected_center["site"])):
        if response.echo[key] != wanted:
            raise Refusal(f"⛔ STOP: {where}: {key} is {response.echo[key]!r}, not {wanted!r}")
    for key, wanted in EXPECTED_STATED.items():
        if response.stated.get(key) != wanted:
            raise Refusal(f"⛔ STOP: {where}: the response states {key} {response.stated.get(key)!r}, not {wanted!r}")
    statement = EXPECTED_CORRECTION_STATEMENTS.get(correction)
    if statement is None:
        raise Refusal(f"⛔ STOP: {where}: no statement is pinned for {correction}; read one and hold it against the "
                      "interface's document first")
    if response.stated.get("output_type") != statement["output_type"]:
        raise Refusal(f"⛔ STOP: {where}: output type {response.stated.get('output_type')!r}, not "
                      f"{statement['output_type']!r}")
    if response.correction_paragraph != statement["paragraph"]:
        raise Refusal(f"⛔ STOP: {where}: the response's statement of its corrections differs from the one pinned: "
                      f"{response.correction_paragraph!r}")
    if EXPECTED_TIME_STATEMENT not in response.time_statement:
        raise Refusal(f"⛔ STOP: {where}: the response does not state that TDB was requested")
    if response.columns != EXPECTED_COLUMNS:
        raise Refusal(f"⛔ STOP: {where}: columns {response.columns} are not {EXPECTED_COLUMNS}")
    if len(response.data_rows) != len(request["instants"]):
        raise Refusal(f"⛔ STOP: {where}: {len(response.data_rows)} lines for {len(request['instants'])} instants")
    for fields, instant in zip(response.data_rows, request["instants"]):
        if float(fields[0]) != instant.jd_tdb:
            raise Refusal(f"⛔ STOP: {where}: answered for JD {fields[0]} where {instant.jd_tdb!r} was asked")
    return named


# ======================================================================================
# Reading: live, or from the copies kept
# ======================================================================================


@dataclass(frozen=True)
class Read:
    """One response and how it was obtained. ⭐ Everything here is the same whichever way it was read, except
    `kind`."""

    url: str
    payload: bytes
    resource_sha256: str
    resource_bytes: int
    acquired_on: str
    kind: str


RETRIEVAL_KINDS: dict[str, str] = {
    "live_request": "every response was requested from the service by this run, one at a time",
    "cache_read": (
        "⛔ NOT AN ACQUISITION. Every response was read from the copy kept when it was requested, after its "
        "address, its resource and its digest were checked against the record kept beside it; no request was sent"
    ),
}


def _transient(exc: AcquisitionError) -> bool:
    """A failure worth one more try after a pause: the network, a 5xx, or a 429. ⛔ Never a refusal."""
    cause = exc.__cause__
    if isinstance(cause, urllib.error.HTTPError):
        return cause.code >= 500 or cause.code == 429
    return isinstance(cause, (urllib.error.URLError, OSError))


def read_live(request: dict, stem: Path, *, sleep: Callable[[float], None] | None = None,
              fetch: Callable[..., object] | None = None) -> Read:
    """One live request through R1's retrieval, backing off on a transient failure, then the copy kept."""
    sleep, fetch = sleep or time.sleep, fetch or retrieve
    url = service.build_url(request["query"])
    for attempt, pause in enumerate((*BACKOFF_SECONDS, None)):
        try:
            retrieval = fetch(url, cache=stem.with_suffix(".txt"), canonical=canonical(request["query"]))
            break
        except AcquisitionError as exc:
            if pause is None or not _transient(exc):
                raise
            print(f"  ⚠ {request['request_id']}: attempt {attempt + 1} failed ({exc.__cause__}); "
                  f"backing off {pause:.0f} s")
            sleep(pause)
    acquired_on = today()
    stem.with_suffix(".payload").write_bytes(retrieval.payload)
    stem.with_suffix(".acquired.json").write_text(json.dumps({
        "url": url, "resource_sha256": retrieval.resource_sha256, "acquired_on": acquired_on,
        "user_agent": USER_AGENT}, sort_keys=True) + "\n", encoding="utf-8")
    return Read(url=url, payload=retrieval.payload, resource_sha256=retrieval.resource_sha256,
                resource_bytes=len(retrieval.resource), acquired_on=acquired_on, kind="live_request")


def read_cached(request: dict, stem: Path) -> Read:
    """⭐ THE CACHE-READ PATH. The response kept when it was requested, checked three ways before it is read: the
    address recorded beside it is this request's, the resource it renders is the copy kept, and both digest to
    the value recorded. ⛔ A missing or disagreeing copy refuses; nothing is fetched in its place."""
    url = service.build_url(request["query"])
    where = request["request_id"]
    files = {suffix: stem.with_suffix(suffix) for suffix in (".txt", ".payload", ".acquired.json")}
    missing = [str(path.name) for path in files.values() if not path.is_file()]
    if missing:
        raise Refusal(f"{where}: no kept copy to read ({missing}). ⛔ A cache read never falls back to a request")
    record = json.loads(files[".acquired.json"].read_text(encoding="utf-8"))
    if record["url"] != url:
        raise Refusal(f"{where}: the kept copy was requested at another address")
    payload = files[".payload"].read_bytes()
    resource = canonical(request["query"])(payload)
    digest = hashlib.sha256(resource).hexdigest()
    if resource != files[".txt"].read_bytes() or digest != record["resource_sha256"]:
        raise Refusal(f"{where}: the kept response, its kept resource and its recorded digest do not agree")
    return Read(url=url, payload=payload, resource_sha256=digest, resource_bytes=len(resource),
                acquired_on=record["acquired_on"], kind="cache_read")


def read(requests: list[dict], *, cache: Path, center: str, digest: str, from_cache: bool,
         sleep: Callable[[float], None] | None = None, fetch: Callable[..., object] | None = None
         ) -> tuple[list[tuple[dict, Read, Response]], str]:
    """Every request, in order, one at a time. Returns each with its read and its split, and the interface version.
    ⛔ Every response is held before the next request is sent, so a stop sends nothing further."""
    sleep = sleep or time.sleep
    out = []
    version: str | None = None
    for index, request in enumerate(requests):
        stem = cache_stem(cache, center=center, correction=request["correction"], digest=digest,
                          command=request["target"]["command"], index=request["chunk"])
        if from_cache:
            got = read_cached(request, stem)
        else:
            if index:
                sleep(REQUEST_INTERVAL_SECONDS)
            stem.parent.mkdir(parents=True, exist_ok=True)
            got = read_live(request, stem, sleep=sleep, fetch=fetch)
        response = split(got.payload, query=request["query"])
        version = hold(response, request, center=center, version=version)
        out.append((request, got, response))
        print(f"  {request['request_id']}: {len(response.data_rows)} instants, "
              f"{response.service_state['target_solution']}/{response.service_state['center_solution']}, "
              f"interface {version}, resource {got.resource_sha256[:12]}... ({got.kind})")
    return out, version


# ======================================================================================
# The records
# ======================================================================================


def rows_for(answered: list[tuple[dict, Read, Response]], *, center: str) -> list[dict]:
    rows = []
    for request, _got, response in answered:
        state = response.service_state
        for fields, instant in zip(response.data_rows, request["instants"]):
            printed = list(fields[2:])
            rows.append({
                "section": f"state_{CORRECTION_SLUGS[request['correction']]}",
                "request_id": request["request_id"],
                "target_command": request["target"]["command"],
                "target_point": request["target"]["point"],
                "vec_corr": request["correction"],
                "center_command": center,
                "target_solution": state["target_solution"],
                "center_solution": state["center_solution"],
                "interface_version": state["interface_version"],
                # ⭐ Recorded where the response names one, as every row of R1's of-date probe records it.
                "earth_orientation_file": state.get("earth_orientation_file"),
                **patterned("jd_tdb", instant.jd_tdb),
                "calendar_date": fields[1],
                **patterned("value", [float(text) for text in printed]),
                "value_printed": printed,
            })
    return rows


#: The published pages read on 2026-11-21 and quoted here. ⛔ Quoted, never interpreted; no legal conclusion is
#: drawn from any of them.
DOCUMENTS: tuple[dict, ...] = (
    {"document": "horizons_manual", "url": "https://ssd.jpl.nasa.gov/horizons/manual.html",
     "retrieved": "2026-11-21",
     "sha256": "be45b0137b37068c48760bbaf306f52a72c10239c175ba91119a30eb30612a81"},
    {"document": "horizons_api", "url": "https://ssd-api.jpl.nasa.gov/doc/horizons.html",
     "retrieved": "2026-11-21",
     "sha256": "6ca45d9c222d6e5c425ae3e0a3c44225cf8b6d30c4a14892b0f1157b0ab4cfe4"},
    {"document": "ssd_api_fair_use_policy", "url": "https://ssd-api.jpl.nasa.gov/",
     "retrieved": "2026-11-21",
     "sha256": "a91502a7cfc7624b1b20a81777db7f376862eed9d556d6f9565f394420f4896d"},
    {"document": "ssd_faq", "url": "https://ssd.jpl.nasa.gov/faq.html", "retrieved": "2026-11-21",
     "sha256": "2480fefc0c49df0706a772822ae3497461fc0f89da72e0aa99d4b4113ef5da66"},
)

STATED_TERMS: tuple[dict, ...] = (
    {"document": "horizons_api",
     "words": "VEC_CORR: NONE (geometric states), LT (astrometric light-time corrected states) or LT+S "
              "(astrometric states corrected for stellar aberration)"},
    {"document": "horizons_api",
     "words": "TIME_TYPE: override default to specify input & output timescale. observer tables: UT or TT; vector "
              "tables: TDB or UT; element tables: TDB only"},
    {"document": "horizons_manual",
     "words": "Apparent Coordinates: Positions or values (like RA and DEC) which take into account factors that "
              "appear to change the target position with respect to the background coordinate system: light-time, "
              "the deflection of light due to large or nearby masses, and stellar aberration."},
    {"document": "horizons_manual",
     "words": "Horizons uses DE441 for the following objects: All planet barycenters 0,1,2,3,4,5,6,7,8,9 / Sun 10 / "
              "Moon 301 / Mercury 199 / Venus 299 / Earth 399"},
    {"document": "ssd_api_fair_use_policy",
     "words": "You agree to submit only one API request at a time (no simultaneous requests)."},
    {"document": "ssd_api_fair_use_policy",
     "words": "Applications making automated connections must provide a valid, application-specific User-Agent "
              "request header that includes correct product name, version, and contact information."},
    {"document": "ssd_faq",
     "words": "No permissions are needed. The data provided on this site are considered public domain. However, "
              "use of information from this site does not imply NASA/Caltech/JPL endorsement."},
)


def build_values_header(answered, *, version: str, instants: list[Epoch], interval: dict, kernel_identity: dict,
                        center: str, corrections: list[str], generator, budget_row: str) -> Header:
    sections = [f"state_{CORRECTION_SLUGS[c]}" for c in corrections]
    first_by_correction = {}
    for request, _got, response in answered:
        first_by_correction.setdefault(request["correction"], response)
    acquired = sorted({got.acquired_on for _r, got, _s in answered})
    return Header(
        fixture_kind="numeric_pin",
        reference="R1",
        generator=generator,
        generated=today(),
        title="Geocentric states in the ICRF under each correction the service's vector interface offers",
        oracle={
            "publisher": "JPL Solar System Dynamics",
            "service": "Horizons",
            "endpoint": service.ENDPOINT,
            "user_agent": USER_AGENT,
            "interface": {"source": EXPECTED_INTERFACE_SOURCE, "version": version,
                          "accepted": [{"version": v, "why": w} for v, w in ACCEPTED_INTERFACE_VERSIONS.items()]},
            "acquired_on": acquired,
            "solutions_that_answered": sorted({s.service_state["target_solution"] for _r, _g, s in answered}),
            "center_solutions": sorted({s.service_state["center_solution"] for _r, _g, s in answered}),
            "earth_orientation_named": [json.loads(text) for text in sorted({json.dumps(
                {k: s.service_state.get(k) for k in ("earth_orientation_file", "earth_orientation_coverage")},
                sort_keys=True) for _r, _g, s in answered})],
            "stated_by_the_service": {
                **{k: v for k, v in first_by_correction[corrections[0]].stated.items() if k != "output_type"},
                "role": "what the service stated about its own output, held equal on every response",
            },
            "the_service_on_each_correction": [
                {"vec_corr": c, "documented_as": CORRECTIONS[c],
                 "output_type": first_by_correction[c].stated["output_type"],
                 "aberrations_and_corrections": first_by_correction[c].correction_paragraph}
                for c in corrections
            ],
            "time_scale_statement": first_by_correction[corrections[0]].time_statement,
        },
        request={
            "endpoint": service.ENDPOINT,
            "user_agent": USER_AGENT,
            "common_query": [{"parameter": k, "value": v} for k, v in sorted(COMMON_QUERY.items())],
            "center": {"command": center, **CENTERS[center]},
            "corrections": [{"vec_corr": c, "documented_as": CORRECTIONS[c]} for c in corrections],
            "targets": [dict(t) for t in TARGETS],
            "instants": {
                "rule": EPOCH_RULE,
                "profile": {k: interval[k] for k in ("profile", "manifest_sha256", "dataset", "declared_coverage")},
                "selected_with": kernel_identity,
                "count": len(instants),
                "set_sha256": epoch_set_digest(instants),
                "chunk_size": CHUNK_SIZE,
                "values": [e.as_json() for e in instants],
            },
            "queries": [{"request_id": r["request_id"], "vec_corr": r["correction"],
                         "target_command": r["target"]["command"], "chunk": r["chunk"],
                         "query": [{"parameter": k, "value": v} for k, v in sorted(r["query"].items())],
                         "resource_sha256": got.resource_sha256}
                        for r, got, _s in answered],
            "one_at_a_time": True,
            "request_interval_seconds": REQUEST_INTERVAL_SECONDS,
            "backoff_seconds": list(BACKOFF_SECONDS),
            "regenerate": f"{SCRIPT} --profile <manifest> --kernel <de440s.bsp> --out <dir> -- needs the network, "
                          "or --from-cache to read the copies a live run kept; a cache read is not an acquisition",
        },
        classification={section: {"class": "reference_only"} for section in sections},
        budget_row=budget_row,
        row_schema={
            "section": "state_none | state_lt | state_lt_s: the correction the row was answered under",
            "request_id": "the request that answered it, as listed in `request.queries`",
            "target_command": "the body identifier sent, verbatim",
            "target_point": "body_centre | system_barycentre: which point of the body the state names",
            "vec_corr": "the correction sent, verbatim",
            "center_command": "the centre sent, verbatim",
            "target_solution": "⭐ the solution the service named for this body, on this row",
            "center_solution": "the solution named for the centre, likewise",
            "interface_version": "the interface version the response named",
            "earth_orientation_file": "the Earth-orientation file the response named, or null where it named none",
            "jd_tdb": "the instant asked, Julian day, TDB — held to the service's echo, bit for bit",
            "calendar_date": "the service's own rendering of the same instant. ⚠ A label; `jd_tdb` is the authority",
            "value": "THE PIN — the nine printed values, in `component_order`, each in its `component_units` entry",
            "value_bits": "the same nine values as IEEE-754 bit patterns",
            "value_printed": "the same nine values as the service printed them",
            "component_order": list(COMPONENTS),
            "component_units": list(COMPONENT_UNITS),
        },
        summary={
            "rows": sum(len(s.data_rows) for _r, _g, s in answered),
            "rows_by_section": {s: sum(len(x.data_rows) for r, _g, x in answered
                                       if f"state_{CORRECTION_SLUGS[r['correction']]}" == s) for s in sections},
            "requests": len(answered),
            "targets": len(TARGETS),
            "instants": len(instants),
            "documents": [dict(d) for d in DOCUMENTS],
            "stated_terms": [dict(t) for t in STATED_TERMS],
            "host": host_record(),
        },
        notes=[
            "⛔ Recorder, never explainer. No row is related to another, no correction is differenced against "
            "another, and nothing here says how the service computes any of them.",
            "⛔ reference_only, with no band: the band a consumer applies to these rows is that consumer's own, set "
            "in its own tree as a reviewed change.",
            "⚠ The service's LT+S is, in its document's words, 'astrometric states corrected for stellar aberration'. "
            "The document names no deflection of light for it; the manual names that deflection among what makes "
            "coordinates 'apparent'. These rows are what the service printed under each word, nothing more.",
            "⚠ The service answers from DE441. A comparison against any other solution carries the difference "
            "between the two solutions, which these rows do not measure.",
            "⚠ The instants are in TDB and were asked in TDB, explicitly. Nothing here is in a frame of date.",
            service.REPRODUCIBILITY_CONDITION,
            service.ACQUISITION_LIMIT,
        ],
    )


def build_acquisition_header(*, kind: str, values_sha256: str, generator, version: str) -> Header:
    return Header(
        fixture_kind="provenance_record",
        reference="instrument",
        generator=generator,
        generated=today(),
        title="How the geocentric ICRF states were obtained from the publisher's ephemeris service",
        oracle={
            "implementation": "python urllib.request over HTTPS",
            "python": host_record()["python"],
            "user_agent": USER_AGENT,
            "endpoint": service.ENDPOINT,
            "interface_version": version,
            "retrieval_kind": kind,
            "retrieval_kind_meaning": RETRIEVAL_KINDS[kind],
            "values_file": {"path": VALUES_PATH, "sha256": values_sha256},
        },
        attests=(
            "the address each response came from, the query sent, the digest of the resource extracted from each by "
            "R1's rule, the service state each named, the date each was requested, and whether this record was "
            "made from live requests or from the copies kept"
        ),
        authority={
            "held_by": "this instrument, as the party that performed the requests or read the copies it kept",
            "kind": "direct observation of a sequence of network retrievals, or a read of the copies kept of one",
            "scope": service.ACQUISITION_LIMIT,
        },
        record_date=today(),
        row_schema={
            "finding": "retrieval",
            "retrieval_kind": "live_request | cache_read",
            "url": "the address requested, parameters sorted",
            "resource_sha256": "the digest of the response with the generation stamp and every service-state value "
                               "cut out and marked, by R1's rule",
            "resource_bytes": "the length of that resource",
            "acquired_on": "the date the response was requested from the service",
            "service_state": "what the response named: interface, the target's and the centre's solution",
            "classified_as_transaction": "the regions cut as belonging to the call rather than the answer; names only",
        },
        summary={"host": host_record(), "retrieval_kind": kind},
        notes=[
            "⛔ A cache read is not an acquisition. Where `retrieval_kind` is cache_read no request was sent; the "
            "copies read were kept by the live run whose date each row names.",
            "⚠ Every row is a response `retrieve()` accepted: a failed request raises there, so none is recorded.",
            service.REPRODUCIBILITY_CONDITION,
        ],
    )


def acquisition_rows(answered, *, kind: str) -> list[dict]:
    return [{
        "finding": "retrieval",
        "request_id": request["request_id"],
        "retrieval_kind": kind,
        "url": got.url,
        "resource_sha256": got.resource_sha256,
        "resource_bytes": got.resource_bytes,
        "acquired_on": got.acquired_on,
        "service_state": response.service_state,
        "classified_as_transaction": list(response.envelope_excluded),
        "instants": len(response.data_rows),
    } for request, got, response in answered]


# ======================================================================================
# The run
# ======================================================================================


def inside(path: Path, root: Path) -> bool:
    path, root = path.resolve(), root.resolve()
    return path == root or root in path.parents


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--profile", required=True, help="the data profile manifest whose interval bounds the grid")
    parser.add_argument("--kernel", required=True, type=Path, help="the pinned short-span kernel the events are "
                                                                   "selected on")
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--cache", default=HERE.parent / "cache", type=Path)
    parser.add_argument("--center", default="500@399")
    parser.add_argument("--corrections", default="NONE,LT,LT+S")
    parser.add_argument("--budget-row", default="R1-service-state")
    parser.add_argument("--from-cache", action="store_true", help="read the copies a live run kept; send nothing")
    parser.add_argument("--plan-only", action="store_true", help="print the request count and estimate; send nothing")
    args = parser.parse_args(argv)

    generator = None if args.plan_only else generator_for(HERE / Path(SCRIPT).name)
    print(describe_reserved_names())
    corrections = [c.strip() for c in args.corrections.split(",") if c.strip()]
    interval = modes.read_interval(args.profile)
    pin = verify(args.kernel)
    instants = epochs(lattice_epochs(interval) + event_epochs(args.kernel, interval))
    digest = epoch_set_digest(instants)
    requests = plan(instants, center=args.center, corrections=corrections)
    sizing = estimate(requests)
    print(f"{len(instants)} instants (set {digest[:16]}), {len(requests)} requests in {len(chunks(instants))} "
          f"chunk(s) per body and correction; estimate {sizing['estimated_wall_seconds'] / 60:.1f} min live; "
          f"longest address {sizing['longest_address_characters']} characters; as {USER_AGENT}")
    if args.plan_only:
        return 0
    values_path, record_path = args.out / VALUES_PATH, args.out / ACQUISITION_PATH
    for path in (values_path, record_path):
        if path.exists():
            raise Refusal(f"{path} exists; a record is never overwritten")

    answered, version = read(requests, cache=args.cache, center=args.center, digest=digest,
                             from_cache=args.from_cache)
    kind = "cache_read" if args.from_cache else "live_request"
    header = build_values_header(answered, version=version, instants=instants, interval=interval,
                                 kernel_identity=oracle_identity(args.kernel, pin), center=args.center,
                                 corrections=corrections, generator=generator, budget_row=args.budget_row)
    rows = rows_for(answered, center=args.center)
    written = write_jsonl(values_path, header, rows)
    values_sha256 = hashlib.sha256(values_path.read_bytes()).hexdigest()
    write_jsonl(record_path, build_acquisition_header(kind=kind, values_sha256=values_sha256, generator=generator,
                                                      version=version), acquisition_rows(answered, kind=kind))
    print(f"wrote {written} rows -> {values_path} (sha256 {values_sha256[:16]}...); record ({kind}) -> {record_path}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (Refusal, ServiceFormatError, AcquisitionError) as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        raise SystemExit(2)
