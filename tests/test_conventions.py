"""The convention probes' own assumptions, pinned.

⭐ These tests are not about what the library returns today. They are about the ways this
recorder could quietly stop measuring the thing it claims to measure — a baseline taken
from the wrong row after a list is reordered, a step detector that cannot tell a leap
second from a drift, a bisection that reports an interval it never re-checked, a summary
whose keys the fixture contract would refuse.

⚠ Every one of them corresponds to a mistake that was actually made while building this,
or to one the surrounding code was already caught making elsewhere.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

#: ⛔ The whole module needs the ephemeris library; see `conftest.py` for why the reduction
#: is announced rather than merely allowed.
swe = pytest.importorskip(
    "swisseph",
    reason="this module calls the ephemeris library; it cannot run where it is not installed",
)

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from saakshi.conventions import (  # noqa: E402
    APPARENT_VARIANTS,
    ATMOSPHERES,
    GLOBAL_STATE,
    AFTER_STRATUM,
    BEFORE_STRATUM,
    Boundary,
    BracketIncomplete,
    bracket_epochs,
    boundary_character,
    classify_boundaries,
    mid_interval_epochs,
    unbounded_interval_coverage,
    HOUSE_SYSTEM_CONTROLS,
    HOUSE_SYSTEM_LETTERS,
    OMITTED_ATPRESS,
    OMITTED_ATTEMP,
    RISE_DEFINITIONS,
    STANDARD_PRESSURE,
    STANDARD_TEMPERATURE,
    STEP_THRESHOLD_SECONDS,
    _angular_delta,
    constant_offset_handover,
    global_state_records,
    house_system_survey,
    leap_second_table,
    leap_table_bounds,
    second_sixty_acceptance,
    system_class_records,
    tt_minus_utc,
)
from saakshi.fixture import _scan_keys  # noqa: E402

JD = swe.julday(2026, 3, 20, 6.0)


# --------------------------------------------------------------------------------------
# The orderings the recorder silently depends on
# --------------------------------------------------------------------------------------


def test_the_omitted_atmosphere_is_visited_first():
    """⛔ The baseline every time cost is measured against is the FIRST row visited.

    Reordering the atmospheres would move that baseline to a stated atmosphere, and every
    `seconds_from_omitted_arguments` in the fixture would silently become a difference from
    something else — with no error anywhere and no sign in the file.
    """
    assert ATMOSPHERES[0].id == "omitted"
    assert ATMOSPHERES[0].atpress == OMITTED_ATPRESS
    assert ATMOSPHERES[0].attemp == OMITTED_ATTEMP
    assert ATMOSPHERES[0].geoalt == 0.0


def test_the_definition_a_caller_gets_by_default_is_visited_first():
    """Same dependency, on the other axis."""
    assert RISE_DEFINITIONS[0][0] == "disc_centre"


def test_the_conventional_atmosphere_is_present_only_as_a_hypothesis():
    """⚠ It must be *offered* to the library as a stated request, never assumed to be the
    default. Its presence in the matrix is what lets the file answer the question at all."""
    stated = {(a.atpress, a.attemp) for a in ATMOSPHERES}
    assert (STANDARD_PRESSURE, STANDARD_TEMPERATURE) in stated
    assert (STANDARD_PRESSURE, 0.0) in stated, (
        "the pressure-standard/temperature-zero pair is the hypothesis the measurement "
        "actually confirms; without it the file cannot say what the defaults are"
    )


def test_every_variant_switches_exactly_one_thing_off_or_says_it_does_not():
    names = [name for name, _flag, _note in APPARENT_VARIANTS]
    assert len(names) == len(set(names))
    combined = [name for name in names if name == "all_three_off"]
    assert combined, "the combined variant is what shows the terms are not simply additive"


# --------------------------------------------------------------------------------------
# The step detector
# --------------------------------------------------------------------------------------


def test_the_step_threshold_sits_far_from_both_things_it_separates():
    """⭐ A whole second on one side, a drift of microseconds on the other.

    The first version of this scan differenced the wrong pair of quantities and reported a
    'step' at every scan point, because the smooth part had not been removed and grows by
    about half a second between them. The threshold alone would not have saved it — but a
    threshold that sits close to either quantity guarantees the next such mistake is silent.
    """
    assert STEP_THRESHOLD_SECONDS < 1e-3
    assert STEP_THRESHOLD_SECONDS > 0.0
    drift = abs(tt_minus_utc(2000, 1, 1) - tt_minus_utc(2000, 7, 1))
    assert drift < STEP_THRESHOLD_SECONDS, (
        "with the smooth part removed, two scan points in a year with no insertion must "
        "agree far inside the threshold; if they do not, the scan is measuring drift again"
    )


def test_the_extracted_table_is_whole_seconds_in_the_era_it_covers():
    steps = leap_second_table(1990, 2030)
    assert steps, "no steps found at all — the extraction has stopped working"
    assert all(row["is_whole_second"] for row in steps), (
        "every insertion in this era is one second; a fractional step here means the "
        "smooth part is leaking back into the measurement"
    )


def test_the_table_has_a_last_entry_and_the_bound_names_it():
    steps = leap_second_table(1961, 2060)
    bounds = leap_table_bounds(1961, 2060, steps)
    last = next(row for row in bounds if row["bound"] == "last_whole_second_step")
    assert last["date"] is not None
    # ⭐ The finding itself: the scan runs decades past that date and finds nothing more.
    assert int(str(last["date"])[:4]) < 2060


def test_a_fractional_step_after_the_table_is_not_labelled_as_being_before_it():
    """⛔ The mistake this labelling was caught making, pinned.

    The summary first called every fractional step one from the era *before* the table's
    first entry. The rows said otherwise: the era after its last entry produces them too.
    A summary that contradicts the rows it summarises is worse than none.
    """
    steps = leap_second_table(1961, 2060)
    fractional = [row for row in steps if not row["is_whole_second"]]
    regimes = {str(row["regime"]) for row in fractional}
    assert "before_the_first_whole_second_step" in regimes
    assert "after_the_last_whole_second_step_seen_so_far" in regimes, (
        "the scan must reach an era past the table's last entry that steps by fractions; "
        "if it does not, the scan's span no longer covers the finding"
    )


def test_the_held_offset_is_temporary_and_the_handover_is_located():
    """⭐ Past the last insertion the offset is held exactly — and then it is not."""
    handover = constant_offset_handover((2020, 1, 1), 60)
    assert handover is not None, (
        "no handover was found in the searched span, so either the library changed or the "
        "span no longer contains it — both are findings and neither is a pass"
    )
    before, after = handover["values"]
    assert abs(after - before) > STEP_THRESHOLD_SECONDS
    assert handover["last_date_holding_the_constant"] < handover["date"]


def test_a_search_window_entirely_inside_the_flat_region_reports_no_handover():
    """⚠ `None` means 'not in this span', and must never be manufactured from a flat span."""
    assert constant_offset_handover((2020, 1, 1), 2) is None


def test_a_second_sixty_the_table_does_not_know_is_refused_not_absorbed():
    """⭐ The better of the two available failures, and worth pinning as a property.

    A build whose table predates a real insertion fails loudly on it. If a later version
    ever starts accepting an unknown sixty-first second, values become quietly one second
    wrong and nothing says so — so this test is about the failure MODE, not the date.
    """
    rows = second_sixty_acceptance(((2017, 6, 30),))
    assert rows[0]["accepted"] is False
    assert rows[0]["refusal"]


# --------------------------------------------------------------------------------------
# Angles, and the wrap that would put the biggest number on the closest pair
# --------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "a,b,expected",
    [(0.1, 359.9, 0.2), (359.9, 0.1, 0.2), (10.0, 20.0, 10.0), (180.0, 0.0, 180.0)],
)
def test_a_longitude_difference_is_taken_the_short_way(a, b, expected):
    assert _angular_delta(a, b) == pytest.approx(expected)


# --------------------------------------------------------------------------------------
# The house-method inventory
# --------------------------------------------------------------------------------------


SAMPLES = (
    (swe.julday(2026, 3, 20, 6.0), 45.0),
    (swe.julday(1900, 1, 1, 3.0), 55.0),
    (swe.julday(2100, 9, 9, 21.0), -33.0),
)


def test_calling_a_name_and_seeing_whether_it_works_is_not_an_inventory():
    """⛔ The measured fact that forced this probe to be rebuilt.

    A name that could not be a house method is answered, not refused — so "which names does
    the build accept" returns every name offered, and an inventory built that way is a list
    of aliases presented as a list of methods.
    """
    for control in HOUSE_SYSTEM_CONTROLS:
        swe.houses_ex(JD, 45.0, 15.0, control.encode(), swe.FLG_MOSEPH)


def test_the_control_names_identify_the_fallback_without_any_documentation():
    classes, representatives, fallback = house_system_survey(SAMPLES, 15.0, swe.FLG_MOSEPH)
    assert fallback, "no class contained a control name, so the fallback was not identified"
    assert set(HOUSE_SYSTEM_CONTROLS) <= set(fallback), (
        "every name that is not a method must land in one class — if they scatter, they are "
        "not behaving as controls and the identification is void"
    )
    real = [m for m in fallback if m in HOUSE_SYSTEM_LETTERS]
    assert real, (
        "the fallback class holds no real method's letter, which would mean the build "
        "answers unknown names with something that has no name at all"
    )


def test_the_survey_returns_one_representative_per_class_and_never_a_control():
    classes, representatives, _fallback = house_system_survey(
        SAMPLES, 15.0, swe.FLG_MOSEPH
    )
    assert len(representatives) <= len(classes)
    assert all(letter in HOUSE_SYSTEM_LETTERS for letter in representatives)
    assert len(set(representatives)) == len(representatives)


def test_the_survey_compares_over_more_than_one_sample():
    """⚠ Two genuinely different methods can coincide at one instant and one latitude. A
    one-sample survey merges them and reports an alias that does not exist."""
    one = house_system_survey(SAMPLES[:1], 15.0, swe.FLG_MOSEPH)[0]
    many = house_system_survey(SAMPLES, 15.0, swe.FLG_MOSEPH)[0]
    assert len(many) >= len(one), (
        "more samples must never merge more names; they can only ever split them"
    )
    assert all(item.samples_agreed == len(SAMPLES) for item in many)


# --------------------------------------------------------------------------------------
# The state audit
# --------------------------------------------------------------------------------------


def test_the_state_audit_records_the_one_that_is_never_re_read():
    """⛔ The measured fact the leap-second probe's whole design rests on."""
    leap = next(item for item in GLOBAL_STATE if item.name == "leap_second_table")
    assert "SURVIVES" in leap.restored_by_close
    assert "fresh process" in leap.consequence or "first" in leap.consequence


