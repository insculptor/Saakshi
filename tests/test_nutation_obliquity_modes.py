"""The nutation-and-obliquity generator: what it may import, where its epochs come from, and every control it keeps.

⛔ Like the mean-node generator it follows, it imports nothing but the standard library and the binding, so the
first tests are static and need no library. The interval tests read a manifest written here. The rest run it end
to end — from a commit of its own, in a scratch repository, because it refuses a dirty tree — and then plant, one
at a time, the defect each control exists to catch, each beside the record as written, which passes.
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
SCRIPT = ROOT / "generators" / "nutation_obliquity_modes.py"
EPHE = ROOT / "cache" / "ephe"

#: The coverage a data profile manifest declares for its one dataset, as the generator reads it.
COVERAGE = 'declared_coverage = { start = "1849-12-26T00:00:00", end = "2150-01-22T00:00:00", scale = "TDB" }'

#: ⭐ Every row of the record, every field, pinned so that nothing in it is compared with nothing. ⚠ Host-bound
#: (macOS arm64, CPython 3.12.11, the library 2.10.03 through its binding 2.10.3.2), as the mean-node record's pins.
READINGS_DIGEST = "e443b3648193889a3c565e04603517dd91572368ded507ab1cc2e2746631fc62"


def _module():
    spec = importlib.util.spec_from_file_location("nutation_obliquity_modes", SCRIPT)
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
# The epochs — the interval's from the manifest, the others the survey's own
# ---------------------------------------------------------------------------------------


def test_the_interval_is_the_manifests_and_converts_back(tmp_path):
    m = _module()
    interval = m.read_interval(str(_manifest(tmp_path)))
    assert (interval["start"], interval["end"]) == (2396752.5, 2506352.5)
    epochs = m.build_epochs(interval)
    assert [e["epoch_id"] for e in epochs] == [
        "edge_search_1000_01_01", "outside_1500", "supported_start_1849_12_26", "j2000",
        "supported_end_2150_01_22", "edge_search_3000_01_01", "outside_3000"]
    assert [e["epoch_id"] for e in epochs if e["in_supported_interval"]] == [
        "supported_start_1849_12_26", "j2000", "supported_end_2150_01_22"]
    assert [e["epoch_id"] for e in m.universal_epochs(epochs)] == [e["epoch_id"] for e in epochs]
    assert all("in_supported_interval" not in e for e in m.universal_epochs(epochs))


def test_the_interval_ends_follow_the_manifest_and_not_a_number_written_here(tmp_path):
    """⭐ The red control for the interval: a manifest declaring other dates gives exactly those days, at both
    ends and in every in-interval flag — so what decides them is the file, never a constant."""
    m = _module()
    planted = 'declared_coverage = { start = "1850-01-01T00:00:00", end = "2150-01-01T00:00:00", scale = "TDB" }'
    for name, coverage, (start, end), ids in (
            ("planted", planted, (2396758.5, 2506331.5), ("supported_start_1850_01_01", "supported_end_2150_01_01")),
            ("declared", COVERAGE, (2396752.5, 2506352.5), ("supported_start_1849_12_26", "supported_end_2150_01_22"))):
        (tmp_path / name).mkdir()
        epochs = m.build_epochs(m.read_interval(str(_manifest(tmp_path / name, coverage))))
        assert {e["epoch_id"]: e["jd"] for e in epochs if e["epoch_id"].startswith("supported_")} == dict(
            zip(ids, (start, end)))
        assert all(e["in_supported_interval"] == (start <= e["jd"] <= end) for e in epochs)


def test_an_epoch_built_outside_that_falls_inside_is_refused(tmp_path):
    """⛔ The outside years and the search's ends are outside by construction, and checked to be — beside the
    declared interval, which they are outside of."""
    m = _module()
    assert m.build_epochs(m.read_interval(str(_manifest(tmp_path))))
    wide = 'declared_coverage = { start = "1400-01-01T00:00:00", end = "2150-01-22T00:00:00", scale = "TDB" }'
    (tmp_path / "wide").mkdir()
    with pytest.raises(m.Refusal, match="outside_1500 is inside the interval"):
        m.build_epochs(m.read_interval(str(_manifest(tmp_path / "wide", wide))))


def test_a_julian_day_that_does_not_convert_back_is_refused(tmp_path, monkeypatch):
    """⛔ A conversion that drifted by a day would move every epoch with it; converting back catches it."""
    m = _module()
    assert m.read_interval(str(_manifest(tmp_path)))["start"] == 2396752.5
    convert = m.julian_day
    monkeypatch.setattr(m, "julian_day", lambda stamp: convert(stamp) + 1.0)
    with pytest.raises(m.Refusal, match="converts back"):
        m.read_interval(str(_manifest(tmp_path)))


def test_a_coverage_that_does_not_run_forward_is_refused(tmp_path):
    m = _module()
    assert m.read_interval(str(_manifest(tmp_path)))["end"] == 2506352.5
    backwards = 'declared_coverage = { start = "2150-01-22T00:00:00", end = "1849-12-26T00:00:00", scale = "TDB" }'
    (tmp_path / "backwards").mkdir()
    with pytest.raises(m.Refusal, match="does not run forward"):
        m.read_interval(str(_manifest(tmp_path / "backwards", backwards)))


def test_a_civil_instant_carrying_a_zone_is_refused():
    m = _module()
    assert m.julian_day("2000-01-01T12:00:00") == m.J2000
    with pytest.raises(m.Refusal, match="carries no zone"):
        m.julian_day("2000-01-01T12:00:00+00:00")


def test_two_epochs_at_one_instant_are_refused(tmp_path, monkeypatch):
    m = _module()
    interval = m.read_interval(str(_manifest(tmp_path)))
    assert len(m.build_epochs(interval)) == 7
    monkeypatch.setattr(m, "OUTSIDE_YEARS", (1500, 1500))
    with pytest.raises(m.Refusal, match="two epochs share an instant or a name"):
        m.build_epochs(interval)


def test_a_manifest_that_does_not_declare_one_coverage_is_refused(tmp_path):
    m = _module()
    with pytest.raises(m.Refusal, match="2 datasets"):
        m.read_interval(str(_manifest(tmp_path, datasets=2)))
    (tmp_path / "bare").mkdir()
    with pytest.raises(m.Refusal, match="no complete coverage"):
        m.read_interval(str(_manifest(tmp_path / "bare", 'declared_coverage = { start = "1849-12-26T00:00:00" }')))


def test_the_other_epochs_are_the_surveys_own():
    """⭐ The outside years are the survey's fixed-condition instants, and the search's ends are the instants the
    survey converts its search years to, through the library — so the record reads the body where the survey
    reads every other body."""
    pytest.importorskip("swisseph", reason="the survey's constants are read through the library")
    import swisseph as swe

    sys.path.insert(0, str(ROOT / "src"))
    sys.path.insert(0, str(ROOT / "generators"))
    from saakshi.swiss import FIXED_CONDITION_EPOCHS

    import r3_swiss

    m = _module()
    assert {f"outside_{y}": m.year_epoch(y) for y in m.OUTSIDE_YEARS} == {
        k: v for k, v in FIXED_CONDITION_EPOCHS.items() if k.startswith("outside_")}
    assert FIXED_CONDITION_EPOCHS["j2000"] == m.J2000
    low, middle, high = m.edge_search_instants()
    assert (low, high) == tuple(swe.julday(year, 1, 1, 0.0) for year in r3_swiss.EDGE_SEARCH_YEARS)
    assert [m.EDGE_SEARCH[i][:4] for i in (0, 1)] == [str(y) for y in r3_swiss.EDGE_SEARCH_YEARS]
    # ⭐ measured: the search's middle IS J2000, so it is read there and gets no epoch of its own
    assert middle == m.J2000


def test_a_search_middle_that_is_no_other_epoch_gets_one_of_its_own(tmp_path, monkeypatch):
    """The twin of the measured case above: a search range whose middle is not J2000 is read at its middle."""
    m = _module()
    interval = m.read_interval(str(_manifest(tmp_path)))
    assert "edge_search_middle" not in [e["epoch_id"] for e in m.build_epochs(interval)]
    monkeypatch.setattr(m, "EDGE_SEARCH", ("1000-01-01T00:00:00", "3100-01-01T00:00:00"))
    epochs = m.build_epochs(interval)
    middle = next(e for e in epochs if e["epoch_id"] == "edge_search_middle")
    assert middle["jd"] == sum(m.edge_search_instants()[::2]) / 2.0 and middle["jd"] != m.J2000


def test_every_epoch_label_is_its_instant(tmp_path):
    """⛔ Epoch labels are the generator's own table, so each is held to its instant by a rule written here."""
    m = _module()
    for epoch in m.build_epochs(m.read_interval(str(_manifest(tmp_path)))):
        label, jd = epoch["epoch_id"], epoch["jd"]
        head, _, rest = label.partition("_")
        if label == "j2000":
            assert jd == 2451545.0
        elif head == "outside":
            assert jd == m.year_epoch(int(rest)) and not epoch["in_supported_interval"], label
        elif head in ("supported", "edge"):
            assert m.civil(jd)[:10] == "-".join(label.rsplit("_", 3)[-3:]), label
        else:
            raise AssertionError(f"an epoch label no rule reads: {label}")


