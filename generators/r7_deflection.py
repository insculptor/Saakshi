"""R7 — light deflection by the IAU SOFA library for a source at a finite distance, as a change of longitude of date.

At each instant of the frame-of-date file named by its digest and for each of ten solar-system targets, the
geocentric direction to the target, light-time corrected, is handed to the library's finite-distance deflection
routine (``iauLd``) once per applicable deflector and then to its aberration routine (``iauAb``); and, beside it,
the same direction to ``iauAb`` alone. Both proper directions are taken into the true equator and equinox of date
and onto the ecliptic of date with that file's own matrix and true obliquity, and the difference of the two
longitudes is written down with its bits — the change the deflection makes, through aberration, in the order
deflection then aberration.

* ⭐ **Which routine**: ``iauLd``, the one the library's own published cookbook describes as *"valid for solar-system
  targets as well as distant objects, which is not strictly true for either iauLdsun or iauLdn"* — it takes the
  body-to-source direction separately. ``iauLdn`` is documented *"For a star"*. ⛔ No source file of the library is
  read by this program; the documents are quoted in the header with their pages.
* ⭐ **The geometry is declared, never the library's choice**: the observer is the geocentre; the target's position
  is its light-time-corrected one (the SPICE Toolkit's converged Newtonian correction on the pinned short-span
  kernel); each deflector is read at its closest-approach epoch — the instant ``t - s*/c``, with ``s*`` the distance
  along the ray from the observer to the foot of the perpendicular from the deflector at ``t``, held to ``[0, the
  ray's length]``; the deflectors are the Sun and the Venus, Jupiter, Saturn, Uranus and Neptune system barycentres,
  with their system GMs from the pinned planetary-constants file; ⛔ **a body never deflects light from its own
  system** (the Sun's from the Sun, Venus's from the Venus barycentre, and each outer barycentre's from itself);
  and ⛔ **a ray passing inside a deflector's equatorial radius, between the observer and the target, is recorded as
  such and nothing is computed for it**.
* ⭐ **The Sun's potential, stated**: the library's aberration routine adds the gravitational potential term of the
  Sun through its Sun-observer distance argument (its documentation's words in the header). So three legs are
  written: deflection on; deflection off as the routine is called; and deflection off with that distance handed as
  ``1e300`` au — ⚠ an input outside the routine's physical domain, used only to separate the term — and the two
  longitude differences that follow from them.
* ⛔ **No band, no verdict.** Every section is ``reference_only``; no budget row.
* ⛔ **Recorder, never explainer.**

Usage:
    python generators/r7_deflection.py --kernel de440s.bsp --gm gm_de440.tpc --radii pck00011.tpc \\
        --frame R7_FILE --frame-sha256 HEX --sofa-build DIR --sofa-source DIR --out DIR
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import struct
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Sequence

HERE = Path(__file__).resolve().parent
sys.dont_write_bytecode = True
for _path in (str(HERE.parent / "src"), str(HERE)):
    if _path not in sys.path:
        sys.path.insert(0, _path)

from saakshi.fixture import Header, bits, describe_reserved_names, write_jsonl  # noqa: E402
from saakshi.kernels import oracle_identity, verify  # noqa: E402
from saakshi.provenance import generator_for, host_record, today  # noqa: E402

import r7_frame_of_date as frame  # noqa: E402

SCRIPT = "generators/r7_deflection.py"
DRIVER_SOURCE = HERE / "native" / "deflection_legs.c"
VALUES_PATH = "standards/r7-deflection.jsonl"

GM_FILE_SHA256 = "924ddf4fb9ead9fe8a1aa55780bcabde40b09d00065d58226e24b68d8092f140"
RADII_FILE_SHA256 = "3dff7b1dbeceaa01f25467767d3fa25816051c85d162d1edf04acb310ee28bb1"

C_KM_S = 299_792.458
AU_KM = 149_597_870.7
SECONDS_PER_DAY = 86_400.0
C_KM_PER_DAY = C_KM_S * SECONDS_PER_DAY
J2000 = 2451545.0
ARCSEC_PER_RADIAN = 648_000.0 / math.pi
S_FAR = 1.0e300
DLIM = 1.0e-20

TARGETS: tuple[tuple[int, str], ...] = (
    (10, "sun"), (301, "moon"), (199, "mercury"), (299, "venus"), (4, "mars_barycentre"),
    (5, "jupiter_barycentre"), (6, "saturn_barycentre"), (7, "uranus_barycentre"), (8, "neptune_barycentre"),
    (9, "pluto_barycentre"),
)
#: The deflectors, body id ascending, each with the body its radius is read for and the ids of its own system.
DEFLECTORS: tuple[dict[str, Any], ...] = (
    {"id": 2, "name": "venus_barycentre", "radius_of": 299, "system": (2, 299)},
    {"id": 5, "name": "jupiter_barycentre", "radius_of": 599, "system": (5,)},
    {"id": 6, "name": "saturn_barycentre", "radius_of": 699, "system": (6,)},
    {"id": 7, "name": "uranus_barycentre", "radius_of": 799, "system": (7,)},
    {"id": 8, "name": "neptune_barycentre", "radius_of": 899, "system": (8,)},
    {"id": 10, "name": "sun", "radius_of": 10, "system": (10,)},
)

DOCUMENTS: tuple[dict[str, str], ...] = (
    {"file": "doc/sofa_ast_c.pdf", "page": "printed p. 11 (section 4.3)",
     "words": "The function iauLd is quite general. ... Its arguments include (among other things) the mass of the "
              "body and full details of the geometrical arrangement. The latter means the function is valid for "
              "solar-system targets as well as distant objects, which is not strictly true for either iauLdsun or "
              "iauLdn."},
    {"file": "doc/sofa_ast_c.pdf", "page": "printed p. 83 (iauLdn)",
     "words": "For a star, apply light deflection by multiple solar-system bodies, as part of transforming "
              "coordinate direction into natural direction."},
    {"file": "doc/sofa_ast_c.pdf", "page": "printed p. 83 (iauLdn, Note 5)",
     "words": "If a different treatment is preferred, the user has the option of instead using the iauLd function. "
              "Similarly, iauLd can be used for cases where the source is nearby, not a star."},
    {"file": "doc/sofa_ast_c.pdf", "page": "printed p. 82 (iauLd, Note 3)",
     "words": "The barycentric position of the deflecting body should ideally correspond to the time of closest "
              "approach of the light ray to the body."},
    {"file": "doc/sofa_ast_c.pdf", "page": "printed p. 82 (iauLd, Note 7)",
     "words": "To accumulate total light deflection taking into account the contributions from several bodies, call "
              "the present routine for each body in succession, in decreasing order of distance from the observer."},
    {"file": "doc/sofa_ast_c.pdf", "page": "printed p. 29 (iauAb, Note 1)",
     "words": "The gravitational potential term from Eq. (7) in Klioner (2003) is added, taking into account only "
              "the Sun's contribution. This has a maximum effect of about 0.4 µas."},
    {"file": "doc/sofa_ast_c.pdf", "page": "printed p. 2 (Figure 1)",
     "words": "astrometric [ α, δ ] → light deflection → aberration → GCRS [ α, δ ]"},
)


class Refusal(Exception):
    """A condition under which nothing may be written."""


def unit(x: Sequence[float]) -> list[float]:
    n = math.sqrt(x[0] * x[0] + x[1] * x[1] + x[2] * x[2])
    return [x[0] / n, x[1] / n, x[2] / n]


def norm(x: Sequence[float]) -> float:
    return math.sqrt(x[0] * x[0] + x[1] * x[1] + x[2] * x[2])


def dot(a: Sequence[float], b: Sequence[float]) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def cross(a: Sequence[float], b: Sequence[float]) -> list[float]:
    return [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]]


def sub(a: Sequence[float], b: Sequence[float]) -> list[float]:
    return [a[0] - b[0], a[1] - b[1], a[2] - b[2]]


def value_of(text: str) -> float:
    return struct.unpack(">d", bytes.fromhex(text))[0]


# ======================================================================================
# The geometry
# ======================================================================================


def closest_approach(x_a0: Sequence[float], x_o: Sequence[float], k: Sequence[float], length: float) -> float:
    """``s*``: the distance from the observer along the ray to the foot of the perpendicular from the deflector,
    held to ``[0, length]`` by comparison."""
    s = dot(sub(x_a0, x_o), [-k[0], -k[1], -k[2]])
    if s < 0.0:
        return 0.0
    if s > length:
        return length
    return s


def inside_disc(x_a: Sequence[float], x_o: Sequence[float], k: Sequence[float], length: float, radius: float
                ) -> tuple[bool, float, float]:
    """Whether the ray passes inside the deflector's radius between observer and source; and ``s_ca``, ``b``."""
    r = sub(x_a, x_o)
    s_ca = dot(r, [-k[0], -k[1], -k[2]])
    b = norm(cross(r, k))
    return (0.0 < s_ca < length and b < radius), s_ca, b


