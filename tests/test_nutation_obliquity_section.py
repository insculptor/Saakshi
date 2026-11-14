"""The nutation and obliquity pseudo-body's calc section and its controls: what it takes from the mean node's
section by import, the identity and band it names, every value it carries, and every control it must keep at every
row.

⛔ Each refusal is tested beside a twin that differs from it in one property and is accepted, so a check that
refuses everything cannot pass. The static half needs nothing but Python; the identity, the children and the
end-to-end run need the binding; the end-to-end run needs the pinned data files too, and each half that cannot run
says so.
"""

from __future__ import annotations

import ast
import copy
import hashlib
import importlib.util
import json
import shutil
import struct
import subprocess
import sys
from fractions import Fraction
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "generators" / "nutation_obliquity_section.py"
NODE_SCRIPT = ROOT / "generators" / "mean_node_section.py"
EPHE = ROOT / "cache" / "ephe"

COVERAGE = 'declared_coverage = { start = "1849-12-26T00:00:00", end = "2150-01-22T00:00:00", scale = "TDB" }'

#: ⭐ The identity its consumer names this configuration by: calc, the data-file request, word 2, this library and
#: binding, an explicit path holding the three pinned files, all four states reset.
IDENTITY_WORD_2 = "c893013badb8338ed6de303033a6862f0a0564b357da1523f61d6c663bb22ac7"
LIBRARY = ("2.10.03", "pyswisseph", "2.10.3.2")

#: ⭐ The section's six returned values per row, its twins' six and its witness readings, as lines — pinned so a
#: reading that moves one bit turns this red. ⚠ Host-bound (macOS arm64), as every pin of a reading here is.
ROWS_DIGEST = "7da3ffb625a99e7d871b1ee50ca6a451c13fc470f6fc0ddc617d72e5882fdb02"
TWINS_DIGEST = "acb011b932715aa3f1cb7d6129b4dab6baae90af4819b9b5b1785227902d4e3d"
WITNESS_DIGEST = "9809de760c62670c754f0a4fc13e8b326fd554d1c092d3de8b787bdd0069e476"

MOON_EDGE = ("414225803ff95413", "414225803ff95414", "4143d189ad337022", "4143d189ad337023")


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def m():
    return _load(SCRIPT, "nutation_obliquity_section")


def bits(x: float) -> str:
    return struct.pack(">d", x).hex()


def _manifest(directory: Path) -> Path:
    path = directory / "profile.v1.toml"
    path.write_text(f'[identity]\nname = "standard"\nversion = 1\n\n[[pinned.dataset]]\nlogical_id = "de440s"\n'
                    f'{COVERAGE}\n', encoding="utf-8")
    return path


# ---------------------------------------------------------------------------------------
# What it imports, and what it takes from the mean node's section rather than writing again
# ---------------------------------------------------------------------------------------


def _imports(node) -> set[str]:
    roots = set()
    for n in ast.walk(node):
        if isinstance(n, ast.Import):
            roots.update(a.name.split(".")[0] for a in n.names)
        elif isinstance(n, ast.ImportFrom) and n.module:
            roots.add(n.module.split(".")[0])
    return roots


def test_it_imports_the_standard_library_and_the_mean_node_section_alone():
    """⛔ Its top level imports the standard library and its sibling; the binding only inside the measurement, this
    repository's contract only inside the identity and the writer's contract loader."""
    tree = ast.parse(SCRIPT.read_text(encoding="utf-8"))
    top = set()
    for n in tree.body:
        if isinstance(n, (ast.Import, ast.ImportFrom)):
            top |= _imports(n)
    assert sorted(r for r in top if r not in sys.stdlib_module_names and r != "__future__") == ["mean_node_section"]
    functions = {f.name: f for f in tree.body if isinstance(f, ast.FunctionDef)}
    assert sorted(name for name, f in functions.items() if "swisseph" in _imports(f)) == ["measure"]
    assert sorted(name for name, f in functions.items() if "saakshi" in _imports(f)) == ["section_identity"]


