"""The locus law and the resolution discipline, as refusals.

⭐ Like the contract's own tests, almost everything here asserts that something is **rejected**.
R6's whole difficulty is that a citation is easy to write and hard to check, so the tests
that matter are the ones proving an uncheckable citation cannot be written down.

⛔ **Nothing here touches the network or a cached copy.** An edition is built from a literal
string, so every rule below is exercised without any text having been acquired — which is
what lets continuous integration run them.
"""

from __future__ import annotations

import pytest

from saakshi.fixture import (
    INTERPRETATION_STATUS,
    SOURCE_KINDS,
    FixtureContractError,
    Generator,
    Header,
    validate_header,
)
from saakshi.texts import DEVANAGARI, passage_fidelity, script_presence
from saakshi.textual import (
    REFUSAL_REASONS,
    SIGNS,
    AbsenceSearch,
    Edition,
    Locus,
    Refusal,
    Rendering,
    TableReading,
    TextualError,
    Witness,
    agreement,
    as_by_sign,
    collect_occurrences,
    digest,
    measured_extent,
    normalise,
    read_integer_cells,
    read_integer_digits,
    reduce_by_trine_minimum,
    refusal_summary,
    region,
    resolve,
    rotate_to,
    source_oracle,
)

GEN = Generator(repo="github.com/insculptor/Saakshi", script="generators/x.py", commit="0" * 40)

BODY = (
    "Chapter one. The first rule is stated here, once and only once.\n"
    "A row of figures: alpha 5 3 2 4 3 4 6 5 2 3 6 5 omega\n"
    "A shorter row: beta 1 2 4 4 1 3 1 2 2 2 gamma\n"
    "A run of digits: delta 30 001 1410041 epsilon\n"
    "a phrase repeated twice appears here, and a phrase repeated twice appears again.\n"
    "End of First Pada. End of Second Pada.\n"
)


def edition(text: str = BODY, *, kind: str = "translation") -> Edition:
    return Edition(
        key="test_copy",
        identity="a copy built for this test",
        language="en",
        witness=Witness(
            address="https://example.invalid/copy.txt",
            retrieved="2026-08-14",
            http_status=200,
            copy_sha256="0" * 64,
            copy_bytes=len(text),
        ),
        rendering=Rendering(
            kind="transcription",
            produced_by="this test",
            sha256=digest(text),
            characters=len(text),
        ),
        extent={"describes": "the whole of it", "complete": True},
        text=text,
    )


LOCUS = {
    "source_kind": "translation",
    "language": "en",
    "edition": "test_copy",
    "locus": "chapter one",
    "interpretation_status": "restated",
}


def textual_rule(**over) -> Header:
    base = dict(
        fixture_kind="textual_rule",
        reference="R6",
        generator=GEN,
        generated="2026-08-14",
        oracle={"editions": {}},
        locus=dict(LOCUS),
    )
    base.update(over)
    return Header(**base)


# --- the locus law: a negative case for every field it requires ------------------------


@pytest.mark.parametrize(
    "field", ["source_kind", "language", "edition", "locus", "interpretation_status"]
)
def test_a_locus_missing_any_required_field_is_refused(field):
    """⛔ All five, one test each. A locus is complete or it is not a locus."""
    incomplete = dict(LOCUS)
    del incomplete[field]
    with pytest.raises(FixtureContractError, match=f"locus.{field}"):
        validate_header(textual_rule(locus=incomplete), where="t")


@pytest.mark.parametrize(
    "field", ["source_kind", "language", "edition", "locus", "interpretation_status"]
)
def test_a_locus_field_present_but_empty_is_refused(field):
    """⚠ Present-and-empty is the shape a template leaves behind, and it is not presence."""
    blank = dict(LOCUS)
    blank[field] = ""
    with pytest.raises(FixtureContractError, match=f"locus.{field}"):
        validate_header(textual_rule(locus=blank), where="t")


def test_an_undeclared_source_kind_is_refused():
    """⛔ The hole R6 was the first to stand on: presence was checked and the value was not."""
    with pytest.raises(FixtureContractError, match="source_kind"):
        validate_header(textual_rule(locus={**LOCUS, "source_kind": "book"}), where="t")


def test_an_undeclared_interpretation_status_is_refused():
    """⭐ The value this repository's own test file used to carry, and which used to pass."""
    with pytest.raises(FixtureContractError, match="interpretation_status"):
        validate_header(textual_rule(locus={**LOCUS, "interpretation_status": "settled"}), where="t")


