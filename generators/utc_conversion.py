"""The civil-time conversion read on the value a caller keeps — the universal one.

`utc_to_jd` returns two Julian days, a dynamical one and a universal one. A caller may keep only
the second::

    _jd_et, jd_ut = swe.utc_to_jd(year, month, day, hour, minute, second, swe.GREG_CAL)

and `src/saakshi/conventions.py`'s leap-second emission differences only the first. So its rows
say where the **dynamical** value steps; ⛔ they say nothing measured about the value such a
caller consumes. This probe makes the **universal** value its subject and records **both**
returned values on every reading — the two differ by the library's time offset, so only a
record of both can separate a leap step from a change in that offset or in library state.

Five parts, every one of them called the way that caller calls it — positional arguments, the
Gregorian flag, the second as a float:

1. **state** — the 115-instant grid of `deployment_capture.py` (every 1 January and 1 July,
   1972-2027, then 2030, 2035 and 2040; 0h UTC) and eight instants across eras, read under up to
   six recorded library states, each compared with the first: no directory named and the
   conversion the process's first call; the same after a call history; an empty directory; the
   pinned data files' directory; a forced tidal-acceleration constant; a user-defined time offset.
2. **steps** — a one-day bracket (the day before, 0h, and the day, 0h) at every 1 January and
   1 July from 1961 to 2060: where each returned value steps, and by how much.
3. **end** — the day the dynamical value stops holding the table's last offset, located by
   bisection, and what the universal value does across that same day.
4. **second_sixty** — 23:59:59, 23:59:60 and the next day's 00:00:00, on the day before every
   whole-second step part 2 found and on six days it did not find.
5. **override** — one file of the documented name holding one invented insertion, in a named
   directory, in the working directory with no directory named, and in the working directory with
   another directory named.

⛔ **Recorder, never explainer.** Nothing here describes how the library computes anything; a
relation between two outputs is recorded as numbers, never as a mechanism.

⛔ **Every reading set is taken in a fresh child process.** The library holds process-wide state
and reads its leap table once per process (`src/saakshi/conventions.py`), so a reading taken
after another state was set reports that state. Children run in an empty working directory of
their own unless a part says otherwise, with every `SE_` environment variable removed — the
removal is recorded, never silent.

⛔ **The standard library and the binding only**, as `deployment_capture.py`: the observation is
one JSON line carrying the probe's own SHA-256, and a second line carrying the observation's.
It writes nothing except temporary directories, which it removes.

Usage::

    python utc_conversion.py [--ephe-path DIR] [--full]
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
from importlib.metadata import PackageNotFoundError, version as _distribution_version

#: The grid `deployment_capture.py` reads, byte for byte the same instants and the same row
#: rendering, so a digest here is comparable with a digest there.
GRID: tuple[tuple[int, int, int], ...] = tuple(
    (year, month, 1) for year in range(1972, 2028) for month in (1, 7)
) + ((2030, 1, 1), (2035, 1, 1), (2040, 1, 1))

#: Instants across eras the grid does not reach — before the table, inside its first decade's
#: predecessor era, and far past its end. 0h UTC.
ERAS: tuple[tuple[int, int, int], ...] = (
    (1800, 1, 1),
    (1900, 1, 1),
    (1950, 1, 1),
    (1961, 1, 1),
    (1965, 1, 1),
    (1971, 12, 31),
    (2050, 1, 1),
    (2100, 1, 1),
)

#: The years part 2 brackets, and the two days in each it brackets. ⚠ Scanned rather than
#: assumed: a step found on either day is recorded, whatever the step is.
STEP_YEARS: tuple[int, int] = (1961, 2060)
INSERTION_DAYS: tuple[tuple[int, int], ...] = ((1, 1), (7, 1))

#: A change in either value across a one-day bracket larger than this is a step. ⚠ Both values
#: also drift across a day where they carry the time offset's own change — milliseconds at most
#: (part 2 records the largest it saw elsewhere) — and a leap second is a whole second.
BRACKET_STEP_SECONDS = 0.01

#: Part 3's test of "the dynamical value still holds the constant". ⚠ Inside the constant region
#: the value is constant to its resolution at these magnitudes, tens of microseconds.
HANDOVER_TOLERANCE_SECONDS = 1e-4

#: The sixty-first second offered on days part 2 did NOT find a step after: before the table,
#: two dates between insertions, and three past the table's last insertion.
SECOND_SIXTY_UNLISTED: tuple[tuple[int, int, int], ...] = (
    (1971, 12, 31),
    (2015, 12, 31),
    (2017, 6, 30),
    (2017, 12, 31),
    (2020, 12, 31),
    (2035, 12, 31),
)

#: Where part 3's bisection starts (a day inside the constant region) and how far it searches.
HANDOVER_FROM: tuple[int, int, int] = (2020, 1, 1)
HANDOVER_SEARCH_YEARS = 60

#: Part 5: the documented file name, the one invented insertion it carries (a sixty-first second
#: at the end of this day), and the days read either side of it.
LEAP_FILE_NAME = "seleapsec.txt"
OVERRIDE_DATE: tuple[int, int, int] = (2020, 6, 30)
OVERRIDE_READ: tuple[tuple[int, int, int], ...] = (
    (2020, 6, 30),
    (2020, 7, 1),
    (2021, 1, 1),
    (2030, 1, 1),
)

#: Part 1's states. ⭐ The first is the reference every other is compared with.
STATES: tuple[tuple[str, str], ...] = (
    (
        "default_first_call",
        "no directory named; the conversion is the process's first library call",
    ),
    (
        "default_after_call_history",
        "no directory named; first: set_sid_mode(SIDM_LAHIRI, 0, 0), get_ayanamsa_ut, "
        "calc_ut(ECL_NUT) with default flags, calc_ut(SUN and MOON, FLG_MOSEPH | FLG_SIDEREAL | "
        "FLG_SPEED), houses_ex(…, b'W', FLG_SIDEREAL), sidtime — all at JD 2451545.0",
    ),
    ("empty_directory", "set_ephe_path(an empty directory) first"),
    (
        "data_files_directory",
        "set_ephe_path(the directory given as --ephe-path) first; ⛔ only with --ephe-path",
    ),
    (
        "tidal_acceleration_forced",
        "no directory named; set_tid_acc(TIDAL_DE200) first",
    ),
    (
        "user_defined_time_offset",
        "no directory named; set_delta_t_userdef(100 s, in days) first",
    ),
)

#: The forced user-defined time offset of the last state, seconds.
USER_DELTA_T_SECONDS = 100.0

SECONDS_PER_DAY = 86400.0
CHILD_TIMEOUT_SECONDS = 300


def bits(value: float) -> str:
    return struct.pack(">d", value).hex()


def unbits(text: str) -> float:
    return struct.unpack(">d", bytes.fromhex(text))[0]


def iso(year: int, month: int, day: int) -> str:
    return f"{year:04d}-{month:02d}-{day:02d}"


def day_before(year: int, month: int, day: int) -> tuple[int, int, int]:
    previous = datetime.date(year, month, day) - datetime.timedelta(days=1)
    return previous.year, previous.month, previous.day


def day_after(year: int, month: int, day: int) -> tuple[int, int, int]:
    following = datetime.date(year, month, day) + datetime.timedelta(days=1)
    return following.year, following.month, following.day


def sha256_of(path: str) -> tuple[int, str]:
    digest = hashlib.sha256()
    size = 0
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            size += len(block)
            digest.update(block)
    return size, digest.hexdigest()


# ======================================================================================
# The child programs — each run in a fresh interpreter
# ======================================================================================


def _convert(swe, year: int, month: int, day: int, hour: int, minute: int, second: float):
    """The call, as the caller makes it. Returns (dynamical, universal) or a refusal string."""
    try:
        jd_et, jd_ut = swe.utc_to_jd(year, month, day, hour, minute, second, swe.GREG_CAL)
    except Exception as exc:  # noqa: BLE001 - a refusal is the observation
        return f"{type(exc).__name__}: {str(exc)[:160]}"
    return float(jd_et), float(jd_ut)


def _row(swe, year: int, month: int, day: int) -> list[str]:
    """`deployment_capture.py`'s row: the civil day, both outputs and the plain Julian day."""
    result = _convert(swe, year, month, day, 0, 0, 0.0)
    jd0 = swe.julday(year, month, day, 0.0)
    if isinstance(result, str):
        return [iso(year, month, day), "refused", result, bits(jd0)]
    return [iso(year, month, day), bits(result[0]), bits(result[1]), bits(jd0)]


