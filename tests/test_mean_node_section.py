"""The mean node's calc section and its controls: what the generator may import, where its rows come from,
the identity it names its configuration by, and every control it must keep at every row.

⛔ Each refusal is tested beside a twin that differs from it in one property and is accepted, so a check that
refuses everything cannot pass. The static half needs nothing but Python; the children need the binding; the
end-to-end run needs the pinned data files too, and each half that cannot run says so.
"""

from __future__ import annotations

import ast
import copy
import hashlib
import importlib.util
import json
import struct
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "generators" / "mean_node_section.py"
MODES_SCRIPT = ROOT / "generators" / "mean_node_modes.py"
EPHE = ROOT / "cache" / "ephe"

COVERAGE = 'declared_coverage = { start = "1849-12-26T00:00:00", end = "2150-01-22T00:00:00", scale = "TDB" }'

#: ⭐ The identity's three measured literals, pinned by the consumer for this configuration (entry point calc, the
#: data-file request, this library and binding, an explicit path holding the three pinned files, all four states
#: reset): without the word line, with ``word|66``, and with ``word|2`` — the control that must differ.
IDENTITY_WITHOUT_WORD = "48bc1649f160b1ac4ebd16188800806d2d9e7bbfae8314398c70e7158c2ebfe2"
IDENTITY_WORD_66 = "bb60c5b3cf3d84612253cc3a984ae799fdf2db9280b9b31136c815e47ccf5be7"
IDENTITY_WORD_2 = "c893013badb8338ed6de303033a6862f0a0564b357da1523f61d6c663bb22ac7"

#: ⭐ The section's values, its nutation twins and its witness readings, as `epoch|bits` lines — pinned so a
#: reading that moves one bit turns this red. ⚠ Host-bound (macOS arm64), as every pin of a reading here is; the
#: section's 76 values and twins were measured bit-identical to the mean-node record's own readings of them.
ROWS_DIGEST = "e740234c8ed2bef8c35e9a0aa6705e7c1fd9e6c8018f124af175ab448b791859"
TWINS_DIGEST = "004e32739fec7c79b0b8bc7680a5485dca5a802e7be0de588ce5e088c2e822de"
WITNESS_DIGEST = "9d4f6b6488c161a558914723f0449d302b3176f2bd0ab0e951357d7439c21a91"

#: The Moon's coverage edge as the survey measures it, as bits.
MOON_EDGE = ("414225803ff95413", "414225803ff95414", "4143d189ad337022", "4143d189ad337023")


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def m():
    return _load(SCRIPT, "mean_node_section")


def bits(x: float) -> str:
    return struct.pack(">d", x).hex()


def _manifest(directory: Path) -> Path:
    path = directory / "profile.v1.toml"
    path.write_text(f'[identity]\nname = "standard"\nversion = 1\n\n[[pinned.dataset]]\nlogical_id = "de440s"\n'
                    f'{COVERAGE}\n', encoding="utf-8")
    return path


# ---------------------------------------------------------------------------------------
# What it imports, and the tables it must keep equal to this repository's
# ---------------------------------------------------------------------------------------


def _imports(node) -> set[str]:
    roots = set()
    for n in ast.walk(node):
        if isinstance(n, ast.Import):
            roots.update(a.name.split(".")[0] for a in n.names)
        elif isinstance(n, ast.ImportFrom) and n.module:
            roots.add(n.module.split(".")[0])
    return roots


def test_a_child_loads_only_the_standard_library_and_the_binding():
    """⛔ The module's top level imports the standard library alone, the child the binding alone, and this
    repository's contract is loaded by the parent only — so a child starts without the library loaded."""
    tree = ast.parse(SCRIPT.read_text(encoding="utf-8"))
    top = set()
    for n in tree.body:
        if isinstance(n, (ast.Import, ast.ImportFrom)):
            top |= _imports(n)
    assert sorted(r for r in top if r not in sys.stdlib_module_names and r != "__future__") == []
    functions = {f.name: f for f in tree.body if isinstance(f, ast.FunctionDef)}
    assert _imports(functions["_child"]) == {"swisseph"}
    holders = sorted(name for name, f in functions.items() if "saakshi" in _imports(f))
    assert holders == ["_contract"]


