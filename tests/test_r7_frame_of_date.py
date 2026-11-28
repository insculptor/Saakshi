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


def test_two_answer_sets_are_compared_field_by_field_and_a_difference_is_located():
    jds = [2451545.0, 2451561.0]
    a = [dict(zip(r7.FIELDS, _answer(jd).split()[1:])) for jd in jds]
    b = [dict(zip(r7.FIELDS, _answer(jd, obl06=0.409 + (5e-17 if k else 0.0)).split()[1:])) for k, jd in enumerate(jds)]
    rows = {r["field"]: r for r in r7.compare(a, b, against="x")}
    assert rows["dpsi"]["identical"] and "largest_in_ulps" not in rows["dpsi"]
    assert rows["obl06"]["differing"] == 1 and rows["obl06"]["largest_at_jd_tdb_bits"] == bits(2451561.0)
    assert rows["obl06"]["largest_in_ulps"] >= 1
    with pytest.raises(r7.Refusal, match="same instants"):
        r7.compare(a, b[::-1], against="x")


# --------------------------------------------------------------------------------------
# The models at a two-part TT handed in
# --------------------------------------------------------------------------------------

GRID = (2396753.5, 2451545.0, 2506351.5)


def _tt_parts(jd: float) -> list[float]:
    return [jd, 1.5e-9 if jd < 2451545.0 else -5.0e-9]


def _tt_file(tmp_path: Path, rows: list[dict] | None = None) -> tuple[Path, str]:
    if rows is None:
        rows = [{"record": "row", "jd_tdb": jd, "jd_tdb_bits": bits(jd), "tt_parts": _tt_parts(jd),
                 "tt_parts_bits": [bits(x) for x in _tt_parts(jd)]} for jd in GRID]
    path = tmp_path / "tt.jsonl"
    path.write_text("".join(json.dumps(x) + "\n" for x in [{"record": "header", "title": "t"}, *rows]))
    return path, hashlib.sha256(path.read_bytes()).hexdigest()


def _grid_values(tmp_path: Path) -> tuple[Path, str]:
    rows = [{"record": "row", "jd_tdb": jd, "jd_tdb_bits": bits(jd)} for jd in GRID for _ in range(2)]
    path = tmp_path / "grid.jsonl"
    path.write_text("".join(json.dumps(x) + "\n" for x in [{"record": "header", "request": {"instants": {
        "set_sha256": "e" * 64}}}, *rows]))
    return path, hashlib.sha256(path.read_bytes()).hexdigest()


def test_the_handed_tt_is_read_by_its_digest_in_the_grids_order(tmp_path):
    path, digest = _tt_file(tmp_path)
    instants = r7.given_tt(path, digest, list(GRID))
    assert [i["jd_tdb"] for i in instants] == list(GRID)
    assert instants[0]["tt_parts_bits"] == [bits(x) for x in _tt_parts(GRID[0])]


def _row(jd, parts=None, patterns=None, **over):
    parts = _tt_parts(jd) if parts is None else parts
    row = {"record": "row", "jd_tdb": jd, "jd_tdb_bits": bits(jd), "tt_parts": parts,
           "tt_parts_bits": [bits(x) for x in parts] if patterns is None else patterns}
    row.update(over)
    return row


@pytest.mark.parametrize("rows, grid, match", [
    ([_row(jd) for jd in GRID[:2]], GRID, "not the grid's"),
    ([_row(jd) for jd in GRID] + [_row(GRID[0])], GRID, "a second row"),
    ([_row(GRID[0], parts=[GRID[0], 0.0]), *(_row(jd) for jd in GRID[1:])], GRID, "the TDB instant itself"),
    ([_row(GRID[0], parts=[GRID[0]]), *(_row(jd) for jd in GRID[1:])], GRID, "not two TT parts"),
    ([_row(GRID[0], patterns=[bits(GRID[0]), bits(2e-9)]), *(_row(jd) for jd in GRID[1:])], GRID, "different numbers"),
    ([_row(GRID[0], jd_tdb_bits=bits(GRID[1])), *(_row(jd) for jd in GRID[1:])], GRID, "different numbers"),
])
def test_a_handed_tt_that_cannot_be_used_as_given_is_refused(tmp_path, rows, grid, match):
    path, digest = _tt_file(tmp_path, rows)
    with pytest.raises(r7.Refusal, match=match):
        r7.given_tt(path, digest, list(grid))


