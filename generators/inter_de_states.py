"""Three development ephemerides side by side over one window, in every file they are distributed in, by two readers.

What is recorded: the geometric state — position and velocity, in the frame the files carry (J2000), at TDB
instants — of twelve points: the Sun, the Moon, Mercury, Venus, the system barycentres of Mars to Pluto, the Earth
and the Earth-Moon barycentre. Each is read out of six files of three fits:

* **DE440** — ``de440s.bsp`` and ``de440.bsp``;
* **DE441** — ``de441_part-1.bsp`` and ``de441_part-2.bsp``, two files that share 32 days;
* **DE442** — ``de442s.bsp`` and ``de442.bsp``.

And beside them the differences between the fits — in kilometres, and for a geocentric position also as the angle
between the two directions as seen from the geocentre.

The instants, inside **the window** (the span of ``de440s.bsp``, read from the file):

* **the geocentric grid** — the distinct instants of a geocentric-vector values file, read by its sha256. Every
  point relative to the solar-system barycentre, and every point but the Earth relative to the geocentre;
* **the record edges** — every instant at which a segment of any of the six files has a record boundary (the
  outer ends of its first and last records included), or at which its coverage ends. There, the segment's own
  state — its target relative to its centre, as the files carry it — from every file that covers the instant.

The readers: **CSPICE** (through ``spiceypy``) with exactly one file in its pool — the pool is cleared before each
file, so no loading order can choose a segment; and **jplephem** on the same file, composing a state as the sum of
the file's own segments at the nearest common ancestor. The value written is CSPICE's, with its bit pattern;
jplephem's largest difference from it is written beside it. ⛔ **Never averaged**: a state on which the two differ
by more than :data:`READER_AGREEMENT` of its section's norm refuses the run, and nothing is written.

⭐ **Where both DE441 files cover an instant, both are read, both are recorded and both are compared** with the other
fits. ⛔ Neither is chosen: which file answers inside the shared days is a reader's rule, and it is not this file's.

⭐ **Where a second file of a fit returns the same bits as the first**, its entry says so (``same_bits_as``) instead
of repeating them; where it does not, its own values are written. The differences between fits are taken from each
fit's file whose span is the window (``de440s``, ``de442s``) and, for DE441, which has none, from each of its files
that covers the instant.

⛔ **No band, no class but ``reference_only``, no verdict.** What a difference between fits means for anyone is
decided elsewhere; this file is the measurement that decision reads.

⛔ **Recorder, never explainer.** Nothing here says how either reader evaluates a file, or why two fits differ.

Refused before anything is read, in this order: a dirty or commitless tree; an output that exists; a budget row not
given exactly; the publisher's terms page that is not the one read; a library whose version is not pinned below; any
of the six files that is not its pin; a values file whose digest is not the one given. Refused while reading: two files whose segment structure
differs; a segment pair carried twice in one file; a file that leaves part of the window uncovered where the window
must be covered; an instant that does not convert exactly; a non-finite return; two readers that disagree.

Usage (a clean tree, the pinned libraries of ``requirements.txt``):
    python generators/inter_de_states.py --kernels DIR --kernel-terms FILE \\
        --grid-values VALUES.jsonl --grid-values-sha256 HEX --budget-row ROW --out DIR
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata as metadata
import json
import math
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterator, Mapping, Sequence

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from saakshi.fixture import Header, bits, describe_reserved_names, patterned, write_jsonl  # noqa: E402
from saakshi.kernels import (  # noqa: E402
    PINS, PUBLISHER_CHECKSUMS, KernelIdentityError, oracle_identity, sha256_file, verify,
)
from saakshi.provenance import generator_for, host_record, today  # noqa: E402

#: The files, in the order they are read and written: ``(key, the publisher's file name, the fit)``. ⭐ The key is
#: the file name made a JSON key; the fit is the publisher's name for the ephemeris the file is of.
FILES: tuple[tuple[str, str, str], ...] = (
    ("de440s", "de440s.bsp", "DE440"),
    ("de440", "de440.bsp", "DE440"),
    ("de441_part_1", "de441_part-1.bsp", "DE441"),
    ("de441_part_2", "de441_part-2.bsp", "DE441"),
    ("de442s", "de442s.bsp", "DE442"),
    ("de442", "de442.bsp", "DE442"),
)
#: The file whose span is the window.
WINDOW_FILE = "de440s"
#: Files that must cover every instant of the window: the window's own, and the other short file.
COVER_WINDOW = ("de440s", "de440", "de442s", "de442")
#: A second file of a fit, and the earlier file of the same fit whose bits it is compared with.
SAME_FIT_AS: dict[str, str] = {"de440": "de440s", "de441_part_2": "de441_part_1", "de442": "de442s"}
#: The files the differences between fits are taken from.
DIFFERENCE_FILES: dict[str, tuple[str, ...]] = {
    "DE440": ("de440s",),
    "DE441": ("de441_part_1", "de441_part_2"),
    "DE442": ("de442s",),
}
#: The pairs of fits differenced, the minuend first.
FIT_PAIRS: tuple[tuple[str, str], ...] = (("DE441", "DE440"), ("DE442", "DE440"), ("DE442", "DE441"))

#: The points, by the codes the files carry them under, and what each code names in these files.
TARGETS: dict[int, str] = {
    10: "sun", 301: "moon", 199: "mercury", 299: "venus", 4: "mars_barycentre", 5: "jupiter_barycentre",
    6: "saturn_barycentre", 7: "uranus_barycentre", 8: "neptune_barycentre", 9: "pluto_barycentre",
    399: "earth", 3: "earth_moon_barycentre",
}
SOLAR_SYSTEM_BARYCENTRE, GEOCENTRE = 0, 399
CENTRES = (SOLAR_SYSTEM_BARYCENTRE, GEOCENTRE)

SECTIONS: tuple[tuple[str, str, slice], ...] = (("position", "km", slice(0, 3)), ("velocity", "km/s", slice(3, 6)))
GRID, EDGE = "geocentric_grid", "record_edge"
OUTPUTS = {GRID: "inter-de-geocentric-grid.jsonl", EDGE: "inter-de-record-edges.jsonl"}

J2000 = 2451545.0
SECONDS_PER_DAY = 86400.0
ARCSEC_PER_RADIAN = 648000.0 / math.pi
#: Reporting levels for the angle counts. ⛔ Not bands: a count above a level says how many, never "fails".
LEVELS_ARCSEC = (1.0e-4, 1.0e-3, 1.0e-2, 1.0e-1, 1.0)

#: ⭐ **When two readers of one file disagree**, as a fraction of the section's norm: 2**-44, i.e. 256 times 2**-52.
#: Set from two numbers measured before this file existed, ⛔ not from anything it reads: the two readers were found
#: to differ by about one 2**-52 of the norm on a short-span file of the first fit (its declared floor, 3.0e-16 in
#: position and 5.2e-16 in velocity), and the one reader-side failure this repository has recorded — an instant
#: handed over in a single division — moved a state by 2.0e-5 km, about 5e-11 of the norm of the leg it moved. A
#: threshold must sit between the two; this one is the power of two 256 times above the first. Where the norm is
#: zero, the two must agree exactly.
READER_AGREEMENT = 2.0**-44

#: The libraries, as ``requirements.txt`` pins them. ⛔ Another version is refused before either is imported.
LIBRARY_PINS = {"spiceypy": "8.2.0", "jplephem": "2.23", "numpy": "2.5.1"}

#: The publisher's terms for its kernels, as read: the page, and the sha256 of the bytes read.
KERNEL_TERMS = {
    "url": "https://naif.jpl.nasa.gov/naif/rules.html",
    "sha256": "ae85f851646e7c4f0a762db852907bc090a2ab50c815eb2a6cd8639e96b7e047",
}


class Refusal(Exception):
    """A condition under which nothing may be recorded."""


# --------------------------------------------------------------------------------------------------------------
# The instants
# --------------------------------------------------------------------------------------------------------------


def grid_instants(values_path: Path, expected_sha256: str) -> list[float]:
    """The distinct TDB Julian dates of a geocentric-vector values file, ascending — refused unless its digest is given."""
    data = values_path.read_bytes()
    actual = hashlib.sha256(data).hexdigest()
    if actual != expected_sha256:
        raise Refusal(f"the values file's sha256 is {actual}, not {expected_sha256}")
    seen: dict[str, float] = {}
    for number, line in enumerate(data.decode("utf-8").splitlines()):
        record = json.loads(line)
        if record.get("record") != "row":
            continue
        value, pattern = record["jd_tdb"], record["jd_tdb_bits"]
        if bits(float(value)) != pattern:
            raise Refusal(f"line {number + 1}: jd_tdb and its pattern are different numbers")
        seen[pattern] = float(value)
    if not seen:
        raise Refusal("the values file holds no instant")
    return sorted(seen.values())


def et_seconds(jd: float) -> float:
    """TDB seconds past J2000 for a Julian date — ⛔ refused unless the conversion is exact both ways."""
    et = (jd - J2000) * SECONDS_PER_DAY
    if not math.isfinite(et) or et != math.floor(et) or et / SECONDS_PER_DAY + J2000 != jd:
        raise Refusal(f"JD {jd!r} does not convert exactly to whole TDB seconds past J2000")
    return et


def split_jd(jd: float) -> tuple[float, float]:
    """The whole day and its fraction, each exact: how the instant is handed to the second reader."""
    whole = float(math.floor(jd))
    return whole, jd - whole


@dataclass(frozen=True)
class Layout:
    """One segment as its file carries it."""

    target: int
    centre: int
    start_jd: float
    end_jd: float
    init_jd: float
    intlen_days: float
    records: int
    frame: int
    data_type: int

    def boundaries(self) -> list[float]:
        """Every record boundary, the outer ends of the first and the last record included."""
        return [self.init_jd + k * self.intlen_days for k in range(self.records + 1)]

    def covers(self, jd: float) -> bool:
        return self.start_jd <= jd <= self.end_jd

    def as_json(self) -> dict[str, Any]:
        return {"target": self.target, "centre": self.centre, **patterned("start_jd", self.start_jd),
                **patterned("end_jd", self.end_jd), **patterned("init_jd", self.init_jd),
                **patterned("intlen_days", self.intlen_days), "records": self.records, "frame": self.frame,
                "data_type": self.data_type}


def check_structures(layouts: Mapping[str, Sequence[Layout]]) -> dict[str, dict[tuple[int, int], Layout]]:
    """Index each file's segments by ``(target, centre)`` — ⛔ refused if a pair is carried twice, or if two files
    carry different pairs: a state composed from one file's segments must mean the same in every other."""
    indexed: dict[str, dict[tuple[int, int], Layout]] = {}
    for key, segments in layouts.items():
        pairs: dict[tuple[int, int], Layout] = {}
        for layout in segments:
            pair = (layout.target, layout.centre)
            if pair in pairs:
                raise Refusal(f"{key}: the pair {pair} is carried by two segments; which answers is a load order")
            pairs[pair] = layout
        indexed[key] = pairs
    structures = {key: sorted(pairs) for key, pairs in indexed.items()}
    first = next(iter(structures.values()))
    for key, pairs in structures.items():
        if pairs != first:
            raise Refusal(f"{key} carries the segments {pairs}, not {first}")
    return indexed


