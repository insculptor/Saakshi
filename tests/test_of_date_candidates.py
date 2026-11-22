"""The feasibility record's own machinery: its instants, its differences, and what it refuses before reading.

⭐ Nothing here needs an oracle library. The readings themselves run only in a dedicated environment holding exactly
the pinned libraries; what can be checked without them — that the sweep is the declared one bit for bit, that the
one computation this file makes (a difference) is well conditioned, and that every refusal fires before anything is
read — is checked here, where continuous integration can see it.
"""

from __future__ import annotations

import importlib.util
import json
import math
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from saakshi.fixture import bits

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "generators" / "of_date_candidates.py"
_spec = importlib.util.spec_from_file_location("of_date_candidates", SCRIPT)
gen = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gen)  # type: ignore[union-attr]


# --- the instants ------------------------------------------------------------------------------------------------


def test_the_sweep_is_the_declared_one_bit_for_bit():
    """⭐ The rule from the span's ends reproduces the published endpoints and count exactly — ⛔ no grid invented."""
    ts = gen.sweep()
    assert len(ts) == 20001
    assert (bits(ts[0]), bits(ts[-1])) == (bits(-4.499_945_242_984_257), bits(6.500_520_191_649_555))
    lo, hi = -4.499_945_242_984_257, 6.500_520_191_649_555
    assert all(bits(t) == bits(lo + (hi - lo) * i / 20000) for i, t in enumerate(ts))
    assert sum(1 for t in ts if abs(t) <= 1.5) == 5454


def _values(path: Path, rows: list[tuple[float, str]]) -> str:
    lines = [json.dumps({"record": "header"})] + [json.dumps({"record": "row", "jd_tdb": v, "jd_tdb_bits": b})
                                                   for v, b in rows]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    import hashlib

    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_the_grid_is_its_files_distinct_instants_and_only_by_digest(tmp_path):
    path = tmp_path / "v.jsonl"
    digest = _values(path, [(2451545.5, bits(2451545.5)), (2451545.0, bits(2451545.0)), (2451545.5, bits(2451545.5))])
    assert gen.grid_instants(path, digest) == [2451545.0, 2451545.5]
    with pytest.raises(gen.Refusal, match="sha256"):
        gen.grid_instants(path, "0" * 64)


def test_an_instant_whose_pattern_disagrees_is_refused(tmp_path):
    path = tmp_path / "v.jsonl"
    digest = _values(path, [(2451545.0, bits(2451545.5))])
    with pytest.raises(gen.Refusal, match="different numbers"):
        gen.grid_instants(path, digest)


# --- the differences ---------------------------------------------------------------------------------------------


def test_a_separation_is_well_conditioned_near_zero():
    """⭐ One milliarcsecond in declination, recovered to well under a microarcsecond."""
    a = gen.unit_vector(6.0, 10.0)
    b = gen.unit_vector(6.0, 10.0 + 1.0e-3 / 3600.0)
    assert gen.separation_arcsec(a, a) == 0.0
    assert abs(gen.separation_arcsec(a, b) - 1.0e-3) < 1.0e-9
    assert gen.separation_arcsec(a, b) == gen.separation_arcsec(b, a)


def test_the_rotation_between_two_matrices_is_its_angle():
    angle = 1.0e-6  # radians about z
    c, s = math.cos(angle), math.sin(angle)
    rz = [[c, -s, 0.0], [s, c, 0.0], [0.0, 0.0, 1.0]]
    identity = [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]
    assert abs(gen.rotation_between_arcsec(rz, identity) - angle * gen.ARCSEC_PER_RADIAN) < 1.0e-9
    assert gen.rotation_between_arcsec(identity, identity) == 0.0


def test_a_longitude_difference_is_taken_across_the_turn():
    assert abs(gen.wrapped_degrees(0.1, 359.9) - 0.2) < 1e-12
    assert abs(gen.wrapped_degrees(359.9, 0.1) + 0.2) < 1e-12


# --- the driver's answers ----------------------------------------------------------------------------------------


def _answer(kind: str, values: list[float]) -> str:
    return " ".join([kind, *(bits(v) for v in values)])


def test_answers_are_read_by_their_patterns():
    assert gen.parse_driver([_answer("A", [1.5, -0.0])], "A", 1, 2) == [[1.5, -0.0]]
    assert bits(gen.parse_driver([_answer("A", [1.5, -0.0])], "A", 1, 2)[0][1]) == "8000000000000000"


@pytest.mark.parametrize(
    "lines,match",
    [
        (["E novas_sky_pos 3"], "refused a request"),
        ([_answer("A", [1.0])], "of 2 values"),
        ([_answer("M", [1.0, 2.0])], "not a A answer"),
        (["A 7ff0000000000000 0000000000000000"], "non-finite"),
        ([_answer("A", [1.0, 2.0])] * 2, "2 A answers for 1"),
        ([], "0 A answers for 1"),
    ],
)
def test_every_bad_answer_refuses(lines, match):
    with pytest.raises(gen.Refusal, match=match):
        gen.parse_driver(lines, "A", 1, 2)


