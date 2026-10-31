"""Per body: whether a returned flag reports, read where the request cannot be answered.

⭐ One body's returned word was measured handing the request back under every condition built
so that the requested source could not answer, while every other body's named the source that
did. So a flag is read as a report only for a body shown reporting, under the word it came back
from — and every refusal here is tested beside a twin that differs from it in one property and
is admitted, so that a test which refuses everything cannot pass.

⚠ Most of this runs on stand-ins for the library's answers. The end-to-end half reads the pinned
data files, and skips — saying so — where they are not present.
"""

from __future__ import annotations

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
sys.path.insert(0, str(ROOT / "src"))

import saakshi.swiss as swiss  # noqa: E402
from saakshi.fixture import bits  # noqa: E402
from saakshi.swiss import (  # noqa: E402
    ECHOES,
    MODES,
    REPORTS,
    UNCOVERED,
    ReadingRefused,
    Session,
    SurveyRefusal,
    UnattestedReport,
    assert_reported,
    body_edges,
    declared_reading_calls,
    fixed_condition_readings,
    one_edge_per_body,
    placement,
    reporting_by_body,
    run_reading_child,
)

_spec = importlib.util.spec_from_file_location("_r3_per_body", ROOT / "generators" / "r3_swiss.py")
assert _spec and _spec.loader
r3 = importlib.util.module_from_spec(_spec)
sys.modules["_r3_per_body"] = r3
_spec.loader.exec_module(r3)

EPHE = ROOT / "cache" / "ephe"
FILE = MODES["swiss_file"]
NODE, SUN, MOON = swe.MEAN_NODE, swe.SUN, swe.MOON
NONUT = swe.FLG_NONUT

#: ⭐ The Moon's coverage edge in the survey this re-emit replaces, as bits — the decimals it
#: carried, written back as the doubles they are. Pinned so the per-body edge is shown to be
#: the same measurement and not merely a plausible one.
COMMITTED_MOON_EDGE = ("414225803ff95413", "414225803ff95414", "4143d189ad337022", "4143d189ad337023")


# ---------------------------------------------------------------------------------------
# The assertion reads the body
# ---------------------------------------------------------------------------------------


def _assert(body, word, attested, returned=None):
    returned = word if returned is None else returned
    return assert_reported(FILE, returned, body=body, word=word, attested=attested, where="t")


def test_a_flag_naming_the_request_is_no_report_for_a_body_that_echoes():
    """⛔ The node's flag names the request whatever answered, so it is never ``reported``."""
    attested = {("calc_ut", NODE, 0): ECHOES, ("calc_ut", SUN, 0): REPORTS}
    with pytest.raises(UnattestedReport) as excinfo:
        _assert(NODE, FILE.flag, attested)
    assert "handing the request back" in str(excinfo.value)
    # ⭐ the twin: the same flag, a body shown reporting
    assert _assert(SUN, FILE.flag, attested)["kind"] == "reported"


def test_a_body_no_fixed_condition_covered_is_refused_not_presumed():
    with pytest.raises(UnattestedReport) as excinfo:
        _assert(SUN, FILE.flag, {("calc_ut", SUN, 0): UNCOVERED})
    assert "not read under every fixed condition" in str(excinfo.value)
    with pytest.raises(UnattestedReport):
        _assert(SUN, FILE.flag, {})
    assert _assert(SUN, FILE.flag, {("calc_ut", SUN, 0): REPORTS})["kind"] == "reported"


def test_the_evidence_is_read_under_the_word_the_flag_came_back_from():
    """⭐ A body shown reporting under one word is not thereby shown reporting under another."""
    attested = {("calc_ut", SUN, NONUT): REPORTS}
    with pytest.raises(UnattestedReport):
        _assert(SUN, FILE.flag | swe.FLG_SPEED, attested)
    assert _assert(SUN, FILE.flag | NONUT, attested)["kind"] == "reported"


def test_a_substitution_is_still_a_substitution_before_the_body_is_read():
    attested = {("calc_ut", SUN, 0): REPORTS}
    with pytest.raises(swiss.EphemerisSubstitution):
        _assert(SUN, FILE.flag, attested, returned=swe.FLG_MOSEPH)


# ---------------------------------------------------------------------------------------
# What a body's readings say
# ---------------------------------------------------------------------------------------


def _reading(condition, requested, returned, *, body=SUN, entry_point="calc_ut"):
    return {"entry_point": entry_point, "body": body, "condition": condition,
            "requested": requested, "returned": returned}


