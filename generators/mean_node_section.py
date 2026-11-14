"""The mean lunar node through calc, as a comparison section, and the three controls it rests on.

Two files, written together from one clean commit:

* a ``numeric_pin`` with one section — the library's mean lunar node through ``calc`` under one declared
  configuration (the data-file request, the pinned files, the whole word with ``FLG_NONUT``), its rows read
  **warm**, several in one process in the order they are written, ``none`` asserted on every row and the
  tidal-acceleration constant read back after each call;
* an R3 ``provenance_record`` of its controls, at **every** row:
  ① **invariance** — the node read under each of five configurations, each reading the one call of a fresh
  process, bit-identical to the row; beside it a **witness**, the Moon at the same instant under the same five,
  whose returned word names a source other than the request where the request cannot answer, differs between
  two answering sources, and under the section's own configuration is the request honoured;
  ② **sufficiency** — the section read again warm in another order, bit-identical;
  ③ **nutation twin** — the same reading without ``FLG_NONUT``, in a fresh process, which must differ.

⛔ **Recorder, never explainer.** Nothing here describes how the library computes anything. Whether the node's
value moves with the request is recorded as bits, never as a mechanism.

⛔ **The rows lie inside a data profile manifest's declared coverage**, read from the file given and converted
back to its own strings — never a Julian day typed here. The instants are the in-coverage calc epochs of the
mean-node record this repository already wrote (``mean_node_modes.py``): a grid every five years at four times of
day, J2000, the coverage's two ends, and instants near where the published IERS Conventions (2010) Eq. (5.43)
row for the fifth Delaunay argument passes 0/360 degrees — used to choose where to sample, and for nothing else.

⛔ **Refusals, each before anything is written**: a dirty or commitless tree; a data directory that is not exactly
the pinned set; an "empty" directory that is not empty (before and after); a child that did not start without the
library loaded, returned other than its readings, or came back twice; a child whose calls into the library —
recorded inside it, through the module's and its submodule's callables after they were wrapped — are not exactly
the sequence its finished rows declare; a reading not at its own part's epochs and instants, or whose labels are
not what they name; a section row without its unit, spelled ``degree``; any control failing at any row; a read-back that differs between rows; a witness reading the
section's configuration answers that lies within a day of the witness's coverage edge as the survey given measures
it. ⚠ These guard honest error, ⛔ not forgery.

The child imports the standard library and the binding alone. The parent writes through this repository's
fixture contract, which refuses at write time what the contract refuses.

Usage::

    python mean_node_section.py --ephe-path DIR --empty-dir DIR --profile MANIFEST --survey FILE --out-dir DIR
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import math
import os
import shutil
import struct
import subprocess
import sys
import tempfile
import tomllib
import types
from pathlib import Path

#: The library's data files, pinned (a test holds this table equal to `src/saakshi/swiss.py`'s).
EPHE_PINS: tuple[dict, ...] = (
    {"dataset": "seas_18.se1", "profile": "swiss_file@1", "size_bytes": 223_004,
     "sha256": "a2cd8fc33807c78ca9a700c91c2e042258b12fc4796519e00781440b5ad8b2e2",
     "publisher": "Astrodienst AG", "pinned_on": "2026-08-04"},
    {"dataset": "semo_18.se1", "profile": "swiss_file@1", "size_bytes": 1_304_771,
     "sha256": "1ca07bd67c24374d77226180c20a4f9996cba013697894810518e7eb582ca4f7",
     "publisher": "Astrodienst AG", "pinned_on": "2026-08-04"},
    {"dataset": "sepl_18.se1", "profile": "swiss_file@1", "size_bytes": 484_061,
     "sha256": "ca1393ceab3a44fbc895887cf789c68819ae6a1cbc9b22225872dbe4ccd99a66",
     "publisher": "Astrodienst AG", "pinned_on": "2026-08-04"},
)

J2000 = 2451545.0
UNIX_EPOCH_JD = 2440587.5
SECONDS_PER_DAY = 86400.0
ARCSECONDS_PER_DEGREE = 3600.0

#: ⚠ The published IERS Conventions (2010) Eq. (5.43) row for F5. ⛔ Used ONLY to locate instants to sample.
F5_ROW: tuple[float, ...] = (125.04455501 * 3600.0, -6962890.5431, 7.4722, 0.007702, -0.00005939)
CROSSING_STRIDE = 4
DYADIC = 2.0**20
CROSSING_OFFSETS: tuple[tuple[float, str], ...] = ((0.0, "at"), (-0.25, "minus_6h"), (0.25, "plus_6h"))
GRID_STEP_YEARS = 5

#: The five configurations of the declared set: (name, requested source, directory on the path).
CONFIGURATIONS: tuple[tuple[str, str, str], ...] = (
    ("moshier_files_present", "moshier", "data_files"),
    ("moshier_dir_empty", "moshier", "empty_directory"),
    ("swiss_file_present", "swiss_file", "data_files"),
    ("swiss_file_dir_empty", "swiss_file", "empty_directory"),
    ("jpl_requested_no_jpl_file", "jpl_file", "data_files"),
)
#: ⭐ The section's configuration, C: the data-file request with the pinned files. ⛔ Never the JPL request with no
#: JPL file, nor the data-file request with an empty directory — the witness shows neither honoured.
SECTION_CONFIGURATION = "swiss_file_present"
#: The two configurations of the set under which the requested source is absent.
ABSENT_SOURCE = ("swiss_file_dir_empty", "jpl_requested_no_jpl_file")

SECTION = "mean_node"
ENTRY_POINT = "calc"
EPHEMERIS_NAMES: tuple[tuple[str, str], ...] = (
    ("moshier", "FLG_MOSEPH"), ("swiss_file", "FLG_SWIEPH"), ("jpl_file", "FLG_JPLEPH"))
EPHEMERIS_MASK = 7

#: ⭐ How each process-wide state the library-state record names is put in place, and it is the same for every
#: reading: a fresh interpreter in which nothing sets it. ⛔ Keyed by that record's names; a test holds them equal.
STATE_DISCIPLINE: dict[str, str] = {
    "sidereal_mode": "never set: every child is a fresh interpreter, and calc is asked for no sidereal position",
    "user_defined_delta_t": "never set: every child is a fresh interpreter, and calc takes a dynamical-time day",
    "tidal_acceleration": "never set: put back by setting the path, and read back after every call",
    "leap_second_table": "never read: no child converts a civil instant",
}

#: ⭐ The row this section is compared against, by the id its consumer minted for it. It replaces this file's earlier
#: proposal `mean-node-convention-1` at the consumer's request. ⛔ The row is the consumer's; nothing here asserts
#: it exists.
BUDGET_ROW = "BU03"

#: ⭐ The unit of the one component every row carries, written on EVERY row: a consumer reads a row's unit from the
#: row itself, ⛔ never from the classification beside it, and refuses a row with none or another spelling.
SECTION_UNIT = "degree"

CHILD_TIMEOUT_SECONDS = 300


class Refusal(Exception):
    """A condition under which nothing may be written."""


def bits(value: float) -> str:
    return struct.pack(">d", value).hex()


def unbits(text: str) -> float:
    return struct.unpack(">d", bytes.fromhex(text))[0]


def patterned(key: str, value: float) -> dict:
    return {key: value, f"{key}_bits": bits(value)}


def wrapped_arcseconds(a_degrees: float, b_degrees: float) -> float:
    return ((a_degrees - b_degrees + 180.0) % 360.0 - 180.0) * ARCSECONDS_PER_DEGREE


# ======================================================================================
# The epochs — the manifest's interval, and the record's in-interval calc epochs
# ======================================================================================


def julian_day(stamp: str) -> float:
    moment = datetime.datetime.fromisoformat(stamp)
    if moment.tzinfo is not None:
        raise Refusal(f"{stamp!r}: a civil instant here carries no zone")
    return UNIX_EPOCH_JD + (moment - datetime.datetime(1970, 1, 1)).total_seconds() / SECONDS_PER_DAY


def civil(jd: float) -> str:
    return (datetime.datetime(1970, 1, 1) + datetime.timedelta(days=jd - UNIX_EPOCH_JD)).isoformat(timespec="seconds")


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
    for stamp, jd in ((coverage["start"], start), (coverage["end"], end)):
        if civil(jd) != stamp:
            raise Refusal(f"{stamp!r} became JD {jd!r}, which converts back to {civil(jd)!r}")
    if not start < end:
        raise Refusal("the declared coverage does not run forward")
    return {"profile": f"{identity.get('name')}@{identity.get('version')}",
            "manifest_sha256": hashlib.sha256(raw).hexdigest(), "dataset": datasets[0].get("logical_id"),
            "declared_coverage": {k: coverage[k] for k in ("start", "end", "scale")}, "start": start, "end": end}


def year_epoch(year: int) -> float:
    return J2000 + (year - 2000) * 365.25


def f5_degrees(jd: float) -> float:
    t = (jd - J2000) / 36525.0
    return sum(c * t ** k for k, c in enumerate(F5_ROW)) / ARCSECONDS_PER_DEGREE


def crossings(start: float, end: float) -> list[float]:
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
    """The section's rows, in the order they are written and read: by instant.

    ⭐ The same instants as the mean-node record's calc epochs inside the interval, derived the same way — a test
    holds them equal, bit for bit — so every row can be compared with that record's own reading of it.
    """
    start, end = interval["start"], interval["end"]
    start_year = int(interval["declared_coverage"]["start"][:4])
    end_year = int(interval["declared_coverage"]["end"][:4])
    years = range(start_year + (-start_year) % GRID_STEP_YEARS, end_year - end_year % GRID_STEP_YEARS + 1,
                  GRID_STEP_YEARS)
    epochs = [{"epoch_id": f"grid_{year}", "jd": math.floor(year_epoch(year)) + 0.25 * (i % 4)}
              for i, year in enumerate(years)]
    epochs.append({"epoch_id": "j2000", "jd": J2000})
    for label, stamp, jd in (("start", interval["declared_coverage"]["start"], start),
                             ("end", interval["declared_coverage"]["end"], end)):
        epochs.append({"epoch_id": f"supported_{label}_{stamp[:10].replace('-', '_')}", "jd": jd})
    for n, crossing in enumerate(crossings(start, end)[::CROSSING_STRIDE]):
        dyadic = round(crossing * DYADIC) / DYADIC
        for offset, tag in CROSSING_OFFSETS:
            epochs.append({"epoch_id": f"wrap{n}_{tag}", "jd": dyadic + offset})
    epochs = [e for e in epochs if start <= e["jd"] <= end]
    if len({e["jd"] for e in epochs}) != len(epochs) or len({e["epoch_id"] for e in epochs}) != len(epochs):
        raise Refusal("two epochs share an instant or a name")
    return sorted(epochs, key=lambda e: e["jd"])


# ======================================================================================
# The directories, and the survey's edge for the witness
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
    if os.listdir(path):
        raise Refusal(f"the empty directory holds {sorted(os.listdir(path))}")


EDGE_ENDS = ("lower_edge_last_outside_jd_ut", "lower_edge_first_inside_jd_ut",
             "upper_edge_first_inside_jd_ut", "upper_edge_last_outside_jd_ut")


def read_survey_edges(path: str) -> dict:
    """Every body's coverage edge in the survey given, as bits, and the survey's digest.

    ⛔ Only ends written as bits are read; a body with two rows, or a row with fewer than four ends, is refused.
    """
    with open(path, "rb") as handle:
        raw = handle.read()
    edges: dict[int, tuple[float, ...]] = {}
    for line in raw.decode("utf-8").splitlines()[1:]:
        row = json.loads(line)
        if row.get("finding") != "coverage_edge":
            continue
        body = row["body"]
        if body in edges or not all(f"{end}_bits" in row for end in EDGE_ENDS):
            raise Refusal(f"the survey's coverage_edge rows for body {body} are not one row of four bit ends")
        edges[body] = tuple(unbits(row[f"{end}_bits"]) for end in EDGE_ENDS)
    return {"sha256": hashlib.sha256(raw).hexdigest(), "edges": edges}


# ======================================================================================
# The child program — a fresh interpreter, one reading or one warm sequence
# ======================================================================================


def _child(spec_json: str) -> None:
    fresh = "swisseph" not in sys.modules
    import swisseph as swe

    # ⭐ EVERY call into the library is recorded with the arguments it ACTUALLY received, here, in the child.
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
                if member.__name__.startswith(swe.__name__ + "."):
                    wrap(member, f"{prefix}{name}.")
            elif callable(member):
                setattr(module, name, recorded(prefix + name, member))

    wrap(swe, "")
    spec = json.loads(spec_json)
    swe.set_ephe_path(spec["path"])
    readings = []
    for jd_bits in spec["jd_bits"]:
        values, returned = swe.calc(unbits(jd_bits), spec["body"], spec["word"])
        # ⭐ Every value the call returned, in order, beside the first three by name: a section of another body
        #    reads all of them (`nutation_obliquity_section.py`); this one writes the three it always wrote.
        readings.append({"longitude_bits": bits(values[0]), "latitude_bits": bits(values[1]),
                         "distance_bits": bits(values[2]), "returned": returned,
                         "tidal_constant_after_bits": bits(swe.get_tid_acc()),
                         "values_bits": [bits(float(v)) for v in values]})
    sys.stdout.write(json.dumps({"nonce": os.urandom(16).hex(), "fresh_interpreter": fresh, "calls": calls,
                                 "readings": readings}))


def child_environment() -> dict[str, str]:
    return {k: v for k, v in os.environ.items() if not k.startswith("SE_")}


def declared_calls(spec: dict) -> list[dict]:
    """The whole call sequence a child's spec allows: its path, then per reading the call and the read-back."""
    calls = [{"function": "set_ephe_path", "args": [spec["path"]], "keywords": []}]
    for jd_bits in spec["jd_bits"]:
        calls.append({"function": ENTRY_POINT, "args": [jd_bits, spec["body"], spec["word"]], "keywords": []})
        calls.append({"function": "get_tid_acc", "args": [], "keywords": []})
    return calls


