"""R3 — the Swiss Ephemeris's apparent longitudes, per body, over an earlier cutover survey's grid, through the TT entry.

Twelve bodies (the Sun, the Moon, Mercury to Pluto, the mean node and the true node), tropical, apparent with the
library's default corrections, with speed, through the terrestrial-time Julian-day entry point (``calc``) — so no
offset from civil to dynamical time enters a comparison made against these rows — under two configurations: the
data-file request with the pinned data files, and the analytical request with no data file present. Every value is
written down as the library returned it, with its bit pattern, the word it was asked under, the word it returned,
and how its source was established.

* ⭐ **The grid is the earlier survey's, re-derived, and held to that survey's own report.** Its rule, written out in
  :data:`GRID_RULE` and :func:`cutover_grid`, reproduces the report's instant count, first instant and last instant
  exactly, or nothing is read. The survey's instants are civil UTC; each is converted the way the survey converted
  it (the library's ``utc_to_jd`` with the data files on the path), in a fresh process of its own, and the
  terrestrial time that conversion returned is the argument handed to ``calc`` — written on the row with its bits.
  The same conversion with an empty directory on the path is recorded beside it, ⛔ never used.
* ⭐ **Plus the instants of an earlier geocentric values file that name three goldens** (the 1855 instant, the 2145
  quarters, the 1995-10-24 window), each at the terrestrial time a time-argument file gives it, read by digest: the
  two parts that file records, summed in one addition shown on the row.
* ⭐ **One reading per fresh interpreter (``-I``)**, admitted only if the calls it made into the library are exactly
  the ones its row declares (Saakshi's reading child). ⛔ No reading is taken in this process.
* ⭐ **Every row's source is asserted by a survey taken in the same run, through the same entry point**: each body's
  returned word read where the request cannot be answered (an empty directory, an absent file, an instant centuries
  outside its own coverage edge — the edge located through ``calc``, in TT). A body whose word was shown to report
  is ``reported`` where its returned source is the requested one; a body whose word was shown to hand the request
  back is ``none``, the refusal, with the reason; ⛔ a returned source other than the request is a refused row,
  recorded, never a value; a body with no verdict is refused too.
* ⭐ **The library's apparent-position switches, measured** (a probe's evidence): at fifty grid instants, every body,
  each configuration, under every combination of the three switches the library offers — true position (no light
  time), no aberration, no light deflection — singly, in pairs and together; each switched reading beside the
  default one, the difference with its bits. ⛔ Nothing here says what any switch does.
* ⛔ **No band, no verdict, no derived value** beyond the one conversion and the one addition shown. Every section
  is ``reference_only``.
* ⛔ **Recorder, never explainer.** Nothing here says how the library computes anything.

Usage:
    python generators/r3_cutover_grid.py --ephe-path DIR --empty-dir DIR \\
        --survey-report FILE --survey-report-sha256 HEX \\
        --grid-values FILE --grid-values-sha256 HEX --tt-from FILE --tt-from-sha256 HEX \\
        --budget-row ROW --out DIR [--workers N] [--plan-only]
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from importlib.metadata import version as _distribution_version
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping

HERE = Path(__file__).resolve().parent
sys.dont_write_bytecode = True
for _path in (str(HERE.parent / "src"), str(HERE)):
    if _path not in sys.path:
        sys.path.insert(0, _path)

import swisseph as swe  # noqa: E402

from saakshi import swiss  # noqa: E402
from saakshi.fixture import Header, bits, describe_reserved_names, write_jsonl  # noqa: E402
from saakshi.provenance import generator_for, host_record, today  # noqa: E402

SCRIPT = "generators/r3_cutover_grid.py"
VALUES_PATH = "swiss/r3-cutover-longitudes.jsonl"
SURVEY_PATH = "swiss/r3-cutover-reporting-survey.jsonl"
BINDING_VERSION = _distribution_version("pyswisseph")
ENTRY_POINT = "calc"


class Refusal(Exception):
    """A condition under which nothing may be written."""


# ======================================================================================
# The grid: the earlier survey's rule, re-derived
# ======================================================================================

GRID_START = dt.datetime(1849, 12, 28, tzinfo=dt.timezone.utc)
GRID_END = dt.datetime(2150, 1, 20, tzinfo=dt.timezone.utc)  # exclusive
DENSE_START = dt.datetime(1900, 1, 1, tzinfo=dt.timezone.utc)  # inclusive
DENSE_END = dt.datetime(2050, 1, 1, tzinfo=dt.timezone.utc)  # exclusive
DENSE_STEP_DAYS, SPARSE_STEP_DAYS = 5, 15
OFFSET_STRIDE_SECONDS, SECONDS_PER_DAY = 37_991, 86_400

GRID_RULE = (
    "the earlier survey's grid, re-derived: civil UTC instants from 1849-12-28 00:00:00 while before 2150-01-20 "
    "00:00:00; the step after an instant is 5 days where the instant (before its offset) is on or after 1900-01-01 "
    "and before 2050-01-01, else 15 days; the i-th instant (from 0) is that day plus (i x 37991) mod 86400 seconds"
)

#: What the earlier survey's own report must say about its grid, field for field.
REPORT_GRID_FIELDS: tuple[str, ...] = ("n_epochs", "first", "last")


def cutover_grid() -> list[dt.datetime]:
    out: list[dt.datetime] = []
    cur, i = GRID_START, 0
    while cur < GRID_END:
        step = DENSE_STEP_DAYS if DENSE_START <= cur < DENSE_END else SPARSE_STEP_DAYS
        out.append(cur + dt.timedelta(seconds=(i * OFFSET_STRIDE_SECONDS) % SECONDS_PER_DAY))
        cur += dt.timedelta(days=step)
        i += 1
    return out


def reproduce(report_path: Path, expected_sha256: str, grid: list[dt.datetime]) -> dict[str, Any]:
    """⛔ The re-derived grid must give the report's count, first and last instant, exactly, or nothing is read."""
    data = report_path.read_bytes()
    actual = hashlib.sha256(data).hexdigest()
    if actual != expected_sha256:
        raise Refusal(f"the survey report's sha256 is {actual}, not {expected_sha256}")
    stated = json.loads(data)["grid"]
    derived = {"n_epochs": len(grid), "first": grid[0].isoformat(), "last": grid[-1].isoformat()}
    for field in REPORT_GRID_FIELDS:
        if stated[field] != derived[field]:
            raise Refusal(f"⛔ STOP: the rule does not reproduce the survey's {field}: {derived[field]!r} against "
                          f"{stated[field]!r}")
    return {"report_sha256": actual, "stated": stated, "reproduced": derived}


