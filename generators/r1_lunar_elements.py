"""R1 — the Moon's geometric osculating elements about the geocentre, on the ecliptic of J2000, at an earlier grid's instants.

The publisher's ephemeris service is asked for the Moon's osculating orbital elements with the geocentre as centre,
referred to the reference plane the service calls ``ECLIPTIC`` in the ICRF, in TDB, at exactly the instants of an
earlier geocentric values file read by its digest; every element is written down as printed, with its bit pattern.

* ⭐ **What the service states about the frame, pinned and held**: on every answer, the reference frame line
  (*"Ecliptic of J2000.0"*), the frame's own definition under *REFERENCE FRAME AND COORDINATES* (the reference epoch,
  the plane, its stated obliquity to the ICRF plane, the X-axis), the output type (*"GEOMETRIC osculating
  elements"*) and its statement that no corrections are applied, the Keplerian GM line, the units, the time scale and
  the columns — each character for character, as read on the first answers of 2026-11-25. Any other is a stop.
* ⭐ **Everything else is the geocentric grid's, by import**: the response's split, the stamp cut from the digest,
  the live and cache-read paths, the instants of the earlier file and their reasons.
* ⛔ **No derived value.** Nothing here turns an element into a node of date, an equinox or anything else. Every
  section is ``reference_only``.
* ⛔ **Recorder, never explainer.**

Usage:
    python generators/r1_lunar_elements.py --grid-values VALUES.jsonl --grid-values-sha256 HEX --out DIR
        --budget-row ROW [--cache DIR] [--from-cache] [--plan-only]
"""

from __future__ import annotations

import argparse
import dataclasses
import hashlib
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
from saakshi.fixture import Header, describe_reserved_names, patterned, write_jsonl  # noqa: E402
from saakshi.provenance import generator_for, host_record, today  # noqa: E402
from saakshi.service import ServiceFormatError  # noqa: E402

import r1_body_centres as centres  # noqa: E402
import r1_geocentric_vectors as grid  # noqa: E402

SCRIPT = "generators/r1_lunar_elements.py"
VALUES_PATH = "service/r1-lunar-elements.jsonl"
ACQUISITION_PATH = "service/r1-lunar-elements-acquisition.jsonl"
CACHE_SUBDIRECTORY = "r1-lunar-elements"
CENTER = "500@399"
TARGET = {"command": "301", "label": "Moon", "point": "body_centre"}
Refusal = grid.Refusal

QUERY: dict[str, str] = {
    "format": "json", "EPHEM_TYPE": "'ELEMENTS'", "COMMAND": "'301'", "CENTER": "'500@399'",
    "REF_PLANE": "'ECLIPTIC'", "REF_SYSTEM": "'ICRF'", "TIME_TYPE": "'TDB'", "TLIST_TYPE": "'JD'",
    "OUT_UNITS": "'AU-D'", "CSV_FORMAT": "'YES'", "OBJ_DATA": "'NO'", "MAKE_EPHEM": "'YES'", "ELM_LABELS": "'YES'",
    "TP_TYPE": "'ABSOLUTE'",
}

COLUMNS: tuple[str, ...] = ("JDTDB", "Calendar Date (TDB)", "EC", "QR", "IN", "OM", "W", "Tp", "N", "MA", "TA", "A",
                            "AD", "PR")
COMPONENTS = COLUMNS[2:]
#: The unit of each element, as the answer's own symbol list states it.
COMPONENT_UNITS: tuple[str, ...] = ("1", "au", "degree", "degree", "degree", "Julian day number", "degree/day",
                                    "degree", "degree", "au", "au", "day")