def applicable(target: int, deflector: dict[str, Any]) -> bool:
    """⛔ A body never deflects light from its own system."""
    return target not in deflector["system"]


def longitude_of_date(direction: Sequence[float], npb: Sequence[float], true_obliquity: float) -> float:
    """``u = NPB s`` (row-major), ``e = R1(eps) u``, ``lambda = atan2(e_y, e_x)`` in ``[0, 2 pi)``."""
    u = [npb[3 * i] * direction[0] + npb[3 * i + 1] * direction[1] + npb[3 * i + 2] * direction[2] for i in range(3)]
    c, s = math.cos(true_obliquity), math.sin(true_obliquity)
    ey = c * u[1] + s * u[2]
    ex = u[0]
    lam = math.atan2(ey, ex)
    return lam + 2.0 * math.pi if lam < 0.0 else lam


def wrapped_arcsec(a: float, b: float) -> float:
    d = math.remainder(a - b, 2.0 * math.pi)
    return d * ARCSEC_PER_RADIAN


# ======================================================================================
# The inputs
# ======================================================================================


def read_frame(path: Path, expected: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Per instant: the TDB, the matrix and the true obliquity, from the frame-of-date file by its digest."""
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != expected:
        raise Refusal("the frame-of-date file is not the one named")
    lines = data.decode("utf-8").splitlines()
    header = json.loads(lines[0])
    if header.get("reference") != "R7":
        raise Refusal("the frame-of-date file is not one this reference wrote")
    by: dict[str, dict[str, Any]] = {}
    for line in lines[1:]:
        row = json.loads(line)
        slot = by.setdefault(row["epoch_id"], {"epoch_id": row["epoch_id"], "jd_tdb_bits": row["jd_tdb_bits"]})
        if row["section"] == "bias_precession_nutation":
            slot["npb"] = [value_of(v) for v in row["value_bits"]]
        elif row["section"] == "true_obliquity":
            slot["true_obliquity"] = value_of(row["value_bits"])
    instants = [by[k] for k in sorted(by)]
    for slot in instants:
        if "npb" not in slot or "true_obliquity" not in slot:
            raise Refusal(f"{slot['epoch_id']}: the frame-of-date file lacks its matrix or its true obliquity")
    return instants, {"sha256": expected, "title": header.get("title"), "generator": header.get("generator")}


def constants(gm_file: Path, radii_file: Path, sp) -> dict[int, dict[str, float]]:
    """Each deflector's system GM and its body's equatorial radius, through the toolkit, from the pinned files."""
    for path, pin in ((gm_file, GM_FILE_SHA256), (radii_file, RADII_FILE_SHA256)):
        if hashlib.sha256(path.read_bytes()).hexdigest() != pin:
            raise Refusal(f"{path.name} is not the file pinned")
    sp.furnsh(str(gm_file))
    sp.furnsh(str(radii_file))
    out = {}
    for d in DEFLECTORS:
        gm = float(sp.bodvcd(d["id"], "GM", 1)[1][0])
        radius = float(sp.bodvcd(d["radius_of"], "RADII", 3)[1][0])
        out[d["id"]] = {"gm_km3_s2": gm, "equatorial_radius_km": radius}
    out["sun_gm"] = {"gm_km3_s2": out[10]["gm_km3_s2"]}
    return out


def cases(instants: list[dict[str, Any]], kernel: Path, consts: dict, sp) -> tuple[list[dict[str, Any]], list[str]]:
    """Every (instant, target): its legs' inputs, or its occultation. And the driver's input lines."""
    sp.furnsh(str(kernel))
    out, lines = [], []
    for slot in instants:
        jd = value_of(slot["jd_tdb_bits"])
        et = (jd - J2000) * SECONDS_PER_DAY
        state_o, _ = sp.spkezr("399", et, "J2000", "NONE", "0")
        x_o, v_o = [float(x) for x in state_o[:3]], [float(x) for x in state_o[3:]]
        sun, _ = sp.spkpos("10", et, "J2000", "NONE", "0")
        s_au = norm(sub(x_o, [float(x) for x in sun])) / AU_KM
        v = [x / C_KM_S for x in v_o]
        bm1 = math.sqrt(1.0 - dot(v, v))
        for target, name in TARGETS:
            r, lt = sp.spkpos(str(target), et, "J2000", "CN", "399")
            r = [float(x) for x in r]
            x_s = [x_o[i] + r[i] for i in range(3)]
            k = unit(sub(x_o, x_s))
            length = norm(r)
            p = unit(r)
            record: dict[str, Any] = {"epoch_id": slot["epoch_id"], "jd_tdb_bits": slot["jd_tdb_bits"],
                                      "target": name, "target_id": target, "light_time_s": float(lt),
                                      "deflectors": [], "slot": slot}
            applied, occulted = [], []
            for d in DEFLECTORS:
                entry: dict[str, Any] = {"deflector": d["name"], "deflector_id": d["id"]}
                if not applicable(target, d):
                    entry["state"] = "not_applicable_own_system"
                    record["deflectors"].append(entry)
                    continue
                x_a0 = [float(x) for x in sp.spkpos(str(d["id"]), et, "J2000", "NONE", "0")[0]]
                s_star = closest_approach(x_a0, x_o, k, length)
                tau_days = s_star / C_KM_PER_DAY
                x_a = [float(x) for x in sp.spkpos(str(d["id"]), et - tau_days * SECONDS_PER_DAY, "J2000", "NONE",
                                                   "0")[0]]
                radius = consts[d["id"]]["equatorial_radius_km"]
                inside, s_ca, b = inside_disc(x_a, x_o, k, length, radius)
                entry.update({"closest_approach_days_before": tau_days, "s_ca_km": s_ca, "b_km": b,
                              "equatorial_radius_km": radius})
                if inside:
                    entry["state"] = "ray_inside_disc"
                    occulted.append(d["name"])
                else:
                    entry["state"] = "applied"
                    em_au = norm(sub(x_o, x_a)) / AU_KM
                    entry["em_au"] = em_au
                    applied.append((em_au, d, unit(sub(x_s, x_a)), unit(sub(x_o, x_a))))
                record["deflectors"].append(entry)
            record["occulted_by"] = occulted
            if not occulted:
                applied.sort(key=lambda t: -t[0])  # ⭐ decreasing distance from the observer (the routine's note)
                record["order_applied"] = [d["name"] for _em, d, _q, _e in applied]
                case_id = len(lines)  # ⭐ the cases sent, numbered 0 .. n-1; an occulted record sends none
                fields = ["C", str(case_id), *(bits(x) for x in p), *(bits(x) for x in v), bits(s_au), bits(bm1),
                          str(len(applied))]
                for em_au, d, q, e in applied:
                    bm = consts[d["id"]]["gm_km3_s2"] / consts["sun_gm"]["gm_km3_s2"]
                    fields += [bits(bm), *(bits(x) for x in q), *(bits(x) for x in e), bits(em_au), bits(DLIM)]
                lines.append(" ".join(fields))
                record["inputs"] = {"p": p, "v": v, "s_au": s_au, "bm1": bm1}
                record["case"] = case_id
            out.append(record)
    return out, lines


# ======================================================================================
# The library
# ======================================================================================


def build_driver(build: Path, source: Path, work: Path) -> tuple[Path, dict[str, Any]]:
    binary = work / "deflection_legs"
    done = subprocess.run(["cc", *frame.DRIVER_CFLAGS, f"-I{source}", str(DRIVER_SOURCE),
                           str(build / "lib" / "libsofa_c.a"), "-lm", "-o", str(binary)],
                          capture_output=True, text=True, check=False)
    if done.returncode != 0:
        raise Refusal(f"the driver did not build: {done.stderr[-600:]}")
    return binary, {"source": {"path": "generators/native/deflection_legs.c",
                               "sha256": hashlib.sha256(DRIVER_SOURCE.read_bytes()).hexdigest()},
                    "cflags": list(frame.DRIVER_CFLAGS),
                    "binary_sha256": hashlib.sha256(binary.read_bytes()).hexdigest()}


def run_driver(binary: Path, lines: list[str]) -> dict[int, dict[str, list[float]]]:
    done = subprocess.run([str(binary)], input="\n".join(lines) + "\n", capture_output=True, text=True, check=False,
                          timeout=600)
    out = done.stdout.splitlines()
    if done.returncode != 0 or not out or out[0] != "V deflection_legs 1":
        raise Refusal(f"the driver stopped (exit {done.returncode}): {(out[-1] if out else done.stderr)[:200]}")
    answers = {}
    for line in out[1:]:
        parts = line.split()
        if parts[0] != "L" or len(parts) != 2 + 12:
            raise Refusal(f"the driver answered {line[:60]!r}")
        v = [value_of(h) for h in parts[2:]]
        answers[int(parts[1])] = {"natural": v[0:3], "proper_on": v[3:6], "proper_off": v[6:9],
                                  "proper_off_far": v[9:12]}
    if sorted(answers) != list(range(len(lines))):
        raise Refusal(f"{len(answers)} answers for {len(lines)} cases")
    return answers


def vec(name: str, x: Sequence[float]) -> dict[str, Any]:
    return {name: list(x), f"{name}_bits": [bits(v) for v in x]}


def scalar(name: str, x: float) -> dict[str, Any]:
    return {name: x, f"{name}_bits": bits(x)}


def rows_for(records: list[dict[str, Any]], answers: dict[int, dict[str, list[float]]]) -> list[dict[str, Any]]:
    rows = []
    for rec in records:
        slot = rec["slot"]
        base = {"epoch_id": rec["epoch_id"], "jd_tdb": value_of(rec["jd_tdb_bits"]), "jd_tdb_bits": rec["jd_tdb_bits"],
                "target": rec["target"], "target_id": rec["target_id"], **scalar("light_time_s", rec["light_time_s"]),
                "deflectors": [{k: (v if not isinstance(v, float) else v) for k, v in d.items()}
                               for d in rec["deflectors"]]}
        for d in base["deflectors"]:
            for key in [k for k in d if isinstance(d[k], float)]:
                d[f"{key}_bits"] = bits(d[key])
        if rec["occulted_by"]:
            rows.append({"section": "ray_inside_disc", **base, "occulted_by": rec["occulted_by"]})
            continue
        a = answers[rec["case"]]
        lam = {leg: longitude_of_date(a[f"proper_{leg}"], slot["npb"], slot["true_obliquity"])
               for leg in ("on", "off", "off_far")}
        rows.append({
            "section": "deflection", **base, "order_applied": rec["order_applied"],
            **vec("p", rec["inputs"]["p"]), **vec("observer_velocity_c", rec["inputs"]["v"]),
            **scalar("sun_distance_au", rec["inputs"]["s_au"]), **scalar("bm1", rec["inputs"]["bm1"]),
            **vec("natural", a["natural"]), **vec("proper_on", a["proper_on"]), **vec("proper_off", a["proper_off"]),
            **vec("proper_off_far", a["proper_off_far"]),
            **scalar("longitude_on", lam["on"]), **scalar("longitude_off", lam["off"]),
            **scalar("longitude_off_far", lam["off_far"]),
            **scalar("delta_longitude_as_called_arcsec", wrapped_arcsec(lam["on"], lam["off"])),
            **scalar("delta_longitude_potential_in_on_leg_only_arcsec", wrapped_arcsec(lam["on"], lam["off_far"])),
            **scalar("potential_term_arcsec", wrapped_arcsec(lam["off"], lam["off_far"])),
        })
    return rows


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    for name in ("--kernel", "--gm", "--radii", "--frame", "--sofa-build", "--sofa-source", "--out"):
        parser.add_argument(name, required=True, type=Path)
    parser.add_argument("--frame-sha256", required=True)
    args = parser.parse_args(argv)
    import spiceypy as sp  # noqa: PLC0415

    generator = generator_for(HERE / Path(SCRIPT).name)
    print(describe_reserved_names())
    if (args.out / VALUES_PATH).exists():
        raise Refusal(f"{args.out / VALUES_PATH} exists; a record is never overwritten")
    pin = verify(args.kernel)
    build = frame.read_build(args.sofa_build, args.sofa_source)
    instants, frame_source = read_frame(args.frame, args.frame_sha256)
    try:
        consts = constants(args.gm, args.radii, sp)
        records, lines = cases(instants, args.kernel, consts, sp)
    finally:
        sp.kclear()
    with tempfile.TemporaryDirectory() as work:
        binary, driver = build_driver(args.sofa_build, args.sofa_source, Path(work))
        answers = run_driver(binary, lines)
    rows = rows_for(records, answers)
    sections = ["deflection", "ray_inside_disc"]
    counts = {s: sum(1 for r in rows if r["section"] == s) for s in sections}
    sections = [s for s in sections if counts[s]]
    header = Header(
        fixture_kind="numeric_pin",
        reference="R7",
        generator=generator,
        generated=today(),
        title="Light deflection by the IAU SOFA library for a finite-distance source, as a change of longitude of date",
        oracle={
            "library": "IAU SOFA (Standards of Fundamental Astronomy), C", "release": f"SOFA-Issue {frame.RELEASE}",
            "distribution_sha256": frame.TARBALL_SHA256, "licence_sha256": frame.LICENCE_SHA256,
            "routines": {"deflection": "iauLd, once per applied deflector, in decreasing distance from the observer",
                         "aberration": "iauAb"},
            "documents": [dict(d) for d in DOCUMENTS],
            "build": build, "driver": driver,
            "acknowledgement": ("Software Routines from the IAU SOFA Collection were used. Copyright © International "
                                "Astronomical Union Standards of Fundamental Astronomy (http://www.iausofa.org)"),
            "geometry": {
                "toolkit": f"SPICE Toolkit via spiceypy {sp.tkvrsn('TOOLKIT')}",
                "kernel": oracle_identity(args.kernel, pin),
                "observer": "the geocentre (399), its barycentric state at the instant, frame J2000 of the toolkit",
                "target": "light-time corrected, the toolkit's converged Newtonian correction (CN), observer 399",
                "deflector_epoch": "t - s*/c, s* = dot(x_A(t) - x_o, -k) held to [0, |x_o - x_s|], k the unit "
                                   "vector source -> observer, c = 299792.458 km/s",
                "own_system_rule": "a deflector is not applied to a target in its own system: Sun {10}; Venus "
                                   "{2, 299}; Jupiter {5}; Saturn {6}; Uranus {7}; Neptune {8}",
                "ray_inside_disc": "0 < s_ca < |x_o - x_s| and b < the deflector's equatorial radius, both at the "
                                   "closest-approach position: recorded, nothing computed",
                "mass": "bm = GM_A / GM_Sun, the system GMs of the constants file",
                "dlim": DLIM, "sun_distance_far_au": S_FAR,
                "constants": {"gm_file_sha256": GM_FILE_SHA256, "radii_file_sha256": RADII_FILE_SHA256,
                              "values": [{"deflector": d["name"], **{k: v for k, v in consts[d["id"]].items()},
                                          **{f"{k}_bits": bits(v) for k, v in consts[d["id"]].items()}}
                                         for d in DEFLECTORS]},
            },
            "frame_of_date": {"file": frame_source, "longitude": "u = NPB s (row-major), e = R1(eps_true) u, "
                                                                  "lambda = atan2(e_y, e_x) in [0, 2 pi)"},
            "host": host_record(),
        },
        request={"instants": {"from": frame_source["sha256"], "count": len(instants)},
                 "targets": [{"target": n, "target_id": t} for t, n in TARGETS],
                 "deflectors": [{"deflector": d["name"], "deflector_id": d["id"]} for d in DEFLECTORS],
                 "regenerate": f"{SCRIPT} --kernel <de440s.bsp> --gm <gm_de440.tpc> --radii <pck00011.tpc> --frame "
                               "<r7 file> --frame-sha256 <hex> --sofa-build <dir> --sofa-source <dir> --out <dir>"},
        classification={s: {"class": "reference_only"} for s in sections},
        row_schema={
            "section": "deflection | ray_inside_disc",
            "p": "the light-time corrected direction observer -> target, unit",
            "natural": "p after iauLd for each applied deflector in `order_applied`",
            "proper_on": "iauAb(natural)", "proper_off": "iauAb(p), the Sun distance as for proper_on",
            "proper_off_far": "iauAb(p) with the Sun distance 1e300 au (⚠ outside the routine's physical domain)",
            "longitude_on": "the longitude of date of proper_on (radian)",
            "delta_longitude_as_called_arcsec": "longitude_on - longitude_off, folded: the routines as called",
            "delta_longitude_potential_in_on_leg_only_arcsec": "longitude_on - longitude_off_far, folded",
            "potential_term_arcsec": "longitude_off - longitude_off_far, folded",
            "deflectors": "per deflector: applied | not_applicable_own_system | ray_inside_disc, with its geometry",
        },
        summary={"rows_by_section": counts, "instants": len(instants), "targets": len(TARGETS)},
        notes=["⛔ Recorder, never explainer.", "⛔ reference_only, with no band and no budget row."],
    )
    written = write_jsonl(args.out / VALUES_PATH, header, rows, declared_sections=sections)
    digest = hashlib.sha256((args.out / VALUES_PATH).read_bytes()).hexdigest()
    print(f"wrote {written} rows -> {args.out / VALUES_PATH} (sha256 {digest[:16]}...); {counts}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (Refusal, frame.Refusal) as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        raise SystemExit(2)