class Children:
    """Runs every child, and refuses any that was not the readings it was asked for."""

    def __init__(self, work: str) -> None:
        self.work = work
        self.nonces: set[str] = set()

    def run(self, spec: dict) -> list[dict]:
        proc = subprocess.run(
            [sys.executable, "-I", os.path.abspath(__file__), "--child", json.dumps(spec)],
            cwd=self.work, env=child_environment(), capture_output=True, text=True,
            timeout=CHILD_TIMEOUT_SECONDS, check=False,
        )
        if proc.returncode != 0:
            raise Refusal(f"a child failed ({proc.returncode}): {proc.stderr[-400:]}")
        result = json.loads(proc.stdout)
        if not result["fresh_interpreter"] or len(result["readings"]) != len(spec["jd_bits"]):
            raise Refusal(f"a child returned {len(result['readings'])} readings for {len(spec['jd_bits'])} asked "
                          f"(fresh interpreter: {result['fresh_interpreter']})")
        if result["nonce"] in self.nonces:
            raise Refusal("two children's readings came back from one child")
        self.nonces.add(result["nonce"])
        if result["calls"] != declared_calls(spec):
            raise Refusal(f"a child's calls were {[c['function'] for c in result['calls']]}; its spec declares "
                          f"{[c['function'] for c in declared_calls(spec)]}")
        return result["readings"]


