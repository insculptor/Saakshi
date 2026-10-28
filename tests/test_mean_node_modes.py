"""The mean-node generator: what it may import, where its epochs come from, and every control it must keep.

⛔ Like the deployment capture and the civil-time probe, the generator imports nothing but the standard
library and the binding, so the first tests are static and need no library. The interval tests read a
manifest written here. The rest run it end to end — from a commit of its own, in a scratch repository,
because it refuses a dirty tree — and then plant, one at a time, the defect each control exists to catch.
"""

from __future__ import annotations

import ast
import copy
import hashlib
import importlib.util
import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "generators" / "mean_node_modes.py"
EPHE = ROOT / "cache" / "ephe"

#: The coverage a data profile manifest declares for its one dataset, as the generator reads it.
COVERAGE = 'declared_coverage = { start = "1849-12-26T00:00:00", end = "2150-01-22T00:00:00", scale = "TDB" }'

#: ⭐ The scoping measurement of 2026-10-26 — two files, `se-mean-node.json` (sha256 391df9e4…) and
#: `flag-control.json` (46d9f5a1…) — rendered over the readings it shares with this generator, which are
#: all 973 of this generator's, digests to this. Pinned so that a reading that moves one bit, or an
#: epoch derived one step differently, turns this red. ⚠ On its 35 offset readings that measurement
#: wrote the configuration's whole word as `requested` while its call received only the ephemeris
#: bits (`flags & 7`); this generator records the word the call received, so its side is compared
#: after that mapping, and the mapping is stated wherever the comparison is.
REPRODUCTION_DIGEST = "581f9f4d307d578d057aac58db7bcc20cb122f85e7b5a817169ca7d9f856550b"

#: ⭐ Every row of the record, every field — the 56 values of the control rows the scoping measurement never
#: recorded (each body's longitude and the constant read back) among them — pinned so that nothing in the
#: record is compared with nothing. ⚠ Host-bound, as the pin above.
READINGS_DIGEST = "8cf244f33ab864e9bf6440b55d0526c66362803ebf0371b080e4286d547b3b51"


