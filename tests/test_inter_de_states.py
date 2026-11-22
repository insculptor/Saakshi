"""The inter-fit record's own machinery: its instants, its two readers' agreement, its rows and its refusals.

⭐ Most of this needs no ephemeris library: the readers are injected, so the coverage rules, the refusal of two
readers that disagree, the overlap of the two files of one fit, the `same_bits_as` compaction and the differences
are all checked where continuous integration can see them. The last section builds six small kernels with the SPICE
Toolkit's own writer and runs the whole measurement on them; it runs wherever the pinned libraries are installed.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import math
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from saakshi.fixture import Generator, bits, validate_header

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "generators" / "inter_de_states.py"
_spec = importlib.util.spec_from_file_location("inter_de_states", SCRIPT)
gen = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = gen  # a dataclass resolves its annotations through the module it is defined in
_spec.loader.exec_module(gen)  # type: ignore[union-attr]

L = gen.Layout
PAIRS = [(1, 0), (2, 0), (3, 0), (4, 0), (5, 0), (6, 0), (7, 0), (8, 0), (9, 0), (10, 0), (301, 3), (399, 3),
         (199, 1), (299, 2)]


def _layouts(start: float, end: float, init: float | None = None) -> list:
    """Segments shaped like the publisher's: 4, 8, 16 and 32 days, one record for the two identically-zero pairs."""
    init = start if init is None else init
    step = {1: 8.0, 2: 16.0, 3: 16.0, 10: 16.0, 301: 4.0, 399: 4.0}
    out = []
    for target, centre in PAIRS:
        length = step.get(target, 32.0) if target not in (199, 299) else end - init
        out.append(L(target, centre, start, end, init, length, int(round((end - init) / length)), 1, 2))
    return out


def _indexed(spans: dict[str, tuple[float, float]]) -> dict:
    return gen.check_structures({key: _layouts(*spans[key]) for key, _n, _f in gen.FILES})


T0 = 2451545.5
SPANS = {"de440s": (T0, T0 + 64), "de440": (T0 - 32, T0 + 96), "de441_part_1": (T0 - 32, T0 + 32),
         "de441_part_2": (T0, T0 + 96), "de442s": (T0, T0 + 64), "de442": (T0 - 32, T0 + 96)}


# --- the instants ------------------------------------------------------------------------------------------------


def _values(path: Path, rows: list[tuple[float, str]]) -> str:
    lines = [json.dumps({"record": "header"})] + [json.dumps({"record": "row", "jd_tdb": v, "jd_tdb_bits": b})
                                                   for v, b in rows]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_the_grid_is_its_files_distinct_instants_and_only_by_digest(tmp_path):
    path = tmp_path / "v.jsonl"
    digest = _values(path, [(T0 + 1, bits(T0 + 1)), (T0, bits(T0)), (T0 + 1, bits(T0 + 1))])
    assert gen.grid_instants(path, digest) == [T0, T0 + 1]
    with pytest.raises(gen.Refusal, match="sha256"):
        gen.grid_instants(path, "0" * 64)
    digest = _values(path, [(T0, bits(T0 + 1))])
    with pytest.raises(gen.Refusal, match="different numbers"):
        gen.grid_instants(path, digest)


def test_an_instant_reaches_both_readers_exactly_or_not_at_all():
    assert gen.et_seconds(2451545.5) == 43200.0
    assert gen.et_seconds(2440400.5) == (2440400.5 - 2451545.0) * 86400.0
    assert gen.et_seconds(2451545.0 + 1.0 / 16.0) == 5400.0
    with pytest.raises(gen.Refusal, match="exactly"):
        gen.et_seconds(2451545.1)
    whole, fraction = gen.split_jd(2396752.5625)
    assert (whole, fraction) == (2396752.0, 0.5625) and whole + fraction == 2396752.5625


def test_a_segment_names_every_record_boundary_and_its_own_coverage():
    layout = L(301, 3, T0, T0 + 12, T0, 4.0, 3, 1, 2)
    assert layout.boundaries() == [T0, T0 + 4, T0 + 8, T0 + 12]
    assert layout.covers(T0) and layout.covers(T0 + 12) and not layout.covers(T0 + 12.5)


