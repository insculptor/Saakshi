"""The library's nutation and obliquity output read under three ephemeris requests, two data-file states and both nutation settings.

What one release of the ephemeris library returns for its pseudo-body for nutation and obliquity, read
black-box through ``calc`` and ``calc_ut``, and what its returned flag says beside the Moon's. One R3
``provenance_record``, written only from a clean commit. It follows ``mean_node_modes.py``'s shape and
discipline, for another body.

Three parts, and ⛔ **every reading is one call in a fresh child process**:

1. **mode_invariance** — ``calc`` on a dynamical-time Julian day, under five configurations (the
   analytical, the data-file and the JPL request, with the pinned data files on the path and with a
   verified-empty directory; the JPL request with no JPL file anywhere), each with the library's
   default nutation and with ``FLG_NONUT``, at every epoch.
2. **universal_time** — the same configurations, words and instants through ``calc_ut``, the instants
   passed as universal-time Julian days; ``deltat_ex`` under the same ephemeris bits; and ``calc`` at
   the universal day plus that offset.
3. **returned_flag_by_body** — the discriminating control: six conditions, four of them built so the
   requested ephemeris cannot answer, and the returned word of the Moon and of the pseudo-body through
   ``calc`` and ``calc_ut``, under both words. ⛔ The record is refused unless the Moon reports the
   substitution exactly where one was built: a reader that cannot see a substitution reads an echo as
   agreement.

⭐ **Every returned value is recorded, all six.** The library's documentation names what each position
holds; the record names them positionally as well, because its consumer reads a reading's first three
returned values under three fixed field names (``longitude``, ``latitude``, ``distance``) whatever the
body — and those names are written, held to the first three positions, so that the consumer can see a
value move.

⛔ **Recorder, never explainer.** Nothing here describes how the library computes anything. A
relation between readings is recorded as numbers, never as a mechanism.

⛔ **The interval's ends are a data profile manifest's declared coverage**, read from the file given and
converted back to the manifest's own strings before use — never a Julian day typed here. ⚠ The other
epochs are labelled instants and formulas written here, each held equal by a test to the survey's own:
J2000, the two years outside every measured edge at which the survey reads a body's returned word, and
the two ends and the middle of the range the survey searches for a body's edge.

⛔ **Refusals, each before anything is written**: a dirty or commitless working tree; a data directory
that is not exactly the pinned set; an "empty" directory that is not empty (both checked before and
after the run); a child that did not start from an interpreter without the library loaded, or returned
other than one reading, or whose output came back twice; ⭐ a child whose calls into the library — every
call made through the library module's callables and its submodule's after they are wrapped, recorded
inside the child with the arguments it actually received — are not exactly the sequence its FINISHED row
declares; a row that breaks one of these pairs — a reading's finding and part to its entry point, its part
to its epochs, its ephemeris label to its word's bits, its configuration or condition to the table defining
it, its nutation label to its word's nutation bit, a reading's body to the pseudo-body and an offset
reading to no body, a body label and name to the body, an epoch name to its instant and in-interval flag,
its three named values to the call's first three returned values; a NONUT request that moved nothing; a
returned word no reading through the same entry point requested; the Moon control not firing. ⚠ These guard
honest error, ⛔ not forgery: a reference to the library bound before the wrapping, its compiled extension
reached another way, or a call through one of its classes (which are not wrapped) is outside them.

The standard library and the binding only, as ``mean_node_modes.py``; ``git`` is called to read the
commit. Children run in an empty working directory that is not the parent's, with every ``SE_``
environment variable removed — the removal is recorded, never silent.

Usage::

    python nutation_obliquity_modes.py --ephe-path DIR --empty-dir DIR --profile MANIFEST --out FILE
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import platform
import shutil
import struct
import subprocess
import sys
import tempfile
import tomllib
import types
from importlib.metadata import PackageNotFoundError, version as _distribution_version

#: Where the generator lives — `generator.repo` and `generator.script`.
REPO = "github.com/insculptor/Saakshi"
SCRIPT = "generators/nutation_obliquity_modes.py"
SCHEMA_VERSION = "1.0.0"

#: The library's data files, pinned as everywhere else in this repository (a test holds this table
#: equal to `src/saakshi/swiss.py`'s, which this script may not import). ⛔ The directory must hold
#: exactly these and nothing else: the library reads what it finds there.
EPHE_PINS: tuple[dict, ...] = (
    {
        "dataset": "seas_18.se1",
        "profile": "swiss_file@1",
        "size_bytes": 223_004,
        "sha256": "a2cd8fc33807c78ca9a700c91c2e042258b12fc4796519e00781440b5ad8b2e2",
        "publisher": "Astrodienst AG",
        "pinned_on": "2026-08-04",
    },
    {
        "dataset": "semo_18.se1",
        "profile": "swiss_file@1",
        "size_bytes": 1_304_771,
        "sha256": "1ca07bd67c24374d77226180c20a4f9996cba013697894810518e7eb582ca4f7",
        "publisher": "Astrodienst AG",
        "pinned_on": "2026-08-04",
    },
    {
        "dataset": "sepl_18.se1",
        "profile": "swiss_file@1",
        "size_bytes": 484_061,
        "sha256": "ca1393ceab3a44fbc895887cf789c68819ae6a1cbc9b22225872dbe4ccd99a66",
        "publisher": "Astrodienst AG",
        "pinned_on": "2026-08-04",
    },
)

#: J2000.0 — the standard epoch, a definition.
J2000 = 2451545.0
#: 1970-01-01T00:00 as a Julian day — a definition, used to turn an ISO date into one.
UNIX_EPOCH_JD = 2440587.5
SECONDS_PER_DAY = 86400.0

#: The years outside every measured edge at which the survey reads a body's returned word (a test holds
#: them to `src/saakshi/swiss.py`'s `FIXED_CONDITION_EPOCHS`).
OUTSIDE_YEARS: tuple[int, ...] = (1500, 3000)
#: The two ends of the range the survey searches for a body's edge, 0h on 1 January of each (a test holds
#: them to `generators/r3_swiss.py`'s `EDGE_SEARCH_YEARS`, as the survey converts them).
EDGE_SEARCH: tuple[str, ...] = ("1000-01-01T00:00:00", "3000-01-01T00:00:00")

#: The five configurations: the requested ephemeris and the directory on the path. ⛔ No "no path set":
#: what the default path holds is undeclared, so an unset path fixes nothing.
CONFIGURATIONS: tuple[tuple[str, str, str], ...] = (
    ("moshier_files_present", "moshier", "data_files"),
    ("moshier_dir_empty", "moshier", "empty_directory"),
    ("swiss_file_present", "swiss_file", "data_files"),
    ("swiss_file_dir_empty", "swiss_file", "empty_directory"),
    ("jpl_requested_no_jpl_file", "jpl_file", "data_files"),
)

#: Part 3. `built_to_substitute`: the requested ephemeris is known not to be able to answer here.
CONDITIONS: tuple[dict, ...] = (
    {"condition": "swiss_file_inside_coverage", "ephemeris": "swiss_file", "path_state": "data_files",
     "epoch": "j2000", "built_to_substitute": False,
     "description": "the data-file request, the pinned files on the path, inside their coverage"},
    {"condition": "swiss_file_outside_coverage_1500", "ephemeris": "swiss_file", "path_state": "data_files",
     "epoch": "outside_1500", "built_to_substitute": True,
     "description": "the data-file request, the pinned files on the path, an instant before their coverage"},
    {"condition": "swiss_file_outside_coverage_3000", "ephemeris": "swiss_file", "path_state": "data_files",
     "epoch": "outside_3000", "built_to_substitute": True,
     "description": "the data-file request, the pinned files on the path, an instant after their coverage"},
    {"condition": "swiss_file_empty_directory", "ephemeris": "swiss_file", "path_state": "empty_directory",
     "epoch": "j2000", "built_to_substitute": True,
     "description": "the data-file request, a verified-empty directory on the path"},
    {"condition": "jpl_file_no_jpl_file", "ephemeris": "jpl_file", "path_state": "data_files",
     "epoch": "j2000", "built_to_substitute": True,
     "description": "the JPL request, the pinned files on the path and no JPL file among them"},
    {"condition": "moshier_files_present", "ephemeris": "moshier", "path_state": "data_files",
     "epoch": "j2000", "built_to_substitute": False,
     "description": "the analytical request, the pinned files on the path"},
)

#: The ephemeris bits of a flag word, by the survey's names for the three sources.
EPHEMERIS_NAMES: tuple[tuple[str, str], ...] = (
    ("moshier", "FLG_MOSEPH"), ("swiss_file", "FLG_SWIEPH"), ("jpl_file", "FLG_JPLEPH"))
EPHEMERIS_MASK = 7

#: ⭐ What the library's documentation says each of this body's six returned values is, in its own words.
#: ⚠ Recorded as the documentation's naming, beside the values, ⛔ never checked against them here.
VALUE_POSITIONS: tuple[str, ...] = (
    "true obliquity of the Ecliptic (includes nutation)",
    "mean obliquity of the Ecliptic",
    "nutation in longitude",
    "nutation in obliquity",
    "0",
    "0",
)
VALUE_POSITIONS_SOURCE = ("the library's programmer's documentation, section 3.2.4 'Obliquity and nutation' "
                          "(www.astro.com/swisseph/swephprg.htm, read 2026-11-02)")
#: ⭐ The consumer's names for a reading's first three returned values, whatever the body.
READER_FIELDS: tuple[str, ...] = ("longitude", "latitude", "distance")

ARCSECONDS_PER_DEGREE = 3600.0
CHILD_TIMEOUT_SECONDS = 120


class Refusal(Exception):
    """A condition under which nothing may be written."""


def bits(value: float) -> str:
    return struct.pack(">d", value).hex()


def unbits(text: str) -> float:
    return struct.unpack(">d", bytes.fromhex(text))[0]


def patterned(key: str, value: float) -> dict:
    return {key: value, f"{key}_bits": bits(value)}


# ======================================================================================
# The epochs — the interval's ends from the manifest given, never typed
# ======================================================================================


def julian_day(stamp: str) -> float:
    moment = datetime.datetime.fromisoformat(stamp)
    if moment.tzinfo is not None:
        raise Refusal(f"{stamp!r}: a civil instant here carries no zone")
    seconds = (moment - datetime.datetime(1970, 1, 1)).total_seconds()
    return UNIX_EPOCH_JD + seconds / SECONDS_PER_DAY


def civil(jd: float) -> str:
    moment = datetime.datetime(1970, 1, 1) + datetime.timedelta(days=jd - UNIX_EPOCH_JD)
    return moment.isoformat(timespec="seconds")


def read_interval(manifest: str) -> dict:
    """The one dataset's declared coverage, as Julian days, converted back and checked."""
    with open(manifest, "rb") as handle:
        raw = handle.read()
    document = tomllib.loads(raw.decode("utf-8"))
    identity = document.get("identity", {})
    datasets = document.get("pinned", {}).get("dataset", [])
    if len(datasets) != 1:
        raise Refusal(f"the manifest declares {len(datasets)} datasets; one coverage is needed")
    coverage = datasets[0].get("declared_coverage")
    if not isinstance(coverage, dict) or not {"start", "end", "scale"} <= set(coverage):
        raise Refusal("the manifest's dataset declares no complete coverage (start, end, scale)")
    start, end = julian_day(coverage["start"]), julian_day(coverage["end"])
    # ⛔ Converted back before use: a Julian day that does not return to the manifest's own string
    #    is not the manifest's interval.
    for stamp, jd in ((coverage["start"], start), (coverage["end"], end)):
        if civil(jd) != stamp:
            raise Refusal(f"{stamp!r} became JD {jd!r}, which converts back to {civil(jd)!r}")
    if not start < end:
        raise Refusal("the declared coverage does not run forward")
    return {
        "profile": f"{identity.get('name')}@{identity.get('version')}",
        "manifest_sha256": hashlib.sha256(raw).hexdigest(),
        "dataset": datasets[0].get("logical_id"),
        "declared_coverage": {k: coverage[k] for k in ("start", "end", "scale")},
        "start": start,
        "end": end,
    }