def _reporting(body=SUN, key=0):
    s, j, m = swe.FLG_SWIEPH | key, swe.FLG_JPLEPH | key, swe.FLG_MOSEPH | key
    return [_reading("empty_directory", s, m, body=body), _reading("no_jpl_file", j, s, body=body),
            _reading("outside_coverage", s, m, body=body)]


def test_a_body_reporting_under_every_fixed_condition_reports():
    assert reporting_by_body(_reporting()) == {("calc_ut", SUN, 0): REPORTS}


def test_one_echo_refuses_however_many_reports_stand_beside_it():
    echo = _reading("outside_coverage", swe.FLG_SWIEPH, swe.FLG_SWIEPH)
    assert reporting_by_body(_reporting() + [echo]) == {("calc_ut", SUN, 0): ECHOES}
    assert reporting_by_body(_reporting()) == {("calc_ut", SUN, 0): REPORTS}


@pytest.mark.parametrize("missing", ["empty_directory", "no_jpl_file", "outside_coverage"])
def test_every_fixed_condition_is_needed_and_none_is_enough_alone(missing):
    readings = [r for r in _reporting() if r["condition"] != missing]
    assert reporting_by_body(readings) == {("calc_ut", SUN, 0): UNCOVERED}


def test_a_reading_with_no_edge_to_be_outside_of_counts_for_nothing():
    """⚠ An instant outside no measured edge is under no condition: it neither admits nor refuses."""
    readings = [r if r["condition"] != "outside_coverage" else {**r, "condition": "no_measured_edge"}
                for r in _reporting()]
    assert reporting_by_body(readings) == {("calc_ut", SUN, 0): UNCOVERED}
    echo_with_no_edge = _reading("no_measured_edge", swe.FLG_SWIEPH, swe.FLG_SWIEPH)
    assert reporting_by_body(_reporting() + [echo_with_no_edge]) == {("calc_ut", SUN, 0): REPORTS}


def test_each_key_is_its_own_verdict():
    verdicts = reporting_by_body(_reporting(key=0) + _reporting(key=NONUT)[:2])
    assert verdicts == {("calc_ut", SUN, 0): REPORTS, ("calc_ut", SUN, NONUT): UNCOVERED}


# ---------------------------------------------------------------------------------------
# Edges, per body and per word
# ---------------------------------------------------------------------------------------


def _edge(lo_out, lo_in, up_in, up_out, word=FILE.flag):
    return {f"{end}_bits": bits(v) for end, v in zip(swiss.EDGE_ENDS, (lo_out, lo_in, up_in, up_out))} | {
        end: v for end, v in zip(swiss.EDGE_ENDS, (lo_out, lo_in, up_in, up_out))} | {"located_with_word": word}


def _adjacent(x):
    return float.fromhex(x.hex()), __import__("math").nextafter(x, float("inf"))


def test_an_instant_is_placed_against_the_bits():
    lo = _adjacent(100.0)
    up = _adjacent(200.0)
    edge = _edge(lo[0], lo[1], up[0], up[1])
    assert placement(50.0, edge) == "outside"
    assert placement(lo[0], edge) == "outside"
    assert placement(lo[1], edge) == "inside"
    assert placement(up[1], edge) == "outside"
    assert placement(150.0, edge) == "inside"
    assert placement(150.0, None) == "no_edge"
    wide = _edge(100.0, 101.0, 200.0, 201.0)
    assert placement(100.5, wide) == "undecided"


def test_one_edge_per_body_is_refused_where_its_words_disagree():
    a = _edge(100.0, 100.5, 200.0, 200.5)
    b = _edge(99.0, 99.5, 200.0, 200.5, word=FILE.flag | NONUT)
    with pytest.raises(SurveyRefusal) as excinfo:
        one_edge_per_body({(SUN, 0): a, (SUN, NONUT): b}, keys=(0, NONUT))
    assert "differs between the words" in str(excinfo.value)
    same = {(SUN, 0): a, (SUN, NONUT): {**a, "located_with_word": FILE.flag | NONUT}}
    one = one_edge_per_body(same, keys=(0, NONUT))
    assert one[SUN]["located_with_words"] == [FILE.flag, FILE.flag | NONUT]


