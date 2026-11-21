"""The drift control for the geocentric grid: every outcome it can report, and that it never gates.

⭐ No network. A grid is emitted from the synthetic service of ``test_r1_geocentric_vectors.py``, and the drift
job then re-asks it of the same service with one thing planted at a time.
"""

from __future__ import annotations

import importlib.util
import json
import sys
import urllib.error
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True


def _load(name: str, path: Path):
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


base = _load("test_r1_geocentric_vectors", ROOT / "tests" / "test_r1_geocentric_vectors.py")
g = base.g
drift = _load("r1_geocentric_drift", ROOT / "generators" / "r1_geocentric_drift.py")

from saakshi.acquisition import AcquisitionError  # noqa: E402

assert drift.grid is g  # ⛔ one copy of the grid's reader, so the two are tested as one


@pytest.fixture
def emitted(monkeypatch, tmp_path) -> Path:
    service = base.FakeService()
    monkeypatch.setattr(g, "retrieve", service)
    monkeypatch.setattr(g, "generator_for", lambda script: base.IDENTITY)
    monkeypatch.setattr(drift, "generator_for", lambda script: base.IDENTITY)
    monkeypatch.setattr(g, "verify", lambda path: None)
    monkeypatch.setattr(g, "oracle_identity", lambda path, pin: {"dataset": "de440s.bsp", "sha256": "1" * 64})
    monkeypatch.setattr(g, "event_epochs", lambda kernel, interval: [(2451549.5, "conjunction_test")])
    monkeypatch.setattr(g.modes, "read_interval", lambda manifest: base.INTERVAL)
    monkeypatch.setattr(g.time, "sleep", lambda s: None)
    out = tmp_path / "grid"
    g.main(["--profile", "p.toml", "--kernel", "k.bsp", "--out", str(out), "--cache", str(tmp_path / "cache")])
    return out / g.VALUES_PATH


def _run(values: Path, tmp_path: Path, *extra, **plant) -> tuple[dict, list[dict], base.FakeService]:
    service = base.FakeService(**plant)
    assert drift.main(["--values", str(values), "--out", str(tmp_path / "drift"), *extra],
                      sleep=lambda s: None, fetch=service) == 0  # ⛔ exits 0 whatever it finds
    lines = (tmp_path / "drift" / drift.REPORT_PATH).read_text().splitlines()
    header, rows = json.loads(lines[0]), [json.loads(line) for line in lines[1:]]
    return header, rows, service


def _outcomes(rows):
    return {r["outcome"] for r in rows if r["finding"] == "query_compared"}


def test_a_quiet_service_is_reported_quiet_on_the_stated_sample(emitted, tmp_path):
    header, rows, service = _run(emitted, tmp_path)
    assert _outcomes(rows) == {"no_drift"}
    assert len(service.calls) == 30 and header["summary"]["sample"]["rule"] == "first_chunk"
    assert (header["fixture_kind"], header["reference"]) == ("provenance_record", "instrument")
    assert rows[-1]["finding"] == "summary" and rows[-1]["queries_compared"] == 30


def test_the_whole_grid_can_be_asked(emitted, tmp_path):
    _header, _rows, service = _run(emitted, tmp_path, "--sample", "all")
    instants = g.epochs(g.lattice_epochs(base.INTERVAL) + [(2451549.5, "conjunction_test")])
    assert len(service.calls) == 30 * len(g.chunks(instants)) > 30


def test_the_queries_are_the_values_files_own(emitted, tmp_path):
    _header, _rows, service = _run(emitted, tmp_path)
    record = [json.loads(line) for line in (emitted.parent / Path(g.ACQUISITION_PATH).name).read_text().splitlines()[1:]]
    urls = {r["request_id"]: r["url"] for r in record}
    sent = [g.service.build_url(q) for q in service.calls]
    assert sent == [urls[r["request_id"]] for r in _rows if r["finding"] == "query_compared"]


@pytest.mark.parametrize("plant, outcome", [
    ({"solution": "DE442"}, "service_state_moved"),
    ({"version": "1.3"}, "service_state_moved"),
    ({"value_offset": 1e-12}, "values_moved"),
    ({"paragraph": "States have been corrected for light-time and gravitational deflection."}, "classification_stale"),
    ({"output_type": "APPARENT cartesian states"}, "classification_stale"),
    ({"columns": "JDTDB, Calendar Date (TDB), X, Y, Z, VX, VY, VZ, LT, RG,"}, "classification_stale"),
])
def test_each_kind_of_drift_is_named_and_proposed_and_gates_nothing(emitted, tmp_path, plant, outcome):
    _header, rows, _service = _run(emitted, tmp_path, **plant)
    assert _outcomes(rows) == {outcome}
    assert all(r["proposal"] == g.service.DRIFT_PROPOSALS[outcome] for r in rows if r["finding"] == "query_compared")


def test_a_moved_value_is_shown_recorded_and_now(emitted, tmp_path):
    _header, rows, _service = _run(emitted, tmp_path, value_offset=1e-12)
    first = next(r for r in rows if r["finding"] == "query_compared")
    assert first["values_changed"] == first["instants_compared"]
    assert first["values_changed_sample"][0]["recorded"] != first["values_changed_sample"][0]["now"]


def test_a_new_earth_orientation_file_alone_is_listed_and_does_not_classify(emitted, tmp_path):
    _header, rows, _service = _run(emitted, tmp_path, eop="eop.261201.p270301")
    compared = [r for r in rows if r["finding"] == "query_compared"]
    assert _outcomes(rows) == {"no_drift"}
    assert all(r["recorded_only_state_changes"]["earth_orientation_file"]["now"] == "eop.261201.p270301"
               for r in compared)


def test_a_query_that_could_not_be_asked_is_not_observed_never_quiet(emitted, tmp_path, monkeypatch):
    def down(url, **kwargs):
        raise AcquisitionError("could not be retrieved") from urllib.error.HTTPError("u", 400, "no", {}, None)

    assert drift.main(["--values", str(emitted), "--out", str(tmp_path / "drift")],
                      sleep=lambda s: None, fetch=down) == 0
    rows = [json.loads(line) for line in (tmp_path / "drift" / drift.REPORT_PATH).read_text().splitlines()[1:]]
    assert _outcomes(rows) == {"not_observed"}


def test_a_record_from_another_emission_is_refused(emitted, tmp_path):
    record = emitted.parent / Path(g.ACQUISITION_PATH).name
    lines = record.read_text().splitlines()
    header = json.loads(lines[0])
    header["oracle"]["values_file"]["sha256"] = "0" * 64
    record.write_text("\n".join([json.dumps(header), *lines[1:]]) + "\n")
    with pytest.raises(drift.Refusal, match="another digest"):
        drift.main(["--values", str(emitted), "--out", str(tmp_path / "drift")], sleep=lambda s: None,
                   fetch=base.FakeService())


def test_a_report_is_never_overwritten(emitted, tmp_path):
    _run(emitted, tmp_path)
    with pytest.raises(drift.Refusal, match="never overwritten"):
        _run(emitted, tmp_path)


def test_requests_are_paced_one_at_a_time(emitted, tmp_path):
    pauses = []
    drift.main(["--values", str(emitted), "--out", str(tmp_path / "drift")], sleep=pauses.append,
               fetch=base.FakeService())
    assert pauses == [g.REQUEST_INTERVAL_SECONDS] * 29