def year_epoch(year: int) -> float:
    return J2000 + (year - 2000) * 365.25


def edge_search_instants() -> tuple[float, float, float]:
    """The survey's edge search: its two ends, and the middle it also reads."""
    low, high = (julian_day(stamp) for stamp in EDGE_SEARCH)
    return low, (low + high) / 2.0, high


def build_epochs(interval: dict) -> list[dict]:
    """The interval's two ends, J2000, the survey's two outside years and its edge search's ends and middle."""
    start, end = interval["start"], interval["end"]
    epochs = []
    for label, stamp, jd in (("start", interval["declared_coverage"]["start"], start),
                             ("end", interval["declared_coverage"]["end"], end)):
        epochs.append({"epoch_id": f"supported_{label}_{stamp[:10].replace('-', '_')}", "jd": jd})
    epochs.append({"epoch_id": "j2000", "jd": J2000})
    for year in OUTSIDE_YEARS:
        epochs.append({"epoch_id": f"outside_{year}", "jd": year_epoch(year)})
    low, middle, high = edge_search_instants()
    for stamp, jd in ((EDGE_SEARCH[0], low), (EDGE_SEARCH[1], high)):
        epochs.append({"epoch_id": f"edge_search_{stamp[:10].replace('-', '_')}", "jd": jd})
    # ⚠ The search's middle is read wherever it falls, and gets an epoch of its own only where none is there
    #   already (measured: it is J2000). Only the years and the range's ends are outside by construction, and
    #   each is checked to be.
    if all(e["jd"] != middle for e in epochs):
        epochs.append({"epoch_id": "edge_search_middle", "jd": middle})
    epochs.sort(key=lambda e: e["jd"])
    for epoch in epochs:
        epoch["in_supported_interval"] = start <= epoch["jd"] <= end
        outside = epoch["epoch_id"].startswith(("outside_", "edge_search_")) and epoch["epoch_id"] != "edge_search_middle"
        if outside and epoch["in_supported_interval"]:
            raise Refusal(f"{epoch['epoch_id']} is inside the interval")
    if len({e["jd"] for e in epochs}) != len(epochs) or len({e["epoch_id"] for e in epochs}) != len(epochs):
        raise Refusal("two epochs share an instant or a name")
    return epochs


