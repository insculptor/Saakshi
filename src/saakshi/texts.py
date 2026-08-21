"""The copies this repository resolves a locus into, and how each one got here.

⛔ **Acquiring a copy and emitting a fixture are two acts, and this module keeps them
apart.** Acquisition goes to the network and is dated; emission reads what is already on
disk and must produce the same bytes on every run. A generator that fetched at emit time
would stamp today's date on a copy obtained months ago, and would make an artifact that
cannot be regenerated without the network — so `acquire()` is a separate entry point and
`load()` refuses rather than reaching for one.

⛔ **No copy is committed.** These are somebody else's texts; the cache directory is ignored
by this repository, and what travels is the fixture — which quotes only what its citations
need. ⚠ Nor does any path to a copy reach a fixture: the writer refuses an absolute path in
any value, and the relative one is an accident of this machine's layout rather than evidence.

⚠ **Two of the three copies here are English translations whose renderings contain no
Sanskrit at all** — measured, at zero code points in the script, in both. A locus into the
original is not resolvable in either, and the generators record that as a refusal rather
than citing a translation as though it were the text.

⛔ **The third copy breaks that sentence, and it is worth saying how.** It carries the
sutras in their own script — measured, at some three hundred thousand code points — so the
presence check that stood for *"no primary text is reachable here"* now answers yes. ⚠ It is
still not a copy a locus into the original may be resolved against: the same machine reading
that captured the Hindi commentary cleanly damaged the sutra lines themselves, and the
conventionally transmitted wording of the one sutra checked occurs in it **zero** times
while a misspelled form occurs once. ⭐ *Presence of a script is not fidelity of a script* —
so the generators ask both questions and record them separately.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping

from .acquisition import AcquisitionError, retrieve
from .textual import Edition, Rendering, Witness, digest, measured_extent, normalise

#: ⚠ Relative to the repository root, and git-ignored. ⛔ Never written into a fixture.
CACHE = Path("cache") / "textual"

#: Pinned, because the extraction is part of the rendering and a different extractor is a
#: different document. Recorded on every rendering it produces.
_PDF_EXTRACTOR = "pypdf"


@dataclass(frozen=True)
class Source:
    """A copy this repository knows how to obtain, render and measure the extent of."""

    key: str
    identity: str
    language: str
    address: str
    filename: str
    rendering_kind: str
    #: Payload bytes to searchable text. ⚠ Named, versioned and recorded.
    render: Callable[[bytes], tuple[str, str]]
    extent: Callable[[str], dict[str, Any]]


def _plain_text(payload: bytes) -> tuple[str, str]:
    """A published text file, already text. The producer of the rendering is the publisher."""
    return payload.decode("utf-8", errors="replace"), (
        "the distributor of the scan; this repository decoded the published text file and "
        "did not itself read any page"
    )


def _pdf_text_layer(payload: bytes) -> tuple[str, str]:
    """The text a PDF itself carries, extracted page by page in order."""
    import pypdf

    reader = pypdf.PdfReader(_BytesIO(payload))
    pages = [(page.extract_text() or "") for page in reader.pages]
    return "\n".join(pages), f"{_PDF_EXTRACTOR} {pypdf.__version__}"


def _BytesIO(payload: bytes):  # noqa: N802 - kept local so the import stays at the edge
    import io

    return io.BytesIO(payload)


# --------------------------------------------------------------------------------------
# The two copies
# --------------------------------------------------------------------------------------

#: ⛔ The markers are the copy's OWN internal boundaries, not a table of contents and not a
#: title. A title claims; a boundary marker is printed where the material actually ends.
_ORDINALS = ("First", "Second", "Third", "Fourth")

_JAIMINI_PADAS = tuple(
    (
        f"adhyaya {adhyaya_n}, pada {pada_n}",
        (
            f"End of {pada} Pada of the {adhyaya} Adhyaya",
            f"End of {pada} Pada of {adhyaya} Adhyaya",
        ),
    )
    for adhyaya_n, adhyaya in enumerate(_ORDINALS[:2], start=1)
    for pada_n, pada in enumerate(_ORDINALS, start=1)
)

_BPHS_CHAPTERS = tuple(
    (f"chapter {n}", (f"Chapter {n}.",)) for n in (66, 67, 68, 69)
)

#: ⚠ The closing formula this copy prints is the same sentence every time, and the machine
#: reading damaged it differently at every occurrence. So each pada is looked for in the
#: spelling the copy actually carries, transcribed with its defects intact - `पावः` for
#: `पादः`, `श्रथश्लाध्यायस्थ` for `प्रथमाध्यायस्य`, and so on. ⛔ Repairing one to a form the
#: copy does not contain would make an extent resolve against a document that exists only
#: here.
#:
#: ⛔⛔ **EVERY SPELLING HERE WAS READ OFF THE COPY. THE ONES THAT WERE GUESSED WERE WRONG,
#: AND THE WRONGNESS LOOKED EXACTLY LIKE A FINDING ABOUT THE COPY.** Three detectors were
#: run over this one file and each measured a different extent - one keyed on the author's
#: name found 9, one keyed on the word for a division found 10, one keyed on the closing
#: verb found 12 - and each miss was a different corruption of the same sentence. ⭐ The
#: union is 14, so the first measurement would have published *"six divisions not found"* as
#: a fact about the book when it was a fact about a regular expression. ⇒ *A walker that
#: knows one carrying form has measured the wrong subject*, and an extent is a **lower
#: bound** unless something establishes that the alphabet is complete. Nothing here does.
#:
#: ⚠ Two padas are not listed. One - the fourth of the third adhyaya - no detector located
#: at all. The other is a closing that IS printed, and is left out on purpose: the
#: digitiser's page footer landed inside it and destroyed the words naming which pada it
#: ends. ⛔ Its position between two located neighbours would settle it, and position is not
#: what a boundary marker is for: a boundary that cannot say what it bounds establishes
#: nothing, and inferring its identity would be the recorder deciding rather than reading.
_MISHRA_PADAS = (
    ("adhyaya 1, pada 1", ("प्रथमाध्याये प्रथम: पादः",)),
    ("adhyaya 1, pada 2", ("श्रथश्लाध्यायस्थ द्वितीयः पादः",)),
    ("adhyaya 1, pada 3", ("प्रथमाध्यायस्य तृतीयः पादः",)),
    ("adhyaya 1, pada 4", ("प्रयभाध्यायस्य चतुर्थ पावः",)),
    ("adhyaya 2, pada 1", ("हि तीयाध्यायस्य प्रथमः पादः",)),
    ("adhyaya 2, pada 2", ("द्वितीयाध्यायस्य हितीयः पादः",)),
    ("adhyaya 2, pada 3", ("द्वितीयाध्यायस्य तृतीयः पादः",)),
    ("adhyaya 2, pada 4", ("हितीयाष्ययास्य चतुर्थः पादः",)),
    ("adhyaya 3, pada 1", ("तृतीयाध्यायस्य प्रथमपाद:",)),
    ("adhyaya 3, pada 2", ("तृतीयाध्यायस्य द्वितीय: पादः",)),
    ("adhyaya 3, pada 3", ("तृती पाध्यायस्य तृतीयः पादः",)),
    ("adhyaya 3, pada 4", ("तृतीयाध्यायस्य चतुर्थः पादः",)),
    ("adhyaya 4, pada 1", ("चतुर्थाध्यायस्य प्रथमः पादः",)),
    ("adhyaya 4, pada 2", ("चतुर्थाध्याये द्वितीयः पाद:",)),
    ("adhyaya 4, pada 3", ("चतुर्थाध्यायस्य तृतीयः पादः",)),
    ("adhyaya 4, pada 4", ("चतुर्याध्याये वियोनिभेदोनाम चतुर्थः पादः",)),
)


def _jaimini_extent(text: str) -> dict[str, Any]:
    """What the Jaimini copy contains, from its own end-of-pada markers.

    ⚠ The markers are looked for in both of the two forms the copy prints them in, and the
    extent reports which were found. ⛔ The copy's title names it a part; what it establishes
    about any adhyaya after the second is nothing, and that is what `beyond` says.
    """
    return measured_extent(
        text,
        markers=_JAIMINI_PADAS,
        describes=(
            "the padas whose closing marker is printed in this copy. Eight are, spanning the "
            "first and second adhyayas; the copy's title names it a part and it stops there"
        ),
        beyond=(
            "nothing. ⛔ This copy carries no material from any adhyaya after the second, so "
            "an absence measured in it is an absence from the first two adhyayas and from "
            "nowhere else. ⚠ It does not establish how many adhyayas the complete work has "
            "either - it states only that it is a part and where its own text ends"
        ),
    )


def _mishra_extent(text: str) -> dict[str, Any]:
    """What this copy contains, from its own closing formulae. ⛔ Incomplete, and it says so.

    ⭐ **The number this returns is a lower bound, and the reason is on `_MISHRA_PADAS`.**
    Each spelling was read off the copy because each guessed spelling was wrong, and three
    successive detectors each reported a smaller extent than the next. ⚠ An extent that
    reported *complete* over this copy would be reporting the reader's optimism; one that
    reports a shortfall without saying it is alphabet-bound is publishing the recorder's
    search as a property of the book.
    """
    return measured_extent(
        text,
        markers=_MISHRA_PADAS,
        describes=(
            "the padas whose closing formula is legible in this machine reading, each looked "
            "for in the damaged spelling this copy actually prints. The copy's own front "
            "matter lists four adhyayas of four padas each. ⛔ A pada listed as not found is "
            "not found in THIS RENDERING under THESE spellings - which is a fact about the "
            "machine reading and this search together, and not a fact about the printed book"
        ),
        beyond=(
            "nothing about the padas whose closing this rendering lost, and nothing about any "
            "pada after the fourth of the fourth adhyaya. ⚠ A locus into a pada whose "
            "boundary was not located is a locus into a region this instrument cannot state "
            "the limits of, so no claim rests on one. ⛔⛔ In particular an ABSENCE MAY NOT BE "
            "MEASURED OVER THIS COPY AT ALL: an absence is only as wide as the extent it is "
            "taken over, this extent is a lower bound rather than a measurement, and an "
            "absence over a lower bound would report the recorder's alphabet as the book's "
            "silence"
        ),
    )


def _scanned_printing_extent(text: str) -> dict[str, Any]:
    """What a copy of page images establishes about its own contents. ⛔ Nothing.

    ⭐⭐⭐ **THIS EXTENT EXISTS TO BE ZERO, AND A ZERO EXTENT IS THE MOST DANGEROUS
    MEASUREMENT IN THIS MODULE.** The copy is a real printing of the right work, retrieved
    from a real address and digested; every page of it is an image, and the rendering carries
    no characters at all. ⛔ So *every* search over it returns zero, *every* absence over it
    looks established, and nothing in a row of zeroes says whether the copy was silent or
    was never read. ⚠ The markers below are the same ones the other printing's extent is
    measured by, and they are looked for on purpose: finding none of them is what makes the
    emptiness a *measurement* rather than an omission.
    """
    return measured_extent(
        text,
        markers=_JAIMINI_PADAS,
        describes=(
            "the padas whose closing marker is printed in this copy - of which there are "
            "NONE, because this rendering carries no characters. ⛔ The copy is 219 pages of "
            "scanned page images with no text layer, so the boundary markers are not missing "
            "from the book: they were never read"
        ),
        beyond=(
            "⛔⛔⛔ NOTHING WHATEVER, AND THAT INCLUDES ITS OWN IDENTITY. This rendering "
            "carries zero characters, so it does not attest the work it contains, the "
            "translator whose words it prints, or the printing it is. Those are known here "
            "only from what the address names the file - which is a fact about a host and "
            "not about a book. ⚠ NO SEARCH OVER THIS COPY MEANS ANYTHING, and an absence "
            "measured over it would be the strongest-looking absence in this repository and "
            "the emptiest: every spelling returns zero because nothing was ever read"
        ),
    )


def _fifth_edition_extent(text: str) -> dict[str, Any]:
    """What the printing that declares itself the fifth contains, from its own markers.

    ⚠ The closing formula is looked for in the two forms this translation prints it in, and
    five of eight resolve in this machine reading against the spellings that were read off
    the OTHER printing of the same translation. ⛔ The three that do not are not missing from
    the book: this is a second machine reading of a second scan, and two readings of one
    sentence differ. ⇒ Reported as found and not-found rather than repaired, and the extent
    this copy DECLARES - the first two adhyayas, stated in its own signed foreword - is
    recorded beside the markers rather than substituted for them.
    """
    return measured_extent(
        text,
        markers=_JAIMINI_PADAS,
        describes=(
            "the padas whose closing marker resolves in this machine reading, looked for in "
            "the spellings read off the other printing of this same translation. ⚠ This copy "
            "also STATES its own extent, in a signed foreword: the first two adhyayas. A "
            "stated extent and a measured one are two different things and both are here"
        ),
        beyond=(
            "nothing. ⛔ A marker not found here is not a division missing from the book - it "
            "is a division whose closing sentence this second machine reading spelled "
            "differently from the first, and repairing it against the other copy's spelling "
            "would make an extent resolve against a document that exists only here"
        ),
    )


def _library_scan_extent(text: str) -> dict[str, Any]:
    """What a machine reading in the wrong script establishes about an English book. ⛔ Nothing.

    ⭐⭐⭐ **THIS EXTENT IS ZERO OVER A QUARTER OF A MILLION CHARACTERS, AND THAT IS A MORE
    DANGEROUS STATE THAN A COPY THAT RENDERS TO NOTHING.** The copy is a real scan of the
    right work, retrieved from a public archive and digested. Its machine reading carries
    **246 777 searchable characters and not one letter of the Latin alphabet**: the reader was
    set to an Indic script and returned a quarter of a million characters of noise for a book
    printed in English. ⛔ So every guard this repository owns that asks whether a copy was
    read at all answers YES for it, and every English spelling searched in it returns zero.
    """
    return measured_extent(
        text,
        markers=_JAIMINI_PADAS,
        describes=(
            "the padas whose closing marker is printed in this copy - of which NONE resolves, "
            "though the rendering is a quarter of a million characters long. ⛔ The markers "
            "are printed in English and this machine reading contains no English"
        ),
        beyond=(
            "⛔⛔⛔ NOTHING WHATEVER, AND UNLIKE A BLANK COPY IT DOES NOT LOOK LIKE NOTHING. "
            "The rendering carries 246 777 characters a locus could in principle resolve "
            "against and zero characters of the alphabet the book is printed in, so a check "
            "asking whether this copy was READ answers yes and a search for any English word "
            "in it answers zero. ⚠ An absence measured over it would be an absence over a "
            "machine reading that cannot express the thing being searched for, and it would "
            "print exactly the same reassuring zeroes as a copy that genuinely omits the rule"
        ),
    )


def _third_edition_extent(text: str) -> dict[str, Any]:
    """What the printing that declares itself the THIRD contains, from its own markers.

    ⭐⭐⭐ **THIS IS THE COPY THIS REPOSITORY HELD AS MUTE.** A previous session acquired a
    printing of this work as 219 pages of scanned page images whose rendering carried no text
    at all, and recorded of it that it attested *nothing whatever, and that includes its own
    identity*. The PDF a public archive distributes under this edition is **byte-identical to
    that copy** - the same 13 905 548 bytes, the same SHA-1, checked against the archive's own
    manifest - and the archive publishes a machine reading of it carrying 205 055 Latin
    letters. ⛔ The muteness was a property of the rendering this repository made, never of
    the copy: *a copy that renders to nothing in one reader is not a copy that says nothing.*

    ⚠ And what the copy says first is its own printing: a signed foreword presenting *the
    third and revised edition*, a title page naming the translator, and a line naming the
    reviser as his grandson. ⇒ The identity the earlier extent said this copy could never
    attest is on its first page, and was never unavailable - it was unread.
    """
    return measured_extent(
        text,
        markers=_JAIMINI_PADAS,
        describes=(
            "the padas whose closing marker resolves in this machine reading, looked for in "
            "the spellings read off the other printings of this same translation. ⚠ This "
            "copy also STATES its own printing, in a signed and dated foreword - the third "
            "and revised edition - and a stated printing and a measured extent are two "
            "different things, so both are here"
        ),
        beyond=(
            "nothing. ⛔ A marker not found here is a division whose closing sentence this "
            "machine reading spelled differently from the others, not a division missing "
            "from the book. ⚠⚠ AND NOTHING ABOUT THE UNREVISED WORDS: this printing names "
            "itself the THIRD revised edition and names the hand that revised it, so it "
            "stands on the same side of the standing refusal as the fifth does. An earlier "
            "printing is a thing this copy establishes EXISTED - a third edition presupposes "
            "a first - and it is not what this copy is"
        ),
    )


def _third_edition_reading_extent(text: str) -> dict[str, Any]:
    """What a FURTHER machine reading of one edition establishes about the printed book.

    ⭐⭐⭐ **THREE MACHINE READINGS OF ONE EDITION DISAGREE ABOUT WHETHER FOUR OF TWELVE
    SPELLINGS ARE ON THE PAGE AT ALL.** These copies are in this table so that an absence
    claimed of a *printing* can be checked against every reading of it that is held, instead
    of against whichever reading happened to be loaded. ⚠ A mark that is printed and that one
    reader loses returns a zero indistinguishable from a mark that was never printed.
    """
    return measured_extent(
        text,
        markers=_JAIMINI_PADAS,
        describes=(
            "the padas whose closing marker resolves in THIS machine reading. ⛔ A count here "
            "is a property of this reading and of the search together, and the same count "
            "taken over the other readings of the same edition does not match it"
        ),
        beyond=(
            "⛔⛔ nothing about the printed book that the other held readings of this edition "
            "do not also have to agree to. This copy is kept in order to BE DISAGREED WITH: "
            "it is one of three renderings of one edition, and the spellings whose "
            "zero/non-zero verdict differs between them are the measurement it exists to "
            "supply"
        ),
    )


def _bphs_extent(text: str) -> dict[str, Any]:
    return measured_extent(
        text,
        markers=_BPHS_CHAPTERS,
        describes=(
            "the chapter openings printed in this copy over the range the loci below fall "
            "in. ⚠ The copy runs far wider than this range; only the range cited is measured"
        ),
        beyond=(
            "nothing about any chapter whose opening is not listed here, and nothing about "
            "any other printing of this translation"
        ),
    )


SOURCES: dict[str, Source] = {
    "jaimini_sutras_rao": Source(
        key="jaimini_sutras_rao",
        identity=(
            "Jaimini Sutras, English translation with notes by B. Suryanarain Rao; the "
            "part covering the first and second adhyayas, as a text-layer PDF"
        ),
        language="en",
        address="https://lakshminarayanlenasia.com/articles/JAIMINISUTRAS.pdf",
        filename="jaimini-sutras-rao.pdf",
        rendering_kind="embedded_text_layer",
        render=_pdf_text_layer,
        extent=_jaimini_extent,
    ),
    #: ⭐ A SECOND PRINTING OF THE FIRST TRANSLATION - the copy the standing refusal asked
    #: for, acquired, and refused for a reason nobody had predicted. ⛔ It is the right work
    #: and it is retrievable; it is 219 pages of page images and its rendering carries **zero
    #: characters**, so not one locus can be resolved in it. ⚠ It is kept in this table rather
    #: than dropped, because a copy that renders to nothing is the case every absence
    #: instrument in this repository passes perfectly, and the only honest way to hold that
    #: control is against a copy that actually exists.
    "jaimini_sutras_rao_scanned_printing": Source(
        key="jaimini_sutras_rao_scanned_printing",
        identity=(
            "a printing of the Jaimini Sutras in B. Suryanarain Rao's English translation, "
            "offered under that description at the address recorded; 219 pages of scanned "
            "page images in a PDF carrying no text layer. ⛔ THE COPY ITSELF ATTESTS NONE OF "
            "THAT. Its rendering carries zero characters, so the work, the translator and the "
            "printing are known here only from the name the host gives the file - which is a "
            "fact about a host and not about a book, and is exactly the ground on which an "
            "earlier candidate was rejected for naming no translator"
        ),
        language="en",
        address=(
            "https://www.ebharatisampat.in/pdfs/"
            "ebharati-pdf-1619416068Jaimini-Sutras-Suryanarain-Rao-1949.pdf"
        ),
        filename="jaimini-sutras-rao-scanned-printing.pdf",
        rendering_kind="embedded_text_layer",
        render=_pdf_text_layer,
        extent=_scanned_printing_extent,
    ),
    #: ⭐⭐⭐ THE CANDIDATE THE STANDING TEST ASKED FOR, AND IT FAILS THE TEST BY SAYING WHY.
    #: A printing of the same translation that carries its own title page, its own imprint and
    #: a SIGNED foreword. ⛔ All twelve spellings marking the second commenting hand occur in
    #: it, so it cannot witness the unrevised words either - and it is the copy that turns
    #: *there is a second hand here and this copy does not say whose* into a located name.
    "jaimini_sutras_rao_fifth_edition": Source(
        key="jaimini_sutras_rao_fifth_edition",
        identity=(
            "Jaiminisutras, English translation with full notes and original texts in "
            "Devanagari and transliteration by Bangalore Suryanarain Rao, revised and "
            "annotated by Bangalore Venkata Raman; a machine reading of a scan as "
            "distributed by a public archive. ⭐ UNLIKE EVERY OTHER COPY HERE THIS ONE STATES "
            "ITS OWN PRINTING: its imprint reads *Fifth Edition 1955* and its foreword "
            "presents *the fifth and revised edition of the English translation of the first "
            "two adhyayas*, signed. ⛔ Both statements are the copy's, located and resolving "
            "exactly once; neither is corroborated from anywhere else"
        ),
        language="en",
        address=(
            "https://archive.org/download/Jaiminisutras1955EditionByBSRao/"
            "Jaiminisutras%201955%20Edition%20by%20B%20S%20Rao_djvu.txt"
        ),
        filename="jaimini-sutras-rao-fifth-edition.txt",
        rendering_kind="optical_character_recognition",
        render=_plain_text,
        extent=_fifth_edition_extent,
    ),
    #: ⛔⛔⛔ THE SECOND CANDIDATE, AND IT IS THE TRAP. A library scan of a printing of the
    #: same translation, dated 1949 by its catalogue. Eleven of the twelve second-hand
    #: spellings return ZERO over it - a textbook absence - and they return zero because the
    #: machine reading contains no English at all. ⚠ Kept in this table for exactly that
    #: reason: it is the copy against which *the copy was shown to have been read* has to be
    #: a real check rather than a character count.
    "jaimini_sutras_rao_library_scan": Source(
        key="jaimini_sutras_rao_library_scan",
        identity=(
            "a scan catalogued as the Jaimini Sutras of B. Suryanarain Rao, dated 1949, as "
            "distributed by a public archive; the archive's own machine reading of it. ⛔ THE "
            "RENDERING ATTESTS NONE OF THAT AND CANNOT. It carries a quarter of a million "
            "characters and not one letter of the Latin alphabet, for a book printed in "
            "English - the reader was set to an Indic script and returned noise. ⚠ Work, "
            "translator and date are known here only from the archive's catalogue"
        ),
        language="en",
        address=(
            "https://archive.org/download/in.ernet.dli.2015.486584/"
            "2015.486584.Jaimini-Sutras_djvu.txt"
        ),
        filename="jaimini-sutras-rao-library-scan.txt",
        rendering_kind="optical_character_recognition",
        render=_plain_text,
        extent=_library_scan_extent,
    ),
    #: ⭐⭐⭐ THE COPY THIS FILE HELD AS MUTE, READ. Byte-identical to the 219-page printing
    #: whose rendering carries no text - same bytes, same SHA-1 - and a public archive
    #: publishes a machine reading of it carrying 205 055 Latin letters. ⛔ The muteness was a
    #: property of the rendering, never of the copy, and this copy's first page states the
    #: printing the earlier extent said it could never attest.
    "jaimini_sutras_rao_third_edition": Source(
        key="jaimini_sutras_rao_third_edition",
        identity=(
            "Jaiminisutras, English translation with full notes and original texts in "
            "Sanscrit and transliteration by Professor B. Suryanarain Rao, revised and "
            "edited by his grandson B. V. Raman; a public archive's machine reading of a "
            "scan. ⭐⭐⭐ THE SCANNED PDF THIS READING WAS MADE FROM IS BYTE-IDENTICAL TO THE "
            "COPY THIS REPOSITORY HOLDS AS *RENDERS TO NOTHING* - 13 905 548 bytes, SHA-1 "
            "cdf112dfa3d061658daf5e55a4c2e35337db5f5a, checked against the archive's own "
            "manifest. ⭐ IT STATES ITS OWN PRINTING: a signed foreword dated Bangalore, "
            "16-11-1949, presents *the third and revised edition*. ⛔ That statement is this "
            "copy's own, and nothing corroborates it"
        ),
        language="en",
        address=(
            "https://archive.org/download/Astrology_Books_by_B_Suryanarayana_Row/"
            "Jaimini%20Sutras%20-%20B%20Suryanarain%20Rao%201949_djvu.txt"
        ),
        filename="jaimini-sutras-rao-1949-printing.txt",
        rendering_kind="optical_character_recognition",
        render=_plain_text,
        extent=_third_edition_extent,
    ),
    #: ⛔ A SECOND MACHINE READING OF THE SAME EDITION, held in order to be disagreed with. It
    #: carries the same signed foreword presenting the third and revised edition, and it loses
    #: marks the first reading finds.
    "jaimini_sutras_rao_third_edition_second_reading": Source(
        key="jaimini_sutras_rao_third_edition_second_reading",
        identity=(
            "a library scan catalogued as Jaiminisutras English Translation, carrying the "
            "same signed foreword presenting the third and revised edition; a public "
            "archive's machine reading of it. ⚠ Held as a SECOND READING of that edition and "
            "not as a further printing: what ties it to the first is a located fragment of "
            "the foreword resolving exactly once in each"
        ),
        language="en",
        address=(
            "https://archive.org/download/in.ernet.dli.2015.134405/"
            "2015.134405.Jaiminisutras-English-Translation_djvu.txt"
        ),
        filename="jaimini-sutras-rao-third-edition-second-reading.txt",
        rendering_kind="optical_character_recognition",
        render=_plain_text,
        extent=_third_edition_reading_extent,
    ),
    #: ⛔ A THIRD MACHINE READING OF THE SAME EDITION. ⚠ It loses the founding sutra's own
    #: translated line, which resolves exactly once in the other two - so the passage every
    #: rule in this file hangs from is simply not in this rendering of the same book.
    "jaimini_sutras_rao_third_edition_third_reading": Source(
        key="jaimini_sutras_rao_third_edition_third_reading",
        identity=(
            "a second library scan catalogued as Jaiminisutras English Translation, of the "
            "same edition; a public archive's machine reading of it. ⚠ Held as a THIRD "
            "READING, and the least legible of the three: the foreword sentence naming the "
            "edition does not resolve in it at all, though the sentence naming the "
            "translator as the reviser's grandfather does"
        ),
        language="en",
        address=(
            "https://archive.org/download/in.ernet.dli.2015.142198/"
            "2015.142198.Jaiminisutras-English-Translation_djvu.txt"
        ),
        filename="jaimini-sutras-rao-third-edition-third-reading.txt",
        rendering_kind="optical_character_recognition",
        render=_plain_text,
        extent=_third_edition_reading_extent,
    ),
    "jaimini_sutram_mishra": Source(
        key="jaimini_sutram_mishra",
        identity=(
            "Jaimini Sutram Sampoorna, the sutras with a Hindi translation and commentary "
            "by Suresh Chandra Mishra, published by Ranjan Publications, Delhi; a machine "
            "reading of a scan, as distributed by a public archive"
        ),
        language="hi",
        address=(
            "https://archive.org/download/"
            "UPAS_jaimini-sutram-sampoorna-of-maharshi-jaimini-with-hindi-trans."
            "-and-commentary-by/"
            "Jaimini%20Sutram%20Sampoorna%20Of%20Maharshi%20Jaimini%20With%20Hindi%20"
            "Trans.%20And%20Commentary%20By%20Dr.%20Suresh%20Chandra%20Mishra%20-%20"
            "Ranjan%20Publications%20Delhi_djvu.txt"
        ),
        filename="jaimini-sutram-mishra.txt",
        rendering_kind="optical_character_recognition",
        render=_plain_text,
        extent=_mishra_extent,
    ),
    "bphs_santhanam": Source(
        key="bphs_santhanam",
        identity=(
            "Brihat Parasara Hora Shastra, English translation, commentary and annotation "
            "by R. Santhanam; a machine reading of a scan of the printed volumes, as "
            "distributed by a public archive"
        ),
        language="en",
        address=(
            "https://archive.org/download/brihatparasarahorashastrabyr.santhanam/"
            "Brihat%20Par%C4%81%C5%9Bara%20Hor%C4%81%20%C5%9Ah%C4%81stra%20By%20R."
            "%20Santhanam_djvu.txt"
        ),
        filename="bphs-santhanam.txt",
        rendering_kind="optical_character_recognition",
        render=_plain_text,
        extent=_bphs_extent,
    ),
}


# --------------------------------------------------------------------------------------
# Specimens of a RENDERING, not copies of a work
# --------------------------------------------------------------------------------------
#
# ⭐⭐⭐ **THE ACCEPTING SIDE OF `LEAST_RECURRENCE` WAS FITTED TO ONE COPY, AND ONE COPY IS
#    NOT A MEASUREMENT OF IT.** Every body this repository had ever held out was language,
#    so nothing held out spoke to the question *how long a stretch of a rendering that is
#    NOT language can pass this floor anyway*. These copies answer it.
#
# ⛔ THEY ARE NOT HELD AS TEXTS. Nothing here resolves a locus in them, no claim is
#    attributed to them and their extent is nothing. They are held because each one is an
#    instance of the failure the floor exists to catch — a public archive's own machine
#    reading of a scan, produced by a reader set to the wrong script, which returned
#    characters and no words.
#
# ⭐ HOW THEY WERE DRAWN, DECLARED BEFORE THEY WERE READ. Two draws over the same public
#    collection the held copy came from. The first took the head of the collection in
#    ascending identifier order and is recorded here because it is the draw that found the
#    defect — ⛔ and because its SHAPE was its answer: identifiers are adjacent when items
#    were uploaded together, so its seven copies were three works in three batches. The
#    second partitions instead: for each of the thirty-six characters an identifier can
#    begin with, the item at three widely separated positions of that bucket.
#
# ⛔ EVERY COPY EITHER DRAW RETURNED THAT THE FLOOR REFUSES IS HERE. None was chosen after
#    its numbers were seen, and the ones the floor refuses for their EXTENT rather than
#    their rendering are named in the accounting below and excluded — a copy under
#    `LEAST_EXTENT_A_REFUSAL_DISCRIMINATES_AT` is not certified noise, and treating one as
#    a specimen would have put a 220-character photograph caption in the evidence.


def _a_copy_this_floor_refuses_extent(text: str) -> dict[str, Any]:
    """⛔ NOTHING, and deliberately not measured.

    ⭐ These copies are held as specimens of a RENDERING KIND. The extent of a copy is what
    the copy establishes about the work it is a copy of, and this repository makes no claim
    about any of these works — it has not read them, it does not cite them, and their
    catalogue entries are the archive's word and not its own. ⚠ An extent function that
    looked for boundary markers here would report zeroes over a rendering that cannot
    express any marker, which is precisely the reassuring-zero failure the library scan in
    this cache exists to demonstrate.
    """
    return {
        "describes": (
            "nothing. This copy is held as a specimen of a machine reading that returned "
            "noise, not as a copy of the work its catalogue names"
        ),
        "divisions_looked_for": [],
        "divisions_found": [],
        "divisions_not_found": [],
        "complete": False,
        "established_from": (
            "nothing in the copy. ⛔ No extent was measured, because nothing here reasons "
            "about the work: the copy is evidence about a CONSTANT, and what is measured "
            "over it is its recurrence and the extents at which windows of it clear the "
            "floor"
        ),
        "beyond_this_extent_the_copy_establishes": (
            "⛔ NOTHING WHATEVER ABOUT THE WORK. The archive's catalogue names a title and "
            "this rendering cannot corroborate it: the reader was set to the wrong script "
            "and returned characters that are not words. ⚠ What the copy does establish is "
            "about the READING - that a machine reading of this size, carrying no language, "
            "recurs as measured on its own row"
        ),
    }


# 34 copies fell below the floor across the two draws.
# 2 are refused for their EXTENT and are NOT certified noise:
#   7-miniature-paintings-from-the-collection-of-puneet-jyotishi-jammu-residence-of-puneet-jyotishi - 220 characters
#   l39kaaratattvam39-nihitam39-guhaayaam_950_x - 4932 characters
# 32 are certified renderings of noise by this repository's own guard.

_COPIES_THIS_FLOOR_REFUSES: tuple[tuple[str, str, str], ...] = (
    (
        '01wonhyowebcollectedworksofkoreanbuddhism_391_m',
        'the head of the collection',
        (
            'https://archive.org/download/01wonhyowebcollectedworksofkoreanbuddhism_391'
            '_m/01_Wonhyo_web%20-%20Collected%20Works%20of%20Korean%20Buddhism_djvu.txt'
        ),
    ),
    (
        '02.encycreligethics.v2.artbun.hastings.selbie.1910.1_202003_973_f',
        'the head of the collection',
        (
            'https://archive.org/download/02.encycreligethics.v2.artbun.hastings.selbie'
            '.1910.1_202003_973_f/02.EncycReligEthics.v2.Art-Bun.Hastings.Selbie.1910.%'
            '5B1%5D_djvu.txt'
        ),
    ),
    (
        '02chinulwebcollectedworksofkoreanbuddhism_545_D',
        'the head of the collection',
        (
            'https://archive.org/download/02chinulwebcollectedworksofkoreanbuddhism_545'
            '_D/02_Chinul_web%20-%20Collected%20Works%20of%20Korean%20Buddhism_djvu.txt'
        ),
    ),
    (
        '04.encycreligethics.v4.condram.hastings.selbie.1910.1_202003_519_g',
        'the head of the collection',
        (
            'https://archive.org/download/04.encycreligethics.v4.condram.hastings.selbi'
            'e.1910.1_202003_519_g/04.EncycReligEthics.v4.Con-Dram.Hastings.Selbie.1910'
            '.%5B1%5D_djvu.txt'
        ),
    ),
    (
        '04hwaomiwebcollectedworksofkoreanbuddhism_992_C',
        'the head of the collection',
        (
            'https://archive.org/download/04hwaomiwebcollectedworksofkoreanbuddhism_992'
            '_C/04_Hwaom_I_web%20-%20Collected%20Works%20of%20Korean%20Buddhism_djvu.tx'
            't'
        ),
    ),
    (
        '06kssayingsoflalleshwari_202003_29_N',
        'the head of the collection',
        (
            'https://archive.org/download/06kssayingsoflalleshwari_202003_29_N/06ksSayi'
            'ngs%20of%20Lalleshwari_djvu.txt'
        ),
    ),
    (
        '07.encycreligethics.v7.hymlib.hastings.selbie.gray.1915.1_202003_461_w',
        'the head of the collection',
        (
            'https://archive.org/download/07.encycreligethics.v7.hymlib.hastings.selbie'
            '.gray.1915.1_202003_461_w/07.EncycReligEthics.v7.Hym-Lib.Hastings.Selbie.G'
            'ray.1915.%5B1%5D_djvu.txt'
        ),
    ),
    (
        '10.encycreligethics.v10.picsac.hastings.selbie.gray.1918.1_202003_416_A',
        "bucket '1', position 1",
        (
            'https://archive.org/download/10.encycreligethics.v10.picsac.hastings.selbi'
            'e.gray.1918.1_202003_416_A/10.EncycReligEthics.v10.Pic-Sac.Hastings.Selbie'
            '.Gray.1918.%5B1%5D_djvu.txt'
        ),
    ),
    (
        '20tarjumabhagavatgitarahasyalokmanyabalgangadhartilak_6',
        "bucket '2', position 1",
        (
            'https://archive.org/download/20tarjumabhagavatgitarahasyalokmanyabalgangad'
            'hartilak_6/20-Tarjuma%20Bhagavat%20Gita%20Rahasya%20-%20Lok%20Manya%20Bal%'
            '20Gangadhar%20Tilak_djvu.txt'
        ),
    ),
    (
        '5000-years-of-kashmir-balraj-puri',
        "bucket '5', position 1",
        (
            'https://archive.org/download/5000-years-of-kashmir-balraj-puri/5000%20Year'
            's%20of%20Kashmir%20-%20Balraj%20Puri_djvu.txt'
        ),
    ),
    (
        '60yearsofchinesemisrulearguingculturalgenocideintibetmarybethmarkeyarticles_195_o',
        "bucket '6', position 1",
        (
            'https://archive.org/download/60yearsofchinesemisrulearguingculturalgenocid'
            'eintibetmarybethmarkeyarticles_195_o/60%20Years%20of%20Chinese%20Misrule%2'
            '0Arguing%20Cultural%20Genocide%20in%20Tibet%20Mary%20Beth%20Markey%20%28Ar'
            'ticles%29_djvu.txt'
        ),
    ),
    (
        '99999990320058mimansakaustubhashrikhanddev424pdevotionalsanskrit1933_202003_143_o',
        "bucket '9', position 1",
        (
            'https://archive.org/download/99999990320058mimansakaustubhashrikhanddev424'
            'pdevotionalsanskrit1933_202003_143_o/99999990320058%20-%20Mimansa%20kaustu'
            'bha%2C%20Shri%20khand%20dev%2C%20424p%2C%20Devotional%2C%20sanskrit%20%281'
            '933%29_djvu.txt'
        ),
    ),
    (
        'annalsofeastindiacompanyjohnbruce17071708vol2prited1810_567_N',
        "bucket 'a', position 1000",
        (
            'https://archive.org/download/annalsofeastindiacompanyjohnbruce17071708vol2'
            'prited1810_567_N/Annals%20of%20East%20India%20Company%20John%20Bruce%20170'
            '7-1708%20Vol%202%20Prited%201810_djvu.txt'
        ),
    ),
    (
        'b.c.lawvolumepart1ms_900_N',
        "bucket 'b', position 1",
        (
            'https://archive.org/download/b.c.lawvolumepart1ms_900_N/B.C.%20Law%20Volum'
            'e%20Part%201%20%28MS%29_djvu.txt'
        ),
    ),
    (
        'biharthehomelandofbuddhism_675_O',
        "bucket 'b', position 500",
        (
            'https://archive.org/download/biharthehomelandofbuddhism_675_O/Bihar%20the%'
            '20Homeland%20of%20Buddhism_djvu.txt'
        ),
    ),
    (
        'bodhicaryavatarapanjikabodhicaryavataraofsantidevalouisdevalleepoussinasiaticsociety1902_375_L',
        "bucket 'b', position 1000",
        (
            'https://archive.org/download/bodhicaryavatarapanjikabodhicaryavataraofsant'
            'idevalouisdevalleepoussinasiaticsociety1902_375_L/Bodhicaryavatara%20Panji'
            'ka%2C%20Bodhicaryavatara%20of%20Santideva%20Louis%20de%20Vallee%20Poussin%'
            '20Asiatic%20Society%201902_djvu.txt'
        ),
    ),
    (
        'collectedworksofmahatmagandhivol23_838_H',
        "bucket 'c', position 500",
        (
            'https://archive.org/download/collectedworksofmahatmagandhivol23_838_H/Coll'
            'ected%20works%20of%20Mahatma%20Gandhi%20Vol%2023_djvu.txt'
        ),
    ),
    (
        'dictionaryofastrologybhansinj.n._738_',
        "bucket 'd', position 500",
        (
            'https://archive.org/download/dictionaryofastrologybhansinj.n._738_/Diction'
            'ary%20of%20Astrology%20%20Bhansin%20J.N.%20_djvu.txt'
        ),
    ),
    (
        'earliestcivilizationofsouthasiarisematuritydeclinelalb.b._837_d',
        "bucket 'e', position 1",
        (
            'https://archive.org/download/earliestcivilizationofsouthasiarisematurityde'
            'clinelalb.b._837_d/Earliest%20Civilization%20of%20South%20Asia%20Rise%20Ma'
            'turity%20%26%20Decline%20Lal%20B.B._djvu.txt'
        ),
    ),
    (
        'k.b.pathakcommemorationvolumes.k.belvalkar_272_w',
        "bucket 'k', position 1",
        (
            'https://archive.org/download/k.b.pathakcommemorationvolumes.k.belvalkar_27'
            '2_w/K.B.%20Pathak%20Commemoration%20Volume%20-S.K.%20Belvalkar_djvu.txt'
        ),
    ),
    (
        'm.hiriyannacommemorationvolume_444_t',
        "bucket 'm', position 1",
        (
            'https://archive.org/download/m.hiriyannacommemorationvolume_444_t/M.%20Hir'
            'iyanna%20Commemoration%20Volume%20%20%20_djvu.txt'
        ),
    ),
    (
        'manusmritivol4part2_202003_726_p',
        "bucket 'm', position 500",
        (
            'https://archive.org/download/manusmritivol4part2_202003_726_p/Manu%20Smrit'
            'i%20Vol4%20Part2_djvu.txt'
        ),
    ),
    (
        'nacaratnamalikaandotherworksofsastrasarmannavyanyayamarip.i.thesis_202003_693_m',
        "bucket 'n', position 1",
        (
            'https://archive.org/download/nacaratnamalikaandotherworksofsastrasarmannav'
            'yanyayamarip.i.thesis_202003_693_m/Naca%20Ratna%20Malika%20and%20Other%20W'
            'orks%20of%20Sastra%20Sarman%20Navya%20Nyaya%20Mari%20P.I.%20%28Thesis%29_d'
            'jvu.txt'
        ),
    ),
    (
        'obscurereligiouscultsshashibhushandasgupta1946_202003_922_Y',
        "bucket 'o', position 1",
        (
            'https://archive.org/download/obscurereligiouscultsshashibhushandasgupta194'
            '6_202003_922_Y/Obscure%20Religious%20Cults%20Shashibhushan%20Dasgupta%2019'
            '46_djvu.txt'
        ),
    ),
    (
        'paar-pare-urdu-novel-joginder-paul',
        "bucket 'p', position 1",
        (
            'https://archive.org/download/paar-pare-urdu-novel-joginder-paul/Paar%20Par'
            'e%20Urdu%20Novel%20-%20Joginder%20Paul_djvu.txt'
        ),
    ),
    (
        'qadeemshaariyaataskashirenhunddyutbykndharkashmirithepgdeptofkashmirikashmiruniversity',
        "bucket 'q', position 1",
        (
            'https://archive.org/download/qadeemshaariyaataskashirenhunddyutbykndharkas'
            'hmirithepgdeptofkashmirikashmiruniversity/Qadeem%20Shaariyaatas%20Kashiren'
            '%20hund%20Dyut%20by%20K%20N%20Dhar%20Kashmiri%20-%20The%20PG%20Dept%20of%2'
            '0Kashmiri%20Kashmir%20University_djvu.txt'
        ),
    ),
    (
        'r.g.bhandarkarcommemorationvolume_745_r',
        "bucket 'r', position 1",
        (
            'https://archive.org/download/r.g.bhandarkarcommemorationvolume_745_r/R.%20'
            'G.%20Bhandarkar%20Commemoration%20Volume%20%20%20_djvu.txt'
        ),
    ),
    (
        'replytolettersofabbeduboisbyjameshough1824_202003_367_e',
        "bucket 'r', position 500",
        (
            'https://archive.org/download/replytolettersofabbeduboisbyjameshough1824_20'
            '2003_367_e/Reply%20to%20letters%20of%20Abbe%20Dubois%20By%20James%20Hough%'
            '201824_djvu.txt'
        ),
    ),
    (
        'scienceandtheindiantraditionwheneinsteinmettagoredavidgoslingl.routledge_28_n',
        "bucket 's', position 1000",
        (
            'https://archive.org/download/scienceandtheindiantraditionwheneinsteinmetta'
            'goredavidgoslingl.routledge_28_n/Science%20and%20the%20Indian%20Tradition%'
            '20When%20Einstein%20Met%20Tagore%20David%20Gosling%20L.%20Routledge_djvu.t'
            'xt'
        ),
    ),
    (
        'the-mudra-rakshasa-nataka-katha-of-mahadeva-ed.-dr-v.-raghavan-series-no.-1-than',
        "bucket 't', position 500",
        (
            'https://archive.org/download/the-mudra-rakshasa-nataka-katha-of-mahadeva-e'
            'd.-dr-v.-raghavan-series-no.-1-than/The%20Mudra%20Rakshasa%20Nataka%20Kath'
            'a%20of%20Mahadeva%20Ed.%20Dr%20V.%20Raghavan%20%20Series%20No.%201%20-%20T'
            'hanjavur%20Sarasvati%20Mahal%20Series_djvu.txt'
        ),
    ),
    (
        'TheTheoryOfTheSamdhisAndTheSamdhyangasInNatyaShastraT.G.Mainkar',
        "bucket 't', position 1000",
        (
            'https://archive.org/download/TheTheoryOfTheSamdhisAndTheSamdhyangasInNatya'
            'ShastraT.G.Mainkar/The%20Theory%20Of%20The%20Samdhis%20And%20The%20Samdhya'
            'ngas%20in%20Natya%20Shastra%20-%20T.G.%20Mainkar_djvu.txt'
        ),
    ),
    (
        'wafatnamah-anhazrat-kashmiri-ghulam-mohd-noor-mohd',
        "bucket 'w', position 1",
        (
            'https://archive.org/download/wafatnamah-anhazrat-kashmiri-ghulam-mohd-noor'
            '-mohd/Wafatnamah%20Anhazrat%20Kashmiri%20-%20Ghulam%20Mohd%20Noor%20Mohd_d'
            'jvu.txt'
        ),
    ),
)


#: ⭐ Built by a loop rather than written out: every specimen carries the same identity,
#: the same extent and the same reader, and thirty-two hand-written copies of one sentence
#: would be thirty-two places for it to drift.
for _identifier, _drawn, _address in _COPIES_THIS_FLOOR_REFUSES:
    _key = "refused_copy_" + "".join(
        character if character.isalnum() else "_" for character in _identifier.lower()
    )
    SOURCES[_key] = Source(
        key=_key,
        identity=(
            f"a public archive's own machine reading of a scan it distributes as "
            f"{_identifier!r}. ⛔ HELD AS A SPECIMEN OF THE READING, NOT AS A COPY OF THE "
            "WORK: this repository has not read the work, cites nothing from it and takes "
            "no position on what the archive's catalogue calls it. What is measured over "
            "it is that it carries characters and not words, and how long a window of it "
            f"clears the recurrence floor anyway. ⚠ Drawn from {_drawn}"
        ),
        language="und",
        address=_address,
        filename=f"specimens/{_identifier}.txt",
        rendering_kind="optical_character_recognition",
        render=_plain_text,
        extent=_a_copy_this_floor_refuses_extent,
    )

#: The specimen keys, in the order the table declares them. ⚠ Read by the generator, which
#: re-measures every one of them rather than quoting a table.
COPIES_THIS_FLOOR_REFUSES_KEYS: tuple[str, ...] = tuple(
    key for key in SOURCES if key.startswith("refused_copy_")
)


# --------------------------------------------------------------------------------------
# The other side of the same two draws: every copy the floor ACCEPTED
# --------------------------------------------------------------------------------------
#
# ⛔⛔⛔ **THEY WERE MEASURED AND THROWN AWAY, AND THAT MADE THE EVIDENCE ONE-SIDED.** The
#    two draws that produced the specimens above returned fifty-nine readable copies. The
#    thirty-four the floor refused were kept; the twenty-five it accepted were measured,
#    printed to a log and deleted. ⇒ Every question about this floor could then only be
#    asked from below it, and the one that mattered - *does it refuse real books?* - needs
#    both sides: where real copies sit is a fact about the accepted side.
#
# ⭐ **THE DRAWS ARE NOT RE-RUN; THE COPIES ARE RE-FETCHED FROM THE ADDRESSES THE DRAWS
#    RECORDED.** A search over a live collection is not a fixed function of its query -
#    items are added - so re-running it would answer a different draw and the two sides
#    would no longer be the same sixty items. What reproduces is checked instead: each
#    copy's normalised character count and its share, against what the draw wrote down.
#
# ⚠ Held on exactly the terms the refused copies are held on: as instances of a READING.
#    This repository has not read these works, cites nothing from them, and takes no
#    position on what the archive's catalogue calls them.


def _a_copy_this_floor_accepts_extent(text: str) -> dict[str, Any]:
    """⛔ NOTHING, for the same reason the refused copies measure none.

    ⚠ *And accepting is not a certificate.* A copy is here because a floor fitted to seven
    renderings let it through, which is a fact about the floor. Nothing about the work, the
    printing or the reading follows from it, and an extent measured here would be the first
    thing a reader mistook for one.
    """
    return {
        "describes": (
            "nothing. This copy is held as the accepted side of a floor's own evidence, "
            "not as a copy of the work its catalogue names"
        ),
        "divisions_looked_for": [],
        "divisions_found": [],
        "divisions_not_found": [],
        "complete": False,
        "established_from": (
            "nothing in the copy. ⛔ No extent was measured, because nothing here reasons "
            "about the work: the copy is evidence about a CONSTANT, and what is measured "
            "over it is its recurrence and what language it carries"
        ),
        "beyond_this_extent_the_copy_establishes": (
            "⛔ NOTHING WHATEVER ABOUT THE WORK, and ⚠ NOTHING ABOUT THE READING EITHER "
            "beyond the two things measured on its row. Clearing a recurrence floor is not "
            "a finding that a copy was read well: the floor is fitted to seven renderings "
            "and a specimen carrying no language has cleared it over a window spanning "
            "96.69 % of itself"
        ),
    }


_COPIES_THAT_CLEARED: tuple[tuple[str, str, str], ...] = (
    (
        '0415073103encofphilosophy10vs_202003_611_x',
        'the head of the collection',
        (
            'https://archive.org/download/0415073103encofphilosophy10vs_202003_611_'
            'x/0415073103_Enc_of_Philosophy_10VS_djvu.txt'
        ),
    ),
    (
        '00bhagavatainkannada1stskandha_202003_821_F',
        "bucket '0', position 1",
        (
            'https://archive.org/download/00bhagavatainkannada1stskandha_202003_821'
            '_F/00_Bhagavata_in_Kannada_1st-Skandha_djvu.txt'
        ),
    ),
    (
        '30776245teachingsofthesidhaspart3conductenglish_202004_297_J',
        "bucket '3', position 1",
        (
            'https://archive.org/download/30776245teachingsofthesidhaspart3conducte'
            'nglish_202004_297_J/30776245-Teachings-of-the-Sidhas-Part-3-Conduct-'
            'English_djvu.txt'
        ),
    ),
    (
        '46955728arutperunjotivazhipaadutamilenglish_202004_226_z',
        "bucket '4', position 1",
        (
            'https://archive.org/download/46955728arutperunjotivazhipaadutamilengli'
            'sh_202004_226_z/46955728-Arutperunjoti-Vazhipaadu-Tamil-'
            'English_djvu.txt'
        ),
    ),
    (
        '84siddhomkavrittantahindicentralinstituteofhighertibetanstudies_130_T',
        "bucket '8', position 1",
        (
            'https://archive.org/download/84siddhomkavrittantahindicentralinstitute'
            'ofhighertibetanstudies_130_T/84%20Siddhom%20ka%20Vrittanta%20Hindi%20-'
            '%20Central%20Institute%20of%20Higher%20Tibetan%20Studies_djvu.txt'
        ),
    ),
    (
        'a-brief-account-of-the-achievements-of-shri-baba-kali-kamli-wala-panchayat-kshet',
        "bucket 'a', position 1",
        (
            'https://archive.org/download/a-brief-account-of-the-achievements-of-'
            'shri-baba-kali-kamli-wala-panchayat-kshet/A%20Brief%20Account%20of%20t'
            'he%20Achievements%20of%20Shri%20Baba%20Kali%20Kamli%20Wala%20Panchayat'
            '%20Kshetra%20And%20Atma%20Vigryan%20Bhavan%20Rishikesh%20-'
            '%20Baba%20Kali%20Kamali%20Baba%20Kshetra%20Calcutta_djvu.txt'
        ),
    ),
    (
        'AjitagamaVolIN.R.Bhatt',
        "bucket 'a', position 500",
        (
            'https://archive.org/download/AjitagamaVolIN.R.Bhatt/Ajitagama%20Vol%20'
            'I%20-%20N.R.%20Bhatt_djvu.txt'
        ),
    ),
    (
        'dli.bengal.10689.10312',
        "bucket 'd', position 1000",
        (
            'https://archive.org/download/dli.bengal.10689.10312/10689.10312_djvu.t'
            'xt'
        ),
    ),
    (
        'facetofacewithsriramanamaharshilakshminarainarticles_202004_426_D',
        "bucket 'f', position 1",
        (
            'https://archive.org/download/facetofacewithsriramanamaharshilakshminar'
            'ainarticles_202004_426_D/Face%20To%20Face%20With%20Sri%20Ramana%20Maha'
            'rshi%20Lakshmi%20Narain%20%28Articles%29_djvu.txt'
        ),
    ),
    (
        'gaban-hans-publishers-premchand',
        "bucket 'g', position 1",
        (
            'https://archive.org/download/gaban-hans-publishers-'
            'premchand/Gaban%20Hans%20Publishers%20-%20Premchand_djvu.txt'
        ),
    ),
    (
        'gov.in.Notification.2022.99',
        "bucket 'g', position 500",
        (
            'https://archive.org/download/gov.in.Notification.2022.99/notification-'
            '99-2022_djvu.txt'
        ),
    ),
    (
        'haaralatabyaniruddhabhattabibliothecaindica_628_V',
        "bucket 'h', position 1",
        (
            'https://archive.org/download/haaralatabyaniruddhabhattabibliothecaindi'
            'ca_628_V/Haaralata%20by%20Aniruddha%20Bhatta%20-'
            '%20Bibliotheca%20Indica_djvu.txt'
        ),
    ),
    (
        'iabu2012buddhasenlightenmentforthewellbeingofhumanity_62_Z',
        "bucket 'i', position 1",
        (
            'https://archive.org/download/iabu2012buddhasenlightenmentforthewellbei'
            'ngofhumanity_62_Z/IABU-2012-Buddha-s-Enlightenment-for-the-Well-Being-'
            'of-Humanity_djvu.txt'
        ),
    ),
    (
        'in.ernet.dli.2015.101106',
        "bucket 'i', position 500",
        (
            'https://archive.org/download/in.ernet.dli.2015.101106/2015.101106.The-'
            'Penal-Law-Of-British-India_djvu.txt'
        ),
    ),
    (
        'in.ernet.dli.2015.101876',
        "bucket 'i', position 1000",
        (
            'https://archive.org/download/in.ernet.dli.2015.101876/2015.101876.Old-'
            'Mortality-Vol-Ii_djvu.txt'
        ),
    ),
    (
        'j-.-krishnamurti-as-i-knew-him-susunaga-veerperumma',
        "bucket 'j', position 1",
        (
            'https://archive.org/download/j-.-krishnamurti-as-i-knew-him-susunaga-v'
            'eerperumma/J%20.Krishnamurti%20as%20i%20Knew%20Him%20-'
            '%20Susunaga%20Veerperumma_djvu.txt'
        ),
    ),
    (
        'krsnakarnamrtamsataka1sanskrittextsatgaudiyagranthamandir_209_z',
        "bucket 'k', position 500",
        (
            'https://archive.org/download/krsnakarnamrtamsataka1sanskrittextsatgaud'
            'iyagranthamandir_209_z/Krsna%20Karnamrtam%20Sataka%201%20-'
            '%20%20Sanskrit%20Texts%20at%20Gaudiya%20Grantha%20Mandir_djvu.txt'
        ),
    ),
    (
        'noticesofsanskritmss.2dser.1871vol.3pt13_814_f',
        "bucket 'n', position 500",
        (
            'https://archive.org/download/noticesofsanskritmss.2dser.1871vol.3pt13_'
            '814_f/Notices%20of%20Sanskrit%20MSS.%202d%20ser.%20%281871%29%2C%20vol'
            '.%203%2C%20Pt%201-3_djvu.txt'
        ),
    ),
    (
        'pli.kerala.rare.14973',
        "bucket 'p', position 1000",
        (
            'https://archive.org/download/pli.kerala.rare.14973/pli.kerala.rare.149'
            '73_djvu.txt'
        ),
    ),
    (
        'sankhyakarikagoudapadabhashyatattvakaumudiofvachaspatimisravrittiofswaminarayana_202003_46_y',
        "bucket 's', position 500",
        (
            'https://archive.org/download/sankhyakarikagoudapadabhashyatattvakaumud'
            'iofvachaspatimisravrittiofswaminarayana_202003_46_y/Sankhya%20Karika%2'
            '0Goudapada%20Bhashya%20Tattva%20Kaumudi%20of%20Vachaspati%20Misra%20Vr'
            'itti%20of%20Swami%20Narayana%20Svetha%20Vaikuntha%20Shastri_djvu.txt'
        ),
    ),
    (
        'tableofcontentsforthe18smritis_187_K',
        "bucket 't', position 1",
        (
            'https://archive.org/download/tableofcontentsforthe18smritis_187_K/Tabl'
            'e%20of%20Contents%20for%20the%2018%20Smritis_djvu.txt'
        ),
    ),
    (
        'uchchatar-sanskrit-pathavali-badri-dutt-shastri',
        "bucket 'u', position 1",
        (
            'https://archive.org/download/uchchatar-sanskrit-pathavali-badri-dutt-s'
            'hastri/Uchchatar%20Sanskrit%20Pathavali%20-'
            '%20Badri%20Dutt%20Shastri_djvu.txt'
        ),
    ),
    (
        'VaallabhVedantaGoswamiShyamManohar',
        "bucket 'v', position 1",
        (
            'https://archive.org/download/VaallabhVedantaGoswamiShyamManohar/Vaalla'
            'bh%20Vedanta%20%20-%20Goswami%20Shyam%20Manohar_djvu.txt'
        ),
    ),
    (
        'Xagy_greek-kashmir-iqbal-ahmad',
        "bucket 'x', position 1",
        (
            'https://archive.org/download/Xagy_greek-kashmir-iqbal-'
            'ahmad/Greek%20Kashmir%20%E2%80%93%20Iqbal%20Ahmad_djvu.txt'
        ),
    ),
    (
        'yadavabhyudayabyvedantadesikaenglishtranslation',
        "bucket 'y', position 1",
        (
            'https://archive.org/download/yadavabhyudayabyvedantadesikaenglishtrans'
            'lation/Yadavabhyudaya%20by%20Vedanta%20Desika%20-'
            '%20English%20translation_djvu.txt'
        ),
    ),
)


#: ⭐ Built by the same loop shape as the specimens, for the same reason.
for _identifier, _drawn, _address in _COPIES_THAT_CLEARED:
    _key = "cleared_copy_" + "".join(
        character if character.isalnum() else "_" for character in _identifier.lower()
    )
    SOURCES[_key] = Source(
        key=_key,
        identity=(
            f"a public archive's own machine reading of a scan it distributes as "
            f"{_identifier!r}. ⛔ HELD AS THE ACCEPTED SIDE OF A FLOOR'S EVIDENCE, NOT AS "
            "A COPY OF THE WORK: this repository has not read the work, cites nothing "
            "from it and takes no position on what the archive's catalogue calls it. "
            "⚠ And accepting is not a certificate - what is measured over it is its "
            "recurrence and what language it carries, nothing else. "
            f"⚠ Drawn from {_drawn}"
        ),
        language="und",
        address=_address,
        filename=f"copies-that-cleared/{_identifier}.txt",
        rendering_kind="optical_character_recognition",
        render=_plain_text,
        extent=_a_copy_this_floor_accepts_extent,
    )

#: The accepted-side keys, in the order the table declares them.
COPIES_THAT_CLEARED_KEYS: tuple[str, ...] = tuple(
    key for key in SOURCES if key.startswith("cleared_copy_")
)


# --------------------------------------------------------------------------------------
# Which of these copies is certified to be a reading in the WRONG SCRIPT
# --------------------------------------------------------------------------------------
#
# ⭐⭐⭐ **A CERTIFICATION BY A PRESENCE, WHICH IS THE ONLY KIND THIS REPOSITORY ACCEPTS.**
#    The rendering carries, at essentially every one of its letters, a script the catalogued
#    work cannot be printed in. That is a presence of the WRONG script — it establishes that
#    the reader was set to a script the printing does not use, so whatever it returned is not
#    the words of the work. ⛔ It is NOT a certification by the copy failing to answer to a
#    word list: an absence establishes nothing, and the copies below are certified without
#    consulting `COMMONEST_WORDS` at all.
#
# ⛔⛔ **AND IT IS A LOWER BOUND, LIKE EVERY COUNT IN THIS REPOSITORY.** Where the catalogued
#    work is itself multilingual — the commemoration and felicitation volumes, which print
#    English articles and Sanskrit ones between the same covers — a Devanagari reading is not
#    by itself wrong, so those copies are ABSTAINED FROM rather than certified, and they are
#    named below with the abstention's reason. ⚠ Several of them are almost certainly
#    wrong-script readings too, and none of them is counted as one.
#
# ⭐ WHY IT EXISTS. `LEAST_RECURRENCE` had only ever been measured against copies it REFUSES.
#    A guard needs the other side: copies it ACCEPTS that it ought not to. Three of the
#    twenty-five copies it accepts are certified here, the largest of them 39 129 518
#    characters.

#: The copy key -> what the catalogued work is, and therefore why this reading is in a script
#: the work cannot be printed in. ⛔ Every entry names the work; none names a measurement.
READINGS_IN_A_SCRIPT_THE_WORK_CANNOT_BE_PRINTED_IN: Mapping[str, str] = {
    "jaimini_sutras_rao_library_scan": (
        "B. Suryanarain Rao's ENGLISH translation of the Jaimini Sutras. ⭐ This "
        "repository's own control, and the copy the wrong-alphabet finding was made on"
    ),
    "refused_copy_01wonhyowebcollectedworksofkoreanbuddhism_391_m": (
        "'Collected Works of Korean Buddhism' volume 1, an ENGLISH-language series"
    ),
    "refused_copy_02_encycreligethics_v2_artbun_hastings_selbie_1910_1_202003_973_f": (
        "Hastings' 'Encyclopaedia of Religion and Ethics' volume 2, ENGLISH, 1910"
    ),
    "refused_copy_02chinulwebcollectedworksofkoreanbuddhism_545_d": (
        "'Collected Works of Korean Buddhism' volume 2, an ENGLISH-language series"
    ),
    "refused_copy_04_encycreligethics_v4_condram_hastings_selbie_1910_1_202003_519_g": (
        "Hastings' 'Encyclopaedia of Religion and Ethics' volume 4, ENGLISH, 1910"
    ),
    "refused_copy_04hwaomiwebcollectedworksofkoreanbuddhism_992_c": (
        "'Collected Works of Korean Buddhism' volume 4, an ENGLISH-language series"
    ),
    "refused_copy_07_encycreligethics_v7_hymlib_hastings_selbie_gray_1915_1_202003_461_w": (
        "Hastings' 'Encyclopaedia of Religion and Ethics' volume 7, ENGLISH, 1915"
    ),
    "refused_copy_10_encycreligethics_v10_picsac_hastings_selbie_gray_1918_1_202003_416_a": (
        "Hastings' 'Encyclopaedia of Religion and Ethics' volume 10, ENGLISH, 1918"
    ),
    "refused_copy_5000_years_of_kashmir_balraj_puri": (
        "Balraj Puri, '5000 Years of Kashmir', ENGLISH, 1993"
    ),
    "refused_copy_60yearsofchinesemisrulearguingculturalgenocideintibetmarybethmarkeyarticles_195_o": (
        "Mary Beth Markey, articles on Tibet, ENGLISH"
    ),
    "refused_copy_annalsofeastindiacompanyjohnbruce17071708vol2prited1810_567_n": (
        "John Bruce, 'Annals of the Honorable East-India Company' volume 2, ENGLISH, "
        "printed 1810"
    ),
    "refused_copy_biharthehomelandofbuddhism_675_o": (
        "'Bihar, the Homeland of Buddhism', ENGLISH"
    ),
    "refused_copy_collectedworksofmahatmagandhivol23_838_h": (
        "'The Collected Works of Mahatma Gandhi' volume 23, the ENGLISH edition"
    ),
    "refused_copy_earliestcivilizationofsouthasiarisematuritydeclinelalb_b__837_d": (
        "B. B. Lal, 'The Earliest Civilization of South Asia', ENGLISH"
    ),
    "refused_copy_obscurereligiouscultsshashibhushandasgupta1946_202003_922_y": (
        "Shashibhushan Dasgupta, 'Obscure Religious Cults', ENGLISH, 1946"
    ),
    "refused_copy_replytolettersofabbeduboisbyjameshough1824_202003_367_e": (
        "James Hough, 'A Reply to the Letters of the Abbe Dubois', ENGLISH, 1824"
    ),
    "refused_copy_scienceandtheindiantraditionwheneinsteinmettagoredavidgoslingl_routledge_28_n": (
        "David L. Gosling, 'Science and the Indian Tradition', Routledge, ENGLISH"
    ),
    "refused_copy_thetheoryofthesamdhisandthesamdhyangasinnatyashastrat_g_mainkar": (
        "T. G. Mainkar, 'The Theory of the Samdhis and the Samdhyangas in Natyashastra', "
        "an ENGLISH monograph of 1978. ⚠ It quotes the Natyashastra's Sanskrit, and the "
        "wrong-script reader got those quotations RIGHT, which is why this copy carries "
        "declared Sanskrit across 48.8 % of its thousand-character blocks"
    ),
    "cleared_copy_0415073103encofphilosophy10vs_202003_611_x": (
        "ISBN 0415073103, the Routledge 'Encyclopedia of Philosophy' in ten volumes, "
        "ENGLISH. ⛔ 39 129 518 normalised characters, the largest copy this repository "
        "holds, and `LEAST_RECURRENCE` ACCEPTS it"
    ),
    "cleared_copy_00bhagavatainkannada1stskandha_202003_821_f": (
        "'Bhagavata in Kannada, 1st Skandha' - a KANNADA work; the reading is Devanagari. "
        "⛔ `LEAST_RECURRENCE` accepts it"
    ),
    "cleared_copy_iabu2012buddhasenlightenmentforthewellbeingofhumanity_62_z": (
        "the IABU 2012 conference proceedings, ENGLISH. ⛔ `LEAST_RECURRENCE` accepts it"
    ),
}

#: Copies a wrong-script reading is SUSPECTED of and **not certified**, with the reason the
#: certification is withheld. ⛔ Named rather than counted: a count with no names is a silent
#: cap on what a reader can check, and these are the copies that would most change the
#: numbers if anyone could certify them.
ABSTAINED_FROM_CERTIFYING: Mapping[str, str] = {
    "refused_copy_b_c_lawvolumepart1ms_900_n": (
        "a felicitation volume that prints English papers and Sanskrit ones together"
    ),
    "refused_copy_k_b_pathakcommemorationvolumes_k_belvalkar_272_w": (
        "a commemoration volume, English and Sanskrit between the same covers"
    ),
    "refused_copy_m_hiriyannacommemorationvolume_444_t": (
        "a commemoration volume, English and Sanskrit between the same covers"
    ),
    "refused_copy_r_g_bhandarkarcommemorationvolume_745_r": (
        "a commemoration volume, English and Sanskrit between the same covers"
    ),
    "refused_copy_manusmritivol4part2_202003_726_p": (
        "the language of this volume is not settled here"
    ),
    "refused_copy_06kssayingsoflalleshwari_202003_29_n": (
        "Kashmiri, English and Devanagari together"
    ),
    "refused_copy_20tarjumabhagavatgitarahasyalokmanyabalgangadhartilak_6": (
        "a translation; the language it was translated INTO is not settled here"
    ),
    "refused_copy_the_mudra_rakshasa_nataka_katha_of_mahadeva_ed__dr_v__raghavan_series_no__1_than": (
        "a Sanskrit work read in Devanagari - the script is not wrong"
    ),
    "refused_copy_nacaratnamalikaandotherworksofsastrasarmannavyanyayamarip_i_thesis_202003_693_m": (
        "a Sanskrit work read in Devanagari - the script is not wrong"
    ),
    "refused_copy_dictionaryofastrologybhansinj_n__738_": (
        "a Devanagari dictionary read in Devanagari - the script is not wrong"
    ),
    "refused_copy_paar_pare_urdu_novel_joginder_paul": (
        "an Urdu novel read in the Arabic script - the script is not wrong"
    ),
    "refused_copy_wafatnamah_anhazrat_kashmiri_ghulam_mohd_noor_mohd": (
        "Kashmiri read in the Arabic script - the script is not wrong"
    ),
    "refused_copy_qadeemshaariyaataskashirenhunddyutbykndharkashmirithepgdeptofkashmirikashmiruniversity": (
        "Kashmiri read in the Arabic script - the script is not wrong"
    ),
}


def certification_of(key: str) -> str:
    """`a_wrong_script_reading`, `abstained` or `not_certified`, for one copy key.

    ⛔ **`not_certified` and `abstained` are different answers and the difference is the
    point.** `abstained` names a copy this repository looked at and DECLINED to certify;
    `not_certified` is every other copy, including every one certified as a READING by a
    presence of its own language, which is a measurement and not a declaration.
    """
    if key in READINGS_IN_A_SCRIPT_THE_WORK_CANNOT_BE_PRINTED_IN:
        return "a_wrong_script_reading"
    if key in ABSTAINED_FROM_CERTIFYING:
        return "abstained"
    return "not_certified"


# --------------------------------------------------------------------------------------
# Acquiring, and loading what was acquired
# --------------------------------------------------------------------------------------


def _record_path(cache: Path, source: Source) -> Path:
    return cache / f"{source.filename}.acquired.json"


def acquire(key: str, *, cache: Path = CACHE, today: str) -> dict[str, Any]:
    """Fetch a copy and write down the retrieval beside it. ⚠ Goes to the network, always.

    The record is written once, at acquisition, and read unchanged at every later emission.
    ⛔ That is what lets a fixture carry the date the copy was actually obtained instead of
    the date it happened to be re-emitted.
    """
    source = SOURCES[key]
    cache.mkdir(parents=True, exist_ok=True)
    copy = cache / source.filename
    # ⚠ A source may file itself in a subdirectory of the cache - the noise specimens do -
    #   and the record is written beside the copy, so both need the directory to exist.
    copy.parent.mkdir(parents=True, exist_ok=True)
    retrieval = retrieve(source.address, cache=copy)
    record = {
        "address": source.address,
        "retrieved": today,
        "http_status": retrieval.status,
        "copy_sha256": retrieval.resource_sha256,
        "copy_bytes": len(retrieval.resource),
    }
    _record_path(cache, source).write_text(
        json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return record


def load(key: str, *, cache: Path = CACHE) -> Edition:
    """The copy, rendered and measured. ⛔ Refuses rather than acquiring one silently."""
    source = SOURCES[key]
    copy = cache / source.filename
    record_path = _record_path(cache, source)
    if not copy.is_file() or not record_path.is_file():
        raise AcquisitionError(
            f"no acquired copy of {key!r} is held. ⛔ Emission does not acquire: a fixture "
            "would then carry today's date for a copy obtained on another day, and would "
            "not regenerate without a network. Run the generator's --acquire step first"
        )
    payload = copy.read_bytes()
    record = json.loads(record_path.read_text(encoding="utf-8"))
    import hashlib

    if hashlib.sha256(payload).hexdigest() != record["copy_sha256"]:
        raise AcquisitionError(
            f"{key}: the held copy does not hash to what the acquisition recorded. ⛔ The "
            "record and the bytes describe two different documents; re-acquire"
        )
    text, produced_by = source.render(payload)
    return Edition(
        key=key,
        identity=source.identity,
        language=source.language,
        witness=Witness(
            address=record["address"],
            retrieved=record["retrieved"],
            http_status=record["http_status"],
            copy_sha256=record["copy_sha256"],
            copy_bytes=record["copy_bytes"],
        ),
        rendering=Rendering(
            kind=source.rendering_kind,
            produced_by=produced_by,
            sha256=digest(text),
            characters=len(text),
        ),
        extent=source.extent(text),
        text=text,
    )


def script_presence(edition: Edition, *, first: int, last: int) -> dict[str, Any]:
    """How many code points of a script the rendering carries. ⭐ Measured, not assumed.

    ⛔ **This answers PRESENCE and nothing else, and it must not be read as fidelity.** Two
    of the copies here render a translation and carry zero code points of the script the
    original is written in; for those, absence settles the question and a locus into the
    original is refused. ⚠ But a copy that carries the script in *quantity* has not thereby
    been shown to carry it *correctly*, and a machine reading can capture continuous prose
    cleanly while damaging the very lines a primary locus would cite. ⇒ Use
    `passage_fidelity` for that question; a caller that treats a true `present` as licence
    to cite the original has substituted one measurement for another.
    """
    count = sum(1 for c in edition.text if first <= ord(c) <= last)
    return {
        "code_points_in_range": count,
        "present": count > 0,
        "range": [f"U+{first:04X}", f"U+{last:04X}"],
    }


def passage_fidelity(
    edition: Edition,
    *,
    passage: str,
    quoted_word: str,
    stated_at: str,
) -> dict[str, Any]:
    """Whether a rendered passage contains the word the copy's OWN prose says it contains.

    ⭐ **The comparison is internal, and that is the whole point.** Asking whether a scanned
    sutra matches the form a work is *conventionally* transmitted in would need an authority
    this repository does not hold, and supplying one from the recorder's own memory is the
    unsourced claim the whole locus discipline exists to refuse. So the question asked here
    is one the copy answers about itself: its commentary names a word as occurring in the
    sutra it is commenting on, and the sutra as rendered either contains that word or does
    not.

    ⛔ A false result does not mean the printed book is wrong. It means **this rendering
    cannot be cited for that passage**, because the copy disagrees with itself about what
    the passage says — and a recorder that quoted the line anyway would be publishing the
    machine reading's damage under the text's own name.
    """
    body = normalise(edition.text)
    rendered = body.count(normalise(passage))
    carries = normalise(quoted_word) in normalise(passage)
    return {
        "passage_as_this_rendering_prints_it": passage,
        "occurrences_of_that_passage": rendered,
        "the_copy_states_the_passage_contains": quoted_word,
        "where_it_states_that": stated_at,
        "the_rendered_passage_contains_it": carries,
        "faithful": bool(rendered == 1 and carries),
        "what_a_false_result_means": (
            "⛔ that this RENDERING may not be cited for this passage - not that the printed "
            "book is wrong, and not that the passage is absent from the work. The copy "
            "disagrees with itself: its own commentary names a word as being in the sutra, "
            "and the sutra as this machine reading captured it does not contain that word"
        ),
    }


#: The block the Sanskrit original of both works is written in.
DEVANAGARI = (0x0900, 0x097F)
