"""Three implementations of the IAU 2006/2000A precession-nutation models, and two of the apparent place of date.

A feasibility measurement, not a reference. It asks three independently written libraries — ERFA (through the
``pyerfa`` binding), Skyfield, and SuperNOVAS (built from its source, reading the development ephemeris through the
SPICE Toolkit) — for the same quantities at the same instants, writes down what each returned with its bit pattern,
and writes the pairwise differences beside them. In this order:

1. the mean obliquity of the ecliptic (IAU 2006);
2. nutation in longitude and in obliquity;
3. the true obliquity, where a library returns one;
4. the bias-precession-nutation matrix, GCRS to the true equator and equinox of date;
5. the geocentric apparent place in the true equator and equinox of date, and in the true ecliptic of date, on
   ``de440s`` — Skyfield against SuperNOVAS — with light deflection by each library's default bodies, and with none.

And, as a sixth section, the mean obliquity of IAU 1980 against that of IAU 2006 (ERFA's two entry points): the
definitional gap between a frame of date realised under the older models and one realised under the newer.

The instants:

* **the sweep** — 20 001 instants in Julian centuries of TT from J2000, evenly spaced over the span of DE440 by the
  rule ``lo + (hi - lo) * i / 20000``, ``lo`` and ``hi`` the span's ends; the models only (``de440s`` covers less);
* **the geocentric grid** — the distinct instants of a geocentric-vector values file, read by its sha256;
* **one civil instant** — 1992-11-11 06:40 at UTC+05:30, converted by ERFA's own entry points (UTC to TAI to TT,
  then TDB at the geocentre).

⭐ **Every value is the library's own return, and every comparison is a difference.** Nothing here evaluates a model
term, and nothing combines two returns into a quantity a library does not return — which is why ERFA has no true
obliquity row: none of its entry points returns one. A unit conversion of a return into arcseconds is the one
arithmetic applied before a difference, and both the return and the converted value are written, each with its bits.

⛔ **No band, no class but ``reference_only``, no verdict.** Agreement between two implementations of one model on one
kernel says nothing about which, if either, is right. Which of them may judge anything is a decision taken elsewhere.

⛔ **Recorder, never explainer.** Nothing here says how any library computes what it returns. The candidates differ
where they differ; the rows say where and by how much, and the reasons are not this file's.

Refused before anything is computed: a dirty or commitless tree; an output that exists; a library, binding, toolkit,
source archive or licence text whose version or digest is not the one pinned below; a kernel that is not the pinned
``de440s``; a values file whose digest is not the one given; a driver that reports another library or toolkit
version. Refused after: any driver request that failed, and any non-finite return.

Usage (a clean tree; the oracle libraries are not this repository's requirements — a dedicated environment):
    <python> generators/of_date_candidates.py --kernel cache/kernels/de440s.bsp \\
        --grid-values VALUES.jsonl --grid-values-sha256 HEX \\
        --supernovas-source DIR --supernovas-tarball FILE --supernovas-archive FILE --supernovas-build-record FILE \\
        --cspice-toolkit DIR --cspice-package FILE --erfa-licence FILE \\
        --budget-row ROW --out DIR
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata as metadata
import json
import math
import platform
import struct
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Sequence

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from saakshi.fixture import Header, bits, describe_reserved_names, patterned, write_jsonl  # noqa: E402
from saakshi.kernels import PINS, oracle_identity, verify  # noqa: E402
from saakshi.provenance import generator_for, host_record, today  # noqa: E402

DRIVER_SOURCE = Path(__file__).resolve().parent / "native" / "supernovas_of_date.c"
OUTPUT_NAME = "of-date-candidates.jsonl"

# --------------------------------------------------------------------------------------------------------------
# The pins. ⛔ Anything else is refused: a record names the exact code that answered.
# --------------------------------------------------------------------------------------------------------------

PYTHON_PINS = {"pyerfa": "2.0.1.5", "skyfield": "1.55", "jplephem": "2.23", "numpy": "2.5.1"}
ERFA_LIBRARY = ("2.0.1", "20231011")  # the C library pyerfa carries, and the release it follows
SUPERNOVAS_VERSION = "1.8.0"
TOOLKIT_VERSION = "CSPICE_N0067"
ARCHIVE_PINS = {
    "supernovas_tarball": "467196a383988506540d1cd3dcef683680c127a0c406766919d1de8475745853",
    "cspice_package": "0deae048443e11ca4d093cac651d9785d4f2594631a183d85a3d58949f4d0aa9",
}
#: The licence texts, by sha256. ⛔ A changed text is a stop: it has to be read again before anything is recorded.
LICENCE_PINS = {
    "pyerfa": "0d404371a5d7d1478307ab142962091ec258b92a71f8cab3736fdb46b03cc716",
    "erfa": "b1858f9a263f22c438a455a32945da51a31a0ae25a21055da13bb7ed57cc3b51",
    "skyfield": "4b3cad9301fc389f9545079b43384659b908e94d6ab271474b3f6da2bd20d65a",
    "jplephem": "31bbf940baa5da362ef4e16ccda663cf09a096673b9eac30413f899c1055981d",
    "supernovas": "6b0382b16279f26ff69014300541967a356a666eb0b91b422f6862f6b7dad17e",
}
LICENCE_NAMES = {
    "pyerfa": "BSD-3-Clause (the binding)",
    "erfa": "BSD-3-Clause, with the SOFA derivation notice (the C library)",
    "skyfield": "MIT",
    "jplephem": "MIT",
    "supernovas": "The Unlicense",
}

#: The driver's flags: the library's own defaults for its static build, ⛔ less `-g` — a debugging map names the
#: compiler's temporary objects, so a driver built with it would have a different digest at every build.
CFLAGS = ("-Os", "-Wall", "-Wno-deprecated-declarations")

# --------------------------------------------------------------------------------------------------------------
# The instants
# --------------------------------------------------------------------------------------------------------------

J2000 = 2451545.0
DAYS_PER_CENTURY = 36525.0
#: DE440's span, as its publisher states it, in TT Julian dates: 1550-01-01 and 2650-01-22, both at 0h.
SPAN_JD = (2287184.5, 2688976.5)
SWEEP_STEPS = 20000
#: The span within which the definitional gap is recorded: 1850-2150, in centuries.
GAP_SPAN = 1.5

CIVIL_INSTANT = {"civil": "1992-11-11T06:40:00", "utc_offset_seconds": 19800, "utc": (1992, 11, 11, 1, 10, 0.0)}

#: The targets of the apparent place, by their ephemeris codes, and what each code names in ``de440s``.
TARGETS = {
    10: "sun", 301: "moon", 199: "mercury", 299: "venus", 4: "mars_barycentre", 5: "jupiter_barycentre",
    6: "saturn_barycentre", 7: "uranus_barycentre", 8: "neptune_barycentre", 9: "pluto_barycentre",
}
#: Each library's default deflecting bodies at full accuracy: the Sun, Jupiter and Saturn (``de440s`` holds the
#: barycentres of the latter two, and both libraries take them). ``none`` is the empty set.
DEFLECTION = {"default": (10, 599, 699), "none": ()}

ARCSEC_PER_RADIAN = 648000.0 / math.pi
ARCSEC_PER_DEGREE = 3600.0
#: Reporting levels for the summary's counts. ⛔ Not bands: a count above a level says how many, never "fails".
LEVELS_ARCSEC = (1.0e-4, 1.0e-3, 1.0e-2)


class Refusal(Exception):
    """A condition under which nothing may be recorded."""


def sweep() -> list[float]:
    """The 20 001 centuries, by the stated rule. ⭐ Evaluated left to right, as the rule is written."""
    lo = (SPAN_JD[0] - J2000) / DAYS_PER_CENTURY
    hi = (SPAN_JD[1] - J2000) / DAYS_PER_CENTURY
    return [lo + (hi - lo) * i / SWEEP_STEPS for i in range(SWEEP_STEPS + 1)]


def grid_instants(values_path: Path, expected_sha256: str) -> list[float]:
    """The distinct TDB Julian dates of a geocentric-vector values file, ascending — refused unless its digest is given."""
    data = values_path.read_bytes()
    actual = hashlib.sha256(data).hexdigest()
    if actual != expected_sha256:
        raise Refusal(f"the values file's sha256 is {actual}, not {expected_sha256}")
    seen: dict[str, float] = {}
    for number, line in enumerate(data.decode("utf-8").splitlines()):
        record = json.loads(line)
        if record.get("record") != "row":
            continue
        value, pattern = record["jd_tdb"], record["jd_tdb_bits"]
        if bits(float(value)) != pattern:
            raise Refusal(f"line {number + 1}: jd_tdb and its pattern are different numbers")
        seen[pattern] = float(value)
    if not seen:
        raise Refusal("the values file holds no instant")
    return sorted(seen.values())


# --------------------------------------------------------------------------------------------------------------
# Differences — the one computation this file makes
# --------------------------------------------------------------------------------------------------------------


def unit_vector(ra_hours: float, dec_degrees: float) -> tuple[float, float, float]:
    ra, dec = math.radians(ra_hours * 15.0), math.radians(dec_degrees)
    return (math.cos(dec) * math.cos(ra), math.cos(dec) * math.sin(ra), math.sin(dec))


def separation_arcsec(a: Sequence[float], b: Sequence[float]) -> float:
    """The angle between two directions, by the arctangent of the cross and dot products (well-conditioned near 0)."""
    cross = (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])
    return math.atan2(math.sqrt(sum(c * c for c in cross)), sum(x * y for x, y in zip(a, b))) * ARCSEC_PER_RADIAN


def rotation_between_arcsec(r1: Sequence[Sequence[float]], r2: Sequence[Sequence[float]]) -> float:
    """The angle of the rotation taking one matrix to the other: from the antisymmetric part of ``r1 · r2ᵀ``."""
    q = [[sum(r1[i][k] * r2[j][k] for k in range(3)) for j in range(3)] for i in range(3)]
    w = ((q[2][1] - q[1][2]) / 2.0, (q[0][2] - q[2][0]) / 2.0, (q[1][0] - q[0][1]) / 2.0)
    return math.asin(min(1.0, math.sqrt(sum(c * c for c in w)))) * ARCSEC_PER_RADIAN


def wrapped_degrees(a: float, b: float) -> float:
    """``a - b`` in degrees, taken into (-180, 180]."""
    d = math.fmod(a - b, 360.0)
    if d <= -180.0:
        d += 360.0
    elif d > 180.0:
        d -= 360.0
    return d


def from_hex(text: str) -> float:
    return struct.unpack(">d", bytes.fromhex(text))[0]


def parse_driver(lines: Sequence[str], kind: str, count: int, width: int) -> list[list[float]]:
    """The driver's answers to ``count`` requests of one kind, each ``width`` doubles. ⛔ Any failure line refuses."""
    out: list[list[float]] = []
    for line in lines:
        fields = line.split()
        if not fields:
            continue
        if fields[0] == "E":
            raise Refusal(f"the driver refused a request: {line.strip()}")
        if fields[0] != kind or len(fields) != width + 1:
            raise Refusal(f"an answer that is not a {kind} answer of {width} values: {line.strip()[:80]}")
        values = [from_hex(f) for f in fields[1:]]
        if not all(math.isfinite(v) for v in values):
            raise Refusal(f"a non-finite return: {line.strip()[:80]}")
        out.append(values)
    if len(out) != count:
        raise Refusal(f"{len(out)} {kind} answers for {count} requests")
    return out


