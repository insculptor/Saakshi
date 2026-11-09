"""R1 — one apparent direction, as the publisher's service prints it in two of-date frames. A probe.

A feasibility probe, not a sampler. It asks the publisher's ephemeris service, from the geocentre, for the
apparent direction of a few bodies at a few instants in the coordinates of two observer quantities on one line
of one response: quantity 2, apparent right ascension and declination in the service's true-equator and
equinox-of-date coordinates, and quantity 31, ecliptic-of-date longitude and latitude. It asks under each angle
format and precision the interface offers, and once with every format parameter left at its default, and
writes down what came back, character for character.

* ⭐ **The request and the service state are R1's, by import.** The address, the query encoding, the retrieval
  with its canonical form, the generation stamp cut out of the digest, and the service-state rules — interface
  version, the target's and the centre's solution, the Earth-orientation file — are `src/saakshi/service.py`'s
  and `src/saakshi/acquisition.py`'s, which `r1_horizons.py` reads through. The one vector request is
  `r1_horizons.py`'s own query with two parameters replaced, read by its own reader. Nothing is defined twice.
* ⭐ **Every row says what answered it**: the interface version, the target's and the centre's solution and the
  Earth-orientation file and coverage, on every row. A response without them is refused.
* ⛔ **A service answering otherwise than R1 recorded it is a stop**, not a row: a different interface version,
  or a different solution named for a body R1 read. Refused before anything is written.
* ⛔ **Recorder, never explainer.** Nothing here relates one frame to the other, computes an angle between
  them, or says how the service computes either. The digits printed are counted. Nothing is computed from them.
* ⛔ **No band, no class, no unit for a comparison and no budget row.** One `provenance_record` under R1.
* ⛔ **Nothing it reads is written into this repository.** The output and the retrieval cache are refused
  inside this working tree: the terms under which the service's responses may be redistributed are quoted
  beside the readings, and have not been examined here.

Usage:
    python r1_of_date_probe.py --profile MANIFEST --cache DIR --out FILE
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

HERE = Path(__file__).resolve().parent
# ⛔ Importing a sibling generator must not write its bytecode beside it: an untracked file is a dirty tree,
#    and the commit this record names would not be the tree it ran from.
sys.dont_write_bytecode = True
for _path in (str(HERE.parent / "src"), str(HERE)):
    if _path not in sys.path:
        sys.path.insert(0, _path)

# ⭐ R1's request and service-state code, by import.
from saakshi import service  # noqa: E402
from saakshi.acquisition import USER_AGENT, AcquisitionError, Retrieval, retrieve  # noqa: E402
from saakshi.fixture import Header, describe_reserved_names, patterned, write_jsonl  # noqa: E402
from saakshi.provenance import REPO, generator_for, host_record, today  # noqa: E402
from saakshi.service import ServiceFormatError  # noqa: E402

# ⭐ The data profile's interval, read by the reader the obliquity records use, by import.
import nutation_obliquity_modes as modes  # noqa: E402

SCRIPT = "generators/r1_of_date_probe.py"


class Refusal(Exception):
    """A condition under which nothing may be written."""


# ======================================================================================
# The client, and the terms it is sent under
# ======================================================================================

#: ⭐ The client this probe names. The service's published Fair Use Policy asks automated clients for a product
#: name, a version and contact information; the contact here is this repository's public address. ⛔ No email
#: address and no person's name.
CONTACT_USER_AGENT = f"{USER_AGENT} (+https://{REPO})"

#: ⚠ The pause between requests, in seconds. One request at a time, never two at once.
REQUEST_INTERVAL_SECONDS = 2.0

#: The published pages this record quotes, as retrieved. ⛔ Quoted, never interpreted, and no legal conclusion
#: is drawn from any of them.
DOCUMENTS: tuple[dict, ...] = (
    {"document": "horizons_manual", "url": "https://ssd.jpl.nasa.gov/horizons/manual.html",
     "retrieved": "2026-11-09",
     "sha256": "be45b0137b37068c48760bbaf306f52a72c10239c175ba91119a30eb30612a81"},
    {"document": "horizons_api", "url": "https://ssd-api.jpl.nasa.gov/doc/horizons.html",
     "retrieved": "2026-11-09",
     "sha256": "6ca45d9c222d6e5c425ae3e0a3c44225cf8b6d30c4a14892b0f1157b0ab4cfe4"},
    {"document": "ssd_api_fair_use_policy", "url": "https://ssd-api.jpl.nasa.gov/",
     "retrieved": "2026-11-09",
     "sha256": "a91502a7cfc7624b1b20a81777db7f376862eed9d556d6f9565f394420f4896d"},
    {"document": "ssd_faq", "url": "https://ssd.jpl.nasa.gov/faq.html", "retrieved": "2026-11-09",
     "sha256": "d48ba84a9bba9972981c62e8d5ae4216732a996ed5274ba3e38b8428cf14bfef"},
)

#: The publisher's stated terms, quoted from the pages above. ⛔ Quoted only.
STATED_TERMS: tuple[dict, ...] = (
    {"document": "ssd_api_fair_use_policy",
     "words": "You agree to submit only one API request at a time (no simultaneous requests)."},
    {"document": "ssd_api_fair_use_policy",
     "words": "Applications making automated connections must provide a valid, application-specific "
              "User-Agent request header that includes correct product name, version, and contact "
              "information."},
    {"document": "ssd_faq",
     "words": "No permissions are needed. The data provided on this site are considered public domain. "
              "However, use of information from this site does not imply NASA/Caltech/JPL endorsement."},
)

# ======================================================================================
# What R1 recorded, against which this run is a stop or not
# ======================================================================================

#: ⛔ The interface R1's acquisition record of 2026-08-04 (commit `6fc673e`) names on every retrieval.
EXPECTED_INTERFACE: dict[str, str] = {
    "interface_source": "NASA/JPL Horizons API",
    "interface_version": "1.2",
}
#: ⛔ The solution that record names for each body this probe reads, and for the Earth.
EXPECTED_SOLUTIONS: dict[str, str] = {"10": "DE441", "301": "DE441", "399": "DE441", "499": "mar099",
                                      "5": "DE441", "9": "DE441"}

# ======================================================================================
# What is asked
# ======================================================================================

#: The bodies read, as sent. ⭐ Different distances, speeds and latitudes, so a direction the two quantities
#: printed differently for one of them would show.
TARGETS: tuple[dict, ...] = (
    {"command": "10", "label": "Sun"},
    {"command": "301", "label": "Moon"},
    {"command": "499", "label": "Mars"},
    {"command": "5", "label": "Jupiter system barycentre"},
    {"command": "9", "label": "Pluto system barycentre"},
)
CENTER_COMMAND = "500@399"
CENTER_BODY = "399"

#: The instants named by a civil terrestrial time, besides the interval's two ends. ⭐ Each is a whole or half
#: Julian day, so its decimal is exact and the service's own echo of it can be held to the bit.
NAMED_INSTANTS: tuple[str, ...] = (
    "1900-01-01T00:00:00", "1950-01-01T00:00:00", "2000-01-01T12:00:00", "2020-01-01T00:00:00",
    "2026-06-01T00:00:00", "2026-12-01T00:00:00", "2027-06-01T00:00:00", "2100-01-01T00:00:00",
)
#: ⭐ A window of instants a sixteenth of a day apart, around the first day the Earth-orientation coverage the
#: service printed on 2026-11-09 begins. Each is exact in binary and in the printed decimal.
WINDOW_CENTRE = "1962-01-20T00:00:00"
WINDOW_HALF_STEPS = 32
WINDOW_STEP_DAYS = 0.0625
#: How far inside the interval's ends the first and last instants are asked. See :func:`instants`.
END_MARGIN_DAYS = 1.0

#: The query every observer request shares. ⭐ Written out in full: a request assembled from defaults nobody
#: wrote down is not sufficient to regenerate.
OBSERVER_QUERY: dict[str, str] = {
    "format": "json",
    "EPHEM_TYPE": "'OBSERVER'",
    "CENTER": f"'{CENTER_COMMAND}'",
    "QUANTITIES": "'2,31'",
    "TIME_TYPE": "'TT'",
    "TLIST_TYPE": "'JD'",
    "CAL_FORMAT": "'JD'",
    "CSV_FORMAT": "'YES'",
    "APPARENT": "'AIRLESS'",
    "OBJ_DATA": "'NO'",
    "MAKE_EPHEM": "'YES'",
}
#: ⭐ The one request whose format parameters are all left at the interface's defaults, so "by default" is
#: read rather than assumed. Only what selects the reading is sent.
DEFAULT_FORMAT_QUERY: dict[str, str] = {
    "format": "json",
    "EPHEM_TYPE": "'OBSERVER'",
    "CENTER": f"'{CENTER_COMMAND}'",
    "QUANTITIES": "'2,31'",
    "TIME_TYPE": "'TT'",
    "TLIST_TYPE": "'JD'",
    "OBJ_DATA": "'NO'",
    "MAKE_EPHEM": "'YES'",
}
DEFAULT_FORMAT_TARGET = "10"

_DEG = r"^[-+]?\d{1,3}\.\d+$"
_RA_HMS = r"^\d{2} \d{2} \d{2}\.\d+$"
_DEC_DMS = r"^[-+]?\d{2} \d{2} \d{2}\.\d+$"
_JD = r"^\d{7}\.\d{9}$"

#: Each variant's format parameters, the bodies it reads, whether it reads the window, and its table's columns
#: as the service labels them, each with the shape a printed value must have. ⛔ The labels are asserted: a
#: re-ordered or re-labelled table would otherwise be read confidently and wrongly.
VARIANTS: tuple[dict, ...] = (
    {"variant": "hms", "params": {"ANG_FORMAT": "'HMS'", "EXTRA_PREC": "'NO'"},
     "targets": ("10", "301", "499"), "window": False,
     "columns": (("Date_________JDTT", _JD), ("", None), ("", None), ("R.A.__(a-app)", _RA_HMS),
                 ("DEC_(a-app)", _DEC_DMS), ("ObsEcLon", _DEG), ("ObsEcLat", _DEG))},
    {"variant": "hms_extra", "params": {"ANG_FORMAT": "'HMS'", "EXTRA_PREC": "'YES'"},
     "targets": ("10", "301", "499"), "window": False,
     "columns": (("Date_________JDTT", _JD), ("", None), ("", None), ("R.A.____(a-app)", _RA_HMS),
                 ("DEC_____(a-app)", _DEC_DMS), ("ObsEcLon", _DEG), ("ObsEcLat", _DEG))},
    {"variant": "deg", "params": {"ANG_FORMAT": "'DEG'", "EXTRA_PREC": "'NO'"},
     "targets": ("10", "301", "499"), "window": False,
     "columns": (("Date_________JDTT", _JD), ("", None), ("", None), ("R.A._(a-app)", _DEG),
                 ("DEC_(a-app)", _DEG), ("ObsEcLon", _DEG), ("ObsEcLat", _DEG))},
    {"variant": "deg_extra", "params": {"ANG_FORMAT": "'DEG'", "EXTRA_PREC": "'YES'"},
     "targets": ("10", "301", "499", "5", "9"), "window": True,
     "columns": (("Date_________JDTT", _JD), ("", None), ("", None), ("R.A.__(a-app)", _DEG),
                 ("DEC___(a-app)", _DEG), ("ObsEcLon", _DEG), ("ObsEcLat", _DEG))},
)
#: The default-format table: whitespace-separated, its labels and the shape of each value's tokens.
DEFAULT_FORMAT_LABELS: tuple[str, ...] = ("Date__(TT)__HR:MN:SC.fff", "R.A.__(a-apparent)__DEC", "ObsEcLon",
                                          "ObsEcLat")
DEFAULT_FORMAT_TOKENS: tuple[str, ...] = (
    r"^\d{4}-[A-Z][a-z]{2}-\d{2}$", r"^\d{2}:\d{2}:\d{2}\.\d+$",
    r"^\d{2}$", r"^\d{2}$", r"^\d{2}\.\d+$", r"^[-+]?\d{2}$", r"^\d{2}$", r"^\d{2}\.\d+$", _DEG, _DEG,
)
_MONTHS = {name: number for number, name in enumerate(
    ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"), start=1)}

#: ⭐ The two parameters replaced in R1's own vector query: the geocentre, and the only plane of date the
#: interface offers a vector table.
VECTOR_REPLACED: dict[str, str] = {"CENTER": f"'{CENTER_COMMAND}'", "REF_PLANE": "'BODY'"}
VECTOR_TARGET = "499"
VECTOR_INSTANT = "2000-01-01T12:00:00"

#: ⭐ Service state an observer response carries that a vector response does not: which solution the service
#: named for the body bending the light and for the body it checks for interference. Recorded where present.
OBSERVER_STATE_PATTERNS: tuple[tuple[str, re.Pattern[str], bool], ...] = (
    ("deflecting_body_solution", re.compile(r"^Rel\. light bend *:.*?\{source: *([^}]+?) *\}", re.M), False),
    ("interferer_solution", re.compile(r"^Vis\. interferer *:.*?\{source: *([^}]+?) *\}", re.M), False),
)
#: ⛔ Required on every observer response here: what the Earth-orientation data in force was.
OBSERVER_REQUIRED_STATE: tuple[str, ...] = ("earth_orientation_file", "earth_orientation_coverage")
#: Recorded on every row.
ROW_STATE: tuple[str, ...] = ("interface_source", "interface_version", "target_solution", "center_solution",
                              "earth_orientation_file", "earth_orientation_coverage")


# ======================================================================================
# The instants
# ======================================================================================


def instants(interval: dict) -> tuple[list[dict], list[dict]]:
    """The named instants and the window, each with its civil terrestrial time, all inside the interval.

    ⚠ The first and last are a day inside the interval's ends, not on them: the manifest declares its coverage
    in one time scale and these instants are asked in another, and an end asked in the wrong scale could fall
    just outside it.
    """
    named = [{"name": "interval_start_next_day", "jd": interval["start"] + END_MARGIN_DAYS}]
    named += [{"name": stamp, "jd": modes.julian_day(stamp)} for stamp in NAMED_INSTANTS]
    named.append({"name": "interval_end_previous_day", "jd": interval["end"] - END_MARGIN_DAYS})
    centre = modes.julian_day(WINDOW_CENTRE)
    window = [{"name": "window", "jd": centre + step * WINDOW_STEP_DAYS}
              for step in range(-WINDOW_HALF_STEPS, WINDOW_HALF_STEPS + 1)]
    for instant in named + window:
        if not interval["start"] < instant["jd"] < interval["end"]:
            raise Refusal(f"{instant['name']} (JD {instant['jd']!r}) is not inside the profile's interval")
        instant["civil_tt"] = modes.civil(instant["jd"])
    if len({i["jd"] for i in named + window}) != len(named) + len(window):
        raise Refusal("two instants coincide")
    return named, window


def tlist(jds: list[float]) -> str:
    """The time list as R1 sends one: the instants' shortest decimals, comma-separated, in one quoted value."""
    return "'" + ",".join(repr(jd) for jd in jds) + "'"