def universal_epochs(epochs: list[dict]) -> list[dict]:
    """The same instants, passed as universal-time Julian days: no in-interval flag, which is a TT reading."""
    return [{"epoch_id": e["epoch_id"], "jd": e["jd"]} for e in epochs]


# ======================================================================================
# The directories — refused unless exactly what they claim to be
# ======================================================================================


def verify_data_directory(path: str) -> None:
    names = sorted(os.listdir(path))
    expected = sorted(pin["dataset"] for pin in EPHE_PINS)
    if names != expected:
        raise Refusal(f"the data directory holds {names}, not exactly the pinned set {expected}")
    for pin in EPHE_PINS:
        with open(os.path.join(path, pin["dataset"]), "rb") as handle:
            content = handle.read()
        if len(content) != pin["size_bytes"] or hashlib.sha256(content).hexdigest() != pin["sha256"]:
            raise Refusal(f"{pin['dataset']} does not match its pin")


def verify_empty_directory(path: str) -> None:
    names = sorted(os.listdir(path))
    if names:
        raise Refusal(f"the empty directory holds {names}")


# ======================================================================================
# The child program — one call per fresh interpreter
# ======================================================================================


def _child(specs_json: str) -> None:
    fresh = "swisseph" not in sys.modules
    import swisseph as swe

    # ⭐ EVERY call into the library is recorded with the arguments it ACTUALLY received, here, in the child —
    #    each float as its bit pattern — so the parent can admit the child only if its whole call sequence is
    #    the one its row declares: the path, the constant read, the one reading call, the read-backs, and
    #    nothing else.
    calls: list[dict] = []

    def recorded(name: str, function):
        def call(*args, **keywords):
            calls.append({"function": name, "args": [bits(a) if isinstance(a, float) else a for a in args],
                          "keywords": sorted(keywords)})
            return function(*args, **keywords)
        return call

    def wrap(module, prefix: str) -> None:
        for name in dir(module):
            member = getattr(module, name)
            if name.startswith("_") or isinstance(member, type):
                continue
            if isinstance(member, types.ModuleType):
                # ⚠ The library's own submodules (``swisseph.contrib``) are wrapped too; any other module is not
                #   the library.
                if member.__name__.startswith(swe.__name__ + "."):
                    wrap(member, f"{prefix}{name}.")
            elif callable(member):
                setattr(module, name, recorded(prefix + name, member))

    wrap(swe, "")

    readings = []
    for spec in json.loads(specs_json):
        if spec["path"] is not None:
            swe.set_ephe_path(spec["path"])
        reading: dict = {}
        if spec["read_before"]:
            reading["tidal_constant_before_bits"] = bits(swe.get_tid_acc())
        if spec["entry_point"] == "deltat_ex":
            reading["delta_t_days_bits"] = bits(swe.deltat_ex(unbits(spec["jd_bits"]), spec["flags"]))
        else:
            call = swe.calc if spec["entry_point"] == "calc" else swe.calc_ut
            values, returned = call(unbits(spec["jd_bits"]), spec["body"], spec["flags"])
            reading.update(values_bits=[bits(float(v)) for v in values], returned=returned)
        reading["tidal_constant_after_bits"] = bits(swe.get_tid_acc())
        files = []
        for slot in (0, 1):
            file_path, first, last, denum = swe.get_current_file_data(slot)
            files.append({"ifno": slot, "file": os.path.basename(file_path) if file_path else "",
                          "start_bits": bits(first), "end_bits": bits(last), "denum": denum})
        reading["current_file_data_after"] = files
        readings.append(reading)
    sys.stdout.write(json.dumps({"nonce": os.urandom(16).hex(), "fresh_interpreter": fresh,
                                 "calls": calls, "readings": readings}))


def child_environment() -> dict[str, str]:
    return {k: v for k, v in os.environ.items() if not k.startswith("SE_")}


class Children:
    """Runs every child, and refuses any that was not one fresh reading."""

    def __init__(self, work: str) -> None:
        self.work = work
        self.nonces: set[str] = set()

    def run(self, specs: list[dict]) -> list[dict]:
        proc = subprocess.run(
            [sys.executable, "-I", os.path.abspath(__file__), "--child", json.dumps(specs)],
            cwd=self.work, env=child_environment(), capture_output=True, text=True,
            timeout=CHILD_TIMEOUT_SECONDS, check=False,
        )
        if proc.returncode != 0:
            raise Refusal(f"a child failed ({proc.returncode}): {proc.stderr[-400:]}")
        result = json.loads(proc.stdout)
        # ⛔ A reading described as cold that was not. One child, one reading, one interpreter.
        if len(result["readings"]) != 1 or not result["fresh_interpreter"]:
            raise Refusal(f"a child took {len(result['readings'])} readings "
                          f"(fresh interpreter: {result['fresh_interpreter']}); every reading is one "
                          "call in a fresh child process")
        if result["nonce"] in self.nonces:
            raise Refusal("two readings came back from one child")
        self.nonces.add(result["nonce"])
        return [{**result["readings"][0], "calls": result["calls"]}]

    def take_all(self, specs: list[dict]) -> list[dict]:
        """One child per spec; what each child's calls were is judged against its finished row (`admit`)."""
        return [reading for spec in specs for reading in self.run([spec])]


def admit(row: dict, calls: list[dict], paths: dict[str, str | None]) -> dict:
    """⛔ The FINISHED row's declared sequence against the calls its child made — after the row is built, so a
    defect in building one of the fields the sequence derives from is judged too."""
    want = declared_calls(row, paths)
    if calls != want:
        made = [c["function"] for c in calls]
        raise Refusal(f"the child's calls were {made} {calls}; the row declares {want}")
    return row


def _call(function: str, *args) -> dict:
    return {"function": function, "args": list(args), "keywords": []}


def declared_calls(row: dict, paths: dict[str, str | None]) -> list[dict]:
    """The whole call sequence a row says its child made, from the row's own fields: the path for its path
    state, the constant read before (reading rows only), the one reading call — entry point, instant, body,
    whole flag word — and the read-backs."""
    calls = []
    if paths[row["path_state"]] is not None:
        calls.append(_call("set_ephe_path", paths[row["path_state"]]))
    if row["finding"] != "returned_flag_by_body":
        calls.append(_call("get_tid_acc"))
    if row["entry_point"] == "deltat_ex":
        calls.append(_call("deltat_ex", row["jd_bits"], row["requested"]))
    else:
        calls.append(_call(row["entry_point"], row["jd_bits"], row["body"], row["requested"]))
    return calls + [_call("get_tid_acc"), _call("get_current_file_data", 0), _call("get_current_file_data", 1)]


