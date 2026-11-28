"""Negative tests for the fixture contract.

⭐ Almost every test here asserts a **refusal**. That is deliberate: a schema whose tests
only build valid documents proves that the happy path works and nothing about whether the
fail-closed half is armed. The contract is a list of things that must be *rejected*, so
the test file is a list of rejections.
"""

from __future__ import annotations

import json

import pytest

from saakshi.fixture import (
    REFERENCES_CONTRACT,
    FixtureContractError,
    Generator,
    Header,
    bits,
    check_jsonl,
    find_absolute_path,
    patterned,
    redact_environment,
    resolve_pattern_partner,
    validate_filename,
    validate_header,
    write_jsonl,
)

GEN = Generator(repo="github.com/insculptor/Saakshi", script="generators/x.py", commit="0" * 40)

#: ⛔ **This constant used to read `interpretation_status: "settled"`, and every test using it
#: passed.** No registry has ever declared that value. `_validate_locus` checked the five
#: fields for *presence* and never for what they said, so the contract's own test suite was
#: quietly demonstrating the hole R6 was the first artifact to stand on — a field whose value
#: set is "any string" reports a pass on anything. The registries are in `fixture.py` and
#: their refusals are tested in `test_textual.py`.
LOCUS = {
    "source_kind": "primary_text",
    "language": "sa",
    "edition": {"publisher": "P", "year": 1900},
    "locus": "ch. 1 v. 2",
    "interpretation_status": "quoted",
}


def numeric(**over) -> Header:
    base = dict(
        fixture_kind="numeric_pin",
        reference="R2",
        generator=GEN,
        generated="2026-08-04",
        oracle={"toolkit": "CSPICE_N0067"},
        request={"grid": "stratified"},
        classification={"position": {"class": "reference_only"}},
        budget_row="K-b",
    )
    base.update(over)
    return Header(**base)


# --- the vocabulary -------------------------------------------------------------------


def test_unknown_kind_is_refused():
    with pytest.raises(FixtureContractError, match="fixture_kind"):
        validate_header(numeric(fixture_kind="grid_row"), where="t")


def test_unknown_reference_is_refused():
    with pytest.raises(FixtureContractError, match="reference"):
        validate_header(numeric(reference="R8"), where="t")


def test_reference_none_without_a_deviation_block_is_refused():
    """⚠ The one value outside the reference registry may never be silent."""
    with pytest.raises(FixtureContractError, match="contract_deviation"):
        validate_header(numeric(reference="none"), where="t")


def test_reference_none_with_a_deviation_block_is_admitted():
    validate_header(
        numeric(
            reference="none",
            contract_deviation=[{"clause": "reference registry", "why": "no value fits"}],
        ),
        where="t",
    )


def test_a_conforming_fixture_may_not_declare_a_deviation():
    """⛔ The half of the hatch that was missing.

    The block was written so a generator could raise a question the contract could not
    answer. Once the question is answered the block must go: a closed deviation left in a
    file sends the next reader to re-decide something already decided, and it does so from
    the one place in the file that exists to be trusted.
    """
    with pytest.raises(FixtureContractError, match="contract_deviation"):
        validate_header(
            numeric(
                reference="R2",
                contract_deviation=[{"clause": "reference registry", "why": "stale"}],
            ),
            where="t",
        )


# --- the pair claim -------------------------------------------------------------------

SELF_CONSISTENCY_ORACLE = {
    "publisher": "JPL Solar System Dynamics",
    "test_artifact": {
        "identity": "testpo.440",
        "sha256": "a" * 64,
        "acquired": "2026-08-04",
        "provenance_record": {"path": "kernel/x.jsonl", "sha256": "b" * 64},
    },
    "subject_artifact": {
        "identity": "de440s.bsp",
        "data_profile": "standard@1",
        "sha256": "c" * 64,
    },
}


def self_consistent(**over) -> Header:
    oracle = json.loads(json.dumps(SELF_CONSISTENCY_ORACLE))
    oracle.update(over.pop("oracle_over", {}))
    return numeric(reference="publisher_self_consistency", oracle=oracle, **over)


def test_publisher_self_consistency_is_in_the_registry():
    validate_header(self_consistent(), where="t")


@pytest.mark.parametrize("artifact", ["test_artifact", "subject_artifact"])
def test_a_pair_claim_missing_half_its_pair_is_refused(artifact):
    """⭐ Half a pair is not a weaker claim. It is a different, unmade one."""
    with pytest.raises(FixtureContractError, match=f"oracle.{artifact}"):
        validate_header(self_consistent(oracle_over={artifact: None}), where="t")


def test_an_unnamed_publisher_is_refused():
    with pytest.raises(FixtureContractError, match="oracle.publisher"):
        validate_header(self_consistent(oracle_over={"publisher": ""}), where="t")


