"""The mean lunar node read under three ephemeris requests, two data-file states and both nutation settings.

What one release of the ephemeris library returns for its mean lunar node, read black-box, and what
its returned flag says beside the Moon's. One R3 ``provenance_record``, written only from a clean
commit.

Five parts, and ⛔ **every reading is one call in a fresh child process**:

1. **mode_invariance** — ``calc`` on a dynamical-time Julian day, under five configurations (the
   analytical, the data-file and the JPL request, with the pinned data files on the path and with a
   verified-empty directory; the JPL request with no JPL file anywhere), each with the library's
   default nutation and with ``FLG_NONUT``, at every epoch.
2. **cause** — ``calc``, NONUT, the analytical and the data-file request with the files present: the
   tidal-acceleration constant forced to two library-named values before the call, read back after.
3. **universal_time** — every configuration, NONUT, seven epochs: ``calc_ut``; ``deltat_ex`` under the
   same ephemeris bits; and ``calc`` at the universal day plus that offset.
4. **universal_time_cause** — part 2's forcing, through ``calc_ut``.
5. **returned_flag_by_body** — the discriminating control: seven conditions, five of them built so
   the requested ephemeris cannot answer, and the returned word of the Moon and of the node through
   ``calc`` and ``calc_ut``. ⛔ The record is refused unless the Moon reports the substitution
   exactly where one was built: a reader that cannot see a substitution reads an echo as agreement.

⛔ **Recorder, never explainer.** Nothing here describes how the library computes anything. A
relation between readings is recorded as numbers, never as a mechanism.

⛔ **The interval's ends are a data profile manifest's declared coverage**, read from the file given and
converted back to the manifest's own strings before use — never a Julian day typed here. They set every
epoch's in-interval flag, the window searched for crossings, the grid's first and last year, and the two
ends among the calc epochs and among the universal-time ones. ⚠ The other epochs are labelled instants and
formulas written here: a grid every five years at four times of day, J2000, four years outside the
interval, four civil dates. The instants where the node
passes 0°/360° are located with the published IERS Conventions (2010) Eq. (5.43) row for the fifth
Delaunay argument, used to FIND those instants and for nothing else.

⛔ **Refusals, each before anything is written**: a dirty or commitless working tree; a data directory
that is not exactly the pinned set; an "empty" directory that is not empty (both checked before and
after the run); a child that did not start from an interpreter without the library loaded, or returned
other than one reading, or whose output came back twice; ⭐ a child whose calls into the library — every
call made through the library module's callables and its submodule's after they are wrapped, recorded
inside the child with the arguments it actually received — are not exactly the sequence its FINISHED row
declares (the directory for its path state, its forced constant, the constant read, one reading call with
its entry point, instant, body and whole flag word, the read-backs); a row that breaks one of these pairs — a
reading's finding and part to its entry point, its part to its forced constant and epochs, its ephemeris label
to its word's bits, its configuration or condition to the table defining it, its nutation label to its word's
nutation bit, a forced constant's name to the library's value of that name, a node reading's body to the node
and an offset reading to no body, a body label and name to the body, an epoch name to its instant and
in-interval flag; a NONUT request that moved no reading; the Moon control not firing. ⚠ These guard honest error, ⛔ not forgery: a reference to the library bound before the wrapping, its
compiled extension reached another way, or a call through one of its classes (which are not wrapped) is outside
them; and a row field its call sequence does not derive from is judged only by the name checks above.

The standard library and the binding only, as ``utc_conversion.py``; ``git`` is called to read the
commit. Children run in an empty working directory that is not the parent's, with every ``SE_``
environment variable removed — the removal is recorded, never silent.

Usage::

    python mean_node_modes.py --ephe-path DIR --empty-dir DIR --profile MANIFEST --out FILE
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import math
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
SCRIPT = "generators/mean_node_modes.py"
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
#: 1970-01-01T00:00 as a Julian day — a definition, used to turn a manifest's ISO date into one.
UNIX_EPOCH_JD = 2440587.5
SECONDS_PER_DAY = 86400.0

#: ⚠ The published IERS Conventions (2010) Eq. (5.43) row for F5, arcseconds and powers of Julian
#: centuries of TT from J2000. ⛔ Used ONLY to locate instants near 0°/360° to sample — never a
#: statement about the library, never compared with anything it returns.
F5_ROW: tuple[float, ...] = (125.04455501 * 3600.0, -6962890.5431, 7.4722, 0.007702, -0.00005939)
#: Every fourth crossing is sampled, at the dyadic Julian day nearest it and six hours either side.
CROSSING_STRIDE = 4
DYADIC = 2.0**20
CROSSING_OFFSETS: tuple[tuple[float, str], ...] = ((0.0, "at"), (-0.25, "minus_6h"), (0.25, "plus_6h"))
#: A grid epoch every this many years across the interval, cycling through four times of day.
GRID_STEP_YEARS = 5
#: Years outside the interval, read on purpose: outside by construction, and checked to be.
OUTSIDE_YEARS: tuple[int, ...] = (1500, 1700, 2500, 3000)
#: Parts 3 and 4: the interval's ends, J2000, and these civil instants (0h), converted by the same
#: function as the manifest's.
UT_CIVIL: tuple[str, ...] = ("1900-01-01T00:00:00", "1950-01-01T00:00:00",
                            "2050-01-01T00:00:00", "2100-01-01T00:00:00")

#: The five configurations: the requested ephemeris and the directory on the path.
CONFIGURATIONS: tuple[tuple[str, str, str], ...] = (
    ("moshier_files_present", "moshier", "data_files"),
    ("moshier_dir_empty", "moshier", "empty_directory"),
    ("swiss_file_present", "swiss_file", "data_files"),
    ("swiss_file_dir_empty", "swiss_file", "empty_directory"),
    ("jpl_requested_no_jpl_file", "jpl_file", "data_files"),
)
#: Part 2 and 4's configurations, and the two library-named constants forced.
CAUSE_CONFIGURATIONS: tuple[str, ...] = ("moshier_files_present", "swiss_file_present")
FORCED: tuple[tuple[str, str], ...] = (("TIDAL_DE200", "forced_tidal_de200"), ("TIDAL_26", "forced_tidal_26"))

#: Part 5. `built_to_substitute`: the requested ephemeris is known not to be able to answer here.
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
    {"condition": "swiss_file_no_path_set", "ephemeris": "swiss_file", "path_state": "no_path_set",
     "epoch": "j2000", "built_to_substitute": True,
     "description": "the data-file request, no path set at all"},
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
# The epochs — derived from the manifest given, never typed
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


def f5_degrees(jd: float) -> float:
    t = (jd - J2000) / 36525.0
    return sum(c * t ** k for k, c in enumerate(F5_ROW)) / ARCSECONDS_PER_DEGREE


def crossings(start: float, end: float) -> list[float]:
    """Where the F5 row passes a multiple of 360° inside [start, end], by bisection."""
    first, last = math.floor(f5_degrees(end) / 360.0), math.floor(f5_degrees(start) / 360.0)
    found = []
    for k in range(first + 1, last + 1):
        a, b = start, end
        for _ in range(200):
            middle = 0.5 * (a + b)
            if f5_degrees(middle) > 360.0 * k:
                a = middle
            else:
                b = middle
        found.append(a)
    return found


def build_epochs(interval: dict) -> list[dict]:
    start, end = interval["start"], interval["end"]
    start_year = int(interval["declared_coverage"]["start"][:4])
    end_year = int(interval["declared_coverage"]["end"][:4])
    years = range(start_year + (-start_year) % GRID_STEP_YEARS, end_year - end_year % GRID_STEP_YEARS + 1,
                  GRID_STEP_YEARS)
    epochs = []
    for i, year in enumerate(years):
        # four genuine times of day: the integer Julian day (noon) plus 0, 6, 12 and 18 hours
        epochs.append({"epoch_id": f"grid_{year}", "jd": math.floor(year_epoch(year)) + 0.25 * (i % 4)})
    epochs.append({"epoch_id": "j2000", "jd": J2000})
    for label, stamp, jd in (("start", interval["declared_coverage"]["start"], start),
                             ("end", interval["declared_coverage"]["end"], end)):
        epochs.append({"epoch_id": f"supported_{label}_{stamp[:10].replace('-', '_')}", "jd": jd})
    for n, crossing in enumerate(crossings(start, end)[::CROSSING_STRIDE]):
        dyadic = round(crossing * DYADIC) / DYADIC
        for offset, tag in CROSSING_OFFSETS:
            epochs.append({"epoch_id": f"wrap{n}_{tag}", "jd": dyadic + offset})
    for year in OUTSIDE_YEARS:
        jd = year_epoch(year)
        if start <= jd <= end:
            raise Refusal(f"outside_{year} is inside the interval")
        epochs.append({"epoch_id": f"outside_{year}", "jd": jd})
    for epoch in epochs:
        epoch["in_supported_interval"] = start <= epoch["jd"] <= end
    if len({e["jd"] for e in epochs}) != len(epochs) or len({e["epoch_id"] for e in epochs}) != len(epochs):
        raise Refusal("two epochs share an instant or a name")
    return epochs


def universal_epochs(interval: dict) -> list[dict]:
    stamps = [interval["declared_coverage"]["start"], *UT_CIVIL[:2], None, *UT_CIVIL[2:],
              interval["declared_coverage"]["end"]]
    out = []
    for stamp in stamps:
        if stamp is None:
            out.append({"epoch_id": "ut_j2000", "jd": J2000})
        else:
            out.append({"epoch_id": f"ut_{stamp[:10].replace('-', '_')}", "jd": julian_day(stamp)})
    return out


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
    #    the one its row declares: the path, a forced constant, the constant read, the one reading call, the
    #    read-backs, and nothing else.
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
        if spec["forced_bits"] is not None:
            swe.set_tid_acc(unbits(spec["forced_bits"]))
        reading: dict = {}
        if spec["read_before"]:
            reading["tidal_constant_before_bits"] = bits(swe.get_tid_acc())
        if spec["entry_point"] == "deltat_ex":
            reading["delta_t_days_bits"] = bits(swe.deltat_ex(unbits(spec["jd_bits"]), spec["flags"]))
        else:
            call = swe.calc if spec["entry_point"] == "calc" else swe.calc_ut
            values, returned = call(unbits(spec["jd_bits"]), spec["body"], spec["flags"])
            reading.update(longitude_bits=bits(values[0]), latitude_bits=bits(values[1]),
                           distance_bits=bits(values[2]), returned=returned)
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
        # ⛔ MN-8: a reading described as cold that was not. One child, one reading, one interpreter.
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
        batches = [[spec] for spec in specs]
        return [reading for batch in batches for reading in self.run(batch)]


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
    state (none where no path is set), the forced constant it records, the constant read before (reading
    rows only), the one reading call — entry point, instant, body, whole flag word — and the read-backs."""
    calls = []
    if paths[row["path_state"]] is not None:
        calls.append(_call("set_ephe_path", paths[row["path_state"]]))
    if "forced_tidal_constant_bits" in row:
        calls.append(_call("set_tid_acc", row["forced_tidal_constant_bits"]))
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
             forced: float | None = None, read_before: bool = True) -> dict:
    return {"path": path, "flags": flags, "entry_point": entry_point, "body": body,
            "jd_bits": bits(jd), "forced_bits": None if forced is None else bits(forced),
            "read_before": read_before}


