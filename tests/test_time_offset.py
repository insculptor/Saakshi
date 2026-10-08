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
    ControlNotPlaceable,
    DeltaTChildFailed,
    DeltaTReading,
    DeltaTSection,
    GlobalState,
    NotRenderable,
    ReadBackDisagrees,
    bits_of,
    configuration_sha256,
    delta_t_basis,
    delta_t_cause_controls,
    delta_t_classification,
    delta_t_configuration,
    delta_t_flag_rows,
    delta_t_library_state,
    delta_t_rows,
    delta_t_sufficiency_controls,
    measure_delta_t,
    run_delta_t_child,
)
from saakshi.fixture import _scan_keys  # noqa: E402
from saakshi.swiss import offset_epochs  # noqa: E402

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


# --------------------------------------------------------------------------------------
# The controls — cause and sufficiency on the compared section's configuration
# --------------------------------------------------------------------------------------

OWN, FILE_CONSTANT, DEFAULT_CONSTANT = -25.58, -25.936, -25.8
SECTION = {s.name: s for s in DELTA_T_SECTIONS}
BASIS = delta_t_basis(ephe=EPHE, sidereal_mode=1, **LIBRARY)
SURVEY = [("year_1900", JD_1900), ("year_2000", JD_2000)]
JD_1955 = float(swe.julday(1955, 1, 1, 0.0))


def _grid() -> list[DeltaTReading]:
    """The compared section reads its own constant back; the others put two other constants
    in force. At 1900 and at a non-survey epoch the value moves with the constant; at 2000
    every configuration returns one value."""
    constant = {
        "delta_t_moshier": OWN,
        "delta_t_swiss_file": FILE_CONSTANT,
        "delta_t_jpl_file": DEFAULT_CONSTANT,
        "delta_t_unflagged": FILE_CONSTANT,
    }
    moved = {OWN: -1.0, FILE_CONSTANT: -2.0, DEFAULT_CONSTANT: -3.0}
    out = []
    for section in DELTA_T_SECTIONS:
        c = constant[section.name]
        for eid, jd, value in (
            ("year_1900", JD_1900, moved[c]),
            ("year_2000", JD_2000, 7.0),
            ("not_surveyed", JD_1955, moved[c] * 10),
        ):
            out.append(DeltaTReading(section, eid, "s", jd, value, c))
    return out


class _Child:
    """Records every plan; answers each reading with a value of its own and, for a forced
    reading, the read-back it is told to (the forced value unless `void`)."""

    def __init__(self, *, void: bool = False, unmoved: bool = False):
        self.plans: list[dict] = []
        self.void, self.unmoved = void, unmoved

    def __call__(self, plan):
        self.plans.append(plan)
        out = []
        for i, step in enumerate(plan["readings"]):
            forced = step["forced_tidal_bits"]
            value = 100.0 + len(self.plans) + i / 100
            if forced is not None and self.unmoved:
                value = -1.0  # the compared section's own baseline at 1900
            back = forced if forced is not None and not self.void else bits_of(OWN)
            out.append({"returned_type": "float", "value_bits": bits_of(value),
                        "read_back_bits": back})
        return out


def _cause(readings, child, survey=SURVEY):
    return delta_t_cause_controls(
        readings, compared=DELTA_T_COMPARED_SECTION, basis=BASIS, survey_epochs=survey,
        ephe_path="d", sidereal_mode=1, child=child,
    )


