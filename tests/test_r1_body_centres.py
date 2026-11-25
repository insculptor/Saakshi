"""The body-centre states: which solutions each answer must name, where the instants come from, how it reads twice.

⭐ No network. The synthetic service of the geocentric grid's tests answers, in the shape the real one was read in,
naming per body the solutions given here, with numbers that are no body's state.
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


b = _load("r1_body_centres", ROOT / "generators" / "r1_body_centres.py")
grid = b.grid
helpers = _load("r1_geocentric_vectors_test_helpers", ROOT / "tests" / "test_r1_geocentric_vectors.py")

from saakshi.acquisition import Retrieval  # noqa: E402
from saakshi.fixture import Generator, bits  # noqa: E402

IDENTITY = Generator(repo="github.com/insculptor/Saakshi", script=b.SCRIPT, commit="0" * 40)
SOLUTIONS = {t["command"]: (t["target_solution"], t["center_solution"]) for t in b.TARGETS}


class FakeService:
    """`retrieve()`'s signature, answering each body under its own solutions unless a plant says otherwise."""

    def __init__(self, solutions=None, **plant):
        self.solutions, self.plant, self.calls = solutions or SOLUTIONS, plant, []

    def __call__(self, url, *, cache, canonical):
        query = {k: v[0] for k, v in urllib.parse.parse_qs(url.split("?", 1)[1]).items()}
        self.calls.append(query)
        target, centre = self.solutions[query["COMMAND"].strip("'")]
        payload = helpers.respond(query, stamp=f"10:00:{len(self.calls) % 60:02d}", solution=target,
                                  center_solution=centre, **self.plant)
        resource = canonical(payload)
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_bytes(resource)
        return Retrieval(url=url, final_url=url, status=200, size_bytes=len(payload),
                         sha256=hashlib.sha256(payload).hexdigest(), validators={}, payload=payload,
                         prior_copy_agreed=None, resource=resource,
                         resource_sha256=hashlib.sha256(resource).hexdigest())


def _grid_file(tmp_path: Path, jds=(2451545.0, 2451561.0, 2451577.0), *, tamper=None) -> tuple[Path, str]:
    """A values file in the earlier grid's shape: a header listing its instants, one row per instant."""
    instants = [grid.Epoch(jd_tdb=jd, reasons=[f"reason_{i}"]) for i, jd in enumerate(jds)]
    listed = {"rule": "a stated rule", "profile": {"profile": "standard@1"}, "count": len(instants),
              "set_sha256": grid.epoch_set_digest(instants), "values": [e.as_json() for e in instants]}
    if tamper == "set_digest":
        listed["set_sha256"] = "0" * 64
    header = {"record": "header", "title": "earlier grid", "generator": {"commit": "1" * 40},
              "request": {"instants": listed}}
    rows = [{"record": "row", "jd_tdb": jd, "jd_tdb_bits": bits(jd)} for jd in jds]
    if tamper == "row_instant":
        rows.append({"record": "row", "jd_tdb": 2451600.0, "jd_tdb_bits": bits(2451600.0)})
    path = tmp_path / "grid.jsonl"
    path.write_text("\n".join(json.dumps(line) for line in [header, *rows]) + "\n", encoding="utf-8")
    return path, hashlib.sha256(path.read_bytes()).hexdigest()


# --------------------------------------------------------------------------------------
# What is asked
# --------------------------------------------------------------------------------------


def test_the_targets_are_six_body_centres_each_with_its_own_pinned_solutions():
    assert [t["command"] for t in b.TARGETS] == ["499", "599", "699", "799", "899", "999"]
    assert {t["point"] for t in b.TARGETS} == {"body_centre"}
    # ⛔ No body centre is held to the planetary solution's name: that is the barycentre's rule.
    assert all(t["target_solution"] != grid.EXPECTED_SOLUTION for t in b.TARGETS)


def test_the_default_corrections_are_geometric_and_light_time_with_aberration():
    assert b.DEFAULT_CORRECTIONS.split(",") == ["NONE", "LT+S"]


def test_the_plan_asks_every_instant_of_every_body_under_each_correction_once(tmp_path):
    path, digest = _grid_file(tmp_path, jds=tuple(2451545.0 + 16 * i for i in range(160)))
    instants, _ = b.grid_instants(path, digest)
    requests = b.plan(instants, corrections=["NONE", "LT+S"])
    assert len(requests) == 6 * 3 * 2  # 160 instants by 75: three chunks
    assert max(len(r["instants"]) for r in requests) <= 75
    asked = {(r["correction"], r["target"]["command"], e.jd_tdb) for r in requests for e in r["instants"]}
    assert len(asked) == 2 * 6 * 160
    for request in requests:
        query = request["query"]
        assert query["CENTER"] == "'500@399'" and query["REF_SYSTEM"] == "'ICRF'" and query["TIME_TYPE"] == "'TDB'"


def test_the_cache_is_kept_apart_from_the_barycentre_responses(tmp_path):
    stem = b.cache_stem(tmp_path, correction="NONE", digest="a" * 64, command="599", index=0)
    assert b.CACHE_SUBDIRECTORY in stem.parts and grid.CACHE_SUBDIRECTORY not in stem.parts


# --------------------------------------------------------------------------------------
# Where the instants come from
# --------------------------------------------------------------------------------------


def test_the_instants_are_the_earlier_files_with_its_reasons(tmp_path):
    path, digest = _grid_file(tmp_path)
    instants, source = b.grid_instants(path, digest)
    assert [e.jd_tdb for e in instants] == [2451545.0, 2451561.0, 2451577.0]
    assert [e.reasons for e in instants] == [["reason_0"], ["reason_1"], ["reason_2"]]
    assert source["values_file_sha256"] == digest and source["count"] == 3


