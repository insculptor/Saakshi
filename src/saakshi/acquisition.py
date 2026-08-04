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

⛔ **AND A RESOURCE IS NOT ALWAYS ITS PAYLOAD.** A published file can be fetched again
byte-identically; a *service* answers with a rendering, and the rendering carries material
that moves on every request — a generation stamp, a job identity — which belongs to the
transaction and not to the answer. The refusal below (*"one address has served two
artifacts"*) is therefore not a rule that merely inconveniences a service caller: pointed at
one unchanged it fires on the **second** request, every time, and would report a service as
having contradicted itself when nothing about the answer moved at all.

⭐ **So the fix is not to weaken the refusal, it is to say what the resource IS.** A caller
supplies a `canonical` form — the part of the payload that is a function of the request —
and the digest, the cache and the disagreement check all run over *that*. ⚠ Where no
canonical form is supplied the payload is the resource, the two digests are equal, and
`payload_is_the_resource` records that equality as a fact rather than leaving it assumed.
"""

from __future__ import annotations

import hashlib
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

USER_AGENT = "saakshi/0.1"

#: Payload bytes in, the resource's canonical bytes out. ⛔ It may raise
#: :class:`AcquisitionError`: an extractor that cannot find the material it exists to
#: exclude has had its assumptions outlived by the format, and continuing would digest a
#: volatile region as though it were stable.
CanonicalForm = Callable[[bytes], bytes]

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
    #: The canonical resource extracted from the payload, and its digest. ⚠ With no
    #: canonical form supplied these are the payload and its digest, which is the honest
    #: statement for a static file: the resource *is* the bytes.
    resource: bytes = b""
    resource_sha256: str = ""

    @property
    def payload_is_the_resource(self) -> bool:
        """Whether the bytes received are themselves the thing being pinned.

        ⭐ True for a published file, false for a service rendering. It is worth a field
        rather than an inference, because the two cases differ in what may be *written
        down*: where the payload is the resource its size and digest are properties of the
        answer, and where it is not they are properties of one transaction.
        """
        return self.sha256 == self.resource_sha256

    def as_record(self) -> dict[str, object]:
        """The retrieval's own fields, for a fixture row. ⛔ Never the payload.

        ⛔ **The payload's size and digest are emitted only where the payload is the
        resource.** Not squeamishness — measured: a service's response embeds a
        human-formatted generation stamp whose *width* moves with the day of the month, so
        even the byte count of a response is not a property of the answer. Writing one down
        produces a fixture that fails its own reproducibility check on the second Tuesday of
        a month, for a reason no reader would ever guess from the field name.
        """
        out: dict[str, object] = {
            "url": self.url,
            "final_url": self.final_url,
            "http_status": self.status,
            "resource_bytes": len(self.resource),
            "resource_sha256": self.resource_sha256,
            "payload_is_the_resource": self.payload_is_the_resource,
        }
        if self.payload_is_the_resource:
            out["size_bytes"] = self.size_bytes
            out["sha256"] = self.sha256
        return out


def retrieve(
    url: str,
    *,
    cache: Path,
    expected_sha256: str | None = None,
    canonical: CanonicalForm | None = None,
) -> Retrieval:
    """Fetch `url` over the network, and record what came back.

    A copy at `cache` is read *after* the fetch, compared, and then refreshed. ⛔ If it
    disagrees the whole run is refused: two different byte sequences have been served from
    one address, and which of them a fixture should pin is not a question a recorder may
    answer on its own.

    ⭐ **`canonical` says what the resource is**, and everything that judges identity — the
    digest, the cache, the disagreement refusal, `expected_sha256` — then runs over the
    resource rather than over the transaction that delivered it. ⚠ With no canonical form
    the two are the same bytes, so the refusal above is unchanged for every published file
    this repository reads.
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
    # ⛔ The canonical form runs BEFORE anything is compared or cached. An extractor that
    #    refuses here has found the response's shape moved out from under the rule that
    #    classifies it, and every judgement below would otherwise be made about a region
    #    whose contents are no longer what this instrument believes they are.
    resource = payload if canonical is None else canonical(payload)
    resource_digest = (
        digest if canonical is None else hashlib.sha256(resource).hexdigest()
    )

    # ⚠ Compared against the RESOURCE. For a published file that is the payload and the
    #   check is unchanged; for a service, pinning the transaction would be pinning the
    #   clock.
    if expected_sha256 is not None and resource_digest != expected_sha256:
        raise AcquisitionError(
            f"{url}: resource sha256 {resource_digest} != expected {expected_sha256}. "
            "⛔ The address answered with something other than the pinned artifact."
        )

    prior_agreed: bool | None = None
    if cache.is_file():
        prior_agreed = hashlib.sha256(cache.read_bytes()).hexdigest() == resource_digest
        if not prior_agreed:
            raise AcquisitionError(
                f"{url}: the resource retrieved now does not match the copy at {cache}. "
                "⛔ One address has served two different artifacts; which one a fixture "
                "should pin is not this recorder's decision."
            )
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_bytes(resource)

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
        resource=resource,
        resource_sha256=resource_digest,
    )