# ======================================================================================
# The golden instants, and the terrestrial time each is read at
# ======================================================================================

GOLDEN_REASONS: tuple[str, ...] = ("golden_1855", "golden_2145", "golden_1995_10_24")


def golden_instants(values_path: Path, expected_sha256: str) -> list[dict[str, Any]]:
    """The instants of an earlier geocentric values file whose reasons name one of the three goldens."""
    data = values_path.read_bytes()
    actual = hashlib.sha256(data).hexdigest()
    if actual != expected_sha256:
        raise Refusal(f"the values file's sha256 is {actual}, not {expected_sha256}")
    header = json.loads(data.split(b"\n", 1)[0])
    chosen = []
    for entry in header["request"]["instants"]["values"]:
        named = [r for r in entry["reasons"] if r in GOLDEN_REASONS]
        if named:
            if bits(float(entry["jd_tdb"])) != entry["jd_tdb_bits"]:
                raise Refusal(f"an instant and its pattern are different numbers: {entry['jd_tdb']!r}")
            chosen.append({"jd_tdb": float(entry["jd_tdb"]), "jd_tdb_bits": entry["jd_tdb_bits"], "golden": named[0],
                           "civil_tdb": entry.get("civil_tdb")})
    if {c["golden"] for c in chosen} != set(GOLDEN_REASONS):
        raise Refusal("the values file does not name every golden asked for")
    return chosen