def test_every_state_row_says_what_a_caller_who_assumed_otherwise_would_get():
    for item in GLOBAL_STATE:
        assert item.set_by and item.restored_by_close and item.consequence


# --------------------------------------------------------------------------------------
# ⭐ The rows and summaries must survive the contract, not be excused from it
# --------------------------------------------------------------------------------------


def test_the_probe_rows_carry_no_key_the_contract_would_refuse():
    """A key built by joining two names, or keyed by a method's capital letter, is refused —
    and the repair is to restructure the record, never to loosen the rule."""
    rows = leap_second_table(2010, 2020)
    rows.extend(second_sixty_acceptance(((2016, 12, 31),)))
    rows.extend(global_state_records())
    classes, _representatives, fallback = house_system_survey(
        SAMPLES[:1], 15.0, swe.FLG_MOSEPH
    )
    rows.extend(system_class_records(classes, fallback))
    for index, row in enumerate(rows):
        _scan_keys(row, where="probe", path=f"row[{index}]")


def test_a_key_of_the_shape_that_was_nearly_written_is_still_refused():
    """⚠ The summary tables here were first written keyed by `definition|atmosphere` and by
    a house method's capital letter. Both are refused; this pins that they still are."""
    from saakshi.fixture import FixtureContractError

    for bad in ({"disc_centre|omitted": 1.0}, {"P": {"last": 1.0}}):
        with pytest.raises(FixtureContractError):
            _scan_keys({"summary": bad}, where="probe", path="header")


