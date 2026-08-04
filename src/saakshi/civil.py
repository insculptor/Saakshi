"""Resolved civil inputs — the thing that keeps a corpus samplable after its source stops.

⭐ **The rule this module exists to enforce.** A continuity corpus is sampled from an engine
that is going away. Anything a row leaves *unresolved* — a civil clock time still needing a
timezone database, a place name still needing a geocoder — is a dependency on state the
engine's deployment happened to hold, and it becomes unrecoverable the moment that
deployment stops. An input the recorder **resolves into the row** is an input nothing has to
hold again.

So a grid point is not a date, a zone name and a place. It is an **instant** (with the offset
that produced it written down beside it) and a **coordinate** (with the place name demoted to
a label). ⛔ `CivilInstant` cannot be constructed any other way; there is no permissive path,
because a half-resolved row looks exactly like a resolved one at read time.

⚠ The offset is the authority; the database identity is context. A later run that disagrees
with a recorded offset has found a rule change, which is a finding — not a reason to prefer
the fresher answer.
"""

from __future__ import annotations

import datetime as _dt
import zoneinfo
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any


class CivilResolutionError(Exception):
    """Raised when an input cannot be resolved to the form a fixture may carry."""


# --------------------------------------------------------------------------------------
# Which rule set actually answered
# --------------------------------------------------------------------------------------


@lru_cache(maxsize=1)
def tzdb_identity() -> dict[str, Any]:
    """Identify the timezone rules in force, as far as they can honestly be identified.

    ⚠ **This is deliberately not a clean answer, because there is not one.** `zoneinfo`
    searches a filesystem path first and falls back to the packaged rule set only if the key
    is not found there, and it does not report which one answered. Two machines running the
    same pinned requirements can therefore resolve the same instant differently — which is
    exactly why the *offset* is what a row carries and this block is only context.

    The system path is inspected directly rather than inferred, and when the deployed
    version cannot be read it is recorded as unreadable rather than guessed.
    """
    packaged: str | None = None
    try:  # the packaged fallback, present only if the wheel is installed
        import tzdata  # type: ignore[import-not-found]

        packaged = getattr(tzdata, "IANA_VERSION", None)
    except Exception:
        packaged = None

    search_path = [str(p) for p in zoneinfo.TZPATH]
    system_version: str | None = None
    system_dir: str | None = None
    for entry in zoneinfo.TZPATH:
        root = Path(entry)
        if not root.is_dir():
            continue
        system_dir = system_dir or str(root)
        # Distributions ship the release under one of these two markers. Absent on some,
        # which is a real limit and is reported as one.
        for marker in ("+VERSION", "tzdata.zi"):
            candidate = root / marker
            if candidate.is_file():
                try:
                    text = candidate.read_text(encoding="utf-8", errors="replace")
                except OSError:  # pragma: no cover - unreadable but present
                    continue
                if marker == "+VERSION":
                    system_version = text.strip()
                else:
                    first = text.splitlines()[0] if text else ""
                    if "version" in first:
                        system_version = first.split()[-1]
                if system_version:
                    break
        if system_version:
            break

    return {
        "search_path": search_path,
        "system_directory": system_dir,
        "system_version": system_version or "unreadable",
        "packaged_version": packaged or "absent",
        "answered_by": (
            "unreported — zoneinfo does not say whether the system path or the packaged "
            "rule set supplied a key; the resolved offset on each row is what a consumer "
            "should rely on"
        ),
    }


# --------------------------------------------------------------------------------------
# A resolved grid point
# --------------------------------------------------------------------------------------


@dataclass(frozen=True)
class CivilInstant:
    """A civil date-time whose offset and coordinate are already resolved.

    ⛔ Build with :func:`resolve`. The constructor is not the entry point, because the
    invariant this class carries is about *how* the fields were obtained.
    """

    grid_id: str
    stratum: str
    civil: str  # ISO-8601, no offset — the local clock reading, as a human would give it
    zone: str  # IANA key, recorded so a reading is explicable
    utc_offset_seconds: int  # ⭐ the authority: what the rules said, at this instant
    utc: str  # ISO-8601 Z — derivable from the two above, written out so nothing recomputes
    latitude: float
    longitude: float
    place_label: str | None = None  # ⛔ a label. Never an input to anything.

    def as_row(self) -> dict[str, Any]:
        """The resolved-input block every row carries."""
        out: dict[str, Any] = {
            "grid_id": self.grid_id,
            "stratum": self.stratum,
            "civil_local": self.civil,
            "zone": self.zone,
            "utc_offset_seconds": self.utc_offset_seconds,
            "utc": self.utc,
            "latitude": self.latitude,
            "longitude": self.longitude,
        }
        if self.place_label is not None:
            out["place_label"] = self.place_label
        return out

    def as_naive_local(self) -> _dt.datetime:
        """The local clock reading, tz-naive — the form a caller usually wants."""
        return _dt.datetime.fromisoformat(self.civil)


def resolve(
    *,
    grid_id: str,
    stratum: str,
    civil: _dt.datetime,
    zone: str,
    latitude: float,
    longitude: float,
    place_label: str | None = None,
) -> CivilInstant:
    """Resolve a grid point, refusing anything that would leave a row half-resolved.

    ⛔ Refuses: an aware `civil` (the offset must be *derived* here, not asserted by the
    caller), an unknown zone, an out-of-range coordinate, and any instant whose offset the
    rules decline to give.

    ⚠ **Ambiguous and non-existent local times are refused, not silently folded.** A clock
    reading inside a DST transition is either two instants or none; picking one is a choice
    the recorder is not entitled to make, and a fold picked here would be invisible in the
    fixture forever.
    """
    if civil.tzinfo is not None:
        raise CivilResolutionError(
            f"{grid_id}: `civil` must be a naive local clock reading — an offset supplied by "
            "the caller is an assertion, and this function exists to derive it"
        )
    if not -90.0 <= latitude <= 90.0:
        raise CivilResolutionError(f"{grid_id}: latitude {latitude!r} out of range")
    if not -180.0 <= longitude <= 180.0:
        raise CivilResolutionError(f"{grid_id}: longitude {longitude!r} out of range")

    try:
        tz = zoneinfo.ZoneInfo(zone)
    except Exception as exc:
        raise CivilResolutionError(f"{grid_id}: unknown timezone {zone!r}") from exc

    aware = civil.replace(tzinfo=tz)
    offset = aware.utcoffset()
    if offset is None:
        raise CivilResolutionError(
            f"{grid_id}: {zone!r} gave no offset for {civil.isoformat()}"
        )

    # ⚠ Both transition pathologies, caught rather than folded.
    other = aware.replace(fold=1 - aware.fold)
    if other.utcoffset() != offset:
        raise CivilResolutionError(
            f"{grid_id}: {civil.isoformat()} is ambiguous or non-existent in {zone!r} "
            f"(fold 0 -> {offset}, fold 1 -> {other.utcoffset()}). ⛔ A grid point inside a "
            "transition is refused: choosing a fold here would be an unrecorded decision"
        )

    total = offset.total_seconds()
    if total != int(total):
        raise CivilResolutionError(
            f"{grid_id}: {zone!r} offset {offset!r} is not a whole number of seconds"
        )

    utc = aware.astimezone(_dt.timezone.utc)
    return CivilInstant(
        grid_id=grid_id,
        stratum=stratum,
        civil=civil.isoformat(timespec="seconds"),
        zone=zone,
        utc_offset_seconds=int(total),
        utc=utc.isoformat(timespec="seconds").replace("+00:00", "Z"),
        latitude=float(latitude),
        longitude=float(longitude),
        place_label=place_label,
    )