def test_it_writes_no_child_epochs_directories_or_renderer_of_its_own():
    """⭐ By import, ⛔ never by copy: the child program, the admission rule, the epochs, the directory checks, the
    survey's edge, the identity's renderer and the shared controls are the mean node's section's."""
    tree = ast.parse(SCRIPT.read_text(encoding="utf-8"))
    defined = {n.name for n in tree.body if isinstance(n, (ast.FunctionDef, ast.ClassDef))}
    for name in ("_child", "Children", "declared_calls", "build_epochs", "read_interval", "verify_data_directory",
                 "verify_empty_directory", "read_survey_edges", "configuration_identity", "section_configuration",
                 "held", "witness_at_every_row", "inside_the_interval", "one_read_back", "witness_edge"):
        assert name not in defined, name
    source = SCRIPT.read_text(encoding="utf-8")
    for used in ("node.Children(", "node.build_epochs(", "node.read_interval(", "node.held(",
                 "node.witness_at_every_row(", "node.inside_the_interval(", "node.one_read_back(",
                 "node.witness_edge(", "node.configuration_identity(", "node.section_configuration()"):
        assert used in source, used


def test_importing_it_writes_no_bytecode_beside_its_sibling(tmp_path):
    """⛔ An untracked file is a dirty tree: importing the sibling must leave the generators directory as it was."""
    work = tmp_path / "generators"
    work.mkdir()
    for path in (SCRIPT, NODE_SCRIPT):
        shutil.copy(path, work / path.name)
    proc = subprocess.run([sys.executable, str(work / "nutation_obliquity_section.py"), "--help"],
                          capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
    assert sorted(p.name for p in work.iterdir()) == ["mean_node_section.py", "nutation_obliquity_section.py"]


# ---------------------------------------------------------------------------------------
# The identity, and the band
# ---------------------------------------------------------------------------------------


def _independent_rendering(word: int, library=LIBRARY) -> str:
    """⭐ The identity rendered here by hand, line by line, from the consumer's rendering: no code of the generator."""
    pins = sorted([("seas_18.se1", "a2cd8fc33807c78ca9a700c91c2e042258b12fc4796519e00781440b5ad8b2e2"),
                   ("semo_18.se1", "1ca07bd67c24374d77226180c20a4f9996cba013697894810518e7eb582ca4f7"),
                   ("sepl_18.se1", "ca1393ceab3a44fbc895887cf789c68819ae6a1cbc9b22225872dbe4ccd99a66")])
    lines = ["configuration|1", "entry_point|calc", "requested|swiss_file", f"word|{word}",
             "library|" + "|".join(library), "path|explicit", *(f"file|{d}|{s}" for d, s in pins),
             *(f"state|{n}|reset" for n in sorted(["leap_second_table", "sidereal_mode", "tidal_acceleration",
                                                    "user_defined_delta_t"]))]
    return hashlib.sha256("".join(line + "\n" for line in lines).encode("utf-8")).hexdigest()


def test_an_independent_rendering_gives_the_pinned_identity(m):
    assert _independent_rendering(2) == IDENTITY_WORD_2 == m.CONFIGURATION_IDENTITY


def test_the_section_identity_is_the_pinned_one_and_anything_else_is_refused(m):
    pytest.importorskip("swisseph", reason="the shared rendering lives in a module that imports the binding")
    assert m.section_identity(LIBRARY, 2) == IDENTITY_WORD_2
    for word, library in ((66, LIBRARY), (4, LIBRARY), (2, ("2.10.04", "pyswisseph", "2.10.3.2"))):
        with pytest.raises(m.Refusal) as excinfo:
            m.section_identity(library, word)
        assert "not the pinned" in str(excinfo.value)
        assert _independent_rendering(word, library) in str(excinfo.value)


def test_two_renderers_that_disagree_before_the_word_line_are_refused(m, monkeypatch):
    """⛔ The section's renderer is held to the shared one on every line but the word's, before the literal is: a
    renderer that drifted on any other line is refused even where its own rendering with the word still matched."""
    pytest.importorskip("swisseph", reason="the shared rendering lives in a module that imports the binding")
    real = m.node.configuration_identity

    def drifted(**keywords):
        return real(**keywords) if keywords["word"] is not None else "0" * 64

    assert m.section_identity(LIBRARY, 2) == IDENTITY_WORD_2
    monkeypatch.setattr(m.node, "configuration_identity", drifted)
    with pytest.raises(m.Refusal) as excinfo:
        m.section_identity(LIBRARY, 2)
    assert "disagree before the word line" in str(excinfo.value)


def test_the_declared_band_is_its_consumers_converted_once(m):
    """⭐ 0.05 arcsecond is 1/72000 degree exactly; the band is that ratio's nearest double, the consumer's bits."""
    assert bits(m.CONSUMER_BAND_DEGREES) == "3eed208a5a912e32"
    below, above = (struct.unpack(">d", struct.pack(">q", struct.unpack(">q", struct.pack(">d", m.CONSUMER_BAND_DEGREES))[0]
                                                   + step))[0] for step in (-1, 1))
    exact = Fraction(1, 72000)
    assert abs(Fraction(m.CONSUMER_BAND_DEGREES) - exact) <= min(abs(Fraction(below) - exact),
                                                                 abs(Fraction(above) - exact))


def test_it_shares_the_mean_node_sections_unit_configurations_and_pins(m):
    node = _load(NODE_SCRIPT, "mean_node_section_for_shape")
    assert (m.SECTION_UNIT, m.CONFIGURATIONS, m.SECTION_CONFIGURATION, m.ENTRY_POINT) == (
        node.SECTION_UNIT, node.CONFIGURATIONS, node.SECTION_CONFIGURATION, node.ENTRY_POINT)
    assert m.SECTION_UNIT == "degree" and m.SECTION == "true_obliquity"


# ---------------------------------------------------------------------------------------
# A child's readings: every returned value, the named three first
# ---------------------------------------------------------------------------------------


def _child_reading(values):
    return {"longitude_bits": values[0], "latitude_bits": values[1], "distance_bits": values[2],
            "values_bits": list(values)}


def test_a_reading_carries_every_returned_value_the_named_three_first(m):
    six = [bits(float(i)) for i in range(6)]
    assert m.every_value(_child_reading(six)) == six
    for broken in (_child_reading(six[:5]), {**_child_reading(six), "values_bits": six + [six[0]]},
                   {**_child_reading(six), "latitude_bits": six[3]}, {k: v for k, v in _child_reading(six).items()
                                                                       if k != "values_bits"}):
        with pytest.raises(m.Refusal):
            m.every_value(broken)


def test_the_mean_node_sections_child_hands_back_every_value_the_call_returned(tmp_path):
    pytest.importorskip("swisseph", reason="the children call the ephemeris library")
    import swisseph as swe

    node = _load(NODE_SCRIPT, "mean_node_section_for_child")
    readings = node.Children(str(tmp_path)).run({"path": str(tmp_path), "body": swe.ECL_NUT, "word": 2,
                                                 "jd_bits": [bits(2451545.0)]})
    values, returned = swe.calc(2451545.0, swe.ECL_NUT, 2)
    assert readings[0]["values_bits"] == [bits(float(v)) for v in values] and len(values) == 6
    assert readings[0]["values_bits"][:3] == [readings[0][k] for k in ("longitude_bits", "latitude_bits",
                                                                       "distance_bits")]


# ---------------------------------------------------------------------------------------
# The controls, at every row — on a synthetic measurement, each refusal beside its twin
# ---------------------------------------------------------------------------------------

FLAG = {"moshier": 4, "swiss_file": 2, "jpl_file": 1}
NONUT = 64
SUBJECT, WITNESS = -1, 1
NAMES = {SUBJECT: "", WITNESS: "Moon"}


def _six(i: int, *, nonut: bool = False) -> list[float]:
    mean, d_psi, d_eps = 23.44 + 0.001 * i, -0.004 + 0.0001 * i, 0.002 + 0.0001 * i
    return [mean, mean, 0.0, 0.0, 0.0, 0.0] if nonut else [mean + d_eps, mean, d_psi, d_eps, 0.0, 0.0]


def _reading(m, control, configuration, body, epoch, *, i, role=None, nonut=False):
    eph, state = {n: (e, s) for n, e, s in m.CONFIGURATIONS}[configuration]
    requested = FLAG[eph] | (NONUT if nonut else 0)
    if body == WITNESS:
        returned = {"moshier_files_present": 4, "moshier_dir_empty": 4, "swiss_file_present": 2,
                    "swiss_file_dir_empty": 4, "jpl_requested_no_jpl_file": 2}[configuration]
        values = [50.5 + i if returned == 2 else 50.0 + i, 0.1, 0.00257]
    else:
        returned, values = requested, _six(i, nonut=nonut)
    row = {"finding": "configuration_control", "control": control, "entry_point": "calc",
           "configuration": configuration, "epoch_id": epoch["epoch_id"], "body": body, "body_name": NAMES[body],
           "jd": epoch["jd"], "jd_bits": bits(epoch["jd"]), "requested": requested, "returned": returned,
           "ephemeris_requested": eph, "nutation": "nonut" if nonut else "default", "path_state": state}
    for key, v in zip(("longitude", "latitude", "distance"), values):
        row[key], row[f"{key}_bits"] = v, bits(v)
    row["tidal_constant_after"], row["tidal_constant_after_bits"] = -25.936, bits(-25.936)
    if body == SUBJECT:
        row["values"], row["values_bits"] = values, [bits(v) for v in values]
    row["call_history"] = "cold_process_per_row"
    if role:
        row["role"] = role
    return row


def _conforming(m, n=3):
    epochs = [{"epoch_id": f"e{i}", "jd": 120.0 + i} for i in range(n)]
    rows = []
    for i, e in enumerate(epochs):
        six = _six(i)
        rows.append({"section": "true_obliquity", "epoch_id": e["epoch_id"], "body": SUBJECT,
                     "instant": {"scale": "tt", "jd": e["jd"], "jd_bits": bits(e["jd"])}, "unit": "degree",
                     "values": [six[0]], "values_bits": [bits(six[0])],
                     "returned_values": {"values": six, "values_bits": [bits(v) for v in six]},
                     "state_read_back": {"state": "tidal_acceleration", "value": -25.936, "value_bits": bits(-25.936)},
                     "source_assertion": {"kind": "none", "reason": "request_invariant"}})
    controls = []
    for i, e in enumerate(epochs):
        for name, _eph, _state in m.CONFIGURATIONS:
            controls.append(_reading(m, "invariance", name, SUBJECT, e, i=i, role="subject"))
        for name, _eph, _state in m.CONFIGURATIONS:
            controls.append(_reading(m, "invariance", name, WITNESS, e, i=i, role="witness"))
        controls.append(_reading(m, "nutation_twin", "swiss_file_present", SUBJECT, e, i=i, nonut=True))
    order = [e["epoch_id"] for e in reversed(epochs)]
    for i, e in enumerate(epochs):
        six = _six(i)
        controls.append({"finding": "configuration_control", "control": "sufficiency", "entry_point": "calc",
                         "epoch_id": e["epoch_id"], "call_history": "permuted", "call_order": order,
                         "values": six, "values_bits": [bits(v) for v in six],
                         "tidal_constant_after": -25.936, "tidal_constant_after_bits": bits(-25.936)})
    readings = [c for c in controls if c["control"] != "sufficiency"]
    context = {"interval": {"start": 100.0, "end": 200.0}, "epochs": epochs, "flag": FLAG, "nonut": NONUT, "word": 2,
               "children": len(readings) + 2, "section_returned": [2] * n, "subject": SUBJECT, "witness": WITNESS,
               "body_names": NAMES, "library_version": "2.10.03"}
    survey = {"sha256": "0" * 64, "edges": {WITNESS: (50.0, 50.0 + 1e-9, 300.0, 300.0 + 1e-9)}}
    return rows, controls, context, survey


def _find(controls, **match):
    return [c for c in controls if all(c.get(k) == v for k, v in match.items())]


def _next_double(x: float) -> float:
    return struct.unpack(">d", struct.pack(">q", struct.unpack(">q", struct.pack(">d", x))[0] + 1))[0]


def _move(row, position):
    """One double away at one returned position, every field naming that position moved with it."""
    values = list(row["values"])
    values[position] = _next_double(values[position]) if values[position] != 0.0 else 5e-324
    row["values"], row["values_bits"] = values, [bits(v) for v in values]
    for key, p in (("longitude", 0), ("latitude", 1), ("distance", 2)):
        if key in row:
            row[key], row[f"{key}_bits"] = values[p], bits(values[p])


def test_the_synthetic_twin_passes_every_control(m):
    summary = m.check(*_conforming(m))
    assert summary["invariance"]["differing_from_their_row_at_any_position"] == 0
    assert summary["sufficiency"]["identical_to_their_row_at_every_position"] == 3
    assert summary["nutation_twin"]["first_value_differs_from_the_rows_first"] == 3


def _mutations():
    """(name, mutation, the refusal's words) — each one property of the conforming twin changed."""
    out = []
    for p in range(6):
        def subject_at(rows, controls, context, survey, p=p):
            _move(_find(controls, role="subject", epoch_id="e1", configuration="moshier_dir_empty")[0], p)
        out.append((f"① (a): a subject one double away at position {p} alone", subject_at, "① (a) fails"))

        def sufficiency_at(rows, controls, context, survey, p=p):
            _move(_find(controls, control="sufficiency", epoch_id="e2")[0], p)
        out.append((f"②: the regeneration one double away at position {p} alone", sufficiency_at, "② fails"))

    def twin_equal(rows, controls, context, survey):
        twin = _find(controls, control="nutation_twin", epoch_id="e0")[0]
        six = list(rows[0]["returned_values"]["values"])
        twin["values"], twin["values_bits"] = six, [bits(v) for v in six]
        for key, p in (("longitude", 0), ("latitude", 1), ("distance", 2)):
            twin[key], twin[f"{key}_bits"] = six[p], bits(six[p])

    def twin_not_its_own_second(rows, controls, context, survey):
        twin = _find(controls, control="nutation_twin", epoch_id="e1")[0]
        values = list(twin["values"])
        values[1] = _next_double(values[1])
        twin["values"], twin["values_bits"] = values, [bits(v) for v in values]
        twin["latitude"], twin["latitude_bits"] = values[1], bits(values[1])

    def twin_not_the_rows_second(rows, controls, context, survey):
        twin = _find(controls, control="nutation_twin", epoch_id="e2")[0]
        values = [_next_double(twin["values"][0])] * 2 + list(twin["values"][2:])
        twin["values"], twin["values_bits"] = values, [bits(v) for v in values]
        for key, p in (("longitude", 0), ("latitude", 1)):
            twin[key], twin[f"{key}_bits"] = values[p], bits(values[p])

    def twin_labelled_default(rows, controls, context, survey):
        twin = _find(controls, control="nutation_twin", epoch_id="e0")[0]
        twin["requested"], twin["returned"], twin["nutation"] = 2, 2, "default"

    def subject_under_nonut(rows, controls, context, survey):
        r = _find(controls, role="subject", epoch_id="e1", configuration="swiss_file_present")[0]
        r["requested"], r["returned"], r["nutation"] = 66, 66, "nonut"

    def witness_echo(rows, controls, context, survey):
        _find(controls, role="witness", epoch_id="e0", configuration="jpl_requested_no_jpl_file")[0]["returned"] = 1

    def witness_echo_empty(rows, controls, context, survey):
        _find(controls, role="witness", epoch_id="e2", configuration="swiss_file_dir_empty")[0]["returned"] = 2

    def c_not_honoured(rows, controls, context, survey):
        _find(controls, role="witness", epoch_id="e1", configuration="swiss_file_present")[0]["returned"] = 4

    def witness_not_differing(rows, controls, context, survey):
        for c in _find(controls, role="witness", epoch_id="e1"):
            c["longitude"], c["longitude_bits"] = 51.5, bits(51.5)

    def row_outside(rows, controls, context, survey):
        context["interval"]["end"] = 121.5

    def same_order(rows, controls, context, survey):
        for c in _find(controls, control="sufficiency"):
            c["call_order"] = [r["epoch_id"] for r in rows]

    def no_returned_values(rows, controls, context, survey):
        del rows[1]["returned_values"]

    def five_returned_values(rows, controls, context, survey):
        nested = rows[2]["returned_values"]
        nested["values"], nested["values_bits"] = nested["values"][:5], nested["values_bits"][:5]

    def compared_not_the_first(rows, controls, context, survey):
        second = rows[0]["returned_values"]["values"][1]
        rows[0]["values"], rows[0]["values_bits"] = [second], [bits(second)]

    def two_components(rows, controls, context, survey):
        nested = rows[0]["returned_values"]
        rows[0]["values"], rows[0]["values_bits"] = nested["values"][:2], nested["values_bits"][:2]

    def a_second_comparison_column(rows, controls, context, survey):
        rows[1]["mean_obliquity"], rows[1]["mean_obliquity_bits"] = 23.44, bits(23.44)

    def subject_reading_of_three(rows, controls, context, survey):
        r = _find(controls, role="subject", epoch_id="e0", configuration="moshier_files_present")[0]
        r["values"], r["values_bits"] = r["values"][:3], r["values_bits"][:3]

    def subject_named_field_not_its_position(rows, controls, context, survey):
        r = _find(controls, role="subject", epoch_id="e0", configuration="swiss_file_dir_empty")[0]
        r["distance"], r["distance_bits"] = r["values"][3], r["values_bits"][3]

    def twin_of_three(rows, controls, context, survey):
        twin = _find(controls, control="nutation_twin", epoch_id="e1")[0]
        twin["values"], twin["values_bits"] = twin["values"][:3], twin["values_bits"][:3]

    def row_without_its_unit(rows, controls, context, survey):
        del rows[1]["unit"]

    def read_back_differs(rows, controls, context, survey):
        rows[1]["state_read_back"]["value_bits"] = bits(-25.8)

    def section_word(rows, controls, context, survey):
        context["section_returned"][1] = 66

    def witness_near_its_edge(rows, controls, context, survey):
        survey["edges"][WITNESS] = (119.5, 119.5 + 1e-9, 300.0, 300.0 + 1e-9)

    def pseudo_body_has_an_edge(rows, controls, context, survey):
        survey["edges"][SUBJECT] = (1.0, 2.0, 3.0, 4.0)

    def missing_configuration(rows, controls, context, survey):
        controls.remove(_find(controls, role="subject", epoch_id="e2", configuration="moshier_dir_empty")[0])
        context["children"] -= 1

    out += [
        ("③ (i): a twin equal to its row at the first value", twin_equal, "③ (i) fails"),
        ("③ (ii): a twin whose first value is not its own second", twin_not_its_own_second, "③ (ii) fails"),
        ("③ (ii): a twin whose first value is not the row's second", twin_not_the_rows_second, "③ (ii) fails"),
        ("③: a twin without FLG_NONUT", twin_labelled_default, "is not what it names"),
        ("①: a subject under FLG_NONUT", subject_under_nonut, "is not what it names"),
        ("① (b) ⑴: the witness echoing the JPL request", witness_echo, "① (b) ⑴"),
        ("① (b) ⑴: the witness echoing over the empty directory", witness_echo_empty, "① (b) ⑴"),
        ("① (b) ⑶: C not honoured for the witness", c_not_honoured, "① (b) ⑶"),
        ("① (b) ⑵: the witness not differing between two sources", witness_not_differing, "① (b) ⑵"),
        ("① (c): a row outside the interval", row_outside, "① (c)"),
        ("②: a same-order regeneration", same_order, "order is the section's own"),
        ("a row without its returned values", no_returned_values, "returned values"),
        ("a row with five returned values", five_returned_values, "returned values"),
        ("a row comparing other than its first value", compared_not_the_first, "first returned value alone"),
        ("a row comparing two components", two_components, "first returned value alone"),
        ("a row with a second comparison column", a_second_comparison_column, "first returned value alone"),
        ("a subject reading carrying three values", subject_reading_of_three, "every returned value"),
        ("a subject's named field not its position", subject_named_field_not_its_position, "every returned value"),
        ("a twin carrying three values", twin_of_three, "every returned value"),
        ("a section row with no unit", row_without_its_unit, "declares unit"),
        ("a second read-back value", read_back_differs, "read back"),
        ("a section word other than the request", section_word, "returned words"),
        ("a witness read within a day of its edge", witness_near_its_edge, "days inside the witness's edge"),
        ("an edge row for the pseudo-body", pseudo_body_has_an_edge, "one for the pseudo-body"),
        ("①: a configuration missing at a row", missing_configuration, "not one at each"),
    ]
    for field in ("body", "jd_bits", "returned", "path_state"):
        def sufficiency_reading(rows, controls, context, survey, field=field):
            _find(controls, control="sufficiency", epoch_id="e1")[0][field] = {"body": -1, "jd_bits": bits(121.0),
                                                                               "returned": 2,
                                                                               "path_state": "data_files"}[field]
        out.append((f"a sufficiency row carrying {field}", sufficiency_reading, "a reading's fields"))
    return out


@pytest.mark.parametrize("name,mutation,words", _mutations(), ids=[n for n, _, _ in _mutations()])
def test_each_control_refuses_its_failure_and_the_twin_passes(m, name, mutation, words):
    case = copy.deepcopy(_conforming(m))
    mutation(*case)
    with pytest.raises(m.Refusal) as excinfo:
        m.check(*case)
    assert words in str(excinfo.value), str(excinfo.value)
    m.check(*_conforming(m))


def test_the_twins_separation_is_measured_at_the_closest_row(m):
    summary = m.check(*_conforming(m))["nutation_twin"]
    assert summary["smallest_separation_of_the_first_values"]["epoch_id"] == "e0"
    assert summary["smallest_separation_of_the_first_values"]["doubles_apart"] > 0
    assert summary["smallest_magnitude_of_the_rows_fourth_value_arcseconds"] == round(0.002 * 3600.0, 9)


# ---------------------------------------------------------------------------------------
# End to end, from a commit of its own, on the pinned data files
# ---------------------------------------------------------------------------------------


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True, check=True).stdout