def _call_history(swe) -> None:
    jd = 2451545.0
    swe.set_sid_mode(swe.SIDM_LAHIRI, 0, 0)
    swe.get_ayanamsa_ut(jd)
    swe.calc_ut(jd, swe.ECL_NUT)
    flags = swe.FLG_MOSEPH | swe.FLG_SIDEREAL | swe.FLG_SPEED
    swe.calc_ut(jd, swe.SUN, flags)
    swe.calc_ut(jd, swe.MOON, flags)
    swe.houses_ex(jd, 28.6139, 77.2090, b"W", swe.FLG_SIDEREAL)
    swe.sidtime(jd)


def _child_state(name: str, directory: str) -> dict:
    import swisseph as swe

    if name == "default_after_call_history":
        _call_history(swe)
    elif name in ("empty_directory", "data_files_directory"):
        swe.set_ephe_path(directory)
    elif name == "tidal_acceleration_forced":
        swe.set_tid_acc(swe.TIDAL_DE200)
    elif name == "user_defined_time_offset":
        swe.set_delta_t_userdef(USER_DELTA_T_SECONDS / SECONDS_PER_DAY)
    elif name != "default_first_call":
        raise ValueError(f"no such state: {name}")
    grid = [_row(swe, *instant) for instant in GRID]
    eras = [_row(swe, *instant) for instant in ERAS]
    return {
        "grid": grid,
        "eras": eras,
        "tidal_acceleration_bits_after": bits(swe.get_tid_acc()),
    }


