"""The ephemeris publisher's own test-value set.

JPL ships a `testpo.<denum>` file beside each development ephemeris: several thousand
values taken from the **original integration**, against which a reader of the *exported*
data can check itself. This generator records that file as a fixture.

⭐ **The values are emitted verbatim, in the units the publisher printed** — AU and AU/day
— and are never converted. A recorder that rescales the numbers it records has already
made a judgement about which constant to rescale by, and has moved the error into a place
the consumer cannot see. The constant needed for the conversion (`AU` in km, taken from the
publisher's own header file) is recorded *beside* the rows as a stated input, so the
consumer converts and can be judged on it.

⚠ **This is a self-consistency measurement, not a comparison against an outside
reference.** The publisher's integration is being checked against the publisher's own
exported data. It is strong evidence that a reader reads correctly and it is **no evidence
at all** about how well the ephemeris models the solar system. The emitted fixture says so
in its own `contract_deviation` block, because the reference registry it is filed under
has no value that means *"no outside reference judged this"*.

⛔ **Recorder, never explainer.** The reproduction check below calls the SPICE Toolkit and
records residuals. It contains no account of how the Toolkit, or the publisher's own
Fortran, evaluates anything.
"""

from __future__ import annotations

import argparse
import hashlib
import statistics
import sys
import urllib.request
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

TESTPO_URL = "https://ssd.jpl.nasa.gov/ftp/eph/planets/ascii/de440/testpo.440"
HEADER_URL = "https://ssd.jpl.nasa.gov/ftp/eph/planets/ascii/de440/header.440"

#: The publisher's own tolerance, as its distributed test program applies it. Quoted for
#: what it is: a number the publisher chose, recorded so the consumer need not invent one.
#: ⛔ Recording it is not adopting it — that is the consumer's decision to take and record.
PUBLISHER_TOLERANCE = {
    "value": 1e-13,
    "applies_to": "absolute difference in the printed unit (AU, AU/day, or radians)",
    "as_applied_by": "the publisher's distributed test program, testeph.f",
    "verbatim": "IF (DEL .GE. 1.D-13) WRITE(*,201)",
    "publisher_note": (
        "the program's own comment: 'The agreement is considered okay if DEL is less "
        "that 1e-13. This corresponds to a few cm for body positions, and very small "
        "values for velocities, and angles and their rates. (A fractional test isn't "
        "suitable since sometimes the values will be near zero for particular "
        "components.)'"
    ),
    "source": "https://ssd.jpl.nasa.gov/ftp/eph/planets/fortran/testeph.f",
}

#: AU in km, from the publisher's own header file for this ephemeris. ⚠ Recorded as a
#: stated input, never applied to the emitted values.
AU_KM = 149597870.7
AU_KM_VERBATIM = "0.149597870699999988D+09"

#: The publisher's test-file body numbering, mapped to the numbering its binary kernels
#: use. ⚠ The two numbering schemes are different and neither is derivable from the other;
#: this table is the whole reason a consumer can use the file at all, and it is verified
#: below rather than asserted — a wrong row produces a residual of millions of km.
BODY_NUMBERING: dict[int, int] = {
    1: 199,  # Mercury
    2: 299,  # Venus
    3: 399,  # Earth
    4: 4,  # Mars system barycentre
    5: 5,  # Jupiter system barycentre
    6: 6,  # Saturn system barycentre
    7: 7,  # Uranus system barycentre
    8: 8,  # Neptune system barycentre
    9: 9,  # Pluto system barycentre
    10: 301,  # Moon
    11: 10,  # Sun
    12: 0,  # solar-system barycentre
    13: 3,  # Earth-Moon barycentre
}

#: What the printed coordinate index means.
COORDINATE = {
    1: ("position_au", "x", "au"),
    2: ("position_au", "y", "au"),
    3: ("position_au", "z", "au"),
    4: ("velocity_au_per_day", "x", "au/day"),
    5: ("velocity_au_per_day", "y", "au/day"),
    6: ("velocity_au_per_day", "z", "au/day"),
}

