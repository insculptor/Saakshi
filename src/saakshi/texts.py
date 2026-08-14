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

⚠ **Both copies here are English translations of Sanskrit works, and neither rendering
contains any Sanskrit at all** — measured, at zero code points in the script, in both. A
locus into the original is therefore not resolvable in either, and the generators record
that as a refusal rather than citing a translation as though it were the text.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from .acquisition import AcquisitionError, retrieve
from .textual import Edition, Rendering, Witness, digest, measured_extent

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

    ⛔ Both copies here render a translation of a Sanskrit work, and both carry **zero**
    code points of the script the original is written in. A locus into the original is
    therefore not resolvable in either, which is a refusal rather than a caveat: citing a
    translation as though it were the text it translates is precisely the substitution the
    `source_kind` registry exists to keep visible.
    """
    count = sum(1 for c in edition.text if first <= ord(c) <= last)
    return {
        "code_points_in_range": count,
        "present": count > 0,
        "range": [f"U+{first:04X}", f"U+{last:04X}"],
    }


#: The block the Sanskrit original of both works is written in.
DEVANAGARI = (0x0900, 0x097F)
