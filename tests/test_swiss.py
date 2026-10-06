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
from dataclasses import replace
from pathlib import Path

import pytest

#: ⛔ Skips the whole module where the ephemeris library is absent, at import time, because
#: the parametrised cases below evaluate its constants during **collection** — a guard
#: applied any later would already have failed.
#:
#: ⚠ A skipped module is a hole in the evidence, so `conftest.py` announces the reduction in
#: the report header and the summary, and refuses to run at all where the caller declared a
#: different environment. The skip is the correct behaviour; going quiet about it is not.
swe = pytest.importorskip(
    "swisseph",
    reason="this module calls the ephemeris library; it cannot run where it is not installed",
)

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import saakshi.swiss as swiss_module  # noqa: E402
from saakshi.fixture import FixtureContractError, _scan_keys, bits  # noqa: E402
from saakshi.kernels import KernelIdentityError  # noqa: E402
from saakshi.swiss import (  # noqa: E402
    ASSERTIONS,
    ENTRY_POINTS,
    MODES,
    OFFSET_READ_BACK_STATE,
    REFUSES_ATTRIBUTION,
    REPORTING,
    REQUESTS,
    SOURCE_MASK,
    TIDAL_BY_SOURCE,
    TIDAL_CONSTANTS,
    EntryPointDeclarationError,
    EphemerisSubstitution,
    assert_library_state_returned,
    Session,
    SurveyRefusal,
    _call_whole_return,
    _check_declaration,
    assert_reported,
    assert_window,
    coverage_edges,
    entry_point_records,
    measured_entry_point_records,
    offset_attribution,
    returns_ephemeris_flag,
    returns_read_blind,
    source_bits_in_return,
    source_name,
    sources_named_by_constant,
    state_mediation,
    state_mediation_measured,
    tidal_constant_names,
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


def test_the_audit_reaches_the_two_time_offset_entry_points():
    """⛔ The prerequisite this survey was extended for: `deltat` and `deltat_ex` are in it."""
    names = [e.name for e in ENTRY_POINTS]
    assert "deltat_ex" in names and "deltat" in names
    # ⭐ The one entry point in the whole audit that takes no ephemeris argument at all.
    no_flag = [e.name for e in ENTRY_POINTS if not e.accepts_flag]
    assert no_flag == ["deltat"]


def test_the_offset_entry_points_are_refused_a_source_rather_than_given_a_plausible_one():
    """⛔ The impossibility IS the finding. `none` is a refusal, not a weaker proxy."""
    assert REFUSES_ATTRIBUTION == {"deltat"}
    rows = {row["entry_point"]: row for row in entry_point_records()}
    assert rows["deltat"]["assertion_available"] == "none"
    # ⚠ The flagged one keeps its proxy -- and the proxy is caveated as being about a
    #   different quantity, which is the whole reason it does not become a basis.
    assert rows["deltat_ex"]["assertion_available"] == "proxy_window"
    assert "DIFFERENT QUANTITY" in rows["deltat_ex"]["assertion_caveat"]
    assert rows["deltat_ex"]["quantity_returned"] != rows["calc_ut"]["quantity_returned"]


def test_the_rule_the_table_used_to_derive_this_field_from_is_shown_misreporting_it():
    """⛔⛔ A DERIVED FIELD WITH NO EXCEPTIONS HAS NO WAY TO BE WRONG OUT LOUD.

    The audit derived `assertion_available` as *reported if it reports, proxy_window
    otherwise*. That rule is run here over the current table to show what it now says: it
    hands `deltat` a proxy over a request that was never made. ⭐ The old rule is kept in
    the test rather than in the code for exactly the reason the string-matched branch
    sorter was — a rule that is wrong is worth pinning as wrong.
    """
    def old_rule(row: dict) -> str:
        return "reported" if row["reports_answering_ephemeris"] else "proxy_window"

    misreported = [
        row["entry_point"]
        for row in entry_point_records()
        if old_rule(row) != row["assertion_available"]
    ]
    assert misreported == ["deltat"]


def test_every_audited_entry_point_states_the_assertion_available_for_it():
    for row in entry_point_records():
        assert row["assertion_available"] in ASSERTIONS
        assert row["evidence"]
        # ⛔ Every assertion weaker than a report costs the reader something and says so.
        if row["assertion_available"] == "reported":
            assert row["assertion_caveat"] == ""
        else:
            assert row["assertion_caveat"]


#: ⛔⛔⛔ THE BASE ROW IS PART OF THE TEST, AND CHOOSING IT BADLY TESTS ONE BRANCH SIX
#: TIMES. Written first with `deltat` as the base throughout, three of these cases passed
#: with their own branch deleted -- because `deltat` takes no ephemeris flag, which makes
#: the flagless branch a catch-all that fires for every wrong value. A disarming sweep
#: found it; the suite could not, because each case asserted only that *some* refusal came
#: back. ⭐ Each case now names the row that isolates its branch AND the words of the
#: refusal it is owed.
_DECLARATION_CASES = [
    ("houses_ex", {"assertion_available": "hearsay"}, "is not one of"),
    (
        "calc_ut",
        {"assertion_available": "proxy_window", "assertion_caveat": "x"},
        "so the assertion available for it is",
    ),
    ("houses_ex", {"assertion_available": "reported"}, "it returns no report"),
    ("houses_ex", {"assertion_available": "none"}, "so a request exists"),
    ("deltat", {"assertion_available": "proxy_window"}, "no request for a proxy to find"),
    ("houses_ex", {"assertion_caveat": ""}, "reads as free"),
]


@pytest.mark.parametrize("base_name, overrides, owed", _DECLARATION_CASES)
def test_the_declaration_guard_refuses_each_way_it_can_be_lied_to(base_name, overrides, owed):
    """⭐⭐⭐ DISARM THE GUARD YOU JUST WROTE -- and check WHICH guard answered.

    ⛔ A test that accepts any refusal is satisfied by a different guard than the one it
    was written for, and reports full coverage while a branch sits dead.
    """
    base = next(e for e in ENTRY_POINTS if e.name == base_name)
    with pytest.raises(EntryPointDeclarationError) as excinfo:
        _check_declaration(replace(base, **overrides))
    assert owed in str(excinfo.value)


def test_each_declaration_case_is_refused_by_exactly_one_branch():
    """⚠ The property the cases above rely on, asserted rather than assumed: no two of
    them are owed the same words, so none can be standing in for another."""
    owed = [case[2] for case in _DECLARATION_CASES]
    assert len(set(owed)) == len(owed)


def test_the_writing_path_re_checks_the_table_and_not_only_the_import():
    """⛔ Deleting one import-time statement is the cheapest way for this table to start
    lying, so the check the fixture writer goes through is checked too."""
    base = next(e for e in ENTRY_POINTS if e.name == "deltat")
    with pytest.raises(EntryPointDeclarationError):
        entry_point_records([replace(base, assertion_available="proxy_window")])
    # ⚠ And it passes the table that is actually declared, or it would prove nothing.
    assert len(entry_point_records()) == len(ENTRY_POINTS)


def test_a_survey_that_left_the_library_pointed_elsewhere_is_refused():
    """⛔ The offset survey builds a state this repository refuses to record in. Left in
    place it would answer every later call analytically, successfully and silently."""
    ok = dict(
        before_constant=-25.936, before_flag=swe.FLG_SWIEPH,
        after_constant=-25.936, after_flag=swe.FLG_SWIEPH,
    )
    assert assert_library_state_returned(**ok) is None
    with pytest.raises(EphemerisSubstitution) as by_constant:
        assert_library_state_returned(**{**ok, "after_constant": -25.8})
    assert "tidal constant" in str(by_constant.value)
    with pytest.raises(EphemerisSubstitution) as by_flag:
        assert_library_state_returned(**{**ok, "after_flag": swe.FLG_MOSEPH})
    assert "moshier" in str(by_flag.value)


def test_the_declaration_guard_passes_every_row_actually_declared():
    """⚠ A guard that refused everything would pass the six tests above and be useless."""
    for entry in ENTRY_POINTS:
        _check_declaration(entry)


# --------------------------------------------------------------------------------------
# ⛔ The refusal's own instrument: a tidal constant is not an identifier
# --------------------------------------------------------------------------------------


def test_the_tidal_constant_cannot_name_the_ephemeris_and_the_instrument_says_so_both_ways():
    """⭐⭐⭐ THE MEASUREMENT THAT MAKES THE REFUSAL A FINDING RATHER THAN A SHRUG.

    The only channel carrying anything about what an offset was computed from is the tidal
    acceleration in force. Read in the library's own vocabulary it answers three different
    ways, and an instrument that could only ever return the empty list would be measuring
    nothing — so all three are pinned together.
    """
    # ⭐ It CAN name one: the analytical ephemeris's constant is its alone among the three.
    assert sources_named_by_constant(TIDAL_CONSTANTS["TIDAL_MOSEPH"]) == ["moshier"]
    # ⛔ It names TWO for the number the library gives both file-backed sources.
    assert TIDAL_CONSTANTS["TIDAL_SWIEPH"] == TIDAL_CONSTANTS["TIDAL_JPLEPH"]
    assert sources_named_by_constant(TIDAL_CONSTANTS["TIDAL_SWIEPH"]) == [
        "jpl_file",
        "swiss_file",
    ]
    # ⛔ And it names NONE for the constant an actual pinned data file puts in force.
    assert sources_named_by_constant(TIDAL_CONSTANTS["TIDAL_DE441"]) == []
    assert tidal_constant_names(TIDAL_CONSTANTS["TIDAL_DE441"]) == ["TIDAL_DE441"]


def test_the_tidal_table_is_the_librarys_own_and_not_a_copy():
    """⛔ A hand-copied table could be made to say anything; this one is read from swe."""
    assert TIDAL_CONSTANTS["TIDAL_MOSEPH"] == swe.TIDAL_MOSEPH
    assert set(TIDAL_BY_SOURCE) == {"moshier", "swiss_file", "jpl_file"}


# --------------------------------------------------------------------------------------
# ⛔ The control on the READER: a silence is only a finding if the reader can hear
# --------------------------------------------------------------------------------------


def test_the_blind_reader_finds_a_flag_where_one_exists_and_none_where_none_does():
    """⭐⭐⭐ 'No flag came back' and 'this harness does not look at flags' are the same
    observation from the outside, and only one of them is a finding."""
    # A calc_ut-shaped return: values, then a flag carrying the data-file source bit.
    reporting = ((1.0, 2.0, 3.0), swe.FLG_SWIEPH | swe.FLG_SPEED)
    assert source_bits_in_return(reporting)["named_sources_readable"] == ["swiss_file"]
    assert source_bits_in_return(reporting)["carries_a_source"] is True
    # A rise_trans-shaped return: an integer that is a return CODE, not a flag.
    not_a_flag = (0, (2451545.0, 0.0))
    reading = source_bits_in_return(not_a_flag)
    assert reading["integers_in_return"] == [0]
    assert reading["carries_a_source"] is False
    # ⛔ The offset entry points: a bare float. Nothing to read at all.
    assert source_bits_in_return(0.000738755787037037)["integers_in_return"] == []
    # ⚠ A bool is an int in this language and would have masked to a source bit.
    assert source_bits_in_return((True, False))["integers_in_return"] == []


# --------------------------------------------------------------------------------------
# ⛔ The survey refuses a grid that cannot answer the question it was run to answer
# --------------------------------------------------------------------------------------


@pytest.fixture()
def two_empty_regimes(tmp_path):
    """Two sessions over directories with no data file.

    ⚠ The regimes collapse into one here, which is fine: these tests are about the survey's
    refusals, and those are read off the epoch grid rather than off the data files. ⛔ The
    library's global state is put back afterwards so no later test inherits this one's.
    """
    left = Session(ephe_path=str(tmp_path / "a"), sidereal_mode=swe.SIDM_LAHIRI)
    right = Session(ephe_path=str(tmp_path / "b"), sidereal_mode=swe.SIDM_LAHIRI)
    (tmp_path / "a").mkdir()
    (tmp_path / "b").mkdir()
    yield left, right
    swe.close()


def _year(year: int) -> tuple[str, float]:
    return (f"year_{year}", float(swe.julday(year, 1, 1, 0.0)))


def test_a_grid_where_the_flag_changes_nothing_is_refused_rather_than_reported_as_no_effect(
    two_empty_regimes,
):
    """⛔⛔ A FIXTURE SIZED TO THE ANSWER FAILS SILENTLY IN THE DIRECTION THAT LOOKS LIKE
    SUCCESS. At a tabulated instant all three flags return one number, so a survey confined
    to such epochs would report no dependence and would look exactly like one that found
    none."""
    left, right = two_empty_regimes
    with pytest.raises(SurveyRefusal) as excinfo:
        offset_attribution(
            epochs=[_year(2000), _year(2100)], with_files=left, without_files=right
        )
    assert "property under test" in str(excinfo.value)


def test_a_grid_where_the_flag_always_matters_is_refused_too(two_empty_regimes):
    """⚠ The other direction, and it is the one a hurried author would leave out: an
    instrument never observed saying *no* has not been shown able to."""
    left, right = two_empty_regimes
    with pytest.raises(SurveyRefusal) as excinfo:
        offset_attribution(
            epochs=[_year(1900), _year(1901)], with_files=left, without_files=right
        )
    assert "no case in which it reports no dependence" in str(excinfo.value)


def test_the_survey_publishes_a_refusal_for_every_offset_value_it_records(two_empty_regimes):
    """⛔ Not one row of this survey carries a source. Every one carries why it cannot."""
    left, right = two_empty_regimes
    rows = offset_attribution(
        epochs=[_year(1900), _year(2000)], with_files=left, without_files=right
    )
    valued = [r for r in rows if r["row"] in ("per_flag", "unflagged")]
    assert valued
    for row in valued:
        assert row["ephemeris_basis"].startswith("⛔ REFUSED")
    control = next(r for r in rows if r["row"] == "harness_control")
    assert control["reader_can_see_a_report_where_one_exists"] is True
    assert control["reader_is_not_fooled_by_an_integer_that_is_not_a_flag"] is True
    assert control["the_two_offset_entry_points_return_no_integer_at_all"] is True
    verdict = next(r for r in rows if r["row"] == "verdict")
    assert verdict["epochs_where_the_flag_changes_the_answer"] == ["year_1900"]
    assert verdict["epochs_where_it_does_not"] == ["year_2000"]
    # ⭐⭐⭐ BOTH DIRECTIONS, INSIDE THE SURVEY. An instrument that only ever disagreed
    #     would produce this same file and would be measuring nothing.
    per_flag = [r for r in rows if r["row"] == "per_flag"]
    assert any(r["constant_and_reported_source_agree"] for r in per_flag)
    assert any(not r["constant_and_reported_source_agree"] for r in per_flag)
    assert verdict["combinations_where_the_constant_identifies_one_source"] > 0
    assert verdict["combinations_where_it_and_the_position_report_disagree"] > 0


def test_the_survey_refuses_to_return_where_the_library_did_not_come_back(tmp_path):
    """⛔⛔ THE ONE DISARM NOTHING CAUGHT, AND WHAT WAS DONE ABOUT IT.

    Replacing the survey's second state reading with a copy of the first makes its restore
    check tautological. The suite could not see it -- no ephemeris data files here, so the
    two states cannot differ -- and neither could the generator, whose refusal fires only
    on a real divergence. ⭐ So the readings come through a seam, and the seam is driven
    both ways: a run whose state comes back is let through, and one whose state does not is
    refused.
    """
    session = Session(ephe_path=str(tmp_path), sidereal_mode=swe.SIDM_LAHIRI)

    def reader(values):
        pending = list(values)
        return lambda _session: pending.pop(0)

    steady = [(-25.936, swe.FLG_SWIEPH), (-25.936, swe.FLG_SWIEPH)]
    moved = [(-25.936, swe.FLG_SWIEPH), (-25.8, swe.FLG_MOSEPH)]
    try:
        # ⚠ The control first: an unmoved state must NOT be refused, or the test below
        #    would pass against a survey that refuses everything.
        assert r3.offset_survey(session, read_state=reader(steady))
        with pytest.raises(EphemerisSubstitution) as excinfo:
            r3.offset_survey(session, read_state=reader(moved))
    finally:
        swe.close()
    assert "did not come back" in str(excinfo.value)


def test_the_unflagged_entry_point_is_recorded_as_having_chosen_a_flag_anyway(
    two_empty_regimes,
):
    """⭐ A caller who never passed a flag has still chosen one, and the row says which."""
    left, right = two_empty_regimes
    rows = offset_attribution(
        epochs=[_year(1900), _year(2000)], with_files=left, without_files=right
    )
    unflagged = [r for r in rows if r["row"] == "unflagged" and r["epoch_id"] == "year_1900"]
    assert unflagged
    for row in unflagged:
        assert row["accepts_ephemeris_flag"] is False
        # ⛔ It takes no ephemeris argument and its answer is one of the flagged answers.
        assert row["equals_the_flagged_answer_for"]
        assert row["this_epoch_has_the_property_under_test"] is True


# --------------------------------------------------------------------------------------
# ⭐ Three answers a consumer tests mechanically -- each MEASURED, never declared
# --------------------------------------------------------------------------------------


def test_the_tidal_constant_is_written_as_bits_beside_every_offset_reading(two_empty_regimes):
    """⭐ A decimal read through text is not a committed value, so every reading carries the
    pattern; ⛔ and the two prose rows, which read no constant, carry none."""
    left, right = two_empty_regimes
    rows = offset_attribution(
        epochs=[_year(1900), _year(2000)], with_files=left, without_files=right
    )
    readings = [r for r in rows if r["row"] in ("per_flag", "unflagged")]
    assert len(readings) == 16
    for row in readings:
        assert row["tidal_constant_in_force_bits"] == bits(row["tidal_constant_in_force"])
    for row in rows:
        if row["row"] in ("harness_control", "verdict"):
            assert "tidal_constant_in_force_bits" not in row


@pytest.fixture()
def one_empty_session(tmp_path):
    (tmp_path / "e").mkdir()
    yield Session(ephe_path=str(tmp_path / "e"), sidereal_mode=swe.SIDM_LAHIRI)
    swe.close()


def test_every_entry_point_is_read_blind_under_every_request_it_can_take(one_empty_session):
    """⛔ A flag-taking entry point read under one request has been read under one request."""
    readings = returns_read_blind(one_empty_session)
    assert list(readings) == [e.name for e in ENTRY_POINTS]
    for entry in ENTRY_POINTS:
        expected = [r for r, _ in REQUESTS] if entry.accepts_flag else ["no_flag_accepted"]
        assert list(readings[entry.name]) == expected


def test_every_blind_read_is_taken_from_a_reset_state():
    """⛔⛔ THE DISARM THE LIBRARY COULD NOT CATCH. Deleting the reset before each read went
    green: with no data files here, no call order changes any return. ⭐ So the reset is
    driven through the reader's own seam -- every call must see one more reset than the
    call before it, and a reader that skips one is refused by this test, not by luck."""

    class CountingSession:
        resets = 0

        def reset(self):
            self.resets += 1

    session = CountingSession()
    seen: list[int] = []

    def call(name, jd, flag):
        seen.append(session.resets)
        return 0.0

    readings = returns_read_blind(session, call=call)
    calls = sum(len(r) for r in readings.values())
    assert seen == list(range(1, calls + 1))


def test_returning_a_flag_is_measured_and_is_not_the_same_question_as_reporting_one(
    one_empty_session,
):
    """⭐⭐ The echoing entry point RETURNS a flag and does not REPORT one. A key that read
    `reports_answering_ephemeris = false` as *returns no flag* would refuse the very flag a
    consumer must carry for it -- which is why the answer is read off the return."""
    readings = returns_read_blind(one_empty_session)
    measured = {name: returns_ephemeris_flag(name, r) for name, r in readings.items()}
    assert measured == {
        "calc_ut": True,
        "get_ayanamsa_ex_ut": True,
        "houses_ex": False,
        "rise_trans": False,
        "deltat_ex": False,
        "deltat": False,
    }
    reports = {e.name: e.reports_source for e in ENTRY_POINTS}
    assert [n for n in measured if measured[n] and not reports[n]] == ["get_ayanamsa_ex_ut"]


def test_a_flag_under_some_requests_and_not_others_is_refused_not_rounded():
    """⛔ All or nothing. Both clean answers are let through, and the mixture is refused --
    with both sides named, so the refusal says what was seen."""
    flag = {"carries_a_source": True, "integers_in_return": [2], "named_sources_readable": ["swiss_file"]}
    none = {"carries_a_source": False, "integers_in_return": [0], "named_sources_readable": []}
    assert returns_ephemeris_flag("x", {"moshier": flag, "swiss_file": flag}) is True
    assert returns_ephemeris_flag("x", {"moshier": none, "swiss_file": none}) is False
    with pytest.raises(SurveyRefusal) as excinfo:
        returns_ephemeris_flag("x", {"moshier": flag, "swiss_file": none})
    assert "['moshier'] and not under ['swiss_file']" in str(excinfo.value)
    with pytest.raises(SurveyRefusal):
        returns_ephemeris_flag("x", {})


def test_an_entry_point_the_reader_cannot_call_is_refused_not_read_as_silent():
    """⛔ An uncalled entry point would read exactly like one that returned nothing."""
    assert _call_whole_return("deltat", 2451545.0, None) is not None
    with pytest.raises(SurveyRefusal) as excinfo:
        _call_whole_return("no_such_entry_point", 2451545.0, None)
    assert "no way to call" in str(excinfo.value)


def test_the_table_is_checked_against_the_measurement_and_not_copied_into_it(
    one_empty_session, two_empty_regimes
):
    """⛔ A declared reporter whose return carried no flag is a contradiction, refused."""
    left, right = two_empty_regimes
    offsets = offset_attribution(
        epochs=[_year(1900), _year(2000)], with_files=left, without_files=right
    )
    readings = returns_read_blind(one_empty_session)
    assert measured_entry_point_records(readings=readings, offset_rows=offsets)
    silent = {"carries_a_source": False, "integers_in_return": [], "named_sources_readable": []}
    lying = {**readings, "calc_ut": {r: silent for r in readings["calc_ut"]}}
    with pytest.raises(EntryPointDeclarationError) as excinfo:
        measured_entry_point_records(readings=lying, offset_rows=offsets)
    assert "The table and the library disagree" in str(excinfo.value)


def test_membership_is_measured_so_the_same_code_answers_differently_on_other_evidence(
    one_empty_session, two_empty_regimes
):
    """⭐⭐⭐ A MEMBERSHIP KEY THAT CANNOT CHANGE ITS ANSWER WITH THE EVIDENCE IS A DECLARATION.

    The suite holds no data files, so both of its regimes are empty and `deltat` -- which
    takes no flag -- reads one state in both. Its value is never seen to MOVE with the state,
    so clause (b) is not established for it here and no membership is written; `deltat_ex`,
    whose flags put two different constants in force, is established. ⚠ With the pinned data
    files present the generator sees `deltat` move too. ⇒ the row's answer is the run's.
    """
    left, right = two_empty_regimes
    offsets = offset_attribution(
        epochs=[_year(1900), _year(2000)], with_files=left, without_files=right
    )
    rows = {
        r["entry_point"]: r
        for r in measured_entry_point_records(
            readings=returns_read_blind(one_empty_session), offset_rows=offsets
        )
    }
    members = sorted(name for name, row in rows.items() if "state_mediation" in row)
    assert members == ["deltat_ex"]
    assert rows["deltat_ex"]["state_mediation"] == {
        "answering_ephemeris": "none",
        "read_back_state": "tidal_acceleration",
    }
    assert rows["deltat"]["state_mediation_measured"]["b_epochs_where_the_state_moved_the_value"] == []
    assert rows["deltat"]["state_mediation_measured"]["b_value_follows_the_read_back_state"] is False
    # ⚠ (a) alone makes nothing a member: the house cusps return no integer at all and have
    #   no read-back, so (b) and (c) are NOT MEASURED -- null, never false.
    houses = rows["houses_ex"]["state_mediation_measured"]
    assert houses["a_returns_no_flag_and_no_code"] is True
    assert houses["b_value_follows_the_read_back_state"] is None
    assert houses["c_read_back_state"] is None
    # ⚠ And a return CODE is a statement: the rise/set integer fails (a).
    assert rows["rise_trans"]["state_mediation_measured"]["a_returns_no_flag_and_no_code"] is False


#: The committed survey's own readings (2026-08-21) -- epoch, regime, entry point, request,
#: constant in force, offset bits. ⭐ The twin every clause-(b) negative mutates one place of.
_SURVEYED = [
    ("year_1900", "present", "deltat_ex", "moshier", -25.58, "bef8e53f9390af26"),
    ("year_1900", "present", "deltat_ex", "swiss_file", -25.936, "bef7b4c59a971c0d"),
    ("year_1900", "present", "deltat_ex", "jpl_file", -25.8, "bef82916b78c0694"),
    ("year_1900", "present", "deltat", None, -25.936, "bef7b4c59a971c0d"),
    ("year_2000", "present", "deltat_ex", "moshier", -25.58, "3f483521f8f78e61"),
    ("year_2000", "present", "deltat_ex", "swiss_file", -25.936, "3f483521f8f78e61"),
    ("year_2000", "present", "deltat_ex", "jpl_file", -25.8, "3f483521f8f78e61"),
    ("year_2000", "present", "deltat", None, -25.936, "3f483521f8f78e61"),
    ("year_1900", "absent", "deltat_ex", "moshier", -25.58, "bef8e53f9390af26"),
    ("year_1900", "absent", "deltat_ex", "swiss_file", -25.8, "bef82916b78c0694"),
    ("year_1900", "absent", "deltat_ex", "jpl_file", -25.8, "bef82916b78c0694"),
    ("year_1900", "absent", "deltat", None, -25.8, "bef82916b78c0694"),
    ("year_2000", "absent", "deltat_ex", "moshier", -25.58, "3f483521f8f78e61"),
    ("year_2000", "absent", "deltat_ex", "swiss_file", -25.8, "3f483521f8f78e61"),
    ("year_2000", "absent", "deltat_ex", "jpl_file", -25.8, "3f483521f8f78e61"),
    ("year_2000", "absent", "deltat", None, -25.8, "3f483521f8f78e61"),
]


def _rows(table):
    return [
        {
            "row": "unflagged" if requested is None else "per_flag",
            "regime": regime,
            "epoch_id": epoch,
            "entry_point": entry_point,
            **({} if requested is None else {"ephemeris_requested": requested}),
            "tidal_constant_in_force_bits": bits(constant),
            "offset_days_bits": value,
        }
        for epoch, regime, entry_point, requested, constant, value in table
    ]


def _entry(name):
    return next(e for e in ENTRY_POINTS if e.name == name)


_SILENT = {"x": {"carries_a_source": False, "integers_in_return": [], "named_sources_readable": []}}


def _b(name, table):
    return state_mediation_measured(_entry(name), readings=_SILENT, offset_rows=_rows(table))


def test_clause_b_holds_on_the_committed_surveys_own_readings_for_both_offset_entry_points():
    """⭐ The twin. Both entry points: one value per state, shared across conditions, moved."""
    for name, sharing in (("deltat_ex", 12), ("deltat", 4)):
        measured = _b(name, _SURVEYED)
        assert measured["b_value_follows_the_read_back_state"] is True
        assert measured["b_epochs_where_the_state_moved_the_value"] == ["year_1900"]
        assert measured["b_readings_sharing_a_state_under_another_condition"] == sharing
        assert measured["c_read_back_state"] == "tidal_acceleration"


def test_clause_b_refuses_one_state_carrying_two_values():
    """⛔ ① -- if one read-back state gave two values, something else entered the value."""
    table = list(_SURVEYED)
    table[9] = table[9][:5] + ("bef8e53f9390af26",)  # 1900 absent swiss_file: -25.8, another value
    for name in ("deltat_ex", "deltat"):
        assert _b(name, table)["b_value_follows_the_read_back_state"] is False


def test_clause_b_refuses_a_function_nobody_tested():
    """⛔ ② -- every state seen once is 'one value per state' about nothing. The present
    regime's flagged readings alone put three states in force once each per epoch."""
    table = [r for r in _SURVEYED if r[1] == "present" and r[2] == "deltat_ex"]
    measured = _b("deltat_ex", table)
    assert measured["b_readings_sharing_a_state_under_another_condition"] == 0
    assert measured["b_epochs_where_the_state_moved_the_value"] == ["year_1900"]
    assert measured["b_value_follows_the_read_back_state"] is False


def test_clause_b_refuses_a_state_that_moves_nothing():
    """⛔ ③ -- at a tabulated epoch every state gives one value; a survey confined there has
    not seen the state carry anything."""
    table = [r for r in _SURVEYED if r[0] == "year_2000"]
    measured = _b("deltat_ex", table)
    assert measured["b_epochs_where_the_state_moved_the_value"] == []
    assert measured["b_value_follows_the_read_back_state"] is False


def test_an_entry_point_with_no_read_back_is_not_measured_rather_than_failed():
    """⛔ NOT MEASURED is null. Publishing it as false would claim a clause fails."""
    measured = _b("calc_ut", _SURVEYED)
    assert measured["b_value_follows_the_read_back_state"] is None
    assert measured["c_read_back_state"] is None
    assert state_mediation(measured) is None


def test_a_read_back_state_the_library_state_record_does_not_name_is_refused(monkeypatch):
    """⛔ A respelt state would publish a read-back of a state nobody measured."""
    assert _b("deltat_ex", _SURVEYED)["c_read_back_state"] == OFFSET_READ_BACK_STATE
    monkeypatch.setattr(swiss_module, "OFFSET_READ_BACK_STATE", "tidal_accel")
    with pytest.raises(SurveyRefusal) as excinfo:
        _b("deltat_ex", _SURVEYED)
    assert "not a state the library-state record names" in str(excinfo.value)


_ALL_THREE = {
    "a_returns_no_flag_and_no_code": True,
    "b_value_follows_the_read_back_state": True,
    "b_readings_sharing_a_state_under_another_condition": 1,
    "b_epochs_where_the_state_moved_the_value": ["year_1900"],
    "c_read_back_state": "tidal_acceleration",
}


@pytest.mark.parametrize(
    "overrides",
    [
        {"a_returns_no_flag_and_no_code": False},
        {"b_value_follows_the_read_back_state": False},
        {"b_value_follows_the_read_back_state": None},
        {"c_read_back_state": None},
    ],
)
def test_the_membership_field_is_written_only_where_all_three_were_measured(overrides):
    """⭐ Each clause alone withholds it -- and the twin, all three, writes it."""
    assert state_mediation(_ALL_THREE) == {
        "answering_ephemeris": "none",
        "read_back_state": "tidal_acceleration",
    }
    assert state_mediation({**_ALL_THREE, **overrides}) is None


def test_the_measured_rows_pass_the_emission_gate_and_the_gate_still_refuses(
    one_empty_session, two_empty_regimes
):
    """⛔⛔ A DRY RUN THAT STOPS BEFORE THE LAST GATE HAS NOT DRY-RUN THE LAST GATE. The rows
    the generator will write go through the writer's own key and pattern scan here -- and the
    scan is driven the other way too, so a pass is not a scan that refuses nothing."""
    left, right = two_empty_regimes
    offsets = offset_attribution(
        epochs=[_year(1900), _year(2000)], with_files=left, without_files=right
    )
    rows = measured_entry_point_records(
        readings=returns_read_blind(one_empty_session), offset_rows=offsets
    )
    for i, row in enumerate([*rows, *offsets]):
        _scan_keys(row, where="dry-run", path=f"row[{i}]")
    with pytest.raises(FixtureContractError):
        _scan_keys({**rows[0], "Returns_Ephemeris_Flag": True}, where="dry-run", path="row[0]")
    reading = next(r for r in offsets if r["row"] == "per_flag")
    with pytest.raises(FixtureContractError):
        _scan_keys(
            {**reading, "tidal_constant_in_force_bits": bits(-1.0)}, where="dry-run", path="r"
        )


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


# --------------------------------------------------------------------------------------
# The session, and the boundary search that depends on it
# --------------------------------------------------------------------------------------


def test_a_reset_re_applies_every_piece_of_state_it_holds(tmp_path, monkeypatch):
    """⚠ Closing the library drops the sidereal mode as well as the data path. A reset that
    restored only the path was measured moving every sidereal value by about 0.88 degrees --
    a plausible number in the same range as the right one."""
    calls: list[tuple[str, object]] = []
    monkeypatch.setattr(swe, "close", lambda: calls.append(("close", None)))
    monkeypatch.setattr(swe, "set_ephe_path", lambda p: calls.append(("path", p)))
    monkeypatch.setattr(
        swe, "set_sid_mode", lambda m, a, b: calls.append(("sid", m))
    )
    Session(ephe_path=str(tmp_path), sidereal_mode=swe.SIDM_LAHIRI).reset()
    assert [name for name, _ in calls] == ["close", "path", "sid"]
    assert calls[1][1] == str(tmp_path)
    assert calls[2][1] == swe.SIDM_LAHIRI


def test_the_boundary_search_refuses_a_predicate_that_is_not_stable(monkeypatch, tmp_path):
    """⛔ The measured failure: probed without a reset, the search returned a 'last outside'
    point that answered as inside. A boundary search that does not re-verify its own
    endpoints reports an interval it has not established."""
    monkeypatch.setattr(swe, "close", lambda: None)
    monkeypatch.setattr(swe, "set_ephe_path", lambda p: None)
    monkeypatch.setattr(swe, "set_sid_mode", lambda m, a, b: None)

    seen: set[float] = set()

    def unstable(jd, planet, flags):
        # ⭐ The real shape of the failure, modelled exactly: asking about the same instant
        #    a second time gives a different answer, because the answer was never a function
        #    of the instant. Re-verification is what catches it.
        inside = 100.0 <= jd <= 200.0
        if jd in seen:
            inside = not inside
        seen.add(jd)
        return (0.0,) * 6, (swe.FLG_SWIEPH if inside else swe.FLG_MOSEPH)

    monkeypatch.setattr(swe, "calc_ut", unstable)
    session = Session(ephe_path=str(tmp_path), sidereal_mode=swe.SIDM_LAHIRI)
    with pytest.raises(EphemerisSubstitution) as excinfo:
        coverage_edges(
            MODES["swiss_file"], body=swe.SUN, jd_low=0.0, jd_high=300.0, session=session
        )
    assert "not stable" in str(excinfo.value)


def test_a_range_with_no_covered_midpoint_is_refused_rather_than_bisected(
    monkeypatch, tmp_path
):
    monkeypatch.setattr(swe, "close", lambda: None)
    monkeypatch.setattr(swe, "set_ephe_path", lambda p: None)
    monkeypatch.setattr(swe, "set_sid_mode", lambda m, a, b: None)
    monkeypatch.setattr(
        swe, "calc_ut", lambda jd, planet, flags: ((0.0,) * 6, swe.FLG_MOSEPH)
    )
    with pytest.raises(EphemerisSubstitution) as excinfo:
        coverage_edges(
            MODES["swiss_file"],
            body=swe.SUN,
            jd_low=0.0,
            jd_high=300.0,
            session=Session(ephe_path=str(tmp_path), sidereal_mode=swe.SIDM_LAHIRI),
        )
    assert "no covered interval" in str(excinfo.value)


def test_a_stable_predicate_yields_endpoints_that_survive_re_verification(
    monkeypatch, tmp_path
):
    monkeypatch.setattr(swe, "close", lambda: None)
    monkeypatch.setattr(swe, "set_ephe_path", lambda p: None)
    monkeypatch.setattr(swe, "set_sid_mode", lambda m, a, b: None)
    monkeypatch.setattr(
        swe,
        "calc_ut",
        lambda jd, planet, flags: (
            (0.0,) * 6,
            swe.FLG_SWIEPH if 100.0 <= jd <= 200.0 else swe.FLG_MOSEPH,
        ),
    )
    edges = coverage_edges(
        MODES["swiss_file"],
        body=swe.SUN,
        jd_low=0.0,
        jd_high=300.0,
        session=Session(ephe_path=str(tmp_path), sidereal_mode=swe.SIDM_LAHIRI),
    )
    assert edges["lower_edge_last_outside_jd_ut"] < 100.0 <= edges[
        "lower_edge_first_inside_jd_ut"
    ]
    assert edges["upper_edge_first_inside_jd_ut"] <= 200.0 < edges[
        "upper_edge_last_outside_jd_ut"
    ]