def _module():
    spec = importlib.util.spec_from_file_location("mean_node_modes", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _manifest(directory: Path, coverage: str = COVERAGE, datasets: int = 1) -> Path:
    body = '[identity]\nname = "standard"\nversion = 1\n'
    for i in range(datasets):
        body += f'\n[[pinned.dataset]]\nlogical_id = "de440s-{i}"\n{coverage}\n'
    path = directory / "profile.v1.toml"
    path.write_text(body, encoding="utf-8")
    return path


def test_it_imports_only_the_standard_library_and_the_binding():
    tree = ast.parse(SCRIPT.read_text(encoding="utf-8"))
    roots = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            roots.add(node.module.split(".")[0])
    foreign = sorted(r for r in roots if r not in sys.stdlib_module_names and r != "swisseph")
    assert foreign == [], f"⛔ the generator imports only the standard library and the binding: {foreign}"


# ---------------------------------------------------------------------------------------
# The epochs — derived from the manifest, never typed
# ---------------------------------------------------------------------------------------


def test_the_interval_is_the_manifests_and_converts_back(tmp_path):
    m = _module()
    interval = m.read_interval(str(_manifest(tmp_path)))
    assert (interval["start"], interval["end"]) == (2396752.5, 2506352.5)
    assert interval["declared_coverage"] == {"start": "1849-12-26T00:00:00", "end": "2150-01-22T00:00:00",
                                             "scale": "TDB"}
    epochs = m.build_epochs(interval)
    assert len(epochs) == 80 and sum(e["in_supported_interval"] for e in epochs) == 76
    assert [e["epoch_id"] for e in epochs if not e["in_supported_interval"]] == [
        "outside_1500", "outside_1700", "outside_2500", "outside_3000"]
    ends = {e["epoch_id"]: e["jd"] for e in epochs if e["epoch_id"].startswith("supported_")}
    assert ends == {"supported_start_1849_12_26": 2396752.5, "supported_end_2150_01_22": 2506352.5}


def test_the_epochs_follow_the_manifest_and_not_a_number_written_here(tmp_path, monkeypatch):
    """⭐ The red control for the interval: the Julian days a first scoping run typed for the same
    interval were those of 1850-01-01 and 2150-01-01. A manifest declaring those dates must give exactly
    those days at every place the interval reaches — both ends among the calc epochs and among the
    universal-time ones, every in-interval flag, and the window searched for crossings — so what decides
    them is the file, never a constant."""
    m = _module()
    planted = 'declared_coverage = { start = "1850-01-01T00:00:00", end = "2150-01-01T00:00:00", scale = "TDB" }'
    windows = []
    search = m.crossings
    monkeypatch.setattr(m, "crossings", lambda start, end: windows.append((start, end)) or search(start, end))
    for name, coverage, (start, end) in (("planted", planted, (2396758.5, 2506331.5)),
                                         ("declared", COVERAGE, (2396752.5, 2506352.5))):
        (tmp_path / name).mkdir()
        interval = m.read_interval(str(_manifest(tmp_path / name, coverage)))
        assert (interval["start"], interval["end"]) == (start, end)
        epochs = m.build_epochs(interval)
        assert sorted(e["jd"] for e in epochs if e["epoch_id"].startswith("supported_")) == [start, end]
        assert all(e["in_supported_interval"] == (start <= e["jd"] <= end) for e in epochs)
        assert windows[-1] == (start, end)
        universal = m.universal_epochs(interval)
        assert (universal[0]["jd"], universal[-1]["jd"]) == (start, end)
        ids = {e["epoch_id"] for e in epochs} | {e["epoch_id"] for e in universal}
        stamps = [s.split('"')[1][:10].replace("-", "_") for s in coverage.split("=")[2:4]]
        assert {f"supported_start_{stamps[0]}", f"supported_end_{stamps[1]}",
                f"ut_{stamps[0]}", f"ut_{stamps[1]}"} <= ids
    # ⭐ The grid's extent is the manifest's too: a coverage of 1855 … 2145 grids exactly those years.
    (tmp_path / "narrow").mkdir()
    narrow = 'declared_coverage = { start = "1855-01-01T00:00:00", end = "2145-01-01T00:00:00", scale = "TDB" }'
    grid = [e["epoch_id"] for e in m.build_epochs(m.read_interval(str(_manifest(tmp_path / "narrow", narrow))))
            if e["epoch_id"].startswith("grid_")]
    assert grid == [f"grid_{year}" for year in range(1855, 2146, 5)]


def test_a_julian_day_that_does_not_convert_back_is_refused(tmp_path, monkeypatch):
    """⛔ A conversion that drifted by a day would move every epoch with it; converting back catches it."""
    m = _module()
    convert = m.julian_day
    monkeypatch.setattr(m, "julian_day", lambda stamp: convert(stamp) + 1.0)
    with pytest.raises(m.Refusal, match="converts back"):
        m.read_interval(str(_manifest(tmp_path)))


def test_a_manifest_that_does_not_declare_one_coverage_is_refused(tmp_path):
    m = _module()
    with pytest.raises(m.Refusal, match="2 datasets"):
        m.read_interval(str(_manifest(tmp_path, datasets=2)))
    (tmp_path / "bare").mkdir()
    with pytest.raises(m.Refusal, match="no complete coverage"):
        m.read_interval(str(_manifest(tmp_path / "bare", 'declared_coverage = { start = "1849-12-26T00:00:00" }')))


def test_the_tables_names_say_what_they_define():
    """⛔ `check()` holds every row's configuration and condition name to the table that defines it, so each
    table is held to its own names' words: the ephemeris a name begins with, and every word that names a
    directory — present, files_present, inside or outside coverage, no_jpl_file, empty, empty_directory,
    no_path — to the path state it names."""
    m = _module()
    prefixes = {"moshier": "moshier_", "swiss_file": "swiss_file_", "jpl_file": "jpl_"}
    words = {"files_present": "data_files", "file_present": "data_files", "no_jpl_file": "data_files",
             "inside_coverage": "data_files", "outside_coverage": "data_files", "dir_empty": "empty_directory",
             "empty_directory": "empty_directory", "no_path_set": "no_path_set"}

    def state_of(name: str) -> str:
        named = {state for word, state in words.items() if word in name}
        assert len(named) == 1, f"{name}: its words name {sorted(named) or 'no'} directory state"
        return named.pop()

    for name, ephemeris, state in m.CONFIGURATIONS:
        assert name.startswith(prefixes[ephemeris]), name
        assert state_of(name) == state, name
    outside = {"swiss_file_outside_coverage_1500": "outside_1500", "swiss_file_outside_coverage_3000": "outside_3000"}
    for condition in m.CONDITIONS:
        name = condition["condition"]
        assert name.startswith(prefixes[condition["ephemeris"]]), name
        assert state_of(name) == condition["path_state"], name
        assert condition["epoch"] == outside.get(name, "j2000"), name
        assert condition["built_to_substitute"] == (
            name not in ("swiss_file_inside_coverage", "moshier_files_present")), name


def test_every_epoch_label_is_its_instant(tmp_path):
    """⛔ Epoch labels are the generator's own table, so each is held to its instant by a rule written here, not
    read from it: a grid year to 1 January of that year (within three days: the grid steps in Julian years
    of 365.25 days, which drift from the civil calendar), J2000 to its definition, an outside
    year to its formula, an interval end or a universal-time date to the civil date it spells, a crossing tag to
    its offset from the crossing — which the published F5 row puts at 0°/360°."""
    m = _module()
    interval = m.read_interval(str(_manifest(tmp_path)))
    epochs = m.build_epochs(interval)
    jd_of = {e["epoch_id"]: e["jd"] for e in epochs}
    offsets = {"at": 0.0, "minus_6h": -0.25, "plus_6h": 0.25}
    for epoch in epochs + m.universal_epochs(interval):
        label, jd = epoch["epoch_id"], epoch["jd"]
        head, _, rest = label.partition("_")
        if label in ("j2000", "ut_j2000"):
            assert jd == 2451545.0, label
        elif head == "grid":
            assert abs(jd - m.julian_day(f"{rest}-01-01T00:00:00")) < 3.0, label
        elif head == "outside":
            assert jd == m.year_epoch(int(rest)) and not epoch["in_supported_interval"], label
        elif head in ("supported", "ut"):
            assert m.civil(jd)[:10] == label.rsplit("_", 3)[-3:][0] + "-" + "-".join(label.rsplit("_", 2)[-2:]), label
        elif head.startswith("wrap"):
            assert jd - jd_of[f"{head}_at"] == offsets[rest], label
            if rest == "at":
                assert abs((m.f5_degrees(jd) + 180.0) % 360.0 - 180.0) < 1e-3, label
        else:
            raise AssertionError(f"an epoch label no rule reads: {label}")


# ---------------------------------------------------------------------------------------
# Running it — from a commit of its own
# ---------------------------------------------------------------------------------------


def _git(repo: Path, *args: str) -> str:
    environment = dict(os.environ, GIT_AUTHOR_NAME="test", GIT_AUTHOR_EMAIL="test@example.invalid",
                       GIT_COMMITTER_NAME="test", GIT_COMMITTER_EMAIL="test@example.invalid")
    return subprocess.run(["git", "-c", "commit.gpgsign=false", *args], cwd=repo, env=environment,
                          capture_output=True, text=True, check=True).stdout


def _committed_copy(base: Path, commit: bool = True) -> tuple[Path, str | None]:
    """A scratch repository holding the generator at its own path, committed."""
    repo = base / "repo"
    (repo / "generators").mkdir(parents=True)
    shutil.copy2(SCRIPT, repo / "generators" / SCRIPT.name)
    _git(repo, "init", "-q")
    if not commit:
        return repo, None
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "generator")
    return repo, _git(repo, "rev-parse", "HEAD").strip()


