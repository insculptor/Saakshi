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
at all** about how well the ephemeris models the solar system.

⭐ **The fixture is filed under `publisher_self_consistency`, and that value obliges it to
name BOTH artifacts.** A self-consistency claim is irreducibly about a pair — the published
*test values* and the published *data* they are reproduced from — so naming one of them and
leaving the other implicit does not weaken the claim, it states a different one. The
emitted `oracle` carries a `test_artifact` and a `subject_artifact`, and the contract
refuses the file if either is incomplete.

⚠ **An earlier version of this file emitted `reference = "none"` with a
`contract_deviation` block**, because no registry value fitted. That block did its job: the
consumer refused the file, a human decided, and the value now exists. ⛔ It is gone from
here, and the contract now refuses a conforming fixture that still carries one — a
deviation that has been closed still reads as an open question.

⛔ **Recorder, never explainer.** The reproduction check below calls the SPICE Toolkit and
records residuals. It contains no account of how the Toolkit, or the publisher's own
Fortran, evaluates anything.
"""

from __future__ import annotations

import argparse
import hashlib
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import numpy as np  # noqa: E402
import spiceypy as sp  # noqa: E402
from jplephem.spk import SPK  # noqa: E402

from saakshi.acquisition import USER_AGENT, Retrieval, retrieve  # noqa: E402
from saakshi.fixture import (  # noqa: E402
    PUBLISHER_SELF_CONSISTENCY,
    Header,
    bits,
    describe_reserved_names,
    write_jsonl,
)
from saakshi.kernels import verify  # noqa: E402
from saakshi.provenance import generator_for, host_record, today  # noqa: E402

TESTPO_URL = "https://ssd.jpl.nasa.gov/ftp/eph/planets/ascii/de440/testpo.440"
HEADER_URL = "https://ssd.jpl.nasa.gov/ftp/eph/planets/ascii/de440/header.440"

#: Where the acquisition record lands, **relative to the fixture root**. ⭐ Relative on
#: purpose: these files are generated in one tree and read in another, and an absolute path
#: — or one anchored at this repository — would resolve on exactly one machine.
ACQUISITION_RECORD_PATH = "kernel/publisher-test-file-acquisition.jsonl"

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

#: Names, for a reader of the fixture. ⛔ Never used to resolve anything — the numbers do
#: that, and a name in a lookup path is how a numbering drifts.
BODY_NAMES: dict[int, str] = {
    1: "Mercury",
    2: "Venus",
    3: "Earth",
    4: "Mars system barycentre",
    5: "Jupiter system barycentre",
    6: "Saturn system barycentre",
    7: "Uranus system barycentre",
    8: "Neptune system barycentre",
    9: "Pluto system barycentre",
    10: "Moon",
    11: "Sun",
    12: "solar-system barycentre",
    13: "Earth-Moon barycentre",
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


def _write_acquisition_record(
    retrieval: Retrieval, *, identification: str, out: Path, script: Path, allow_dirty: bool
) -> tuple[Path, str]:
    """Attest how the published test file was obtained. Returns its path and its digest.

    ⭐ **A separate artifact, and a `provenance_record` rather than a `numeric_pin`**, because
    it compares nothing. The pin file records that the bytes it read hash to a value; this
    records where those bytes were fetched from, when, and by what. ⛔ Neither statement
    implies the other, and a consumer's loader checking that a digest matches has checked
    the first and not the second.

    ⚠ **Its limit is written into it.** It cannot establish that the publisher published
    anything. A server answering an address is a different claim from a party publishing a
    file, and nothing observable from outside closes that gap — so the gap is stated where
    a reader of the record will see it, rather than left to be assumed away.
    """
    rows: list[dict] = [
        {
            "finding": "retrieval",
            **retrieval.as_record(),
            "retrieved_on": today(),
            "acquiring_instrument": {
                "software": "python urllib.request",
                "python": host_record()["python"],
                "user_agent": USER_AGENT,
            },
            "evidence": (
                "the digest is over exactly the bytes this retrieval returned, taken before "
                "anything was parsed"
            ),
        },
        {
            "finding": "server_validators",
            **retrieval.validators,
            "evidence": (
                "what the server stated about the resource's own age and identity. ⚠ These "
                "are the server's assertions, restatable at will, and they corroborate "
                "rather than prove: a modification time years before this retrieval is "
                "consistent with a long-published file and does not establish one"
            ),
        },
        {
            "finding": "digest_reproduction",
            "prior_copy_present": retrieval.prior_copy_agreed is not None,
            "prior_copy_agreed": retrieval.prior_copy_agreed,
            "evidence": (
                "whether a copy retained from an earlier retrieval agreed with these bytes. "
                "⛔ A disagreement aborts the run: one address having served two artifacts "
                "is not something a recorder may resolve on its own. ⚠ `prior_copy_present` "
                "false means there was nothing to compare against, which is reported as its "
                "own state and never collapsed into agreement"
            ),
        },
        {
            "finding": "identification_line",
            "value": identification,
            "evidence": "the file's own first line, as the publisher wrote it",
        },
    ]

    header = Header(
        fixture_kind="provenance_record",
        # ⭐ `instrument`, and the contrast with the value fixture is the point. That file
        #    is `publisher_self_consistency` because the publisher is on both sides of what
        #    it claims. This one is `instrument` because the observation in it is ours: a
        #    harness watched a retrieval and wrote down what it saw. ⛔ Two files about the
        #    same artifact, filed under different references, because they attest different
        #    parties' claims — which is what the single-valued `reference` field is for.
        reference="instrument",
        generator=generator_for(script, allow_dirty=allow_dirty),
        generated=today(),
        title="How the publisher's test-value file was obtained",
        oracle={
            "implementation": "python urllib.request over HTTPS",
            "python": host_record()["python"],
            "user_agent": USER_AGENT,
            "artifact_acquired": "testpo.440",
            "publisher_named_by_the_address": "JPL Solar System Dynamics",
            "method": (
                "a single live GET, with the digest taken over the response body before "
                "anything was parsed"
            ),
        },
        attests=(
            "the address a published test-value file was requested from, the address that "
            "answered, the status and size of the response, the digest of exactly the bytes "
            "returned, the date of the retrieval, and the instrument that performed it"
        ),
        authority={
            "held_by": "this instrument, as the party that performed the retrieval",
            "kind": "direct observation of a network retrieval",
            "scope": (
                "⛔ THE LIMIT, STATED RATHER THAN IMPLIED: this record cannot establish that "
                "the publisher published this file. It establishes that an address under the "
                "publisher's domain returned these bytes to this instrument on this date. A "
                "server answering an address is not the same claim as a party publishing a "
                "file, and no observation available from outside closes the difference"
            ),
        },
        record_date=today(),
        row_schema={
            "finding": (
                "retrieval | server_validators | digest_reproduction | identification_line"
            ),
            "url": "the address requested",
            "final_url": (
                "the address that answered. ⚠ Recorded separately from the one requested, "
                "because a redirect means the bytes came from somewhere else"
            ),
            "http_status": "the response status",
            "sha256": "digest of exactly the bytes returned",
            "last_modified": "the server's statement of when the resource last changed",
            "etag": "the server's opaque identity for this version of the resource",
            "evidence": "what was observed, and what it does not show",
        },
        notes=[
            "⛔ A cache read is not an acquisition. This record is only written after a live "
            "retrieval; a cached copy is used as a second observation to check the first "
            "against, never as a substitute for it.",
            "⚠ The response's `Date` header is deliberately not recorded. It changes on "
            "every request, and a field that moves every run turns a byte-for-byte "
            "reproducibility check into noise. The recorded validators are properties of the "
            "resource, so they are stable.",
        ],
    )

    path = Path(out) / ACQUISITION_RECORD_PATH
    write_jsonl(path, header, rows)
    return path, hashlib.sha256(path.read_bytes()).hexdigest()


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

    retrieval = retrieve(TESTPO_URL, cache=args.cache / "testpo.440")
    identification, parsed = _parse(retrieval.payload.decode("ascii"))
    print(f"parsed {len(parsed)} published values; file sha256 {retrieval.sha256[:16]}...")

    # ⭐ Written BEFORE the value fixture, because the value fixture cites it by digest.
    #    A record produced after the file that points at it could only be pointed at by a
    #    digest taken of something else.
    record_path, record_sha = _write_acquisition_record(
        retrieval,
        identification=identification,
        out=args.out,
        script=Path(__file__),
        allow_dirty=args.allow_dirty,
    )
    print(f"acquisition record -> {record_path} (sha256 {record_sha[:16]}...)")

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
        reference=PUBLISHER_SELF_CONSISTENCY,
        generator=generator,
        generated=today(),
        title="The ephemeris publisher's own test values, as published",
        # ⭐ THE PAIR. `publisher_self_consistency` names a relationship, not a source, so
        #    the oracle has to name both of its terms or the claim is unstated. The contract
        #    refuses this file if either artifact is incomplete — see `fixture.py`'s
        #    `_SELF_CONSISTENCY_ARTIFACTS`.
        oracle={
            "publisher": "JPL Solar System Dynamics",
            "ephemeris": "DE440 / LE440",
            "claim": (
                "the values in `test_artifact` are reproduced from the data in "
                "`subject_artifact`. ⛔ Both artifacts are the publisher's own, so the "
                "publisher is on both sides and no outside reference judged anything here"
            ),
            "test_artifact": {
                "identity": "testpo.440",
                "sha256": retrieval.sha256,
                "acquired": today(),
                # ⭐ The half a digest cannot cover. `sha256` says these bytes hash to this
                #    value; it says nothing about where they came from, and a local file
                #    with the right name hashes just as convincingly. The record names the
                #    address, the date and the instrument — and states, in its own words,
                #    that it still cannot prove the publisher published anything.
                "provenance_record": {
                    "path": ACQUISITION_RECORD_PATH,
                    "sha256": record_sha,
                    "reference": "instrument",
                    "role": (
                        "attests the acquisition of this artifact. ⚠ Filed under a different "
                        "reference than this file on purpose: the acquisition is this "
                        "instrument's observation, not the publisher's claim"
                    ),
                },
                "url": TESTPO_URL,
                "size_bytes": retrieval.size_bytes,
                "identification_line": identification,
                "values_are": (
                    "taken from the original integration, for checking a reader of the "
                    "exported data against it"
                ),
                "units_as_published": {
                    "position": "au",
                    "velocity": "au/day",
                },
                "publisher_tolerance": PUBLISHER_TOLERANCE,
            },
            "subject_artifact": {
                "identity": pin.dataset,
                # ⚠ The profile is not decoration. "The same ephemeris" is distributed as
                #   several files of different spans, and a self-consistency claim about one
                #   of them is not a claim about another — the row set below is filtered to
                #   THIS file's span, and the exclusion counts are in `summary`.
                "data_profile": pin.profile,
                "sha256": pin.sha256,
                "size_bytes": pin.size_bytes,
                "sha256_verified_at_read": True,
                "publisher": pin.publisher,
                "pinned_on": pin.pinned_on,
                "span_jed_tdb": [span_start_jd, span_end_jd],
                "role": (
                    "the published data the test values are reproduced from, and the file "
                    "the reproduction check below actually read"
                ),
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
            # ⭐ A list of records, not an object keyed by the number. An integer-keyed
            #    object forces every key to be a stringified int, which reads as data
            #    hiding in the schema and diffs badly. The contract's key rule refused it,
            #    which was the right call.
            "body_numbering": {
                "note": (
                    "maps the publisher's test-file body numbers to the numbering its "
                    "binary kernels use. The two schemes are different and neither is "
                    "derivable from the other"
                ),
                "entries": [
                    {"published": published, "kernel": kernel, "body": name}
                    for (published, kernel), name in zip(
                        BODY_NUMBERING.items(), BODY_NAMES.values()
                    )
                ],
            },
            "coordinate_index": [
                {"index": index, "section": section, "component": component, "unit": unit}
                for index, (section, component, unit) in COORDINATE.items()
            ],
            "filters_applied": (
                "rows are included only where both bodies appear in the numbering map, the "
                "coordinate index is a position or velocity component, and the epoch lies "
                "within the supplied kernel's span. Every exclusion is counted by reason "
                "in `summary`"
            ),
            "regenerate": "generators/publisher_testpo.py --kernel <de440s.bsp> --out <dir>",
        },
        # ⚠ `reference_only` — "committed, not yet compared" — and it is UNCHANGED in this
        # pass only because changing it was not asked for. ⛔ The reasoning it used to rest
        # on is gone: it said that recording the publisher's tolerance would amount to
        # adopting it, and a fixture's own band is now generation context that the consumer
        # judges past. So the argument that moved the companion R2 file off `reference_only`
        # applies here too, and until someone takes that decision this file cannot pass a
        # band. See the note at the end of this header.
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
            "⭐ THE CLASSIFICATION IS AN OPEN QUESTION, RAISED HERE RATHER THAN DECIDED. "
            "`reference_only` means committed but not compared, so this file cannot pass "
            "any band that is set for it. Its companion R2 file has moved to `tolerance` "
            "with a measured band, on the argument that a fixture's own band is generation "
            "context rather than an adopted judgement. That argument applies to this file "
            "unchanged, and the measurement it would use is already in `summary`: 0 of the "
            "rows checked reach the publisher's own stated tolerance. ⛔ Changing it was "
            "not in the scope of the pass that produced this file, so it was left alone "
            "rather than altered quietly.",
        ],
    )

    # ⭐ Derived from the file that was actually verified, never hard-coded.
    out_path = (
        Path(args.out)
        / "kernel"
        / pin.dataset.removesuffix(".bsp")
        / "publisher-test-values.jsonl"
    )
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
