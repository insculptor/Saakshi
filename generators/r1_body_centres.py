"""R1 — geocentric states of six planets' body centres in the ICRF, at the instants of an earlier geocentric grid.

The publisher's ephemeris service is asked, from the geocentre, for the state of the **body centre** of Mars,
Jupiter, Saturn, Uranus, Neptune and Pluto, in the ICRF, in TDB, in astronomical units and days, geometric and
with light-time and stellar aberration, at exactly the instants of an earlier geocentric values file read by its
digest — and every value is written down as printed, with its bit pattern, beside the service state that answered
it.

* ⭐ **A new target set, and therefore a generator of its own rather than a flag on the earlier one.** That
  generator asks for system barycentres, every one answered from the planetary solution, and holds every response
  to that one solution. A body centre is answered from a solution of its own per body (read from the service's own
  answers on 2026-11-25, :data:`TARGETS`), and for three of the six the service names that same solution for the
  geocentre too. A flag on the earlier generator would have put two different solution rules behind one script
  name; here each target carries the pair of solutions its answers must name, and a different pair is a stop.
* ⭐ **Everything else is the earlier generator's, by import**: the query every request shares, the response's
  split, the stamp cut out of the digest, the correction statements every response is held to, the live and
  cache-read paths, the row shape. Nothing is defined twice.
* ⭐ **The instants are not chosen here.** They are the distinct instants of the values file named on the command
  line by its sha256, with the reasons that file gives for each, so the two files are row-for-row at the same
  instants.
* ⛔ **No band and no derived value.** Every section is `reference_only`. ⛔ Nothing here relates a body centre to
  a barycentre, to another correction or to anything else: no difference is computed or written. Whatever such a
  difference is taken to mean is decided where it is used.
* ⛔ **Recorder, never explainer.** Nothing here says how the service computes anything.

Usage:
    python generators/r1_body_centres.py --grid-values VALUES.jsonl --grid-values-sha256 HEX --out DIR
        --budget-row ROW [--cache DIR] [--from-cache] [--plan-only] [--corrections NONE,LT+S]
"""

from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
import re
import sys
import time
from pathlib import Path
from typing import Callable

HERE = Path(__file__).resolve().parent
# ⛔ Importing a sibling generator must not write its bytecode beside it: an untracked file is a dirty tree.
sys.dont_write_bytecode = True
for _path in (str(HERE.parent / "src"), str(HERE)):
    if _path not in sys.path:
        sys.path.insert(0, _path)

from saakshi import service  # noqa: E402
from saakshi.acquisition import USER_AGENT, AcquisitionError, retrieve  # noqa: E402
from saakshi.fixture import Header, bits, describe_reserved_names, write_jsonl  # noqa: E402
from saakshi.provenance import generator_for, host_record, today  # noqa: E402
from saakshi.service import ServiceFormatError  # noqa: E402

import r1_geocentric_vectors as grid  # noqa: E402

SCRIPT = "generators/r1_body_centres.py"
VALUES_PATH = "service/r1-body-centres.jsonl"
ACQUISITION_PATH = "service/r1-body-centres-acquisition.jsonl"
CACHE_SUBDIRECTORY = "r1-body-centres"
CENTER = "500@399"

Refusal = grid.Refusal

#: The bodies asked, as sent, and ⛔ the solutions each answer must name — for the target and for the centre.
#: ⭐ Pinned from the service's own answers, read 2026-11-25: one geometric request per body at the two ends of the
#: instant set below, each naming exactly these. Any other pair on any later answer is a stop, before anything is
#: written.
TARGETS: tuple[dict[str, str], ...] = (
    {"command": "499", "label": "Mars", "point": "body_centre", "target_solution": "mar099",
     "center_solution": "DE441"},
    {"command": "599", "label": "Jupiter", "point": "body_centre", "target_solution": "jup365_merged",
     "center_solution": "jup365_merged"},
    {"command": "699", "label": "Saturn", "point": "body_centre", "target_solution": "sat441l",
     "center_solution": "DE441"},
    {"command": "799", "label": "Uranus", "point": "body_centre", "target_solution": "ura184_merged",
     "center_solution": "ura184_merged"},
    {"command": "899", "label": "Neptune", "point": "body_centre", "target_solution": "nep098_merged",
     "center_solution": "nep098_merged"},
    {"command": "999", "label": "Pluto", "point": "body_centre", "target_solution": "plu060_merged",
     "center_solution": "DE441"},
)

