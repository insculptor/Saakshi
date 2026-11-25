"""The frame of date from the IAU's own library: the build it must be, the driver's answers, the rows written.

⭐ The refusals run anywhere, against a stand-in driver and a stand-in build. The end-to-end half runs only where a
build of the pinned distribution is named by ``R7_SOFA_BUILD`` and ``R7_SOFA_SOURCE`` (it is never in this tree).
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import re
import stat
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
_SPEC = importlib.util.spec_from_file_location("r7_frame_of_date", ROOT / "generators" / "r7_frame_of_date.py")
r7 = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = r7
_SPEC.loader.exec_module(r7)

from saakshi.fixture import Generator, bits  # noqa: E402

IDENTITY = Generator(repo="github.com/insculptor/Saakshi", script=r7.SCRIPT, commit="0" * 40)


def _answer(jd: float, **over) -> str:
    values = {"jd_tdb": jd, "tdb_minus_tt": -0.0006, "tt1": jd, "tt2": 7e-9, "obl06": 0.409, "dpsi": 3e-5,
              "deps": -4e-5, **{f"r{i}{j}": float(i == j) for i in range(3) for j in range(3)}}
    values["true_obliquity"] = values["obl06"] + values["deps"]
    values.update(over)
    return "T " + " ".join(bits(values[f]) for f in r7.FIELDS)


def _fake_driver(tmp_path: Path, lines: list[str]) -> Path:
    path = tmp_path / "driver"
    path.write_text("#!/bin/sh\ncat >/dev/null\n" + "".join(f"echo '{line}'\n" for line in lines))
    path.chmod(path.stat().st_mode | stat.S_IEXEC)
    return path


def test_the_driver_is_held_to_its_version_line_its_instants_and_its_count(tmp_path):
    jds = [2451545.0, 2451561.0]
    good = ["V standards_of_date 1", *(_answer(jd) for jd in jds)]
    assert len(r7.run_driver(_fake_driver(tmp_path, good), jds)) == 2
    for lines, match in ((["V other 1", *good[1:]], "stopped"), ([good[0], good[2], good[1]], "another instant"),
                         (good[:2], "answers for")):
        with pytest.raises(r7.Refusal, match=match):
            r7.run_driver(_fake_driver(tmp_path, lines), jds)


def test_the_true_obliquity_is_the_one_addition_of_the_two_terms_or_nothing_is_written():
    jd = 2451545.0
    answer = dict(zip(r7.FIELDS, _answer(jd).split()[1:]))
    rows = r7.fixture_rows([jd], [answer])
    assert [r["section"] for r in rows] == list(r7.SECTIONS)
    true = rows[-1]
    assert true["value"] == 0.409 + -4e-5 and true["value_bits"] == bits(0.409 + -4e-5)
    assert rows[0]["tt_parts_bits"] == [bits(jd), bits(7e-9)] and rows[0]["tdb_parts_bits"] == [bits(jd), bits(0.0)]
    matrix = rows[3]["value"]
    assert len(matrix) == 9 and matrix[0] == 1.0 and matrix[1] == 0.0  # row-major
    bad = dict(zip(r7.FIELDS, _answer(jd, true_obliquity=0.409).split()[1:]))
    with pytest.raises(r7.Refusal, match="not the sum"):
        r7.fixture_rows([jd], [bad])


def test_the_matrix_is_written_row_major_as_declared():
    """⭐ Element k = 3 i + j is row i, column j: an asymmetric matrix tells the two orders apart."""
    jd = 2451545.0
    values = {f"r{i}{j}": float(10 * i + j) for i in range(3) for j in range(3)}
    answer = dict(zip(r7.FIELDS, _answer(jd, **values).split()[1:]))
    matrix = next(r for r in r7.fixture_rows([jd], [answer]) if r["section"] == "bias_precession_nutation")
    assert matrix["value"] == [0.0, 1.0, 2.0, 10.0, 11.0, 12.0, 20.0, 21.0, 22.0]
    assert "row-major" in r7.MATRIX["element_order"]


def _build(tmp_path: Path, **over) -> tuple[Path, Path]:
    build, source = tmp_path / "build", tmp_path / "src"
    (build / "lib").mkdir(parents=True)
    source.mkdir()
    (build / "lib" / "libsofa_c.a").write_bytes(b"archive")
    for name in ("sofa.h", "sofam.h"):
        (source / name).write_text(name)
    record = {"tarball_sha256": r7.TARBALL_SHA256,
              "archive_sha256": hashlib.sha256(b"archive").hexdigest(),
              "header_sha256": {n: hashlib.sha256(n.encode()).hexdigest() for n in ("sofa.h", "sofam.h")},
              "validation_last_line": "t_sofa_c validation successful", "sources": {"a.c": "0" * 64}, **over}
    (build / "build-record.json").write_text(json.dumps(record))
    return build, source


def test_a_build_of_the_pinned_distribution_is_read_with_its_file_names_as_values(tmp_path):
    """⛔ A file name is not a key: the record the header carries must pass the contract's key rule."""
    from saakshi.fixture import Header, validate_header

    build, source = _build(tmp_path)
    record = r7.read_build(build, source)
    assert record["sources"] == [{"file": "a.c", "sha256": "0" * 64}]
    assert {h["file"] for h in record["headers"]} == {"sofa.h", "sofam.h"}
    validate_header(Header(fixture_kind="numeric_pin", reference="R7", generator=IDENTITY, generated="2026-11-25",
                           oracle={"build": record}, request={"r": 1},
                           classification={"s": {"class": "reference_only"}}), where="t")