# ======================================================================================
# The plan: every request, in the order it is sent
# ======================================================================================


def plan(interval: dict, vector_query: dict[str, str]) -> list[dict]:
    named, window = instants(interval)
    labels = {target["command"]: target["label"] for target in TARGETS}
    vector_instant = {"name": VECTOR_INSTANT, "jd": modes.julian_day(VECTOR_INSTANT),
                      "civil_tt": VECTOR_INSTANT}
    requests = [{
        "request_id": f"vectors-{VECTOR_TARGET}",
        "part": "vectors",
        "target_command": VECTOR_TARGET,
        "target_label": labels[VECTOR_TARGET],
        "instants": [vector_instant],
        "query": {**vector_query, **VECTOR_REPLACED, "COMMAND": f"'{VECTOR_TARGET}'",
                  "TLIST": tlist([vector_instant["jd"]])},
    }]
    for variant in VARIANTS:
        chosen = named + (window if variant["window"] else [])
        for command in variant["targets"]:
            requests.append({
                "request_id": f"observer-{variant['variant']}-{command}",
                "part": "observer",
                "variant": variant["variant"],
                "target_command": command,
                "target_label": labels[command],
                "instants": chosen,
                "query": {**OBSERVER_QUERY, **variant["params"], "COMMAND": f"'{command}'",
                          "TLIST": tlist([i["jd"] for i in chosen])},
            })
    requests.append({
        "request_id": f"observer-default-{DEFAULT_FORMAT_TARGET}",
        "part": "observer_default_format",
        "variant": "default_format",
        "target_command": DEFAULT_FORMAT_TARGET,
        "target_label": labels[DEFAULT_FORMAT_TARGET],
        "instants": named,
        "query": {**DEFAULT_FORMAT_QUERY, "COMMAND": f"'{DEFAULT_FORMAT_TARGET}'",
                  "TLIST": tlist([i["jd"] for i in named])},
    })
    return requests


