"""Retrieving a published artifact, in a way that can be written down afterwards.

A fixture that pins a published file records that file's digest. ⛔ **The digest alone
attests nothing about where the bytes came from** — it says that whatever was read hashes
to a value, and a local file with the right name hashes just as convincingly as a
downloaded one. So the retrieval itself is recorded: the address asked for, the address
that answered, the status, the size, the digest of exactly those bytes, and whatever the
server said about the resource's own age.

⛔ **A cache read is not an acquisition.** The obvious implementation returns cached bytes
when they exist and stamps today's date on them, which produces a record that is false in
the one field it exists to establish. So this module always goes to the network, and uses
any cached copy as a *second* observation to check the first against rather than as a
substitute for it.

⚠ **What this can and cannot establish.** It records what this instrument received from
that address on that date. It cannot establish that the publisher published it: a server
answering an address is not the same claim, and nothing available from outside closes that
gap. The record says so in its own words rather than letting a reader assume otherwise.
"""

from __future__ import annotations

import hashlib
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

USER_AGENT = "saakshi/0.1"

#: Response headers worth recording. ⭐ Chosen because they are properties of the
#: **resource**, not of the request: they are the same on every retrieval, so recording
#: them leaves a fixture byte-identical when it is regenerated. ⛔ `Date` is deliberately
#: absent — it changes every request, and a field that moves on every run turns a
#: reproducibility check into noise.
_VALIDATORS = {"Last-Modified": "last_modified", "ETag": "etag"}


class AcquisitionError(Exception):
    """The artifact could not be acquired, or was not the artifact expected."""


@dataclass(frozen=True)
class Retrieval:
    """One retrieval, as observed."""

    url: str
    final_url: str
    status: int
    size_bytes: int
    sha256: str
    validators: dict[str, str]
    payload: bytes
    #: ⭐ Whether a copy from an earlier retrieval was on disk, and whether it agreed.
    #: `None` means there was nothing to compare against — reported as its own state, never
    #: collapsed into agreement.
    prior_copy_agreed: bool | None

    def as_record(self) -> dict[str, object]:
        """The retrieval's own fields, for a fixture row. ⛔ Never the payload."""
        return {
            "url": self.url,
            "final_url": self.final_url,
            "http_status": self.status,
            "size_bytes": self.size_bytes,
            "sha256": self.sha256,
        }


def retrieve(url: str, *, cache: Path, expected_sha256: str | None = None) -> Retrieval:
    """Fetch `url` over the network, and record what came back.

    A copy at `cache` is read *after* the fetch, compared, and then refreshed. ⛔ If it
    disagrees the whole run is refused: two different byte sequences have been served from
    one address, and which of them a fixture should pin is not a question a recorder may
    answer on its own.
    """
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            payload = response.read()
            status = int(response.status)
            final_url = response.geturl()
            headers = response.headers
    except (urllib.error.URLError, OSError) as exc:
        raise AcquisitionError(
            f"{url}: could not be retrieved ({exc}). ⛔ There is no offline path: a record "
            "of an acquisition that did not happen is worse than no record, because it "
            "looks discharged"
        ) from exc

    digest = hashlib.sha256(payload).hexdigest()
    if expected_sha256 is not None and digest != expected_sha256:
        raise AcquisitionError(
            f"{url}: sha256 {digest} != expected {expected_sha256}. ⛔ The address answered "
            "with something other than the pinned artifact."
        )

    prior_agreed: bool | None = None
    if cache.is_file():
        prior_agreed = hashlib.sha256(cache.read_bytes()).hexdigest() == digest
        if not prior_agreed:
            raise AcquisitionError(
                f"{url}: the bytes retrieved now do not match the copy at {cache}. ⛔ One "
                "address has served two different artifacts; which one a fixture should "
                "pin is not this recorder's decision."
            )
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_bytes(payload)

    return Retrieval(
        url=url,
        final_url=final_url,
        status=status,
        size_bytes=len(payload),
        sha256=digest,
        validators={
            name: headers[header]
            for header, name in _VALIDATORS.items()
            if headers.get(header)
        },
        payload=payload,
        prior_copy_agreed=prior_agreed,
    )