def golden_time_arguments(goldens: list[dict[str, Any]], tt_path: Path, expected_sha256: str
                          ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Each golden's terrestrial time, from a time-argument file's two parts: ``tt = part_1 + part_2``, one addition."""
    data = tt_path.read_bytes()
    actual = hashlib.sha256(data).hexdigest()
    if actual != expected_sha256:
        raise Refusal(f"the time-argument file's sha256 is {actual}, not {expected_sha256}")
    lines = data.decode("utf-8").splitlines()
    header = json.loads(lines[0])
    by_tdb: dict[str, dict[str, Any]] = {}
    for line in lines[1:]:
        row = json.loads(line)
        if row.get("section") == "time_argument":
            by_tdb[row["jd_tdb_bits"]] = row
    out = []
    for golden in goldens:
        row = by_tdb.get(golden["jd_tdb_bits"])
        if row is None:
            raise Refusal(f"the time-argument file has no row for TDB {golden['jd_tdb']!r}")
        parts = [swiss.value_of_bits(p) for p in row["tt_parts_bits"]]
        if [bits(p) for p in parts] != row["tt_parts_bits"] or len(parts) != 2:
            raise Refusal("a time-argument row's two parts are not two doubles")
        jd_tt = parts[0] + parts[1]
        out.append({**golden, "tt_parts": parts, "tt_parts_bits": row["tt_parts_bits"], "jd_tt": jd_tt,
                    "jd_tt_bits": bits(jd_tt)})
    source = {"sha256": actual, "title": header.get("title"), "generator": header.get("generator"),
              "routine": (header.get("oracle") or {}).get("time_argument"),
              "rule": "jd_tt = tt_parts[0] + tt_parts[1], one IEEE-754 double addition"}
    return out, source


# ======================================================================================
# What is read, and how
# ======================================================================================

BODIES: tuple[tuple[int, str], ...] = (
    (swe.SUN, "sun"), (swe.MOON, "moon"), (swe.MERCURY, "mercury"), (swe.VENUS, "venus"), (swe.MARS, "mars"),
    (swe.JUPITER, "jupiter"), (swe.SATURN, "saturn"), (swe.URANUS, "uranus"), (swe.NEPTUNE, "neptune"),
    (swe.PLUTO, "pluto"), (swe.MEAN_NODE, "mean_node"), (swe.TRUE_NODE, "true_node"),
)

#: The configurations, each a requested source and a directory on the path.
CONFIGURATIONS: dict[str, dict[str, Any]] = {
    "swiss_file": {"source": "swiss_file", "path_state": "data_files",
                   "label": "the data-file request, the pinned data files on the path"},
    "moshier_files_absent": {"source": "moshier", "path_state": "empty_directory",
                             "label": "the analytical request, an empty directory on the path"},
}
#: ⚠ A control at the probe's instants only: the analytical request with the data files on the path, the state
#: the earlier survey read its analytical side in. ⛔ Not a configuration of the grid.
CONTROL_CONFIGURATION: dict[str, dict[str, Any]] = {
    "moshier_files_present": {"source": "moshier", "path_state": "data_files",
                              "label": "the analytical request, the pinned data files on the path (control)"},
}

BASE_WORD = swe.FLG_SPEED
SWITCHES: tuple[tuple[str, int], ...] = (
    ("true_position", swe.FLG_TRUEPOS), ("no_aberration", swe.FLG_NOABERR), ("no_deflection", swe.FLG_NOGDEFL),
)


def switch_words() -> list[tuple[tuple[str, ...], int]]:
    """Every combination of the three switches, the default (none) first, each with its non-ephemeris bits."""
    out = []
    for mask in range(1 << len(SWITCHES)):
        names = tuple(name for k, (name, _flag) in enumerate(SWITCHES) if mask >> k & 1)
        word = BASE_WORD
        for k, (_name, flag) in enumerate(SWITCHES):
            if mask >> k & 1:
                word |= flag
        out.append((names, word))
    return out


PROBE_INSTANTS = 50


def probe_indices(n: int) -> list[int]:
    """Fifty grid indices, evenly spread, both ends included: round(k (n - 1) / 49)."""
    return sorted({round(k * (n - 1) / (PROBE_INSTANTS - 1)) for k in range(PROBE_INSTANTS)})


#: ⭐ The child a conversion is made in: the path, then the one conversion, every call recorded.
_CONVERSION_CHILD = r"""
import json
import os
import struct
import sys
import types

fresh = "swisseph" not in sys.modules
import swisseph as swe


def bits(x):
    return struct.pack(">d", x).hex()


def value(h):
    return struct.unpack(">d", bytes.fromhex(h))[0]


calls = []


def recorded(name, function):
    def call(*args, **keywords):
        calls.append({"function": name, "args": [bits(a) if isinstance(a, float) else a for a in args],
                      "keywords": sorted(keywords)})
        return function(*args, **keywords)
    return call


def wrap(module, prefix):
    for name in dir(module):
        member = getattr(module, name)
        if name.startswith("_") or isinstance(member, type):
            continue
        if isinstance(member, types.ModuleType):
            if member.__name__.startswith(swe.__name__ + "."):
                wrap(member, prefix + name + ".")
        elif callable(member):
            setattr(module, name, recorded(prefix + name, member))


wrap(swe, "")
spec = json.loads(sys.stdin.read())
swe.set_ephe_path(spec["path"])
y, m, d, h, mi = spec["civil"]
returned = swe.utc_to_jd(y, m, d, h, mi, value(spec["seconds_bits"]), swe.GREG_CAL)
sys.stdout.write(json.dumps({"nonce": os.urandom(16).hex(), "fresh_interpreter": fresh, "calls": calls,
                             "returned_bits": [bits(float(v)) for v in returned]}))
"""


def conversion_spec(instant: dt.datetime, path: str) -> dict[str, Any]:
    return {"path": path, "civil": [instant.year, instant.month, instant.day, instant.hour, instant.minute],
            "seconds_bits": bits(float(instant.second + instant.microsecond / 1e6))}


def declared_conversion_calls(spec: Mapping[str, Any]) -> list[dict[str, Any]]:
    return [{"function": "set_ephe_path", "args": [spec["path"]], "keywords": []},
            {"function": "utc_to_jd", "args": [*spec["civil"], spec["seconds_bits"], swe.GREG_CAL], "keywords": []}]


def run_conversion_child(spec: Mapping[str, Any], *, work_dir: str) -> dict[str, Any]:
    proc = subprocess.run([sys.executable, "-I", "-c", _CONVERSION_CHILD], input=json.dumps(dict(spec)),
                          cwd=work_dir, env=swiss.child_environment(), capture_output=True, text=True,
                          timeout=swiss.CHILD_TIMEOUT_SECONDS, check=False)
    if proc.returncode != 0:
        raise Refusal(f"a conversion child failed ({proc.returncode}): {proc.stderr.strip()[-300:]}")
    result = json.loads(proc.stdout)
    if not result["fresh_interpreter"]:
        raise Refusal("a conversion child had the library loaded before it was asked")
    if result["calls"] != declared_conversion_calls(spec):
        raise Refusal(f"a conversion child's calls were {[c['function'] for c in result['calls']]}")
    if len(result["returned_bits"]) != 2:
        raise Refusal(f"a conversion returned {len(result['returned_bits'])} values, not two")
    return result


def run_all(specs: list[dict[str, Any]], run: Callable[..., dict[str, Any]], *, work_dir: str, workers: int
            ) -> list[dict[str, Any]]:
    """Every child, at most ``workers`` at once, results in the order asked. ⛔ Two results from one child refuse."""
    with ThreadPoolExecutor(max_workers=workers) as pool:
        results = list(pool.map(lambda s: run(s, work_dir=work_dir), specs))
    nonces = [r["nonce"] for r in results]
    if len(set(nonces)) != len(nonces):
        raise Refusal("two results came back from one child")
    return results


# ======================================================================================
# Assertions of source, row by row
# ======================================================================================


def assertion_for(config: Mapping[str, Any], *, body: int, word: int, returned: int,
                  attested: Mapping[tuple[str, int, int], str], where: str) -> dict[str, Any]:
    """``reported``, or ``none`` for a body whose word was shown to echo. ⛔ Raises for anything else."""
    mode = swiss.MODES[config["source"]]
    if (returned & swiss.SOURCE_MASK) != mode.flag:
        raise swiss.EphemerisSubstitution(f"{where}: requested {mode.source}, answered by "
                                           f"{swiss.source_name(returned)}")
    verdict = attested.get((ENTRY_POINT, body, word & ~swiss.SOURCE_MASK))
    if verdict == swiss.ECHOES:
        return {"kind": "none", "reason": "returned_word_echoes", "requested": mode.source, "returned_flag": returned,
                "evidence": "this body's returned word through calc was measured, in this run's survey, handing "
                            "the request back under every condition where the request could not be answered; "
                            "a flag naming the requested source is therefore no report of it"}
    return swiss.assert_reported(mode, returned, body=body, word=word, attested=attested, where=where,
                                 entry_point=ENTRY_POINT)


#: ⛔ The share of one configuration's readings of one body that may be refused before the run stops.
SYSTEMATIC_SHARE = 0.01


def longitude_rows(section: str, config: Mapping[str, Any], points: list[dict[str, Any]],
                   results: list[dict[str, Any]], specs: list[dict[str, Any]],
                   attested: Mapping[tuple[str, int, int], str]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows, refused = [], []
    for point, spec, result in zip(points, specs, results):
        body, word, returned = spec["body"], spec["word"], int(result["returned"])
        where = f"{section}/{point['epoch_id']}/{point['body_name']}/{word}"
        try:
            assertion = assertion_for(config, body=body, word=word, returned=returned, attested=attested,
                                      where=where)
        except (swiss.EphemerisSubstitution, swiss.UnattestedReport) as exc:
            refused.append({"section": section, "epoch_id": point["epoch_id"], "body": point["body_name"],
                            "requested_word": word, "returned_word": returned, "error": type(exc).__name__,
                            "detail": str(exc)[:240]})
            continue
        if len(result["values_bits"]) != 6:
            raise Refusal(f"{where}: {len(result['values_bits'])} values returned, not six")
        values = [swiss.value_of_bits(p) for p in result["values_bits"]]
        row = {"section": section, "epoch_id": point["epoch_id"], "stratum": point["stratum"],
               "jd_tt": spec_jd(spec), "jd_tt_bits": spec["jd_bits"], "body": point["body_name"], "body_number": body,
               "requested_word": word, "returned_word": returned, "unit": UNIT, "values": values,
               "values_bits": list(result["values_bits"]), "source_assertion": assertion}
        if "switches" in point:
            row["switches"] = list(point["switches"])
        rows.append(row)
    for config_body in {(r["section"], r["body"]) for r in refused}:
        total = sum(1 for p in points if p["body_name"] == config_body[1])
        count = sum(1 for r in refused if (r["section"], r["body"]) == config_body)
        if count > SYSTEMATIC_SHARE * total:
            raise Refusal(f"⛔ STOP: {count} of {total} readings of {config_body[1]} in {section} refused — systematic")
    return rows, refused


UNIT = "degree, degree, au, degree/day, degree/day, au/day"


def spec_jd(spec: Mapping[str, Any]) -> float:
    return swiss.value_of_bits(spec["jd_bits"])


def wrapped(a: float, b: float) -> float:
    """``a - b`` in degrees, folded into (-180, 180]."""
    d = (a - b) % 360.0
    return d - 360.0 if d > 180.0 else d


def with_differences(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """⭐ Each switched reading beside its default one: the component-wise difference (the longitude folded), bits."""
    default = {(r["section"], r["epoch_id"], r["body"]): r for r in rows if not r["switches"]}
    for row in rows:
        if not row["switches"]:
            continue
        base = default.get((row["section"], row["epoch_id"], row["body"]))
        if base is None:
            raise Refusal(f"a switched reading of {row['body']} at {row['epoch_id']} has no default reading beside it")
        diff = [wrapped(row["values"][0], base["values"][0])] + [
            a - b for a, b in zip(row["values"][1:], base["values"][1:])]
        row["difference_from_default"] = diff
        row["difference_from_default_bits"] = [bits(v) for v in diff]
    return rows


# ======================================================================================
# The run
# ======================================================================================


def verify_empty(path: Path, when: str) -> None:
    if any(path.iterdir()):
        raise Refusal(f"the directory given as empty holds entries {when}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--ephe-path", required=True, type=Path)
    parser.add_argument("--empty-dir", required=True, type=Path)
    parser.add_argument("--survey-report", required=True, type=Path)
    parser.add_argument("--survey-report-sha256", required=True)
    parser.add_argument("--grid-values", required=True, type=Path)
    parser.add_argument("--grid-values-sha256", required=True)
    parser.add_argument("--tt-from", required=True, type=Path)
    parser.add_argument("--tt-from-sha256", required=True)
    parser.add_argument("--budget-row", required=True, help="⚠ a placeholder name; the consumer labels its rows")
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--plan-only", action="store_true")
    args = parser.parse_args(argv)

    generator = None if args.plan_only else generator_for(HERE / Path(SCRIPT).name)
    print(describe_reserved_names())
    grid = cutover_grid()
    reproduced = reproduce(args.survey_report, args.survey_report_sha256, grid)
    goldens = golden_instants(args.grid_values, args.grid_values_sha256)
    goldens, tt_source = golden_time_arguments(goldens, args.tt_from, args.tt_from_sha256)
    probes = probe_indices(len(grid))
    words = switch_words()
    n_long = (len(grid) + len(goldens)) * len(BODIES) * len(CONFIGURATIONS)
    n_probe = len(probes) * len(BODIES) * (len(words) * len(CONFIGURATIONS) + 1)
    print(f"grid {len(grid)} instants reproduced ({reproduced['reproduced']['first']} .. "
          f"{reproduced['reproduced']['last']}); {len(goldens)} golden instants; {2 * len(grid)} conversions; "
          f"{n_long} longitude readings; {n_probe} probe readings; workers {args.workers}", flush=True)
    if args.plan_only:
        return 0
    for path in (args.out / VALUES_PATH, args.out / SURVEY_PATH):
        if path.exists():
            raise Refusal(f"{path} exists; a record is never overwritten")
    ephe_pins = swiss.verify_ephe_set(args.ephe_path)
    ephe_identity = swiss.ephe_set_identity(args.ephe_path, ephe_pins)
    verify_empty(args.empty_dir, "before the first reading")
    paths = {"data_files": str(args.ephe_path.resolve()), "empty_directory": str(args.empty_dir.resolve())}

    # --- the survey: which bodies' words report, through calc, under every word read here ---------------------
    keys = sorted({word & ~swiss.SOURCE_MASK for _names, word in words})
    survey = swiss.measure_reporting(bodies=[b for b, _n in BODIES], keys=keys, ephe_path=args.ephe_path,
                                     sidereal_mode=swe.SIDM_LAHIRI, entry_point=ENTRY_POINT)
    attested = survey["attested"]
    print(f"survey: {sum(1 for v in attested.values() if v == swiss.REPORTS)} reports, "
          f"{sum(1 for v in attested.values() if v == swiss.ECHOES)} echoes, "
          f"{sum(1 for v in attested.values() if v == swiss.UNCOVERED)} uncovered", flush=True)

    with tempfile.TemporaryDirectory() as work:
        # --- the conversions ---------------------------------------------------------------------------------
        conv_specs = {state: [conversion_spec(t, paths[state]) for t in grid] for state in ("data_files",
                                                                                          "empty_directory")}
        converted = {state: run_all(specs, run_conversion_child, work_dir=work, workers=args.workers)
                     for state, specs in conv_specs.items()}
        points: list[dict[str, Any]] = []
        conversion_rows = []
        for i, instant in enumerate(grid):
            passed = converted["data_files"][i]["returned_bits"]
            control = converted["empty_directory"][i]["returned_bits"]
            epoch_id = f"c{i:05d}"
            conversion_rows.append({
                "section": "time_conversion", "epoch_id": epoch_id, "index": i, "civil_utc": instant.isoformat(),
                "offset_seconds": (i * OFFSET_STRIDE_SECONDS) % SECONDS_PER_DAY,
                "utc_to_jd_data_files": [swiss.value_of_bits(p) for p in passed],
                "utc_to_jd_data_files_bits": list(passed),
                "utc_to_jd_empty_directory": [swiss.value_of_bits(p) for p in control],
                "utc_to_jd_empty_directory_bits": list(control),
                "jd_tt_passed": swiss.value_of_bits(passed[0]), "jd_tt_passed_bits": passed[0]})
            points.append({"epoch_id": epoch_id, "stratum": "cutover_grid", "jd_tt_bits": passed[0]})
        golden_rows = []
        for k, g in enumerate(goldens):
            epoch_id = f"g{k:02d}"
            golden_rows.append({"section": "golden_time_argument", "epoch_id": epoch_id, "golden": g["golden"],
                                "jd_tdb": g["jd_tdb"], "jd_tdb_bits": g["jd_tdb_bits"], "civil_tdb": g["civil_tdb"],
                                "tt_parts": g["tt_parts"], "tt_parts_bits": g["tt_parts_bits"], "jd_tt": g["jd_tt"],
                                "jd_tt_bits": g["jd_tt_bits"]})
            points.append({"epoch_id": epoch_id, "stratum": g["golden"], "jd_tt_bits": g["jd_tt_bits"]})

        # --- the longitudes ------------------------------------------------------------------------------------
        sections: dict[str, list[dict[str, Any]]] = {}
        refused_all: list[dict[str, Any]] = []

        def read(section: str, config: Mapping[str, Any], at: Iterable[dict[str, Any]],
                 word_list: list[tuple[tuple[str, ...], int]]) -> None:
            mode = swiss.MODES[config["source"]]
            planned, specs = [], []
            for point in at:
                for names, word in word_list:
                    for body, name in BODIES:
                        planned.append({**point, "body_name": name, **({"switches": names} if len(word_list) > 1
                                                                        else {})})
                        specs.append({"path": paths[config["path_state"]], "sidereal_mode": None,
                                      "entry_point": ENTRY_POINT, "jd_bits": point["jd_tt_bits"], "body": body,
                                      "word": mode.flag | word})
            results = run_all(specs, swiss.run_reading_child, work_dir=work, workers=args.workers)
            rows, refused = longitude_rows(section, config, planned, results, specs, attested)
            sections[section] = with_differences(rows) if len(word_list) > 1 else rows
            refused_all.extend(refused)
            print(f"  {section}: {len(rows)} rows, {len(refused)} refused", flush=True)

        default_word = [((), BASE_WORD)]
        for name, config in CONFIGURATIONS.items():
            read(name, config, points, default_word)
        probe_points = [points[i] for i in probes]
        for name, config in CONFIGURATIONS.items():
            read(f"flag_semantics_{name}", config, probe_points, words)
        for name, config in CONTROL_CONFIGURATION.items():
            read(f"control_{name}", config, probe_points, default_word)
        verify_empty(Path(work), "after the last reading (the work directory)")
    verify_empty(args.empty_dir, "after the last reading")

    # ⭐ A determinism control: each probe's default reading is the grid's reading of the same call.
    mismatches = 0
    for name in CONFIGURATIONS:
        index = {(r["epoch_id"], r["body"]): r for r in sections[name]}
        for row in sections[f"flag_semantics_{name}"]:
            if not row["switches"] and (row["epoch_id"], row["body"]) in index:
                if index[(row["epoch_id"], row["body"])]["values_bits"] != row["values_bits"]:
                    mismatches += 1
    if mismatches:
        raise Refusal(f"⛔ STOP: {mismatches} probe default readings differ from the grid's reading of the same call")

    # ⭐ The mean node across the two configurations, counted, never explained.
    node_same = node_total = 0
    a = {(r["epoch_id"]): r for r in sections["swiss_file"] if r["body"] == "mean_node"}
    for r in sections["moshier_files_absent"]:
        if r["body"] == "mean_node" and r["epoch_id"] in a:
            node_total += 1
            node_same += a[r["epoch_id"]]["values_bits"] == r["values_bits"]

    rows = conversion_rows + golden_rows + [row for rows_ in sections.values() for row in rows_]
    section_names = ["time_conversion", "golden_time_argument", *sections]
    configs = {**CONFIGURATIONS, **{f"control_{k}": v for k, v in CONTROL_CONFIGURATION.items()},
               **{f"flag_semantics_{k}": v for k, v in CONFIGURATIONS.items()}}
    basis = {}
    for name in sections:
        config = configs[name]
        basis[name] = {
            "entry_point": ENTRY_POINT, "time_argument": "Julian day, TT",
            "requested_source": config["source"], "path_state": config["path_state"], "label": config["label"],
            "requested_words": sorted({r["requested_word"] for r in sections[name]}),
            "returned": "recorded per row (`returned_word`); its source bits equal the request on every row written",
            "data_files": ephe_identity if config["path_state"] == "data_files" else {"declared_empty_set": True},
        }
    header = Header(
        fixture_kind="numeric_pin",
        reference="R3",
        generator=generator,
        generated=today(),
        title="The Swiss Ephemeris's apparent longitudes per body over an earlier cutover survey's grid, through TT",
        oracle={
            "implementation": "Swiss Ephemeris", "library_version": swe.version,
            "called_via": {"binding": "pyswisseph", "version": BINDING_VERSION},
            "reading": ("⛔ each reading is one call in a fresh child interpreter (-I), its working directory "
                        "verified empty after the run, every SE_ environment variable removed; every call the child "
                        "made into the library was recorded inside it and had to be exactly the row's: the "
                        "directory for its path state and the one reading call with the row's instant, body and "
                        "whole word. ⚠ Honest error, not forgery"),
            "ephemeris_basis": basis,
            "time_argument": {
                "grid": "the TT the library's utc_to_jd returned (its first value) for the row's civil UTC instant, "
                        "in a fresh child with the pinned data files on the path — the state the earlier survey "
                        "converted in; the same conversion with an empty directory on the path is recorded beside "
                        "it in `time_conversion` and never used",
                "goldens": tt_source,
            },
            "survey": {"path": SURVEY_PATH, "entry_point": ENTRY_POINT,
                       "verdicts": [{"body": name, "body_number": body, "non_ephemeris_key": key,
                                     "verdict": attested[(ENTRY_POINT, body, key)]}
                                    for body, name in BODIES for key in keys]},
            "host": host_record(),
            "licence": "the library is AGPL-3.0; it is called here, never redistributed by this repository",
        },
        request={
            "grid": {"rule": GRID_RULE, **reproduced, "count": len(grid)},
            "goldens": {"from_values_file_sha256": args.grid_values_sha256, "reasons": list(GOLDEN_REASONS),
                        "count": len(goldens)},
            "bodies": [{"body": n, "body_number": b} for b, n in BODIES],
            "configurations": CONFIGURATIONS, "control": CONTROL_CONFIGURATION,
            "word": {"default": BASE_WORD, "meaning": "the speed bit and the source bit; the library's default "
                                                      "corrections otherwise"},
            "switches": [{"switch": n, "bit": f} for n, f in SWITCHES],
            "probe": {"instants": len(probes), "rule": "grid indices round(k (n - 1) / 49), k = 0 .. 49",
                      "indices": probes, "words": [{"switches": list(n), "word": w} for n, w in words]},
            "regenerate": f"{SCRIPT} --ephe-path <pinned files> --empty-dir <empty> --survey-report <report> "
                          "--survey-report-sha256 <hex> --grid-values <values> --grid-values-sha256 <hex> "
                          "--tt-from <time arguments> --tt-from-sha256 <hex> --budget-row <row> --out <dir>",
        },
        classification={name: {"class": "reference_only"} for name in section_names},
        budget_row=args.budget_row,
        row_schema={
            "section": " | ".join(section_names),
            "epoch_id": "c<grid index> for the grid, g<n> for a golden instant",
            "civil_utc": "time_conversion: the grid's civil UTC instant, as the earlier survey's rule makes it",
            "utc_to_jd_data_files": "time_conversion: the library's utc_to_jd return, data files on the path",
            "utc_to_jd_empty_directory": "time_conversion: the same with an empty directory on the path (never used)",
            "jd_tt_passed": "time_conversion: the TT handed to calc for this instant",
            "tt_parts": "golden_time_argument: the two parts the time-argument file records",
            "jd_tt": "the TT handed to calc — ⚠ display; `jd_tt_bits` is the value",
            "requested_word": "the whole word asked", "returned_word": "the whole word returned",
            "values": "longitude, latitude, distance, and their speeds — ⚠ display; `values_bits` is the value",
            "switches": "flag_semantics sections: the switches set ([] = the default call)",
            "difference_from_default": "flag_semantics sections: this reading minus the default one, component-wise, "
                                       "the longitude folded into (-180, 180]",
            "source_assertion": "reported | none, as the survey taken in the same run shows it",
        },
        summary={
            "rows_by_section": {name: sum(1 for r in rows if r["section"] == name) for name in section_names},
            "refused": {"count": len(refused_all), "rows": refused_all[:200]},
            "probe_default_equals_grid_reading": {"compared": sum(
                1 for name in CONFIGURATIONS for r in sections[f"flag_semantics_{name}"] if not r["switches"]),
                "differing": mismatches},
            "mean_node_bit_identical_across_configurations": {"compared": node_total, "identical": node_same},
            "conversions_differing_between_path_states": sum(
                1 for r in conversion_rows if r["utc_to_jd_data_files_bits"] != r["utc_to_jd_empty_directory_bits"]),
            "host": host_record(),
        },
        notes=[
            "⛔ Recorder, never explainer. Nothing here says how the library computes anything or what a switch does.",
            "⛔ reference_only, with no band.",
            "⭐ The grid reproduces the earlier survey's own report exactly (count, first, last); the earlier survey "
            "read through the universal-time entry point, these rows through the terrestrial-time one at the TT its "
            "own conversion gives.",
            "⚠ The mean node's returned word hands the request back (the survey in this run), so its rows assert "
            "`none`; whether its values move between the configurations is counted in the summary.",
        ],
    )
    written = write_jsonl(args.out / VALUES_PATH, header, rows, declared_sections=section_names)
    values_sha256 = hashlib.sha256((args.out / VALUES_PATH).read_bytes()).hexdigest()
    survey_header = Header(
        fixture_kind="provenance_record",
        reference="R3",
        generator=generator,
        generated=today(),
        title="Which bodies' returned words report their source through the terrestrial-time entry point",
        oracle={"implementation": "Swiss Ephemeris", "library_version": swe.version,
                "called_via": {"binding": "pyswisseph", "version": BINDING_VERSION},
                "method": survey["evidence"]["method"], "entry_point": ENTRY_POINT,
                "data_files": ephe_identity, "values_file": {"path": VALUES_PATH, "sha256": values_sha256}},
        attests=("for each body and each word read in the values file named, whether the word the library returns "
                 "through calc reports the ephemeris that answered, or hands the request back, measured where the "
                 "request could not be answered; and each body's coverage edge through calc, in TT"),
        authority={"held_by": "the library itself, as observed",
                   "kind": "direct observation of return values under controlled conditions",
                   "scope": "⚠ this version of the library and this binding only"},
        record_date=today(),
        row_schema={"finding": "verdict | coverage_edge | returned_flag_by_body"},
        summary={"verdicts": [{"body": name, "body_number": b, "non_ephemeris_key": key,
                               "verdict": attested[(ENTRY_POINT, b, key)]} for b, name in BODIES for key in keys]},
        notes=["⛔ Recorder, never explainer."],
    )
    survey_rows = ([{"finding": "verdict", **v} for v in survey["evidence"]["verdicts"]]
                   + [{"finding": "coverage_edge", **e} for e in survey["evidence"]["edges"]]
                   + list(survey["evidence"]["readings"]))
    write_jsonl(args.out / SURVEY_PATH, survey_header, survey_rows)
    print(f"wrote {written} rows -> {args.out / VALUES_PATH} (sha256 {values_sha256[:16]}...); survey -> "
          f"{args.out / SURVEY_PATH}; refused {len(refused_all)}; mean node identical {node_same}/{node_total}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (Refusal, swiss.ReadingRefused, swiss.SurveyRefusal, swiss.EphemerisSubstitution) as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        raise SystemExit(2)