def parents(pairs: Mapping[tuple[int, int], Layout]) -> dict[int, int]:
    return {target: centre for (target, centre) in pairs}


def chain(parent: Mapping[int, int], body: int) -> list[int]:
    """``body``, then each centre in turn, ending at the solar-system barycentre."""
    out = [body]
    while out[-1] != SOLAR_SYSTEM_BARYCENTRE:
        if out[-1] not in parent:
            raise Refusal(f"no segment carries {out[-1]} towards the solar-system barycentre")
        out.append(parent[out[-1]])
    return out


def legs(parent: Mapping[int, int], target: int, centre: int) -> tuple[list[tuple[int, int]], list[tuple[int, int]]]:
    """The segments added and the segments subtracted to compose ``target`` relative to ``centre``, at their
    nearest common ancestor: ``(added, subtracted)``, each a list of ``(target, centre)``."""
    up, down = chain(parent, target), chain(parent, centre)
    common = next(body for body in up if body in down)
    added = [(body, parent[body]) for body in up[: up.index(common)]]
    subtracted = [(body, parent[body]) for body in down[: down.index(common)]]
    return added, subtracted


@dataclass(frozen=True)
class Point:
    """One state asked of every file that covers it."""

    stratum: str
    epoch_id: str
    jd: float
    target: int
    centre: int