DEFAULT_CORRECTIONS = "NONE,LT+S"


# ======================================================================================
# The instants: another values file's, by digest
# ======================================================================================


def grid_instants(values_path: Path, expected_sha256: str) -> tuple[list[grid.Epoch], dict]:
    """The distinct instants of a geocentric values file, with the reasons its header gives each.

    ⛔ Refused unless the file's digest is the one given, unless every row's instant is one its header lists, and
    unless the header's own instant-set digest is the digest of what it lists.
    """
    data = values_path.read_bytes()
    actual = hashlib.sha256(data).hexdigest()
    if actual != expected_sha256:
        raise Refusal(f"the values file's sha256 is {actual}, not {expected_sha256}")
    lines = data.decode("utf-8").splitlines()
    header = json.loads(lines[0])
    if header.get("record") != "header":
        raise Refusal("the values file does not begin with its header")
    listed = header["request"]["instants"]
    instants: list[grid.Epoch] = []
    for entry in listed["values"]:
        jd = float(entry["jd_tdb"])
        if bits(jd) != entry["jd_tdb_bits"]:
            raise Refusal(f"the header lists {entry['jd_tdb']!r} with a pattern that is another number")
        instants.append(grid.Epoch(jd_tdb=jd, reasons=list(entry["reasons"])))
    if [e.jd_tdb for e in instants] != sorted({e.jd_tdb for e in instants}):
        raise Refusal("the header's instants are not distinct and in time order")
    if grid.epoch_set_digest(instants) != listed["set_sha256"]:
        raise Refusal("the header's instant-set digest is not the digest of the instants it lists")
    if len(instants) != listed["count"]:
        raise Refusal(f"the header lists {len(instants)} instants and counts {listed['count']}")
    on_rows = set()
    for number, line in enumerate(lines[1:], start=2):
        row = json.loads(line)
        if bits(float(row["jd_tdb"])) != row["jd_tdb_bits"]:
            raise Refusal(f"line {number}: jd_tdb and its pattern are different numbers")
        on_rows.add(row["jd_tdb_bits"])
    if on_rows != {bits(e.jd_tdb) for e in instants}:
        raise Refusal("the rows' instants are not the instants the header lists")
    source = {
        "values_file_sha256": actual,
        "title": header.get("title"),
        "generator": header.get("generator"),
        "rule": listed.get("rule"),
        "profile": listed.get("profile"),
        "count": listed["count"],
        "set_sha256": listed["set_sha256"],
    }
    return instants, source


# ======================================================================================
# The plan, and reading it
# ======================================================================================


def plan(instants: list[grid.Epoch], *, corrections: list[str]) -> list[dict]:
    pieces = grid.chunks(instants)
    requests = []
    for correction in corrections:
        for target in TARGETS:
            for index, piece in enumerate(pieces):
                requests.append({
                    "request_id": f"{grid.CORRECTION_SLUGS[correction]}-{target['command']}-c{index:02d}",
                    "correction": correction,
                    "target": target,
                    "chunk": index,
                    "instants": piece,
                    "query": grid.query_for(command=target["command"], center=CENTER, correction=correction,
                                            instants=piece),
                })
    return requests


