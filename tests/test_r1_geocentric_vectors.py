"""The geocentric ICRF grid: what it asks, what it holds every response to, and how it reads twice.

⭐ No network. A synthetic service answers in the shape the real one was read in on 2026-11-21, with numbers that
are no body's state, so every refusal can be planted one at a time and every emission compared byte for byte.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
import urllib.error
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
_SPEC = importlib.util.spec_from_file_location("r1_geocentric_vectors", ROOT / "generators" / "r1_geocentric_vectors.py")
g = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = g
_SPEC.loader.exec_module(g)

from saakshi.acquisition import AcquisitionError, Retrieval  # noqa: E402
from saakshi.fixture import Generator  # noqa: E402

INTERVAL = {"profile": "standard@1", "manifest_sha256": "0" * 64, "dataset": "de440s",
            "declared_coverage": {"start": "1849-12-26T00:00:00", "end": "2150-01-22T00:00:00", "scale": "TDB"},
            "start": g.modes.julian_day("1849-12-26T00:00:00"), "end": g.modes.julian_day("2150-01-22T00:00:00")}
IDENTITY = Generator(repo="github.com/insculptor/Saakshi", script=g.SCRIPT, commit="0" * 40)


# --------------------------------------------------------------------------------------
# A synthetic service, in the shape the real one answered in
# --------------------------------------------------------------------------------------

STATED_LINES = {"NONE": "GEOMETRIC cartesian states", "LT": "LT CORRECTED cartesian states",
                "LT+S": "LT+S CORRECTED cartesian states"}


def respond(query: dict, *, source="NASA/JPL Horizons API", version="1.2", solution="DE441", center_solution="DE441", output_type=None,
            paragraph=None, frame="ICRF", echo_target=None, columns=None, drop_line=False, shift_jd=0.0,
            time_text='Barycentric Dynamical Time ("TDB" or T_eph) output was requested. This', stamp="10:00:00",
            eop="eop.261120.p270216") -> bytes:
    command = query["COMMAND"].strip("'")
    correction = query["VEC_CORR"].strip("'")
    jds = [float(text) for text in query["TLIST"].strip("'").split(",")]
    statement = g.EXPECTED_CORRECTION_STATEMENTS[correction]
    lines = []
    for jd in jds[:-1] if drop_line else jds:
        values = [f"{(int(command) + k) * 1e-3 + (jd - 2451545.0) * 1e-9:.15E}" for k in range(9)]
        lines.append(f"{jd + shift_jd:.9f}, A.D. 2000-Jan-01 00:00:00.0000, " + ", ".join(values) + ",")
    header = columns or ", ".join(g.EXPECTED_COLUMNS) + ","
    text = "\n".join([
        "*" * 79,
        f"Ephemeris / API_USER Fri Nov 21 {stamp} 2026 Pasadena, USA      / Horizons",
        "*" * 79,
        f"Target body name: Body ({echo_target or command})              {{source: {solution}}}",
        f"Center body name: Earth (399)                     {{source: {center_solution}}}",
        "Center-site name: BODY CENTER",
        "*" * 79,
        f"EOP file        : {eop}",
        "EOP coverage    : DATA-BASED 1962-JAN-20 TO 2026-NOV-20. PREDICTS-> 2027-FEB-15",
        "Output units    : AU-D",
        "Calendar mode   : Mixed Julian/Gregorian",
        f"Output type     : {output_type or statement['output_type']}",
        "Output format   : 3 (position, velocity, LT, range, range-rate)",
        f"Reference frame : {frame}",
        "*" * 79,
        "            " + header,
        "*" * 120,
        "$$SOE", *lines, "$$EOE",
        "*" * 120,
        " ", "TIME", "", "  " + time_text, "continuous coordinate time.", " ",
        "CALENDAR SYSTEM", "", "  Mixed calendar mode was active.", "",
        "REFERENCE FRAME AND COORDINATES", "",
        "  Symbol meaning [1 au= 149597870.700 km, 1 day= 86400.0 s]:", "",
        "ABERRATIONS AND CORRECTIONS", "", " " + (paragraph or statement["paragraph"]) + "   ", "",
        "Computations by ...", "",
    ])
    return json.dumps({"signature": {"source": source, "version": version},
                       "result": text}).encode("utf-8")


class FakeService:
    """`retrieve()`'s signature, answering from :func:`respond`. ⭐ It keeps the canonical copy as `retrieve()`
    does, so the cache-read path reads what a live run would have left."""

    def __init__(self, **plant):
        self.plant, self.calls = plant, []

    def __call__(self, url, *, cache, canonical):
        query = {k: v[0] for k, v in __import__("urllib.parse").parse.parse_qs(url.split("?", 1)[1]).items()}
        self.calls.append(query)
        payload = respond(query, stamp=f"10:00:{len(self.calls) % 60:02d}", **self.plant)
        resource = canonical(payload)
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_bytes(resource)
        return Retrieval(url=url, final_url=url, status=200, size_bytes=len(payload),
                         sha256=hashlib.sha256(payload).hexdigest(), validators={}, payload=payload,
                         prior_copy_agreed=None, resource=resource,
                         resource_sha256=hashlib.sha256(resource).hexdigest())


def _instants(n=3):
    return g.epochs([(2451545.0 + 16 * i, "test") for i in range(n)])


def _request(correction="NONE", command="199", n=3):
    return g.plan(_instants(n), center="500@399", corrections=[correction])[
        [t["command"] for t in g.TARGETS].index(command)]


# --------------------------------------------------------------------------------------
# What is asked
# --------------------------------------------------------------------------------------


def test_the_query_states_the_frame_the_system_the_scale_and_the_table():
    query = g.query_for(command="199", center="500@399", correction="LT+S", instants=_instants(1))
    assert {k: query[k] for k in ("EPHEM_TYPE", "CENTER", "REF_PLANE", "REF_SYSTEM", "TIME_TYPE", "OUT_UNITS",
                                  "VEC_TABLE", "VEC_CORR", "CSV_FORMAT")} == {
        "EPHEM_TYPE": "'VECTORS'", "CENTER": "'500@399'", "REF_PLANE": "'FRAME'", "REF_SYSTEM": "'ICRF'",
        "TIME_TYPE": "'TDB'", "OUT_UNITS": "'AU-D'", "VEC_TABLE": "'3'", "VEC_CORR": "'LT+S'", "CSV_FORMAT": "'YES'"}


def test_the_centre_and_the_correction_are_parameters_not_constants():
    assert not {"CENTER", "VEC_CORR", "COMMAND", "TLIST"} & set(g.COMMON_QUERY)
    for correction in g.CORRECTIONS:
        assert g.query_for(command="5", center="500@399", correction=correction,
                           instants=_instants(1))["VEC_CORR"] == f"'{correction}'"
    with pytest.raises(g.Refusal, match="no expectation"):
        g.query_for(command="5", center="500@0", correction="NONE", instants=_instants(1))
    with pytest.raises(g.Refusal, match="document names"):
        g.query_for(command="5", center="500@399", correction="LT+S+D", instants=_instants(1))


def test_the_corrections_are_quoted_from_the_document():
    assert g.CORRECTIONS == {"NONE": "geometric states", "LT": "astrometric light-time corrected states",
                             "LT+S": "astrometric states corrected for stellar aberration"}


def test_the_targets_are_the_planetary_solutions_points():
    assert [t["command"] for t in g.TARGETS] == ["10", "301", "199", "299", "4", "5", "6", "7", "8", "9"]
    assert {t["command"] for t in g.TARGETS if t["point"] == "system_barycentre"} == set("456789")


# --------------------------------------------------------------------------------------
# The epoch rule
# --------------------------------------------------------------------------------------


def test_the_lattice_rule_reaches_both_ends_and_both_strata():
    chosen = g.lattice_epochs(INTERVAL)
    reasons = {}
    for jd, reason in chosen:
        reasons.setdefault(reason, []).append(jd)
    assert reasons["interval_start_plus_one_day"] == [INTERVAL["start"] + 1.0]
    assert reasons["interval_end_minus_one_day"] == [INTERVAL["end"] - 1.0]
    assert len(reasons["dense_lattice"]) == 274 and len(reasons["sparse_lattice"]) == 110
    assert len(reasons["golden_1995_10_24"]) == 9 and len(reasons["golden_2145"]) == 4
    assert all(INTERVAL["start"] < jd < INTERVAL["end"] for jd, _ in chosen)
    assert all(jd * 16 == int(jd * 16) for jd, _ in chosen)


def test_an_instant_the_echo_cannot_be_held_to_is_refused():
    with pytest.raises(g.Refusal, match="sixteenth"):
        g._exact(2451545.0 + 1 / 24, what="an hour")


def test_one_instant_per_day_in_time_order_with_every_reason():
    merged = g.epochs([(3.5, "b"), (1.5, "a"), (3.5, "c")])
    assert [(e.jd_tdb, e.reasons) for e in merged] == [(1.5, ["a"]), (3.5, ["b", "c"])]


def test_the_plan_asks_every_instant_of_every_body_under_every_correction_once():
    instants = _instants(450)
    requests = g.plan(instants, center="500@399", corrections=list(g.CORRECTIONS))
    assert len(requests) == 3 * 10 * 3 and len({r["request_id"] for r in requests}) == len(requests)
    for correction in g.CORRECTIONS:
        for target in g.TARGETS:
            mine = [r for r in requests if r["correction"] == correction and r["target"] is target]
            asked = [e.jd_tdb for r in mine for e in r["instants"]]
            assert asked == sorted(asked) == [e.jd_tdb for e in instants]
    assert max(len(r["instants"]) for r in requests) <= g.CHUNK_SIZE


def test_the_cache_is_keyed_on_target_centre_correction_and_instant_set(tmp_path):
    def stem(**change):
        key = {"center": "500@399", "correction": "LT", "digest": "a" * 64, "command": "199", "index": 0, **change}
        return g.cache_stem(tmp_path, **key)
    seen = {stem(), stem(correction="LT+S"), stem(digest="b" * 64), stem(command="5"), stem(index=1)}
    assert len(seen) == 5
    assert all(g.CACHE_SUBDIRECTORY in s.parts for s in seen)
    assert stem().with_suffix(".txt").name != "r1-199.txt"  # ⛔ never the barycentric R1 copy's name


def test_the_instant_set_digest_moves_with_any_instant():
    assert g.epoch_set_digest(_instants(3)) != g.epoch_set_digest(_instants(4))


# --------------------------------------------------------------------------------------
# What every response is held to
# --------------------------------------------------------------------------------------


@pytest.mark.parametrize("correction", list(g.CORRECTIONS))
def test_a_response_as_read_on_the_day_is_held(correction):
    request = _request(correction)
    response = g.split(respond(request["query"]), query=request["query"])
    assert g.hold(response, request, center="500@399", version=None) == "1.2"
    assert response.service_state["earth_orientation_file"] == "eop.261120.p270216"


@pytest.mark.parametrize("plant, match", [
    ({"source": "Another API"}, "STOP: .*: interface 'Another API'"),
    ({"version": "1.4"}, "neither the document's nor the last observed"),
    ({"solution": "DE440"}, "target_solution"),
    ({"center_solution": "DE430"}, "center_solution"),
    ({"echo_target": "499"}, "target_echo"),
    ({"output_type": "APPARENT cartesian states"}, "output type"),
    ({"paragraph": "States have been corrected for light-time, stellar aberration and gravitational deflection."},
     "statement of its corrections"),
    ({"frame": "B1950"}, "reference_frame"),
    ({"time_text": 'Coordinated Universal Time ("UT") output was requested.'}, "TDB"),
    ({"columns": "JDTDB, Calendar Date (TDB), X, Y, Z, VX, VY, VZ, RG, LT, RR,"}, "columns"),
    ({"drop_line": True}, "lines for"),
    ({"shift_jd": 0.5}, "answered for JD"),
])
def test_each_departure_is_a_stop(plant, match):
    request = _request("LT+S")
    response = g.split(respond(request["query"], **plant), query=request["query"])
    with pytest.raises(g.Refusal, match=match):
        g.hold(response, request, center="500@399", version=None)


def test_both_accepted_versions_are_accepted_but_never_two_in_one_run():
    request = _request()
    for version in g.ACCEPTED_INTERFACE_VERSIONS:
        response = g.split(respond(request["query"], version=version), query=request["query"])
        assert g.hold(response, request, center="500@399", version=None) == version
    response = g.split(respond(request["query"], version="1.3"), query=request["query"])
    with pytest.raises(g.Refusal, match="earlier in this run"):
        g.hold(response, request, center="500@399", version="1.2")


def test_a_correction_with_no_pinned_statement_is_a_stop(monkeypatch):
    request = _request("LT")
    response = g.split(respond(request["query"]), query=request["query"])
    monkeypatch.setitem(g.EXPECTED_CORRECTION_STATEMENTS, "LT", None)
    monkeypatch.delitem(g.EXPECTED_CORRECTION_STATEMENTS, "LT")
    with pytest.raises(g.Refusal, match="no statement is pinned"):
        g.hold(response, request, center="500@399", version=None)


def test_the_stamp_and_the_state_are_cut_from_the_resource():
    request = _request()
    one = g.split(respond(request["query"], stamp="10:00:01"), query=request["query"])
    two = g.split(respond(request["query"], stamp="23:59:59", eop="eop.261121.p270217"), query=request["query"])
    assert one.resource_text == two.resource_text
    assert "DE441" not in one.resource_text and "<excluded:generation_stamp>" in one.resource_text


# --------------------------------------------------------------------------------------
# Reading: live, with backoff, and from the copies kept
# --------------------------------------------------------------------------------------


def test_a_transient_failure_backs_off_and_a_refusal_does_not(tmp_path):
    request, pauses = _request(), []
    service = FakeService()
    failures = iter([urllib.error.URLError("down"), urllib.error.HTTPError("u", 503, "busy", {}, None)])

    def flaky(url, **kwargs):
        failure = next(failures, None)
        if failure is not None:
            raise AcquisitionError("could not be retrieved") from failure
        return service(url, **kwargs)

    got = g.read_live(request, tmp_path / "x", sleep=pauses.append, fetch=flaky)
    assert pauses == list(g.BACKOFF_SECONDS) and got.kind == "live_request"

    def refused(url, **kwargs):
        raise AcquisitionError("bad request") from urllib.error.HTTPError("u", 400, "no", {}, None)

    pauses.clear()
    with pytest.raises(AcquisitionError):
        g.read_live(request, tmp_path / "y", sleep=pauses.append, fetch=refused)
    assert pauses == []


def test_after_the_last_backoff_it_stops(tmp_path):
    pauses = []

    def down(url, **kwargs):
        raise AcquisitionError("could not be retrieved") from urllib.error.URLError("down")

    with pytest.raises(AcquisitionError):
        g.read_live(_request(), tmp_path / "x", sleep=pauses.append, fetch=down)
    assert pauses == list(g.BACKOFF_SECONDS)


def test_the_cache_read_returns_what_the_live_read_did_but_its_kind(tmp_path):
    request = _request("LT")
    stem = tmp_path / "copy"
    live = g.read_live(request, stem, sleep=lambda s: None, fetch=FakeService())
    cached = g.read_cached(request, stem)
    assert (cached.url, cached.payload, cached.resource_sha256, cached.resource_bytes, cached.acquired_on) == (
        live.url, live.payload, live.resource_sha256, live.resource_bytes, live.acquired_on)
    assert (live.kind, cached.kind) == ("live_request", "cache_read")


@pytest.mark.parametrize("tamper", ["missing", "address", "payload"])
def test_a_cache_read_refuses_rather_than_falling_back(tmp_path, tamper):
    request = _request()
    stem = tmp_path / "copy"
    g.read_live(request, stem, sleep=lambda s: None, fetch=FakeService())
    if tamper == "missing":
        stem.with_suffix(".payload").unlink()
    elif tamper == "address":
        record = json.loads(stem.with_suffix(".acquired.json").read_text())
        stem.with_suffix(".acquired.json").write_text(json.dumps({**record, "url": record["url"] + "x"}))
    else:
        stem.with_suffix(".payload").write_bytes(respond(_request(n=4)["query"]))
    with pytest.raises(g.Refusal):
        g.read_cached(request, stem)


def test_a_stop_sends_nothing_further(tmp_path):
    requests = g.plan(_instants(2), center="500@399", corrections=["NONE"])
    service = FakeService(solution="DE440")
    with pytest.raises(g.Refusal, match="target_solution"):
        g.read(requests, cache=tmp_path, center="500@399", digest="a" * 64, from_cache=False,
               sleep=lambda s: None, fetch=service)
    assert len(service.calls) == 1


def test_requests_are_paced_one_at_a_time(tmp_path):
    pauses = []
    requests = g.plan(_instants(2), center="500@399", corrections=["NONE"])
    g.read(requests, cache=tmp_path, center="500@399", digest="a" * 64, from_cache=False,
           sleep=pauses.append, fetch=FakeService())
    assert pauses == [g.REQUEST_INTERVAL_SECONDS] * (len(requests) - 1)


# --------------------------------------------------------------------------------------
# The two emissions
# --------------------------------------------------------------------------------------


@pytest.fixture
def stand_ins(monkeypatch, tmp_path):
    """The run, with the network, the kernel and the tree's identity replaced, and two event instants."""
    service = FakeService()
    monkeypatch.setattr(g, "retrieve", service)
    monkeypatch.setattr(g, "generator_for", lambda script: IDENTITY)
    monkeypatch.setattr(g, "verify", lambda path: None)
    monkeypatch.setattr(g, "oracle_identity", lambda path, pin: {"dataset": "de440s.bsp", "sha256": "1" * 64})
    monkeypatch.setattr(g, "event_epochs", lambda kernel, interval: [(2451549.5, "conjunction_test"),
                                                                     (2451700.5, "station_test")])
    monkeypatch.setattr(g.modes, "read_interval", lambda manifest: INTERVAL)
    monkeypatch.setattr(g.time, "sleep", lambda s: None)
    return service


