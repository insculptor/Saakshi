"""The half-day grid generator: what it imports, the instants it builds, and every control it keeps.

⭐ It reads through the modes generator's child and admission rule, by import, so its first tests are static and need
no library; the instant tests read a manifest written here. The rest run it end to end — from a commit of its own in a
scratch repository holding both generators, after the modes record it ties to is written there from the same
manifest — and then plant, one at a time, the defect each control exists to catch, each beside the record as written,
which passes.
"""

from __future__ import annotations

import ast
import copy
import hashlib
import importlib.util
import json
import os
import platform
import random
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "generators" / "nutation_obliquity_grid.py"
MODES = ROOT / "generators" / "nutation_obliquity_modes.py"
EPHE = ROOT / "cache" / "ephe"

#: The coverage the data profile manifest declares for its one dataset.
COVERAGE = 'declared_coverage = { start = "1849-12-26T00:00:00", end = "2150-01-22T00:00:00", scale = "TDB" }'
#: ⭐ A short interval for the end-to-end run: 185 lattice instants, J2000 among them, and two at the stride.
SHORT = 'declared_coverage = { start = "1999-11-01T00:00:00", end = "2000-02-01T00:00:00", scale = "TDB" }'

#: ⭐ Every row of the short record, every field, pinned so that nothing in it is compared with nothing. ⚠ Host-bound
#: (macOS arm64, CPython 3.12.11, the library 2.10.03 through its binding 2.10.3.2), as the modes record's pins.
READINGS_DIGEST = "f28b5672067083ab02d023b87c4e727f51a50e7d4288f88fcb5c11c0718453ee"


