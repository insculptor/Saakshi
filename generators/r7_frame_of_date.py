"""R7 — the frame of date by the IAU's standard models, computed by the IAU SOFA library from its own distribution.

Four quantities of the IAU 2006/2000A models, at the instants of an earlier geocentric values file, each as the
library returns it, with its bit pattern: the mean obliquity (``iauObl06``), the nutation in longitude and in
obliquity (``iauNut06a``), the bias-precession-nutation matrix (``iauPnm06a``), and the true obliquity, formed as
the mean obliquity plus the nutation in obliquity — one IEEE-754 addition, shown, because the library returns none.

* ⭐ **The time argument.** The instants are TDB. Each is handed to the models as TT, by the library's own route:
  ``tdb_minus_tt = iauDtdb(jd_tdb, 0.0, 0.0, 0.0, 0.0, 0.0)`` (the geocentre), then ``(tt1, tt2) =
  iauTdbtt(jd_tdb, 0.0, tdb_minus_tt)``; the two TT parts are what every model receives, and they are written on
  every row. ⛔ A TDB date is never handed to a TT argument.
* ⭐ **The matrix, declared**: its nine elements in row-major order ``[r00, r01, r02, r10, ..., r22]``, row i and
  column j as the library's own vector-matrix conventions index them; its sense is the library's: ``v_date = R
  v_GCRS``, from the Geocentric Celestial Reference System to the true equator and equinox of date.
* ⭐ **The library is the one built from the pinned distribution.** A driver committed beside this file
  (``native/standards_of_date.c``) is compiled against the given build and run once, as one fresh child; it calls
  the library's routines unmodified and writes back every double they return as bits. The build record (compiler,
  flags, every source by sha256) is carried in the header.
* ⭐ **No budget row.** Every section is ``reference_only``: the file is never compared on its own; whatever uses it
  names it by its digest.
* ``bit-identity`` (a second command, run where the ERFA binding of a pinned version is installed): ERFA's routines
  of the same names at the same inputs, beside this file's values and those of a second build of the library, each
  pair stated identical or not, with the largest difference. ⛔ Nothing is chosen between them.
* ⛔ **Recorder, never explainer.** Nothing here says how the library computes anything. ⛔ No source file of the
  library is read by this program; the compiler reads them.

Usage:
    python generators/r7_frame_of_date.py fixture --sofa-build DIR --sofa-source DIR --sofa-tarball FILE \\
        --licence FILE --terms-page FILE --grid-values FILE --grid-values-sha256 HEX --out DIR
    <a python with pyerfa> generators/r7_frame_of_date.py bit-identity --fixture FILE --fixture-sha256 HEX \\
        --sofa-build DIR --sofa-source DIR --control-build DIR --out DIR
"""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Sequence

HERE = Path(__file__).resolve().parent
sys.dont_write_bytecode = True
if str(HERE.parent / "src") not in sys.path:
    sys.path.insert(0, str(HERE.parent / "src"))

from saakshi.fixture import Header, bits, describe_reserved_names, write_jsonl  # noqa: E402
from saakshi.provenance import generator_for, host_record, today  # noqa: E402

SCRIPT = "generators/r7_frame_of_date.py"
DRIVER_SOURCE = HERE / "native" / "standards_of_date.c"
FIXTURE_PATH = "standards/r7-frame-of-date.jsonl"
IDENTITY_PATH = "standards/r7-erfa-bit-identity.jsonl"

#: ⛔ The distribution, the licence text as it ships, and the publisher's terms page, each as read and pinned.
RELEASE = "2023-10-11"
TARBALL_SHA256 = "d9c10833cae8b4d9361a0ffda31ec361fd1262362025bec4d4e51a880150ace2"
LICENCE_SHA256 = "ffe5460c057a4765e6ca7cf30b50e9f1306e84640e8ec9c05566bbad2c96c994"  # doc/copyr.lis
TERMS_PAGE_SHA256 = "bb6bb7787bf2619cfbeb79bbc648fb0c7a63c0aa629f6a2245f4f61294f1911d"
DRIVER_CFLAGS: tuple[str, ...] = ("-pedantic", "-Wall", "-O")