def test_a_cause_control_is_placed_only_where_the_survey_read_and_the_value_can_move():
    child = _Child()
    rows, skipped = _cause(_grid(), child)
    # ⭐ at 1900, one per OTHER constant; ⛔ not at the epoch no survey read; ⛔ not at 2000
    assert [(r["epoch_id"], r["forced_value_bits"]) for r in rows] == sorted(
        [("year_1900", bits_of(DEFAULT_CONSTANT)), ("year_1900", bits_of(FILE_CONSTANT))],
        key=lambda p: p[1],
    )
    assert {(s["epoch_id"], s["constant_bits"]) for s in skipped} == {
        ("year_2000", bits_of(DEFAULT_CONSTANT)), ("year_2000", bits_of(FILE_CONSTANT))}
    assert all("cannot move" in s["why"] for s in skipped)
    # ⭐ each in a process of its own, forcing the constant, through the compared section's call
    assert [len(p["readings"]) for p in child.plans] == [1, 1]
    for plan, row in zip(child.plans, rows):
        (step,) = plan["readings"]
        assert step["forced_tidal_bits"] == row["forced_value_bits"]
        assert step["flag"] == SECTION[DELTA_T_COMPARED_SECTION].flag
        assert step["jd_bits"] == bits_of(JD_1900)
    for row in rows:
        assert row["state"] == DELTA_T_READ_BACK_STATE
        assert row["baseline_value_bits"] == bits_of(-1.0)
        assert row["read_back_after_call_bits"] == row["forced_value_bits"]
        assert row["value_bits"] not in (bits_of(-1.0),)
        _scan_keys(row, where="t", path="row")
    # ⭐ the value is the child's, as read
    assert [r["value"] for r in rows] == [101.0, 102.0]


def test_a_cause_control_never_forces_the_sections_own_constant():
    """⛔ Forcing the value already in force cannot fail, and is not a control."""
    grid = [
        DeltaTReading(r.section, r.epoch_id, r.stratum, r.jd, r.value, OWN) for r in _grid()
    ]
    child = _Child()
    rows, skipped = _cause(grid, child)
    assert rows == [] and child.plans == []
    assert {s["epoch_id"] for s in skipped} == {"year_1900", "year_2000"}
    assert all("no other configuration" in s["why"] for s in skipped)


def test_a_void_or_unmoved_cause_control_is_written_as_measured():
    """⛔ Measured, never declared: a call that overwrote the forced constant, or a value that
    did not move, is the finding — and is written, not filtered."""
    rows, _ = _cause(_grid(), _Child(void=True, unmoved=True))
    assert len(rows) == 2
    for row in rows:
        assert row["read_back_after_call_bits"] == bits_of(OWN) != row["forced_value_bits"]
        assert row["value_bits"] == row["baseline_value_bits"]


def test_a_survey_epoch_that_is_another_instant_under_the_same_name_is_refused():
    with pytest.raises(ControlNotPlaceable, match="year_1900"):
        _cause(_grid(), _Child(), survey=[("year_1900", JD_1900 + 1.0)])


def test_a_survey_epoch_the_section_did_not_read_is_refused():
    """⛔ Dropping it would leave the survey's discriminating epoch uncontrolled, silently."""
    with pytest.raises(ControlNotPlaceable, match="year_1950"):
        _cause(_grid(), _Child(), survey=SURVEY + [("year_1950", JD_1955)])


def test_the_survey_reads_the_offset_at_instants_the_time_offset_grid_also_reads():
    """⭐ The cause control stands on the survey's epochs, so they must be epochs of the
    time-offset grid by name AND by instant — held against the generator's own grid."""
    import importlib.util

    path = Path(__file__).resolve().parents[1] / "generators" / "convention_probes.py"
    spec = importlib.util.spec_from_file_location("_convention_probes", path)
    assert spec and spec.loader
    probes = importlib.util.module_from_spec(spec)
    sys.modules["_convention_probes"] = probes
    spec.loader.exec_module(probes)
    grid = {eid: bits_of(jd) for eid, _stratum, jd in probes._epochs(probes.DELTA_T_EPOCHS)}
    survey = offset_epochs()
    assert survey, "⛔ an empty survey would make this pass vacuously"
    for epoch_id, jd in survey:
        assert grid.get(epoch_id) == bits_of(jd), epoch_id


def test_every_control_names_the_compared_sections_configuration():
    rows, _ = _cause(_grid(), _Child())
    sufficiency = delta_t_sufficiency_controls(
        _grid(), compared=DELTA_T_COMPARED_SECTION, basis=BASIS, ephe_path="d",
        sidereal_mode=1, child=_Child(),
    )
    # ⭐ the identity of the analytical section under sidereal mode 1 — a published vector
    expected = "aa366175f15d303f64fa1728d72e32dd99016a11c1179b839d1cf6026bdf1c57"
    assert {r["configuration_sha256"] for r in rows + sufficiency} == {expected}
    assert {r["entry_point"] for r in rows + sufficiency} == {"deltat_ex"}
    assert {r["finding"] for r in rows + sufficiency} == {"configuration_control"}