SYMBOLS: tuple[str, ...] = (
    "EC     Eccentricity, e", "QR     Periapsis distance, q (au)", "IN     Inclination w.r.t X-Y plane, i (degrees)",
    "OM     Longitude of Ascending Node, OMEGA, (degrees)", "W      Argument of Perifocus, w (degrees)",
    "Tp     Time of periapsis (Julian Day Number)", "N      Mean motion, n (degrees/day)",
    "MA     Mean anomaly, M (degrees)", "TA     True anomaly, nu (degrees)", "A      Semi-major axis, a (au)",
    "AD     Apoapsis distance (au)", "PR     Sidereal orbit period (day)",
)

#: ⛔ What every answer must state, pinned from the answers read on 2026-11-25.
STATED: dict[str, str] = {
    "reference_frame": "Ecliptic of J2000.0",
    "output_units": "AU-D, deg, Julian Day Number (Tp)",
    "output_type": "GEOMETRIC osculating elements",
    "output_format": "10",
    "au_in_km": "149597870.700",
    "seconds_per_day": "86400.0",
}
PARAGRAPH = "Geometric osculating elements have NO corrections or aberrations applied."
KEPLERIAN_GM = "8.9970113929473456E-10 au^3/d^2"
FRAME_DEFINITION = (
    "Ecliptic at the standard reference epoch\n\n"
    "    Reference epoch: J2000.0\n"
    "    X-Y plane: adopted Earth orbital plane at the reference epoch\n"
    "               Note: IAU76 obliquity of 84381.448 arcseconds wrt ICRF X-Y plane\n"
    "    X-axis   : ICRF\n"
    "    Z-axis   : perpendicular to the X-Y plane in the directional (+ or -) sense\n"
    "               of Earth's north pole at the reference epoch."
)


def frame_definition(text: str) -> str:
    """The block under *REFERENCE FRAME AND COORDINATES*, up to the symbol list, trailing spaces cut."""
    if text.count("\nREFERENCE FRAME AND COORDINATES\n") != 1:
        raise ServiceFormatError("the frame section is not exactly one")
    body = text.split("\nREFERENCE FRAME AND COORDINATES\n", 1)[1].split("\n  Symbol meaning", 1)[0]
    return "\n".join(line.rstrip() for line in body.strip("\n").splitlines()).strip()


def keplerian_gm(text: str) -> str:
    found = re.findall(r"^Keplerian GM +: *(.+?) *$", text, re.M)
    if len(found) != 1:
        raise ServiceFormatError("the Keplerian GM line is not exactly one")
    return found[0]


def hold(response: grid.Response, request: dict, *, version: str | None) -> str:
    """⛔ Every check an answer is held to. Returns the interface version it named."""
    where = request["request_id"]
    state = response.service_state
    if state.get("interface_source") != grid.EXPECTED_INTERFACE_SOURCE:
        raise Refusal(f"⛔ STOP: {where}: interface {state.get('interface_source')!r}")
    named = state.get("interface_version")
    if named not in grid.ACCEPTED_INTERFACE_VERSIONS or (version is not None and named != version):
        raise Refusal(f"⛔ STOP: {where}: interface version {named!r}")
    for key in ("target_solution", "center_solution"):
        if state.get(key) != grid.EXPECTED_SOLUTION:
            raise Refusal(f"⛔ STOP: {where}: {key} is {state.get(key)!r}, not {grid.EXPECTED_SOLUTION!r}")
    for key, wanted in (("target_echo", "301"), ("center_echo", "399"), ("center_site", "BODY CENTER")):
        if response.echo[key] != wanted:
            raise Refusal(f"⛔ STOP: {where}: {key} is {response.echo[key]!r}, not {wanted!r}")
    for key, wanted in STATED.items():
        if response.stated.get(key) != wanted:
            raise Refusal(f"⛔ STOP: {where}: the answer states {key} {response.stated.get(key)!r}, not {wanted!r}")
    if response.correction_paragraph != PARAGRAPH:
        raise Refusal(f"⛔ STOP: {where}: the answer's statement of its corrections differs: "
                      f"{response.correction_paragraph!r}")
    if frame_definition(response.resource_text) != FRAME_DEFINITION:
        raise Refusal(f"⛔ STOP: {where}: the answer's definition of its frame differs from the one pinned")
    if keplerian_gm(response.resource_text) != KEPLERIAN_GM:
        raise Refusal(f"⛔ STOP: {where}: the Keplerian GM line differs from the one pinned")
    if grid.EXPECTED_TIME_STATEMENT not in response.time_statement:
        raise Refusal(f"⛔ STOP: {where}: the answer does not state that TDB was requested")
    for symbol in SYMBOLS:
        if symbol not in response.resource_text:
            raise Refusal(f"⛔ STOP: {where}: the symbol {symbol.split()[0]} is not defined as pinned")
    if response.columns != COLUMNS:
        raise Refusal(f"⛔ STOP: {where}: columns {response.columns} are not {COLUMNS}")
    if len(response.data_rows) != len(request["instants"]):
        raise Refusal(f"⛔ STOP: {where}: {len(response.data_rows)} lines for {len(request['instants'])} instants")
    for fields, instant in zip(response.data_rows, request["instants"]):
        if float(fields[0]) != instant.jd_tdb:
            raise Refusal(f"⛔ STOP: {where}: answered for JD {fields[0]} where {instant.jd_tdb!r} was asked")
    return named