def test_a_handed_tt_file_that_is_not_the_one_named_is_refused(tmp_path):
    path, _ = _tt_file(tmp_path)
    with pytest.raises(r7.Refusal, match="sha256"):
        r7.given_tt(path, "0" * 64, list(GRID))


def _at_tt_answer(t1: str, t2: str, **over) -> str:
    values = {"obl06": 0.409, "dpsi": 3e-5, "deps": -4e-5, **{f"r{i}{j}": float(10 * i + j) for i in range(3)
                                                              for j in range(3)}}
    values["true_obliquity"] = values["obl06"] + values["deps"]
    values.update(over)
    return "T " + " ".join([t1, t2, *(bits(values[f]) for f in r7.AT_TT_FIELDS[2:])])


def _echo_driver(tmp_path: Path, *, version: str = "V standards_at_tt 1", skew: bool = False,
                 short: bool = False) -> Path:
    """A stand-in: answers each TT handed with fixed values (or, with `skew`, for a TT one ulp later; with `short`,
    only the first)."""
    tail = _at_tt_answer("A", "B").split(" ", 3)[3]
    second = '$(printf "%016x" $((0x$b + 1)))' if skew else "$b"
    stop = "; break" if short else ""
    path = tmp_path / "at_tt_driver"
    path.write_text(f"#!/bin/sh\necho '{version}'\nwhile read a b; do echo \"T $a {second} {tail}\"{stop}; done\n"
                    "cat >/dev/null\n")
    path.chmod(path.stat().st_mode | stat.S_IEXEC)
    return path


def test_the_at_tt_driver_is_held_to_its_version_line_the_parts_handed_and_its_count(tmp_path):
    path, digest = _tt_file(tmp_path)
    instants = r7.given_tt(path, digest, list(GRID))
    assert len(r7.run_at_tt_driver(_echo_driver(tmp_path), instants)) == 3
    with pytest.raises(r7.Refusal, match="stopped"):
        r7.run_at_tt_driver(_echo_driver(tmp_path, version="V standards_of_date 1"), instants)
    with pytest.raises(r7.Refusal, match="other TT parts"):
        r7.run_at_tt_driver(_echo_driver(tmp_path, skew=True), instants)
    with pytest.raises(r7.Refusal, match="1 answers for 3"):
        r7.run_at_tt_driver(_echo_driver(tmp_path, short=True), instants)


def test_the_at_tt_rows_are_lists_and_only_the_compared_section_carries_its_unit():
    instant = {"jd_tdb": GRID[1], "jd_tdb_bits": bits(GRID[1]), "tt_parts_bits": [bits(x) for x in _tt_parts(GRID[1])]}
    answer = dict(zip(r7.AT_TT_FIELDS, _at_tt_answer(*instant["tt_parts_bits"]).split()[1:]))
    frame = {r["section"]: r for r in r7.at_tt_rows([instant], [answer], sections=r7.FRAME_SECTIONS)}
    assert [len(frame[s]["value"]) for s in r7.FRAME_SECTIONS] == [1, 2, 9, 1]
    assert frame["bias_precession_nutation"]["value"] == [0.0, 1.0, 2.0, 10.0, 11.0, 12.0, 20.0, 21.0, 22.0]
    assert frame["true_obliquity"]["value_bits"] == [bits(0.409 + -4e-5)] and "unit" not in frame["true_obliquity"]
    assert all(r["tt_parts_bits"] == instant["tt_parts_bits"] for r in frame.values())
    eps = r7.at_tt_rows([instant], [answer], sections=r7.OBLIQUITY_SECTIONS, unit_on="true_obliquity")
    assert [r.get("unit") for r in eps] == [None, None, "radian"]
    bad = dict(answer, true_obliquity=bits(0.409))
    with pytest.raises(r7.Refusal, match="not the sum"):
        r7.at_tt_rows([instant], [bad], sections=r7.FRAME_SECTIONS)


