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
import re
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
    AbsenceAcrossReadings,
    AbsenceSearch,
    Alignment,
    Edition,
    Rendering,
    Witness,
    IndependentHandAttestation,
    Locus,
    MarkerAlphabet,
    NamedInAnotherCopy,
    PassageAbsence,
    Refusal,
    SecondHand,
    SelfContradiction,
    TextualError,
    alphabet_contamination,
    collect_occurrences,
    digest,
    LEAST_EXTENT_AN_ACCEPTANCE_DISCRIMINATES_AT,
    LEAST_EXTENT_A_REFUSAL_DISCRIMINATES_AT,
    LEAST_RECURRENCE,
    RECURRENCE_MEASURED_AT,
    discrimination_of_resolving_once,
    normalise,
    blocks_this_floor_refuses,
    every_window_of,
    recurrence_of,
    reading_disagreement,
    refusal_summary,
    resolve,
    scripts_in,
    scripts_required_by,
    source_oracle,
)

EDITION = "jaimini_sutras_rao"

#: ⭐ The copy the standing refusal asked for — a second printing of the FIRST translation —
#: acquired this session and refused for a reason nobody predicted. ⛔ 219 pages of scanned
#: page images: the right work, retrievable, digested, and carrying no searchable text at all.
SCANNED_PRINTING = "jaimini_sutras_rao_scanned_printing"

#: A second real book of this genre, held in the same cache. ⛔ This generator loads it ONLY
#: as held-out evidence about its own constants - no rule, refusal or attestation below reads
#: it, and that is what makes it held out.
BPHS_SANTHANAM = "bphs_santhanam"

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

# --------------------------------------------------------------------------------------
# The two candidate printings acquired for the second-printing TEST
# --------------------------------------------------------------------------------------

#: ⭐⭐⭐ THE COPY THIS FILE HELD AS MUTE, READ BY SOMEONE ELSE. The 219-page printing whose
#: rendering carries no text is byte-identical to a copy a public archive distributes with a
#: machine reading of 205 055 Latin letters - same 13 905 548 bytes, same SHA-1. ⛔ The
#: muteness was a property of the rendering, never of the copy.
THIRD_EDITION = "jaimini_sutras_rao_third_edition"

#: ⛔ Two further machine readings of that same edition, held in order to be DISAGREED WITH.
THIRD_EDITION_READINGS: tuple[str, ...] = (
    THIRD_EDITION,
    "jaimini_sutras_rao_third_edition_second_reading",
    "jaimini_sutras_rao_third_edition_third_reading",
)

#: What the copy held as mute prints about its own printing. ⛔ Resolves exactly once, and
#: nothing outside this copy corroborates it.
THIRD_EDITION_FOREWORD = "the third and revised edition of the English Translation"

#: ⭐ The same claim on a different page of the same copy - the title page's own imprint, as
#: this machine reading damaged it. ⚠ Corroborates the foreword WITHIN one copy, which is a
#: weaker thing than corroboration across copies and is recorded as such.
THIRD_EDITION_IMPRINT = "THIRD E DITTO"

#: ⛔ The fragment that makes three renderings three readings of ONE edition rather than
#: three books. It is the only one of the four tried that resolves exactly once in all three.
THE_READINGS_ARE_OF_ONE_EDITION_BECAUSE = "my revered grandfather late Professor"

#: ⭐⭐⭐ THE MATERIAL THE SECOND-HAND ALPHABET MUST NOT MARK, and does. Each passage resolves
#: exactly once in the third edition. ⛔ Four of the twelve spellings occur inside one of
#: them, and every one of the four is something a printing FREE of the second hand would
#: still carry: its translator's name, its first sutra, and its reader's own damage.
THE_ALPHABET_MUST_NOT_MARK: tuple[tuple[str, str], ...] = (
    (
        "the translator named on his own title page",
        "By Prof. B SURYANARAIN RAO",
    ),
    (
        "the translator named on the half-title of the translation itself",
        "ENGLISH TRANSLATION BY Professor B. SURYANARAIN RAO",
    ),
    (
        "the translation of the FIRST SUTRA of the work - the primary text speaking",
        "I shall now explain my work for the benefit of the readers",
    ),
    (
        "the machine reading's own damage, printed where it could not read a letter",
        "REVISED AND EDITED BY HIS GRANDSON B* V. RAMAN",
    ),
)

#: ⚠ The foreword's disclaimer as the THIRD edition prints it. ⛔ The fifth prints the same
#: sentence with one verb changed, and the pair is the finding.
THIRD_EDITION_DISCLAIMER = "I have not interfered with either"

#: The same sentence in the fifth edition, six years later.
FIFTH_EDITION_DISCLAIMER = "I have not meddled with either"

#: ⭐ The sentence that contradicts it, printed in BOTH editions.
THE_CONTRADICTING_SENTENCE = "The Translation herewith presented has been"


#: ⭐⭐⭐ THE CANDIDATE THE STANDING TEST ASKED FOR — and it fails the test by explaining
#: itself. A printing of the same translation carrying a title page, an imprint and a SIGNED
#: foreword. All twelve spellings occur in it, so it cannot witness the unrevised words
#: either; and it is the copy that turns *this copy does not say whose* into a located name.
FIFTH_EDITION = "jaimini_sutras_rao_fifth_edition"

#: ⛔⛔⛔ THE SECOND CANDIDATE, AND IT IS THE TRAP THE TEST WAS WARNED ABOUT WEARING A
#: DIFFERENT FACE. Eleven of the twelve spellings return zero over it. It carries a quarter
#: of a million searchable characters and not one letter of the alphabet its book is
#: printed in.
LIBRARY_SCAN = "jaimini_sutras_rao_library_scan"

#: What the naming copy prints about its own printing. ⛔ Resolves exactly once there, and
#: nothing corroborates it: it is that copy's claim about itself, recorded as such.
FIFTH_EDITION_IMPRINT = "Fifth Edition 1955"

#: The signed statement naming the second commenting hand. ⛔ Resolves exactly once.
FIFTH_EDITION_NAMES_THE_HAND = "Revised and Annotated by BANGALORE VENKATA RAMAN"

#: The name as that copy prints it. ⛔ Measured to occur ZERO times in the unnamed copy —
#: the earlier finding is re-measured rather than trusted.
THE_NAME_AS_THAT_COPY_PRINTS_IT = "Bangalore Venkata Raman"

#: ⭐⭐⭐ THE ONE FRAGMENT THAT RESOLVES EXACTLY ONCE IN BOTH COPIES, out of the ten tried.
#: It is the second hand's own claim of a book — the claim the earlier session refused to
#: turn into a name, now doing the work honestly because the other copy prints the name.
THE_TIE_BETWEEN_THE_TWO_COPIES = (
    "* I have discussed Rasi Dasa at considerable length in my book Studies in Jaimini "
    "Astrology."
)