def test_the_tables_names_say_what_they_define():
    """⛔ `check()` holds every row's configuration and condition name to the table that defines it, so each
    table is held to its own names' words — and ⛔ no configuration or condition leaves the path unset."""
    m = _module()
    prefixes = {"moshier": "moshier_", "swiss_file": "swiss_file_", "jpl_file": "jpl_"}
    words = {"files_present": "data_files", "file_present": "data_files", "no_jpl_file": "data_files",
             "inside_coverage": "data_files", "outside_coverage": "data_files", "dir_empty": "empty_directory",
             "empty_directory": "empty_directory"}

    def state_of(name: str) -> str:
        named = {state for word, state in words.items() if word in name}
        assert len(named) == 1, f"{name}: its words name {sorted(named) or 'no'} directory state"
        return named.pop()

    for name, ephemeris, state in m.CONFIGURATIONS:
        assert name.startswith(prefixes[ephemeris]) and state_of(name) == state, name
    outside = {"swiss_file_outside_coverage_1500": "outside_1500", "swiss_file_outside_coverage_3000": "outside_3000"}
    for condition in m.CONDITIONS:
        name = condition["condition"]
        assert name.startswith(prefixes[condition["ephemeris"]]) and state_of(name) == condition["path_state"], name
        assert condition["epoch"] == outside.get(name, "j2000"), name
        assert condition["built_to_substitute"] == (
            name not in ("swiss_file_inside_coverage", "moshier_files_present")), name
    states = {s for *_, s in m.CONFIGURATIONS} | {c["path_state"] for c in m.CONDITIONS}
    assert states == {"data_files", "empty_directory"}