def test_the_at_tt_driver_makes_no_conversion_between_time_scales():
    """⛔ The time argument is the caller's: the second driver calls the three models and nothing else."""
    text = r7.AT_TT_DRIVER_SOURCE.read_text(encoding="utf-8")
    called = set(re.findall(r"\b(iau\w+)\s*\(", text))
    assert called == {"iauObl06", "iauNut06a", "iauPnm06a"}
    defined = re.findall(r"^(?:static\s+)?(?:int|double|void|char|float|long)\s+\**\s*(\w+)\s*\(", text, re.M)
    assert defined and not [name for name in defined if re.match(r"(iau|sofa)", name, re.I)]
    assert "does not itself constitute software provided by and/or endorsed by SOFA" in " ".join(
        text.replace("*", " ").split())
    assert set(r7.AT_TT_ROUTINES) == set(r7.AT_TT_UNITS) == set(r7.FRAME_SECTIONS)
    assert set(r7.OBLIQUITY_SECTIONS) < set(r7.FRAME_SECTIONS)


@pytest.fixture
def at_tt_inputs(monkeypatch, tmp_path):
    """Stand-ins for everything the command reads: pins, a build record, a driver, the two instant files."""
    pins = {}
    for name, constant in (("tarball", "TARBALL_SHA256"), ("licence", "LICENCE_SHA256"),
                           ("terms", "TERMS_PAGE_SHA256")):
        path = tmp_path / f"{name}.bin"
        path.write_bytes(name.encode())
        monkeypatch.setattr(r7, constant, hashlib.sha256(path.read_bytes()).hexdigest())
        pins[name] = path
    build, source = _build(tmp_path)
    monkeypatch.setattr(r7, "generator_for", lambda script: IDENTITY)
    driver = _echo_driver(tmp_path)
    monkeypatch.setattr(r7, "build_at_tt_driver", lambda b, s, w: (driver, {"source": {"path": "p"}}))
    grid, grid_sha = _grid_values(tmp_path)
    tt, tt_sha = _tt_file(tmp_path)

    def argv(**over):
        args = {"--sofa-build": build, "--sofa-source": source, "--sofa-tarball": pins["tarball"],
                "--licence": pins["licence"], "--terms-page": pins["terms"], "--grid-values": grid,
                "--grid-values-sha256": grid_sha, "--instants": tt, "--instants-sha256": tt_sha,
                "--instants-produced-by": "a producer, a function", "--instants-conversion": "a_conversion",
                "--obliquity-budget-row": "a-row", "--obliquity-band": "4.84813681109536e-08",
                "--out": tmp_path / "out", **over}
        return ["at-tt", *(str(x) for kv in args.items() for x in kv)]

    return argv, tt_sha


def _read(path: Path) -> tuple[dict, list[dict]]:
    lines = [json.loads(x) for x in path.read_text().splitlines()]
    return lines[0], lines[1:]