@pytest.mark.parametrize("language", ["English", "english", "Eng.", "en-GB", "e", "abcd"])
def test_a_language_that_is_not_a_code_is_refused(language):
    """⚠ A shape, not a registry — but three spellings of one language is three groups."""
    with pytest.raises(FixtureContractError, match="language"):
        validate_header(textual_rule(locus={**LOCUS, "language": language}), where="t")


def test_every_declared_source_kind_and_status_is_accepted():
    """⛔ A registry that refuses one of its own members is worse than no registry."""
    for kind in SOURCE_KINDS:
        for status in INTERPRETATION_STATUS:
            validate_header(
                textual_rule(
                    locus={**LOCUS, "source_kind": kind, "interpretation_status": status}
                ),
                where="t",
            )


# --- the per-kind law the three R6 kinds carry -----------------------------------------


@pytest.mark.parametrize("kind", ["textual_rule", "textual_fork", "worked_example"])
def test_an_r6_only_kind_refuses_another_reference(kind):
    header = textual_rule(fixture_kind=kind, reference="R3")
    with pytest.raises(FixtureContractError, match="R6-only"):
        validate_header(header, where="t")


@pytest.mark.parametrize("field,value", [("classification", {"a": {"class": "exact"}}), ("budget_row", "K-b")])
def test_a_rule_may_carry_neither_a_classification_nor_a_band(field, value):
    """⛔ A rule is not a number and has no band."""
    with pytest.raises(FixtureContractError, match=field):
        validate_header(textual_rule(**{field: value}), where="t")


def test_a_fork_with_one_reading_is_refused():
    header = textual_rule(
        fixture_kind="textual_fork", locus=None, readings=[{"locus": dict(LOCUS)}]
    )
    with pytest.raises(FixtureContractError, match="readings"):
        validate_header(header, where="t")


def test_each_reading_of_a_fork_needs_its_own_complete_locus():
    """⛔ Half a located fork is a fork with an unlocatable half."""
    incomplete = {k: v for k, v in LOCUS.items() if k != "edition"}
    header = textual_rule(
        fixture_kind="textual_fork",
        locus=None,
        readings=[{"locus": dict(LOCUS)}, {"locus": incomplete}],
    )
    with pytest.raises(FixtureContractError, match=r"readings\[1\]"):
        validate_header(header, where="t")


def test_a_worked_example_may_not_carry_a_budget_row():
    """⛔ A number a text resolves proves reproduction, never modern accuracy."""
    header = textual_rule(
        fixture_kind="worked_example",
        classification={"figures": {"class": "exact"}},
        budget_basis="source_reproduction",
        request={"asked": "the figures"},
        budget_row="K-b",
    )
    with pytest.raises(FixtureContractError, match="budget_row"):
        validate_header(header, where="t")


def test_a_worked_example_must_declare_source_reproduction():
    header = textual_rule(
        fixture_kind="worked_example",
        classification={"figures": {"class": "exact"}},
        budget_basis="modern_comparison",
        request={"asked": "the figures"},
    )
    with pytest.raises(FixtureContractError, match="budget_basis"):
        validate_header(header, where="t")


# --- resolution -------------------------------------------------------------------------


def test_a_fragment_found_once_resolves():
    assert resolve(edition(), "The first rule is stated here").resolved


def test_a_fragment_found_twice_does_not_resolve():
    """⛔ The ordinary case, not an exotic one: a contents page restates its chapter."""
    found = resolve(edition(), "a phrase repeated twice appears")
    assert found.occurrences == 2
    assert not found.resolved


def test_a_fragment_that_is_absent_does_not_resolve():
    assert resolve(edition(), "a sentence nobody printed").occurrences == 0


def test_an_empty_fragment_is_refused():
    with pytest.raises(TextualError, match="resolves everywhere"):
        resolve(edition(), "   ")


def test_resolution_survives_a_line_break_inside_the_quotation():
    """⚠ The one normalisation there is, and the reason a quotation may be broken anywhere."""
    assert resolve(edition(), "The first rule\n   is stated\there").resolved


def test_resolution_does_not_survive_a_changed_digit():
    """⛔ Nothing but whitespace is normalised, so a repaired quotation still fails."""
    assert not resolve(edition(), "alpha 5 3 2 4 3 4 6 5 2 3 6 6").resolved