def plan(instants: list[grid.Epoch]) -> list[dict]:
    return [{"request_id": f"elements-301-c{i:02d}", "correction": "NONE", "target": TARGET, "chunk": i,
             "instants": piece, "query": {**QUERY, "TLIST": grid.tlist([e.jd_tdb for e in piece])}}
            for i, piece in enumerate(grid.chunks(instants))]


def cache_stem(cache: Path, *, digest: str, index: int) -> Path:
    return cache / CACHE_SUBDIRECTORY / "center_500_399" / "plane_ecliptic" / \
        f"epochs_{digest[:16]}_by_{grid.CHUNK_SIZE}" / f"301-c{index:02d}"


def read(requests: list[dict], *, cache: Path, digest: str, from_cache: bool,
         sleep: Callable[[float], None] | None = None, fetch: Callable[..., object] | None = None):
    sleep, fetch = sleep or time.sleep, fetch or retrieve
    out, version = [], None
    for index, request in enumerate(requests):
        stem = cache_stem(cache, digest=digest, index=request["chunk"])
        if from_cache:
            got = grid.read_cached(request, stem)
        else:
            if index:
                sleep(grid.REQUEST_INTERVAL_SECONDS)
            stem.parent.mkdir(parents=True, exist_ok=True)
            got = grid.read_live(request, stem, sleep=sleep, fetch=fetch)
        response = grid.split(got.payload, query=request["query"])
        version = hold(response, request, version=version)
        out.append((request, got, response))
        print(f"  {request['request_id']}: {len(response.data_rows)} instants, interface {version}, "
              f"resource {got.resource_sha256[:12]}... ({got.kind})", flush=True)
    return out, version