@pytest.mark.parametrize(
    "artifact,member",
    [
        ("test_artifact", "identity"),
        ("test_artifact", "sha256"),
        ("test_artifact", "acquired"),
        ("test_artifact", "provenance_record"),
        ("subject_artifact", "identity"),
        ("subject_artifact", "data_profile"),
        ("subject_artifact", "sha256"),
    ],
)
def test_every_member_of_each_artifact_is_required(artifact, member):
    oracle = json.loads(json.dumps(SELF_CONSISTENCY_ORACLE))
    del oracle[artifact][member]
    with pytest.raises(FixtureContractError, match=f"oracle.{artifact}.{member}"):
        validate_header(self_consistent(oracle_over=oracle), where="t")


def test_a_pair_claim_is_only_shape_checked_under_its_own_reference():
    """⚠ The shape rule belongs to the value, not to every fixture.

    A bare oracle under `R2` stays legal; the same bare oracle under the pair reference is
    refused. Asserting both sides keeps the rule from quietly becoming universal.
    """
    validate_header(numeric(reference="R2", oracle={"toolkit": "CSPICE_N0067"}), where="t")
    with pytest.raises(FixtureContractError, match="oracle.test_artifact"):
        validate_header(
            numeric(
                reference="publisher_self_consistency",
                oracle={"publisher": "JPL Solar System Dynamics"},
            ),
            where="t",
        )


def test_textual_kinds_are_r6_only():
    with pytest.raises(FixtureContractError, match="R6-only"):
        validate_header(
            Header(
                fixture_kind="textual_rule",
                reference="R4",
                generator=GEN,
                generated="2026-08-04",
                oracle={},
                locus=LOCUS,
            ),
            where="t",
        )


# --- per-kind required / forbidden fields -----------------------------------------------


TOLERANCE = {"class": "tolerance", "band": "0.01", "unit": "arcsec"}


def test_numeric_pin_with_a_compared_section_needs_a_budget_row():
    with pytest.raises(FixtureContractError, match="budget_row"):
        validate_header(numeric(budget_row=None, classification={"position": TOLERANCE}), where="t")
    with pytest.raises(FixtureContractError, match="budget_row"):
        validate_header(numeric(budget_row=None, classification={"position": {"class": "exact"}}), where="t")


def test_a_constituent_every_section_reference_only_may_name_no_budget_row():
    """⭐ Never compared on its own; whatever uses it names it by digest."""
    validate_header(numeric(budget_row=None, classification={"a": {"class": "reference_only"},
                                                            "b": {"class": "reference_only"}}), where="t")


def test_one_compared_section_makes_the_row_required_again():
    with pytest.raises(FixtureContractError, match="budget_row"):
        validate_header(numeric(budget_row=None, classification={"a": {"class": "reference_only"},
                                                                "b": TOLERANCE}), where="t")


def test_the_seventh_reference_is_in_the_registry():
    validate_header(numeric(reference="R7", budget_row=None), where="t")
    assert "R7" in REFERENCES_CONTRACT and "R8" not in REFERENCES_CONTRACT


# --- a unit per component ----------------------------------------------------------------

UNITS = {"position": {"value": ["km", "km", "km"]}}


def test_a_unit_per_component_is_written_after_the_classification_and_held_on_every_row(tmp_path):
    header = numeric(section_units=UNITS)
    validate_header(header, where="t")
    keys = list(header.as_json())
    assert keys.index("section_units") == keys.index("classification") + 1
    row = {"section": "position", **patterned("value", [1.0, 2.0, 3.0])}
    assert write_jsonl(tmp_path / "u.jsonl", header, [row]) == 1
    assert "section_units" not in numeric().as_json()  # ⭐ a header without it writes what it always wrote


@pytest.mark.parametrize("units, match", [
    ({}, "empty"),
    ({"velocity": {"value": ["km"]}}, "no entry in `classification`"),
    ({"position": {}}, "no value stem"),
    ({"position": {"value": []}}, "non-empty list"),
    ({"position": {"value": "km"}}, "non-empty list"),
    ({"position": {"value": ["au/day"]}}, "outside the units"),  # ⛔ the spelling a row schema uses is not a unit
    ({"position": {"value": ["kilometre"]}}, "outside the units"),
])
def test_a_unit_map_that_cannot_be_applied_is_refused(units, match):
    with pytest.raises(FixtureContractError, match=match):
        validate_header(numeric(section_units=units), where="t")


def test_a_unit_map_is_for_numeric_pins_only():
    record = Header(fixture_kind="provenance_record", reference="instrument", generator=GEN,
                    generated="2026-08-04", oracle={"implementation": "x"}, attests="a", authority={"held_by": "b"},
                    record_date="2026-08-04", section_units=UNITS)
    with pytest.raises(FixtureContractError, match="numeric pins only"):
        validate_header(record, where="t")