class Tally:
    """Per difference: the largest magnitude, where, and how many exceed each reporting level — by stratum."""

    def __init__(self) -> None:
        self.by: dict[tuple[str, str, str], dict[str, Any]] = {}

    def add(self, section: str, key: str, stratum: str, value: float, where: str) -> None:
        entry = self.by.setdefault((section, key, stratum), {"count": 0, "max": 0.0, "at": where, "low": value,
                                                               "high": value, "above": [0] * len(LEVELS_ARCSEC)})
        entry["count"] += 1
        if abs(value) > abs(entry["max"]) or entry["count"] == 1:
            entry["max"], entry["at"] = value, where
        entry["low"], entry["high"] = min(entry["low"], value), max(entry["high"], value)
        for i, level in enumerate(LEVELS_ARCSEC):
            entry["above"][i] += abs(value) > level

    def as_json(self) -> list[dict[str, Any]]:
        out = []
        for (section, key, stratum), entry in sorted(self.by.items()):
            out.append({
                "section": section, "difference": key, "stratum": stratum, "instants": entry["count"],
                **patterned("largest_arcsec", entry["max"]), "largest_at": entry["at"],
                **patterned("range_arcsec", [entry["low"], entry["high"]]),
                "above_levels": list(entry["above"]),
            })
        return out