def _invoke(repo: Path, ephe: Path, empty: Path, profile: Path, out: Path) -> subprocess.CompletedProcess:
    environment = dict(os.environ, SE_MARKER_FOR_TEST="1")
    return subprocess.run(
        [sys.executable, str(repo / "generators" / SCRIPT.name), "--ephe-path", str(ephe),
         "--empty-dir", str(empty), "--profile", str(profile), "--out", str(out)],
        cwd=repo, env=environment, capture_output=True, text=True, timeout=900, check=False,
    )


def test_a_dirty_or_commitless_tree_is_refused_before_anything_is_read(tmp_path):
    """⛔ `generator.commit` would name a state that does not exist."""
    dirty, _ = _committed_copy(tmp_path / "dirty")
    (dirty / "untracked.txt").write_text("x", encoding="ascii")
    empty = tmp_path / "empty"
    empty.mkdir()
    out = tmp_path / "out.jsonl"
    proc = _invoke(dirty, tmp_path / "nowhere", empty, tmp_path / "nowhere.toml", out)
    assert proc.returncode == 2 and "dirty" in proc.stderr and not out.exists()
    bare, _ = _committed_copy(tmp_path / "bare", commit=False)
    proc = _invoke(bare, tmp_path / "nowhere", empty, tmp_path / "nowhere.toml", out)
    assert proc.returncode == 2 and "refused" in proc.stderr and not out.exists()