def test_the_named_values_are_the_consumers_three_and_six_positions_are_documented():
    m = _module()
    assert m.READER_FIELDS == ("longitude", "latitude", "distance")
    assert len(m.VALUE_POSITIONS) == 6 and m.VALUE_POSITIONS[4:] == ("0", "0")


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


def test_a_script_away_from_its_own_path_or_an_existing_output_is_refused(tmp_path):
    """⛔ `generator.script` would name a file that did not run; an emission over an existing file would replace
    evidence. Each refused before anything is read — beside the record written at its own path (`emission`)."""
    repo, _ = _committed_copy(tmp_path / "moved")
    (repo / "generators" / SCRIPT.name).rename(repo / "generators" / "elsewhere.py")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "moved")
    empty = tmp_path / "empty"
    empty.mkdir()
    out = tmp_path / "out.jsonl"
    proc = subprocess.run([sys.executable, str(repo / "generators" / "elsewhere.py"), "--ephe-path", str(EPHE),
                           "--empty-dir", str(empty), "--profile", str(tmp_path / "nowhere.toml"), "--out", str(out)],
                          cwd=repo, capture_output=True, text=True, timeout=120, check=False)
    assert proc.returncode == 2 and "this script is generators/elsewhere.py" in proc.stderr and not out.exists()
    repo, _ = _committed_copy(tmp_path / "existing")
    out.write_text("held\n", encoding="ascii")
    proc = _invoke(repo, EPHE, empty, tmp_path / "nowhere.toml", out)
    assert proc.returncode == 2 and "exists; each emission goes to a new path" in proc.stderr
    assert out.read_text(encoding="ascii") == "held\n"


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
    assert header["generator"] == {"repo": "github.com/insculptor/Saakshi",
                                   "script": "generators/nutation_obliquity_modes.py", "commit": emission["commit"]}
    oracle = header["oracle"]
    assert oracle["library_version"] == swe.version
    assert oracle["called_via"] == {"binding": "pyswisseph", "version": version("pyswisseph")}
    assert oracle["session"]["removed_environment_variables"] == ["SE_MARKER_FOR_TEST"]
    assert oracle["host"] == {"python": sys.version.split()[0], "platform": platform.platform(),
                              "machine": platform.machine()}
    assert {r["finding"] for r in emission["rows"]} == {"nutation_obliquity_reading", "delta_t_reading",
                                                       "returned_flag_by_body"}
    assert {r["body"] for r in emission["rows"] if r["finding"] == "nutation_obliquity_reading"} == {swe.ECL_NUT}
    assert header["summary"]["readings"] == header["summary"]["children"] == len(emission["rows"]) == 293
    assert header["summary"]["rows_by_part"] == {"mode_invariance": 70, "universal_time": 175,
                                                 "returned_flag_by_body": 48}