def _module():
    spec = importlib.util.spec_from_file_location("nutation_obliquity_grid", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _manifest(directory: Path, coverage: str = COVERAGE) -> Path:
    path = directory / "profile.v1.toml"
    path.write_text(f'[identity]\nname = "standard"\nversion = 1\n\n[[pinned.dataset]]\nlogical_id = "de440s"\n'
                    f'{coverage}\n', encoding="utf-8")
    return path


def _instants(m, manifest: Path) -> tuple[dict, list[dict], list[dict]]:
    interval = m.modes.read_interval(str(manifest))
    epochs = m.modes.build_epochs(interval)
    return interval, epochs, m.build_grid(interval, epochs)


# ---------------------------------------------------------------------------------------
# What it is made of — the modes generator's reading, by import
# ---------------------------------------------------------------------------------------


def test_it_imports_only_the_standard_library_the_binding_and_the_modes_generator():
    tree = ast.parse(SCRIPT.read_text(encoding="utf-8"))
    roots = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            roots.add(node.module.split(".")[0])
    foreign = sorted(r for r in roots if r not in sys.stdlib_module_names
                     and r not in ("swisseph", "nutation_obliquity_modes"))
    assert foreign == [], f"⛔ the generator imports only the standard library, the binding and the modes one: {foreign}"
    assert "nutation_obliquity_modes" in roots


def test_it_reads_through_the_modes_generator_and_copies_none_of_it():
    """⛔ By import, never by copy: none of the modes generator's reading is defined here, and what is used is that
    module's own object."""
    tree = ast.parse(SCRIPT.read_text(encoding="utf-8"))
    defined = {node.name for node in tree.body if isinstance(node, (ast.FunctionDef, ast.ClassDef))}
    defined |= {t.id for node in tree.body if isinstance(node, ast.Assign) for t in node.targets
                if isinstance(t, ast.Name)}
    theirs = {"_child", "Children", "admit", "declared_calls", "spec_for", "child_environment", "read_interval",
              "build_epochs", "verify_data_directory", "verify_empty_directory", "EPHE_PINS", "CONFIGURATIONS",
              "EPHEMERIS_NAMES", "row_from", "values_from", "julian_day", "civil"}
    assert defined & theirs == set()
    m = _module()
    assert Path(m.modes.__file__).resolve() == MODES.resolve()
    assert m.Refusal is m.modes.Refusal and m.bits is m.modes.bits
    # ⭐ the statement of freshness is the modes generator's, character for character
    strings = [node.value for node in ast.walk(ast.parse(MODES.read_text(encoding="utf-8")))
               if isinstance(node, ast.Constant) and isinstance(node.value, str)]
    assert m.FRESHNESS in strings


def test_it_writes_no_bytecode_beside_the_modes_generator():
    """⛔ An untracked bytecode file is a dirty tree; the generator turns bytecode writing off before its import."""
    tree = ast.parse(SCRIPT.read_text(encoding="utf-8"))
    order = [node for node in tree.body if isinstance(node, (ast.Assign, ast.Import))]
    names = [ast.unparse(node) for node in order]
    assert names.index("sys.dont_write_bytecode = True") < names.index("import nutation_obliquity_modes as modes")


# ---------------------------------------------------------------------------------------
# The instants — a lattice across the manifest's interval, and the modes record's seven
# ---------------------------------------------------------------------------------------


def test_the_grid_over_the_declared_interval(tmp_path):
    """⭐ Every half day from 1849-12-26 to 2150-01-22, exactly, and the modes record's seven instants: three on the
    lattice, four outside it."""
    m = _module()
    interval, epochs, grid = _instants(m, _manifest(tmp_path))
    lattice = [i for i in grid if "lattice_index" in i]
    assert (len(grid), len(lattice)) == (219_205, 219_201)
    assert all(i["jd"] == 2396752.5 + i["lattice_index"] * 0.5 for i in lattice)
    assert (lattice[0]["jd"], lattice[-1]["jd"]) == (interval["start"], interval["end"]) == (2396752.5, 2506352.5)
    named = {i["epoch_id"]: i for i in grid if "epoch_id" in i}
    assert sorted(named) == sorted(e["epoch_id"] for e in epochs) and len(named) == 7
    assert {k: v.get("lattice_index") for k, v in named.items() if v["in_supported_interval"]} == {
        "supported_start_1849_12_26": 0, "j2000": 109_585, "supported_end_2150_01_22": 219_200}
    assert sorted(k for k, v in named.items() if "lattice_index" not in v) == [
        "edge_search_1000_01_01", "edge_search_3000_01_01", "outside_1500", "outside_3000"]
    assert [i["jd"] for i in grid] == sorted(i["jd"] for i in grid)
    subset = m.build_subset(grid)
    assert len(subset) == 2_193 + 1 + 4
    assert len(grid) + 10 * len(subset) == 241_185


def test_the_subset_is_the_stride_and_the_modes_records_instants(tmp_path):
    m = _module()
    _, _, grid = _instants(m, _manifest(tmp_path))
    rule = [i for i in grid if "epoch_id" in i or i["lattice_index"] % 100 == 0]
    assert m.build_subset(grid) == rule and m.SUBSET_STRIDE == 100


def test_an_interval_whose_end_is_not_on_the_lattice_is_refused(tmp_path):
    """⛔ The lattice ends on the interval's end — beside the declared interval, which it does."""
    m = _module()
    assert _instants(m, _manifest(tmp_path))[2]
    (tmp_path / "off").mkdir()
    off = 'declared_coverage = { start = "1849-12-26T00:00:00", end = "2150-01-22T06:00:00", scale = "TDB" }'
    with pytest.raises(m.Refusal, match="the lattice must end on it"):
        _instants(m, _manifest(tmp_path / "off", off))


def test_an_instant_of_the_modes_record_inside_the_interval_off_the_lattice_is_refused(tmp_path):
    """⛔ A lattice from 06:00 does not hold J2000 (noon); the modes record's instant is refused, not added."""
    m = _module()
    shifted = 'declared_coverage = { start = "1849-12-26T06:00:00", end = "2150-01-22T06:00:00", scale = "TDB" }'
    with pytest.raises(m.Refusal, match="j2000 is inside the interval and not on the lattice"):
        _instants(m, _manifest(tmp_path, shifted))


def test_two_lattice_instants_at_one_julian_day_are_refused(tmp_path, monkeypatch):
    m = _module()
    interval, epochs, _ = _instants(m, _manifest(tmp_path, SHORT))
    monkeypatch.setattr(m, "bits", lambda value: "0" * 16)
    with pytest.raises(m.Refusal, match="two lattice instants share a Julian day"):
        m.build_grid(interval, epochs)


def test_the_step_and_its_reason():
    m = _module()
    assert m.STEP_DAYS == 0.5 and m.STEP_REASON.startswith("half a day")
    assert m.STEP_SOURCE["document"] in {d["document"] for d in m.DOCUMENTS}
    assert "periods greater than 2 days" in m.STEP_SOURCE["quote"]


def test_the_documented_models_are_quotes_with_their_sources():
    """⭐ Each quote names a document retrieved, by address, day and digest — documentation only."""
    m = _module()
    documents = {d["document"]: d for d in m.DOCUMENTS}
    for d in m.DOCUMENTS:
        assert d["url"].startswith("https://") and d["retrieved"] == "2026-11-03"
        assert len(d["sha256"]) == 64 and int(d["sha256"], 16) >= 0
    assert set(m.DOCUMENTED_MODELS) == {"precession", "obliquity", "nutation"}
    for quantity, quotes in m.DOCUMENTED_MODELS.items():
        assert quotes, quantity
        for q in quotes:
            assert q["document"] in documents and q["document"] != "iers_conventions_2010_chapter_5"
            assert q["quote"] and q["where"]
    assert m.DOCUMENTATION_SEARCH["hits"] == 0


def test_every_field_a_row_carries_is_in_the_row_schema():
    m = _module()
    described = set(m.ROW_SCHEMA)
    assert described == {"part", "configuration", "ephemeris_requested", "path_state", "nutation", "epoch_id",
                         "lattice_index", "jd", "in_supported_interval", "requested", "returned", "values"}


# ---------------------------------------------------------------------------------------
# Reading several children at once — each still one fresh reading
# ---------------------------------------------------------------------------------------


def _reply(nonce: str, readings: int = 1, value: float = 0.0) -> str:
    return json.dumps({"nonce": nonce, "fresh_interpreter": True, "calls": [],
                       "readings": [{"values_bits": [value]}] * readings})


def test_readings_come_back_in_the_specs_order_not_the_order_children_finished(tmp_path, monkeypatch):
    m = _module()

    def run(args, **keywords):
        spec = json.loads(args[-1])[0]
        time.sleep(random.random() / 200)
        return subprocess.CompletedProcess(args, 0, stdout=_reply(os.urandom(16).hex(), value=spec["jd_bits"]),
                                           stderr="")

    monkeypatch.setattr(m.modes.subprocess, "run", run)
    readers = m.Readers(str(tmp_path), 6)
    specs = [{"jd_bits": i} for i in range(60)]
    assert [r["values_bits"][0] for r in readers.take(specs)] == list(range(60))
    assert readers.count() == 60 and len(readers.pools) > 1


def test_two_readings_carrying_one_childs_nonce_are_refused_across_threads(tmp_path, monkeypatch):
    """⛔ Each thread's children see only their own nonces, so the nonces across them are held distinct afterwards —
    beside distinct nonces, counted."""
    m = _module()
    lock = threading.Lock()
    nonces = iter(["a" * 32, "a" * 32])

    def run(args, **keywords):
        time.sleep(0.01)
        with lock:
            nonce = next(nonces)
        return subprocess.CompletedProcess(args, 0, stdout=_reply(nonce), stderr="")

    monkeypatch.setattr(m.modes.subprocess, "run", run)
    readers = m.Readers(str(tmp_path), 2)
    barrier = threading.Barrier(2, timeout=30)
    one = readers._one
    monkeypatch.setattr(readers, "_one", lambda spec: (barrier.wait(), one(spec))[1])
    with pytest.raises(m.Refusal, match="two readings came back from one child"):
        list(readers.take([{}, {}]))
        readers.count()
    nonces = iter(["b" * 32, "c" * 32])
    readers = m.Readers(str(tmp_path), 2)
    assert len(list(readers.take([{}, {}]))) == 2 and readers.count() == 2


def test_a_child_that_took_two_readings_is_refused_through_the_modes_rule(tmp_path, monkeypatch):
    m = _module()
    monkeypatch.setattr(m.modes.subprocess, "run",
                        lambda args, **k: subprocess.CompletedProcess(args, 0, stdout=_reply(os.urandom(16).hex(), 2),
                                                                      stderr=""))
    with pytest.raises(m.Refusal, match="took 2 readings"):
        list(m.Readers(str(tmp_path), 1).take([{}]))


def test_no_children_at_once_is_refused(tmp_path):
    m = _module()
    assert m.Readers(str(tmp_path), 1).workers == 1
    with pytest.raises(m.Refusal, match="0 children at once"):
        m.Readers(str(tmp_path), 0)


# ---------------------------------------------------------------------------------------
# Running it — from a commit of its own, beside the modes record it ties to
# ---------------------------------------------------------------------------------------


def _git(repo: Path, *args: str) -> str:
    environment = dict(os.environ, GIT_AUTHOR_NAME="test", GIT_AUTHOR_EMAIL="test@example.invalid",
                       GIT_COMMITTER_NAME="test", GIT_COMMITTER_EMAIL="test@example.invalid")
    return subprocess.run(["git", "-c", "commit.gpgsign=false", *args], cwd=repo, env=environment,
                          capture_output=True, text=True, check=True).stdout


def _committed_copy(base: Path) -> tuple[Path, str]:
    """A scratch repository holding both generators at their own paths, committed — and ⚠ no ignore file."""
    repo = base / "repo"
    (repo / "generators").mkdir(parents=True)
    for script in (SCRIPT, MODES):
        shutil.copy2(script, repo / "generators" / script.name)
    _git(repo, "init", "-q")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "generators")
    return repo, _git(repo, "rev-parse", "HEAD").strip()