@pytest.mark.parametrize("row, match", [
    ({"section": "position", "v": 1.0}, "absent from the row"),
    ({"section": "position", **patterned("value", [1.0, 2.0])}, "2 components where"),
    ({"section": "position", **patterned("value", 1.0)}, "not a list of"),
])
def test_a_row_that_disagrees_with_its_unit_map_is_refused(tmp_path, row, match):
    good = {"section": "position", **patterned("value", [1.0, 2.0, 3.0])}
    for check in (check_jsonl, write_jsonl):
        with pytest.raises(FixtureContractError, match=match):
            check(tmp_path / f"{check.__name__}.jsonl", numeric(section_units=UNITS), [good, row])


def test_a_section_the_unit_map_does_not_list_is_not_held_to_it(tmp_path):
    header = numeric(classification={"position": {"class": "reference_only"}, "velocity": {"class": "reference_only"}},
                     section_units=UNITS)
    rows = [{"section": "position", **patterned("value", [1.0, 2.0, 3.0])}, {"section": "velocity", "v": 1.0}]
    assert check_jsonl(tmp_path / "v.jsonl", header, rows).rows == 2


def test_numeric_pin_may_not_carry_a_locus():
    with pytest.raises(FixtureContractError, match="locus"):
        validate_header(numeric(locus=LOCUS), where="t")


def test_worked_example_may_not_map_to_an_astronomical_budget_row():
    """⛔ A `source_reproduction` row proves nothing about modern accuracy."""
    with pytest.raises(FixtureContractError, match="budget_row"):
        validate_header(
            Header(
                fixture_kind="worked_example",
                reference="R6",
                generator=GEN,
                generated="2026-08-04",
                oracle={},
                request={},
                classification={"lagna": {"class": "exact"}},
                locus=LOCUS,
                budget_basis="source_reproduction",
                budget_row="moon-longitude",
            ),
            where="t",
        )


def test_worked_example_needs_source_reproduction_basis():
    with pytest.raises(FixtureContractError, match="budget_basis"):
        validate_header(
            Header(
                fixture_kind="worked_example",
                reference="R6",
                generator=GEN,
                generated="2026-08-04",
                oracle={},
                request={},
                classification={"lagna": {"class": "exact"}},
                locus=LOCUS,
                budget_basis="astronomical",
            ),
            where="t",
        )


def test_textual_rule_may_not_carry_a_numeric_classification():
    with pytest.raises(FixtureContractError, match="classification"):
        validate_header(
            Header(
                fixture_kind="textual_rule",
                reference="R6",
                generator=GEN,
                generated="2026-08-04",
                oracle={},
                locus=LOCUS,
                classification={"rule": {"class": "exact"}},
            ),
            where="t",
        )


def test_textual_fork_needs_two_readings():
    with pytest.raises(FixtureContractError, match="readings"):
        validate_header(
            Header(
                fixture_kind="textual_fork",
                reference="R6",
                generator=GEN,
                generated="2026-08-04",
                oracle={},
                readings=[{"locus": LOCUS}],
            ),
            where="t",
        )


def test_a_reading_with_an_incomplete_locus_is_refused():
    partial = {k: v for k, v in LOCUS.items() if k != "edition"}
    with pytest.raises(FixtureContractError, match="locus.edition"):
        validate_header(
            Header(
                fixture_kind="textual_fork",
                reference="R6",
                generator=GEN,
                generated="2026-08-04",
                oracle={},
                readings=[{"locus": LOCUS}, {"locus": partial}],
            ),
            where="t",
        )


# --- classification law ----------------------------------------------------------------


def test_tolerance_without_a_band_is_refused():
    with pytest.raises(FixtureContractError, match="band"):
        validate_header(
            numeric(classification={"position": {"class": "tolerance", "unit": "km"}}),
            where="t",
        )


def test_tolerance_without_a_unit_is_refused():
    with pytest.raises(FixtureContractError, match="unit"):
        validate_header(
            numeric(classification={"position": {"class": "tolerance", "band": 1e-9}}),
            where="t",
        )


def test_a_band_on_a_non_tolerance_class_is_refused():
    """A band next to `exact` reads as a tolerance nobody declared."""
    with pytest.raises(FixtureContractError, match="band"):
        validate_header(
            numeric(classification={"position": {"class": "exact", "band": 1e-9}}),
            where="t",
        )


# --- reserved-name discipline -----------------------------------------------------------


def test_a_reserved_name_in_a_key_is_refused():
    with pytest.raises(FixtureContractError, match="acme"):
        validate_header(numeric(summary={"acme_version": 1}), where="t", reserved=("acme",))