# ======================================================================================
# The parent — chooses each child's request, records what came back
# ======================================================================================


def measure(ephe_path: str, empty_dir: str, profile: str, work: str) -> tuple[list[dict], list[dict], dict]:
    """Returns (section rows, control rows, context)."""
    import swisseph as swe

    flag = {name: getattr(swe, constant) for name, constant in EPHEMERIS_NAMES}
    nonut = swe.FLG_NONUT
    paths = {"data_files": os.path.abspath(ephe_path), "empty_directory": os.path.abspath(empty_dir)}
    configurations = {name: (eph, state) for name, eph, state in CONFIGURATIONS}
    interval = read_interval(profile)
    epochs = build_epochs(interval)
    children = Children(work)
    c_eph, c_state = configurations[SECTION_CONFIGURATION]
    word = flag[c_eph] | nonut

    def warm(order: list[dict]) -> list[dict]:
        return children.run({"path": paths[c_state], "body": swe.MEAN_NODE, "word": word,
                             "jd_bits": [bits(e["jd"]) for e in order]})

    # ---- the section: warm, in row order; and ② the same rows read warm in the reverse order
    section = warm(epochs)
    reversed_order = list(reversed(epochs))
    permuted = dict(zip((e["epoch_id"] for e in reversed_order), warm(reversed_order), strict=True))

    rows = []
    for epoch, reading in zip(epochs, section, strict=True):
        rows.append({"section": SECTION, "epoch_id": epoch["epoch_id"], "body": swe.MEAN_NODE,
                     "instant": {"scale": "tt", **patterned("jd", epoch["jd"])}, "unit": SECTION_UNIT,
                     "values": [unbits(reading["longitude_bits"])], "values_bits": [reading["longitude_bits"]],
                     "state_read_back": {"state": "tidal_acceleration",
                                         **patterned("value", unbits(reading["tidal_constant_after_bits"]))},
                     "source_assertion": {"kind": "none", "reason": "request_invariant"}})

    def cold(control: str, configuration: str, body: int, request: int, epoch: dict, nutation: str,
             role: str | None) -> dict:
        eph, state = configurations[configuration]
        reading = children.run({"path": paths[state], "body": body, "word": request, "jd_bits": [bits(epoch["jd"])]})[0]
        row = {"finding": "configuration_control", "control": control, "entry_point": ENTRY_POINT,
               "configuration": configuration, "epoch_id": epoch["epoch_id"], "body": body,
               "body_name": swe.get_planet_name(body), **patterned("jd", epoch["jd"]), "requested": request,
               "returned": reading["returned"], "ephemeris_requested": eph, "nutation": nutation,
               "path_state": state}
        for key in ("longitude", "latitude", "distance", "tidal_constant_after"):
            row.update(patterned(key, unbits(reading[f"{key}_bits"])))
        row["call_history"] = "cold_process_per_row"
        if role is not None:
            row["role"] = role
        return row

    controls = []
    for epoch in epochs:
        for configuration, (eph, _state) in configurations.items():
            controls.append(cold("invariance", configuration, swe.MEAN_NODE, flag[eph] | nonut, epoch, "nonut",
                                 "subject"))
        for configuration, (eph, _state) in configurations.items():
            controls.append(cold("invariance", configuration, swe.MOON, flag[eph] | nonut, epoch, "nonut",
                                 "witness"))
        controls.append(cold("nutation_twin", SECTION_CONFIGURATION, swe.MEAN_NODE, flag[c_eph], epoch, "default",
                             None))
    order = [e["epoch_id"] for e in reversed_order]
    for epoch in epochs:
        value_bits = permuted[epoch["epoch_id"]]["longitude_bits"]
        controls.append({"finding": "configuration_control", "control": "sufficiency", "entry_point": ENTRY_POINT,
                         "epoch_id": epoch["epoch_id"], "call_history": "permuted", "call_order": order,
                         "values": [unbits(value_bits)], "values_bits": [value_bits],
                         "tidal_constant_after": unbits(permuted[epoch["epoch_id"]]["tidal_constant_after_bits"]),
                         "tidal_constant_after_bits": permuted[epoch["epoch_id"]]["tidal_constant_after_bits"]})

    context = {"interval": interval, "epochs": epochs, "flag": flag, "nonut": nonut, "word": word,
               "children": len(children.nonces), "section_returned": [r["returned"] for r in section],
               "subject": swe.MEAN_NODE, "witness": swe.MOON,
               "body_names": {swe.MEAN_NODE: swe.get_planet_name(swe.MEAN_NODE),
                              swe.MOON: swe.get_planet_name(swe.MOON)},
               "library_version": swe.version}
    return rows, controls, context