def _child_steps() -> dict:
    import swisseph as swe

    rows = []
    for year in range(STEP_YEARS[0], STEP_YEARS[1] + 1):
        for month, day in INSERTION_DAYS:
            rows.append(_row(swe, *day_before(year, month, day)) + _row(swe, year, month, day))
    return {"rows": rows}


def _child_handover() -> dict:
    import swisseph as swe

    def offset(jd: float) -> tuple[float, tuple[int, int, int]]:
        year, month, day, _hour = swe.revjul(jd)
        civil = (int(year), int(month), int(day))
        jd_et, _jd_ut = swe.utc_to_jd(*civil, 0, 0, 0.0, swe.GREG_CAL)
        return (jd_et - swe.julday(*civil, 0.0)) * SECONDS_PER_DAY, civil

    start = swe.julday(*HANDOVER_FROM, 0.0)
    constant, _ = offset(start)

    def flat(jd: float) -> bool:
        return abs(offset(jd)[0] - constant) <= HANDOVER_TOLERANCE_SECONDS

    end = start + HANDOVER_SEARCH_YEARS * 365.25
    if not flat(start) or flat(end):
        return {"found": False, "constant_bits": bits(constant)}
    inside, outside = start, end
    while outside - inside > 1.0:
        middle = inside + (outside - inside) // 2
        if middle in (inside, outside):
            break
        if flat(middle):
            inside = middle
        else:
            outside = middle
    if not flat(inside) or flat(outside):
        return {"found": False, "unstable": True, "constant_bits": bits(constant)}
    last = offset(inside)[1]
    first = offset(outside)[1]
    return {
        "found": True,
        "constant_bits": bits(constant),
        "rows": [_row(swe, *last), _row(swe, *first)],
    }