def test_its_data_file_pins_are_this_repositorys(m):
    pytest.importorskip("swisseph", reason="the shared pin table lives in a module that imports the binding")
    sys.path.insert(0, str(ROOT / "src"))
    from saakshi.swiss import EPHE_PINS

    mine = {p["dataset"]: p for p in m.EPHE_PINS}
    assert set(mine) == set(EPHE_PINS)
    for name, pin in EPHE_PINS.items():
        assert (mine[name]["sha256"], mine[name]["size_bytes"], mine[name]["profile"]) == (
            pin.sha256, pin.size_bytes, pin.profile)


def test_its_states_are_exactly_the_ones_the_library_state_audit_measured(m):
    pytest.importorskip("swisseph", reason="the library-state audit lives in a module that imports the binding")
    sys.path.insert(0, str(ROOT / "src"))
    from saakshi.conventions import GLOBAL_STATE

    assert sorted(m.STATE_DISCIPLINE) == sorted(state.name for state in GLOBAL_STATE)


# ---------------------------------------------------------------------------------------
# The configuration identity
# ---------------------------------------------------------------------------------------


LIBRARY = ("2.10.03", "pyswisseph", "2.10.3.2")


@pytest.mark.parametrize("word,expected", [(None, IDENTITY_WITHOUT_WORD), (66, IDENTITY_WORD_66),
                                           (2, IDENTITY_WORD_2)])
def test_the_identity_renders_the_consumers_measured_literals(m, word, expected):
    got = m.configuration_identity(entry_point="calc", requested="swiss_file", word=word, library=LIBRARY,
                                   configuration=m.section_configuration())
    assert got == expected


def test_without_the_word_the_identity_is_the_shared_renderings_own(m):
    """⭐ The word line is the only addition: with it absent, the shared rendering's own pinned vectors."""
    pytest.importorskip("swisseph", reason="the shared rendering lives in a module that imports the binding")
    sys.path.insert(0, str(ROOT / "src"))
    from saakshi.conventions import configuration_sha256

    for requested in ("moshier", "swiss_file"):
        for state in ({"discipline": "reset"}, {"discipline": "declared", "value": "1"},
                      {"discipline": "declared", "value_bits": "3ff0000000000000"}):
            configuration = m.section_configuration()
            configuration["library_state"]["sidereal_mode"] = state
            assert m.configuration_identity(entry_point="deltat_ex", requested=requested, word=None,
                                            library=LIBRARY, configuration=configuration) == configuration_sha256(
                entry_point="deltat_ex", requested=requested, library_version=LIBRARY[0], binding=LIBRARY[1],
                binding_version=LIBRARY[2], configuration=configuration)


def test_a_field_that_would_forge_a_boundary_or_a_file_twice_is_refused(m):
    configuration = m.section_configuration()
    with pytest.raises(m.Refusal):
        m.configuration_identity(entry_point="calc|x", requested="swiss_file", word=66, library=LIBRARY,
                                 configuration=configuration)
    configuration["ephemeris_path"]["resolved_contents"].append(configuration["ephemeris_path"]["resolved_contents"][0])
    with pytest.raises(m.Refusal):
        m.configuration_identity(entry_point="calc", requested="swiss_file", word=66, library=LIBRARY,
                                 configuration=configuration)


# ---------------------------------------------------------------------------------------
# The rows: the manifest's interval, and the mean-node record's in-interval epochs
# ---------------------------------------------------------------------------------------