def _emit(tmp_path, name, *extra):
    out = tmp_path / name
    g.main(["--profile", "p.toml", "--kernel", "k.bsp", "--out", str(out), "--cache", str(tmp_path / "cache"),
            *extra])
    return out


def test_the_second_emission_reads_the_cache_and_writes_the_same_values(stand_ins, tmp_path):
    live = _emit(tmp_path, "live")
    sent = len(stand_ins.calls)
    again = _emit(tmp_path, "again", "--from-cache")
    assert len(stand_ins.calls) == sent == 90  # ⛔ the cache read sent nothing
    assert (live / g.VALUES_PATH).read_bytes() == (again / g.VALUES_PATH).read_bytes()

    def without_kind(path):
        lines = [json.loads(line) for line in path.read_text().splitlines()]
        for line in lines:
            line.pop("retrieval_kind", None)
            for block in ("oracle", "summary"):
                if block in line:
                    line[block].pop("retrieval_kind", None)
                    line[block].pop("retrieval_kind_meaning", None)
        return lines

    one, two = (p / g.ACQUISITION_PATH for p in (live, again))
    assert one.read_bytes() != two.read_bytes()
    assert without_kind(one) == without_kind(two)
    kinds = {json.loads(line).get("retrieval_kind") for line in two.read_text().splitlines()[1:]}
    assert kinds == {"cache_read"}