def _child_sixty(dates_json: str) -> dict:
    import swisseph as swe

    out = []
    for year, month, day in json.loads(dates_json):
        following = day_after(year, month, day)
        readings = []
        for civil, hour, minute, second in (
            ((year, month, day), 23, 59, 59.0),
            ((year, month, day), 23, 59, 60.0),
            (following, 0, 0, 0.0),
        ):
            result = _convert(swe, *civil, hour, minute, second)
            if isinstance(result, str):
                readings.append({"accepted": False, "refusal": result})
            else:
                readings.append(
                    {"accepted": True, "dynamical_bits": bits(result[0]),
                     "universal_bits": bits(result[1])}
                )
        out.append({"date": iso(year, month, day), "readings": readings})
    return {"days": out}


def _child_override(directory: str) -> dict:
    import swisseph as swe

    if directory != "-":
        swe.set_ephe_path(directory)
    rows = [_row(swe, *instant) for instant in OVERRIDE_READ]
    result = _convert(swe, *OVERRIDE_DATE, 23, 59, 60.0)
    sixty = (
        {"accepted": False, "refusal": result}
        if isinstance(result, str)
        else {"accepted": True, "dynamical_bits": bits(result[0]), "universal_bits": bits(result[1])}
    )
    return {"rows": rows, "second_sixty": sixty}


def _child(argv: list[str]) -> None:
    kind, args = argv[0], argv[1:]
    result = {
        "state": _child_state,
        "steps": _child_steps,
        "handover": _child_handover,
        "sixty": _child_sixty,
        "override": _child_override,
    }[kind](*args)
    sys.stdout.write(json.dumps(result, sort_keys=True))


# ======================================================================================
# The parent — chooses each child's state and working directory, records what came back
# ======================================================================================


def child_environment() -> dict[str, str]:
    return {k: v for k, v in os.environ.items() if not k.startswith("SE_")}


def run_child(args: list[str], cwd: str) -> dict:
    proc = subprocess.run(
        [sys.executable, "-I", os.path.abspath(__file__), "--child", *args],
        cwd=cwd,
        env=child_environment(),
        capture_output=True,
        text=True,
        timeout=CHILD_TIMEOUT_SECONDS,
        check=False,
    )
    if proc.returncode != 0:
        return {"child_failed": proc.returncode, "stderr_tail": proc.stderr[-400:]}
    return json.loads(proc.stdout)


def digest_rows(rows: list[list[str]]) -> str:
    canonical = "".join("|".join(row) + "\n" for row in rows).encode("ascii")
    return hashlib.sha256(canonical).hexdigest()


def offsets(row: list[str]) -> dict | None:
    """Both outputs as seconds past the plain Julian day of the same civil instant."""
    if row[1] == "refused":
        return None
    jd0 = unbits(row[3])
    return {
        "dynamical": (unbits(row[1]) - jd0) * SECONDS_PER_DAY,
        "universal": (unbits(row[2]) - jd0) * SECONDS_PER_DAY,
    }


def era_view(rows: list[list[str]]) -> list[dict]:
    view = []
    for row in rows:
        entry: dict = {"date": row[0]}
        found = offsets(row)
        if found is None:
            entry["refusal"] = row[2]
        else:
            entry.update(
                dynamical_bits=row[1],
                universal_bits=row[2],
                dynamical_offset_seconds=round(found["dynamical"], 6),
                universal_offset_seconds=round(found["universal"], 6),
                dynamical_minus_universal_seconds=round(
                    (unbits(row[1]) - unbits(row[2])) * SECONDS_PER_DAY, 6
                ),
            )
        view.append(entry)
    return view