# --------------------------------------------------------------------------------------------------------------
# Identity
# --------------------------------------------------------------------------------------------------------------


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def python_identity(erfa_licence: Path) -> dict[str, Any]:
    """The binding and library versions and the licence digests, ⛔ each refused unless it is the pin."""
    versions = {name: metadata.version(name) for name in PYTHON_PINS}
    if versions != PYTHON_PINS:
        raise Refusal(f"library versions {versions} are not the pins {PYTHON_PINS}")
    import erfa  # ⭐ only after the pins: a refused version is never imported

    library = (erfa.version.erfa_version, erfa.version.sofa_version)
    if library != ERFA_LIBRARY:
        raise Refusal(f"the binding carries ERFA {library}, not {ERFA_LIBRARY}")
    licences = {}
    for name in ("pyerfa", "skyfield", "jplephem"):
        files = [f for f in metadata.files(name) or () if Path(str(f)).name.upper().startswith("LICENSE")]
        if len(files) != 1:
            raise Refusal(f"{name}: {len(files)} licence files in its distribution, not one")
        licences[name] = hashlib.sha256(Path(str(files[0].locate())).read_bytes()).hexdigest()
    licences["erfa"] = sha256_file(erfa_licence)
    for name, digest in licences.items():
        if digest != LICENCE_PINS[name]:
            raise Refusal(f"the {name} licence text is not the one read (sha256 {digest}); read it again first")
    return {"versions": versions, "erfa_library": library, "licences": licences}


def carried_build_record(record: dict[str, Any]) -> dict[str, Any]:
    """The library's build record as a fixture may carry it: its source file names become values, never keys.

    ⛔ A file name is not a fixture key (``target.c`` is not lower_snake_case), so the map of name to digest is
    carried as a list of ``{file, sha256}`` in the record's own order. Nothing else in it changes.
    """
    sources = record.get("sources")
    if not isinstance(sources, dict) or not sources:
        raise Refusal("the library's build record names no sources")
    return {**{k: v for k, v in record.items() if k != "sources"},
            "sources": [{"file": name, "sha256": digest} for name, digest in sources.items()]}