# ======================================================================================
# The parent — chooses each child's request, records what came back
# ======================================================================================


def spec_for(*, path: str | None, flags: int, entry_point: str, jd: float, body: int | None = None,
             read_before: bool = True) -> dict:
    return {"path": path, "flags": flags, "entry_point": entry_point, "body": body,
            "jd_bits": bits(jd), "read_before": read_before}


def values_from(reading: dict) -> dict:
    """Every returned value, positionally — and the first three under the consumer's names for them."""
    values = [unbits(b) for b in reading["values_bits"]]
    out: dict = {}
    for name, value in zip(READER_FIELDS, values):
        out.update(patterned(name, value))
    out["values"] = values
    out["values_bits"] = list(reading["values_bits"])
    return out


def row_from(reading: dict, base: dict) -> dict:
    row = dict(base)
    if "tidal_constant_before_bits" in reading:
        row.update(patterned("tidal_constant_before", unbits(reading["tidal_constant_before_bits"])))
    row.update(patterned("tidal_constant_after", unbits(reading["tidal_constant_after_bits"])))
    if "delta_t_days_bits" in reading:
        row.update(patterned("delta_t_days", unbits(reading["delta_t_days_bits"])))
    else:
        row["returned"] = reading["returned"]
        row.update(values_from(reading))
    row["current_file_data_after"] = [
        {"ifno": f["ifno"], "file": f["file"], **patterned("start", unbits(f["start_bits"])),
         **patterned("end", unbits(f["end_bits"])), "denum": f["denum"]}
        for f in reading["current_file_data_after"]
    ]
    return row


def measure(ephe_path: str, empty_dir: str, profile: str, work: str) -> tuple[list[dict], dict]:
    import swisseph as swe

    flag = {name: getattr(swe, constant) for name, constant in EPHEMERIS_NAMES}
    nonut = swe.FLG_NONUT
    words = (("default", 0), ("nonut", nonut))
    subject = swe.ECL_NUT
    paths = {"data_files": os.path.abspath(ephe_path), "empty_directory": os.path.abspath(empty_dir)}
    configurations = {name: (eph, state) for name, eph, state in CONFIGURATIONS}
    interval = read_interval(profile)
    epochs = build_epochs(interval)
    by_id = {e["epoch_id"]: e for e in epochs}
    universal = universal_epochs(epochs)
    children = Children(work)
    rows: list[dict] = []

    def item(part: str, configuration: str, nutation: str, entry_point: str, epoch: dict,
             requested: int) -> tuple[dict, dict]:
        eph, state = configurations[configuration]
        offset = entry_point == "deltat_ex"
        spec = spec_for(path=paths[state], flags=requested, entry_point=entry_point, jd=epoch["jd"],
                        body=None if offset else subject)
        base: dict = {"finding": "delta_t_reading" if offset else "nutation_obliquity_reading", "part": part,
                      "configuration": configuration, "ephemeris_requested": eph, "path_state": state,
                      "nutation": nutation, "entry_point": entry_point}
        if not offset:
            base["body"] = subject
        base["epoch_id"] = epoch["epoch_id"]
        base.update(patterned("jd", epoch["jd"]))
        if "in_supported_interval" in epoch:
            base["in_supported_interval"] = epoch["in_supported_interval"]
        base["requested"] = requested
        return base, spec

    def read(items: list[tuple[dict, dict]]) -> list[dict]:
        taken = children.take_all([s for _, s in items])
        return [admit(row_from(reading, base), reading["calls"], paths)
                for (base, _spec), reading in zip(items, taken, strict=True)]

    # ---- 1. mode_invariance: calc, a dynamical-time day
    rows += read([item("mode_invariance", configuration, nutation, "calc", epoch, flag[eph] | extra)
                  for configuration, (eph, _state) in configurations.items()
                  for nutation, extra in words
                  for epoch in epochs])

    # ---- 2. universal_time: calc_ut; deltat_ex under the ephemeris bits alone; calc at UT + that offset
    for configuration, (eph, _state) in configurations.items():
        rows += read([item("universal_time", configuration, nutation, "calc_ut", epoch, flag[eph] | extra)
                      for nutation, extra in words
                      for epoch in universal])
        offsets = read([item("universal_time", configuration, "ephemeris_bits_only", "deltat_ex", epoch, flag[eph])
                        for epoch in universal])
        rows += offsets
        shifted = [{"epoch_id": f"{epoch['epoch_id']}_plus_delta_t", "jd": epoch["jd"] + offset["delta_t_days"]}
                   for epoch, offset in zip(universal, offsets, strict=True)]
        rows += read([item("universal_time", configuration, nutation, "calc", epoch, flag[eph] | extra)
                      for nutation, extra in words
                      for epoch in shifted])

    # ---- 3. returned_flag_by_body — the discriminating control
    bodies = ((swe.MOON, "moon"), (subject, "nutation_obliquity"))
    flag_items = []
    for condition in CONDITIONS:
        epoch = by_id[condition["epoch"]]
        for nutation, extra in words:
            requested = flag[condition["ephemeris"]] | extra
            for entry_point in ("calc", "calc_ut"):
                for body, body_label in bodies:
                    base = {"finding": "returned_flag_by_body", "condition": condition["condition"],
                            "built_to_substitute": condition["built_to_substitute"],
                            "ephemeris_requested": condition["ephemeris"], "path_state": condition["path_state"],
                            "nutation": nutation, "entry_point": entry_point, "body": body,
                            "body_label": body_label, "body_name": swe.get_planet_name(body),
                            "epoch_id": epoch["epoch_id"], **patterned("jd", epoch["jd"]), "requested": requested}
                    spec = spec_for(path=paths[condition["path_state"]], flags=requested, entry_point=entry_point,
                                    jd=epoch["jd"], body=body, read_before=False)
                    flag_items.append((base, spec))
    taken = children.take_all([s for _, s in flag_items])
    for (base, _spec), reading in zip(flag_items, taken, strict=True):
        returned = reading["returned"]
        rows.append(admit({**base, "returned": returned,
                           "substitution_reported": (returned & EPHEMERIS_MASK) != (base["requested"] & EPHEMERIS_MASK),
                           **values_from(reading),
                           **patterned("tidal_constant_after", unbits(reading["tidal_constant_after_bits"]))},
                          reading["calls"], paths))

    context = {"interval": interval, "epochs": epochs, "universal": universal, "nonut": nonut,
               "children": len(children.nonces), "conditions": CONDITIONS, "flag": flag,
               "bodies": {label: body for body, label in bodies},
               "body_names": {body: swe.get_planet_name(body) for body, _label in bodies}}
    return rows, context


# ======================================================================================
# The controls a record must pass before it is written
# ======================================================================================


def _arcseconds(a_degrees: float, b_degrees: float) -> float:
    return abs(a_degrees - b_degrees) * ARCSECONDS_PER_DEGREE


