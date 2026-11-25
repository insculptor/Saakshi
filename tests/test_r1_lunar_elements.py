"""The Moon's osculating elements: the frame the service states, held on every answer; read twice from one acquisition.

⭐ No network. A synthetic service answers in the shape the real one was read in, with numbers that are no orbit's.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
import urllib.parse
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


e = _load("r1_lunar_elements", ROOT / "generators" / "r1_lunar_elements.py")
grid = e.grid
centres_tests = _load("r1_body_centres_test_helpers", ROOT / "tests" / "test_r1_body_centres.py")

from saakshi.acquisition import Retrieval  # noqa: E402
from saakshi.fixture import Generator  # noqa: E402

IDENTITY = Generator(repo="github.com/insculptor/Saakshi", script=e.SCRIPT, commit="0" * 40)


def respond(query: dict, *, frame=None, reference_frame="Ecliptic of J2000.0", paragraph=None, gm=None,
            columns=None, drop_line=False, stamp="10:00:00") -> bytes:
    jds = [float(t) for t in query["TLIST"].strip("'").split(",")]
    lines = []
    for jd in jds[:-1] if drop_line else jds:
        values = [f"{(k + 1) * 1e-2 + (jd - 2451545.0) * 1e-9:.15E}" for k in range(12)]
        lines.append(f"{jd:.9f}, A.D. 2000-Jan-01 00:00:00.0000, " + ", ".join(values) + ",")
    definition = frame or e.FRAME_DEFINITION
    text = "\n".join([
        "*" * 79, f"Ephemeris / API_USER Wed Nov 25 {stamp} 2026 Pasadena, USA      / Horizons", "*" * 79,
        "Target body name: Moon (301)                      {source: DE441}",
        "Center body name: Earth (399)                     {source: DE441}",
        "Center-site name: BODY CENTER", "*" * 79,
        f"Keplerian GM    : {gm or e.KEPLERIAN_GM}",
        "Output units    : AU-D, deg, Julian Day Number (Tp)", "Calendar mode   : Mixed Julian/Gregorian",
        "Output type     : GEOMETRIC osculating elements", "Output format   : 10",
        "EOP file        : eop.261124.p270220", f"Reference frame : {reference_frame}", "*" * 79,
        "            " + (columns or ", ".join(e.COLUMNS) + ","), "*" * 120, "$$SOE", *lines, "$$EOE", "*" * 120,
        " ", "TIME", "", '  Barycentric Dynamical Time ("TDB" or T_eph) output was requested. This', " ",
        "CALENDAR SYSTEM", "", "  Mixed calendar mode was active.", "",
        "REFERENCE FRAME AND COORDINATES", "", "  " + definition + "  ", "",
        "  Symbol meaning [1 au= 149597870.700 km, 1 day= 86400.0 s]:", "",
        *("      " + s for s in e.SYMBOLS), "",
        "ABERRATIONS AND CORRECTIONS", "", " " + (paragraph or e.PARAGRAPH), "", "Computations by ...", "",
    ])
    return json.dumps({"signature": {"source": "NASA/JPL Horizons API", "version": "1.2"},
                       "result": text}).encode("utf-8")


class FakeService:
    def __init__(self, **plant):
        self.plant, self.calls = plant, []

    def __call__(self, url, *, cache, canonical):
        query = {k: v[0] for k, v in urllib.parse.parse_qs(url.split("?", 1)[1]).items()}
        self.calls.append(query)
        payload = respond(query, stamp=f"10:00:{len(self.calls) % 60:02d}", **self.plant)
        resource = canonical(payload)
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_bytes(resource)
        return Retrieval(url=url, final_url=url, status=200, size_bytes=len(payload),
                         sha256=hashlib.sha256(payload).hexdigest(), validators={}, payload=payload,
                         prior_copy_agreed=None, resource=resource,
                         resource_sha256=hashlib.sha256(resource).hexdigest())


def _instants(tmp_path, n=3):
    path, digest = centres_tests._grid_file(tmp_path, jds=tuple(2451545.0 + 16 * i for i in range(n)))
    return e.centres.grid_instants(path, digest)[0], path, digest


def test_the_query_asks_the_moon_about_the_geocentre_on_the_ecliptic_in_tdb(tmp_path):
    instants, _p, _d = _instants(tmp_path, 160)
    requests = e.plan(instants)
    assert len(requests) == 3 and max(len(r["instants"]) for r in requests) <= 75
    q = requests[0]["query"]
    assert (q["EPHEM_TYPE"], q["COMMAND"], q["CENTER"], q["REF_PLANE"], q["REF_SYSTEM"], q["TIME_TYPE"]) == (
        "'ELEMENTS'", "'301'", "'500@399'", "'ECLIPTIC'", "'ICRF'", "'TDB'")


def test_an_answer_as_read_on_the_day_is_held(tmp_path):
    instants, _p, _d = _instants(tmp_path)
    request = e.plan(instants)[0]
    response = grid.split(respond(request["query"]), query=request["query"])
    assert e.hold(response, request, version=None) == "1.2"


@pytest.mark.parametrize("plant, match", [
    ({"frame": e.FRAME_DEFINITION.replace("84381.448", "84381.406")}, "definition of its frame"),
    ({"reference_frame": "ICRF"}, "reference_frame"),
    ({"paragraph": "Elements have corrections applied."}, "statement of its corrections"),
    ({"gm": "8.9970113929473455E-10 au^3/d^2"}, "Keplerian GM"),
    ({"columns": "JDTDB, Calendar Date (TDB), EC, QR, IN, W, OM, Tp, N, MA, TA, A, AD, PR,"}, "columns"),
    ({"drop_line": True}, "lines for"),
])
def test_each_departure_from_what_was_read_is_a_stop(tmp_path, plant, match):
    instants, _p, _d = _instants(tmp_path)
    request = e.plan(instants)[0]
    response = grid.split(respond(request["query"], **plant), query=request["query"])
    with pytest.raises(e.Refusal, match=match):
        e.hold(response, request, version=None)


@pytest.fixture
def stand_ins(monkeypatch):
    service = FakeService()
    monkeypatch.setattr(e, "retrieve", service)
    monkeypatch.setattr(e, "generator_for", lambda script: IDENTITY)
    monkeypatch.setattr(e.time, "sleep", lambda s: None)
    return service


def _emit(tmp_path, path, digest, name, *extra):
    out = tmp_path / name
    e.main(["--grid-values", str(path), "--grid-values-sha256", digest, "--out", str(out), "--cache",
            str(tmp_path / "cache"), "--budget-row", "placeholder-row", *extra])
    return out


def test_the_second_emission_reads_the_cache_and_writes_the_same_values(stand_ins, tmp_path):
    _instants_, path, digest = _instants(tmp_path)
    live = _emit(tmp_path, path, digest, "live")
    sent = len(stand_ins.calls)
    again = _emit(tmp_path, path, digest, "again", "--from-cache")
    assert sent == 1 and len(stand_ins.calls) == sent
    assert (live / e.VALUES_PATH).read_bytes() == (again / e.VALUES_PATH).read_bytes()
    lines = [json.loads(line) for line in (live / e.VALUES_PATH).read_text().splitlines()]
    assert lines[0]["reference"] == "R1" and lines[0]["oracle"]["stated_by_the_service"]["frame_definition"] == (
        e.FRAME_DEFINITION)
    assert len(lines) == 4 and all(len(r["value"]) == 12 for r in lines[1:])
