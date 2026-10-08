"""The time offset, re-emitted one configuration per section — its assumptions, pinned.

⭐ These are about the ways the re-emit could quietly stop saying what it says: a
configuration identity a consumer would compute differently, a state discipline that
reads as complete while omitting a state, a reset that does not undo what it claims to, a
section that holds two requests' answers, a row that names a source it cannot have.

⚠ The suite holds no data files, so the readings here are taken against an empty
directory — enough to show the child process resets, forces and reads back, and never
enough to show what the files make the library return.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

#: ⛔ The whole module needs the ephemeris library; see `conftest.py`.
swe = pytest.importorskip(
    "swisseph",
    reason="this module calls the ephemeris library; it cannot run where it is not installed",
)

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import saakshi.conventions as conventions  # noqa: E402
from saakshi.conventions import (  # noqa: E402
    DELTA_T_COMPARED_SECTION,
    DELTA_T_NO_SOURCE,
    DELTA_T_READ_BACK_STATE,
    DELTA_T_SECTIONS,
    DELTA_T_STATE_DISCIPLINE,
    GLOBAL_STATE,
    NO_FLAG_ACCEPTED,
    NOT_REPORTED,
    BracketIncomplete,
    ConfigurationIncomplete,
    DeltaTChildFailed,
    DeltaTReading,
    DeltaTSection,
    GlobalState,
    NotRenderable,
    ReadBackDisagrees,
    bits_of,
    configuration_sha256,
    delta_t_basis,
    delta_t_classification,
    delta_t_configuration,
    delta_t_flag_rows,
    delta_t_library_state,
    delta_t_rows,
    measure_delta_t,
    run_delta_t_child,
)
from saakshi.fixture import _scan_keys  # noqa: E402

JD_1900 = float(swe.julday(1900, 1, 1, 0.0))
JD_2000 = float(swe.julday(2000, 1, 1, 0.0))

#: The three data files a consumer's published identity vectors were computed over.
FILES = [
    {"dataset": "seas_18.se1",
     "sha256": "a2cd8fc33807c78ca9a700c91c2e042258b12fc4796519e00781440b5ad8b2e2"},
    {"dataset": "semo_18.se1",
     "sha256": "1ca07bd67c24374d77226180c20a4f9996cba013697894810518e7eb582ca4f7"},
    {"dataset": "sepl_18.se1",
     "sha256": "ca1393ceab3a44fbc895887cf789c68819ae6a1cbc9b22225872dbe4ccd99a66"},
]
EPHE = {"directory_contents_verified": True, "files": FILES}
LIBRARY = {"library_version": "2.10.03", "binding": "pyswisseph", "binding_version": "2.10.3.2"}
STATES = ("sidereal_mode", "user_defined_delta_t", "tidal_acceleration", "leap_second_table")


def _configuration(**states: dict[str, str]) -> dict:
    library_state = {name: {"discipline": "reset"} for name in STATES}
    library_state.update(states)
    return {
        "ephemeris_path": {
            "set": "explicit",
            "resolved_contents": [dict(f) for f in FILES],
            "directory_contents_verified": True,
        },
        "library_state": library_state,
    }


def _identity(requested: str, configuration: dict, entry_point: str = "deltat_ex") -> str:
    return configuration_sha256(
        entry_point=entry_point, requested=requested, configuration=configuration, **LIBRARY
    )


# --------------------------------------------------------------------------------------
# The configuration identity — a consumer computes it too, so it must agree to the bit
# --------------------------------------------------------------------------------------


def test_the_identity_reproduces_a_consumers_four_published_vectors():
    """⭐ Measured literals, never a second implementation's output: the same configuration
    a consumer published four identities for, rendered here independently."""
    assert _identity("moshier", _configuration()) == (
        "59ca2c5e29ca3ea17a6c08b1fbc6993675fb6c8199ec4e17972bbd8f02c8def7"
    )
    # ⛔ the control that must differ — the request is part of the identity
    assert _identity("swiss_file", _configuration()) == (
        "31dca48d19dadda724306e3eec152c207dd5d27a08d4d289f1cc9a9f9759c572"
    )
    assert _identity(
        "moshier", _configuration(sidereal_mode={"discipline": "declared", "value": "1"})
    ) == "aa366175f15d303f64fa1728d72e32dd99016a11c1179b839d1cf6026bdf1c57"
    # ⛔ the tag control: the same state, the other form of the same number, another identity
    assert _identity(
        "moshier",
        _configuration(sidereal_mode={"discipline": "declared", "value_bits": "3ff0000000000000"}),
    ) == "37208b6f3f95755d8c87ae1af18ccd19520d05347339866c54fdcfed01b373f3"


def test_the_identity_does_not_depend_on_the_order_things_were_listed_in():
    """Files by dataset and states by name, sorted — a re-listing is not a new configuration."""
    shuffled = _configuration()
    shuffled["ephemeris_path"]["resolved_contents"].reverse()
    shuffled["library_state"] = dict(reversed(list(shuffled["library_state"].items())))
    assert _identity("moshier", shuffled) == _identity("moshier", _configuration())


@pytest.mark.parametrize(
    "where",
    ["value", "state_name", "entry_point", "dataset"],
)
@pytest.mark.parametrize("forger", ["|", "\n", "\r"])
def test_a_field_boundary_inside_a_rendered_value_is_refused(where, forger):
    """⛔ A '|' or a line break would let two configurations render the same text."""
    configuration = _configuration()
    entry_point = "deltat_ex"
    if where == "value":
        configuration["library_state"]["sidereal_mode"] = {
            "discipline": "declared", "value": f"1{forger}2"}
    elif where == "state_name":
        configuration["library_state"][f"sidereal{forger}mode"] = {"discipline": "reset"}
    elif where == "entry_point":
        entry_point = f"deltat{forger}ex"
    else:
        configuration["ephemeris_path"]["resolved_contents"][0]["dataset"] = f"a{forger}b"
    with pytest.raises(NotRenderable):
        _identity("moshier", configuration, entry_point=entry_point)


def test_a_dataset_listed_twice_is_refused():
    configuration = _configuration()
    configuration["ephemeris_path"]["resolved_contents"].append(dict(FILES[0]))
    with pytest.raises(NotRenderable, match="twice"):
        _identity("moshier", configuration)


# --------------------------------------------------------------------------------------
# The state discipline — complete over what was measured, and only that
# --------------------------------------------------------------------------------------


def test_the_discipline_covers_exactly_the_states_the_audit_measured():
    assert set(DELTA_T_STATE_DISCIPLINE) == {state.name for state in GLOBAL_STATE}
    assert set(delta_t_library_state(sidereal_mode=1)) == {state.name for state in GLOBAL_STATE}


def test_a_state_measured_later_and_not_declared_is_a_refusal(monkeypatch):
    """⭐ A fifth state joins the requirement on its measurement — the declaration cannot
    stay complete-looking while missing it."""
    fifth = GlobalState(name="a_fifth_state", set_by="x", restored_by_close="x", consequence="x")
    monkeypatch.setattr(conventions, "GLOBAL_STATE", GLOBAL_STATE + (fifth,))
    with pytest.raises(ConfigurationIncomplete, match="a_fifth_state"):
        delta_t_library_state(sidereal_mode=1)


def test_a_discipline_for_a_state_nobody_measured_is_a_refusal(monkeypatch):
    shrunk = tuple(s for s in GLOBAL_STATE if s.name != "leap_second_table")
    monkeypatch.setattr(conventions, "GLOBAL_STATE", shrunk)
    with pytest.raises(ConfigurationIncomplete, match="leap_second_table"):
        delta_t_library_state(sidereal_mode=1)


def test_only_the_sidereal_mode_is_declared_and_it_carries_the_sessions_value():
    for mode in (1, 7):
        state = delta_t_library_state(sidereal_mode=mode)
        assert state["sidereal_mode"] == {"discipline": "declared", "value": str(mode)}
        assert all(
            entry == {"discipline": "reset"}
            for name, entry in state.items()
            if name != "sidereal_mode"
        )


# --------------------------------------------------------------------------------------
# One section per configuration
# --------------------------------------------------------------------------------------


def test_every_section_is_one_entry_point_under_one_request():
    names = [section.name for section in DELTA_T_SECTIONS]
    assert len(names) == len(set(names))
    pairs = {(section.entry_point, section.requested) for section in DELTA_T_SECTIONS}
    assert pairs == {
        ("deltat_ex", "moshier"),
        ("deltat_ex", "swiss_file"),
        ("deltat_ex", "jpl_file"),
        ("deltat", NO_FLAG_ACCEPTED),
    }
    # ⭐ The request is derived from the flag, so a section cannot say one and call another.
    assert DeltaTSection("x", "deltat_ex", swe.FLG_MOSEPH).requested == "moshier"
    assert DeltaTSection("x", "deltat", None).requested == NO_FLAG_ACCEPTED


def test_exactly_one_section_is_classified_for_comparison_and_it_is_the_analytical_one():
    classification = delta_t_classification()
    assert set(classification) == {section.name for section in DELTA_T_SECTIONS}
    exact = [name for name, spec in classification.items() if spec["class"] == "exact"]
    assert exact == [DELTA_T_COMPARED_SECTION]
    compared = next(s for s in DELTA_T_SECTIONS if s.name == DELTA_T_COMPARED_SECTION)
    assert (compared.entry_point, compared.requested) == ("deltat_ex", "moshier")
    assert all(
        spec == {"class": "reference_only"}
        for name, spec in classification.items()
        if name != DELTA_T_COMPARED_SECTION
    )


def test_a_compared_section_that_is_absent_or_doubled_is_refused():
    with pytest.raises(ConfigurationIncomplete):
        delta_t_classification(compared="no_such_section")
    doubled = DELTA_T_SECTIONS + (DELTA_T_SECTIONS[0],)
    with pytest.raises(ConfigurationIncomplete):
        delta_t_classification(sections=doubled)


def test_the_basis_declares_every_section_and_no_file_level_request():
    basis = delta_t_basis(ephe=EPHE, sidereal_mode=1, **LIBRARY)
    assert set(basis) == {"library_version", "called_via", "data_files", "sections"}
    assert set(basis["sections"]) == set(delta_t_classification())
    pairs = {(f["dataset"], f["sha256"]) for f in FILES}
    assert {(f["dataset"], f["sha256"]) for f in basis["data_files"]["files"]} == pairs
    for section in DELTA_T_SECTIONS:
        declared = basis["sections"][section.name]
        assert declared["entry_point"] == section.entry_point
        assert declared["requested"] == section.requested
        assert declared["returned"] == NOT_REPORTED
        assert declared["configuration"] == delta_t_configuration(EPHE, sidereal_mode=1)
        resolved = declared["configuration"]["ephemeris_path"]["resolved_contents"]
        assert {(f["dataset"], f["sha256"]) for f in resolved} == pairs


# --------------------------------------------------------------------------------------
# The child process — the reset it claims, shown undoing what it claims to undo
# --------------------------------------------------------------------------------------


def _plan(tmp_path: Path, *steps: dict) -> dict:
    return {"ephe_path": str(tmp_path), "sidereal_mode": 1, "readings": list(steps)}


def _moshier_1900(**extra) -> dict:
    return {"flag": swe.FLG_MOSEPH, "jd_bits": bits_of(JD_1900), "forced_tidal_bits": None,
            **extra}


def test_the_reset_undoes_a_user_defined_offset_and_a_forced_constant(tmp_path):
    """⛔ A reset nothing can be shown to undo is a reset nobody has measured. The user-defined
    offset SURVIVES a close, so only the explicit reset puts it back. ⚠ The forced constant is
    put back by the close AND by setting the path — measured, each alone — so this test holds
    the pair, and removing only one of them is not something it can see. Both states are set
    before a reading, and the reading must not see them."""
    clean, dirty = run_delta_t_child(
        _plan(
            tmp_path,
            _moshier_1900(),
            _moshier_1900(contaminate={"user_defined_delta_t": 0.5,
                                       "tidal_acceleration": -25.936}),
        )
    )
    assert clean["returned_type"] == "float"
    assert dirty == clean


def test_a_forced_constant_survives_the_call_and_moves_the_value(tmp_path):
    forced = bits_of(-25.936)
    clean, moved = run_delta_t_child(
        _plan(tmp_path, _moshier_1900(), _moshier_1900(forced_tidal_bits=forced))
    )
    assert moved["read_back_bits"] == forced
    assert clean["read_back_bits"] != forced
    assert moved["value_bits"] != clean["value_bits"]


def test_the_entry_point_that_takes_no_flag_is_called_without_one(tmp_path):
    """⚠ At 1900, where the flag moves the answer — at 2000 every request agrees, and a
    reading there could not tell the two entry points apart."""
    unflagged, analytical = run_delta_t_child(
        _plan(
            tmp_path,
            {"flag": None, "jd_bits": bits_of(JD_1900), "forced_tidal_bits": None},
            _moshier_1900(),
        )
    )
    assert unflagged["returned_type"] == "float"
    assert unflagged["value_bits"] != analytical["value_bits"]
    # ⭐ with no data file, the call that takes no flag holds the library's default constant
    assert unflagged["read_back_bits"] == bits_of(-25.8)
    assert analytical["read_back_bits"] == bits_of(-25.58)


def test_readings_are_taken_section_by_section_in_one_process():
    plans: list[dict] = []

    def child(plan):
        plans.append(plan)
        return [
            {"returned_type": "float", "value_bits": bits_of(1.0 + i), "read_back_bits":
             bits_of(-25.58)}
            for i in range(len(plan["readings"]))
        ]

    epochs = [("e1", "s", JD_1900), ("e2", "s", JD_2000)]
    readings = measure_delta_t(epochs, ephe_path="d", sidereal_mode=1, child=child)
    assert len(plans) == 1, "⛔ one process for the grid, so its call history is one history"
    flags = [step["flag"] for step in plans[0]["readings"]]
    assert flags == [s.flag for s in DELTA_T_SECTIONS for _ in epochs]
    assert [(r.section.name, r.epoch_id) for r in readings] == [
        (s.name, e) for s in DELTA_T_SECTIONS for e, _s, _jd in epochs
    ]
    # ⭐ each value is the child's, in order — never one reading copied into another
    assert [r.value for r in readings] == [1.0 + i for i in range(len(readings))]


def test_a_return_that_is_not_a_bare_number_is_refused():
    """⛔ `not_reported` is written because the return carries no flag; a return that is not a
    bare number has to be read again before anything is written about it."""

    def child(plan):
        return [{"returned_type": "tuple", "value_bits": None, "read_back_bits":
                 bits_of(-25.58)} for _ in plan["readings"]]

    with pytest.raises(DeltaTChildFailed, match="tuple"):
        measure_delta_t([("e1", "s", JD_1900)], ephe_path="d", sidereal_mode=1, child=child)


def test_a_child_that_returns_fewer_readings_than_it_was_asked_for_is_refused():
    def child(plan):
        return [{"returned_type": "float", "value_bits": bits_of(1.0),
                 "read_back_bits": bits_of(-25.58)}]

    with pytest.raises(ValueError):
        measure_delta_t([("e1", "s", JD_1900)], ephe_path="d", sidereal_mode=1, child=child)


# --------------------------------------------------------------------------------------
# The rows
# --------------------------------------------------------------------------------------


def _readings(*, read_back=-25.58, values=None) -> list[DeltaTReading]:
    out = []
    for i, section in enumerate(DELTA_T_SECTIONS):
        for j, (eid, jd) in enumerate((("e1", JD_1900), ("e2", JD_2000))):
            value = values[(section.name, eid)] if values else float(i * 10 + j)
            out.append(DeltaTReading(section, eid, "s", jd, value, read_back))
    return out


def test_every_row_refuses_a_source_and_reads_the_state_back():
    rows = delta_t_rows(_readings())
    assert len(rows) == len(DELTA_T_SECTIONS) * 2
    for row in rows:
        assert row["source_assertion"] == {"kind": "none", "reason": DELTA_T_NO_SOURCE}
        assert row["state_read_back"] == {
            "state": DELTA_T_READ_BACK_STATE,
            "value": -25.58,
            "value_bits": bits_of(-25.58),
        }
        section = next(s for s in DELTA_T_SECTIONS if s.name == row["section"])
        if section.flag is None:
            assert "ephemeris_requested" not in row
        else:
            assert row["ephemeris_requested"] == section.requested
        _scan_keys(row, where="t", path="row")
    # ⭐ the read-back state is the audit's own spelling
    assert DELTA_T_READ_BACK_STATE in {state.name for state in GLOBAL_STATE}


def test_epoch_ids_are_unique_within_every_section():
    rows = delta_t_rows(_readings())
    for section in DELTA_T_SECTIONS:
        ids = [row["epoch_id"] for row in rows if row["section"] == section.name]
        assert len(ids) == len(set(ids)) == 2


def test_a_section_that_reads_back_two_constants_is_refused():
    readings = _readings()
    readings[1] = DeltaTReading(
        readings[1].section, readings[1].epoch_id, "s", readings[1].jd, readings[1].value, -25.8
    )
    with pytest.raises(ReadBackDisagrees, match=DELTA_T_SECTIONS[0].name):
        delta_t_rows(readings)


def test_the_flag_comparison_is_derived_from_the_sections_and_never_a_row():
    values = {}
    for section in DELTA_T_SECTIONS:
        values[(section.name, "e1")] = {"delta_t_swiss_file": 2.0}.get(section.name, 1.0)
        values[(section.name, "e2")] = 5.0
    values[("delta_t_unflagged", "e1")] = 2.0
    rows = delta_t_rows(_readings(values=values))
    assert "flag_dependence" not in {row["section"] for row in rows}
    by_epoch = {row["epoch_id"]: row for row in delta_t_flag_rows(_readings(values=values))}
    assert by_epoch["e1"]["unflagged_equals"] == ["swiss_file"]
    assert by_epoch["e1"]["value_labels"] == ["jpl_file", "moshier", "swiss_file"]
    assert by_epoch["e1"]["spread_seconds"] == 86_400.0
    assert by_epoch["e2"]["unflagged_equals"] == ["jpl_file", "moshier", "swiss_file"]
    assert by_epoch["e2"]["spread_seconds"] == 0.0


def test_an_epoch_with_no_reading_of_the_unflagged_entry_point_is_refused():
    readings = [r for r in _readings() if not (r.section.flag is None and r.epoch_id == "e2")]
    with pytest.raises(BracketIncomplete, match="e2"):
        delta_t_flag_rows(readings)