def test_a_pair_carried_twice_or_a_different_structure_is_refused():
    twice = _layouts(T0, T0 + 64) + [L(301, 3, T0, T0 + 64, T0, 4.0, 16, 1, 2)]
    with pytest.raises(gen.Refusal, match="two segments"):
        gen.check_structures({"de440s": twice})
    with pytest.raises(gen.Refusal, match="carries the segments"):
        gen.check_structures({"de440s": _layouts(T0, T0 + 64), "de440": _layouts(T0, T0 + 64)[:-1]})


def test_a_state_is_composed_at_the_nearest_common_ancestor():
    parent = {t: c for t, c in PAIRS}
    assert gen.legs(parent, 301, 399) == ([(301, 3)], [(399, 3)])
    assert gen.legs(parent, 4, 399) == ([(4, 0)], [(399, 3), (3, 0)])
    assert gen.legs(parent, 301, 0) == ([(301, 3), (3, 0)], [])
    assert gen.legs(parent, 199, 0) == ([(199, 1), (1, 0)], [])
    with pytest.raises(gen.Refusal, match="towards"):
        gen.chain({301: 3}, 301)


def test_the_grid_asks_every_point_of_both_centres_but_the_earth_of_itself():
    points = gen.grid_points([T0, T0 + 1], T0, T0 + 64)
    assert len(points) == 2 * (2 * 12 - 1)
    assert not [p for p in points if p.target == p.centre]
    assert {p.epoch_id for p in points} == {"g000", "g001"}
    with pytest.raises(gen.Refusal, match="outside the window"):
        gen.grid_points([T0 - 1], T0, T0 + 64)


def test_the_record_edges_are_every_boundary_and_coverage_end_in_the_window_with_their_reasons():
    indexed = _indexed(SPANS)
    lo, hi = gen.window(indexed)
    assert (lo, hi) == (T0, T0 + 64)
    points, reasons = gen.edge_points(indexed, lo, hi)
    moon = sorted(p.jd for p in points if p.target == 301)
    assert moon == [T0 + 4 * k for k in range(17)]
    assert {p.jd for p in points if p.target == 4} == {T0, T0 + 32, T0 + 64}
    # the end of the first file of a fit, inside the window, is that file's coverage end and record boundary
    end = reasons[(T0 + 32, 301, 3)]
    assert "de441_part_1" in end["segment_end_in"] and "de441_part_1" in end["record_boundary_in"]
    assert reasons[(T0, 301, 3)]["segment_end_in"] == ["de440s", "de441_part_2", "de442s"]
    assert len({p.epoch_id for p in points}) == len({p.jd for p in points})
    # an identically-zero pair has edges only where some file's record or coverage starts or ends
    assert {p.jd for p in points if p.target == 199} == {T0, T0 + 32, T0 + 64}


# --- the readers: agreement or refusal, never an average -----------------------------------------------------------


def test_two_readers_agree_within_the_stated_fraction_and_not_beyond_it():
    state = (3.0e8, 4.0e8, 0.0, 30.0, 40.0, 0.0)
    edge = 5.0e8 * gen.READER_AGREEMENT
    ok = (3.0e8 + edge / 2, 4.0e8, 0.0, 30.0, 40.0, 0.0)
    assert 0.0 < gen.reader_deltas(state, ok, where="t")[0] == abs(ok[0] - state[0]) <= edge
    bad = (3.0e8 + 4 * edge, 4.0e8, 0.0, 30.0, 40.0, 0.0)
    with pytest.raises(gen.Refusal, match="disagree on the position"):
        gen.reader_deltas(state, bad, where="t")
    with pytest.raises(gen.Refusal, match="disagree on the velocity"):
        gen.reader_deltas(state, (*state[:3], 30.0 + 1.0e-9, 40.0, 0.0), where="t")
    assert gen.READER_AGREEMENT == 2.0**-44