def _pinned_files_or_skip() -> None:
    if not all((EPHE / pin).is_file() for pin in ("seas_18.se1", "semo_18.se1", "sepl_18.se1")):
        pytest.skip("the pinned data files are not on this machine (cache/ephe)")


@pytest.mark.parametrize("defect", ["extra_file", "missing_file", "wrong_bytes", "empty_not_empty"])
def test_a_directory_that_is_not_what_it_claims_is_refused(tmp_path, defect):
    """⛔ The library reads what it finds in a directory, so the directory is the input."""
    _pinned_files_or_skip()
    repo, _ = _committed_copy(tmp_path)
    data, empty = tmp_path / "data", tmp_path / "empty"
    shutil.copytree(EPHE, data, ignore=shutil.ignore_patterns("*.txt", ".*"))
    for extra in sorted(data.iterdir()):
        if extra.name not in ("seas_18.se1", "semo_18.se1", "sepl_18.se1"):
            extra.unlink()
    empty.mkdir()
    if defect == "extra_file":
        (data / "seleapsec.txt").write_text("20200630\n", encoding="ascii")
    elif defect == "missing_file":
        (data / "seas_18.se1").unlink()
    elif defect == "wrong_bytes":
        content = bytearray((data / "seas_18.se1").read_bytes())
        content[-1] ^= 1
        (data / "seas_18.se1").write_bytes(bytes(content))
    else:
        (empty / "a.se1").write_bytes(b"")
    out = tmp_path / "out.jsonl"
    proc = _invoke(repo, data, empty, _manifest(tmp_path), out)
    assert proc.returncode == 2, proc.stderr[-400:]
    expected = {"extra_file": "not exactly the pinned set", "missing_file": "not exactly the pinned set",
                "wrong_bytes": "does not match its pin", "empty_not_empty": "the empty directory holds"}
    assert expected[defect] in proc.stderr
    assert not out.exists()


@pytest.fixture(scope="module")
def emission(tmp_path_factory) -> dict:
    pytest.importorskip(
        "swisseph", reason="the generator calls the ephemeris library; it cannot run where it is not installed")
    _pinned_files_or_skip()
    base = tmp_path_factory.mktemp("emission")
    repo, commit = _committed_copy(base)
    empty = base / "empty"
    empty.mkdir()
    out = base / "record.jsonl"
    proc = _invoke(repo, EPHE, empty, _manifest(base), out)
    assert proc.returncode == 0, proc.stderr[-800:]
    assert f"commit {commit}" in proc.stderr
    text = out.read_text(encoding="ascii")
    lines = [json.loads(line) for line in text.splitlines()]
    return {"commit": commit, "header": lines[0], "rows": lines[1:], "text": text}