def cache_stem(cache: Path, *, correction: str, digest: str, command: str, index: int) -> Path:
    """⭐ A subdirectory of its own, keyed on target, correction and instant set, so no barycentre response kept by
    the earlier generator can stand in for a body centre's."""
    safe = re.sub(r"[^A-Za-z0-9]+", "_", CENTER)
    return (cache / CACHE_SUBDIRECTORY / f"center_{safe}" / f"corr_{grid.CORRECTION_SLUGS[correction]}"
            / f"epochs_{digest[:16]}_by_{grid.CHUNK_SIZE}" / f"{command}-c{index:02d}")


def read(requests: list[dict], *, cache: Path, digest: str, from_cache: bool,
         sleep: Callable[[float], None] | None = None, fetch: Callable[..., object] | None = None):
    """Every request, in order, one at a time, each held — to its own target's solutions — before the next is
    sent."""
    sleep, fetch = sleep or time.sleep, fetch or retrieve
    out, version = [], None
    for index, request in enumerate(requests):
        target = request["target"]
        stem = cache_stem(cache, correction=request["correction"], digest=digest, command=target["command"],
                          index=request["chunk"])
        if from_cache:
            got = grid.read_cached(request, stem)
        else:
            if index:
                sleep(grid.REQUEST_INTERVAL_SECONDS)
            stem.parent.mkdir(parents=True, exist_ok=True)
            got = grid.read_live(request, stem, sleep=sleep, fetch=fetch)
        response = grid.split(got.payload, query=request["query"])
        version = grid.hold(response, request, center=CENTER, version=version,
                            solutions=(target["target_solution"], target["center_solution"]))
        out.append((request, got, response))
        print(f"  {request['request_id']}: {len(response.data_rows)} instants, "
              f"{response.service_state['target_solution']}/{response.service_state['center_solution']}, "
              f"interface {version}, resource {got.resource_sha256[:12]}... ({got.kind})", flush=True)
    return out, version


# ======================================================================================
# The records
# ======================================================================================