def test_where_the_norm_is_zero_the_readers_must_agree_exactly():
    zero = (0.0,) * 6
    assert gen.reader_deltas(zero, zero, where="t") == (0.0, 0.0)
    with pytest.raises(gen.Refusal, match="disagree"):
        gen.reader_deltas(zero, (1.0e-300, 0.0, 0.0, 0.0, 0.0, 0.0), where="t")
    with pytest.raises(gen.Refusal, match="non-finite"):
        gen.reader_deltas(zero, (math.nan, 0.0, 0.0, 0.0, 0.0, 0.0), where="t")


class FakeReaders:
    """Two readers on one synthetic file: a state that depends on the file's fit, and a second reader that can be
    made to drift."""

    drift: dict[str, float] = {}
    opened: list[str] = []

    def __init__(self, path: Path, pairs) -> None:
        self.key = path.name
        FakeReaders.opened.append(self.key)

    def close(self) -> None:
        pass

    def cspice(self, target, centre, jd):
        offset = {"de441_part_1": 1.0e-3, "de441_part_2": 1.0e-3, "de442s": 2.0, "de442": 2.0}.get(self.key, 0.0)
        if target in (199, 299):
            return (0.0,) * 6
        base = 1.0e6 * target - (0.0 if centre == 0 else 7.0e5) + (jd - T0)
        return (base + offset, base, -base, 1.0, 2.0, 3.0)

    def jplephem(self, target, centre, jd):
        state = list(self.cspice(target, centre, jd))
        state[0] += FakeReaders.drift.get(self.key, 0.0)
        return tuple(state)


def _measure(points, indexed, drift=None):
    FakeReaders.drift, FakeReaders.opened = dict(drift or {}), []
    kernels = {key: Path(key) for key, _n, _f in gen.FILES}
    return gen.measure(kernels, indexed, points, open_readers=FakeReaders)


def test_each_file_is_read_by_itself_and_only_where_it_covers_the_instant():
    indexed = _indexed(SPANS)
    lo, hi = gen.window(indexed)
    points = gen.grid_points([T0 + 1, T0 + 40], lo, hi)
    readings = _measure(points, indexed)
    assert FakeReaders.opened == [key for key, _n, _f in gen.FILES]
    covered = {key: {points[i].jd for i in r} for key, r in readings.items()}
    assert covered["de441_part_1"] == {T0 + 1} and covered["de441_part_2"] == {T0 + 1, T0 + 40}
    assert all(covered[key] == {T0 + 1, T0 + 40} for key in gen.COVER_WINDOW)


def test_a_drifting_second_reader_refuses_the_run():
    indexed = _indexed(SPANS)
    points = gen.grid_points([T0 + 1], *gen.window(indexed))
    with pytest.raises(gen.Refusal, match="de442 g000.*disagree"):
        _measure(points, indexed, drift={"de442": 1.0e-3})


def test_a_short_file_that_leaves_the_window_uncovered_is_refused():
    spans = dict(SPANS, de442s=(T0, T0 + 32))
    indexed = _indexed(spans)
    points = gen.grid_points([T0 + 40], *gen.window(indexed))
    with pytest.raises(gen.Refusal, match="de442s does not cover g000"):
        _measure(points, indexed)


# --- the rows ------------------------------------------------------------------------------------------------------


def test_a_difference_is_minuend_minus_subtrahend_with_its_norm_and_angle():
    a, b = (1.0, 0.0, 0.0), (1.0, 1.0e-6, 0.0)
    block = gen.difference(a, b, angle=True)
    assert block["values"] == [0.0, -1.0e-6, 0.0] and block["norm"] == 1.0e-6
    assert abs(block["angle_arcsec"] - 1.0e-6 * gen.ARCSEC_PER_RADIAN) < 1.0e-12
    assert "angle_arcsec" not in gen.difference(a, b, angle=False)
    assert all(block[f"{k}_bits"] == (bits(block[k]) if not isinstance(block[k], list) else [bits(v) for v in block[k]])
               for k in ("values", "norm", "angle_arcsec"))


def test_a_separation_is_well_conditioned_near_zero():
    a = (math.cos(0.3), math.sin(0.3), 0.0)
    tiny = 1.0e-3 / gen.ARCSEC_PER_RADIAN
    b = (math.cos(0.3 + tiny), math.sin(0.3 + tiny), 0.0)
    assert gen.separation_arcsec(a, a) == 0.0
    assert abs(gen.separation_arcsec(a, b) - 1.0e-3) < 1.0e-9