def test_the_rows_are_the_mean_node_records_in_interval_calc_epochs_bit_for_bit(m, tmp_path):
    modes = _load(MODES_SCRIPT, "mean_node_modes_for_epochs")
    manifest = str(_manifest(tmp_path))
    assert m.read_interval(manifest) == modes.read_interval(manifest)
    mine = [(e["epoch_id"], bits(e["jd"])) for e in m.build_epochs(m.read_interval(manifest))]
    theirs = sorted(((e["epoch_id"], bits(e["jd"])) for e in modes.build_epochs(modes.read_interval(manifest))
                     if e["in_supported_interval"]), key=lambda t: struct.unpack(">d", bytes.fromhex(t[1]))[0])
    assert mine == theirs and len(mine) == 76


def test_the_rows_follow_the_manifest_and_not_a_number_written_here(m, tmp_path):
    narrow = tmp_path / "narrow"
    narrow.mkdir()
    path = narrow / "profile.v1.toml"
    path.write_text('[identity]\nname = "standard"\nversion = 1\n\n[[pinned.dataset]]\nlogical_id = "x"\n'
                    'declared_coverage = { start = "1990-01-01T00:00:00", end = "2010-01-01T00:00:00", scale = "TDB" }\n',
                    encoding="utf-8")
    interval = m.read_interval(str(path))
    epochs = m.build_epochs(interval)
    assert all(interval["start"] <= e["jd"] <= interval["end"] for e in epochs)
    assert len(epochs) < 76


# ---------------------------------------------------------------------------------------
# The survey's edge
# ---------------------------------------------------------------------------------------


def _survey(tmp_path: Path, rows: list[dict]) -> Path:
    path = tmp_path / "survey.jsonl"
    path.write_text("\n".join([json.dumps({"record": "header"}), *map(json.dumps, rows)]) + "\n", encoding="utf-8")
    return path


def _edge_row(body: int, ends=MOON_EDGE) -> dict:
    return {"finding": "coverage_edge", "body": body,
            **{f"{end}_bits": b for end, b in zip(("lower_edge_last_outside_jd_ut", "lower_edge_first_inside_jd_ut",
                                                   "upper_edge_first_inside_jd_ut", "upper_edge_last_outside_jd_ut"),
                                                  ends)}}


def test_the_survey_is_read_by_its_bits_one_row_per_body(m, tmp_path):
    read = m.read_survey_edges(str(_survey(tmp_path, [_edge_row(1)])))
    assert [bits(x) for x in read["edges"][1]] == list(MOON_EDGE)
    with pytest.raises(m.Refusal):
        m.read_survey_edges(str(_survey(tmp_path, [_edge_row(1), _edge_row(1)])))
    partial = _edge_row(1)
    del partial["upper_edge_last_outside_jd_ut_bits"]
    with pytest.raises(m.Refusal):
        m.read_survey_edges(str(_survey(tmp_path, [partial])))


# ---------------------------------------------------------------------------------------
# The controls, at every row — on a synthetic measurement, each refusal beside its twin
# ---------------------------------------------------------------------------------------

FLAG = {"moshier": 4, "swiss_file": 2, "jpl_file": 1}
NAMES = {10: "mean Node", 1: "Moon"}


def _reading(m, control, configuration, body, epoch, value, *, role=None, nonut=True):
    eph, state = {n: (e, s) for n, e, s in m.CONFIGURATIONS}[configuration]
    requested = FLAG[eph] | (64 if nonut else 0)
    if body == 1:
        returned = {"moshier_files_present": 68, "moshier_dir_empty": 68, "swiss_file_present": 66,
                    "swiss_file_dir_empty": 68, "jpl_requested_no_jpl_file": 66}[configuration]
    else:
        returned = requested
    row = {"finding": "configuration_control", "control": control, "entry_point": "calc",
           "configuration": configuration, "epoch_id": epoch["epoch_id"], "body": body, "body_name": NAMES[body],
           "jd": epoch["jd"], "jd_bits": bits(epoch["jd"]), "requested": requested, "returned": returned,
           "ephemeris_requested": eph, "nutation": "nonut" if nonut else "default", "path_state": state}
    for key, v in (("longitude", value), ("latitude", 0.0), ("distance", 0.00257), ("tidal_constant_after", -25.936)):
        row[key], row[f"{key}_bits"] = v, bits(v)
    row["call_history"] = "cold_process_per_row"
    if role:
        row["role"] = role
    return row