#: The routine behind each quantity, and the unit it is returned in.
ROUTINES: dict[str, dict[str, str]] = {
    "time_argument": {"routine": "iauDtdb then iauTdbtt",
                      "unit": "seconds (tdb_minus_tt); Julian days, two parts (tt_parts)"},
    "mean_obliquity": {"routine": "iauObl06", "unit": "radian"},
    "nutation": {"routine": "iauNut06a", "unit": "radian, radian (in longitude, in obliquity)"},
    "bias_precession_nutation": {"routine": "iauPnm06a", "unit": "dimensionless, nine elements row-major"},
    "true_obliquity": {"routine": "iauObl06 + iauNut06a's obliquity component, one IEEE-754 addition",
                       "unit": "radian"},
}
SECTIONS = tuple(ROUTINES)

MATRIX = {
    "element_order": "row-major: [r00, r01, r02, r10, r11, r12, r20, r21, r22], r_ij = row i, column j",
    "sense": "v_date = R v_GCRS: from the Geocentric Celestial Reference System to the true equator and equinox of "
             "date (the library's own statement of the routine's matrix)",
    "where_stated": [
        {"document": "SOFA Tools for Earth Attitude (cookbook, C)", "file": "doc/sofa_pn_c.pdf",
         "page": "printed p. 136", "words": "The matrix operates in the sense v_date = BPN v_GCRS , where the "
                                            "p-vector v_date is with respect to the true equatorial triad of date "
                                            "date1+date2 and the p-vector v_GCRS is with respect to the Geocentric "
                                            "Celestial Reference System (IAU, 2000)."},
        {"document": "SOFA Vector/Matrix Library (C)", "file": "doc/sofa_vm_c.pdf", "page": "printed pp. 14-15",
         "words": "in memory, successive triples are columns in Fortran and rows in C"},
    ],
}


class Refusal(Exception):
    """A condition under which nothing may be written."""


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def value_of(text: str) -> float:
    return struct.unpack(">d", bytes.fromhex(text))[0]


# ======================================================================================
# The instants, and the library
# ======================================================================================


def grid_instants(values_path: Path, expected_sha256: str) -> tuple[list[float], dict[str, Any]]:
    """The distinct TDB Julian dates of a geocentric values file, ascending, read by its digest."""
    data = values_path.read_bytes()
    actual = hashlib.sha256(data).hexdigest()
    if actual != expected_sha256:
        raise Refusal(f"the values file's sha256 is {actual}, not {expected_sha256}")
    seen: dict[str, float] = {}
    lines = data.decode("utf-8").splitlines()
    for number, line in enumerate(lines[1:], start=2):
        row = json.loads(line)
        value, pattern = float(row["jd_tdb"]), row["jd_tdb_bits"]
        if bits(value) != pattern:
            raise Refusal(f"line {number}: jd_tdb and its pattern are different numbers")
        seen[pattern] = value
    instants = sorted(seen.values())
    header = json.loads(lines[0])
    listed = header.get("request", {}).get("instants", {})
    return instants, {"values_file_sha256": actual, "count": len(instants), "set_sha256": listed.get("set_sha256")}


def read_build(build: Path, source: Path) -> dict[str, Any]:
    """The library's build record, ⛔ refused unless it names the pinned distribution, its archive is the one on
    disk, and the headers it was built with are the ones the driver will be compiled against."""
    record = json.loads((build / "build-record.json").read_text(encoding="utf-8"))
    if record.get("tarball_sha256") != TARBALL_SHA256:
        raise Refusal("the build record names another distribution")
    if record.get("archive_sha256") != sha256_file(build / "lib" / "libsofa_c.a"):
        raise Refusal("the library archive on disk is not the one the build record names")
    for name, digest in record["header_sha256"].items():
        if sha256_file(source / name) != digest:
            raise Refusal(f"the header {name} is not the one the library was built with")
    if record.get("validation_last_line") != "t_sofa_c validation successful":
        raise Refusal("the build's own validation did not report success")
    # ⛔ A file name is not a fixture key: both maps of name to digest are carried as lists of {file, sha256}.
    return {**{k: v for k, v in record.items() if k not in ("sources", "header_sha256")},
            "headers": [{"file": f, "sha256": d} for f, d in record["header_sha256"].items()],
            "sources": [{"file": f, "sha256": d} for f, d in record["sources"].items()]}