def _invoke(repo: Path, *args: str, script: str = SCRIPT.name) -> subprocess.CompletedProcess:
    environment = dict(os.environ, SE_MARKER_FOR_TEST="1")
    return subprocess.run([sys.executable, str(repo / "generators" / script), *args], cwd=repo, env=environment,
                          capture_output=True, text=True, timeout=900, check=False)


def _grid_args(ephe: Path, empty: Path, profile: Path, record: Path, out: Path, workers: int = 4) -> list[str]:
    return ["--ephe-path", str(ephe), "--empty-dir", str(empty), "--profile", str(profile), "--modes-record",
            str(record), "--out", str(out), "--workers", str(workers)]


def _pinned_files_or_skip() -> None:
    if not all((EPHE / pin).is_file() for pin in ("seas_18.se1", "semo_18.se1", "sepl_18.se1")):
        pytest.skip("the pinned data files are not on this machine (cache/ephe)")


def test_a_dirty_tree_a_moved_script_or_an_existing_output_is_refused_before_anything_is_read(tmp_path):
    """⛔ Each refused before a reading — beside the record written at its own path (`emission`)."""
    empty = tmp_path / "empty"
    empty.mkdir()
    out = tmp_path / "out.jsonl"
    nowhere = (tmp_path / "nowhere", empty, tmp_path / "nowhere.toml", tmp_path / "nowhere.jsonl", out)
    dirty, _ = _committed_copy(tmp_path / "dirty")
    (dirty / "untracked.txt").write_text("x", encoding="ascii")
    proc = _invoke(dirty, *_grid_args(*nowhere))
    assert proc.returncode == 2 and "dirty" in proc.stderr and not out.exists()
    moved, _ = _committed_copy(tmp_path / "moved")
    (moved / "generators" / SCRIPT.name).rename(moved / "generators" / "elsewhere.py")
    _git(moved, "add", "-A")
    _git(moved, "commit", "-q", "-m", "moved")
    proc = _invoke(moved, *_grid_args(*nowhere), script="elsewhere.py")
    assert proc.returncode == 2 and "runs generators/elsewhere.py, not generators/nutation_obliquity_grid.py" in proc.stderr
    repo, _ = _committed_copy(tmp_path / "existing")
    out.write_text("held\n", encoding="ascii")
    proc = _invoke(repo, *_grid_args(*nowhere))
    assert proc.returncode == 2 and "exists; each emission goes to a new path" in proc.stderr
    assert out.read_text(encoding="ascii") == "held\n"