def _conforming(m, n=3):
    epochs = [{"epoch_id": f"e{i}", "jd": 120.0 + i} for i in range(n)]
    rows = [{"section": "mean_node", "epoch_id": e["epoch_id"], "body": 10,
             "instant": {"scale": "tt", "jd": e["jd"], "jd_bits": bits(e["jd"])},
             "values": [10.0 + i], "values_bits": [bits(10.0 + i)],
             "state_read_back": {"state": "tidal_acceleration", "value": -25.936, "value_bits": bits(-25.936)},
             "source_assertion": {"kind": "none", "reason": "request_invariant"}} for i, e in enumerate(epochs)]
    controls = []
    for i, e in enumerate(epochs):
        for name, eph, _state in m.CONFIGURATIONS:
            controls.append(_reading(m, "invariance", name, 10, e, 10.0 + i, role="subject"))
        for name, eph, _state in m.CONFIGURATIONS:
            moon = 50.5 + i if eph != "moshier" and name != "swiss_file_dir_empty" else 50.0 + i
            controls.append(_reading(m, "invariance", name, 1, e, moon, role="witness"))
        controls.append(_reading(m, "nutation_twin", "swiss_file_present", 10, e, 11.0 + i, nonut=False))
    order = [e["epoch_id"] for e in reversed(epochs)]
    for i, e in enumerate(epochs):
        controls.append({"finding": "configuration_control", "control": "sufficiency", "entry_point": "calc",
                         "epoch_id": e["epoch_id"], "call_history": "permuted", "call_order": order,
                         "values": [10.0 + i], "values_bits": [bits(10.0 + i)]})
    readings = [c for c in controls if c["control"] != "sufficiency"]
    context = {"interval": {"start": 100.0, "end": 200.0}, "epochs": epochs, "flag": FLAG, "nonut": 64, "word": 66,
               "children": len(readings) + 2, "section_returned": [66] * n, "subject": 10, "witness": 1,
               "body_names": NAMES, "library_version": "2.10.03"}
    survey = {"sha256": "0" * 64, "edges": {1: (50.0, 50.0 + 1e-9, 300.0, 300.0 + 1e-9)}}
    return rows, controls, context, survey


def _find(controls, **match):
    return [c for c in controls if all(c.get(k) == v for k, v in match.items())]


def _set_value(row, key, value):
    row[key], row[f"{key}_bits"] = value, bits(value)


def test_the_synthetic_twin_passes_every_control(m):
    summary = m.check(*_conforming(m))
    assert summary["invariance"]["largest_difference_arcseconds"] == 0.0
    assert summary["sufficiency"]["identical_to_their_row"] == 3


