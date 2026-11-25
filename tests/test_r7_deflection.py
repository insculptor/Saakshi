"""Light deflection by the IAU's library: the geometry declared, the own-system rule, the disc, the three legs.

⭐ The geometry and the refusals run anywhere. The end-to-end half runs only where a build of the pinned library
(``R7_SOFA_BUILD``, ``R7_SOFA_SOURCE``), the two constants files (``R7_NAIF_GM``, ``R7_NAIF_RADII``) and the
short-span kernel (``cache/kernels/de440s.bsp``) are present.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import math
import os
import stat
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
_SPEC = importlib.util.spec_from_file_location("r7_deflection", ROOT / "generators" / "r7_deflection.py")
d = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = d
_SPEC.loader.exec_module(d)

from saakshi.fixture import Generator, bits  # noqa: E402

IDENTITY = Generator(repo="github.com/insculptor/Saakshi", script=d.SCRIPT, commit="0" * 40)
BY_ID = {x["id"]: x for x in d.DEFLECTORS}


def test_the_closest_approach_is_the_foot_of_the_perpendicular_held_to_the_ray():
    x_o, k = [0.0, 0.0, 0.0], [-1.0, 0.0, 0.0]  # source along +x, light travelling towards -x
    assert d.closest_approach([5.0, 3.0, 0.0], x_o, k, 10.0) == 5.0
    assert d.closest_approach([-5.0, 3.0, 0.0], x_o, k, 10.0) == 0.0  # behind the observer
    assert d.closest_approach([15.0, 3.0, 0.0], x_o, k, 10.0) == 10.0  # beyond the source


def test_a_ray_inside_the_disc_between_observer_and_source_is_found_and_no_other():
    x_o, k = [0.0, 0.0, 0.0], [-1.0, 0.0, 0.0]
    assert d.inside_disc([5.0, 0.5, 0.0], x_o, k, 10.0, 1.0)[0]
    assert not d.inside_disc([5.0, 1.5, 0.0], x_o, k, 10.0, 1.0)[0]  # outside the radius
    assert not d.inside_disc([12.0, 0.5, 0.0], x_o, k, 10.0, 1.0)[0]  # behind the source
    assert not d.inside_disc([-2.0, 0.5, 0.0], x_o, k, 10.0, 1.0)[0]  # behind the observer


def test_a_body_never_deflects_light_from_its_own_system():
    assert not d.applicable(10, BY_ID[10]) and d.applicable(301, BY_ID[10])
    assert not d.applicable(299, BY_ID[2]) and not d.applicable(2, BY_ID[2])
    for system in (5, 6, 7, 8):
        assert not d.applicable(system, BY_ID[system])
        assert d.applicable(9, BY_ID[system]) and d.applicable(10, BY_ID[system])
    assert all(d.applicable(301, x) for x in d.DEFLECTORS)


def test_the_longitude_of_date_is_taken_through_the_matrix_and_the_obliquity():
    identity = [1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0]
    assert d.longitude_of_date([0.0, 1.0, 0.0], identity, 0.0) == math.pi / 2
    assert abs(d.longitude_of_date([0.0, -1.0, 0.0], identity, 0.0) - 1.5 * math.pi) < 1e-15
    # ⭐ R1(eps): an ecliptic direction at 45 degrees, written in the equatorial frame, reads back as 45 degrees
    eps, h = 0.4, math.sqrt(0.5)
    equatorial = [h, h * math.cos(eps), h * math.sin(eps)]
    assert abs(d.longitude_of_date(equatorial, identity, eps) - math.pi / 4) < 1e-15
    # ⭐ the matrix row-major: a quarter turn about z, [[0,-1,0],[1,0,0],[0,0,1]], takes x to y (90 degrees);
    # read column-major it would take x to -y (270 degrees)
    quarter = [0.0, -1.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0]
    assert d.longitude_of_date([1.0, 0.0, 0.0], quarter, 0.0) == math.pi / 2


def test_a_longitude_difference_is_folded_and_in_arcseconds():
    assert abs(d.wrapped_arcsec(1e-6, 2 * math.pi - 1e-6) - 2e-6 * d.ARCSEC_PER_RADIAN) < 1e-9


def _fake(tmp_path, lines):
    path = tmp_path / "driver"
    path.write_text("#!/bin/sh\ncat >/dev/null\n" + "".join(f"echo '{line}'\n" for line in lines))
    path.chmod(path.stat().st_mode | stat.S_IEXEC)
    return path


def test_the_driver_is_held_to_its_version_its_shape_and_its_count(tmp_path):
    row = "L 0 " + " ".join([bits(1.0)] * 12)
    assert d.run_driver(_fake(tmp_path, ["V deflection_legs 1", row]), ["C 0"])[0]["natural"] == [1.0] * 3
    for lines, match in ((["V other", row], "stopped"), (["V deflection_legs 1", row[:-17]], "answered"),
                         (["V deflection_legs 1"], "answers for")):
        with pytest.raises(d.Refusal, match=match):
            d.run_driver(_fake(tmp_path, lines), ["C 0"])


def test_a_frame_file_of_another_digest_or_reference_is_refused(tmp_path):
    path = tmp_path / "frame.jsonl"
    path.write_text(json.dumps({"record": "header", "reference": "R1"}) + "\n")
    with pytest.raises(d.Refusal, match="not the one named"):
        d.read_frame(path, "0" * 64)
    with pytest.raises(d.Refusal, match="not one this reference wrote"):
        d.read_frame(path, hashlib.sha256(path.read_bytes()).hexdigest())


# --------------------------------------------------------------------------------------
# End to end, where everything is named
# --------------------------------------------------------------------------------------


def _frame_file(tmp_path, jds):
    identity = [1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0]
    rows = [{"record": "header", "reference": "R7", "title": "a frame"}]
    for k, jd in enumerate(jds):
        base = {"epoch_id": f"e{k:03d}", "jd_tdb_bits": bits(jd)}
        rows.append({"section": "bias_precession_nutation", **base, "value_bits": [bits(x) for x in identity]})
        rows.append({"section": "true_obliquity", **base, "value_bits": bits(0.4090928)})
    path = tmp_path / "frame.jsonl"
    path.write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    return path, hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture
def everything(monkeypatch, tmp_path):
    names = {k: os.environ.get(k) for k in ("R7_SOFA_BUILD", "R7_SOFA_SOURCE", "R7_NAIF_GM", "R7_NAIF_RADII")}
    kernel = ROOT / "cache" / "kernels" / "de440s.bsp"
    if not all(names.values()) or not kernel.is_file():
        pytest.skip("the library build, the constants files or the kernel are not named here")
    pytest.importorskip("spiceypy", reason="the SPICE binding is absent")
    monkeypatch.setattr(d, "generator_for", lambda script: IDENTITY)
    return names, kernel


def test_a_short_run_writes_three_legs_and_keeps_the_own_system_rule(everything, tmp_path):
    names, kernel = everything
    frame, digest = _frame_file(tmp_path, [2451545.0, 2460000.5])
    d.main(["--kernel", str(kernel), "--gm", names["R7_NAIF_GM"], "--radii", names["R7_NAIF_RADII"], "--frame",
            str(frame), "--frame-sha256", digest, "--sofa-build", names["R7_SOFA_BUILD"], "--sofa-source",
            names["R7_SOFA_SOURCE"], "--out", str(tmp_path / "out")])
    lines = [json.loads(x) for x in (tmp_path / "out" / d.VALUES_PATH).read_text().splitlines()]
    header, rows = lines[0], lines[1:]
    assert header["reference"] == "R7" and "budget_row" not in header
    assert len(rows) == 2 * len(d.TARGETS)
    for row in rows:
        states = {x["deflector"]: x["state"] for x in row["deflectors"]}
        if row["target"] == "sun":
            assert states["sun"] == "not_applicable_own_system"
        if row["target"] == "venus":
            assert states["venus_barycentre"] == "not_applicable_own_system"
        if row["section"] == "deflection":
            assert 1e-8 < abs(row["potential_term_arcsec"]) < 1e-5  # present; the library states about 0.4 µas
            assert row["delta_longitude_as_called_arcsec_bits"] == bits(row["delta_longitude_as_called_arcsec"])
            assert row["order_applied"] == [x["deflector"] for x in sorted(
                (x for x in row["deflectors"] if x["state"] == "applied"), key=lambda x: -x["em_au"])]