@pytest.mark.parametrize("defect", ["extra_file", "empty_not_empty"])
def test_a_directory_that_is_not_what_it_claims_is_refused(tmp_path, defect):
    """⛔ The modes generator's directory checks, run here before the first reading."""
    _pinned_files_or_skip()
    repo, _ = _committed_copy(tmp_path)
    data, empty = tmp_path / "data", tmp_path / "empty"
    data.mkdir()
    empty.mkdir()
    for pin in ("seas_18.se1", "semo_18.se1", "sepl_18.se1"):
        shutil.copy2(EPHE / pin, data / pin)
    if defect == "extra_file":
        (data / "seleapsec.txt").write_text("20200630\n", encoding="ascii")
    else:
        (empty / "a.se1").write_bytes(b"")
    out = tmp_path / "out.jsonl"
    proc = _invoke(repo, *_grid_args(data, empty, _manifest(tmp_path, SHORT), tmp_path / "none.jsonl", out))
    assert proc.returncode == 2 and not out.exists()
    assert {"extra_file": "not exactly the pinned set", "empty_not_empty": "the empty directory holds"}[
        defect] in proc.stderr


def test_a_working_directory_left_holding_anything_is_refused(tmp_path, monkeypatch):
    m = _module()

    class Past(Exception):
        pass

    def raise_past(*a, **k):
        raise Past

    monkeypatch.setattr(m, "source_commit", lambda: "0" * 40)
    monkeypatch.setattr(m.modes, "verify_data_directory", lambda path: None)
    monkeypatch.setattr(m, "check", raise_past)
    empty = tmp_path / "empty"
    empty.mkdir()
    monkeypatch.setattr(m, "measure", lambda *a: ([], {}))
    with pytest.raises(Past):
        m.generate("data", str(empty), "profile", "modes", str(tmp_path / "a.jsonl"))
    monkeypatch.setattr(m, "measure", lambda ephe, e, profile, record, work, workers:
                        (Path(work, "stray").write_text("x"), ([], {}))[1])
    with pytest.raises(m.Refusal, match="the empty directory holds \\['stray'\\]"):
        m.generate("data", str(empty), "profile", "modes", str(tmp_path / "b.jsonl"))


def test_a_directory_that_changed_during_the_run_is_refused(tmp_path, monkeypatch):
    """⛔ Both directories are checked again after the last reading: a file arriving in either during the run is
    refused — beside a run that left both as they were, which goes on past the checks."""
    _pinned_files_or_skip()
    m = _module()

    class Past(Exception):
        pass

    def raise_past(*a, **k):
        raise Past

    data, empty = tmp_path / "data", tmp_path / "empty"
    data.mkdir()
    empty.mkdir()
    for pin in ("seas_18.se1", "semo_18.se1", "sepl_18.se1"):
        shutil.copy2(EPHE / pin, data / pin)
    monkeypatch.setattr(m, "source_commit", lambda: "0" * 40)
    monkeypatch.setattr(m, "check", raise_past)
    monkeypatch.setattr(m, "measure", lambda *a: ([], {}))
    with pytest.raises(Past):
        m.generate(str(data), str(empty), "profile", "modes", str(tmp_path / "a.jsonl"))
    for directory, name, match in ((data, "late.txt", "not exactly the pinned set"),
                                   (empty, "late.se1", "the empty directory holds \\['late.se1'\\]")):
        monkeypatch.setattr(m, "measure", lambda *a, d=directory, n=name: ((d / n).write_text("x"), ([], {}))[1])
        with pytest.raises(m.Refusal, match=match):
            m.generate(str(data), str(empty), "profile", "modes", str(tmp_path / f"{name}.jsonl"))
        (directory / name).unlink()