# --------------------------------------------------------------------------------------
# ⭐ The bracketed switchovers — a derived grid, and the ways it could stop measuring
# --------------------------------------------------------------------------------------

BOUNDARIES = (
    Boundary("switch_a", 1948, 1, 1),
    Boundary("switch_b", 1955, 1, 1),
    Boundary("switch_c", 1974, 1, 1),
)


def _flag_row(epoch_id, *, agree, unflagged, offset=0.0):
    """A `flag_dependence` row with a chosen discrete character and arbitrary values."""
    labels = ["jpl_file", "moshier", "swiss_file"]
    patterns = {label: ("aaaa" if label in agree else f"bb{label[:2]}") for label in labels}
    return {
        "section": "flag_dependence",
        "epoch_id": epoch_id,
        "value_labels": labels,
        "values": [offset for _ in labels],
        "values_bits": [patterns[label] for label in labels],
        "unflagged_entry_point": offset,
        "unflagged_equals": list(unflagged),
    }


def _rows(**character):
    rows = []
    for boundary in BOUNDARIES:
        for suffix in ("before", "after"):
            agree, unflagged = character[f"{boundary.boundary_id}_{suffix}"]
            rows.append(_flag_row(f"{boundary.boundary_id}_{suffix}", agree=agree,
                                  unflagged=unflagged))
    return rows