@pytest.mark.parametrize("tamper, match", [
    ("set_digest", "instant-set digest"),
    ("row_instant", "rows' instants"),
])
def test_an_earlier_file_that_does_not_hold_together_is_refused(tmp_path, tamper, match):
    path, digest = _grid_file(tmp_path, tamper=tamper)
    with pytest.raises(b.Refusal, match=match):
        b.grid_instants(path, digest)


def test_an_earlier_file_of_another_digest_is_refused(tmp_path):
    path, _ = _grid_file(tmp_path)
    with pytest.raises(b.Refusal, match="sha256"):
        b.grid_instants(path, "0" * 64)


# --------------------------------------------------------------------------------------
# What every answer is held to
# --------------------------------------------------------------------------------------


@pytest.mark.parametrize("solutions, match", [
    ({**SOLUTIONS, "599": ("DE441", "jup365_merged")}, "target_solution"),
    ({**SOLUTIONS, "599": ("jup365_merged", "DE441")}, "center_solution"),
])
def test_an_answer_naming_any_other_solution_pair_is_a_stop(tmp_path, solutions, match):
    path, digest = _grid_file(tmp_path)
    instants, _ = b.grid_instants(path, digest)
    requests = b.plan(instants, corrections=["NONE"])
    service = FakeService(solutions=solutions)
    with pytest.raises(b.Refusal, match=match):
        b.read(requests, cache=tmp_path / "cache", digest=grid.epoch_set_digest(instants), from_cache=False,
               sleep=lambda s: None, fetch=service)
    # ⛔ The stop came at Jupiter's request, and nothing after it was sent.
    assert [q["COMMAND"] for q in service.calls] == ["'499'", "'599'"]


def test_the_earlier_grids_own_rule_is_unchanged_without_a_pair():
    """⭐ The keyword is additive: the barycentre generator still holds every answer to the planetary solution."""
    request = helpers._request("NONE", "199")
    response = grid.split(helpers.respond(request["query"]), query=request["query"])
    assert grid.hold(response, request, center="500@399", version=None) == "1.2"
    bad = grid.split(helpers.respond(request["query"], solution="mar099"), query=request["query"])
    with pytest.raises(grid.Refusal, match="target_solution"):
        grid.hold(bad, request, center="500@399", version=None)


# --------------------------------------------------------------------------------------
# The run
# --------------------------------------------------------------------------------------


@pytest.fixture
def stand_ins(monkeypatch, tmp_path):
    service = FakeService()
    monkeypatch.setattr(b, "retrieve", service)
    monkeypatch.setattr(b, "generator_for", lambda script: IDENTITY)
    monkeypatch.setattr(b.time, "sleep", lambda s: None)
    return service


def _emit(tmp_path, name, *extra):
    path, digest = _grid_file(tmp_path) if not (tmp_path / "grid.jsonl").exists() else (
        tmp_path / "grid.jsonl", hashlib.sha256((tmp_path / "grid.jsonl").read_bytes()).hexdigest())
    out = tmp_path / name
    b.main(["--grid-values", str(path), "--grid-values-sha256", digest, "--out", str(out),
            "--cache", str(tmp_path / "cache"), "--budget-row", "placeholder-row", *extra])
    return out


def test_the_second_emission_reads_the_cache_and_writes_the_same_values(stand_ins, tmp_path):
    live = _emit(tmp_path, "live")
    sent = len(stand_ins.calls)
    assert sent == 6 * 2  # six bodies, two corrections, one chunk
    again = _emit(tmp_path, "again", "--from-cache")
    assert len(stand_ins.calls) == sent  # ⛔ the cache read sent nothing
    assert (live / b.VALUES_PATH).read_bytes() == (again / b.VALUES_PATH).read_bytes()
    kinds = {json.loads(line).get("retrieval_kind") for line in (again / b.ACQUISITION_PATH).read_text().splitlines()[1:]}
    assert kinds == {"cache_read"}


def test_the_values_file_names_each_bodys_solutions_and_computes_nothing(stand_ins, tmp_path):
    out = _emit(tmp_path, "live")
    lines = [json.loads(line) for line in (out / b.VALUES_PATH).read_text().splitlines()]
    header, rows = lines[0], lines[1:]
    assert header["reference"] == "R1" and header["fixture_kind"] == "numeric_pin"
    assert header["classification"] == {"state_none": {"class": "reference_only"},
                                        "state_lt_s": {"class": "reference_only"}}
    assert header["budget_row"] == "placeholder-row"
    assert header["request"]["instants"]["taken_from"]["values_file_sha256"] == hashlib.sha256(
        (tmp_path / "grid.jsonl").read_bytes()).hexdigest()
    assert len(rows) == 3 * 6 * 2
    for row in rows:
        assert (row["target_solution"], row["center_solution"]) == SOLUTIONS[row["target_command"]]
        assert row["target_point"] == "body_centre"
        assert not any("diff" in key or "minus" in key for key in row)
    record = json.loads((out / b.ACQUISITION_PATH).read_text().splitlines()[0])
    assert record["oracle"]["values_file"]["path"] == b.VALUES_PATH


def test_a_record_is_never_overwritten(stand_ins, tmp_path):
    _emit(tmp_path, "live")
    with pytest.raises(b.Refusal, match="never overwritten"):
        _emit(tmp_path, "live")


def test_the_plan_alone_sends_nothing(stand_ins, tmp_path, capsys):
    _emit(tmp_path, "plan", "--plan-only")
    assert stand_ins.calls == [] and "12 requests" in capsys.readouterr().out