def window(indexed: Mapping[str, Mapping[tuple[int, int], Layout]]) -> tuple[float, float]:
    """The span of the window's file: the instants every one of its segments covers."""
    segments = indexed[WINDOW_FILE].values()
    return max(s.start_jd for s in segments), min(s.end_jd for s in segments)


def covering(pairs: Mapping[tuple[int, int], Layout], needed: Sequence[tuple[int, int]], jd: float) -> bool:
    return all(pairs[pair].covers(jd) for pair in needed)


def grid_points(instants: Sequence[float], lo: float, hi: float) -> list[Point]:
    """Every point relative to the solar-system barycentre, and every point but the Earth relative to the geocentre."""
    out: list[Point] = []
    for index, jd in enumerate(instants):
        if not lo <= jd <= hi:
            raise Refusal(f"grid instant {jd!r} is outside the window [{lo!r}, {hi!r}]")
        et_seconds(jd)
        for target in TARGETS:
            for centre in CENTRES:
                if target != centre:
                    out.append(Point(GRID, f"g{index:03d}", jd, target, centre))
    return out


def edge_points(indexed: Mapping[str, Mapping[tuple[int, int], Layout]], lo: float, hi: float
                ) -> tuple[list[Point], dict[tuple[float, int, int], dict[str, list[str]]]]:
    """The record edges in the window, and for each the files it is a boundary or a coverage end of."""
    reasons: dict[tuple[float, int, int], dict[str, list[str]]] = {}
    for key, _name, _fit in FILES:
        for (target, centre), layout in indexed[key].items():
            for jd in layout.boundaries():
                if lo <= jd <= hi:
                    reasons.setdefault((jd, target, centre), {"record_boundary_in": [], "segment_end_in": []})[
                        "record_boundary_in"].append(key)
            for jd in (layout.start_jd, layout.end_jd):
                if lo <= jd <= hi:
                    reasons.setdefault((jd, target, centre), {"record_boundary_in": [], "segment_end_in": []})[
                        "segment_end_in"].append(key)
    instants = sorted({jd for (jd, _t, _c) in reasons})
    index = {jd: i for i, jd in enumerate(instants)}
    points = []
    for jd, target, centre in sorted(reasons):
        et_seconds(jd)
        points.append(Point(EDGE, f"e{index[jd]:05d}", jd, target, centre))
    return points, reasons