# ======================================================================================
# A response, split by R1's rules
# ======================================================================================


@dataclass(frozen=True)
class Observed:
    """One response: its service state recorded, its envelope cut, its resource and its text."""

    service_state: dict[str, str]
    envelope_excluded: tuple[str, ...]
    resource_text: str
    text: str


def split(payload: bytes, *, query: dict[str, str]) -> Observed:
    """R1's split of a response, over any table: the interface named, the stamp cut, the service state recorded.

    ⭐ Every rule is `service.py`'s: its signature keys, its envelope patterns, its service-state patterns and
    their `required` flags, its one-match location, its marker. Only the observer table's two extra solution
    lines are added. Over a vector response the resource is the one `service.parse` cuts, character for
    character, and the tests hold it so.
    """
    where = query.get("COMMAND", "<no command>")
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
    for name, pattern, required in (*service._SERVICE_STATE_PATTERNS, *OBSERVER_STATE_PATTERNS):
        span = service._locate(text, name, pattern, required=required, where=where)
        if span is None:
            continue
        cuts.append((*span, name))
        state[name] = text[span[0]:span[1]]
    resource = text
    for start, end, name in sorted(cuts, reverse=True):
        resource = resource[:start] + service._EXCLUDED.format(name=name) + resource[end:]
    return Observed(service_state=state, envelope_excluded=tuple(excluded), resource_text=resource, text=text)


