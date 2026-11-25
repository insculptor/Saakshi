"""R1 — Mercury's and the Sun's geocentric states around each published Mercury event of a transcription file.

For every event a transcription file (named by its digest) records with a civil UT instant, the publisher's ephemeris
service is asked for the geocentric ICRF states of Mercury (199) and of the Sun (10), geometric and with light-time
and stellar aberration, on a lattice of TDB instants a sixteenth of a day apart covering the printed instant ± 1 day.
Every value is written down as printed, with its bit pattern.

* ⭐ **The lattice is declared, never interpolated**: every TDB Julian day ``k/16`` with ``u - 1 - 1/16 <= k/16 <=
  u + 1 + 1/16``, ``u`` the printed UT instant read as a Julian day. The sixteenth-of-a-day margin on each side is
  what lets a UT instant stand for the window without converting it to TDB (the two differ by about a minute in
  these years); ⛔ no instant is converted, and none is between lattice points. Windows that overlap are one set of
  instants; each instant keeps every event that put it there.
* ⭐ **Everything else is the geocentric grid's, by import**: the request set (centre, frame, system, scale, units,
  table), the response's split, every statement each answer is held to (DE441 for both bodies and the centre), the
  live and cache-read paths.
* ⛔ **No station is found here.** The rows are states at lattice instants; locating a zero of any rate is the
  consumer's. Every section is ``reference_only``.
* ⛔ **Recorder, never explainer.**

Usage:
    python generators/r1_station_windows.py --stations FILE --stations-sha256 HEX --out DIR --budget-row ROW
        [--cache DIR] [--from-cache] [--plan-only]
"""

from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
import math
import re
import sys
import time
from pathlib import Path
from typing import Callable

HERE = Path(__file__).resolve().parent
sys.dont_write_bytecode = True
for _path in (str(HERE.parent / "src"), str(HERE)):
    if _path not in sys.path:
        sys.path.insert(0, _path)

from saakshi import service  # noqa: E402
from saakshi.acquisition import USER_AGENT, AcquisitionError, retrieve  # noqa: E402
from saakshi.fixture import Header, describe_reserved_names, write_jsonl  # noqa: E402
from saakshi.provenance import generator_for, host_record, today  # noqa: E402
from saakshi.service import ServiceFormatError  # noqa: E402

import r1_geocentric_vectors as grid  # noqa: E402

SCRIPT = "generators/r1_station_windows.py"
VALUES_PATH = "service/r1-station-windows.jsonl"
ACQUISITION_PATH = "service/r1-station-windows-acquisition.jsonl"
CACHE_SUBDIRECTORY = "r1-station-windows"
CENTER = "500@399"
Refusal = grid.Refusal

TARGETS: tuple[dict[str, str], ...] = (
    {"command": "199", "label": "Mercury", "point": "body_centre"},
    {"command": "10", "label": "Sun", "point": "body_centre"},
)
DEFAULT_CORRECTIONS = "NONE,LT+S"
HALF_WIDTH_DAYS = 1.0
MARGIN_DAYS = 1.0 / 16.0
STEP_PER_DAY = 16
WINDOW_RULE = ("every TDB Julian day k/16 with u - 1 - 1/16 <= k/16 <= u + 1 + 1/16, u the printed UT instant read as "
               "a Julian day; ⛔ no instant converted between scales, none between lattice points")


def events(path: Path, expected: str) -> tuple[list[dict], dict]:
    """Every row of the transcription that carries a civil UT instant, with where it came from."""
    data = path.read_bytes()
    actual = hashlib.sha256(data).hexdigest()
    if actual != expected:
        raise Refusal(f"the transcription's sha256 is {actual}, not {expected}")
    lines = data.decode("utf-8").splitlines()
    header = json.loads(lines[0])
    out = []
    for line in lines[1:]:
        row = json.loads(line)
        stamp = row.get("utc_from_printed")
        if stamp is None:
            continue
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}", stamp):
            raise Refusal(f"an event's instant {stamp!r} is not a civil minute")
        out.append({"section": row["section"], "utc": stamp, "event": row.get("printed_event")
                    or row.get("printed_phenomenon")})
    if not out:
        raise Refusal("the transcription records no event with an instant")
    return out, {"sha256": actual, "title": header.get("title"), "sections": sorted({e["section"] for e in out})}