# --------------------------------------------------------------------------------------------------------------
# The two readers, one file at a time
# --------------------------------------------------------------------------------------------------------------


def require_library_pins() -> dict[str, str]:
    """⛔ Refused before any reader is imported: an unpinned library reads under the same name."""
    found = {}
    for name, pinned in LIBRARY_PINS.items():
        try:
            found[name] = metadata.version(name)
        except metadata.PackageNotFoundError:
            found[name] = "absent"
    if found != LIBRARY_PINS:
        raise Refusal(f"the libraries are {found}, not the pins {LIBRARY_PINS}")
    return found


def read_layouts(path: Path) -> list[Layout]:
    from jplephem.spk import SPK

    spk = SPK.open(str(path))
    try:
        out = []
        for segment in spk.segments:
            init, intlen, coefficients = segment.load_array()
            out.append(Layout(target=int(segment.target), centre=int(segment.center),
                              start_jd=float(segment.start_jd), end_jd=float(segment.end_jd),
                              init_jd=float(init), intlen_days=float(intlen), records=int(coefficients.shape[1]),
                              frame=int(segment.frame), data_type=int(segment.data_type)))
        return out
    finally:
        spk.close()


class Readers:
    """CSPICE and jplephem, both on one file. ⛔ CSPICE's pool holds this file and nothing else."""

    def __init__(self, path: Path, pairs: Mapping[tuple[int, int], Layout]) -> None:
        import spiceypy as sp
        from jplephem.spk import SPK

        self._sp = sp
        sp.kclear()
        sp.furnsh(str(path))
        if sp.ktotal("ALL") != 1:
            raise Refusal(f"the CSPICE pool holds {sp.ktotal('ALL')} files, not one")
        self._spk = SPK.open(str(path))
        self._parent = parents(pairs)

    def close(self) -> None:
        self._spk.close()
        self._sp.kclear()

    def cspice(self, target: int, centre: int, jd: float) -> tuple[float, ...]:
        state, _light_time = self._sp.spkgeo(target, et_seconds(jd), "J2000", centre)
        return tuple(float(v) for v in state)

    def jplephem(self, target: int, centre: int, jd: float) -> tuple[float, ...]:
        import numpy as np

        whole, fraction = split_jd(jd)
        added, subtracted = legs(self._parent, target, centre)
        total = np.zeros(6)
        for sign, group in ((1.0, added), (-1.0, subtracted)):
            for body, parent in group:
                position, velocity = self._spk[parent, body].compute_and_differentiate(whole, fraction)
                total += sign * np.concatenate([position, velocity / SECONDS_PER_DAY])
        return tuple(float(v) for v in total)


@dataclass
class Reading:
    """One file's answer for one point: CSPICE's state, and jplephem's largest difference from it per section."""

    state: tuple[float, ...]
    deltas: tuple[float, float]


def norm(values: Sequence[float]) -> float:
    return math.hypot(*values)