def test_a_body_with_no_edge_under_one_word_and_an_edge_under_another_is_refused():
    a = _edge(100.0, 100.5, 200.0, 200.5)
    with pytest.raises(SurveyRefusal):
        one_edge_per_body({(NODE, 0): None, (NODE, NONUT): a}, keys=(0, NONUT))
    assert one_edge_per_body({(NODE, 0): None, (NODE, NONUT): None}, keys=(0, NONUT)) == {NODE: None}


def _stub_library(monkeypatch, answered):
    monkeypatch.setattr(swe, "close", lambda: None)
    monkeypatch.setattr(swe, "set_ephe_path", lambda p: None)
    monkeypatch.setattr(swe, "set_sid_mode", lambda m, a, b: None)
    monkeypatch.setattr(swe, "calc_ut", lambda jd, body, word: (
        (0.0,) * 6, swe.FLG_SWIEPH if answered(jd, body) else swe.FLG_MOSEPH))


def _session(tmp_path):
    return Session(ephe_path=str(tmp_path), sidereal_mode=swe.SIDM_LAHIRI)


def test_a_body_answered_across_the_whole_range_has_no_edge_and_says_so(monkeypatch, tmp_path):
    _stub_library(monkeypatch, lambda jd, body: body == NODE or 100.0 <= jd <= 200.0)
    edges = body_edges(bodies=[NODE, SUN], keys=[0], jd_low=0.0, jd_high=300.0, session=_session(tmp_path))
    assert edges[(NODE, 0)] is None
    # ⭐ the twin: a body the files stop answering has its edge, as adjacent bits
    sun = edges[(SUN, 0)]
    assert abs(int(sun["lower_edge_last_outside_jd_ut_bits"], 16)
               - int(sun["lower_edge_first_inside_jd_ut_bits"], 16)) == 1


def test_an_edge_on_one_side_only_is_refused(monkeypatch, tmp_path):
    _stub_library(monkeypatch, lambda jd, body: jd <= 200.0)
    with pytest.raises(SurveyRefusal) as excinfo:
        body_edges(bodies=[SUN], keys=[0], jd_low=0.0, jd_high=300.0, session=_session(tmp_path))
    assert "on one side" in str(excinfo.value)


def test_a_bracket_that_is_not_two_adjacent_doubles_is_refused(monkeypatch, tmp_path):
    _stub_library(monkeypatch, lambda jd, body: 100.0 <= jd <= 200.0)
    monkeypatch.setattr(swiss, "coverage_edges", lambda *a, **k: _edge(99.0, 100.0, 200.0, 201.0))
    with pytest.raises(SurveyRefusal) as excinfo:
        body_edges(bodies=[SUN], keys=[0], jd_low=0.0, jd_high=300.0, session=_session(tmp_path))
    assert "adjacent" in str(excinfo.value)
    lo, up = _adjacent(100.0), _adjacent(200.0)
    monkeypatch.setattr(swiss, "coverage_edges", lambda *a, **k: _edge(lo[0], lo[1], up[0], up[1]))
    assert body_edges(bodies=[SUN], keys=[0], jd_low=0.0, jd_high=300.0, session=_session(tmp_path))


# ---------------------------------------------------------------------------------------
# The readings: filed under a condition only where they are under it
# ---------------------------------------------------------------------------------------


class _Children:
    """Stands in for the child runner: answers the Moon-like way, every nonce new."""

    def __init__(self, echo_bodies=(), nonce=None):
        self.echo, self.count, self.nonce, self.specs = set(echo_bodies), 0, nonce, []

    def __call__(self, spec, *, work_dir):
        self.count += 1
        self.specs.append(spec)
        word = spec["word"]
        if spec["body"] in self.echo:
            returned = word
        elif spec["path"] == "E" or word & swe.FLG_JPLEPH:
            returned = (word & ~7) | (swe.FLG_MOSEPH if spec["path"] == "E" else swe.FLG_SWIEPH)
        else:
            returned = (word & ~7) | swe.FLG_MOSEPH
        return {"nonce": self.nonce or f"n{self.count}", "returned": returned,
                "values_bits": [bits(1.0), bits(0.0), bits(2.0)]}


def _readings(edges, keys=(0,), run=None, bodies=(SUN,)):
    return fixed_condition_readings(bodies=list(bodies), keys=list(keys), edges=edges, ephe_path="F",
                                    empty_dir="E", work_dir="W", sidereal_mode=1,
                                    run=run or _Children())


EDGE = _edge(*_adjacent(2378496.0), *_adjacent(2597651.0))


