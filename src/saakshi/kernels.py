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
    profile: str  # the data-profile label that pins it, `<name>@<version>`
    size_bytes: int
    sha256: str
    publisher: str
    pinned_on: str


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
    ),
    "de440.bsp": KernelPin(
        dataset="de440.bsp",
        profile="extended@1",
        size_bytes=119_799_808,
        sha256="a4ce9bf9b3282becc9f4b2ac3cebe03a2ae7599981aabd7265fd8482fff7c4b5",
        publisher="NAIF / JPL Solar System Dynamics",
        pinned_on="2026-08-04",
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
