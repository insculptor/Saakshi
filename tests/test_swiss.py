"""The source assertion's own refusals.

⭐ These tests exist because the failure they guard against is invisible in the artifact.
A recorder that asks for one ephemeris, is quietly given another, and writes the answer
down produces a file that is well-formed, plausible, and mislabelled — and a comparison
between two such files reports exact zeros, which reads as agreement and means only that
both sides were the same ephemeris.

⚠ So the refusals are tested directly, with the library's return values supplied rather
than obtained: the point is not what the library does today, it is that a mismatch is
refused however it arises.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest
import swisseph as swe

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from saakshi.kernels import KernelIdentityError  # noqa: E402
from saakshi.swiss import (  # noqa: E402
    ENTRY_POINTS,
    MODES,
    REPORTING,
    SOURCE_MASK,
    EphemerisSubstitution,
    assert_reported,
    assert_window,
    entry_point_records,
    source_name,
    verify_ephe_set,
)

_PATH = Path(__file__).resolve().parents[1] / "generators" / "r3_swiss.py"
_spec = importlib.util.spec_from_file_location("_r3_swiss", _PATH)
assert _spec and _spec.loader
r3 = importlib.util.module_from_spec(_spec)
sys.modules["_r3_swiss"] = r3
_spec.loader.exec_module(r3)

MOSHIER = MODES["moshier"]
FILE = MODES["swiss_file"]


# --------------------------------------------------------------------------------------
# The direct assertion
# --------------------------------------------------------------------------------------


def test_a_matching_source_is_accepted_and_records_how_it_was_established():
    record = assert_reported(FILE, swe.FLG_SWIEPH | swe.FLG_SPEED, where="t")
    assert record["kind"] == "reported"
    assert record["requested"] == "swiss_file"
    assert record["answered"] == "swiss_file"


def test_the_substitution_this_whole_module_exists_for_is_refused():
    """⛔ The measured failure: a data-file request answered analytically, successfully."""
    with pytest.raises(EphemerisSubstitution) as excinfo:
        assert_reported(FILE, swe.FLG_MOSEPH | swe.FLG_SPEED, where="t")
    assert "moshier" in str(excinfo.value)
    assert "WRONG ephemeris" in str(excinfo.value)


def test_the_reverse_substitution_is_refused_too():
    with pytest.raises(EphemerisSubstitution):
        assert_reported(MOSHIER, swe.FLG_SWIEPH | swe.FLG_SPEED, where="t")


@pytest.mark.parametrize(
    "extra",
    [0, swe.FLG_SPEED, swe.FLG_SIDEREAL, swe.FLG_SPEED | swe.FLG_SIDEREAL, swe.FLG_EQUATORIAL],
)
def test_non_source_bits_never_affect_the_verdict(extra):
    """⚠ A returned flag carries more than a source; comparing whole flags would refuse
    every legitimate call, and 'loosen the check' is how a real check gets deleted."""
    assert assert_reported(FILE, swe.FLG_SWIEPH | extra, where="t")["kind"] == "reported"


def test_an_unnamed_source_bit_is_named_as_unnamed_rather_than_guessed():
    assert source_name(swe.FLG_JPLEPH) == "jpl_file"
    assert source_name(0).startswith("unnamed_source_bits_")


def test_no_source_bit_at_all_is_a_substitution_not_a_pass():
    """⛔ Absence of a source bit must never read as 'the requested one, presumably'."""
    with pytest.raises(EphemerisSubstitution):
        assert_reported(FILE, swe.FLG_SPEED, where="t")


# --------------------------------------------------------------------------------------
# The proxy, for entry points that report nothing
# --------------------------------------------------------------------------------------


def _fake_calc(*, answers):
    """A stand-in for the reporting entry point: `answers` maps jd -> returned flag."""

    def calc(jd, planet, flags):
        return (0.0,) * 6, answers[jd]

    return calc


def test_a_proxy_needs_both_ends_and_records_that_it_is_a_proxy():
    record = assert_window(
        FILE,
        body=swe.SUN,
        jd_start=10.0,
        jd_end=11.0,
        where="t",
        calc=_fake_calc(answers={10.0: swe.FLG_SWIEPH, 11.0: swe.FLG_SWIEPH}),
    )
    assert record["kind"] == "proxy_window"
    assert record["proxy_entry_point"] == "calc_ut"
    assert [end["end"] for end in record["ends"]] == ["start", "end"]


@pytest.mark.parametrize("bad_end", [10.0, 11.0])
def test_either_end_outside_the_requested_source_refuses_the_row(bad_end):
    """⭐ Measured, not assumed: across a coverage edge the two ends disagreed while the
    non-reporting call went on returning a source-dependent answer, so one end alone
    describes nothing."""
    answers = {10.0: swe.FLG_SWIEPH, 11.0: swe.FLG_SWIEPH}
    answers[bad_end] = swe.FLG_MOSEPH
    with pytest.raises(EphemerisSubstitution) as excinfo:
        assert_window(
            FILE, body=swe.SUN, jd_start=10.0, jd_end=11.0, where="t",
            calc=_fake_calc(answers=answers),
        )
    assert "no source report from this entry point" in str(excinfo.value)


def test_a_degenerate_window_is_still_a_proxy_and_still_checked():
    with pytest.raises(EphemerisSubstitution):
        assert_window(
            FILE, body=swe.SUN, jd_start=5.0, jd_end=5.0, where="t",
            calc=_fake_calc(answers={5.0: swe.FLG_MOSEPH}),
        )


def test_a_backwards_window_is_a_programming_error_not_a_silent_pass():
    with pytest.raises(ValueError):
        assert_window(FILE, body=swe.SUN, jd_start=11.0, jd_end=10.0, where="t")


# --------------------------------------------------------------------------------------
# The audit table
# --------------------------------------------------------------------------------------


def test_the_audit_records_that_most_entry_points_cannot_be_asked():
    """⚠ The finding that shapes R3: only one of the four reports its source."""
    assert REPORTING == {"calc_ut"}
    silent = [e.name for e in ENTRY_POINTS if not e.reports_source]
    assert "houses_ex" in silent and "rise_trans" in silent
    # ⛔ The echoing one is the dangerous one: it satisfies "assert the returned flag".
    echo = next(e for e in ENTRY_POINTS if e.name == "get_ayanamsa_ex_ut")
    assert echo.accepts_flag and not echo.reports_source


def test_every_audited_entry_point_states_the_assertion_available_for_it():
    for row in entry_point_records():
        expected = "reported" if row["reports_answering_ephemeris"] else "proxy_window"
        assert row["assertion_available"] == expected
        assert row["evidence"]


# --------------------------------------------------------------------------------------
# The data files
# --------------------------------------------------------------------------------------


def test_a_directory_with_no_data_file_is_refused_rather_than_silently_analytical(tmp_path):
    """⛔ An empty directory would leave every data-file request answered by the analytical
    ephemeris, successfully and without a word."""
    with pytest.raises(KernelIdentityError) as excinfo:
        verify_ephe_set(tmp_path)
    assert "would be" in str(excinfo.value)


def test_an_unpinned_data_file_in_the_directory_is_refused(tmp_path):
    """⭐ The library reads the directory, so a file nobody passed can still answer."""
    (tmp_path / "sepl_30.se1").write_bytes(b"not the pinned file")
    with pytest.raises(KernelIdentityError) as excinfo:
        verify_ephe_set(tmp_path)
    assert "unpinned" in str(excinfo.value)


def test_a_pinned_name_carrying_the_wrong_bytes_is_refused(tmp_path):
    """The right name is not the right file."""
    (tmp_path / "sepl_18.se1").write_bytes(b"wrong bytes under a right-looking name")
    with pytest.raises(KernelIdentityError) as excinfo:
        verify_ephe_set(tmp_path)
    assert "sepl_18.se1" in str(excinfo.value)


def test_a_missing_directory_is_refused(tmp_path):
    with pytest.raises(KernelIdentityError):
        verify_ephe_set(tmp_path / "absent")


# --------------------------------------------------------------------------------------
# The comparison's own arithmetic
# --------------------------------------------------------------------------------------


def test_an_angular_delta_never_reports_360_where_the_bodies_agree():
    """⛔ Plain subtraction across the wrap puts the largest number in the file on the pair
    that agrees best."""
    delta = r3._component_delta("longitude_tropical", 0, 359.9999, 0.0001)
    assert delta == pytest.approx(0.0002, abs=1e-9)


def test_only_the_angular_components_of_a_section_wrap():
    """⚠ A speed is not an angle; wrapping it would hide a real disagreement."""
    assert r3._component_delta("longitude_tropical", 3, 359.9999, 0.0001) > 359.0


def test_every_component_of_an_all_angular_section_wraps():
    assert r3._component_delta("house_cusps", 7, 359.9999, 0.0001) == pytest.approx(
        0.0002, abs=1e-9
    )


def test_a_non_angular_section_never_wraps():
    """Julian days are not angles; a rise/set difference of 360 days is 360 days."""
    assert r3._component_delta("rise_set", 0, 2451545.0, 2451905.0) == pytest.approx(360.0)


def test_every_section_declares_whether_it_wraps():
    """⭐ No default. A section added without an entry must fail here rather than be
    silently treated as non-angular."""
    assert set(r3.ANGULAR) == set(r3.SECTIONS)
    for section, spec in r3.ANGULAR.items():
        assert spec == "all" or isinstance(spec, frozenset), section


# --------------------------------------------------------------------------------------
# The comparison excludes what it could not attribute
# --------------------------------------------------------------------------------------


def test_a_row_missing_from_one_source_is_excluded_from_the_comparison():
    """⭐ The exclusion IS the mechanism: an unattributed row never becomes a value, so it
    cannot contribute an exact zero that would read as agreement."""
    left = {
        "by_key": {
            "a": ("longitude_tropical", [10.0]),
            "b": ("longitude_tropical", [20.0]),
        }
    }
    right = {"by_key": {"a": ("longitude_tropical", [10.5])}}
    result = r3.compare_modes(left, right)
    assert result["rows_compared"] == 1
    assert result["per_section"]["longitude_tropical"]["compared"] == 1
    assert result["per_section"]["longitude_tropical"]["identical"] == 0
    assert result["rows_only_in_one_source"]["moshier_only"] == 1


def test_identical_rows_are_counted_as_identical_not_as_absent():
    left = {"by_key": {"a": ("ayanamsha", [23.85])}}
    right = {"by_key": {"a": ("ayanamsha", [23.85])}}
    result = r3.compare_modes(left, right)
    entry = result["per_section"]["ayanamsha"]
    assert entry["compared"] == 1 and entry["identical"] == 1
    assert entry["max_abs_delta"] == 0.0


# --------------------------------------------------------------------------------------
# The grid follows the measured edges
# --------------------------------------------------------------------------------------


def test_the_grid_straddles_whatever_edges_it_is_given():
    """⭐ The grid is a function of the measured coverage, so a different data-file set
    still produces a grid that tests its own boundary."""
    edges = {
        "lower_edge_first_inside_jd_ut": 2378496.5,
        "lower_edge_last_outside_jd_ut": 2378496.4999,
        "upper_edge_first_inside_jd_ut": 2597641.5,
        "upper_edge_last_outside_jd_ut": 2597641.5001,
    }
    epochs = r3.build_epochs(edges)
    strata = {stratum for _, stratum, _ in epochs}
    assert {"in_coverage", "outside_coverage", "coverage_edge"} <= strata
    inside = [jd for _, stratum, jd in epochs if stratum == "in_coverage"]
    assert all(2378496.5 < jd < 2597641.5 for jd in inside)
    outside = [jd for _, stratum, jd in epochs if stratum == "outside_coverage"]
    assert any(jd < 2378496.5 for jd in outside)
    assert any(jd > 2597641.5 for jd in outside)
    assert len({eid for eid, _, _ in epochs}) == len(epochs)


def test_the_source_mask_covers_exactly_the_three_source_bits():
    assert SOURCE_MASK == swe.FLG_JPLEPH | swe.FLG_SWIEPH | swe.FLG_MOSEPH
    assert SOURCE_MASK & swe.FLG_SPEED == 0
    assert SOURCE_MASK & swe.FLG_SIDEREAL == 0