# ======================================================================================
# The controls a section must pass before either file is written
# ======================================================================================


def source(word: int) -> int:
    return word & EPHEMERIS_MASK


def held(rows: list[dict], controls: list[dict], context: dict, *, invariance_bits: int,
         twin_bits: int) -> tuple[list[dict], list[dict], dict]:
    """Every row and reading held to what it names, each part to its own epochs; and every returned word one these
    readings requested. Returns (the readings, the sufficiency rows, the readings by part, epoch and configuration).

    ⭐ What a section of this shape keeps whatever its body and word: the invariance part's readings carry
    ``invariance_bits`` beside each configuration's ephemeris bits, the twin's ``twin_bits`` beside the section's
    own — the one bit that differs between the section's word and its twin's. Raises Refusal on any that fails.
    """
    epochs = {e["epoch_id"]: e for e in context["epochs"]}
    flag = context["flag"]
    configurations = {name: (eph, state) for name, eph, state in CONFIGURATIONS}
    subject, witness = context["subject"], context["witness"]
    readings = [c for c in controls if c["control"] != "sufficiency"]
    sufficiency = [c for c in controls if c["control"] == "sufficiency"]
    if context["children"] != len(readings) + 2:
        raise Refusal(f"{len(readings)} cold readings and two warm sequences from {context['children']} children")

    # ⛔ Held, each to what it names: a row to its epoch's instant; a reading's control and role to its body and word;
    #    its configuration to the table; its nutation label to its word's nutation bit; its ephemeris label to its
    #    word's bits; its body name to its body. ⭐ Each part to ITS OWN epochs — exactly the section's, each once per
    #    configuration — never a family.
    if [r["epoch_id"] for r in rows] != [e["epoch_id"] for e in context["epochs"]]:
        raise Refusal("the section's rows are not its epochs in order")
    for row in rows:
        if row["instant"]["jd_bits"] != bits(epochs[row["epoch_id"]]["jd"]) or row["body"] != subject:
            raise Refusal(f"section row {row['epoch_id']} is not that instant or not the section's body")
        if row.get("unit") != SECTION_UNIT:
            raise Refusal(f"section row {row['epoch_id']} declares unit {row.get('unit')!r}, not {SECTION_UNIT!r}")
    expected_parts = {
        ("invariance", "subject"): {(e, c) for e in epochs for c in configurations},
        ("invariance", "witness"): {(e, c) for e in epochs for c in configurations},
        ("nutation_twin", None): {(e, SECTION_CONFIGURATION) for e in epochs},
    }
    seen: dict[tuple, list] = {part: [] for part in expected_parts}
    for r in readings:
        part = (r["control"], r.get("role"))
        if part not in expected_parts:
            raise Refusal(f"a reading filed as {part}")
        seen[part].append((r["epoch_id"], r["configuration"]))
        eph, state = configurations[r["configuration"]]
        nutation_bit = invariance_bits if r["control"] == "invariance" else twin_bits
        body = witness if part == ("invariance", "witness") else subject
        if (r["ephemeris_requested"], r["path_state"]) != (eph, state) or r["requested"] != flag[eph] | nutation_bit \
                or r["nutation"] != ("nonut" if nutation_bit else "default") or r["body"] != body \
                or r["body_name"] != context["body_names"][body] or r["entry_point"] != ENTRY_POINT \
                or r["call_history"] != "cold_process_per_row":
            raise Refusal(f"a {part} reading at {r['epoch_id']} under {r['configuration']} is not what it names")
        if r["epoch_id"] not in epochs or r["jd_bits"] != bits(epochs[r["epoch_id"]]["jd"]):
            raise Refusal(f"a {part} reading named {r['epoch_id']} is not that part's instant")
    for part, want in expected_parts.items():
        got = seen[part]
        if len(got) != len(set(got)) or set(got) != want:
            raise Refusal(f"part {part} holds {len(got)} readings, not one at each of its {len(want)} places")
    if sorted(s["epoch_id"] for s in sufficiency) != sorted(epochs):
        raise Refusal("the sufficiency part is not one row at each of the section's epochs")
    # ⛔ Every returned word one these readings requested, under its own source: a reader of words by their
    #    requests cannot read any other, and refuses the body under every key over it.
    asked = {r["requested"]: r["ephemeris_requested"] for r in readings}
    for r in readings:
        if r["returned"] not in asked or flag[asked[r["returned"]]] != source(r["returned"]):
            raise Refusal(f"a reading at {r['epoch_id']} returned word {r['returned']}, which no reading here "
                          "requested under the source its bits name")
    return readings, sufficiency, {(r["control"], r.get("role"), r["epoch_id"], r["configuration"]): r
                                   for r in readings}