def row_from(reading: dict, base: dict) -> dict:
    row = dict(base)
    if "tidal_constant_before_bits" in reading:
        row.update(patterned("tidal_constant_before", unbits(reading["tidal_constant_before_bits"])))
    row.update(patterned("tidal_constant_after", unbits(reading["tidal_constant_after_bits"])))
    if "delta_t_days_bits" in reading:
        row.update(patterned("delta_t_days", unbits(reading["delta_t_days_bits"])))
    else:
        row["returned"] = reading["returned"]
        for key in ("longitude", "latitude", "distance"):
            row.update(patterned(key, unbits(reading[f"{key}_bits"])))
    row["current_file_data_after"] = [
        {"ifno": f["ifno"], "file": f["file"], **patterned("start", unbits(f["start_bits"])),
         **patterned("end", unbits(f["end_bits"])), "denum": f["denum"]}
        for f in reading["current_file_data_after"]
    ]
    return row


def wrapped_arcseconds(a_degrees: float, b_degrees: float) -> float:
    return ((a_degrees - b_degrees + 180.0) % 360.0 - 180.0) * ARCSECONDS_PER_DEGREE


def measure(ephe_path: str, empty_dir: str, profile: str, work: str) -> tuple[list[dict], dict]:
    import swisseph as swe

    flag = {name: getattr(swe, constant) for name, constant in EPHEMERIS_NAMES}
    nonut = swe.FLG_NONUT
    paths = {"data_files": os.path.abspath(ephe_path), "empty_directory": os.path.abspath(empty_dir),
             "no_path_set": None}
    configurations = {name: (eph, state) for name, eph, state in CONFIGURATIONS}
    interval = read_interval(profile)
    epochs = build_epochs(interval)
    by_id = {e["epoch_id"]: e for e in epochs}
    universal = universal_epochs(interval)
    children = Children(work)
    rows: list[dict] = []

    def item(part: str, configuration: str, nutation: str, entry_point: str, epoch: dict, requested: int,
             *, body: int | None, forced: tuple[str, float] | None = None) -> tuple[dict, dict]:
        eph, state = configurations[configuration]
        spec = spec_for(path=paths[state], flags=requested, entry_point=entry_point, jd=epoch["jd"],
                        body=body, forced=None if forced is None else forced[1])
        finding = "delta_t_reading" if entry_point == "deltat_ex" else "mean_node_reading"
        base: dict = {"finding": finding, "part": part, "configuration": configuration,
                      "ephemeris_requested": eph, "path_state": state, "nutation": nutation,
                      "entry_point": entry_point}
        if body is not None:
            base["body"] = body
        base["epoch_id"] = epoch["epoch_id"]
        base.update(patterned("jd", epoch["jd"]))
        if "in_supported_interval" in epoch:
            base["in_supported_interval"] = epoch["in_supported_interval"]
        base["requested"] = requested
        if forced is not None:
            base["forced_constant"] = forced[0]
            base.update(patterned("forced_tidal_constant", forced[1]))
        return base, spec

    def read(items: list[tuple[dict, dict]]) -> list[dict]:
        out = []
        taken = children.take_all([s for _, s in items])
        for (base, spec), reading in zip(items, taken, strict=True):
            if spec["forced_bits"] is not None:
                base["forced_held_after_call"] = reading["tidal_constant_after_bits"] == spec["forced_bits"]
            out.append(admit(row_from(reading, base), reading["calls"], paths))
        return out

    # ---- 1. mode_invariance
    rows += read([item("mode_invariance", configuration, nutation, "calc", epoch, flag[eph] | extra,
                       body=swe.MEAN_NODE)
                  for configuration, (eph, _state) in configurations.items()
                  for nutation, extra in (("default", 0), ("nonut", nonut))
                  for epoch in epochs])

    # ---- 2. cause, through calc: the interval's ends and J2000
    cause_epochs = sorted((e for e in epochs if e["epoch_id"] == "j2000"
                           or e["epoch_id"].startswith(("supported_start", "supported_end"))),
                          key=lambda e: e["jd"])
    rows += read([item("cause", configuration, "nonut", "calc", epoch, flag[configurations[configuration][0]] | nonut,
                       body=swe.MEAN_NODE, forced=(constant, getattr(swe, constant)))
                  for configuration in CAUSE_CONFIGURATIONS
                  for constant, _label in FORCED
                  for epoch in cause_epochs])

    # ---- 3. universal_time: calc_ut; deltat_ex under the ephemeris bits alone; calc at UT + that offset
    for configuration, (eph, _state) in configurations.items():
        word = flag[eph] | nonut
        rows += read([item("universal_time", configuration, "nonut", "calc_ut", epoch, word, body=swe.MEAN_NODE)
                      for epoch in universal])
        offsets = read([item("universal_time", configuration, "ephemeris_bits_only", "deltat_ex", epoch,
                             word & EPHEMERIS_MASK, body=None)
                        for epoch in universal])
        rows += offsets
        shifted = [{"epoch_id": f"{epoch['epoch_id']}_plus_delta_t", "jd": epoch["jd"] + offset["delta_t_days"]}
                   for epoch, offset in zip(universal, offsets, strict=True)]
        rows += read([item("universal_time", configuration, "nonut", "calc", epoch, word, body=swe.MEAN_NODE)
                      for epoch in shifted])

    # ---- 4. universal_time_cause
    rows += read([item("universal_time_cause", configuration, "nonut", "calc_ut", epoch,
                       flag[configurations[configuration][0]] | nonut, body=swe.MEAN_NODE,
                       forced=(constant, getattr(swe, constant)))
                  for configuration in CAUSE_CONFIGURATIONS
                  for constant, _label in FORCED
                  for epoch in universal])

    # ---- 5. returned_flag_by_body — the discriminating control
    bodies = ((swe.MOON, "moon"), (swe.MEAN_NODE, "mean_node"))
    flag_items = []
    for condition in CONDITIONS:
        epoch = by_id[condition["epoch"]]
        requested = flag[condition["ephemeris"]] | nonut
        for entry_point in ("calc", "calc_ut"):
            for body, body_label in bodies:
                base = {"finding": "returned_flag_by_body", "condition": condition["condition"],
                        "built_to_substitute": condition["built_to_substitute"],
                        "ephemeris_requested": condition["ephemeris"], "path_state": condition["path_state"],
                        "entry_point": entry_point, "body": body, "body_label": body_label,
                        "body_name": swe.get_planet_name(body), "epoch_id": epoch["epoch_id"],
                        **patterned("jd", epoch["jd"]), "requested": requested}
                spec = spec_for(path=paths[condition["path_state"]], flags=requested, entry_point=entry_point,
                                jd=epoch["jd"], body=body, read_before=False)
                flag_items.append((base, spec))
    taken = children.take_all([s for _, s in flag_items])
    for (base, _spec), reading in zip(flag_items, taken, strict=True):
        returned = reading["returned"]
        rows.append(admit({**base, "returned": returned,
                           "substitution_reported": (returned & EPHEMERIS_MASK) != (base["requested"] & EPHEMERIS_MASK),
                           **patterned("longitude", unbits(reading["longitude_bits"])),
                           **patterned("tidal_constant_after", unbits(reading["tidal_constant_after_bits"]))},
                          reading["calls"], paths))

    context = {"interval": interval, "epochs": epochs, "universal": universal, "nonut": nonut,
               "children": len(children.nonces), "conditions": CONDITIONS, "flag": flag,
               "forced": {name: bits(getattr(swe, name)) for name, _label in FORCED},
               "bodies": {label: body for body, label in bodies},
               "body_names": {body: swe.get_planet_name(body) for body, _label in bodies}}
    return rows, context


