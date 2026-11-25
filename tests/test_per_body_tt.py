"""The per-body survey through the TT entry point: edges located through it, named in TT, placed against as TT.

⭐ A survey is evidence about the entry point it read. The universal-time entry point's survey says nothing, by
itself, about the terrestrial-time one; so the same survey can now be taken through either, and an edge located
through one is never read under the other's field names. The universal-time edge is written exactly as before.
"""

from __future__ import annotations

import math

import pytest
import swisseph as swe

from saakshi import swiss
from saakshi.fixture import bits
from saakshi.swiss import (
    ECHOES,
    EDGE_ENDS,
    REPORTS,
    Session,
    SurveyRefusal,
    body_edges,
    coverage_edges,
    edge_ends,
    measure_reporting,
    one_edge_per_body,
    placement,
)

from test_per_body import EPHE, _pinned_files_or_skip

SUN, MOON, NODE, TRUE_NODE = swe.SUN, swe.MOON, swe.MEAN_NODE, swe.TRUE_NODE


def test_each_entry_point_names_its_edges_by_its_own_time_argument():
    assert edge_ends("calc_ut") == EDGE_ENDS
    assert edge_ends("calc") == tuple(end.replace("_jd_ut", "_jd_tt") for end in EDGE_ENDS)
    assert all(end.endswith("_jd_tt") for end in edge_ends("calc"))


@pytest.mark.parametrize("entry_point", ["houses_ex", "calc_ut ", "get_ayanamsa_ex_ut"])
def test_an_entry_point_with_no_recorded_time_argument_is_refused(entry_point):
    with pytest.raises(SurveyRefusal, match="no time argument"):
        edge_ends(entry_point)
    with pytest.raises(SurveyRefusal, match="no time argument"):
        measure_reporting(bodies=[SUN], keys=[0], ephe_path=EPHE, sidereal_mode=swe.SIDM_LAHIRI,
                          entry_point=entry_point)


def _stub(monkeypatch, entry_point, answered):
    """The library, answering through ``entry_point`` only: the other position call raises if it is reached."""
    monkeypatch.setattr(swe, "close", lambda: None)
    monkeypatch.setattr(swe, "set_ephe_path", lambda p: None)
    monkeypatch.setattr(swe, "set_sid_mode", lambda m, a, b: None)

    def call(jd, body, word):
        return (0.0,) * 6, swe.FLG_SWIEPH if answered(jd, body) else swe.FLG_MOSEPH

    def wrong(jd, body, word):
        raise AssertionError("the edge was probed through the other entry point")

    other = "calc_ut" if entry_point == "calc" else "calc"
    monkeypatch.setattr(swe, entry_point, call)
    monkeypatch.setattr(swe, other, wrong)


def _session(tmp_path):
    return Session(ephe_path=str(tmp_path), sidereal_mode=swe.SIDM_LAHIRI)


def test_an_edge_located_through_the_tt_entry_point_is_tt_in_every_field(monkeypatch, tmp_path):
    _stub(monkeypatch, "calc", lambda jd, body: 100.0 <= jd <= 200.0)
    edge = coverage_edges(swiss.MODES["swiss_file"], body=SUN, jd_low=0.0, jd_high=300.0,
                          session=_session(tmp_path), entry_point="calc")
    assert edge["entry_point"] == "calc"
    for end in edge_ends("calc"):
        assert edge[f"{end}_bits"] == bits(edge[end])
    assert not any(key.endswith("_jd_ut") or key.endswith("_jd_ut_bits") or key.endswith("_ut") for key in edge)
    assert edge["lower_edge_calendar_tt"].endswith(" TT") and edge["search_range_jd_tt"] == [0.0, 300.0]
    assert abs(int(edge["lower_edge_last_outside_jd_tt_bits"], 16)
               - int(edge["lower_edge_first_inside_jd_tt_bits"], 16)) == 1