def test_an_outside_reading_is_filed_outside_only_where_its_body_has_an_edge():
    rows = _readings({(SUN, 0): EDGE, (NODE, 0): None}, bodies=(SUN, NODE), run=_Children(echo_bodies={NODE}))
    sun = [r["condition"] for r in rows if r["body"] == SUN]
    node = [r["condition"] for r in rows if r["body"] == NODE]
    assert sun == ["empty_directory", "no_jpl_file", "outside_coverage", "outside_coverage",
                   "analytical_request"]
    assert node == ["empty_directory", "no_jpl_file", "no_measured_edge", "no_measured_edge",
                    "analytical_request"]
    verdicts = reporting_by_body(rows)
    assert verdicts[("calc_ut", SUN, 0)] == REPORTS and verdicts[("calc_ut", NODE, 0)] == ECHOES


@pytest.mark.parametrize("edge", [
    _edge(1000.0, 1000.5, 3_000_000.0, 3_000_000.5),   # every chosen instant inside
    _edge(2268919.5, 2268920.5, 2600000.0, 2600000.5),  # the 1500 instant undecided
])
def test_an_outside_instant_that_is_not_outside_is_refused(edge):
    with pytest.raises(SurveyRefusal) as excinfo:
        _readings({(SUN, 0): edge})
    assert "chosen to be outside" in str(excinfo.value)
    assert _readings({(SUN, 0): EDGE})


def test_a_reading_carries_the_raw_words_and_its_freshness():
    row = _readings({(SUN, NONUT): EDGE}, keys=(NONUT,))[0]
    assert row["requested"] == swe.FLG_SWIEPH | NONUT and row["nutation"] == "nonut"
    assert row["returned"] == swe.FLG_MOSEPH | NONUT and row["substitution_reported"] is True
    assert row["call_history"] == "cold_process_per_row"
    assert row["longitude_bits"] == bits(1.0) and row["distance"] == 2.0
    assert row["jd_bits"] == bits(row["jd"])


def test_a_word_with_another_non_ephemeris_bit_is_labelled_by_its_bits_and_never_as_nutation():
    row = _readings({(SUN, swe.FLG_SPEED): EDGE}, keys=(swe.FLG_SPEED,))[0]
    assert "nutation" not in row and row["non_ephemeris_key"] == swe.FLG_SPEED
    sidereal = _Children()
    _readings({(SUN, swe.FLG_SIDEREAL): EDGE}, keys=(swe.FLG_SIDEREAL,), run=sidereal)
    plain = _Children()
    _readings({(SUN, 0): EDGE}, keys=(0,), run=plain)
    assert {s["sidereal_mode"] for s in sidereal.specs} == {1}
    assert {s["sidereal_mode"] for s in plain.specs} == {None}


def test_two_readings_from_one_child_are_refused():
    with pytest.raises(ReadingRefused):
        _readings({(SUN, 0): EDGE}, run=_Children(nonce="same"))


def test_a_survey_row_never_carries_a_word_the_survey_cannot_label():
    """⛔ The O15 limit, held at the writer: a speed word beside the plain one is two words
    under one label, and a reader of words refuses the whole record over it."""
    good = _readings({(SUN, 0): EDGE, (SUN, NONUT): EDGE}, keys=(0, NONUT))
    r3.survey_rows_hold_only_survey_words(good)
    speed = _readings({(SUN, swe.FLG_SPEED): EDGE}, keys=(swe.FLG_SPEED,))
    with pytest.raises(SurveyRefusal):
        r3.survey_rows_hold_only_survey_words(good + speed)
    relabelled = [{**good[0], "nutation": "nonut"}]
    with pytest.raises(SurveyRefusal):
        r3.survey_rows_hold_only_survey_words(relabelled)


@pytest.mark.parametrize("node_verdict", [ECHOES, REPORTS])
def test_a_value_row_of_the_node_is_never_labelled_reported(tmp_path, node_verdict):
    """⛔ The value grid's own rows: the node's flag names the request, and under the measured
    verdict its rows are not written — recorded as unattested instead. ⭐ The twin, with a
    verdict saying it reports, writes them: so the refusal is the evidence's, not the body's."""
    keys = (swe.FLG_SPEED, swe.FLG_SPEED | swe.FLG_SIDEREAL)
    attested = {("calc_ut", body, key): (node_verdict if body == NODE else REPORTS)
                for body, _name in r3.BODIES for key in keys}
    session = Session(ephe_path=str(tmp_path), sidereal_mode=swe.SIDM_LAHIRI)
    sampled = r3.sample_mode(MODES["moshier"], [("e", "in_coverage", 2451545.0)], session,
                             attested=attested)
    position = [r for r in sampled["rows"] if r["section"].startswith("longitude_")]
    node_rows = [r for r in position if r["body_number"] == NODE]
    if node_verdict == ECHOES:
        assert node_rows == [] and len(sampled["unattested"]) == 2
        assert {r["body_number"] for r in position} == {b for b, _ in r3.BODIES} - {NODE}
    else:
        assert len(node_rows) == 2 and sampled["unattested"] == []