def reader_deltas(cspice: Sequence[float], other: Sequence[float], *, where: str) -> tuple[float, float]:
    """jplephem's largest difference from CSPICE per section — ⛔ refused where the two disagree."""
    if not all(math.isfinite(v) for v in (*cspice, *other)):
        raise Refusal(f"{where}: a reader returned a non-finite value")
    out = []
    for name, _unit, part in SECTIONS:
        delta = max(abs(a - b) for a, b in zip(cspice[part], other[part]))
        scale = norm(cspice[part])
        if delta > READER_AGREEMENT * scale:  # ⭐ a zero norm admits no difference at all: exact agreement
            raise Refusal(f"{where}: the readers disagree on the {name} by {delta!r} against a norm of {scale!r}; "
                          "⛔ nothing is averaged and nothing is written")
        out.append(delta)
    return out[0], out[1]


def measure(kernels: Mapping[str, Path], indexed: Mapping[str, Mapping[tuple[int, int], Layout]],
            points: Sequence[Point], *, open_readers: Callable[..., Readers] = Readers
            ) -> dict[str, dict[int, Reading]]:
    """Every point from every file that covers it, one file at a time."""
    out: dict[str, dict[int, Reading]] = {}
    for key, _name, _fit in FILES:
        pairs = indexed[key]
        parent = parents(pairs)
        readers = open_readers(kernels[key], pairs)
        answered: dict[int, Reading] = {}
        try:
            for index, point in enumerate(points):
                if point.stratum == GRID:
                    added, subtracted = legs(parent, point.target, point.centre)
                    needed = added + subtracted
                else:
                    needed = [(point.target, point.centre)]
                if not covering(pairs, needed, point.jd):
                    if key in COVER_WINDOW:
                        raise Refusal(f"{key} does not cover {point.epoch_id} (JD {point.jd!r}), inside the window")
                    continue
                state = readers.cspice(point.target, point.centre, point.jd)
                other = readers.jplephem(point.target, point.centre, point.jd)
                where = f"{key} {point.epoch_id} {point.target}/{point.centre}"
                answered[index] = Reading(state, reader_deltas(state, other, where=where))
        finally:
            readers.close()
        out[key] = answered
    return out


# --------------------------------------------------------------------------------------------------------------
# The rows — the differences are the one computation this file makes
# --------------------------------------------------------------------------------------------------------------


def separation_arcsec(a: Sequence[float], b: Sequence[float]) -> float:
    """The angle between two directions, by the arctangent of the cross and dot products (well-conditioned near 0)."""
    cross = (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])
    return math.atan2(norm(cross), sum(x * y for x, y in zip(a, b))) * ARCSEC_PER_RADIAN


def difference(minuend: Sequence[float], subtrahend: Sequence[float], *, angle: bool) -> dict[str, Any]:
    values = [a - b for a, b in zip(minuend, subtrahend)]
    block = {**patterned("values", values), **patterned("norm", norm(values))}
    if angle:
        block.update(patterned("angle_arcsec", separation_arcsec(minuend, subtrahend)))
    return block


def state_entry(key: str, values: Sequence[float], delta: float, written: Mapping[str, Sequence[float]]
                ) -> dict[str, Any]:
    """One file's entry: its values, or — where the earlier file of its fit returned the same bits — that file's key."""
    twin = SAME_FIT_AS.get(key)
    if twin in written and [bits(v) for v in written[twin]] == [bits(v) for v in values]:
        return {"same_bits_as": twin, **patterned("jplephem_max_abs_delta", delta)}
    return {**patterned("values", list(values)), **patterned("jplephem_max_abs_delta", delta)}


def iter_rows(points: Sequence[Point], readings: Mapping[str, Mapping[int, Reading]],
              reasons: Mapping[tuple[float, int, int], Mapping[str, list[str]]], stratum: str) -> Iterator[dict]:
    """The rows of one stratum, in point order, position before velocity."""
    for index, point in enumerate(points):
        if point.stratum != stratum:
            continue
        for section, (name, unit, part) in enumerate(SECTIONS):
            values: dict[str, Sequence[float]] = {}
            states: dict[str, Any] = {}
            for key, _file, _fit in FILES:
                reading = readings[key].get(index)
                if reading is None:
                    continue
                states[key] = state_entry(key, reading.state[part], reading.deltas[section], values)
                values[key] = reading.state[part]
            differences = {}
            angle = name == "position" and point.centre == GEOCENTRE
            for minuend_fit, subtrahend_fit in FIT_PAIRS:
                for a in DIFFERENCE_FILES[minuend_fit]:
                    for b in DIFFERENCE_FILES[subtrahend_fit]:
                        if a in values and b in values:
                            differences[f"{a}_minus_{b}"] = difference(values[a], values[b], angle=angle)
            row: dict[str, Any] = {"epoch_id": point.epoch_id, "stratum": stratum, **patterned("jd_tdb", point.jd),
                                   "target": point.target, "target_name": TARGETS.get(point.target, "segment_body"),
                                   "centre": point.centre, "section": name, "unit": unit}
            if stratum == EDGE:
                row.update({k: list(v) for k, v in reasons[(point.jd, point.target, point.centre)].items()})
            row["states"] = states
            row["differences"] = differences
            yield row


