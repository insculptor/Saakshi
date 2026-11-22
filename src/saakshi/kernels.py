"""Pinned-kernel identity.

A generator that samples an ephemeris kernel must be reading **the** kernel, not a file
with the right name. A content-addressed *filename* records only what somebody intended;
anything that can write to the directory can write a wrong file under a right-looking
name. So the digest is computed over the bytes, every run, before a single value is read.

⛔ **These pins are a recorded fact, not a dependency.** Saakshi reads no other
repository at runtime — the boundary in both directions is what makes these fixtures
evidence rather than an internal loop. Each row records where its digest came from and
when it was taken, so a stale pin is a visible discrepancy rather than a silent one.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

_CHUNK = 1 << 20


@dataclass(frozen=True)
class KernelPin:
    """One pinned dataset."""

    dataset: str  # the publisher's file name — ⛔ never an identity of its own
    profile: str  # the data-profile label that pins it, `<name>@<version>`; `none` where no profile does
    size_bytes: int
    sha256: str
    publisher: str
    pinned_on: str
    #: The digest the publisher itself lists for the file, where it lists one. ⭐ Not the identity —
    #: the sha256 is — but the link from that identity back to the publisher: the sha256 was taken
    #: over bytes whose digest matched this one when they were fetched.
    publisher_md5: str | None = None


#: ⭐ The publisher's own digest list, `aa_checksums.txt` beside the kernels in NAIF's
#: `generic_kernels/spk/planets/` (dated 2025-02-06). Every MD5 below is copied from it, and every
#: file was checked against it before its sha256 was recorded.
PUBLISHER_CHECKSUMS = "https://naif.jpl.nasa.gov/pub/naif/generic_kernels/spk/planets/aa_checksums.txt"

#: ⚠ These digests are over the **publisher's unmodified files**, and are reproducible by
#: anyone who downloads them: `sha256sum de440s.bsp`. They are recorded here so a generator
#: can refuse a substituted file without consulting anything outside this repository.
PINS: dict[str, KernelPin] = {
    "de440s.bsp": KernelPin(
        dataset="de440s.bsp",
        profile="standard@1",
        size_bytes=32_726_016,
        sha256="c1c7feeab882263fc493a9d5a5b2ddd71b54826cdf65d8d17a76126b260a49f2",
        publisher="NAIF / JPL Solar System Dynamics",
        pinned_on="2026-08-04",
        publisher_md5="3917ee56769db332790c751e2168843d",
    ),
    "de440.bsp": KernelPin(
        dataset="de440.bsp",
        profile="extended@1",
        size_bytes=119_799_808,
        sha256="a4ce9bf9b3282becc9f4b2ac3cebe03a2ae7599981aabd7265fd8482fff7c4b5",
        publisher="NAIF / JPL Solar System Dynamics",
        pinned_on="2026-08-04",
        publisher_md5="c9d581bfd84209dbeee8b1583939b148",
    ),
    # ⭐ One fit in two files that share 32 days (JD 2440400.5 to 2440432.5). Pinned separately,
    #    because each is a file; which of them answers inside the shared days is a reader's rule,
    #    and nothing here makes it.
    "de441_part-1.bsp": KernelPin(
        dataset="de441_part-1.bsp",
        profile="historical@1",
        size_bytes=1_651_119_104,
        sha256="13757827f5db41b835a24bbd637488636ce79a8ca754062fed17844f7d5b618e",
        publisher="NAIF / JPL Solar System Dynamics",
        pinned_on="2026-11-22",
        publisher_md5="7e5fcf9ecb5d08e1ab70c049baa60cd3",
    ),
    "de441_part-2.bsp": KernelPin(
        dataset="de441_part-2.bsp",
        profile="historical@1",
        size_bytes=1_656_830_976,
        sha256="3abb17dae2d78dd34880377544aacb54892104a0d4462b322cb9f4454d4887f6",
        publisher="NAIF / JPL Solar System Dynamics",
        pinned_on="2026-11-22",
        publisher_md5="ad8dfa4e505ef0e3a5d587a5b4705632",
    ),
    # ⚠ No data profile registers DE442, so its files carry `none` rather than a label invented here.
    "de442.bsp": KernelPin(
        dataset="de442.bsp",
        profile="none",
        size_bytes=119_771_136,
        sha256="8d5001fab315eeff222cc51f7cf7ffcdb43fb38fb9ac73ff09e09a5b361fd388",
        publisher="NAIF / JPL Solar System Dynamics",
        pinned_on="2026-11-22",
        publisher_md5="446656322267e7b819a26cb08a0d8718",
    ),
    "de442s.bsp": KernelPin(
        dataset="de442s.bsp",
        profile="none",
        size_bytes=32_701_440,
        sha256="54d97562a5b094d298b1b8eafa5a2e17e3e010ce85e1a366d07f003ad159323c",
        publisher="NAIF / JPL Solar System Dynamics",
        pinned_on="2026-11-22",
        publisher_md5="cc49327e06088124c0e39d8dde9f0b58",
    ),
}


class KernelIdentityError(Exception):
    """The file on disk is not the pinned file. ⛔ There is no override."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        while chunk := fh.read(_CHUNK):
            digest.update(chunk)
    return digest.hexdigest()


def verify(path: Path, pin: KernelPin | None = None) -> KernelPin:
    """Hash the file and refuse it unless it is the pinned one.

    Passing `pin` explicitly is preferred; falling back to the file's *name* is a
    convenience for the command line and is not evidence of anything — the digest is.
    """
    path = Path(path)
    if not path.is_file():
        raise KernelIdentityError(f"{path}: no such file")
    if pin is None:
        pin = PINS.get(path.name.lower())
        if pin is None:
            raise KernelIdentityError(
                f"{path.name}: no pin recorded for this file name; pass the pin explicitly "
                f"(known: {sorted(PINS)})"
            )
    size = path.stat().st_size
    if size != pin.size_bytes:
        raise KernelIdentityError(
            f"{path}: size {size} != pinned {pin.size_bytes} for {pin.profile}"
        )
    actual = sha256_file(path)
    if actual != pin.sha256:
        raise KernelIdentityError(
            f"{path}: sha256 {actual} != pinned {pin.sha256} for {pin.profile}. "
            "⛔ The right name is not the right file."
        )
    return pin


def oracle_identity(path: Path, pin: KernelPin) -> dict[str, object]:
    """The kernel half of a fixture's `oracle` block."""
    return {
        "dataset": pin.dataset,
        "profile": pin.profile,
        "size_bytes": pin.size_bytes,
        "sha256": pin.sha256,
        "sha256_verified_at_read": True,
        "publisher": pin.publisher,
        "pinned_on": pin.pinned_on,
    }