def test_a_second_file_of_a_fit_is_compacted_only_on_identical_bits():
    written = {"de440s": [1.0, 0.0, 2.0]}
    assert gen.state_entry("de440", [1.0, 0.0, 2.0], 0.0, written)["same_bits_as"] == "de440s"
    assert "values" in gen.state_entry("de440", [1.0, -0.0, 2.0], 0.0, written)  # ⭐ -0.0 is not 0.0 by bits
    assert "values" in gen.state_entry("de440", [1.0, 0.0, 2.0 + 2.0**-51], 0.0, written)
    assert "values" in gen.state_entry("de441_part_2", [1.0, 0.0, 2.0], 0.0, written)  # its twin is part 1


def _rows(stratum):
    indexed = _indexed(SPANS)
    lo, hi = gen.window(indexed)
    points = gen.grid_points([T0 + 1, T0 + 16, T0 + 40], lo, hi)
    edges, reasons = gen.edge_points(indexed, lo, hi)
    points += edges
    readings = _measure(points, indexed)
    return list(gen.iter_rows(points, readings, reasons, stratum)), points, readings, reasons


def test_inside_the_shared_days_both_files_of_one_fit_are_recorded_and_compared():
    rows, *_ = _rows(gen.GRID)
    shared = [r for r in rows if r["jd_tdb"] == T0 + 16 and r["target"] == 301 and r["centre"] == 399]
    assert len(shared) == 2
    for row in shared:
        assert set(row["states"]) == {key for key, _n, _f in gen.FILES}
        assert row["states"]["de441_part_2"] == {"same_bits_as": "de441_part_1",
                                                 **gen.patterned("jplephem_max_abs_delta", 0.0)}
        assert set(row["differences"]) == {"de441_part_1_minus_de440s", "de441_part_2_minus_de440s",
                                           "de442s_minus_de440s", "de442s_minus_de441_part_1",
                                           "de442s_minus_de441_part_2"}
    after = [r for r in rows if r["jd_tdb"] == T0 + 40 and r["section"] == "position"]
    assert all("de441_part_1" not in r["states"] for r in after)
    assert all(set(r["differences"]) == {"de441_part_2_minus_de440s", "de442s_minus_de440s",
                                         "de442s_minus_de441_part_2"} for r in after)


def test_an_angle_is_written_for_a_geocentric_position_and_nowhere_else():
    rows, *_ = _rows(gen.GRID)
    for row in rows:
        has = {"angle_arcsec" in block for block in row["differences"].values()}
        assert has == {row["section"] == "position" and row["centre"] == 399}


def test_the_record_edge_rows_carry_their_reasons_and_the_segments_own_pair():
    rows, points, *_ = _rows(gen.EDGE)
    assert rows and all(r["stratum"] == gen.EDGE and "record_boundary_in" in r for r in rows)
    assert {(r["target"], r["centre"]) for r in rows} == set(PAIRS)
    assert {r["target"]: r["target_name"] for r in rows if r["target"] in (1, 2, 3)} == {
        1: "mercury_barycentre", 2: "venus_barycentre", 3: "earth_moon_barycentre"}
    with pytest.raises(gen.Refusal, match="no name"):
        gen.name_of(11)
    assert len(rows) == 2 * sum(1 for p in points if p.stratum == gen.EDGE)


def test_the_summary_names_the_largest_difference_where_it_is_and_counts_above_each_level():
    rows, *_ = _rows(gen.GRID)
    summary = gen.summarise(iter(rows))
    entry = next(d for d in summary["differences"] if d["difference"] == "de442s_minus_de440s"
                 and d["target"] == 301 and d["centre"] == 399 and d["section"] == "position")
    assert entry["rows"] == 3 and entry["largest_norm"]["value"] == 2.0
    assert len(entry["angle_above_levels"]) == len(gen.LEVELS_ARCSEC)
    packaging = {(p["file"], p["section"]): p for p in summary["packaging"]}
    assert packaging[("de440", "position")]["different"] == 0
    assert packaging[("de441_part_2", "position")]["compared"] == 2 * 23
    assert summary["rows"] == {"position": 3 * 23, "velocity": 3 * 23}