def test_a_survey_returning_a_word_none_of_its_readings_requested_is_refused():
    """⛔ Measured on the first re-emit: the default-word readings returned the analytical word,
    which nothing had requested, and a reader of words by their requests refused every body
    over it. ⭐ The twin: the same readings with the analytical request read beside them."""
    rows = _readings({(SUN, 0): EDGE, (SUN, NONUT): EDGE}, keys=(0, NONUT))
    swiss.returned_words_are_requested(rows)
    without = [r for r in rows if r["condition"] != "analytical_request"]
    with pytest.raises(SurveyRefusal) as excinfo:
        swiss.returned_words_are_requested(without)
    assert "no reading here requested" in str(excinfo.value)
    mislabelled = [{**r, "ephemeris_requested": "swiss_file"} if r["condition"] == "analytical_request"
                   else r for r in rows]
    with pytest.raises(SurveyRefusal):
        swiss.returned_words_are_requested(mislabelled)


def test_the_analytical_reading_neither_admits_nor_refuses():
    rows = _readings({(SUN, 0): EDGE})
    analytical = [r for r in rows if r["condition"] == "analytical_request"]
    assert len(analytical) == 1 and analytical[0]["returned"] == analytical[0]["requested"]
    assert reporting_by_body(rows) == reporting_by_body(
        [r for r in rows if r["condition"] != "analytical_request"]) == {("calc_ut", SUN, 0): REPORTS}


def test_the_survey_writer_refuses_such_a_row_before_it_writes_anything(tmp_path):
    speed = _readings({(SUN, swe.FLG_SPEED): EDGE}, keys=(swe.FLG_SPEED,))
    with pytest.raises(SurveyRefusal):
        r3.write_audit_fixture(
            audit_rows=[], edges={}, edges_by_body={}, body_rows=speed, verdicts={},
            demonstration=[], state_rows=[], offset_rows=[], session=None, out_dir=tmp_path,
            script=ROOT / "generators" / "r3_swiss.py", ephe={},
        )
    assert not any(tmp_path.iterdir())
    unreadable = [r for r in _readings({(SUN, 0): EDGE}) if r["condition"] != "analytical_request"]
    with pytest.raises(SurveyRefusal) as excinfo:
        r3.write_audit_fixture(
            audit_rows=[], edges={}, edges_by_body={}, body_rows=unreadable, verdicts={},
            demonstration=[], state_rows=[], offset_rows=[], session=None, out_dir=tmp_path,
            script=ROOT / "generators" / "r3_swiss.py", ephe={},
        )
    assert "no reading here requested" in str(excinfo.value)
    assert not any(tmp_path.iterdir())


@pytest.mark.parametrize("planted", ["empty", "work", None])
def test_a_directory_used_as_empty_is_verified_empty_after_the_readings(monkeypatch, tmp_path, planted):
    """⛔ The empty directory is an attested input (a verified-empty path state), and the
    children's working directory must hold nothing they could have read or left behind."""
    monkeypatch.setattr(r3, "body_edges", lambda **k: {})

    def readings(*, empty_dir, work_dir, **_):
        if planted is not None:
            Path({"empty": empty_dir, "work": work_dir}[planted], "x.se1").write_bytes(b"")
        return []

    monkeypatch.setattr(r3, "fixed_condition_readings", readings)
    session = Session(ephe_path=str(tmp_path), sidereal_mode=swe.SIDM_LAHIRI)
    if planted is None:
        assert r3.measure_per_body(tmp_path, session) == ({}, [])
    else:
        with pytest.raises(SurveyRefusal):
            r3.measure_per_body(tmp_path, session)


# ---------------------------------------------------------------------------------------
# The child: one fresh reading, admitted only if it made exactly its row's calls
# ---------------------------------------------------------------------------------------


def _spec(tmp_path, **over):
    spec = {"path": str(tmp_path), "sidereal_mode": None, "entry_point": "calc_ut",
            "jd_bits": bits(2451545.0), "body": SUN, "word": swe.FLG_SWIEPH | NONUT}
    spec.update(over)
    return spec