def test_a_reserved_name_matches_as_a_substring_of_a_key():
    """A reserved name buried inside a longer key still encodes it."""
    with pytest.raises(FixtureContractError, match="acme"):
        validate_header(numeric(summary={"legacy_acme_id": 1}), where="t", reserved=("acme",))


def test_this_repository_name_is_reserved_by_default():
    with pytest.raises(FixtureContractError, match="saakshi"):
        validate_header(numeric(summary={"saakshi_run": 1}), where="t")


def test_a_reserved_name_in_a_value_is_permitted():
    """✅ `generator.repo` MUST name this repository — a value records origin."""
    validate_header(numeric(), where="t")
    assert "Saakshi" in json.dumps(numeric().as_json())


@pytest.mark.parametrize("name", ["saakshi_states.jsonl", "acme-grid.json"])
def test_a_reserved_name_in_a_filename_is_refused(name, tmp_path):
    with pytest.raises(FixtureContractError):
        validate_filename(tmp_path / name, reserved=("saakshi", "acme"))


def test_the_default_reserved_list_is_described_honestly():
    from saakshi.fixture import describe_reserved_names, reserved_names

    assert reserved_names()  # never empty — the default always applies
    assert "reserved-name check" in describe_reserved_names()


# --- absolute paths ---------------------------------------------------------------------
#
# ⛔ Found in a shipped artifact by the working-tree scan, not by any of these tests: a
# library's own error message quoted the temporary directory the recorder was run from. The
# generator had already decided not to record that directory; the library put it in anyway.


@pytest.mark.parametrize(
    "text",
    [
        "not found in PATH 'C:\\Users\\somebody\\ephe'",
        "not found in PATH 'C:/Users/somebody/ephe'",
        "not found in PATH '/home/somebody/ephe'",
        "not found in PATH '\\\\server\\share\\ephe'",
    ],
)
def test_an_absolute_path_in_a_value_is_refused(text):
    with pytest.raises(FixtureContractError, match="absolute path"):
        validate_header(numeric(oracle={"toolkit": "x", "note": text}), where="t")


def test_an_absolute_path_in_a_row_is_refused(tmp_path):
    with pytest.raises(FixtureContractError, match="absolute path"):
        write_jsonl(
            tmp_path / "states.jsonl",
            numeric(),
            [{"section": "position", "detail": "read from /var/lib/ephe/x.se1"}],
        )


@pytest.mark.parametrize(
    "text",
    [
        # ⛔ The regression that the first draft of the rule actually had: a URL ends in a
        #    letter, a colon and a slash, so it looked exactly like a drive-absolute path
        #    and would have refused every generator that records a publisher's address.
        "https://ssd.jpl.nasa.gov/ftp/eph/planets/ascii/de440/testpo.440",
        "kernel/publisher-test-file-acquisition.jsonl",
        "swisseph.houses_ex: error",
        "2.0817e-17 au/day",
        "the library is AGPL-3.0; it is called here, never redistributed",
    ],
)
def test_what_is_not_an_absolute_path_survives_untouched(text):
    assert find_absolute_path(text) is None
    assert redact_environment(text) == text
    validate_header(numeric(oracle={"toolkit": "x", "note": text}), where="t")


def test_redaction_keeps_everything_that_made_the_message_evidence():
    """⭐ Which entry point spoke and which file it wanted are the evidence. The directory
    is the machine, and only the machine is removed."""
    said = redact_environment(
        "swisseph.rise_trans: SwissEph file 'sepl_12.se1' not found in "
        "PATH 'C:\\Users\\somebody\\Temp\\scratchpad'"
    )
    assert "swisseph.rise_trans" in said
    assert "sepl_12.se1" in said
    assert "somebody" not in said
    assert find_absolute_path(said) is None
    validate_header(numeric(oracle={"toolkit": "x", "note": said}), where="t")


def test_a_redacted_message_says_that_something_was_removed():
    """⚠ Otherwise a reader cannot tell a redaction from a library that printed nothing."""
    assert "removed" in redact_environment("in PATH '/home/somebody/ephe'")


@pytest.mark.parametrize("name", ["states.bin", "states.csv", "states.jsonl.gz"])
def test_a_non_plain_text_fixture_is_refused(name, tmp_path):
    with pytest.raises(FixtureContractError, match="plain text"):
        validate_filename(tmp_path / name)


def test_a_capitalised_key_is_refused():
    with pytest.raises(FixtureContractError, match="lower_snake_case"):
        validate_header(numeric(summary={"Rows": 1}), where="t")


# --- writing ---------------------------------------------------------------------------


def test_a_dirty_generator_cannot_be_stamped():
    dirty = Generator(repo="r", script="s", commit="c", dirty=True)
    with pytest.raises(FixtureContractError, match="dirty"):
        dirty.as_json()