# --------------------------------------------------------------------------------------------------------------
# The summary — levels and places, never bands
# --------------------------------------------------------------------------------------------------------------


def _at(row: Mapping[str, Any]) -> dict[str, Any]:
    return {"epoch_id": row["epoch_id"], **patterned("jd_tdb", row["jd_tdb"])}


def summarise(rows: Iterator[dict]) -> dict[str, Any]:
    """Per difference, point, centre and section: how many rows, the largest norm and angle, and where."""
    differences: dict[tuple, dict] = {}
    packaging: dict[tuple, dict] = {}
    count = {name: 0 for name, _u, _p in SECTIONS}
    for row in rows:
        count[row["section"]] += 1
        for key, entry in row["states"].items():
            twin = SAME_FIT_AS.get(key)
            if twin is None or twin not in row["states"]:
                continue
            p = packaging.setdefault((key, twin, row["section"]), {"compared": 0, "bit_identical": 0, "largest": None})
            p["compared"] += 1
            if "same_bits_as" in entry:
                p["bit_identical"] += 1
                continue
            mine = entry["values"]
            theirs = row["states"][twin].get("values")
            if theirs is None:  # its twin itself repeats an earlier file's bits; no twin of a twin exists here
                raise Refusal(f"{key}: its twin {twin} carries no values")
            largest = max(abs(x - y) for x, y in zip(mine, theirs))
            if p["largest"] is None or largest > p["largest"]["value"]:
                p["largest"] = {**patterned("value", largest), **_at(row), "target": row["target"],
                                "centre": row["centre"]}
        for name, block in row["differences"].items():
            k = (name, row["target"], row["centre"], row["section"])
            d = differences.setdefault(k, {"rows": 0, "norm": None, "angle": None,
                                           "above": [0] * len(LEVELS_ARCSEC)})
            d["rows"] += 1
            if d["norm"] is None or block["norm"] > d["norm"]["value"]:
                d["norm"] = {**patterned("value", block["norm"]), **_at(row)}
            if "angle_arcsec" in block:
                if d["angle"] is None or block["angle_arcsec"] > d["angle"]["value"]:
                    d["angle"] = {**patterned("value", block["angle_arcsec"]), **_at(row)}
                for i, level in enumerate(LEVELS_ARCSEC):
                    d["above"][i] += block["angle_arcsec"] > level
    return {
        "rows": count,
        "levels_arcsec": [f"{level:g}" for level in LEVELS_ARCSEC],
        "levels_meaning": "reporting levels for the angle counts below. ⛔ Not bands: nothing passes or fails here",
        "differences": [
            {"difference": name, "target": target, "centre": centre, "section": section, "rows": d["rows"],
             "largest_norm": d["norm"],
             **({"largest_angle_arcsec": d["angle"], "angle_above_levels": d["above"]} if d["angle"] else {})}
            for (name, target, centre, section), d in sorted(differences.items(), key=lambda item: item[0])
        ],
        "packaging": [
            {"file": key, "compared_with": twin, "section": section, "compared": p["compared"],
             "bit_identical": p["bit_identical"], "different": p["compared"] - p["bit_identical"],
             "largest_component_difference": p["largest"]}
            for (key, twin, section), p in sorted(packaging.items())
        ],
    }


def reader_summary(points: Sequence[Point], readings: Mapping[str, Mapping[int, Reading]], stratum: str
                   ) -> list[dict[str, Any]]:
    """Per file and section: how many states, how many the readers returned bit for bit, and the largest
    difference relative to the norm — the measured floor under the refusal threshold."""
    out = []
    for key, _file, _fit in FILES:
        for section, (name, _unit, part) in enumerate(SECTIONS):
            states = identical = no_norm = 0
            worst: dict[str, Any] | None = None
            for index, reading in readings[key].items():
                point = points[index]
                if point.stratum != stratum:
                    continue
                states += 1
                delta = reading.deltas[section]
                identical += delta == 0.0
                scale = norm(reading.state[part])
                if scale == 0.0:
                    no_norm += 1
                    continue
                relative = delta / scale
                if worst is None or relative > worst["relative"]:
                    worst = {**patterned("relative", relative), **patterned("max_abs_delta", delta),
                             "epoch_id": point.epoch_id, **patterned("jd_tdb", point.jd), "target": point.target,
                             "centre": point.centre}
            out.append({"file": key, "section": name, "states": states, "max_abs_delta_zero": identical,
                        "rows_with_no_norm": no_norm, "largest_relative_delta": worst})
    return out