def build_driver(source_dir: Path, toolkit: Path, archive: Path, record: Path,
                 work: Path) -> tuple[Path, dict[str, Any]]:
    """Compile the committed driver against the built library and the toolkit. Returns the binary and its record.

    ⛔ The library's build record must name the archive given, by digest: the record is what says which sources,
    flags and compiler made it.
    """
    library_build = carried_build_record(json.loads(record.read_text(encoding="utf-8")))
    if library_build.get("archive_sha256") != sha256_file(archive):
        raise Refusal("the library's build record names another archive")
    binary = work / "supernovas_of_date"
    command = ["cc", *CFLAGS, f"-I{source_dir / 'include'}", f"-I{work / 'inc'}", str(DRIVER_SOURCE), str(archive),
               str(toolkit / "lib" / "cspice.a"), "-lm", "-o", str(binary)]
    (work / "inc").mkdir()
    (work / "inc" / "cspice").symlink_to(toolkit / "include")
    done = subprocess.run(command, capture_output=True, text=True, check=False)
    if done.returncode != 0:
        raise Refusal(f"the driver did not build: {done.stderr[-800:]}")
    compiler = subprocess.run(["cc", "--version"], capture_output=True, text=True, check=True).stdout.splitlines()[0]
    return binary, {
        "compiler": compiler,
        "cflags": list(CFLAGS),
        "driver_source": {"path": "generators/native/supernovas_of_date.c", "sha256": sha256_file(DRIVER_SOURCE)},
        "driver_binary_sha256": sha256_file(binary),
        "library_archive_sha256": sha256_file(archive),
        "library_build": library_build,
        "toolkit_archive_sha256": sha256_file(toolkit / "lib" / "cspice.a"),
    }


def run_driver(binary: Path, kernel: Path, requests: Sequence[str]) -> list[str]:
    """One fresh child for every request of a run. ⛔ A version other than the pins is refused."""
    done = subprocess.run([str(binary), str(kernel)], input="".join(requests), capture_output=True, text=True,
                          check=False, timeout=3600)
    lines = done.stdout.splitlines()
    if not lines or lines[0].split()[:1] != ["V"]:
        raise Refusal(f"the driver did not start: {done.stderr[-400:]}")
    version = lines[0].split()[1:]
    if version != [SUPERNOVAS_VERSION, TOOLKIT_VERSION]:
        raise Refusal(f"the driver reports {version}, not {[SUPERNOVAS_VERSION, TOOLKIT_VERSION]}")
    if done.returncode != 0:
        raise Refusal(f"the driver stopped (exit {done.returncode}): {lines[-1][:120] if lines else ''}")
    return lines[1:]


# --------------------------------------------------------------------------------------------------------------
# The readings
# --------------------------------------------------------------------------------------------------------------


def civil_instant() -> dict[str, Any]:
    """ERFA's own conversion of the civil instant: UTC to TAI to TT, and TDB at the geocentre."""
    import erfa

    u1, u2 = erfa.dtf2d("UTC", *CIVIL_INSTANT["utc"])
    a1, a2 = erfa.utctai(u1, u2)
    t1, t2 = erfa.taitt(a1, a2)
    # ⚠ At the geocentre (u = v = 0) the observer's terms vanish, so the UT fraction and longitude enter none; the
    #    UTC fraction of the day is given for the first.
    ut = math.fmod(float(u1) - 0.5, 1.0) + float(u2)
    dtdb = erfa.dtdb(t1, t2, ut, 0.0, 0.0, 0.0)
    b1, b2 = erfa.tttdb(t1, t2, dtdb)
    return {"utc": (float(u1), float(u2)), "tt": (float(t1), float(t2)), "tdb_minus_tt_seconds": float(dtdb),
            "tdb": (float(b1), float(b2))}


