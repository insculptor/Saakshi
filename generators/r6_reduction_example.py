"""A number a source resolves itself, reproduced — and nothing more than that.

⭐ **A worked example proves reproduction, not accuracy**, which is why the contract forbids
this kind from ever carrying an astronomical budget row. What is established below is that a
method read off a source's own illustration, applied to the figures that source printed,
returns the figures that source printed. That is a claim about following the text. It is not
a claim that the text is right about anything.

⭐ **The source printed its example twice — as a chart and spelled out in its prose — so it
supplied its own second witness**, and both are transcribed here independently and compared
cell by cell. A rendering that mangled either would show up as a disagreement instead of
passing as evidence. ⛔ Without that control, "we reproduced the source" would rest on one
machine reading of one scanned table, which is the least reliable thing in the file.

⛔ **AND THE EXAMPLE DOES NOT EXERCISE THE RULE THE CHAPTER STATES.** Two limits are measured
and recorded rather than mentioned: the chapter's stated rule, read literally, is a different
method from the one this example resolves to; and the example's own figures never reach the
exception the chapter attaches to that rule, so reproducing it says nothing about the
exception either way. A worked example resolves a method only over the inputs it happens to
contain.

⛔ **Recorder, never explainer.** The arithmetic is the source's own, applied to the source's
own figures, to check the source against itself.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from saakshi.fixture import Header, describe_reserved_names, write_jsonl  # noqa: E402
from saakshi.provenance import generator_for, today  # noqa: E402
from saakshi.texts import CACHE, acquire, load  # noqa: E402
from saakshi.textual import (  # noqa: E402
    NO_LICENCE_DETERMINATION,
    SIGNS,
    Locus,
    Refusal,
    TextualError,
    agreement,
    as_by_sign,
    normalise,
    read_integer_cells,
    read_integer_digits,
    reduce_by_trine_minimum,
    refusal_summary,
    resolve,
    rotate_to,
    source_oracle,
)

EDITION = "bphs_santhanam"

#: The sign the source's chart begins at — it prints the row from the sign its subject
#: occupies, so the first cell is not the first sign. ⚠ Getting this wrong is invisible: the
#: figures are all still there, in an order that looks deliberate.
CHART_BEGINS_AT = "capricorn"

CHART_BEGINS_AT_FRAGMENT = (
    "So, all the 12 Rashis beginning from Capricorn have been written in the first "
    "horizontal column of the chart."
)

# --------------------------------------------------------------------------------------
# The example as the prose spells it out
# --------------------------------------------------------------------------------------

#: Each sentence the source works one group of three in, the signs it names in order, and
#: which of the integers standing in that sentence are the figures before and after.
#:
#: ⚠ The positions are a **declared reading** of each sentence, and each sentence is quoted in
#: full on its own row, so a reader can check the reading against the words rather than
#: against our summary of them. ⛔ Parsing them by one general pattern was not possible: the
#: source phrases all four differently, and a pattern loose enough to catch all four would
#: also catch figures that are not the example's.
PROSE: tuple[dict[str, Any], ...] = (
    {
        "group": "the group of three the subject stands in",
        "signs": ("capricorn", "taurus", "virgo"),
        "before_at": (0, 1, 2),
        "after_at": (4, 5, 6),
        "fragment": (
            "The numbers of rekhas are 5, 3 and 2 in Capricorn, Taurus and Virgo "
            "respectively. The least number of rekhas is 2 in Virgo. By deducting it from "
            "the number of rekhas in the three Rashis, there will be 3 left in Capricorn, 1 "
            "in Taurus and 0 in Virgo."
        ),
    },
    {
        "group": "the second group of three",
        "signs": ("aquarius", "gemini", "libra"),
        "before_at": (0, 1, 2),
        "after_at": (3, 4, 5),
        "fragment": (
            "The Trikona of Aquarius is made up of Aquarius, Gemini and Libra with 3, 4 and "
            "3 rekhas respectively. By deducting the lowest number Aquarius will he left "
            "with 0, Gemini with 1 and Libra with 0,"
        ),
    },
    {
        "group": "the third group of three",
        "signs": ("pisces", "cancer", "scorpio"),
        "before_at": (0, 1, 2),
        "after_at": (3, 4, 5),
        "fragment": (
            "The Trikona of Pisces is made up of Pisces, Cancer, and Scorpio with 2, 6 and 6 "
            "rekhas respectively. By applying the method explained above Pisces will be left "
            "with 0, Cancer with 4 and Scorpio with 4."
        ),
    },
    {
        "group": "the fourth group of three",
        "signs": ("aries", "leo", "sagittarius"),
        "before_at": (0, 1, 2),
        "after_at": (3, 4, 5),
        "fragment": (
            "The Trikona of Aries is made up of Aries, Leo and Sagittarius with 4, 5 and 5 "
            "rekhas respectively. By applying the same method Aries will be left with 0, Leo "
            "with 1 and Sagittarius with 1."
        ),
    },
)

#: The chapter's stated rule, and the exception attached to it. ⛔ Neither is what this
#: example resolves to, and both are quoted so a reader can see the gap rather than take it
#: from us.
STATED_RULE_FRAGMENT = (
    "the rashi which has lesser number of rekhas should be allotted rekhas arrived at by "
    "deducting its number of rekhas from the total number of rekhas of the three Trikona "
    "rashis"
)
STATED_EXCEPTION_FRAGMENT = (
    "No Trikona-Shodhana is necessary if any of the Trikona rashi has no rekha."
)


def prose_figures() -> tuple[dict[str, int], dict[str, int], list[dict[str, Any]]]:
    """The example's figures as the prose gives them, group by group."""
    before: dict[str, int] = {}
    after: dict[str, int] = {}
    rows: list[dict[str, Any]] = []
    for group in PROSE:
        numbers = [int(n) for n in re.findall(r"\d+", normalise(group["fragment"]))]
        got_before = [numbers[i] for i in group["before_at"]]
        got_after = [numbers[i] for i in group["after_at"]]
        before.update(dict(zip(group["signs"], got_before)))
        after.update(dict(zip(group["signs"], got_after)))
        rows.append(
            {
                "group": group["group"],
                "signs": list(group["signs"]),
                "integers_standing_in_the_sentence": numbers,
                "read_as_before": got_before,
                "read_as_after": got_after,
            }
        )
    return before, after, rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--cache", type=Path, default=CACHE)
    parser.add_argument("--acquire", action="store_true")
    args = parser.parse_args()

    script = Path(__file__)
    generator_for(script)
    print(describe_reserved_names())

    if args.acquire:
        record = acquire(EDITION, cache=args.cache, today=today())
        print(f"acquired {EDITION}: {record['copy_bytes']} bytes")

    edition = load(EDITION, cache=args.cache)
    print(f"edition {EDITION}: {edition.rendering.kind}, {edition.rendering.characters} characters")

    # --- the chart -------------------------------------------------------------------
    chart_before = read_integer_cells(
        edition,
        label="the chart's row of figures before the reduction",
        after="Kt Number of Rekhas",
        before="Page 710 Trikona Shodhana",
        cells=12,
    )
    chart_after = read_integer_digits(
        edition,
        label="the chart's row of figures after the reduction",
        after="Page 710 Trikona Shodhana",
        before="Number In the above chart",
        cells=12,
    )
    for reading in (chart_before, chart_after):
        if not reading.legible:
            raise TextualError(
                f"{reading.label}: {len(reading.values)} cells where "
                f"{reading.expected_cells} are required. ⛔ Nothing is written: the cells "
                "that survive are still digits in a plausible order, so a short row "
                "transcribed as an answer would be indistinguishable from a correct one"
            )
    chart_before_by_sign = as_by_sign(rotate_to(chart_before.values, first_sign=CHART_BEGINS_AT))
    chart_after_by_sign = as_by_sign(rotate_to(chart_after.values, first_sign=CHART_BEGINS_AT))

    # --- the prose -------------------------------------------------------------------
    prose_before, prose_after, prose_rows = prose_figures()

    # --- the two witnesses, compared --------------------------------------------------
    order = list(SIGNS)
    before_agreement = agreement(
        "the figures before the reduction",
        [chart_before_by_sign[s] for s in order],
        [prose_before[s] for s in order],
        first_is="transcribed from the chapter's chart",
        second_is="read out of the chapter's prose, group by group",
    )
    after_agreement = agreement(
        "the figures after the reduction",
        [chart_after_by_sign[s] for s in order],
        [prose_after[s] for s in order],
        first_is="transcribed from the chapter's chart",
        second_is="read out of the chapter's prose, group by group",
    )
    for check in (before_agreement, after_agreement):
        print(
            f"witnesses agree on {check['cells_agreeing']} of {check['cells_compared']} "
            f"cells: {check['label']}"
        )
    if not (before_agreement["agrees"] and after_agreement["agrees"]):
        raise TextualError(
            "the chapter's chart and the chapter's prose do not give the same figures. ⛔ "
            "Nothing is written: one of the two transcriptions is wrong and this file cannot "
            "say which, so it would be publishing a reproduction of an unknown quantity"
        )

    # --- the reproduction --------------------------------------------------------------
    computed = reduce_by_trine_minimum([chart_before_by_sign[s] for s in order])
    reproduction = agreement(
        "the method applied, against the figures the source printed",
        list(computed),
        [chart_after_by_sign[s] for s in order],
        first_is="the method this example resolves to, applied to the printed figures before",
        second_is="the figures the source printed after",
    )
    print(
        f"reproduction: {reproduction['cells_agreeing']} of {reproduction['cells_compared']} "
        "cells match the figures the source printed"
    )
    if not reproduction["agrees"]:
        raise TextualError(
            "the method read off this example does not return the figures the example "
            "prints. ⛔ Nothing is written: the reading is wrong, and a `worked_example` "
            "whose reproduction fails is not a weaker fixture, it is a false one"
        )

    # --- what the example does NOT establish -------------------------------------------
    exception_reached = any(
        0 in (chart_before_by_sign[SIGNS[i]] for i in trine)
        for trine in ((i, i + 4, i + 8) for i in range(4))
    )

    refusals = [
        Refusal(
            subject="the chapter's stated rule, as a description of this example's method",
            reason="fragment_not_found",
            detail=(
                "the chapter's rule sentence, read literally, deducts a group member's figure "
                "from the sum of the group's three figures. Applied to this example's own "
                "first group that gives a figure larger than any in it. ⛔ The method the "
                "example resolves to is a different one, so reproducing the example does not "
                "establish the rule as stated - it establishes what the example does"
            ),
            what_would_close_it=(
                "a second translation whose rule sentence and illustration agree, or the "
                "original, in which the sentence could be read directly"
            ),
        ),
        Refusal(
            subject="the exception the chapter attaches to the rule",
            reason="fragment_not_found",
            detail=(
                "the chapter states that no reduction is needed where a member of a group "
                "holds nothing. ⛔ No group in this example contains such a member - measured, "
                "not assumed - so every figure here is produced without the exception ever "
                "being reached. An implementation with the exception inverted reproduces this "
                "example exactly"
            ),
            what_would_close_it=(
                "an illustration in which some group holds a member with nothing, which this "
                "chapter does not print"
            ),
        ),
        Refusal(
            subject="a second edition's printing of the same example",
            reason="no_edition_in_hand",
            detail=(
                "both witnesses here are the chart and the prose of one copy of one "
                "translation. ⚠ They are independent transcriptions and not independent "
                "sources: a figure mis-set in this printing is mis-set in both"
            ),
            what_would_close_it="another printing or translation of the same chapter",
        ),
    ]

    # --- rows ----------------------------------------------------------------------------
    def locus_for(locus: str, fragment: str, *, kind: str, status: str) -> dict[str, Any]:
        return Locus(
            source_kind=kind,
            edition=edition,
            locus=locus,
            interpretation_status=status,
            fragment=fragment,
        ).as_json()

    rows: list[dict[str, Any]] = [
        {
            "section": "printed_figures",
            "finding": "chart",
            **chart_before.as_json(),
            "keyed_by_sign": chart_before_by_sign,
            "the_chart_begins_at": CHART_BEGINS_AT,
            "the_chart_begins_at_locus": locus_for(
                "chapter 67, the notes below the chart",
                CHART_BEGINS_AT_FRAGMENT,
                kind="commentary",
                status="quoted",
            ),
        },
        {
            "section": "printed_figures",
            "finding": "chart",
            **chart_after.as_json(),
            "keyed_by_sign": chart_after_by_sign,
            "note": (
                "⚠ this row of the chart survived the rendering as a run of digits with the "
                "cell boundaries lost, so it is read digit by digit and counted against the "
                "twelve the signs require. It is the prose that makes that safe to do"
            ),
        },
    ]
    for group, prose_row in zip(PROSE, prose_rows):
        rows.append(
            {
                "section": "printed_figures",
                "finding": "prose",
                **prose_row,
                "locus": locus_for(
                    f"chapter 67, the notes below the chart, {group['group']}",
                    group["fragment"],
                    kind="worked_illustration",
                    status="quoted",
                ),
            }
        )
    rows += [
        {"section": "printed_figures", "finding": "witness_agreement", **before_agreement},
        {"section": "printed_figures", "finding": "witness_agreement", **after_agreement},
        {
            "section": "printed_figures",
            "finding": "witness_agreement",
            "label": "why this control is here at all",
            "meaning": (
                "⭐ the source printed its example twice and thereby supplied its own second "
                "witness. Both transcriptions are taken independently and compared cell by "
                "cell, so a table the rendering mangled would appear as a disagreement rather "
                "than pass as evidence. ⚠ They are two transcriptions of one printing, not "
                "two sources: a figure mis-set at the press is mis-set in both"
            ),
        },
        {
            "section": "reproduction",
            "finding": "reproduction",
            **reproduction,
            "method_as_the_example_resolves_it": (
                "within each group of three, the smallest figure is deducted from all three"
            ),
            "method_locus": locus_for(
                "chapter 67, the notes below the chart, where the method is applied",
                PROSE[0]["fragment"],
                kind="worked_illustration",
                status="read_from_worked_example",
            ),
            "what_this_establishes": (
                "that the method read off this illustration returns the figures the source "
                "printed. ⛔ Nothing about modern accuracy, and nothing about whether the "
                "method is correct - which is why this kind may never carry a budget row"
            ),
        },
        {
            "section": "resolution",
            "finding": "limit",
            "limit": "the example does not exercise the exception the chapter states",
            "the_exception_as_stated": locus_for(
                "chapter 67, shlokas 3-5, the exception",
                STATED_EXCEPTION_FRAGMENT,
                kind="translation",
                status="quoted",
            ),
            "any_group_contains_a_member_holding_nothing": exception_reached,
            "meaning": (
                "⛔ measured, not assumed: no group in this example holds a member with "
                "nothing, so the exception is never reached. An implementation that inverted "
                "it would reproduce every figure here. A worked example resolves a method only "
                "over the inputs it happens to contain"
            ),
        },
        {
            "section": "resolution",
            "finding": "limit",
            "limit": "the method reproduced is not the rule the chapter states",
            "the_rule_as_stated": locus_for(
                "chapter 67, shlokas 3-5, the rule",
                STATED_RULE_FRAGMENT,
                kind="translation",
                status="disputed_reading",
            ),
            "read_literally_it_gives": (
                "a group member's figure deducted from the sum of the group's three, which "
                "for this example's first group is larger than any figure in it"
            ),
            "meaning": (
                "⭐ what is reproduced below is what the source's illustration does, not what "
                "its rule sentence says. The two are recorded as separate claims because they "
                "are separate claims"
            ),
        },
    ]
    rows += [{"section": "resolution", **refusal.as_row()} for refusal in refusals]

    header = Header(
        fixture_kind="worked_example",
        reference="R6",
        generator=generator_for(script),
        generated=today(),
        title=(
            "A source's own worked reduction, transcribed from its chart and from its prose "
            "independently, and reproduced from the figures it printed"
        ),
        oracle=source_oracle([edition], resolved=len(PROSE) + 4, refused=len(refusals)),
        locus=Locus(
            source_kind="worked_illustration",
            edition=edition,
            locus="chapter 67, the worked illustration below the chart",
            interpretation_status="read_from_worked_example",
            fragment=PROSE[0]["fragment"],
        ).as_json(),
        # ⛔ Required by this kind and fixed by the contract: what a text resolves proves that
        #    we followed the text, and nothing about how well the text models anything.
        budget_basis="source_reproduction",
        classification={
            "printed_figures": {"class": "exact"},
            "reproduction": {"class": "exact"},
            "resolution": {"class": "exact"},
        },
        request={
            "what_was_asked_of_the_source": (
                "the twelve figures it prints before its reduction, the twelve it prints "
                "after, and the method that carries one to the other"
            ),
            "the_chart_begins_at": CHART_BEGINS_AT,
            "figures_per_row": len(SIGNS),
            "witnesses": [
                "the chapter's chart, transcribed cell by cell",
                "the chapter's prose, read group by group",
            ],
            "normalisation": (
                "as declared on the rendering; both witnesses are read from the same "
                "normalised text"
            ),
        },
        summary={
            "cells_the_two_witnesses_agree_on": {
                "before": before_agreement["cells_agreeing"],
                "after": after_agreement["cells_agreeing"],
                "of": len(SIGNS),
            },
            "cells_reproduced": reproduction["cells_agreeing"],
            "of": reproduction["cells_compared"],
            "what_this_establishes": (
                "that the method this illustration resolves to returns the figures the source "
                "printed. ⛔ Not that the method is correct, and not anything about modern "
                "accuracy - this kind may carry no budget row for exactly that reason"
            ),
            "what_it_does_not_establish": [
                "the chapter's stated rule, which read literally is a different method",
                "the exception the chapter attaches to that rule, which this example's "
                "figures never reach - measured",
            ],
            **refusal_summary(refusals),
        },
        row_schema={
            "chart": "a row of the source's chart, with the cell count it was checked against",
            "prose": "one group as the source spells it out, with the sentence quoted",
            "witness_agreement": "the chart and the prose compared cell by cell",
            "reproduction": "the method applied, against the figures the source printed",
            "limit": "something this example does not establish, measured",
            "refused": "a claim considered and not written down, with what would close it",
        },
        notes=[
            "⛔ A WORKED EXAMPLE PROVES REPRODUCTION, NOT ACCURACY. What is established is "
            "that a method read off this source's own illustration, applied to the figures "
            "this source printed, returns the figures this source printed. The contract "
            "forbids this kind from carrying a budget row, and that is the reason.",
            "⭐ THE SOURCE PRINTED ITS EXAMPLE TWICE AND SO SUPPLIED ITS OWN SECOND WITNESS. "
            "The chart and the prose are transcribed independently and compared cell by cell "
            "before anything is reproduced. ⚠ They are two transcriptions of one printing, "
            "not two sources - a figure mis-set at the press is mis-set in both.",
            "⛔ THE EXAMPLE DOES NOT EXERCISE THE EXCEPTION ITS OWN CHAPTER STATES - measured. "
            "No group here holds a member with nothing, so an implementation that inverted "
            "the exception would reproduce every figure in this file. A worked example "
            "resolves a method only over the inputs it happens to contain, and a consumer "
            "pinning against it has tested the inputs and not the rule.",
            "⛔ AND THE METHOD REPRODUCED IS NOT THE RULE THE CHAPTER STATES. Read literally, "
            "the rule sentence is a different method, and the disagreement is recorded as a "
            "fork of its own elsewhere. This file reproduces what the illustration does; it "
            "does not decide what the chapter means.",
            "⚠ ONE OF THE TWO CHART ROWS SURVIVED THE RENDERING AS A RUN OF DIGITS WITH ITS "
            "CELL BOUNDARIES LOST. It is read digit by digit and counted against the twelve "
            "the signs require, and it is the prose that makes that safe. A row read this way "
            "without a second witness would be a guess with a plausible shape.",
            "⛔ R6 RECORDS WHAT A TEXT STATES AND RESOLVES. " + NO_LICENCE_DETERMINATION + ".",
        ],
    )
    path = args.out / "textual" / "reduction-worked-example.jsonl"
    count = write_jsonl(
        path, header, rows, declared_sections=["printed_figures", "reproduction", "resolution"]
    )
    print(f"wrote {count} rows -> {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