def canonical(query: dict[str, str]) -> Callable[[bytes], bytes]:
    """The canonical form `retrieve()` digests: the resource of :func:`split`."""
    return lambda payload: split(payload, query=query).resource_text.encode("utf-8")


def expect_service(state: dict[str, str], *, target: str, where: str) -> None:
    """⛔ The stop: a service answering otherwise than R1 recorded it."""
    for key, value in EXPECTED_INTERFACE.items():
        if state.get(key) != value:
            raise Refusal(f"⛔ STOP: {where}: {key} is {state.get(key)!r}; R1 recorded {value!r}")
    for key, command in (("target_solution", target), ("center_solution", CENTER_BODY)):
        if state.get(key) != EXPECTED_SOLUTIONS[command]:
            raise Refusal(f"⛔ STOP: {where}: {key} is {state.get(key)!r}; R1 recorded "
                          f"{EXPECTED_SOLUTIONS[command]!r} for {command}")


# ======================================================================================
# The tables
# ======================================================================================


def _block(text: str, *, where: str) -> tuple[str, list[str]]:
    """The column header line and the data lines. ⛔ Exactly one of each delimiter and one header line."""
    if text.count("$$SOE") != 1 or text.count("$$EOE") != 1:
        raise ServiceFormatError(f"{where}: the data block delimiters are not a single pair")
    before, rest = text.split("$$SOE", 1)
    lines = [line for line in before.splitlines() if line.strip()]
    if len(lines) < 2 or set(lines[-1].strip()) != {"*"}:
        raise ServiceFormatError(f"{where}: no rule line above the data block")
    header = lines[-2]
    # ⚠ Which line is the header is settled by position, above the rule; what it says is settled by the labels.
    #   A second line beginning 'Date' means a table this probe has not identified.
    if len(re.findall(r"^ *Date", text, re.M)) != 1:
        raise ServiceFormatError(f"{where}: more than one line begins 'Date'")
    data = [line for line in rest.split("$$EOE", 1)[0].splitlines() if line.strip()]
    return header, data