def test_the_record_is_an_r3_provenance_record_naming_its_commit_and_versions(emission):
    import swisseph as swe
    from importlib.metadata import version

    header = emission["header"]
    assert (header["record"], header["fixture_kind"], header["reference"]) == ("header", "provenance_record", "R3")
    assert header["generator"] == {"repo": "github.com/insculptor/Saakshi", "script": "generators/mean_node_modes.py",
                                   "commit": emission["commit"]}
    oracle = header["oracle"]
    assert oracle["library_version"] == swe.version
    assert oracle["called_via"] == {"binding": "pyswisseph", "version": version("pyswisseph")}
    assert oracle["session"]["removed_environment_variables"] == ["SE_MARKER_FOR_TEST"]
    assert oracle["host"] == {"python": sys.version.split()[0], "platform": platform.platform(),
                              "machine": platform.machine()}
    assert {r["finding"] for r in emission["rows"]} == {"mean_node_reading", "delta_t_reading",
                                                       "returned_flag_by_body"}
    assert all("body" in r for r in emission["rows"] if r["finding"] != "delta_t_reading")
    assert header["summary"]["readings"] == header["summary"]["children"] == len(emission["rows"]) == 973


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


def shared_rendering(rows: list[dict]) -> str:
    """The fields the scoping measurement recorded, per reading, keyed — as its reproduction renders them."""
    rendered = {}
    for r in rows:
        if r["finding"] == "returned_flag_by_body":
            key, values = ("flag", r["condition"], r["entry_point"], r["body_label"]), (r["requested"], r["returned"])
        else:
            key = (r["part"], r["configuration"], r["nutation"], r["entry_point"], r.get("forced_constant", ""),
                   r["jd_bits"])
            files = tuple((f["ifno"], f["file"], f["start_bits"], f["end_bits"], f["denum"])
                          for f in r["current_file_data_after"])
            if r["entry_point"] == "deltat_ex":
                values = (r["requested"], r["tidal_constant_before_bits"], r["tidal_constant_after_bits"],
                          r["delta_t_days_bits"], files)
            else:
                values = (r["requested"], r["returned"], r["tidal_constant_before_bits"],
                          r["tidal_constant_after_bits"], r["longitude_bits"], r["latitude_bits"],
                          r["distance_bits"], files)
        assert key not in rendered, key
        rendered[key] = values
    canonical = "".join(repr((k, rendered[k])) + "\n" for k in sorted(rendered, key=repr))
    return hashlib.sha256(canonical.encode()).hexdigest()


def test_it_reproduces_the_scoping_measurement_bit_for_bit(emission):
    """⭐ Control 1: every reading the generator shares with the 2026-10-26 scoping measurement."""
    assert shared_rendering(emission["rows"]) == REPRODUCTION_DIGEST


def test_every_row_of_the_record_is_pinned(emission):
    canonical = "".join(json.dumps(r, sort_keys=True, ensure_ascii=True) + "\n" for r in emission["rows"])
    assert hashlib.sha256(canonical.encode()).hexdigest() == READINGS_DIGEST


def test_the_node_echoes_where_the_moon_reports(emission):
    flags = [r for r in emission["rows"] if r["finding"] == "returned_flag_by_body"]
    assert len(flags) == 28
    for row in flags:
        if row["body_label"] == "moon":
            assert row["substitution_reported"] is row["built_to_substitute"], row["condition"]
        else:
            assert row["substitution_reported"] is False and row["returned"] == row["requested"], row["condition"]
    assert sum(r["built_to_substitute"] for r in flags) == 20