def test_the_values_file_holds_the_contract_and_says_what_answered(stand_ins, tmp_path):
    out = _emit(tmp_path, "live")
    lines = (out / g.VALUES_PATH).read_text().splitlines()
    header, rows = json.loads(lines[0]), [json.loads(line) for line in lines[1:]]
    assert (header["fixture_kind"], header["reference"]) == ("numeric_pin", "R1")
    assert header["classification"] == {s: {"class": "reference_only"} for s in ("state_none", "state_lt", "state_lt_s")}
    assert len(rows) == header["summary"]["rows"] == 10 * 3 * header["request"]["instants"]["count"]
    assert all(r["target_solution"] == "DE441" and r["interface_version"] == "1.2" and r["earth_orientation_file"]
               for r in rows)
    assert all(len(r["value"]) == len(r["value_bits"]) == len(r["value_printed"]) == 9 for r in rows)
    assert header["request"]["instants"]["rule"] == g.EPOCH_RULE
    assert [q["request_id"] for q in header["request"]["queries"]] == [r["request_id"] for r in
                                                                       g.plan(g.epochs(g.lattice_epochs(INTERVAL) + [
                                                                           (2451549.5, "conjunction_test"),
                                                                           (2451700.5, "station_test")]),
                                                                           center="500@399",
                                                                           corrections=list(g.CORRECTIONS))]
    statements = {s["vec_corr"]: s["aberrations_and_corrections"] for s in header["oracle"]["the_service_on_each_correction"]}
    assert statements == {c: g.EXPECTED_CORRECTION_STATEMENTS[c]["paragraph"] for c in g.CORRECTIONS}