def _mutations():
    """(name, mutation, the refusal's words) — each one property of the conforming twin changed."""

    def subject_bit(rows, controls, context, survey):
        _set_value(_find(controls, role="subject", epoch_id="e1", configuration="jpl_requested_no_jpl_file")[0],
                   "longitude", 11.000000000000002)

    def missing_configuration(rows, controls, context, survey):
        victim = _find(controls, role="subject", epoch_id="e2", configuration="moshier_dir_empty")[0]
        controls.remove(victim)
        context["children"] -= 1

    def witness_echo(rows, controls, context, survey):
        _find(controls, role="witness", epoch_id="e0", configuration="swiss_file_dir_empty")[0]["returned"] = 66

    def witness_not_differing(rows, controls, context, survey):
        for c in _find(controls, role="witness", epoch_id="e1"):
            _set_value(c, "longitude", 51.5)

    def c_not_honoured(rows, controls, context, survey):
        _find(controls, role="witness", epoch_id="e2", configuration="swiss_file_present")[0]["returned"] = 68

    def row_outside(rows, controls, context, survey):
        context["interval"]["end"] = 121.5

    def sufficiency_differs(rows, controls, context, survey):
        c = _find(controls, control="sufficiency", epoch_id="e1")[0]
        c["values"], c["values_bits"] = [11.5], [bits(11.5)]

    def same_order(rows, controls, context, survey):
        for c in _find(controls, control="sufficiency"):
            c["call_order"] = [r["epoch_id"] for r in rows]

    def twin_equal(rows, controls, context, survey):
        _set_value(_find(controls, control="nutation_twin", epoch_id="e0")[0], "longitude", 10.0)

    def read_back_differs(rows, controls, context, survey):
        rows[1]["state_read_back"]["value_bits"] = bits(-25.8)

    def section_word(rows, controls, context, survey):
        context["section_returned"][1] = 2

    def another_epochs_instant(rows, controls, context, survey):
        c = _find(controls, role="subject", epoch_id="e1", configuration="moshier_files_present")[0]
        c["jd"], c["jd_bits"] = 122.0, bits(122.0)

    def a_foreign_epoch(rows, controls, context, survey):
        _find(controls, role="witness", epoch_id="e2", configuration="moshier_dir_empty")[0]["epoch_id"] = "e9"

    def nutation_label(rows, controls, context, survey):
        _find(controls, role="subject", epoch_id="e0", configuration="swiss_file_present")[0]["nutation"] = "default"

    def configuration_name(rows, controls, context, survey):
        _find(controls, role="subject", epoch_id="e0", configuration="moshier_files_present")[0]["path_state"] = \
            "empty_directory"

    def body_name(rows, controls, context, survey):
        _find(controls, role="witness", epoch_id="e1", configuration="moshier_files_present")[0]["body_name"] = "Sun"

    def unrequested_word(rows, controls, context, survey):
        _find(controls, control="nutation_twin", epoch_id="e1")[0]["returned"] = 4

    def witness_near_its_edge(rows, controls, context, survey):
        survey["edges"][1] = (119.5, 119.5 + 1e-9, 300.0, 300.0 + 1e-9)

    def node_has_an_edge(rows, controls, context, survey):
        survey["edges"][10] = (1.0, 2.0, 3.0, 4.0)

    def no_witness_edge(rows, controls, context, survey):
        del survey["edges"][1]

    def children_count(rows, controls, context, survey):
        context["children"] += 1

    def rows_out_of_order(rows, controls, context, survey):
        rows[0], rows[1] = rows[1], rows[0]

    return [
        ("① (a): a subject one bit away", subject_bit, "① (a) fails"),
        ("①: a configuration missing at a row", missing_configuration, "not one at each"),
        ("① (b) ⑴: the witness echoing where its source is absent", witness_echo, "① (b) ⑴"),
        ("① (b) ⑵: the witness not differing between two sources", witness_not_differing, "① (b) ⑵"),
        ("① (b) ⑶: C not honoured for the witness", c_not_honoured, "① (b) ⑶"),
        ("① (c): a row outside the interval", row_outside, "① (c)"),
        ("②: the regeneration differing", sufficiency_differs, "② fails"),
        ("②: a same-order regeneration", same_order, "order is the section's own"),
        ("③: a twin equal to its row", twin_equal, "③ fails"),
        ("a second read-back value", read_back_differs, "read back"),
        ("a section word other than the request", section_word, "returned words"),
        ("G-S1: a reading at another epoch's instant", another_epochs_instant, "not that part's instant"),
        ("G-S1: a reading at an epoch not the section's", a_foreign_epoch, "not that part's instant"),
        ("a nutation label not its word's", nutation_label, "is not what it names"),
        ("a configuration not its table's", configuration_name, "is not what it names"),
        ("a body name not its body's", body_name, "is not what it names"),
        ("a returned word no reading requested", unrequested_word, "no reading here"),
        ("a witness read within a day of its edge", witness_near_its_edge, "days inside the witness's edge"),
        ("an edge row for the node", node_has_an_edge, "one for the node"),
        ("no edge for the witness", no_witness_edge, "no edge for the witness"),
        ("a reading count other than the children's", children_count, "children"),
        ("the rows out of their order", rows_out_of_order, "not its epochs in order"),
    ]