def test_a_child_reading_is_one_fresh_call_with_exactly_its_rows_arguments(tmp_path):
    work = tmp_path / "work"
    work.mkdir()
    result = run_reading_child(_spec(tmp_path), work_dir=str(work))
    assert result["fresh_interpreter"] is True
    assert result["calls"] == declared_reading_calls(_spec(tmp_path))
    # an empty directory: the request cannot be answered, and the word says which source did
    assert result["returned"] & 7 == swe.FLG_MOSEPH


@pytest.mark.parametrize("plant", [
    ("values, returned = getattr(swe, spec[\"entry_point\"])(value(spec[\"jd_bits\"]), spec[\"body\"], spec[\"word\"])",
     "values, returned = getattr(swe, spec[\"entry_point\"])(value(spec[\"jd_bits\"]), spec[\"body\"], spec[\"word\"] & 7)"),
    ("wrap(swe, \"\")\n", "wrap(swe, \"\")\nswe.get_tid_acc()\n"),
    ("fresh = \"swisseph\" not in sys.modules\n", "import swisseph\nfresh = \"swisseph\" not in sys.modules\n"),
])
def test_a_child_that_did_other_than_its_row_declares_is_refused(tmp_path, monkeypatch, plant):
    anchor, replacement = plant
    assert swiss._READING_CHILD.count(anchor) == 1
    monkeypatch.setattr(swiss, "_READING_CHILD", swiss._READING_CHILD.replace(anchor, replacement))
    work = tmp_path / "work"
    work.mkdir()
    with pytest.raises(ReadingRefused):
        run_reading_child(_spec(tmp_path), work_dir=str(work))


# ---------------------------------------------------------------------------------------
# End to end, on the pinned data files
# ---------------------------------------------------------------------------------------


def _pinned_files_or_skip():
    if not all((EPHE / name).is_file() for name in swiss.EPHE_PINS):
        pytest.skip("the pinned data files are not in cache/ephe; the end-to-end half cannot run")


@pytest.fixture(scope="module")
def per_body():
    _pinned_files_or_skip()
    swiss.verify_ephe_set(EPHE)
    session = Session(ephe_path=str(EPHE), sidereal_mode=swe.SIDM_LAHIRI)
    edges, readings = r3.measure_per_body(EPHE, session)
    return edges, readings, reporting_by_body(readings)


def test_the_node_echoes_under_every_word_and_every_other_body_reports(per_body):
    _edges, _readings_, verdicts = per_body
    keys = r3.SURVEY_KEYS + r3.VALUE_KEYS
    for body, _name in r3.BODIES:
        expected = ECHOES if body == NODE else REPORTS
        assert {verdicts[("calc_ut", body, key)] for key in keys} == {expected}, body


def test_the_moons_edge_is_the_committed_surveys_measured_again(per_body):
    edges, _readings_, _verdicts = per_body
    one = one_edge_per_body(edges, keys=r3.SURVEY_KEYS)
    assert tuple(one[MOON][f"{end}_bits"] for end in swiss.EDGE_ENDS) == COMMITTED_MOON_EDGE
    assert one[NODE] is None


def test_one_bodys_edge_moves_with_the_speed_bit_so_an_edge_is_written_for_the_survey_words_only(per_body):
    """⚠ Measured: the true node's edge under the speed word is not its edge under the plain
    word. One edge per body is therefore only writable over the words its readings use."""
    edges, _readings_, _verdicts = per_body
    assert one_edge_per_body(edges, keys=r3.SURVEY_KEYS)
    with pytest.raises(SurveyRefusal):
        one_edge_per_body(edges, keys=r3.SURVEY_KEYS + r3.VALUE_KEYS)


def test_the_survey_rows_are_its_two_words_and_each_reading_is_fresh(per_body):
    _edges, readings, _verdicts = per_body
    rows = [r for r in readings if (r["requested"] & ~7) in r3.SURVEY_KEYS]
    r3.survey_rows_hold_only_survey_words(rows)
    assert len(rows) == len(r3.BODIES) * len(r3.SURVEY_KEYS) * len(
        swiss.FIXED_CONDITIONS + swiss.TABLE_READINGS)
    swiss.returned_words_are_requested(rows)
    assert {r["call_history"] for r in readings} == {"cold_process_per_row"}
    json.dumps(rows)