def build_values_header(answered, *, version: str, instants: list[grid.Epoch], source: dict,
                        corrections: list[str], generator, budget_row: str) -> Header:
    sections = [f"state_{grid.CORRECTION_SLUGS[c]}" for c in corrections]
    first_by_correction = {}
    for request, _got, response in answered:
        first_by_correction.setdefault(request["correction"], response)
    named = sorted({json.dumps({"target_command": r["target"]["command"],
                                "target_solution": s.service_state["target_solution"],
                                "center_solution": s.service_state["center_solution"]}, sort_keys=True)
                    for r, _g, s in answered})
    return Header(
        fixture_kind="numeric_pin",
        reference="R1",
        generator=generator,
        generated=today(),
        title="Geocentric states of six planets' body centres in the ICRF, at the instants of an earlier grid",
        oracle={
            "publisher": "JPL Solar System Dynamics",
            "service": "Horizons",
            "endpoint": service.ENDPOINT,
            "user_agent": USER_AGENT,
            "interface": {"source": grid.EXPECTED_INTERFACE_SOURCE, "version": version,
                          "accepted": [{"version": v, "why": w} for v, w in grid.ACCEPTED_INTERFACE_VERSIONS.items()]},
            "acquired_on": sorted({got.acquired_on for _r, got, _s in answered}),
            "solutions_named_per_target": [json.loads(text) for text in named],
            "earth_orientation_named": [json.loads(text) for text in sorted({json.dumps(
                {k: s.service_state.get(k) for k in ("earth_orientation_file", "earth_orientation_coverage")},
                sort_keys=True) for _r, _g, s in answered})],
            "stated_by_the_service": {
                **{k: v for k, v in first_by_correction[corrections[0]].stated.items() if k != "output_type"},
                "role": "what the service stated about its own output, held equal on every response",
            },
            "the_service_on_each_correction": [
                {"vec_corr": c, "documented_as": grid.CORRECTIONS[c],
                 "output_type": first_by_correction[c].stated["output_type"],
                 "aberrations_and_corrections": first_by_correction[c].correction_paragraph}
                for c in corrections
            ],
            "time_scale_statement": first_by_correction[corrections[0]].time_statement,
        },
        request={
            "endpoint": service.ENDPOINT,
            "user_agent": USER_AGENT,
            "common_query": [{"parameter": k, "value": v} for k, v in sorted(grid.COMMON_QUERY.items())],
            "center": {"command": CENTER, **grid.CENTERS[CENTER]},
            "corrections": [{"vec_corr": c, "documented_as": grid.CORRECTIONS[c]} for c in corrections],
            "targets": [dict(t) for t in TARGETS],
            "instants": {
                "taken_from": source,
                "count": len(instants),
                "set_sha256": grid.epoch_set_digest(instants),
                "chunk_size": grid.CHUNK_SIZE,
                "values": [e.as_json() for e in instants],
            },
            "queries": [{"request_id": r["request_id"], "vec_corr": r["correction"],
                         "target_command": r["target"]["command"], "chunk": r["chunk"],
                         "query": [{"parameter": k, "value": v} for k, v in sorted(r["query"].items())],
                         "resource_sha256": got.resource_sha256}
                        for r, got, _s in answered],
            "one_at_a_time": True,
            "request_interval_seconds": grid.REQUEST_INTERVAL_SECONDS,
            "backoff_seconds": list(grid.BACKOFF_SECONDS),
            "regenerate": f"{SCRIPT} --grid-values <values file> --grid-values-sha256 <its digest> --out <dir> "
                          "--budget-row <row> -- needs the network, or --from-cache to read the copies a live run "
                          "kept; a cache read is not an acquisition",
        },
        classification={section: {"class": "reference_only"} for section in sections},
        budget_row=budget_row,
        row_schema={
            "section": "state_none | state_lt_s: the correction the row was answered under",
            "request_id": "the request that answered it, as listed in `request.queries`",
            "target_command": "the body identifier sent, verbatim",
            "target_point": "body_centre: the point of the body the state names",
            "vec_corr": "the correction sent, verbatim",
            "center_command": "the centre sent, verbatim",
            "target_solution": "⭐ the solution the service named for this body, on this row",
            "center_solution": "⭐ the solution the service named for the centre, on this row",
            "interface_version": "the interface version the response named",
            "earth_orientation_file": "the Earth-orientation file the response named, or null where it named none",
            "jd_tdb": "the instant asked, Julian day, TDB — held to the service's echo, bit for bit",
            "calendar_date": "the service's own rendering of the same instant. ⚠ A label; `jd_tdb` is the authority",
            "value": "THE PIN — the nine printed values, in `component_order`, each in its `component_units` entry",
            "value_bits": "the same nine values as IEEE-754 bit patterns",
            "value_printed": "the same nine values as the service printed them",
            "component_order": list(grid.COMPONENTS),
            "component_units": list(grid.COMPONENT_UNITS),
        },
        summary={
            "rows": sum(len(s.data_rows) for _r, _g, s in answered),
            "rows_by_section": {s: sum(len(x.data_rows) for r, _g, x in answered
                                       if f"state_{grid.CORRECTION_SLUGS[r['correction']]}" == s) for s in sections},
            "requests": len(answered),
            "targets": len(TARGETS),
            "instants": len(instants),
            "documents": [dict(d) for d in grid.DOCUMENTS],
            "stated_terms": [dict(t) for t in grid.STATED_TERMS],
            "host": host_record(),
        },
        notes=[
            "⛔ Recorder, never explainer. No row is related to another; ⛔ no body centre is differenced against a "
            "barycentre, another correction or anything else, and nothing here says how the service computes them.",
            "⛔ reference_only, with no band: the band a consumer applies to these rows is that consumer's own, set "
            "in its own tree as a reviewed change.",
            "⭐ Each body centre is answered from a solution of its own, which every row names; for three of the six "
            "the service names that same solution for the geocentre. These rows are what the service printed under "
            "those names, nothing more.",
            "⭐ The instants are the earlier geocentric file's, by its digest (`request.instants.taken_from`), with "
            "the reasons that file gives each; the two files are row-for-row at the same instants.",
            "⚠ The service's LT+S is, in its document's words, 'astrometric states corrected for stellar aberration'. "
            "The document names no deflection of light for it.",
            "⚠ The instants are in TDB and were asked in TDB, explicitly. Nothing here is in a frame of date.",
            service.REPRODUCIBILITY_CONDITION,
            service.ACQUISITION_LIMIT,
        ],
    )