#: ⭐ The one record-level statement of freshness its consumer admits, character for character — the mean-node
#: record's own. ⛔ A paraphrase attests nothing, so the consumer would read none of these readings as fresh.
FRESHNESS_LITERAL = ("⛔ every reading is one call in a fresh child interpreter (-I); the children run in an empty "
                     "working directory that is not the parent's, verified empty after the run; the parent takes "
                     "no reading")


def test_its_freshness_is_the_one_literal_its_consumer_admits(emission):
    assert emission["header"]["oracle"]["session"]["isolation"] == FRESHNESS_LITERAL
    precedent = _module_named("mean_node_modes")
    assert FRESHNESS_LITERAL in json.loads(json.dumps(precedent))


def _module_named(name: str) -> str:
    """A generator's source with its implicitly concatenated string literals joined, as Python joins them."""
    tree = ast.parse((ROOT / "generators" / f"{name}.py").read_text(encoding="utf-8"))
    return "\n".join(node.value for node in ast.walk(tree)
                     if isinstance(node, ast.Constant) and isinstance(node.value, str))


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


def test_the_pseudo_body_echoes_where_the_moon_reports(emission):
    import swisseph as swe

    flags = [r for r in emission["rows"] if r["finding"] == "returned_flag_by_body"]
    assert len(flags) == 48 and sum(r["built_to_substitute"] for r in flags) == 32
    for row in flags:
        if row["body_label"] == "moon":
            assert row["substitution_reported"] is row["built_to_substitute"], row["condition"]
        else:
            assert row["body"] == swe.ECL_NUT and row["returned"] == row["requested"], row["condition"]
            assert row["substitution_reported"] is False
    readings = [r for r in emission["rows"] if r.get("body") == swe.ECL_NUT]
    assert all(r["returned"] == r["requested"] for r in readings) and len(readings) == 234