def _fields(line: str) -> list[str]:
    fields = [part.strip() for part in line.split(",")]
    while fields and not fields[-1]:
        fields.pop()
    return fields


_DIGITS = re.compile(r"\.(\d+)(?:[Ee][-+]?\d+)?$")


def decimals(printed: str) -> int | None:
    """Digits after the decimal point of a printed value's last component, an exponent not counted; None where
    nothing is printed."""
    if not printed:
        return None
    match = _DIGITS.search(printed.split()[-1])
    return len(match.group(1)) if match else 0


def read_csv_table(text: str, *, variant: dict, wanted: list[dict], where: str) -> tuple[list[str], list[list[str]]]:
    """One comma-separated observer table, every check applied. Returns the labels and each line's fields."""
    header, data = _block(text, where=where)
    labels = _fields(header)
    expected = [label for label, _ in variant["columns"]]
    if labels != expected:
        raise ServiceFormatError(f"{where}: columns {labels} are not {expected}")
    if len(data) != len(wanted):
        raise ServiceFormatError(f"{where}: {len(data)} data lines for {len(wanted)} instants asked")
    rows = []
    for line, instant in zip(data, wanted):
        fields = _fields(line)
        if len(fields) != len(labels):
            raise ServiceFormatError(f"{where}: a data line has {len(fields)} fields, not {len(labels)}: {line!r}")
        for field, (label, shape) in zip(fields, variant["columns"]):
            if shape is not None and not re.match(shape, field):
                raise ServiceFormatError(f"{where}: {label!r} printed {field!r}, not the shape {shape}")
        if float(fields[0]) != instant["jd"]:
            raise ServiceFormatError(f"{where}: answered for JD {fields[0]} where {instant['jd']!r} was asked")
        rows.append(fields)
    return labels, rows


def _calendar_jd(date: str, clock: str) -> float:
    year, month, day = date.split("-")
    hours, minutes, seconds = clock.split(":")
    whole, _, fraction = seconds.partition(".")
    if fraction.strip("0"):
        raise ServiceFormatError(f"{date} {clock}: a fraction of a second this probe never asks for")
    stamp = f"{year}-{_MONTHS[month]:02d}-{day}T{hours}:{minutes}:{whole}"
    return modes.julian_day(stamp)