@pytest.fixture(scope="module")
def emission(tmp_path_factory) -> dict:
    pytest.importorskip(
        "swisseph", reason="the generator calls the ephemeris library; it cannot run where it is not installed")
    _pinned_files_or_skip()
    base = tmp_path_factory.mktemp("grid-emission")
    repo, commit = _committed_copy(base)
    empty = base / "empty"
    empty.mkdir()
    manifest = _manifest(base, SHORT)
    record = base / "modes.jsonl"
    proc = _invoke(repo, "--ephe-path", str(EPHE), "--empty-dir", str(empty), "--profile", str(manifest), "--out",
                   str(record), script=MODES.name)
    assert proc.returncode == 0, proc.stderr[-800:]
    out = base / "grid.jsonl"
    proc = _invoke(repo, *_grid_args(EPHE, empty, manifest, record, out))
    assert proc.returncode == 0, proc.stderr[-800:]
    assert f"commit {commit}" in proc.stderr
    assert _git(repo, "status", "--porcelain", "--untracked-files=all") == ""
    text = out.read_text(encoding="ascii")
    lines = [json.loads(line) for line in text.splitlines()]
    return {"commit": commit, "header": lines[0], "rows": lines[1:], "text": text, "manifest": manifest,
            "record": record, "repo": repo, "empty": empty, "base": base}


def test_the_record_is_an_r3_provenance_record_naming_its_commit_and_versions(emission):
    import swisseph as swe
    from importlib.metadata import version

    header = emission["header"]
    assert (header["record"], header["fixture_kind"], header["reference"]) == ("header", "provenance_record", "R3")
    assert header["generator"] == {"repo": "github.com/insculptor/Saakshi",
                                   "script": "generators/nutation_obliquity_grid.py", "commit": emission["commit"]}
    oracle = header["oracle"]
    assert oracle["library_version"] == swe.version
    assert oracle["called_via"] == {"binding": "pyswisseph", "version": version("pyswisseph")}
    assert oracle["session"]["removed_environment_variables"] == ["SE_MARKER_FOR_TEST"]
    assert oracle["session"]["children_at_once"] == 4
    assert oracle["session"]["isolation"] == _module().FRESHNESS
    assert oracle["host"] == {"python": sys.version.split()[0], "platform": platform.platform(),
                              "machine": platform.machine()}
    assert header["summary"]["readings"] == header["summary"]["children"] == len(emission["rows"]) == 269
    assert header["summary"]["rows_by_part"] == {"grid": 189, "invariance": 80}
    assert {r["part"] for r in emission["rows"]} == {"grid", "invariance"}


def test_its_freshness_is_the_modes_records_own_literal(emission):
    """⭐ Character for character the modes record's statement — the reading is that record's."""
    modes = json.loads(Path(emission["record"]).read_text(encoding="ascii").splitlines()[0])
    assert emission["header"]["oracle"]["session"]["isolation"] == modes["oracle"]["session"]["isolation"]


def test_the_record_keeps_this_repositorys_fixture_contract(emission):
    sys.path.insert(0, str(ROOT / "src"))
    from saakshi.fixture import Generator, Header, _scan_keys, validate_header

    header = dict(emission["header"])
    built = Header(
        fixture_kind=header["fixture_kind"], reference=header["reference"],
        generator=Generator(**header["generator"]), generated=header["generated"], oracle=header["oracle"],
        attests=header["attests"], authority=header["authority"], record_date=header["record_date"],
        title=header["title"], notes=header["notes"], summary=header["summary"], row_schema=header["row_schema"],
    )
    validate_header(built, where="record", reserved=("saakshi",))
    assert built.as_json() == header
    for i, row in enumerate(emission["rows"]):
        _scan_keys(row, where="record", path=f"row[{i}]", reserved=("saakshi",))


def test_its_data_file_pins_are_this_repositorys(emission):
    sys.path.insert(0, str(ROOT / "src"))
    from saakshi.swiss import EPHE_PINS

    pins = {p.dataset: {"dataset": p.dataset, "profile": p.profile, "size_bytes": p.size_bytes,
                        "sha256": p.sha256, "publisher": p.publisher, "pinned_on": p.pinned_on}
            for p in EPHE_PINS.values()}
    assert emission["header"]["oracle"]["data_files"]["files"] == [pins[n] for n in sorted(pins)]


def test_every_row_of_the_record_is_pinned(emission):
    canonical = "".join(json.dumps(r, sort_keys=True, ensure_ascii=True) + "\n" for r in emission["rows"])
    assert hashlib.sha256(canonical.encode()).hexdigest() == READINGS_DIGEST


def test_what_the_record_measured(emission):
    """⭐ The findings, as measured on this host — so a reading that moves turns this red, and says which."""
    summary = emission["header"]["summary"]
    assert summary["returned_word"] == {"readings": 269, "returned_exactly_the_requested_word": 269}
    invariance = summary["invariance"]
    assert invariance["subset"]["instants"] == 8 and invariance["subset"]["readings"] == 80
    assert invariance["instants_with_one_set_of_six_values_across_the_five_configurations"] == {
        "default": {"instants": 8, "of": 8}, "nonut": {"instants": 8, "of": 8}}
    assert invariance["grid_rows_bit_identical_to_their_subset_twin"] == {"rows": 8, "of": 8}
    assert summary["tie"]["readings_tied"] == {"grid": 7, "invariance": 70}
    assert summary["tie"]["modes_record"]["sha256"] == hashlib.sha256(Path(emission["record"]).read_bytes()).hexdigest()
    assert summary["nonut"]["pairs"] == 40
    assert summary["nonut"]["pairs_bit_identical_at_position"] == [0, 40, 0, 0, 40, 40]
    grid = summary["grid"]
    assert (grid["instants"], grid["lattice"]["instants"], grid["requested"]) == (189, 185, 2)
    assert grid["the_modes_records_instants"] == {
        "on_the_lattice": ["supported_start_1999_11_01", "j2000", "supported_end_2000_02_01"],
        "outside_the_interval": ["edge_search_1000_01_01", "outside_1500", "edge_search_3000_01_01", "outside_3000"]}
    assert summary["binding"]["callables_whose_name_names_a_model"] == [] and summary["binding"]["callables"] == 149
    assert {"name": "MOD_NUT_DEFAULT", "value": 4} in summary["binding"]["exported_constants_named_for_models"]
    for part, counted in summary["read_back"].items():
        rows = [r for r in emission["rows"] if (r["part"] == "grid" and part == "grid")
                or (r["part"] == "invariance" and part == f"invariance_{r['configuration']}")]
        assert sum(t["readings"] for t in counted["tidal_constant"]) == len(rows) > 0
        assert sum(f["readings"] for f in counted["open_files"]) == len(rows)
    assert sum(1 for part in summary["read_back"] if part.startswith("invariance_")) == 5