def test_the_header_holds_to_the_contract(tmp_path):
    rows, points, readings, _reasons = _rows(gen.GRID)
    indexed = _indexed(SPANS)

    class Pin:
        def __init__(self, name):
            self.dataset, self.profile, self.size_bytes, self.sha256 = name, "p@1", 1, "0" * 64
            self.publisher, self.pinned_on, self.publisher_md5 = "x", "2026-01-01", "0" * 32

    pins = {key: Pin(name) for key, name, _f in gen.FILES}
    header = gen.build_header(
        stratum=gen.GRID, generator=Generator(repo="r", script="s", commit="0" * 40), pins=pins,
        kernels={key: Path(key) for key in pins}, indexed=indexed,
        libraries={"spiceypy": "a", "jplephem": "b", "numpy": "c"}, toolkit="T", lo=T0, hi=T0 + 64,
        grid={"values_sha256": "0" * 64, "instants": 3, "rule": "r"}, edges={"instants": 1, "points": 1, "rule": "r"},
        summary=gen.summarise(iter(rows)), readers=gen.reader_summary(points, readings, gen.GRID), budget_row="a-row")
    validate_header(header, where="t")
    from saakshi.fixture import write_jsonl

    written = write_jsonl(tmp_path / "f.jsonl", header, iter(rows), declared_sections=["position", "velocity"])
    assert written == len(rows)


def test_a_library_other_than_the_pin_is_refused_before_it_is_imported(monkeypatch):
    monkeypatch.setattr(gen.metadata, "version", lambda name: "0")
    monkeypatch.setitem(sys.modules, "spiceypy", None)
    with pytest.raises(gen.Refusal, match="not the pins"):
        gen.require_library_pins()


# --- refused before anything is read -----------------------------------------------------------------------------


def _git(repo: Path, *args: str) -> None:
    environment = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@example.invalid",
                       GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@example.invalid")
    subprocess.run(["git", "-c", "commit.gpgsign=false", *args], cwd=repo, env=environment, check=True,
                   capture_output=True)


def _run(tmp_path: Path, out: Path, budget_row: str = "a-row", terms: str | None = None
         ) -> subprocess.CompletedProcess:
    repo = tmp_path / "repo"
    if not repo.exists():
        (repo / "generators").mkdir(parents=True)
        shutil.copy2(SCRIPT, repo / "generators" / SCRIPT.name)
        shutil.copytree(ROOT / "src", repo / "src", ignore=shutil.ignore_patterns("__pycache__"))
        _git(repo, "init", "-q")
        _git(repo, "add", "-A")
        _git(repo, "commit", "-q", "-m", "one")
    nowhere = str(tmp_path / "nowhere")
    args = ["--kernels", nowhere, "--kernel-terms", terms or nowhere, "--grid-values", nowhere, "--grid-values-sha256",
            "0" * 64, "--budget-row", budget_row, "--out", str(out)]
    return subprocess.run([sys.executable, "-B", str(repo / "generators" / SCRIPT.name), *args], cwd=repo,
                          capture_output=True, text=True, timeout=120, check=False)


def test_an_existing_output_and_an_unstated_row_are_refused_first(tmp_path):
    out = tmp_path / "out"
    out.mkdir()
    held = out / gen.OUTPUTS[gen.EDGE]
    held.write_text("held\n", encoding="ascii")
    done = _run(tmp_path, out)
    assert done.returncode == 2 and "exists" in done.stderr
    assert held.read_text(encoding="ascii") == "held\n"
    done = _run(tmp_path, tmp_path / "fresh", budget_row=" padded ")
    assert done.returncode == 2 and "--budget-row" in done.stderr


def test_a_terms_page_other_than_the_one_read_or_a_missing_input_is_refused_not_crashed(tmp_path):
    page = tmp_path / "rules.html"
    page.write_text("<title>Rules</title>\n", encoding="ascii")
    done = _run(tmp_path, tmp_path / "fresh", terms=str(page))
    assert done.returncode == 2 and "terms page is not the one read" in done.stderr
    done = _run(tmp_path, tmp_path / "fresh")
    assert done.returncode == 2 and "REFUSED" in done.stderr and "Traceback" not in done.stderr