def read_default_table(text: str, *, wanted: list[dict], where: str) -> tuple[list[str], list[list[str]]]:
    """The default-format table: whitespace-separated tokens, every check applied."""
    header, data = _block(text, where=where)
    labels = header.split()
    if tuple(labels) != DEFAULT_FORMAT_LABELS:
        raise ServiceFormatError(f"{where}: columns {labels} are not {list(DEFAULT_FORMAT_LABELS)}")
    if len(data) != len(wanted):
        raise ServiceFormatError(f"{where}: {len(data)} data lines for {len(wanted)} instants asked")
    rows = []
    for line, instant in zip(data, wanted):
        tokens = line.split()
        if len(tokens) != len(DEFAULT_FORMAT_TOKENS):
            raise ServiceFormatError(f"{where}: a data line has {len(tokens)} tokens, not "
                                     f"{len(DEFAULT_FORMAT_TOKENS)}: {line!r}")
        for token, shape in zip(tokens, DEFAULT_FORMAT_TOKENS):
            if not re.match(shape, token):
                raise ServiceFormatError(f"{where}: printed {token!r}, not the shape {shape}")
        if _calendar_jd(tokens[0], tokens[1]) != instant["jd"]:
            raise ServiceFormatError(f"{where}: answered for {tokens[0]} {tokens[1]} where JD "
                                     f"{instant['jd']!r} was asked")
        rows.append([" ".join(tokens[0:2]), " ".join(tokens[2:5]), " ".join(tokens[5:8]), tokens[8], tokens[9]])
    return labels, rows


def default_fields(labels: list[str]) -> list[str]:
    """The default table's five printed fields under its four labels: its second label heads two values."""
    return [labels[0], f"{labels[1]} [ra]", f"{labels[1]} [dec]", labels[2], labels[3]]


# ======================================================================================
# Reading
# ======================================================================================

Fetch = Callable[[str, Path, Callable[[bytes], bytes]], Retrieval]


def fetch_live(url: str, cache: Path, canonical_form: Callable[[bytes], bytes]) -> Retrieval:
    """One live request, through R1's retrieval, under this probe's client name."""
    return retrieve(url, cache=cache, canonical=canonical_form, user_agent=CONTACT_USER_AGENT)


def inside(path: Path, root: Path) -> bool:
    path, root = path.resolve(), root.resolve()
    return path == root or root in path.parents


def read(requests: list[dict], *, cache: Path, fetch: Fetch = fetch_live,
         sleep: Callable[[float], None] = time.sleep) -> tuple[list[dict], list[dict]]:
    """Every request, one at a time, with the pause between. Returns the request rows and the reading rows."""
    request_rows: list[dict] = []
    reading_rows: list[dict] = []
    for index, request in enumerate(requests):
        if index:
            sleep(REQUEST_INTERVAL_SECONDS)
        query = request["query"]
        where = request["request_id"]
        url = service.build_url(query)
        if request["part"] == "vectors":
            retrieval = fetch(url, cache / f"{where}.txt", service.canonical_form(query))
            response = service.parse(retrieval.payload, query=query)
            state, envelope = dict(response.service_state), list(response.envelope_excluded)
            labels = list(service._EXPECTED_COLUMNS)
            if len(response.data_rows) != len(request["instants"]):
                raise ServiceFormatError(f"{where}: {len(response.data_rows)} lines for "
                                         f"{len(request['instants'])} instants asked")
            for fields, instant in zip(response.data_rows, request["instants"]):
                if float(fields[0]) != instant["jd"]:
                    raise ServiceFormatError(f"{where}: answered for JD {fields[0]} where {instant['jd']!r} was asked")
            rows = [list(fields) for fields in response.data_rows]
            names = list(labels)
            stated = dict(response.stated)
            scale = "TDB"
        else:
            retrieval = fetch(url, cache / f"{where}.txt", canonical(query))
            observed = split(retrieval.payload, query=query)
            state, envelope = dict(observed.service_state), list(observed.envelope_excluded)
            for name in OBSERVER_REQUIRED_STATE:
                if name not in state:
                    raise ServiceFormatError(f"{where}: the response names no {name}")
            if request["part"] == "observer":
                variant = next(v for v in VARIANTS if v["variant"] == request["variant"])
                labels, rows = read_csv_table(observed.text, variant=variant, wanted=request["instants"],
                                              where=where)
                names = list(labels)
            else:
                labels, rows = read_default_table(observed.text, wanted=request["instants"], where=where)
                names = default_fields(labels)
            stated = {}
            scale = "TT"
        expect_service(state, target=request["target_command"], where=where)
        request_rows.append({
            "finding": "request",
            "request_id": where,
            "part": request["part"],
            "variant": request.get("variant"),
            "target_command": request["target_command"],
            "target_label": request["target_label"],
            "query": [{"parameter": name, "value": value} for name, value in sorted(query.items())],
            **retrieval.as_record(),
            "service_state": state,
            "classified_as_transaction": envelope,
            "stated": stated,
            "columns": labels,
            "fields": names,
            "readings": len(rows),
        })
        for fields, instant in zip(rows, request["instants"]):
            reading_rows.append({
                "finding": "reading",
                "request_id": where,
                "part": request["part"],
                "variant": request.get("variant"),
                "target_command": request["target_command"],
                **{name: state.get(name) for name in ROW_STATE},
                "instant": instant["name"],
                **patterned("jd", instant["jd"]),
                "time_scale": scale,
                "civil": instant["civil_tt"],
                "printed": fields,
                "decimals": [decimals(field) for field in fields],
            })
        print(f"  {where}: {len(rows)} readings, {state.get('target_solution')}/{state.get('center_solution')}, "
              f"interface {state.get('interface_version')}, resource {retrieval.resource_sha256[:12]}...")
    return request_rows, reading_rows