def build_acquisition_header(*, kind: str, values_sha256: str, generator, version: str) -> Header:
    """The earlier generator's acquisition record, naming this generator's values file and title."""
    header = grid.build_acquisition_header(kind=kind, values_sha256=values_sha256, generator=generator,
                                           version=version)
    return dataclasses.replace(
        header,
        title="How the geocentric body-centre states were obtained from the publisher's ephemeris service",
        oracle={**header.oracle, "values_file": {"path": VALUES_PATH, "sha256": values_sha256}},
    )


# ======================================================================================
# The run
# ======================================================================================


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--grid-values", required=True, type=Path,
                        help="the geocentric values file whose instants are asked")
    parser.add_argument("--grid-values-sha256", required=True, help="that file's sha256; any other is refused")
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--budget-row", required=True, help="⚠ a placeholder name; the consumer labels its rows")
    parser.add_argument("--cache", default=HERE.parent / "cache", type=Path)
    parser.add_argument("--corrections", default=DEFAULT_CORRECTIONS)
    parser.add_argument("--from-cache", action="store_true", help="read the copies a live run kept; send nothing")
    parser.add_argument("--plan-only", action="store_true", help="print the request count and estimate; send nothing")
    args = parser.parse_args(argv)

    generator = None if args.plan_only else generator_for(HERE / Path(SCRIPT).name)
    print(describe_reserved_names())
    corrections = [c.strip() for c in args.corrections.split(",") if c.strip()]
    for correction in corrections:
        if correction not in grid.EXPECTED_CORRECTION_STATEMENTS:
            raise Refusal(f"correction {correction!r}: no statement is pinned for it")
    instants, source = grid_instants(args.grid_values, args.grid_values_sha256)
    digest = grid.epoch_set_digest(instants)
    requests = plan(instants, corrections=corrections)
    sizing = grid.estimate(requests)
    print(f"{len(instants)} instants (set {digest[:16]}), {len(requests)} requests in {len(grid.chunks(instants))} "
          f"chunk(s) per body and correction; estimate {sizing['estimated_wall_seconds'] / 60:.1f} min live; "
          f"longest address {sizing['longest_address_characters']} characters; as {USER_AGENT}", flush=True)
    if args.plan_only:
        return 0
    values_path, record_path = args.out / VALUES_PATH, args.out / ACQUISITION_PATH
    for path in (values_path, record_path):
        if path.exists():
            raise Refusal(f"{path} exists; a record is never overwritten")

    answered, version = read(requests, cache=args.cache, digest=digest, from_cache=args.from_cache)
    kind = "cache_read" if args.from_cache else "live_request"
    header = build_values_header(answered, version=version, instants=instants, source=source,
                                 corrections=corrections, generator=generator, budget_row=args.budget_row)
    rows = grid.rows_for(answered, center=CENTER)
    written = write_jsonl(values_path, header, rows)
    values_sha256 = hashlib.sha256(values_path.read_bytes()).hexdigest()
    write_jsonl(record_path, build_acquisition_header(kind=kind, values_sha256=values_sha256, generator=generator,
                                                      version=version), grid.acquisition_rows(answered, kind=kind))
    print(f"wrote {written} rows -> {values_path} (sha256 {values_sha256[:16]}...); record ({kind}) -> {record_path}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (Refusal, ServiceFormatError, AcquisitionError) as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        raise SystemExit(2)
