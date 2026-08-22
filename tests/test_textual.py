"""The locus law and the resolution discipline, as refusals.

⭐ Like the contract's own tests, almost everything here asserts that something is **rejected**.
R6's whole difficulty is that a citation is easy to write and hard to check, so the tests
that matter are the ones proving an uncheckable citation cannot be written down.

⛔ **Nothing here touches the network or a cached copy.** An edition is built from a literal
string, so every rule below is exercised without any text having been acquired — which is
what lets continuous integration run them.
"""

from __future__ import annotations

import inspect
from collections import Counter

import pytest

import saakshi.textual

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
    COMMONEST_WORDS,
    GREATEST_FLANK_A_CERTIFIED_READING_HAS_NEEDED,
    HOW_THE_FLANK_BOUNDS_WERE_MEASURED,
    LEAST_FLANK_AT_WHICH_A_LOCAL_PRESENCE_IS_FREE_IN_A_RENDERING_OF_NOISE,
    LOCAL_PRESENCE_MEASURED_AT_FLANKS,
    THE_LANGUAGE_A_LOCUS_DECLARES,
    declared_words_the_passage_carries,
    least_flank_at_which_a_passage_carries_a_declared_word,
    least_flank_at_which_every_position_carries_a_declared_word,
    refuse_a_rendering_that_goes_too_far_without_its_declared_language,
    require_the_passage_to_carry_the_language_the_locus_declares,
    the_passage_a_locus_resolves_in,
    whether_a_local_presence_separates,
    word_list_a_locus_calls_for,
    GREATEST_EXTENT_AT_WHICH_A_WINDOW_OF_A_REFUSED_COPY_HAS_CLEARED,
    GREATEST_SHARE_A_WRONG_SCRIPT_READING_REACHES,
    LEAST_LENGTH_A_DECLARED_WORD_CARRIES,
    LEAST_COPIES_THIS_FLOOR_MISCLASSIFIES_AT_ANY_VALUE,
    LEAST_EXTENT_A_REFUSAL_DISCRIMINATES_AT,
    LEAST_RECURRENCE,
    LEAST_SHARE_A_COPY_CARRYING_ITS_OWN_LANGUAGE_REACHES,
    STATISTICS_MEASURED_AGAINST_THIS_FLOOR,
    RECURRENCE_MEASURED_AT,
    REFUSAL_REASONS,
    SIGNS,
    AbsenceAcrossReadings,
    AbsenceSearch,
    Alignment,
    Edition,
    IndependentHandAttestation,
    MarkerAlphabet,
    Fork,
    Locus,
    NamedInAnotherCopy,
    PassageAbsence,
    Refusal,
    Rendering,
    SecondHand,
    SelfContradiction,
    TableReading,
    TextualError,
    Witness,
    agreement,
    alphabet_contamination,
    as_by_sign,
    collect_occurrences,
    digest,
    how_a_per_language_floor_would_be_fitted,
    least_error_a_single_value_can_reach,
    measured_extent,
    normalise,
    one_per_cent_grid,
    read_integer_cells,
    reading_disagreement,
    discrimination_of_resolving_once,
    read_integer_digits,
    blocks_that_carry_declared_words,
    blocks_this_floor_refuses,
    declared_words_of,
    declared_words_that_occur,
    words_of,
    every_window_of,
    largest_extent_at_which_a_window_clears,
    recurrence_of,
    reduce_by_trine_minimum,
    refuse_a_rendering_that_does_not_repeat,
    script_of,
    scripts_in,
    scripts_required_by,
    refusal_summary,
    region,
    resolve,
    rotate_to,
    source_oracle,
)

GEN = Generator(repo="github.com/insculptor/Saakshi", script="generators/x.py", commit="0" * 40)

#: ⛔⛔⛔ **EVERY COPY BUILT IN THIS FILE REPEATED NOTHING, AND THAT IS THE PROPERTY
#: OF THE RENDERING OF NOISE ITSELF.** A machine reading that returned noise is dangerous
#: because nothing in it recurs, so every fragment of it resolves exactly once — and the
#: fixtures these instruments were tested against had exactly that property. ⇒ No test
#: written here could have caught the defect, because the test copies WERE the defect.
#: ⭐ So a fixture standing in for a book now repeats like one. ⚠ The repeated line is NEW
#: text: repeating a line quoted elsewhere would stop that quotation resolving.
REPEATS_LIKE_A_BOOK = (
    "Printed at the foot of every page: this copy repeats itself. "
    "Printed at the foot of every page: this copy repeats itself."
)

BODY = (
    "Chapter one. The first rule is stated here, once and only once.\n"
    "A row of figures: alpha 5 3 2 4 3 4 6 5 2 3 6 5 omega\n"
    "A shorter row: beta 1 2 4 4 1 3 1 2 2 2 gamma\n"
    "A run of digits: delta 30 001 1410041 epsilon\n"
    "a phrase repeated twice appears here, and a phrase repeated twice appears again.\n"
    "End of First Pada. End of Second Pada.\n" + REPEATS_LIKE_A_BOOK
)

#: ⛔ Words the test copy is shown to contain, so that a zero measured in it means something.
#: ⚠ Occurs exactly once in `BODY`, which is what an absence's positive control must do.
CONTROL = "The first rule is stated here, once and only once."


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
        positive_control=CONTROL,
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
        positive_control=CONTROL,
    )
    assert "First Rule" not in str(list(search.as_row()["hits_by_spelling"][0].keys()))


def test_every_occurrence_is_collected_and_never_a_sample():
    hits = collect_occurrences(edition(), "a phrase repeated twice appears")
    assert len(hits) == 2


