"""One chapter, one configuration, three incompatible readings — none of them adopted.

⭐ **A fork is usually described as two books disagreeing. This one is a chapter disagreeing
with itself**, and that is the harder kind to notice, because a reader who consults the
source once comes away certain. The chapter states a reduction rule for a configuration, then
works two illustrations of that same configuration, and the three do not agree: applied to
one pair of numbers they give three different answers.

⛔ **NEITHER MEMBER IS THE FINDING; THE PAIR IS.** A consumer who read only the rule would
implement one method, a consumer who followed only the first illustration another, and each
would be certain the source supported it. What the source supports is a question it does not
settle, and recording that is this file's whole content. ⛔ No reading here is adopted,
preferred or ranked.

⭐ **The thing that would arbitrate is measured to be unreadable.** The chapter prints a chart
carrying the whole illustration, and in the copy in hand that chart lost two of its twelve
cells in each of its two rows. ⚠ That is a property of *that table*, not of the copy: the
neighbouring chapter's chart reads complete, twelve of twelve, in the same rendering. Both
measurements are on the file, because either alone licenses a wrong general rule about what a
machine reading of a scan can be trusted with.

⛔ **Recorder, never explainer.** The arithmetic below applies each reading, as stated, to the
one configuration all three address. It implements nothing and endorses nothing.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from saakshi.fixture import Header, describe_reserved_names, write_jsonl  # noqa: E402
from saakshi.provenance import generator_for, today  # noqa: E402
from saakshi.texts import CACHE, acquire, load  # noqa: E402
from saakshi.textual import (  # noqa: E402
    NO_LICENCE_DETERMINATION,
    Locus,
    Refusal,
    read_integer_cells,
    refusal_summary,
    resolve,
    source_oracle,
)

EDITION = "bphs_santhanam"

#: The configuration all three readings address, and the numbers the chapter itself uses for
#: it. ⚠ Both illustrated pairs are pairs of signs under one lord, both unoccupied, holding
#: these two numbers — so nothing the rule mentions distinguishes them.
SHARED_CONFIGURATION = {
    "two_signs_of_one_lord": True,
    "neither_occupied_by_a_body": True,
    "numbers_held": [2, 1],
    "why_the_two_illustrations_are_one_case": (
        "the chapter's rules turn on two things only: whether each of the pair is occupied, "
        "and how their numbers compare. Both illustrated pairs are unoccupied and hold two "
        "and one. ⛔ Nothing the chapter states separates them"
    ),
}


def _bigger_smaller(values: list[int]) -> tuple[int, int]:
    return max(values), min(values)


def reading_both_take_the_smaller(values: list[int]) -> tuple[int, int]:
    """As the rule states it: both are given the smaller number."""
    _, smaller = _bigger_smaller(values)
    return smaller, smaller


def reading_the_smaller_goes_to_zero(values: list[int]) -> tuple[int, int]:
    """As the first illustration works it: the smaller is reduced to zero, the bigger stands."""
    bigger, _ = _bigger_smaller(values)
    return bigger, 0


def reading_the_difference_leaves_both(values: list[int]) -> tuple[int, int]:
    """As the second illustration works it: the difference is deducted from both."""
    bigger, smaller = _bigger_smaller(values)
    return bigger - (bigger - smaller), smaller - (bigger - smaller)


READINGS: tuple[dict[str, Any], ...] = (
    {
        "id": "both_are_given_the_smaller_number",
        "how_the_source_puts_it": "both should be given the smaller number",
        "source_kind": "translation",
        "interpretation_status": "quoted",
        "locus": "chapter 68, shlokas 1-5, the first of the six numbered rules",
        "fragment": (
            "If both the rashis are without a planet and the Trikona Shodhana numbers "
            "are different (one is more than other), both should be given the smaller, number."
        ),
        "apply": reading_both_take_the_smaller,
        "standing": (
            "the chapter's own numbered rule for this configuration, in the translator's "
            "rendering of the text"
        ),
    },
    {
        "id": "the_smaller_goes_to_zero_and_the_bigger_stands",
        "how_the_source_puts_it": (
            "the smaller is reduced to zero and the bigger is left unchanged"
        ),
        "source_kind": "worked_illustration",
        "interpretation_status": "read_from_worked_example",
        "locus": (
            "chapter 68, the imaginary illustration, the pair of signs under the lord of the "
            "second and seventh from the first sign"
        ),
        "fragment": (
            "By Ekadhipatya Shodhana, the number of Libra will be reduced to zero and the "
            "number of Taurus will remain unchanged."
        ),
        "apply": reading_the_smaller_goes_to_zero,
        "standing": (
            "not stated as a rule anywhere in the chapter; read off an illustration the "
            "chapter works itself"
        ),
        "setup_fragment": (
            "Taurus is without planet and has a bigger number (2). Libra is without planet "
            "and has a smaller number (1)."
        ),
    },
    {
        "id": "the_difference_is_deducted_from_both",
        "how_the_source_puts_it": "the difference between the two is deducted from both",
        "source_kind": "worked_illustration",
        "interpretation_status": "read_from_worked_example",
        "locus": (
            "chapter 68, the imaginary illustration, the pair of signs under the lord of the "
            "ninth and twelfth from the first sign"
        ),
        "fragment": (
            "By Ekadhipatya Shodhana We will deduct the difference between 2 and 1, that is "
            "1, from both the numbers. The number of Sagittarius will be reduced to zero and "
            "the number of Pisces will be reduced to 1."
        ),
        "apply": reading_the_difference_leaves_both,
        "standing": (
            "not stated as a rule anywhere in the chapter; read off a second illustration in "
            "the same paragraph as the first, which it does not agree with"
        ),
        "setup_fragment": (
            "Both Sagittarius and Pisces are without planets. Sagittarius possess 1 and Pisces 2."
        ),
    },
)


def reading_blocks(edition) -> list[dict[str, Any]]:
    """The `readings` block of the header. ⛔ Each carries its own complete, resolved locus."""
    blocks = []
    for reading in READINGS:
        bigger, smaller = reading["apply"](list(SHARED_CONFIGURATION["numbers_held"]))
        blocks.append(
            {
                "reading": reading["id"],
                "how_the_source_puts_it": reading["how_the_source_puts_it"],
                "standing": reading["standing"],
                "applied_to_the_shared_configuration": {
                    "the_larger_becomes": bigger,
                    "the_smaller_becomes": smaller,
                },
                "locus": Locus(
                    source_kind=reading["source_kind"],
                    edition=edition,
                    locus=reading["locus"],
                    interpretation_status=reading["interpretation_status"],
                    fragment=reading["fragment"],
                ).as_json(),
            }
        )
    return blocks


def evidence_rows(edition) -> list[dict[str, Any]]:
    rows = []
    for reading in READINGS:
        row: dict[str, Any] = {
            "finding": "reading",
            "reading": reading["id"],
            "how_the_source_puts_it": reading["how_the_source_puts_it"],
            "standing": reading["standing"],
            "locus": Locus(
                source_kind=reading["source_kind"],
                edition=edition,
                locus=reading["locus"],
                interpretation_status=reading["interpretation_status"],
                fragment=reading["fragment"],
            ).as_json(),
        }
        if reading.get("setup_fragment"):
            # ⭐ The words that establish the configuration, resolved separately from the
            #    words that give the answer. Without them the reading is an assertion that
            #    the two illustrations are the same case, which is the load-bearing claim.
            row["the_configuration_as_the_source_states_it"] = Locus(
                source_kind="worked_illustration",
                edition=edition,
                locus=reading["locus"] + ", the sentence setting it up",
                interpretation_status="quoted",
                fragment=reading["setup_fragment"],
            ).as_json()
        rows.append(row)
    return rows


def divergence_row() -> dict[str, Any]:
    """The three readings applied to the one configuration all three address."""
    numbers = list(SHARED_CONFIGURATION["numbers_held"])
    answers = {
        reading["id"]: list(reading["apply"](numbers)) for reading in READINGS
    }
    distinct = {tuple(v) for v in answers.values()}
    return {
        "finding": "divergence",
        "configuration": SHARED_CONFIGURATION,
        "answers_as_larger_then_smaller": answers,
        "distinct_answers": len(distinct),
        "readings_compared": len(answers),
        "they_all_agree": len(distinct) == 1,
        "meaning": (
            "⛔ three readings taken from one chapter, applied to the one configuration all "
            "three of them address, giving three different answers. A consumer that consulted "
            "the source once would have come away with whichever of the three it happened to "
            "read, and no way of knowing there were others"
        ),
        "not_adopted": (
            "⛔ this file adopts none of them, prefers none of them and does not rank them. "
            "Recording that the source does not settle the question is the whole of the claim"
        ),
    }


def table_rows(edition) -> list[dict[str, Any]]:
    """What the charts say — and the measurement of whether they can be read at all.

    ⭐ The disputed chapter's own chart is what would arbitrate between its rule and its
    illustrations. It is measured here rather than described, and it is short. ⚠ The
    neighbouring chapter's chart, in the same copy and the same rendering, is complete — so
    the failure belongs to that table and a general rule drawn from either alone is wrong.
    """
    # ⚠ The landmarks are quoted from the middle of the chart's own row captions, which the
    #   rendering clipped at the left edge. ⛔ A shorter closing landmark was tried and
    #   refused for occurring forty times — and measured afterwards, it would have opened
    #   exactly this region anyway. It was ambiguous and harmless, which is the case a cell
    #   count cannot see and the reason the ambiguity refusal is not merely a second count.
    disputed_input = read_integer_cells(
        edition,
        label="the disputed chapter's chart, its reduced-number row",
        after="ikona Corrected)",
        before="kadhipatya Corrected)",
        cells=12,
    )
    disputed_output = read_integer_cells(
        edition,
        label="the disputed chapter's chart, its final row",
        after="kadhipatya Corrected)",
        before="Herein Aries",
        cells=12,
    )
    # ⚠ The caption alone occurs twice in this copy, and its earlier occurrence stands over a
    #   different chart. Measured: the region it opens runs to 548 figures where 12 are
    #   required — so here the cell count would also have caught it, and the two checks are
    #   independent rather than redundant. ⛔ The ambiguity refusal is what caught it first,
    #   and it is the one that does not depend on knowing the answer's shape in advance.
    #   The landmark below carries the preceding cell in order to resolve.
    neighbour = read_integer_cells(
        edition,
        label="the neighbouring chapter's chart, its input row",
        after="Kt Number of Rekhas",
        before="Page 710 Trikona Shodhana",
        cells=12,
    )
    rows = []
    for reading, role in (
        (disputed_input, "the chart that would arbitrate this fork"),
        (disputed_output, "the same chart's second row"),
        (neighbour, "a chart in the neighbouring chapter, as a control on the rendering"),
    ):
        rows.append(
            {
                "finding": "table_legibility",
                "role": role,
                **reading.as_json(),
                "meaning": (
                    "a row printed across the twelve signs has twelve cells. ⛔ Where fewer "
                    "were read, the cells that survived are still digits in a plausible "
                    "order, so a recorder that did not count them would have transcribed a "
                    "short row as an answer"
                ),
            }
        )
    rows.append(
        {
            "finding": "table_legibility",
            "role": "the pair, which is the finding",
            "legible_tables": [r.label for r in (disputed_input, disputed_output, neighbour) if r.legible],
            "illegible_tables": [
                r.label for r in (disputed_input, disputed_output, neighbour) if not r.legible
            ],
            "meaning": (
                "⭐ in one copy and one rendering, one chapter's chart reads complete and the "
                "next chapter's loses cells. ⛔ Legibility is therefore a property of a table "
                "and must be measured per table: 'a machine reading of a scan cannot be "
                "trusted with a table' and 'this one came through fine' are both wrong, and "
                "either measurement alone supports one of them"
            ),
        }
    )
    return rows


def refusals_for(edition) -> list[Refusal]:
    heading = "Ekadhipatya Shodhana in the Ashtaka Varga Scheme"
    heading_hits = resolve(edition, heading).occurrences
    return [
        Refusal(
            subject="the chapter's own chart, as the arbiter between its rule and its illustrations",
            reason="table_not_legible_in_this_rendering",
            detail=(
                "the chart carries the whole illustration and would settle which reading the "
                "chapter means. Both of its rows were measured at ten cells where the twelve "
                "signs require twelve, so it is not read here at all rather than read in part"
            ),
            what_would_close_it=(
                "a rendering that preserves the chart, or a second copy of the same "
                "translation whose chart is legible"
            ),
        ),
        Refusal(
            subject=f"a locus cited by the chapter heading alone ({heading_hits} occurrences)",
            reason="fragment_ambiguous",
            detail=(
                "the words of the heading are printed where the chapter opens and again in "
                "the front matter that points at it. ⛔ A recorder taking the first hit would "
                "cite a table of contents and call it the chapter. Resolution requires "
                "exactly one occurrence, so headings are not used as loci here"
            ),
            what_would_close_it=(
                "quoting words from the passage itself, which is what every locus in this "
                "file does"
            ),
        ),
        Refusal(
            subject="the Sanskrit standing above each of the chapter's numbered rules",
            reason="script_not_present_in_this_rendering",
            detail=(
                "the copy carries zero code points of the script the original is written in, "
                "measured. The disagreement recorded here is between a translator's rendering "
                "of a rule and the same translator's illustrations of it; ⛔ whether the "
                "original admits it cannot be established from this copy at all"
            ),
            what_would_close_it=(
                "a copy carrying the original, which would make the fork checkable at its "
                "source rather than only in translation"
            ),
        ),
        Refusal(
            subject="a second translation of this chapter",
            reason="no_edition_in_hand",
            detail=(
                "a second translator's rendering would show whether the disagreement is in "
                "the work or in this translation of it, which is the first question a reader "
                "of this file will ask. ⛔ It is not answered here"
            ),
            what_would_close_it="a resolvable copy of another translation of the same chapter",
        ),
    ]


def build_header(script: Path, edition, readings, refusals, divergence) -> Header:
    return Header(
        fixture_kind="textual_fork",
        reference="R6",
        generator=generator_for(script),
        generated=today(),
        title=(
            "A reduction rule on which one chapter disagrees with its own two worked "
            "illustrations, recorded as three readings and adopted as none"
        ),
        oracle=source_oracle([edition], resolved=len(readings), refused=len(refusals)),
        readings=readings,
        summary={
            "readings": len(readings),
            "distinct_answers_to_the_one_shared_configuration": divergence["distinct_answers"],
            "all_three_sit_in": "one chapter of one translation",
            "adopted": None,
            "adopted_note": (
                "⛔ none. A fork is a record that a source does not settle a question, and "
                "settling it here would be this repository substituting itself for the source"
            ),
            "the_arbiter": (
                "the chapter's own chart would decide it, and both of its rows were measured "
                "at ten cells where twelve are required. ⚠ The neighbouring chapter's chart "
                "reads twelve of twelve in the same rendering, so the failure is that "
                "table's and not the copy's"
            ),
            **refusal_summary(refusals),
        },
        row_schema={
            "reading": "one located reading, with the words that establish its configuration",
            "divergence": "the readings applied to the one configuration all of them address",
            "table_legibility": "a chart measured against the cell count its subject requires",
            "refused": "a claim considered and not written down, with what would close it",
        },
        notes=[
            "⛔ THE PAIR IS THE FINDING, NOT EITHER MEMBER. Read alone, the chapter's rule is "
            "a rule and each illustration is an illustration, and each of the three reads as "
            "settled. Read together they give three different answers to one configuration. "
            "A consumer that consulted this source once would have come away certain, and "
            "would have been certain of whichever of the three it happened to open at.",
            "⛔ NO READING IS ADOPTED, PREFERRED OR RANKED. What is recorded is that the "
            "source does not settle the question. A recorder that picked one would have "
            "turned an open question into a decision nobody made, in a file whose whole "
            "purpose is to keep it open.",
            "⭐ TWO OF THE THREE READINGS ARE NOT STATED ANYWHERE. They are read off "
            "illustrations the chapter works itself, and every row says so in its "
            "interpretation status. ⚠ That is a weaker kind of evidence than a stated rule "
            "and a stronger kind than an inference: the source resolved these numbers, and "
            "only one method resolves them the way it did.",
            "⭐ LEGIBILITY IS A PROPERTY OF A TABLE, NOT OF A RENDERING - measured, in both "
            "directions, in one copy. The chart that would arbitrate this fork lost two of "
            "twelve cells in each row; the neighbouring chapter's chart came through "
            "complete. ⛔ Either measurement alone licenses a wrong general rule about what a "
            "machine reading of a scan can be trusted with, so both are here.",
            "⛔ THE ORIGINAL IS NOT IN THIS COPY. Zero code points of its script are present, "
            "measured. Everything above is a disagreement inside one translation, and "
            "whether the work itself admits it is not established here. "
            + NO_LICENCE_DETERMINATION + ".",
        ],
    )


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

    readings = reading_blocks(edition)
    divergence = divergence_row()
    print(
        f"{divergence['readings_compared']} reading(s) -> "
        f"{divergence['distinct_answers']} distinct answer(s) to one configuration"
    )
    if divergence["they_all_agree"]:
        raise RuntimeError(
            "the three readings agreed, so there is no fork to record. ⛔ This file exists "
            "only because they do not; emitting it anyway would publish a disagreement that "
            "is not there"
        )

    refusals = refusals_for(edition)
    rows = evidence_rows(edition)
    rows.append(divergence)
    rows += table_rows(edition)
    rows += [refusal.as_row() for refusal in refusals]

    header = build_header(script, edition, readings, refusals, divergence)
    path = args.out / "textual" / "reduction-rule-fork.jsonl"
    count = write_jsonl(path, header, rows)
    print(f"wrote {count} rows -> {path}")
    print(f"refused {len(refusals)} claim(s), each named on a row of its own")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