def compare_states(reference: dict, other: dict) -> dict:
    """How a state's readings differ from the reference's, per output, over grid and eras."""
    pairs = list(zip(reference["grid"] + reference["eras"], other["grid"] + other["eras"],
                     strict=True))
    summary: dict = {
        "universal_is_the_plain_julian_day": {
            "reference": sum(1 for a, _ in pairs if a[1] != "refused" and a[2] == a[3]),
            "this_state": sum(1 for _, b in pairs if b[1] != "refused" and b[2] == b[3]),
            "of": len(pairs),
        }
    }
    for label, index in (("dynamical", 1), ("universal", 2)):
        identical = 0
        largest = 0.0
        largest_at = None
        differing = []
        for a, b in pairs:
            if a[index] == b[index]:
                identical += 1
                continue
            differing.append(a[0])
            if "refused" in (a[1], b[1]):
                continue
            gap = abs(unbits(a[index]) - unbits(b[index])) * SECONDS_PER_DAY
            if gap > largest:
                largest, largest_at = gap, a[0]
        summary[label] = {
            "identical": identical,
            "of": len(pairs),
            "largest_difference_seconds": round(largest, 6),
            "largest_at": largest_at,
            "first_differing": differing[:3],
        }
    return summary


def equal_runs(rows: list[list[str]]) -> list[list[str]]:
    """Maximal runs of consecutive rows whose universal value IS the plain Julian day, bit for bit.

    ⭐ Recorded as runs of dates, never as a rule: what happens between two read days is not read.
    """
    runs: list[list[str]] = []
    current: list[str] | None = None
    for row in rows:
        if row[1] != "refused" and row[2] == row[3]:
            if current is None:
                current = [row[0], row[0]]
            else:
                current[1] = row[0]
        elif current is not None:
            runs.append(current)
            current = None
    if current is not None:
        runs.append(current)
    return runs


def steps_view(result: dict, full: bool) -> dict:
    if "rows" not in result:
        return result
    found = []
    quiet = {"dynamical": (0.0, None), "universal": (0.0, None)}
    for row in result["rows"]:
        before, after = row[:4], row[4:]
        a, b = offsets(before), offsets(after)
        if a is None or b is None:
            found.append({"date": after[0], "refused": True})
            continue
        dynamical = b["dynamical"] - a["dynamical"]
        universal = b["universal"] - a["universal"]
        if abs(dynamical) > BRACKET_STEP_SECONDS or abs(universal) > BRACKET_STEP_SECONDS:
            found.append(
                {
                    "date": after[0],
                    "dynamical_step_seconds": round(dynamical, 6),
                    "universal_step_seconds": round(universal, 6),
                    "universal_minus_dynamical_step_seconds": round(universal - dynamical, 6),
                    "dynamical_offset_after_seconds": round(b["dynamical"], 6),
                    "universal_offset_after_seconds": round(b["universal"], 6),
                }
            )
            continue
        for label, value in (("dynamical", dynamical), ("universal", universal)):
            if abs(value) > quiet[label][0]:
                quiet[label] = (abs(value), after[0])
    whole = [
        s["date"] for s in found
        if "dynamical_step_seconds" in s and abs(abs(s["dynamical_step_seconds"]) - 1.0) < 1e-4
    ]
    view = {
        "brackets": len(result["rows"]),
        "rows_sha256": digest_rows(result["rows"]),
        "steps": found,
        "whole_second_dynamical_step_dates": whole,
        "universal_is_the_plain_julian_day_runs": equal_runs([row[4:] for row in result["rows"]]),
        "largest_change_on_other_brackets_seconds": {
            label: {"value": round(value, 6), "at": at} for label, (value, at) in quiet.items()
        },
    }
    if full:
        view["bit_patterns"] = result["rows"]
    return view


def handover_view(result: dict) -> dict:
    if not result.get("found"):
        return result
    last, first = result["rows"]
    a, b = offsets(last), offsets(first)
    return {
        "found": True,
        "constant_offset_seconds": round(unbits(result["constant_bits"]) , 6),
        "last_day_holding_the_constant": last[0],
        "first_day_moved": first[0],
        "rows": result["rows"],
        "dynamical_step_seconds": round(b["dynamical"] - a["dynamical"], 6),
        "universal_step_seconds": round(b["universal"] - a["universal"], 6),
    }


