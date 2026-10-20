"""What a running deployment's ephemeris library resolves, captured on the host that runs it.

⛔ **The one generator here that writes no fixture and imports nothing from this repository.**
It is run on the host whose behaviour it records — a host where this repository is not
installed and must never be — so it needs the standard library and the ephemeris binding and
nothing else. It prints one JSON document, the **raw observation**, and a second line carrying
that document's SHA-256 so a copy carried off the host by hand can be checked for truncation.
A fixture is made from the observation afterwards, where provenance can be stamped.

It writes nothing except one temporary directory, which it removes.

Two questions, each about a deployment and therefore owed before the deployment changes:

1. **Which leap-second table the deployment's civil-to-dynamical conversion uses** — the
   installed build's own, or one the deployment's filesystem supplies. Answered as a
   **difference**: the conversion in the deployment's default state against the same build
   pointed at an empty directory, at every half-year boundary from 1972, both returned values
   bit for bit. Identical bits at every boundary mean the table in use has the build's own
   content, whatever file may or may not exist.
2. **Whether the library's data files resolve on its default path there, and which, by
   digest.** Answered by the **returned flag** of a position call that requests them. ⛔ A file
   path reported after the call is not resolution: measured on a host holding no data files at
   all, a path is still reported and the flag says the request was not met. So every reported
   path is also checked on disk, and every file found is hashed.

⛔ **Every reading is taken in a fresh child process.** The library holds process-wide state,
and `src/saakshi/conventions.py` records that its leap table is read once per process.

⛔ **Environment variables are read through an allowlist.** A running service's environment
holds credentials; only names beginning `SE_` and the host's own commit variable are recorded.

⛔ **Recorder, never explainer.** Nothing here describes how the library computes anything.

Usage, on the host::

    python deployment_capture.py            # compact: digests, steps, differences
    python deployment_capture.py --full     # every bit pattern of the leap grid as well
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import platform
import re
import shutil
import struct
import subprocess
import sys
import tempfile
from importlib.metadata import PackageNotFoundError, version as _distribution_version

#: The half-year boundaries the conversion is read at, then three later instants.
GRID: tuple[tuple[int, int, int], ...] = tuple(
    (year, month, 1) for year in range(1972, 2028) for month in (1, 7)
) + ((2030, 1, 1), (2035, 1, 1), (2040, 1, 1))

#: A sixty-first second on a date the published table lists, and on one it does not.
SECOND_SIXTY: tuple[tuple[int, int, int], ...] = ((2016, 12, 31), (2015, 12, 31))

#: The time-offset epochs of the committed comparison fixture: 1900, 2000 and 2100, 0h UT.
DELTA_T_EPOCHS: tuple[float, ...] = (2415020.5, 2451544.5, 2488069.5)

#: A step in the dynamical offset larger than this is recorded as a step.
STEP_THRESHOLD_SECONDS = 1e-4

#: The commit a hosting environment may name for the code it runs.
COMMIT_VARIABLES: tuple[str, ...] = ("RENDER_GIT_COMMIT", "GIT_COMMIT", "SOURCE_VERSION")

#: The one prefix of environment variable recorded in full.
LIBRARY_VARIABLE_PREFIX = "SE_"

#: The leap-second file name the library's documentation gives, looked for beside data files.
LEAP_FILE_NAME = "seleapsec.txt"

#: The data-file suffix.
DATA_SUFFIX = ".se1"

#: A search path quoted in a refusal message, as the library words it.
REFUSAL_PATH = re.compile(r"PATH '([^']*)'")

CHILD_TIMEOUT_SECONDS = 120


def bits(value: float) -> str:
    return struct.pack(">d", value).hex()


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


def _child_leap(directory: str) -> dict:
    import swisseph as swe

    if directory != "-":
        swe.set_ephe_path(directory)
    rows = []
    for year, month, day in GRID:
        jd_et, jd_ut = swe.utc_to_jd(year, month, day, 0, 0, 0.0, swe.GREG_CAL)
        jd0 = swe.julday(year, month, day, 0.0)
        rows.append([f"{year:04d}-{month:02d}-{day:02d}", bits(jd_et), bits(jd_ut), bits(jd0)])
    sixty = []
    for year, month, day in SECOND_SIXTY:
        case = {"utc": f"{year:04d}-{month:02d}-{day:02d}T23:59:60"}
        try:
            jd_et, jd_ut = swe.utc_to_jd(year, month, day, 23, 59, 60.0, swe.GREG_CAL)
        except Exception as exc:  # noqa: BLE001 - a refusal is the observation
            case.update(accepted=False, refusal=f"{type(exc).__name__}: {str(exc)[:160]}")
        else:
            case.update(accepted=True, dynamical_bits=bits(jd_et), universal_bits=bits(jd_ut))
        sixty.append(case)
    return {"rows": rows, "second_sixty": sixty, "tidal_acceleration_bits": bits(swe.get_tid_acc())}


#: The bodies a position call is made for, by the data file each would read.
BODIES: tuple[str, ...] = ("SUN", "MOON", "CERES")


def _child_files(body: str) -> dict:
    import swisseph as swe

    out: dict = {"body": body.lower(), "flag_requested": int(swe.FLG_SWIEPH)}
    try:
        _values, returned = swe.calc_ut(2451545.0, getattr(swe, body), swe.FLG_SWIEPH)
    except Exception as exc:  # noqa: BLE001
        out["refusal"] = f"{type(exc).__name__}: {str(exc)[:160]}"
    else:
        source_bits = int(returned) & int(swe.FLG_JPLEPH | swe.FLG_SWIEPH | swe.FLG_MOSEPH)
        out["returned"] = int(returned)
        out["source"] = {
            int(swe.FLG_SWIEPH): "swiss_file",
            int(swe.FLG_MOSEPH): "moshier",
            int(swe.FLG_JPLEPH): "jpl_file",
        }.get(source_bits, f"bits_{source_bits}")
    reported = []
    for number in range(5):
        path, start, end, denum = swe.get_current_file_data(number)
        if not path:
            continue
        entry = {
            "file_number": number,
            "name": os.path.basename(path),
            "directory": os.path.dirname(path),
            "on_disk": os.path.isfile(path),
            "start": start,
            "end": end,
            "denum": denum,
        }
        if entry["on_disk"]:
            entry["bytes"], entry["sha256"] = sha256_of(path)
        reported.append(entry)
    out["reported_files"] = reported
    return out


#: (call, flag name) pairs read for the time offset, each in its own process.
DELTA_T_CALLS: tuple[tuple[str, str], ...] = (
    ("deltat", "-"),
    ("deltat_ex", "FLG_MOSEPH"),
    ("deltat_ex", "FLG_SWIEPH"),
)


def _child_delta_t(call: str, flag: str, jd: str) -> dict:
    import swisseph as swe

    instant = float(jd)
    if call == "deltat":
        value = swe.deltat(instant)
    else:
        value = swe.deltat_ex(instant, getattr(swe, flag))
    return {
        "call": call,
        "flag": flag,
        "jd_ut_bits": bits(instant),
        "day_bits": bits(value),
        "tidal_acceleration_bits": bits(swe.get_tid_acc()),
    }


def _child(argv: list[str]) -> None:
    kind, args = argv[0], argv[1:]
    result = {
        "leap": _child_leap,
        "files": _child_files,
        "delta_t": _child_delta_t,
    }[kind](*args)
    sys.stdout.write(json.dumps(result, sort_keys=True))


# ======================================================================================
# The parent — chooses each child's working directory and records what came back
# ======================================================================================


def run_child(args: list[str], cwd: str) -> dict:
    proc = subprocess.run(
        [sys.executable, "-I", os.path.abspath(__file__), "--child", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=CHILD_TIMEOUT_SECONDS,
        check=False,
    )
    if proc.returncode != 0:
        return {"child_failed": proc.returncode, "stderr_tail": proc.stderr[-400:]}
    return json.loads(proc.stdout)


def service_process() -> dict:
    """The serving process, where this host shows one: its command and working directory.

    ⛔ Its environment is read for `SE_` names only — nothing else in it is recorded.
    """
    found: dict = {"looked_for": "a process whose command line names uvicorn"}
    try:
        pids = sorted((int(p) for p in os.listdir("/proc") if p.isdigit()))
    except OSError as exc:
        found["unavailable"] = f"{type(exc).__name__}"
        return found
    for pid in pids:
        if pid == os.getpid():
            continue
        try:
            with open(f"/proc/{pid}/cmdline", "rb") as handle:
                argv = [a.decode("utf-8", "replace") for a in handle.read().split(b"\0") if a]
        except OSError:
            continue
        if not any("uvicorn" in a for a in argv):
            continue
        found.update(pid=pid, command=argv)
        try:
            found["cwd"] = os.readlink(f"/proc/{pid}/cwd")
        except OSError as exc:
            found["cwd_unreadable"] = type(exc).__name__
        try:
            with open(f"/proc/{pid}/environ", "rb") as handle:
                pairs = [e.decode("utf-8", "replace") for e in handle.read().split(b"\0") if e]
            found["library_variables"] = sorted(
                p for p in pairs if p.startswith(LIBRARY_VARIABLE_PREFIX)
            )
            found["environment_size"] = len(pairs)
        except OSError as exc:
            found["environment_unreadable"] = type(exc).__name__
        return found
    found["none_found"] = True
    return found


def list_directory(directory: str) -> dict:
    entry: dict = {"directory": directory, "exists": os.path.isdir(directory)}
    if not entry["exists"]:
        return entry
    files = []
    try:
        names = sorted(os.listdir(directory))
    except OSError as exc:
        entry["unreadable"] = type(exc).__name__
        return entry
    for name in names:
        path = os.path.join(directory, name)
        if os.path.isfile(path) and (name.endswith(DATA_SUFFIX) or name.lower() == LEAP_FILE_NAME):
            size, digest = sha256_of(path)
            files.append({"name": name, "bytes": size, "sha256": digest})
    entry["files"] = files
    return entry


def leap_summary(result: dict, full: bool) -> dict:
    if "rows" not in result:
        return result
    rows = result["rows"]
    canonical = "".join("|".join(row) + "\n" for row in rows).encode("ascii")
    steps = []
    previous = None
    for date, et_bits, _ut_bits, jd0_bits in rows:
        dynamical = struct.unpack(">d", bytes.fromhex(et_bits))[0]
        jd0 = struct.unpack(">d", bytes.fromhex(jd0_bits))[0]
        offset = (dynamical - jd0) * 86400.0
        if previous is None or abs(offset - previous) > STEP_THRESHOLD_SECONDS:
            steps.append([date, round(offset, 6)])
        previous = offset
    summary = {
        "rows": len(rows),
        "rows_sha256": hashlib.sha256(canonical).hexdigest(),
        "dynamical_offset_steps_seconds": steps,
        "second_sixty": result["second_sixty"],
        "tidal_acceleration_bits": result["tidal_acceleration_bits"],
    }
    if full:
        summary["bit_patterns"] = rows
    return summary


def capture(full: bool, control_default_dir: str | None) -> dict:
    import swisseph as swe

    try:
        binding_version = _distribution_version("pyswisseph")
    except PackageNotFoundError:
        binding_version = None
    with open(os.path.abspath(__file__), "rb") as handle:
        own = handle.read()
    module_bytes, module_sha256 = sha256_of(swe.__file__)
    serving = service_process()
    default_cwd = serving.get("cwd") if os.path.isdir(serving.get("cwd", "")) else os.getcwd()

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
            "executable": sys.executable,
            "library_version": swe.version,
            "binding_version": binding_version,
            "binding_module": {
                "name": os.path.basename(swe.__file__),
                "bytes": module_bytes,
                "sha256": module_sha256,
            },
            "library_path_reported": swe.get_library_path(),
        },
        "environment": {
            "library_variables": sorted(
                f"{k}={v}" for k, v in os.environ.items() if k.startswith(LIBRARY_VARIABLE_PREFIX)
            ),
            "commit_variables": {k: os.environ[k] for k in COMMIT_VARIABLES if k in os.environ},
            "shell_cwd": os.getcwd(),
        },
        "service_process": serving,
        "default_state": (
            {"kind": "explicit_control_directory", "directory": control_default_dir}
            if control_default_dir
            else {"kind": "default", "cwd": default_cwd}
        ),
    }

    scratch = tempfile.mkdtemp(prefix="capture-empty-")
    try:
        default_arg = control_default_dir or "-"
        default = run_child(["leap", default_arg], cwd=default_cwd)
        empty = run_child(["leap", scratch], cwd=scratch)
        compared = {"dynamical_identical": 0, "universal_identical": 0, "differing": []}
        if "rows" in default and "rows" in empty:
            for a, b in zip(default["rows"], empty["rows"], strict=True):
                same_dyn, same_uni = a[1] == b[1], a[2] == b[2]
                compared["dynamical_identical"] += same_dyn
                compared["universal_identical"] += same_uni
                if not (same_dyn and same_uni):
                    which = [n for n, same in (("dynamical", same_dyn), ("universal", same_uni))
                             if not same]
                    compared["differing"].append([a[0], which])
        observation["leap"] = {
            "grid": "every 1 January and 1 July 1972-2027, then 2030, 2035, 2040-01-01; 0h UTC",
            "default_state": leap_summary(default, full),
            "empty_directory": leap_summary(empty, full),
            "comparison": compared,
        }
    finally:
        shutil.rmtree(scratch, ignore_errors=True)

    if not control_default_dir:
        by_body = [run_child(["files", body], cwd=default_cwd) for body in BODIES]
        searched = {default_cwd}
        searched.update(swe.EPHE_PATH.split(os.pathsep))
        searched.update(f["directory"] for b in by_body for f in b.get("reported_files", []))
        # ⭐ A refusal may name the search path the library used; those directories are
        #    listed too, because the compiled constant above was measured not to be it.
        for b in by_body:
            for named in REFUSAL_PATH.findall(b.get("refusal", "")):
                searched.update(named.split(os.pathsep))
        searched = {os.path.normpath(os.path.join(default_cwd, d)) for d in searched if d}
        observation["data_files"] = {
            "compiled_default_path": swe.EPHE_PATH,
            "by_body": by_body,
            "directories": [list_directory(d) for d in sorted(searched)],
        }
        observation["delta_t"] = [
            run_child(["delta_t", call, flag, repr(jd)], cwd=default_cwd)
            for jd in DELTA_T_EPOCHS
            for call, flag in DELTA_T_CALLS
        ]
    return observation


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if argv[:1] == ["--child"]:
        _child(argv[1:])
        return 0
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--full", action="store_true", help="every leap-grid bit pattern too")
    parser.add_argument(
        "--control-default-dir",
        help="⛔ tests only: stand an explicit directory in for the default state; the "
        "observation then says so, and records nothing about data files or the time offset",
    )
    args = parser.parse_args(argv)
    observation = capture(args.full, args.control_default_dir)
    line = json.dumps(observation, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    sys.stdout.write(line + "\n")
    sys.stdout.write("observation_sha256 " + hashlib.sha256(line.encode("ascii")).hexdigest() + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