@pytest.mark.parametrize("over, match", [
    ({"tarball_sha256": "1" * 64}, "another distribution"),
    ({"archive_sha256": "1" * 64}, "archive on disk"),
    ({"header_sha256": {"sofa.h": "1" * 64}}, "header sofa.h"),
    ({"validation_last_line": "t_sofa_c validation failed"}, "validation"),
])
def test_any_other_build_is_refused(tmp_path, over, match):
    build, source = _build(tmp_path, **over)
    with pytest.raises(r7.Refusal, match=match):
        r7.read_build(build, source)


def test_no_routine_of_the_driver_carries_the_librarys_prefix():
    """⛔ The licence's naming condition: our own routines never take the library's prefix, in any case."""
    text = r7.DRIVER_SOURCE.read_text(encoding="utf-8")
    defined = re.findall(r"^(?:static\s+)?(?:int|double|void|char|float|long)\s+\**\s*(\w+)\s*\(", text, re.M)
    assert defined and "main" in defined
    assert not [name for name in defined if re.match(r"(iau|sofa)", name, re.I)]
    prose = " ".join(text.replace("*", " ").split())
    assert "does not itself constitute software provided by and/or endorsed by SOFA" in prose


# --------------------------------------------------------------------------------------
# End to end, where a build is named
# --------------------------------------------------------------------------------------


@pytest.fixture
def named_build():
    build, source = os.environ.get("R7_SOFA_BUILD"), os.environ.get("R7_SOFA_SOURCE")
    if not (build and source and Path(build, "build-record.json").is_file()):
        pytest.skip("no build of the pinned distribution is named (R7_SOFA_BUILD, R7_SOFA_SOURCE)")
    return Path(build), Path(source)


def test_the_real_driver_answers_every_instant_and_the_rows_hold_together(named_build, tmp_path):
    build, source = named_build
    r7.read_build(build, source)
    binary, driver = r7.build_driver(build, source, tmp_path)
    jds = [2396753.5, 2451545.0, 2506351.5]
    answers = r7.run_driver(binary, jds)
    rows = r7.fixture_rows(jds, answers)
    assert len(rows) == 3 * len(r7.SECTIONS)
    for row in rows:
        if row["section"] == "time_argument":
            assert row["tt_parts_bits"][0] == bits(row["jd_tdb"])  # the first part follows the TDB's
            assert abs(row["tdb_minus_tt_seconds"]) < 0.002
        if row["section"] == "bias_precession_nutation":
            m = row["value"]
            for i in range(3):  # each row a unit vector: the matrix is a rotation, row-major
                assert abs(sum(m[3 * i + j] ** 2 for j in range(3)) - 1.0) < 1e-14
    assert driver["binary_sha256"] == hashlib.sha256(binary.read_bytes()).hexdigest()