def _context(m, emission) -> dict:
    import swisseph as swe
    from importlib.metadata import version

    interval, epochs, grid = _instants(m, emission["manifest"])
    summary = emission["header"]["summary"]
    return {"interval": interval, "epochs": epochs, "grid": grid, "subset": m.build_subset(grid),
            "flag": {"moshier": swe.FLG_MOSEPH, "swiss_file": swe.FLG_SWIEPH, "jpl_file": swe.FLG_JPLEPH},
            "nonut": swe.FLG_NONUT, "subject": swe.ECL_NUT, "children": summary["children"],
            "tied": m.read_modes_record(str(emission["record"]), interval, epochs, swe.version, version("pyswisseph")),
            "read_back": summary["read_back"], "binding": summary["binding"], "workers": 4}


def test_the_controls_pass_on_the_record_as_written(emission):
    m = _module()
    summary = m.check(copy.deepcopy(emission["rows"]), _context(m, emission))
    assert summary == emission["header"]["summary"]
    assert m.notes(summary) == emission["header"]["notes"]


def test_the_notes_say_what_the_summary_says(emission):
    m = _module()
    summary = copy.deepcopy(emission["header"]["summary"])
    assert "269 of 269 readings" in m.notes(summary)[2]
    summary["returned_word"]["returned_exactly_the_requested_word"] = 268
    summary["invariance"]["grid_rows_bit_identical_to_their_subset_twin"]["rows"] = 7
    written = m.notes(summary)
    assert "268 of 269 readings" in written[2] and "at 7 of 8" in written[3]


# ---------------------------------------------------------------------------------------
# Each control, planted red beside the record as written
# ---------------------------------------------------------------------------------------


def _rows(emission) -> list[dict]:
    return copy.deepcopy(emission["rows"])


def _set_value(row: dict, position: int, value: float) -> None:
    row["values"][position] = value
    row["values_bits"][position] = _module().bits(value)


def _refused(emission, rows, match: str, **context) -> None:
    m = _module()
    built = _context(m, emission)
    built.update(context)
    if "children" not in context:
        built["children"] = len(rows)
    with pytest.raises(m.Refusal, match=match):
        m.check(rows, built)


def test_stop_a_returned_word_other_than_the_request(emission):
    rows = _rows(emission)
    next(r for r in rows if r["part"] == "grid" and r.get("lattice_index") == 50)["returned"] = 1
    _refused(emission, rows, "STOP: a grid reading at JD .* requested word 2 and returned 1")


def test_stop_values_that_move_across_the_configurations(emission):
    rows = _rows(emission)
    row = next(r for r in rows if r["part"] == "invariance" and r.get("lattice_index") == 100
               and r["configuration"] == "moshier_dir_empty" and r["nutation"] == "nonut")
    _set_value(row, 3, row["values"][3] + 1e-12)
    _refused(emission, rows, "STOP: at JD .* under the nonut word the values moved across the configurations")


def test_a_grid_reading_and_its_subset_twin_that_differ_are_refused(emission):
    rows = _rows(emission)
    row = next(r for r in rows if r["part"] == "grid" and r.get("lattice_index") == 100)
    _set_value(row, 0, row["values"][0] + 1e-12)
    _refused(emission, rows, "the grid's reading and its subset twin")


def test_stop_a_reading_at_the_modes_records_instant_that_is_not_its(emission):
    """⛔ The modes record says otherwise at one of its instants — every reading here unchanged."""
    m = _module()
    context = _context(m, emission)
    tie = context["tied"]["tie"]
    key = next(k for k in tie if k[:2] == ("jpl_requested_no_jpl_file", "nonut"))
    tie[key] = dict(tie[key], values_bits=list(tie[key]["values_bits"][:5]) + ["3ff0000000000000"])
    with pytest.raises(m.Refusal, match="STOP: the invariance reading at .* is not the modes record's"):
        m.check(_rows(emission), context)
    context = _context(m, emission)
    del context["tied"]["tie"][next(iter(context["tied"]["tie"]))]
    with pytest.raises(m.Refusal, match="STOP: the .* reading at .* is not the modes record's"):
        m.check(_rows(emission), context)