# --------------------------------------------------------------------------------------------------------------
# The header
# --------------------------------------------------------------------------------------------------------------

ROW_SCHEMA = {
    "epoch_id": "g<index> for the geocentric grid's instants in ascending order; e<index> for the record-edge "
                "instants in ascending order",
    "stratum": f"{GRID} | {EDGE}",
    "jd_tdb": "the instant, a TDB Julian date, exactly as handed to both readers (CSPICE as whole TDB seconds past "
              "J2000, converted exactly; jplephem as the whole day and its fraction, each exact)",
    "jd_tdb_bits": "IEEE-754 bit pattern of jd_tdb",
    "target": "the code of the point whose state this is, as the files carry it",
    "target_name": "what that code names in these files (segment_body: a code no other row names)",
    "centre": "the code the state is relative to: 0 the solar-system barycentre, 399 the geocentre; in a record-"
              "edge row, the segment's own centre",
    "section": "position | velocity",
    "unit": "km | km/s",
    "record_boundary_in": "record-edge rows: the files whose segment for this pair has a record boundary here",
    "segment_end_in": "record-edge rows: the files whose segment for this pair begins or ends its coverage here",
    "states": "per file that covers the instant, in reading order: `values` (CSPICE's three components) with "
              "`values_bits`, or `same_bits_as` naming the earlier file of the same fit whose three components "
              "these are bit for bit; and `jplephem_max_abs_delta` (with bits): jplephem's largest component "
              "difference from CSPICE on this file, in this row's unit",
    "differences": "per pair of fits, `<minuend file>_minus_<subtrahend file>`: `values` (componentwise, CSPICE's "
                   "values), `norm` (of that difference), and on a geocentric position `angle_arcsec` — the angle "
                   "between the two position vectors, in arcseconds. Each with its bits",
}


def build_header(*, stratum: str, generator, pins: Mapping[str, Any], kernels: Mapping[str, Path],
                 indexed: Mapping[str, Mapping[tuple[int, int], Layout]], libraries: Mapping[str, str],
                 toolkit: str, lo: float, hi: float, grid: Mapping[str, Any], edges: Mapping[str, Any],
                 summary: Mapping[str, Any], readers: Sequence[Mapping[str, Any]], budget_row: str) -> Header:
    return Header(
        fixture_kind="numeric_pin",
        reference="R2",
        generator=generator,
        generated=today(),
        title="three development ephemerides over one window, in every file they are distributed in, by two readers"
              + (" — the geocentric grid" if stratum == GRID else " — the record edges of every segment"),
        oracle={
            "implementation": "CSPICE",
            "toolkit_version": toolkit,
            "called_via": {"binding": "spiceypy", "version": libraries["spiceypy"]},
            "entry_point": "spkgeo — the geometric state, no light-time or aberration correction, frame J2000",
            "pool": "cleared before each file; exactly one file furnished while it is read",
            "cross_check": {"implementation": "jplephem", "version": libraries["jplephem"], "licence": "MIT",
                            "role": "a second reader of the identical bytes; a state composed as the sum of the "
                                    "file's own segments at the nearest common ancestor",
                            "numpy": libraries["numpy"]},
            "time_scale": "TDB",
            "units": {"position": "km", "velocity": "km/s"},
            "kernels": [
                {"key": key, "fit": fit, **oracle_identity(kernels[key], pins[key]),
                 "publisher_md5": pins[key].publisher_md5,
                 "segments": [layout.as_json() for _pair, layout in sorted(indexed[key].items())]}
                for key, _file, fit in FILES
            ],
            "publisher_checksums": PUBLISHER_CHECKSUMS,
            "kernel_terms": dict(KERNEL_TERMS),
            "redistribution": "the Toolkit is called, never redistributed by this repository; every kernel is the "
                              "publisher's unmodified file, identified by digest, and none is redistributed",
        },
        request={
            "window": {"file": WINDOW_FILE, **patterned("start_jd", lo), **patterned("end_jd", hi)},
            "stratum": stratum,
            "geocentric_grid": dict(grid),
            "record_edges": dict(edges),
            "targets": [{"code": code, "names": name} for code, name in TARGETS.items()],
            "centres": list(CENTRES),
            "files": [{"key": key, "file": name, "fit": fit} for key, name, fit in FILES],
            "same_fit_as": dict(SAME_FIT_AS),
            "difference_files": {fit.lower(): list(keys) for fit, keys in DIFFERENCE_FILES.items()},
            "fit_pairs": [list(pair) for pair in FIT_PAIRS],
            "reader_agreement": {**patterned("fraction", READER_AGREEMENT), "unit": "of the section's norm",
                                 "rule": "a state on which jplephem differs from CSPICE by more than this refuses "
                                         "the run; where the norm is zero the two must agree exactly. ⛔ Never "
                                         "averaged"},
            "regenerate": "generators/inter_de_states.py --kernels <dir holding the six files> --kernel-terms "
                          "<the terms page as read> --grid-values <values file> --grid-values-sha256 "
                          f"{grid['values_sha256']} --budget-row {budget_row} --out <a new dir>",
        },
        classification={name: {"class": "reference_only"} for name, _u, _p in SECTIONS},
        budget_row=budget_row,
        row_schema=ROW_SCHEMA,
        summary={**summary, "readers": list(readers), "host": host_record()},
        notes=[
            "Every state is geometric: no light-time, no aberration, no deflection, no frame beyond the files' own.",
            "⭐ Where both files of DE441 cover an instant, both are read, recorded and compared; neither is chosen.",
            "⭐ A second file of a fit that returns the same bits as the first says so with `same_bits_as`; where it "
            "does not, its own values are in the row, and `summary.packaging` carries the largest such difference.",
            "⛔ No band and no verdict. The differences between fits are measured here and declared elsewhere.",
        ],
    )


