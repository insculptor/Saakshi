"""The civil-time conversion probe: what it may import, what it records, and the differences it must see.

⛔ Like the deployment capture, the probe imports nothing but the standard library and the binding,
so the first test is static and needs no library. The rest run it end to end in a child process.
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

SCRIPT = Path(__file__).resolve().parents[1] / "generators" / "utc_conversion.py"

#: The 115-row grid digest the deployment capture recorded for the same grid, in the default
#: state, on both builds it has met. ⭐ Pinned so a library that moves one bit of either output on
#: the grid turns this red.
GRID_DIGEST = "54cf3e606b2ddeb2e4aac8e75ad9a986a76d840bb3df341fdd8a48acdaa5c152"


def test_it_imports_only_the_standard_library_and_the_binding():
    tree = ast.parse(SCRIPT.read_text(encoding="utf-8"))
    roots = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            roots.add(node.module.split(".")[0])
    foreign = sorted(r for r in roots if r not in sys.stdlib_module_names and r != "swisseph")
    assert foreign == [], f"⛔ the probe must run where only the binding is installed: {foreign}"


# ---------------------------------------------------------------------------------------
# End to end — these call the ephemeris library
# ---------------------------------------------------------------------------------------


def _run(tmp_path: Path, *args: str) -> dict:
    pytest.importorskip(
        "swisseph",
        reason="the probe calls the ephemeris library; it cannot run where it is not installed",
    )
    work = tmp_path / "cwd"
    scratch = tmp_path / "tmp"
    work.mkdir()
    scratch.mkdir()
    environment = dict(os.environ, TMPDIR=str(scratch), SE_MARKER_FOR_TEST="1")
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
    line = json.dumps(json.loads(lines[0]), sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    assert line == lines[0]
    assert lines[1] == "observation_sha256 " + hashlib.sha256(line.encode("ascii")).hexdigest()
    return json.loads(lines[0])


@pytest.fixture(scope="module")
def observation(tmp_path_factory) -> dict:
    return _run(tmp_path_factory.mktemp("compact"))


def test_the_observation_names_its_probe_and_strips_the_library_variables(observation):
    assert observation["probe"]["sha256"] == hashlib.sha256(SCRIPT.read_bytes()).hexdigest()
    assert observation["probe"]["mode"] == "compact"
    assert observation["children"]["removed_environment_variables"] == ["SE_MARKER_FOR_TEST"]


def test_the_default_state_reads_the_grid_the_deployment_capture_read(observation):
    states = observation["state"]["states"]
    assert states["default_first_call"]["grid_rows"] == 115
    assert states["default_first_call"]["grid_rows_sha256"] == GRID_DIGEST
    # ⛔ Without --ephe-path the data-files state is recorded as not taken, never skipped silently.
    assert states["data_files_directory"]["taken"] is False


def test_a_call_history_and_an_empty_directory_change_neither_output(observation):
    states = observation["state"]["states"]
    for name in ("default_after_call_history", "empty_directory"):
        against = states[name]["against_default_first_call"]
        for label in ("dynamical", "universal"):
            assert against[label]["identical"] == against[label]["of"] == 123, (name, label)


def test_a_user_defined_offset_is_seen_on_the_universal_output(observation):
    """⭐ The red control for part 1: a state built to differ must be reported as differing."""
    against = observation["state"]["states"]["user_defined_time_offset"]["against_default_first_call"]
    assert against["universal"]["identical"] < against["universal"]["of"]
    assert against["universal_is_the_plain_julian_day"]["this_state"] == 123


def test_the_steps_are_found_on_the_universal_output(observation):
    steps = observation["steps"]
    assert steps["brackets"] == 200
    assert len(steps["whole_second_dynamical_step_dates"]) == 27
    whole = set(steps["whole_second_dynamical_step_dates"])
    universal = [s for s in steps["steps"] if s["date"] in whole]
    assert all(0.99 < s["universal_step_seconds"] < 1.0 for s in universal)


def test_a_sixty_first_second_is_offered_on_every_found_day_and_refused_on_an_unlisted_one(observation):
    by_date = {d["date"]: d for d in observation["second_sixty"]}
    found = [d for d in by_date.values() if d["found_by_part_2"]]
    assert len(found) == 27 and all(d["second_60"]["accepted"] for d in found)
    assert by_date["2015-12-31"]["second_60"]["accepted"] is False


def test_the_override_is_seen_only_from_the_named_directory(observation):
    """⭐ The red control for part 5: the planted file must move the reading after its date."""
    cases = observation["override"]["cases"]
    named = {r["date"]: r["differs_from_no_file"] for r in cases["file_in_named_directory"]["rows"]}
    assert named["2020-06-30"] == {"dynamical": False, "universal": False}
    assert named["2020-07-01"] == {"dynamical": True, "universal": True}
    assert cases["file_in_named_directory"]["second_sixty_on_the_invented_day"]["accepted"] is True
    for case in ("file_in_working_directory_none_named", "file_in_working_directory_other_named"):
        assert not any(any(r["differs_from_no_file"].values()) for r in cases[case]["rows"]), case


def test_the_full_mode_adds_every_bit_pattern(tmp_path):
    full = _run(tmp_path, "--full")
    assert len(full["state"]["states"]["default_first_call"]["grid_bit_patterns"]) == 115
    assert len(full["steps"]["bit_patterns"]) == 200