J2000_JD = 2451545.0
SECONDS_PER_DAY = 86400.0


def _fetch(url: str, cache: Path) -> bytes:
    if cache.is_file():
        return cache.read_bytes()
    request = urllib.request.Request(url, headers={"User-Agent": "saakshi/0.1"})
    with urllib.request.urlopen(request, timeout=120) as response:
        payload = response.read()
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_bytes(payload)
    return payload


def _parse(text: str) -> tuple[str, list[dict]]:
    """Return the file's identification line and its parsed rows."""
    lines = text.splitlines()
    identification = next((line.strip() for line in lines if line.strip()), "")
    try:
        start = next(i for i, line in enumerate(lines) if line.strip() == "EOT") + 1
    except StopIteration as exc:  # pragma: no cover - a malformed file is not a fixture
        raise SystemExit("no 'EOT' marker: this is not the expected file") from exc

    rows: list[dict] = []
    for lineno, line in enumerate(lines[start:], start=start + 1):
        parts = line.split()
        if len(parts) != 7:
            if parts:
                raise SystemExit(f"line {lineno}: expected 7 fields, got {len(parts)}")
            continue
        denum, date, jed, target, centre, coordinate, value = parts
        rows.append(
            {
                "line": lineno,
                "denum": int(denum),
                "calendar_date": date,
                "jed_tdb": float(jed),
                "publisher_target": int(target),
                "publisher_centre": int(centre),
                "coordinate_index": int(coordinate),
                "value": float(value),
                "value_printed": value,
            }
        )
    return identification, rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kernel", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--cache", default=Path("cache"), type=Path)
    parser.add_argument("--allow-dirty", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()

    generator = generator_for(Path(__file__), allow_dirty=args.allow_dirty)
    print(describe_reserved_names())

    pin = verify(args.kernel)
    print(f"kernel verified: {pin.dataset} ({pin.profile}) sha256 ok")

    payload = _fetch(TESTPO_URL, args.cache / "testpo.440")
    testpo_sha = hashlib.sha256(payload).hexdigest()
    identification, parsed = _parse(payload.decode("ascii"))
    print(f"parsed {len(parsed)} published values; file sha256 {testpo_sha[:16]}...")

    sp.furnsh(str(args.kernel))
    # ⭐ The span is read off the supplied file, never hard-coded: a constant here would
    #    silently mis-filter the day a different kernel is passed.
    spk = SPK.open(str(args.kernel))
    span_start_jd = J2000_JD + min(s.start_second for s in spk.segments) / SECONDS_PER_DAY
    span_end_jd = J2000_JD + max(s.end_second for s in spk.segments) / SECONDS_PER_DAY
    print(f"kernel span: JD {span_start_jd} .. {span_end_jd}")

    rows: list[dict] = []
    excluded: dict[str, int] = {}
    residuals: list[float] = []
    worst: dict | None = None
    over_tolerance = 0

    def exclude(reason: str) -> None:
        excluded[reason] = excluded.get(reason, 0) + 1

    for entry in parsed:
        target = BODY_NUMBERING.get(entry["publisher_target"])
        centre = BODY_NUMBERING.get(entry["publisher_centre"])
        if target is None or centre is None:
            # Nutations and librations. ⚠ Not a defect and not a gap in the evidence: a
            # planetary-position kernel does not carry them, so no reader of one can be
            # judged on them.
            exclude("quantity_not_carried_by_this_kernel")
            continue
        if entry["coordinate_index"] not in COORDINATE:
            exclude("coordinate_index_out_of_range")
            continue
        if not (span_start_jd <= entry["jed_tdb"] <= span_end_jd):
            # ⚠ The published set spans 1550–2650; this kernel is the time subset.
            exclude("epoch_outside_this_kernel_span")
            continue

        section, component, unit = COORDINATE[entry["coordinate_index"]]
        et = (entry["jed_tdb"] - J2000_JD) * SECONDS_PER_DAY

        # The reproduction check. ⚠ Its result is recorded; it never alters the published
        # value, and it is not emitted as a value of its own.
        state, _lt = sp.spkgeo(target, et, "J2000", centre)
        index = entry["coordinate_index"] - 1
        if index < 3:
            reproduced = float(state[index]) / AU_KM
        else:
            reproduced = float(state[index]) * SECONDS_PER_DAY / AU_KM
        residual = abs(reproduced - entry["value"])
        residuals.append(residual)
        if residual >= PUBLISHER_TOLERANCE["value"]:
            over_tolerance += 1
        if worst is None or residual > worst["residual"]:
            worst = {
                "residual": residual,
                "calendar_date": entry["calendar_date"],
                "publisher_target": entry["publisher_target"],
                "publisher_centre": entry["publisher_centre"],
                "coordinate_index": entry["coordinate_index"],
            }

        rows.append(
            {
                "section": section,
                "source_line": entry["line"],
                "calendar_date": entry["calendar_date"],
                "jed_tdb": entry["jed_tdb"],
                "jed_tdb_bits": bits(entry["jed_tdb"]),
                "et_seconds": et,
                "et_seconds_bits": bits(et),
                "publisher_target": entry["publisher_target"],
                "publisher_centre": entry["publisher_centre"],
                "target": target,
                "centre": centre,
                "coordinate_index": entry["coordinate_index"],
                "component": component,
                "unit": unit,
                "value": entry["value"],
                "value_bits": bits(entry["value"]),
                "value_printed": entry["value_printed"],
                "reproduction_abs_delta": residual,
            }
        )

    array = np.array(residuals) if residuals else np.zeros(1)
    header = Header(
        fixture_kind="numeric_pin",
        reference="none",
        generator=generator,
        generated=today(),
        title="The ephemeris publisher's own test values, as published",
        contract_deviation=[
            {
                "field": "reference",
                "clause": "the reference registry admits R1-R6 and 'instrument' only",
                "why": (
                    "this is a publisher self-consistency measurement: the publisher's "
                    "integration against the publisher's own exported data. No outside "
                    "reference judged it. Filing it under the ephemeris-service reference "
                    "would widen that reference's authority to cover a claim it was never "
                    "given, and 'instrument' names a harness, which this is not"
                ),
                "requested": (
                    "either admit 'none' in the registry, or mint a value that means "
                    "'a publisher's own self-consistency file'. ⛔ Neither is this "
                    "repository's decision to take"
                ),
            }
        ],
        oracle={
            "publisher": "JPL Solar System Dynamics",
            "ephemeris": "DE440 / LE440",
            "test_file": {
                "url": TESTPO_URL,
                "sha256": testpo_sha,
                "bytes": len(payload),
                "retrieved": today(),
                "identification_line": identification,
            },
            "published_values_are": (
                "taken from the original integration, for checking a reader of the "
                "exported data against it"
            ),
            "units_as_published": {
                "position": "au",
                "velocity": "au/day",
            },
            "au_in_km": {
                "value": AU_KM,
                "verbatim": AU_KM_VERBATIM,
                "source": HEADER_URL,
                "role": (
                    "a stated input for the consumer's own unit conversion. ⛔ It has NOT "
                    "been applied to any emitted value"
                ),
            },
            "publisher_tolerance": PUBLISHER_TOLERANCE,
            "kernel_the_rows_were_filtered_against": {
                **oracle_identity(args.kernel, pin),
                "span_jed_tdb": [span_start_jd, span_end_jd],
            },
            "reproduction_check": {
                "performed_with": "CSPICE",
                "toolkit_version": sp.tkvrsn("TOOLKIT"),
                "called_via": {"binding": "spiceypy", "version": sp.__version__},
                "role": (
                    "confirms that this kernel reproduces the published values, and that "
                    "the body-numbering table below is correct. ⛔ It does not judge, and "
                    "does not replace, the consumer's own reader being checked against "
                    "these rows"
                ),
            },
        },
        request={
            "body_numbering": {
                "note": (
                    "maps the publisher's test-file body numbers to the numbering its "
                    "binary kernels use. The two schemes are different and neither is "
                    "derivable from the other"
                ),
                "map": {str(k): v for k, v in BODY_NUMBERING.items()},
            },
            "coordinate_index": {
                str(k): {"section": s, "component": c, "unit": u}
                for k, (s, c, u) in COORDINATE.items()
            },
            "filters_applied": (
                "rows are included only where both bodies appear in the numbering map, the "
                "coordinate index is a position or velocity component, and the epoch lies "
                "within the supplied kernel's span. Every exclusion is counted by reason "
                "in `summary`"
            ),
            "regenerate": "generators/publisher_testpo.py --kernel <de440s.bsp> --out <dir>",
        },
        # ⛔ `reference_only` — committed, not yet compared. The publisher states a
        # tolerance and this file records it, but adopting a band is the consumer's
        # decision to take and to record, not this recorder's to make on its behalf.
        classification={
            "position_au": {"class": "reference_only"},
            "velocity_au_per_day": {"class": "reference_only"},
        },
        budget_row="K-a",
        row_schema={
            "source_line": "1-based line number in the published file",
            "calendar_date": "as printed by the publisher",
            "jed_tdb": "Julian date, TDB, as printed",
            "et_seconds": "the same epoch as seconds past J2000.0 TDB — derived, for convenience",
            "publisher_target": "body number in the publisher's test-file numbering",
            "publisher_centre": "centre, in the same numbering",
            "target": "the same body in the numbering the binary kernels use",
            "centre": "the same centre, likewise",
            "coordinate_index": "1-3 position components, 4-6 velocity components",
            "value": "THE PIN — the publisher's printed value, in `unit`, unconverted",
            "value_printed": "the same value as the decimal string the publisher printed",
            "reproduction_abs_delta": (
                "|this kernel via CSPICE - value|, in `unit`. ⚠ A measurement recorded "
                "beside the pin, ⛔ never the pin itself and never a tolerance"
            ),
        },
        summary={
            "published_values_parsed": len(parsed),
            "rows_emitted": len(rows),
            "excluded_by_reason": excluded,
            "reproduction": {
                "rows_checked": len(residuals),
                "at_or_over_publisher_tolerance": over_tolerance,
                "max_abs_delta": float(array.max()),
                "median_abs_delta": float(statistics.median(residuals)) if residuals else 0.0,
                "mean_abs_delta": float(array.mean()),
                "worst": worst,
                "meaning": (
                    "the supplied kernel, read by the SPICE Toolkit, against the "
                    "publisher's printed values. ⚠ It establishes that this repackaged "
                    "binary file carries the same ephemeris as the published test set, "
                    "and that the body-numbering map is right. ⛔ It says nothing about "
                    "any other reader"
                ),
            },
            "host": host_record(),
        },
        notes=[
            "The publisher's set spans a wider interval than the kernel supplied here; "
            "excluded epochs are counted, never dropped silently.",
            "Nutation and libration values are excluded because a planetary-position "
            "kernel does not carry them. That is a property of the kernel, not a gap in "
            "the evidence.",
            "⛔ This file is evidence that a reader reads correctly. It is NOT evidence "
            "about how accurately the ephemeris models the solar system: the publisher is "
            "on both sides of the comparison.",
        ],
    )

    out_path = Path(args.out) / "kernel" / "de440s" / "publisher-test-values.jsonl"
    written = write_jsonl(
        out_path,
        header,
        rows,
        declared_sections=["position_au", "velocity_au_per_day"],
    )

    print(f"wrote {written} rows -> {out_path}")
    print(f"excluded: {excluded}")
    print(
        f"reproduction: max |delta| = {array.max():.3e} {PUBLISHER_TOLERANCE['applies_to']}"
    )
    print(
        f"reproduction: {over_tolerance}/{len(residuals)} rows at or over the publisher's "
        f"{PUBLISHER_TOLERANCE['value']:.0e}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