def test_a_locus_whose_fragment_did_not_resolve_cannot_be_written_down():
    unresolved = Locus(
        source_kind="translation",
        edition=edition(),
        locus="chapter one",
        interpretation_status="restated",
        fragment="a sentence nobody printed",
    )
    with pytest.raises(TextualError, match="occurs 0 time"):
        unresolved.as_json()


def test_a_locus_whose_fragment_is_ambiguous_cannot_be_written_down():
    ambiguous = Locus(
        source_kind="translation",
        edition=edition(),
        locus="chapter one",
        interpretation_status="restated",
        fragment="a phrase repeated twice appears",
    )
    with pytest.raises(TextualError, match="occurs 2 time"):
        ambiguous.as_json()


def test_a_written_locus_names_its_edition_by_key_not_by_block():
    """⭐ Written once in the oracle, referenced by key on every row that cites it."""
    written = Locus(
        source_kind="translation",
        edition=edition(),
        locus="chapter one",
        interpretation_status="restated",
        fragment="The first rule is stated here",
    ).as_json()
    assert written["edition"] == "test_copy"
    assert written["resolution"]["resolved"]


def test_an_undeclared_source_kind_is_refused_at_the_locus_too():
    with pytest.raises(TextualError, match="source kind"):
        Locus(
            source_kind="book",
            edition=edition(),
            locus="chapter one",
            interpretation_status="restated",
            fragment="The first rule is stated here",
        )


# --- the copy: rendering, extent -----------------------------------------------------


def test_an_edition_whose_rendering_digest_is_wrong_is_refused():
    """⛔ Otherwise a locus resolves in one document and is attributed to another."""
    with pytest.raises(TextualError, match="digest"):
        Edition(
            key="k",
            identity="i",
            language="en",
            witness=Witness("a", "2026-08-14", 200, "0" * 64, 1),
            rendering=Rendering("transcription", "t", "f" * 64, 1),
            extent={},
            text=BODY,
        )


def test_an_undeclared_rendering_kind_is_refused():
    with pytest.raises(TextualError, match="rendering kind"):
        Edition(
            key="k",
            identity="i",
            language="en",
            witness=Witness("a", "2026-08-14", 200, "0" * 64, 1),
            rendering=Rendering("photocopy", "t", digest(BODY), len(BODY)),
            extent={},
            text=BODY,
        )


def test_an_extent_is_measured_from_the_copys_own_markers():
    extent = measured_extent(
        BODY,
        markers=[("pada 1", ("End of First Pada",)), ("pada 2", ("End of Second Pada",))],
        describes="two divisions",
        beyond="nothing",
    )
    assert extent["complete"]
    assert extent["divisions_found"] == ["pada 1", "pada 2"]


def test_an_extent_reports_a_division_it_could_not_find():
    extent = measured_extent(
        BODY,
        markers=[("pada 1", ("End of First Pada",)), ("pada 3", ("End of Third Pada",))],
        describes="two divisions",
        beyond="nothing",
    )
    assert not extent["complete"]
    assert extent["divisions_not_found"] == ["pada 3"]


def test_a_division_printed_in_either_of_two_spellings_is_found():
    """⚠ Alternates are not slack: an extent that under-reports is as wrong as one that over-reports."""
    extent = measured_extent(
        BODY,
        markers=[("pada 1", ("End of the First Pada", "End of First Pada"))],
        describes="one division",
        beyond="nothing",
    )
    assert extent["complete"]


# --- tables ---------------------------------------------------------------------------


def test_a_region_delimited_by_an_ambiguous_landmark_is_refused():
    with pytest.raises(TextualError, match="does not delimit a region"):
        region(
            edition(),
            label="t",
            after="a phrase repeated twice appears",
            before="End of First Pada",
        )


def test_a_full_row_is_legible():
    reading = read_integer_cells(edition(), label="t", after="alpha", before="omega", cells=12)
    assert reading.legible
    assert reading.values == (5, 3, 2, 4, 3, 4, 6, 5, 2, 3, 6, 5)
    assert reading.as_json()["values"] == list(reading.values)


def test_a_short_row_is_not_legible_and_emits_no_values():
    """⛔ The cells that survive are still digits in a plausible order."""
    reading = read_integer_cells(edition(), label="t", after="beta", before="gamma", cells=12)
    assert not reading.legible
    assert len(reading.values) == 10
    assert reading.as_json()["values"] is None


def test_a_run_of_digits_is_read_digit_by_digit():
    reading = read_integer_digits(edition(), label="t", after="delta", before="epsilon", cells=12)
    assert reading.legible
    assert reading.values == (3, 0, 0, 0, 1, 1, 4, 1, 0, 0, 4, 1)