def witness_at_every_row(by: dict, context: dict) -> list[float]:
    """⛔ ① (b) — the witness at every row: reports where its source is absent; spans two answering sources; C
    honoured. Returns, per row, the smallest separation between C's answer and another answering source's."""
    epochs = {e["epoch_id"]: e for e in context["epochs"]}
    word = context["word"]
    configurations = {name: (eph, state) for name, eph, state in CONFIGURATIONS}
    separations = []
    for epoch_id in epochs:
        w = {c: by[("invariance", "witness", epoch_id, c)] for c in configurations}
        for c in ABSENT_SOURCE:
            if source(w[c]["returned"]) == source(w[c]["requested"]):
                raise Refusal(f"① (b) ⑴ fails at {epoch_id}: the witness echoed under {c}")
        c_reading = w[SECTION_CONFIGURATION]
        if c_reading["requested"] != word or c_reading["returned"] != word:
            raise Refusal(f"① (b) ⑶ fails at {epoch_id}: under C the witness requested {c_reading['requested']} "
                          f"and returned {c_reading['returned']}")
        spanning = [c for c in configurations if c not in ABSENT_SOURCE and c != SECTION_CONFIGURATION
                    and source(w[c]["returned"]) != source(c_reading["returned"])
                    and any(w[c][f"{k}_bits"] != c_reading[f"{k}_bits"] for k in ("longitude", "latitude", "distance"))]
        if not spanning:
            raise Refusal(f"① (b) ⑵ fails at {epoch_id}: no other configuration's answer differs from C's")
        separations.append(min(abs(wrapped_arcseconds(w[c]["longitude"], c_reading["longitude"])) for c in spanning))
    return separations


def inside_the_interval(rows: list[dict], context: dict) -> None:
    """⛔ ① (c) — every row inside the interval."""
    epochs = {e["epoch_id"]: e for e in context["epochs"]}
    start, end = context["interval"]["start"], context["interval"]["end"]
    if not all(start <= epochs[r["epoch_id"]]["jd"] <= end for r in rows):
        raise Refusal("① (c): a row lies outside the declared interval")


def one_read_back(rows: list[dict], context: dict) -> set[str]:
    """⛔ One read-back across the section (the configuration's one state), and the section's word every row."""
    read_back = {r["state_read_back"]["value_bits"] for r in rows}
    if len(read_back) != 1:
        raise Refusal(f"the section read back {sorted(read_back)}; one configuration reads back one value")
    if set(context["section_returned"]) != {context["word"]}:
        raise Refusal(f"the section's returned words were {sorted(set(context['section_returned']))}, not "
                      f"{context['word']}")
    return read_back


def witness_edge(survey: dict, readings: list[dict], context: dict, *, subject_noun: str = "the node") -> tuple:
    """⛔ The survey's edge: no witness reading the files answered lies within a day of the witness's measured
    coverage edge, and the section's body has no edge row of its own. Returns (the edge, the smallest margin)."""
    subject, witness = context["subject"], context["witness"]
    edge = survey["edges"].get(witness)
    if edge is None or subject in survey["edges"]:
        raise Refusal(f"the survey carries no edge for the witness, or one for {subject_noun}")
    honoured = [r for r in readings if r["body"] == witness and r["ephemeris_requested"] != "moshier"
                and source(r["returned"]) == source(r["requested"])]
    margin = min(min(r["jd"] - edge[1], edge[2] - r["jd"]) for r in honoured)
    if margin <= 1.0:
        raise Refusal(f"a witness reading the files answered lies {margin} days inside the witness's edge")
    return edge, margin


def check(rows: list[dict], controls: list[dict], context: dict, survey: dict) -> dict:
    """The section's own controls, at every row. Returns the summary; raises Refusal on any that fails."""
    epochs = {e["epoch_id"]: e for e in context["epochs"]}
    configurations = {name: (eph, state) for name, eph, state in CONFIGURATIONS}
    witness = context["witness"]
    readings, sufficiency, by = held(rows, controls, context, invariance_bits=context["nonut"], twin_bits=0)
    values = {r["epoch_id"]: r["values_bits"][0] for r in rows}

    # ⛔ ① (a) — every subject reading bit-identical to its row.
    for (control, role, epoch_id, configuration), r in by.items():
        if role == "subject" and r["longitude_bits"] != values[epoch_id]:
            raise Refusal(f"① (a) fails at {epoch_id}: under {configuration} the node read {r['longitude_bits']}, "
                          f"the row {values[epoch_id]}")

    separations = witness_at_every_row(by, context)
    inside_the_interval(rows, context)

    # ⛔ ② — the permuted regeneration bit-identical, in an order that differs.
    order = sufficiency[0]["call_order"]
    if order == [r["epoch_id"] for r in rows] or any(s["call_order"] != order for s in sufficiency):
        raise Refusal("② : the regeneration's order is the section's own, or not one order")
    for s in sufficiency:
        if s["values_bits"] != [values[s["epoch_id"]]]:
            raise Refusal(f"② fails at {s['epoch_id']}: the permuted regeneration read {s['values_bits']}")

    # ⛔ ③ — the twin without FLG_NONUT differs from the row.
    twin_moves = []
    for epoch_id in epochs:
        t = by[("nutation_twin", None, epoch_id, SECTION_CONFIGURATION)]
        if t["longitude_bits"] == values[epoch_id]:
            raise Refusal(f"③ fails at {epoch_id}: the reading without FLG_NONUT equals the row")
        twin_moves.append(abs(wrapped_arcseconds(t["longitude"], unbits(values[epoch_id]))))

    read_back = one_read_back(rows, context)
    edge, margin = witness_edge(survey, readings, context)

    worst = max(abs(wrapped_arcseconds(r["longitude"], unbits(values[r["epoch_id"]])))
                for r in readings if r.get("role") == "subject")
    return {
        "rows": len(rows),
        "readings": len(readings),
        "children": context["children"],
        "invariance": {"subject_readings": sum(1 for r in readings if r.get("role") == "subject"),
                       "differing_from_their_row": 0,
                       "largest_difference_arcseconds": worst},
        "witness": {"body": witness, "readings": sum(1 for r in readings if r.get("role") == "witness"),
                    "smallest_separation_between_two_answering_sources_arcseconds": round(min(separations), 6),
                    "largest_separation_arcseconds": round(max(separations), 6),
                    "returned_word_by_configuration": {
                        c: sorted({by[("invariance", "witness", e, c)]["returned"] for e in epochs})
                        for c in configurations},
                    "smallest_margin_inside_its_coverage_edge_days": round(margin, 6)},
        "subject_returned_word_by_configuration": {
            c: sorted({by[("invariance", "subject", e, c)]["returned"] for e in epochs}) for c in configurations},
        "sufficiency": {"rows": len(sufficiency), "call_history": "permuted", "identical_to_their_row": len(sufficiency)},
        "nutation_twin": {"rows": len(epochs),
                          "smallest_difference_arcseconds": round(min(twin_moves), 6),
                          "largest_difference_arcseconds": round(max(twin_moves), 6)},
        "state_read_back": {"state": "tidal_acceleration", **patterned("value", unbits(next(iter(read_back))))},
        "section_returned_word": context["word"],
        "survey_edge": {"survey_sha256": survey["sha256"], "body": witness,
                        **{f"{end}_bits": bits(v) for end, v in zip(EDGE_ENDS, edge)},
                        **dict(zip(EDGE_ENDS, edge))},
    }


