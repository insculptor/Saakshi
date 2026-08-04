"""R2 — kernel-layer state parity fixtures.

Geometric `(epoch, target, centre) -> state` rows over a stratified grid, read out of a
development-ephemeris kernel pinned by digest.

**Two independent implementations read the identical bytes.** The SPICE Toolkit is the
oracle of record; `jplephem`, a pure-Python BSD reader, is the cross-check. Where they
disagree, the magnitude is recorded per row and summarised in the header.

⚠ **That disagreement is not a tolerance band.** It is an empirical *floor* — how far
apart two third-party readers of the same file already are. The band for any consumer's
own reader is a separate measurement, taken against these rows, in that consumer's own
tree. Recording the floor here makes that later measurement interpretable; it does not
pre-empt it.

⛔ **Recorder, never explainer.** This script calls two libraries and writes down what
they returned. It contains no account of *how* either evaluates a record. Code that
consumes these fixtures derives the file format clean-room from published specification,
and a note here would become an implementation source for it.
"""

from __future__ import annotations

import argparse
import math
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import numpy as np  # noqa: E402
import spiceypy as sp  # noqa: E402
from jplephem.spk import SPK  # noqa: E402

from saakshi.fixture import (  # noqa: E402
    Header,
    bits,
    describe_reserved_names,
    write_jsonl,
)
from saakshi.kernels import oracle_identity, verify  # noqa: E402
from saakshi.provenance import generator_for, host_record, today  # noqa: E402

# The grid's own reproducibility constant. ⭐ Recorded in the fixture's `request` block so
# the identical grid regenerates; ⛔ never re-rolled, because a fixture whose inputs move is
# not a fixture.
GRID_SEED = 20260804

#: `(target, centre)`, target first. Chosen to exercise four distinct chain shapes.
PAIRS: list[tuple[int, int, str]] = [
    # --- every segment the file actually carries, read directly ---------------------
    (1, 0, "direct"),
    (2, 0, "direct"),
    (3, 0, "direct"),
    (4, 0, "direct"),
    (5, 0, "direct"),
    (6, 0, "direct"),
    (7, 0, "direct"),
    (8, 0, "direct"),
    (9, 0, "direct"),
    (10, 0, "direct"),
    # ⚠ Two segments this file carries as identically zero — Mercury and Venus relative to their
    #   own system barycentres, carried as degree-1 segments over the whole span. Labelled
    #   for what makes them interesting: a value meant to be exactly zero is the one a
    #   reader can get wrong without a residual showing anywhere else.
    (199, 1, "direct_identically_zero"),
    (299, 2, "direct_identically_zero"),
    (301, 3, "direct"),
    (399, 3, "direct"),
    # --- a chain whose nearest common ancestor is NOT the root ----------------------
    # ⭐ (301, 399) is the interesting chaining case: both legs hang off 3, so a reader
    #    that always chains through the root does more work and may compose in a different
    #    order. Its reverse is included so antisymmetry is checkable from the fixture.
    (301, 399, "common_ancestor_not_root"),
    (399, 301, "common_ancestor_not_root"),
    # --- chains that pass through the root ------------------------------------------
    (399, 10, "through_root"),
    (301, 10, "through_root"),
    (10, 399, "through_root"),
    (399, 0, "through_root"),
    (199, 0, "through_root"),
    (299, 0, "through_root"),
    (199, 399, "through_root"),
    (299, 399, "through_root"),
    (4, 399, "through_root"),
    (5, 399, "through_root"),
    (9, 399, "through_root"),
]

SECONDS_PER_DAY = 86400.0


def _parent_map(spk: SPK) -> dict[int, int]:
    """Derive the centre of each body from the file, never from an assumption."""
    return {target: centre for (centre, target) in spk.pairs}


def _shortest_interval(spk: SPK) -> tuple[float, float]:
    """`(init, intlen)` of the segment with the shortest interval in the file.

    Record boundaries of the *shortest* segment are the densest, so they are where a
    boundary-selection error is most likely to be caught.
    """
    best: tuple[float, float] | None = None
    for segment in spk.segments:
        init, intlen, _ = segment.load_array()
        if best is None or float(intlen) < best[1]:
            best = (float(init), float(intlen))
    assert best is not None
    return best