def lattice(found: list[dict]) -> list[grid.Epoch]:
    by_k: dict[int, list[str]] = {}
    for e in found:
        u = grid.modes.julian_day(e["utc"] + ":00")
        low = math.ceil((u - HALF_WIDTH_DAYS - MARGIN_DAYS) * STEP_PER_DAY)
        high = math.floor((u + HALF_WIDTH_DAYS + MARGIN_DAYS) * STEP_PER_DAY)
        for k in range(low, high + 1):
            reason = f"window:{e['section']}:{e['utc']}"
            reasons = by_k.setdefault(k, [])
            if reason not in reasons:
                reasons.append(reason)
    instants = [grid.Epoch(jd_tdb=k / STEP_PER_DAY, reasons=by_k[k]) for k in sorted(by_k)]
    for e in instants:
        grid._exact(e.jd_tdb, what="a window instant")
    return instants


def plan(instants: list[grid.Epoch], *, corrections: list[str]) -> list[dict]:
    pieces = grid.chunks(instants)
    return [{"request_id": f"{grid.CORRECTION_SLUGS[c]}-{t['command']}-c{i:02d}", "correction": c, "target": t,
             "chunk": i, "instants": piece,
             "query": grid.query_for(command=t["command"], center=CENTER, correction=c, instants=piece)}
            for c in corrections for t in TARGETS for i, piece in enumerate(pieces)]


def cache_stem(cache: Path, *, correction: str, digest: str, command: str, index: int) -> Path:
    return (cache / CACHE_SUBDIRECTORY / "center_500_399" / f"corr_{grid.CORRECTION_SLUGS[correction]}"
            / f"epochs_{digest[:16]}_by_{grid.CHUNK_SIZE}" / f"{command}-c{index:02d}")


