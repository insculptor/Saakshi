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

⭐⭐ **There is a second witness, and it answers all five rules — every one corroborated.**
Another translator, another language, and a copy that carries the sutras in their own script.

⛔⛔⛔ **The fifth rule was published from this file as a FORK, and the fork was not there.**
The withdrawn reading held that the second copy invoked the ascending node's reversed degrees
only at a later, narrower determination and not where the series is founded. That copy's
commentary to the founding sutra states the rule in full, two paragraphs below the passage
the reading was formed from. ⭐⭐⭐ *A different reason found is not the absence of the reason
you were looking for* — the recorder read "it says X here" as "it does not say Y here", over
a passage nobody searched. The correction is a row, not a silent edit, and a fork is now
refused at write time unless its absence half has been measured over a bounded passage.

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
    Alignment,
    Locus,
    PassageAbsence,
    Refusal,
    SecondHand,
    collect_occurrences,
    refusal_summary,
    source_oracle,
)

EDITION = "jaimini_sutras_rao"

#: ⭐ The copy the standing refusal asked for — a second printing of the FIRST translation —
#: acquired this session and refused for a reason nobody predicted. ⛔ 219 pages of scanned
#: page images: the right work, retrievable, digested, and carrying no searchable text at all.
SCANNED_PRINTING = "jaimini_sutras_rao_scanned_printing"

# --------------------------------------------------------------------------------------
# The second commenting hand in the first copy
# --------------------------------------------------------------------------------------

#: ⛔⛔⛔ THE FIRST COPY CARRIES TWO COMMENTATORS AND THIS FILE HAD COUNTED ONE. Every passage
#: below is the copy speaking of the translator in the THIRD PERSON — a hand that writes
#: "Prof. Rao's NOTES" is not Prof. Rao. ⭐ Located, each occurring exactly once.
THIRD_PERSON_OF_THE_TRANSLATOR: tuple[str, ...] = (
    (
        "Though Suryanarain Rao has elucidated the abbreviations used by Jaimini to imply "
        "numerals I propose to make some observations for the benefit of the reader"
    ),
    (
        "* I have not meddled 'with the ' English rendering of this sutra by Prof. B. "
        "Suryanarain Rao."
    ),
    "This is a rather tough stanza and Professor Rao's notes are not clear.",
)

#: ⚠ The second hand claiming books of its own. ⛔ Evidence that it is an AUTHOR; and not
#: evidence of WHICH author — naming it would mean supplying an authorship from memory.
SECOND_HAND_CLAIMS: tuple[str, ...] = (
    "* I have discussed Rasi Dasa at considerable length in my book Studies in Jaimini Astrology.",
    "* This has been clearly described in my work Manual of Hindu Astrology.",
)

#: ⭐ Every spelling read off THIS copy, from the passages above and the marker they carry.
#: ⛔ Not guessed: the asterisk is the printed marker, and the rest are the second hand's own
#: turns of phrase, each attested in the copy.
SECOND_HAND_ALPHABET: tuple[str, ...] = (
    "*",
    "Prof.",
    "Professor",
    "my book",
    "my work",
    "my Studies",
    "Studies in Jaimini Astrology",
    "Manual of Hindu Astrology",
    "I propose",
    "I have not meddled",
    "I understand it thus",
    "come to our rescue",
)

#: The landmarks bounding the notes to the founding sutra — the passage both recorded
#: translator's-note rules stand in. ⛔ Each resolves exactly once; checked, not assumed.
NOTES_TO_SUTRA_11_OPEN = "SU. 11 .-Atmadhikaha kaladibhirna bhogassaptanamashtamva."
NOTES_TO_SUTRA_11_CLOSE = "SU. 12 ."

# --------------------------------------------------------------------------------------
# The passage the withdrawn fork rested on
# --------------------------------------------------------------------------------------

#: ⛔ The two landmarks bounding the second copy's commentary to the founding sutra, each of
#: which resolves exactly once. ⚠ The opening one is the sutra line itself, quoted in the
#: damaged spelling the machine reading produced — which is why it may bound a region and may
#: not be cited as the sutra: see the fidelity refusal.
FOUNDING_PASSAGE_OPENS = "आत्साधिकः कला दिभिनभोग: सप्तानासष्टानां वा ॥११॥"
FOUNDING_PASSAGE_CLOSES = "ईष्टे बन्धमोक्षयोः ॥१२॥"