def test_what_the_record_measured(emission):
    """⭐ The findings, as measured on this host — so a reading that moves turns this red, and says which."""
    summary = emission["header"]["summary"]
    for nutation in ("default", "nonut"):
        calc = summary["mode_invariance"][nutation]
        assert (calc["epochs_with_one_set_of_six_values_across_the_five_configurations"], calc["of"]) == (7, 7)
        ut = summary["universal_time"][nutation]
        assert ut["epochs_where_the_values_moved"] == [
            "edge_search_1000_01_01", "outside_1500", "supported_start_1849_12_26"]
    assert (summary["universal_time"]["calc_ut_identical_to_calc_at_ut_plus_delta_t"],
            summary["universal_time"]["of"]) == (70, 70)
    assert summary["nonut"] == {"pairs": 105, "pairs_bit_identical_at_position": [0, 105, 0, 0, 105, 105],
                                "nonut_readings_of_the_body": 117, "position_0_bit_identical_to_position_1": 117,
                                "positions_2_and_3_both_zero": 117}
    assert summary["edge"]["measured_edge"] is None and summary["edge"]["returned_the_requested_source"] == 12
    assert summary["body_name"] == ""


def _context(m, emission) -> dict:
    import swisseph as swe

    rows = emission["rows"]
    epochs = [{"epoch_id": r["epoch_id"], "jd": r["jd"], "in_supported_interval": r["in_supported_interval"]}
              for r in rows if r.get("part") == "mode_invariance"
              and r["configuration"] == "moshier_files_present" and r["nutation"] == "default"]
    assert [e["epoch_id"] for e in epochs] == emission["header"]["summary"]["epochs"]["ids"]
    return {"epochs": epochs, "universal": m.universal_epochs(epochs), "nonut": swe.FLG_NONUT,
            "children": emission["header"]["summary"]["children"], "conditions": m.CONDITIONS, "interval": None,
            "flag": {"moshier": swe.FLG_MOSEPH, "swiss_file": swe.FLG_SWIEPH, "jpl_file": swe.FLG_JPLEPH},
            "bodies": {"moon": swe.MOON, "nutation_obliquity": swe.ECL_NUT},
            "body_names": {b: swe.get_planet_name(b) for b in (swe.MOON, swe.ECL_NUT)}}


def test_the_controls_pass_on_the_record_as_written(emission):
    m = _module()
    summary = m.check(copy.deepcopy(emission["rows"]), _context(m, emission))
    assert summary == {k: v for k, v in emission["header"]["summary"].items() if k != "epochs"}
    assert m.notes(summary) == emission["header"]["notes"]


def test_the_notes_say_what_the_summary_says(emission):
    """⭐ A note states a finding from the summary it is about, so a summary that says otherwise changes it."""
    m = _module()
    summary = copy.deepcopy({k: v for k, v in emission["header"]["summary"].items() if k != "epochs"})
    assert "ECHOES THE REQUEST" in m.notes(summary)[1]
    assert "DID NOT MOVE" in m.notes(summary)[2]
    summary["returned_word"]["returned_exactly_the_requested_word"] -= 1
    summary["mode_invariance"]["nonut"]["epochs_where_the_values_moved"] = ["j2000"]
    summary["mode_invariance"]["nonut"]["epochs_with_one_set_of_six_values_across_the_five_configurations"] -= 1
    written = m.notes(summary)
    assert "ECHOES" not in written[1] and "233 of its 234" in written[1]
    assert "MOVED with the configuration at j2000" in written[2]


def test_a_reader_that_ignores_the_returned_flag_fails_the_moon_control(emission):
    """⭐ With the files absent the Moon's word reports a substitution. A generator that wrote the request in
    place of what came back would leave every pseudo-body row as it is — and is refused."""
    m = _module()
    rows = copy.deepcopy(emission["rows"])
    for row in rows:
        if row["finding"] == "returned_flag_by_body":
            row["returned"] = row["requested"]
            row["substitution_reported"] = False
    mine = [r for r in rows if r.get("body_label") == "nutation_obliquity"]
    assert mine == [r for r in emission["rows"] if r.get("body_label") == "nutation_obliquity"]
    with pytest.raises(m.Refusal, match="the Moon control did not fire"):
        m.check(rows, _context(m, emission))