# --- the whole measurement on six small kernels written by the Toolkit ---------------------------------------------


def _write_kernel(path: Path, start: float, end: float, fit_offset: float) -> None:
    """A kernel of the publisher's segment shapes, each record's coefficients a function of its own start: two files
    of one fit therefore carry identical records wherever they overlap."""
    import spiceypy as sp

    handle = sp.spkopn(str(path), "synthetic", 0)
    try:
        for layout in _layouts(start, end):
            intlen = layout.intlen_days * 86400.0
            cdata = []
            for k in range(layout.records):
                t = layout.init_jd + k * layout.intlen_days
                for axis in range(3):
                    if layout.target in (199, 299):
                        cdata += [0.0, 0.0, 0.0]
                    else:
                        scale = 1.0e5 * layout.target * (axis + 1)
                        cdata += [scale + (t - T0) * 10.0 + fit_offset * (layout.target == 301),
                                  3.0e3 * (axis + 1), 1.0 * (round((t - T0) / layout.intlen_days) % 3)]
            sp.spkw02(handle, layout.target, layout.centre, "J2000", gen.et_seconds(start), gen.et_seconds(end),
                      f"t{layout.target}", intlen, layout.records, 2, cdata, gen.et_seconds(layout.init_jd))
    finally:
        sp.spkcls(handle)


def test_the_whole_measurement_on_six_written_kernels(tmp_path):
    pytest.importorskip("spiceypy")
    pytest.importorskip("jplephem")
    pytest.importorskip("numpy")
    offsets = {"de440s": 0.0, "de440": 0.0, "de441_part_1": 0.25, "de441_part_2": 0.25, "de442s": 2.0, "de442": 2.0}
    kernels = {}
    for key, name, _fit in gen.FILES:
        kernels[key] = tmp_path / name
        _write_kernel(kernels[key], *SPANS[key], offsets[key])
    indexed = gen.check_structures({key: gen.read_layouts(kernels[key]) for key, _n, _f in gen.FILES})
    lo, hi = gen.window(indexed)
    assert (lo, hi) == (T0, T0 + 64)
    points = gen.grid_points([T0 + 1, T0 + 16, T0 + 40], lo, hi)
    edges, reasons = gen.edge_points(indexed, lo, hi)
    points += edges
    readings = gen.measure(kernels, indexed, points)
    rows = list(gen.iter_rows(points, readings, reasons, gen.GRID))
    moon = next(r for r in rows if r["jd_tdb"] == T0 + 16 and r["target"] == 301 and r["centre"] == 0
                and r["section"] == "position")
    assert moon["states"]["de440"]["same_bits_as"] == "de440s"
    assert moon["states"]["de441_part_2"]["same_bits_as"] == "de441_part_1"
    assert moon["differences"]["de441_part_1_minus_de440s"]["values"] == [0.25, 0.25, 0.25]
    assert moon["differences"]["de442s_minus_de441_part_2"]["values"] == [1.75, 1.75, 1.75]
    mars = next(r for r in rows if r["jd_tdb"] == T0 + 1 and r["target"] == 4 and r["section"] == "position")
    assert set(mars["differences"]["de442s_minus_de440s"]["values"]) == {0.0}
    edge_rows = list(gen.iter_rows(points, readings, reasons, gen.EDGE))
    assert len(edge_rows) == 2 * len(edges)
    # ⭐ a second file of a fit differs from the first only where one of the two ends its coverage: there one is
    #    read at its last record's far end and the other at its next record's near end
    differing = [(r, key) for r in edge_rows for key, twin in gen.SAME_FIT_AS.items()
                 if key in r["states"] and twin in r["states"] and "values" in r["states"][key]]
    assert differing
    for row, key in differing:
        assert {key, gen.SAME_FIT_AS[key]} & set(row["segment_end_in"]), (row["epoch_id"], key)
    summary = gen.summarise(iter(edge_rows))
    assert sum(p["different"] for p in summary["packaging"]) == len(differing)
    floors = gen.reader_summary(points, readings, gen.GRID)
    assert all(f["states"] > 0 for f in floors)