@pytest.mark.parametrize("name,mutation,words", _mutations(), ids=[n for n, _, _ in _mutations()])
def test_each_control_refuses_its_failure_and_the_twin_passes(m, name, mutation, words):
    case = copy.deepcopy(_conforming(m))
    mutation(*case)
    with pytest.raises(m.Refusal) as excinfo:
        m.check(*case)
    assert words in str(excinfo.value), str(excinfo.value)
    m.check(*_conforming(m))


# ---------------------------------------------------------------------------------------
# The children — one fresh interpreter each, admitted only if it made exactly its calls
# ---------------------------------------------------------------------------------------


def _planted(tmp_path: Path, anchor: str, replacement: str):
    source = SCRIPT.read_text(encoding="utf-8")
    assert source.count(anchor) == 1, anchor
    path = tmp_path / "planted_section.py"
    path.write_text(source.replace(anchor, replacement), encoding="utf-8")
    return _load(path, f"planted_{abs(hash(anchor))}")


def _spec(tmp_path: Path, jds=(2451545.0,)) -> dict:
    return {"path": str(tmp_path), "body": 10, "word": 66, "jd_bits": [bits(j) for j in jds]}


def test_a_child_is_one_fresh_interpreter_making_exactly_its_calls(m, tmp_path):
    pytest.importorskip("swisseph", reason="the children call the ephemeris library")
    readings = m.Children(str(tmp_path)).run(_spec(tmp_path, jds=(2451545.0, 2451546.0)))
    assert len(readings) == 2 and {r["returned"] for r in readings} == {66}


@pytest.mark.parametrize("anchor,replacement", [
    ('values, returned = swe.calc(unbits(jd_bits), spec["body"], spec["word"])',
     'values, returned = swe.calc(unbits(jd_bits), spec["body"], spec["word"] & 7)'),
    ('    swe.set_ephe_path(spec["path"])\n', '    swe.set_ephe_path(spec["path"])\n    swe.get_tid_acc()\n'),
    ('    fresh = "swisseph" not in sys.modules\n', '    import swisseph\n    fresh = "swisseph" not in sys.modules\n'),
    ('    sys.stdout.write(json.dumps({"nonce"', '    readings.append(readings[-1])\n    sys.stdout.write(json.dumps({"nonce"'),
], ids=["a word changed at the call", "a call the row does not declare", "a warm interpreter", "a reading too many"])
def test_a_child_that_did_other_than_its_spec_declares_is_refused(tmp_path, anchor, replacement):
    pytest.importorskip("swisseph", reason="the children call the ephemeris library")
    planted = _planted(tmp_path, anchor, replacement)
    work = tmp_path / "work"
    work.mkdir()
    with pytest.raises(planted.Refusal):
        planted.Children(str(work)).run(_spec(work))


def test_one_childs_output_returned_twice_is_refused(m, tmp_path, monkeypatch):
    out = json.dumps({"nonce": "same", "fresh_interpreter": True, "calls": m.declared_calls(_spec(tmp_path)),
                      "readings": [{}]})
    monkeypatch.setattr(m.subprocess, "run", lambda *a, **k: subprocess.CompletedProcess(a, 0, out, ""))
    children = m.Children(str(tmp_path))
    children.run(_spec(tmp_path))
    with pytest.raises(m.Refusal):
        children.run(_spec(tmp_path))


# ---------------------------------------------------------------------------------------
# End to end, from a commit of its own, on the pinned data files
# ---------------------------------------------------------------------------------------


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True, check=True).stdout