def test_a_reader_that_ignores_the_returned_flag_fails_the_moon_control(emission):
    """⭐ Control 2: with the files absent the Moon's word reports a substitution. A generator that wrote
    the request in place of what came back would leave every node row as it is — and is refused."""
    m = _module()
    rows = copy.deepcopy(emission["rows"])
    for row in rows:
        if row["finding"] == "returned_flag_by_body":
            row["returned"] = row["requested"]
            row["substitution_reported"] = False
    node_rows = [r for r in rows if r["finding"] == "returned_flag_by_body" and r["body_label"] == "mean_node"]
    original = [r for r in emission["rows"] if r["finding"] == "returned_flag_by_body" and r["body_label"] == "mean_node"]
    assert node_rows == original, "the node rows of a deaf reader are indistinguishable from the real ones"
    with pytest.raises(m.Refusal, match="the Moon control did not fire"):
        m.check(rows, _context(m, emission))


def _context(m, emission) -> dict:
    import swisseph as swe

    summary = emission["header"]["summary"]
    epochs = [{"epoch_id": r["epoch_id"], "jd": r["jd"], "in_supported_interval": r["in_supported_interval"]}
              for r in emission["rows"] if r.get("part") == "mode_invariance"
              and r["configuration"] == "moshier_files_present" and r["nutation"] == "default"]
    universal = [{"epoch_id": r["epoch_id"], "jd": r["jd"]} for r in emission["rows"]
                 if r.get("part") == "universal_time" and r["entry_point"] == "calc_ut"
                 and r["configuration"] == "moshier_files_present"]
    assert [u["epoch_id"] for u in universal] == summary["epochs"]["universal_time_epochs"]
    return {"epochs": epochs, "universal": universal, "nonut": swe.FLG_NONUT, "children": summary["children"],
            "conditions": m.CONDITIONS, "interval": None,
            "flag": {"moshier": swe.FLG_MOSEPH, "swiss_file": swe.FLG_SWIEPH, "jpl_file": swe.FLG_JPLEPH},
            "forced": {name: m.bits(getattr(swe, name)) for name, _ in m.FORCED},
            "bodies": {"moon": swe.MOON, "mean_node": swe.MEAN_NODE},
            "body_names": {b: swe.get_planet_name(b) for b in (swe.MOON, swe.MEAN_NODE)}}


def test_the_controls_pass_on_the_record_as_written(emission):
    m = _module()
    summary = m.check(copy.deepcopy(emission["rows"]), _context(m, emission))
    written = {k: v for k, v in emission["header"]["summary"].items() if k != "epochs"}
    assert summary == written


def test_a_reading_taken_without_a_fresh_child_is_refused(tmp_path):
    """⭐ Control 3 (MN-8): two readings handed to one child are refused, not recorded as two cold ones."""
    pytest.importorskip("swisseph", reason="the child calls the ephemeris library")
    _pinned_files_or_skip()
    m = _module()
    spec = m.spec_for(path=str(EPHE), flags=4, entry_point="calc", jd=2451545.0, body=10)
    children = m.Children(str(tmp_path))
    assert len(children.run([spec])) == 1
    with pytest.raises(m.Refusal, match="took 2 readings"):
        children.run([spec, spec])


def test_one_childs_reading_returned_twice_is_refused(tmp_path, monkeypatch):
    """⛔ A parent that handed one child's output to two readings would record one reading twice."""
    m = _module()
    reply = json.dumps({"nonce": "0" * 32, "fresh_interpreter": True, "calls": [{"flags": 4}],
                        "readings": [{}]})
    monkeypatch.setattr(m.subprocess, "run",
                        lambda *a, **k: subprocess.CompletedProcess(a, 0, stdout=reply, stderr=""))
    children = m.Children(str(tmp_path))
    children.run([{}])
    with pytest.raises(m.Refusal, match="two readings came back from one child"):
        children.run([{}])