def test_a_named_value_that_is_not_its_position_is_refused(emission):
    """⛔ The consumer reads the call's first three values through three names; a row whose name holds another
    position's value would hand it the wrong number under the right name."""
    m = _module()
    rows = copy.deepcopy(emission["rows"])
    row = next(r for r in rows if r["finding"] == "nutation_obliquity_reading")
    row["latitude"], row["latitude_bits"] = row["values"][3], row["values_bits"][3]
    with pytest.raises(m.Refusal, match="named values are not the call's first three"):
        m.check(rows, _context(m, emission))
    rows = copy.deepcopy(emission["rows"])
    row = next(r for r in rows if r["finding"] == "nutation_obliquity_reading")
    row["values"], row["values_bits"] = row["values"][:3], row["values_bits"][:3]
    with pytest.raises(m.Refusal, match="named values are not the call's first three of 3"):
        m.check(rows, _context(m, emission))


def test_a_returned_word_nobody_requested_is_refused(emission):
    """⛔ A consumer reads a returned word only through the words readings requested. A word none of them did —
    here the speed bit beside a Moon reading's — could not be read, and would refuse the body under every word."""
    m = _module()
    rows = copy.deepcopy(emission["rows"])
    row = next(r for r in rows if r.get("body_label") == "moon" and r["substitution_reported"])
    row["returned"] |= 256
    with pytest.raises(m.Refusal, match="which no reading through that entry point requested"):
        m.check(rows, _context(m, emission))


def test_a_reading_taken_without_a_fresh_child_is_refused(tmp_path):
    """⭐ Two readings handed to one child are refused, not recorded as two cold ones — beside one, admitted."""
    pytest.importorskip("swisseph", reason="the child calls the ephemeris library")
    _pinned_files_or_skip()
    m = _module()
    spec = m.spec_for(path=str(EPHE), flags=2, entry_point="calc", jd=2451545.0, body=-1)
    children = m.Children(str(tmp_path))
    assert len(children.run([spec])) == 1
    with pytest.raises(m.Refusal, match="took 2 readings"):
        children.run([spec, spec])


def test_one_childs_reading_returned_twice_is_refused(tmp_path, monkeypatch):
    """⛔ A parent that handed one child's output to two readings would record one reading twice."""
    m = _module()
    reply = json.dumps({"nonce": "0" * 32, "fresh_interpreter": True, "calls": [], "readings": [{}]})
    monkeypatch.setattr(m.subprocess, "run",
                        lambda *a, **k: subprocess.CompletedProcess(a, 0, stdout=reply, stderr=""))
    children = m.Children(str(tmp_path))
    children.run([{}])
    with pytest.raises(m.Refusal, match="two readings came back from one child"):
        children.run([{}])


def test_every_child_runs_isolated_without_the_librarys_environment(tmp_path, monkeypatch):
    """⛔ A child is an isolated interpreter (-I), and every SE_ variable is removed from its environment —
    beside a variable that is not the library's, which is kept."""
    m = _module()
    monkeypatch.setenv("SE_EPHE_PATH", "/somewhere")
    monkeypatch.setenv("NOT_THE_LIBRARYS", "kept")
    environment = m.child_environment()
    assert "SE_EPHE_PATH" not in environment and environment["NOT_THE_LIBRARYS"] == "kept"
    seen = []
    reply = json.dumps({"nonce": "1" * 32, "fresh_interpreter": True, "calls": [], "readings": [{}]})

    def run(args, **keywords):
        seen.append((args, keywords["env"]))
        return subprocess.CompletedProcess(args, 0, stdout=reply, stderr="")

    monkeypatch.setattr(m.subprocess, "run", run)
    m.Children(str(tmp_path)).run([{}])
    (args, env), = seen
    assert args[:2] == [sys.executable, "-I"] and "SE_EPHE_PATH" not in env


