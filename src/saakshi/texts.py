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
from typing import Any, Callable

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