def test_a_record_is_never_overwritten(stand_ins, tmp_path):
    _emit(tmp_path, "live")
    with pytest.raises(g.Refusal, match="never overwritten"):
        _emit(tmp_path, "live")


def test_a_cache_read_with_nothing_kept_refuses(stand_ins, tmp_path):
    with pytest.raises(g.Refusal, match="no kept copy"):
        _emit(tmp_path, "again", "--from-cache")
    assert stand_ins.calls == []


def test_the_plan_alone_sends_nothing(stand_ins, tmp_path, capsys):
    assert g.main(["--profile", "p.toml", "--kernel", "k.bsp", "--out", str(tmp_path / "o"), "--plan-only"]) == 0
    assert stand_ins.calls == [] and not (tmp_path / "o").exists()
    assert "90 requests" in capsys.readouterr().out


# --------------------------------------------------------------------------------------
# The event selection, on the pinned kernel
# --------------------------------------------------------------------------------------

KERNEL = ROOT / "cache" / "kernels" / "de440s.bsp"


@pytest.mark.skipif(not KERNEL.is_file(), reason="the pinned short-span kernel is not in cache/kernels")
def test_the_event_rule_finds_every_event_it_asks_for():
    pytest.importorskip("spiceypy", reason="the SPICE binding is absent")
    chosen = g.event_epochs(KERNEL, INTERVAL)
    conjunctions = [r for _, r in chosen if r.startswith("conjunction_")]
    stations = [r for _, r in chosen if r.startswith("station_")]
    assert len(conjunctions) == sum(g.CONJUNCTIONS_PER_ANCHOR.values()) * len(g.EVENT_ANCHORS)
    assert len(stations) == sum(g.STATIONS_PER_ANCHOR.values()) * len(g.EVENT_ANCHORS)
    assert all(jd == int(jd - 0.5) + 0.5 for jd, _ in chosen)  # whole days at 0 h TDB