def test_sufficiency_regenerates_the_section_under_two_other_call_histories():
    child = _Child()
    grid = _grid()
    rows = delta_t_sufficiency_controls(
        grid, compared=DELTA_T_COMPARED_SECTION, basis=BASIS, ephe_path="d", sidereal_mode=1,
        child=child,
    )
    mine = [r for r in grid if r.section.name == DELTA_T_COMPARED_SECTION]
    row_order = [r.epoch_id for r in mine]
    # ⭐ one process holding EVERY reading of the file, in reverse ...
    permuted_plan, *cold_plans = child.plans
    assert [(s["flag"], s["jd_bits"]) for s in permuted_plan["readings"]] == [
        (r.section.flag, bits_of(r.jd)) for r in reversed(grid)
    ]
    # ... then one process per row of the section, each holding that row alone
    assert [[(s["flag"], s["jd_bits"]) for s in p["readings"]] for p in cold_plans] == [
        [(r.section.flag, bits_of(r.jd))] for r in mine
    ]
    permuted = [r for r in rows if r["call_history"] == "permuted"]
    cold = [r for r in rows if r["call_history"] == "cold_process_per_row"]
    assert {r["epoch_id"] for r in permuted} == {r["epoch_id"] for r in cold} == set(row_order)
    for r in permuted:
        assert sorted(r["call_order"]) == sorted(row_order)
        assert r["call_order"] != row_order, "⛔ the same order is not another call history"
    assert all("call_order" not in r for r in cold)
    # ⭐ every value is the regeneration's own — never copied from the section
    section_values = {bits_of(r.value) for r in mine}
    assert not {b for r in rows for b in r["values_bits"]} & section_values
    for r in rows:
        _scan_keys(r, where="t", path="row")


def test_a_one_row_section_is_regenerated_only_in_cold_processes():
    """⛔ A permutation of one row is the same order."""
    one = [r for r in _grid() if r.epoch_id == "year_1900"]
    rows = delta_t_sufficiency_controls(
        one, compared=DELTA_T_COMPARED_SECTION, basis=BASIS, ephe_path="d", sidereal_mode=1,
        child=_Child(),
    )
    assert [r["call_history"] for r in rows] == ["cold_process_per_row"]


def test_the_controls_against_the_library_itself_with_no_data_files(tmp_path):
    """⭐ End to end in an empty directory: the readings, then both controls, from real child
    processes. With no files the three other configurations hold the library's default
    constant, so one cause control is placed at 1900 and none at 2000."""
    epochs = [("year_1900", "s", JD_1900), ("year_2000", "s", JD_2000)]
    readings = measure_delta_t(epochs, ephe_path=str(tmp_path), sidereal_mode=1)
    basis = delta_t_basis(ephe=EPHE, sidereal_mode=1, **LIBRARY)
    cause, skipped = delta_t_cause_controls(
        readings, compared=DELTA_T_COMPARED_SECTION, basis=basis, survey_epochs=SURVEY,
        ephe_path=str(tmp_path), sidereal_mode=1,
    )
    (row,) = cause
    assert row["epoch_id"] == "year_1900"
    assert row["forced_value_bits"] == bits_of(DEFAULT_CONSTANT)
    assert row["read_back_after_call_bits"] == row["forced_value_bits"]
    siblings = {bits_of(r.value) for r in readings
                if r.epoch_id == "year_1900" and r.section.name != DELTA_T_COMPARED_SECTION}
    assert {row["value_bits"]} == siblings != {row["baseline_value_bits"]}
    assert [s["epoch_id"] for s in skipped] == ["year_2000"]

    sufficiency = delta_t_sufficiency_controls(
        readings, compared=DELTA_T_COMPARED_SECTION, basis=basis, ephe_path=str(tmp_path),
        sidereal_mode=1,
    )
    section = {r.epoch_id: [bits_of(r.value)] for r in readings
               if r.section.name == DELTA_T_COMPARED_SECTION}
    assert len(sufficiency) == 4
    for r in sufficiency:
        assert r["values_bits"] == section[r["epoch_id"]]
