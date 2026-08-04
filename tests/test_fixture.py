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
    validate_filename,
    validate_header,
    write_jsonl,
)

GEN = Generator(repo="github.com/insculptor/Saakshi", script="generators/x.py", commit="0" * 40)

LOCUS = {
    "source_kind": "primary_text",
    "language": "sa",
    "edition": {"publisher": "P", "year": 1900},
    "locus": "ch. 1 v. 2",
    "interpretation_status": "settled",
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