SAME = (("moshier", "swiss_file", "jpl_file"), ("moshier",))
DIFFERENT = (("moshier",), ("swiss_file",))


def test_a_bracket_is_a_day_either_side_and_never_the_date_itself():
    """⚠ A reading taken ON the date says which side the behaviour is on for neither side."""
    epochs = bracket_epochs((Boundary("switch_a", 1948, 1, 1),))
    assert [stratum for _e, stratum, _jd in epochs] == [BEFORE_STRATUM, AFTER_STRATUM]
    before, after = (jd for _e, _s, jd in epochs)
    date = swe.julday(1948, 1, 1, 0.0)
    assert (date - before, after - date) == (1.0, 1.0)


def test_a_date_nothing_changes_across_does_not_survive():
    character = {f"{b.boundary_id}_{s}": SAME for b in BOUNDARIES for s in ("before", "after")}
    verdicts = classify_boundaries(BOUNDARIES, _rows(**character))
    assert [v["survives"] for v in verdicts] == [False, False, False]
    assert mid_interval_epochs(BOUNDARIES, verdicts) == []


def test_a_date_the_agreement_pattern_changes_across_survives():
    character = {f"{b.boundary_id}_{s}": SAME for b in BOUNDARIES for s in ("before", "after")}
    character["switch_b_after"] = DIFFERENT
    character["switch_c_before"] = DIFFERENT
    verdicts = classify_boundaries(BOUNDARIES, _rows(**character))
    assert [v["boundary_id"] for v in verdicts if v["survives"]] == ["switch_b", "switch_c"]


def test_only_the_intervals_real_switchovers_enclose_are_sampled():
    """⭐ The grid is derived. A mid-interval epoch between two dates that turned out not to
    be boundaries would be a sample of an interval that does not exist."""
    character = {f"{b.boundary_id}_{s}": SAME for b in BOUNDARIES for s in ("before", "after")}
    character["switch_b_after"] = DIFFERENT
    character["switch_c_before"] = DIFFERENT
    verdicts = classify_boundaries(BOUNDARIES, _rows(**character))

    epochs = mid_interval_epochs(BOUNDARIES, verdicts)
    assert [eid for eid, _s, _jd in epochs] == ["mid_switch_b_to_switch_c"]
    midpoint = epochs[0][2]
    assert swe.julday(1955, 1, 1, 0.0) < midpoint < swe.julday(1974, 1, 1, 0.0)