def build_driver(build: Path, source: Path, work: Path) -> tuple[Path, dict[str, Any]]:
    binary = work / "standards_of_date"
    command = ["cc", *DRIVER_CFLAGS, f"-I{source}", str(DRIVER_SOURCE), str(build / "lib" / "libsofa_c.a"), "-lm",
               "-o", str(binary)]
    done = subprocess.run(command, capture_output=True, text=True, check=False)
    if done.returncode != 0:
        raise Refusal(f"the driver did not build: {done.stderr[-600:]}")
    compiler = subprocess.run(["cc", "--version"], capture_output=True, text=True, check=True).stdout.splitlines()[0]
    return binary, {"source": {"path": "generators/native/standards_of_date.c",
                               "sha256": sha256_file(DRIVER_SOURCE)},
                    "cflags": list(DRIVER_CFLAGS), "compiler": compiler, "binary_sha256": sha256_file(binary)}


FIELDS = ("jd_tdb", "tdb_minus_tt", "tt1", "tt2", "obl06", "dpsi", "deps", "true_obliquity",
          *(f"r{i}{j}" for i in range(3) for j in range(3)))


def run_driver(binary: Path, instants: Sequence[float]) -> list[dict[str, str]]:
    """One fresh child for the whole run; every line held to its instant. Returns the bits by field."""
    done = subprocess.run([str(binary)], input="".join(bits(jd) + "\n" for jd in instants), capture_output=True,
                          text=True, check=False, timeout=600)
    lines = done.stdout.splitlines()
    if done.returncode != 0 or not lines or lines[0] != "V standards_of_date 1":
        raise Refusal(f"the driver stopped (exit {done.returncode}): {(lines[-1] if lines else done.stderr)[:200]}")
    out = []
    for jd, line in zip(instants, lines[1:]):
        parts = line.split()
        if parts[0] != "T" or len(parts) != 1 + len(FIELDS):
            raise Refusal(f"the driver answered {line[:60]!r}")
        row = dict(zip(FIELDS, parts[1:]))
        if row["jd_tdb"] != bits(jd):
            raise Refusal(f"the driver answered for another instant than {jd!r}")
        for name, pattern in row.items():
            if value_of(pattern) != value_of(pattern):  # NaN
                raise Refusal(f"{name} at {jd!r} is not a number")
        out.append(row)
    if len(out) != len(instants):
        raise Refusal(f"{len(out)} answers for {len(instants)} instants")
    return out


# ======================================================================================
# The fixture
# ======================================================================================


def fixture_rows(instants: Sequence[float], answers: Sequence[dict[str, str]]) -> list[dict[str, Any]]:
    rows = []
    for k, (jd, a) in enumerate(zip(instants, answers)):
        base = {"epoch_id": f"e{k:03d}", "jd_tdb": jd, "jd_tdb_bits": a["jd_tdb"],
                "tt_parts": [value_of(a["tt1"]), value_of(a["tt2"])], "tt_parts_bits": [a["tt1"], a["tt2"]]}
        rows.append({"section": "time_argument", **base, "tdb_parts": [jd, 0.0], "tdb_parts_bits": [bits(jd),
                                                                                                    bits(0.0)],
                     "tdb_minus_tt_seconds": value_of(a["tdb_minus_tt"]),
                     "tdb_minus_tt_seconds_bits": a["tdb_minus_tt"]})
        rows.append({"section": "mean_obliquity", **base, "value": value_of(a["obl06"]), "value_bits": a["obl06"]})
        rows.append({"section": "nutation", **base, "value": [value_of(a["dpsi"]), value_of(a["deps"])],
                     "value_bits": [a["dpsi"], a["deps"]]})
        matrix = [a[f"r{i}{j}"] for i in range(3) for j in range(3)]
        rows.append({"section": "bias_precession_nutation", **base, "value": [value_of(m) for m in matrix],
                     "value_bits": matrix})
        total = value_of(a["obl06"]) + value_of(a["deps"])
        if bits(total) != a["true_obliquity"]:
            raise Refusal(f"the driver's sum at {jd!r} is not the sum of its two terms")
        rows.append({"section": "true_obliquity", **base, "value": total, "value_bits": a["true_obliquity"],
                     "formed_as": "mean_obliquity.value + nutation.value[1], one IEEE-754 double addition"})
    return rows


