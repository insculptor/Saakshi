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
    Alignment,
    Edition,
    Fork,
    Locus,
    PassageAbsence,
    Refusal,
    Rendering,
    SecondHand,
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
    "SUTRA FOUR MARKER. Closing matter.\n"
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
    "End of First Pada. End of Second Pada.\n"
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
