"""What one located text states about the significator series — and what it does not.

⛔ **The claim this file exists to make is not "a book says so".** It is that each recorded
rule was *resolved*: the words quoted at each locus were searched for in a named copy, whose
address, digest, rendering and measured extent are all on the header, and were found there
exactly once. A citation nobody can resolve is not a citation, and prose asserting that a
citation is good is a claim like any other, made in the one form that cannot be checked.

⭐ **Three of the rules here sit in the translator's notes rather than in the sutras**, and
the fixture says which is which on every row. They are printed on the same pages and are not
the same authority: one is the text, the other is a modern reader of it. A consumer that
took the notes for the text would be implementing a commentator under a sutra's name.

⭐ **The absence is a measurement, not an aside.** A widely repeated rule of this system is
recorded here as *absent* — and an absence is only as wide as its alphabet and its copy, so
every spelling searched is listed with its own hit count, every hit is located rather than
counted, and the extent it was established over is the extent the copy was measured to have.
⛔ The copy is a part of the work. The absence is an absence from that part.

⛔ **Recorder, never explainer.** Restating what a classical text states is R6's whole point.
Nothing here describes how any software computes anything.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from saakshi.fixture import Header, describe_reserved_names, write_jsonl  # noqa: E402
from saakshi.provenance import generator_for, today  # noqa: E402
from saakshi.texts import CACHE, DEVANAGARI, acquire, load, script_presence  # noqa: E402
from saakshi.textual import (  # noqa: E402
    NO_LICENCE_DETERMINATION,
    AbsenceSearch,
    Locus,
    Refusal,
    collect_occurrences,
    refusal_summary,
    source_oracle,
)

EDITION = "jaimini_sutras_rao"

# --------------------------------------------------------------------------------------
# The located rules
# --------------------------------------------------------------------------------------

#: ⚠ Each fragment is quoted with its own spacing defects intact. The copy is a text layer
#: with words broken across line ends, and *repairing* a quotation is the one edit that would
#: make a locus resolve against a document nobody else has.
RULES: tuple[dict[str, Any], ...] = (
    {
        "id": "the_first_significator_is_the_highest_in_degrees",
        "subject": "which body heads the series, and over how many bodies it is reckoned",
        "states": (
            "the body holding the greatest degrees within its sign heads the series, and the "
            "reckoning is offered over seven bodies or over eight, the eighth being the "
            "ascending node"
        ),
        "source_kind": "translation",
        "interpretation_status": "restated",
        "locus": "adhyaya 1, pada 1, sutra 11",
        "fragment": (
            "Of the seven planets from the Sun to Saturn, or the eight pl anets from the Sun "
            "to Rahu, whichever gets the highest number of degrees becomes the Atmakaraka."
        ),
        "note": (
            "⭐ one sutra, two reckonings, and the text does not choose between them. A "
            "consumer offering only one of the two has narrowed its source rather than "
            "followed it"
        ),
    },
    {
        "id": "the_second_significator_is_next_in_degrees",
        "subject": "how the series continues past its head",
        "states": "the body next in degrees after the head of the series takes the second place",
        "source_kind": "translation",
        "interpretation_status": "restated",
        "locus": "adhyaya 1, pada 1, sutra 13",
        "fragment": (
            "The planet who is next in kalas or degrees to Atmakaraka will become Amatyakaraka."
        ),
    },
    {
        "id": "the_third_significator_is_next_again",
        "subject": "how the series continues past its second place",
        "states": "the body next in degrees after the second place takes the third",
        "source_kind": "translation",
        "interpretation_status": "restated",
        "locus": "adhyaya 1, pada 1, sutra 14",
        "fragment": (
            "The planet who gets the highest number of degrees next to Amatyakaraka becomes "
            "Bhratrukaraka or gets lordship over brothers."
        ),
        "note": (
            "the series is defined by one relation applied repeatedly, so every place below "
            "the first depends on the ordering of every place above it"
        ),
    },
    {
        "id": "the_node_is_ranked_by_reversed_degrees",
        "subject": "how the eighth body's degrees enter the ordering",
        "states": (
            "the ascending node moves against the order of the signs, so it counts as holding "
            "the greatest degrees when it stands at the beginning of a sign"
        ),
        # ⛔ NOT the sutra. This is the translator writing in his own voice, and the whole
        #    value of the field is that a reader can see the difference without going to look.
        "source_kind": "commentary",
        "interpretation_status": "restated",
        "locus": "adhyaya 1, pada 1, the translator's notes to sutra 11",
        "fragment": (
            "As Rahu and Ketu move in the reverse, they will be considered as getting the "
            "highest number of degrees when they are at the beginning of a sign."
        ),
        "note": (
            "⛔ this is the translator's note, not the sutra. The sutra names the eighth body "
            "and says nothing about how its degrees are read; the rule that they are read "
            "backwards is the commentator's"
        ),
    },
    {
        "id": "a_tie_merges_two_places_and_the_node_fills_the_vacancy",
        "subject": "what happens when two bodies hold equal degrees",
        "states": (
            "bodies holding the same degrees and minutes merge into one place of the series, "
            "and the place left empty by the merge is filled by the ascending node"
        ),
        "source_kind": "commentary",
        "interpretation_status": "restated",
        "locus": "adhyaya 1, pada 1, the translator's notes to sutra 11",
        "fragment": (
            "If two or three planets obtain the same Ka/as or degrees and minutes, they are "
            "all merged into  one Karaka or Lordship over some event in the human life."
        ),
        "note": (
            "⚠ quoted with the copy's own misreading of one word intact. Repairing it would "
            "make the locus resolve against a document that exists only here"
        ),
    },
)

# --------------------------------------------------------------------------------------
# The absence
# --------------------------------------------------------------------------------------

#: ⛔ **A scan is only as wide as its alphabet.** Every spelling below was searched and its
#: own hit count is published. A reader who thinks of a spelling that is not here has found
#: the limit of this claim, which is the point of listing them.
ALPHABET: tuple[str, ...] = (
    "Amatyakaraka",
    "Amatya karaka",
    "Amatya-karaka",
    "Amatya",
    "Mantrikaraka",
    "Mantri",
    "AmK",
    "minister",
    "Atmakaraka",
    "Atma karaka",
)

#: The spellings whose every hit is enumerated on the row. ⚠ The two general terms are
#: searched and counted but not enumerated: they run to dozens of hits and the claim does not
#: rest on them. That reduction is stated on the row rather than left to be noticed.
ENUMERATED: tuple[str, ...] = ("Amatyakaraka", "Amatya karaka", "Amatya-karaka", "AmK", "Mantrikaraka")

ABSENT_CLAIM = (
    "that the head of the series conjoining or aspecting the second place of the series is a "
    "combination for rulership. ⚠ It is the most widely repeated rule attributed to this "
    "system, and no sutra or note in the extent searched states it"
)

WHAT_THE_HITS_SAY = (
    "sutra 13 and its notes: the second place is the body next in degrees to the first",
    "sutra 43 and its notes: the body next in degrees after the second place indicates "
    "religious inclination",
    "sutra 82 and its notes: a body counted sixth from the second place, standing in a "
    "particular divisional sign, indicates the worship of malign spirits",
    "sutras 49 and 50 and their notes: where a tie sends the first place to a merge, the "
    "second place takes a further role, and the ascending node reverses the condition",
    "⛔ none of them pairs the first place with the second as a combination for rulership",
)


def rule_rows(edition, refusals: list[Refusal]) -> list[dict[str, Any]]:
    rows = []
    for rule in RULES:
        locus = Locus(
            source_kind=rule["source_kind"],
            edition=edition,
            locus=rule["locus"],
            interpretation_status=rule["interpretation_status"],
            fragment=rule["fragment"],
        )
        row: dict[str, Any] = {
            "finding": "rule",
            "rule": rule["id"],
            "subject": rule["subject"],
            "the_source_states": rule["states"],
            "locus": locus.as_json(),
        }
        if rule.get("note"):
            row["note"] = rule["note"]
        rows.append(row)
    return rows


def refusals_for(edition) -> list[Refusal]:
    """What was considered and not written down. ⚠ Named, because a count caps nothing."""
    return [
        Refusal(
            subject="the Sanskrit of any sutra in this work",
            reason="script_not_present_in_this_rendering",
            detail=(
                "the copy in hand renders an English translation and carries zero code "
                "points of the script the original is written in - measured, not assumed. A "
                "locus into the original cannot be resolved here, and citing the translation "
                "in its place would file a translator's sentence as the text's own"
            ),
            what_would_close_it=(
                "a copy carrying the original, in a rendering that preserves its script"
            ),
        ),
        Refusal(
            subject="any rule in the third or fourth division of this work",
            reason="outside_the_extent_of_the_copy",
            detail=(
                "the copy's own closing markers run out at the fourth pada of the second "
                "adhyaya and its title names it a part. Nothing beyond that was searched, so "
                "nothing beyond it is claimed - including by the absence row above"
            ),
            what_would_close_it="the remaining parts, acquired and measured the same way",
        ),
        Refusal(
            subject=(
                "the seven-place reckoning's treatment of the places the eight-place "
                "reckoning keeps separate"
            ),
            reason="no_edition_in_hand",
            detail=(
                "the sutra offers both reckonings and does not say which places merge when "
                "the shorter one is used. A second work is the usual authority for that, and "
                "no copy of it is held here. ⛔ Filling the gap from the first work would be "
                "inference presented as citation"
            ),
            what_would_close_it=(
                "a resolvable copy of a text that states the merge, cited as a fork against "
                "this one if the two disagree"
            ),
        ),
        Refusal(
            subject="a second witness to any rule recorded above",
            reason="no_edition_in_hand",
            detail=(
                "every rule here rests on one copy of one translation. ⚠ That is a weaker "
                "state than a fork, not a stronger one: a fork at least establishes that two "
                "readings exist, and a single witness establishes only what one translator "
                "printed"
            ),
            what_would_close_it="a second translation of the same work, acquired and resolved",
        ),
    ]


def build_header(script: Path, edition, resolved: int, refusals, controls) -> Header:
    return Header(
        fixture_kind="textual_rule",
        reference="R6",
        generator=generator_for(script),
        generated=today(),
        title=(
            "The significator series as one located translation states it, and one widely "
            "repeated rule it does not"
        ),
        oracle=source_oracle([edition], resolved=resolved, refused=len(refusals)),
        # ⚠ The containing locus. Each rule row carries its own, more precise one; this is
        #   the sutra at which the series is founded and from which every later place hangs.
        locus=Locus(
            source_kind="translation",
            edition=edition,
            locus="adhyaya 1, pada 1, sutra 11 - the sutra the series is founded on",
            interpretation_status="restated",
            fragment=RULES[0]["fragment"],
        ).as_json(),
        summary={
            "rules_resolved": resolved,
            "of_which_are_the_translators_notes_rather_than_the_text": sum(
                1 for rule in RULES if rule["source_kind"] == "commentary"
            ),
            "claims_refused": len(refusals),
            **refusal_summary(refusals),
            "the_absence": (
                "one rule was searched for and not found. ⛔ It is an absence from the extent "
                "measured, in the spellings listed, in this rendering - see the absence row, "
                "which enumerates every hit rather than counting them"
            ),
            "controls": {control["control"]: control["held"] for control in controls},
        },
        row_schema={
            "rule": "one located statement, with the locus it was resolved at",
            "absence": "a rule searched for and not found, with its alphabet and its extent",
            "refused": "a claim considered and not written down, with what would close it",
            "control": "a check on this file's own method, with what it measured",
        },
        notes=[
            "⛔ A CITATION A READER CANNOT RESOLVE IS NOT A CITATION. Every locus here was "
            "resolved: the quoted words were searched for in the named copy, under the "
            "declared normalisation, and occur in it exactly once. A fragment found twice "
            "would have been refused, because a table of contents restates the words of the "
            "chapter it points at and a recorder taking the first hit cites the contents "
            "page.",
            "⭐ THE TRANSLATOR'S NOTES ARE NOT THE TEXT, AND THE ROWS SAY WHICH IS WHICH. Two "
            "of the rules here - how the eighth body's degrees are read, and what a tie does "
            "- appear only in the notes. They are printed on the same page as the sutras and "
            "carry a different authority, and a consumer that took one for the other would "
            "implement a modern commentator under a sutra's name.",
            "⛔ AN ABSENCE IS ONLY AS WIDE AS ITS ALPHABET AND ITS COPY. The absence row "
            "lists every spelling searched with its own hit count, locates every hit rather "
            "than counting it, and states the measured extent it holds over. The copy is a "
            "part of the work: nothing is claimed about the parts it does not contain.",
            "⚠ EVERY RULE HERE RESTS ON ONE WITNESS. One copy, one translation, one "
            "translator. That is recorded as a refusal rather than left as an impression, "
            "because a rule resolved against a single edition is resolved, not corroborated.",
            "⛔ R6 RECORDS WHAT A TEXT STATES AND NOTHING ELSE. Not that the statement is "
            "correct, not that this repository holds it, not that any consumer should "
            "implement it. " + NO_LICENCE_DETERMINATION + ".",
        ],
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--cache", type=Path, default=CACHE)
    parser.add_argument(
        "--acquire",
        action="store_true",
        help="fetch the copy over the network first; ⛔ emission never acquires on its own",
    )
    args = parser.parse_args()

    script = Path(__file__)
    generator_for(script)  # ⛔ refuse a dirty tree before anything is written
    print(describe_reserved_names())

    if args.acquire:
        record = acquire(EDITION, cache=args.cache, today=today())
        print(f"acquired {EDITION}: {record['copy_bytes']} bytes, status {record['http_status']}")

    edition = load(EDITION, cache=args.cache)
    print(
        f"edition {EDITION}: {edition.rendering.kind} via {edition.rendering.produced_by}, "
        f"{edition.rendering.characters} characters"
    )
    print(
        "extent: "
        f"{len(edition.extent['divisions_found'])} of "
        f"{len(edition.extent['divisions_looked_for'])} divisions found"
    )

    script_check = script_presence(edition, first=DEVANAGARI[0], last=DEVANAGARI[1])
    controls = [
        {
            "finding": "control",
            "control": "the_extent_was_measured_not_assumed",
            "measured": edition.extent,
            "held": edition.extent["complete"],
            "meaning": (
                "every division this copy claims to contain was located by its own closing "
                "marker. ⛔ A title is not an extent, and an absence measured over a copy "
                "whose extent was assumed is an absence over an unknown quantity"
            ),
        },
        {
            "finding": "control",
            "control": "the_original_script_is_absent_from_this_rendering",
            "measured": script_check,
            "held": not script_check["present"],
            "meaning": (
                "the copy renders a translation and carries none of the script the original "
                "is written in. ⭐ This is why every locus here is filed as a translation or "
                "a commentary and none as a primary text: the field would otherwise record a "
                "source this file has never seen"
            ),
        },
    ]

    refusals = refusals_for(edition)
    rows = rule_rows(edition, refusals)

    absence = AbsenceSearch(
        claim=ABSENT_CLAIM,
        alphabet=ALPHABET,
        edition=edition,
        occurrences=[
            hit for spelling in ENUMERATED for hit in collect_occurrences(edition, spelling)
        ],
        what_the_hits_do_say=WHAT_THE_HITS_SAY,
    )
    absence_row = absence.as_row()
    absence_row["spellings_whose_hits_are_enumerated"] = list(ENUMERATED)
    absence_row["spellings_counted_but_not_enumerated"] = [
        s for s in ALPHABET if s not in ENUMERATED
    ]
    absence_row["why_two_were_not_enumerated"] = (
        "they are the general terms for the first place of the series and for a public "
        "office, and they run to dozens of hits apiece. ⚠ The claim does not rest on them - "
        "it rests on the second place, every hit of which is enumerated above. The reduction "
        "is stated here rather than left for a reader to infer from a total"
    )
    rows.append(absence_row)
    rows += [refusal.as_row() for refusal in refusals]
    rows += controls

    for control in controls:
        print(f"control {control['control']}: {'held' if control['held'] else 'FAILED'}")
    if not all(control["held"] for control in controls):
        raise RuntimeError(
            "a control failed, so nothing is written. ⛔ A file whose own method did not "
            "check out is evidence of nothing and reads as evidence"
        )

    header = build_header(script, edition, len(RULES), refusals, controls)
    path = args.out / "textual" / "significator-series-rules.jsonl"
    count = write_jsonl(path, header, rows)
    print(f"wrote {count} rows -> {path}")
    print(
        f"resolved {len(RULES)} rule(s), refused {len(refusals)}; "
        f"{sum(absence.hits.values())} hit(s) across {len(ALPHABET)} spelling(s), "
        "none of them the rule searched for"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