def test_two_witnesses_that_agree_are_reported_as_agreeing():
    check = agreement("t", [1, 2, 3], [1, 2, 3], first_is="a", second_is="b")
    assert check["agrees"] and check["cells_agreeing"] == 3


def test_a_single_disagreeing_cell_is_located():
    check = agreement("t", [1, 2, 3], [1, 9, 3], first_is="a", second_is="b")
    assert not check["agrees"]
    assert check["disagreements"] == [{"index": 1, "first": 2, "second": 9}]


def test_witnesses_of_different_lengths_never_agree():
    """⛔ Zipping two rows of unequal length silently compares the shorter of them."""
    check = agreement("t", [1, 2, 3], [1, 2], first_is="a", second_is="b")
    assert not check["agrees"] and not check["lengths_match"]


# --- the arithmetic a worked example licenses ------------------------------------------


def test_a_row_that_is_not_twelve_cells_is_refused():
    with pytest.raises(TextualError, match="12 cells"):
        reduce_by_trine_minimum([1, 2, 3])


def test_the_reduction_subtracts_each_groups_smallest_from_all_three():
    row = [0] * 12
    for sign, value in {"aries": 4, "leo": 5, "sagittarius": 5}.items():
        row[SIGNS.index(sign)] = value
    out = as_by_sign(reduce_by_trine_minimum(row))
    assert (out["aries"], out["leo"], out["sagittarius"]) == (0, 1, 1)


def test_the_reduction_is_not_the_rule_the_chapter_states_read_literally():
    """⭐ The fork, pinned as arithmetic rather than as a sentence.

    The chapter's rule sentence, read literally, deducts a member's figure from the *sum* of
    its group's three. ⛔ On the chapter's own first group that is larger than any figure in
    it, which is the whole reason the example is a second reading rather than an illustration
    of the first.
    """
    capricorn, taurus, virgo = 5, 3, 2
    by_the_example = min(capricorn, taurus, virgo)
    from_the_total = capricorn + taurus + virgo - virgo
    assert by_the_example == 2
    assert from_the_total == 8
    assert from_the_total > max(capricorn, taurus, virgo)


def test_a_row_printed_from_another_sign_is_re_keyed():
    """⚠ Getting this wrong is invisible: the figures are all still there, in an order that looks deliberate."""
    printed_from_capricorn = list(range(12))
    out = as_by_sign(rotate_to(printed_from_capricorn, first_sign="capricorn"))
    assert out["capricorn"] == 0 and out["aquarius"] == 1 and out["aries"] == 3


# --- refusals and absence ---------------------------------------------------------------


def test_an_undeclared_refusal_reason_is_refused():
    with pytest.raises(TextualError, match="refusal reason"):
        Refusal(subject="s", reason="because", detail="d", what_would_close_it="w")


def test_refusals_are_summarised_by_name_and_not_only_counted():
    """⚠ A count with no names is a silent cap on what a reader can check."""
    summary = refusal_summary(
        [
            Refusal("the first thing", "no_edition_in_hand", "d", "w"),
            Refusal("the second thing", "no_edition_in_hand", "d", "w"),
        ]
    )
    assert summary["refused"] == 2
    assert summary["subjects_by_reason"]["no_edition_in_hand"] == [
        "the first thing",
        "the second thing",
    ]


def test_an_absence_publishes_a_count_for_every_spelling_it_searched():
    """⛔ A scan is only as wide as its alphabet."""
    search = AbsenceSearch(
        claim="that the copy states something it does not",
        alphabet=("first rule", "second rule", "shorter row"),
        edition=edition(),
        occurrences=[],
        what_the_hits_do_say=("nothing to the point",),
    )
    row = search.as_row()
    assert [entry["spelling"] for entry in row["hits_by_spelling"]] == list(search.alphabet)
    assert search.hits == {"first rule": 1, "second rule": 0, "shorter row": 1}


def test_an_absence_row_keys_are_identifiers_and_never_the_search_terms():
    """⛔ A JSON key is a permanent identifier; a search term is data that will change."""
    search = AbsenceSearch(
        claim="c",
        alphabet=("First Rule",),
        edition=edition(),
        occurrences=[],
        what_the_hits_do_say=(),
    )
    assert "First Rule" not in str(list(search.as_row()["hits_by_spelling"][0].keys()))


def test_every_occurrence_is_collected_and_never_a_sample():
    hits = collect_occurrences(edition(), "a phrase repeated twice appears")
    assert len(hits) == 2