@pytest.fixture(scope="module")
def emission(tmp_path_factory):
    pytest.importorskip("swisseph", reason="the generator calls the ephemeris library")
    if not all((EPHE / p).is_file() for p in ("seas_18.se1", "semo_18.se1", "sepl_18.se1")):
        pytest.skip("the pinned data files are not in cache/ephe; the end-to-end run cannot happen")
    base = tmp_path_factory.mktemp("emission")
    repo = base / "repo"
    (repo / "generators").mkdir(parents=True)
    (repo / "generators" / "mean_node_section.py").write_text(SCRIPT.read_text(encoding="utf-8"), encoding="utf-8")
    shutil_copy = __import__("shutil").copytree
    shutil_copy(ROOT / "src", repo / "src", ignore=__import__("shutil").ignore_patterns("__pycache__"))
    _git(repo, "init", "-q")
    _git(repo, "add", "-A")
    _git(repo, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", "t")
    empty = base / "empty"
    empty.mkdir()
    out = base / "out"
    survey = _survey(base, [_edge_row(1)])
    proc = subprocess.run([sys.executable, "-B", str(repo / "generators" / "mean_node_section.py"),
                           "--ephe-path", str(EPHE), "--empty-dir", str(empty), "--profile", str(_manifest(base)),
                           "--survey", str(survey), "--out-dir", str(out)],
                          capture_output=True, text=True, timeout=1800)
    assert proc.returncode == 0, proc.stderr[-2000:]
    read = lambda name: [json.loads(line) for line in (out / name).read_text(encoding="utf-8").splitlines()]
    return {"section": read("mean-node-section.jsonl"), "controls": read("mean-node-section-controls.jsonl"),
            "stderr": proc.stderr, "out": out, "commit": _git(repo, "rev-parse", "HEAD").strip()}


def _digest(lines: str) -> str:
    return hashlib.sha256(lines.encode()).hexdigest()


def test_it_writes_the_section_and_its_controls_naming_one_commit_one_host_one_identity(emission):
    section, controls = emission["section"], emission["controls"]
    header, control_header = section[0], controls[0]
    assert header["fixture_kind"] == "numeric_pin" and control_header["fixture_kind"] == "provenance_record"
    assert header["generator"]["commit"] == control_header["generator"]["commit"] == emission["commit"]
    assert header["oracle"]["host"] == control_header["oracle"]["host"]
    basis = header["oracle"]["ephemeris_basis"]["sections"]["mean_node"]
    assert (basis["entry_point"], basis["requested"], basis["returned"], basis["requested_word"],
            basis["claimed_class"], basis["generation"]) == ("calc", "swiss_file", "swiss_file", 66,
                                                             "request_invariant", "warm_in_row_order")
    assert {c["configuration_sha256"] for c in controls[1:]} == {IDENTITY_WORD_66}
    assert header["classification"] == {"mean_node": {"class": "tolerance", "band": 0.0, "unit": "degree"}}
    assert {r["source_assertion"]["kind"] for r in section[1:]} == {"none"}


def test_its_readings_are_the_pinned_ones(emission):
    rows = "".join(f"{r['epoch_id']}|{r['values_bits'][0]}\n" for r in emission["section"][1:])
    controls = emission["controls"][1:]
    twins = "".join(f"{c['epoch_id']}|{c['longitude_bits']}\n" for c in controls if c["control"] == "nutation_twin")
    witness = "".join(f"{c['epoch_id']}|{c['configuration']}|{c['returned']}|{c['longitude_bits']}\n"
                      for c in controls if c.get("role") == "witness")
    assert (_digest(rows), _digest(twins), _digest(witness)) == (ROWS_DIGEST, TWINS_DIGEST, WITNESS_DIGEST)


def test_a_second_emission_into_the_same_place_is_refused(emission):
    sys.path.insert(0, str(ROOT / "src"))
    m = _load(SCRIPT, "mean_node_section_again")
    with pytest.raises(m.Refusal):
        m.write_files([], [], {"interval": {}, "epochs": [], "word": 66, "library_version": "x"}, {},
                      str(emission["out"]))