def check(rows: list[dict], context: dict) -> dict:
    """The record's own controls. Returns the summary; raises Refusal on any that fails."""
    nonut = context["nonut"]
    subject = context["bodies"]["nutation_obliquity"]
    readings = [r for r in rows if r["finding"] in ("nutation_obliquity_reading", "delta_t_reading")]
    flags = [r for r in rows if r["finding"] == "returned_flag_by_body"]
    if context["children"] != len(rows):
        raise Refusal(f"{len(rows)} readings from {context['children']} children")

    # ⛔ Held, each to what it names: a reading's finding and part to its entry point; its part to its epochs;
    #    its ephemeris label to its word's bits; its configuration or condition to the table that defines it;
    #    its nutation label to its word's nutation bit; a reading's body to the pseudo-body, and an offset
    #    reading to no body; a body label and a body name to the body; an epoch name to its instant and
    #    in-interval flag; the three named values to the call's first three returned values.
    parts = {"mode_invariance": ("calc",), "universal_time": ("calc_ut", "deltat_ex", "calc")}
    configurations = {name: (eph, state) for name, eph, state in CONFIGURATIONS}
    conditions = {c["condition"]: c for c in context["conditions"]}
    instants = {e["epoch_id"]: e for e in context["epochs"]}
    universal = {e["epoch_id"]: e for e in context["universal"]}
    offsets = {(r["configuration"], r["epoch_id"]): r for r in readings if r["entry_point"] == "deltat_ex"}
    for row in rows:
        if context["flag"][row["ephemeris_requested"]] != row["requested"] & EPHEMERIS_MASK:
            raise Refusal(f"a row labelled {row['ephemeris_requested']} requested {row['requested']}")
        word, label = row["requested"], row["nutation"]
        if (label, bool(word & nonut), word == word & EPHEMERIS_MASK) not in (
                ("default", False, True), ("nonut", True, False), ("ephemeris_bits_only", False, True)) or (
                label != "ephemeris_bits_only") == (row["entry_point"] == "deltat_ex"):
            raise Refusal(f"a row labelled {label} through {row['entry_point']} requested {word}")
        if row["entry_point"] != "deltat_ex":
            values = row["values_bits"]
            if len(values) != len(VALUE_POSITIONS) or [row[f"{n}_bits"] for n in READER_FIELDS] != values[:3]:
                raise Refusal(f"a {row['entry_point']} row's named values are not the call's first three of "
                              f"{len(values)}")
        if row["finding"] == "returned_flag_by_body":
            condition = conditions.get(row["condition"], {})
            named = tuple(condition.get(k) for k in ("ephemeris", "path_state", "epoch", "built_to_substitute"))
            if named != (row["ephemeris_requested"], row["path_state"], row["epoch_id"], row["built_to_substitute"]):
                raise Refusal(f"a row named {row['condition']} is not that condition")
            if context["bodies"].get(row["body_label"]) != row["body"]:
                raise Refusal(f"a row labelled {row['body_label']} read body {row['body']}")
            if row["body_name"] != context["body_names"].get(row["body"]):
                raise Refusal(f"a row naming body {row['body']} {row['body_name']!r}")
            epoch = instants.get(row["epoch_id"])
        else:
            filed = "delta_t_reading" if row["entry_point"] == "deltat_ex" else "nutation_obliquity_reading"
            if row["finding"] != filed or row["entry_point"] not in parts[row["part"]]:
                raise Refusal(f"a {row['entry_point']} reading filed as {row['finding']} in part {row['part']}")
            if filed == "nutation_obliquity_reading" and row["body"] != subject:
                raise Refusal(f"a nutation_obliquity_reading read body {row['body']}")
            if filed == "delta_t_reading" and "body" in row:
                raise Refusal(f"a delta_t_reading carries body {row['body']}")
            if configurations.get(row["configuration"]) != (row["ephemeris_requested"], row["path_state"]):
                raise Refusal(f"a row named {row['configuration']} is not that configuration")
            # ⭐ a part is its epochs: the calc epochs for the first; the universal ones, or one shifted by its
            #    own configuration's offset and read through calc, for the second
            shifted = row["epoch_id"].endswith("_plus_delta_t")
            if row["part"] == "mode_invariance":
                epoch = instants.get(row["epoch_id"])
            elif shifted and row["entry_point"] == "calc":
                ut = universal.get(row["epoch_id"].removesuffix("_plus_delta_t"))
                offset = None if ut is None else offsets.get((row["configuration"], ut["epoch_id"]))
                epoch = None if offset is None else {"jd": ut["jd"] + offset["delta_t_days"]}
            elif not shifted and row["entry_point"] != "calc":
                epoch = universal.get(row["epoch_id"])
            else:
                epoch = None
            if epoch is None:
                raise Refusal(f"a reading in part {row['part']} at {row['epoch_id']} is not that part's")
        if epoch is None or bits(epoch["jd"]) != row["jd_bits"] or row.get("in_supported_interval",
                                                           epoch.get("in_supported_interval")) != epoch.get("in_supported_interval"):
            raise Refusal(f"a row named {row['epoch_id']} is not that instant")

    # ⛔ A returned word no reading through the same entry point requested could not be read by a reader that
    #    looks words up through the requests, and would be refused for the body under every word.
    requested = {(r["entry_point"], r["requested"]): r["ephemeris_requested"] for r in rows}
    for row in rows:
        if "returned" not in row:
            continue
        source = requested.get((row["entry_point"], row["returned"]))
        if source is None or context["flag"][source] != row["returned"] & EPHEMERIS_MASK:
            raise Refusal(f"a {row['entry_point']} reading returned word {row['returned']}, which no reading "
                          "through that entry point requested under the source its bits name")

    # ⛔ NONUT, measured: every nonut reading has a default twin under the same configuration and instant.
    values = [r for r in readings if r["finding"] == "nutation_obliquity_reading"]
    pairs: dict[tuple, dict[str, dict]] = {}
    for row in values:
        pairs.setdefault((row["part"], row["entry_point"], row["configuration"], row["epoch_id"]), {})[row["nutation"]] = row
    equal_at = [0] * len(VALUE_POSITIONS)
    for key, pair in pairs.items():
        if set(pair) != {"default", "nonut"}:
            raise Refusal(f"{key}: a reading under {sorted(pair)} alone has no twin under the other word")
        if pair["default"]["values_bits"] == pair["nonut"]["values_bits"]:
            raise Refusal(f"{key}: the NONUT request moved nothing; it was not applied")
        for i, (a, b) in enumerate(zip(pair["default"]["values_bits"], pair["nonut"]["values_bits"])):
            equal_at[i] += a == b

    # ⛔ The discriminating control: the Moon reports a substitution exactly where one was built.
    for row in flags:
        if row["body_label"] == "moon" and row["substitution_reported"] != row["built_to_substitute"]:
            raise Refusal(
                f"the Moon control did not fire under {row['condition']} through {row['entry_point']}: "
                f"requested {row['requested']}, returned {row['returned']}. A reader that cannot see a "
                "substitution reads an echo as agreement")

    return summarise(rows, context, values, pairs, equal_at)