def test_an_absence_carries_the_measured_extent_it_holds_over():
    row = AbsenceSearch(
        claim="c", alphabet=("nothing",), edition=edition(), occurrences=[], what_the_hits_do_say=()
    ).as_row()
    assert row["established_over"] == edition().extent


# --- the oracle block --------------------------------------------------------------------


def test_the_oracle_names_every_edition_and_counts_what_was_refused():
    oracle = source_oracle([edition()], resolved=3, refused=2)
    assert set(oracle["editions"]) == {"test_copy"}
    assert oracle["claims_resolved"] == 3 and oracle["claims_refused"] == 2
    assert "licence" in oracle


def test_normalise_collapses_whitespace_and_nothing_else():
    assert normalise("  a \n\t b  ") == "a b"
    assert normalise("a-b") == "a-b"


def test_a_table_reading_states_the_count_it_was_checked_against():
    reading = TableReading(label="t", expected_cells=12, values=(1, 2))
    assert reading.as_json()["cells_expected"] == 12
    assert reading.as_json()["cells_read"] == 2


# --- presence is not fidelity -------------------------------------------------------------
#
# ⭐ The copy that forced this apart carries a script in quantity and still cannot be cited
#    for the one passage a claim rested on. ⛔ A repository owning only a presence check
#    would have read its `True` as licence, so both directions are pinned here.


def _fidelity_copy(body: str) -> Edition:
    return edition(body)


def test_a_passage_is_faithful_when_the_copy_agrees_with_itself():
    body = "the sutra reads alpha beta gamma here. the commentary says it contains beta."
    result = passage_fidelity(
        _fidelity_copy(body),
        passage="alpha beta gamma",
        quoted_word="beta",
        stated_at="the commentary",
    )
    assert result["faithful"] is True
    assert result["occurrences_of_that_passage"] == 1
    assert result["the_rendered_passage_contains_it"] is True


def test_a_passage_is_not_faithful_when_it_lacks_the_word_the_copy_says_is_in_it():
    # the rendering dropped 'beta' from the passage; the copy's own prose still names it
    body = "the sutra reads alpha gxmma here. the commentary says it contains beta."
    result = passage_fidelity(
        _fidelity_copy(body),
        passage="alpha gxmma",
        quoted_word="beta",
        stated_at="the commentary",
    )
    assert result["faithful"] is False
    assert result["the_rendered_passage_contains_it"] is False


def test_a_passage_that_does_not_resolve_is_not_faithful_either():
    # ⛔ a passage occurring twice locates nothing, so it cannot be cited even if the word is
    #    present in it — fidelity must not accept what resolution refuses
    body = "alpha beta gamma and again alpha beta gamma."
    result = passage_fidelity(
        _fidelity_copy(body),
        passage="alpha beta gamma",
        quoted_word="beta",
        stated_at="the commentary",
    )
    assert result["occurrences_of_that_passage"] == 2
    assert result["faithful"] is False


def test_a_passage_absent_from_the_copy_is_not_faithful():
    result = passage_fidelity(
        _fidelity_copy("nothing of the sort appears here."),
        passage="alpha beta gamma",
        quoted_word="beta",
        stated_at="the commentary",
    )
    assert result["occurrences_of_that_passage"] == 0
    assert result["faithful"] is False


def test_presence_and_fidelity_are_different_questions_about_one_copy():
    """⭐ The measured case, in miniature: the script is there and the passage is still wrong.

    ⛔ This is the pairing the refusal rests on. A copy can carry a script in quantity and
    have lost the very words a locus into it would quote.
    """
    body = "सूत्र: आत्साधिकः सप्तानासष्टानां वा । टीका में 'अष्टानाम्' शब्द है ।"
    copy = _fidelity_copy(body)
    presence = script_presence(copy, first=DEVANAGARI[0], last=DEVANAGARI[1])
    fidelity = passage_fidelity(
        copy,
        passage="आत्साधिकः सप्तानासष्टानां वा",
        quoted_word="अष्टानाम्",
        stated_at="the commentary",
    )
    assert presence["present"] is True
    assert presence["code_points_in_range"] > 0
    assert fidelity["faithful"] is False


def test_the_two_new_refusal_reasons_are_declared():
    # ⛔ an undeclared reason reports a pass and carries no meaning to a reader grouping on it
    assert "script_present_but_passage_not_faithful" in REFUSAL_REASONS
    assert "extent_of_the_copy_is_a_lower_bound" in REFUSAL_REASONS