#: ⭐⭐ Every spelling read off THIS copy, and specifically off its OTHER statement of the
#: same rule. ⛔ Not off the concept: the concept's ordinary word (`विपरीत`) occurs **zero**
#: times in the passage under search, while the rule is stated there in full — because this
#: copy gives the rule as arithmetic in one place and as description in another. An alphabet
#: assembled from the idea rather than from the other copy's wording confirms the very
#: absence it was built to test.
REVERSAL_ALPHABET: tuple[str, ...] = (
    "विपरीत",      # the copy's word at sutra 53's commentary, describing the rule
    "भुक्तांश",     # the copy's term for the degrees the rule reads, same commentary
    "घटाकर",       # the copy's word for the subtraction that performs it, same commentary
    "व्युत्क्रम",    # the copy's word for reversed order, used of counting elsewhere
    "उल्टा",
    "उल्टी",
    "वक्र",
)

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
        # ⛔⛔⛔ THIS ROW READ `forked` WHEN IT WAS PUBLISHED, AND THE FORK WAS NOT THERE.
        #    See the `correction` row and the control built on the passage that refutes it.
        "verdict": "corroborated",
        "locus": "adhyaya 1, pada 1, the commentary to sutra 11 - the sutra founding the series",
        "fragment": (
            "यदि राहु सर्वाधिक भुक्तांश वाला हो (एतदर्थ राहु के स्पष्टांशों को ३० ' में से "
            "घटाकर शेष को लें) तो वह भी आत्मकारक हो सकता है"
        ),
        "second_locus": "adhyaya 2, pada 1, sutra 53 and its commentary",
        "second_fragment": (
            "राहु के भुक्तांश जानने के लिए राहु स्पष्ट के अंशों को ३०० में से घटाकर शेष का "
            "ग्रहण करना चाहिए"
        ),
        "the_second_source_states": (
            "that the node's degrees are read by subtracting its longitude from thirty, and "
            "states it in BOTH places the question arises: in the commentary to the sutra "
            "FOUNDING the series, where it says the node must be considered in determining "
            "the head of the series and gives the subtraction in parentheses; and again at "
            "the later sutra governing the narrower determination. ⭐ The same mechanism the "
            "first copy's note states, given here as arithmetic rather than as description"
        ),
        "note": (
            "⛔⛔⛔ THIS ROW WAS PUBLISHED AS A FORK AND THE FORK WAS NOT THERE. The withdrawn "
            "reading held that the second copy did not invoke the reversal where the series "
            "is founded, on the strength of that copy giving a DIFFERENT reason at the "
            "founding sutra for leaving the descending node out — which it does, and which is "
            "still located below. ⭐⭐⭐ But *a different reason found is not the absence of "
            "the reason you were looking for*: the reversal stands two paragraphs further "
            "down the same commentary, applied by name to the head of the series. ⚠ The "
            "passage was never searched, and nothing required it to be"
        ),
    },
)