def test_a_row_in_an_undeclared_section_is_refused(tmp_path):
    with pytest.raises(FixtureContractError, match="section"):
        write_jsonl(tmp_path / "s.jsonl", numeric(), [{"section": "velocity", "v": 1.0}])


def test_an_empty_fixture_is_refused_and_not_left_behind(tmp_path):
    path = tmp_path / "s.jsonl"
    with pytest.raises(FixtureContractError, match="no rows"):
        write_jsonl(path, numeric(), [])
    assert not path.exists()


def test_a_declared_section_with_no_classification_is_refused(tmp_path):
    with pytest.raises(FixtureContractError, match="classification"):
        write_jsonl(
            tmp_path / "s.jsonl",
            numeric(),
            [{"section": "position", "v": 1.0}],
            declared_sections=["position", "velocity"],
        )


def test_a_valid_fixture_round_trips(tmp_path):
    path = tmp_path / "states.jsonl"
    n = write_jsonl(
        path,
        numeric(),
        [{"section": "position", "value": 1.5, "value_bits": bits(1.5)}],
        declared_sections=["position"],
    )
    assert n == 1
    lines = path.read_text(encoding="utf-8").splitlines()
    assert json.loads(lines[0])["record"] == "header"
    assert json.loads(lines[0])["schema_version"] == "1.0.0"
    row = json.loads(lines[1])
    assert row["record"] == "row" and row["value_bits"] == "3ff8000000000000"


#: Each case is something `write_jsonl` refuses: (filename, header, rows, declared sections).
_REFUSED_WRITES = {
    "a filename that is not plain text": ("s.csv", {}, [{"section": "position"}], None),
    "a header the contract refuses": ("s.jsonl", {"summary": {"Rows": 1}}, [{"section": "position"}], None),
    "an absolute path in the header": ("s.jsonl", {"oracle": {"note": "/var/lib/ephe/x"}}, [{"section": "position"}], None),
    "a declared section with no class": ("s.jsonl", {}, [{"section": "position"}], ["position", "velocity"]),
    "a row in an undeclared section": ("s.jsonl", {}, [{"section": "velocity"}], None),
    "a row with no section": ("s.jsonl", {}, [{"v": 1.0}], None),
    "an absolute path in a later row": (
        "s.jsonl", {}, [{"section": "position"}, {"section": "position", "detail": "/var/lib/ephe/x"}], None,
    ),
    "a pattern disagreeing with its decimal": (
        "s.jsonl", {}, [{"section": "position", "value": 1.5, "value_bits": bits(2.5)}], None,
    ),
    "no rows at all": ("s.jsonl", {}, [], None),
}


@pytest.mark.parametrize("case", sorted(_REFUSED_WRITES))
def test_a_dry_run_refuses_what_the_write_refuses_with_the_same_words(case, tmp_path):
    """⛔ The dry run is the write's own law, shared — so its refusal is the write's, word for word."""
    name, over, rows, declared = _REFUSED_WRITES[case]
    path = tmp_path / name
    with pytest.raises(FixtureContractError) as wet:
        write_jsonl(path, numeric(**over), rows, declared_sections=declared)
    path.unlink(missing_ok=True)
    with pytest.raises(FixtureContractError) as dry:
        check_jsonl(path, numeric(**over), rows, declared_sections=declared)
    assert str(dry.value) == str(wet.value)
    assert not path.exists() and not any(tmp_path.iterdir()), "a dry run wrote something"


def test_a_dry_run_names_the_bytes_a_write_leaves(tmp_path):
    """⭐ Its digest and size are those of the file the write then writes."""
    import hashlib

    rows = [{"section": "position", "value": 1.5, "value_bits": bits(1.5)},
            {"section": "position", "value": -0.0, "value_bits": bits(-0.0)}]
    path = tmp_path / "states.jsonl"
    would = check_jsonl(path, numeric(), rows, declared_sections=["position"])
    assert not path.exists()
    assert write_jsonl(path, numeric(), rows, declared_sections=["position"]) == would.rows == 2
    data = path.read_bytes()
    assert (len(data), hashlib.sha256(data).hexdigest()) == (would.size, would.sha256)


def test_bits_round_trip():
    import struct

    for v in (0.0, -0.0, 1.5, -1e-300, 6.02e23):
        assert struct.unpack(">d", bytes.fromhex(bits(v)))[0] == v or (v == 0.0)


# --- a bit pattern is for a measurement, and a count is not a measurement --------------
#
# ⭐ The rule these tests pin was settled by asking what the pattern is *for*. A decimal
# approximates a double, so the pattern says which double; a count is not approximated by
# its own digits, so there is nothing for a pattern to settle. ⛔ The exemption is not
# attached to a fixture kind — a `worked_example` full of counts and a `numeric_pin`
# carrying an identifier are the same case, and the tests below say so by using both.