def test_an_absence_carries_the_measured_extent_it_holds_over():
    row = AbsenceSearch(
        claim="c",
        alphabet=("nothing",),
        edition=edition(),
        occurrences=[],
        what_the_hits_do_say=(),
        positive_control=CONTROL,
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


# --- a fork is a presence AND an absence, and only the presence ever gets measured -----
#
# ⛔⛔ These exist because the unarmed version failed in production. A fork was published
# holding that one copy did not state a rule where another did; the rule stood two paragraphs
# below the passage the reading was formed from, in the copy said to be silent. ⭐ Every test
# below is a defect that reading would have had to survive.

#: ⚠ One rule, stated in TWO carrying forms — as arithmetic in one passage and as description
#: in another. That is the shape that defeated the recorder, so it is the shape tested.
TWO_FORM_BODY = (
    "Front matter mentioning none of it.\n"
    "SUTRA ONE MARKER. The head of the series is whichever holds the highest degrees. "
    "The node must also be considered, taking the remainder after subtracting from thirty.\n"
    "SUTRA TWO MARKER. A different matter altogether, with no bearing on the node.\n"
    "SUTRA THREE MARKER. For the node the reverse is understood.\n"
    "SUTRA FOUR MARKER. Closing matter.\n" + REPEATS_LIKE_A_BOOK
)

#: ⭐ Read off the copy, and off BOTH carrying forms of the rule.
BOTH_FORMS = ("reverse", "subtracting from thirty")


def other_edition(text: str = TWO_FORM_BODY) -> Edition:
    ed = edition(text)
    return Edition(
        key="second_copy",
        identity=ed.identity,
        language=ed.language,
        witness=ed.witness,
        rendering=Rendering(
            kind="transcription",
            produced_by="this test",
            sha256=digest(text),
            characters=len(text),
        ),
        extent=ed.extent,
        text=text,
    )


def passage_absence(**over) -> PassageAbsence:
    base = dict(
        claim="that this copy does not state the rule where the series is founded",
        edition=other_edition(),
        passage_label="sutra one",
        after="SUTRA ONE MARKER.",
        before="SUTRA TWO MARKER.",
        alphabet=BOTH_FORMS,
        alphabet_read_from="read off this copy's own statements of the rule",
    )
    base.update(over)
    return PassageAbsence(**base)


def stating_locus() -> Locus:
    return Locus(
        source_kind="commentary",
        edition=edition(),
        locus="chapter one",
        interpretation_status="restated",
        fragment="The first rule is stated here, once and only once.",
    )


def fork(**over) -> Fork:
    base = dict(
        rule="the_node_is_ranked_by_reversed_degrees",
        subject="whether the rule reaches the ranking of the series",
        stated_by=stating_locus(),
        absent_from=passage_absence(),
    )
    base.update(over)
    return Fork(**base)


def test_the_null_control_a_genuinely_silent_passage_yields_a_fork():
    """⭐ The accepting case, so the refusals below are known not to refuse everything."""
    silent = passage_absence(
        passage_label="sutra two", after="SUTRA TWO MARKER.", before="SUTRA THREE MARKER."
    )
    assert silent.hits == {"reverse": 0, "subtracting from thirty": 0}
    assert silent.established
    row = fork(absent_from=silent).as_row()
    assert row["finding"] == "fork"
    assert row["and_measured_absent_from"]["established"] is True


def test_the_published_defect_a_fork_whose_passage_states_the_rule_is_refused():
    """⛔⛔ The exact shape of the withdrawn finding: the 'silent' copy is not silent."""
    refuted = passage_absence()
    assert refuted.hits["subtracting from thirty"] == 1
    assert not refuted.established
    with pytest.raises(TextualError) as excinfo:
        fork(absent_from=refuted)
    # ⭐ The refusal NAMES the word that refutes it — a reader must not have to go looking.
    assert "subtracting from thirty" in str(excinfo.value)


def test_the_obvious_alphabet_alone_would_have_confirmed_the_error():
    """⚠⚠ THE UNCOMFORTABLE CONTROL, AND THE REASON THE ALPHABET RULE IS NOT ENOUGH.

    ⭐⭐⭐ Searching the passage for the rule's *ordinary word* finds nothing, because the
    copy states the rule there in its other carrying form. The absence is then `established`
    and the fork is accepted — and it is **wrong**. ⛔ This instrument does not escape its
    alphabet, and a test that pretended otherwise would be the defect one level up. What the
    row carries instead is the alphabet itself, so a reader can see what was not looked for.
    """
    one_form = passage_absence(alphabet=("reverse",))
    assert one_form.hits == {"reverse": 0}
    assert one_form.established  # ⛔ established, and false
    assert fork(absent_from=one_form).as_row()["finding"] == "fork"


def test_a_spelling_absent_from_the_whole_copy_is_refused_as_guessed():
    """⛔ A zero from a guessed spelling is indistinguishable from a passage's silence."""
    with pytest.raises(TextualError) as excinfo:
        passage_absence(alphabet=("reverse", "widdershins"))
    assert "widdershins" in str(excinfo.value)


def test_an_absence_with_no_alphabet_searched_nothing():
    with pytest.raises(TextualError):
        passage_absence(alphabet=())


def test_a_passage_bounded_by_an_ambiguous_landmark_is_refused():
    """⛔ Inherited from `region`, and it is what makes the bound a measurement."""
    doubled = TWO_FORM_BODY + "SUTRA ONE MARKER. printed a second time.\n"
    with pytest.raises(TextualError):
        passage_absence(edition=other_edition(doubled)).hits


def test_a_fork_naming_one_copy_on_both_sides_is_refused():
    """⛔ A copy disagreeing with itself is a different finding and is recorded as one."""
    same = passage_absence(edition=edition(TWO_FORM_BODY))
    with pytest.raises(TextualError) as excinfo:
        fork(stated_by=stating_locus(), absent_from=same)
    assert "both sides" in str(excinfo.value)


def test_a_passage_absence_row_declares_its_bound_and_its_alphabet():
    row = passage_absence(
        passage_label="sutra two", after="SUTRA TWO MARKER.", before="SUTRA THREE MARKER."
    ).as_row()
    assert row["spellings_searched"] == list(BOTH_FORMS)
    assert [h["spelling"] for h in row["hits_by_spelling"]] == list(BOTH_FORMS)
    assert "lower bound" in row["bounded_by"]
    assert "alphabet" in row["limit"]


# --- two copies number AND order the sutras differently --------------------------------


def alignment(**over) -> Alignment:
    anchor_first = Locus(
        source_kind="translation", edition=edition(), locus="anchor",
        interpretation_status="restated",
        fragment="The first rule is stated here, once and only once.",
    )
    anchor_second = Locus(
        source_kind="translation", edition=other_edition(), locus="anchor",
        interpretation_status="restated", fragment="SUTRA ONE MARKER.",
    )
    base = dict(
        label="whether two numbers name one place",
        anchor_in_first=anchor_first, anchor_first_number=48,
        anchor_in_second=anchor_second, anchor_second_number=50,
        first_number=50, second_number=52,
    )
    base.update(over)
    return Alignment(**base)


def test_an_offset_that_carries_is_reported_as_carrying():
    a = alignment()
    assert a.offset_at_the_anchor == 2 and a.offset_at_these_loci == 2
    assert a.offset_holds


def test_an_offset_that_does_not_carry_is_reported_and_claims_nothing():
    """⛔⛔ The real pair: 2 at the anchor, 3 at the sutra under comparison.

    ⭐ A recorder carrying the anchor's offset lands on a different sutra and concludes the
    two copies attach the rule to different determinations — which is what was published.
    ⚠ And a false result must NOT be read as "different places": the class says only that
    arithmetic on sutra numbers cannot settle it.
    """
    a = alignment(second_number=53)
    assert not a.offset_holds
    row = a.as_json()
    assert row["offset_measured_at_the_anchor"] == 2
    assert row["offset_at_these_loci"] == 3
    assert row["the_anchors_offset_holds_at_these_loci"] is False
    assert "does NOT mean" in row["what_a_false_result_means"]


def test_the_across_copies_refusal_reason_is_declared():
    assert "place_in_the_work_not_established_across_copies" in REFUSAL_REASONS
    Refusal(
        subject="that two copies state a rule at the same sutra",
        reason="place_in_the_work_not_established_across_copies",
        detail="the copies reorder the sutras, so no single offset describes the pair",
        what_would_close_it="a copy printing both scripts for the same sutra",
    )


# --- a copy that renders to nothing ------------------------------------------------------
#
# ⭐⭐⭐ Every test below is built around one real copy: a printing of the right work,
# retrieved and digested by this repository, whose 219 pages are all images. Its extractor
# returned an empty string per page and joined them with newlines, so its rendering reports
# **218** characters while nothing in it can be searched. ⛔ That combination — mute and
# non-zero — is what made the hazard invisible, so the fixture reproduces it exactly.


def mute_edition() -> Edition:
    """A copy that rendered to nothing, with the non-zero character count the real one has."""
    text = "\n" * 218
    return Edition(
        key="renders_to_nothing",
        identity="219 pages of scanned page images, carrying no text layer",
        language="en",
        witness=Witness(
            address="https://example.invalid/scan.pdf",
            retrieved="2026-08-16",
            http_status=200,
            copy_sha256="0" * 64,
            copy_bytes=13_905_548,
        ),
        rendering=Rendering(
            kind="embedded_text_layer",
            produced_by="pypdf 5.1.0",
            sha256=digest(text),
            # ⚠ The number a reader trusts, and it is the page count minus one.
            characters=len(text),
        ),
        extent={"describes": "nothing was read", "complete": False},
        text=text,
    )


def test_the_renderings_character_count_is_not_the_searchable_text():
    """⛔ The guard everyone writes — `characters == 0` — does not fire on the real copy."""
    mute = mute_edition()
    assert mute.rendering.characters == 218
    assert mute.searchable_characters == 0
    assert not mute.carries_searchable_text


def test_an_absence_is_refused_over_a_copy_that_renders_to_nothing():
    """⭐⭐⭐ The strongest-looking absence this module can print, and the emptiest."""
    with pytest.raises(TextualError) as caught:
        AbsenceSearch(
            claim="the rule is not in this copy",
            alphabet=("Atmakaraka", "Amatyakaraka"),
            edition=mute_edition(),
            occurrences=[],
            what_the_hits_do_say=(),
            positive_control="anything at all",
        )
    assert "no searchable text" in str(caught.value)


def test_an_absence_is_refused_without_a_positive_control():
    """⛔ Nothing else in the row tells a copy silent about the rule from one silent about all."""
    with pytest.raises(TextualError) as caught:
        AbsenceSearch(
            claim="c",
            alphabet=("nothing",),
            edition=edition(),
            occurrences=[],
            what_the_hits_do_say=(),
        )
    assert "positive control" in str(caught.value)


def test_an_absence_is_refused_when_its_positive_control_does_not_resolve():
    """⚠ A control that locates nothing shows nothing, and one found twice shows nothing either."""
    for control in ("words this copy does not contain", "a phrase repeated twice appears"):
        with pytest.raises(TextualError) as caught:
            AbsenceSearch(
                claim="c",
                alphabet=("nothing",),
                edition=edition(),
                occurrences=[],
                what_the_hits_do_say=(),
                positive_control=control,
            )
        assert "positive control" in str(caught.value)


def test_the_absence_row_carries_the_proof_that_the_copy_was_readable():
    """⭐ The null control: a real absence still passes, and now says why its zeroes count."""
    row = AbsenceSearch(
        claim="c",
        alphabet=("nothing",),
        edition=edition(),
        occurrences=[],
        what_the_hits_do_say=(),
        positive_control=CONTROL,
    ).as_row()
    assert row["the_copy_was_shown_to_be_readable_by"]["occurrences"] == 1
    assert row["hits_in_total"] == 0


def test_a_passage_absence_over_a_mute_copy_names_the_right_cause():
    """⭐⭐⭐ It refused before this session too — and blamed the alphabet.

    ⛔ The attestation rule fires over a mute copy because *every* spelling is unattested in
    it, so the refusal arrived with the wrong cause attached and would send the next reader
    to fix a vocabulary that was never the problem. ⚠ The two states must be told apart.
    """
    with pytest.raises(TextualError) as caught:
        PassageAbsence(
            claim="c",
            edition=mute_edition(),
            passage_label="p",
            after="SU. 11",
            before="SU. 12",
            alphabet=("Prof.",),
            alphabet_read_from="read off the copy",
        )
    message = str(caught.value)
    assert "no searchable text" in message
    assert "guessed" not in message.replace("NOT an alphabet that was guessed", "")


def test_a_passage_absence_still_blames_the_alphabet_when_the_alphabet_is_guessed():
    """⚠ The null control for the test above: the two causes must not have collapsed."""
    with pytest.raises(TextualError) as caught:
        PassageAbsence(
            claim="c",
            edition=edition(),
            passage_label="p",
            after="Chapter one.",
            before="End of First Pada.",
            alphabet=("a spelling nobody in this copy uses",),
            alphabet_read_from="guessed, which is the defect",
        )
    assert "guessed" in str(caught.value)


# --- more than one commenting hand in one copy --------------------------------------------

HANDED = (
    "Chapter one. The first rule is stated here, once and only once.\n"
    "NOTES The lord of the sign is meant.\n"
    "* I have not meddled with the rendering of this sutra by Prof. B. Suryanarain Rao.\n"
    "* I have discussed this at length in my book Studies in Something Else.\n"
    "End of First Pada. End of Second Pada.\n" + " " + REPEATS_LIKE_A_BOOK
)

THIRD_PERSON = (
    "* I have not meddled with the rendering of this sutra by Prof. B. Suryanarain Rao.",
)
OWN_WORK = ("* I have discussed this at length in my book Studies in Something Else.",)


def test_a_second_hand_is_established_from_located_passages():
    """⭐ A hand that writes of *Prof. Rao* in the third person is not Prof. Rao."""
    row = SecondHand(
        edition=edition(HANDED),
        the_notes_are_credited_to="B. Suryanarain Rao",
        speaks_of_the_translator_in_the_third_person=THIRD_PERSON,
        claims_work_of_its_own=OWN_WORK,
        marked_by=("*", "Prof."),
        named_within_this_copy=False,
    ).as_row()
    assert row["how_many_commenting_hands_this_copy_carries"] == 2
    assert row["the_copy_speaks_of_the_translator_in_the_third_person"][0]["occurrences"] == 1
    assert row["the_second_hand_is_named_within_this_copy"] is False


def test_a_second_hand_with_no_third_person_passage_is_refused():
    """⛔ Otherwise it is a reader's impression of a change in voice."""
    with pytest.raises(TextualError) as caught:
        SecondHand(
            edition=edition(HANDED),
            the_notes_are_credited_to="B. Suryanarain Rao",
            speaks_of_the_translator_in_the_third_person=(),
            claims_work_of_its_own=OWN_WORK,
            marked_by=("*",),
            named_within_this_copy=False,
        )
    assert "third person" in str(caught.value)


def test_a_second_hand_whose_passage_does_not_resolve_is_refused():
    """⚠ Built by mutating the real passage, and the text is asserted to have changed."""
    mutated = THIRD_PERSON[0].replace("meddled", "meddled at all")
    assert mutated != THIRD_PERSON[0]
    with pytest.raises(TextualError) as caught:
        SecondHand(
            edition=edition(HANDED),
            the_notes_are_credited_to="B. Suryanarain Rao",
            speaks_of_the_translator_in_the_third_person=(mutated,),
            claims_work_of_its_own=(),
            marked_by=("*",),
            named_within_this_copy=False,
        )
    assert "occurs 0 time(s)" in str(caught.value)


def test_a_second_hand_cannot_be_established_in_a_copy_that_renders_to_nothing():
    with pytest.raises(TextualError):
        SecondHand(
            edition=mute_edition(),
            the_notes_are_credited_to="B. Suryanarain Rao",
            speaks_of_the_translator_in_the_third_person=THIRD_PERSON,
            claims_work_of_its_own=(),
            marked_by=("*",),
            named_within_this_copy=False,
        )


def test_the_two_new_refusal_reasons_are_declared():
    for reason in (
        "rendering_carries_no_searchable_text",
        "revised_printing_cannot_witness_the_unrevised_words",
    ):
        assert reason in REFUSAL_REASONS
        Refusal(
            subject="a subject",
            reason=reason,
            detail="a detail",
            what_would_close_it="what would close it",
        )


# ==========================================================================================
# A COPY CAN BE READ IN THE WRONG ALPHABET, AND EVERY OLDER GUARD PASSES IT
# ==========================================================================================

#: A rendering of noise in an Indic script — a machine reading of an English book by a reader
#: set to the wrong script. ⛔ Not hypothetical: a library scan in this repository's cache is
#: 246 777 characters of exactly this, with no Latin letter in it.
NOISE = "१९०६ छण ९१६११ ७००७९ अए0गा9०5 एणं {91 छऽ 25010 ४६४६ ७९ एन्वञप्रा ११६४ त २४०६२"

#: ⚠ A rendering carrying BOTH scripts. This is the copy the control-script rule is for: it
#: passes the script-presence check for a Latin alphabet, so only the control catches it.
BILINGUAL = BODY + " आत्साधिकः कला दिभिनभोग: सप्तानासष्टानां वा"


def test_script_of_ignores_marks_that_live_inside_a_script_block():
    """⛔⛔ THE BUG THIS FIXES WAS WRITTEN IN THIS REPOSITORY AND MEASURED 6 077 TIMES.

    Read as a bare code-point range the Latin bucket counts braces, brackets and signs, so
    the guard built to catch a copy with no Latin LETTERS reported six thousand Latin
    characters in exactly that copy — and passed it.
    """
    for mark in "{}[]^`|~\\_":
        assert script_of(mark) is None
    for digit in "0123456789":
        assert script_of(digit) is None
    assert script_of("A") == "latin"
    assert script_of("आ") == "devanagari"
    assert scripts_in("{[^`|~}") == {}


def test_scripts_in_counts_letters_only():
    counts = scripts_in("Rao [12] आत्मा")
    assert counts["latin"] == 3
    # ⚠ Three, not five: the virama and the vowel sign are combining marks, and a mark is
    #   not a letter. ⭐ The same rule that keeps a brace out of the Latin count.
    assert counts["devanagari"] == 3


def test_a_term_that_is_only_a_mark_requires_no_script():
    """⭐ The one spelling that is a printed mark must not stand in for eleven that are words."""
    assert scripts_required_by(("*",)) == set()
    assert scripts_required_by(("*", "Prof.")) == {"latin"}


def test_absence_refuses_a_rendering_carrying_none_of_the_searched_script():
    """⛔⛔⛔ THE COPY WAS READ, AND NOT IN THE ALPHABET THE CLAIM IS WRITTEN IN."""
    copy = edition(NOISE)
    assert copy.carries_searchable_text  # ⚠ every older guard passes it
    assert copy.searchable_characters > 0
    assert copy.scripts.get("latin", 0) == 0
    with pytest.raises(TextualError) as excinfo:
        AbsenceSearch(
            claim="that this copy does not say it",
            alphabet=("Prof.", "Professor"),
            edition=copy,
            occurrences=[],
            what_the_hits_do_say=[],
            positive_control="४६४६ ७९ एन्वञप्रा",
        )
    message = str(excinfo.value)
    assert "no ['latin']" in message
    # ⛔ And it must not blame the recorder for a silence that is the reading's.
    assert "searchable characters" in message


def test_absence_refuses_an_alphabet_written_in_no_script_at_all():
    with pytest.raises(TextualError, match="written in no script"):
        AbsenceSearch(
            claim="that this copy does not print it",
            alphabet=("*", "12"),
            edition=edition(),
            occurrences=[],
            what_the_hits_do_say=[],
            positive_control=CONTROL,
        )


def test_absence_refuses_a_positive_control_in_another_script():
    """⭐⭐⭐ THE GUARD ARMED LAST TIME HAS ITS OWN FAILURE MODE, AND THIS IS IT.

    The copy carries both scripts, so the script-presence check above passes. The control
    resolves exactly once. ⛔ And it shows only that the copy was read in the script the
    control is written in — which is not the script the zeroes were counted in.
    """
    copy = edition(BILINGUAL)
    assert copy.scripts["latin"] > 0 and copy.scripts["devanagari"] > 0
    assert resolve(copy, "आत्साधिकः कला").occurrences == 1
    with pytest.raises(TextualError, match="control is written in"):
        AbsenceSearch(
            claim="that this copy does not say it",
            alphabet=("Professor", "Prof."),
            edition=copy,
            occurrences=[],
            what_the_hits_do_say=[],
            positive_control="आत्साधिकः कला",
        )


def test_absence_accepts_a_control_in_the_alphabets_own_script():
    """⚠ The null control: the same row with a control in the right script is written."""
    row = AbsenceSearch(
        claim="that this copy does not say it",
        alphabet=("Professor", "Prof."),
        edition=edition(BILINGUAL),
        occurrences=[],
        what_the_hits_do_say=[],
        positive_control=CONTROL,
    ).as_row()
    assert row["hits_in_total"] == 0


def test_passage_absence_names_the_script_before_it_blames_the_alphabet():
    """⛔⛔ THE FIX THAT NAMED THE RIGHT CAUSE WAS WRITTEN FOR ONE CAUSE.

    The mute-copy check was moved ahead of attestation because over a blank copy attestation
    fires and reports that the recorder GUESSED the vocabulary. ⚠ A copy read in the wrong
    script does it again, and the previous fix does not cover it: the spellings are genuinely
    unattested there, and the cause is the machine reading.
    """
    with pytest.raises(TextualError) as excinfo:
        PassageAbsence(
            claim="that the passage does not say it",
            edition=edition(NOISE),
            passage_label="a passage",
            after="४६४६",
            before="२४०६२",
            alphabet=("Prof.", "Professor"),
            alphabet_read_from="the other printing, where each is attested",
        )
    message = str(excinfo.value)
    assert "wrong script" in message
    # ⛔ And it must DENY the wrong cause rather than report it: the attestation rule below
    #   would have said these spellings were guessed, which is a vocabulary nobody got wrong.
    assert "NOT a guessed alphabet" in message
    assert "so they were guessed rather than read off it" not in message


def test_discrimination_of_resolving_once_is_total_in_a_rendering_of_noise():
    """⭐⭐⭐ THE CONDITION THIS REPOSITORY LEANS ON HARDEST FILTERS NOTHING THERE."""
    noise = edition(NOISE)
    fragments = [NOISE[i : i + 8] for i in range(0, len(NOISE) - 8, 8)]
    measured = discrimination_of_resolving_once(noise, fragments)
    assert measured["share_resolving_exactly_once"] == 1.0
    book = discrimination_of_resolving_once(
        edition(), ["a phrase repeated twice", "Chapter one."]
    )
    assert book["resolving_more_than_once"] == 1
    assert book["share_resolving_exactly_once"] == 0.5


# ==========================================================================================
# A HAND ONE COPY CANNOT NAME, NAMED BY ANOTHER COPY
# ==========================================================================================

UNNAMED = (
    "Though the translator has elucidated the abbreviations I propose to observe further.\n"
    "* I have discussed this at length in my book Studies in the Subject.\n"
    "The rest is clear from the translator's notes.\n" + " " + REPEATS_LIKE_A_BOOK
)
NAMING = (
    "Revised and Annotated by A NAMED HAND. Fifth Edition 1955.\n"
    "* I have discussed this at length in my book Studies in the Subject.\n"
    "FOREWORD. I have not meddled with the notes. The translation has been revised by me.\n" + " " + REPEATS_LIKE_A_BOOK
)


def _named_in_another_copy(**overrides):
    kwargs = dict(
        the_hand="the hand the first copy cannot name",
        unnamed_in=edition(UNNAMED),
        named_in=Edition(
            key="naming_copy",
            identity="a second copy built for this test",
            language="en",
            witness=Witness(
                address="https://example.invalid/second.txt",
                retrieved="2026-08-18",
                http_status=200,
                copy_sha256="1" * 64,
                copy_bytes=len(NAMING),
            ),
            rendering=Rendering(
                kind="transcription",
                produced_by="this test",
                sha256=digest(NAMING),
                characters=len(NAMING),
            ),
            extent={"describes": "the whole of it", "complete": True},
            text=NAMING,
        ),
        the_name_as_that_copy_prints_it="A NAMED HAND",
        the_passage_that_names_it="Revised and Annotated by A NAMED HAND.",
        the_printing_that_copy_declares="Fifth Edition 1955.",
        tied_to_the_unnamed_hand_by=(
            "* I have discussed this at length in my book Studies in the Subject.",
        ),
        what_this_does_not_establish="which printing the unnamed copy is",
    )
    kwargs.update(overrides)
    return NamedInAnotherCopy(**kwargs)


def test_a_hand_is_named_by_the_other_copys_page():
    row = _named_in_another_copy().as_row()
    assert row["finding"] == "hand_named_in_another_copy"
    assert row["the_name_occurs_in_the_unnamed_copy"] == 0
    assert row["tied_to_the_unnamed_hand_by"][0]["occurrences_in_the_unnamed_copy"] == 1
    assert row["tied_to_the_unnamed_hand_by"][0]["occurrences_in_the_naming_copy"] == 1


def test_naming_refuses_when_one_copy_is_asked_to_do_both_jobs():
    with pytest.raises(TextualError, match="it is a re-reading"):
        _named_in_another_copy(unnamed_in=_named_in_another_copy().named_in)


def test_naming_refuses_an_unresolved_naming_passage():
    with pytest.raises(TextualError, match="locates nothing"):
        _named_in_another_copy(the_passage_that_names_it="Revised by somebody else.")


def test_naming_refuses_when_the_name_is_in_the_copy_said_not_to_name_it():
    """⛔ Then the earlier *cannot be named from this copy* was wrong, and THAT is the finding."""
    with pytest.raises(TextualError, match="said not to name the hand"):
        _named_in_another_copy(
            unnamed_in=edition(UNNAMED + "Annotated by A NAMED HAND.\n"),
        )


def test_naming_refuses_without_a_tie():
    with pytest.raises(TextualError, match="until something located ties them"):
        _named_in_another_copy(tied_to_the_unnamed_hand_by=())


def test_naming_refuses_a_tie_that_resolves_on_only_one_side():
    """⭐⭐⭐ NINE OF TEN REAL CANDIDATES FAIL HERE, AND NONE OF THE NINE IS AN ABSENCE.

    Two machine readings of the same sentence spell it differently, so a fragment resolving
    in one and not the other measures the readings and not the printings.
    """
    with pytest.raises(TextualError, match="ties nothing"):
        _named_in_another_copy(
            tied_to_the_unnamed_hand_by=("The rest is clear from the translator's notes.",)
        )


# ==========================================================================================
# A COPY THAT DISAGREES WITH ITSELF
# ==========================================================================================


def test_a_copy_can_disagree_with_itself_and_the_pair_is_the_finding():
    row = SelfContradiction(
        edition=edition(NAMING),
        the_hand="the reviser",
        statements=(
            ("that nothing was altered", "I have not meddled with the notes."),
            ("that it was revised", "The translation has been revised by me."),
        ),
        why_they_cannot_both_be_relied_on="a reader needs the question they disagree about",
        what_it_settles="that this copy is not the authority for what was altered",
    ).as_row()
    assert row["finding"] == "the_copy_disagrees_with_itself"
    assert [s["occurrences"] for s in row["statements"]] == [1, 1]


def test_one_statement_is_not_a_contradiction():
    with pytest.raises(TextualError, match="one statement is not a contradiction"):
        SelfContradiction(
            edition=edition(NAMING),
            the_hand="the reviser",
            statements=(("that nothing was altered", "I have not meddled with the notes."),),
            why_they_cannot_both_be_relied_on="x",
            what_it_settles="y",
        )


def test_a_contradiction_is_between_two_located_statements():
    with pytest.raises(TextualError, match="locates nothing"):
        SelfContradiction(
            edition=edition(NAMING),
            the_hand="the reviser",
            statements=(
                ("that nothing was altered", "I have not meddled with the notes."),
                ("that it was revised", "A sentence this copy does not contain."),
            ),
            why_they_cannot_both_be_relied_on="x",
            what_it_settles="y",
        )


def test_the_edition_publishes_its_scripts_beside_its_searchable_count():
    """⭐ The pair is the finding one level down: readable, and not in the book's alphabet."""
    published = edition(NOISE).as_json()["searchable"]
    assert published["characters_a_locus_can_resolve_against"] > 0
    scripts = {row["script"]: row["code_points"] for row in published["scripts_this_rendering_carries"]}
    assert "latin" not in scripts
    assert scripts["devanagari"] > 0


def test_the_two_new_refusal_reasons_are_declared():
    assert "rendering_carries_none_of_the_searched_script" in REFUSAL_REASONS
    assert "positive_control_is_not_in_the_searched_script" in REFUSAL_REASONS


# ==========================================================================================
# ⭐⭐⭐ AN ALPHABET THAT MARKS ONE HAND, CHECKED AGAINST THE OTHER HAND'S WORDS
#
# The alphabet by which this repository marks a second commenting hand was read off a copy
# in which both hands are printed on the same pages, and it inherited both. Four of its
# twelve spellings fire on the translator's own honorific, on a phrase of the first sutra,
# and on the machine reading's own damage — none of which a second hand puts there.
# ==========================================================================================

#: A copy carrying the translator's byline, the first sutra, and a commentator's own voice.
TWO_HANDS = (
    "ENGLISH TRANSLATION BY Professor B. SURYANARAIN RAO. "
    "SU. 1. I shall now explain my work for the benefit of the readers. "
    "NOTES. * I have discussed this at length in my book On The Series. "
    "The rest is clear from Prof. Rao's own notes." + " " + REPEATS_LIKE_A_BOOK
)

#: The same edition read a second time, losing one mark the first reader found.
TWO_HANDS_SECOND_READING = (
    "ENGLISH TRANSLATION BY Professor B. SURYANARAIN RAO. "
    "SU. 1. I shall now explain rny work for the benefit of the readers. "
    "NOTES. I have discussed this at length in rny b00k On The Series. "
    "The rest is clear from Prof. Rao's own notes." + " " + REPEATS_LIKE_A_BOOK
)


def test_a_spelling_that_fires_on_the_other_hands_words_is_reported():
    """⛔ *my work* is a phrase of the FIRST SUTRA, and it is in the second hand's alphabet."""
    found = alphabet_contamination(
        ("my work", "my book"),
        edition(TWO_HANDS),
        (("the first sutra", "I shall now explain my work for the benefit of the readers"),),
    )
    assert [c["spelling"] for c in found] == ["my work"]
    assert found[0]["that_passage_occurs_in_the_copy"] == 1


def test_a_contaminated_alphabet_cannot_licence_an_absence():
    """⭐⭐⭐ The test would have rejected the printing it was built to find."""
    with pytest.raises(TextualError, match="occur in material it must not mark"):
        MarkerAlphabet(
            marks="the second commenting hand",
            alphabet=("my work", "my book"),
            edition=edition(TWO_HANDS),
            must_not_mark=(
                ("the first sutra", "I shall now explain my work for the benefit of the readers"),
            ),
        )


def test_an_alphabet_that_marks_only_the_second_hand_is_accepted():
    row = MarkerAlphabet(
        marks="the second commenting hand",
        alphabet=("my book", "Prof. Rao's own notes"),
        edition=edition(TWO_HANDS),
        must_not_mark=(
            ("the first sutra", "I shall now explain my work for the benefit of the readers"),
        ),
    ).as_row()
    assert row["contaminated_spellings"] == []
    assert row["checked_against"][0]["occurrences"] == 1


def test_an_alphabet_checked_against_nothing_is_refused():
    """⛔ A discrimination check with no material to discriminate against reports success."""
    with pytest.raises(TextualError, match="No passage of the material it must NOT mark"):
        MarkerAlphabet(
            marks="the second commenting hand",
            alphabet=("my book",),
            edition=edition(TWO_HANDS),
            must_not_mark=(),
        )


def test_a_spelling_can_only_be_refuted_by_words_shown_to_be_in_the_copy():
    with pytest.raises(TextualError, match="locates nothing"):
        MarkerAlphabet(
            marks="the second commenting hand",
            alphabet=("my book",),
            edition=edition(TWO_HANDS),
            must_not_mark=(("a sutra", "a sentence this copy does not contain"),),
        )


def test_an_alphabet_cannot_be_checked_against_a_copy_that_renders_to_nothing():
    """⛔ Every passage resolves zero times, so every spelling would look clean."""
    with pytest.raises(TextualError, match="renders to no searchable text"):
        MarkerAlphabet(
            marks="the second commenting hand",
            alphabet=("my book",),
            edition=edition(""),
            must_not_mark=(("the first sutra", "I shall now explain my work"),),
        )


# ==========================================================================================
# ⭐⭐⭐ A ZERO IS A PROPERTY OF THE READING THAT PRODUCED IT
#
# Three machine readings of one edition disagree about whether four of twelve spellings are
# on the page at all. A clean pass, had one been obtained, would have measured the reader.
# ==========================================================================================


def test_a_mark_lost_by_one_reader_is_reported_as_disagreement():
    found = reading_disagreement(
        ("my book", "Professor"),
        (edition(TWO_HANDS), edition(TWO_HANDS_SECOND_READING)),
    )
    assert [d["spelling"] for d in found] == ["my book"]
    assert [h["hits"] for h in found[0]["hits_by_reading"]] == [1, 0]


def test_an_absence_is_refused_when_the_readings_disagree():
    with pytest.raises(TextualError, match="found by one reading"):
        AbsenceAcrossReadings(
            claim="that this printing carries none of the second hand's marks",
            alphabet=("my book",),
            readings=(edition(TWO_HANDS), edition(TWO_HANDS_SECOND_READING)),
            the_readings_are_of_one_edition_because="ENGLISH TRANSLATION BY Professor",
        )


def test_readings_that_agree_are_accepted_and_the_tie_is_published():
    row = AbsenceAcrossReadings(
        claim="that this printing carries none of the second hand's marks",
        alphabet=("a phrase neither reading contains",),
        readings=(edition(TWO_HANDS), edition(TWO_HANDS_SECOND_READING)),
        the_readings_are_of_one_edition_because="ENGLISH TRANSLATION BY Professor",
    ).as_row()
    assert row["spellings_whose_verdict_differs_between_readings"] == []
    assert [
        r["occurrences"] for r in row["the_readings_are_of_one_edition_because"]["occurrences_by_reading"]
    ] == [1, 1]


def test_one_reading_cannot_check_itself():
    """⛔ One reading agrees with itself perfectly, which is the state this guard refuses."""
    with pytest.raises(TextualError, match="1 reading"):
        AbsenceAcrossReadings(
            claim="x",
            alphabet=("my book",),
            readings=(edition(TWO_HANDS),),
            the_readings_are_of_one_edition_because="ENGLISH TRANSLATION BY Professor",
        )


def test_readings_must_be_tied_to_one_edition_by_a_located_fragment():
    """⛔ Without the tie, two books' difference reads as one reader's error."""
    with pytest.raises(TextualError, match="tying these readings to one edition"):
        AbsenceAcrossReadings(
            claim="x",
            alphabet=("my book",),
            readings=(edition(TWO_HANDS), edition("An unrelated book about something else.")),
            the_readings_are_of_one_edition_because="ENGLISH TRANSLATION BY Professor",
        )


def test_a_reading_that_carries_no_text_cannot_stand_as_a_check():
    """⛔ A mute reading agrees with every absence ever claimed."""
    with pytest.raises(TextualError, match="agrees with every absence"):
        AbsenceAcrossReadings(
            claim="x",
            alphabet=("my book",),
            readings=(edition(TWO_HANDS), edition("")),
            the_readings_are_of_one_edition_because="ENGLISH TRANSLATION BY Professor",
        )


def test_the_footnote_mark_carries_no_script_and_so_marks_no_hand():
    """⭐⭐⭐ The one spelling that is not a word was all that denied a copy of pure noise a
    clean pass — and it denied it by accident."""
    assert scripts_in("*") == {}
    assert scripts_required_by(("*",)) == set()
    assert scripts_required_by(("*", "my book")) == {"latin"}


# ==========================================================================================
# ⭐⭐⭐ THE VERDICT IS A PRESENCE, BECAUSE A ZERO IS WHAT A BROKEN READER PRODUCES FOR FREE
#
# The retired second-printing test required a candidate copy to carry NONE of twelve
# spellings. A library scan of the work whose machine reading carries no Latin letters at all
# scores a PERFECT pass on the eleven of them that are words. ⛔ Under an absence every way a
# reader can fail turns a hit into a zero, and a zero is a pass — so the instrument's errors
# all point at success. These tests exercise the replacement, whose errors are refusals.
# ==========================================================================================


def _copy(text: str, *, key: str) -> Edition:
    """An edition with its own key. ⛔ Built from a literal, like every copy in this file."""
    return Edition(
        key=key,
        identity=f"a copy built for this test, {key}",
        language="en",
        witness=Witness(
            address=f"https://example.invalid/{key}.txt",
            retrieved="2026-08-18",
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


#: The copy the rule is filed in — an English translation a second hand revised.
REVISED_TRANSLATION = _copy(
    "ENGLISH TRANSLATION BY Professor B. SURYANARAIN RAO. "
    "SU. 11. Of the bodies, whichever gets the highest degrees heads the series. "
    "NOTES. If two bodies obtain the same degrees they are merged into one lordship. "
    "* I have discussed this at length in my book On The Series.",
    key="the_revised_translation",
)

#: A copy outside that hand's reach — a different translator, working from the original.
#: ⭐ It carries the ORIGINAL's script, which is what puts it outside; the English printings
#: carry none of it.
#: ⭐ A book repeats itself, in any script. ⚠ The tail below is what makes this fixture a
#: rendering of language rather than a rendering of noise, and the difference is measured.
REPEATS_LIKE_A_BOOK_IN_THE_ORIGINALS_SCRIPT = (
    " यह पंक्ति हर पृष्ठ के नीचे छपी है। यह पंक्ति हर पृष्ठ के नीचे छपी है।"
)

#: ⛔⛔ **IT WAS 225 CHARACTERS AND WAS GROWN TO 381 TO CLEAR AN ACCEPTING BOUND OF 315.**
#: ⛔⛔⛔ **THAT BOUND IS GONE, AND 381 WOULD NOT HAVE SAVED IT.** The accepting side's own
#: number, measured over thirty-three specimens instead of one, is **320 000** — so a copy
#: this size clears the floor for exactly the reason a window of noise does, and no amount of
#: growing a fixture reaches that. ⇒ The arm was removed rather than raised; see
#: `test_the_accepting_side_is_disarmed_and_the_reason_is_measured`.
#: ⭐ The copy is left at 381 all the same, because it was grown with **new prose** rather
#: than more repetitions of its own tail — padding it with the line it already repeats would
#: raise the share by making the copy *less* like a book — and shrinking it back would be
#: churn that erases the record of why it grew.
SECOND_TRANSLATION = _copy(
    "जैमिनिसूत्रम् — हिन्दी अनुवाद सहित। "
    "यदि दो या अधिक ग्रहों के अंश समान हों तो वे दोनों ही आत्मकारक माने जाएँगे। "
    "उस स्थिति में राहु उस रिक्तता को पूरा करेगा। "
    "यह नियम सूत्रकार ने स्वयं नहीं कहा, किन्तु परम्परा में यही माना जाता रहा है। "
    "अनुवादक ने इसे अपनी टिप्पणी में स्पष्ट किया है, और उसी रूप में यहाँ उद्धृत है।"
    + REPEATS_LIKE_A_BOOK_IN_THE_ORIGINALS_SCRIPT,
    key="the_second_translation",
)

#: ⛔ A SECOND PRINTING OF THE SAME TRANSLATION. It is inside the reach, and two printings one
#: hand revised agree about the revision — the standing refusal, as an entry condition.
ANOTHER_PRINTING = _copy(
    "Jaiminisutras, fifth edition, revised and annotated. "
    "If two bodies obtain the same degrees they are merged into one lordship.",
    key="another_printing_of_the_same_translation",
)

def _noise(letters: int) -> str:
    """A rendering in which nothing recurs, long enough to be measured at twelve characters.

    ⚠ Built by a rule rather than quoted: the property under test is *nothing in this copy
    repeats*, and a quotable fragment of the real thing is too short to measure. ⭐ The real
    one is in this repository's cache — 246 777 characters, 44 of 246 689 fragments recurring.
    """
    aksharas, out, state = "कखगघङचछजझञटठडढणतथदधनपफबभमयरलवशषसह", [], 7
    for step in range(letters):
        state = (state * 1103515245 + 12345) % 2147483648
        out.append(aksharas[state % len(aksharas)])
        if step % 5 == 4:
            out.append(" ")
    return "".join(out)


#: ⛔⛔⛔ THE COPY THAT PASSED THE RETIRED TEST PERFECTLY, as it really behaves. A machine
#: reading in which nothing of the work survives — offered here as an attestation, in the
#: right script, and long enough for its recurrence to be measured.
#:
#: ⛔⛔⛔ **IT WAS 1 799 CHARACTERS, AND AT THAT EXTENT A REAL BOOK IS REFUSED TOO.** Every
#: test in this file that certified *the instruments refuse the rendering of noise* was
#: certifying a refusal the copy's **size** earned, not its noise.
#:
#: ⛔⛔⛔ **AND THEN IT HAPPENED AGAIN, TO THE REPAIR.** Grown to 7 199 characters to clear a
#: `LEAST_EXTENT_A_REFUSAL_DISCRIMINATES_AT` of 6 000, it went under the bound a second time
#: the moment that constant was re-measured over every window instead of one tiling phase and
#: came out **7 686** — so for a session these tests were again certifying a refusal the
#: copy's size had earned. ⇒ ⭐⭐⭐ *A fixture sized to a fitted constant is only as sound as
#: the constant, and it fails silently in exactly the direction that looks like success.*
#: It now clears the bound by 713 characters. ⭐ The generator is prefix-stable, so every
#: offset quoted out of this copy below is the same text it was before it grew, twice.
A_RENDERING_OF_NOISE = _copy(_noise(7000), key="a_rendering_of_noise")

#: ⛔⛔⛔ AND THE COPY THAT MANUFACTURES THE PRESENCE. Its attesting passage is a run of the
#: copy's OWN NOISE — quoted out of it, so it resolves exactly once, clears the passage-length
#: floor and carries the original's script. ⚠ Before the recurrence guard this row CONSTRUCTED,
#: attesting a rule nobody ever stated, and the class's own limit reads *a reader can destroy
#: the evidence of a presence but cannot manufacture it*.
NOISE_THE_PASSAGE_IS_QUOTED_OUT_OF = _copy(_noise(7000), key="noise_quoted_against_itself")

#: The run of that copy's own noise a recorder would offer. ⛔ It resolves EXACTLY ONCE there.
PASSAGE_QUOTED_OUT_OF_THE_NOISE = NOISE_THE_PASSAGE_IS_QUOTED_OUT_OF.normalised[200:260]

#: ⚠ A copy that repeats like a book and simply does not contain the passage. ⭐ It is here
#: because the refusal it earns — *locates nothing* — is the one the noise copy used to earn
#: for the wrong reason: the old fixture could not supply the passage, and a real rendering
#: of noise supplies whatever it is asked for.
A_COPY_THAT_REPEATS_BUT_LACKS_THE_PASSAGE = _copy(
    "जैमिनि का एक और अनुवाद, जिसमें यह नियम नहीं है। "
    "इस संस्करण में केवल मूल सूत्र दिए गए हैं, टिप्पणी नहीं। "
    "प्रकाशक ने भूमिका में लिखा है कि पाठ अपरिवर्तित रखा गया है। "
    "अनुक्रमणिका और परिशिष्ट भी इसी क्रम में छपे हैं। "
    "पृष्ठ संख्या नीचे दाहिनी ओर दी गई है, और अध्याय का नाम ऊपर।"
    + REPEATS_LIKE_A_BOOK_IN_THE_ORIGINALS_SCRIPT,
    key="a_copy_that_lacks_the_passage",
)

#: The rule as the second translation states it — long enough that resolving is not free.
ATTESTING_PASSAGE = "यदि दो या अधिक ग्रहों के अंश समान हों तो वे दोनों ही आत्मकारक माने जाएँगे"


#: ⚠ A copy carrying BOTH the translation and the original. Over it the reach condition
#: separates nothing, because the script no longer tells the two copies apart.
A_BILINGUAL_PRINTING = _copy(
    "SU. 11. If two bodies obtain the same degrees they are merged into one lordship. "
    "यदि दो या अधिक ग्रहों के अंश समान हों।",
    key="a_bilingual_printing",
)


def _attestation(**overrides):
    fields = {
        "rule": "a_tie_merges_two_places_and_the_node_fills_the_vacancy",
        "the_rule_as_published": "bodies holding equal degrees merge into one lordship",
        "filed_as": "commentary",
        "filed_in": REVISED_TRANSLATION,
        "the_hand_whose_reach_is_at_issue": "the hand that revised this English translation",
        "the_reach_is_bounded_by": (
            "the naming copy's own title page, which reads revised and annotated by that hand"
        ),
        "attested_in": SECOND_TRANSLATION,
        "the_attesting_passages": (ATTESTING_PASSAGE,),
        "the_locus_there": "adhyaya 1, pada 1, the commentary to sutra 11",
        "the_original_is_written_in": "devanagari",
        "what_this_does_not_establish": (
            "⛔ not that the English words are the translator's, and not that the rule is in "
            "the sutras — the second translator is himself a modern commentator"
        ),
    }
    fields.update(overrides)
    return IndependentHandAttestation(**fields)


def test_a_rule_filed_as_a_hands_words_is_attested_outside_that_hands_reach():
    """⭐ The verdict is a resolution. The rule had to be FOUND."""
    row = _attestation().as_row()
    assert row["finding"] == "rule_attested_outside_one_hands_reach"
    assert [p["occurrences"] for p in row["the_attesting_passages"]] == [1]
    assert row["the_attesting_copy_is_outside_the_reach_because"][
        "letters_of_it_in_the_copy_the_rule_is_filed_in"
    ] == 0


def test_a_copy_that_repeats_and_lacks_the_passage_attests_nothing():
    """⭐ The refusal *locates nothing*, earned by a copy that really does lack the rule.

    ⚠ This is the case the noise copy used to stand in for, and it stood in for it wrongly.
    """
    with pytest.raises(TextualError, match="locates nothing"):
        _attestation(attested_in=A_COPY_THAT_REPEATS_BUT_LACKS_THE_PASSAGE)


def test_the_copy_that_passed_the_retired_test_perfectly_fails_this_one():
    """⭐⭐⭐ THE WHOLE POINT, ON ONE COPY — and the cause has changed.

    ⛔ The old fixture was twenty aksharas long and was refused because it could not supply
    the passage. The real thing supplies whatever it is asked for, so what refuses it is that
    NOTHING IN IT REPEATS.
    """
    with pytest.raises(TextualError, match="LITTLE IN THIS COPY REPEATS"):
        _attestation(attested_in=A_RENDERING_OF_NOISE)


def test_a_presence_is_free_wherever_nothing_repeats():
    """⛔⛔⛔ THE DEFECT THIS GUARD WAS ARMED FOR, AND IT IS IN THE PRESENCE-SHAPED VERDICT.

    A passage quoted out of a copy's own noise resolves exactly once, carries the original's
    script and clears the length floor — so it attested a rule nobody has ever stated. ⭐ The
    verdict shape does not save an instrument from a rendering that repeats nothing: a reader
    that LOSES text cannot manufacture a presence, and a reader that returns NOISE can.
    """
    # ⚠ Every older guard passes this copy, and the passage really does resolve exactly once.
    assert A_RENDERING_OF_NOISE.carries_searchable_text
    assert A_RENDERING_OF_NOISE.carries_script("devanagari")
    assert resolve(
        NOISE_THE_PASSAGE_IS_QUOTED_OUT_OF, PASSAGE_QUOTED_OUT_OF_THE_NOISE
    ).resolved
    with pytest.raises(TextualError, match="LITTLE IN THIS COPY REPEATS"):
        _attestation(
            attested_in=NOISE_THE_PASSAGE_IS_QUOTED_OUT_OF,
            the_attesting_passages=(PASSAGE_QUOTED_OUT_OF_THE_NOISE,),
        )


def test_a_second_printing_of_the_same_translation_is_refused_at_the_door():
    """⛔⛔ `revised_printing_cannot_witness_the_unrevised_words`, as an entry condition. Two
    printings one hand revised agree about the revision."""
    with pytest.raises(TextualError, match="carries no devanagari"):
        _attestation(attested_in=ANOTHER_PRINTING)


def test_the_reach_condition_must_actually_separate_the_two_copies():
    """⛔ If the copy the rule is filed in also carries the original, the script separates
    nothing and a second printing of one translation could satisfy it."""
    with pytest.raises(TextualError, match="does not separate the two copies"):
        _attestation(filed_in=A_BILINGUAL_PRINTING)


def test_the_test_means_nothing_over_a_row_filed_as_the_text():
    """⛔ A sutra is not attributed to a hand, so no hand's reach is at issue."""
    with pytest.raises(TextualError, match="attributed to the TEXT"):
        _attestation(filed_as="translation")


def test_a_copy_cannot_be_both_the_revised_one_and_the_independent_one():
    with pytest.raises(TextualError, match="not an independent attestation"):
        _attestation(attested_in=REVISED_TRANSLATION)


def test_a_fragment_too_short_to_state_a_rule_is_refused():
    """⛔ A word or two cannot state a rule, so its resolving establishes nothing about one."""
    with pytest.raises(TextualError, match="at least 12 are required"):
        _attestation(the_attesting_passages=("राहु",))


def test_the_length_bound_is_not_a_defence_against_chance_resolution():
    """⭐⭐⭐ THE JUSTIFICATION THIS BOUND WAS FIRST GIVEN WAS BACKWARDS, AND THE MEASUREMENT
    IS PINNED HERE SO IT CANNOT BE WRITTEN AGAIN. Resolving exactly once gets MORE common as a
    fragment lengthens, not less - so no length bound makes a resolution more meaningful, and
    raising this constant would make attestation cheaper rather than safer."""
    # ⚠ A corpus shaped like prose: one phrase recurring in many DISTINCT surroundings, so
    #   a short window lands inside the recurring phrase and a long one spans out of it.
    letters = "कखगघचछजझटठडढतथदधनपफबभम"
    recurring = "राहु के अंश "
    body = " ".join(
        recurring + "".join(letters[(i * 7 + j * 3) % len(letters)] for j in range(14))
        for i in range(30)
    )
    copy = _copy(body, key="a_length_curve_copy")
    windows = lambda n: sorted({body[i:i + n] for i in range(len(body) - n)} - {""})
    at8 = discrimination_of_resolving_once(copy, windows(8))
    at24 = discrimination_of_resolving_once(copy, windows(24))
    assert at24["share_resolving_exactly_once"] > at8["share_resolving_exactly_once"]


def test_an_attestation_needs_a_located_passage():
    with pytest.raises(TextualError, match="no attesting passage"):
        _attestation(the_attesting_passages=())


def test_an_unresolved_passage_attests_nothing():
    with pytest.raises(TextualError, match="locates nothing"):
        _attestation(the_attesting_passages=(
            "यह लम्बा वाक्य इस प्रति में कहीं भी नहीं मिलता और इसीलिए कुछ भी प्रमाणित नहीं करता",))


def test_the_reach_must_be_bounded_by_something():
    """⛔ *Outside its reach* is not a measurement until the reach is stated from a page."""
    with pytest.raises(TextualError, match="not bounded by anything"):
        _attestation(the_reach_is_bounded_by="  ")


def test_an_attestation_that_does_not_state_its_limit_reads_as_an_attribution():
    with pytest.raises(TextualError, match="reads as an attribution"):
        _attestation(what_this_does_not_establish="")


def test_a_mute_copy_can_neither_raise_the_question_nor_answer_it():
    with pytest.raises(TextualError, match="neither raise this question nor answer it"):
        _attestation(attested_in=_copy("", key="a_mute_copy"))


def test_the_row_publishes_that_its_verdict_is_a_presence():
    """⚠ The contrast is on the row, not left in a document a consumer will not read."""
    row = _attestation().as_row()
    assert "PERFECT pass" in row["the_verdict_is_a_presence_not_an_absence"]
    assert "NOT discharged by this row" in (
        row["the_attesting_copy_is_outside_the_reach_because"]["why_this_is_the_condition"]
    )


# ==========================================================================================
# A RENDERING IN WHICH NOTHING REPEATS ANSWERS EVERY QUESTION EXACTLY ONCE
# ==========================================================================================
#
# ⛔⛔⛔ Every guard above this line asks whether a copy was READ. None of them asks what a
# resolution in it is WORTH — and in a machine reading that returned noise, resolving exactly
# once is free. ⭐ That defeats an ABSENCE (every spelling returns zero and the positive
# control quoted from the copy's own noise resolves perfectly) and it defeats a PRESENCE
# (a passage quoted out of that same noise attests whatever it is said to state).


def test_recurrence_is_counted_at_every_position_and_never_sampled():
    """⭐ Exact arithmetic, on a copy small enough to check by hand."""
    fifteen = recurrence_of(edition("A" * 15))
    # ⚠ Four windows of twelve characters, all the same one.
    assert fifteen["distinct_fragments"] == 1
    assert fifteen["fragments_that_recur"] == 1
    assert fifteen["the_most_frequent_fragment_occurs"] == 4
    assert fifteen["share_that_recurs"] == 1.0
    assert fifteen["fragment_length"] == RECURRENCE_MEASURED_AT

    thirteen = recurrence_of(edition("ABCDEFGHIJKLM"))
    assert thirteen["distinct_fragments"] == 2
    assert thirteen["fragments_that_recur"] == 0
    assert thirteen["share_that_recurs"] == 0.0


def test_a_copy_too_small_to_repeat_is_refused_rather_than_passed():
    """⛔ A copy shorter than the length recurrence is measured at establishes nothing.

    ⚠ The refusal matters more than it looks: a share of `None` compared with a floor would
    be a guard that passes exactly the copies it can say least about.
    """
    with pytest.raises(TextualError, match="too small to repeat"):
        refuse_a_rendering_that_does_not_repeat(
            edition("AB"), what_it_would_make_free="anything at all"
        )


def test_the_floor_stands_between_a_rendering_of_noise_and_a_rendering_of_language():
    """⭐⭐ The direction, pinned. ⛔ The floor is only half of it — the LENGTH is the other."""
    noise = recurrence_of(A_RENDERING_OF_NOISE)["share_that_recurs"]
    book = recurrence_of(edition())["share_that_recurs"]
    assert noise < LEAST_RECURRENCE < book
    # ⚠ And the noise copy is not mute, not out of extent and not in the wrong script: every
    #   older guard passes it, which is why this one had to be written.
    assert A_RENDERING_OF_NOISE.carries_searchable_text
    assert A_RENDERING_OF_NOISE.carries_script("devanagari")
    # ⛔⛔⛔ AND IT IS LARGE ENOUGH FOR ITS REFUSAL TO BE ABOUT THE RENDERING. At the 1 799
    #   characters this fixture used to carry, a real book fails this floor too — so the
    #   bound is the module's number and not a round one written beside it.
    assert A_RENDERING_OF_NOISE.searchable_characters >= LEAST_EXTENT_A_REFUSAL_DISCRIMINATES_AT


def test_an_absence_over_a_copy_that_repeats_nothing_is_refused():
    """⛔⛔⛔ THE LATENT DEFECT THIS SESSION CLOSED, in the alphabet it was latent in.

    Scored on a DEVANAGARI alphabet the rendering of noise passes every earlier guard: it
    carries the script, it is not mute, and a control quoted out of its own noise resolves
    exactly once. ⭐ The row it would have written is a twelve-spelling absence over a copy
    that says nothing at all.
    """
    control = A_RENDERING_OF_NOISE.normalised[300:360]
    assert resolve(A_RENDERING_OF_NOISE, control).resolved  # ⚠ the control really does resolve
    assert scripts_required_by(("नियम", "अंश")) == {"devanagari"}
    with pytest.raises(TextualError, match="LITTLE IN THIS COPY REPEATS") as excinfo:
        AbsenceSearch(
            claim="that this copy states no such rule",
            alphabet=("नियम", "अंश"),
            edition=A_RENDERING_OF_NOISE,
            occurrences=[],
            what_the_hits_do_say=[],
            positive_control=control,
        )
    # ⛔ And it names the right cause: not mute, not the wrong alphabet, not out of extent.
    assert "not the alphabet that is wrong" in str(excinfo.value)


def test_the_same_absence_over_a_copy_that_repeats_is_accepted():
    """⭐⭐ The accepting case, so the refusal above is known not to refuse everything.

    ⛔ A guard that only forbids cannot tell an empty subject from a clean one.
    """
    taken = AbsenceSearch(
        claim="that this copy does not state it",
        alphabet=("widdershins",),
        edition=edition(),
        occurrences=[],
        what_the_hits_do_say=[],
        positive_control=CONTROL,
    )
    assert taken.hits == {"widdershins": 0}
    worth = taken.as_row()["and_resolving_exactly_once_is_not_free_here"]
    assert worth["share_that_recurs"] >= worth["the_floor_this_had_to_clear"]
    assert worth["measured_over"] == "every position of the rendering, not a sample"


def test_a_passage_absence_over_a_copy_that_repeats_nothing_is_refused_before_attestation():
    """⛔⛔ AND THE CAUSE IS THE COPY, NOT THE VOCABULARY — for the third time in this class.

    Both landmarks and every spelling are quoted out of the copy's own noise, so the region
    is bounded, every spelling is attested, and the zeroes in it are the machine reading's.
    """
    body = A_RENDERING_OF_NOISE.normalised
    after, before = body[100:130], body[400:430]
    assert resolve(A_RENDERING_OF_NOISE, after).resolved
    assert resolve(A_RENDERING_OF_NOISE, before).resolved
    attested = body[700:712]  # ⚠ attested in the copy, so the guessed-alphabet rule passes
    assert attested in body
    with pytest.raises(TextualError, match="LITTLE IN THIS COPY REPEATS"):
        PassageAbsence(
            claim="that this passage does not state the rule",
            edition=A_RENDERING_OF_NOISE,
            passage_label="somewhere in the noise",
            after=after,
            before=before,
            alphabet=(attested,),
            alphabet_read_from="read off this copy, which is the whole trouble",
        )


def test_every_row_publishes_what_a_resolution_in_its_copy_is_worth():
    """⭐ The measurement travels with the claim, because a reader cannot re-run it."""
    absence = passage_absence().as_row()["and_resolving_exactly_once_is_not_free_here"]
    assert absence["edition"] == "second_copy"
    assert absence["fragment_length"] == RECURRENCE_MEASURED_AT
    assert absence["the_floor_this_had_to_clear"] == LEAST_RECURRENCE
    assert "NOTHING IN THIS COPY REPEATS" in absence["what_a_share_near_zero_means"]

    attested = _attestation().as_row()["the_attesting_copy_repeats_itself"]
    assert attested["edition"] == "the_second_translation"
    assert attested["share_that_recurs"] >= LEAST_RECURRENCE


#: ⛔⛔ THE CENSUS, AND IT IS DRIVEN OFF ITS OWN VALUE. Each entry below is OFFERED the
#: rendering of noise and must refuse it, naming the copy rather than the alphabet, the
#: vocabulary or the extent. ⚠ The roster is counted against the number of guarded
#: resolutions in the module itself: a case quietly dropped from this list, or a guard armed
#: without one, is an unmeasured guard — and an unmeasured guard reports a pass.
#: ⭐ Measured, by disarming each call site in turn: eight of the nine were caught by this
#: list and the ninth was NOT — the copy a hand is said NOT to be named in had no case here,
#: so its guard could have been deleted in silence.
RESOLUTIONS_THAT_ARE_EVIDENCE = 9


def _offered_the_rendering_of_noise() -> dict[str, "callable"]:
    noise = A_RENDERING_OF_NOISE
    body = noise.normalised
    second_reading = _copy(body, key="a_second_reading_of_the_noise")
    return {
        "AbsenceSearch": lambda: AbsenceSearch(
            claim="that this copy states no such rule",
            alphabet=("नियम",),
            edition=noise,
            occurrences=[],
            what_the_hits_do_say=[],
            positive_control=body[300:360],
        ),
        "PassageAbsence": lambda: PassageAbsence(
            claim="that this passage states no such rule",
            edition=noise,
            passage_label="somewhere in the noise",
            after=body[100:130],
            before=body[400:430],
            alphabet=(body[700:712],),
            alphabet_read_from="read off this copy, which is the whole trouble",
        ),
        "IndependentHandAttestation": lambda: _attestation(
            attested_in=noise, the_attesting_passages=(body[200:260],)
        ),
        "AbsenceAcrossReadings": lambda: AbsenceAcrossReadings(
            claim="that this printing carries none of the marks",
            alphabet=("नियम",),
            readings=(noise, second_reading),
            the_readings_are_of_one_edition_because=body[500:540],
        ),
        "SecondHand": lambda: SecondHand(
            edition=noise,
            the_notes_are_credited_to="the translator",
            speaks_of_the_translator_in_the_third_person=(body[100:140],),
            claims_work_of_its_own=(),
            marked_by=("*",),
            named_within_this_copy=False,
        ),
        "NamedInAnotherCopy, the copy that names the hand": lambda: _named_in_another_copy(
            named_in=noise,
            the_name_as_that_copy_prints_it=body[50:70],
            the_passage_that_names_it=body[40:90],
            the_printing_that_copy_declares=body[600:640],
        ),
        # ⛔ The other half of that row, and the half nothing was measuring: the copy said NOT
        #   to name the hand. An absence re-measured over a rendering of noise is a zero.
        "NamedInAnotherCopy, the copy that does not": lambda: _named_in_another_copy(
            unnamed_in=noise
        ),
        "SelfContradiction": lambda: SelfContradiction(
            edition=noise,
            the_hand="the reviser",
            statements=(("one thing", body[300:340]), ("another", body[400:440])),
            why_they_cannot_both_be_relied_on="a reader needs the question they disagree about",
            what_it_settles="nothing whatever",
        ),
        "MarkerAlphabet": lambda: MarkerAlphabet(
            marks="a commenting hand",
            alphabet=("नियम",),
            edition=noise,
            must_not_mark=(("the text", body[200:240]),),
        ),
    }


def test_every_instrument_that_leans_on_a_resolution_refuses_the_rendering_of_noise():
    """⭐⭐⭐ ONE DEFECT, EIGHT INSTRUMENTS. ⛔ A fix written for one cause is not a fix.

    ⚠ Each is offered the copy and each must name the same cause. An instrument missing from
    the roster is not tested, so the roster is counted rather than iterated in silence.
    """
    offered = _offered_the_rendering_of_noise()
    assert len(offered) == RESOLUTIONS_THAT_ARE_EVIDENCE
    # ⛔⛔ AND THE ROSTER IS TIED TO THE MODULE, not maintained beside it. A guard added
    #    without a case here fails this line rather than passing quietly — which is how the
    #    one unmeasured guard was found.
    armed = inspect.getsource(saakshi.textual).count(
        "refuse_a_rendering_that_does_not_repeat("
    )
    assert armed == RESOLUTIONS_THAT_ARE_EVIDENCE + 1  # ⚠ +1: the definition itself
    for name, build in offered.items():
        with pytest.raises(TextualError, match="LITTLE IN THIS COPY REPEATS") as excinfo:
            build()
        assert "not the alphabet that is wrong" in str(excinfo.value), name


def test_the_row_no_longer_claims_a_presence_cannot_be_manufactured():
    """⛔⛔ A PUBLISHED SENTENCE THE MEASUREMENT REFUTED, PINNED SO IT CANNOT DRIFT BACK.

    The row carried *a reader can destroy the evidence of a presence but cannot manufacture
    it* as an unqualified claim. ⚠ Pinned by BOTH halves: the correction must be present and
    the unqualified form must be gone — a test that only forbids cannot tell a corrected
    sentence from a deleted one.
    """
    row = _attestation().as_row()
    limit = row["limit"]
    assert "A READER THAT RETURNS NOISE MANUFACTURES ONE" in limit
    assert "the_attesting_copy_repeats_itself" in limit
    assert "reader can destroy the evidence of a presence but cannot manufacture it" not in limit
    # ⭐ And the verdict-shape note says why the copy of noise scores nothing, correctly.
    assert "NOT because it can state nothing" in row["the_verdict_is_a_presence_not_an_absence"]


def test_a_locus_is_deliberately_not_guarded_and_the_reason_is_recorded():
    """⭐⭐ A LOCUS IS AN ADDRESS, NOT EVIDENCE — which is why the guard stops here.

    A locus says *these words are at this place in this copy*, and in a rendering of noise
    that is still true: a reader following it finds the words. ⛔ What a resolution cannot do
    there is stand as evidence FOR something, which is why every instrument that reasons from
    one carries the guard and this one does not. ⚠ Recorded as a test rather than as prose so
    that arming it later is a decision somebody has to take deliberately.
    """
    cited = Locus(
        source_kind="commentary",
        edition=A_RENDERING_OF_NOISE,
        locus="somewhere in the noise",
        interpretation_status="quoted",
        fragment=A_RENDERING_OF_NOISE.normalised[900:960],
    )
    assert cited.resolution.resolved
    # ⛔ And an Alignment built on two such loci is refused by the copies rather than by this
    #   guard: an anchor must resolve in BOTH copies, and one copy's noise is not another's.
    assert recurrence_of(A_RENDERING_OF_NOISE)["share_that_recurs"] < LEAST_RECURRENCE


# ==========================================================================================
# A FLOOR THAT REFUSES FOUR FIFTHS OF EVERY REAL BOOK IS NOT MEASURING THE RENDERING
# ==========================================================================================
#
# ⛔⛔⛔ The guard above was fitted to seven copies of a quarter of a million characters each
# and then applied to copies of any size. Tiled into consecutive blocks — complete, disjoint,
# every character of every copy in exactly one block — the floor refuses **12 338 of 15 563**
# two-hundred-character blocks of the real books held here, and 1 233 of 1 233 blocks of the
# rendering of noise. ⇒ Below a measured extent the two are refused ALIKE, and the instrument
# published *it is a machine reading that returned noise* for both.


#: ⭐⭐⭐ A COPY WHOSE CLEARING IS NON-MONOTONE IN THE EXTENT, BUILT FROM THE REAL MECHANISM.
#: Two copies of one passage separated by a stretch that repeats nothing are invisible to
#: every window shorter than that stretch: a window seeing one copy sees no repeat at all. So
#: this copy clears the floor at small extents (inside a short doubled phrase), refuses across
#: a band of middling ones, and clears AGAIN once a window is finally long enough to span both
#: copies of the passage.
#:
#: ⛔ That shape is not invented for the test. It is the shape a real rendering of noise has:
#: one specimen clears 21 850 windows at 100 000 characters and 25 497 at 150 000.
_A_DOUBLED_PHRASE = "और फिर वही बात आती है। "
#: ⚠ 190 characters, and the length is load-bearing twice over. A window spanning both
#: copies is lifted over the floor by about `len(passage) / extent`, so too short a passage
#: cannot lift a long window at all — at 98 characters the copy below never cleared above the
#: band and the test asserted a property its fixture did not have.
_A_PASSAGE_PRINTED_TWICE = (
    "यह वाक्य इस पुस्तक में दो बार छपा है और दोनों के बीच बहुत सारा ऐसा पाठ है जो "
    "कभी दुबारा नहीं आता। इसी तरह एक पुस्तक के हर पृष्ठ पर एक ही शीर्षरेखा छपती है "
    "और वह भी दूर दूर पर दुबारा आती है। "
)


def _clears_at_some_extents_and_not_at_others() -> Edition:
    """⛔ Built from DISJOINT slices of one noise string, never the same slice twice: two
    calls to `_noise` return the same characters, and reusing one would plant a repeat this
    copy is not supposed to have."""
    filler = _noise(40000)
    return _copy(
        filler[:2000]
        + _A_DOUBLED_PHRASE
        + _A_DOUBLED_PHRASE
        + filler[2000:4000]
        + _A_PASSAGE_PRINTED_TWICE
        + filler[4000:12000]
        + _A_PASSAGE_PRINTED_TWICE
        + filler[12000:26000],
        key="clears_at_some_extents_and_not_at_others",
    )


#: ⚠ Coarse on purpose. The default grid asks a thousand extents of this copy and the suite
#: runs in two seconds; eleven points are enough to show the property, and the points are
#: written here so the band between them is visible rather than implied.
_A_GRID_WITH_THE_BAND_IN_IT = (
    300, 1000, 1200, 1400, 2000, 4000, 8000, 8500, 12000, 19000, 20000, 24000,
)


def test_the_accepting_bound_is_a_supremum_and_not_the_first_extent_that_clears_nothing():
    """⛔⛔⛔ THE RULE THAT PUT THE REFUSING BOUND 1 686 CHARACTERS WRONG IS WRONG HERE TOO.

    `LEAST_EXTENT_A_REFUSAL_DISCRIMINATES_AT` read 6 000 for a session because it was taken as
    *the smallest extent at which nothing is refused*, and the count is not monotone: 7 450
    refused nothing, 7 500 refused 42. The accepting side is measured the same way and is not
    monotone either, so `largest_extent_at_which_a_window_clears` takes the **supremum**.

    ⭐ The two rules are told apart here by a copy that genuinely has a band — and the losing
    rule is written out in this test rather than described, because a rule nobody computes is
    a rule nobody has checked.
    """
    subject = _clears_at_some_extents_and_not_at_others()
    cleared_at = {
        extent: every_window_of(subject, extent=extent)["windows_cleared"]
        for extent in _A_GRID_WITH_THE_BAND_IN_IT
    }

    # ⛔ THE FIXTURE MUST HAVE THE PROPERTY, or the two rules agree and this proves nothing.
    #    Something clears low down, a whole band clears nothing, and something clears above it.
    assert cleared_at[300] > 0 and cleared_at[1000] > 0 and cleared_at[1200] > 0
    assert all(cleared_at[extent] == 0 for extent in (1400, 2000, 4000, 8000))
    assert cleared_at[8500] > 0 and cleared_at[12000] > 0 and cleared_at[19000] > 0
    assert cleared_at[20000] == 0 and cleared_at[24000] == 0

    # ⛔ The rule this function must NOT use, computed here from scratch.
    the_wrong_rule = next(
        extent for extent in _A_GRID_WITH_THE_BAND_IN_IT if cleared_at[extent] == 0
    )
    assert the_wrong_rule == 1400

    measured = largest_extent_at_which_a_window_clears(
        subject, grid=_A_GRID_WITH_THE_BAND_IN_IT
    )
    assert measured["largest_extent_at_which_a_window_clears"] == 19000
    assert measured["the_accepting_bound_this_copy_alone_would_set"] == 19001
    # ⭐ THIRTEEN TIMES APART, and the wrong rule is the one that looks safe.
    assert measured["largest_extent_at_which_a_window_clears"] > 13 * the_wrong_rule
    assert measured["extents_at_which_some_window_clears"] == 6
    assert measured["extents_checked"] == len(_A_GRID_WITH_THE_BAND_IN_IT)


def test_a_bound_carries_the_grid_it_was_taken_on():
    """⚠ A BOUND QUOTED WITHOUT ITS GRID READS AS EXACT AND THIS ONE IS A GRID POINT.

    The refusing side published 2 000 for one held-out body only because its grid jumped
    2 000 → 5 000. ⭐ So `one_per_cent_grid` is a named thing, its resolution is a property
    anyone can check, and every row a bound appears on carries the grid beside it.
    """
    grid = one_per_cent_grid(50000)
    assert grid[0] == 300
    assert grid[-1] <= 50000
    # ⛔ The property, recomputed here rather than trusted: no step is coarser than one per
    #    cent of where it lands, so a bound is located to within one per cent of itself.
    for lower, upper in zip(grid, grid[1:]):
        assert upper > lower
        assert (upper - lower) <= max(1, upper / 100)
    # ⭐ And it is a grid, not a continuum: it does NOT contain every integer.
    assert len(grid) < 50000 - 300

    # ⚠ The row says which grid it was taken on, so a value read off a coarser one is not
    #   mistaken for a value read off this.
    subject = _clears_at_some_extents_and_not_at_others()
    said = largest_extent_at_which_a_window_clears(
        subject, grid=_A_GRID_WITH_THE_BAND_IN_IT
    )["the_grid_it_was_taken_on"]
    assert said["points"] == len(_A_GRID_WITH_THE_BAND_IN_IT)
    assert said["least"] == 300 and said["greatest"] == 24000


def test_the_extent_a_refusal_discriminates_at_is_the_measured_one():
    """⚠ Pinned, because it is fitted — and because it MOVED, by 1 686 characters.

    ⛔⛔⛔ It read 6 000 for a session. That was the smallest tiling size at which no *block*
    of any real copy is refused, and the tiling reads one phase of the windows a copy actually
    contains — 283 of 1 675 741 at that extent. Asked of every window, 6 000 refuses 5 593 of
    them and the supremum is 7 685. ⭐ The two numbers are both pinned, so a revert to the old
    one cannot pass as a re-measurement.
    """
    assert LEAST_EXTENT_A_REFUSAL_DISCRIMINATES_AT == 7686
    assert LEAST_EXTENT_A_REFUSAL_DISCRIMINATES_AT != 6000
    # ⭐ And it is published on every row a share is, because a share cannot be read alone.
    row = recurrence_of(A_RENDERING_OF_NOISE)
    assert row["characters_measured"] == A_RENDERING_OF_NOISE.searchable_characters
    assert row["the_extent_a_low_share_means_anything_at"] == LEAST_EXTENT_A_REFUSAL_DISCRIMINATES_AT
    assert row["a_low_share_here_is_about_the_copy"] is True
    # ⛔⛔⛔ AND THE OTHER SIDE, WHICH HAS NO BOUND TO PUT HERE. The row used to carry a
    #    number and a `True`; both were read off ONE specimen and the number was 1 016x too
    #    small. What it carries now is the largest extent at which a rendering of noise HAS
    #    cleared this floor, and a sentence saying no extent has been established.
    assert row["the_greatest_extent_at_which_a_window_of_a_refused_copy_has_cleared"] == (
        GREATEST_EXTENT_AT_WHICH_A_WINDOW_OF_A_REFUSED_COPY_HAS_CLEARED
    )
    assert row["this_copy_is_longer_than_that"] is False
    # ⛔⛔⛔ THE WITHDRAWAL IS OWED IN TWO DIRECTIONS NOW, AND EACH IS PINNED BY ITS OWN
    #    WORDS. It used to read "NOT ESTABLISHED AT ANY EXTENT", which withdrew only the
    #    EXTENT claim; three whole copies this floor accepts are now certified wrong-script
    #    readings, so what has to be withdrawn is the VALUE claim as well. ⭐ Asserting the
    #    words owed rather than that some withdrawal is present: a guard test that accepts
    #    any refusal is satisfied by a different guard than the one it was written for.
    assert "NOT ESTABLISHED, AT ANY EXTENT OR ANY VALUE" in (
        row["a_high_share_here_is_about_the_copy"]
    )
    assert "0.030511" in row["a_high_share_here_is_about_the_copy"]
    assert str(LEAST_COPIES_THIS_FLOOR_MISCLASSIFIES_AT_ANY_VALUE) in (
        row["a_high_share_here_is_about_the_copy"]
    )
    assert row["the_greatest_share_a_wrong_script_reading_reaches"] == (
        GREATEST_SHARE_A_WRONG_SCRIPT_READING_REACHES
    )
    # ⚠ The correction to the published sentence, present: a near-zero share means what it
    #   says ONLY above the extent. ⛔ Pinned by the qualification rather than by the number,
    #   which appears in the same sentence for a different reason.
    assert "ONLY WHERE THE COPY IS LARGE ENOUGH" in row["what_a_share_near_zero_means"]


def test_a_copy_under_the_extent_is_refused_for_its_size_and_not_for_being_noise():
    """⛔⛔⛔ THE DEFECT: A REFUSAL THAT NAMED A CAUSE NOBODY MEASURED.

    A page of a real book, offered on its own, repeats nothing — there has not been enough of
    it for anything to come round twice. ⭐ It is still refused, and it must be: a resolution
    in it is free for the same reason it is free in noise. ⚠ What it must NOT be told is that
    it is a machine reading that returned noise, because nothing here measured that.
    """
    a_page = edition(
        "Chapter twelve. The lord of the ninth from the karaka is examined first, "
        "and the sign it occupies is noted before any aspect upon it is weighed. "
        "Where two claims fall together the elder is preferred, unless a benefic "
        "stands in the eleventh from either, in which case neither is dropped.",
        kind="translation",
    )
    assert a_page.searchable_characters < LEAST_EXTENT_A_REFUSAL_DISCRIMINATES_AT
    assert recurrence_of(a_page)["share_that_recurs"] < LEAST_RECURRENCE  # ⚠ as a real page does
    with pytest.raises(TextualError) as excinfo:
        refuse_a_rendering_that_does_not_repeat(
            a_page, what_it_would_make_free="a presence quoted out of it"
        )
    said = str(excinfo.value)
    assert "THE CAUSE IS THE EXTENT AND NOT THE RENDERING" in said
    assert "Nothing measured says this is a machine reading that returned noise" in said
    # ⛔⛔ BOTH HALVES. A test asserting only the new sentence cannot tell a corrected cause
    #    from one printed beside the old one, so the old verdict must be gone from this
    #    refusal — and it is the VERDICT that must be gone, not the words, which the sentence
    #    above quotes in order to withdraw them.
    assert "NOTHING IN THIS COPY REPEATS" not in said
    assert "LITTLE IN THIS COPY REPEATS" not in said
    assert "It is a machine reading that returned noise" not in said
    assert "not the alphabet that is wrong" not in said
    # ⭐ And the branch that IS about the rendering names itself, so this one must not.
    assert "THE EXTENT IS NOT THE CAUSE" not in said


def test_the_fixture_that_stood_in_for_noise_was_itself_under_the_extent():
    """⛔⛔⛔ AND SO NO TEST IN THIS FILE COULD HAVE CAUGHT IT — TWICE OVER NOW.

    The previous session found every copy built here repeated nothing, which is the property
    of noise itself. This one finds the copy built to BE noise was 1 799 characters — an
    extent at which four fifths of every real book held is refused by the same floor. ⇒ The
    roster test certified a refusal the fixture's SIZE earned. ⭐ Driven off its own value:
    the old fixture is rebuilt here and shown to earn the extent cause, so growing it was a
    correction rather than a decoration.
    """
    as_it_was = _copy(_noise(1500), key="the_fixture_as_it_stood")
    assert as_it_was.searchable_characters == 1799
    assert as_it_was.searchable_characters < LEAST_EXTENT_A_REFUSAL_DISCRIMINATES_AT
    with pytest.raises(TextualError, match="THE CAUSE IS THE EXTENT"):
        refuse_a_rendering_that_does_not_repeat(
            as_it_was, what_it_would_make_free="the attestation"
        )

    # ⛔⛔⛔ AND THE REPAIR WAS UNDERSIZED TOO, WHICH IS THE THIRD SESSION RUNNING THAT THIS
    #    FILE'S OWN TEST BED WAS THE SUBJECT. It was grown to 7 199 characters to clear a
    #    `LEAST_EXTENT_A_REFUSAL_DISCRIMINATES_AT` of 6 000; when that constant was measured
    #    over every window instead of one tiling phase it came out 7 686, and the repair went
    #    back under the bound without a single test noticing. ⭐ Rebuilt here and shown to
    #    earn the extent cause, so growing it again is a correction and not a decoration.
    the_repair = _copy(_noise(6000), key="the_fixture_as_it_was_repaired")
    assert the_repair.searchable_characters == 7199
    assert the_repair.searchable_characters < LEAST_EXTENT_A_REFUSAL_DISCRIMINATES_AT
    with pytest.raises(TextualError, match="THE CAUSE IS THE EXTENT"):
        refuse_a_rendering_that_does_not_repeat(
            the_repair, what_it_would_make_free="the attestation"
        )
    # ⭐⭐ And the copy standing there NOW earns the rendering's cause, not its size's. That
    #   is the positive half: without it this test would pass with the fixture at any size.
    with pytest.raises(TextualError, match="LITTLE IN THIS COPY REPEATS"):
        refuse_a_rendering_that_does_not_repeat(
            A_RENDERING_OF_NOISE, what_it_would_make_free="the attestation"
        )

    # ⭐ The generator is prefix-stable, so each copy that replaced one is the same text plus
    #   more of it — every offset quoted out of it elsewhere in this file still resolves.
    assert the_repair.normalised.startswith(as_it_was.normalised)
    assert A_RENDERING_OF_NOISE.normalised.startswith(the_repair.normalised)


def test_a_tiling_phase_is_a_sample_of_the_windows_and_that_is_how_the_bound_went_wrong():
    """⛔⛔⛔ THE DEFECT, IN MINIATURE AND DRIVEN OFF ITS OWN VALUE.

    `blocks_this_floor_refuses` is complete over a copy's **characters** — every one of them
    in exactly one block, no overlap — and it says so. The question a bound on the extent asks
    is a different one: *is there a specimen of real text this long that the floor refuses?*
    The specimens are the copy's **windows**, and one tiling phase reads a vanishing share of
    them. ⇒ ⭐⭐⭐ *A measurement can be complete over what it counts and a sample of what it
    is about.*

    The copy below puts an unrepeating stretch of one block's length straddling a block
    boundary. Every block is half language, so the tiling refuses **nothing** and reports the
    extent sound; a window starting mid-block is the unrepeating stretch entire, and it is
    refused. ⚠ That is exactly the shape that put 6 000 in this file for a session.
    """
    boundary = 600
    half = boundary // 2
    repeating = REPEATS_LIKE_A_BOOK_IN_THE_ORIGINALS_SCRIPT * 40
    # ⭐ Half a block of language, then a whole block of noise, then the rest language: the
    #   unrepeating stretch lands ACROSS the boundary rather than inside a block.
    straddles = _copy(
        repeating[:half] + _noise(boundary)[:boundary] + repeating[: boundary + half],
        key="the_defect_in_miniature",
    )
    tiled = blocks_this_floor_refuses(straddles, block=boundary)
    windows = every_window_of(straddles, extent=boundary)
    # ⛔ The tiling: clean. It would license `boundary` as an extent this floor discriminates at.
    assert tiled["blocks"] >= 2
    assert tiled["blocks_refused"] == 0
    # ⭐ Every window, over the same copy at the same extent: it does not.
    assert windows["windows"] == straddles.searchable_characters - boundary + 1
    assert windows["windows_refused"] > 0
    assert windows["refused_regions"] == 1  # ⚠ one passage, not a scattering
    # ⛔⛔ And the tiling read this fraction of the specimens — the number that matters.
    assert tiled["blocks"] < windows["windows"] / 100
    # ⛔⛔⛔ AND THE WINDOW INSTRUMENT MUST BE READING EVERY OFFSET, not every `extent`-th one.
    #    Pinned by the count itself: one window per offset, and one fewer for each character
    #    the extent grows by. An instrument that sampled would still report a refused region.
    assert windows["windows"] == straddles.searchable_characters - boundary + 1
    assert every_window_of(straddles, extent=boundary + 1)["windows"] == windows["windows"] - 1


def test_every_window_of_counts_both_sides_of_the_floor():
    """⛔ A WINDOW COUNT THAT PUBLISHES ONLY REFUSALS IS HOW THE ACCEPTING SIDE WENT UNMEASURED.

    Which of the two counts is the error depends on what the copy is: for a real book a
    refusal is the error, for a rendering of noise a clearance is. So both are returned, and
    an instrument that reported one of them could not have found either bound.

    ⛔⛔⛔ **THE FIRST VERSION OF THIS TEST COULD NOT FAIL, AND IT WAS WRITTEN THIS SESSION
    AGAINST EXACTLY THAT.** It asked the identity of the rendering of noise, where every
    window is refused and `windows_cleared` is zero anyway — so an instrument hard-wired to
    report zero cleared windows passed it. Found by disarming the field. ⇒ ⭐⭐⭐ *A control
    must be asked of a subject on which it can come out wrong*, which for a count of the
    accepting side means a copy some of whose windows are accepted.
    """
    # ⭐ The subject that can fail: a copy with windows on BOTH sides of the floor.
    boundary = 600
    half = boundary // 2
    repeating = REPEATS_LIKE_A_BOOK_IN_THE_ORIGINALS_SCRIPT * 40
    mixed = _copy(
        repeating[:half] + _noise(boundary)[:boundary] + repeating[: boundary + half],
        key="a_copy_with_windows_on_both_sides",
    )
    both = every_window_of(mixed, extent=boundary)
    assert both["windows_refused"] > 0
    assert both["windows_cleared"] > 0  # ⛔ THE ASSERTION THE OLD SUBJECT COULD NOT CARRY
    assert both["windows_refused"] + both["windows_cleared"] == both["windows"]
    assert both["least_share"] < LEAST_RECURRENCE <= both["greatest_share"]

    # ⚠ And the noise copy, where the count is one-sided and the identity still holds.
    measured = every_window_of(A_RENDERING_OF_NOISE, extent=400)
    assert measured["windows_refused"] + measured["windows_cleared"] == measured["windows"]
    assert measured["windows_cleared"] == 0  # ⭐ noise, above the accepting bound
    assert measured["greatest_share"] < LEAST_RECURRENCE

    # ⚠ And a copy too short for one window says so rather than returning a zero.
    empty = every_window_of(SECOND_TRANSLATION, extent=100_000)
    assert empty["windows"] == 0
    assert "fewer than the" in empty["why_there_are_none"]


def test_every_window_of_agrees_with_a_naive_reading_of_its_own_definition():
    """⛔⛔⛔ THE INSTRUMENT THE CORRECTED BOUND RESTS ON HAD NOTHING MEASURING IT.

    `every_window_of` slides an incremental counter — one fragment out, one fragment in — and
    an incremental counter is exactly the kind of thing that can drift back into reading every
    `extent`-th window instead of every window, which is the sampling this session was spent
    undoing. ⚠ Disarming it that way broke nothing: the miniature-defect test still saw a
    refused region and still passed.

    ⭐ So it is checked against a second, naive implementation of the same definition —
    recounted from scratch at every offset, no shared state — over a fixture small enough to
    afford it. ⛔ The naive one is written here rather than imported, because an instrument
    checked against itself has been checked against nothing.
    """
    boundary = 200
    subject = _copy(
        (REPEATS_LIKE_A_BOOK_IN_THE_ORIGINALS_SCRIPT * 6)[:300]
        + _noise(200)[:200]
        + (REPEATS_LIKE_A_BOOK_IN_THE_ORIGINALS_SCRIPT * 6)[:300],
        key="checked_against_a_naive_reading",
    )
    body = subject.normalised
    length = RECURRENCE_MEASURED_AT

    naive_refused = 0
    naive_cleared = 0
    shares = []
    for start in range(len(body) - boundary + 1):
        window = body[start : start + boundary]
        counts: dict[str, int] = {}
        for at in range(len(window) - length + 1):
            fragment = window[at : at + length]
            counts[fragment] = counts.get(fragment, 0) + 1
        recurring = sum(1 for seen in counts.values() if seen > 1)
        share = recurring / len(counts) if counts else 0.0
        shares.append(share)
        if share < LEAST_RECURRENCE:
            naive_refused += 1
        else:
            naive_cleared += 1

    measured = every_window_of(subject, extent=boundary)
    assert measured["windows"] == len(shares)
    assert measured["windows_refused"] == naive_refused
    assert measured["windows_cleared"] == naive_cleared
    assert measured["least_share"] == round(min(shares), 6)
    assert measured["greatest_share"] == round(max(shares), 6)
    # ⛔ And the subject must have windows on both sides, or the agreement is trivial.
    assert naive_refused > 0 and naive_cleared > 0


def test_the_accepting_side_is_disarmed_and_the_reason_is_measured():
    """⛔⛔⛔ IT WAS ARMED LAST SESSION AT 315, ON ONE SPECIMEN. THE SECOND SPECIMEN MOVED IT.

    The accepting bound is the largest extent at which a window of a rendering of noise still
    CLEARS the floor. Over the single such rendering this repository then held it is **314**,
    and that number was published as *the extent at which clearing this floor says something
    about a copy*. ⛔ Thirty-two further specimens — drawn from the same public collection by
    two declared draws, every copy either draw returned that the floor refuses — put it at
    **320 000**: one of them carries no language at all and clears this floor over windows
    spanning 96.69 % of itself.

    ⇒ ⭐⭐⭐ **ARMED AT 315 THE GUARD WAS WORSE THAN ABSENT.** A caller reads what a guard
    passes as checked, so it certified the entire band from 315 to 320 000 — which is where
    every copy anyone would offer lives — on a number a thousand times too small.

    ⚠ And it cannot simply be raised. At 320 000 it refuses every fixture in this file, and
    there is no honest smaller value: the extent at which a specimen stops clearing tracks how
    close its own share sits to the floor, so the next specimen moves it again.
    """
    assert GREATEST_EXTENT_AT_WHICH_A_WINDOW_OF_A_REFUSED_COPY_HAS_CLEARED == 320000
    # ⛔ The old value, pinned as WRONG, so a revert cannot pass as a re-measurement.
    assert GREATEST_EXTENT_AT_WHICH_A_WINDOW_OF_A_REFUSED_COPY_HAS_CLEARED != 315
    # ⭐ And it is the far side of the refusing bound now, where it used to be 24x below it.
    assert (
        GREATEST_EXTENT_AT_WHICH_A_WINDOW_OF_A_REFUSED_COPY_HAS_CLEARED
        > 40 * LEAST_EXTENT_A_REFUSAL_DISCRIMINATES_AT
    )

    # ⛔⛔⛔ THE DISARM ITSELF. A copy that CLEARS the floor and is far under the number is
    #    NOT refused - which is the behaviour this test exists to pin, because the previous
    #    session's test pinned the opposite.
    short_and_repeating = _copy(
        (REPEATS_LIKE_A_BOOK_IN_THE_ORIGINALS_SCRIPT * 4)[:200], key="short_but_repeating"
    )
    assert short_and_repeating.searchable_characters < 315
    assert recurrence_of(short_and_repeating)["share_that_recurs"] >= LEAST_RECURRENCE
    passed = refuse_a_rendering_that_does_not_repeat(
        short_and_repeating, what_it_would_make_free="the attestation"
    )
    assert passed["share_that_recurs"] >= LEAST_RECURRENCE

    # ⛔⛔ BUT PASSING IS NOT CERTIFYING, and the row it returns has to say so in its own
    #    words. This is the whole of what replaced the refusal.
    assert passed["this_copy_is_longer_than_that"] is False
    assert "NOT ESTABLISHED, AT ANY EXTENT OR ANY VALUE" in (
        passed["a_high_share_here_is_about_the_copy"]
    )
    assert passed["the_greatest_extent_at_which_a_window_of_a_refused_copy_has_cleared"] == 320000
    # ⛔ And the value side of the same withdrawal, on the row a PASS returns.
    assert passed["the_greatest_share_a_wrong_script_reading_reaches"] == 0.030511
    assert passed["this_copy_repeats_more_than_that"] is (
        passed["share_that_recurs"] > 0.030511
    )

    # ⛔⛔⛔ AND THE COST OF ARMING IT, MEASURED RATHER THAN ASSERTED. Every fixture this file
    #    builds an attestation or an absence on is orders of magnitude under the number, so an
    #    armed guard refuses all of them - including the copy that IS a rendering of noise,
    #    which is refused for its rendering and would additionally be refused for its size.
    for fixture in (
        SECOND_TRANSLATION,
        REVISED_TRANSLATION,
        A_COPY_THAT_REPEATS_BUT_LACKS_THE_PASSAGE,
        A_RENDERING_OF_NOISE,
    ):
        assert (
            fixture.searchable_characters
            < GREATEST_EXTENT_AT_WHICH_A_WINDOW_OF_A_REFUSED_COPY_HAS_CLEARED
        )
    # ⚠ The largest of them is still four hundred times under it. Growing a fixture is not a
    #   route to arming this side, and that is why the arm went rather than the fixtures.
    assert (
        max(
            fixture.searchable_characters
            for fixture in (SECOND_TRANSLATION, A_RENDERING_OF_NOISE)
        )
        * 30
        < GREATEST_EXTENT_AT_WHICH_A_WINDOW_OF_A_REFUSED_COPY_HAS_CLEARED
    )


def test_each_refusal_names_its_own_branch_and_neither_is_sorted_by_its_prose():
    """⛔⛔⛔ THE SENTENCE TWO BRANCHES WERE SORTED BY IS GONE FROM ONE OF THEM.

    Until this session `refuse_a_rendering_that_does_not_repeat` ended its rendering branch
    *"It is a machine reading that returned noise"*, and the extent branch denied that
    sentence by quoting it — ⛔ so every reader sorting the two had to test the extent branch
    FIRST or read the denial as the verdict. That trap was pinned here, and the census that
    gathered this file's refused copies had already fallen into it.

    ⛔⛔⛔ **AND THEN THE VERDICT ITSELF WAS WITHDRAWN, WHICH BREAKS THE SORT THE OTHER WAY.**
    The diagnosis is measured to be false of copies this branch fires on — see
    `LEAST_RECURRENCE` — so the branch no longer contains the sentence at all. ⚠ A reader
    still sorting on it now classifies **every** refused copy as neither branch, and reports
    it as nothing in particular: *a string-matched branch detector fails silently in whichever
    direction the message last moved.*

    ⇒ ⭐⭐⭐ **SO NEITHER BRANCH IS SORTED BY ITS PROSE ANY MORE. EACH NAMES ITSELF**, and this
    test pins both markers, their exclusivity, and the fact that the withdrawn sentence can no
    longer sort anything.
    """
    noise = A_RENDERING_OF_NOISE
    tiny = _copy(_noise(60)[:200], key="too_small_to_say_anything")
    assert tiny.searchable_characters < LEAST_EXTENT_A_REFUSAL_DISCRIMINATES_AT
    assert noise.searchable_characters > LEAST_EXTENT_A_REFUSAL_DISCRIMINATES_AT

    with pytest.raises(TextualError) as for_the_rendering:
        refuse_a_rendering_that_does_not_repeat(noise, what_it_would_make_free="a claim")
    with pytest.raises(TextualError) as for_the_extent:
        refuse_a_rendering_that_does_not_repeat(tiny, what_it_would_make_free="a claim")

    rendering_said, extent_said = str(for_the_rendering.value), str(for_the_extent.value)
    withdrawn = "a machine reading that returned noise"

    # ⛔ THE VERDICT IS GONE FROM THE BRANCH THAT USED TO CARRY IT, and the extent branch
    #   still quotes it in order to deny it — so the old sort now returns the WRONG branch
    #   for the copy it was written to catch, rather than none.
    assert withdrawn not in rendering_said
    assert withdrawn in extent_said
    # ⭐ It is the VERDICT that is gone, not the words: the branch says in terms that nothing
    #   here establishes it, which is a withdrawal and not a silence.
    assert "NOTHING HERE SAYS IT IS A MACHINE READING THAT RETURNED NOISE" in rendering_said
    assert "Nothing measured says this is a machine reading that returned noise" in extent_said

    # ⭐ Each branch's own marker. Unambiguous, and exclusive both ways.
    extent_marker = "THE CAUSE IS THE EXTENT AND NOT THE RENDERING"
    rendering_marker = "THE EXTENT IS NOT THE CAUSE"
    assert extent_marker in extent_said and extent_marker not in rendering_said
    assert rendering_marker in rendering_said and rendering_marker not in extent_said

    def certify(said: str) -> str:
        """⭐ Order-free, because the two markers cannot both appear — asserted above."""
        if extent_marker in said:
            return "refused_for_its_extent"
        if rendering_marker in said:
            return "refused_for_its_recurrence"
        return "refused_for_another_reason"

    assert certify(rendering_said) == "refused_for_its_recurrence"
    assert certify(extent_said) == "refused_for_its_extent"

    # ⛔⛔ A CONTROL THAT CANNOT COME OUT WRONG: the sort this test replaces, run here, and
    #    shown to misreport BOTH copies. Without this the repair above is only asserted.
    def the_old_sort(said: str) -> str:
        if withdrawn in said:
            return "refused_as_a_rendering_of_noise"
        return "refused_for_another_reason"

    assert the_old_sort(rendering_said) == "refused_for_another_reason"  # ⛔ it IS that
    assert the_old_sort(extent_said) == "refused_as_a_rendering_of_noise"  # ⛔ it is NOT


def test_the_specimens_the_accepting_side_rests_on_are_still_there():
    """⚠ THE NUMBER IS A MAXIMUM OVER A SET, SO THE SET IS PART OF THE MEASUREMENT.

    `GREATEST_EXTENT_AT_WHICH_A_WINDOW_OF_A_REFUSED_COPY_HAS_CLEARED` is 320 000 because
    thirty-two specimens were held out against it. ⛔ Silently losing them — a truncated
    table, a bad merge — would leave the constant standing on the one copy it stood on
    before, and **nothing else in this suite would notice**, because the constant is a
    literal and the specimens live in another module.

    ⚠ This checks the registry, not the copies: the copies are acquired third-party material
    under a git-ignored cache, and a test that required them would fail on a fresh clone.
    """
    from saakshi.texts import COPIES_THIS_FLOOR_REFUSES_KEYS, SOURCES

    assert len(COPIES_THIS_FLOOR_REFUSES_KEYS) >= 32
    # ⛔ Distinct copies, not one copy registered thirty-two times.
    addresses = {SOURCES[key].address for key in COPIES_THIS_FLOOR_REFUSES_KEYS}
    assert len(addresses) == len(COPIES_THIS_FLOOR_REFUSES_KEYS)
    filenames = {SOURCES[key].filename for key in COPIES_THIS_FLOOR_REFUSES_KEYS}
    assert len(filenames) == len(COPIES_THIS_FLOOR_REFUSES_KEYS)
    # ⭐ Each says in its own identity that it is held as a SPECIMEN and not as a work, so a
    #   reader meeting one in a fixture cannot take it for a copy this repository reasons from.
    for key in COPIES_THIS_FLOOR_REFUSES_KEYS:
        identity = SOURCES[key].identity
        assert "HELD AS A SPECIMEN OF THE READING, NOT AS A COPY OF THE WORK" in identity
        assert SOURCES[key].language == "und"
    # ⛔⛔ And both draws are represented. The first draw is the one that found the defect and
    #    the one whose shape was its answer; dropping it would erase the accounting.
    drawn = " ".join(SOURCES[key].identity for key in COPIES_THIS_FLOOR_REFUSES_KEYS)
    assert "the head of the collection" in drawn
    assert "bucket" in drawn


def test_each_constant_publishes_what_it_was_fitted_to_and_what_held_it_out():
    """⚠ THREE CONSTANTS FITTED TO ONE SET OF COPIES, AND A COPY DISAGREEING WITH ALL THREE
    WOULD LOOK EXACTLY LIKE ONE DISAGREEING WITH NONE.

    That is an argument, and what answers an argument about a constant is a held-out
    measurement — which `generators/r6_karaka_rules.py` now takes, over four bodies it has
    never loaded. ⭐ All three transfer. What this test pins is that the answer is written
    where the constant is READ, and that it is written with its limits rather than as a
    clean bill.

    ⛔⛔⛔ AND THE LIMIT THAT MATTERED MOST HAS SINCE BEEN MEASURED. This test used to pin
    the sentence *⚠ Fitted to **one** copy* on the accepting bound — a limit correctly
    published and then left standing for a session. Thirty-two specimens later that bound is
    gone, so what is pinned here now is that the constant which replaced it says it is a
    **maximum and not a bound**, and says what it is a function of.
    """
    published = inspect.getsource(saakshi.textual)
    # ⭐ Each of the constants that IS fitted says out loud that it is fitted, not derived.
    assert "⚠ Fitted, exactly as `LEAST_RECURRENCE` is" in published
    assert "**not a law about renderings**" in published
    # ⛔ And the one that is not a bound at all refuses to be read as one.
    assert "A MEASURED MAXIMUM, NOT A BOUND" in published
    assert "a lower bound on itself" in published
    # ⛔⛔ The withdrawn limit must be GONE, not left standing beside its own correction:
    #    a copy fitted to ONE specimen is no longer what this number is.
    assert "⚠ Fitted to **one** copy" not in published
    # ⭐⭐ And the refusing extent carries the held-out result, with the bodies named.
    assert "four bodies it was **not** fitted to" in published
    assert "held-out evidence it transfers and is not tight" in published
    # ⭐⭐ And the floor carries its own held-out result, including the shrunken margin.
    assert "AND IT TRANSFERS, BUT THE FITTED SET IS THE FLATTERING ONE" in published
    assert "overstates the headroom by a" in published
    # ⛔ The weakest number must be labelled the weakest number, at the point of reading.
    #   ⚠ It used to be labelled *the weaker of the two*, which reads as a ranking between
    #   two comparable things. It is not one: nothing establishes it at all.
    assert "It is the weaker of the two numbers and it says so." not in published
    assert "will rise again with" in published


def test_the_decision_taken_on_the_accepting_side_is_published_and_the_old_one_withdrawn():
    """⛔ A DECISION THAT LIVES ONLY IN A COMMIT MESSAGE IS NOT A DECISION A READER CAN FIND.

    ⭐⭐ **BOTH HALVES.** A test asserting only the new sentence cannot tell a corrected
    decision from one printed beside the withdrawn one — the same defect this file fixed for
    `a_reader_cannot_manufacture_the_evidence_of_a_presence`. So the DISARMING is pinned
    present with the measurement under it, and the arming this session withdrew — together
    with the 314 it was read off — is pinned **absent**.

    ⛔⛔⛔ THIS TEST HAS NOW PINNED TWO OPPOSITE DECISIONS ON THE SAME QUESTION IN TWO
    SESSIONS, and that is the point of it: each time, what it refuses to allow is the old
    sentence surviving next to the new one where a reader would meet both and believe the
    first.
    """
    published = inspect.getsource(saakshi.textual)
    # ⭐ The disarming, and the measured counter-example it rests on.
    assert "THE ACCEPTING SIDE IS NOT ARMED" in published
    assert "ARMED AT 315 THIS GUARD WAS WORSE THAN ABSENT" in published
    assert "96.69 % of itself" in published
    # ⭐⭐ And the reason the fifteenth session gave, restored on the right number.
    assert "right and the number it was argued with was wrong" in published
    # ⛔ The withdrawn decision must be GONE, not merely outvoted by a newer paragraph.
    assert "That is a decision, not a" not in published
    assert "It is recorded here so that arming it later is" not in published
    assert "THE ACCEPTING SIDE, ARMED." not in published
    assert "the largest extent at which any window of it clears this floor is **314**" not in published
    # ⛔⛔ The phase defect, published where the constant is read.
    assert "the word \"complete\" was true of the wrong noun" in published.lower()


# ======================================================================================
# ⛔⛔⛔ WHAT LANGUAGE A COPY CARRIES — the measurement that falsified the floor's diagnosis
# ======================================================================================

#: A short passage of real Devanagari Hindi, written out here rather than loaded, because the
#: copies are third-party material under a git-ignored cache and a test that needed them
#: would fail on a fresh clone.
_REAL_DEVANAGARI = (
    "यदि लग्न में शुभ ग्रह स्थित हो तो उसके अनुसार फल होता है । इसके अतिरिक्त जिस "
    "स्थान में पाप ग्रह हो उसके प्रकार का विचार करने के लिए अपने ही नियम हैं । "
    "किन्तु यहाँ तत्र और तस्य का प्रयोग नहीं किया गया है । अत्र सर्व प्रकार से "
    "यह अस्ति कि जो भवति वह चाहिए के अनुसार ही होती है । "
)


def _syllables_and_no_words(syllables: int) -> str:
    """Devanagari syllables in which no word of any language occurs. ⚠ Built, not quoted.

    ⭐ A consonant and a vowel sign, which is what a machine reading set to the wrong script
    actually returns — and what `_noise` does NOT return, because it emits bare consonants.
    """
    consonants = "कखगघचछजझटठडढणतथदधनपफबभमयरलवशषसह"
    signs = "ािीुूेैोौ"
    out, state, wanted, in_word = [], 11, 1, 0
    for _ in range(syllables):
        state = (state * 1103515245 + 12345) % 2147483648
        out.append(consonants[state % len(consonants)])
        out.append(signs[(state // len(consonants)) % len(signs)])
        in_word += 1
        # ⚠ Words of one, two and three syllables in turn. ⛔ A reader that returned only
        #   long ones could not produce the single-syllable word this rule exists to keep
        #   out, and the control would pass while measuring nothing.
        if in_word == wanted:
            out.append(" ")
            in_word, wanted = 0, wanted % 3 + 1
    return "".join(out)


def test_a_word_is_cut_with_its_marks_and_the_bucket_that_cannot_cut_one():
    """⛔⛔⛔ `script_of` ASKS `isalpha`, AND A DEVANAGARI VOWEL SIGN IS NOT A LETTER.

    That bucket is right about the question it answers — *could this rendering express this
    alphabet at all* — and cutting words on it is a different question. A matra, a virama and
    a nukta are combining marks, so `isalpha` is `False` for every one of them and a word cut
    on that rule falls apart at its first vowel.

    ⭐ **A CONTROL THAT CANNOT COME OUT WRONG: the wrong rule is written out here and run.**
    Asserting only that the right rule works cannot tell a repair from a coincidence.
    """
    body = normalise(_REAL_DEVANAGARI)

    def cut_on_script_of(text: str) -> list[str]:
        """⛔ The rule this instrument must NOT use, reimplemented from its definition."""
        pieces, current = [], []
        for character in text:
            if script_of(character) is not None:
                current.append(character)
            elif current:
                pieces.append("".join(current))
                current = []
        if current:
            pieces.append("".join(current))
        return pieces

    wrong = cut_on_script_of(body)
    right = words_of(body)
    assert wrong, "the wrong rule must still return something, or this proves nothing"
    mean_wrong = sum(len(piece) for piece in wrong) / len(wrong)
    mean_right = sum(len(word) for word in right) / len(right)
    # ⛔ The debris is measurably shorter, and it is shorter because the marks are gone.
    assert mean_wrong < mean_right / 1.5
    assert "यदि" in right and "यदि" not in wrong
    # ⭐ And nothing is lost the other way: every letter of the body is still inside a word.
    assert sum(1 for c in body if c.isalpha()) == sum(
        1 for word in right for c in word if c.isalpha()
    )
    # ⚠ A run of bare marks is not a word.
    assert words_of("ािे") == ()


def test_the_length_rule_is_enforced_from_the_declared_list_and_not_by_hand():
    """⛔⛔⛔ A WORD LIST IS NOT A MEASUREMENT UNTIL ITS SHORTEST TERM IS LONGER THAN NOISE.

    The declared list carries two-character particles. They are declared — a reader must see
    what was considered — and `declared_words_of` drops them, because a two-character
    Devanagari word is one syllable and a wrong-script reader produces syllables by the
    thousand. ⛔ On the real evidence this was not hypothetical: with them left in, a machine
    reading of an English book of 1993 set to an Indic script scored 370.4 declared words per
    ten thousand, above a Sanskrit commentary read in its own script at 329.9, and the whole
    of that reading was `वा` occurring 744 times.

    ⭐ **THE CONTROL IS THE FAILURE ITSELF**: the same count is taken here with the rule off,
    over a copy carrying no Sanskrit at all, and it must come out non-zero.
    """
    declared = COMMONEST_WORDS["sanskrit_or_hindi"]
    used = declared_words_of("sanskrit_or_hindi")
    assert set(used) < set(declared), "the rule must actually drop something"
    assert all(len(word) >= LEAST_LENGTH_A_DECLARED_WORD_CARRIES for word in used)
    dropped = [word for word in declared if word not in used]
    assert "वा" in dropped  # वा — the two-character word that produced the reading

    # ⛔⛔ THE FIXTURE MUST HAVE THE PROPERTY UNDER TEST. `_noise` emits bare consonants and
    #   never a vowel sign, so no two-character syllable ever appears in it and the failure
    #   this rule exists for cannot happen. ⚠ A control run over it would have passed while
    #   measuring nothing — the defect this file has now paid for four sessions running. What
    #   the archive's wrong-script readers actually return is syllables, so this one does.
    noise = _copy(_syllables_and_no_words(6000), key="carries_no_sanskrit")
    counted = Counter(words_of(noise.normalised))
    assert not any(counted[word] for word in used), "the fixture must carry no declared word"
    # ⛔ THE RULE OFF: the dropped particles do occur in a copy with no language in it.
    assert sum(counted[word] for word in dropped) > 0
    # ⭐ THE RULE ON: the terms that survive it do not.
    measured = declared_words_that_occur(noise, language="sanskrit_or_hindi")
    assert measured["occurrences"] == 0
    assert measured["per_ten_thousand_words"] == 0.0


def test_a_presence_of_declared_words_says_something_and_an_absence_says_nothing():
    """⭐⭐⭐ THE ASYMMETRY THE WHOLE INSTRUMENT RESTS ON, AND IT IS THE GUARD'S OWN.

    *A reader can destroy the evidence of a presence but cannot manufacture it.* Words fixed
    before any copy was measured, and taken out of none of them, occur in a copy only because
    the copy has them. ⛔ The converse does not hold and the row says so: a copy can be
    perfectly legible and still not be running prose.
    """
    carries = _copy(_REAL_DEVANAGARI * 40, key="a_copy_carrying_devanagari")
    carries_none = _copy(_noise(4000), key="a_copy_carrying_no_language")

    present = declared_words_that_occur(carries, language="sanskrit_or_hindi")
    absent = declared_words_that_occur(carries_none, language="sanskrit_or_hindi")
    assert present["occurrences"] > 0 and present["per_ten_thousand_words"] > 100
    assert absent["occurrences"] == 0
    # ⛔ BOTH DIRECTIONS ON THE OTHER LIST TOO, or the reading is about one word list.
    assert declared_words_that_occur(carries, language="english")["occurrences"] == 0
    assert declared_words_that_occur(edition(), language="english")["occurrences"] > 0
    # ⚠ And the row refuses to be read as a verdict.
    assert "NOT" in present["how_to_read_this"] or "no threshold" in present["how_to_read_this"]
    assert "an absence establishes nothing" in present["how_to_read_this"]
    with pytest.raises(TextualError, match="no word list is declared"):
        declared_words_that_occur(carries, language="martian")


def test_the_block_measurement_is_complete_and_disjoint_over_the_copys_characters():
    """⭐ COMPLETE OVER THE COPY'S CHARACTERS — which is the noun THIS question is about.

    ⛔⛔ The same word was true of the wrong noun once in this file and cost a constant: a
    bound on an *extent* asks whether a specimen of that size exists, and the specimens are
    the copy's windows. This asks *how much of this copy is language*, and a tiling from
    offset zero partitions exactly that. ⚠ Checked here rather than asserted: the blocks and
    the remainder must account for every character.
    """
    copy = _copy(_REAL_DEVANAGARI * 40, key="a_copy_to_tile")
    for block in (500, 1000, 3000):
        measured = blocks_that_carry_declared_words(
            copy, language="sanskrit_or_hindi", block=block
        )
        assert (
            measured["blocks"] * block + measured["characters_left_over"]
            == copy.searchable_characters
        )
        assert 0 <= measured["characters_left_over"] < block
        assert 0 <= measured["blocks_carrying_a_declared_word"] <= measured["blocks"]
    # ⭐ A copy that is language throughout carries a declared word nearly everywhere; a copy
    #   that is not carries one nowhere. ⛔ Both, or the measurement is about the tiling.
    carries = blocks_that_carry_declared_words(
        copy, language="sanskrit_or_hindi", block=1000
    )
    assert carries["share_of_the_copy"] > 0.9
    none = blocks_that_carry_declared_words(
        _copy(_noise(4000), key="tiled_noise"), language="sanskrit_or_hindi", block=1000
    )
    assert none["blocks"] > 0 and none["share_of_the_copy"] == 0.0
    with pytest.raises(TextualError, match="at least one character"):
        blocks_that_carry_declared_words(copy, language="english", block=0)


def test_the_refusal_no_longer_names_a_cause_and_the_row_says_so_on_both_sides():
    """⛔⛔⛔ THE DIAGNOSIS IS GONE FROM THE REFUSAL AND FROM THE ROW, AND BOTH ARE CHECKED.

    A copy over the extent bound whose share falls under the floor used to be told *it is a
    machine reading that returned noise*. Measured over sixty-one copies, that is false of
    copies the branch fires on: two whole books it refuses carry the commonest words of their
    own language across 79 % and 83 % of themselves.

    ⭐ The refusal stands — a presence is free wherever little repeats, whatever made the copy
    that way — and it is the CAUSE that is withdrawn, in terms rather than by omission.
    """
    with pytest.raises(TextualError) as excinfo:
        refuse_a_rendering_that_does_not_repeat(
            A_RENDERING_OF_NOISE, what_it_would_make_free="a claim"
        )
    said = str(excinfo.value)
    assert "LITTLE IN THIS COPY REPEATS" in said
    assert "NOTHING HERE SAYS IT IS A MACHINE READING THAT RETURNED NOISE" in said
    assert "language_a_copy_carries" in said
    # ⛔ And the row a caller reads carries the same withdrawal on the LOW side, where it used
    #   to carry nothing at all — the high side has said NOT ESTABLISHED since last session.
    row = recurrence_of(A_RENDERING_OF_NOISE)
    assert row["a_low_share_here_is_about_the_reading"].startswith("⛔ NOT ESTABLISHED")
    assert "language_a_copy_carries" in row["a_low_share_here_is_about_the_reading"]
    assert row["a_high_share_here_is_about_the_copy"].startswith("⛔ NOT ESTABLISHED")


def test_both_sides_of_the_draws_are_registered_and_the_accepted_side_is_not_certified():
    """⛔⛔⛔ A FLOOR MEASURED ONLY OVER WHAT IT REFUSES CANNOT BE ASKED WHETHER IT IS RIGHT.

    The two draws returned fifty-nine readable copies. The thirty-four the floor refused were
    kept — thirty-two of them certified, two refused for their extent and excluded — and the
    twenty-five it accepted were measured and deleted. ⇒ Every question about this floor could
    only be asked from below it.

    ⚠ This checks the registry, not the copies: they are third-party material under a
    git-ignored cache, and a test that required them would fail on a fresh clone.
    """
    from saakshi.texts import (
        COPIES_THAT_CLEARED_KEYS,
        COPIES_THIS_FLOOR_REFUSES_KEYS,
        SOURCES,
    )

    assert len(COPIES_THAT_CLEARED_KEYS) >= 25
    both = (*COPIES_THIS_FLOOR_REFUSES_KEYS, *COPIES_THAT_CLEARED_KEYS)
    # ⛔ No copy may be on both sides, and no address or filename may be shared.
    assert len(set(both)) == len(both)
    assert len({SOURCES[key].address for key in both}) == len(both)
    assert len({SOURCES[key].filename for key in both}) == len(both)
    for key in COPIES_THAT_CLEARED_KEYS:
        source = SOURCES[key]
        assert source.filename.startswith("copies-that-cleared/")
        assert source.address.startswith("https://archive.org/download/")
        # ⭐⭐ AND ACCEPTING IS NOT A CERTIFICATE, which the identity must say rather than
        #    leave to the reader — the whole reason this side is held is that the floor's
        #    verdict is under test, not being relied on.
        assert "NOT AS A COPY OF THE WORK" in source.identity
        assert "accepting is not a certificate" in source.identity
    drawn = " ".join(SOURCES[key].identity for key in COPIES_THAT_CLEARED_KEYS)
    assert "the head of the collection" in drawn and "bucket" in drawn


# --------------------------------------------------------------------------------------
# ⛔⛔⛔ The floor errs in BOTH directions, and neither named repair can be made
# --------------------------------------------------------------------------------------


def test_the_two_certified_sets_cross_so_no_value_of_this_floor_separates_them():
    """⛔⛔⛔ THE MEASUREMENT THIS SESSION WAS FOR, PINNED AT BOTH ENDS.

    The floor was known to refuse real books. It is now measured to ACCEPT readings in a
    script their work cannot be printed in — three of them, the largest 39 129 518
    characters — and the two ranges CROSS, so no value of this statistic separates them.

    ⭐ Both numbers are pinned, and so is the direction of the crossing: a revert that put
    either back where a one-sided fitting had it cannot pass as a re-measurement.
    """
    assert LEAST_SHARE_A_COPY_CARRYING_ITS_OWN_LANGUAGE_REACHES == 0.006873
    assert GREATEST_SHARE_A_WRONG_SCRIPT_READING_REACHES == 0.030511
    # ⛔ CROSSED, and by more than four times. This is the whole finding in one line.
    assert (
        GREATEST_SHARE_A_WRONG_SCRIPT_READING_REACHES
        > LEAST_SHARE_A_COPY_CARRYING_ITS_OWN_LANGUAGE_REACHES
    )
    assert (
        GREATEST_SHARE_A_WRONG_SCRIPT_READING_REACHES
        / LEAST_SHARE_A_COPY_CARRYING_ITS_OWN_LANGUAGE_REACHES
    ) > 4
    # ⭐ And the published floor sits BETWEEN them, which is what makes it wrong both ways.
    assert (
        LEAST_SHARE_A_COPY_CARRYING_ITS_OWN_LANGUAGE_REACHES
        < LEAST_RECURRENCE
        < GREATEST_SHARE_A_WRONG_SCRIPT_READING_REACHES
    )
    assert LEAST_COPIES_THIS_FLOOR_MISCLASSIFIES_AT_ANY_VALUE == 5


def test_the_least_error_curve_is_complete_and_the_published_value_is_already_least():
    """⭐ The instrument, driven over the shape the real evidence has.

    ⛔ The fixture reproduces the crossing rather than standing in for it: the lowest real
    book sits BELOW the highest wrong-script reading, so no value separates, and the total
    is NOT monotone in the value — which is why the whole curve travels rather than a bound
    read off it.
    """
    readings = {"a": 0.006873, "b": 0.00864, "c": 0.0104, "d": 0.09}
    wrong = {"x": 0.0002, "y": 0.011922, "z": 0.030511}
    measured = least_error_a_single_value_can_reach(
        carrying_their_own_language=readings,
        read_in_a_script_the_work_cannot_be_printed_in=wrong,
    )
    assert measured["any_value_separates_them"] is False
    assert measured["the_lowest_real_book"] == {"copy": "a", "share": 0.006873}
    assert measured["the_highest_wrong_script_reading"] == {"copy": "z", "share": 0.030511}
    # ⭐ COMPLETE over the values the two sets take — one point per distinct value, never a
    #   grid. A threshold's behaviour changes only at an observed value.
    assert len(measured["the_whole_curve"]) == len(set(readings.values()) | set(wrong.values()))
    assert [point["value"] for point in measured["the_whole_curve"]] == sorted(
        set(readings.values()) | set(wrong.values())
    )
    # ⛔⛔ AND NOT MONOTONE: it falls, rises and falls again, so *the smallest value at which
    #   the total stops falling* is not the minimum. That rule put the refusing extent bound
    #   1 686 characters wrong two sessions ago.
    totals = [point["copies_misclassified"] for point in measured["the_whole_curve"]]
    assert any(totals[i] < totals[i - 1] for i in range(1, len(totals)))
    assert any(totals[i] > totals[i - 1] for i in range(1, len(totals)))
    assert measured["least_copies_any_value_misclassifies"] == min(totals)
    # ⭐ The cost of refusing every wrong-script reading, which is what an armed guard costs.
    assert measured["the_least_value_that_refuses_every_wrong_script_reading"] == 0.09
    assert measured["what_that_value_costs"] == 3
    # ⛔⛔⛔ AND THE FIELD THAT SAYS THE PUBLISHED VALUE CANNOT BE IMPROVED IS DRIVEN BOTH
    #    WAYS, ON TWO INPUTS. It reads True over the real evidence, and the generator's
    #    control asserts that - so a field hard-wired True satisfies the control it was
    #    written for and nothing says otherwise. Here it must read FALSE: the published value
    #    misclassifies four of these seven and the least any value reaches is two.
    assert measured["the_published_value_is_already_least"] is False
    assert measured["at_the_published_value"]["copies_misclassified"] == 4
    assert measured["least_copies_any_value_misclassifies"] == 2
    assert measured["the_value_that_reaches_it"] == 0.006873


def test_the_least_error_curve_reports_a_separation_when_there_is_one():
    """⭐⭐⭐ THE POSITIVE CONTROL. Every other fixture here crosses, so a verdict that
    could only ever say *no* would satisfy all of them and measure nothing.

    ⛔ On two sets that DO separate, the same instrument says so, reports zero
    misclassified, and reports the published value already at the minimum.
    """
    measured = least_error_a_single_value_can_reach(
        carrying_their_own_language={"a real book": 0.02},
        read_in_a_script_the_work_cannot_be_printed_in={"a wrong-script reading": 0.005},
    )
    assert measured["any_value_separates_them"] is True
    assert measured["least_copies_any_value_misclassifies"] == 0
    assert measured["at_the_published_value"]["copies_misclassified"] == 0
    assert measured["the_published_value_is_already_least"] is True
    assert measured["at_the_published_value"]["real_books_refused"] == []
    assert measured["at_the_published_value"]["wrong_script_readings_accepted"] == []
    assert measured["the_least_value_that_refuses_every_wrong_script_reading"] == 0.02
    assert measured["what_that_value_costs"] == 0


def test_the_least_error_curve_refuses_a_copy_certified_on_both_sides():
    """⛔ A copy in both sets makes every count below it a number about nothing.

    ⭐ The words of the refusal are asserted, not merely that a refusal came back: this
    module has six guard branches that all raise `TextualError`, and a test satisfied by any
    of them reports coverage while its own branch sits dead.
    """
    with pytest.raises(TextualError) as raised:
        least_error_a_single_value_can_reach(
            carrying_their_own_language={"a": 0.02, "shared": 0.05},
            read_in_a_script_the_work_cannot_be_printed_in={"shared": 0.01},
        )
    assert "the two certified sets share" in str(raised.value)
    assert "shared" in str(raised.value)


def test_the_least_error_curve_refuses_either_side_being_empty():
    """⛔ A maximum over an empty set is how an accepting bound came to be published off one
    specimen. ⭐ Two calls, each isolating ONE side, because a single empty-both call would
    be satisfied by whichever check ran first.
    """
    with pytest.raises(TextualError) as no_readings:
        least_error_a_single_value_can_reach(
            carrying_their_own_language={},
            read_in_a_script_the_work_cannot_be_printed_in={"x": 0.01},
        )
    assert "both certified sets are required" in str(no_readings.value)
    with pytest.raises(TextualError) as no_wrong:
        least_error_a_single_value_can_reach(
            carrying_their_own_language={"a": 0.01},
            read_in_a_script_the_work_cannot_be_printed_in={},
        )
    assert "both certified sets are required" in str(no_wrong.value)
    # ⛔ And neither of those is the disjointness refusal, which shares the same exception
    #   type — the two are owed different words and this pins that they are.
    assert "the two certified sets share" not in str(no_readings.value)
    assert "the two certified sets share" not in str(no_wrong.value)


def test_a_per_language_floor_is_routed_into_buckets_that_hold_one_side_each():
    """⛔⛔⛔ THE FIRST NAMED REPAIR, MEASURED. A per-language floor needs a routing rule, the
    only routing rule available is `COMMONEST_WORDS`, and it puts the two sides in different
    buckets — so a floor fitted in a language bucket is fitted with nothing below it, which
    is this floor's original defect one bucket at a time.
    """
    rows = [
        {
            "copy": "an english book",
            "share_that_recurs": 0.05,
            "certified": "a_reading",
            "carries": {"english": 0.99, "sanskrit_or_hindi": 0.0},
        },
        {
            "copy": "a sanskrit book",
            "share_that_recurs": 0.0069,
            "certified": "a_reading",
            "carries": {"english": 0.0, "sanskrit_or_hindi": 0.79},
        },
        {
            "copy": "an english book read in devanagari",
            "share_that_recurs": 0.0305,
            "certified": "a_wrong_script_reading",
            "carries": {"english": 0.0, "sanskrit_or_hindi": 0.01},
        },
        {
            "copy": "a legible bengali book no list here can meet",
            "share_that_recurs": 0.0328,
            "certified": "not_certified",
            "carries": {"english": 0.0, "sanskrit_or_hindi": 0.0},
        },
    ]
    fitted = how_a_per_language_floor_would_be_fitted(by_copy=rows, criterion=0.75)
    assert fitted["criterion"] == 0.75
    # ⛔ NO bucket holds both sides, so there is nothing to fit anywhere.
    assert fitted["buckets_holding_both_sides"] == []
    assert fitted["buckets_where_a_value_would_separate"] == []
    assert fitted["every_wrong_script_reading_landed_in"] == ["no_declared_language"]
    assert fitted["the_bucket_holding_the_wrong_script_readings_holds_no_reading"] is True
    assert fitted["by_bucket"]["english"]["certified_wrong_script_readings"] == 0
    assert fitted["by_bucket"]["sanskrit_or_hindi"]["certified_wrong_script_readings"] == 0
    assert fitted["by_bucket"]["no_declared_language"]["certified_readings"] == 0
    # ⚠ And the undeclared bucket cannot simply be refused wholesale: a legible copy in a
    #   language nobody declared is sitting in it, refused for a fact about the word list.
    assert fitted["by_bucket"]["no_declared_language"]["not_certified"] == 1
    assert "legible Bengali" in fitted["what_this_establishes"]


def test_a_per_language_bucket_that_does_hold_both_sides_still_does_not_separate():
    """⛔ The other branch of the same routing, isolated: at the loosest criterion the census
    published, one wrong-script reading DOES land in a language bucket — and a value fitted
    there does not separate, because it sits inside the readings' own range.

    ⚠ This is the real shape: `TheTheoryOfTheSamdhis…` carries declared Sanskrit across
    48.8 % of itself, because the wrong-script reader got its Sanskrit quotations right.
    """
    rows = [
        {
            "copy": "the lowest sanskrit book",
            "share_that_recurs": 0.006873,
            "certified": "a_reading",
            "carries": {"english": 0.0, "sanskrit_or_hindi": 0.79},
        },
        {
            "copy": "the highest sanskrit book",
            "share_that_recurs": 0.089183,
            "certified": "a_reading",
            "carries": {"english": 0.0, "sanskrit_or_hindi": 1.0},
        },
        {
            "copy": "an english monograph whose sanskrit quotations survived",
            "share_that_recurs": 0.009675,
            "certified": "a_wrong_script_reading",
            "carries": {"english": 0.0, "sanskrit_or_hindi": 0.49},
        },
    ]
    fitted = how_a_per_language_floor_would_be_fitted(by_copy=rows, criterion=0.25)
    assert fitted["buckets_holding_both_sides"] == ["sanskrit_or_hindi"]
    # ⛔⛔⛔ A VALUE CAN BE FITTED HERE AND IT STILL DOES NOT SEPARATE — the wrong-script
    #    reading sits INSIDE the readings' range, not below it.
    assert fitted["buckets_where_a_value_would_separate"] == []
    cell = fitted["by_bucket"]["sanskrit_or_hindi"]
    assert cell["a_value_can_be_fitted_here"] is True
    assert cell["and_it_would_separate_them"] is False
    assert cell["readings_run"][0] < cell["wrong_script_readings_run"][1]
    # ⭐ And the same rows at a tighter criterion move it out again, which is why the
    #   criterion travels on the row rather than being chosen once and forgotten.
    tighter = how_a_per_language_floor_would_be_fitted(by_copy=rows, criterion=0.75)
    assert tighter["buckets_holding_both_sides"] == []
    assert tighter["every_wrong_script_reading_landed_in"] == ["no_declared_language"]


def test_a_per_language_floor_refuses_an_empty_offering():
    """⛔ Nothing to route is not an empty result, it is a refusal — owed its own words."""
    with pytest.raises(TextualError) as raised:
        how_a_per_language_floor_would_be_fitted(by_copy=[], criterion=0.75)
    assert "no copies were offered to route" in str(raised.value)


def test_every_statistic_offered_as_a_replacement_is_named():
    """⭐ A count with no names is a silent cap on what a reader can check.

    ⛔ Nine were offered and none of them separates the two sets; the nine are named so that
    a reader can see which questions were asked, and a tenth that was never asked is not
    hidden inside a total.
    """
    assert len(STATISTICS_MEASURED_AGAINST_THIS_FLOOR) == 9
    assert len(set(STATISTICS_MEASURED_AGAINST_THIS_FLOOR)) == 9
    # ⭐ The floor as it stands is one of the nine, so the list includes its own subject.
    assert (
        "share_of_distinct_12_character_fragments_that_recur"
        in STATISTICS_MEASURED_AGAINST_THIS_FLOOR
    )
    # ⛔ The one that is degenerate rather than merely inverted is named too.
    assert "the_copy_against_a_shuffle_of_itself" in STATISTICS_MEASURED_AGAINST_THIS_FLOOR


def test_the_wrong_script_certification_is_a_declaration_over_copies_this_repository_holds():
    """⛔ Certified by a PRESENCE of the wrong script, and never by a word count.

    ⚠ Checks the registry, not the copies: they are third-party material under a git-ignored
    cache, and a test that required them would fail on a fresh clone.
    """
    from saakshi.texts import (
        ABSTAINED_FROM_CERTIFYING,
        COPIES_THAT_CLEARED_KEYS,
        READINGS_IN_A_SCRIPT_THE_WORK_CANNOT_BE_PRINTED_IN,
        SOURCES,
        certification_of,
    )

    assert len(READINGS_IN_A_SCRIPT_THE_WORK_CANNOT_BE_PRINTED_IN) == 21
    assert len(ABSTAINED_FROM_CERTIFYING) == 13
    # ⛔ Disjoint, and every key is a copy this repository actually registers.
    overlap = set(READINGS_IN_A_SCRIPT_THE_WORK_CANNOT_BE_PRINTED_IN) & set(
        ABSTAINED_FROM_CERTIFYING
    )
    # ⛔ Named, not counted: a copy certified AND abstained from is a contradiction, and a
    #   bare `assert not` would print a boolean where the reader needs the key.
    assert overlap == set(), sorted(overlap)
    for key in (
        *READINGS_IN_A_SCRIPT_THE_WORK_CANNOT_BE_PRINTED_IN,
        *ABSTAINED_FROM_CERTIFYING,
    ):
        assert key in SOURCES
    # ⭐⭐⭐ AND THREE OF THEM ARE COPIES THIS FLOOR ACCEPTS. That is the new evidence: until
    #    the accepted side was held, this floor could only ever be measured from below.
    accepted = set(READINGS_IN_A_SCRIPT_THE_WORK_CANNOT_BE_PRINTED_IN) & set(
        COPIES_THAT_CLEARED_KEYS
    )
    assert len(accepted) == 3
    # ⛔ Each certification names the catalogued WORK, which is what makes the script wrong.
    for key, reason in READINGS_IN_A_SCRIPT_THE_WORK_CANNOT_BE_PRINTED_IN.items():
        assert any(word in reason for word in ("ENGLISH", "KANNADA"))
    # ⛔ And the abstentions name why the certification is WITHHELD, one by one.
    for key, reason in ABSTAINED_FROM_CERTIFYING.items():
        assert reason.strip()
    # ⭐ Three isolating inputs, one per answer, because a sorter tested on one input
    #   reports full coverage while two of its three branches sit dead.
    assert certification_of(next(iter(READINGS_IN_A_SCRIPT_THE_WORK_CANNOT_BE_PRINTED_IN))) == (
        "a_wrong_script_reading"
    )
    assert certification_of(next(iter(ABSTAINED_FROM_CERTIFYING))) == "abstained"
    assert certification_of("jaimini_sutras_rao") == "not_certified"
    # ⛔ It consults no copy and no measurement: a key nothing is held for still answers.
    assert certification_of("a key no source exists for") == "not_certified"


# ==========================================================================================
# The LOCAL presence — the passage a locus resolves in, rather than the copy it sits in
# ==========================================================================================
#
# ⛔⛔⛔ The floor is measured unrepairable and the twentieth session's question was what
#    replaces a REFUSING instrument. These exercise the answer: a presence of words the copy
#    did not supply, measured at the copy's WORST position rather than over the whole of it.
#    ⭐ Every verdict field below is driven BOTH ways, and every branch is isolated by an
#    input no other branch answers to — the twentieth session's escape was a field that was
#    always True and the nineteenth's was a guard test satisfied by a different guard.

#: A copy that carries English throughout, ⚠ with the declared words spread so that the
#: WORST position is a measurable distance from one rather than an assumed zero.
CARRIES_ENGLISH_THROUGHOUT = _copy(
    (
        "The rule is stated here and that is the whole of it. "
        + "qqqq " * 40
        + "This is the second passage and it says the same thing with other words. "
        + "wwww " * 40
        + "The third passage restates what the first two have said, from the beginning."
    ),
    key="carries_english_throughout",
)

#: ⛔ A copy in which one long stretch carries no declared word at all — the shape a rendering
#: of noise has, and the shape one long index in a real book has too. ⚠ That ambiguity is
#: the finding, not a defect in the fixture.
#: ⚠ Every token in the stretch is distinct, which is the property a machine reading that
#: returned noise has and the reason a fragment quoted out of one resolves exactly once.
HAS_ONE_LONG_STRETCH_WITHOUT_IT = _copy(
    "The rule is stated here at the beginning. "
    + "".join(f"zqx{number:04d} " for number in range(400))
    + " and that is all.",
    key="has_one_long_stretch_without_it",
)

#: ⛔ A fragment out of the middle of that stretch. It resolves exactly ONCE — which is the
#: whole danger the local presence exists to meet: in a rendering that repeats nothing, a
#: citation quoted out of the noise locates one place and attests a rule nobody stated.
A_FRAGMENT_OUT_OF_THE_STRETCH = "".join(f"zqx{number:04d} " for number in range(200, 210))


def test_a_flank_of_zero_reads_nothing_and_is_refused():
    """⛔ A presence measured over no text is not a presence."""
    with pytest.raises(TextualError) as error:
        the_passage_a_locus_resolves_in(edition(), CONTROL, flank=0)
    assert "reads nothing" in str(error.value)


def test_a_passage_is_taken_only_around_a_fragment_that_resolves_once():
    """⛔ Two hits is two passages, and the first of them is whichever the copy prints first."""
    twice = _copy(CONTROL + " ... " + CONTROL, key="prints_it_twice")
    with pytest.raises(TextualError) as error:
        the_passage_a_locus_resolves_in(twice, CONTROL, flank=50)
    assert "occurs 2 time(s)" in str(error.value)
    # ⭐ The positive control: the same fragment in a copy that prints it once.
    assert the_passage_a_locus_resolves_in(edition(), CONTROL, flank=50)["flank"] == 50


def test_the_fragment_is_excluded_from_its_own_passage():
    """⛔⛔⛔ A DECLARED WORD INSIDE THE QUOTATION WAS SUPPLIED BY THE CITATION.

    ⭐ The isolating input: a fragment that is ITSELF made of declared words, sitting in a
    copy whose surroundings carry none. If the fragment counted, this would attest — and the
    longer the quotation the freer the presence would be.
    """
    fragment = "the and that for with this are not from have"
    copy = _copy("qqqq " * 30 + fragment + " wwww " * 30, key="the_words_are_in_the_quote")
    passage = the_passage_a_locus_resolves_in(copy, fragment, flank=200)
    assert fragment not in passage["passage"]
    assert passage["the_fragment_is_excluded"] is True
    carried = declared_words_the_passage_carries(
        copy, fragment, language="english", flank=200
    )
    # ⛔ BOTH WAYS: nothing is carried here, and something is carried when the surroundings
    #   are what supply it rather than the quotation.
    assert carried["carries_the_declared_language"] is False
    assert carried["occurrences"] == 0
    supplied_by_the_copy = _copy(
        "and that is the whole of it. " + fragment + " which was the rule from the first.",
        key="the_words_are_around_the_quote",
    )
    other = declared_words_the_passage_carries(
        supplied_by_the_copy, fragment, language="english", flank=200
    )
    assert other["carries_the_declared_language"] is True
    assert other["occurrences"] > 0


def test_the_least_flank_is_the_smallest_one_that_works_and_the_search_is_checked():
    """⭐ The binary search is pinned against a linear one — ⛔ never against itself."""
    copy = CARRIES_ENGLISH_THROUGHOUT
    fragment = "This is the second passage"
    least = least_flank_at_which_a_passage_carries_a_declared_word(
        copy, fragment, language="english", cap=5000
    )
    assert least is not None
    linear = next(
        flank
        for flank in range(1, 5000)
        if declared_words_the_passage_carries(
            copy, fragment, language="english", flank=flank
        )["carries_the_declared_language"]
    )
    assert least == linear
    # ⛔ And one below it must NOT carry — a smallest that is not smallest is not a bound.
    assert not declared_words_the_passage_carries(
        copy, fragment, language="english", flank=least - 1
    )["carries_the_declared_language"]


def test_a_language_with_no_declared_list_is_an_abstention_and_not_a_refusal():
    """⛔⛔ AND THE TWO MUST NOT BE SPELLED THE SAME.

    ⭐ The words each branch is owed are asserted, and no two branches are owed the same
    ones — a guard test that accepts any refusal is satisfied by a different guard.
    """
    assert word_list_a_locus_calls_for("en") == "english"
    assert word_list_a_locus_calls_for("hi") == "sanskrit_or_hindi"
    assert word_list_a_locus_calls_for("sa") == "sanskrit_or_hindi"
    # ⚠ `und` is what most copies in this repository's cache declare, and it is exactly the
    #   case the instrument cannot speak for.
    assert word_list_a_locus_calls_for("und") is None
    assert word_list_a_locus_calls_for("bn") is None
    silent = require_the_passage_to_carry_the_language_the_locus_declares(
        Locus(
            source_kind="translation",
            edition=CARRIES_ENGLISH_THROUGHOUT,
            locus="a place",
            interpretation_status="restated",
            fragment="This is the second passage",
            language="bn",
        )
    )
    assert silent["outcome"] == "cannot_measure"
    assert "ABSTENTION AND NOT A REFUSAL" in silent["what_this_establishes"]
    assert silent["word_list"] is None


def test_the_three_outcomes_are_isolated_and_each_is_owed_its_own_words():
    """⭐⭐⭐ Three inputs, three outcomes, and the words of each are pinned apart."""
    attested = require_the_passage_to_carry_the_language_the_locus_declares(
        Locus(
            source_kind="translation",
            edition=CARRIES_ENGLISH_THROUGHOUT,
            locus="a place",
            interpretation_status="restated",
            fragment="This is the second passage",
            language="en",
        )
    )
    cannot = require_the_passage_to_carry_the_language_the_locus_declares(
        Locus(
            source_kind="translation",
            edition=HAS_ONE_LONG_STRETCH_WITHOUT_IT,
            locus="a place",
            interpretation_status="restated",
            fragment=A_FRAGMENT_OUT_OF_THE_STRETCH,
            language="en",
        ),
        cap=200,
    )
    silent = require_the_passage_to_carry_the_language_the_locus_declares(
        Locus(
            source_kind="translation",
            edition=CARRIES_ENGLISH_THROUGHOUT,
            locus="a place",
            interpretation_status="restated",
            fragment="This is the second passage",
            language="und",
        )
    )
    assert [attested["outcome"], cannot["outcome"], silent["outcome"]] == [
        "attested",
        "cannot_attest",
        "cannot_measure",
    ]
    # ⛔ The words owed, per branch, and no two branches owed the same ones.
    assert "WITHIN" in attested["what_this_establishes"]
    assert "NO POSITIVE EVIDENCE AT THIS PLACE" in cannot["what_this_establishes"]
    assert "No list of commonest words is declared" in silent["what_this_establishes"]
    owed = [row["what_this_establishes"] for row in (attested, cannot, silent)]
    assert len(set(owed)) == 3
    # ⭐ And the attested row carries the number, not a boolean — the number is the finding.
    assert isinstance(
        attested["least_flank_at_which_the_passage_carries_a_declared_word"], int
    )
    # ⛔⛔ AND IT SAYS ON THE ROW THAT THE NUMBER DOES NOT SEPARATE. The twentieth session's
    #    escape was a field carrying a headline with nothing behind it.
    assert "MUST NOT BE THRESHOLDED" in (
        attested["this_number_does_not_separate_a_reading_from_a_rendering_of_noise"]
    )


def test_an_absence_at_a_locus_establishes_nothing_about_the_copy():
    """⛔ The diagnosis withdrawn from the recurrence refusal must not reappear here."""
    cannot = require_the_passage_to_carry_the_language_the_locus_declares(
        Locus(
            source_kind="translation",
            edition=HAS_ONE_LONG_STRETCH_WITHOUT_IT,
            locus="a place",
            interpretation_status="restated",
            fragment=A_FRAGMENT_OUT_OF_THE_STRETCH,
            language="en",
        ),
        cap=200,
    )
    said = cannot["what_this_establishes"]
    assert "machine reading that returned noise" in said
    assert "nothing about whether the passage is" in said
    # ⛔ It is stated as what the refusal does NOT say. A test asserting only that the words
    #   are absent would pass on a row that said nothing at all.
    assert "AND NOTHING" in said


def test_the_copy_level_guard_refuses_a_long_stretch_and_accepts_a_book():
    """⭐⭐⭐ A REFUSING INSTRUMENT BUILT ENTIRELY OUT OF PRESENCES."""
    accepted = refuse_a_rendering_that_goes_too_far_without_its_declared_language(
        CARRIES_ENGLISH_THROUGHOUT,
        language="en",
        what_it_would_make_free="an attestation",
        cap=2000,
    )
    assert accepted["outcome"] == "accepted"
    assert accepted["least_flank_at_which_every_position_carries_a_declared_word"] > 0
    with pytest.raises(TextualError) as error:
        refuse_a_rendering_that_goes_too_far_without_its_declared_language(
            HAS_ONE_LONG_STRETCH_WITHOUT_IT,
            language="en",
            what_it_would_make_free="an attestation",
            cap=200,
        )
    said = str(error.value)
    # ⛔⛔ THE BRANCH NAMES ITSELF. A string-matched branch detector fails silently in
    #    whichever direction the message last moved, so nothing downstream sorts on prose.
    assert "THE CAUSE IS THE DISTANCE TO A DECLARED WORD AND NOT THE RECURRENCE" in said
    # ⛔ And it does NOT say what the recurrence refusal says, in either of its branches.
    assert "LITTLE IN THIS COPY REPEATS" not in said
    assert "THE CAUSE IS THE EXTENT AND NOT THE RENDERING" not in said
    # ⛔⛔⛔ THE WHOLE WITHDRAWAL, NOT A PREFIX OF IT. The sweep escaped once here: a disarm
    #    that replaced everything AFTER these words with the diagnosis itself left the prefix
    #    standing, and an assertion on the prefix passed. ⇒ the branch names its own limit and
    #    the test is owed the marker, not the opening.
    assert "NO DIAGNOSIS IS MADE HERE AND THAT IS THIS REFUSAL NAMING ITS OWN LIMIT" in said
    assert "an absence establishes nothing" in said


def test_the_copy_level_guard_abstains_where_no_word_list_is_declared():
    """⚠ Silent over legible Bengali, Tamil, Urdu and Kashmiri — ⛔ and it says so."""
    row = refuse_a_rendering_that_goes_too_far_without_its_declared_language(
        HAS_ONE_LONG_STRETCH_WITHOUT_IT,
        language="bn",
        what_it_would_make_free="an attestation",
        cap=200,
    )
    # ⭐ The isolating input: a copy the guard WOULD refuse under a language it has a list
    #   for. So the abstention is reached by the language and not by the copy.
    assert row["outcome"] == "cannot_measure"
    assert "NOTHING ABOUT THIS COPY" in row["what_this_establishes"]
    with pytest.raises(TextualError):
        refuse_a_rendering_that_goes_too_far_without_its_declared_language(
            HAS_ONE_LONG_STRETCH_WITHOUT_IT,
            language="en",
            what_it_would_make_free="an attestation",
            cap=200,
        )


def test_the_worst_position_is_exact_and_is_checked_against_a_linear_search():
    """⭐ Complete over every position, and pinned against a search that does not share code."""
    copy = CARRIES_ENGLISH_THROUGHOUT
    reached = least_flank_at_which_every_position_carries_a_declared_word(
        copy, language="english", cap=5000
    )
    assert reached is not None
    body = copy.normalised
    terms = frozenset(declared_words_of("english"))

    def every_position_carries(flank: int) -> bool:
        # ⛔ A linear check over every position, written independently of the union-of-
        #   intervals the module uses. Two implementations, one number.
        for at in range(len(body)):
            low = max(0, at - flank)
            high = min(len(body), at + flank)
            if not (terms & set(words_of(body[low:high]))):
                return False
        return True

    assert every_position_carries(reached)
    assert not every_position_carries(reached - 1)


def test_the_separation_verdict_is_driven_both_ways_with_a_positive_control():
    """⛔⛔⛔ A CONTROL THAT ASSERTS A FIELD IS TRUE IS SATISFIED BY A FIELD THAT IS ALWAYS TRUE.

    ⭐ So the verdict is put to two sets that DO separate and two that do NOT, and the
    instrument must say so both times. Every fixture that can only come out one way measures
    nothing.
    """
    separates = whether_a_local_presence_separates(
        carrying_their_own_language={"a": 163, "b": 8828},
        read_in_a_script_the_work_cannot_be_printed_in={"c": 16642, "d": None},
    )
    assert separates["the_two_sets_do_not_cross"] is True
    assert separates["how_far_apart"] == round(16642 / 8828, 4)
    # ⛔ BOTH sides carry a `None` here on purpose. With only the wrong-script side empty of
    #   one, merging the two lists is invisible - the sweep escaped exactly that way.
    assert separates["wrong_script_readings_that_carry_a_declared_word_at_no_flank"] == ["d"]
    assert separates["readings_that_carry_a_declared_word_at_no_flank"] == []
    both_sides = whether_a_local_presence_separates(
        carrying_their_own_language={"a": 163, "b": 8828, "tamil": None},
        read_in_a_script_the_work_cannot_be_printed_in={"c": 16642, "d": None},
    )
    # ⭐ And the two are counted APART: on the wrong-script side a `None` is the instrument
    #   working; on the reading side it is a fact about COMMONEST_WORDS and nothing else.
    assert both_sides["wrong_script_readings_that_carry_a_declared_word_at_no_flank"] == ["d"]
    assert both_sides["readings_that_carry_a_declared_word_at_no_flank"] == ["tamil"]
    assert both_sides["the_two_sets_do_not_cross"] is True
    crossed = whether_a_local_presence_separates(
        carrying_their_own_language={"a": 163, "b": 30000},
        read_in_a_script_the_work_cannot_be_printed_in={"c": 16642, "d": None},
    )
    assert crossed["the_two_sets_do_not_cross"] is False
    assert crossed["how_far_apart"] is None


def test_the_separation_refuses_a_copy_in_both_sets_and_an_empty_side():
    """⛔ A maximum over an empty set is how an accepting bound came to be published off one
    specimen, and a copy certified both ways makes every count a number about nothing."""
    with pytest.raises(TextualError) as error:
        whether_a_local_presence_separates(
            carrying_their_own_language={"a": 163},
            read_in_a_script_the_work_cannot_be_printed_in={"a": 16642},
        )
    assert "share 1 copy" in str(error.value)
    with pytest.raises(TextualError) as error:
        whether_a_local_presence_separates(
            carrying_their_own_language={},
            read_in_a_script_the_work_cannot_be_printed_in={"a": 16642},
        )
    assert "both certified sets are required" in str(error.value)


def test_the_two_published_flank_bounds_do_not_cross_and_carry_their_provenance():
    """⛔ A bound quoted without how it was measured reads as a property of the world."""
    assert (
        GREATEST_FLANK_A_CERTIFIED_READING_HAS_NEEDED
        < LEAST_FLANK_AT_WHICH_A_LOCAL_PRESENCE_IS_FREE_IN_A_RENDERING_OF_NOISE
    )
    assert "LOWER BOUNDS" in HOW_THE_FLANK_BOUNDS_WERE_MEASURED
    assert "46 certified copies" in HOW_THE_FLANK_BOUNDS_WERE_MEASURED
    # ⚠ The grid the census is published on travels with the row, like every grid here.
    assert LOCAL_PRESENCE_MEASURED_AT_FLANKS == tuple(
        sorted(LOCAL_PRESENCE_MEASURED_AT_FLANKS)
    )
    assert GREATEST_FLANK_A_CERTIFIED_READING_HAS_NEEDED not in (
        LOCAL_PRESENCE_MEASURED_AT_FLANKS
    )


def test_the_declared_word_lists_the_locus_map_names_are_all_declared():
    """⛔ A map naming a list that does not exist routes a locus into a KeyError at emit time."""
    for code, name in THE_LANGUAGE_A_LOCUS_DECLARES.items():
        assert name in COMMONEST_WORDS, code
        assert declared_words_of(name)