def _epochs(spk: SPK) -> list[tuple[str, str, float]]:
    """The stratified epoch set: `(epoch_id, stratum, et_seconds)`."""
    start = min(s.start_second for s in spk.segments)
    end = max(s.end_second for s in spk.segments)
    init, intlen = _shortest_interval(spk)

    out: list[tuple[str, str, float]] = []

    def add(epoch_id: str, stratum: str, et: float) -> None:
        out.append((epoch_id, stratum, float(et)))

    # The two ends, exactly. ⭐ These are the extreme admissible epochs, so a reader's
    # range guard must ACCEPT them — an off-by-one guard fails here and nowhere else.
    add("span_start", "span_edge", start)
    add("span_end", "span_edge", end)
    add("span_start_plus_1s", "span_edge", start + 1.0)
    add("span_end_minus_1s", "span_edge", end - 1.0)

    add("j2000", "epoch_zero", 0.0)

    # Record boundaries of the shortest-interval segment, and one ULP either side.
    for k in (1, 2, 6851, 13700, 27399):
        boundary = init + k * intlen
        if not (start <= boundary <= end):
            continue
        add(f"boundary_k{k}", "record_boundary", boundary)
        add(f"boundary_k{k}_minus_ulp", "record_boundary_adjacent", math.nextafter(boundary, -math.inf))
        add(f"boundary_k{k}_plus_ulp", "record_boundary_adjacent", math.nextafter(boundary, math.inf))
        add(f"midpoint_k{k}", "record_midpoint", boundary + intlen / 2.0)

    # A deterministic spread across the whole span.
    rng = random.Random(GRID_SEED)
    for i in range(24):
        add(f"spread_{i:02d}", "stratified_spread", rng.uniform(start, end))

    return out