# ======================================================================================
# The record
# ======================================================================================


def check(request_rows: list[dict], reading_rows: list[dict], requests: list[dict]) -> None:
    """⛔ Before anything is written: every request answered once, every row carrying what answered it."""
    if [row["request_id"] for row in request_rows] != [r["request_id"] for r in requests]:
        raise Refusal("the requests answered are not the requests planned, in order")
    if len(reading_rows) != sum(len(r["instants"]) for r in requests):
        raise Refusal("the readings are not one per instant asked")
    for row in reading_rows:
        missing = [name for name in ROW_STATE if not row.get(name)]
        if missing:
            raise Refusal(f"{row['request_id']} {row['instant']}: a row without {missing}")


def precision(request_rows: list[dict], reading_rows: list[dict]) -> list[dict]:
    """Per request and printed field: the digits after the decimal point, as counted on every reading."""
    out = []
    for request in request_rows:
        rows = [r for r in reading_rows if r["request_id"] == request["request_id"]]
        for position, name in enumerate(request["fields"]):
            counts = sorted({r["decimals"][position] for r in rows if r["decimals"][position] is not None})
            if counts:
                out.append({"request_id": request["request_id"], "field": name, "decimals_printed": counts})
    return out


def build_header(request_rows: list[dict], reading_rows: list[dict], *, interval: dict, generator,
                 requests: list[dict]) -> Header:
    states = sorted({json.dumps(row["service_state"], sort_keys=True) for row in request_rows})
    return Header(
        fixture_kind="provenance_record",
        reference="R1",
        generator=generator,
        generated=today(),
        title="One apparent direction in two of-date frames, as the publisher's service printed it",
        oracle={
            "publisher": "JPL Solar System Dynamics",
            "service": "Horizons",
            "endpoint": service.ENDPOINT,
            "user_agent": CONTACT_USER_AGENT,
            "acquiring_instrument": {"software": "python urllib.request", "python": host_record()["python"]},
            "queried_on": today(),
            "service_states_observed": [json.loads(state) for state in states],
        },
        attests=(
            "what the publisher's ephemeris service printed, on this date, for the queries recorded here: the "
            "columns of each table, every value as printed, the digits printed, and the service state each "
            "response named"
        ),
        authority={
            "held_by": "the publisher, for what its service printed; this instrument, for the queries sent and "
                       "for the rule that split each response",
            "kind": "direct observation of a sequence of service responses",
            "scope": service.ACQUISITION_LIMIT,
        },
        record_date=today(),
        request={
            "endpoint": service.ENDPOINT,
            "user_agent": CONTACT_USER_AGENT,
            "request_interval_seconds": REQUEST_INTERVAL_SECONDS,
            "requests_issued": len(requests),
            "one_at_a_time": True,
            "interval": {key: interval[key] for key in ("profile", "manifest_sha256", "dataset",
                                                       "declared_coverage")},
            "targets": [dict(target) for target in TARGETS],
            "center": {"command": CENTER_COMMAND, "body": CENTER_BODY},
            "window": {"centre": WINDOW_CENTRE, "half_steps": WINDOW_HALF_STEPS,
                       **patterned("step_days", WINDOW_STEP_DAYS)},
            "variants": [{"variant": v["variant"],
                          "parameters": [{"parameter": k, "value": x} for k, x in sorted(v["params"].items())],
                          "targets": list(v["targets"]), "window": v["window"]} for v in VARIANTS],
            "vectors": {"from": "r1_horizons.COMMON_QUERY", "replaced": [{"parameter": k, "value": x}
                                                                          for k, x in sorted(VECTOR_REPLACED.items())]},
            "regenerate": "generators/r1_of_date_probe.py --profile <manifest> --cache <dir> --out <file> -- "
                          "needs the network; a cached response is not an acquisition",
        },
        row_schema={
            "finding": "request | reading",
            "query": "a request's every parameter as sent, sorted",
            "resource_sha256": "the digest of the response with the generation stamp and every service-state "
                               "value cut out and marked, by R1's rule",
            "service_state": "what the response named: interface, solutions, Earth-orientation file and coverage",
            "columns": "the table's column labels, as printed",
            "fields": "the printed fields those labels head, in order: the labels themselves, except where one "
                      "label heads two values",
            "printed": "a reading's every field, as printed, in the order of `fields`",
            "decimals": "digits after the decimal point of each printed field's last component; null where the "
                        "field is blank",
            "jd": "the instant asked, as a Julian day in `time_scale`, asserted against the service's answer",
            "civil": "the same instant as a civil date and time in that scale",
        },
        summary={
            "requests": len(request_rows),
            "readings": len(reading_rows),
            "precision": precision(request_rows, reading_rows),
            "documents": [dict(d) for d in DOCUMENTS],
            "stated_terms": [dict(t) for t in STATED_TERMS],
            "expected_from_r1": {"interface": EXPECTED_INTERFACE, "solutions": [
                {"command": c, "solution": s} for c, s in sorted(EXPECTED_SOLUTIONS.items())]},
            "host": host_record(),
        },
        notes=[
            "⛔ Recorder, never explainer. Nothing here relates the two frames, derives an angle between them, or "
            "says how the service computes either. The digits are counted; nothing is computed from them.",
            "⛔ No band, no class, no unit for a comparison and no budget row. Whether any reading here can serve "
            "as a comparand is its consumer's question.",
            "⭐ The service state is on every row: a reading that does not say what answered it is not written.",
            service.REPRODUCIBILITY_CONDITION,
            service.ACQUISITION_LIMIT,
        ],
    )