def summarise(rows: list[dict], context: dict, values: list[dict], pairs: dict, equal_at: list[int]) -> dict:
    names = [c[0] for c in CONFIGURATIONS]
    subject_rows = [r for r in rows if r.get("body") == context["bodies"]["nutation_obliquity"]]

    def invariance(part: str, entry_point: str) -> dict:
        out = {}
        for nutation in ("default", "nonut"):
            mine = [r for r in values if (r["part"], r["entry_point"], r["nutation"]) == (part, entry_point, nutation)
                    and not r["epoch_id"].endswith("_plus_delta_t")]
            by_epoch: dict[str, dict[str, dict]] = {}
            for r in mine:
                by_epoch.setdefault(r["epoch_id"], {})[r["configuration"]] = r
            one = [e for e, rs in by_epoch.items() if len({tuple(r["values_bits"]) for r in rs.values()}) == 1]
            spread = {}
            for epoch_id, rs in by_epoch.items():
                spread[epoch_id] = [round(max(_arcseconds(a["values"][i], b["values"][i])
                                              for a in rs.values() for b in rs.values()), 9)
                                    for i in range(4)]
            out[nutation] = {
                "epochs_with_one_set_of_six_values_across_the_five_configurations": len(one),
                "of": len(by_epoch),
                "epochs_where_the_values_moved": sorted((e for e in by_epoch if e not in one),
                                                        key=lambda e: by_epoch[e][names[0]]["jd"]),
                "largest_spread_across_configurations_arcseconds_positions_0_to_3": spread,
                "returned_word_by_configuration": {c: sorted({r["returned"] for r in mine if r["configuration"] == c})
                                                   for c in names},
            }
        return out

    universal = [r for r in values if r["part"] == "universal_time"]
    at_ut = {(r["configuration"], r["nutation"], r["epoch_id"]): r for r in universal if r["entry_point"] == "calc_ut"}
    shifted = {(r["configuration"], r["nutation"], r["epoch_id"].removesuffix("_plus_delta_t")): r
               for r in universal if r["entry_point"] == "calc"}
    identical = sum(1 for k, r in at_ut.items() if r["values_bits"] == shifted[k]["values_bits"])

    nonut_rows = [r for r in subject_rows if r["nutation"] == "nonut" and "values" in r]
    first_equals_second = sum(1 for r in nonut_rows if r["values_bits"][0] == r["values_bits"][1])
    third_and_fourth_zero = sum(1 for r in nonut_rows if r["values"][2] == 0.0 and r["values"][3] == 0.0)

    edge_ids = [e["epoch_id"] for e in context["epochs"] if e["jd"] in edge_search_instants()]
    edge_rows = [r for r in values if r["configuration"] == "swiss_file_present" and r["epoch_id"] in edge_ids]
    answered = sum(1 for r in edge_rows if r["returned"] & EPHEMERIS_MASK == r["requested"] & EPHEMERIS_MASK)

    echoed = sum(1 for r in subject_rows if r["returned"] == r["requested"])

    discrimination = {}
    for condition in context["conditions"]:
        entry = {"built_to_substitute": condition["built_to_substitute"]}
        for row in rows:
            if row["finding"] == "returned_flag_by_body" and row["condition"] == condition["condition"]:
                entry[f"{row['entry_point']}_{row['body_label']}_{row['nutation']}_substitution_reported"] = (
                    row["substitution_reported"])
        discrimination[condition["condition"]] = entry

    return {
        "readings": len(rows),
        "children": context["children"],
        "rows_by_part": {part: sum(1 for r in rows if r.get("part") == part)
                         for part in ("mode_invariance", "universal_time")}
        | {"returned_flag_by_body": sum(1 for r in rows if r["finding"] == "returned_flag_by_body")},
        "body": context["bodies"]["nutation_obliquity"],
        "body_name": context["body_names"][context["bodies"]["nutation_obliquity"]],
        "value_positions": {
            "documented_as": list(VALUE_POSITIONS),
            "documented_in": VALUE_POSITIONS_SOURCE,
            "reader_fields": {name: i for i, name in enumerate(READER_FIELDS)},
            "meaning": "every reading carries all six returned values in `values`, and the first three again "
                       "under the consumer's names for a reading's first three returned values, whatever the "
                       "body. ⚠ Those names are not what the values are: position 0 is no longitude. ⚠ "
                       "Position 3 is in no named field",
        },
        "returned_word": {
            "readings_of_the_body": len(subject_rows),
            "returned_exactly_the_requested_word": echoed,
            "of_which_built_to_substitute": sum(1 for r in subject_rows if r.get("built_to_substitute")
                                                and r["returned"] == r["requested"]),
            "built_to_substitute": sum(1 for r in subject_rows if r.get("built_to_substitute")),
        },
        "mode_invariance": invariance("mode_invariance", "calc"),
        "universal_time": {
            **invariance("universal_time", "calc_ut"),
            "calc_ut_identical_to_calc_at_ut_plus_delta_t": identical,
            "of": len(at_ut),
        },
        "nonut": {
            "pairs": len(pairs),
            "pairs_bit_identical_at_position": equal_at,
            "nonut_readings_of_the_body": len(nonut_rows),
            "position_0_bit_identical_to_position_1": first_equals_second,
            "positions_2_and_3_both_zero": third_and_fourth_zero,
        },
        "edge": {
            "search_epochs": edge_ids,
            "readings": len(edge_rows),
            "returned_the_requested_source": answered,
            "measured_edge": None,
            "meaning": ("the data-file request, the pinned files on the path, at both ends of the range the "
                        "survey searches for a body's edge and at its middle, through both entry points and "
                        "under both words: where every one of these returned the requested source, no edge "
                        "is located inside the range by the returned word"),
        } if answered == len(edge_rows) else {
            "search_epochs": edge_ids,
            "readings": len(edge_rows),
            "returned_the_requested_source": answered,
            "measured_edge": "not located here: the returned word named another source at some search instant",
        },
        "returned_flag_by_body": discrimination,
    }


# ======================================================================================
# The record
# ======================================================================================


def source_commit() -> str:
    """The clean commit this script is at. ⛔ Refused on a dirty or commitless tree."""
    here = os.path.dirname(os.path.realpath(__file__))

    def git(*args: str, cwd: str = here) -> str:
        proc = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=False)
        if proc.returncode != 0:
            raise Refusal(f"git {' '.join(args)}: {proc.stderr.strip()[:200]}")
        return proc.stdout

    top = os.path.realpath(git("rev-parse", "--show-toplevel").strip())
    status = git("status", "--porcelain", "--untracked-files=all", cwd=top)
    if status.strip():
        raise Refusal("the working tree is dirty; generator.commit would name a state that does not "
                      "exist. Commit the generator, then generate:\n" + status[:800])
    script = os.path.relpath(os.path.realpath(__file__), top).replace(os.sep, "/")
    if script != SCRIPT:
        raise Refusal(f"this script is {script}, not {SCRIPT}")
    git("ls-files", "--error-unmatch", "--", script, cwd=top)
    return git("rev-parse", "HEAD", cwd=top).strip()


