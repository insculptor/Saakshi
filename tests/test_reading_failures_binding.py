"""A reading that raises stops the generator before anything is written — through the binding.

The defect, and the tests that read the code for it without any library, are in
``test_reading_failures.py``. These call the binding and are skipped where it is absent.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

# --- through the binding ----------------------------------------------------------------

swe = pytest.importorskip("swisseph", reason="the ephemeris binding is absent (ORACLE_LIBRARIES=absent)")

from saakshi import conventions, swiss  # noqa: E402
from saakshi.swiss import MODES, ReadingRefused, Session, SurveyRefusal, UnattestedReport  # noqa: E402

EPHE = ROOT / "cache" / "ephe"
EPOCH = [("epoch_2000", "reference_epoch", 2451545.0)]
SUN = ((swe.SUN, "sun"),)


def _generator(name: str):
    sys.dont_write_bytecode = True
    spec = importlib.util.spec_from_file_location(name, ROOT / "generators" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(ROOT / "generators"))
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def session(tmp_path):
    """The analytical source only: an empty directory on the path, so no data file answers."""
    empty = tmp_path / "empty"
    empty.mkdir()
    s = Session(ephe_path=str(empty), sidereal_mode=swe.SIDM_LAHIRI)
    yield s
    swe.close()


def _all_reporting():
    return {("calc_ut", body, key): swiss.REPORTS
            for body, _ in SUN for key in conventions.apparent_keys()}


def test_an_attested_body_is_read(session):
    """⚠ The control: with every word attested, the section reads its rows."""
    rows = conventions.apparent_variants(EPOCH, SUN, MODES["moshier"], session, attested=_all_reporting())
    assert len(rows) == len(conventions.APPARENT_VARIANTS)


@pytest.mark.parametrize("verdict", [None, swiss.ECHOES, swiss.UNCOVERED])
def test_a_body_not_shown_reporting_stops_the_section(session, verdict):
    attested = _all_reporting()
    key = ("calc_ut", swe.SUN, conventions.apparent_keys()[3])
    if verdict is None:
        del attested[key]
    else:
        attested[key] = verdict
    with pytest.raises(UnattestedReport):
        conventions.apparent_variants(EPOCH, SUN, MODES["moshier"], session, attested=attested)


def test_a_reading_that_raises_is_not_swallowed(session, monkeypatch):
    def broken(*args):
        raise RuntimeError("a reading failed")

    monkeypatch.setattr(conventions.swe, "calc_ut", broken)
    with pytest.raises(RuntimeError, match="a reading failed"):
        conventions.apparent_variants(EPOCH, SUN, MODES["moshier"], session, attested=_all_reporting())


def test_the_keys_are_the_reference_and_every_variant():
    keys = conventions.apparent_keys()
    assert keys[0] == swe.FLG_SPEED and len(keys) == len(set(keys)) == 1 + len(conventions.APPARENT_VARIANTS)


# --- the attestation child ---------------------------------------------------------------


def _fake_child(monkeypatch, *, returncode=0, stdout="", stderr=""):
    seen = {}

    def run(args, **kwargs):
        seen.update(args=args, **kwargs)
        return subprocess.CompletedProcess(args, returncode, stdout=stdout, stderr=stderr)

    monkeypatch.setattr(swiss.subprocess, "run", run)
    return seen


def _reading(body, key, condition, requested_source, returned_source):
    return {"entry_point": "calc_ut", "body": body, "condition": condition,
            "requested": swiss.SOURCE_FLAGS[requested_source] | key,
            "returned": swiss.SOURCE_FLAGS[returned_source] | key}


def test_the_child_is_fresh_and_isolated_and_the_verdicts_are_the_parents(monkeypatch, tmp_path):
    key = swe.FLG_SPEED
    readings = [_reading(0, key, c, s, "moshier") for c, s, *_ in swiss.FIXED_CONDITIONS]
    seen = _fake_child(monkeypatch, stdout=json.dumps({"edges": [], "readings": readings}))
    result = swiss.measure_reporting(bodies=[0], keys=[key], ephe_path=tmp_path, sidereal_mode=0)
    assert seen["args"][:3] == [sys.executable, "-I", "-c"]
    assert not any(name.startswith("SE_") for name in seen["env"])
    assert result["attested"] == {("calc_ut", 0, key): swiss.REPORTS}
    assert result["evidence"]["verdicts"] == [{"body": 0, "non_ephemeris_key": key, "verdict": "reports"}]


def test_one_echo_among_the_readings_refuses_the_body(monkeypatch, tmp_path):
    key = swe.FLG_SPEED
    readings = [_reading(0, key, c, s, "moshier") for c, s, *_ in swiss.FIXED_CONDITIONS]
    readings[0] = _reading(0, key, swiss.FIXED_CONDITIONS[0][0], "swiss_file", "swiss_file")
    _fake_child(monkeypatch, stdout=json.dumps({"edges": [], "readings": readings}))
    result = swiss.measure_reporting(bodies=[0], keys=[key], ephe_path=tmp_path, sidereal_mode=0)
    assert result["attested"] == {("calc_ut", 0, key): swiss.ECHOES}


def test_a_failed_child_is_refused(monkeypatch, tmp_path):
    _fake_child(monkeypatch, returncode=1, stderr="boom")
    with pytest.raises(ReadingRefused, match="attestation child failed"):
        swiss.measure_reporting(bodies=[0], keys=[swe.FLG_SPEED], ephe_path=tmp_path, sidereal_mode=0)


def test_a_body_with_no_reading_is_refused(monkeypatch, tmp_path):
    readings = [_reading(0, swe.FLG_SPEED, c, s, "moshier") for c, s, *_ in swiss.FIXED_CONDITIONS]
    _fake_child(monkeypatch, stdout=json.dumps({"edges": [], "readings": readings}))
    with pytest.raises(SurveyRefusal, match="no reading was returned"):
        swiss.measure_reporting(bodies=[0, 1], keys=[swe.FLG_SPEED], ephe_path=tmp_path, sidereal_mode=0)


@pytest.mark.skipif(not (EPHE / "sepl_18.se1").is_file(), reason="cache/ephe holds no data files")
def test_the_sun_is_measured_reporting_under_the_speed_bit():
    """⭐ One real measurement, through the real child, on the pinned data files."""
    result = swiss.measure_reporting(bodies=[swe.SUN], keys=[swe.FLG_SPEED], ephe_path=EPHE,
                                     sidereal_mode=0)
    assert result["attested"] == {("calc_ut", swe.SUN, swe.FLG_SPEED): swiss.REPORTS}
    assert len(result["evidence"]["readings"]) == len(swiss.FIXED_CONDITIONS) + len(swiss.TABLE_READINGS)
    assert len(result["evidence"]["edges"]) == 1


# --- the two generators -----------------------------------------------------------------


def test_the_binding_probe_reads_its_rung_through_the_attestation(tmp_path):
    probe = _generator("probe6b_ffi")
    empty = tmp_path / "empty"
    empty.mkdir()
    swe.set_ephe_path(str(empty))
    try:
        attestation = {"attested": {("calc_ut", swe.SUN, swe.FLG_SPEED): swiss.REPORTS},
                       "evidence": {"verdicts": []}}
        assertion = probe.ephemeris_assertion(attestation, {"files": []})
        assert assertion["position_rung"]["kind"] == "reported"
        assert assertion["position_rung_attestation"]["data_files"] == {"files": []}
        with pytest.raises(UnattestedReport):
            probe.ephemeris_assertion({"attested": {}, "evidence": {}}, {"files": []})
    finally:
        swe.close()


def _staged_main(probes, monkeypatch, tmp_path, *, fail_in=None):
    """`main`, with every section replaced by one that writes a stand-in file, one of them
    optionally raising after another has already written."""
    monkeypatch.setattr(probes, "generator_for", lambda script: None)
    monkeypatch.setattr(probes, "verify_ephe_set", lambda path: [])
    monkeypatch.setattr(probes, "ephe_set_identity", lambda path, pins: {})
    monkeypatch.setattr(probes, "describe_reserved_names", lambda: "")
    monkeypatch.setattr(probes.Session, "reset", lambda self: None)
    for name in ("write_delta_t", "write_apparent", "write_refraction", "write_leap_seconds",
                 "write_polar_houses", "write_state_audit"):
        def section(*, out_dir, name=name, **kwargs):
            if name == fail_in:
                raise RuntimeError(f"{name}: a reading failed")
            path = out_dir / "conventions" / f"{name}.jsonl"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("{}\n", encoding="utf-8")
            return path, 1
        monkeypatch.setattr(probes, name, section)
    out = tmp_path / "out"
    monkeypatch.setattr(sys, "argv", ["convention_probes.py", "--ephe-path", str(tmp_path), "--out", str(out)])
    return out


def test_a_section_that_raises_leaves_out_untouched(monkeypatch, tmp_path):
    probes = _generator("convention_probes")
    out = _staged_main(probes, monkeypatch, tmp_path, fail_in="write_apparent")
    with pytest.raises(RuntimeError, match="write_apparent"):
        probes.main()
    assert not out.exists()  # ⛔ the time-offset section ran first and wrote nothing here


def test_every_section_is_published_once_all_have_been_read(monkeypatch, tmp_path):
    """⚠ The control for the test above."""
    probes = _generator("convention_probes")
    out = _staged_main(probes, monkeypatch, tmp_path)
    assert probes.main() == 0
    assert len(list((out / "conventions").glob("*.jsonl"))) == 6
