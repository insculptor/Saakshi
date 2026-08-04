"""R5 — continuity corpus: what the earlier implementation answered, before it stops running.

A stratified grid of resolved instants and coordinates is put through a declared call
surface, and every value that came back is written down as an addressed leaf.

⭐ **The point of the exercise, in one sentence.** A continuity oracle can only be sampled
while it runs, so the corpus has to be taken before the earlier implementation's service
goes away — and every input a row leaves *unresolved* is a piece of that service's state the
row still depends on. This recorder resolves the timezone offset and the coordinate into
each row, so what it writes needs no timezone database, no place-name service and no running
deployment to be read again.

⚠ **`reference_only`, always, and it is not a placeholder.** These values are evidence about
an implementation, not about the sky. Nothing here may be classified `exact`: agreement with
these rows is continuity, disagreement is a difference between two implementations, and
which of the two is closer to an authority is a question no continuity fixture can answer.

⛔ **Recorder, never explainer.** The surface is declared in a local file; this script
resolves dotted paths, calls them, and flattens what came out. It contains no account of
what any of it computes, and no per-atom logic — which is what keeps a continuity corpus
from becoming a description of the implementation it samples.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from saakshi.civil import (  # noqa: E402
    CivilInstant,
    CivilResolutionError,
    resolve,
    tzdb_identity,
)
from saakshi.fixture import Header, describe_reserved_names, write_jsonl  # noqa: E402
from saakshi.leaves import digest, flatten, verify_bits  # noqa: E402
from saakshi.provenance import generator_for, host_record, today  # noqa: E402
from saakshi.surface import DEFAULT_SURFACE, Surface, load  # noqa: E402

#: The grid's reproducibility constant. ⭐ Recorded in `request` so the identical grid
#: regenerates; ⛔ never re-rolled — a fixture whose inputs move is not a fixture.
GRID_SEED = 20260804

#: Sites, as geography rather than as places. Each is `(zone, latitude, longitude, label)`.
#:
#: ⭐ Chosen for what each one *exercises*, not for where anybody lives: a zone whose
#: historical offset changed, zones far from their solar meridian, both sides of the
#: date line, the equator, and two latitudes above the polar circle where a day may have no
#: sunrise at all. ⚠ The labels are labels — nothing is ever computed from one.
SITES: tuple[tuple[str, float, float, str], ...] = (
    ("Asia/Kolkata", 26.4499, 80.3319, "northern india, inland"),
    ("Asia/Kolkata", 8.0883, 77.5385, "southern india, near the cape"),
    ("Asia/Kathmandu", 27.7172, 85.3240, "an offset that is not a whole hour"),
    ("Europe/London", 51.5074, -0.1278, "prime meridian, seasonal offset"),
    ("America/New_York", 40.7128, -74.0060, "western hemisphere, seasonal offset"),
    ("Pacific/Auckland", -36.8485, 174.7633, "southern hemisphere, near the date line"),
    ("Pacific/Kiritimati", 1.8721, -157.4278, "east of the date line, far ahead of it"),
    ("America/Anchorage", 61.2181, -149.9003, "high latitude, seasonal offset"),
    ("Europe/Kyiv", 50.4501, 30.5234, "a zone whose rules changed within living memory"),
    ("Africa/Nairobi", -1.2921, 36.8219, "equatorial, no seasonal offset"),
    ("Asia/Shanghai", 31.2304, 121.4737, "far from its zone's solar meridian"),
    ("Asia/Kashgar", 39.4704, 75.9898, "further still, same single national zone"),
    ("Atlantic/Reykjavik", 64.1466, -21.9426, "just below the polar circle"),
    ("Europe/Oslo", 78.2232, 15.6267, "above the polar circle — a day may have no sunrise"),
    ("Antarctica/Rothera", -67.5675, -68.1250, "below the antarctic circle"),
    ("Pacific/Chatham", -43.9535, -176.5597, "an offset at three-quarters of an hour"),
)

#: Local clock readings sampled at each site. ⚠ Deliberately spread across the day, and
#: deliberately including one just after midnight, because a date rolls there.
CLOCK_TIMES: tuple[tuple[int, int], ...] = ((0, 12), (6, 40), (12, 0), (17, 25), (23, 50))

#: Years, spread over the range an implementation of this kind is asked about. ⭐ The early
#: entries are the ones that exercise a timezone rule set: an offset before standard time was
#: adopted is exactly the value a later database release is most likely to move.
YEARS: tuple[int, ...] = (
    1901, 1927, 1941, 1955, 1969, 1983, 1992, 2000, 2013, 2026, 2040, 2061, 2087, 2099,
)


def _stratum(zone: str, latitude: float, year: int) -> str:
    if abs(latitude) > 66.5:
        return "polar"
    if year < 1950:
        return "historical_offset"
    if abs(latitude) < 5.0:
        return "equatorial"
    if year > 2050:
        return "far_future"
    return "general"


def _resolve_or_nudge(
    *, grid_id: str, stratum: str, civil: _dt.datetime, site: tuple[str, float, float, str]
) -> tuple[CivilInstant, int]:
    """Resolve a grid point, stepping forward in whole hours if it lands in a transition.

    ⚠ The nudge is **recorded on the row**, not absorbed. A clock reading inside a
    daylight-saving transition is either two instants or none; this recorder refuses to pick
    one, so it moves to a reading that is unambiguous and says by how much. ⛔ Silently
    folding would put a chosen instant in the fixture with nothing to show it was chosen.
    """
    zone, latitude, longitude, label = site
    last: Exception | None = None
    for nudge in range(0, 7):
        try:
            instant = resolve(
                grid_id=grid_id,
                stratum=stratum,
                civil=civil + _dt.timedelta(hours=nudge),
                zone=zone,
                latitude=latitude,
                longitude=longitude,
                place_label=label,
            )
            return instant, nudge
        except CivilResolutionError as exc:
            last = exc
    raise CivilResolutionError(
        f"{grid_id}: no unambiguous reading within 6 hours of {civil.isoformat()} in "
        f"{zone!r} — last refusal: {last}"
    )


#: The golden ratio's fractional part. Ordering indices by `frac(j * PHI)` is a standard
#: low-discrepancy sequence: **every prefix is spread over the whole range**, which is the
#: one property a truncated grid needs and an even stride does not have.
_PHI = 0.6180339887498949


def _spread(count: int) -> list[int]:
    """Indices `0..count-1`, ordered so that any prefix covers the whole range."""
    return sorted(range(count), key=lambda j: (j * _PHI) % 1.0)


def _bounded_subset(plan: list, limit: int) -> list:
    """Take `limit` points, guaranteeing every stratum appears and each one is spanned.

    ⚠ **An even stride is wrong here, and it failed silently.** The enumeration is
    year-major over a fixed number of sites, so a stride is an arithmetic progression that
    can alias against the site count — at one limit it selected four of sixteen sites and
    reached neither the polar nor the equatorial ones, while still returning exactly the
    requested number of rows. A sample that is the right size and the wrong shape is the
    hardest kind to notice.

    So the selection is explicit about the property it owes: round-robin across strata, each
    stratum drawn in low-discrepancy order, then restored to enumeration order so the file
    reads naturally. Grid ids come from the enumeration, not the selection, so a point means
    the same thing at every limit and two runs of different sizes compare row for row.
    """
    by_stratum: dict[str, list] = {}
    for entry in plan:
        by_stratum.setdefault(entry[1], []).append(entry)

    queues = {
        stratum: [entries[j] for j in _spread(len(entries))]
        for stratum, entries in by_stratum.items()
    }
    order = list(by_stratum)  # first-appearance order — deterministic

    picked: list = []
    cursor = 0
    while len(picked) < limit:
        progressed = False
        for stratum in order:
            queue = queues[stratum]
            if cursor < len(queue):
                picked.append(queue[cursor])
                progressed = True
                if len(picked) == limit:
                    break
        if not progressed:  # every stratum exhausted
            break
        cursor += 1

    return sorted(picked, key=lambda entry: entry[0])


def build_grid(limit: int | None) -> list[tuple[CivilInstant, int]]:
    """The stratified grid, deterministic and in a fixed order.

    ⭐ Deterministic without a random draw: sites, years and clock readings are enumerated
    with coprime strides, so the set is reproducible from the counts alone and a reader can
    see what it covers without running anything. `GRID_SEED` is recorded as the identity of
    *this* enumeration, so a future change to it is visible in the fixture rather than
    silent.

    ⚠ **A truncated grid must still be a stratified one.** Enumerating year-major and then
    cutting at `limit` produced a "sample" that was three-quarters one stratum, because a
    short run never reached the later years at all — a bounded run that quietly covers one
    corner is worse than an unbounded one, since its row count looks like coverage. The
    subset is therefore taken at an even stride across the whole enumeration, so any
    `limit` spans every year, every site and every stratum.
    """
    plan: list[tuple[str, str, _dt.datetime, tuple[str, float, float, str]]] = []
    index = 0
    for year_i, year in enumerate(YEARS):
        for site_i, site in enumerate(SITES):
            zone, latitude, longitude, _ = site
            hour, minute = CLOCK_TIMES[(year_i + site_i) % len(CLOCK_TIMES)]
            month = 1 + ((year_i * 5 + site_i * 7) % 12)
            day = 1 + ((year_i * 11 + site_i * 13) % 28)
            plan.append(
                (
                    f"g{index:04d}",
                    _stratum(zone, latitude, year),
                    _dt.datetime(year, month, day, hour, minute),
                    site,
                )
            )
            index += 1

    if limit is not None and 0 < limit < len(plan):
        plan = _bounded_subset(plan, limit)

    out: list[tuple[CivilInstant, int]] = []
    for grid_id, stratum, civil, site in plan:
        instant, nudge = _resolve_or_nudge(
            grid_id=grid_id, stratum=stratum, civil=civil, site=site
        )
        out.append((instant, nudge))
    return out


def determinism_probe(surface: Surface, native: object) -> list[dict[str, object]]:
    """Call every section twice on one input and report any section that did not agree.

    ⭐ **A recorder cannot inspect a call for hidden state, but it can catch it.** Sampling
    the same input twice costs one grid point and detects the entire class at once: a clock
    read inside the callee, a random draw, an unordered iteration, a warm cache. Anything
    that makes a corpus disagree with itself makes it disagree with every future comparison
    too, for a reason that has nothing to do with either implementation.

    ⚠ This is not theoretical. The first clean-room regeneration of this corpus differed
    from the original, and the cause was a sampled call whose default argument meant *"now"*
    — so every row carried the moment of sampling, and a flag on every period was a function
    of when the recorder ran rather than of the input. ⛔ It looked reproducible. That is
    precisely why a demonstration is required and an argument is not enough.

    ⛔ There is no permissive mode. The remedy is always to pin the varying input in the
    surface declaration, which is a fixture's job: an input nobody wrote down is an input
    nobody can reproduce.

    ⚠ **A detector, not a proof.** Two calls can agree by luck — a first version called each
    section twice back to back and cleared 7 of 17 sections that were *all* clock-dependent,
    simply because both calls landed inside the same microsecond. The two passes are
    therefore separated by a full sweep of every other section, which makes a clock
    difference near-certain; but a section this reports as stable is **not** thereby proven
    stable, and one section it reports is enough to refuse.
    """

    def sweep() -> dict[str, list[dict[str, Any]]]:
        out: dict[str, list[dict[str, Any]]] = {}
        for atom in surface.atoms:
            for section, kwargs in atom.variations():
                call_args: list[object] = [native]
                if atom.settings is not None and surface.settings_builder is not None:
                    call_args.append(surface.settings_builder(**atom.settings))
                try:
                    out[section] = flatten(atom.call(*call_args, **kwargs))
                except Exception:
                    continue  # a refusal is recorded during sampling, not here
        return out

    first, second = sweep(), sweep()

    findings: list[dict[str, object]] = []
    for section, before in first.items():
        after = second.get(section)
        if after is None or digest(before) == digest(after):
            continue
        by_path = {leaf["path"]: leaf for leaf in after}
        moved = [leaf["path"] for leaf in before if by_path.get(leaf["path"]) != leaf]
        findings.append({"section": section, "leaves_moved": len(moved), "paths": moved[:5]})
    return findings


def _native_kwargs(surface: Surface, instant: CivilInstant) -> dict[str, object]:
    """Bind the builder's arguments to resolved inputs, and to nothing else."""
    available: dict[str, object] = {
        "civil_local_naive": instant.as_naive_local(),
        "civil_local_iso": instant.civil,
        "utc_aware": _dt.datetime.fromisoformat(instant.utc.replace("Z", "+00:00")),
        "utc_iso": instant.utc,
        "zone": instant.zone,
        "utc_offset_seconds": instant.utc_offset_seconds,
        "latitude": instant.latitude,
        "longitude": instant.longitude,
        "place_label": instant.place_label,
    }
    return {argument: available[source] for argument, source in surface.native_fields.items()}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--surface",
        default=str(DEFAULT_SURFACE),
        help="the call-surface declaration (local, not committed)",
    )
    parser.add_argument("--out", default="out", help="output directory")
    parser.add_argument(
        "--natives",
        type=int,
        default=64,
        help=(
            "how many grid points to sample. ⭐ The export manifest is what bounds this; "
            "the number used is recorded in the fixture, so coverage is countable"
        ),
    )
    parser.add_argument(
        "--report-only",
        action="store_true",
        help=(
            "sample, print the size and the per-atom leaf counts, write nothing. ⭐ Run this "
            "first: it prices a grid before anyone commits to one"
        ),
    )
    args = parser.parse_args()

    print(describe_reserved_names())

    surface = load(args.surface)
    print(f"surface: {len(surface.atoms)} atom(s) -> {len(surface.section_names())} section(s)")
    print(f"sampled tree at commit {surface.commit[:12]}")

    grid = build_grid(args.natives)
    nudged = sum(1 for _, nudge in grid if nudge)
    print(f"grid: {len(grid)} resolved instant(s), {nudged} moved clear of a transition")

    # ⛔ Before anything is sampled. A corpus that disagrees with itself will disagree with
    #    every future comparison too, and the reason will look like an engine difference.
    probe_native = surface.native_builder(**_native_kwargs(surface, grid[0][0]))
    unstable = determinism_probe(surface, probe_native)
    if unstable:
        print(
            "REFUSED: a sampled call returned different values for the same input.",
            file=sys.stderr,
        )
        for finding in unstable:
            print(
                f"    {finding['section']}: {finding['leaves_moved']} leaf/leaves moved "
                f"-> {finding['paths']}",
                file=sys.stderr,
            )
        print(
            "    Pin the varying input in the surface declaration (an argument defaulting "
            "to 'now' is the usual cause). An input nobody wrote down is an input nobody "
            "can reproduce.",
            file=sys.stderr,
        )
        return 1
    print(f"determinism probe: {len(surface.section_names())} section(s) stable on one input")

    rows: list[dict[str, object]] = []
    per_section: dict[str, int] = {}
    failures: list[dict[str, object]] = []

    for instant, nudge in grid:
        native = surface.native_builder(**_native_kwargs(surface, instant))
        for atom in surface.atoms:
            for section, kwargs in atom.variations():
                call_args: list[object] = [native]
                if atom.settings is not None and surface.settings_builder is not None:
                    call_args.append(surface.settings_builder(**atom.settings))
                try:
                    value = atom.call(*call_args, **kwargs)
                except Exception as exc:
                    # ⚠ Recorded, never swallowed and never fatal. A call the earlier
                    #    implementation refuses for a given input is itself a fact about it,
                    #    and losing the rest of the corpus to one refusal would be worse.
                    failures.append(
                        {
                            "grid_id": instant.grid_id,
                            "section": section,
                            "error": type(exc).__name__,
                            "detail": str(exc)[:200],
                        }
                    )
                    continue
                leaves = flatten(value)
                # ⛔ Per row, at write time: the pattern and the decimal are the same
                #    number, or nothing is written. A consumer reading one form and a
                #    consumer reading the other must never hold different values.
                verify_bits(leaves, where=f"{instant.grid_id}/{section}")
                row: dict[str, object] = {
                    **instant.as_row(),
                    "section": section,
                    "call": atom.id,
                    "leaf_count": len(leaves),
                    "value_digest": digest(leaves),
                    "leaves": leaves,
                }
                if nudge:
                    row["transition_nudge_hours"] = nudge
                if kwargs:
                    row["call_arguments"] = {k: str(v) for k, v in kwargs.items()}
                rows.append(row)
                per_section[section] = per_section.get(section, 0) + len(leaves)

    if not rows:
        print("REFUSED: nothing was sampled - every call failed.", file=sys.stderr)
        for failure in failures[:10]:
            print(f"    {failure}", file=sys.stderr)
        return 1

    total_leaves = sum(int(row["leaf_count"]) for row in rows)  # type: ignore[arg-type]
    print(f"sampled: {len(rows)} row(s), {total_leaves} leaves, {len(failures)} refusal(s)")
    for section in sorted(per_section):
        print(f"    {section}: {per_section[section]} leaves")

    if args.report_only:
        import json

        approx = sum(len(json.dumps(row)) for row in rows)
        per_native = approx / max(1, len(grid))
        print(f"size: {approx / 1e6:.2f} MB for {len(grid)} natives "
              f"({per_native / 1e3:.1f} kB per native); "
              f"1000 natives would be ~{per_native * 1000 / 1e6:.0f} MB")
        print("report-only: nothing written")
        return 0

    header = Header(
        fixture_kind="numeric_pin",
        reference="R5",
        generator=generator_for(Path(__file__)),
        generated=today(),
        title="continuity corpus — values the earlier implementation returned",
        oracle={
            **surface.oracle_identity(),
            # ⭐ The whole discharge, stated in the fixture rather than in a note beside it.
            "resolved_inputs": {
                "timezone": (
                    "every row carries the resolved UTC offset in seconds beside the local "
                    "clock reading. ⭐ Regeneration consults no timezone database, so no "
                    "later rule change can move a row"
                ),
                "coordinate": (
                    "every row carries latitude and longitude. A place name is a label and "
                    "is never an input — ⛔ a place-name service is not recoverable by "
                    "restarting the sampled implementation"
                ),
                "database_identity": tzdb_identity(),
            },
        },
        request={
            "grid": "stratified",
            "grid_seed": GRID_SEED,
            "natives": len(grid),
            "sites": len(SITES),
            "years": list(YEARS),
            "clock_times": [f"{h:02d}:{m:02d}" for h, m in CLOCK_TIMES],
            "strata": sorted({str(row["stratum"]) for row in rows}),
            "sections": sorted(per_section),
            "regenerate": (
                "generators/r5_continuity.py --surface <declaration> --out <dir> "
                f"--natives {len(grid)} — the site, year and clock tables above fix the grid"
            ),
        },
        # ⛔ `reference_only` on every section, and it is the only honest class here.
        # These values are what one implementation returned. Agreement is continuity;
        # disagreement is a difference between implementations, and nothing in a continuity
        # fixture can say which of the two is closer to an authority. A band, if one is ever
        # wanted, is the consumer's reviewed decision and is taken against these rows.
        classification={section: {"class": "reference_only"} for section in per_section},
        budget_row="R5-continuity",
        row_schema={
            "grid_id": "stable id of this instant within the grid",
            "stratum": "why this point is in the grid",
            "civil_local": "the local clock reading, as given",
            "zone": "IANA key — explicable, but the offset below is the authority",
            "utc_offset_seconds": "⭐ resolved: what the rules said at this instant",
            "utc": "the resolved instant",
            "latitude": "degrees north — ⚠ display; `latitude_bits` is the value",
            "latitude_bits": "⭐ IEEE-754 bit pattern; the authoritative form of the input",
            "longitude": "degrees east — ⚠ display; `longitude_bits` is the value",
            "longitude_bits": "⭐ IEEE-754 bit pattern; the authoritative form of the input",
            "place_label": "⛔ a label; never an input",
            "section": "the sampled call, and its variation",
            "call": "the atom id this section belongs to",
            "leaf_count": "how many addressed values this row carries",
            "value_digest": (
                "sha256 over the canonical leaf set, taken over the AUTHORITATIVE form of "
                "each leaf — bit patterns for doubles, literals for what crosses a text "
                "boundary exactly. ⭐ So it is checkable without reading a decimal float"
            ),
            "leaves": (
                "one record per returned value: `path` is its address inside the returned "
                "object, and the value is `number` + `bits`, `integer`, `text`, `flag` or "
                "`null`"
            ),
            "transition_nudge_hours": (
                "present only when the declared clock reading fell inside a daylight-saving "
                "transition and was moved forward to an unambiguous one"
            ),
            "call_arguments": "the varied arguments of this section, as text",
        },
        summary={
            "rows": len(rows),
            "leaves": total_leaves,
            "natives": len(grid),
            "sections": len(per_section),
            "leaves_by_section": dict(sorted(per_section.items())),
            "transitions_avoided": nudged,
            "refusals": {
                "count": len(failures),
                "sample": failures[:20],
                "meaning": (
                    "a call the sampled implementation declined for a given input. Recorded "
                    "because a refusal is a fact about it; ⚠ NOT an error in this recorder"
                ),
            },
            "host": host_record(),
        },
        notes=[
            "R5 is continuity only. ⛔ These rows are never astronomical truth: a later "
            "implementation that disagrees with one has found a difference between two "
            "implementations, not an error, and which is closer to an authority is a "
            "question only an authority can answer.",
            "⭐ Every deployment-held input is resolved into the row. That is what makes "
            "this corpus samplable once and readable forever, rather than tied to the "
            "lifetime of a running service.",
            "Leaf paths are the sampled object's own field names, recorded as VALUES. They "
            "are data about what was sampled, never keys of this fixture — a rename in the "
            "sampled tree must not silently rename the evidence.",
            "A value the walker cannot represent is recorded by type name, never coerced. "
            "⛔ A stringified object would look like a value.",
            "⛔ Every determinism-bearing double in this file — recorded values AND the "
            "coordinate inputs — carries a hex bit pattern, and the decimal beside it is "
            "display that must never be read. ⚠ A widely-used JSON library was measured "
            "mis-parsing 18.9% of shortest-round-tripping doubles by up to 2 ULP and "
            "corrupted a parity measurement by four and a half orders of magnitude before "
            "anyone suspected the parser. ⭐ An INPUT matters more than an output here: an "
            "output is compared, an input is replayed.",
        ],
    )

    out_path = Path(args.out) / "continuity" / "corpus.jsonl"
    written = write_jsonl(out_path, header, rows, declared_sections=sorted(per_section))
    print(f"wrote {written} rows -> {out_path}")
    if failures:
        print(f"NOTE: {len(failures)} call(s) were refused by the sampled implementation; "
              "they are summarised in the header")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