def test_a_call_sequence_other_than_the_rows_is_refused():
    """⭐ The finished row declares every call its child made; the child records every call the library received.
    One extra call — a warm reading through ANY entry point — or one argument other than the row's is refused."""
    m = _module()
    row = {"finding": "mean_node_reading", "path_state": "data_files", "entry_point": "calc",
           "jd_bits": m.bits(2451545.0), "body": 10, "requested": 68}
    paths = {"data_files": "/d", "empty_directory": "/e", "no_path_set": None}
    declared = m.declared_calls(row, paths)
    assert [c["function"] for c in declared] == ["set_ephe_path", "get_tid_acc", "calc", "get_tid_acc",
                                                 "get_current_file_data", "get_current_file_data"]
    assert m.admit(row, declared, paths) is row
    for planted in (declared[:2] + [m._call("contrib.calc_ut", m.bits(2451545.0), 1, 68)] + declared[2:],
                    [dict(c, args=[c["args"][0], 10, 4]) if c["function"] == "calc" else c for c in declared],
                    [dict(c, args=["/e"]) if c["function"] == "set_ephe_path" else c for c in declared]):
        with pytest.raises(m.Refusal, match="the row declares"):
            m.admit(row, planted, paths)


def _planted(tmp_path: Path, anchor: str, replacement: str):
    """A copy of the generator carrying one defect, imported from its own file so its children run it."""
    text = SCRIPT.read_text(encoding="utf-8")
    assert text.count(anchor) == 1, anchor
    path = tmp_path / "planted.py"
    path.write_text(text.replace(anchor, replacement), encoding="utf-8")
    spec = importlib.util.spec_from_file_location("planted", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("defect", ["nonut_dropped_at_the_call", "a_warm_call_first",
                                    "a_warm_call_through_the_submodule", "the_wrong_directory",
                                    "a_row_built_wrong_after_the_call"])
def test_a_child_that_did_other_than_its_row_declares_is_refused(tmp_path, defect):
    """⭐ The same control against real children, so the recorder itself is under test — and against a row
    built wrong after its call, because the finished row is what is judged."""
    pytest.importorskip("swisseph", reason="the child calls the ephemeris library")
    _pinned_files_or_skip()
    call = 'values, returned = call(unbits(spec["jd_bits"]), spec["body"], spec["flags"])'
    plants = {
        "nonut_dropped_at_the_call": (call, call.replace('spec["flags"])', 'spec["flags"] & ~swe.FLG_NONUT)')),
        "a_warm_call_first": (call, 'swe.pheno_ut(unbits(spec["jd_bits"]), 1, spec["flags"])\n            ' + call),
        "a_warm_call_through_the_submodule": (
            call, 'swe.contrib.calc_ut(unbits(spec["jd_bits"]), 1, spec["flags"])\n            ' + call),
        "the_wrong_directory": ('            swe.set_ephe_path(spec["path"])',
                                f'            swe.set_ephe_path({str(EPHE)!r})'),
        "a_row_built_wrong_after_the_call": ('    row = dict(base)\n', '    row = dict(base, requested=base["requested"] ^ 64)\n'),
    }
    m = _planted(tmp_path, *plants[defect])
    empty = tmp_path / "empty"
    empty.mkdir()
    paths = {"data_files": str(EPHE), "empty_directory": str(empty), "no_path_set": None}
    base = {"finding": "mean_node_reading", "path_state": "empty_directory", "entry_point": "calc",
            "jd_bits": m.bits(2451545.0), "body": 10, "requested": 66}
    spec = m.spec_for(path=str(empty), flags=66, entry_point="calc", jd=2451545.0, body=10)
    work = tmp_path / "work"
    work.mkdir()
    honest = _module()
    reading = honest.Children(str(work)).take_all([spec])[0]
    assert honest.admit(honest.row_from(reading, base), reading["calls"], paths)
    reading = m.Children(str(work)).take_all([spec])[0]
    with pytest.raises(m.Refusal, match="the row declares"):
        m.admit(m.row_from(reading, base), reading["calls"], paths)


NAME_PLANTS = {
    "an_ephemeris_label_not_its_word": (lambda r: r.get("ephemeris_requested") == "swiss_file"
                                        and r["finding"] == "mean_node_reading",
                                        {"ephemeris_requested": "jpl_file"}, "labelled jpl_file"),
    "a_configuration_name_not_its_path": (lambda r: r.get("configuration") == "swiss_file_present",
                                          {"configuration": "swiss_file_dir_empty"}, "is not that configuration"),
    "a_condition_name_not_its_path": (lambda r: r.get("condition") == "swiss_file_empty_directory",
                                      {"condition": "swiss_file_inside_coverage"}, "is not that condition"),
    "a_forced_constant_misnamed": (lambda r: r.get("forced_constant") == "TIDAL_DE200",
                                   {"forced_constant": "TIDAL_26"}, "naming TIDAL_26"),
    "an_offset_labelled_nonut": (lambda r: r["finding"] == "delta_t_reading", {"nutation": "nonut"},
                                 "labelled nonut through deltat_ex"),
    "a_body_label_not_its_body": (lambda r: r.get("body_label") == "moon", {"body_label": "mean_node"},
                                  "labelled mean_node read body 1"),
    "an_epoch_name_not_its_instant": (lambda r: r.get("epoch_id") == "grid_1900", {"epoch_id": "grid_1905"},
                                      "is not that instant"),
    "an_offset_filed_as_a_node_reading": (lambda r: r["finding"] == "delta_t_reading",
                                          {"finding": "mean_node_reading"}, "filed as mean_node_reading"),
    "a_reading_in_another_part": (lambda r: r.get("part") == "cause", {"part": "universal_time_cause"},
                                  "in part universal_time_cause"),
    "a_node_reading_of_another_body": (lambda r: r["finding"] == "mean_node_reading", {"body": 1},
                                       "a mean_node_reading read body 1"),
    "a_body_name_not_its_body": (lambda r: r.get("body_label") == "moon", {"body_name": "mean Node"},
                                 "naming body 1"),
    "a_cause_reading_filed_as_mode_invariance": (lambda r: r.get("part") == "cause", {"part": "mode_invariance"},
                                                 "is not that part's"),
    "a_forced_universal_reading_filed_unforced": (lambda r: r.get("part") == "universal_time_cause",
                                                  {"part": "universal_time"}, "is not that part's"),
    "an_offset_reading_with_a_body": (lambda r: r["finding"] == "delta_t_reading", {"body": 10},
                                      "a delta_t_reading carries body 10"),
}


@pytest.mark.parametrize("plant", sorted(NAME_PLANTS))
def test_a_row_whose_name_is_not_what_it_names_is_refused(emission, plant):
    """⛔ Each pair `check()` holds — a name to what it names — refuses a row that breaks it: a label is a claim."""
    m = _module()
    select, change, message = NAME_PLANTS[plant]
    rows = copy.deepcopy(emission["rows"])
    next(r for r in rows if select(r)).update(change)
    with pytest.raises(m.Refusal, match=message):
        m.check(rows, _context(m, emission))


def test_a_reading_count_other_than_the_childrens_is_refused(emission):
    m = _module()
    context = _context(m, emission)
    context["children"] -= 1
    with pytest.raises(m.Refusal, match="972 children"):
        m.check(copy.deepcopy(emission["rows"]), context)


def test_a_dropped_nonut_is_refused(emission):
    """⭐ Control 4: without the bit the node moves by up to the nutation's whole effect (~17.5″ here). A
    nonut reading equal to its default twin, or a nonut row that did not request the bit, is refused."""
    m = _module()
    assert emission["header"]["summary"]["largest_default_minus_nonut_arcseconds"] == 17.4844
    rows = copy.deepcopy(emission["rows"])
    twins = {(r["configuration"], r["epoch_id"]): r for r in rows
             if r.get("part") == "mode_invariance" and r["nutation"] == "default"}
    for row in rows:
        if row.get("part") == "mode_invariance" and row["nutation"] == "nonut":
            twin = twins[(row["configuration"], row["epoch_id"])]
            row.update(longitude=twin["longitude"], longitude_bits=twin["longitude_bits"])
    with pytest.raises(m.Refusal, match="NONUT request moved nothing"):
        m.check(rows, _context(m, emission))
    rows = copy.deepcopy(emission["rows"])
    first = next(r for r in rows if r.get("nutation") == "nonut")
    first["requested"] &= ~64
    with pytest.raises(m.Refusal, match="labelled nonut"):
        m.check(rows, _context(m, emission))