def test_the_tally_keeps_the_largest_magnitude_its_place_and_the_range():
    tally = gen.Tally()
    for value, where in ((1.0e-5, "a"), (-2.0e-3, "b"), (5.0e-4, "c")):
        tally.add("s", "d", "x", value, where)
    (entry,) = tally.as_json()
    assert (entry["largest_arcsec"], entry["largest_at"], entry["instants"]) == (-2.0e-3, "b", 3)
    assert entry["range_arcsec"] == [-2.0e-3, 5.0e-4]
    assert entry["above_levels"] == [2, 1, 0]


def test_a_build_records_file_names_are_carried_as_values_not_keys():
    """⛔ The writer refuses ``target.c`` as a key; the record keeps every name and digest, in order, as values."""
    from saakshi.fixture import validate_header

    record = {"compiler": "c", "archive_sha256": "a" * 64, "sources": {"target.c": "1" * 64, "solsys-cspice.c": "2" * 64}}
    carried = gen.carried_build_record(record)
    assert carried["sources"] == [{"file": "target.c", "sha256": "1" * 64},
                                  {"file": "solsys-cspice.c", "sha256": "2" * 64}]
    assert {k: v for k, v in carried.items() if k != "sources"} == {"compiler": "c", "archive_sha256": "a" * 64}
    from saakshi.fixture import Generator, Header

    header = Header(fixture_kind="numeric_pin", reference="R2", generated="2026-01-01", budget_row="r",
                    generator=Generator(repo="r", script="s", commit="0" * 40), request={"grid": "x"},
                    classification={"a": {"class": "reference_only"}}, oracle={"build": carried})
    validate_header(header, where="t")
    with pytest.raises(gen.Refusal, match="no sources"):
        gen.carried_build_record({"compiler": "c"})


def test_a_library_other_than_the_pin_is_refused_before_it_is_imported(monkeypatch):
    monkeypatch.setattr(gen.metadata, "version", lambda name: "0")
    monkeypatch.setitem(sys.modules, "erfa", None)  # an import would raise, and the refusal must come first
    with pytest.raises(gen.Refusal, match="not the pins"):
        gen.python_identity(Path("unused"))


# --- refused before anything is read -----------------------------------------------------------------------------


def _git(repo: Path, *args: str) -> None:
    environment = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@example.invalid",
                       GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@example.invalid")
    subprocess.run(["git", "-c", "commit.gpgsign=false", *args], cwd=repo, env=environment, check=True,
                   capture_output=True)


def _run(tmp_path: Path, out: Path, budget_row: str = "a-row") -> subprocess.CompletedProcess:
    repo = tmp_path / "repo"
    if not repo.exists():
        (repo / "generators" / "native").mkdir(parents=True)
        shutil.copy2(SCRIPT, repo / "generators" / SCRIPT.name)
        shutil.copy2(gen.DRIVER_SOURCE, repo / "generators" / "native" / gen.DRIVER_SOURCE.name)
        shutil.copytree(ROOT / "src", repo / "src", ignore=shutil.ignore_patterns("__pycache__"))
        _git(repo, "init", "-q")
        _git(repo, "add", "-A")
        _git(repo, "commit", "-q", "-m", "one")
    nowhere = str(tmp_path / "nowhere")
    args = ["--kernel", nowhere, "--grid-values", nowhere, "--grid-values-sha256", "0" * 64,
            "--supernovas-source", nowhere, "--supernovas-tarball", nowhere, "--supernovas-archive", nowhere,
            "--supernovas-build-record", nowhere, "--cspice-toolkit", nowhere, "--cspice-package", nowhere,
            "--erfa-licence", nowhere, "--budget-row", budget_row, "--out", str(out)]
    return subprocess.run([sys.executable, "-B", str(repo / "generators" / SCRIPT.name), *args], cwd=repo,
                          capture_output=True, text=True, timeout=120, check=False)


def test_an_existing_output_and_an_unstated_row_are_refused_first(tmp_path):
    out = tmp_path / "out"
    out.mkdir()
    (out / gen.OUTPUT_NAME).write_text("held\n", encoding="ascii")
    done = _run(tmp_path, out)
    assert done.returncode == 2 and "exists" in done.stderr
    assert (out / gen.OUTPUT_NAME).read_text(encoding="ascii") == "held\n"
    done = _run(tmp_path, tmp_path / "fresh", budget_row=" padded ")
    assert done.returncode == 2 and "--budget-row" in done.stderr