# ======================================================================================
# The controls a record must pass before it is written
# ======================================================================================


def check(rows: list[dict], context: dict) -> dict:
    """The record's own controls. Returns the summary; raises Refusal on any that fails."""
    nonut = context["nonut"]
    readings = [r for r in rows if r["finding"] in ("mean_node_reading", "delta_t_reading")]
    flags = [r for r in rows if r["finding"] == "returned_flag_by_body"]
    if context["children"] != len(rows):
        raise Refusal(f"{len(rows)} readings from {context['children']} children")

    # ⛔ Held, each to what it names: a reading's finding and part to its entry point; its part to its forced
    #    constant and its epochs; its ephemeris label to its word's bits; its configuration or condition to the
    #    table that defines it; its nutation label to its word's nutation bit; a forced constant's name to the
    #    library's value of that name; a node reading's body to the node, and an offset reading to no body; a
    #    body label and a body name to the body; an epoch name to its instant and in-interval flag.
    parts = {"mode_invariance": ("calc",), "cause": ("calc",), "universal_time": ("calc_ut", "deltat_ex", "calc"),
             "universal_time_cause": ("calc_ut",)}
    configurations = {name: (eph, state) for name, eph, state in CONFIGURATIONS}
    conditions = {c["condition"]: c for c in context["conditions"]}
    instants = {e["epoch_id"]: e for e in [*context["epochs"], *context["universal"]]}
    offsets = {(r["configuration"], r["epoch_id"]): r for r in readings if r["entry_point"] == "deltat_ex"}
    for row in rows:
        if context["flag"][row["ephemeris_requested"]] != row["requested"] & EPHEMERIS_MASK:
            raise Refusal(f"a row labelled {row['ephemeris_requested']} requested {row['requested']}")
        if row["finding"] != "returned_flag_by_body":
            filed = "delta_t_reading" if row["entry_point"] == "deltat_ex" else "mean_node_reading"
            if row["finding"] != filed or row["entry_point"] not in parts[row["part"]]:
                raise Refusal(f"a {row['entry_point']} reading filed as {row['finding']} in part {row['part']}")
            if filed == "mean_node_reading" and row["body"] != context["bodies"]["mean_node"]:
                raise Refusal(f"a mean_node_reading read body {row['body']}")
            if filed == "delta_t_reading" and "body" in row:
                raise Refusal(f"a delta_t_reading carries body {row['body']}")
            # ⭐ a part is its forced constant (present in the two cause parts alone) and its epochs (the calc
            #    epochs for the first two parts, the universal ones, or one shifted by an offset, for the others)
            universal_part = row["part"] in ("universal_time", "universal_time_cause")
            family = ({e["epoch_id"] for e in context["universal"]} if universal_part
                      else {e["epoch_id"] for e in context["epochs"]})
            if ("forced_constant" in row) != (row["part"] in ("cause", "universal_time_cause")) or (
                    row["epoch_id"].removesuffix("_plus_delta_t") not in family) or (
                    row["epoch_id"].endswith("_plus_delta_t") and row["entry_point"] != "calc"):
                raise Refusal(f"a reading in part {row['part']} at {row['epoch_id']} is not that part's")
        elif row["body_name"] != context["body_names"][row["body"]]:
            raise Refusal(f"a row naming body {row['body']} {row['body_name']!r}")
        if row["finding"] == "returned_flag_by_body":
            condition = conditions[row["condition"]]
            named = (condition["ephemeris"], condition["path_state"], condition["epoch"], condition["built_to_substitute"])
            if named != (row["ephemeris_requested"], row["path_state"], row["epoch_id"], row["built_to_substitute"]):
                raise Refusal(f"a row named {row['condition']} is not that condition")
            if context["bodies"][row["body_label"]] != row["body"]:
                raise Refusal(f"a row labelled {row['body_label']} read body {row['body']}")
        elif configurations[row["configuration"]] != (row["ephemeris_requested"], row["path_state"]):
            raise Refusal(f"a row named {row['configuration']} is not that configuration")
        if row["finding"] != "returned_flag_by_body":
            word, label = row["requested"], row["nutation"]
            if (label, bool(word & nonut), word == word & EPHEMERIS_MASK) not in (
                    ("default", False, True), ("nonut", True, False), ("ephemeris_bits_only", False, True)) or (
                    label != "ephemeris_bits_only") == (row["entry_point"] == "deltat_ex"):
                raise Refusal(f"a row labelled {label} through {row['entry_point']} requested {word}")
            if "forced_constant" in row and context["forced"][row["forced_constant"]] != row["forced_tidal_constant_bits"]:
                raise Refusal(f"a row naming {row['forced_constant']} forced {row['forced_tidal_constant_bits']}")
        epoch = instants.get(row["epoch_id"])
        if epoch is None:
            ut = instants[row["epoch_id"].removesuffix("_plus_delta_t")]
            offset = offsets[(row["configuration"], ut["epoch_id"])]["delta_t_days"]
            epoch = {"jd": ut["jd"] + offset}
        if bits(epoch["jd"]) != row["jd_bits"] or row.get("in_supported_interval",
                                                           epoch.get("in_supported_interval")) != epoch.get("in_supported_interval"):
            raise Refusal(f"a row named {row['epoch_id']} is not that instant")

    # ⛔ NONUT, measured.
    modes = [r for r in readings if r["part"] == "mode_invariance"]
    pairs: dict[tuple[str, str], dict[str, dict]] = {}
    for row in modes:
        pairs.setdefault((row["configuration"], row["epoch_id"]), {})[row["nutation"]] = row
    largest = 0.0
    for key, pair in pairs.items():
        if pair["default"]["longitude_bits"] == pair["nonut"]["longitude_bits"]:
            raise Refusal(f"{key}: the NONUT request moved nothing; it was not applied")
        largest = max(largest, abs(wrapped_arcseconds(pair["default"]["longitude"], pair["nonut"]["longitude"])))

    # ⛔ The discriminating control: the Moon reports a substitution exactly where one was built.
    for row in flags:
        if row["body_label"] == "moon" and row["substitution_reported"] != row["built_to_substitute"]:
            raise Refusal(
                f"the Moon control did not fire under {row['condition']} through {row['entry_point']}: "
                f"requested {row['requested']}, returned {row['returned']}. A reader that cannot see a "
                "substitution reads an echo as agreement")

    configurations = [c[0] for c in CONFIGURATIONS]
    invariance = {}
    for nutation in ("default", "nonut"):
        by_epoch: dict[str, set] = {}
        returned: dict[str, set] = {}
        for row in modes:
            if row["nutation"] != nutation:
                continue
            by_epoch.setdefault(row["epoch_id"], set()).add(row["longitude_bits"])
            returned.setdefault(row["configuration"], set()).add(row["returned"])
        invariance[nutation] = {
            "epochs_with_one_longitude_across_the_five_configurations": sum(1 for s in by_epoch.values() if len(s) == 1),
            "of": len(by_epoch),
            "returned_word_by_configuration": {c: sorted(returned[c]) for c in configurations},
        }

    def baseline(part: str, entry: str) -> dict:
        return {(r["configuration"], r["epoch_id"]): r for r in readings
                if r["part"] == part and r["entry_point"] == entry and r["nutation"] == "nonut"
                and "forced_constant" not in r}

    def caused(part: str, base: dict) -> dict:
        forced = [r for r in readings if r["part"] == part]
        held = [r for r in forced if r["forced_held_after_call"]]
        moved = [r for r in held if r["longitude_bits"] != base[(r["configuration"], r["epoch_id"])]["longitude_bits"]]
        return {"readings": len(forced), "forced_value_held_after_the_call": len(held),
                "longitude_moved_where_held": len(moved),
                "largest_move_arcseconds": round(max(
                    (abs(wrapped_arcseconds(r["longitude"], base[(r["configuration"], r["epoch_id"])]["longitude"]))
                     for r in moved), default=0.0), 6)}

    universal = [r for r in readings if r["part"] == "universal_time"]
    at_ut = {(r["configuration"], r["epoch_id"]): r for r in universal if r["entry_point"] == "calc_ut"}
    shifted = {(r["configuration"], r["epoch_id"].removesuffix("_plus_delta_t")): r
               for r in universal if r["entry_point"] == "calc"}
    identical = sum(1 for k, r in at_ut.items() if r["longitude_bits"] == shifted[k]["longitude_bits"])
    spread = {}
    for epoch in context["universal"]:
        values = [at_ut[(c, epoch["epoch_id"])]["longitude"] for c in configurations]
        spread[epoch["epoch_id"]] = round(max(abs(wrapped_arcseconds(a, b)) for a in values for b in values), 9)

    discrimination = {}
    for condition in context["conditions"]:
        entry = {"built_to_substitute": condition["built_to_substitute"]}
        for row in flags:
            if row["condition"] == condition["condition"]:
                entry[f"{row['entry_point']}_{row['body_label']}_substitution_reported"] = row["substitution_reported"]
        discrimination[condition["condition"]] = entry

    return {
        "readings": len(rows),
        "children": context["children"],
        "rows_by_part": {part: sum(1 for r in readings if r["part"] == part)
                         for part in ("mode_invariance", "cause", "universal_time", "universal_time_cause")}
        | {"returned_flag_by_body": len(flags)},
        "mode_invariance": invariance,
        "largest_default_minus_nonut_arcseconds": round(largest, 4),
        "cause": caused("cause", baseline("mode_invariance", "calc")),
        "universal_time": {
            "calc_ut_identical_to_calc_at_ut_plus_delta_t": identical,
            "of": len(at_ut),
            "largest_spread_across_configurations_arcseconds": spread,
        },
        "universal_time_cause": caused("universal_time_cause", baseline("universal_time", "calc_ut")),
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
    "finding": "mean_node_reading | delta_t_reading | returned_flag_by_body",
    "part": "mode_invariance | cause | universal_time | universal_time_cause",
    "configuration": "which ephemeris was requested and which directory was on the path",
    "ephemeris_requested": "moshier | swiss_file | jpl_file -- the source the request names",
    "path_state": "data_files (exactly the pinned set) | empty_directory (verified empty) | no_path_set",
    "nutation": "default (no nutation bit requested) | nonut (FLG_NONUT requested) | ephemeris_bits_only "
                "(deltat_ex: only the ephemeris bits of the configuration's NONUT word are passed)",
    "entry_point": "the library function called",
    "body": "the library's own body integer (a delta_t_reading has none)",
    "epoch_id": "which instant; the Julian day passed is `jd`, and `jd_bits` is that value",
    "in_supported_interval": "whether the instant lies inside the data profile's declared coverage",
    "requested": "⭐ the WHOLE flag word passed, nutation bit included",
    "returned": "the whole flag word the call returned",
    "forced_constant": "the library name of the tidal-acceleration constant forced before the call",
    "forced_held_after_call": "⛔ whether the constant read back after the call is still the one forced. Where it is not, the reading says nothing about the forced value -- written as measured",
    "tidal_constant_before": "the tidal-acceleration constant in force before the call, read from the library",
    "tidal_constant_after": "the same, read after the call",
    "longitude": "the first returned value; `longitude_bits` is the value, the decimal is display",
    "latitude": "the second returned value",
    "distance": "the third returned value",
    "delta_t_days": "what deltat_ex returned, in days",
    "current_file_data_after": "⚠ what the library reports about its open files after the call, file name only -- recorded, never interpreted and never relied on",
    "condition": "returned_flag_by_body: the condition built",
    "built_to_substitute": "⭐ whether the condition was built so that the requested ephemeris cannot answer",
    "body_label": "returned_flag_by_body: which of the two bodies",
    "body_name": "the library's own name for the body",
    "substitution_reported": "⭐ whether the returned word's ephemeris bits differ from the requested word's",
}


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
                           "its finished row declares: the directory for its path state (none where no path is "
                           "set), the forced constant it records, the constant read, exactly one reading call "
                           "with the row's entry point, instant, body and whole flag word, and the read-backs -- "
                           "nothing else; held, each to what it names: a reading's finding and part to its entry "
                           "point, its part to its forced constant and epochs, its ephemeris label to its word's "
                           "bits, its configuration or condition to the table defining it, its nutation label to "
                           "its word's nutation bit, a forced constant's name to the library's value of that name, "
                           "a node reading's body to the node and an offset reading to no body, a body label and "
                           "name to the body, an epoch name to its instant and in-interval flag; each child "
                           "started from an interpreter that had not loaded the library and returned one reading, "
                           "and no two readings came from one child. \u26a0 Honest error, not forgery: a reference "
                           "to the library bound before the wrapping, its compiled extension reached another way, "
                           "or a call through one of its classes is outside the record; and a row field neither "
                           "the call sequence nor these pairs read is held by nothing here",
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
            "method": "each entry point called under a declared configuration and what came back read: the "
                      "returned values and the whole returned word, the tidal-acceleration constant before "
                      "and after the call, and the library's report of its open files",
        },
        "title": "What one release of the ephemeris library returns for its mean lunar node under three "
                 "ephemeris requests, two data-file states and both nutation settings, and what its returned "
                 "word says beside the Moon's",
        "attests": "a vendor_convention attestation: what this release of the ephemeris library returned for its "
                   "mean lunar node through calc and calc_ut, under three ephemeris requests, two data-file "
                   "states and both nutation settings, with the whole requested and returned words, the "
                   "tidal-acceleration constant read back, a forced constant, and the time offset beside each "
                   "universal-time call; and, beside the Moon's, what the node's returned word says when the "
                   "requested ephemeris cannot answer",
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
                          "Julian day. They set every epoch's in-interval flag, the crossing search window, "
                          "the grid's first and last year, and the two ends among the calc and the "
                          "universal-time epochs; the other epochs are labelled instants and formulas written "
                          "in the generator",
                "profile": interval["profile"],
                "manifest_sha256": interval["manifest_sha256"],
                "dataset": interval["dataset"],
                "declared_coverage": interval["declared_coverage"],
                **patterned("start_jd", interval["start"]),
                **patterned("end_jd", interval["end"]),
                "used_as": "dynamical-time Julian days passed to calc; the coverage's scale is TDB and its "
                           "difference from TT, milliseconds, is not applied",
                "count": len(context["epochs"]),
                "inside_the_interval": sum(1 for e in context["epochs"] if e["in_supported_interval"]),
                "crossings": "instants where the published IERS Conventions (2010) Eq. (5.43) F5 row passes "
                             "0/360 degrees, located with that row only to choose where to sample -- ⛔ "
                             "not a statement about the library",
                "universal_time_epochs": [e["epoch_id"] for e in context["universal"]],
            },
            **summary,
        },
        "notes": [
            "⛔ A PROVENANCE RECORD, AND IT GATES NOTHING. It states what was observed and compares nothing: no "
            "tolerance, no reference value, no verdict. It is written before any rule that might use it is "
            "decided, so that the rule is written from the measurement rather than the other way round.",
            "⭐ THE NODE'S RETURNED WORD ECHOES THE REQUEST. Under every condition built so that the requested "
            "ephemeris cannot answer -- outside the data files' coverage, an empty directory, no path, a JPL "
            "request with no JPL file -- the Moon's returned word reports the substitution and the node's returns "
            "the request unchanged, through calc and through calc_ut alike. So for this body the returned "
            "word does not distinguish the ephemeris that answered from the one requested.",
            "⭐ THROUGH calc THE LONGITUDE DID NOT MOVE with the requested ephemeris, the data-file state or a "
            "forced tidal constant that held through the call (summary.mode_invariance, summary.cause). "
            "THROUGH calc_ut IT DID, by small amounts, and calc_ut was bit-identical to calc at the universal "
            "day plus deltat_ex's offset under the same ephemeris bits in every unforced reading "
            "(summary.universal_time) -- recorded as numbers, ⛔ not as a mechanism.",
            "⚠ NONUT DECIDES THE VALUE. Every nonut reading of the first part has a default-nutation twin under "
            "the same configuration and instant, and the record refuses to exist if any pair agrees, because a "
            "NONUT request that moves nothing was not applied; and in every part the whole flag word each call "
            "actually received is recorded inside the child and must be the row's own, so a bit dropped at any "
            "call is refused.",
            "⚠ Not measured: sidereal mode, FLG_SPEED, any body but these two, any other entry point, any "
            "other library version or host. The warm, many-readings-per-process sweeps of the first scoping run "
            "are deliberately absent: this generator takes every reading in a fresh process, and refuses a child "
            "whose recorded library calls are other than its row declares.",
            "⚠ Dated, versioned and placed deliberately. This is an observation of one release through one "
            "binding on one machine, not a claim about the software in general.",
        ],
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
    work = tempfile.mkdtemp(prefix="mean-node-modes-")
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