def test_a_working_directory_left_holding_anything_is_refused(tmp_path, monkeypatch):
    """⛔ The children's working directory is verified empty after the run — beside a run that left it empty,
    which goes on past the check."""
    m = _module()

    class Past(Exception):
        pass

    def raise_past(*a, **k):
        raise Past

    monkeypatch.setattr(m, "source_commit", lambda: "0" * 40)
    monkeypatch.setattr(m, "verify_data_directory", lambda path: None)
    monkeypatch.setattr(m, "check", raise_past)
    empty = tmp_path / "empty"
    empty.mkdir()
    monkeypatch.setattr(m, "measure", lambda ephe, e, profile, work: ([], {}))
    with pytest.raises(Past):
        m.generate("data", str(empty), "profile", str(tmp_path / "a.jsonl"))
    monkeypatch.setattr(m, "measure",
                        lambda ephe, e, profile, work: (Path(work, "stray").write_text("x"), ([], {}))[1])
    with pytest.raises(m.Refusal, match="the empty directory holds \\['stray'\\]"):
        m.generate("data", str(empty), "profile", str(tmp_path / "b.jsonl"))


def test_a_call_sequence_other_than_the_rows_is_refused():
    """⭐ The finished row declares every call its child made; one extra call, or one argument other than the
    row's, is refused — beside the declared sequence, admitted."""
    m = _module()
    row = {"finding": "nutation_obliquity_reading", "path_state": "data_files", "entry_point": "calc",
           "jd_bits": m.bits(2451545.0), "body": -1, "requested": 66}
    paths = {"data_files": "/d", "empty_directory": "/e"}
    declared = m.declared_calls(row, paths)
    assert [c["function"] for c in declared] == ["set_ephe_path", "get_tid_acc", "calc", "get_tid_acc",
                                                 "get_current_file_data", "get_current_file_data"]
    assert m.admit(row, declared, paths) is row
    for planted in (declared[:2] + [m._call("contrib.calc_ut", m.bits(2451545.0), 1, 66)] + declared[2:],
                    [dict(c, args=[c["args"][0], -1, 2]) if c["function"] == "calc" else c for c in declared],
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
    built wrong after its call, because the finished row is what is judged. The honest generator's reading of
    the same spec is admitted beside each."""
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
        "a_row_built_wrong_after_the_call": ('    row = dict(base)\n',
                                             '    row = dict(base, requested=base["requested"] ^ 64)\n'),
    }
    m = _planted(tmp_path, *plants[defect])
    empty = tmp_path / "empty"
    empty.mkdir()
    paths = {"data_files": str(EPHE), "empty_directory": str(empty)}
    base = {"finding": "nutation_obliquity_reading", "path_state": "empty_directory", "entry_point": "calc",
            "jd_bits": m.bits(2451545.0), "body": -1, "requested": 66}
    spec = m.spec_for(path=str(empty), flags=66, entry_point="calc", jd=2451545.0, body=-1)
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
                                        and r["finding"] == "nutation_obliquity_reading",
                                        {"ephemeris_requested": "jpl_file"}, "labelled jpl_file"),
    "a_configuration_name_not_its_path": (lambda r: r.get("configuration") == "swiss_file_present",
                                          {"configuration": "swiss_file_dir_empty"}, "is not that configuration"),
    "a_condition_name_not_its_path": (lambda r: r.get("condition") == "swiss_file_empty_directory",
                                      {"condition": "swiss_file_inside_coverage"}, "is not that condition"),
    "an_offset_labelled_nonut": (lambda r: r["finding"] == "delta_t_reading", {"nutation": "nonut"},
                                 "labelled nonut through deltat_ex"),
    "a_reading_labelled_ephemeris_bits_only": (lambda r: r["finding"] == "nutation_obliquity_reading"
                                               and r["nutation"] == "default", {"nutation": "ephemeris_bits_only"},
                                               "labelled ephemeris_bits_only through calc"),
    "a_flag_row_labelled_against_its_word": (lambda r: r["finding"] == "returned_flag_by_body"
                                             and r["nutation"] == "nonut", {"nutation": "default"},
                                             "labelled default through"),
    "a_body_label_not_its_body": (lambda r: r.get("body_label") == "moon", {"body_label": "nutation_obliquity"},
                                  "labelled nutation_obliquity read body 1"),
    "a_body_name_not_its_body": (lambda r: r.get("body_label") == "nutation_obliquity", {"body_name": "Moon"},
                                 "naming body -1 'Moon'"),
    "an_epoch_name_not_its_instant": (lambda r: r.get("epoch_id") == "outside_1500"
                                      and r["finding"] == "nutation_obliquity_reading", {"epoch_id": "outside_3000"},
                                      "is not that instant"),
    "a_flag_row_at_an_epoch_nobody_named": (lambda r: r["finding"] == "returned_flag_by_body",
                                            {"epoch_id": "nowhere"}, "is not that condition"),
    "an_offset_filed_as_a_reading": (lambda r: r["finding"] == "delta_t_reading",
                                     {"finding": "nutation_obliquity_reading"},
                                     "filed as nutation_obliquity_reading"),
    "a_calc_ut_reading_in_the_calc_part": (lambda r: r.get("entry_point") == "calc_ut"
                                           and r["finding"] == "nutation_obliquity_reading",
                                           {"part": "mode_invariance"}, "in part mode_invariance"),
    "a_calc_reading_at_an_unshifted_universal_instant": (lambda r: r.get("part") == "mode_invariance",
                                                         {"part": "universal_time"}, "is not that part's"),
    "a_reading_of_another_body": (lambda r: r["finding"] == "nutation_obliquity_reading", {"body": 1},
                                  "a nutation_obliquity_reading read body 1"),
    "an_offset_reading_with_a_body": (lambda r: r["finding"] == "delta_t_reading", {"body": -1},
                                      "a delta_t_reading carries body -1"),
    "an_in_interval_flag_not_its_instant": (lambda r: r.get("epoch_id") == "outside_1500"
                                            and r.get("part") == "mode_invariance",
                                            {"in_supported_interval": True}, "is not that instant"),
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
    with pytest.raises(m.Refusal, match="292 children"):
        m.check(copy.deepcopy(emission["rows"]), context)


def test_a_dropped_nonut_is_refused(emission):
    """⭐ A nonut reading equal to its default twin, a nonut row that did not request the bit, or a reading with
    no twin under the other word, is refused."""
    m = _module()
    rows = copy.deepcopy(emission["rows"])
    twins = {(r["part"], r["entry_point"], r["configuration"], r["epoch_id"]): r for r in rows
             if r["finding"] == "nutation_obliquity_reading" and r["nutation"] == "default"}
    for row in rows:
        if row["finding"] == "nutation_obliquity_reading" and row["nutation"] == "nonut":
            twin = twins[(row["part"], row["entry_point"], row["configuration"], row["epoch_id"])]
            for key in ("values", "values_bits", "longitude", "longitude_bits", "latitude", "latitude_bits",
                        "distance", "distance_bits"):
                row[key] = copy.deepcopy(twin[key])
    with pytest.raises(m.Refusal, match="NONUT request moved nothing"):
        m.check(rows, _context(m, emission))
    rows = copy.deepcopy(emission["rows"])
    next(r for r in rows if r.get("nutation") == "nonut")["requested"] &= ~64
    with pytest.raises(m.Refusal, match="labelled nonut"):
        m.check(rows, _context(m, emission))
    rows = [r for r in copy.deepcopy(emission["rows"])
            if not (r["finding"] == "nutation_obliquity_reading" and r["nutation"] == "nonut"
                    and r["epoch_id"] == "j2000" and r["part"] == "mode_invariance")]
    context = _context(m, emission)
    context["children"] = len(rows)
    with pytest.raises(m.Refusal, match="has no twin under the other word"):
        m.check(rows, context)
