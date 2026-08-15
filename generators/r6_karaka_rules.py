"""What two located copies state about the significator series — and what neither does.

⛔ **The claim this file exists to make is not "a book says so".** It is that each recorded
rule was *resolved*: the words quoted at each locus were searched for in a named copy, whose
address, digest, rendering and measured extent are all on the header, and were found there
exactly once. A citation nobody can resolve is not a citation, and prose asserting that a
citation is good is a claim like any other, made in the one form that cannot be checked.

⭐ **Two of the rules here sit in the translator's notes rather than in the sutras**, and
the fixture says which is which on every row. They are printed on the same pages and are not
the same authority: one is the text, the other is a modern reader of it. A consumer that
took the notes for the text would be implementing a commentator under a sutra's name.

⭐⭐ **There is a second witness now, and it did not simply agree.** A second copy — another
translator, another language, and one that carries the sutras in their own script — answers
all five rules: four corroborated, and one **forked**. ⛔ The fork is not about what the rule
says. Both copies contain the rule that the ascending node's degrees are read backwards; they
attach it to *different sutras governing different determinations*, and the one that matters
is whether it applies when the series itself is ranked. ⭐ *A disagreement about a rule's
scope moves more charts than a disagreement about its content*, and neither copy is corrected
against the other here: which is right is not a recorder's question.

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
from saakshi.texts import (  # noqa: E402
    CACHE,
    DEVANAGARI,
    acquire,
    load,
    passage_fidelity,
    script_presence,
)
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

#: ⭐ The second witness. A rule resolved against one edition is *resolved*, not
#: *corroborated*, and every rule here rested on one copy, one translation, one translator
#: until this copy was acquired.
#:
#: ⚠ **It is not the same kind of copy, and the difference is load-bearing.** The first is an
#: English translation whose rendering carries no Sanskrit at all. This one carries the
#: sutras in their own script and a Hindi commentary on them — so where they agree, two
#: translators working in two languages agree, which is a stronger statement than two
#: printings of one translator; and where they disagree, the disagreement is locatable in
#: both rather than being one copy's silence.
SECOND_EDITION = "jaimini_sutram_mishra"

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
# The second witness
# --------------------------------------------------------------------------------------

#: What the second copy states about each rule above, quoted from ITS pages at ITS locus.
#:
#: ⛔ **A second witness is not the same fragment searched in another file.** The words are
#: the edition's own property: a different translator, in a different language, does not
#: print the first one's sentence. So each entry carries its own locus and its own fragment,
#: and what is compared is what each copy *states* — never the two quotations, which could
#: not match and would mean nothing if they did.
#:
#: ⚠ **Every fragment below is the second copy's COMMENTARY, not its sutra line.** That copy
#: prints the sutras in their own script and its machine reading damaged them; see the
#: fidelity control. So the second witness is a second *commentator* reading the same sutras,
#: which is what it can honestly be and is stated as such on every row.
CORROBORATION: tuple[dict[str, Any], ...] = (
    {
        "rule": "the_first_significator_is_the_highest_in_degrees",
        "verdict": "corroborated",
        "locus": "adhyaya 1, pada 1, the commentary to sutra 11",
        "fragment": (
            "सूर्य से लेकर शनि पर्यन्त सातों में से अथवा राहु को मिलाकर आठौं ग्रहों में से "
            "जिसके अंश सबसे अधिक होंगे, वही आत्मकारक होगा"
        ),
        "the_second_source_states": (
            "of the seven from the Sun as far as Saturn, or of the eight bodies counting the "
            "ascending node, the one holding the greatest degrees is the head of the series"
        ),
        "note": (
            "⭐ the two copies state this one almost sentence for sentence, in two languages "
            "and from two translators. ⚠ Including the part a consumer is most likely to "
            "narrow: both offer the seven-body and eight-body reckonings and neither chooses"
        ),
    },
    {
        "rule": "the_second_significator_is_next_in_degrees",
        "verdict": "corroborated",
        "locus": "adhyaya 1, pada 1, the commentary to sutras 13 to 17",
        "fragment": "आत्मकारक से कम अंशादि वाला ग्रह अमात्यकारक होता है",
        "the_second_source_states": (
            "the body holding fewer degrees than the head of the series takes the second place"
        ),
    },
    {
        "rule": "the_third_significator_is_next_again",
        "verdict": "corroborated",
        "locus": "adhyaya 1, pada 1, the commentary to sutras 13 to 17",
        "fragment": "तब *उससे कम अंशादि वाला भ्रातृकारक",
        "the_second_source_states": (
            "the body holding fewer degrees again takes the third place"
        ),
        "note": (
            "⚠ quoted with the machine reading's stray asterisk intact. ⛔ Removing it would "
            "make the locus resolve against a document that exists only here"
        ),
    },
    {
        "rule": "a_tie_merges_two_places_and_the_node_fills_the_vacancy",
        "verdict": "corroborated",
        "locus": "adhyaya 1, pada 1, the commentary to sutra 11",
        "fragment": (
            "यदि दो या अधिक ग्रहों के अंश समान हों तो वे दोनों ही ग्रह आत्मकारक माने जाएँगे"
        ),
        "second_fragment": "उस स्थिति में राहु उस रिक्तता को पूरा करेगा",
        "the_second_source_states": (
            "where two or more bodies hold equal degrees both are taken as the head of the "
            "series, which leaves the series one body short, and the ascending node fills the "
            "place left empty"
        ),
        "note": (
            "⭐⭐ THE RESULT THAT WAS NOT EXPECTED. This rule is the first copy's "
            "TRANSLATOR'S NOTE rather than its sutra, and a note is one modern reader's "
            "voice — so a second edition was expected to be unable to speak to it at all. It "
            "speaks to both halves. ⚠ What that establishes is precise and is not that the "
            "note is right: it is that the rule is attested by two commentators independently "
            "rather than being one translator's gloss, which is a different and weaker claim "
            "than a sutra stating it, and a stronger one than a single note"
        ),
    },
    {
        "rule": "the_node_is_ranked_by_reversed_degrees",
        "verdict": "forked",
        "locus": "adhyaya 2, pada 1, sutra 53 and its commentary",
        "fragment": (
            "राहु के भुक्तांश जानने के लिए राहु स्पष्ट के अंशों को ३०० में से घटाकर शेष का "
            "ग्रहण करना चाहिए"
        ),
        "second_fragment": "केतु का ग्रहण इसलिए नहीं किया जाता",
        "the_second_source_states": (
            "that the node's degrees are read by subtracting its longitude from thirty — the "
            "same mechanism the first copy's note states, and stated here as arithmetic "
            "rather than as a description — but states it at a sutra governing a DIFFERENT "
            "determination, and at the sutra founding the series it instead gives a different "
            "reason for leaving the descending node out, that its degrees always equal the "
            "ascending node's"
        ),
        "note": (
            "⛔⛔ THE FORK IS ABOUT SCOPE, NOT ABOUT CONTENT, AND SCOPE IS THE CONSEQUENTIAL "
            "HALF. Both copies contain the reversal. The first attaches it to the series "
            "itself; the second attaches it to a later, narrower determination and does not "
            "invoke it where the series is founded. ⭐ A consumer that reverses the node's "
            "degrees when ranking the series is following the first copy's note, and the "
            "second copy does not authorise it there — and because the node's rank changes "
            "with the reading, so does the series, for any chart in which the node would place"
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


def corroboration_rows(second) -> list[dict[str, Any]]:
    """What the second copy states about each rule, at its own locus, in its own words.

    ⛔ Every fragment is resolved in the second copy exactly as the first copy's are in it —
    the `Locus` refuses at write time if a fragment does not occur exactly once, so a row
    that reaches the file has been located rather than asserted.
    """
    rows: list[dict[str, Any]] = []
    for entry in CORROBORATION:
        locus = Locus(
            # ⚠ the second copy speaks here through its commentator, never through its sutra
            #   lines — see the fidelity control for why that is forced rather than chosen
            source_kind="commentary",
            edition=second,
            locus=entry["locus"],
            interpretation_status="restated",
            fragment=entry["fragment"],
        )
        row: dict[str, Any] = {
            "finding": "corroboration",
            "rule": entry["rule"],
            "verdict": entry["verdict"],
            "the_second_source_states": entry["the_second_source_states"],
            "locus": locus.as_json(),
        }
        if entry.get("second_fragment"):
            # ⛔ A second passage carrying the other half of the claim. It is resolved on its
            #    own rather than concatenated: two passages that are pages apart do not form
            #    one quotation, and joining them would produce a fragment found nowhere.
            row["second_locus"] = Locus(
                source_kind="commentary",
                edition=second,
                locus=entry["locus"],
                interpretation_status="restated",
                fragment=entry["second_fragment"],
            ).as_json()
        if entry.get("note"):
            row["note"] = entry["note"]
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
        # ⭐ The "a second witness to any rule recorded above" refusal that stood here through
        #   four hand-offs is DISCHARGED: a second copy is in hand and every rule is answered
        #   by it, four corroborated and one forked. ⛔ It is replaced rather than deleted,
        #   because what the second copy could NOT be asked is a narrower refusal and not no
        #   refusal at all.
        Refusal(
            subject=(
                "a witness to the first copy's TRANSLATOR'S NOTES as that translator's own "
                "words"
            ),
            reason="no_edition_in_hand",
            detail=(
                "two of the rules here are printed in the first copy's notes rather than in "
                "its sutras. ⭐ The second copy speaks to both, and that is worth having — but "
                "it speaks as another commentator on the same sutras, which establishes that "
                "a rule is attested twice and never that the first translator's note says "
                "what this file records it saying. ⛔ Only another copy of THAT translation "
                "can witness that, and the copy in hand is the only one held"
            ),
            what_would_close_it=(
                "a second printing of the first translation, acquired and resolved against "
                "the same loci"
            ),
        ),
        Refusal(
            subject="any sutra of this work as the second copy prints it",
            reason="script_present_but_passage_not_faithful",
            detail=(
                "⚠ this refusal exists because the obvious check passes. The second copy "
                "carries the original's script in quantity, so a presence test answers yes — "
                "and its machine reading still damaged the sutra lines while capturing the "
                "commentary around them cleanly. Measured on the sutra the series is founded "
                "on: the copy's own commentary names a word as occurring in that sutra, and "
                "the sutra as rendered does not contain it. ⛔ Quoting the line would publish "
                "the machine reading's damage under the text's own name"
            ),
            what_would_close_it=(
                "a rendering of that copy whose sutra lines are faithful, or a copy of the "
                "original in a rendering that can be checked against itself the same way"
            ),
        ),
        Refusal(
            subject="an absence measured over the second copy",
            reason="extent_of_the_copy_is_a_lower_bound",
            detail=(
                "the absence recorded in this file is measured over the first copy only. ⛔ It "
                "is not extended to the second, and the reason is not effort: three detectors "
                "were run over that copy's boundary markers and each measured a different "
                "extent, because the machine reading damaged the same closing sentence "
                "differently at every occurrence. Its extent is therefore a lower bound, and "
                "an absence taken over a lower bound reports the recorder's alphabet as the "
                "book's silence. ⚠ A second alphabet would also be needed, in a second script"
            ),
            what_would_close_it=(
                "an extent for that copy established by something other than a search for "
                "spellings a reader had to think of first"
            ),
        ),
    ]


def build_header(script: Path, edition, second, resolved: int, refusals, controls) -> Header:
    return Header(
        fixture_kind="textual_rule",
        reference="R6",
        generator=generator_for(script),
        generated=today(),
        title=(
            "The significator series as two located copies state it, one rule they place "
            "differently, and one widely repeated rule neither states"
        ),
        oracle=source_oracle([edition, second], resolved=resolved, refused=len(refusals)),
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
            "rules_answered_by_the_second_copy": len(CORROBORATION),
            "of_which_corroborated": sum(
                1 for c in CORROBORATION if c["verdict"] == "corroborated"
            ),
            "of_which_forked": sum(1 for c in CORROBORATION if c["verdict"] == "forked"),
            "what_the_second_copy_settles_and_what_it_does_not": (
                "⭐ where the two agree, two translators working in two languages agree, which "
                "no second printing of one translation could establish. ⛔ Where they differ "
                "the difference is recorded as a fork rather than resolved: which copy is "
                "right is not a question a recorder may settle, and both are located"
            ),
            "the_absence": (
                "one rule was searched for and not found. ⛔ It is an absence from the extent "
                "measured, in the spellings listed, in ONE rendering - the first copy's. It "
                "is deliberately not extended to the second, whose extent is a lower bound; "
                "see the absence row and the matching refusal"
            ),
            "controls": {control["control"]: control["held"] for control in controls},
        },
        row_schema={
            "rule": "one located statement, with the locus it was resolved at",
            "corroboration": (
                "what the second copy states about one rule above, at its own locus and in "
                "its own words, with a verdict of corroborated or forked"
            ),
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
            "⭐⭐ THERE ARE TWO WITNESSES NOW, AND THE SECOND ONE FORKED RATHER THAN AGREED "
            "ON THE RULE THAT MATTERS MOST. Four of the five rules are corroborated by a "
            "second copy in a second language by a second translator. The fifth - how the "
            "eighth body's degrees are read - is contained in both copies and PLACED "
            "DIFFERENTLY by them: the first attaches it to the series itself, the second to a "
            "later and narrower determination. ⛔ The fork is not resolved here. Which copy is "
            "right is not a recorder's question, and a consumer ranking the series by reversed "
            "degrees is following one copy against the other rather than following the source.",
            "⚠ THE SECOND COPY SPEAKS THROUGH ITS COMMENTATOR AND NOT THROUGH ITS SUTRAS, AND "
            "THAT WAS FORCED. It carries the original's script in quantity - so the presence "
            "check that stands for 'no primary text is reachable' answers yes for it - and its "
            "machine reading still damaged the sutra lines while capturing the commentary "
            "cleanly. ⭐ Presence of a script is not fidelity of a script, and the two are "
            "measured separately because the first would otherwise be read as the second.",
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
        for key in (EDITION, SECOND_EDITION):
            record = acquire(key, cache=args.cache, today=today())
            print(f"acquired {key}: {record['copy_bytes']} bytes, status {record['http_status']}")

    edition = load(EDITION, cache=args.cache)
    second = load(SECOND_EDITION, cache=args.cache)
    print(
        f"edition {EDITION}: {edition.rendering.kind} via {edition.rendering.produced_by}, "
        f"{edition.rendering.characters} characters"
    )
    print(
        "extent: "
        f"{len(edition.extent['divisions_found'])} of "
        f"{len(edition.extent['divisions_looked_for'])} divisions found"
    )

    print(
        f"edition {SECOND_EDITION}: {second.rendering.kind}, "
        f"{second.rendering.characters} characters; extent "
        f"{len(second.extent['divisions_found'])} of "
        f"{len(second.extent['divisions_looked_for'])} divisions found"
    )

    script_check = script_presence(edition, first=DEVANAGARI[0], last=DEVANAGARI[1])
    second_script = script_presence(second, first=DEVANAGARI[0], last=DEVANAGARI[1])
    # ⚠ The passage is the sutra the whole series hangs on, and the word is one the copy's
    #   OWN commentary states is in it. ⛔ Nothing here supplies a "correct" wording from
    #   outside: that would be the unsourced claim this discipline exists to refuse.
    second_fidelity = passage_fidelity(
        second,
        passage="आत्साधिकः कला दिभिनभोग: सप्तानासष्टानां वा",
        quoted_word="अष्टानाम्",
        stated_at="adhyaya 1, pada 1, the commentary to sutra 11",
    )
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
        # ⭐⭐ The second copy inverts the control above, and that is why the pair is kept.
        #    It DOES carry the script, so a presence test answers yes for it - and the same
        #    machine reading damaged the sutra lines. ⛔ Had this file owned only the presence
        #    control, the yes would have been read as licence to cite the original.
        {
            "finding": "control",
            "control": "the_second_copy_carries_the_script_and_is_still_not_citable_for_it",
            "measured": {
                "presence": second_script,
                "fidelity": second_fidelity,
            },
            "held": bool(second_script["present"] and not second_fidelity["faithful"]),
            "meaning": (
                "⭐ PRESENCE IS NOT FIDELITY, MEASURED RATHER THAN ARGUED. The second copy "
                "carries the original's script in quantity and its rendering of the sutra "
                "this series is founded on still cannot be cited: the copy's own commentary "
                "names a word as occurring in that sutra and the rendered sutra lacks it. ⛔ "
                "This control holds when BOTH are true, so it fails if the script ever goes "
                "missing and equally if the passage ever becomes faithful - either would mean "
                "the refusal built on it has stopped describing the copy"
            ),
        },
    ]

    refusals = refusals_for(edition)
    rows = rule_rows(edition, refusals)
    rows += corroboration_rows(second)

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

    header = build_header(script, edition, second, len(RULES), refusals, controls)
    path = args.out / "textual" / "significator-series-rules.jsonl"
    count = write_jsonl(path, header, rows)
    print(f"wrote {count} rows -> {path}")
    print(
        f"resolved {len(RULES)} rule(s), refused {len(refusals)}; "
        f"{sum(absence.hits.values())} hit(s) across {len(ALPHABET)} spelling(s), "
        "none of them the rule searched for"
    )
    corroborated = sum(1 for c in CORROBORATION if c["verdict"] == "corroborated")
    forked = sum(1 for c in CORROBORATION if c["verdict"] == "forked")
    print(
        f"second witness: {corroborated} corroborated, {forked} forked, "
        f"across {len(CORROBORATION)} rule(s)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