def _survey(directory: Path) -> Path:
    path = directory / "survey.jsonl"
    edge = {"finding": "coverage_edge", "body": WITNESS,
            **{f"{end}_bits": b for end, b in zip(("lower_edge_last_outside_jd_ut", "lower_edge_first_inside_jd_ut",
                                                   "upper_edge_first_inside_jd_ut", "upper_edge_last_outside_jd_ut"),
                                                  MOON_EDGE)}}
    path.write_text("\n".join([json.dumps({"record": "header"}), json.dumps(edge)]) + "\n", encoding="utf-8")
    return path


@pytest.fixture(scope="module")
def emission(tmp_path_factory):
    pytest.importorskip("swisseph", reason="the generator calls the ephemeris library")
    if not all((EPHE / p).is_file() for p in ("seas_18.se1", "semo_18.se1", "sepl_18.se1")):
        pytest.skip("the pinned data files are not in cache/ephe; the end-to-end run cannot happen")
    base = tmp_path_factory.mktemp("emission")
    repo = base / "repo"
    (repo / "generators").mkdir(parents=True)
    for path in (SCRIPT, NODE_SCRIPT):
        shutil.copy(path, repo / "generators" / path.name)
    shutil.copytree(ROOT / "src", repo / "src", ignore=shutil.ignore_patterns("__pycache__"))
    _git(repo, "init", "-q")
    _git(repo, "add", "-A")
    _git(repo, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", "t")
    empty = base / "empty"
    empty.mkdir()
    out = base / "out"
    proc = subprocess.run([sys.executable, str(repo / "generators" / "nutation_obliquity_section.py"),
                           "--ephe-path", str(EPHE), "--empty-dir", str(empty), "--profile", str(_manifest(base)),
                           "--survey", str(_survey(base)), "--budget-row", "ROW-UNDER-TEST", "--out-dir", str(out)],
                          capture_output=True, text=True, timeout=1800)
    assert proc.returncode == 0, proc.stderr[-2000:]
    read = lambda name: [json.loads(line) for line in (out / name).read_text(encoding="utf-8").splitlines()]
    return {"section": read("nutation-obliquity-section.jsonl"),
            "controls": read("nutation-obliquity-section-controls.jsonl"), "out": out, "repo": repo,
            "manifest": _manifest(base), "commit": _git(repo, "rev-parse", "HEAD").strip(),
            "status": _git(repo, "status", "--porcelain", "--untracked-files=all")}


def _digest(lines: str) -> str:
    return hashlib.sha256(lines.encode()).hexdigest()


def test_it_writes_the_section_and_its_controls_naming_one_commit_one_host_one_identity(emission):
    section, controls = emission["section"], emission["controls"]
    header, control_header = section[0], controls[0]
    assert header["fixture_kind"] == "numeric_pin" and control_header["fixture_kind"] == "provenance_record"
    assert header["generator"]["commit"] == control_header["generator"]["commit"] == emission["commit"]
    assert header["generator"]["script"] == "generators/nutation_obliquity_section.py"
    assert header["oracle"]["host"] == control_header["oracle"]["host"]
    basis = header["oracle"]["ephemeris_basis"]["sections"]["true_obliquity"]
    assert (basis["entry_point"], basis["requested"], basis["returned"], basis["requested_word"],
            basis["claimed_class"], basis["generation"]) == ("calc", "swiss_file", "swiss_file", 2,
                                                             "request_invariant", "warm_in_row_order")
    states = basis["configuration"]["library_state"]
    assert sorted(states) == ["leap_second_table", "sidereal_mode", "tidal_acceleration", "user_defined_delta_t"]
    assert all(v == {"discipline": "reset"} for v in states.values())
    assert basis["configuration"]["ephemeris_path"]["set"] == "explicit"
    assert [f["dataset"] for f in basis["configuration"]["ephemeris_path"]["resolved_contents"]] == [
        "seas_18.se1", "semo_18.se1", "sepl_18.se1"]
    assert header["summary"]["configuration_sha256"] == IDENTITY_WORD_2
    assert {c["configuration_sha256"] for c in controls[1:]} == {IDENTITY_WORD_2}
    assert header["classification"] == {"true_obliquity": {"class": "tolerance", "band": 1.388888888888889e-05,
                                                           "unit": "degree"}}
    assert header["budget_row"] == "ROW-UNDER-TEST"
    assert emission["status"] == ""


def test_every_row_compares_its_first_value_and_carries_all_six(emission):
    rows = emission["section"][1:]
    assert len(rows) == 76
    for row in rows:
        assert row["body"] == -1 and row["unit"] == "degree"
        assert row["source_assertion"] == {"kind": "none", "reason": "request_invariant"}
        assert [k for k in row if k.endswith("_bits")] == ["values_bits"]
        assert len(row["returned_values"]["values_bits"]) == 6
        assert row["values_bits"] == row["returned_values"]["values_bits"][:1]
        assert row["state_read_back"]["state"] == "tidal_acceleration"


def test_its_rows_are_the_mean_node_sections_rows_bit_for_bit(emission):
    node = _load(NODE_SCRIPT, "mean_node_section_for_rows")
    theirs = [(e["epoch_id"], bits(e["jd"])) for e in node.build_epochs(node.read_interval(str(emission["manifest"])))]
    assert [(r["epoch_id"], r["instant"]["jd_bits"]) for r in emission["section"][1:]] == theirs


def test_every_reading_of_the_pseudo_body_carries_six_and_no_sufficiency_row_is_a_reading(emission):
    controls = emission["controls"][1:]
    pseudo = [c for c in controls if c.get("body") == -1]
    assert len(pseudo) == 76 * 6
    for c in pseudo:
        assert len(c["values_bits"]) == 6
        assert c["values_bits"][:3] == [c["longitude_bits"], c["latitude_bits"], c["distance_bits"]]
    twins = [c for c in controls if c["control"] == "nutation_twin"]
    assert {(c["requested"], c["returned"], c["nutation"], c["path_state"]) for c in twins} == {(66, 66, "nonut",
                                                                                               "data_files")}
    subjects = [c for c in controls if c.get("role") == "subject"]
    assert {c["nutation"] for c in subjects} == {"default"} and {c["requested"] for c in subjects} == {1, 2, 4}
    witness = [c for c in controls if c.get("role") == "witness"]
    assert len(witness) == 76 * 5 and all("values_bits" not in c for c in witness)
    sufficiency = [c for c in controls if c["control"] == "sufficiency"]
    assert len(sufficiency) == 76
    for s in sufficiency:
        assert not {"body", "jd_bits", "returned", "path_state", "requested"} & set(s) and len(s["values_bits"]) == 6


def test_its_readings_are_the_pinned_ones(emission):
    rows = "".join(f"{r['epoch_id']}|{'|'.join(r['returned_values']['values_bits'])}\n"
                   for r in emission["section"][1:])
    controls = emission["controls"][1:]
    twins = "".join(f"{c['epoch_id']}|{'|'.join(c['values_bits'])}\n" for c in controls
                    if c["control"] == "nutation_twin")
    witness = "".join(f"{c['epoch_id']}|{c['configuration']}|{c['returned']}|{c['longitude_bits']}\n"
                      for c in controls if c.get("role") == "witness")
    assert (_digest(rows), _digest(twins), _digest(witness)) == (ROWS_DIGEST, TWINS_DIGEST, WITNESS_DIGEST)


def test_a_second_emission_into_the_same_place_is_refused(emission):
    sys.path.insert(0, str(ROOT / "src"))
    m = _load(SCRIPT, "nutation_obliquity_section_again")
    with pytest.raises(m.Refusal):
        m.write_files([], [], {"interval": {}, "epochs": [], "word": 2, "library_version": "x"}, {},
                      str(emission["out"]), "ROW")


def test_the_row_id_is_a_parameter_and_never_a_default(tmp_path):
    proc = subprocess.run([sys.executable, str(SCRIPT), "--ephe-path", "x", "--empty-dir", "y", "--profile", "z",
                           "--survey", "s", "--out-dir", str(tmp_path / "o")], capture_output=True, text=True)
    assert proc.returncode == 2 and "--budget-row" in proc.stderr
    m = _load(SCRIPT, "nutation_obliquity_section_row")
    for bad in ("", " ROW", "ROW "):
        with pytest.raises(m.Refusal) as excinfo:
            m.generate("x", "y", "z", "s", str(tmp_path / "o"), bad)
        assert "empty or padded" in str(excinfo.value)