def sixty_view(result: dict, listed: set[str]) -> list[dict]:
    if "days" not in result:
        return [result]
    out = []
    for day in result["days"]:
        entry: dict = {"date": day["date"], "found_by_part_2": day["date"] in listed}
        first, sixty, following = day["readings"]
        entry["second_60"] = sixty
        if sixty["accepted"] and first["accepted"] and following["accepted"]:
            for label in ("dynamical", "universal"):
                key = f"{label}_bits"
                entry[f"{label}_59_to_60_seconds"] = round(
                    (unbits(sixty[key]) - unbits(first[key])) * SECONDS_PER_DAY, 6
                )
                entry[f"{label}_60_to_next_0_seconds"] = round(
                    (unbits(following[key]) - unbits(sixty[key])) * SECONDS_PER_DAY, 6
                )
        elif first["accepted"] and following["accepted"]:
            for label in ("dynamical", "universal"):
                key = f"{label}_bits"
                entry[f"{label}_59_to_next_0_seconds"] = round(
                    (unbits(following[key]) - unbits(first[key])) * SECONDS_PER_DAY, 6
                )
        out.append(entry)
    return out


def override_view(cases: dict[str, dict]) -> dict:
    reference = cases["no_file_named_directory"]
    view = {}
    for case, result in cases.items():
        if "rows" not in result:
            view[case] = result
            continue
        rows = []
        for row, base in zip(result["rows"], reference.get("rows", result["rows"]), strict=True):
            found = offsets(row)
            rows.append(
                {
                    "date": row[0],
                    "dynamical_bits": row[1],
                    "universal_bits": row[2],
                    "dynamical_offset_seconds": None if found is None else round(found["dynamical"], 6),
                    "universal_offset_seconds": None if found is None else round(found["universal"], 6),
                    "differs_from_no_file": {"dynamical": row[1] != base[1], "universal": row[2] != base[2]},
                }
            )
        view[case] = {"rows": rows, "second_sixty_on_the_invented_day": result["second_sixty"]}
    return view