ROW_SCHEMA = {
    "finding": "nutation_obliquity_reading | delta_t_reading | returned_flag_by_body",
    "part": "mode_invariance | universal_time",
    "configuration": "which ephemeris was requested and which directory was on the path",
    "ephemeris_requested": "moshier | swiss_file | jpl_file -- the source the request names",
    "path_state": "data_files (exactly the pinned set) | empty_directory (verified empty)",
    "nutation": "default (no non-ephemeris bit requested) | nonut (FLG_NONUT and nothing else) | "
                "ephemeris_bits_only (deltat_ex: only the configuration's ephemeris bits are passed)",
    "entry_point": "the library function called",
    "body": "the library's own body integer (a delta_t_reading has none)",
    "epoch_id": "which instant; the Julian day passed is `jd`, and `jd_bits` is that value. ⚠ calc receives "
                "it as dynamical time, calc_ut and deltat_ex as universal time; `_plus_delta_t` marks a calc "
                "reading at a universal instant plus its own configuration's deltat_ex",
    "in_supported_interval": "for a mode_invariance reading: whether the instant lies inside the data "
                             "profile's declared coverage",
    "requested": "⭐ the WHOLE flag word passed, every bit of it",
    "returned": "the whole flag word the call returned",
    "tidal_constant_before": "the tidal-acceleration constant in force before the call, read from the library",
    "tidal_constant_after": "the same, read after the call",
    "values": "⭐ all six values the call returned, in the order returned; `values_bits` are the values, the "
              "decimals are display. What the documentation calls each is in summary.value_positions",
    "longitude": "⚠ the call's FIRST returned value, under the name the consumer reads a reading's first "
                 "value by, whatever the body -- for this body ⛔ not a longitude; `longitude_bits` is the value",
    "latitude": "⚠ the call's second returned value, under the consumer's name for it -- ⛔ not a latitude",
    "distance": "⚠ the call's third returned value, under the consumer's name for it -- ⛔ not a distance",
    "delta_t_days": "what deltat_ex returned, in days",
    "current_file_data_after": "⚠ what the library reports about its open files after the call, file name "
                               "only -- recorded, never interpreted and never relied on",
    "condition": "returned_flag_by_body: the condition built",
    "built_to_substitute": "⭐ whether the condition was built so that the requested ephemeris cannot answer",
    "body_label": "returned_flag_by_body: which of the two bodies",
    "body_name": "the library's own name for the body, exactly as it returns it (the pseudo-body's is summary.body_name)",
    "substitution_reported": "⭐ whether the returned word's ephemeris bits differ from the requested word's",
}


def notes(summary: dict) -> list[str]:
    """The record's notes. ⭐ Each finding is stated from the summary it is about, never typed beside it."""
    words = summary["returned_word"]
    echo = words["returned_exactly_the_requested_word"] == words["readings_of_the_body"]
    calc = summary["mode_invariance"]
    calc_still = all(calc[n]["epochs_with_one_set_of_six_values_across_the_five_configurations"] == calc[n]["of"]
                     for n in ("default", "nonut"))
    ut = summary["universal_time"]
    moved = sorted({e for n in ("default", "nonut") for e in ut[n]["epochs_where_the_values_moved"]})
    nonut = summary["nonut"]
    out = [
        "⛔ A PROVENANCE RECORD, AND IT GATES NOTHING. It states what was observed and compares nothing: no "
        "tolerance, no reference value, no verdict. It is written before any rule that might use it is "
        "decided, so that the rule is written from the measurement rather than the other way round.",
        ("⭐ THE PSEUDO-BODY'S RETURNED WORD ECHOES THE REQUEST. In every one of its "
         f"{words['readings_of_the_body']} readings, the {words['built_to_substitute']} under a condition built so "
         "that the requested ephemeris cannot answer among them, it returned exactly the word it was handed, "
         "through calc and through calc_ut alike, while the Moon's returned word reported the substitution under "
         "the same conditions. So for this body the returned word does not distinguish the ephemeris that "
         "answered from the one requested." if echo else
         f"⭐ THE PSEUDO-BODY'S RETURNED WORD was the requested word in {words['returned_exactly_the_requested_word']} "
         f"of its {words['readings_of_the_body']} readings (summary.returned_word)."),
        ("⭐ THROUGH calc ITS SIX VALUES DID NOT MOVE with the requested ephemeris or the data-file state, at "
         "every epoch, under both words, the epochs outside the data files' coverage included "
         "(summary.mode_invariance)." if calc_still else
         "⭐ THROUGH calc ITS VALUES MOVED with the configuration at "
         + ", ".join(sorted({e for n in ("default", "nonut") for e in calc[n]["epochs_where_the_values_moved"]}))
         + " (summary.mode_invariance)."),
        "⭐ THROUGH calc_ut THEY " + (("MOVED at " + ", ".join(moved)) if moved else "DID NOT MOVE")
        + f", and calc_ut was bit-identical to calc at the universal day plus deltat_ex's offset under the same "
        f"ephemeris bits in {ut['calc_ut_identical_to_calc_at_ut_plus_delta_t']} of {ut['of']} readings "
        "(summary.universal_time) -- recorded as numbers, ⛔ not as a mechanism.",
        f"⚠ NONUT DECIDES THE VALUES. Every one of {nonut['pairs']} nonut readings differs from its default twin "
        "under the same configuration and instant, and the record refuses to exist if any pair agrees. Under "
        f"FLG_NONUT, position 0 was bit-identical to position 1 in {nonut['position_0_bit_identical_to_position_1']} "
        f"of {nonut['nonut_readings_of_the_body']} readings, and positions 2 and 3 were both zero in "
        f"{nonut['positions_2_and_3_both_zero']} (summary.nonut) -- numbers, ⛔ not a mechanism.",
        "⚠ THE THREE NAMED VALUES ARE POSITIONS, NOT QUANTITIES. Every reading writes the call's first three "
        "returned values under the names its consumer reads a reading's first three values by, held equal to "
        "them bit for bit; for this body position 0 is no longitude, and position 3 is in no named field "
        "(summary.value_positions).",
        "⚠ Not measured: sidereal mode, FLG_SPEED (a word carrying it is outside the two labels a reading here "
        "may carry), any other entry point, any other library version or host. Every reading is the one call "
        "of a fresh process, and a child whose recorded library calls are other than its row declares is "
        "refused.",
        "⚠ Dated, versioned and placed deliberately. This is an observation of one release through one "
        "binding on one machine, not a claim about the software in general.",
    ]
    return out