def test_a_modes_record_with_a_reading_no_row_ties_to_is_refused(emission):
    m = _module()
    context = _context(m, emission)
    tie = context["tied"]["tie"]
    tie[("swiss_file_present", "default", m.bits(1.5))] = next(iter(tie.values()))
    with pytest.raises(m.Refusal, match="tied .* of the modes record's 71 readings"):
        m.check(_rows(emission), context)


#: ⭐ One clause of the nutation-off relation broken at a time, every other clause left holding: the word whose rows
#: move, and each position's new value — `+` a nudge, `1` a copy of position 1.
NONUT_PLANTS = {
    "nonut_position_1_not_its_default_twins": ("nonut", {0: "+", 1: "+"}),
    "nonut_position_0_not_position_1": ("nonut", {0: "+"}),
    "nonut_position_2_not_zero": ("nonut", {2: 1e-9}),
    "nonut_position_3_not_zero": ("nonut", {3: 1e-9}),
    "default_position_0_not_moved_by_nonut": ("default", {0: "1"}),
    "default_position_2_not_moved_by_nonut": ("default", {2: 0.0}),
    "default_position_3_not_moved_by_nonut": ("default", {3: 0.0}),
}


@pytest.mark.parametrize("plant", sorted(NONUT_PLANTS))
def test_stop_the_nutation_off_relation(emission, plant):
    """⛔ Each clause of the relation, planted at a subset instant under every configuration (and the grid's twin), so
    nothing but that clause moves."""
    m = _module()
    word, changes = NONUT_PLANTS[plant]
    rows = _rows(emission)
    for row in rows:
        if row.get("lattice_index") == 100 and (row["part"] == "invariance" and row["nutation"] == word
                                                or row["part"] == "grid" and word == "default"):
            for position, value in changes.items():
                new = {"+": row["values"][position] + 1e-9, "1": row["values"][1]}.get(value, value)
                _set_value(row, position, new)
    _refused(emission, rows, "STOP: at JD .* the nutation-off relation the modes record measured does not hold")
    assert m.ZERO_BITS == m.bits(0.0)


def test_a_reading_count_other_than_the_childrens_is_refused(emission):
    _refused(emission, _rows(emission), "269 readings from 268 children", children=268)


NAME_PLANTS = {
    "a_configuration_name_not_its_path": (lambda r: r.get("configuration") == "swiss_file_present",
                                          {"configuration": "swiss_file_dir_empty"}, "is not that configuration"),
    "an_ephemeris_label_not_its_word": (lambda r: r.get("configuration") == "swiss_file_present",
                                        {"requested": 4}, "labelled swiss_file .* requested 4"),
    "a_nutation_label_not_its_word": (lambda r: r.get("nutation") == "default", {"nutation": "nonut"},
                                      "labelled .* nonut requested"),
    "a_grid_word_not_its_configurations": (lambda r: r["part"] == "grid", {"requested": 66},
                                           "a grid row labelled swiss_file default requested 66"),
    "a_grid_row_naming_a_configuration": (lambda r: r["part"] == "grid", {"configuration": "swiss_file_present"},
                                          "a grid row names a configuration"),
    "a_row_in_no_part": (lambda r: r["part"] == "grid", {"part": "elsewhere"}, "a row in part 'elsewhere'"),
    "a_lattice_index_not_its_instant": (lambda r: r.get("lattice_index") == 7, {"lattice_index": 8},
                                        "is not the instant its index or epoch names"),
    "a_lattice_index_off_the_lattice": (lambda r: r.get("lattice_index") == 7, {"lattice_index": 185},
                                        "is not the instant its index or epoch names"),
    "a_lattice_index_not_its_epochs": (lambda r: r.get("epoch_id") == "j2000", {"lattice_index": 124},
                                       "is not the instant its index or epoch names"),
    "an_epoch_name_not_its_instant": (lambda r: r.get("epoch_id") == "j2000", {"epoch_id": "outside_1500"},
                                      "is not the instant its index or epoch names"),
    "an_in_interval_flag_not_its_instant": (lambda r: r.get("epoch_id") == "outside_1500",
                                            {"in_supported_interval": True}, "is not the instant"),
    "an_instant_of_the_modes_record_unnamed": (lambda r: r.get("epoch_id") == "j2000" and r["part"] == "grid",
                                               {"epoch_id": None}, "the grid part holds 189 rows"),
}


@pytest.mark.parametrize("plant", sorted(NAME_PLANTS))
def test_a_row_whose_name_is_not_what_it_names_is_refused(emission, plant):
    select, change, match = NAME_PLANTS[plant]
    rows = _rows(emission)
    row = next(r for r in rows if select(r))
    row.update(change)
    if change.get("epoch_id", 0) is None:
        del row["epoch_id"]
    _refused(emission, rows, match)


@pytest.mark.parametrize("defect", ["five_values", "a_pattern_not_its_value"])
def test_six_values_and_their_patterns(emission, defect):
    rows = _rows(emission)
    row = rows[3]
    if defect == "five_values":
        row["values"], row["values_bits"] = row["values"][:5], row["values_bits"][:5]
    else:
        row["values"][0] += 1e-9
    _refused(emission, rows, "values are not six values and their patterns")


