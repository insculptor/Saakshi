"""The convention grid's own machinery: its lists, its plan, its admission of children, its rows and its refusals.

⭐ Almost all of this needs no ephemeris library: a child is injected that answers each declared call with a return
of the entry point's real shape, so the plan's arithmetic, the admission rule, the returned-word checks, the
recording of a library error and the three files are all checked where continuous integration can see them. The
last test runs a tiny grid through real fresh children wherever the binding and the pinned data files are present.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import math
import os
import struct
import sys
import threading
from pathlib import Path

import pytest

from saakshi.fixture import Generator, bits

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "generators" / "convention_grid.py"
_spec = importlib.util.spec_from_file_location("convention_grid", SCRIPT)
gen = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = gen  # a dataclass resolves its annotations through the module it is defined in
_spec.loader.exec_module(gen)  # type: ignore[union-attr]
C = gen.CONSTANTS
GENERATOR = Generator(repo="r", script="generators/convention_grid.py", commit="0" * 40)


def _f(x: float) -> dict:
    return {"number": x, "bits": bits(x)}


def _seq(*items) -> dict:
    return {"sequence": list(items)}


class FakeChild:
    """Answers a spec as a fresh child would: the declared calls, a fresh nonce, a return of the entry point's
    shape. ``tamper`` may rewrite the result (to plant one fault)."""

    def __init__(self, tamper=None):
        self.n = 0
        self.tamper = tamper
        self.specs = []
        self.lock = threading.Lock()

    def __call__(self, spec, work_dir):
        # ⚠ The run calls this from several threads at once. The count is taken under a lock and kept in a local:
        #   read back from `self.n` later, two readings could carry one nonce, and the run would refuse them as
        #   one child's — a refusal of the fake, not of the code under test.
        with self.lock:
            self.n += 1
            n = self.n
            self.specs.append(spec)
        call = spec["call"]
        f = call["function"]
        args = call["args"]
        base = 0.001 * n
        if f == "calc_ut":
            returned = _seq(_seq(*[_f(base + i) for i in range(6)]), {"integer": args[2]["integer"]})
        elif f == "get_ayanamsa_ex_ut":
            returned = _seq({"integer": args[1]["integer"] & ~C["FLG_NONUT"]}, _f(23.0 + base))
        elif f in ("get_ayanamsa_ut", "sidtime"):
            returned = _f(5.0 + base)
        elif f in ("houses_ex", "houses_armc"):
            returned = _seq(_seq(*[_f(30.0 * i + base) for i in range(12)]), _seq(*[_f(i + base) for i in range(8)]))
        elif f == "rise_trans":
            returned = _seq({"integer": 0}, _seq(*[_f(2461000.5 + base)] + [_f(0.0)] * 9))
        else:
            raise AssertionError(f)
        result = {"nonce": f"{n:032x}", "fresh_interpreter": True, "calls": gen.declared_calls(spec),
                  "returned": returned}
        return self.tamper(spec, result) if self.tamper else result


def _tiny() -> "gen.Grid":
    return gen.Grid(
        ayanamsha_instants=[("g0", 2415020.5), gen.chart_instant()],
        house_instants=[("h0", gen.jd_ut((2026, 3, 20), 360.0)), gen.chart_instant()],
        rise_dates=[("d0", gen.jd_ut((2026, 6, 21)))],
        modes=gen.MODES[:2] + gen.MODES[-1:],
        house_modes=gen.HOUSE_MODES[:2],
        house_systems="WPI",
        sites=[s for s in gen.SITES if s[0] in ("kanpur", "longyearbyen")],
    )


def _dirs(tmp_path):
    paths = {"empty_directory": str(tmp_path / "empty"), "data_files": str(tmp_path / "data")}
    for name in ("empty", "data", "work", "staging"):
        (tmp_path / name).mkdir()
    return paths


def _run(tmp_path, child=None, grid=None):
    paths = _dirs(tmp_path)
    return gen.run(grid or _tiny(), paths=paths, work_dir=str(tmp_path / "work"), staging=tmp_path / "staging",
                   workers=3, runner=child or FakeChild())


def _rows(staged, stratum):
    return [row for part in staged[stratum] for row in part.rows_back()]


# --- the lists, as written ---------------------------------------------------------------------------------------


def test_the_eleven_modes_are_the_three_reference_modes_and_the_eight_anchored_ones():
    assert [(n, C[n]) for n, _k in gen.MODES] == [
        ("SIDM_LAHIRI", 1), ("SIDM_KRISHNAMURTI", 5), ("SIDM_RAMAN", 3), ("SIDM_TRUE_CITRA", 27),
        ("SIDM_TRUE_REVATI", 28), ("SIDM_TRUE_PUSHYA", 29), ("SIDM_TRUE_MULA", 35), ("SIDM_TRUE_SHEORAN", 39),
        ("SIDM_GALCENT_0SAG", 17), ("SIDM_GALCENT_RGILBRAND", 30), ("SIDM_ALDEBARAN_15TAU", 14)]
    assert [k for _n, k in gen.MODES].count("reference_epoch") == 3
    assert gen.HOUSE_MODES == ("SIDM_LAHIRI", "SIDM_KRISHNAMURTI", "SIDM_RAMAN")


def test_the_twenty_one_house_methods_and_the_ten_sites():
    assert gen.HOUSE_SYSTEMS == "WEPKORCSTBMUVXHFDIYLQ" and len(set(gen.HOUSE_SYSTEMS)) == 21
    assert gen.SUNSHINE in gen.HOUSE_SYSTEMS
    assert [(s, la, lo) for s, la, lo, _g in gen.SITES] == [
        ("kanpur", 26.4499, 80.3319), ("delhi", 28.6139, 77.2090), ("meerut", 28.9845, 77.7064),
        ("varanasi", 25.3176, 82.9739), ("chennai", 13.0827, 80.2707), ("oslo", 59.9139, 10.7522),
        ("helsinki", 60.1699, 24.9384), ("sub_polar", 64.1466, -21.9426), ("tromso", 69.6492, 18.9553),
        ("longyearbyen", 78.2232, 15.6267)]


def test_the_chart_instant_and_the_calendar_arithmetic():
    assert gen.jd_ut((2000, 1, 1), 720.0) == 2451545.0
    assert gen.jd_ut((1900, 1, 1)) == 2415020.5
    assert gen.chart_instant() == ("chart_1992_11_11", 2448937.5 + 70.0 / 1440.0)


def test_fourteen_rise_forms_the_first_the_deployed_call_with_its_atmosphere_omitted():
    forms = gen.rise_forms()
    assert len(forms) == 14 and len({f for f, _d, _a in forms}) == 14
    assert forms[0] == ("disc_center_atmosphere_omitted", C["BIT_DISC_CENTER"], None)
    assert ("disc_center_no_refraction_zero_zero", C["BIT_DISC_CENTER"] | C["BIT_NO_REFRACTION"], (0.0, 0.0)) in forms


# --- the plan ----------------------------------------------------------------------------------------------------


def test_the_full_grid_holds_the_planned_readings_by_arithmetic_and_by_plan():
    grid = gen.full_grid([2400000.5 + i for i in range(507)])
    counts = gen.planned_counts(grid)
    assert counts == {"ayanamsha": 83312, "house_inputs": 1940, "house_cusps": 307490, "rise_set": 205692}
    assert len(gen.plan_ayanamsha(grid)) == counts["ayanamsha"]
    assert len(gen.plan_house_inputs(grid)) == counts["house_inputs"]
    assert len(gen.plan_rise(grid)) == counts["rise_set"]
    fake = gen.HouseInputs(100.0 / 15.0, 23.44, 23.43, -10.0)
    inputs = {(iid, c): fake for iid, _jd in grid.house_instants for c, _p, _b in gen.CONDITIONS}
    assert len(gen.plan_houses(grid, inputs)) == counts["house_cusps"]
    assert len(grid.ayanamsha_instants) == 508 and len(grid.house_instants) == 97 and len(grid.rise_dates) == 366


def test_the_angle_is_the_sidereal_time_in_degrees_plus_the_east_longitude_reduced():
    assert gen.armc_of(1.0, 10.0) == 25.0
    assert gen.armc_of(0.5, -21.9426) == 0.5 * 15.0 - 21.9426 + 360.0
    assert gen.armc_of(23.9, 80.3319) == math.fmod(23.9 * 15.0 + 80.3319, 360.0)


def test_the_house_inputs_are_components_zero_and_one_of_the_obliquity_and_the_declination(tmp_path):
    grid = _tiny()
    items = gen.plan_house_inputs(grid)
    rows = gen.measure(items, gen.Readers(str(tmp_path), 2, FakeChild()), {"empty_directory": "/e",
                                                                            "data_files": "/d"}, None, keep=True)
    got = gen.house_inputs_from(items, rows)
    one = got[("h0", "files_absent")]
    by_form = {r["form"]: r for r in rows if r["instant_id"] == "h0" and r["condition"] == "files_absent"}
    values = lambda form: [struct.unpack(">d", bytes.fromhex(p))[0] for p in by_form[form]["values_bits"]]
    assert one.sidereal_time == values("sidereal_time")[0]
    assert (one.obliquity_true, one.obliquity_mean) == tuple(values("nutation_obliquity")[:2])
    assert one.sun_declination == values("sun_equatorial")[1]


def test_an_input_reading_that_raised_refuses_the_house_plan(tmp_path):
    grid = _tiny()
    items = gen.plan_house_inputs(grid)
    rows = [{"library_error": "x"} for _ in items]
    with pytest.raises(gen.Refusal, match="returned no value"):
        gen.house_inputs_from(items, rows)


# --- the run, end to end with injected children -------------------------------------------------------------------


def test_every_planned_reading_is_taken_once_and_staged_in_the_plan_order(tmp_path):
    child = FakeChild()
    staged, planned = _run(tmp_path, child)
    assert child.n == sum(planned.values())
    rows = _rows(staged, "ayanamsha")
    assert [r["form"] for r in rows[:5]] == ["sun_tropical_with_nutation", "sun_tropical_no_nutation",
                                             "moon_tropical_with_nutation", "moon_tropical_no_nutation",
                                             "nutation_obliquity"]
    assert all("values_bits" in r for r in rows)


def test_the_three_files_are_written_and_a_second_run_is_byte_identical(tmp_path):
    digests = []
    for n in (1, 2):
        where = tmp_path / f"run{n}"
        where.mkdir()
        staged, planned = _run(where)
        written = gen.emit(where / "out", staged=staged, planned=planned, generator=GENERATOR, grid=_tiny(),
                           oracle=gen.oracle_block("2.10.03", "2.10.3.2", {"files": []}),
                           grid_values={"values_sha256": "0" * 64, "distinct_instants": 1}, budget_row="row-1")
        assert [p.name for p, _r in written] == list(gen.OUTPUTS.values())
        digests.append([hashlib.sha256(p.read_bytes()).hexdigest() for p, _r in written])
        header = json.loads((where / "out" / gen.OUTPUTS["houses"]).read_text().splitlines()[0])
        assert header["summary"]["readings"] == header["summary"]["readings_planned"]
        assert set(header["classification"]) == {"house_inputs", "house_cusps"}
    assert digests[0] == digests[1]


def test_the_dropped_no_nutation_bit_is_recorded_beside_the_request(tmp_path):
    staged, _p = _run(tmp_path)
    row = next(r for r in _rows(staged, "ayanamsha") if r["form"] == "ayanamsha_flagged_no_nutation")
    assert row["requested"] & C["FLG_NONUT"] and not row["returned_flag"] & C["FLG_NONUT"]


def test_a_library_error_is_recorded_with_the_directories_named_by_role(tmp_path):
    paths = {}

    def tamper(spec, result):
        if spec["call"]["function"] == "houses_ex":
            paths["empty"] = spec["path"]
            return {**{k: v for k, v in result.items() if k != "returned"},
                    "library_error": f"swisseph.houses_ex: error; file not found in PATH '{spec['path']}/'"}
        return result

    staged, _p = _run(tmp_path, FakeChild(tamper))
    errors = [r for r in _rows(staged, "houses") if "library_error" in r]
    assert errors and all("values" not in r for r in errors)
    assert all(paths["empty"] not in r["library_error"] and str(tmp_path) not in r["library_error"] for r in errors)
    assert any("<empty_directory>/" in r["library_error"] for r in errors)


@pytest.mark.parametrize("fault, match", [
    (lambda s, r: {**r, "fresh_interpreter": False}, "loaded before"),
    (lambda s, r: {**r, "calls": r["calls"] + [{"function": "close", "args": [], "keywords": {}}]}, "calls were"),
    (lambda s, r: {**r, "calls": r["calls"][1:]}, "calls were"),
    (lambda s, r: {**r, "nonce": "0" * 32}, "one child"),
])
def test_a_child_that_is_not_one_fresh_declared_reading_refuses_the_run(tmp_path, fault, match):
    with pytest.raises(gen.Refusal, match=match):
        _run(tmp_path, FakeChild(fault))


def _swap_word(function, new_word):
    def tamper(spec, result):
        if spec["call"]["function"] != function:
            return result
        returned = json.loads(json.dumps(result["returned"]))
        for node in returned["sequence"]:
            if "integer" in node:
                node["integer"] = new_word(node["integer"])
        return {**result, "returned": returned}
    return tamper


def test_a_position_answered_by_another_ephemeris_refuses_the_run(tmp_path):
    swap = lambda w: (w & ~gen.EPHEMERIS_BITS) | (C["FLG_MOSEPH"] if w & C["FLG_SWIEPH"] else C["FLG_SWIEPH"])
    with pytest.raises(gen.Refusal, match="returned ephemeris bits"):
        _run(tmp_path, FakeChild(_swap_word("calc_ut", swap)))


def test_an_ayanamsha_answered_by_another_ephemeris_refuses_the_run(tmp_path):
    swap = lambda w: (w & ~gen.EPHEMERIS_BITS) | (C["FLG_MOSEPH"] if w & C["FLG_SWIEPH"] else C["FLG_SWIEPH"])
    with pytest.raises(gen.Refusal, match="returned ephemeris bits"):
        _run(tmp_path, FakeChild(_swap_word("get_ayanamsa_ex_ut", swap)))


def test_a_value_that_is_not_finite_refuses_the_run(tmp_path):
    def tamper(spec, result):
        if spec["call"]["function"] == "sidtime":
            return {**result, "returned": {"number": float("nan"), "bits": bits(float("nan"))}}
        return result

    with pytest.raises(gen.Refusal, match="not finite"):
        _run(tmp_path, FakeChild(tamper))


def test_a_return_of_another_shape_refuses_the_run(tmp_path):
    def tamper(spec, result):
        if spec["call"]["function"] == "houses_armc":
            return {**result, "returned": _seq(_seq(*[_f(1.0)] * 12), _seq(*[_f(1.0)] * 7))}
        return result

    with pytest.raises(gen.Refusal, match="returned 0 integers and 19 doubles"):
        _run(tmp_path, FakeChild(tamper))


def test_a_returned_double_whose_two_forms_differ_refuses_the_run(tmp_path):
    def tamper(spec, result):
        if spec["call"]["function"] == "get_ayanamsa_ut":
            return {**result, "returned": {"number": 1.0, "bits": bits(2.0)}}
        return result

    with pytest.raises(gen.Refusal, match="different numbers"):
        _run(tmp_path, FakeChild(tamper))


def test_a_plan_whose_length_is_not_the_arithmetic_refuses_the_run(tmp_path, monkeypatch):
    real = gen.planned_counts
    monkeypatch.setattr(gen, "planned_counts", lambda g: {**real(g), "ayanamsha": real(g)["ayanamsha"] + 1})
    with pytest.raises(gen.Refusal, match="the ayanamsha plan holds"):
        _run(tmp_path)


def test_a_house_plan_whose_length_is_not_the_arithmetic_refuses_the_run(tmp_path, monkeypatch):
    real = gen.planned_counts
    monkeypatch.setattr(gen, "planned_counts", lambda g: {**real(g), "house_cusps": real(g)["house_cusps"] + 1})
    with pytest.raises(gen.Refusal, match="the house plan holds"):
        _run(tmp_path)


def test_a_reading_not_taken_refuses_the_run(tmp_path, monkeypatch):
    real = gen.measure

    def short(items, *a, **k):
        rise = items and items[0].base["section"] == "source_proxy"
        return real(items[:-1] if rise else items, *a, **k)

    monkeypatch.setattr(gen, "measure", short)
    with pytest.raises(gen.Refusal, match="readings were taken"):
        _run(tmp_path)


def test_an_input_missing_from_an_instant_refuses_the_house_plan(tmp_path):
    grid = _tiny()
    items = gen.plan_house_inputs(grid)
    rows = gen.measure(items, gen.Readers(str(tmp_path), 2, FakeChild()), {"empty_directory": "/e",
                                                                            "data_files": "/d"}, None, keep=True)
    keep = [(i, r) for i, r in zip(items, rows) if not (i.base["form"] == "sun_equatorial"
                                                        and i.base["instant_id"] == "h0")]
    with pytest.raises(gen.Refusal, match="the inputs at"):
        gen.house_inputs_from([i for i, _r in keep], [r for _i, r in keep])


# --- refusals before reading --------------------------------------------------------------------------------------


def _values_file(path: Path, rows) -> str:
    lines = [json.dumps({"record": "header"})] + [json.dumps({"record": "row", "jd_tdb": v, "jd_tdb_bits": p})
                                                    for v, p in rows]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_the_values_file_is_read_by_its_digest_and_its_bits(tmp_path):
    path = tmp_path / "v.jsonl"
    digest = _values_file(path, [(2451545.0, bits(2451545.0)), (2451545.0, bits(2451545.0)), (2400000.5,
                                                                                               bits(2400000.5))])
    assert gen.grid_instants(path, digest) == [2400000.5, 2451545.0]
    with pytest.raises(gen.Refusal, match="sha256"):
        gen.grid_instants(path, "0" * 64)
    digest = _values_file(path, [(2451545.0, bits(2451545.5))])
    with pytest.raises(gen.Refusal, match="different numbers"):
        gen.grid_instants(path, digest)


def test_a_data_directory_holding_anything_but_the_pinned_files_is_refused(tmp_path):
    for name in ("seas_18.se1", "semo_18.se1", "sepl_18.se1", "sefstars.txt"):
        (tmp_path / name).write_bytes(b"")
    with pytest.raises(gen.Refusal, match="not exactly"):
        gen.require_data_directory(tmp_path)
    (tmp_path / "sefstars.txt").unlink()
    (tmp_path / "semo_18.se1").unlink()
    with pytest.raises(gen.Refusal, match="not exactly"):
        gen.require_data_directory(tmp_path)


def test_a_directory_left_holding_anything_is_refused(tmp_path):
    gen.require_empty(tmp_path, "work directory")
    (tmp_path / "x").write_text("x")
    with pytest.raises(gen.Refusal, match="work directory holds"):
        gen.require_empty(tmp_path, "work directory")


def test_a_binding_other_than_the_pin_is_refused_before_it_is_imported(monkeypatch):
    monkeypatch.setattr(gen, "_distribution_version", lambda name: "0")
    monkeypatch.setitem(sys.modules, "swisseph", None)
    with pytest.raises(gen.Refusal, match="the binding is 0"):
        gen.require_binding()


def _main_with(monkeypatch, tmp_path, **override):
    monkeypatch.setattr(gen, "generator_for", lambda script: GENERATOR)
    args = {"--ephe-path": str(tmp_path), "--grid-values": str(tmp_path / "v.jsonl"),
            "--grid-values-sha256": "0" * 64, "--budget-row": "row-1", "--out": str(tmp_path / "out"), **override}
    return gen.main([x for kv in args.items() for x in kv])


def test_an_existing_output_is_refused_first(monkeypatch, tmp_path, capsys):
    (tmp_path / "out").mkdir()
    (tmp_path / "out" / gen.OUTPUTS["rise_set"]).write_text("")
    assert _main_with(monkeypatch, tmp_path) == 2
    assert "exists in the output directory" in capsys.readouterr().err


def test_a_budget_row_not_given_exactly_is_refused(monkeypatch, tmp_path, capsys):
    assert _main_with(monkeypatch, tmp_path, **{"--budget-row": " row-1"}) == 2
    assert "given exactly" in capsys.readouterr().err


# --- the binding itself, wherever it is installed -----------------------------------------------------------------

swe_present = importlib.util.find_spec("swisseph") is not None
#: The pinned data files: this tree's cache, or a directory named in the environment (a scratch copy has no cache).
EPHE = Path(os.environ.get("CONVENTION_GRID_EPHE", ROOT / "cache" / "ephe"))


@pytest.mark.skipif(not swe_present, reason="the binding is not installed here")
def test_the_constants_written_here_are_the_binding_s(monkeypatch):
    import swisseph as swe

    assert {n: getattr(swe, n) for n in C} == C
    monkeypatch.setitem(gen.CONSTANTS, "SUN", 99)
    if gen._distribution_version("pyswisseph") == gen.BINDING_PIN:
        with pytest.raises(gen.Refusal, match="constants differ"):
            gen.require_binding()


@pytest.mark.skipif(not swe_present, reason="the binding is not installed here")
def test_a_library_other_than_the_pin_is_refused(monkeypatch):
    import swisseph as swe

    monkeypatch.setattr(gen, "_distribution_version", lambda name: gen.BINDING_PIN)
    monkeypatch.setattr(swe, "version", "0.0")
    with pytest.raises(gen.Refusal, match="the library is 0.0"):
        gen.require_binding()


@pytest.mark.skipif(not swe_present, reason="the binding is not installed here")
def test_a_pinned_set_other_than_the_one_written_here_is_refused(monkeypatch, tmp_path):
    monkeypatch.setattr(gen, "DATA_FILES", ("a.se1",))
    (tmp_path / "a.se1").write_bytes(b"")
    with pytest.raises(gen.Refusal, match="the pinned data files are"):
        gen.require_data_directory(tmp_path)


def test_no_children_at_once_is_refused(tmp_path):
    with pytest.raises(gen.Refusal, match="0 children"):
        gen.Readers(str(tmp_path), 0, FakeChild())


@pytest.mark.skipif(not (swe_present and EPHE.is_dir()), reason="needs the binding and the pinned data files")
def test_a_tiny_grid_through_real_fresh_children(tmp_path):
    paths = _dirs(tmp_path)
    paths["data_files"] = str(EPHE.resolve())
    gen.require_data_directory(EPHE)
    staged, planned = gen.run(_tiny(), paths=paths, work_dir=str(tmp_path / "work"), staging=tmp_path / "staging",
                              workers=4)
    rows = [r for parts in staged.values() for part in parts for r in part.rows_back()]
    assert len(rows) == sum(planned.values())
    gen.require_empty(tmp_path / "empty", "empty directory")
    gen.require_empty(tmp_path / "work", "work directory")
    polar = [r for r in rows if r.get("site") == "longyearbyen" and r.get("house_system") == "P"
             and r["section"] == "house_cusps"]
    assert polar and all("library_error" in r for r in polar)
    assert not any(os.sep + "Users" + os.sep in json.dumps(r) for r in rows)
