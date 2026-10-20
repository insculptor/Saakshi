"""The deployment capture: what it may import, what it records, and the differences it must see.

⛔ The generator runs on a host this repository is never installed on, so the first test is
static and needs no library: it imports nothing but the standard library and the binding.
The rest run it end to end in a child process, as it is run on a host.
"""

from __future__ import annotations

import ast
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "generators" / "deployment_capture.py"


def test_it_imports_only_the_standard_library_and_the_binding():
    tree = ast.parse(SCRIPT.read_text(encoding="utf-8"))
    roots = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            roots.add(node.module.split(".")[0])
    foreign = sorted(r for r in roots if r not in sys.stdlib_module_names and r != "swisseph")
    assert foreign == [], f"⛔ the capture must run where only the binding is installed: {foreign}"


# ---------------------------------------------------------------------------------------
# End to end — these call the ephemeris library
# ---------------------------------------------------------------------------------------


def _run(tmp_path: Path, *args: str, env: dict[str, str] | None = None) -> tuple[dict, str]:
    pytest.importorskip(
        "swisseph",
        reason="the capture calls the ephemeris library; it cannot run where it is not installed",
    )
    work = tmp_path / "cwd"
    scratch = tmp_path / "tmp"
    work.mkdir()
    scratch.mkdir()
    environment = {k: v for k, v in os.environ.items() if not k.startswith("SE_")}
    environment.update(TMPDIR=str(scratch), **(env or {}))
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=work,
        env=environment,
        capture_output=True,
        text=True,
        check=True,
        timeout=600,
    )
    lines = proc.stdout.splitlines()
    assert len(lines) == 2, proc.stdout[-400:]
    # ⛔ It writes nothing: the working directory and the temporary directory are left empty.
    assert list(work.iterdir()) == []
    assert list(scratch.iterdir()) == []
    return json.loads(lines[0]), lines[1]


def test_the_observation_carries_its_own_digest_and_the_probes(tmp_path):
    observation, trailer = _run(tmp_path)
    line = json.dumps(observation, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    assert trailer == "observation_sha256 " + hashlib.sha256(line.encode("ascii")).hexdigest()
    assert observation["probe"]["sha256"] == hashlib.sha256(SCRIPT.read_bytes()).hexdigest()
    assert observation["default_state"]["kind"] == "default"
    leap = observation["leap"]
    assert leap["default_state"]["rows"] == leap["empty_directory"]["rows"] == 115
    assert "bit_patterns" not in leap["default_state"]
    assert {b["body"] for b in observation["data_files"]["by_body"]} == {"sun", "moon", "ceres"}
    assert len(observation["delta_t"]) == 9


def test_a_resolved_data_file_is_reported_with_its_digest(tmp_path):
    ephe = Path(__file__).resolve().parents[1] / "cache" / "ephe"
    if not (ephe / "sepl_18.se1").is_file():
        pytest.skip("the pinned data files are not on this machine (cache/ephe)")
    observation, _ = _run(tmp_path, env={"SE_EPHE_PATH": str(ephe)})
    sun = next(b for b in observation["data_files"]["by_body"] if b["body"] == "sun")
    assert sun["source"] == "swiss_file"
    planet = next(f for f in sun["reported_files"] if f["name"] == "sepl_18.se1")
    assert planet["on_disk"] is True
    assert planet["sha256"] == hashlib.sha256((ephe / "sepl_18.se1").read_bytes()).hexdigest()


def test_a_planted_table_is_seen_as_a_difference(tmp_path):
    """⭐ The red control: a pair built to differ. A table that adds an invented insertion
    date stands in for the default state; the comparison must name the boundary it moves."""
    planted = tmp_path / "planted"
    planted.mkdir()
    (planted / "seleapsec.txt").write_text("20200630\n", encoding="ascii")
    observation, _ = _run(tmp_path, "--control-default-dir", str(planted))
    assert observation["default_state"]["kind"] == "explicit_control_directory"
    assert "data_files" not in observation and "delta_t" not in observation
    differing = dict((date, which) for date, which in observation["leap"]["comparison"]["differing"])
    assert "2020-07-01" in differing and "dynamical" in differing["2020-07-01"]
    assert "2020-01-01" not in differing


def test_no_variable_outside_the_allowlist_is_recorded(tmp_path):
    observation, _ = _run(
        tmp_path, env={"SE_MARKER_FOR_TEST": "1", "DATABASE_PASSWORD_FOR_TEST": "sentinel-9f3"}
    )
    text = json.dumps(observation)
    assert "sentinel-9f3" not in text
    assert "SE_MARKER_FOR_TEST=1" in observation["environment"]["library_variables"]


def test_the_full_mode_adds_every_bit_pattern(tmp_path):
    observation, _ = _run(tmp_path, "--full")
    rows = observation["leap"]["default_state"]["bit_patterns"]
    assert len(rows) == 115 and rows[0][0] == "1972-01-01"