#: ⛔⛔ The two sentences of one signed foreword that cannot both be relied on. Quoted in the
#: spelling this machine reading produced, defects intact.
FOREWORD_CLAIMS_NO_ALTERATION = (
    "I have not meddled with either the translation or the notes as given by Prof. Rao for "
    "fear of aifecting the sense."
)
FOREWORD_CLAIMS_THOROUGH_REVISION = (
    "The Translation herewith presented has been tho- roughly revised by me"
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

#: ⭐ The corroboration row for each rule, by rule id. ⚠ It is what lets a rule filed as a
#: HAND's words be attested in a copy outside that hand's reach - and a rule with no
#: corroboration simply has no attestation row, which is a visible gap rather than a
#: silence.
CORROBORATION_BY_RULE: dict[str, dict[str, Any]] = {c["rule"]: c for c in CORROBORATION}

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


#: ⛔⛔⛔ TWELVE CHARACTERS OF THE LIBRARY SCAN'S OWN NOISE, READ OFF IT, RESOLVING EXACTLY
#: ONCE. It is offered as a positive control on purpose, to show what a positive control is
#: worth in that copy: 300 of 300 candidate fragments of this length resolve exactly once
#: there, because nothing in a noise rendering repeats. ⭐ The condition this repository
#: leans on hardest is, in that one copy, the easiest in the file to satisfy.
LIBRARY_SCAN_CONTROL_FROM_ITS_OWN_NOISE = "\u096a\u096c\u096a\u096c \u096d\u096f \u090f\u0928\u094d\u0935\u091e\u092a\u094d\u0930\u093e"


def run_the_test(edition, *, positive_control: str) -> dict[str, Any]:
    """THE TEST: the twelve second-hand spellings over a whole candidate copy, zero required.

    ⭐ **The counting half is three lines and it is not the test.** What makes it a test is
    what happens when the count comes back zero, so both absence instruments are actually
    RUN against the copy and what they did is recorded — accepted, or refused and with which
    cause named. ⛔ A candidate that passes by being unreadable and a candidate that passes
    by not carrying the hand print the same row of zeroes, and only the refusal tells them
    apart.
    """
    body = edition.normalised.lower()
    counts = {
        spelling: body.count(normalise(spelling).lower())
        for spelling in SECOND_HAND_ALPHABET
    }
    total = sum(counts.values())
    outcomes = []
    for name, build in (
        (
            "an absence over the whole copy",
            lambda: AbsenceSearch(
                claim="that this printing carries none of the second hand's marks",
                alphabet=SECOND_HAND_ALPHABET,
                edition=edition,
                occurrences=[],
                what_the_hits_do_say=[],
                positive_control=positive_control,
            ),
        ),
        (
            "an absence over a bounded passage",
            lambda: PassageAbsence(
                claim="that a passage of this printing carries none of the second hand's marks",
                edition=edition,
                passage_label="any passage of this copy",
                after=positive_control,
                before=positive_control,
                alphabet=SECOND_HAND_ALPHABET,
                alphabet_read_from=(
                    "the twelve spellings read off the OTHER printing of this translation, "
                    "where each is attested"
                ),
            ),
        ),
    ):
        try:
            build()
        except TextualError as refusal:
            outcomes.append(
                {"instrument": name, "outcome": "refused", "the_cause_it_named": str(refusal)}
            )
        else:
            outcomes.append(
                {
                    "instrument": name,
                    "outcome": "accepted",
                    "the_cause_it_named": (
                        "none - the copy was readable in the alphabet searched and the "
                        "control resolved, so the counts below are the measurement"
                    ),
                }
            )
    return {
        "edition": edition.key,
        "searchable_characters": edition.searchable_characters,
        "the_renderings_own_character_count": edition.rendering.characters,
        "scripts_this_rendering_carries": [
            {"script": name, "letters": n} for name, n in sorted(edition.scripts.items())
        ],
        "the_alphabet_is_written_in": sorted(scripts_required_by(SECOND_HAND_ALPHABET)),
        "hits_by_spelling": [
            {"spelling": spelling, "hits": counts[spelling]}
            for spelling in SECOND_HAND_ALPHABET
        ],
        "hits_in_total": total,
        "spellings_with_any_hit": sum(1 for n in counts.values() if n),
        "spellings_searched": len(SECOND_HAND_ALPHABET),
        # ⛔ The number the test asks for, and the number that is not the answer.
        "would_the_count_alone_have_passed_this_copy": total == 0,
        "what_the_absence_instruments_did": outcomes,
        "how_the_instruments_were_exercised": (
            "⚠ both were CONSTRUCTED against this copy, which is where every refusal read "
            "here lives - a copy is rejected before a single spelling is counted, so a row "
            "that refuses never reaches the counting at all. ⛔ The bounded-passage "
            "instrument was given the positive control as both of its landmarks, which is "
            "not a passage anyone would search: nothing here reads the region, only the "
            "refusal the construction raises"
        ),
    }


def build_header(
    script: Path, edition, second, scanned, fifth, library_scan, resolved: int, refusals, controls
) -> Header:
    return Header(
        fixture_kind="textual_rule",
        reference="R6",
        generator=generator_for(script),
        generated=today(),
        title=(
            "The significator series as two located copies state it, a fork this file "
            "published and has withdrawn, and one widely repeated rule neither states"
        ),
        # ⚠ FIVE copies now, and three of them resolve nothing. It is listed because a reader
        #   checking this file must be able to see the copy that was acquired and refused —
        #   a candidate rejected in prose is a claim, and a candidate carrying a witness, a
        #   rendering and a measured extent of nothing is a measurement.
        oracle=source_oracle(
            [edition, second, scanned, fifth, library_scan],
            resolved=resolved,
            refused=len(refusals),
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
            "the_second_printing_test_is_withdrawn_and_what_replaces_it": (
                "⛔⛔⛔ THE TEST WAS RUN OVER THREE COPIES, ALL THREE FAILED, AND THE "
                "REASON NO CANDIDATE EVER PASSED IS THAT NO COPY OF THIS WORK CAN. Four of "
                "the twelve spellings it scored on mark the translator on his own title "
                "page, the TRANSLATED FIRST SUTRA, and the machine reading's own damage - so "
                "a printing free of the second hand fails it too. ⭐⭐⭐ And the score was "
                "never the protection: a library scan of this work carrying NO LATIN LETTERS "
                "scores a PERFECT pass on the eleven spellings that are words. ⇒ The control "
                "built on the test is WITHDRAWN as a correction row, carrying the three "
                "candidates' measurements into it so nothing measured is lost. ✅ What "
                "replaces it requires a PRESENCE: a rule filed as a HAND's words must RESOLVE "
                "at a located place in a copy outside that hand's reach. ⚠ It answers the "
                "EXPOSURE - whether a published rule could be a reviser's invention - and NOT "
                "the attribution: `revised_printing_cannot_witness_the_unrevised_words` "
                "stands, restated as the new test's entry condition"
            ),
            "what_a_rule_filed_as_a_hands_words_is_now_required_to_carry": (
                "⭐⭐ AN ATTESTATION IN A COPY THAT HAND COULD NOT HAVE TOUCHED. Both rules "
                "here filed as the translator's NOTES - the only two the question is live at "
                "- resolve at their own locus in a second translation working from the "
                "original, on both of their fragments. ⛔ What that establishes is that the "
                "RULE predates the hand's reach, never that the English words are the "
                "translator's; and the second translator is himself a modern commentator, so "
                "two copies agreeing establishes that a rule is not ONE hand's invention and "
                "nothing further"
            ),
            "the_second_hand_is_named_and_the_name_came_from_a_copy": (
                "⭐⭐⭐ *THERE IS A SECOND HAND HERE AND THIS COPY DOES NOT SAY WHOSE* IS "
                "ANSWERED, BY ANOTHER COPY'S PAGE. The naming printing carries a title page "
                "reading *Revised and Annotated by* a named hand and a SIGNED foreword by the "
                "same. ⛔ The tie between the two copies is ONE fragment resolving exactly "
                "once in both - the second hand's own claim of a book - out of ten tried; the "
                "other nine are present in both printings and spelled differently by the two "
                "machine readings. ⚠ The naming does not establish which printing the copy in "
                "hand is, and that refusal stands"
            ),
            "what_a_revisers_own_account_of_his_revision_is_worth": (
                "⛔⛔⛔ NOTHING, AND IT IS MEASURED RATHER THAN ARGUED. The signed foreword "
                "states *I have not meddled with either the translation or the notes as given "
                "by Prof. Rao* and, a paragraph later, *The translation herewith presented "
                "has been thoroughly revised by me*. ⭐ Neither is doubted; the PAIR is "
                "published. ⚠ It also retires an inference this file made from the other "
                "copy - that a disclaimer scoped to ONE sutra is worth making only by a hand "
                "that alters others - because the copy that kept its front matter makes the "
                "same disclaimer generally"
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
            "hand_named_in_another_copy": (
                "a commenting hand one copy carries and cannot name, named on the page of a "
                "different copy of the same translation, with the located fragment tying the "
                "two and an explicit statement of what the naming does NOT establish"
            ),
            "the_copy_disagrees_with_itself": (
                "two statements by one hand in one copy that cannot both be relied on, each "
                "resolving exactly once; the pair is the finding and neither is adopted"
            ),
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
        for key in (
            EDITION,
            SECOND_EDITION,
            SCANNED_PRINTING,
            FIFTH_EDITION,
            LIBRARY_SCAN,
            *THIRD_EDITION_READINGS,
        ):
            record = acquire(key, cache=args.cache, today=today())
            print(f"acquired {key}: {record['copy_bytes']} bytes, status {record['http_status']}")

    edition = load(EDITION, cache=args.cache)
    second = load(SECOND_EDITION, cache=args.cache)
    # ⭐ The copy the standing refusal asked for. ⛔ It is loaded so that what it establishes
    #   is MEASURED rather than described: 219 pages, a rendering reporting 218 characters,
    #   and not one character a locus could resolve against.
    scanned = load(SCANNED_PRINTING, cache=args.cache)
    # ⭐⭐⭐ The two candidates the second-printing TEST was run against. One states its own
    #   printing and names the second hand; the other returns eleven zeroes out of twelve and
    #   returns them because its machine reading contains no English.
    fifth = load(FIFTH_EDITION, cache=args.cache)
    library_scan = load(LIBRARY_SCAN, cache=args.cache)
    # ⭐⭐⭐ THE THIRD CANDIDATE, AND IT IS THE COPY THIS FILE ALREADY HELD. Byte-identical
    #   to the printing recorded here as *renders to nothing*, read by its distributor into
    #   205 055 Latin letters. ⛔ Loaded three times over, because three machine readings of
    #   one edition are what show a zero to be a property of a reader.
    third_edition_readings = [load(key, cache=args.cache) for key in THIRD_EDITION_READINGS]
    third = third_edition_readings[0]
    for reading in third_edition_readings:
        print(
            f"reading {reading.key}: searchable {reading.searchable_characters}, "
            f"scripts {reading.scripts}"
        )
    for candidate in (fifth, library_scan):
        print(
            f"candidate {candidate.key}: searchable {candidate.searchable_characters}, "
            f"scripts {candidate.scripts}"
        )
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

    # ======================================================================================
    # THE SECOND-PRINTING TEST, third time of asking — run, and read
    # ======================================================================================

    test_results = [
        run_the_test(fifth, positive_control=FOREWORD_CLAIMS_NO_ALTERATION),
        run_the_test(
            library_scan, positive_control=LIBRARY_SCAN_CONTROL_FROM_ITS_OWN_NOISE
        ),
        # ⚠ The copy the previous session acquired, re-run so the three sit in one row and a
        #   reader can see that two different causes produce the same reassuring zeroes.
        run_the_test(scanned, positive_control=FOREWORD_CLAIMS_NO_ALTERATION),
    ]
    for result in test_results:
        print(
            f"test {result['edition']}: {result['hits_in_total']} hit(s) across "
            f"{result['spellings_with_any_hit']}/{result['spellings_searched']} spelling(s); "
            f"count alone would pass: {result['would_the_count_alone_have_passed_this_copy']}"
        )

    # ⭐⭐⭐ The finding the test did not ask for: the hand this repository could not name is
    #    named, on another copy's own page, and the two copies are tied by one located
    #    fragment out of the ten tried.
    naming = NamedInAnotherCopy(
        the_hand=(
            "the second commenting hand in the printing every rule in this file resolves "
            "into - the one that names the translator in the third person, says his notes "
            "are not clear, and claims books of its own"
        ),
        unnamed_in=edition,
        named_in=fifth,
        the_name_as_that_copy_prints_it=THE_NAME_AS_THAT_COPY_PRINTS_IT,
        the_passage_that_names_it=FIFTH_EDITION_NAMES_THE_HAND,
        the_printing_that_copy_declares=FIFTH_EDITION_IMPRINT,
        tied_to_the_unnamed_hand_by=(THE_TIE_BETWEEN_THE_TWO_COPIES,),
        what_this_does_not_establish=(
            "⛔ WHICH PRINTING THE UNNAMED COPY IS. It carries no title page, no imprint and "
            "no foreword, and the naming copy's imprint speaks for the naming copy. ⚠ Nor "
            "does it establish that every asterisked note in the unnamed copy is this hand's: "
            "what is located is one claim of a book, printed in both copies, beside a signed "
            "statement in one of them that the annotations are the signer's. ⛔ And the "
            "attribution runs no further than the copies - nothing here corroborates the "
            "naming copy's title page from outside it"
        ),
    )

    # ⛔⛔ The foreword that names the hand also states two things that cannot both be acted
    #    on, and the first of them is exactly the sentence that would retire this file's
    #    standing refusal.
    foreword = SelfContradiction(
        edition=fifth,
        the_hand="the hand the naming copy's title page calls its reviser and annotator",
        statements=(
            ("that nothing of the translation or the notes was altered", FOREWORD_CLAIMS_NO_ALTERATION),
            ("that the translation was thoroughly revised by the same hand", FOREWORD_CLAIMS_THOROUGH_REVISION),
        ),
        why_they_cannot_both_be_relied_on=(
            "⛔ they are two sentences of ONE signed foreword, and a reader deciding whether "
            "this printing carries the translator's own words needs exactly the question they "
            "disagree about. ⭐ Taking the first alone would have retired this file's standing "
            "refusal on the strength of a claim the same hand contradicts a paragraph later; "
            "taking the second alone would assert an alteration the copy does not itemise"
        ),
        what_it_settles=(
            "⭐⭐⭐ that a REVISER'S OWN ACCOUNT OF WHAT HE CHANGED IS NOT EVIDENCE OF WHAT HE "
            "CHANGED - measured here rather than argued, because this one disagrees with "
            "itself in a single paragraph. ⛔ It also settles that the earlier reading of the "
            "unnamed copy's scoped disclaimer was an inference and not a measurement: *a "
            "disclaimer scoped to one sutra is worth making only by a hand that alters "
            "others* looked compelling because the copy in hand had lost its front matter, "
            "and the copy that kept its front matter makes the same disclaimer generally"
        ),
    )

    # ⭐⭐ How much a positive control is worth in each of the two copies, at the same
    #    fragment length. ⛔ A cap is applied and it is stated: the number is a share over the
    #    first 300 distinct runs of that length in document order, not over every run.
    def _runs(source, pattern: str, length: int, cap: int = 300) -> list[str]:
        seen: set[str] = set()
        out: list[str] = []
        for run in re.findall(pattern % (length - 1), source.normalised):
            run = run.strip()
            if len(run) == length and run not in seen:
                seen.add(run)
                out.append(run)
                if len(out) >= cap:
                    break
        return out

    noise_discrimination = discrimination_of_resolving_once(
        library_scan, _runs(library_scan, r"[\u0900-\u097F][\u0900-\u097F\s]{%d}", 8)
    )
    book_discrimination = discrimination_of_resolving_once(
        edition, _runs(edition, r"[A-Za-z][A-Za-z\s]{%d}", 8)
    )

    # ⭐⭐⭐ The measurement that says the script bucket had to be defined over LETTERS. Read
    #    as a bare code-point range it reports six thousand Latin characters in the copy that
    #    contains no Latin letter, and the guard built on it would have passed that copy.
    punctuation_in_the_latin_block = sum(
        1
        for character in library_scan.normalised
        if 0x0041 <= ord(character) <= 0x024F and not character.isalpha()
    )

    ten_candidate_ties = [
        *(rule["fragment"] for rule in RULES),
        *THIRD_PERSON_OF_THE_TRANSLATOR,
        *SECOND_HAND_CLAIMS,
    ]
    ties_resolving_in_both = [
        fragment
        for fragment in ten_candidate_ties
        if edition.normalised.count(normalise(fragment)) == 1
        and fifth.normalised.count(normalise(fragment)) == 1
    ]

    refusals += [
        Refusal(
            subject=(
                "the printing that declares itself the fifth as a witness to the "
                "translator's own unrevised words"
            ),
            reason="revised_printing_cannot_witness_the_unrevised_words",
            detail=(
                "⭐⭐⭐ THE TEST WAS RUN AND THIS CANDIDATE FAILED IT, WHICH IS THE MOST "
                "USEFUL THING IT COULD HAVE DONE. All twelve spellings marking the second "
                "hand occur in it - 215 hits, twelve of twelve spellings - so it carries that "
                "hand throughout. ⛔ And it says why in its own words: its title page reads "
                "*Revised and Annotated by* a named hand, its imprint reads *Fifth Edition "
                "1955*, and its signed foreword presents the fifth and revised edition. ⚠ Two "
                "printings a reviser worked over agree about the revision, so a second such "
                "printing can never be the witness this refusal asks for"
            ),
            what_would_close_it=(
                "⛔ a printing carrying NONE of the twelve spellings, over a copy shown to be "
                "readable IN THE SCRIPT THOSE SPELLINGS ARE WRITTEN IN. ⚠ Two candidates have "
                "now failed in two different ways and neither failure was the absence of the "
                "hand: one carries it and says so, the other returns eleven zeroes because "
                "its machine reading contains no English at all"
            ),
        ),
        Refusal(
            subject=(
                "any absence whatever measured over the library scan acquired this session"
            ),
            reason="rendering_carries_none_of_the_searched_script",
            detail=(
                "⛔⛔⛔ IT IS THE RIGHT WORK, IT WAS READ, AND IT WAS READ IN THE WRONG "
                "ALPHABET. The archive's own machine reading of this scan carries 246 777 "
                "searchable characters and NOT ONE LETTER OF THE LATIN ALPHABET, for a book "
                "printed in English: the reader was set to an Indic script and returned a "
                "quarter of a million characters of noise. ⭐ Eleven of the twelve spellings "
                "return zero over it and the twelfth - the printed asterisk, which is not a "
                "word - returns 128, so a test scored on the count alone comes within one "
                "punctuation mark of declaring this copy free of the second hand. ⚠ Every "
                "guard this repository owned before this session passes it: it is not "
                "missing, not out of extent, and emphatically not mute"
            ),
            what_would_close_it=(
                "a machine reading of this same scan produced in the script the book is "
                "printed in, by its distributor. ⛔ Not by this repository: an absence over "
                "our own machine reading is an absence over our own mistakes"
            ),
        ),
        Refusal(
            subject="which printing the copy every rule here resolves into actually is",
            reason="place_in_the_work_not_established_across_copies",
            detail=(
                "⚠ THE PREREQUISITE NOBODY HAD STATED, AND IT IS STILL UNMET. The copy in "
                "hand carries no title page, no imprint and no foreword; measured, the words "
                "*edition*, *Preface*, *Copyright*, *Publisher*, *Published* and *Printed* "
                "occur zero times in it. ⛔ A printing that names itself has now been "
                "acquired, and matching the two by their words does not settle it either: of "
                f"ten fragments resolving exactly once in the copy in hand, {len(ties_resolving_in_both)} "
                "resolves exactly once in the naming copy too - the other nine occur ZERO "
                "times there, and every one of the nine is present on the page in a slightly "
                "different machine reading. ⭐⭐⭐ *A fragment that resolves in one machine "
                "reading and not in a second machine reading of the same words measures the "
                "two readings, not the two printings* - and a recorder scoring that as "
                "agreement or as absence would publish either conclusion with equal "
                "confidence"
            ),
            what_would_close_it=(
                "an imprint, a title page or a copyright statement inside the copy in hand, "
                "resolving there. ⛔ Not a filename, not a catalogue entry and not a "
                "resemblance to another copy"
            ),
        ),
    ]

    controls += [
        {
            "finding": "control",
            "control": "a_rendering_can_be_read_in_the_wrong_alphabet_and_pass_every_older_guard",
            "measured": {
                "edition": library_scan.key,
                "searchable_characters": library_scan.searchable_characters,
                "the_renderings_own_character_count": library_scan.rendering.characters,
                "letters_of_the_alphabet_the_book_is_printed_in": library_scan.scripts.get(
                    "latin", 0
                ),
                "letters_this_rendering_does_carry": [
                    {"script": name, "letters": n}
                    for name, n in sorted(library_scan.scripts.items())
                ],
                "characters_in_the_latin_block_that_are_not_letters": (
                    punctuation_in_the_latin_block
                ),
                "would_the_mute_copy_guard_fire": not library_scan.carries_searchable_text,
                "would_a_guard_written_characters_equals_zero_fire": (
                    library_scan.rendering.characters == 0
                ),
                "what_the_latin_block_count_would_have_said": (
                    "⛔⛔ 6 077, AND THIS REPOSITORY WROTE THAT NUMBER BEFORE IT CHECKED IT. "
                    "Defined as a bare code-point range the Latin bucket counts every brace, "
                    "bracket and sign that happens to live inside the block, so the guard "
                    "built to catch a copy with no Latin letters reported six thousand Latin "
                    "characters IN EXACTLY THAT COPY and passed it. ⭐ The bucket is defined "
                    "over LETTERS now, and this row carries both numbers because the pair is "
                    "the finding"
                ),
            },
            "held": bool(
                library_scan.carries_searchable_text
                and library_scan.scripts.get("latin", 0) == 0
                and punctuation_in_the_latin_block > 0
            ),
            "meaning": (
                "⭐⭐⭐ A COPY THAT WAS READ, IN THE WRONG ALPHABET, IS STRICTLY MORE "
                "DANGEROUS THAN A COPY THAT WAS NEVER READ. The mute printing fails every "
                "check that asks whether anything was read; this one passes all of them - a "
                "quarter of a million searchable characters - and still returns zero for "
                "every English word in an English book. ⛔ This control holds only while all "
                "three remain true: the copy is readable, it carries no letter of the searched "
                "script, and its Latin block is nonetheless full of marks. Any one of them "
                "changing means the guard has stopped describing the copy it was built for"
            ),
        },
        {
            "finding": "control",
            "control": "resolving_exactly_once_filters_nothing_in_a_rendering_of_noise",
            "measured": {
                "in_the_copy_of_noise": noise_discrimination,
                "in_a_copy_that_is_a_book": book_discrimination,
                "fragment_length_compared": 8,
                "the_cap_applied": (
                    "the first 300 distinct runs of that length in document order, per copy. "
                    "⛔ Stated because a cap nobody states reads as complete coverage"
                ),
                "the_control_this_copy_will_happily_provide": {
                    "quoted": LIBRARY_SCAN_CONTROL_FROM_ITS_OWN_NOISE,
                    "occurrences": library_scan.normalised.count(
                        normalise(LIBRARY_SCAN_CONTROL_FROM_ITS_OWN_NOISE)
                    ),
                },
            },
            "held": bool(
                noise_discrimination["share_resolving_exactly_once"]
                > book_discrimination["share_resolving_exactly_once"]
            ),
            "meaning": (
                "⭐⭐⭐ THE CONDITION THIS REPOSITORY LEANS ON HARDEST IS, IN ONE COPY, THE "
                "EASIEST IN THE FILE TO SATISFY. A previous session armed every absence to "
                "require a positive control resolving EXACTLY ONCE. Over the library scan 300 "
                "of 300 eight-character fragments resolve exactly once, because nothing in a "
                "noise rendering repeats; over a real book at the same length 129 of 300 do. "
                "⛔ So a control quoted out of that copy's own noise is free to obtain, "
                "resolves perfectly, and licenses a twelve-spelling absence in an alphabet "
                "the rendering contains none of. ⇒ A control is now required to be written in "
                "the SCRIPT THE ALPHABET IS WRITTEN IN, and that refusal is exercised against "
                "a real copy carrying both scripts"
            ),
        },
        {
            "finding": "control",
            "control": "the_hand_this_file_could_not_name_is_named_on_another_copys_page",
            "measured": {
                # ⚠ The naming itself is a ROW of its own in this file, not repeated here.
                "the_row_that_carries_it": "hand_named_in_another_copy",
                "the_name_as_the_other_copy_prints_it": THE_NAME_AS_THAT_COPY_PRINTS_IT,
                "candidate_ties_tried": len(ten_candidate_ties),
                "ties_resolving_exactly_once_in_both_copies": len(ties_resolving_in_both),
                "why_nine_failed": (
                    "⛔ NOT ABSENCE. Every one of the nine is on the page in both printings "
                    "and the two machine readings spell it differently - a letter read as a "
                    "digit, a word hyphenated across a line break, a quotation mark invented. "
                    "⭐ A recorder scoring these as *the naming copy does not contain the "
                    "rules* would publish nine absences that are facts about two OCR passes"
                ),
            },
            "held": bool(len(ties_resolving_in_both) >= 1),
            "meaning": (
                "⭐⭐⭐ *THERE IS A SECOND HAND HERE AND THIS COPY DOES NOT SAY WHOSE* IS "
                "ANSWERED, AND ONLY A COPY COULD ANSWER IT. The earlier refusal was never "
                "that the hand was unguessable - it was that turning the books it claims into "
                "a name would supply an authorship from the recorder's memory. A printing of "
                "the same translation names it on its title page and again in a signed "
                "foreword. ⛔ The tie between the two copies is ONE located fragment out of "
                "ten tried, and that is why the tie is required: nine of ten candidates fail "
                "on OCR difference alone"
            ),
        },
        {
            "finding": "control",
            "control": "the_naming_copys_foreword_disagrees_with_itself_about_the_revision",
            "measured": {
                # ⚠ The two statements are a ROW of their own; the control asserts the shape.
                "the_row_that_carries_it": "the_copy_disagrees_with_itself",
                "edition": fifth.key,
                "statements_located": len(foreword.statements),
            },
            "held": len(foreword.statements) == 2,
            "meaning": (
                "⛔⛔⛔ THE SENTENCE THAT WOULD HAVE RETIRED THIS FILE'S STANDING REFUSAL IS "
                "CONTRADICTED BY ITS OWN AUTHOR A PARAGRAPH LATER. *I have not meddled with "
                "either the translation or the notes as given by Prof. Rao* and *The "
                "translation herewith presented has been thoroughly revised by me* are two "
                "sentences of one signed foreword. ⭐ Neither is doubted and neither is "
                "adopted: the pair is the finding, and what it settles is that a reviser's "
                "own account of what he changed is not evidence of what he changed. ⚠ It also "
                "retires an INFERENCE this file published - that a disclaimer scoped to one "
                "sutra is worth making only by a hand that alters others - because the copy "
                "that still has its front matter makes the same disclaimer generally, and the "
                "scoped one is a repetition rather than a contrast"
            ),
        },
    ]


    # ----------------------------------------------------------------------------------
    # ⭐⭐⭐ THE FOURTH ASKING OF THE SECOND-PRINTING QUESTION, AND THE ANSWER IS ABOUT THE
    #     TEST. A third candidate was acquired and it is the copy this file already held.
    # ----------------------------------------------------------------------------------
    third_test = run_the_test(third, positive_control=THIRD_EDITION_FOREWORD)

    # ⛔ The alphabet checked against material it must not mark. Constructed so the refusal
    #   is exercised rather than described; the contamination itself is always computable.
    contamination = alphabet_contamination(
        SECOND_HAND_ALPHABET, third, THE_ALPHABET_MUST_NOT_MARK
    )
    try:
        MarkerAlphabet(
            marks="the second commenting hand",
            alphabet=SECOND_HAND_ALPHABET,
            edition=third,
            must_not_mark=THE_ALPHABET_MUST_NOT_MARK,
        )
    except TextualError as refused:
        alphabet_refusal = str(refused)
    else:
        alphabet_refusal = ""

    # ⛔ The same alphabet over three machine readings of ONE edition.
    disagreement = reading_disagreement(SECOND_HAND_ALPHABET, third_edition_readings)
    try:
        AbsenceAcrossReadings(
            claim="that this printing carries none of the second hand's marks",
            alphabet=SECOND_HAND_ALPHABET,
            readings=third_edition_readings,
            the_readings_are_of_one_edition_because=THE_READINGS_ARE_OF_ONE_EDITION_BECAUSE,
        )
    except TextualError as refused:
        readings_refusal = str(refused)
    else:
        readings_refusal = ""

    # ⭐ What the library scan would have scored had the one non-word spelling been dropped.
    #   ⛔ It is not dropped anywhere; the number is measured to show what the alphabet's one
    #   defective entry was accidentally doing.
    library_body = library_scan.normalised.lower()
    library_words_only = sum(
        1
        for spelling in SECOND_HAND_ALPHABET
        if scripts_in(spelling) and library_body.count(normalise(spelling).lower())
    )

    controls += [
        {
            "finding": "control",
            "control": "the_alphabet_the_test_is_scored_on_does_not_mark_the_hand_it_names",
            "measured": {
                "edition": third.key,
                "spellings_searched": len(SECOND_HAND_ALPHABET),
                "contaminated": len(contamination),
                "which": [c["spelling"] for c in contamination],
                "the_instrument_refused_it": bool(alphabet_refusal),
            },
            "held": bool(alphabet_refusal) and len(contamination) == 4,
            "meaning": (
                "⭐⭐⭐ THE TEST WOULD HAVE REJECTED THE PRINTING IT WAS BUILT TO FIND. Four of "
                "twelve spellings fire on the translator's own honorific, on a phrase of the "
                "first sutra, and on the machine reading's own damage - all of which a "
                "printing FREE of the second hand still carries. ⛔ An alphabet read off a "
                "copy carrying two hands inherits both: reading off a copy establishes that a "
                "spelling is ATTESTED, never that it DISCRIMINATES"
            ),
        },
        {
            "finding": "control",
            "control": "one_defective_spelling_was_the_only_thing_preventing_a_false_pass",
            "measured": {
                "edition": library_scan.key,
                "scripts_this_rendering_carries": [
                    {"script": name, "letters": n}
                    for name, n in sorted(library_scan.scripts.items())
                ],
                "latin_letters": library_scan.scripts.get("latin", 0),
                "spellings_with_any_hit_over_all_twelve": sum(
                    1
                    for spelling in SECOND_HAND_ALPHABET
                    if library_body.count(normalise(spelling).lower())
                ),
                "spellings_with_any_hit_over_the_eleven_that_are_words": library_words_only,
            },
            "held": library_words_only == 0,
            "meaning": (
                "⭐⭐⭐ THE ONE SPELLING THAT MARKS NOTHING IS THE ONLY THING THAT DENIED A "
                "COPY OF PURE NOISE A CLEAN PASS, AND IT DENIED IT BY ACCIDENT. A previous "
                "session recorded that the library scan - a rendering of an English printing "
                "carrying ZERO Latin letters - *misses a clean pass by one punctuation mark*. "
                "Scored on the eleven spellings that are words it scores 0 of 11: a PERFECT "
                "PASS, over a copy that cannot express English. ⛔ A recorder who tidied the "
                "asterisk out - correctly, since it is not a word and marks nothing - would "
                "have published a printing free of the second hand on the strength of noise. "
                "⚠ The repository was not in fact exposed: the script refusal armed the same "
                "session rejects that copy before a spelling is counted. ⭐ But the SCORE was "
                "never the protection, and this file said the count came close to working"
            ),
        },
        {
            "finding": "control",
            "control": "an_absence_over_one_reading_is_not_an_absence_over_the_printing",
            "measured": {
                "readings": [reading.key for reading in third_edition_readings],
                "spellings_whose_verdict_differs": len(disagreement),
                "which": [d["spelling"] for d in disagreement],
                "the_instrument_refused_it": bool(readings_refusal),
            },
            "held": bool(readings_refusal) and len(disagreement) == 4,
            "meaning": (
                "⭐⭐⭐ THE SAME EDITION READ THREE TIMES GIVES THREE DIFFERENT ANSWERS. Four "
                "of twelve spellings flip between zero and not-zero - among them the second "
                "hand's own claim of a book, printed on the page and lost by two of the three "
                "readers. ⛔ This is the second and independent defect in the test: even a "
                "clean pass would have measured the reader"
            ),
        },
        {
            "finding": "control",
            "control": "the_copy_this_file_held_as_mute_is_readable_and_names_its_own_printing",
            "measured": {
                "the_mute_rendering": {
                    "edition": scanned.key,
                    "the_renderings_own_character_count": scanned.rendering.characters,
                    "searchable_characters": scanned.searchable_characters,
                },
                "a_byte_identical_copy_read_by_its_distributor": {
                    "edition": third.key,
                    "searchable_characters": third.searchable_characters,
                    "latin_letters": third.scripts.get("latin", 0),
                },
                "the_bytes_are_the_same": {
                    "copy_bytes": 13905548,
                    "sha1": "cdf112dfa3d061658daf5e55a4c2e35337db5f5a",
                    "checked_against": (
                        "the distributing archive's own published file manifest, and the "
                        "digest of the copy in this repository's cache"
                    ),
                },
                "and_it_states_its_printing": resolve(
                    third, THIRD_EDITION_FOREWORD
                ).occurrences,
            },
            "held": (
                scanned.searchable_characters == 0
                and third.searchable_characters > 0
                and resolve(third, THIRD_EDITION_FOREWORD).resolved
            ),
            "meaning": (
                "⭐⭐⭐ A COPY THAT RENDERS TO NOTHING IN ONE READER IS NOT A COPY THAT SAYS "
                "NOTHING. This file recorded of the blank copy that it establishes *nothing "
                "whatever, and that includes its own identity* - that its work, translator "
                "and printing were known only from a host's filename. The same bytes, read by "
                "someone else, carry 205 055 Latin letters and state the printing on the "
                "first page. ⛔ The identity was never unavailable; it was unread, and the "
                "row that said otherwise made a property of this repository's renderer into a "
                "property of a book. See the correction row"
            ),
        },
        {
            "finding": "control",
            "control": "no_earlier_printing_than_the_third_edition_was_reachable",
            "measured": {
                "printings_of_this_translation_now_held": [
                    third.key,
                    fifth.key,
                    scanned.key,
                    library_scan.key,
                    edition.key,
                ],
                "printings_that_state_their_own_edition": [third.key, fifth.key],
                "the_earliest_reachable": third.key,
                "an_earlier_printing_is_established_to_have_existed_by": (
                    "this copy naming itself the THIRD revised edition, which presupposes a "
                    "first"
                ),
            },
            "held": True,
            "meaning": (
                "⛔ Every reachable digitised printing of this translation carries the same "
                "second hand's signed foreword. The earliest is the third edition, already "
                "revised by that hand. ⚠ A statement about what was found and never about "
                "what exists - and, given the two rows above, it would not have settled "
                "anything if an earlier one had been found, because the alphabet it would "
                "have been scored on does not mark the hand it names"
            ),
        },
    ]

    rows = rule_rows(edition, refusals)
    rows += corroboration_rows(second)
    rows.append(dict(WITHDRAWN))
    # ⛔⛔⛔ THE CONTROL THAT WAS WITHDRAWN, AND IT IS WITHDRAWN AS A ROW RATHER THAN DELETED.
    #    Its held condition was `no candidate passed the test`, and that is now known to be
    #    satisfied by EVERY copy of this work - so it could not change state and was not a
    #    control. ⭐ The three candidates' measurements move INTO the correction row, so
    #    nothing measured is lost by withdrawing the claim built on top of them.
    rows.append(
        {
            "finding": "correction",
            "rule": "the_second_printing_test_was_run_and_no_candidate_passed_it",
            "what_was_published": (
                "a CONTROL asserting that the second-printing test had been run over every "
                "candidate acquired and that none had passed it - written to FAIL the day a "
                "candidate passed, on the ground that that would be the day this file's "
                "standing refusal could be retired"
            ),
            "what_refutes_it": (
                "⛔⛔⛔ ITS HELD CONDITION IS SATISFIED BY EVERY COPY OF THIS WORK, SO IT "
                "COULD NEVER HAVE FAILED. Four of the twelve spellings the test scores on "
                "mark material the second hand did not put there - the translator's honorific "
                "on his own title page, the same on the half-title, a phrase of the TRANSLATED "
                "FIRST SUTRA (*I shall now explain my work*, resolving exactly once in every "
                "copy held here), and the machine reading's own damage. ⇒ A printing free of "
                "the second hand still contains sutra 1 and still names its translator, so no "
                "copy can carry none of the twelve. ⭐ A control that cannot change state is "
                "not a control; it is an assertion wearing a control's clothes"
            ),
            "and_the_second_reason_it_could_not_have_worked": (
                "⛔ the same edition read three times gives three answers - four of the twelve "
                "spellings flip between zero and not-zero across three machine readings of one "
                "printing. ⇒ A clean pass, had one been reachable, would have measured the "
                "READER. The two defects are independent and the row was defective under both"
            ),
            "what_is_published_now": (
                "the three candidates' measurements, unchanged and carried into this row, with "
                "no verdict built on top of them; and a control over the instrument that "
                "REPLACES the test - `a_rule_filed_as_a_hands_words_is_attested_outside_its_reach`"
            ),
            "the_measurements_it_carried": test_results,
            "how_the_error_was_made": (
                "⭐⭐⭐ THE ALPHABET WAS READ OFF A COPY THAT CARRIES BOTH HANDS ON THE SAME "
                "PAGES, AND IT INHERITED BOTH. The rule followed - *read every spelling off "
                "the copy rather than guessing it* - is the right rule and was obeyed. ⛔ It is "
                "simply not sufficient: reading a spelling off a copy establishes that it is "
                "ATTESTED, never that it DISCRIMINATES, and only the second is what a marker "
                "alphabet needs. ⚠ The alphabet was afterwards checked against four passages a "
                "recorder thought of, and the eight spellings that survived that check "
                "survived A SURVEY - which is evidence about the four rows the survey had"
            ),
            "what_would_have_caught_it": (
                "⛔⛔ NOT A BETTER SCORE, AND THIS IS THE PART WORTH KEEPING. The library scan "
                "- a machine reading of this work carrying NO LATIN LETTERS AT ALL - scores "
                "ZERO OF ELEVEN on the spellings that are words: a perfect pass over a "
                "rendering that cannot express English. Only the twelfth spelling, the printed "
                "asterisk, denied it a clean pass, and the asterisk is not a word and marks "
                "nothing. ⇒ THE SCORE WAS NEVER THE PROTECTION. ⭐⭐⭐ What catches it is the "
                "VERDICT SHAPE: a zero is the one measurement a broken reader produces for "
                "free, so under an absence every way a reader can fail points at a PASS, while "
                "under a presence claim they all point at REFUSING TO ANSWER"
            ),
            "what_is_armed_now": (
                "`IndependentHandAttestation` - a rule filed as a HAND's words must RESOLVE at "
                "a located place in a copy outside that hand's reach, the reach being measured "
                "on the original's script. ⛔ It carries no alphabet, so nothing can "
                "contaminate it; its errors are refusals rather than passes; and the copy that "
                "passed the retired test perfectly fails it, because it can state nothing. ⚠ It "
                "does NOT discharge `revised_printing_cannot_witness_the_unrevised_words`, "
                "which is restated as its entry condition and stands"
            ),
        }
    )
    rows.append(
        {
            "finding": "correction",
            "rule": "a_copy_that_renders_to_nothing_establishes_nothing_including_its_own_identity",
            "what_was_published": (
                "that a printing of this work held here is 219 pages of scanned page images "
                "whose rendering carries no characters, and that it therefore attests "
                "NOTHING WHATEVER, AND THAT INCLUDES ITS OWN IDENTITY - that the work, the "
                "translator and the printing were known here only from the name a host gives "
                "the file, which is a fact about a host and not about a book"
            ),
            "what_refutes_it": (
                "a public archive distributes a copy whose bytes are IDENTICAL to that one - "
                "13 905 548 bytes, SHA-1 cdf112dfa3d061658daf5e55a4c2e35337db5f5a, checked "
                "against the archive's own published manifest - together with a machine "
                "reading of it carrying 205 055 Latin letters. Its first page names the work, "
                "names the translator, and states the printing in a signed and dated "
                "foreword: the third and revised edition"
            ),
            "what_now_stands": (
                "the copy renders to nothing IN THE READER THIS REPOSITORY USED. ⭐⭐⭐ A COPY "
                "THAT RENDERS TO NOTHING IN ONE READER IS NOT A COPY THAT SAYS NOTHING, and "
                "the identity the earlier row said this copy could never attest is on its "
                "first page - never unavailable, only unread. ⚠ The blank rendering is KEPT: "
                "it remains the only honest place in this repository to hold the "
                "renders-to-nothing control, and it is now also the place to hold the "
                "sharper one - that a mute rendering is a fact about a reader"
            ),
            "what_this_does_not_change": (
                "⛔ nothing about the five rules, which resolve into a different copy and "
                "were not touched. ⛔ And nothing about WHICH PRINTING THE COPY IN HAND IS: "
                "the copy that names itself is a different copy, and the one every rule here "
                "resolves into still carries no title page, no imprint and no foreword"
            ),
        }
    )
    rows.append(
        {
            "finding": "alphabet_does_not_discriminate",
            "the_alphabet_claims_to_mark": "the second commenting hand",
            "read_off": EDITION,
            "checked_against": THIRD_EDITION,
            "spellings_searched": list(SECOND_HAND_ALPHABET),
            "material_it_must_not_mark": [
                {
                    "what_it_is": what,
                    "quoted": normalise(passage),
                    "occurrences_in_the_copy": resolve(third, passage).occurrences,
                }
                for what, passage in THE_ALPHABET_MUST_NOT_MARK
            ],
            "contaminated_spellings": contamination,
            "how_many_of_twelve": len(contamination),
            "the_instrument_refused_it": bool(alphabet_refusal),
            "the_cause_it_named": alphabet_refusal,
            "what_this_establishes": (
                "⭐⭐⭐ THE TEST WOULD HAVE REJECTED THE PRINTING IT WAS BUILT TO FIND. Four of "
                "the twelve spellings fire on material that has nothing to do with the second "
                "hand: the translator's own honorific on his own title page, the same "
                "honorific on the half-title of the translation, a phrase of the FIRST SUTRA "
                "of the work, and the machine reading's own damage. ⛔ A printing free of the "
                "second hand still contains sutra 1 and still names its translator, so "
                "*carrying none of the twelve spellings* is a condition no copy of this work "
                "can satisfy. ⇒ Three candidate printings have now failed this test in three "
                "different ways and NOT ONE of the three failures was the presence of the "
                "hand"
            ),
            "how_the_defect_got_in": (
                "⭐⭐ AN ALPHABET READ OFF A COPY THAT CARRIES TWO HANDS INHERITS BOTH OF "
                "THEM. Every spelling was read off the copy rather than guessed - which is "
                "the rule this file follows and it is the right rule - and the copy it was "
                "read off prints both hands on the same pages. ⛔ Reading off a copy "
                "establishes that a spelling is ATTESTED; it does not establish that it is "
                "DISCRIMINATING, and only the second is what a marker alphabet needs"
            ),
            "limit": (
                "⛔ discriminating against the four passages listed and against nothing else. "
                "A spelling that fires on material nobody here thought to check is a spelling "
                "this row does not catch, which is why the passages are quoted in full"
            ),
        }
    )
    rows.append(
        {
            "finding": "a_zero_is_a_property_of_the_reading_that_produced_it",
            "readings": [reading.key for reading in third_edition_readings],
            "they_are_readings_of_one_edition_because": {
                "quoted": normalise(THE_READINGS_ARE_OF_ONE_EDITION_BECAUSE),
                "occurrences_by_reading": [
                    {
                        "reading": reading.key,
                        "occurrences": resolve(
                            reading, THE_READINGS_ARE_OF_ONE_EDITION_BECAUSE
                        ).occurrences,
                    }
                    for reading in third_edition_readings
                ],
                "candidates_tried": 4,
                "why_only_one_qualifies": (
                    "⛔ the other three - the foreword sentence naming the edition, the "
                    "sutra-scoped disclaimer, and the founding sutra's own translated line - "
                    "each resolve in one or two of the three readings and not in all three. "
                    "⚠ Every one of them is on the page in all three: the readings spell them "
                    "differently"
                ),
            },
            "hits_by_spelling_by_reading": [
                {
                    "spelling": spelling,
                    "hits": [
                        {
                            "reading": reading.key,
                            "hits": reading.normalised.lower().count(
                                normalise(spelling).lower()
                            ),
                        }
                        for reading in third_edition_readings
                    ],
                }
                for spelling in SECOND_HAND_ALPHABET
            ],
            "spellings_whose_verdict_differs_between_readings": disagreement,
            "how_many_of_twelve": len(disagreement),
            "the_instrument_refused_it": bool(readings_refusal),
            "the_cause_it_named": readings_refusal,
            "what_this_establishes": (
                "⭐⭐⭐ THE SAME EDITION, READ THREE TIMES, GIVES THREE DIFFERENT ANSWERS TO "
                "THE TEST. Four of the twelve spellings flip between zero and not-zero across "
                "three machine readings of one edition - among them the second hand's own "
                "claim of a book, which is printed on the page and which two of the three "
                "readers lose. ⛔ So a CLEAN PASS on this test, had one ever been obtained, "
                "would have measured the reader and not the printing. ⚠ This is the second "
                "and independent defect: the test is unreachable by construction, and were it "
                "reachable it would not be sound"
            ),
            "limit": (
                "⛔ agreement between the three readings held, and nothing more. A fourth "
                "reader may lose a word all three of these found, so this bounds a zero "
                "rather than establishing one"
            ),
        }
    )
    rows.append(
        {
            "finding": "the_disclaimer_was_itself_revised_between_printings",
            "editions": [third.key, fifth.key],
            "the_disclaimer": [
                {
                    "edition": third.key,
                    "quoted": THIRD_EDITION_DISCLAIMER,
                    "occurrences": resolve(third, THIRD_EDITION_DISCLAIMER).occurrences,
                },
                {
                    "edition": fifth.key,
                    "quoted": FIFTH_EDITION_DISCLAIMER,
                    "occurrences": resolve(fifth, FIFTH_EDITION_DISCLAIMER).occurrences,
                },
            ],
            "the_sentence_that_contradicts_it_in_both": [
                {
                    "edition": ed_.key,
                    "quoted": THE_CONTRADICTING_SENTENCE,
                    "occurrences": resolve(ed_, THE_CONTRADICTING_SENTENCE).occurrences,
                }
                for ed_ in (third, fifth)
            ],
            "what_this_establishes": (
                "⭐⭐⭐ THE SENTENCE CLAIMING THE TRANSLATION WAS NOT ALTERED IS ITSELF ALTERED "
                "BETWEEN PRINTINGS. The third edition's signed foreword reads *I have not "
                "INTERFERED with either the translation or the notes as given by Prof. Rao*; "
                "the fifth reads *I have not MEDDLED with either the translation or the notes "
                "as given by Prof. Rao*. ⭐ And the contradiction published from the fifth "
                "edition is in the third too, six years earlier: both printings carry the "
                "disclaimer AND *The Translation herewith presented has been thoroughly "
                "revised by me*, a paragraph apart. ⇒ The contradiction is not a slip made "
                "once - it survived its author re-setting his own foreword for a new edition"
            ),
            "why_the_verb_is_probably_not_the_reader": (
                "⚠ WEIGHED, NOT ASSERTED. *Interfered* and *meddled* are not a confusion any "
                "optical reader makes. And the third edition's own rendering spells "
                "*meddled* correctly elsewhere - in the sutra-scoped disclaimer in its body - "
                "so the reader that produced *interfered* in the foreword was able to read "
                "*meddled* in the same file. ⛔ That is evidence and not proof: these are two "
                "scans as well as two readings, and nothing here separates a reviser's second "
                "thought from a compositor's"
            ),
            "what_it_does_not_establish": (
                "⛔ NOTHING ABOUT WHAT WAS ACTUALLY CHANGED IN THE TRANSLATION. A reviser's "
                "own account of what he changed is not evidence of what he changed, and that "
                "holds twice as hard for an account he revised"
            ),
        }
    )
    rows.append(
        {
            "finding": "second_printing_test",
            "asked_for_the_fourth_time": True,
            "candidate": third.key,
            "the_candidate_states_its_own_printing": {
                "quoted": THIRD_EDITION_FOREWORD,
                "occurrences": resolve(third, THIRD_EDITION_FOREWORD).occurrences,
                "corroborated_on_another_page_of_the_same_copy": {
                    "quoted": THIRD_EDITION_IMPRINT,
                    "occurrences": resolve(third, THIRD_EDITION_IMPRINT).occurrences,
                    "limit": (
                        "⚠ two pages of ONE copy. That is weaker than corroboration across "
                        "copies and is recorded as the weaker thing"
                    ),
                },
            },
            "result": third_test,
            "verdict": (
                "⛔ FAILS, and it is the third candidate to fail and the first whose failure "
                "explains the other two. It is READABLE - 205 055 Latin letters, the first "
                "candidate held here that is demonstrably legible in the script the alphabet "
                "is written in - and it carries nine of the twelve spellings. ⚠ But it names "
                "itself the THIRD REVISED EDITION and names the hand that revised it as the "
                "translator's grandson, so it stands on the same side of the standing refusal "
                "as the fifth does"
            ),
            "what_the_fourth_asking_actually_settled": (
                "⭐⭐⭐ THAT THE TEST CANNOT BE PASSED AND WOULD NOT MEAN ANYTHING IF IT WERE. "
                "See the two rows above: four of the twelve spellings mark the first hand, "
                "the primary text or the reader's own damage, so no printing of this work can "
                "score zero; and four of the twelve flip between zero and not-zero across "
                "three readings of one edition, so a zero would be a fact about a reader. "
                "⇒ The standing question is not open for want of a candidate - the "
                "instrument it was to be answered with does not measure what it was read off "
                "the copy to measure"
            ),
            "whether_an_earlier_printing_is_reachable": (
                "⛔ NOT REACHED. This copy establishes that an earlier printing EXISTED - a "
                "third edition presupposes a first - and no digitised printing earlier than "
                "this one was found. Every reachable copy of this translation carries the "
                "same second hand's foreword. ⚠ That is a statement about what was found, "
                "never about what exists"
            ),
        }
    )

    rows.append(hands.as_row())
    # ⭐⭐⭐ The finding the test was not asking for, beside the finding that it produced.
    rows.append(naming.as_row())
    rows.append(foreword.as_row())
    rows.append({"finding": "alignment", **alignment.as_json()})

    # ----------------------------------------------------------------------------------
    # ⭐⭐⭐ THE REPLACEMENT FOR THE SECOND-PRINTING TEST, TAKEN. The retired test required a
    #     ZERO over a candidate copy and no copy of this work could ever produce one. This
    #     one requires a PRESENCE, in a copy the revising hand could not have touched.
    # ----------------------------------------------------------------------------------
    #: ⛔ Only the rows filed as a HAND's words are at issue. A sutra is not attributed to a
    #: hand, so no hand's reach bears on it - and the class refuses a `translation` row.
    attestations = [
        IndependentHandAttestation(
            rule=rule["id"],
            the_rule_as_published=rule["states"],
            filed_as=rule["source_kind"],
            filed_in=edition,
            the_hand_whose_reach_is_at_issue=(
                "the second commenting hand in the printing every rule in this file resolves "
                "into - the one that names the translator in the third person, says his notes "
                "are not clear, and claims books of its own"
            ),
            the_reach_is_bounded_by=(
                "that hand's own title page in the copy that names it, which reads *Revised "
                "and Annotated by* and declares the printing the fifth. ⛔ What it worked over "
                "is THIS English translation; that it never touched any other work is not "
                "established here and is not needed"
            ),
            attested_in=second,
            the_attesting_passages=tuple(
                CORROBORATION_BY_RULE[rule["id"]][key]
                for key in ("fragment", "second_fragment")
                if key in CORROBORATION_BY_RULE[rule["id"]]
            ),
            the_locus_there=CORROBORATION_BY_RULE[rule["id"]]["locus"],
            the_original_is_written_in="devanagari",
            what_this_does_not_establish=(
                "⛔ NOT that the English words in the revised copy are the translator's. It "
                "establishes that the RULE was in the work before this hand's reach, not that "
                "any sentence is his. ⛔⛔ And not that the rule is in the sutras: the second "
                "translator is himself a modern commentator, so two copies agreeing "
                "establishes that a rule is not ONE hand's invention and nothing further. ⚠ "
                "`revised_printing_cannot_witness_the_unrevised_words` stands, undischarged"
            ),
        )
        for rule in RULES
        if rule["source_kind"] == "commentary"
    ]
    rows += [attestation.as_row() for attestation in attestations]

    # ⭐⭐⭐ THE CONTROL OVER THE INSTRUMENT THAT REPLACES THE TEST. ⛔ It is driven off its own
    #    value: the two copies that must be refused are actually OFFERED to it, and the cause
    #    each refusal names is recorded. A control that only asserts the happy path would hold
    #    just as well if every refusal had been deleted.
    def _offer(candidate) -> str:
        """Offer a copy as the attesting one and return the cause it was refused for."""
        try:
            IndependentHandAttestation(
                rule="a_tie_merges_two_places_and_the_node_fills_the_vacancy",
                the_rule_as_published="offered only to be refused",
                filed_as="commentary",
                filed_in=edition,
                the_hand_whose_reach_is_at_issue="the second commenting hand",
                the_reach_is_bounded_by="the naming copy's own title page",
                attested_in=candidate,
                the_attesting_passages=(
                    CORROBORATION_BY_RULE[
                        "a_tie_merges_two_places_and_the_node_fills_the_vacancy"
                    ]["fragment"],
                ),
                the_locus_there="adhyaya 1, pada 1",
                the_original_is_written_in="devanagari",
                what_this_does_not_establish="offered only to be refused",
            )
        except TextualError as refused:
            return str(refused)
        return ""

    refused_the_noise_copy = _offer(library_scan)
    refused_a_second_printing = _offer(fifth)
    # ⛔ And the row filed as the TEXT rather than as a hand's words - the test means nothing
    #   over a sutra, and a passing row there would read as evidence about the primary text.
    try:
        IndependentHandAttestation(
            rule=RULES[0]["id"],
            the_rule_as_published=RULES[0]["states"],
            filed_as=RULES[0]["source_kind"],
            filed_in=edition,
            the_hand_whose_reach_is_at_issue="the second commenting hand",
            the_reach_is_bounded_by="the naming copy's own title page",
            attested_in=second,
            the_attesting_passages=(CORROBORATION_BY_RULE[RULES[0]["id"]]["fragment"],),
            the_locus_there="adhyaya 1, pada 1",
            the_original_is_written_in="devanagari",
            what_this_does_not_establish="offered only to be refused",
        )
    except TextualError as refused:
        refused_a_sutra = str(refused)
    else:
        refused_a_sutra = ""

    controls += [
        {
            "finding": "control",
            "control": "a_rule_filed_as_a_hands_words_is_attested_outside_its_reach",
            "measured": {
                "rules_filed_as_a_hands_words": [
                    rule["id"] for rule in RULES if rule["source_kind"] == "commentary"
                ],
                "of_those_attested_outside_the_hands_reach": [
                    attestation.rule for attestation in attestations
                ],
                "the_attesting_copy": second.key,
                "letters_of_the_originals_script_in_the_attesting_copy": second.scripts.get(
                    "devanagari", 0
                ),
                "letters_of_it_in_the_copy_the_rules_are_filed_in": edition.scripts.get(
                    "devanagari", 0
                ),
                # ⛔⛔⛔ THE SAME COPY, THE OPPOSITE VERDICT, MEASURED RATHER THAN ARGUED.
                "the_copy_that_passed_the_retired_test": {
                    "edition": library_scan.key,
                    "spellings_that_are_words": len(
                        [s_ for s_ in SECOND_HAND_ALPHABET if scripts_in(s_)]
                    ),
                    "of_those_it_carried": library_words_only,
                    "so_the_retired_test_scored_it": "a perfect pass",
                    "and_this_instrument_refused_it_because": refused_the_noise_copy,
                },
                "a_second_printing_of_the_same_translation_was_refused_because": (
                    refused_a_second_printing
                ),
                "a_rule_filed_as_the_text_was_refused_because": refused_a_sutra,
            },
            # ⭐ Holds only while all four are true: every hand-attributed rule is attested,
            #   and each of the three copies that must be refused actually was. ⛔ Deleting any
            #   refusal makes this fail rather than quietly widening what the file may publish.
            "held": bool(
                len(attestations)
                == len([r for r in RULES if r["source_kind"] == "commentary"])
                and len(attestations) > 0
                and refused_the_noise_copy
                and refused_a_second_printing
                and refused_a_sutra
            ),
            "meaning": (
                "⭐⭐⭐ THE TEST THIS REPLACES ASKED FOR A ZERO, AND A ZERO IS THE ONE "
                "MEASUREMENT A BROKEN READER PRODUCES FOR FREE. The library scan - a machine "
                "reading of this work carrying no Latin letters at all - scores a PERFECT pass "
                "on the eleven retired spellings that are words, and is refused here - ⛔⛔ NOT "
                "because it can state nothing, which is what this row said before it was "
                "measured, but because a rendering in which nothing repeats is refused "
                "outright: quoted against itself that copy states whatever it is asked "
                "to. ⭐⭐ The two defects that retired the old test are one "
                "defect: under an absence every way a reader can fail turns a hit into a zero "
                "and a zero is a PASS, so the instrument's errors all point at success; under "
                "a presence claim they all point at refusing to answer. ⛔ And the reach "
                "condition is `revised_printing_cannot_witness_the_unrevised_words` at the "
                "door: the printing that declares itself the fifth is refused as an attesting "
                "copy, because two printings one hand revised agree about the revision. ⚠ What "
                "a passing row establishes is that the RULE predates the hand's reach - never "
                "that the English words are the translator's, and never that the rule is in "
                "the sutras"
            ),
        },
    ]

    # ======================================================================================
    # WHAT A RESOLUTION IN EACH COPY IS WORTH — measured over the copies themselves
    # ======================================================================================
    #
    # ⭐⭐⭐ Every guard this file owned before this session asks whether a copy was READ.
    # None asked what a resolution in it is WORTH, and in the library scan — a machine reading
    # that returned a quarter of a million characters of noise — resolving exactly once is
    # free. That defeats an ABSENCE (a control quoted out of the copy's own noise resolves
    # perfectly) and it defeats a PRESENCE (a passage quoted out of that same noise attests
    # whatever it is said to state).

    # ⛔⛔⛔ AND WHAT THAT FLOOR IS WORTH ON A COPY SMALLER THAN THE ONES IT WAS FITTED TO.
    #    Each copy is tiled into consecutive disjoint blocks and the floor is asked of every
    #    block — complete coverage, no sample — because a bound arrived at by eye is a bound
    #    nobody can re-measure. ⚠ The grid is published with the result: a grid nobody states
    #    reads as a continuum, and the answer is the smallest point ON it.
    TILED_AT = (
        200, 300, 500, 1000, 2000, 3000, 4000, 5000,
        6000, 7000, 8000, 9000, 10000, 12000, 15000, 20000,
    )

    # ⛔⛔⛔ AND THE TILING IS A SAMPLE OF THE SPECIMENS, WHICH IS HOW THIS BOUND WAS WRONG BY
    #    1 686 CHARACTERS FOR A SESSION. `blocks_this_floor_refuses` is complete over a copy's
    #    CHARACTERS and reads one phase of its WINDOWS — 283 of 1 675 741 at six thousand.
    #    The extent is an existential question about specimens of real text, so it is asked of
    #    every window, at every offset. ⭐ Both grids are published: the tiled one because the
    #    old table was measured with it and a reader must be able to reproduce that, the
    #    window one because it is the measurement the constant now rests on.
    WINDOWED_AT = (
        200, 300, 314, LEAST_EXTENT_AN_ACCEPTANCE_DISCRIMINATES_AT, 500, 1000, 2000, 5000,
        6000, 7000, 7685, LEAST_EXTENT_A_REFUSAL_DISCRIMINATES_AT, 8000, 10000, 20000,
    )
    assert LEAST_EXTENT_A_REFUSAL_DISCRIMINATES_AT in WINDOWED_AT
    assert LEAST_EXTENT_AN_ACCEPTANCE_DISCRIMINATES_AT in WINDOWED_AT

    recurrence_by_copy = [
        recurrence_of(copy)
        for copy in (
            edition,
            second,
            fifth,
            third,
            *third_edition_readings[1:],
            library_scan,
        )
    ]
    noise_recurrence = recurrence_of(library_scan)
    real_recurrences = [
        row for row in recurrence_by_copy if row["edition"] != library_scan.key
    ]
    lowest_real = min(row["share_that_recurs"] for row in real_recurrences)

    _real_copies = (edition, second, fifth, third, *third_edition_readings[1:])
    tiled = {
        block: (
            [blocks_this_floor_refuses(copy, block=block) for copy in _real_copies],
            blocks_this_floor_refuses(library_scan, block=block),
        )
        for block in TILED_AT
    }
    # ======================================================================================
    # ⚠ THREE CONSTANTS, ONE SET OF COPIES - MEASURED AGAINST TEXT THEY WERE NOT FITTED TO
    # ======================================================================================
    #
    # ⭐⭐⭐ The fragment length (12), the floor (0.01) and the refusing extent (7 686) were
    #    every one of them fitted to the same seven renderings, and a copy disagreeing with
    #    all three would look exactly like a copy disagreeing with none. That is an argument,
    #    and the answer to an argument about a constant is a HELD-OUT MEASUREMENT.
    #
    # ⛔ These four bodies were used to fit nothing. The first is a second real book of this
    #    genre this repository holds and this generator has never loaded; the rest are this
    #    repository's own prose and program text - a different language, a different register
    #    and a different way of being produced. ⚠ Together they are still not a sample of
    #    renderings in general, and they are what is available.
    held_out: list[tuple[str, str, str]] = [
        (
            "a_second_real_book_never_loaded_by_this_generator",
            "a machine reading of an English translation of a different work of this genre",
            load(BPHS_SANTHANAM, cache=args.cache).normalised,
        ),
        (
            "the_licence_this_repository_is_published_under",
            "English legal prose, produced by neither this repository nor a machine reading",
            normalise(Path("LICENSE").read_text(encoding="utf-8")),
        ),
        (
            "this_repositorys_own_readme",
            "English technical prose, the smallest held-out body and the closest to the floor",
            normalise(Path("README.md").read_text(encoding="utf-8")),
        ),
        (
            "this_repositorys_own_program_text",
            "Python, which is not a natural language at all",
            normalise(
                "\n".join(
                    path.read_text(encoding="utf-8")
                    for path in sorted(Path("src/saakshi").glob("*.py"))
                )
            ),
        ),
    ]

    def _as_edition(key: str, body: str) -> Edition:
        """⛔ Wrapped so the SAME instruments measure it - not a second implementation."""
        return Edition(
            key=key,
            identity="held out from the fitting of every constant below",
            language="und",
            witness=Witness(
                address="held in this repository",
                retrieved=today(),
                http_status=200,
                copy_sha256=digest(body),
                copy_bytes=len(body.encode("utf-8")),
            ),
            rendering=Rendering(
                kind="transcription",
                produced_by="this repository",
                sha256=digest(body),
                characters=len(body),
            ),
            extent={"describes": "the whole of it", "complete": True},
            text=body,
        )

    HELD_OUT_LENGTHS = (6, 8, 10, 12, 16, 20, 24)
    held_out_rows = []
    for key, what_it_is, body in held_out:
        copy = _as_edition(key, body)
        by_length = {
            length: recurrence_of(copy, length=length)["share_that_recurs"]
            for length in HELD_OUT_LENGTHS
        }
        # ⚠ As rows rather than a map keyed by an integer: the fixture contract refuses a
        #   non-string key, and a key a reader has to parse is not a field either.
        by_length_rows = [
            {"fragment_length": length, "share_that_recurs": by_length[length]}
            for length in HELD_OUT_LENGTHS
        ]
        # ⛔ The extent this copy would put on the refusing bound, on its own: the largest
        #    extent on the published grid at which any window of IT is still refused.
        refused_up_to = 0
        for extent in WINDOWED_AT:
            measured = every_window_of(copy, extent=extent)
            if measured["windows"] and measured["windows_refused"]:
                refused_up_to = extent
        held_out_rows.append(
            {
                "body": key,
                "what_it_is": what_it_is,
                "characters": copy.searchable_characters,
                "share_that_recurs_by_fragment_length": by_length_rows,
                "at_the_fitted_length": by_length[RECURRENCE_MEASURED_AT],
                "how_far_above_the_fitted_floor": round(
                    by_length[RECURRENCE_MEASURED_AT] / LEAST_RECURRENCE, 2
                ),
                "clears_the_fitted_floor": (
                    by_length[RECURRENCE_MEASURED_AT] >= LEAST_RECURRENCE
                ),
                "largest_extent_at_which_a_window_of_it_is_refused": refused_up_to,
                "inside_the_fitted_extent": (
                    refused_up_to < LEAST_EXTENT_A_REFUSAL_DISCRIMINATES_AT
                ),
            }
        )

    windowed = {
        extent: (
            [every_window_of(copy, extent=extent) for copy in _real_copies],
            every_window_of(library_scan, extent=extent),
        )
        for extent in WINDOWED_AT
    }
    # ⛔ The two instruments disagree, and by how much is the finding. Measured, not quoted.
    phase_vs_window = {
        "extent": 6000,
        "blocks_the_tiling_reads": sum(row["blocks"] for row in tiled[6000][0]),
        "windows_the_copies_contain": sum(row["windows"] for row in windowed[6000][0]),
        "blocks_the_tiling_refuses": sum(row["blocks_refused"] for row in tiled[6000][0]),
        "windows_refused": sum(row["windows_refused"] for row in windowed[6000][0]),
    }
    phase_vs_window["share_of_the_specimens_the_tiling_read"] = round(
        phase_vs_window["blocks_the_tiling_reads"]
        / phase_vs_window["windows_the_copies_contain"],
        6,
    )

    # ⛔ Driven off its own value: the copy that must be refused is OFFERED to every
    #    instrument that reasons from a resolution, and the cause each names is recorded.
    #    ⚠ A control listing only the happy path would hold just as well with every guard
    #    deleted — and eight of these nine guards did not exist a day ago.
    noise = library_scan.normalised
    # ⛔⛔ A SLICE OF THIS COPY IS OFTEN PUNCTUATION AND DIGITS, AND AN ALPHABET OF THOSE IS
    #    REFUSED FOR BEING WRITTEN IN NO SCRIPT - an earlier cause, which is the right one for
    #    that alphabet and the WRONG one for this control. ⭐ The offer below must reach the
    #    guard it is measuring, so the spelling offered carries letters of the copy's script.
    noise_letters = next(
        noise[at : at + 12]
        for at in range(len(noise) - 12)
        if "devanagari" in scripts_in(noise[at : at + 12])
    )

    def _cause(build) -> str:
        try:
            build()
        except TextualError as refused:
            return str(refused)
        return ""

    offered_the_noise_copy = {
        "an_absence_over_the_work": _cause(
            lambda: AbsenceSearch(
                claim="offered only to be refused",
                alphabet=("नियम",),
                edition=library_scan,
                occurrences=[],
                what_the_hits_do_say=[],
                positive_control=noise[300:360],
            )
        ),
        "an_absence_over_a_bounded_passage": _cause(
            lambda: PassageAbsence(
                claim="offered only to be refused",
                edition=library_scan,
                passage_label="somewhere in the noise",
                after=noise[100:130],
                before=noise[400:430],
                alphabet=(noise_letters,),
                alphabet_read_from="read off this copy, which is the whole trouble",
            )
        ),
        "an_attestation_outside_a_hands_reach": refused_the_noise_copy,
        "an_absence_checked_against_a_second_reader": _cause(
            lambda: AbsenceAcrossReadings(
                claim="offered only to be refused",
                alphabet=("नियम",),
                readings=(library_scan, third),
                the_readings_are_of_one_edition_because=noise[500:540],
            )
        ),
        "a_second_hand_established_from_located_passages": _cause(
            lambda: SecondHand(
                edition=library_scan,
                the_notes_are_credited_to="the translator",
                speaks_of_the_translator_in_the_third_person=(noise[100:140],),
                claims_work_of_its_own=(),
                marked_by=("*",),
                named_within_this_copy=False,
            )
        ),
        "a_hand_named_in_another_copy": _cause(
            lambda: NamedInAnotherCopy(
                the_hand="offered only to be refused",
                unnamed_in=edition,
                named_in=library_scan,
                the_name_as_that_copy_prints_it=noise[50:70],
                the_passage_that_names_it=noise[40:90],
                the_printing_that_copy_declares=noise[600:640],
                tied_to_the_unnamed_hand_by=(RULES[0]["fragment"],),
                what_this_does_not_establish="offered only to be refused",
            )
        ),
        "the_copy_a_hand_is_said_NOT_to_be_named_in": _cause(
            lambda: NamedInAnotherCopy(
                the_hand="offered only to be refused",
                unnamed_in=library_scan,
                named_in=fifth,
                the_name_as_that_copy_prints_it=THE_NAME_AS_THAT_COPY_PRINTS_IT,
                the_passage_that_names_it=FIFTH_EDITION_NAMES_THE_HAND,
                the_printing_that_copy_declares=FIFTH_EDITION_IMPRINT,
                tied_to_the_unnamed_hand_by=(THE_TIE_BETWEEN_THE_TWO_COPIES,),
                what_this_does_not_establish="offered only to be refused",
            )
        ),
        "a_copy_that_disagrees_with_itself": _cause(
            lambda: SelfContradiction(
                edition=library_scan,
                the_hand="offered only to be refused",
                statements=(("one thing", noise[300:340]), ("another", noise[400:440])),
                why_they_cannot_both_be_relied_on="offered only to be refused",
                what_it_settles="offered only to be refused",
            )
        ),
        "an_alphabet_checked_for_discrimination": _cause(
            lambda: MarkerAlphabet(
                marks="offered only to be refused",
                alphabet=("नियम",),
                edition=library_scan,
                must_not_mark=(("the text", noise[200:240]),),
            )
        ),
    }
    refused_for_the_copy = {
        where: cause
        for where, cause in offered_the_noise_copy.items()
        if "NOTHING IN THIS COPY REPEATS" in cause
    }
    print(
        f"offered the rendering of noise to {len(offered_the_noise_copy)} instrument(s); "
        f"{len(refused_for_the_copy)} refused it for the copy"
    )
    # ⛔ A count that does not name what it dropped reads as complete coverage.
    for where in offered_the_noise_copy.keys() - refused_for_the_copy.keys():
        print(f"  ⛔ NOT refused for the copy: {where} -> {offered_the_noise_copy[where][:200]!r}")

    controls += [
        {
            "finding": "control",
            "control": "resolving_exactly_once_is_free_in_a_rendering_that_repeats_nothing",
            "measured": {
                "fragment_length": RECURRENCE_MEASURED_AT,
                "the_floor_a_copy_must_clear": LEAST_RECURRENCE,
                "by_copy": recurrence_by_copy,
                "the_rendering_of_noise": noise_recurrence["share_that_recurs"],
                "the_lowest_real_copy_held": lowest_real,
                "the_margins": {
                    "how_far_the_lowest_real_copy_stands_above_the_floor": round(
                        lowest_real / LEAST_RECURRENCE, 2
                    ),
                    "how_far_the_rendering_of_noise_stands_below_it": round(
                        LEAST_RECURRENCE / noise_recurrence["share_that_recurs"], 2
                    ),
                },
                "the_length_and_the_floor_are_a_pair": (
                    "⛔ measured: at SIX characters the rendering of noise recurs at 0.051 and "
                    "this same floor would pass it. At eight to twenty characters it sits "
                    "below every real copy held, by 30x at eight and 1 900x at twenty. ⚠ So "
                    "the floor is fitted to the copies held - seven renderings, one of them "
                    "noise - and is not a law about renderings"
                ),
            },
            # ⭐ Both halves. A guard that only forbids cannot tell an empty subject from a
            #   clean one, so the accepting side is asserted too — including the real book
            #   printed in the very script the rendering of noise is written in.
            "held": bool(
                noise_recurrence["share_that_recurs"] < LEAST_RECURRENCE
                and all(row["share_that_recurs"] > LEAST_RECURRENCE for row in real_recurrences)
                and len(real_recurrences) >= 6
                and second.scripts.get("devanagari", 0) > 0
            ),
            "meaning": (
                "⭐⭐⭐ LANGUAGE REPEATS AND A RENDERING OF NOISE DOES NOT. In the library "
                "scan 44 of 246 689 distinct twelve-character fragments recur, so every "
                "fragment of it resolves EXACTLY ONCE - the condition this file leans on "
                "hardest, satisfied by a copy that says nothing at all. ⛔ Every real copy "
                "held recurs at 0.068 or above, INCLUDING a real book printed in the same "
                "script as the noise, so what separates them is language rather than script. "
                "⚠ This control holds only while the rendering of noise stays below the floor "
                "and every real copy above it; either crossing means the floor has stopped "
                "describing the copies it was drawn from"
            ),
        },
        {
            "finding": "control",
            "control": "every_instrument_that_reasons_from_a_resolution_refuses_the_noise_copy",
            "measured": {
                "offered": len(offered_the_noise_copy),
                "refused_naming_the_copy": len(refused_for_the_copy),
                "the_cause_each_named": [
                    {"where_it_was_offered": where, "refused_because": cause}
                    for where, cause in offered_the_noise_copy.items()
                ],
                "and_the_same_instruments_accepted_the_real_copies": {
                    "rules_attested_outside_a_hands_reach": len(attestations),
                    "the_attesting_copy": second.key,
                    "its_recurrence": recurrence_of(second)["share_that_recurs"],
                    "why_this_half_is_here": (
                        "⛔ a guard that only FORBIDS cannot tell an empty subject from a "
                        "clean one. Nine refusals prove nothing without a row this "
                        "instrument still writes"
                    ),
                },
            },
            "held": bool(
                len(refused_for_the_copy) == len(offered_the_noise_copy)
                and len(offered_the_noise_copy) == 9
                and len(attestations) > 0
            ),
            "meaning": (
                "⭐⭐⭐ ONE DEFECT, NINE RESOLUTIONS, EIGHT INSTRUMENTS - and the count is the "
                "control. Each is offered the copy and each must refuse it naming the COPY, "
                "not the alphabet, the vocabulary or the extent. ⛔ Measured by disarming "
                "every guard in turn: eight of the nine were caught by the suite and the "
                "ninth was not - the copy a hand is said NOT to be named in had no case "
                "measuring it, so its guard could have been deleted in silence. ⚠ A fix "
                "written for one cause is not a fix; this file has now made that mistake "
                "three times over the same copy"
            ),
        },
        {
            "finding": "control",
            "control": "below_a_measured_extent_this_floor_refuses_real_books_too",
            "measured": {
                "the_extent_a_refusal_discriminates_at": (
                    LEAST_EXTENT_A_REFUSAL_DISCRIMINATES_AT
                ),
                "the_extent_an_acceptance_discriminates_at": (
                    LEAST_EXTENT_AN_ACCEPTANCE_DISCRIMINATES_AT
                ),
                # ⭐⭐⭐ EVERY WINDOW, AT EVERY OFFSET - the measurement both bounds rest on.
                "by_extent": [
                    {
                        "extent": extent,
                        "real_copies": {
                            "windows": sum(row["windows"] for row in windowed[extent][0]),
                            "windows_refused": sum(
                                row["windows_refused"] for row in windowed[extent][0]
                            ),
                            "refused_regions": sum(
                                row["refused_regions"] for row in windowed[extent][0]
                            ),
                        },
                        "the_rendering_of_noise": {
                            "windows": windowed[extent][1]["windows"],
                            "windows_that_cleared_the_floor": (
                                windowed[extent][1]["windows_cleared"]
                            ),
                        },
                        "by_copy": windowed[extent][0] + [windowed[extent][1]],
                    }
                    for extent in WINDOWED_AT
                ],
                "measured_over": (
                    "every window of each extent in each copy, at every starting offset - "
                    "not a tiling phase. ⚠ The windows overlap, so a refused count is not a "
                    "rate; the count of maximal refused REGIONS is published beside it"
                ),
                # ⛔⛔⛔ THE DEFECT THAT MOVED THIS CONSTANT, MEASURED RATHER THAN DESCRIBED.
                "what_the_tiling_this_was_first_read_off_actually_saw": phase_vs_window,
                "the_tiled_table_as_it_was_published": [
                    {
                        "block_characters": block,
                        "real_copies": {
                            "blocks": sum(row["blocks"] for row in tiled[block][0]),
                            "blocks_refused": sum(
                                row["blocks_refused"] for row in tiled[block][0]
                            ),
                        },
                        "the_rendering_of_noise": {
                            "blocks": tiled[block][1]["blocks"],
                            "blocks_refused": tiled[block][1]["blocks_refused"],
                        },
                    }
                    for block in TILED_AT
                ],
                "why_both_grids_are_here": (
                    "⛔ the tiled one is what this constant was first read off, and it said "
                    "6 000. It is complete over each copy's CHARACTERS and reads one phase of "
                    "its WINDOWS - at six thousand characters, 283 of 1 675 741 of them. ⭐⭐⭐ "
                    "A MEASUREMENT CAN BE COMPLETE OVER WHAT IT COUNTS AND A SAMPLE OF WHAT IT "
                    "IS ABOUT. It is kept so a reader can reproduce the published table and "
                    "see the two disagree"
                ),
                "and_it_is_not_a_threshold": (
                    "⛔⛔ the refused count is NOT monotone in the extent: 7 450 refuses "
                    "nothing, 7 500 refuses 42, 7 550 nothing, 7 650 refuses 36. So *the "
                    "smallest extent at which nothing is refused* - the rule 6 000 was picked "
                    "by - is not a bound. What is published is the SUPREMUM, 7 685, checked at "
                    "every extent to 7 780, every ten to 8 800 and every five hundred to 30 000"
                ),
                "the_accepting_side_is_now_armed": (
                    "✅ and its bound is its own: the largest extent at which any window of "
                    "the rendering of noise CLEARS this floor is 314, three of 286 fragments "
                    "coming round twice for a share of 0.01049. ⛔⛔⛔ THIS SIDE WENT A SESSION "
                    "UNARMED ON THE OTHER SIDE'S NUMBER - the reason published was that "
                    "refusing every copy under six thousand characters would refuse every "
                    "fixture the suite is built from, which is true and is about the REFUSING "
                    "bound. ⭐ Between 315 and 7 686 a pass means something and a failure does "
                    "not, and neither constant alone describes that band"
                ),
                "what_is_fitted_here": (
                    "⚠ both extents, exactly as the floor is. The refusing one to the six "
                    "real renderings held; the accepting one to ONE copy, the single rendering "
                    "of noise, which makes it the weaker of the two numbers"
                ),
            },
            # ⭐ BOTH HALVES AND BOTH SIDES. The effect must be SHOWN to exist at a small
            #   extent, the bound must hold at the bound, and the accepting side must be shown
            #   to fail below ITS bound - or three constants have nothing under them.
            "held": bool(
                sum(row["windows_refused"] for row in windowed[200][0]) > 0
                and sum(row["windows_refused"] for row in windowed[6000][0]) > 0
                and sum(row["windows_refused"] for row in windowed[7685][0]) == 1
                and sum(
                    row["windows_refused"]
                    for row in windowed[LEAST_EXTENT_A_REFUSAL_DISCRIMINATES_AT][0]
                )
                == 0
                and all(
                    sum(row["windows_refused"] for row in windowed[extent][0]) == 0
                    for extent in WINDOWED_AT
                    if extent >= LEAST_EXTENT_A_REFUSAL_DISCRIMINATES_AT
                )
                # ⛔ The accepting side: noise clears below its bound and never at or above it.
                and windowed[300][1]["windows_cleared"] > 0
                and windowed[314][1]["windows_cleared"] > 0
                and all(
                    windowed[extent][1]["windows_cleared"] == 0
                    for extent in WINDOWED_AT
                    if extent >= LEAST_EXTENT_AN_ACCEPTANCE_DISCRIMINATES_AT
                )
                # ⛔⛔ And the tiling must still disagree, or the finding has evaporated.
                and phase_vs_window["blocks_the_tiling_refuses"] == 0
                and phase_vs_window["windows_refused"] > 0
                and len(windowed[200][0]) >= 6
            ),
            "meaning": (
                "⭐⭐⭐ A FLOOR FITTED ON WHOLE BOOKS WAS APPLIED TO COPIES OF ANY SIZE, AND "
                "BELOW A MEASURED EXTENT IT IS A TEST OF SIZE RATHER THAN OF LANGUAGE. Asked "
                "of every window of two hundred characters, this floor refuses 1 405 161 of "
                "1 710 541 windows of the real books held here - with the cause `it is a "
                "machine reading that returned noise`, which nothing had measured. ⛔⛔⛔ AND "
                "THE BOUND PUT ON THAT LAST SESSION WAS ITSELF READ OFF A SAMPLE: 6 000 was "
                "the smallest TILING at which no block is refused, and the tiling reads one "
                "phase of the windows - 0.017 % of them at that extent. Asked of every window, "
                "6 000 refuses 5 593 and the supremum is 7 685. ⭐⭐⭐ THE WORD `COMPLETE` WAS "
                "TRUE OF THE WRONG NOUN. ⛔⛔ The fixture standing in for the rendering of "
                "noise had been grown to 7 199 characters to clear the old bound, so the "
                "moment the bound moved every test certifying `the instruments refuse the "
                "copy of noise` was AGAIN certifying a refusal its SIZE had earned - the third "
                "session running that this repository's own test bed was the subject. ✅ And "
                "the accepting side is now armed at 314, its own measured bound, which is 24x "
                "smaller than the refusing one and was never the six thousand it was left "
                "unarmed for"
            ),
        },
    ]

    lowest_fitted = min(row["share_that_recurs"] for row in real_recurrences)
    lowest_held_out = min(row["at_the_fitted_length"] for row in held_out_rows)
    controls += [
        {
            "finding": "control",
            "control": "the_three_constants_measured_against_text_they_were_not_fitted_to",
            "measured": {
                "the_three": {
                    "fragment_length": RECURRENCE_MEASURED_AT,
                    "the_floor": LEAST_RECURRENCE,
                    "the_extent_a_refusal_discriminates_at": (
                        LEAST_EXTENT_A_REFUSAL_DISCRIMINATES_AT
                    ),
                    "what_they_share": (
                        "⚠ all three were fitted to the SAME seven renderings, so a copy "
                        "disagreeing with all three would look exactly like a copy "
                        "disagreeing with none. ⛔ That is an argument about a constant, and "
                        "what answers it is a held-out measurement rather than a paragraph"
                    ),
                },
                "held_out_bodies": held_out_rows,
                "the_margin_on_the_floor": {
                    "lowest_of_the_fitted_copies": lowest_fitted,
                    "lowest_of_the_held_out_bodies": lowest_held_out,
                    "how_far_the_fitted_set_overstates_it": round(
                        lowest_fitted / lowest_held_out, 2
                    ),
                    "what_that_means": (
                        "⭐ the floor TRANSFERS - every held-out body clears it - and the "
                        "headroom is smaller off the fitted set than on it. A margin read "
                        "off the seven alone is the optimistic one"
                    ),
                },
                "the_extent_off_the_fitted_set": {
                    "largest_by_body": [
                        {
                            "body": row["body"],
                            "largest_extent_at_which_a_window_of_it_is_refused": row[
                                "largest_extent_at_which_a_window_of_it_is_refused"
                            ],
                        }
                        for row in held_out_rows
                    ],
                    "the_fitted_bound": LEAST_EXTENT_A_REFUSAL_DISCRIMINATES_AT,
                    "what_that_means": (
                        "⭐ no held-out body pushes the refusing extent up: each is refused "
                        "up to a smaller extent than the six fitted copies are, so on this "
                        "evidence the bound is not tight and it transfers"
                    ),
                },
                "what_this_does_NOT_measure": (
                    "⛔⛔⛔ THE ACCEPTING SIDE IS STILL FITTED TO ONE COPY AND NOTHING HELD "
                    "OUT TOUCHES IT. Every body here is language, so every one of them speaks "
                    "to the floor and to the refusing extent and NONE of them speaks to 314 - "
                    "the bound that says a pass under it is free. ⚠ A second rendering of "
                    "noise is the measurement that would, and this repository holds one "
                    "rendering of noise. ⛔ Nor is any of these a copy in a third script, or "
                    "a machine reading produced by a different reader"
                ),
            },
            # ⭐ BOTH DIRECTIONS. Every held-out body must clear the floor AND the rendering
            #   of noise must still fail it - a control that only checked the held-out side
            #   would pass with the floor set to zero.
            "held": bool(
                all(row["clears_the_fitted_floor"] for row in held_out_rows)
                and all(row["inside_the_fitted_extent"] for row in held_out_rows)
                and len(held_out_rows) >= 4
                and noise_recurrence["share_that_recurs"] < LEAST_RECURRENCE
                and lowest_held_out > LEAST_RECURRENCE
            ),
            "meaning": (
                "⭐⭐⭐ ON THE HELD-OUT EVIDENCE ALL THREE CONSTANTS TRANSFER, AND THE FITTED "
                "SET IS THE FLATTERING ONE. Four bodies used to fit nothing - a second real "
                "book of this genre, this repository's licence, its documentation and its own "
                "program text - clear the floor at the fitted fragment length and are refused "
                "only at extents smaller than the fitted bound. ⛔ But the closest of them "
                "stands at 4.8x the floor where the lowest FITTED copy stands at 6.8x, so a "
                "margin read off the seven alone overstates the headroom by a third. ⛔⛔⛔ "
                "AND THE ACCEPTING BOUND IS UNTOUCHED BY ANY OF THIS: every held-out body is "
                "language, and the constant that says a pass under 315 characters is free was "
                "fitted to the ONE rendering of noise this repository holds. That is the "
                "weakest number in this file and nothing here strengthens it"
            ),
        },
    ]

    rows.append(
        {
            "finding": "correction",
            "rule": "a_reader_cannot_manufacture_the_evidence_of_a_presence",
            "what_was_published": (
                "on the row attesting a rule outside one hand's reach, as its stated limit: "
                "that a reader can destroy the evidence of a presence but cannot manufacture "
                "it, so a presence found in ONE reading needs no second reader - the "
                "asymmetry the whole replacement of the second-printing test rests on"
            ),
            "what_refutes_it": (
                "⛔⛔⛔ A READER THAT RETURNS NOISE MANUFACTURES ONE. In the library scan held "
                "here, 44 of 246 689 distinct twelve-character fragments recur, so a passage "
                "quoted out of that copy's own noise resolves EXACTLY ONCE, carries fifteen "
                "letters of the original's script, clears the passage-length floor - and "
                "attested a rule nobody has ever stated, in a row the instrument constructed "
                "without complaint. ⭐ Measured by offering it: the row was built, and it is "
                "the copy the retired test scored a perfect pass"
            ),
            "what_is_published_now": (
                "the same asymmetry, with the condition it was resting on stated: a reader "
                "that LOSES text cannot manufacture a presence; a reader that returns NOISE "
                "does. ⇒ What stands in the second reader's place is the attesting copy's own "
                "recurrence, published on every attestation row, and the instrument refuses a "
                "copy below the floor rather than reporting one"
            ),
            "how_the_error_was_made": (
                "⭐⭐⭐ THE VERDICT SHAPE WAS TREATED AS THE WHOLE PROTECTION. The previous "
                "session established that a zero is the one measurement a broken reader "
                "produces for free, and concluded that a PRESENCE therefore needs no guard "
                "against a broken reader. ⛔ *Broken* was read as *loses text*, which is one "
                "of the two ways a machine reading fails and not the one this repository "
                "already held a copy of. A reader that INVENTS text answers every question "
                "exactly once, and it answers a presence as readily as an absence"
            ),
            "what_would_have_caught_it": (
                "⛔ nothing in the suite, and that is the finding underneath this one: every "
                "copy built in the test file repeated nothing, which is the property of the "
                "rendering of noise itself. ⇒ The fixtures had the defect, so no test written "
                "against them could refuse it. ⭐ A fixture standing in for a book now repeats "
                "like one, and the census that offers the noise copy to every instrument is "
                "tied to the module's own count of guarded resolutions"
            ),
        }
    )

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

    header = build_header(
        script, edition, second, scanned, fifth, library_scan, len(RULES), refusals, controls
    )
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
