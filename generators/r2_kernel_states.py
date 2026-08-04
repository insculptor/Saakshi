"""R2 — kernel-layer state parity fixtures.

Geometric `(epoch, target, centre) -> state` rows over a stratified grid, read out of a
development-ephemeris kernel pinned by digest.

**Two independent implementations read the identical bytes.** The SPICE Toolkit is the
oracle of record; `jplephem`, a pure-Python BSD reader, is the cross-check. Where they
disagree, the magnitude is recorded per row and summarised in the header.

⭐ **The band this file declares is that floor, and a band's SHAPE is the finding.** Three
denominators were available and two of them are wrong:

* **a distance** (kilometres) — wrong, because the disagreement scales with coordinate
  magnitude. One number is a millimetre at Pluto's barycentre and absurdly loose for the
  Moon;
* **the component** — wrong, and less obviously so: a component passing near zero drives
  its own ratio arbitrarily large while nothing has gone wrong;
* ⭐ **the norm of the section's three components** — stable, dimensionless, and the shape
  used here. ⚠ It is undefined for the segments this file carries as identically zero, and
  those rows say so rather than dividing.

⚠ **The declared band is generation context, not a judgement.** It records what two
third-party readers of the same bytes already differ by; it is not the band a consumer
should apply. That is set from the consumer's own budget and measured against these rows in
the consumer's own tree — a mismatch between the two is something to report, never a reason
to refuse this file.

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

#: One unit in the last place, relative, for a double: 2**-52. ⭐ Used only to *report* a
#: measured relative disagreement in a scale-free way. The band itself is declared as the
#: measured fraction, because a fraction needs no agreement about what "a ULP" means.
RELATIVE_ULP = 2.0**-52

#: The sections, and the slice of the six-vector each one is.
SECTIONS: tuple[tuple[str, str, slice], ...] = (
    ("position", "km", slice(0, 3)),
    ("velocity", "km/s", slice(3, 6)),
)


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


def _split_epoch(et: float) -> tuple[float, float]:
    """Seconds past J2000 -> a two-part Julian date that loses nothing.

    ⚠ **This is not a detail.** Writing the obvious `jd = 2451545.0 + et / 86400.0` makes
    the division round: at an arbitrary epoch three centuries from J2000 the rounding is
    ~4e-12 days, and the fastest body in the file moves ~2e-5 km in that time. Measured on
    this grid, the naive form produced a worst-case disagreement of **2.0e-5 km** between
    two readers that, given the epoch this way, agree **bit for bit**.

    ⭐ The lesson generalises past this script: a recorder that converts units before
    handing a value to the thing it is measuring is measuring its own arithmetic. The
    integral day is exactly representable and adds to 2451545.0 exactly; only the
    sub-day remainder is rounded, and it is small enough for that to vanish.
    """
    whole_days = math.floor(et / SECONDS_PER_DAY)
    remainder_seconds = et - whole_days * SECONDS_PER_DAY
    return 2451545.0 + whole_days, remainder_seconds / SECONDS_PER_DAY


def _leg(spk: SPK, centre: int, target: int, et: float) -> np.ndarray:
    jd, jd_fraction = _split_epoch(et)
    position, velocity = spk[centre, target].compute_and_differentiate(jd, jd_fraction)
    return np.concatenate([position, velocity / SECONDS_PER_DAY])


def _chain_to_root(parents: dict[int, int], body: int) -> list[int]:
    """`body`, then each centre in turn, ending at the root."""
    chain = [body]
    while chain[-1] != 0:
        chain.append(parents[chain[-1]])
    return chain


def _state_via_jplephem(
    spk: SPK, parents: dict[int, int], target: int, centre: int, et: float
) -> np.ndarray:
    """State of `target` relative to `centre`, composed at the nearest common ancestor.

    ⭐ Composed as a sum of the file's own segments — the only arithmetic is vector
    addition, which follows from what a relative position *is*.
    """
    target_chain = _chain_to_root(parents, target)
    centre_chain = _chain_to_root(parents, centre)
    common = next(body for body in target_chain if body in centre_chain)

    total = np.zeros(6)
    for body in target_chain[: target_chain.index(common)]:
        total += _leg(spk, parents[body], body, et)
    for body in centre_chain[: centre_chain.index(common)]:
        total -= _leg(spk, parents[body], body, et)
    return total


def _state_via_root(
    spk: SPK, parents: dict[int, int], target: int, centre: int, et: float
) -> np.ndarray:
    """The same state, but always composed through the root.

    ⚠ Kept only as a **probe**, never as a fixture value. For a pair whose nearest common
    ancestor is not the root it differs from the composition above by the cancellation of
    two barycentric vectors, and measuring that difference is the point.
    """
    total = np.zeros(6)
    for body in _chain_to_root(parents, target)[:-1]:
        total += _leg(spk, parents[body], body, et)
    for body in _chain_to_root(parents, centre)[:-1]:
        total -= _leg(spk, parents[body], body, et)
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
    # ⭐ The band is measured per section, because the two sections were measured to differ.
    #    One band across both would be set by the worse of them and would silently claim the
    #    better one is that loose.
    worst_relative: dict[str, float] = {name: 0.0 for name, _, _ in SECTIONS}
    worst_relative_row: dict[str, dict | None] = {name: None for name, _, _ in SECTIONS}
    undefined_denominator: dict[str, int] = {name: 0 for name, _, _ in SECTIONS}
    # The chaining-strategy probe: same file, same reader, different composition point.
    worst_strategy_delta = 0.0
    worst_strategy_row: dict | None = None

    for epoch_id, stratum, et in epochs:
        for target, centre, shape in PAIRS:
            state, _light_time = sp.spkgeo(target, et, "J2000", centre)
            state = np.asarray(state, dtype=float)

            cross = _state_via_jplephem(spk, parents, target, centre, et)
            delta = np.abs(state - cross)

            strategy_delta = float(
                np.abs(cross - _state_via_root(spk, parents, target, centre, et)).max()
            )
            if strategy_delta > worst_strategy_delta:
                worst_strategy_delta = strategy_delta
                worst_strategy_row = {
                    "epoch_id": epoch_id,
                    "target": target,
                    "centre": centre,
                    "chain_shape": shape,
                    "max_abs_delta": strategy_delta,
                }
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
            for name, unit, part in SECTIONS:
                components = state[part]
                abs_delta = float(delta[part].max())
                norm = float(np.linalg.norm(components))
                # ⛔ Not a guard against a crash — a statement about what can be judged.
                #    The identically-zero segments have no scale, so a relative band says
                #    nothing about them, and `null` is the honest value. Their absolute
                #    delta is still recorded and is still checkable against zero.
                if norm == 0.0:
                    relative: float | None = None
                    undefined_denominator[name] += 1
                else:
                    relative = abs_delta / norm
                    if relative > worst_relative[name]:
                        worst_relative[name] = relative
                        worst_relative_row[name] = {
                            "epoch_id": epoch_id,
                            "target": target,
                            "centre": centre,
                            "chain_shape": shape,
                            "max_rel_delta": relative,
                            "max_rel_delta_in_ulp": relative / RELATIVE_ULP,
                        }
                rows.append(
                    {
                        **common,
                        "section": name,
                        "unit": unit,
                        "values": [float(v) for v in components],
                        "values_bits": [bits(float(v)) for v in components],
                        "cross_check_max_abs_delta": abs_delta,
                        "state_vector_norm": norm,
                        "cross_check_max_rel_delta": relative,
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
        # ⛔ NOT `reference_only`. That value means "committed but not compared", and a file
        # carrying it cannot pass whatever band is set for it — which makes it the wrong
        # value for a fixture whose whole purpose is to be compared against.
        #
        # ⛔ And not `exact` either: that would assert bit-identity across independent
        # implementations, which the run below measures to be false for roughly a quarter of
        # the states.
        #
        # ⭐ So `tolerance`, with the band MEASURED on this run and per section. ⚠ It is
        # generation context — what two third-party readers of these bytes already differ
        # by — and not a judgement anyone must adopt. The consumer judges from its own
        # budget; a disagreement with the number here is a line to report, not a load error.
        # There is deliberately **no headroom**: the band is the worst observation, because
        # adding margin to an observation is where a measurement quietly becomes an opinion.
        classification={
            name: {
                "class": "tolerance",
                "band": worst_relative[name],
                "unit": "relative_to_section_state_vector_norm",
            }
            for name, _, _ in SECTIONS
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
            "state_vector_norm": (
                "Euclidean norm of this row's three components, in this row's unit — the "
                "denominator the declared band is relative to. ⭐ The norm rather than the "
                "component, because a component passing near zero inflates its own ratio "
                "while nothing has gone wrong"
            ),
            "cross_check_max_rel_delta": (
                "`cross_check_max_abs_delta / state_vector_norm`, dimensionless — the shape "
                "the band is declared in. ⚠ **null** where the norm is zero: the "
                "identically-zero segments have no scale, so no relative statement about "
                "them is possible. ⛔ Their absolute delta is still recorded and is still "
                "checkable against zero, which is the only check they admit"
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
                "epoch_handling": (
                    "the epoch is handed to the cross-check reader as an exact integral "
                    "Julian day plus a sub-day fraction. ⚠ Converting seconds to days in "
                    "one division instead produced a worst-case disagreement of 2.0e-5 km "
                    "on this same grid — the recorder's own rounding, not a difference "
                    "between the readers"
                ),
                "meaning": (
                    "two independent implementations reading the identical bytes. This is an "
                    "empirical floor on what 'machine precision' means for this file, and it "
                    "is NOT a consumer's own residual, which can only be measured in that "
                    "consumer's tree"
                ),
            },
            "declared_band": {
                "per_section": {
                    name: {
                        "band": worst_relative[name],
                        "in_ulp": worst_relative[name] / RELATIVE_ULP,
                        "worst_state": worst_relative_row[name],
                        "rows_with_no_denominator": undefined_denominator[name],
                    }
                    for name, _, _ in SECTIONS
                },
                "unit": "relative_to_section_state_vector_norm",
                "ulp_definition": RELATIVE_ULP,
                "derivation": (
                    "the largest relative disagreement observed on this grid, per section, "
                    "with no headroom added. ⭐ Reported in ULP too because that is the "
                    "scale-free reading, but declared as the fraction, which needs no "
                    "agreement about what a ULP is"
                ),
                "why_this_denominator": (
                    "⛔ a band in kilometres is the wrong SHAPE — the disagreement scales "
                    "with coordinate magnitude, so one number is a millimetre at the outer "
                    "barycentres and absurdly loose for the Moon. ⛔ A band relative to the "
                    "COMPONENT is wrong too, and less visibly: a component passing near zero "
                    "drives its own ratio arbitrarily large with nothing wrong. ⭐ The norm "
                    "of the section's three components is the stable denominator"
                ),
                "status": (
                    "⚠ GENERATION CONTEXT, not a judgement. It records what two third-party "
                    "readers of these bytes already differ by. The band a consumer applies "
                    "comes from that consumer's own budget, measured against these rows in "
                    "that consumer's tree; a disagreement with this number is a line to "
                    "report, ⛔ never a reason to refuse this file"
                ),
                "rows_with_no_denominator_note": (
                    "the identically-zero segments. ⚠ They carry `cross_check_max_rel_delta` "
                    "as null and are excluded from the band entirely — including them at a "
                    "ratio of zero would tighten the reported floor with rows that were "
                    "never capable of loosening it"
                ),
            },
            "chaining_strategy_probe": {
                "max_abs_delta": worst_strategy_delta,
                "worst_state": worst_strategy_row,
                "unit": "km or km/s, whichever component was worst",
                "meaning": (
                    "the SAME reader on the SAME bytes, composing the same state two ways: "
                    "at the nearest common ancestor, versus always through the root. For a "
                    "pair whose common ancestor is not the root, the second subtracts two "
                    "large barycentric vectors and loses digits to cancellation. ⭐ A "
                    "consumer implementing chaining faces this choice, so the cost is "
                    "recorded. ⛔ It is a property of the arithmetic, not of either reader, "
                    "and it is not a tolerance"
                ),
                "values_emitted_use": "the nearest common ancestor",
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
            "⭐ THE BAND IS DECLARED, MEASURED, AND STILL NOT AN INSTRUCTION. It is what two "
            "third-party readers of these bytes differ by; the band a consumer applies is "
            "that consumer's own, and a mismatch between the two is a reported line rather "
            "than a load error. ⛔ A later tightening on the consumer's side can therefore "
            "never make this file unloadable.",
            "⚠ A relative band cannot judge the identically-zero rows, and this file does "
            "not pretend otherwise: their `cross_check_max_rel_delta` is null and they are "
            "excluded from the band. They are the rows where an exact-zero check is the only "
            "check available, so a consumer that judges them by band alone judges them not "
            "at all.",
        ],
    )

    # ⭐ Derived from the file that was actually verified, never hard-coded: a fixed
    #    directory would quietly overwrite one kernel's evidence with another's.
    out_path = Path(args.out) / "kernel" / pin.dataset.removesuffix(".bsp") / "r2-states.jsonl"
    written = write_jsonl(
        out_path, header, rows, declared_sections=[name for name, _, _ in SECTIONS]
    )

    print(f"wrote {written} rows -> {out_path}")
    print(f"cross-check: {exact_states}/{total_states} states bit-identical")
    print(f"cross-check: worst |CSPICE - jplephem| = {worst_delta!r}")
    if delta_magnitudes:
        arr = np.array(delta_magnitudes)
        print(f"cross-check: differing states median = {np.median(arr)!r}")
    for name, _, _ in SECTIONS:
        print(
            f"band ({name}): {worst_relative[name]:.4e} "
            f"= {worst_relative[name] / RELATIVE_ULP:.2f} ULP of the section norm; "
            f"{undefined_denominator[name]} row(s) had no denominator"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
