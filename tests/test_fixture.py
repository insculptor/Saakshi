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
    FixtureContractError,
    Generator,
    Header,
    bits,
    find_absolute_path,
    redact_environment,
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
        validate_header(numeric(reference="R7"), where="t")


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


def test_numeric_pin_needs_a_budget_row():
    with pytest.raises(FixtureContractError, match="budget_row"):
        validate_header(numeric(budget_row=None), where="t")


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