def _worked_example(**over) -> Header:
    base = dict(
        fixture_kind="worked_example",
        reference="R6",
        generator=GEN,
        generated="2026-08-14",
        oracle={"editions": {}},
        request={"asked": "the figures it printed"},
        classification={"printed_figures": {"class": "exact"}},
        budget_basis="source_reproduction",
        locus=LOCUS,
    )
    base.update(over)
    return Header(**base)


def test_bits_refuses_a_count():
    """⛔ Sixteen well-formed hex digits stating a measurement that was never made."""
    with pytest.raises(FixtureContractError, match="count"):
        bits(5)


def test_bits_refuses_a_flag():
    """⚠ `bool` is an `int` in Python, and a flag is not a quantity at all."""
    with pytest.raises(FixtureContractError, match="count"):
        bits(True)


def test_bits_still_takes_the_double_beside_it():
    assert bits(5.0) == "4014000000000000"


def test_an_integer_a_double_holds_exactly_is_written_bare(tmp_path):
    """⭐ The exemption itself, pinned: no pattern, and the value survives the file."""
    path = tmp_path / "counts.jsonl"
    write_jsonl(
        path,
        _worked_example(),
        [{"section": "printed_figures", "cells_read": 12, "rekha": 2**53}],
        declared_sections=["printed_figures"],
    )
    row = json.loads(path.read_text(encoding="utf-8").splitlines()[1])
    assert row["rekha"] == 2**53 and row["cells_read"] == 12
    assert not any(key.endswith("_bits") for key in row)


def test_an_integer_past_the_bound_is_refused(tmp_path):
    """⛔ The first magnitude at which the bare decimal stops being the number."""
    with pytest.raises(FixtureContractError, match="larger than"):
        write_jsonl(
            tmp_path / "counts.jsonl",
            _worked_example(),
            [{"section": "printed_figures", "hits": 2**53 + 1}],
            declared_sections=["printed_figures"],
        )


def test_the_bound_is_a_magnitude_and_catches_a_negative(tmp_path):
    with pytest.raises(FixtureContractError, match="larger than"):
        write_jsonl(
            tmp_path / "counts.jsonl",
            _worked_example(),
            [{"section": "printed_figures", "offset": -(2**53) - 1}],
            declared_sections=["printed_figures"],
        )


def test_the_bound_reaches_a_header_because_a_count_in_a_header_is_a_count():
    header = _worked_example(request={"asked": "x", "characters_searched": 2**53 + 1})
    with pytest.raises(FixtureContractError, match="larger than"):
        validate_header(header, where="t")


def test_the_bound_is_not_keyed_to_a_kind(tmp_path):
    """⭐⭐ The finding, as a test.

    Exempting the *kind* would have been the easy fix and the wrong axis: the corpus this
    repository already emits is a `numeric_pin` carrying more than a hundred thousand
    integer leaves with no pattern. The rule is about what the number **is**, so the same
    row must be judged identically under either header.
    """
    row = [{"section": "position", "hits": 2**53 + 1}]
    with pytest.raises(FixtureContractError, match="larger than"):
        write_jsonl(tmp_path / "a.jsonl", numeric(), row, declared_sections=["position"])
    with pytest.raises(FixtureContractError, match="larger than"):
        write_jsonl(
            tmp_path / "b.jsonl",
            _worked_example(classification={"position": {"class": "exact"}}),
            row,
            declared_sections=["position"],
        )


# --- a pattern is only a pattern if a reader can tell what it is the pattern OF ---------
#
# ⭐ These pin the second half of the bit-pattern rule. The first half asked *which values*
# carry a pattern; this half asks whether the patterns that ARE written can be trusted —
# and until they were added, nothing checked a scalar sibling or a parallel array at all.
# `leaves.verify_bits` reached only the flattened leaf model, which is 135 524 of the
# 244 292 pairs this repository has emitted. The other 108 768 were unguarded.


def test_a_pattern_that_names_no_value_is_refused(tmp_path):
    """⛔ It reads in the file as though the value beside it were guarded. Nothing is."""
    with pytest.raises(FixtureContractError, match="names no value"):
        write_jsonl(
            tmp_path / "a.jsonl",
            numeric(),
            [{"section": "position", "jd_ut": 1.5, "jd_utc_bits": bits(1.5)}],
            declared_sections=["position"],
        )


def test_a_pattern_that_disagrees_with_its_decimal_is_refused(tmp_path):
    """⛔ Two readers, one row, two different numbers, and no way to notice."""
    with pytest.raises(FixtureContractError, match="different numbers"):
        write_jsonl(
            tmp_path / "a.jsonl",
            numeric(),
            [{"section": "position", "value": 1.5, "value_bits": bits(1.4999999)}],
            declared_sections=["position"],
        )