def read(requests: list[dict], *, cache: Path, digest: str, from_cache: bool,
         sleep: Callable[[float], None] | None = None, fetch: Callable[..., object] | None = None):
    sleep, fetch = sleep or time.sleep, fetch or retrieve
    out, version = [], None
    for index, request in enumerate(requests):
        stem = cache_stem(cache, correction=request["correction"], digest=digest,
                          command=request["target"]["command"], index=request["chunk"])
        if from_cache:
            got = grid.read_cached(request, stem)
        else:
            if index:
                sleep(grid.REQUEST_INTERVAL_SECONDS)
            stem.parent.mkdir(parents=True, exist_ok=True)
            got = grid.read_live(request, stem, sleep=sleep, fetch=fetch)
        response = grid.split(got.payload, query=request["query"])
        version = grid.hold(response, request, center=CENTER, version=version)
        out.append((request, got, response))
        print(f"  {request['request_id']}: {len(response.data_rows)} instants, interface {version}, "
              f"resource {got.resource_sha256[:12]}... ({got.kind})", flush=True)
    return out, version


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--stations", required=True, type=Path)
    parser.add_argument("--stations-sha256", required=True)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--budget-row", required=True, help="⚠ a placeholder name; the consumer labels its rows")
    parser.add_argument("--cache", default=HERE.parent / "cache", type=Path)
    parser.add_argument("--corrections", default=DEFAULT_CORRECTIONS)
    parser.add_argument("--from-cache", action="store_true")
    parser.add_argument("--plan-only", action="store_true")
    args = parser.parse_args(argv)
    generator = None if args.plan_only else generator_for(HERE / Path(SCRIPT).name)
    print(describe_reserved_names())
    corrections = [c.strip() for c in args.corrections.split(",") if c.strip()]
    found, source = events(args.stations, args.stations_sha256)
    instants = lattice(found)
    digest = grid.epoch_set_digest(instants)
    requests = plan(instants, corrections=corrections)
    print(f"{len(found)} events, {len(instants)} instants (set {digest[:16]}), {len(requests)} requests; "
          f"as {USER_AGENT}", flush=True)
    if args.plan_only:
        return 0
    values_path, record_path = args.out / VALUES_PATH, args.out / ACQUISITION_PATH
    for path in (values_path, record_path):
        if path.exists():
            raise Refusal(f"{path} exists; a record is never overwritten")
    answered, version = read(requests, cache=args.cache, digest=digest, from_cache=args.from_cache)
    kind = "cache_read" if args.from_cache else "live_request"
    first = {}
    for r, _g, s in answered:
        first.setdefault(r["correction"], s)
    sections = [f"state_{grid.CORRECTION_SLUGS[c]}" for c in corrections]
    header = Header(
        fixture_kind="numeric_pin", reference="R1", generator=generator, generated=today(),
        title="Mercury's and the Sun's geocentric ICRF states around published Mercury events",
        oracle={
            "publisher": "JPL Solar System Dynamics", "service": "Horizons", "endpoint": service.ENDPOINT,
            "user_agent": USER_AGENT, "interface": {"source": grid.EXPECTED_INTERFACE_SOURCE, "version": version},
            "acquired_on": sorted({g.acquired_on for _r, g, _s in answered}),
            "solutions_that_answered": sorted({s.service_state["target_solution"] for _r, _g, s in answered}),
            "the_service_on_each_correction": [
                {"vec_corr": c, "output_type": first[c].stated["output_type"],
                 "aberrations_and_corrections": first[c].correction_paragraph} for c in corrections],
            "time_scale_statement": first[corrections[0]].time_statement,
        },
        request={
            "endpoint": service.ENDPOINT, "user_agent": USER_AGENT,
            "common_query": [{"parameter": k, "value": v} for k, v in sorted(grid.COMMON_QUERY.items())],
            "center": {"command": CENTER, **grid.CENTERS[CENTER]}, "targets": [dict(t) for t in TARGETS],
            "corrections": [{"vec_corr": c, "documented_as": grid.CORRECTIONS[c]} for c in corrections],
            "events": {"from": source, "count": len(found), "list": found},
            "instants": {"rule": WINDOW_RULE, "count": len(instants), "set_sha256": digest,
                         "chunk_size": grid.CHUNK_SIZE, "values": [e.as_json() for e in instants]},
            "queries": [{"request_id": r["request_id"], "query": [{"parameter": k, "value": v}
                                                                  for k, v in sorted(r["query"].items())],
                         "resource_sha256": g.resource_sha256} for r, g, _s in answered],
            "one_at_a_time": True,
        },
        classification={s: {"class": "reference_only"} for s in sections},
        budget_row=args.budget_row,
        row_schema={"value": "THE PIN — the nine printed values in `component_order`",
                    "component_order": list(grid.COMPONENTS), "component_units": list(grid.COMPONENT_UNITS)},
        summary={"rows": sum(len(s.data_rows) for _r, _g, s in answered), "requests": len(answered),
                 "host": host_record()},
        notes=["⛔ No station is located here: the rows are states at lattice instants.",
               "⚠ The events' instants are as the transcription records them (printed UT, or a printed local time "
               "taken back by the publisher's own stated offset); which of them, if any, a consumer uses is its own.",
               service.REPRODUCIBILITY_CONDITION, service.ACQUISITION_LIMIT],
    )
    written = write_jsonl(values_path, header, grid.rows_for(answered, center=CENTER))
    values_sha256 = hashlib.sha256(values_path.read_bytes()).hexdigest()
    record = grid.build_acquisition_header(kind=kind, values_sha256=values_sha256, generator=generator,
                                           version=version)
    record = dataclasses.replace(record, title="How the states around the published Mercury events were obtained",
                                 oracle={**record.oracle, "values_file": {"path": VALUES_PATH,
                                                                          "sha256": values_sha256}})
    write_jsonl(record_path, record, grid.acquisition_rows(answered, kind=kind))
    print(f"wrote {written} rows -> {values_path} (sha256 {values_sha256[:16]}...); record ({kind}) -> {record_path}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (Refusal, ServiceFormatError, AcquisitionError) as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        raise SystemExit(2)