# ======================================================================================
# The configuration identity — the consumer's rendering, with the whole word
# ======================================================================================


def configuration_identity(*, entry_point: str, requested: str, word: int | None, library: tuple[str, str, str],
                           configuration: dict) -> str:
    """The SHA-256 a consumer names a configuration by — the rendering ``conventions.configuration_sha256`` writes,
    with one line more, ``word|<integer>``, immediately after the request, where a section carries its whole word.

    ⛔ A ``|`` or a line break in any rendered field is refused, and so is a dataset listed twice.
    """
    def field(text: str) -> str:
        if "|" in text or "\n" in text or "\r" in text:
            raise Refusal(f"{text!r} would forge a field boundary in the identity")
        return text

    path = configuration["ephemeris_path"]
    lines = ["configuration|1", f"entry_point|{field(entry_point)}", f"requested|{field(requested)}"]
    if word is not None:
        lines.append(f"word|{int(word)}")
    lines += [f"library|{'|'.join(field(x) for x in library)}", f"path|{field(path['set'])}"]
    files = [(field(f["dataset"]), field(f["sha256"])) for f in path["resolved_contents"]]
    if len({d for d, _ in files}) != len(files):
        raise Refusal("a dataset is listed twice")
    lines += [f"file|{d}|{s}" for d, s in sorted(files, key=lambda f: (f[0].encode(), f[1].encode()))]
    for name in sorted(configuration["library_state"], key=lambda n: n.encode()):
        entry = configuration["library_state"][name]
        if entry["discipline"] == "reset":
            lines.append(f"state|{field(name)}|reset")
        elif "value" in entry:
            lines.append(f"state|{field(name)}|declared|value|{field(entry['value'])}")
        else:
            lines.append(f"state|{field(name)}|declared|bits|{field(entry['value_bits'])}")
    return hashlib.sha256("".join(line + "\n" for line in lines).encode("utf-8")).hexdigest()


def section_configuration() -> dict:
    return {
        "ephemeris_path": {"set": "explicit",
                           "resolved_contents": [{"dataset": p["dataset"], "sha256": p["sha256"]} for p in EPHE_PINS],
                           "directory_contents_verified": True},
        "library_state": {name: {"discipline": "reset"} for name in STATE_DISCIPLINE},
    }


# ======================================================================================
# The two files
# ======================================================================================


def _contract():
    """This repository's fixture contract, for the parent alone — ⛔ a child never loads it."""
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
    from saakshi import fixture, provenance

    return fixture, provenance


SECTION_ROW_SCHEMA = {
    "section": "the one section, the mean lunar node through calc",
    "epoch_id": "which instant",
    "body": "the library's own body integer: the mean node",
    "instant": "⭐ the dynamical-time Julian day passed to calc -- `scale` tt, `jd_bits` the value, `jd` display",
    "unit": "⭐ the unit of every component of `values`, `degree`, on every row",
    "values": "[longitude] in degrees -- ⚠ display; `values_bits` is the value",
    "values_bits": "⭐ the bit pattern of the longitude calc returned",
    "state_read_back": "the tidal-acceleration constant read back after the call -- `value_bits` the value",
    "source_assertion": "⭐ `none`, reason `request_invariant`: the node's returned word hands the request back, and "
                        "its value did not move with the request across the declared configurations (the control "
                        "record). ⛔ Never `reported`: the node's word cannot report",
}