def test_a_missing_bracket_is_refused_rather_than_judged():
    """⛔ A boundary judged from one end is judged from no ends — the same shape as a
    comparison that reports zero because the second call never happened."""
    character = {f"{b.boundary_id}_{s}": SAME for b in BOUNDARIES for s in ("before", "after")}
    rows = [r for r in _rows(**character) if r["epoch_id"] != "switch_b_after"]
    with pytest.raises(BracketIncomplete, match="switch_b"):
        classify_boundaries(BOUNDARIES, rows)


def test_the_character_is_discrete_so_ordinary_drift_cannot_look_like_a_switchover():
    """⭐ The offset moves across every date in the calendar. A rule cut from the value
    would report all four dates as boundaries and discriminate nothing."""
    drifted = _flag_row("x", agree=("moshier", "swiss_file", "jpl_file"), unflagged=("moshier",))
    same_character = dict(drifted, values_bits=["aaaa", "aaaa", "aaaa"])
    assert boundary_character(drifted) == boundary_character(same_character)


def test_an_unbounded_interval_with_nothing_in_it_is_refused():
    """⚠ These two have no midpoint to take, so the check is that something already measured
    lies inside them. An interval with no reading in it is one the grid has not covered."""
    character = {f"{b.boundary_id}_{s}": SAME for b in BOUNDARIES for s in ("before", "after")}
    character["switch_b_after"] = DIFFERENT
    verdicts = classify_boundaries(BOUNDARIES, _rows(**character))

    covering = [("year_1900", "s", swe.julday(1900, 1, 1, 0.0)),
                ("year_2100", "s", swe.julday(2100, 1, 1, 0.0))]
    coverage = unbounded_interval_coverage(BOUNDARIES, verdicts, covering)
    assert [c["interval"] for c in coverage] == ["before_the_earliest", "after_the_latest"]
    assert coverage[0]["covered_by"] == ["year_1900"]

    with pytest.raises(BracketIncomplete, match="before_the_earliest"):
        unbounded_interval_coverage(BOUNDARIES, verdicts, covering[1:])


def test_the_switchover_verdicts_carry_no_key_the_contract_would_refuse():
    character = {f"{b.boundary_id}_{s}": SAME for b in BOUNDARIES for s in ("before", "after")}
    character["switch_b_after"] = DIFFERENT
    verdicts = classify_boundaries(BOUNDARIES, _rows(**character))
    _scan_keys({"switchovers": {"verdicts": verdicts}}, where="probe", path="header")


def test_every_verdict_carries_the_limit_of_the_test_that_produced_it():
    """⛔ `survives = false` means NOT OBSERVABLE from outside, never NOT THERE. A reader who
    takes the second reading has turned a bounded negative into an unbounded one."""
    character = {f"{b.boundary_id}_{s}": SAME for b in BOUNDARIES for s in ("before", "after")}
    for verdict in classify_boundaries(BOUNDARIES, _rows(**character)):
        limit = verdict["limit"].lower()
        assert "cannot observe" in limit
        assert "never one that is not there" in limit


def test_the_step_across_a_bracket_is_recorded_and_not_judged():
    """⭐ The discrete test cannot see a switchover between two models that share a
    flag-dependence character. ⛔ The answer is not to invent a threshold to catch those —
    that is a band by another name — but to write the number out for a reader who has one."""
    from saakshi.conventions import boundary_step

    before = _flag_row("x_before", agree=("moshier",), unflagged=("moshier",), offset=1.0)
    after = _flag_row("x_after", agree=("moshier",), unflagged=("moshier",), offset=2.0)
    step = boundary_step(before, after)

    assert step["seconds_by_source"] == {
        "jpl_file": 86400.0,
        "moshier": 86400.0,
        "swiss_file": 86400.0,
    }
    assert step["seconds_unflagged"] == 86400.0
    # ⚠ The caveat travels with the number, because the number alone reads as a verdict.
    assert "NOT evidence of a discontinuity" in step["meaning"]
    assert "drift" in step["meaning"]