def capture(ephe_path: str | None, full: bool) -> dict:
    import swisseph as swe

    try:
        binding_version = _distribution_version("pyswisseph")
    except PackageNotFoundError:
        binding_version = None
    with open(os.path.abspath(__file__), "rb") as handle:
        own = handle.read()
    module_bytes, module_sha256 = sha256_of(swe.__file__)

    observation: dict = {
        "probe": {
            "sha256": hashlib.sha256(own).hexdigest(),
            "bytes": len(own),
            "mode": "full" if full else "compact",
        },
        "captured_at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        "host": {
            "platform": platform.platform(),
            "machine": platform.machine(),
            "python": sys.version.split()[0],
            "library_version": swe.version,
            "binding_version": binding_version,
            "binding_module": {
                "name": os.path.basename(swe.__file__),
                "bytes": module_bytes,
                "sha256": module_sha256,
            },
            "compiled_default_path": swe.EPHE_PATH,
        },
        "called_as": (
            "_jd_et, jd_ut = swe.utc_to_jd(year, month, day, hour, minute, second, swe.GREG_CAL)"
            " — positional, the second a float; the universal value is the one kept"
        ),
        "children": {
            "working_directory": "an empty temporary directory of their own, unless a part says otherwise",
            "removed_environment_variables": sorted(k for k in os.environ if k.startswith("SE_")),
        },
    }

    scratch = tempfile.mkdtemp(prefix="utc-conversion-")
    try:
        work = os.path.join(scratch, "work")
        empty = os.path.join(scratch, "empty")
        with_file = os.path.join(scratch, "with-file")
        working_with_file = os.path.join(scratch, "working-with-file")
        for directory in (work, empty, with_file, working_with_file):
            os.mkdir(directory)

        # ---- 1. state
        states: dict[str, dict] = {}
        for name, _description in STATES:
            if name == "data_files_directory":
                if not ephe_path:
                    continue
                directory = os.path.abspath(ephe_path)
            elif name == "empty_directory":
                directory = empty
            else:
                directory = "-"
            states[name] = run_child(["state", name, directory], cwd=work)
        reference = states["default_first_call"]
        part_state: dict = {
            "grid": "every 1 January and 1 July 1972-2027, then 2030, 2035, 2040-01-01; 0h UTC",
            "eras": [iso(*e) for e in ERAS],
            "states": {},
        }
        for name, description in STATES:
            if name not in states:
                part_state["states"][name] = {"description": description, "taken": False}
                continue
            result = states[name]
            entry: dict = {"description": description, "taken": True}
            if "grid" not in result:
                entry.update(result)
            else:
                entry["grid_rows"] = len(result["grid"])
                entry["grid_rows_sha256"] = digest_rows(result["grid"])
                entry["eras_rows_sha256"] = digest_rows(result["eras"])
                entry["grid_universal_is_the_plain_julian_day_runs"] = equal_runs(result["grid"])
                entry["tidal_acceleration_bits_after"] = result["tidal_acceleration_bits_after"]
                if name == "default_first_call":
                    entry["eras"] = era_view(result["eras"])
                    if full:
                        entry["grid_bit_patterns"] = result["grid"]
                elif "grid" in reference:
                    entry["against_default_first_call"] = compare_states(reference, result)
            if name == "data_files_directory" and ephe_path:
                data = os.path.abspath(ephe_path)
                entry["files"] = [
                    {"name": n, **dict(zip(("bytes", "sha256"), sha256_of(os.path.join(data, n))))}
                    for n in sorted(os.listdir(data)) if n.endswith(".se1") or n == LEAP_FILE_NAME
                ]
            part_state["states"][name] = entry
        observation["state"] = part_state

        # ---- 2. steps
        steps = steps_view(run_child(["steps"], cwd=work), full)
        observation["steps"] = steps

        # ---- 3. end
        observation["end"] = handover_view(run_child(["handover"], cwd=work))

        # ---- 4. the sixty-first second
        listed = [
            day_before(*map(int, date.split("-")))
            for date in steps.get("whole_second_dynamical_step_dates", [])
        ]
        dates = listed + [d for d in SECOND_SIXTY_UNLISTED if d not in listed]
        observation["second_sixty"] = sixty_view(
            run_child(["sixty", json.dumps(dates)], cwd=work), {iso(*d) for d in listed}
        )

        # ---- 5. override
        entry = f"{OVERRIDE_DATE[0]:04d}{OVERRIDE_DATE[1]:02d}{OVERRIDE_DATE[2]:02d}\n"
        for directory in (with_file, working_with_file):
            with open(os.path.join(directory, LEAP_FILE_NAME), "w", encoding="ascii") as handle:
                handle.write(entry)
        cases = {
            "no_file_named_directory": run_child(["override", empty], cwd=work),
            "file_in_named_directory": run_child(["override", with_file], cwd=work),
            "file_in_working_directory_none_named": run_child(
                ["override", "-"], cwd=working_with_file
            ),
            "file_in_working_directory_other_named": run_child(
                ["override", empty], cwd=working_with_file
            ),
        }
        observation["override"] = {
            "file_name": LEAP_FILE_NAME,
            "file_content": entry,
            "invented_insertion": iso(*OVERRIDE_DATE) + "T23:59:60",
            "cases": override_view(cases),
        }
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
    return observation


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if argv[:1] == ["--child"]:
        _child(argv[1:])
        return 0
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--ephe-path", help="the pinned data files' directory, for part 1's fourth state")
    parser.add_argument("--full", action="store_true", help="every bit pattern of parts 1 and 2 too")
    args = parser.parse_args(argv)
    observation = capture(args.ephe_path, args.full)
    line = json.dumps(observation, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    sys.stdout.write(line + "\n")
    sys.stdout.write("observation_sha256 " + hashlib.sha256(line.encode("ascii")).hexdigest() + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