CONTROL_ROW_SCHEMA = {
    "finding": "configuration_control",
    "control": "invariance (①) | sufficiency (②) | nutation_twin (③)",
    "role": "for an invariance row: subject (the node) | witness (the Moon, at the same instant)",
    "entry_point": "the library function called",
    "configuration_sha256": "the identity of the section's configuration these rows control",
    "configuration": "which configuration of the declared set the reading was taken under",
    "epoch_id": "the section row the reading is at",
    "body": "the library's own body integer",
    "body_name": "the library's own name for it",
    "jd": "the dynamical-time Julian day passed -- ⚠ display; `jd_bits` is the value",
    "jd_bits": "⭐ the instant's bit pattern, as the call received it",
    "requested": "⭐ the WHOLE word passed",
    "returned": "the whole word the call returned",
    "ephemeris_requested": "moshier | swiss_file | jpl_file -- the source the request names",
    "nutation": "nonut (FLG_NONUT and nothing else) | default (no non-ephemeris bit)",
    "path_state": "data_files (exactly the pinned set) | empty_directory (verified empty)",
    "longitude": "the call's first returned value -- ⚠ display; `longitude_bits` is the value",
    "longitude_bits": "⭐ its bit pattern",
    "latitude": "the second returned value",
    "latitude_bits": "⭐ its bit pattern",
    "distance": "the third returned value",
    "distance_bits": "⭐ its bit pattern",
    "tidal_constant_after": "the tidal-acceleration constant read back after the call",
    "tidal_constant_after_bits": "⭐ its bit pattern",
    "call_history": "cold_process_per_row (the reading was the only call of a fresh interpreter) | permuted (the "
                    "section read warm, in `call_order`)",
    "call_order": "for a sufficiency row: the section's epochs in the order the regeneration read them",
    "values": "for a sufficiency row: what the regeneration read at the row's epoch -- `values_bits` the value",
    "values_bits": "⭐ its bit pattern",
}


OUTPUTS = ("mean-node-section.jsonl", "mean-node-section-controls.jsonl")


def refuse_existing(out_dir: str) -> dict[str, str]:
    """The two paths, ⛔ refused if either exists: each emission goes to a new path."""
    paths = {name: os.path.join(out_dir, name) for name in OUTPUTS}
    for path in paths.values():
        if os.path.exists(path):
            raise Refusal(f"{path} exists; each emission goes to a new path")
    return paths


def write_files(rows: list[dict], controls: list[dict], context: dict, summary: dict, out_dir: str) -> dict:
    """Both files through the fixture contract; ⛔ refused if either exists."""
    paths = refuse_existing(out_dir)
    fixture, provenance = _contract()
    from importlib.metadata import version as distribution_version

    generator = provenance.generator_for(Path(__file__))
    host = provenance.host_record()
    binding = distribution_version("pyswisseph")
    library = (context["library_version"], "pyswisseph", binding)
    configuration = section_configuration()
    identity = configuration_identity(entry_point=ENTRY_POINT, requested="swiss_file", word=context["word"],
                                      library=library, configuration=configuration)
    for c in controls:
        c["configuration_sha256"] = identity
    controls = [{k: c[k] for k in ("finding", "control", "entry_point", "configuration_sha256")}
                | {k: v for k, v in c.items() if k not in ("finding", "control", "entry_point", "configuration_sha256")}
                for c in controls]
    interval = context["interval"]
    today = provenance.today()
    data_files = {"directory_contents_verified": True, "files": [dict(pin) for pin in EPHE_PINS],
                  "unpinned_file_policy": "refused. The library reads the directory, so a file nobody passed can "
                                          "still answer"}
    common = {"implementation": "Swiss Ephemeris", "library_version": library[0],
              "called_via": {"binding": "pyswisseph", "version": binding}, "host": host}
    epochs_summary = {
        "source": "a data profile manifest's declared coverage, read from the file given and converted back to its own "
                  "strings -- never a typed Julian day; the instants inside it are the mean-node record's calc epochs",
        "profile": interval["profile"], "manifest_sha256": interval["manifest_sha256"], "dataset": interval["dataset"],
        "declared_coverage": interval["declared_coverage"],
        **patterned("start_jd", interval["start"]), **patterned("end_jd", interval["end"]),
        "used_as": "dynamical-time Julian days passed to calc; the coverage's scale is TDB and its difference from TT, "
                   "milliseconds, is not applied",
        "count": len(context["epochs"]),
    }
    section_header = fixture.Header(
        fixture_kind="numeric_pin", reference="R3", generator=generator, generated=today,
        title="The mean lunar node through calc, under the data-file request with the whole word, read warm",
        oracle={
            **common,
            "session": {"generation": "warm: every row read in one fresh child interpreter (-I), in row order, the "
                                      "library's calls recorded inside it and held to the rows",
                        "removed_environment_variables": sorted(k for k in os.environ if k.startswith("SE_"))},
            "data_files": data_files,
            "ephemeris_basis": {
                "library_version": library[0], "called_via": {"binding": "pyswisseph", "version": binding},
                "data_files": {"files": [{"dataset": p["dataset"], "sha256": p["sha256"]} for p in EPHE_PINS]},
                "sections": {SECTION: {"entry_point": ENTRY_POINT, "requested": "swiss_file",
                                       "returned": "swiss_file", "requested_word": context["word"],
                                       "claimed_class": "request_invariant", "generation": "warm_in_row_order",
                                       "configuration": configuration}},
            },
            "licence": "the library is AGPL-3.0; the generator that wrote this file calls it and redistributes none "
                       "of it",
        },
        request={"entry_point": ENTRY_POINT, "body": context["subject"], "requested_word": context["word"],
                 "configuration": SECTION_CONFIGURATION,
                 "epochs": [{"epoch_id": e["epoch_id"], **patterned("jd", e["jd"])} for e in context["epochs"]],
                 "regenerate": "generators/mean_node_section.py --ephe-path <the pinned files' directory> --empty-dir "
                               "<an empty directory> --profile <the data profile manifest> --survey <the survey> "
                               "--out-dir <a directory>"},
        # ⭐ A tolerance, MEASURED here and with no headroom: the largest difference between the row and any other
        #    reading of it the controls took -- none. ⛔ The band a consumer applies is its own; this one is context.
        classification={SECTION: {"class": "tolerance", "band": summary["invariance"]["largest_difference_arcseconds"]
                                  / ARCSECONDS_PER_DEGREE, "unit": SECTION_UNIT}},
        budget_row=BUDGET_ROW,
        row_schema=SECTION_ROW_SCHEMA,
        summary={"configuration_sha256": identity, "epochs": epochs_summary,
                 "controls": {"record": "mean-node-section-controls.jsonl", "invariance": summary["invariance"],
                              "sufficiency": summary["sufficiency"], "nutation_twin": summary["nutation_twin"]},
                 "state_read_back": summary["state_read_back"], "returned_word_every_row": summary["section_returned_word"],
                 "budget_row": "the id its consumer minted for the row this section is compared against. ⛔ The row is "
                               "the consumer's; nothing here asserts it exists"},
        notes=[
            "⭐ A COMPARISON OF A CONVENTION, NEVER OF THE SKY. What one release of the library returned for its mean "
            "lunar node through calc under one declared configuration, at instants inside a data profile's coverage.",
            "⛔ EVERY ROW ASSERTS `none`. The node's returned word hands the request back under every condition built "
            "so that the request cannot be answered, so it reports nothing; what this section stands on instead is "
            "that its value did not move with the request, which the control record shows at every row.",
            "⚠ The band is what this instrument measured between the row and every other reading of it -- no "
            "difference at all -- and is context: the band a comparison applies is its consumer's.",
            "⚠ Dated, versioned and placed deliberately: one release, one binding, one host.",
        ],
    )
    control_header = fixture.Header(
        fixture_kind="provenance_record", reference="R3", generator=generator, generated=today,
        title="The invariance, sufficiency and nutation-twin controls of the mean node's calc section, at every row",
        oracle={
            **common,
            "session": {
                "isolation": "⛔ each invariance and nutation_twin reading is the one call of a fresh child interpreter "
                             "(-I); each sufficiency row was read warm, every row of the section in one fresh child, in "
                             "its call_order; the children run in an empty working directory verified empty after the "
                             "run, and the parent takes no reading",
                "checked": "every call each child made into the library, through the module's and its submodule's "
                           "callables after they were wrapped, was recorded inside it and had to be exactly the "
                           "sequence its rows declare: the directory, then per reading the call with the row's "
                           "instant, body and whole word, and the constant read back. ⚠ Honest error, not forgery",
                "removed_environment_variables": sorted(k for k in os.environ if k.startswith("SE_")),
            },
            "data_files": data_files,
            "empty_directory": {"verified_empty": True, "checked": "before the first reading and after the last"},
            "method": "the node and the Moon read through calc at each section row's instant under each configuration "
                      "of the declared set, the node without FLG_NONUT under the section's own, and the section read "
                      "again warm in the reverse order",
            "survey": {"sha256": summary["survey_edge"]["survey_sha256"],
                       "read": "the witness's coverage_edge row, as bits, to place every witness reading the files "
                               "answered more than a day inside it"},
            "licence": "the library is AGPL-3.0; the generator that wrote this file calls it and redistributes none "
                       "of it",
        },
        attests="that at every row of the mean node's calc section the node read bit-identically under each of five "
                "configurations of request and data-file state, each reading in a fresh process; that at each such "
                "instant the Moon's returned word named a source other than the request where the request could not "
                "be answered, differed between two answering sources, and under the section's configuration was the "
                "request honoured; that the section read again warm in another order was bit-identical; and that each "
                "row read without FLG_NONUT differed",
        authority={"held_by": "the library itself, as observed",
                   "kind": "black-box observation of return values under declared configurations",
                   "scope": "⚠ this version of the library and this binding only, run on the recorded host"},
        record_date=today,
        row_schema=CONTROL_ROW_SCHEMA,
        summary={"configuration_sha256": identity, "section": "mean-node-section.jsonl", "epochs": epochs_summary,
                 **{k: v for k, v in summary.items() if k != "survey_edge"}, "survey_edge": summary["survey_edge"]},
        notes=[
            "⛔ A PROVENANCE RECORD; IT GATES NOTHING ON ITS OWN. It holds what the section's controls read, and every "
            "control passed at every row before either file was written.",
            "⭐ THE WITNESS IS NOT A SUBJECT. The Moon is read so that each row's instant is shown to be one where the "
            "requested source can be told from another; nothing is asserted about the Moon on any row of the section.",
            "⚠ The sufficiency regeneration is warm and permuted, never cold: a cold reading under the section's "
            "configuration is already the invariance part's, and would repeat it rather than check the warm one.",
        ],
    )
    os.makedirs(out_dir, exist_ok=True)
    fixture.write_jsonl(Path(paths["mean-node-section.jsonl"]), section_header, rows, declared_sections=[SECTION])
    fixture.write_jsonl(Path(paths["mean-node-section-controls.jsonl"]), control_header, controls)
    out = {"commit": generator.commit, "configuration_sha256": identity}
    for name, path in paths.items():
        with open(path, "rb") as handle:
            out[name] = hashlib.sha256(handle.read()).hexdigest()
    return out