#: ⭐ The reading that was published and is now withdrawn. ⛔ It is written down rather than
#: quietly replaced: this file has been handed over, and an artifact that changes a verdict
#: without saying so asks a reader to trust that nothing else moved.
WITHDRAWN = {
    "finding": "correction",
    "rule": "the_node_is_ranked_by_reversed_degrees",
    "what_was_published": (
        "that the two copies FORK on this rule: that both contain the reversal of the "
        "ascending node's degrees, that the first attaches it to the sutra founding the "
        "series while the second attaches it only to a later and narrower determination, and "
        "that a consumer reversing the node when ranking the series therefore follows one "
        "copy against the other"
    ),
    "what_refutes_it": (
        "the second copy's own commentary to the founding sutra, which states that the node "
        "must be considered in determining the head of the series and gives the subtraction "
        "that reverses its degrees, in parentheses, two paragraphs below the passage the "
        "withdrawn reading was formed from. ⭐ Located, and occurring exactly once"
    ),
    "what_is_published_now": (
        "that the rule is CORROBORATED, at the founding sutra and at the later determination "
        "alike, by both copies"
    ),
    "how_the_error_was_made": (
        "⛔⛔ AN ABSENCE WAS ASSERTED OVER A PASSAGE NOBODY SEARCHED. The recorder read the "
        "founding sutra's commentary far enough to find the second copy giving a different "
        "ground for excluding the descending node, and read *it says X here* as *it does not "
        "say Y here*. ⭐ The five located fragments in that session each resolved exactly "
        "once and five deliberate mutations of them were each refused — and none of that "
        "touched the claim built on top of them. *A refusal control proves the fragments you "
        "wrote are located; it says nothing about the finding you assembled out of them*"
    ),
    "what_would_have_caught_it": (
        "⚠ and this is the uncomfortable half: an absence search over that passage in the "
        "OBVIOUS alphabet would have confirmed the fork. The ordinary word for the reversal "
        "is absent from the founding commentary — measured, zero occurrences — because the "
        "copy states the rule there as ARITHMETIC and elsewhere as DESCRIPTION. ⭐⭐⭐ The "
        "alphabet that catches it is the one read off the SAME RULE AS THE OTHER COPY STATES "
        "IT, carrying form by carrying form. *A walker that knows one carrying form has "
        "measured the wrong subject* — the same sentence as the extent defect before it, one "
        "level up"
    ),
    "what_is_armed_now": (
        "a fork is refused at write time unless its absence half is established over a "
        "passage bounded by two landmarks that each resolve exactly once, in an alphabet "
        "every spelling of which is attested somewhere in that copy. ⛔ Run against the "
        "withdrawn fork, it refuses it and names the two words that refute it"
    ),
}

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
            # ⚠ It carries its OWN locus label where the two passages are at different loci.
            #   Labelling a passage with a neighbour's locus is how a reading gets attributed
            #   to a sutra it does not stand under, which is the defect this file corrects.
            row["second_locus"] = Locus(
                source_kind="commentary",
                edition=second,
                locus=entry.get("second_locus", entry["locus"]),
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
        # ⭐⭐ The "second printing of the first translation" refusal has now been PUT TWICE
        #   and narrowed twice. It is not closed, and the reason it is not closed changed:
        #   the obstacle used to be that no such copy was held, and it is now that the copy
        #   held is one a second hand revised.
        Refusal(
            subject=(
                "a witness to the first copy's TRANSLATOR'S NOTES as that translator's own "
                "words"
            ),
            reason="revised_printing_cannot_witness_the_unrevised_words",
            detail=(
                "⭐ the question was RE-PUT this session, because the candidate that would "
                "close it had been rejected against a question since replaced — and re-putting "
                "it moved the obstacle rather than removing it. Measured in the first copy "
                "itself: it carries a SECOND commenting hand, which names the translator in "
                "the third person, comments on his notes and claims books of its own. ⛔ So "
                "the printing this file resolves into is one a later hand worked over, and "
                "two printings that hand revised would agree with each other about the "
                "revision. ⚠ Sharper still, and read off the copy: that hand writes *I have "
                "not meddled with the English rendering of THIS sutra* — a disclaimer scoped "
                "to one sutra is worth making only by a hand that meddles elsewhere. ⭐ A "
                "reviser who rewrites silently leaves no marker at all, so the absence of his "
                "marks from a passage does not return the passage to the translator"
            ),
            what_would_close_it=(
                "⭐ a printing of this translation that does NOT carry the second hand — and "
                "that is now a TEST rather than a hope: acquire a candidate, search it for "
                "the twelve spellings by which this copy marks that hand, and require zero "
                "over the whole copy. ⛔⛔ The test is worthless without a positive control on "
                "the same copy, because a copy that renders to nothing passes it perfectly — "
                "measured, on the 219-page printing acquired this session"
            ),
        ),
        # ⭐⭐⭐ THE CANDIDATE WAS ACQUIRED. This refusal is the reason it settled nothing, and
        #    it is a reason no survey could have produced: it had to be fetched and rendered.
        Refusal(
            subject=(
                "any locus at all in the second printing of the first translation acquired "
                "this session"
            ),
            reason="rendering_carries_no_searchable_text",
            detail=(
                "⭐ the copy is held: retrieved, digested, 13 905 548 bytes, 219 pages. Every "
                "page is an image and the file carries no text layer, so the rendering "
                "resolves nothing and attests nothing — ⛔ including its own identity. The "
                "work, the translator and the printing are known here only from the name the "
                "host gives the file, which is a fact about a host and not about a book, and "
                "is the same ground an earlier candidate was rejected on for naming no "
                "translator. ⚠⚠ And the number that would have caught it does not: the "
                "extractor returned one empty string per page and joined them with newlines, "
                "so the rendering reports **218** characters — the page count minus one — "
                "while the searchable text is empty. A guard written `characters == 0` passes "
                "it"
            ),
            what_would_close_it=(
                "a rendering of this printing that carries text — a machine reading produced "
                "and published by its distributor, as the other two copies here were. ⛔ Not "
                "one produced by this instrument: the errors would then be ours, and an "
                "absence measured over our own machine reading would be measured over our own "
                "mistakes"
            ),
        ),
        # ⚠ Named because it is the prerequisite nobody had stated, and it is unmet.
        Refusal(
            subject=(
                "that the copy this file resolves into is a DIFFERENT printing from any "
                "other copy of this translation"
            ),
            reason="no_edition_in_hand",
            detail=(
                "⛔⛔ THE HELD COPY DOES NOT SAY WHICH PRINTING IT IS. Measured over its "
                "rendering: *edition*, *Preface*, *Copyright*, *Publisher*, *Published* and "
                "*Printed* occur ZERO times, and it carries no title page and no imprint. ⚠ Its "
                "ONLY date-like number is a Samvat era count standing inside the translator's "
                "own preliminary observations - *counts now as 1988* - which dates the writing "
                "rather than the printing, and stands in an era this copy does not convert. ⭐ "
                "So *a SECOND printing* is a claim that cannot be made from this side of the "
                "comparison, however good the other copy is: two copies could be one printing "
                "digitised twice, and every rule would come back corroborated across printings "
                "for what was one printing read twice. ⚠ The same shape as two addresses "
                "serving one scan"
            ),
            what_would_close_it=(
                "an imprint, a title page or a preface legible in a rendering of this copy, "
                "naming the printing it is"
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


def build_header(script: Path, edition, second, scanned, resolved: int, refusals, controls) -> Header:
    return Header(
        fixture_kind="textual_rule",
        reference="R6",
        generator=generator_for(script),
        generated=today(),
        title=(
            "The significator series as two located copies state it, a fork this file "
            "published and has withdrawn, and one widely repeated rule neither states"
        ),
        # ⚠ THREE copies now, and the third resolves nothing. It is listed because a reader
        #   checking this file must be able to see the copy that was acquired and refused —
        #   a candidate rejected in prose is a claim, and a candidate carrying a witness, a
        #   rendering and a measured extent of nothing is a measurement.
        oracle=source_oracle(
            [edition, second, scanned], resolved=resolved, refused=len(refusals)
        ),
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
            "a_verdict_published_here_has_been_withdrawn": (
                "⛔⛔⛔ ONE. The fifth rule was published as a FORK and is now CORROBORATED. "
                "The withdrawn reading held that the second copy did not invoke the node's "
                "reversed degrees where the series is founded; that copy's commentary to the "
                "founding sutra states the rule in full, two paragraphs below the passage the "
                "reading was formed from. ⭐ The correction row carries what was published, "
                "what refutes it, how the error was made and what is armed against it"
            ),
            "what_the_second_copy_settles_and_what_it_does_not": (
                "⭐ where the two agree, two translators working in two languages agree, which "
                "no second printing of one translation could establish. ⛔ Where they differ "
                "the difference is recorded as a fork rather than resolved: which copy is "
                "right is not a question a recorder may settle, and both are located. ⚠ And a "
                "fork is now REFUSED AT WRITE TIME unless its absence half is measured over a "
                "bounded passage - because the one fork this file published had no such "
                "measurement behind it and was wrong"
            ),
            "how_many_commenting_hands_the_first_copy_carries": (
                "⛔⛔⛔ TWO, AND THIS FILE HAD COUNTED ONE. Beside the translator whose notes "
                "two rules here are filed under, the copy carries a second hand that names "
                "him in the third person, says his notes are not clear, and claims books of "
                "its own. ⭐ It cannot be NAMED from this copy - no title page, no imprint, no "
                "preface - and naming it from the books it claims would supply an authorship "
                "from the recorder's memory. ⚠ *There is a second hand here and this copy does "
                "not say whose* is the finding, not a shortfall"
            ),
            "the_second_printing_question_was_re_put_and_did_not_close": (
                "⭐ the candidate that would close it had been rejected against a question "
                "since replaced, so the question was put again - and the obstacle MOVED "
                "rather than lifting. It used to be that no second printing was held. It is "
                "now that the printing this file resolves into is one a second hand revised, "
                "and two printings that hand revised would agree about the revision. ⛔ A "
                "printing was in fact acquired this session and settles nothing: 219 pages of "
                "images, no searchable text"
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
            "correction": (
                "a reading this file PUBLISHED and has withdrawn, with what refutes it, how "
                "the error was made and what is armed against its recurrence"
            ),
            "alignment": (
                "whether two copies' sutra numbers for one rule can be shown to name the same "
                "place in the work, measured against a neighbouring sutra both copies print"
            ),
            "hands_in_the_copy": (
                "that one copy carries a commenting hand OTHER than the one its notes are "
                "credited to, established from the copy speaking of that translator in the "
                "third person, with every such passage located"
            ),
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
            "⛔⛔⛔ THIS FILE PUBLISHED A FORK ON THE RULE THAT MATTERS MOST, AND THE FORK "
            "WAS NOT THERE. All five rules are corroborated by a second copy in a second "
            "language by a second translator - including the fifth, how the eighth body's "
            "degrees are read, which was published as placed differently by the two copies. "
            "The second copy states it where the series is founded AND at the later "
            "determination, as the first does. ⭐⭐⭐ The withdrawn reading was an ABSENCE "
            "NOBODY MEASURED: the recorder found the second copy giving a different ground "
            "for excluding the descending node at the founding sutra, and read 'it says X "
            "here' as 'it does not say Y here'. *A different reason found is not the absence "
            "of the reason you were looking for.* See the correction row.",
            "⚠ AND THE OBVIOUS CHECK WOULD HAVE CONFIRMED THE ERROR. The ordinary word for "
            "the reversal occurs ZERO times in the passage that states the rule, because that "
            "copy gives it there as arithmetic and elsewhere as description. ⭐ The alphabet "
            "that catches it is the one read off the same rule AS THE OTHER COPY STATES IT, "
            "carrying form by carrying form - the same lesson as the boundary-marker defect "
            "before it, one level up.",
            "⚠ THE SECOND COPY SPEAKS THROUGH ITS COMMENTATOR AND NOT THROUGH ITS SUTRAS, AND "
            "THAT WAS FORCED. It carries the original's script in quantity - so the presence "
            "check that stands for 'no primary text is reachable' answers yes for it - and its "
            "machine reading still damaged the sutra lines while capturing the commentary "
            "cleanly. ⭐ Presence of a script is not fidelity of a script, and the two are "
            "measured separately because the first would otherwise be read as the second.",
            "⛔⛔⛔ THE COPY THESE RULES ARE RESOLVED INTO CARRIES TWO COMMENTING HANDS, AND "
            "THIS FILE HAD COUNTED ONE. It has always said that the translator's notes are "
            "not the sutras, on the ground that a consumer taking one for the other would "
            "implement a modern commentator under a sutra's name. ⭐ A revised translation has "
            "THREE authorities, and the third is the one nobody counts: this copy carries a "
            "hand that writes 'Prof. Rao's NOTES', says 'Professor Rao's notes are not "
            "clear', and claims books of its own. Its material is marked with an asterisk and "
            "none of its twelve marks falls in the passage carrying the two note-rules - ⛔ "
            "which establishes that the passage carries none of its MARKS, and not that it "
            "carries the translator's words: a reviser who rewrites silently leaves no marker.",
            "⭐⭐⭐ AN ABSENCE OVER A COPY THAT WAS NEVER READ IS THE STRONGEST-LOOKING "
            "ABSENCE AND THE EMPTIEST, AND THIS FILE NOW HOLDS SUCH A COPY. The second "
            "printing the standing refusal asked for was acquired: the right work, retrieved "
            "and digested, 219 pages - every one an image. Every spelling returns zero over "
            "it in any alphabet. ⚠ And the count that should catch it does not: the extractor "
            "joined 219 empty pages with newlines, so the rendering reports 218 characters "
            "while nothing is searchable, and a guard written `characters == 0` passes it. ⇒ "
            "Both absence instruments now require a POSITIVE CONTROL - words the copy is "
            "shown to contain - before any zero is written down.",
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
        for key in (EDITION, SECOND_EDITION, SCANNED_PRINTING):
            record = acquire(key, cache=args.cache, today=today())
            print(f"acquired {key}: {record['copy_bytes']} bytes, status {record['http_status']}")

    edition = load(EDITION, cache=args.cache)
    second = load(SECOND_EDITION, cache=args.cache)
    # ⭐ The copy the standing refusal asked for. ⛔ It is loaded so that what it establishes
    #   is MEASURED rather than described: 219 pages, a rendering reporting 218 characters,
    #   and not one character a locus could resolve against.
    scanned = load(SCANNED_PRINTING, cache=args.cache)
    print(
        f"edition {SCANNED_PRINTING}: {scanned.rendering.kind}, rendering reports "
        f"{scanned.rendering.characters} characters; searchable "
        f"{scanned.searchable_characters}"
    )
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

    # ⭐ The measurement that withdrew the fork, kept as a control rather than as prose. It
    #   asserts the OPPOSITE of what the withdrawn reading needed: the passage said to be
    #   silent is not silent. ⛔ It fails the day that passage stops containing the rule,
    #   which is exactly when the withdrawal would stop being justified.
    refuting_passage = PassageAbsence(
        claim=(
            "the withdrawn reading's claim: that the second copy does not invoke the "
            "reversal of the node's degrees where the series is founded"
        ),
        edition=second,
        passage_label="adhyaya 1, pada 1, the commentary to sutra 11",
        after=FOUNDING_PASSAGE_OPENS,
        before=FOUNDING_PASSAGE_CLOSES,
        alphabet=REVERSAL_ALPHABET,
        alphabet_read_from=(
            "every spelling read off this copy — four off its own commentary to sutra 53, "
            "where it states the same rule, and three off its use of reversed order "
            "elsewhere. ⛔ None was guessed from the idea, and each is attested in this copy"
        ),
    )

    # ⭐⭐ The two copies number AND order the sutras differently, so no offset describes the
    #    pair. Measured at the neighbouring sutra both copies print.
    alignment = Alignment(
        label=(
            "whether the two copies' loci for the later determination are the same sutra"
        ),
        anchor_in_first=Locus(
            source_kind="translation",
            edition=edition,
            locus="adhyaya 2, pada 1, sutra 48",
            interpretation_status="restated",
            fragment=(
                "SU. 48.-Brahmani sanaupatayorva tataha. If Sani, Rahu or Ketu becomes Brahma,"
            ),
        ),
        anchor_first_number=48,
        anchor_in_second=Locus(
            source_kind="translation",
            edition=second,
            locus="adhyaya 2, pada 1, sutra 50",
            interpretation_status="restated",
            fragment="ब्रह्मणि शनो पातयोर्वा ततः ॥५०॥",
        ),
        anchor_second_number=50,
        first_number=50,
        second_number=53,
    )

    # ⛔ Appended after the three standing controls because these two WITHDRAW a published
    #   finding, and a reader should meet them beside the correction row.
    controls += [
        {
            "finding": "control",
            "control": "the_passage_the_withdrawn_fork_called_silent_is_not_silent",
            "measured": refuting_passage.as_row(),
            # ⭐ The control asserts the passage DOES contain the rule, so it holds when the
            #   absence does NOT. ⚠ It fails the day that passage stops containing it — which
            #   is the day the withdrawal would stop being justified.
            "held": not refuting_passage.established,
            "meaning": (
                "⭐⭐⭐ THE FORK PUBLISHED FROM THIS FILE RESTED ON AN ABSENCE NOBODY "
                "MEASURED. The second copy's commentary to the founding sutra states the "
                "reversal in full. ⚠ And the ordinary word for it is absent from that "
                "passage - measured, zero - so an absence search in the obvious alphabet "
                "would have CONFIRMED the fork: the copy gives the rule there as arithmetic "
                "and elsewhere as description. ⛔ An alphabet built from the idea rather than "
                "from the other copy's own wording tests nothing"
            ),
        },
        {
            "finding": "control",
            "control": "no_single_offset_describes_the_two_copies_numbering",
            "measured": alignment.as_json(),
            # ⭐ Holds when the anchor's offset does NOT carry: the claim being controlled is
            #   that arithmetic on sutra numbers is unsafe across this pair, and it is.
            "held": not alignment.offset_holds,
            "meaning": (
                "⛔⛔ A DIFFERENCE OF SUTRA NUMBER READS EXACTLY LIKE A DIFFERENCE OF PLACE. "
                "The offset measured at the neighbouring sutra both copies print is 2; at the "
                "sutra under comparison it is 3, because the copies ORDER the sutras "
                "differently. ⭐ A recorder carrying the neighbour's offset lands on a "
                "different sutra and concludes the two copies attach the rule to different "
                "determinations - which is what was published. Identity of place is refused "
                "rather than asserted"
            ),
        },
    ]

    # ⭐⭐⭐ THE SECOND COMMENTING HAND IN THE FIRST COPY — the finding of this session, and
    #    the reason the second-printing question could not simply be re-put and answered.
    hands = SecondHand(
        edition=edition,
        the_notes_are_credited_to="B. Suryanarain Rao",
        speaks_of_the_translator_in_the_third_person=THIRD_PERSON_OF_THE_TRANSLATOR,
        claims_work_of_its_own=SECOND_HAND_CLAIMS,
        marked_by=SECOND_HAND_ALPHABET,
        # ⛔ Measured, and false: the copy carries no title page, imprint or preface, and
        #    naming the hand from the books it claims would supply an authorship from memory.
        named_within_this_copy=False,
    )

    # ⭐ Whether the second hand's marks fall in the passage the two recorded note-rules stand
    #   in. ⛔ Bounded by two landmarks that each resolve exactly once — the one absence that
    #   may honestly be taken here — and its LIMIT is stated on the control rather than left
    #   to be inferred: a silent revision leaves no marker, so this zero does not return the
    #   passage to the translator.
    second_hand_in_the_notes = PassageAbsence(
        claim=(
            "that the second commenting hand's marks stand in the notes to the founding "
            "sutra, where both of this file's translator's-note rules are located"
        ),
        edition=edition,
        passage_label="adhyaya 1, pada 1, the notes to sutra 11",
        after=NOTES_TO_SUTRA_11_OPEN,
        before=NOTES_TO_SUTRA_11_CLOSE,
        alphabet=SECOND_HAND_ALPHABET,
        alphabet_read_from=(
            "every spelling read off this copy — the asterisk it prints as the second hand's "
            "marker, and eleven of that hand's own turns of phrase, taken from the five "
            "passages in which it speaks of the translator in the third person or claims work "
            "of its own. ⛔ None was guessed, and each is attested in this copy"
        ),
    )

    refusals = refusals_for(edition) + [
        Refusal(
            subject=(
                "that the two copies state the reversal at the SAME sutra of the later "
                "determination"
            ),
            reason="place_in_the_work_not_established_across_copies",
            detail=(
                "both copies state it, and where in the work each states it cannot be settled "
                "from their numbering. ⭐ Measured at the neighbouring sutra both print: the "
                "offset is 2 there, 2 again at the sutra after the disputed one, and 3 at the "
                "disputed one itself — because the copies do not merely renumber, they "
                "REORDER, one placing a sutra before the pair that the other places after. "
                "⛔⛔ An offset carried from any neighbour lands on a different sutra "
                "entirely, which is how a difference of numbering becomes a published "
                "difference of doctrine. ⚠ Settling it from the sutras' own words would need "
                "to match a roman transliteration against a Devanagari line, and no authority "
                "for that is held here"
            ),
            what_would_close_it=(
                "a copy that prints both scripts for the same sutra, or a stated concordance "
                "between the two copies' numbering, resolvable in a named copy"
            ),
        ),
    ]
    controls += [
        {
            "finding": "control",
            "control": "the_second_hands_marks_are_absent_from_the_notes_that_carry_two_rules",
            "measured": second_hand_in_the_notes.as_row(),
            "held": second_hand_in_the_notes.established,
            "meaning": (
                "⭐ the two rules this file files as THE TRANSLATOR'S NOTES stand in an "
                "8 959-character passage bounded by the founding sutra and the next, and none "
                "of the twelve spellings by which this copy marks its SECOND commenting hand "
                "occurs in it. ⛔⛔ WHAT THIS DOES NOT ESTABLISH IS THE THING IT LOOKS LIKE: "
                "the passage carries none of that hand's MARKS, which is not the same as "
                "carrying the first translator's words. A reviser who rewrites silently leaves "
                "no marker, and this copy's second hand says in its own voice that it "
                "refrained from altering ONE sutra's rendering - a disclaimer scoped to one "
                "sutra is worth making only by a hand that alters others"
            ),
        },
        {
            "finding": "control",
            "control": "a_copy_that_renders_to_nothing_passes_every_absence_test",
            "measured": {
                "edition": scanned.key,
                "pages_retrieved": 219,
                "bytes_retrieved": scanned.witness.copy_bytes,
                "the_renderings_own_character_count": scanned.rendering.characters,
                "characters_a_locus_can_resolve_against": scanned.searchable_characters,
                "what_the_218_characters_are": (
                    "one newline per page boundary. The extractor returned an empty string "
                    "for each of 219 image pages and joined them, so the count is the page "
                    "count minus one and contains no text whatever"
                ),
                "would_a_guard_written_characters_equals_zero_fire": False,
                # ⚠ A list of objects rather than a map keyed by the instrument's name. The
                #   writer refuses a key that is not lower_snake_case, and it refused these.
                "absence_instruments_run_against_this_copy": [
                    {
                        "instrument": "an absence over the whole copy",
                        "outcome": "refused - the copy carries no searchable text",
                    },
                    {
                        "instrument": "an absence over a bounded passage",
                        "outcome": (
                            "refused, and NAMING THE RIGHT CAUSE - before this session it "
                            "refused too, but reported that the alphabet had been GUESSED, "
                            "which would send a reader to fix a vocabulary that was never "
                            "the problem"
                        ),
                    },
                ],
            },
            "held": bool(
                not scanned.carries_searchable_text and scanned.rendering.characters != 0
            ),
            "meaning": (
                "⭐⭐⭐ AN ABSENCE OVER A COPY THAT WAS NEVER READ IS THE STRONGEST-LOOKING "
                "ABSENCE THIS INSTRUMENT CAN PRINT AND THE EMPTIEST. This copy is the second "
                "printing the standing refusal asked for: the right work, retrieved, digested "
                "- and 219 pages of images. Every spelling returns zero over it, in any "
                "alphabet, at any length. ⛔ And the number that should have caught it does "
                "not: the rendering reports 218 characters, so a guard written `characters == "
                "0` passes it. ⇒ Both absence instruments now require the copy to have been "
                "SHOWN to speak, and this control holds only while that copy is both mute and "
                "non-zero - the exact combination that made the hazard invisible"
            ),
        },
    ]

    rows = rule_rows(edition, refusals)
    rows += corroboration_rows(second)
    rows.append(dict(WITHDRAWN))
    rows.append(hands.as_row())
    rows.append({"finding": "alignment", **alignment.as_json()})

    absence = AbsenceSearch(
        claim=ABSENT_CLAIM,
        alphabet=ALPHABET,
        edition=edition,
        occurrences=[
            hit for spelling in ENUMERATED for hit in collect_occurrences(edition, spelling)
        ],
        what_the_hits_do_say=WHAT_THE_HITS_SAY,
        # ⛔ The proof that the zeroes in this row were measured over a copy that speaks. It
        #   is the founding sutra's own translated line — the passage every rule here hangs
        #   from — and it resolves exactly once.
        positive_control=RULES[0]["fragment"],
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

    header = build_header(script, edition, second, scanned, len(RULES), refusals, controls)
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