def cmd_fixture(args: argparse.Namespace) -> int:
    generator = generator_for(HERE / Path(SCRIPT).name)
    print(describe_reserved_names())
    if (args.out / FIXTURE_PATH).exists():
        raise Refusal(f"{args.out / FIXTURE_PATH} exists; a record is never overwritten")
    for path, pin, what in ((args.sofa_tarball, TARBALL_SHA256, "the distribution"),
                            (args.licence, LICENCE_SHA256, "the licence text"),
                            (args.terms_page, TERMS_PAGE_SHA256, "the terms page")):
        if sha256_file(path) != pin:
            raise Refusal(f"{what} is not the one read and pinned; read it again first")
    build = read_build(args.sofa_build, args.sofa_source)
    instants, source = grid_instants(args.grid_values, args.grid_values_sha256)
    with tempfile.TemporaryDirectory() as work:
        binary, driver = build_driver(args.sofa_build, args.sofa_source, Path(work))
        answers = run_driver(binary, instants)
    rows = fixture_rows(instants, answers)
    header = Header(
        fixture_kind="numeric_pin",
        reference="R7",
        generator=generator,
        generated=today(),
        title="The frame of date by the IAU 2006/2000A models, as the IAU SOFA library computes it",
        oracle={
            "library": "IAU SOFA (Standards of Fundamental Astronomy), C",
            "release": f"SOFA-Issue {RELEASE}",
            "distribution": {"file": "sofa_c-20231011.tar.gz", "sha256": TARBALL_SHA256,
                             "url": "https://www.iausofa.org/s/sofa_c-20231011tar.gz"},
            "licence": {"text": "doc/copyr.lis of the distribution", "sha256": LICENCE_SHA256,
                        "terms_page": {"url": "https://www.iausofa.org/terms-and-conditions",
                                       "sha256": TERMS_PAGE_SHA256}},
            "routine_per_quantity": [{"section": s, **r} for s, r in ROUTINES.items()],
            "time_argument": ("TT, two-part: (tt1, tt2) = iauTdbtt(jd_tdb, 0.0, iauDtdb(jd_tdb, 0.0, 0.0, 0.0, 0.0, "
                              "0.0)) for each TDB instant jd_tdb; every model receives (tt1, tt2)"),
            "matrix": MATRIX,
            "build": build,
            "driver": driver,
            "acknowledgement": ("Software Routines from the IAU SOFA Collection were used. Copyright © International "
                                "Astronomical Union Standards of Fundamental Astronomy (http://www.iausofa.org)"),
            "host": host_record(),
        },
        request={
            "instants": {"rule": "the distinct TDB instants of the geocentric values file named, by its digest",
                         **source},
            "calls": "one fresh child: the driver, compiled from the committed source against the build named",
            "regenerate": f"{SCRIPT} fixture --sofa-build <dir> --sofa-source <src dir> --sofa-tarball <file> "
                          "--licence <copyr.lis> --terms-page <file> --grid-values <values> --grid-values-sha256 "
                          "<hex> --out <dir>",
        },
        classification={s: {"class": "reference_only"} for s in SECTIONS},
        row_schema={
            "section": " | ".join(SECTIONS),
            "epoch_id": "e<index>, the instant's position in ascending order",
            "jd_tdb": "the instant, TDB Julian date — ⚠ display; `jd_tdb_bits` is the value",
            "tt_parts": "the two-part TT every model received — ⚠ display; `tt_parts_bits` is the value",
            "tdb_parts": "time_argument: the two-part TDB handed to the conversion",
            "tdb_minus_tt_seconds": "time_argument: iauDtdb's return",
            "value": "the routine's return in the section's unit (`oracle.routine_per_quantity`); the matrix as "
                     "`oracle.matrix.element_order` declares",
            "formed_as": "true_obliquity: the one addition that forms it",
        },
        summary={"rows_by_section": {s: len(instants) for s in SECTIONS}, "instants": len(instants)},
        notes=["⛔ Recorder, never explainer.", "⛔ reference_only, with no band and no budget row.",
               "⭐ Every model received TT, converted from the instant's TDB by the library's own two routines."],
    )
    written = write_jsonl(args.out / FIXTURE_PATH, header, rows, declared_sections=list(SECTIONS))
    print(f"wrote {written} rows -> {args.out / FIXTURE_PATH} (sha256 {sha256_file(args.out / FIXTURE_PATH)[:16]}...)")
    return 0