def instants(values_path: Path, values_sha256: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for i, t in enumerate(sweep()):
        stratum = "sweep_within_1850_2150" if abs(t) <= GAP_SPAN else "sweep_outside_1850_2150"
        out.append({"grid": "sweep", "id": f"s{i:05d}", "stratum": stratum, "t": t,
                    "jd": (J2000, t * DAYS_PER_CENTURY), "apparent_tdb": None})
    for i, jd in enumerate(grid_instants(values_path, values_sha256)):
        out.append({"grid": "geocentric_grid", "id": f"g{i:03d}", "stratum": "geocentric_grid", "t": None,
                    "jd": (jd, 0.0), "apparent_tdb": jd})
    civil = civil_instant()
    out.append({"grid": "civil_instant", "id": "c0", "stratum": "civil_instant", "t": None, "jd": civil["tt"],
                "apparent_tdb": civil["tdb"][0] + civil["tdb"][1]})
    return out, civil


def instant_block(p: dict[str, Any]) -> dict[str, Any]:
    block: dict[str, Any] = {"grid": p["grid"], "instant": p["id"], "stratum": p["stratum"]}
    if p["t"] is not None:
        block.update(patterned("t_centuries", p["t"]))
    block.update(patterned("jd_parts", list(p["jd"])))
    return block


def read_models(points: list[dict[str, Any]], binary: Path, kernel: Path) -> dict[str, list]:
    import erfa
    import numpy as np
    from skyfield.api import load
    from skyfield.nutationlib import earth_tilt

    d1 = np.array([p["jd"][0] for p in points])
    d2 = np.array([p["jd"][1] for p in points])
    ts = load.timescale(builtin=True)
    t = ts.tt_jd(d1, d2)
    mean_deg, true_deg, _, sky_dpsi, sky_deps = earth_tilt(t)
    sky_m = np.asarray(t.M)  # (3, 3, n)
    requests = [f"M {bits(float(a))} {bits(float(b))}\n" for a, b in zip(d1, d2)]
    nov = parse_driver(run_driver(binary, kernel, requests), "M", len(points), 19)
    return {
        "erfa_obl06": erfa.obl06(d1, d2), "erfa_obl80": erfa.obl80(d1, d2),
        "erfa_nut06a": erfa.nut06a(d1, d2), "erfa_nut00a": erfa.nut00a(d1, d2), "erfa_pnm06a": erfa.pnm06a(d1, d2),
        "sky_mean_deg": mean_deg, "sky_true_deg": true_deg, "sky_dpsi": sky_dpsi, "sky_deps": sky_deps,
        "sky_m": sky_m, "nov": nov,
    }


def read_apparent(points: list[dict[str, Any]], binary: Path, kernel: Path) -> list[dict[str, Any]]:
    from skyfield.api import load, load_file
    from skyfield.framelib import ecliptic_frame

    ts = load.timescale(builtin=True)
    eph = load_file(str(kernel))
    earth = eph["earth"]
    cases = [(p, code, setting) for p in points if p["apparent_tdb"] is not None
             for code in TARGETS for setting in DEFLECTION]
    requests = [f"A {bits(p['apparent_tdb'])} {code} {1 if setting == 'default' else 0}\n" for p, code, setting in cases]
    nov = parse_driver(run_driver(binary, kernel, requests), "A", len(cases), 8)
    out = []
    try:
        for (p, code, setting), n in zip(cases, nov):
            t = ts.tdb_jd(p["apparent_tdb"])
            app = earth.at(t).observe(eph[code]).apparent(deflectors=DEFLECTION[setting])
            ra, dec, dist = app.radec(epoch="date")
            lat, lon, _ = app.frame_latlon(ecliptic_frame)
            out.append({"point": p, "code": code, "setting": setting,
                        "sky": (float(ra.hours), float(dec.degrees), float(dist.au), float(lon.degrees),
                                float(lat.degrees)),
                        "nov": n})
    finally:
        eph.close()
    return out


# --------------------------------------------------------------------------------------------------------------
# The rows
# --------------------------------------------------------------------------------------------------------------


def model_rows(points: list[dict[str, Any]], r: dict[str, Any], tally: Tally) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for i, p in enumerate(points):
        base, where = instant_block(p), p["id"]
        n = r["nov"][i]

        def diffs(section: str, values: dict[str, float]) -> dict[str, Any]:
            out: dict[str, Any] = {}
            names = list(values)
            for a in range(len(names)):
                for b in range(a + 1, len(names)):
                    key = f"{names[b]}_minus_{names[a]}_arcsec"
                    d = values[names[b]] - values[names[a]]
                    out.update(patterned(key, d))
                    tally.add(section, key, p["stratum"], d, where)
            return out

        obl06 = float(r["erfa_obl06"][i])
        mean = {"erfa": obl06 * ARCSEC_PER_RADIAN, "skyfield": float(r["sky_mean_deg"][i]) * ARCSEC_PER_DEGREE,
                "supernovas": n[0]}
        rows.append({"section": "mean_obliquity", **base,
                     **patterned("erfa_obl06_radians", obl06),
                     **patterned("skyfield_earth_tilt_mean_degrees", float(r["sky_mean_deg"][i])),
                     **patterned("supernovas_mean_obliq_arcsec", n[0]),
                     **patterned("supernovas_e_tilt_mean_degrees", n[1]),
                     **patterned("erfa_arcsec", mean["erfa"]), **patterned("skyfield_arcsec", mean["skyfield"]),
                     **diffs("mean_obliquity", mean)})

        dpsi06, deps06 = float(r["erfa_nut06a"][0][i]), float(r["erfa_nut06a"][1][i])
        dpsi00, deps00 = float(r["erfa_nut00a"][0][i]), float(r["erfa_nut00a"][1][i])
        row = {"section": "nutation", **base,
               **patterned("erfa_nut06a_radians", [dpsi06, deps06]),
               **patterned("erfa_nut00a_radians", [dpsi00, deps00]),
               **patterned("skyfield_earth_tilt_arcsec", [float(r["sky_dpsi"][i]), float(r["sky_deps"][i])]),
               **patterned("supernovas_nutation_angles_arcsec", [n[6], n[7]]),
               **patterned("supernovas_e_tilt_arcsec", [n[4], n[5]]),
               **patterned("supernovas_iau2000a_radians", [n[8], n[9]])}
        for j, name in ((0, "dpsi"), (1, "deps")):
            values = {"erfa": (dpsi06, deps06)[j] * ARCSEC_PER_RADIAN, "skyfield": float((r["sky_dpsi"], r["sky_deps"])[j][i]),
                      "supernovas": n[6 + j]}
            variant = {"erfa_nut00a": (dpsi00, deps00)[j] * ARCSEC_PER_RADIAN,
                       "supernovas_iau2000a": n[8 + j] * ARCSEC_PER_RADIAN}
            row.update(patterned(f"{name}_erfa_arcsec", values["erfa"]))
            row.update(patterned(f"{name}_erfa_nut00a_arcsec", variant["erfa_nut00a"]))
            row.update(patterned(f"{name}_supernovas_iau2000a_arcsec", variant["supernovas_iau2000a"]))
            for key, d in ((f"{name}_skyfield_minus_erfa_arcsec", values["skyfield"] - values["erfa"]),
                           (f"{name}_supernovas_minus_erfa_arcsec", values["supernovas"] - values["erfa"]),
                           (f"{name}_supernovas_minus_skyfield_arcsec", values["supernovas"] - values["skyfield"]),
                           (f"{name}_skyfield_minus_erfa_nut00a_arcsec", values["skyfield"] - variant["erfa_nut00a"]),
                           (f"{name}_supernovas_iau2000a_minus_erfa_nut00a_arcsec",
                            variant["supernovas_iau2000a"] - variant["erfa_nut00a"])):
                row.update(patterned(key, d))
                tally.add("nutation", key, p["stratum"], d, where)
        rows.append(row)

        sky_true, nov_true = float(r["sky_true_deg"][i]), n[2]
        d = (nov_true - sky_true) * ARCSEC_PER_DEGREE
        tally.add("true_obliquity", "supernovas_minus_skyfield_arcsec", p["stratum"], d, where)
        rows.append({"section": "true_obliquity", **base,
                     **patterned("skyfield_earth_tilt_true_degrees", sky_true),
                     **patterned("supernovas_e_tilt_true_degrees", nov_true),
                     **patterned("supernovas_minus_skyfield_arcsec", d)})

        m_erfa = [[float(r["erfa_pnm06a"][i][a][b]) for b in range(3)] for a in range(3)]
        m_sky = [[float(r["sky_m"][a][b][i]) for b in range(3)] for a in range(3)]
        m_nov = [[n[10 + 3 * a + b] for b in range(3)] for a in range(3)]
        row = {"section": "bias_precession_nutation", **base,
               **patterned("erfa_pnm06a", [x for line in m_erfa for x in line]),
               **patterned("skyfield_m", [x for line in m_sky for x in line]),
               **patterned("supernovas_gcrs_to_tod", [x for line in m_nov for x in line])}
        for key, (x, y) in (("skyfield_from_erfa_arcsec", (m_sky, m_erfa)),
                            ("supernovas_from_erfa_arcsec", (m_nov, m_erfa)),
                            ("supernovas_from_skyfield_arcsec", (m_nov, m_sky))):
            angle = rotation_between_arcsec(x, y)
            row.update(patterned(f"rotation_{key}", angle))
            tally.add("bias_precession_nutation", f"rotation_{key}", p["stratum"], angle, where)
        rows.append(row)

        if p["t"] is None or abs(p["t"]) <= GAP_SPAN:
            obl80 = float(r["erfa_obl80"][i])
            gap = (obl80 - obl06) * ARCSEC_PER_RADIAN
            tally.add("mean_obliquity_1980_minus_2006", "obl80_minus_obl06_arcsec", p["stratum"], gap, where)
            rows.append({"section": "mean_obliquity_1980_minus_2006", **base,
                         **patterned("erfa_obl80_radians", obl80), **patterned("erfa_obl06_radians", obl06),
                         **patterned("obl80_minus_obl06_arcsec", gap)})
    return rows


def apparent_rows(readings: list[dict[str, Any]], tally: Tally) -> list[dict[str, Any]]:
    rows = []
    for reading in readings:
        p, code, setting = reading["point"], reading["code"], reading["setting"]
        s_ra, s_dec, s_dist, s_lon, s_lat = reading["sky"]
        n_ra, n_dec, n_dis, x, y, z, n_lon, n_lat = reading["nov"]
        where = f"{p['id']}/{TARGETS[code]}/{setting}"
        stratum = f"{p['stratum']}/{setting}"
        sep = separation_arcsec(unit_vector(s_ra, s_dec), unit_vector(n_ra, n_dec))
        ecl = separation_arcsec(unit_vector(s_lon / 15.0, s_lat), unit_vector(n_lon / 15.0, n_lat))
        dlat = (n_lat - s_lat) * ARCSEC_PER_DEGREE
        dlon = wrapped_degrees(n_lon, s_lon) * ARCSEC_PER_DEGREE
        for key, d in (("separation_of_date_arcsec", sep), ("separation_ecliptic_of_date_arcsec", ecl),
                       ("latitude_supernovas_minus_skyfield_arcsec", dlat),
                       ("longitude_supernovas_minus_skyfield_arcsec", dlon)):
            tally.add("apparent_place", key, stratum, d, where)
            tally.add("apparent_place", key, f"{stratum}/{TARGETS[code]}", d, where)
        rows.append({"section": "apparent_place", "grid": p["grid"], "instant": p["id"], "stratum": p["stratum"],
                     **patterned("jd_tdb", p["apparent_tdb"]), "target_code": code, "target": TARGETS[code],
                     "deflection": setting,
                     **patterned("skyfield_ra_hours_dec_degrees_distance_au", [s_ra, s_dec, s_dist]),
                     **patterned("skyfield_ecliptic_longitude_latitude_degrees", [s_lon, s_lat]),
                     **patterned("supernovas_ra_hours_dec_degrees_distance_au", [n_ra, n_dec, n_dis]),
                     **patterned("supernovas_r_hat", [x, y, z]),
                     **patterned("supernovas_ecliptic_longitude_latitude_degrees", [n_lon, n_lat]),
                     **patterned("separation_of_date_arcsec", sep),
                     **patterned("separation_ecliptic_of_date_arcsec", ecl),
                     **patterned("latitude_supernovas_minus_skyfield_arcsec", dlat),
                     **patterned("longitude_supernovas_minus_skyfield_arcsec", dlon)})
    return rows


SECTIONS = ("mean_obliquity", "nutation", "true_obliquity", "bias_precession_nutation",
            "mean_obliquity_1980_minus_2006", "apparent_place")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    for name in ("--kernel", "--grid-values", "--grid-values-sha256", "--supernovas-source", "--supernovas-tarball",
                 "--supernovas-archive", "--supernovas-build-record", "--cspice-toolkit", "--cspice-package",
                 "--erfa-licence", "--budget-row", "--out"):
        parser.add_argument(name, required=True)
    args = parser.parse_args(argv)
    print(describe_reserved_names())
    try:
        generator = generator_for(Path(__file__))
        out_path = Path(args.out) / OUTPUT_NAME
        if out_path.exists():
            raise Refusal(f"{OUTPUT_NAME} exists in the output directory; each emission goes to a new one")
        if not args.budget_row or args.budget_row != args.budget_row.strip():
            raise Refusal("--budget-row is the consumer's row id, given exactly")
        identity = python_identity(Path(args.erfa_licence))
        kernel = Path(args.kernel)
        pin = verify(kernel, PINS["de440s.bsp"])
        archives = {"supernovas_tarball": sha256_file(Path(args.supernovas_tarball)),
                    "cspice_package": sha256_file(Path(args.cspice_package))}
        if archives != ARCHIVE_PINS:
            raise Refusal(f"source archives {archives} are not the pins {ARCHIVE_PINS}")
        source = Path(args.supernovas_source)
        supernovas_licence = sha256_file(source / "LICENSE")
        if supernovas_licence != LICENCE_PINS["supernovas"]:
            raise Refusal(f"the supernovas licence text is not the one read (sha256 {supernovas_licence})")
        identity["licences"]["supernovas"] = supernovas_licence

        points, civil = instants(Path(args.grid_values), args.grid_values_sha256)
        with tempfile.TemporaryDirectory() as work:
            binary, build = build_driver(source, Path(args.cspice_toolkit), Path(args.supernovas_archive),
                                         Path(args.supernovas_build_record), Path(work))
            models = read_models(points, binary, kernel)
            readings = read_apparent(points, binary, kernel)
    except Refusal as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2

    tally = Tally()
    rows = model_rows(points, models, tally) + apparent_rows(readings, tally)
    counts = {section: sum(1 for row in rows if row["section"] == section) for section in SECTIONS}
    header = Header(
        fixture_kind="numeric_pin",
        reference="none",
        contract_deviation=[{
            "clause": "reference",
            "deviation": "the registry has no value for an independent implementation of the IAU 2006/2000A models, "
                         "nor for an apparent place of date computed with one on a development ephemeris",
            "closes_when": "the consumer decides which of these candidates, if any, may be a reference for the frame "
                           "of date — this file is the measurement that decision reads, and takes no part in it",
        }],
        generator=generator,
        generated=today(),
        title="the frame of date by three implementations of one model set, and the apparent place by two on one kernel",
        oracle={
            "candidates": {
                "erfa": {"binding": "pyerfa", "binding_version": identity["versions"]["pyerfa"],
                         "library_version": identity["erfa_library"][0], "sofa_release": identity["erfa_library"][1],
                         "entry_points": ["obl06", "obl80", "nut06a", "nut00a", "pnm06a",
                                          "dtf2d", "utctai", "taitt", "dtdb", "tttdb"]},
                "skyfield": {"version": identity["versions"]["skyfield"],
                             "reader": {"jplephem": identity["versions"]["jplephem"]},
                             "entry_points": ["nutationlib.earth_tilt", "Time.M", "apparent(deflectors=...)",
                                              "radec(epoch='date')", "frame_latlon(ecliptic_frame)"],
                             "timescale": "load.timescale(builtin=True) — its own leap and offset tables, no download"},
                "supernovas": {"version": SUPERNOVAS_VERSION, "source_tarball_sha256": archives["supernovas_tarball"],
                               "reader": {"toolkit": TOOLKIT_VERSION,
                                          "package_sha256": archives["cspice_package"]},
                               "build": build,
                               "entry_points": ["mean_obliq", "e_tilt", "nutation_angles", "iau2000a", "gcrs_to_tod",
                                                "novas_sky_pos", "equ2ecl"],
                               "fixed_arguments": {
                                   "accuracy": "NOVAS_FULL_ACCURACY", "observer": "geocentre",
                                   "time": "TDB, no leap seconds, no UT1 offset", "polar_offsets": [0, 0],
                                   "deflection": "grav_bodies_full_accuracy: the library's default set, or 0"}},
            },
            "licences": {name: {"text_sha256": digest, "name": LICENCE_NAMES[name]}
                         for name, digest in sorted(identity["licences"].items())},
            "licence_reading": (
                "each text read in full: each governs the software and its redistribution, and none states a "
                "condition on numbers the software computes. ⛔ Not a legal conclusion"),
            "toolkit_terms": "the toolkit package carries no licence file; its publisher's terms are recorded beside "
                             "this file, not here",
            "kernel": oracle_identity(kernel, pin),
            "numpy": identity["versions"]["numpy"],
            "network_requests": 0,
        },
        request={
            "sweep": {"rule": "lo + (hi - lo) * i / 20000 for i in 0..20000, evaluated left to right",
                      **patterned("lo_centuries", sweep()[0]), **patterned("hi_centuries", sweep()[-1]),
                      "span_jd_tt": list(SPAN_JD), "instants": SWEEP_STEPS + 1,
                      "within_1850_2150": sum(1 for t in sweep() if abs(t) <= GAP_SPAN)},
            "geocentric_grid": {"values_sha256": args.grid_values_sha256,
                                "instants": sum(1 for p in points if p["grid"] == "geocentric_grid"),
                                "time_scale": "TDB, as that file records it"},
            "civil_instant": {"civil": CIVIL_INSTANT["civil"], "utc_offset_seconds": CIVIL_INSTANT["utc_offset_seconds"],
                              **patterned("utc_parts", list(civil["utc"])), **patterned("tt_parts", list(civil["tt"])),
                              **patterned("tdb_minus_tt_seconds", civil["tdb_minus_tt_seconds"]),
                              **patterned("tdb_parts", list(civil["tdb"]))},
            "time_arguments": (
                "for the models, the two-part date jd_parts goes to every library's own time argument unchanged: ERFA's "
                "two-part TT, Skyfield's tt_jd(whole, fraction), SuperNOVAS's TDB as jd1 + jd2 (its one-argument entry "
                "points) or as centuries ((jd1 - 2451545.0) + jd2) / 36525.0. ⚠ The geocentric grid's dates are TDB "
                "and are given to the TT arguments as they are; TT - TDB is under 2 ms and is not converted away. For "
                "the apparent place, one TDB date as a single double goes to both libraries"),
            "targets": [{"code": code, "name": name} for code, name in TARGETS.items()],
            "deflection": {name: list(codes) for name, codes in DEFLECTION.items()},
            "regenerate": "generators/of_date_candidates.py (the usage in its docstring), in an environment holding "
                          "exactly the pinned libraries",
        },
        classification={section: {"class": "reference_only"} for section in SECTIONS},
        budget_row=args.budget_row,
        row_schema={
            "section": "the quantity, in the order measured",
            "grid": "which grid the instant belongs to: sweep, geocentric_grid or civil_instant",
            "instant": "the instant's id within its grid",
            "stratum": "the stratum its differences are counted in",
            "t_centuries": "the sweep's own value, TT Julian centuries from J2000",
            "jd_parts": "the two-part Julian date given to the models",
            "unit_suffix": "_radians, _degrees, _arcsec: a library's return in its own unit, or that return converted "
                           "to arcseconds; the name says which",
            "minus": "a key holding _minus_ is the difference between two libraries' returns of one quantity, in "
                     "arcseconds",
            "rotation": "a key starting rotation_ is the angle of the rotation between two libraries' matrices",
            "separation": "a key starting separation_ is the angle between two libraries' directions",
        },
        summary={
            "rows": len(rows), "rows_by_section": counts,
            "levels_arcsec": [f"{level:g}" for level in LEVELS_ARCSEC],
            "levels_meaning": "reporting levels for the counts below. ⛔ Not bands: nothing passes or fails here",
            "differences": tally.as_json(),
            "absent": {"erfa_true_obliquity": "no ERFA entry point returns a true obliquity; a sum of two returns "
                                              "is a derived value, and this file derives none"},
            "host": {**host_record(), "processor": platform.processor()},
        },
        notes=[
            "⛔ Three programs implementing one model set are one model, implemented three times. Their agreement "
            "bounds how differently it can be implemented; it says nothing about the model.",
            "⛔ The apparent place is two implementations on one kernel. Neither is the publisher's service, and "
            "nothing here is compared with one.",
            "⚠ The default deflecting bodies are each library's own; both name the Sun, Jupiter and Saturn, and "
            "both take Jupiter's and Saturn's barycentres from this kernel, which holds no planet centre for them.",
            "⚠ A unit conversion is applied to a return before a difference is taken: radians by 648000/pi, degrees "
            "by 3600. Both forms are written.",
        ],
    )
    written = write_jsonl(out_path, header, rows, declared_sections=list(SECTIONS))
    print(f"wrote {written} rows -> {out_path.name} (sha256 {sha256_file(out_path)})")
    print(json.dumps(counts))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