def test_the_universal_time_edge_is_written_exactly_as_before(monkeypatch, tmp_path):
    """⭐ Key for key and in order: an earlier emission re-run must not move by a byte."""
    _stub(monkeypatch, "calc_ut", lambda jd, body: 100.0 <= jd <= 200.0)
    edge = coverage_edges(swiss.MODES["swiss_file"], body=SUN, jd_low=0.0, jd_high=300.0,
                          session=_session(tmp_path))
    assert list(edge) == [
        "body", "located_by",
        "lower_edge_last_outside_jd_ut", "lower_edge_last_outside_jd_ut_bits",
        "lower_edge_first_inside_jd_ut", "lower_edge_first_inside_jd_ut_bits",
        "upper_edge_first_inside_jd_ut", "upper_edge_first_inside_jd_ut_bits",
        "upper_edge_last_outside_jd_ut", "upper_edge_last_outside_jd_ut_bits",
        "lower_edge_calendar_ut", "upper_edge_calendar_ut", "search_range_jd_ut", "scope",
    ]
    assert edge["lower_edge_calendar_ut"].endswith("Z")


def test_a_tt_edge_is_placed_against_and_held_one_per_body(monkeypatch, tmp_path):
    _stub(monkeypatch, "calc", lambda jd, body: body == NODE or 100.0 <= jd <= 200.0)
    edges = body_edges(bodies=[SUN, NODE], keys=[0, swe.FLG_SPEED], jd_low=0.0, jd_high=300.0,
                       session=_session(tmp_path), entry_point="calc")
    assert edges[(NODE, 0)] is None
    sun = edges[(SUN, 0)]
    assert placement(50.0, sun) == "outside" and placement(150.0, sun) == "inside"
    assert placement(math.nextafter(200.0, 300.0) + 1.0, sun) == "outside"
    one = one_edge_per_body(edges, keys=[0, swe.FLG_SPEED])
    assert one[NODE] is None and one[SUN]["entry_point"] == "calc"


def test_a_tt_edge_read_under_the_universal_time_names_is_impossible(monkeypatch, tmp_path):
    """⛔ The fields an edge is read through are its own: a reader asking for the other scale's finds nothing."""
    _stub(monkeypatch, "calc", lambda jd, body: 100.0 <= jd <= 200.0)
    edge = coverage_edges(swiss.MODES["swiss_file"], body=SUN, jd_low=0.0, jd_high=300.0,
                          session=_session(tmp_path), entry_point="calc")
    with pytest.raises(KeyError):
        edge[f"{EDGE_ENDS[0]}_bits"]
    assert swiss._ends_of(edge) == edge_ends("calc")


# ---------------------------------------------------------------------------------------
# End to end, through real fresh children, on the pinned files
# ---------------------------------------------------------------------------------------


@pytest.fixture(scope="module")
def through_tt():
    _pinned_files_or_skip()
    swiss.verify_ephe_set(EPHE)
    return measure_reporting(bodies=[SUN, MOON, NODE, TRUE_NODE], keys=[swe.FLG_SPEED], ephe_path=EPHE,
                             sidereal_mode=swe.SIDM_LAHIRI, entry_point="calc")


def test_through_tt_every_body_but_the_mean_node_reports_and_the_node_echoes(through_tt):
    verdicts = through_tt["attested"]
    assert verdicts[("calc", NODE, swe.FLG_SPEED)] == ECHOES
    for body in (SUN, MOON, TRUE_NODE):
        assert verdicts[("calc", body, swe.FLG_SPEED)] == REPORTS, body


def test_through_tt_every_reading_is_a_tt_reading_and_every_edge_is_tt(through_tt):
    evidence = through_tt["evidence"]
    assert evidence["entry_point"] == "calc"
    assert {r["entry_point"] for r in evidence["readings"]} == {"calc"}
    assert {r["call_history"] for r in evidence["readings"]} == {"cold_process_per_row"}
    for row in evidence["edges"]:
        edge = row["edge"]
        if edge is not None:
            assert edge["entry_point"] == "calc" and f"{edge_ends('calc')[0]}_bits" in edge