# ======================================================================================
# ERFA beside SOFA
# ======================================================================================

ERFA_PINS = {"pyerfa": "2.0.1.5", "erfa_version": "2.0.1", "sofa_version": "20231011"}


def ulps(a: float, b: float) -> int:
    """The distance between two doubles of one sign in units of the last place (their bit patterns' difference)."""
    ia, ib = (struct.unpack(">q", struct.pack(">d", x))[0] for x in (a, b))
    return abs(ia - ib)


def cmd_bit_identity(args: argparse.Namespace) -> int:
    import importlib.metadata as metadata

    generator = generator_for(HERE / Path(SCRIPT).name)
    if (args.out / IDENTITY_PATH).exists():
        raise Refusal(f"{args.out / IDENTITY_PATH} exists; a record is never overwritten")
    if metadata.version("pyerfa") != ERFA_PINS["pyerfa"]:
        raise Refusal(f"pyerfa {metadata.version('pyerfa')} is not the pin {ERFA_PINS['pyerfa']}")
    import erfa  # ⭐ only after the pin

    if (erfa.version.erfa_version, erfa.version.sofa_version) != (ERFA_PINS["erfa_version"],
                                                                  ERFA_PINS["sofa_version"]):
        raise Refusal("the binding carries another ERFA or SOFA version")
    if sha256_file(args.fixture) != args.fixture_sha256:
        raise Refusal("the fixture is not the one named")
    lines = args.fixture.read_text(encoding="utf-8").splitlines()
    by_section: dict[str, list[dict[str, Any]]] = {}
    for line in lines[1:]:
        row = json.loads(line)
        by_section.setdefault(row["section"], []).append(row)
    times = by_section["time_argument"]
    instants = [value_of(r["jd_tdb_bits"]) for r in times]
    builds = {"primary": read_build(args.sofa_build, args.sofa_source),
              "control": read_build(args.control_build, args.sofa_source)}
    with tempfile.TemporaryDirectory() as work:
        binaries = {}
        for name, path in (("primary", args.sofa_build), ("control", args.control_build)):
            (Path(work) / name).mkdir()
            binaries[name], _ = build_driver(path, args.sofa_source, Path(work) / name)
        answers = {name: run_driver(binary, instants) for name, binary in binaries.items()}
    # ⛔ The primary build's answers must be the fixture's, bit for bit: this run read what the fixture records.
    for row, a in zip(times, answers["primary"]):
        if [a["tt1"], a["tt2"]] != row["tt_parts_bits"]:
            raise Refusal("this run's primary build does not reproduce the fixture")

    def erfa_at(a: dict[str, str]) -> dict[str, str]:
        jd = value_of(a["jd_tdb"])
        dtr = float(erfa.dtdb(jd, 0.0, 0.0, 0.0, 0.0, 0.0))
        tt1, tt2 = (float(x) for x in erfa.tdbtt(jd, 0.0, value_of(a["tdb_minus_tt"])))
        t1, t2 = value_of(a["tt1"]), value_of(a["tt2"])  # ⭐ the models at the SOFA run's own TT, input for input
        eps0 = float(erfa.obl06(t1, t2))
        dpsi, deps = (float(x) for x in erfa.nut06a(t1, t2))
        r = erfa.pnm06a(t1, t2)
        out = {"jd_tdb": a["jd_tdb"], "tdb_minus_tt": bits(dtr), "tt1": bits(tt1), "tt2": bits(tt2),
               "obl06": bits(eps0), "dpsi": bits(dpsi), "deps": bits(deps), "true_obliquity": bits(eps0 + deps)}
        out.update({f"r{i}{j}": bits(float(r[i][j])) for i in range(3) for j in range(3)})
        return out

    candidates = {"erfa": [erfa_at(a) for a in answers["primary"]], "sofa_control_build": answers["control"]}
    rows, summary = [], []
    for name, other in candidates.items():
        for field in FIELDS[1:]:
            differ, worst, worst_at, worst_ulps = 0, 0.0, None, 0
            for a, b in zip(answers["primary"], other):
                if a[field] != b[field]:
                    differ += 1
                    d = abs(value_of(a[field]) - value_of(b[field]))
                    if d > worst:
                        worst, worst_at, worst_ulps = d, a["jd_tdb"], ulps(value_of(a[field]), value_of(b[field]))
            entry = {"finding": "bit_identity", "against": name, "field": field, "compared": len(other),
                     "differing": differ, "identical": differ == 0, "largest_abs_difference": worst,
                     "largest_abs_difference_bits": bits(worst), "largest_at_jd_tdb_bits": worst_at,
                     "largest_in_ulps": worst_ulps}
            rows.append(entry)
            summary.append({k: entry[k] for k in ("against", "field", "differing", "identical")})
    import platform

    header = Header(
        fixture_kind="provenance_record",
        reference="R7",
        generator=generator,
        generated=today(),
        title="ERFA beside the IAU SOFA library, routine by routine, at the same inputs",
        oracle={"fixture": {"path": FIXTURE_PATH, "sha256": args.fixture_sha256},
                "erfa": {**ERFA_PINS, "python": platform.python_version()},
                "builds": builds,
                "inputs": "each routine at the inputs the SOFA run handed it: the TDB instant for iauDtdb/eraDtdb, "
                          "the instant and the SOFA run's TDB-TT for iauTdbtt/eraTdbtt, the SOFA run's two TT parts "
                          "for the three models; the true obliquity is each library's own two terms summed"},
        attests=("whether ERFA's routines of the same names return, at the same inputs, the same bits as the IAU "
                 "SOFA library built from its own distribution — under the build the fixture used and under a "
                 "second build of the same sources with contraction of floating-point operations switched off"),
        authority={"held_by": "this instrument, as the party that ran both libraries",
                   "kind": "direct comparison of returned bit patterns",
                   "scope": "⚠ these versions, these builds and this host only"},
        record_date=today(),
        row_schema={"finding": "bit_identity", "against": "erfa | sofa_control_build", "field": " | ".join(FIELDS[1:])},
        summary={"comparisons": summary},
        notes=["⛔ Recorder, never explainer: where two differ, nothing here says why or which is right."],
    )
    write_jsonl(args.out / IDENTITY_PATH, header, rows)
    print(f"wrote {len(rows)} rows -> {args.out / IDENTITY_PATH}")
    for s in summary:
        print(f"  {s['against']:>20} {s['field']:>16}: {'identical' if s['identical'] else str(s['differing']) + ' differ'}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    f = sub.add_parser("fixture")
    for name in ("--sofa-build", "--sofa-source", "--sofa-tarball", "--licence", "--terms-page", "--grid-values",
                 "--out"):
        f.add_argument(name, required=True, type=Path)
    f.add_argument("--grid-values-sha256", required=True)
    b = sub.add_parser("bit-identity")
    for name in ("--fixture", "--sofa-build", "--sofa-source", "--control-build", "--out"):
        b.add_argument(name, required=True, type=Path)
    b.add_argument("--fixture-sha256", required=True)
    args = parser.parse_args(argv)
    return cmd_fixture(args) if args.command == "fixture" else cmd_bit_identity(args)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Refusal as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        raise SystemExit(2)