def test_one_run_writes_the_frame_and_the_obliquity_at_the_tt_handed(at_tt_inputs, tmp_path):
    argv, tt_sha = at_tt_inputs
    assert r7.main(argv()) == 0
    frame, frame_rows = _read(tmp_path / "out" / r7.FRAME_AT_TT_PATH)
    eps, eps_rows = _read(tmp_path / "out" / r7.OBLIQUITY_AT_TT_PATH)
    assert "budget_row" not in frame and eps["budget_row"] == "a-row"
    assert frame["classification"] == {s: {"class": "reference_only"} for s in r7.FRAME_SECTIONS}
    assert eps["classification"]["true_obliquity"] == {"class": "tolerance", "band": "4.84813681109536e-08",
                                                       "unit": "radian"}  # ⭐ the band's text, as given
    assert {s: c["class"] for s, c in eps["classification"].items() if s != "true_obliquity"} == {
        "mean_obliquity": "reference_only", "nutation": "reference_only"}
    for header, sections in ((frame, r7.FRAME_SECTIONS), (eps, r7.OBLIQUITY_SECTIONS)):
        oracle = header["oracle"]
        assert oracle["implementation"] == "sofa"
        assert oracle["routines"] == {s: r7.AT_TT_ROUTINES[s] for s in sections}
        assert header["section_units"] == {s: {"value": r7.AT_TT_UNITS[s]} for s in sections}
        assert oracle["time_argument"] == {"scale": "TT", "from": "TDB", "conversion": "a_conversion",
                                           "instants": {"file_sha256": tt_sha,
                                                        "produced_by": "a producer, a function"}}
        assert {oracle["distribution"]["sha256"], oracle["licence"]["sha256"]} == {r7.TARBALL_SHA256,
                                                                                   r7.LICENCE_SHA256}
    assert {k: frame["oracle"]["matrix"][k] for k in ("element_order", "sense")} == r7.MATRIX_TOKENS
    assert "matrix" not in eps["oracle"]
    assert [r["section"] for r in frame_rows[:4]] == list(r7.FRAME_SECTIONS)  # ⛔ no time-argument section
    assert len(frame_rows) == 4 * len(GRID) and len(eps_rows) == 3 * len(GRID)
    for row in frame_rows + eps_rows:
        assert row["tt_parts_bits"] == [bits(x) for x in _tt_parts(row["jd_tdb"])]
    assert {r.get("unit") for r in eps_rows if r["section"] == "true_obliquity"} == {"radian"}
    assert not [r for r in frame_rows if "unit" in r]


@pytest.mark.parametrize("over, match", [
    ({"--obliquity-band": "x"}, "not a number"),
    ({"--obliquity-band": "0"}, "positive finite"),
    ({"--obliquity-band": "-0.5"}, "positive finite"),
    ({"--obliquity-band": "inf"}, "positive finite"),
    ({"--obliquity-band": "nan"}, "positive finite"),
    ({"--obliquity-budget-row": " a-row"}, "empty or padded"),
    ({"--instants-produced-by": ""}, "empty or padded"),
    ({"--instants-conversion": "a "}, "empty or padded"),
])
def test_an_argument_that_cannot_be_recorded_as_given_is_refused(at_tt_inputs, tmp_path, over, match):
    argv, _ = at_tt_inputs
    with pytest.raises(r7.Refusal, match=match):
        r7.main(argv(**over))
    assert not (tmp_path / "out").exists()


def test_an_at_tt_record_is_never_overwritten(at_tt_inputs):
    argv, _ = at_tt_inputs
    r7.main(argv())
    with pytest.raises(r7.Refusal, match="never overwritten"):
        r7.main(argv())


def test_the_real_at_tt_driver_at_the_librarys_own_tt_returns_the_first_drivers_bits(named_build, tmp_path):
    """⭐ Same models, same TT: the second driver handed the first driver's own TT parts answers bit for bit."""
    build, source = named_build
    (tmp_path / "one").mkdir()
    (tmp_path / "two").mkdir()
    first, _ = r7.build_driver(build, source, tmp_path / "one")
    second, _ = r7.build_at_tt_driver(build, source, tmp_path / "two")
    answers = r7.run_driver(first, list(GRID))
    handed = [{"jd_tdb": jd, "jd_tdb_bits": a["jd_tdb"], "tt_parts_bits": [a["tt1"], a["tt2"]]}
              for jd, a in zip(GRID, answers)]
    again = r7.run_at_tt_driver(second, handed)
    for a, b in zip(answers, again):
        assert {f: a[f] for f in r7.AT_TT_FIELDS} == b