def r1_vector_query() -> dict[str, str]:
    """`r1_horizons.py`'s own query, by import. ⚠ Imported here, not at the top: it imports the SPICE binding,
    which every R1 run has and the fixture contract's own environment does not."""
    import r1_horizons  # noqa: PLC0415

    return dict(r1_horizons.COMMON_QUERY)


def generate(profile: str, cache: Path, out: Path, *, fetch: Fetch = fetch_live,
             sleep: Callable[[float], None] = time.sleep, vector_query: dict[str, str] | None = None,
             allow_dirty: bool = False) -> int:
    root = HERE.parent
    for name, path in (("--out", out), ("--cache", cache)):
        if inside(path, root):
            raise Refusal(f"{name} {path} is inside this working tree. ⛔ A service reading is not written here.")
    if out.exists():
        raise Refusal(f"{out} exists; a record is never overwritten")
    generator = generator_for(HERE / Path(SCRIPT).name, allow_dirty=allow_dirty)
    print(describe_reserved_names())
    interval = modes.read_interval(profile)
    requests = plan(interval, vector_query if vector_query is not None else r1_vector_query())
    print(f"{len(requests)} requests, one at a time, {REQUEST_INTERVAL_SECONDS} s apart, as {CONTACT_USER_AGENT}")
    request_rows, reading_rows = read(requests, cache=cache, fetch=fetch, sleep=sleep)
    check(request_rows, reading_rows, requests)
    header = build_header(request_rows, reading_rows, interval=interval, generator=generator, requests=requests)
    written = write_jsonl(out, header, [*request_rows, *reading_rows])
    print(f"wrote {written} rows -> {out.name}")
    return written


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--profile", required=True, help="the data profile manifest whose coverage bounds the instants")
    parser.add_argument("--cache", required=True, type=Path, help="the retrieval cache, outside this tree")
    parser.add_argument("--out", required=True, type=Path, help="the record, outside this tree")
    args = parser.parse_args(argv)
    try:
        generate(args.profile, args.cache, args.out)
    except (Refusal, modes.Refusal, AcquisitionError) as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