def rows_for(answered) -> list[dict]:
    rows = []
    for request, _got, response in answered:
        state = response.service_state
        for fields, instant in zip(response.data_rows, request["instants"]):
            printed = list(fields[2:])
            rows.append({
                "section": "osculating_elements", "request_id": request["request_id"], "target_command": "301",
                "center_command": CENTER, "target_solution": state["target_solution"],
                "center_solution": state["center_solution"], "interface_version": state["interface_version"],
                "earth_orientation_file": state.get("earth_orientation_file"),
                **patterned("jd_tdb", instant.jd_tdb), "calendar_date": fields[1],
                **patterned("value", [float(t) for t in printed]), "value_printed": printed,
            })
    return rows


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--grid-values", required=True, type=Path)
    parser.add_argument("--grid-values-sha256", required=True)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--budget-row", required=True, help="⚠ a placeholder name; the consumer labels its rows")
    parser.add_argument("--cache", default=HERE.parent / "cache", type=Path)
    parser.add_argument("--from-cache", action="store_true")
    parser.add_argument("--plan-only", action="store_true")
    args = parser.parse_args(argv)
    generator = None if args.plan_only else generator_for(HERE / Path(SCRIPT).name)
    print(describe_reserved_names())
    instants, source = centres.grid_instants(args.grid_values, args.grid_values_sha256)
    digest = grid.epoch_set_digest(instants)
    requests = plan(instants)
    print(f"{len(instants)} instants (set {digest[:16]}), {len(requests)} requests; as {USER_AGENT}", flush=True)
    if args.plan_only:
        return 0
    values_path, record_path = args.out / VALUES_PATH, args.out / ACQUISITION_PATH
    for path in (values_path, record_path):
        if path.exists():
            raise Refusal(f"{path} exists; a record is never overwritten")
    answered, version = read(requests, cache=args.cache, digest=digest, from_cache=args.from_cache)
    kind = "cache_read" if args.from_cache else "live_request"
    first = answered[0][2]
    header = Header(
        fixture_kind="numeric_pin", reference="R1", generator=generator, generated=today(),
        title="The Moon's geometric osculating elements about the geocentre, on the ecliptic of J2000",
        oracle={
            "publisher": "JPL Solar System Dynamics", "service": "Horizons", "endpoint": service.ENDPOINT,
            "user_agent": USER_AGENT, "interface": {"source": grid.EXPECTED_INTERFACE_SOURCE, "version": version},
            "acquired_on": sorted({got.acquired_on for _r, got, _s in answered}),
            "stated_by_the_service": {**STATED, "aberrations_and_corrections": first.correction_paragraph,
                                      "frame_definition": frame_definition(first.resource_text),
                                      "keplerian_gm": keplerian_gm(first.resource_text),
                                      "time_scale_statement": first.time_statement,
                                      "symbols": list(SYMBOLS),
                                      "role": "what the service stated about its own output, held equal on every "
                                              "answer"},
            "earth_orientation_named": sorted({s.service_state.get("earth_orientation_file") or ""
                                               for _r, _g, s in answered}),
        },
        request={
            "endpoint": service.ENDPOINT, "user_agent": USER_AGENT,
            "query": [{"parameter": k, "value": v} for k, v in sorted(QUERY.items()) if k != "TLIST"],
            "instants": {"taken_from": source, "count": len(instants), "set_sha256": digest,
                         "chunk_size": grid.CHUNK_SIZE, "values": [e.as_json() for e in instants]},
            "queries": [{"request_id": r["request_id"], "chunk": r["chunk"],
                         "query": [{"parameter": k, "value": v} for k, v in sorted(r["query"].items())],
                         "resource_sha256": got.resource_sha256} for r, got, _s in answered],
            "one_at_a_time": True,
        },
        classification={"osculating_elements": {"class": "reference_only"}},
        budget_row=args.budget_row,
        row_schema={"value": "THE PIN — the twelve printed elements in `component_order`, each in its unit",
                    "value_bits": "the same as IEEE-754 bit patterns", "value_printed": "as printed",
                    "component_order": list(COMPONENTS), "component_units": list(COMPONENT_UNITS)},
        summary={"rows": sum(len(s.data_rows) for _r, _g, s in answered), "requests": len(answered),
                 "host": host_record()},
        notes=["⛔ Recorder, never explainer: no element is turned into a node of date or anything else.",
               "⭐ The frame is the one the service defines in its own words (`oracle.stated_by_the_service`).",
               service.REPRODUCIBILITY_CONDITION, service.ACQUISITION_LIMIT],
    )
    written = write_jsonl(values_path, header, rows_for(answered))
    values_sha256 = hashlib.sha256(values_path.read_bytes()).hexdigest()
    record = grid.build_acquisition_header(kind=kind, values_sha256=values_sha256, generator=generator,
                                           version=version)
    record = dataclasses.replace(record, title="How the Moon's osculating elements were obtained from the service",
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