def test_the_sign_of_zero_is_a_disagreement(tmp_path):
    """⭐ `-0.0 == 0.0` is true, which is exactly why the comparison goes through bits()."""
    with pytest.raises(FixtureContractError, match="different numbers"):
        write_jsonl(
            tmp_path / "a.jsonl",
            numeric(),
            [{"section": "position", "value": -0.0, "value_bits": bits(0.0)}],
            declared_sections=["position"],
        )


@pytest.mark.parametrize("bad", ["3FF8000000000000", "3ff800000000000", "zz", 1.5, None])
def test_a_malformed_pattern_is_refused(bad, tmp_path):
    """⚠ Including an uppercase one: sixteen lowercase hex digits, as bits() writes them."""
    with pytest.raises(FixtureContractError, match="not a bit pattern"):
        write_jsonl(
            tmp_path / "a.jsonl",
            numeric(),
            [{"section": "position", "value": 1.5, "value_bits": bad}],
            declared_sections=["position"],
        )


def test_a_parallel_array_of_the_wrong_length_is_refused(tmp_path):
    """⛔ A parallel array is read by index, so a gap repatterns everything after it."""
    with pytest.raises(FixtureContractError, match="parallel array is read by index"):
        write_jsonl(
            tmp_path / "a.jsonl",
            numeric(),
            [{
                "section": "position",
                "values": [1.5, 2.5, 3.5],
                "values_bits": [bits(1.5), bits(2.5)],
            }],
            declared_sections=["position"],
        )


def test_a_parallel_array_is_verified_elementwise(tmp_path):
    """⚠ The right length and a wrong element is the case a length check alone misses."""
    with pytest.raises(FixtureContractError, match="different numbers"):
        write_jsonl(
            tmp_path / "a.jsonl",
            numeric(),
            [{
                "section": "position",
                "values": [1.5, 2.5],
                "values_bits": [bits(1.5), bits(9.5)],
            }],
            declared_sections=["position"],
        )


def test_the_check_reaches_a_header_because_a_summary_quotes_patterns(tmp_path):
    """⚠ A `summary` block carries the same pairs a row does, and is written once."""
    header = numeric(summary={"worst": {"delta": 1.5, "delta_bits": bits(2.5)}})
    with pytest.raises(FixtureContractError, match="different numbers"):
        validate_header(header, where="t")


# --- the abbreviated spelling, tolerated on purpose and pinned so it cannot spread ------


def test_an_abbreviated_stem_resolves_when_it_is_unambiguous():
    """⚠ `r2_kernel_states.py` used to write `et_seconds` and name its pattern `et_bits`.

    ⭐ It was documented in that file's own `row_schema`, so it was a local choice rather
    than a defect — but it was a **second spelling of one relationship**, and it cost
    something measurable: a survey of this repository's artifacts matched only
    `<key>_bits`, counted 5 294 patterned values as bare, and put the wrong figure on the
    contract page. ⛔ A convention no code enforces drifts, and the drift is invisible
    until something counts.

    ⭐ **That generator now writes the pair through `patterned()`, and this test stays.**
    ⛔ The tolerance is not kept for a writer — it is kept for a *reader*: artifacts
    spelling it `et_bits` have already been handed over, and a resolver that refused them
    would refuse evidence nobody can regenerate a second time under the old spelling.
    """
    keys = ["et_seconds", "et_bits", "target", "values", "values_bits"]
    assert resolve_pattern_partner("et_bits", keys) == "et_seconds"
    assert resolve_pattern_partner("values_bits", keys) == "values"


def test_an_ambiguous_abbreviated_stem_resolves_to_nothing(tmp_path):
    """⛔ Two candidates is not a near miss — a reader cannot tell which was meant."""
    keys = ["et_seconds", "et_days", "et_bits"]
    assert resolve_pattern_partner("et_bits", keys) is None
    with pytest.raises(FixtureContractError, match="names no value"):
        write_jsonl(
            tmp_path / "a.jsonl",
            numeric(),
            [{"section": "position", "et_seconds": 1.5, "et_days": 2.5,
              "et_bits": bits(1.5)}],
            declared_sections=["position"],
        )


def test_prose_describing_a_pattern_is_not_verified_as_one(tmp_path):
    """⚠ A `row_schema` maps a value key AND its pattern key to prose about them.

    The pairing is still resolved — that is what keeps a documented pattern key honest —
    but there is no number to check, and demanding one would refuse every fixture that
    documents its own rows.
    """
    header = numeric(row_schema={
        "et_seconds": "TDB seconds past J2000.0",
        "et_bits": "IEEE-754 bit pattern of et_seconds",
    })
    validate_header(header, where="t")  # ⛔ must not raise