def generate(ephe_path: str, empty_dir: str, profile: str, survey_path: str, out_dir: str) -> dict:
    _fixture, provenance = _contract()
    provenance.generator_for(Path(__file__))  # ⛔ refuse a dirty tree before anything is measured
    refuse_existing(out_dir)
    verify_data_directory(ephe_path)
    verify_empty_directory(empty_dir)
    survey = read_survey_edges(survey_path)
    work = tempfile.mkdtemp(prefix="mean-node-section-")
    try:
        rows, controls, context = measure(ephe_path, empty_dir, profile, work)
        verify_empty_directory(work)
    finally:
        shutil.rmtree(work, ignore_errors=True)
    verify_data_directory(ephe_path)
    verify_empty_directory(empty_dir)
    summary = check(rows, controls, context, survey)
    return write_files(rows, controls, context, summary, out_dir)


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if argv[:1] == ["--child"]:
        _child(argv[1])
        return 0
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--ephe-path", required=True, help="the pinned data files' directory, and nothing else")
    parser.add_argument("--empty-dir", required=True, help="an empty directory")
    parser.add_argument("--profile", required=True, help="the data profile manifest whose coverage bounds the rows")
    parser.add_argument("--survey", required=True, help="the survey whose coverage_edge rows place the witness")
    parser.add_argument("--out-dir", required=True, help="where the two files are written; neither may exist")
    args = parser.parse_args(argv)
    try:
        written = generate(args.ephe_path, args.empty_dir, args.profile, args.survey, args.out_dir)
    except Refusal as refusal:
        sys.stderr.write(f"refused: {refusal}\n")
        return 2
    sys.stderr.write(json.dumps(written, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
