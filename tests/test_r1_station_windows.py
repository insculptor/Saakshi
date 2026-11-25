"""States around published Mercury events: the lattice declared, overlapping windows merged, read twice.

⭐ No network: the geocentric grid's synthetic service answers.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
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


w = _load("r1_station_windows", ROOT / "generators" / "r1_station_windows.py")
grid = w.grid
helpers = _load("r1_geocentric_vectors_test_helpers_w", ROOT / "tests" / "test_r1_geocentric_vectors.py")

from saakshi.fixture import Generator  # noqa: E402

IDENTITY = Generator(repo="github.com/insculptor/Saakshi", script=w.SCRIPT, commit="0" * 40)


def _transcription(tmp_path, stamps, *, bad=None):
    rows = [{"record": "header", "title": "events"}]
    for k, stamp in enumerate(stamps):
        rows.append({"record": "row", "section": "s", "utc_from_printed": stamp, "printed_event": f"e{k}"})
    rows.append({"record": "row", "section": "statements", "printed": "no instant here"})
    if bad:
        rows.append({"record": "row", "section": "s", "utc_from_printed": bad})
    path = tmp_path / "t.jsonl"
    path.write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    return path, hashlib.sha256(path.read_bytes()).hexdigest()


def test_the_window_is_every_sixteenth_within_a_day_and_a_sixteenth_of_the_printed_instant(tmp_path):
    path, digest = _transcription(tmp_path, ["2026-02-25T16:46"])
    found, _ = w.events(path, digest)
    instants = w.lattice(found)
    u = grid.modes.julian_day("2026-02-25T16:46:00")
    assert all(e.jd_tdb * 16 == int(e.jd_tdb * 16) for e in instants)
    assert instants[0].jd_tdb >= u - 1 - 1 / 16 and instants[-1].jd_tdb <= u + 1 + 1 / 16
    assert instants[0].jd_tdb - 1 / 16 < u - 1 - 1 / 16 and instants[-1].jd_tdb + 1 / 16 > u + 1 + 1 / 16
    assert len(instants) == 34
    assert {r for e in instants for r in e.reasons} == {"window:s:2026-02-25T16:46"}


def test_overlapping_windows_are_one_set_and_each_instant_keeps_every_reason(tmp_path):
    path, digest = _transcription(tmp_path, ["2026-02-25T16:46", "2026-02-25T16:49", "2026-02-26T06:50"])
    instants = w.lattice(w.events(path, digest)[0])
    jds = [e.jd_tdb for e in instants]
    assert jds == sorted(set(jds))
    assert max(len(e.reasons) for e in instants) == 3 and len(instants) < 3 * 34


def test_an_event_instant_that_is_not_a_civil_minute_is_refused(tmp_path):
    path, digest = _transcription(tmp_path, ["2026-02-25T16:46"], bad="2026-02-25 16:46 JST")
    with pytest.raises(w.Refusal, match="civil minute"):
        w.events(path, digest)


def test_a_transcription_of_another_digest_or_with_no_instant_is_refused(tmp_path):
    path, _ = _transcription(tmp_path, ["2026-02-25T16:46"])
    with pytest.raises(w.Refusal, match="sha256"):
        w.events(path, "0" * 64)
    empty, digest = _transcription(tmp_path, [])
    with pytest.raises(w.Refusal, match="no event"):
        w.events(empty, digest)


def test_the_plan_asks_mercury_and_the_sun_under_both_corrections(tmp_path):
    path, digest = _transcription(tmp_path, ["2026-02-25T16:46", "2026-11-13T09:15"])
    requests = w.plan(w.lattice(w.events(path, digest)[0]), corrections=["NONE", "LT+S"])
    assert {(r["target"]["command"], r["correction"]) for r in requests} == {
        ("199", "NONE"), ("10", "NONE"), ("199", "LT+S"), ("10", "LT+S")}
    assert max(len(r["instants"]) for r in requests) <= 75


@pytest.fixture
def stand_ins(monkeypatch):
    service = helpers.FakeService()
    monkeypatch.setattr(w, "retrieve", service)
    monkeypatch.setattr(w, "generator_for", lambda script: IDENTITY)
    monkeypatch.setattr(w.time, "sleep", lambda s: None)
    return service


def test_the_second_emission_reads_the_cache_and_writes_the_same_values(stand_ins, tmp_path):
    path, digest = _transcription(tmp_path, ["2026-02-25T16:46"])

    def emit(name, *extra):
        out = tmp_path / name
        w.main(["--stations", str(path), "--stations-sha256", digest, "--out", str(out), "--cache",
                str(tmp_path / "cache"), "--budget-row", "placeholder-row", *extra])
        return out

    live = emit("live")
    sent = len(stand_ins.calls)
    again = emit("again", "--from-cache")
    assert sent == 4 and len(stand_ins.calls) == sent
    assert (live / w.VALUES_PATH).read_bytes() == (again / w.VALUES_PATH).read_bytes()
    lines = [json.loads(x) for x in (live / w.VALUES_PATH).read_text().splitlines()]
    assert lines[0]["request"]["events"]["from"]["sha256"] == digest
    assert len(lines) == 1 + 34 * 2 * 2
    with pytest.raises(w.Refusal, match="never overwritten"):
        emit("live")