# --- the one stated exemption: a row's returned values, as patterns alone ---------------
#
# ⭐ A row may carry every value a call returned nested under `returned_values`, as bit
# patterns with no decimal beside them: the reader of that object takes it with one member and
# refuses a second. ⛔ The exemption is one key in one object, and these tests hold it there —
# anywhere else the same key without its values is refused exactly as before, and the patterns
# it lets stand alone are still checked as patterns.


def _row(**extra):
    return {"section": "position", **patterned("values", [1.5]), **extra}


def test_a_rows_returned_values_may_carry_its_patterns_alone(tmp_path):
    path = tmp_path / "a.jsonl"
    write_jsonl(
        path,
        numeric(),
        [_row(returned_values={"values_bits": [bits(1.5), bits(-0.0)]})],
        declared_sections=["position"],
    )
    row = json.loads(path.read_text(encoding="utf-8").splitlines()[1])
    assert row["returned_values"] == {"values_bits": [bits(1.5), bits(-0.0)]}


def test_the_exemption_names_one_key_in_one_object():
    """⛔ One pair of names, stated once: widening it is a change to this line and this test."""
    from saakshi import fixture as contract

    assert contract.UNPAIRED_PATTERNS == ("returned_values", "values_bits")


@pytest.mark.parametrize(
    "row",
    [
        _row(returned_values={"values_bits": [bits(1.5)], "jd_bits": bits(2.5)}),
        {"section": "position", "values_bits": [bits(1.5)]},
        _row(state_read_back={"values_bits": [bits(1.5)]}),
        _row(reading={"returned_values": {"values_bits": [bits(1.5)]}}),
        _row(readings=[{"returned_values": {"values_bits": [bits(1.5)]}}]),
    ],
    ids=[
        "another pattern key beside it in the same object",
        "the same key at the row's top level",
        "the same key in another object of the row",
        "the object one level deeper",
        "the object inside a list",
    ],
)
def test_anywhere_else_a_pattern_without_its_values_is_still_refused(row, tmp_path):
    with pytest.raises(FixtureContractError, match="names no value"):
        write_jsonl(tmp_path / "a.jsonl", numeric(), [row], declared_sections=["position"])


def test_the_exemption_does_not_reach_a_header():
    header = numeric(summary={"returned_values": {"values_bits": [bits(1.5)]}})
    with pytest.raises(FixtureContractError, match="names no value"):
        validate_header(header, where="t")


@pytest.mark.parametrize(
    "bad",
    [["3FF8000000000000"], ["zz"], [bits(1.5), 1.5], [None], [], bits(1.5), None],
)
def test_the_patterns_it_lets_stand_alone_are_still_checked_as_patterns(bad, tmp_path):
    with pytest.raises(FixtureContractError, match="not a bit pattern|a list of bit patterns"):
        write_jsonl(
            tmp_path / "a.jsonl",
            numeric(),
            [_row(returned_values={"values_bits": bad})],
            declared_sections=["position"],
        )


def test_beside_its_values_the_key_is_paired_as_anywhere_else(tmp_path):
    """⚠ The exemption waives a partner that is absent; a partner that is present is checked."""
    with pytest.raises(FixtureContractError, match="different numbers"):
        write_jsonl(
            tmp_path / "a.jsonl",
            numeric(),
            [_row(returned_values={"values": [1.5], "values_bits": [bits(2.5)]})],
            declared_sections=["position"],
        )


# --- the pair has one spelling now ------------------------------------------------------


def test_patterned_writes_the_pair(tmp_path):
    assert patterned("jd_ut", 1.5) == {"jd_ut": 1.5, "jd_ut_bits": bits(1.5)}


def test_patterned_writes_the_parallel_array_form():
    assert patterned("values", [1.5, 2.5]) == {
        "values": [1.5, 2.5],
        "values_bits": [bits(1.5), bits(2.5)],
    }


def test_patterned_refuses_a_count():
    """⛔ The same refusal as bits(), at the other place the mistake gets made."""
    with pytest.raises(FixtureContractError, match="count"):
        patterned("cells_read", 12)
    with pytest.raises(FixtureContractError, match="count"):
        patterned("hits", [1, 2])


def test_a_row_built_by_patterned_survives_the_writer(tmp_path):
    """⭐ The mechanism and the check agree: what patterned() writes, the walk accepts."""
    path = tmp_path / "a.jsonl"
    write_jsonl(
        path,
        numeric(),
        [{"section": "position", **patterned("jd_ut", 1.5),
          **patterned("values", [2.5, -0.0])}],
        declared_sections=["position"],
    )
    row = json.loads(path.read_text(encoding="utf-8").splitlines()[1])
    assert row["jd_ut_bits"] == bits(1.5)
    assert row["values_bits"] == [bits(2.5), bits(-0.0)]