# --------------------------------------------------------------------------------------------------------------
# The run
# --------------------------------------------------------------------------------------------------------------


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    for name in ("--kernels", "--kernel-terms", "--grid-values", "--grid-values-sha256", "--budget-row", "--out"):
        parser.add_argument(name, required=True)
    args = parser.parse_args(argv)
    print(describe_reserved_names())
    try:
        generator = generator_for(Path(__file__))
        out_dir = Path(args.out)
        for output in OUTPUTS.values():
            if (out_dir / output).exists():
                raise Refusal(f"{output} exists in the output directory; each emission goes to a new one")
        if not args.budget_row or args.budget_row != args.budget_row.strip():
            raise Refusal("--budget-row is the consumer's row id, given exactly")
        terms = sha256_file(Path(args.kernel_terms))
        if terms != KERNEL_TERMS["sha256"]:
            raise Refusal(f"the kernel terms page is not the one read (sha256 {terms})")
        libraries = require_library_pins()
        kernels = {key: Path(args.kernels) / name for key, name, _fit in FILES}
        pins = {key: verify(kernels[key], PINS[name]) for key, name, _fit in FILES}
        print("kernels verified: " + ", ".join(f"{key} sha256 ok" for key in pins))
        instants = grid_instants(Path(args.grid_values), args.grid_values_sha256)

        indexed = check_structures({key: read_layouts(kernels[key]) for key, _name, _fit in FILES})
        lo, hi = window(indexed)
        points = grid_points(instants, lo, hi)
        edges, reasons = edge_points(indexed, lo, hi)
        points += edges
        print(f"window [{lo!r}, {hi!r}]; {len(instants)} grid instants; {len(points) - len(edges)} grid points; "
              f"{len(edges)} record-edge points")
        readings = measure(kernels, indexed, points)
    except (Refusal, KernelIdentityError, OSError) as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2

    import spiceypy as sp

    toolkit = sp.tkvrsn("TOOLKIT")
    grid = {"values_sha256": args.grid_values_sha256, "instants": len(instants),
            "rule": "the distinct jd_tdb of the values file named by its sha256, each checked against its bits"}
    edge_instants = len({point.jd for point in edges})
    edge_rule = {"instants": edge_instants, "points": len(edges),
                 "rule": "every record boundary of every segment of every file, the outer ends of its first and last "
                         "records included, and every segment's coverage ends — those inside the window; at each, "
                         "the segment's own pair, from every file that covers it"}
    for stratum, output in OUTPUTS.items():
        summary = summarise(iter_rows(points, readings, reasons, stratum))
        header = build_header(stratum=stratum, generator=generator, pins=pins, kernels=kernels, indexed=indexed,
                              libraries=libraries, toolkit=toolkit, lo=lo, hi=hi, grid=grid, edges=edge_rule,
                              summary=summary, readers=reader_summary(points, readings, stratum),
                              budget_row=args.budget_row)
        path = out_dir / output
        written = write_jsonl(path, header, iter_rows(points, readings, reasons, stratum),
                              declared_sections=[name for name, _u, _p in SECTIONS])
        print(f"wrote {written} rows -> {path} (sha256 {sha256_file(path)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