def build_record(rows: list[dict], context: dict, summary: dict, commit: str) -> list[str]:
    import swisseph as swe

    try:
        binding_version = _distribution_version("pyswisseph")
    except PackageNotFoundError:
        binding_version = None
    interval = context["interval"]
    today = datetime.datetime.now(datetime.timezone.utc).date().isoformat()
    header = {
        "record": "header",
        "schema_version": SCHEMA_VERSION,
        "fixture_kind": "provenance_record",
        "reference": "R3",
        "generator": {"repo": REPO, "script": SCRIPT, "commit": commit},
        "generated": today,
        "oracle": {
            "implementation": "Swiss Ephemeris",
            "library_version": swe.version,
            "called_via": {"binding": "pyswisseph", "version": binding_version},
            "session": {
                "isolation": "⛔ every reading is one call in a fresh child interpreter (-I); the children run "
                             "in an empty working directory that is not the parent's, verified empty after the "
                             "run; the parent takes no reading",
                "why": "the library keeps process-wide state, and a reading taken after another call "
                       "reports that call's state as well as its own",
                "checked": "every call each child made through the callables of the library module and of its "
                           "submodule (its classes are not wrapped), after they were wrapped, was recorded inside "
                           "the child with the arguments it actually received, and the whole sequence is the one "
                           "its finished row declares: the directory for its path state, the constant read, "
                           "exactly one reading call with the row's entry point, instant, body and whole flag "
                           "word, and the read-backs -- nothing else; held, each to what it names: a reading's "
                           "finding and part to its entry point, its part to its epochs, its ephemeris label to "
                           "its word's bits, its configuration or condition to the table defining it, its "
                           "nutation label to its word's nutation bit, a reading's body to the pseudo-body and an "
                           "offset reading to no body, a body label and name to the body, an epoch name to its "
                           "instant and in-interval flag, the three named values to the call's first three "
                           "returned values; each child started from an interpreter that had not loaded the "
                           "library and returned one reading, and no two readings came from one child. ⚠ "
                           "Honest error, not forgery: a reference to the library bound before the wrapping, its "
                           "compiled extension reached another way, or a call through one of its classes is "
                           "outside the record; and a row field neither the call sequence nor these pairs read "
                           "is held by nothing here",
                "removed_environment_variables": sorted(k for k in os.environ if k.startswith("SE_")),
            },
            "licence": "the library is AGPL-3.0; it is called here, never redistributed by this repository",
            "host": {"python": sys.version.split()[0], "platform": platform.platform(),
                     "machine": platform.machine()},
            "data_files": {
                "directory_contents_verified": True,
                "files": [dict(pin) for pin in EPHE_PINS],
                "unpinned_file_policy": "refused. The library reads the directory, so a file nobody passed "
                                        "can still answer",
            },
            "empty_directory": {"verified_empty": True,
                                "checked": "before the first reading and after the last, as the data directory"},
            "method": "each entry point called under a declared configuration and what came back read: all "
                      "six returned values and the whole returned word, the tidal-acceleration constant before "
                      "and after the call, and the library's report of its open files",
        },
        "title": "What one release of the ephemeris library returns for its nutation and obliquity pseudo-body "
                 "under three ephemeris requests, two data-file states and both nutation settings, and what its "
                 "returned word says beside the Moon's",
        "attests": "a vendor_convention attestation: what this release of the ephemeris library returned for its "
                   "pseudo-body for nutation and obliquity through calc and calc_ut, under three ephemeris "
                   "requests, two data-file states and both nutation settings, with every returned value, the "
                   "whole requested and returned words, the tidal-acceleration constant read back, and the time "
                   "offset beside each universal-time call; and, beside the Moon's, what the pseudo-body's "
                   "returned word says when the requested ephemeris cannot answer",
        "authority": {
            "held_by": "the library itself, as observed",
            "kind": "black-box observation of return values under declared configurations, every reading in "
                    "a fresh process",
            "scope": "⚠ this version of the library and this binding only, run on the recorded host. A "
                     "later version, or the same version built for another machine, may return different "
                     "bits, which is why the observation is dated, versioned and placed rather than stated "
                     "as a property of the software in general",
        },
        "record_date": today,
        "row_schema": ROW_SCHEMA,
        "summary": {
            "epochs": {
                "source": "the interval's ends: a data profile manifest's declared coverage, read from the "
                          "file given and converted back to its own strings before use -- never a typed "
                          "Julian day. The other epochs are labelled instants and formulas written in the "
                          "generator, each the survey's own: J2000, the two years at which it reads a body "
                          "outside every measured edge, and the ends and middle of the range it searches for "
                          "a body's edge",
                "profile": interval["profile"],
                "manifest_sha256": interval["manifest_sha256"],
                "dataset": interval["dataset"],
                "declared_coverage": interval["declared_coverage"],
                **patterned("start_jd", interval["start"]),
                **patterned("end_jd", interval["end"]),
                "used_as": "Julian days passed to calc as dynamical time and to calc_ut as universal time; the "
                           "coverage's scale is TDB and its difference from TT, milliseconds, is not applied",
                "ids": [e["epoch_id"] for e in context["epochs"]],
                "count": len(context["epochs"]),
                "inside_the_interval": sum(1 for e in context["epochs"] if e["in_supported_interval"]),
            },
            **summary,
        },
        "notes": notes(summary),
    }
    lines = [json.dumps(header, ensure_ascii=True)]
    lines.extend(json.dumps({"record": "row", **row}, ensure_ascii=True) for row in rows)
    return lines


def generate(ephe_path: str, empty_dir: str, profile: str, out: str) -> str:
    """Measure, check and write. Returns the commit the record names."""
    commit = source_commit()
    if os.path.exists(out):
        raise Refusal(f"{out} exists; each emission goes to a new path")
    verify_data_directory(ephe_path)
    verify_empty_directory(empty_dir)
    work = tempfile.mkdtemp(prefix="nutation-obliquity-modes-")
    try:
        rows, context = measure(ephe_path, empty_dir, profile, work)
        verify_empty_directory(work)
    finally:
        shutil.rmtree(work, ignore_errors=True)
    verify_data_directory(ephe_path)
    verify_empty_directory(empty_dir)
    summary = check(rows, context)
    lines = build_record(rows, context, summary, commit)
    with open(out, "x", encoding="ascii", newline="\n") as handle:
        handle.write("\n".join(lines) + "\n")
    return commit


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if argv[:1] == ["--child"]:
        _child(argv[1])
        return 0
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--ephe-path", required=True, help="the pinned data files' directory, and nothing else")
    parser.add_argument("--empty-dir", required=True, help="an empty directory")
    parser.add_argument("--profile", required=True, help="the data profile manifest whose coverage sets the epochs")
    parser.add_argument("--out", required=True, help="the record to write; must not exist")
    args = parser.parse_args(argv)
    try:
        commit = generate(args.ephe_path, args.empty_dir, args.profile, args.out)
    except Refusal as refusal:
        sys.stderr.write(f"refused: {refusal}\n")
        return 2
    with open(args.out, "rb") as handle:
        digest = hashlib.sha256(handle.read()).hexdigest()
    sys.stderr.write(f"commit {commit}\nwrote {args.out}\nsha256 {digest}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
