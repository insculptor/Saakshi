"""The per-body longitudes over the cutover grid: the rule reproduced, the time argument shown, the source asserted.

⭐ The rule is held to the three facts the earlier survey's own report states about its grid. The end-to-end half
runs a three-instant grid through real fresh children on the pinned data files, twice, and compares the bytes.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import pytest
swe = pytest.importorskip(
    "swisseph",
    reason="this module calls the ephemeris library; it cannot run where it is not installed",
)

ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
_SPEC = importlib.util.spec_from_file_location("r3_cutover_grid", ROOT / "generators" / "r3_cutover_grid.py")
c = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = c
_SPEC.loader.exec_module(c)

from saakshi import swiss  # noqa: E402
from saakshi.fixture import Generator, bits  # noqa: E402

from test_per_body import EPHE, _pinned_files_or_skip  # noqa: E402

IDENTITY = Generator(repo="github.com/insculptor/Saakshi", script=c.SCRIPT, commit="0" * 40)

#: ⭐ What the earlier survey's own report states about its grid (its `grid` block), and nothing else of it.
SURVEY_GRID = {"n_epochs": 14612, "first": "1849-12-28T00:00:00+00:00", "last": "2150-01-19T14:41:41+00:00"}


def _report(tmp_path, grid_block):
    path = tmp_path / "report.json"
    path.write_text(json.dumps({"grid": {**grid_block, "rule": "as stated"}}), encoding="utf-8")
    return path, hashlib.sha256(path.read_bytes()).hexdigest()


def test_the_rule_reproduces_the_earlier_surveys_count_first_and_last_instant(tmp_path):
    grid = c.cutover_grid()
    path, digest = _report(tmp_path, SURVEY_GRID)
    out = c.reproduce(path, digest, grid)
    assert out["reproduced"] == SURVEY_GRID
    assert grid[1] - grid[0] == dt.timedelta(days=15, seconds=37_991)


@pytest.mark.parametrize("field, value", [("n_epochs", 14611), ("first", "1849-12-28T00:00:01+00:00"),
                                          ("last", "2150-01-19T14:41:40+00:00")])
def test_a_rule_that_does_not_reproduce_the_report_is_a_stop(tmp_path, field, value):
    path, digest = _report(tmp_path, {**SURVEY_GRID, field: value})
    with pytest.raises(c.Refusal, match=f"does not reproduce the survey's {field}"):
        c.reproduce(path, digest, c.cutover_grid())


def test_a_report_of_another_digest_is_refused(tmp_path):
    path, _ = _report(tmp_path, SURVEY_GRID)
    with pytest.raises(c.Refusal, match="sha256"):
        c.reproduce(path, "0" * 64, c.cutover_grid())


def test_the_dense_stratum_is_five_days_and_the_rest_fifteen():
    grid = c.cutover_grid()
    days = [(b.date() - a.date()).days for a, b in zip(grid, grid[1:])]
    starts = [g.replace(hour=0, minute=0, second=0) for g in grid]
    for start, step in zip(starts, days):
        dense = c.DENSE_START <= start < c.DENSE_END
        assert step in ((5, 6, 4) if dense else (15, 16, 14))  # ± a day: the offset may cross midnight


def test_every_switch_combination_once_and_the_default_first():
    words = c.switch_words()
    assert len(words) == 8 and words[0] == ((), swe.FLG_SPEED)
    assert len({w for _n, w in words}) == 8
    assert (("true_position", "no_aberration", "no_deflection"),
            swe.FLG_SPEED | swe.FLG_TRUEPOS | swe.FLG_NOABERR | swe.FLG_NOGDEFL) in words


def test_fifty_probe_instants_both_ends_included():
    indices = c.probe_indices(14612)
    assert len(indices) == 50 and indices[0] == 0 and indices[-1] == 14611


# --------------------------------------------------------------------------------------
# The golden instants and their time argument
# --------------------------------------------------------------------------------------


def _values_file(tmp_path):
    entries = [{"jd_tdb": 2398584.5, "reasons": ["golden_1855"]},
               {"jd_tdb": 2449963.5, "reasons": ["golden_1995_10_24"]},
               {"jd_tdb": 2504636.5, "reasons": ["golden_2145", "dense_lattice"]},
               {"jd_tdb": 2451545.0, "reasons": ["dense_lattice"]}]
    for e in entries:
        e["jd_tdb_bits"] = bits(e["jd_tdb"])
        e["civil_tdb"] = "label"
    path = tmp_path / "values.jsonl"
    path.write_text(json.dumps({"record": "header", "request": {"instants": {"values": entries}}}) + "\n")
    return path, hashlib.sha256(path.read_bytes()).hexdigest()


def _tt_file(tmp_path, jds, *, skip=None):
    rows = [{"record": "header", "title": "time arguments", "oracle": {"time_argument": "a stated routine"}}]
    for jd in jds:
        if jd == skip:
            continue
        rows.append({"record": "row", "section": "time_argument", "jd_tdb_bits": bits(jd),
                     "tt_parts_bits": [bits(jd), bits(-1.0e-8)]})
    path = tmp_path / "tt.jsonl"
    path.write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    return path, hashlib.sha256(path.read_bytes()).hexdigest()


def test_the_goldens_are_read_at_the_sum_of_the_two_recorded_parts(tmp_path):
    vpath, vsha = _values_file(tmp_path)
    goldens = c.golden_instants(vpath, vsha)
    assert [g["golden"] for g in goldens] == ["golden_1855", "golden_1995_10_24", "golden_2145"]
    tpath, tsha = _tt_file(tmp_path, [g["jd_tdb"] for g in goldens])
    out, source = c.golden_time_arguments(goldens, tpath, tsha)
    for g in out:
        assert g["jd_tt"] == g["jd_tdb"] + (-1.0e-8) and g["jd_tt_bits"] == bits(g["jd_tt"])
    assert source["sha256"] == tsha and "one IEEE-754 double addition" in source["rule"]


def test_a_golden_with_no_time_argument_is_refused(tmp_path):
    vpath, vsha = _values_file(tmp_path)
    goldens = c.golden_instants(vpath, vsha)
    tpath, tsha = _tt_file(tmp_path, [g["jd_tdb"] for g in goldens], skip=goldens[1]["jd_tdb"])
    with pytest.raises(c.Refusal, match="no row"):
        c.golden_time_arguments(goldens, tpath, tsha)


# --------------------------------------------------------------------------------------
# The source of every row
# --------------------------------------------------------------------------------------

FILE = c.CONFIGURATIONS["swiss_file"]
ATTESTED = {("calc", swe.SUN, swe.FLG_SPEED): swiss.REPORTS, ("calc", swe.MEAN_NODE, swe.FLG_SPEED): swiss.ECHOES,
            ("calc", swe.MOON, swe.FLG_SPEED): swiss.UNCOVERED}
WORD = swe.FLG_SWIEPH | swe.FLG_SPEED


def test_a_reporting_body_answered_by_its_request_is_reported():
    a = c.assertion_for(FILE, body=swe.SUN, word=WORD, returned=WORD, attested=ATTESTED, where="w")
    assert a["kind"] == "reported" and a["returned_flag"] == WORD


def test_a_body_whose_word_echoes_is_none_never_reported():
    a = c.assertion_for(FILE, body=swe.MEAN_NODE, word=WORD, returned=WORD, attested=ATTESTED, where="w")
    assert a["kind"] == "none" and a["reason"] == "returned_word_echoes"


def test_a_substitution_is_refused_whatever_the_body():
    for body in (swe.SUN, swe.MEAN_NODE):
        with pytest.raises(swiss.EphemerisSubstitution):
            c.assertion_for(FILE, body=body, word=WORD, returned=swe.FLG_MOSEPH | swe.FLG_SPEED,
                            attested=ATTESTED, where="w")


def test_a_body_with_no_verdict_or_an_uncovered_one_is_refused():
    with pytest.raises(swiss.UnattestedReport):
        c.assertion_for(FILE, body=swe.MOON, word=WORD, returned=WORD, attested=ATTESTED, where="w")
    with pytest.raises(swiss.UnattestedReport):
        c.assertion_for(FILE, body=swe.MARS, word=WORD, returned=WORD, attested=ATTESTED, where="w")


def _result(returned):
    return {"returned": returned, "values_bits": [bits(float(k)) for k in range(6)], "nonce": "x"}


def test_a_refused_reading_is_recorded_and_never_a_row_and_many_stop_the_run():
    points = [{"epoch_id": f"c{i}", "stratum": "s", "body_name": "sun"} for i in range(200)]
    specs = [{"body": swe.SUN, "word": WORD, "jd_bits": bits(2451545.0 + i)} for i in range(200)]
    results = [_result(WORD)] * 199 + [_result(swe.FLG_MOSEPH | swe.FLG_SPEED)]
    rows, refused = c.longitude_rows("swiss_file", FILE, points, results, specs, ATTESTED)
    assert len(rows) == 199 and len(refused) == 1 and refused[0]["error"] == "EphemerisSubstitution"
    results = [_result(WORD)] * 197 + [_result(swe.FLG_MOSEPH | swe.FLG_SPEED)] * 3
    with pytest.raises(c.Refusal, match="systematic"):
        c.longitude_rows("swiss_file", FILE, points, results, specs, ATTESTED)


def test_a_switched_reading_carries_its_difference_from_the_default_folded():
    base = {"section": "s", "epoch_id": "c0", "body": "sun", "switches": [], "values": [359.9, 0.0, 1.0, 1.0, 0.0, 0.0]}
    other = {"section": "s", "epoch_id": "c0", "body": "sun", "switches": ["no_aberration"],
             "values": [0.1, 0.0, 1.0, 1.0, 0.0, 0.0]}
    c.with_differences([base, other])
    assert abs(other["difference_from_default"][0] - 0.2) < 1e-9
    assert other["difference_from_default_bits"][0] == bits(other["difference_from_default"][0])


# --------------------------------------------------------------------------------------
# Through real children
# --------------------------------------------------------------------------------------


def test_a_conversion_is_one_fresh_call_with_exactly_its_arguments(tmp_path):
    _pinned_files_or_skip()
    spec = c.conversion_spec(dt.datetime(1992, 11, 11, 1, 10, 0, tzinfo=dt.timezone.utc), str(EPHE.resolve()))
    result = c.run_conversion_child(spec, work_dir=str(tmp_path))
    et, ut = (swiss.value_of_bits(p) for p in result["returned_bits"])
    assert 0.0 < (et - ut) * 86400.0 < 120.0  # two Julian days, TT after UT, by seconds
    assert result["calls"] == c.declared_conversion_calls(spec)


def test_a_conversion_child_that_makes_another_call_is_refused(tmp_path, monkeypatch):
    _pinned_files_or_skip()
    planted = c._CONVERSION_CHILD.replace("swe.set_ephe_path(spec[\"path\"])",
                                          "swe.set_ephe_path(spec[\"path\"])\nswe.set_sid_mode(1, 0.0, 0.0)")
    assert planted != c._CONVERSION_CHILD
    monkeypatch.setattr(c, "_CONVERSION_CHILD", planted)
    spec = c.conversion_spec(dt.datetime(1992, 11, 11, 1, 10, 0, tzinfo=dt.timezone.utc), str(EPHE.resolve()))
    with pytest.raises(c.Refusal, match="calls were"):
        c.run_conversion_child(spec, work_dir=str(tmp_path))


@pytest.fixture
def tiny(monkeypatch, tmp_path):
    _pinned_files_or_skip()
    grid = [dt.datetime(1950, 1, 1, 0, 0, 0, tzinfo=dt.timezone.utc),
            dt.datetime(1995, 10, 24, 4, 32, 29, tzinfo=dt.timezone.utc),
            dt.datetime(2049, 6, 30, 12, 0, 0, tzinfo=dt.timezone.utc)]
    monkeypatch.setattr(c, "cutover_grid", lambda: grid)
    monkeypatch.setattr(c, "probe_indices", lambda n: [1])
    monkeypatch.setattr(c, "generator_for", lambda script: IDENTITY)
    report, rsha = _report(tmp_path, {"n_epochs": 3, "first": grid[0].isoformat(), "last": grid[-1].isoformat()})
    vpath, vsha = _values_file(tmp_path)
    goldens = c.golden_instants(vpath, vsha)
    tpath, tsha = _tt_file(tmp_path, [g["jd_tdb"] for g in goldens])
    empty = tmp_path / "empty"
    empty.mkdir()
    args = ["--ephe-path", str(EPHE), "--empty-dir", str(empty), "--survey-report", str(report),
            "--survey-report-sha256", rsha, "--grid-values", str(vpath), "--grid-values-sha256", vsha,
            "--tt-from", str(tpath), "--tt-from-sha256", tsha, "--budget-row", "placeholder-row", "--workers", "4"]
    return args, tmp_path


def _lines(path):
    return [json.loads(line) for line in path.read_text().splitlines()]


def test_a_tiny_grid_through_real_children_twice_byte_identical(tiny):
    args, tmp_path = tiny
    c.main([*args, "--out", str(tmp_path / "one")])
    c.main([*args, "--out", str(tmp_path / "two")])
    one, two = (tmp_path / d / c.VALUES_PATH for d in ("one", "two"))
    assert one.read_bytes() == two.read_bytes()
    lines = _lines(one)
    header, rows = lines[0], lines[1:]
    counts = header["summary"]["rows_by_section"]
    bodies = len(c.BODIES)
    assert counts["time_conversion"] == 3 and counts["golden_time_argument"] == 3
    assert counts["swiss_file"] == counts["moshier_files_absent"] == 6 * bodies
    assert counts["flag_semantics_swiss_file"] == counts["flag_semantics_moshier_files_absent"] == 8 * bodies
    assert counts["control_moshier_files_present"] == bodies
    assert header["summary"]["refused"]["count"] == 0
    assert set(header["classification"]) == set(counts)
    assert all(v == {"class": "reference_only"} for v in header["classification"].values())
    for row in rows:
        if "source_assertion" in row:
            kind = row["source_assertion"]["kind"]
            assert kind == ("none" if row["body"] == "mean_node" else "reported"), row["body"]
            assert row["returned_word"] & 7 == row["requested_word"] & 7
    conv = [r for r in rows if r["section"] == "time_conversion"]
    # ⭐ The TT handed on is the data-file conversion's, never the control's.
    assert all(r["jd_tt_passed_bits"] == r["utc_to_jd_data_files_bits"][0] for r in conv)
    by_id = {r["epoch_id"]: r for r in conv}
    for row in rows:
        if row["section"] == "swiss_file" and row["epoch_id"] in by_id:
            assert row["jd_tt_bits"] == by_id[row["epoch_id"]]["jd_tt_passed_bits"]
    survey = _lines(tmp_path / "one" / c.SURVEY_PATH)
    assert survey[0]["oracle"]["values_file"]["sha256"] == hashlib.sha256(one.read_bytes()).hexdigest()
    assert {r["entry_point"] for r in survey[1:] if r["finding"] == "returned_flag_by_body"} == {"calc"}


def test_a_record_is_never_overwritten(tiny):
    args, tmp_path = tiny
    out = tmp_path / "one"
    (out / "swiss").mkdir(parents=True)
    (out / c.VALUES_PATH).write_text("")
    with pytest.raises(c.Refusal, match="never overwritten"):
        c.main([*args, "--out", str(out)])