@pytest.mark.parametrize("part", ["grid", "invariance"])
def test_a_part_missing_a_reading_is_refused(emission, part):
    rows = _rows(emission)
    rows.remove(next(r for r in rows if r["part"] == part and r.get("lattice_index") == 100))
    _refused(emission, rows, f"the {part} part holds")


def test_a_modes_record_that_is_not_the_one_to_tie_to_is_refused(emission, tmp_path):
    """⛔ Another script's, another manifest's, another library's, other instants, a row named for another instant,
    a reading missing — each refused before any reading, beside the record as written, which is read."""
    import swisseph as swe
    from importlib.metadata import version

    m = _module()
    interval, epochs, _ = _instants(m, emission["manifest"])
    lines = Path(emission["record"]).read_text(encoding="ascii").splitlines()
    assert len(m.read_modes_record(str(emission["record"]), interval, epochs, swe.version,
                                   version("pyswisseph"))["tie"]) == 70

    def planted(header_change=None, rows_change=None) -> str:
        header, rows = json.loads(lines[0]), [json.loads(line) for line in lines[1:]]
        if header_change:
            header_change(header)
        if rows_change:
            rows = rows_change(rows)
        path = tmp_path / f"planted-{os.urandom(4).hex()}.jsonl"
        path.write_text("\n".join(json.dumps(x) for x in [header, *rows]) + "\n", encoding="ascii")
        return str(path)

    def first_calc(rows):
        return next(r for r in rows if r.get("part") == "mode_invariance")

    cases = (
        (planted(lambda h: h["generator"].update(script="generators/elsewhere.py")), "was written by"),
        (planted(lambda h: h["summary"]["epochs"].update(manifest_sha256="0" * 64)), "another manifest"),
        (planted(lambda h: h["oracle"].update(library_version="0.0")), "read library '0.0'"),
        (planted(lambda h: h["oracle"]["called_via"].update(version="0.0")), "through binding '0.0'"),
        (planted(lambda h: h["summary"]["epochs"].update(ids=h["summary"]["epochs"]["ids"][::-1])),
         "instants are not these"),
        (planted(rows_change=lambda rows: [dict(r, jd_bits=m.bits(1.5)) if r is first_calc(rows) else r
                                           for r in rows]), "is not that instant"),
        (planted(rows_change=lambda rows: [r for r in rows if r is not first_calc(rows)]),
         "holds 69 calc readings at its instants; this record ties to 70"),
    )
    for path, match in cases:
        with pytest.raises(m.Refusal, match=match):
            m.read_modes_record(path, interval, epochs, swe.version, version("pyswisseph"))


def test_a_modes_record_from_another_manifest_is_refused_before_any_reading(emission, tmp_path):
    other = _manifest(tmp_path, 'declared_coverage = { start = "1999-11-02T00:00:00", end = "2000-02-01T00:00:00", '
                                'scale = "TDB" }')
    out = tmp_path / "out.jsonl"
    proc = _invoke(emission["repo"], *_grid_args(EPHE, emission["empty"], other, emission["record"], out))
    assert proc.returncode == 2 and "read its instants from another manifest" in proc.stderr and not out.exists()


def test_every_reading_is_admitted_by_the_modes_rule_on_the_row_as_written(emission, tmp_path):
    """⭐ A real child's calls against the written row and the header's constants: admitted as built, refused with
    another instant or another directory written after the call."""
    import swisseph as swe

    m = _module()
    paths = {"data_files": str(EPHE.resolve()), "empty_directory": str(emission["empty"].resolve())}
    instant = {"lattice_index": 123, "jd": 2451545.0, "in_supported_interval": True, "epoch_id": "j2000"}
    spec = m.modes.spec_for(path=paths["data_files"], flags=2, entry_point="calc", jd=2451545.0, body=swe.ECL_NUT)
    work = tmp_path / "work"
    work.mkdir()
    reading, = list(m.Readers(str(work), 1).take([spec]))
    row = {"part": "grid", **m.where(instant), "requested": 2, "returned": reading["returned"],
           "values": [m.unbits(b) for b in reading["values_bits"]], "values_bits": reading["values_bits"]}
    assert m.modes.admit(m.declared(row, swe.ECL_NUT), reading["calls"], paths)
    for change in ({"jd_bits": m.bits(2451545.5)}, {"requested": 66}, {"path_state": "empty_directory"}):
        with pytest.raises(m.Refusal, match="the row declares"):
            m.modes.admit(m.declared(dict(row, **change), swe.ECL_NUT), reading["calls"], paths)


def test_a_reading_the_modes_rule_refuses_refuses_the_record(emission, tmp_path, monkeypatch):
    """⛔ The rule is applied to every reading as it comes back, before any row is kept."""
    m = _module()

    def refuse(row, calls, paths):
        raise m.Refusal("planted: the row declares otherwise")

    monkeypatch.setattr(m.modes, "admit", refuse)
    work = tmp_path / "work"
    work.mkdir()
    with pytest.raises(m.Refusal, match="planted: the row declares otherwise"):
        m.measure(str(EPHE), str(emission["empty"]), str(emission["manifest"]), str(emission["record"]), str(work), 2)