def _state_via_jplephem(
    spk: SPK, parents: dict[int, int], body: int, et: float
) -> np.ndarray:
    """State of `body` relative to the root, in km and km/s.

    ⭐ Composed as a sum of the file's own segments — the only arithmetic here is vector
    addition, which follows from what a relative position *is*.
    """
    total = np.zeros(6)
    current = body
    while current != 0:
        centre = parents[current]
        position, velocity = spk[centre, current].compute_and_differentiate(
            2451545.0, et / SECONDS_PER_DAY
        )
        total[:3] += position
        total[3:] += velocity / SECONDS_PER_DAY  # jplephem differentiates per day
        current = centre
    return total


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kernel", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--allow-dirty", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()

    generator = generator_for(Path(__file__), allow_dirty=args.allow_dirty)

    print(describe_reserved_names())

    pin = verify(args.kernel)
    print(f"kernel verified: {pin.dataset} ({pin.profile}) sha256 ok")

    sp.furnsh(str(args.kernel))
    spk = SPK.open(str(args.kernel))
    parents = _parent_map(spk)
    epochs = _epochs(spk)
    print(f"epochs: {len(epochs)}   pairs: {len(PAIRS)}")

    rows: list[dict] = []
    worst_delta = 0.0
    worst_row: dict | None = None
    exact_states = 0
    total_states = 0
    delta_magnitudes: list[float] = []

    for epoch_id, stratum, et in epochs:
        for target, centre, shape in PAIRS:
            state, _light_time = sp.spkgeo(target, et, "J2000", centre)
            state = np.asarray(state, dtype=float)

            cross = _state_via_jplephem(spk, parents, target, et) - _state_via_jplephem(
                spk, parents, centre, et
            )
            delta = np.abs(state - cross)
            row_delta = float(delta.max())
            total_states += 1
            if row_delta == 0.0:
                exact_states += 1
            else:
                delta_magnitudes.append(row_delta)
            if row_delta > worst_delta:
                worst_delta = row_delta
                worst_row = {
                    "epoch_id": epoch_id,
                    "target": target,
                    "centre": centre,
                    "max_abs_delta": row_delta,
                }

            common = {
                "epoch_id": epoch_id,
                "stratum": stratum,
                "chain_shape": shape,
                "et_seconds": et,
                "et_bits": bits(et),
                "target": target,
                "centre": centre,
            }
            rows.append(
                {
                    **common,
                    "section": "position",
                    "unit": "km",
                    "values": [float(v) for v in state[:3]],
                    "values_bits": [bits(float(v)) for v in state[:3]],
                    "cross_check_max_abs_delta": float(delta[:3].max()),
                }
            )
            rows.append(
                {
                    **common,
                    "section": "velocity",
                    "unit": "km/s",
                    "values": [float(v) for v in state[3:]],
                    "values_bits": [bits(float(v)) for v in state[3:]],
                    "cross_check_max_abs_delta": float(delta[3:].max()),
                }
            )

    header = Header(
        fixture_kind="numeric_pin",
        reference="R2",
        generator=generator,
        generated=today(),
        title="Geometric states from a pinned DE kernel, read by two independent implementations",
        oracle={
            "implementation": "CSPICE",
            "toolkit_version": sp.tkvrsn("TOOLKIT"),
            "called_via": {"binding": "spiceypy", "version": sp.__version__},
            "entry_point": "spkgeo — geometric state, no light-time or aberration correction",
            "cross_check": {
                "implementation": "jplephem",
                "version": "2.23",
                "licence": "BSD-2-Clause",
                "role": "independent second reader of the identical bytes",
            },
            "frame": "J2000",
            "time_scale": "TDB seconds past J2000.0",
            "units": {"position": "km", "velocity": "km/s"},
            "kernel": oracle_identity(args.kernel, pin),
            "redistribution": (
                "the Toolkit is called, never redistributed by this repository "
                "the kernel is the publisher's unmodified file, identified by digest"
            ),
        },
        request={
            "grid": "stratified",
            "grid_seed": GRID_SEED,
            "epoch_count": len(epochs),
            "pair_count": len(PAIRS),
            "strata": sorted({stratum for _, stratum, _ in epochs}),
            "chain_shapes": sorted({shape for _, _, shape in PAIRS}),
            "pairs": [{"target": t, "centre": c, "chain_shape": s} for t, c, s in PAIRS],
            "regenerate": (
                "generators/r2_kernel_states.py --kernel <de440s.bsp> --out <dir> "
                "— the seed and the pair list above fix the grid exactly"
            ),
        },
        # ⛔ `reference_only` — "committed but not compared" — and it is the honest value.
        # `validation/budget.toml` carries K-b at `band = "unmeasured"`, which is fail-closed:
        # no band exists yet, so no comparison can be judged. A consumer measures its own
        # reader's residual against these rows and the band is set ONCE from that measurement;
        # only then does this classification become `tolerance` with band and unit.
        # ⛔ Writing `exact` here would assert bit-identity across independent
        # implementations, which nothing has established and which two readers composing
        # in different orders would be expected to break.
        classification={
            "position": {"class": "reference_only"},
            "velocity": {"class": "reference_only"},
        },
        budget_row="K-b",
        row_schema={
            "epoch_id": "stable id of the epoch within this grid",
            "stratum": "why this epoch is in the grid",
            "chain_shape": "direct | direct_identically_zero | common_ancestor_not_root | through_root",
            "et_seconds": "TDB seconds past J2000.0",
            "et_bits": "IEEE-754 bit pattern of et_seconds",
            "target": "NAIF id of the body whose state this is",
            "centre": "NAIF id of the body the state is relative to",
            "section": "position | velocity",
            "unit": "km or km/s",
            "values": "the three components, as CSPICE returned them",
            "values_bits": "IEEE-754 bit patterns of the same three components",
            "cross_check_max_abs_delta": (
                "max |CSPICE - jplephem| over this row's three components, in this row's "
                "unit. ⛔ NOT a tolerance, and NOT a consumer's own residual"
            ),
        },
        summary={
            "states": total_states,
            "rows": len(rows),
            "cross_check": {
                "states_bit_identical": exact_states,
                "states_differing": total_states - exact_states,
                "max_abs_delta_any_component": worst_delta,
                "worst_state": worst_row,
                "meaning": (
                    "two independent implementations reading the identical bytes. This is an "
                    "empirical floor on what 'machine precision' means for this file. "
                    "It is NOT K-b's band, which budget.toml records as `unmeasured`, and it "
                    "is NOT a consumer's own residual, which can only be measured in that consumer's tree"
                ),
            },
            "host": host_record(),
        },
        notes=[
            "R2 judges kernel-layer state parity, Chebyshev evaluation and frame math — "
            "evaluation, frame math. Never astrology conventions and never apparent "
            "positions — it is a kernel oracle, not a pipeline oracle.",
            "Every state is geometric. No light-time, no stellar aberration, no frame "
            "transformation beyond the file's own J2000 frame.",
            "The two `direct_identically_zero` pairs are Mercury and Venus relative "
            "to their own system barycentres, which this kernel carries as degree-1 segments "
            "over the whole span. A reader can get an exact zero wrong invisibly.",
        ],
    )

    out_path = Path(args.out) / "kernel" / "de440s" / "r2-states.jsonl"
    written = write_jsonl(
        out_path, header, rows, declared_sections=["position", "velocity"]
    )

    print(f"wrote {written} rows -> {out_path}")
    print(f"cross-check: {exact_states}/{total_states} states bit-identical")
    print(f"cross-check: worst |CSPICE - jplephem| = {worst_delta!r}")
    if delta_magnitudes:
        arr = np.array(delta_magnitudes)
        print(f"cross-check: differing states median = {np.median(arr)!r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
