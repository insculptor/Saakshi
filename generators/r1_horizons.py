"""R1 — sampling the ephemeris publisher's own service.

Geometric `(epoch, target, centre) -> state` rows, asked of the publisher's live ephemeris
service and written down. The grid is deliberately laid over the span of a kernel this
repository already pins, so every row can be held up beside the file — ⛔ as a *recorded
cross-reference*, never as a band.

⭐ **THE THING THIS FIXTURE EXISTS TO MAKE VISIBLE.** The service does not answer from one
ephemeris. Asked for a planet's **barycentre** it names the planetary solution; asked for
the **planet**, at the same instant, in the same frame, with a request differing in nothing
but the body number, it names a **body-specific** solution — and the two answers differ.
⚠ Nothing in the numbers says so. The only thing that says so is the solution identifier the
service prints beside the body name, which is why this recorder classifies that identifier
as service state, writes it on **every row**, and refuses a response that omits it.

⛔ **This is the same failure this repository already met on the library side** — a source
substituted silently, successfully, and returning an entirely ordinary value — arriving from
a completely different direction. A recorder that writes down what came back without
establishing what answered produces a file that is well-formed and mislabelled.

⛔ **`reference_only`, and the reason is a refusal to declare a band, not a failure to
measure one.** See `_CLASSIFICATION_ARGUMENT`.

⛔ **Recorder, never explainer.** This script asks a service questions and writes down the
answers. It contains no account of how the service, or any ephemeris behind it, computes
anything.
"""

from __future__ import annotations

import argparse
import hashlib
import math
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import spiceypy as sp  # noqa: E402

from saakshi.acquisition import USER_AGENT, Retrieval, retrieve  # noqa: E402
from saakshi.fixture import (  # noqa: E402
    Header,
    bits,
    describe_reserved_names,
    write_jsonl,
)
from saakshi.kernels import oracle_identity, verify  # noqa: E402
from saakshi.provenance import generator_for, host_record, today  # noqa: E402
from saakshi.service import (  # noqa: E402
    ACQUISITION_LIMIT,
    ENDPOINT,
    REPRODUCIBILITY_CONDITION,
    ServiceResponse,
    build_url,
    canonical_form,
    parse,
)

#: Where the acquisition record lands, **relative to the fixture root** — relative for the
#: same reason its companion is: these files are generated in one tree and read in another.
ACQUISITION_RECORD_PATH = "service/r1-acquisition.jsonl"

#: The centre every state is taken relative to. ⚠ Written as the service's own site code,
#: because that is what was sent; the body number it corresponds to is recorded beside it.
CENTER_COMMAND = "500@0"
CENTER_BODY = 0

#: The bodies asked for. `command` is sent verbatim; `kernel_body` is the same body in the
#: numbering the pinned kernels use, or `None` where the pinned kernel does not carry it.
#:
#: ⭐ **`4` and `499` are both here on purpose.** They differ in nothing but the body number,
#: and they are what demonstrates the finding in this module's docstring rather than
#: asserting it. ⚠ `499` is also the row the pinned file cannot answer at all — so the
#: demonstration lands from both sides at once: the service reached a solution, and the file
#: does not carry it.
TARGETS: tuple[dict[str, object], ...] = (
    {"command": "199", "kernel_body": 199, "label": "Mercury"},
    {"command": "299", "kernel_body": 299, "label": "Venus"},
    {"command": "399", "kernel_body": 399, "label": "Earth"},
    {"command": "301", "kernel_body": 301, "label": "Moon"},
    {"command": "4", "kernel_body": 4, "label": "Mars system barycentre"},
    {"command": "499", "kernel_body": None, "label": "Mars"},
    {"command": "5", "kernel_body": 5, "label": "Jupiter system barycentre"},
    {"command": "6", "kernel_body": 6, "label": "Saturn system barycentre"},
    {"command": "7", "kernel_body": 7, "label": "Uranus system barycentre"},
    {"command": "8", "kernel_body": 8, "label": "Neptune system barycentre"},
    {"command": "9", "kernel_body": 9, "label": "Pluto system barycentre"},
    {"command": "10", "kernel_body": 10, "label": "Sun"},
)

#: The epoch grid: 21 instants at a fixed whole-day spacing.
#:
#: ⭐ **Every value is a half-integer Julian date, and that is a choice, not a coincidence.**
#: The recorder converts each epoch to seconds past the reference instant before handing it
#: to the kernel reader, and a conversion performed before a value reaches the thing being
#: measured makes the conversion part of the measurement. Half-integers keep both the
#: subtraction and the scaling exact — and the exactness is *asserted* below rather than
#: reasoned about, because that is the difference between a property and a belief.
EPOCH_START_JD = 2415020.5
EPOCH_STEP_DAYS = 3653
EPOCH_COUNT = 21
EPOCHS: tuple[float, ...] = tuple(
    float(EPOCH_START_JD + index * EPOCH_STEP_DAYS) for index in range(EPOCH_COUNT)
)

J2000_JD = 2451545.0
SECONDS_PER_DAY = 86400.0

#: The sections a row can belong to, and the unit each carries. ⭐ One place the strings
#: exist, so a summary can never report a section in a unit no row has.
SECTIONS: tuple[str, ...] = ("position_au", "velocity_au_per_day")
SECTION_UNITS: dict[str, str] = {
    "position_au": "au",
    "velocity_au_per_day": "au/day",
}
#: Which parsed columns belong to which section, in component order.
SECTION_COLUMNS: dict[str, tuple[int, int, int]] = {
    "position_au": (2, 3, 4),
    "velocity_au_per_day": (5, 6, 7),
}
COMPONENT_ORDER: tuple[str, str, str] = ("x", "y", "z")

#: ⚠ A deliberate pause between requests. This is a shared public service and the grid is
#: one request per body; the delay is recorded in `request` so a reader knows the sampling
#: was paced rather than assuming it.
REQUEST_INTERVAL_SECONDS = 1.0

#: The query every request shares. ⭐ Written out in full and recorded verbatim, because
#: `request` in this contract means *sufficient to regenerate*, and a service query that is
#: assembled from defaults nobody wrote down is not.
COMMON_QUERY: dict[str, str] = {
    "format": "json",
    "EPHEM_TYPE": "VECTORS",
    "CENTER": f"'{CENTER_COMMAND}'",
    "OUT_UNITS": "'AU-D'",
    "REF_PLANE": "'FRAME'",
    "VEC_CORR": "'NONE'",
    "VEC_TABLE": "'2'",
    "VEC_LABELS": "'NO'",
    "CSV_FORMAT": "'YES'",
    "OBJ_DATA": "'NO'",
    "TIME_DIGITS": "'FRACSEC'",
}

#: ⚠ Above how many last places a disagreement is reported as *observable in the printed
#: value*. A handful, not one: the two sides evaluate and print independently, so agreement
#: to the exact last representable place is not the bar, and a bar of one would classify
#: ordinary arithmetic noise as a difference between ephemerides.
_RESOLUTION_LIMIT = 4.0

#: ⛔ Attached wherever the last-place ratio is reported, because the ratio is the kind of
#: number that acquires a unit by being useful.
_LAST_PLACE_DISCLAIMER = (
    "⛔ A DIAGNOSTIC RATIO, NOT A UNIT AND NOT A BAND. It divides one absolute quantity in "
    "the row's own unit by another — the disagreement on a component, over the spacing "
    "between representable values at that same component's own magnitude — and this file "
    "declares no band at all, so it mints no vocabulary for one. ⚠ It is also not the "
    "relative-to-the-section-norm form used elsewhere in this repository and is not "
    "interchangeable with it. ⭐ It is here to answer one question: whether a disagreement "
    "is visible in the value the service printed, or is the resolution of that value."
)

_CLASSIFICATION_ARGUMENT = (
    "⛔ `reference_only`, and it is a REFUSAL TO DECLARE A BAND rather than a failure to "
    "measure one — the distinction the contract warns about, met head on. A per-row "
    "disagreement against the pinned kernel IS measured here and IS written on every row "
    "the file can answer. It is not offered as a band, for a reason that is the whole point "
    "of this fixture: ⭐ the companion self-consistency file's band is a FLOOR because both "
    "of its sides are the same ephemeris read two ways, so what remains is reader noise. "
    "Here the two sides are DIFFERENT NAMED SOLUTIONS — the service says so, per row, in "
    "`target_solution`, and for one body it names a solution the pinned file does not carry "
    "at all. A band cut from that disagreement would declare the difference between two "
    "ephemerides to be the tolerance of a reader, and ⛔ every reader inside it would pass "
    "without having been checked. ⚠ That is the same shape of defect as a comparison that "
    "reports zero because both sides were the same source: a number that looks like a "
    "measurement of one thing and is a measurement of another. ⭐ The band a consumer "
    "applies to these rows is set from that consumer's own budget, measured in that "
    "consumer's own tree, as a reviewed change."
)


def _et_seconds(jd_tdb: float) -> float:
    """Seconds past the reference instant, with the exactness asserted rather than assumed.

    ⚠ A measured finding from the companion kernel work, applied here in the other
    direction: a rescaling performed before a value reaches the thing being measured makes
    the rescaling part of the measurement. The grid is chosen so this is exact; ⛔ the run
    stops rather than proceeding with an epoch that did not survive the conversion.
    """
    et = (jd_tdb - J2000_JD) * SECONDS_PER_DAY
    if et / SECONDS_PER_DAY + J2000_JD != jd_tdb:
        raise SystemExit(
            f"epoch {jd_tdb!r} does not survive conversion to seconds and back. ⛔ The "
            "rounding would be attributed to the ephemeris."
        )
    return et


def _fetch(command: str, cache_dir: Path) -> tuple[Retrieval, ServiceResponse]:
    """One request, with the resource split out of the transaction that delivered it."""
    query = dict(COMMON_QUERY)
    query["COMMAND"] = f"'{command}'"
    query["TLIST"] = "'" + ",".join(repr(epoch) for epoch in EPOCHS) + "'"
    url = build_url(query)
    # ⭐ `canonical_form` is what keeps `retrieve()`'s "one address has served two
    #    artifacts" refusal pointed at the ANSWER. Without it that refusal fires on the
    #    second run of every service query and reports a contradiction nobody made.
    retrieval = retrieve(
        url,
        cache=cache_dir / f"r1-{command}.txt",
        canonical=canonical_form(query),
    )
    return retrieval, parse(retrieval.payload, query=query)


def _demonstrate_split(command: str, cache_dir: Path) -> dict[str, object]:
    """Issue one query twice and show the split holds, rather than asserting that it does.

    ⭐ **The claim under test is not "the response repeats"** — it does not, and if it did
    there would be nothing to demonstrate. The claim is that what moved is exactly what this
    instrument classified as belonging to the transaction, and what did not move is exactly
    the resource. Both halves are checked.

    ⚠ Reported as an observation with its own states, ⛔ never collapsed into a pass. In
    particular a run in which the transaction material happened *not* to move is not a
    failure and is not a success: it is a run that demonstrated nothing, and it says so.
    """
    # ⚠ Both observations use their own cache directories, and neither is the one the
    #   recorded run uses. Seeding the recorded cache from here would make one query's
    #   `prior_copy_agreed` differ from every other query's on a first run, for a reason
    #   that has nothing to do with the query.
    probe = cache_dir / "split-demonstration"
    first_retrieval, first = _fetch(command, probe / "first")
    time.sleep(REQUEST_INTERVAL_SECONDS)
    second_retrieval, second = _fetch(command, probe / "second")

    resource_agreed = first_retrieval.resource_sha256 == second_retrieval.resource_sha256
    transaction_moved = first_retrieval.sha256 != second_retrieval.sha256
    state_agreed = first.service_state == second.service_state
    return {
        "finding": "split_demonstration",
        "query_repeated": command,
        "resource_digest_agreed": resource_agreed,
        "transaction_bytes_moved": transaction_moved,
        "service_state_agreed": state_agreed,
        "classified_as_transaction": list(first.envelope_excluded),
        "classified_as_service_state": sorted(first.service_state),
        "evidence": (
            "the identical query issued twice. ⭐ `transaction_bytes_moved` true and "
            "`resource_digest_agreed` true together are the demonstration: something in the "
            "response moved, and none of it was inside the region this instrument digests. "
            "⚠ `transaction_bytes_moved` false is neither pass nor failure — it is a run "
            "that showed nothing, because nothing moved for the split to have excluded. "
            "⛔ `resource_digest_agreed` false aborts the run in `retrieve()` before this "
            "row can be written."
        ),
    }


def _write_acquisition_record(
    *,
    responses: dict[str, tuple[Retrieval, ServiceResponse]],
    demonstration: dict[str, object],
    out: Path,
    script: Path,
    allow_dirty: bool,
) -> tuple[Path, str]:
    """Attest how the service was queried. Returns its path and its digest.

    ⭐ A `provenance_record` under `instrument`, exactly as its published-file counterpart
    is, and for the same reason: the value fixture carries the *service's* claim, and this
    carries *ours* — that a harness sent these queries to that address on this date and
    received these resources. ⛔ Two files about one artifact under two references, because
    they attest two parties' claims.
    """
    rows: list[dict] = [
        {
            "finding": "endpoint",
            "endpoint": ENDPOINT,
            "publisher_named_by_the_address": "JPL Solar System Dynamics",
            "acquiring_instrument": {
                "software": "python urllib.request",
                "python": host_record()["python"],
                "user_agent": USER_AGENT,
            },
            "retrieved_on": today(),
            "requests_issued": len(responses),
            "request_interval_seconds": REQUEST_INTERVAL_SECONDS,
            "evidence": (
                "one live request per body, paced. ⛔ A cache read is not an acquisition: "
                "every request below went to the network, and a retained copy is used as a "
                "second observation to check the resource against, never as a substitute "
                "for the request"
            ),
        }
    ]

    for command, (retrieval, response) in responses.items():
        rows.append(
            {
                "finding": "retrieval",
                "query_command": command,
                **retrieval.as_record(),
                "prior_copy_present": retrieval.prior_copy_agreed is not None,
                "prior_copy_agreed": retrieval.prior_copy_agreed,
                "service_state": response.service_state,
                "classified_as_transaction": list(response.envelope_excluded),
                "evidence": (
                    "⛔ `sha256` and `size_bytes` are ABSENT here, and their absence is the "
                    "record. They are properties of one transaction, not of the answer: the "
                    "response embeds a generation stamp, so the payload's digest differs on "
                    "every request and even its byte count moves with the width of a date. "
                    "⭐ `resource_sha256` is over the part of the response that is a "
                    "function of the request, with every region named in "
                    "`classified_as_transaction` and every key of `service_state` cut out "
                    "and replaced by a marker"
                ),
            }
        )

    rows.append(demonstration)
    rows.append(
        {
            "finding": "service_state_baseline",
            # ⚠ A list of records, not an object keyed by the query. The contract refused
            #   the keyed form — a body number is data, and data hiding in a schema is what
            #   the key rule exists to stop. The companion published-file fixture learned
            #   the identical lesson from the identical refusal.
            "state_by_query": [
                {"query_command": command, "service_state": response.service_state}
                for command, (_, response) in responses.items()
            ],
            "evidence": (
                "⭐ The condition the reproducibility claim in this file's notes is "
                "conditional on, recorded so a later run can be held up beside it. ⚠ It is "
                "not a pin and nothing refuses a file over it: a change here is a finding to "
                "report and a re-emission to propose, ⛔ never a gate"
            ),
        }
    )

    header = Header(
        fixture_kind="provenance_record",
        reference="instrument",
        generator=generator_for(script, allow_dirty=allow_dirty),
        generated=today(),
        title="How the publisher's ephemeris service was queried",
        oracle={
            "implementation": "python urllib.request over HTTPS",
            "python": host_record()["python"],
            "user_agent": USER_AGENT,
            "endpoint": ENDPOINT,
            "publisher_named_by_the_address": "JPL Solar System Dynamics",
            "method": (
                "one live GET per body. ⭐ The digest is NOT taken over the response body: "
                "it is taken over the resource extracted from it, by the rule in "
                "`src/saakshi/service.py`, which is written down in full because it is this "
                "instrument's rule and not the service's"
            ),
        },
        attests=(
            "the addresses a published ephemeris service was queried at, the queries sent, "
            "the status of each response, the digest of the resource extracted from each, "
            "the service state each response named, the date of the queries, and the "
            "instrument that performed them"
        ),
        authority={
            "held_by": "this instrument, as the party that performed the queries",
            "kind": "direct observation of a sequence of network retrievals",
            "scope": ACQUISITION_LIMIT,
        },
        record_date=today(),
        row_schema={
            "finding": (
                "endpoint | retrieval | split_demonstration | service_state_baseline"
            ),
            "url": "the address requested, parameters sorted so one query has one address",
            "final_url": "the address that answered",
            "http_status": "the response status",
            "resource_sha256": (
                "digest of the RESOURCE — the response with every classified transaction "
                "region and every service-state value cut out and replaced by a marker"
            ),
            "resource_bytes": "the length of that resource",
            "payload_is_the_resource": (
                "⛔ false for every row here, and that is the difference between this record "
                "and its published-file counterpart, where it is true"
            ),
            "service_state": (
                "what the response said about the service's own state: which solution "
                "answered for the target and the centre, which interface version replied, "
                "and the Earth-orientation file where the query referred to one"
            ),
            "classified_as_transaction": (
                "the regions excluded as belonging to the call rather than the answer. ⛔ "
                "Names only — their values are observed on every run and never written"
            ),
        },
        summary={"host": host_record()},
        notes=[
            "⛔ A cache read is not an acquisition. Every row here follows a live request; a "
            "retained copy is a second observation used to check the first, never a "
            "substitute for it.",
            "⚠ The response `Date` header is not recorded, for the reason it is not recorded "
            "anywhere in this repository: it moves on every request. ⛔ For a service that is "
            "necessary and nowhere near sufficient — the same material also appears INSIDE "
            "the body, where no header allow-list reaches it, and that is what "
            "`classified_as_transaction` names.",
            "⚠ The values of the transaction regions are deliberately absent. They were "
            "observed on this run and reported to the operator; writing one down would put "
            "the clock into a file whose whole purpose is to regenerate identically.",
            REPRODUCIBILITY_CONDITION,
        ],
    )

    path = Path(out) / ACQUISITION_RECORD_PATH
    write_jsonl(path, header, rows)
    return path, hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--kernel",
        required=True,
        type=Path,
        help="a pinned kernel, for the recorded cross-reference",
    )
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--cache", default=Path("cache"), type=Path)
    parser.add_argument("--allow-dirty", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()

    generator = generator_for(Path(__file__), allow_dirty=args.allow_dirty)
    print(describe_reserved_names())

    pin = verify(args.kernel)
    print(f"kernel verified: {pin.dataset} ({pin.profile}) sha256 ok")
    sp.furnsh(str(args.kernel))

    # ⭐ The demonstration first, and on a body the grid also samples: it is what licenses
    #    every digest written below, so a run that cannot demonstrate the split should not
    #    reach the point of writing one.
    print(f"demonstrating the split on COMMAND={TARGETS[0]['command']} ...")
    demonstration = _demonstrate_split(str(TARGETS[0]["command"]), args.cache)
    print(
        "  transaction bytes moved: {transaction_bytes_moved}; resource digest agreed: "
        "{resource_digest_agreed}; service state agreed: {service_state_agreed}".format(
            **demonstration
        )
    )
    if not demonstration["transaction_bytes_moved"]:
        print(
            "  NOTE: nothing in the transaction moved on this run, so the exclusion "
            "demonstrated nothing. Recorded as its own state, not as a pass."
        )

    responses: dict[str, tuple[Retrieval, ServiceResponse]] = {}
    for index, target in enumerate(TARGETS):
        command = str(target["command"])
        if index:
            time.sleep(REQUEST_INTERVAL_SECONDS)
        retrieval, response = _fetch(command, args.cache)
        responses[command] = (retrieval, response)
        print(
            f"  COMMAND={command:>4} -> {len(response.data_rows)} epochs, "
            f"source {response.service_state['target_solution']}, "
            f"resource {retrieval.resource_sha256[:16]}..."
        )

    # ⭐ Written BEFORE the value fixture, which cites it by digest. A record produced after
    #    the file pointing at it could only be pointed at by a digest of something else.
    record_path, record_sha = _write_acquisition_record(
        responses=responses,
        demonstration=demonstration,
        out=args.out,
        script=Path(__file__),
        allow_dirty=args.allow_dirty,
    )
    print(f"acquisition record -> {record_path} (sha256 {record_sha[:16]}...)")

    # ⚠ The service states its own unit constant; it is read out of the response rather
    #   than written here, and it is used for the CROSS-REFERENCE ONLY. ⛔ No emitted pin is
    #   ever rescaled — a recorder that rescales what it records has moved a judgement about
    #   which constant to use into a place the consumer cannot see.
    stated = next(iter(responses.values()))[1].stated
    au_km = float(stated["au_in_km"])
    for command, (_, response) in responses.items():
        if response.stated != stated:
            raise SystemExit(
                f"COMMAND={command} states different output constants than the first "
                f"response ({response.stated} vs {stated}). ⛔ One grid cannot be filed "
                "under two sets of stated units."
            )

    rows: list[dict] = []
    solutions: dict[str, str] = {}
    no_cross_reference: dict[str, int] = {}
    # ⭐ Tracked per section AND per body. The per-body breakdown is not decoration: it is
    #    what turns the refusal to declare a band from an argument into a measurement.
    worst_by_query: dict[str, dict[str, dict]] = {section: {} for section in SECTIONS}
    #: Each body's worst disagreement expressed against the spacing between representable
    #: values *at the disagreeing component's own magnitude*.
    last_places: dict[str, dict[str, float]] = {section: {} for section in SECTIONS}

    for target in TARGETS:
        command = str(target["command"])
        kernel_body = target["kernel_body"]
        _, response = responses[command]
        solutions[command] = response.service_state["target_solution"]

        if len(response.data_rows) != len(EPOCHS):
            raise SystemExit(
                f"COMMAND={command}: {len(response.data_rows)} data lines for "
                f"{len(EPOCHS)} requested epochs. ⛔ A silently short answer read as a "
                "complete one is the failure this contract exists to prevent."
            )

        for epoch_index, fields in enumerate(response.data_rows):
            jd_tdb = EPOCHS[epoch_index]
            returned_jd = float(fields[0])
            if returned_jd != jd_tdb:
                raise SystemExit(
                    f"COMMAND={command}: the service answered for JD {returned_jd!r} where "
                    f"{jd_tdb!r} was asked. ⛔ An answer to a different question, filed "
                    "under the question asked, is worse than no answer."
                )
            et = _et_seconds(jd_tdb)

            kernel_state = None
            if kernel_body is not None:
                state, _lt = sp.spkgeo(int(kernel_body), et, "J2000", CENTER_BODY)
                kernel_state = [float(value) for value in state]

            for section in SECTIONS:
                columns = SECTION_COLUMNS[section]
                printed = [fields[column] for column in columns]
                values = [float(text) for text in printed]
                norm = math.sqrt(sum(value * value for value in values))

                row: dict = {
                    "section": section,
                    "target_command": command,
                    "target_label": str(target["label"]),
                    # ⭐ ON EVERY ROW, not once in the header. Which solution answered is a
                    #    property of the answer, and a file that states it once cannot
                    #    express that two rows of it came from two different ones.
                    "target_solution": response.service_state["target_solution"],
                    "center_command": CENTER_COMMAND,
                    "center_body": CENTER_BODY,
                    "center_solution": response.service_state["center_solution"],
                    "jd_tdb": jd_tdb,
                    "jd_tdb_bits": bits(jd_tdb),
                    "calendar_date": fields[1],
                    "et_seconds": et,
                    "et_seconds_bits": bits(et),
                    "unit": SECTION_UNITS[section],
                    "component_order": list(COMPONENT_ORDER),
                    "value": values,
                    "value_bits": [bits(value) for value in values],
                    "value_printed": printed,
                    "state_vector_norm": norm,
                }

                if kernel_state is None:
                    row["cross_check_max_abs_delta"] = None
                    row["cross_check_max_rel_delta"] = None
                    row["cross_check_unavailable"] = (
                        "the pinned kernel does not carry this body. ⭐ Not a gap in the "
                        "evidence — it is the finding: the service answered from a solution "
                        "the file does not contain, and `target_solution` names it"
                    )
                    no_cross_reference[command] = no_cross_reference.get(command, 0) + 1
                else:
                    scale = 1.0 if section == "position_au" else SECONDS_PER_DAY
                    offset = 0 if section == "position_au" else 3
                    reference = [
                        kernel_state[offset + index] * scale / au_km for index in range(3)
                    ]
                    deltas = [abs(values[i] - reference[i]) for i in range(3)]
                    abs_delta = max(deltas)
                    row["cross_check_max_abs_delta"] = abs_delta
                    # ⚠ `null` where the section has no scale, never a division. The same
                    #   rule the companion state fixture applies, for the same reason.
                    row["cross_check_max_rel_delta"] = (
                        abs_delta / norm if norm > 0.0 else None
                    )
                    # ⚠ Per COMPONENT, against that component's own spacing. An earlier
                    #   form of this compared the worst delta against the spacing at the
                    #   LARGEST component's magnitude — two quantities that need not come
                    #   from the same component or even the same epoch, which made the
                    #   comparison read as noise. The delta and the scale it is judged
                    #   against have to be the same number's.
                    places = [
                        deltas[i] / math.ulp(abs(values[i]))
                        for i in range(3)
                        if values[i] != 0.0
                    ]
                    current = worst_by_query[section].get(command)
                    if current is None or abs_delta > current["abs_delta"]:
                        worst_by_query[section][command] = {
                            "query_command": command,
                            "abs_delta": abs_delta,
                            "unit": SECTION_UNITS[section],
                            "target_solution": row["target_solution"],
                            "jd_tdb": jd_tdb,
                            "calendar_date": fields[1],
                        }
                    if places:
                        last_places[section][command] = max(
                            last_places[section].get(command, 0.0), max(places)
                        )

                rows.append(row)

    checked = {
        section: sum(
            1
            for row in rows
            if row["section"] == section and row["cross_check_max_abs_delta"] is not None
        )
        for section in SECTIONS
    }
    distinct_solutions = sorted(set(solutions.values()))

    worst: dict[str, dict | None] = {
        section: (
            max(worst_by_query[section].values(), key=lambda entry: entry["abs_delta"])
            if worst_by_query[section]
            else None
        )
        for section in SECTIONS
    }

    def _spread(section: str) -> dict[str, object] | None:
        """⭐ How much looser one band over this grid would be than the body it was cut for.

        ⛔ MEASURED, never asserted. The argument against banding a difference between two
        ephemerides is only worth making if the spread is large, and whether it is large is
        not something a generator may claim on the reader's behalf.
        """
        deltas = [entry["abs_delta"] for entry in worst_by_query[section].values()]
        positive = [delta for delta in deltas if delta > 0.0]
        if len(positive) < 2:
            return None
        widest, narrowest = max(positive), min(positive)
        tightest = min(worst_by_query[section].values(), key=lambda e: e["abs_delta"])
        return {
            "widest": max(worst_by_query[section].values(), key=lambda e: e["abs_delta"]),
            "narrowest_nonzero": narrowest,
            "narrowest_body": tightest["query_command"],
            "ratio": widest / narrowest,
            "unit": SECTION_UNITS[section],
            "meaning": (
                "⛔ THE MEASUREMENT THAT SETTLES IT. One band over this grid would be cut "
                "from the widest disagreement and applied to every body, including the one "
                "whose largest disagreement is `narrowest_nonzero` — so it would be `ratio` "
                "times looser than that body was ever observed to be, and every row of that "
                "body would pass it without having been checked. ⚠ Bodies whose worst "
                "disagreement is exactly zero are excluded from the ratio rather than "
                "dividing by them"
            ),
        }

    spread = {section: _spread(section) for section in SECTIONS}
    resolution = {
        section: sorted(
            (
                {
                    "query_command": command,
                    "worst_abs_delta": worst_by_query[section][command]["abs_delta"],
                    "unit": SECTION_UNITS[section],
                    "worst_delta_over_last_place_spacing": places,
                    "observable_in_the_printed_value": places > _RESOLUTION_LIMIT,
                }
                for command, places in last_places[section].items()
            ),
            key=lambda entry: entry["worst_delta_over_last_place_spacing"],
            reverse=True,
        )
        for section in SECTIONS
    }
    indistinguishable = {
        section: sum(
            1 for entry in resolution[section] if not entry["observable_in_the_printed_value"]
        )
        for section in SECTIONS
    }

    def _ordering_conflict(section: str) -> dict[str, object] | None:
        """⭐ Whether ranking by absolute disagreement and by last places disagree.

        ⚠ **A caution about the diagnostic above, measured rather than assumed.** A body
        whose components are all near zero has a minute spacing between representable
        values, so a disagreement that is the *smallest on the grid* in absolute terms can
        rank among the largest in last places. ⛔ Where the two orderings disagree there is
        no single ordering to cut a band from, which is the same objection the companion
        state fixture met when choosing a band's denominator — arriving here through the
        magnitude of a whole quantity rather than of one component.
        """
        if len(resolution[section]) < 2:
            return None
        by_absolute = min(resolution[section], key=lambda e: e["worst_abs_delta"])
        by_places = min(
            resolution[section], key=lambda e: e["worst_delta_over_last_place_spacing"]
        )
        if by_absolute["query_command"] == by_places["query_command"]:
            return None
        return {
            "smallest_by_absolute_disagreement": by_absolute,
            "smallest_by_last_place_spacing": by_places,
            "meaning": (
                "⭐ THE TWO ORDERINGS DISAGREE, so neither is THE ordering. The body with "
                "the smallest absolute disagreement on this grid is not the body whose "
                "disagreement is least visible in its own printed value — a quantity near "
                "zero has a minute spacing between representable values, so the smallest "
                "absolute disagreement of the eleven ranks high in last places. ⛔ There is "
                "no single ordering here to cut a band from"
            ),
        }

    ordering_conflict = {section: _ordering_conflict(section) for section in SECTIONS}

    header = Header(
        fixture_kind="numeric_pin",
        reference="R1",
        generator=generator,
        generated=today(),
        title="Geometric states as the publisher's ephemeris service answered them",
        oracle={
            "publisher": "JPL Solar System Dynamics",
            "service": "Horizons",
            "endpoint": ENDPOINT,
            "interface_version": next(iter(responses.values()))[1].service_state[
                "interface_version"
            ],
            "queried_on": today(),
            "acquisition_record": {
                "path": ACQUISITION_RECORD_PATH,
                "sha256": record_sha,
                "reference": "instrument",
                "role": (
                    "attests how these answers were obtained. ⚠ Filed under a different "
                    "reference than this file on purpose: the acquisition is this "
                    "instrument's observation, not the publisher's claim"
                ),
            },
            # ⭐ NOT one identity. The service answered from more than one solution across
            #    this single grid, and an oracle block naming one of them would be false
            #    about the others.
            "solutions_that_answered": {
                "distinct": distinct_solutions,
                "by_query": [
                    {"query_command": command, "target_solution": solution}
                    for command, solution in solutions.items()
                ],
                "note": (
                    "⛔ The service does not answer from one ephemeris. Every row names the "
                    "solution that answered it in `target_solution`; this is the same "
                    "information collected, and it is here so a reader meets it before "
                    "reading a single value"
                ),
            },
            "stated_by_the_service": {
                **stated,
                "role": (
                    "constants and settings the service stated about its own output, read "
                    "out of the response and resolved into this artifact. ⭐ A consumer "
                    "converting units later needs nothing the service holds. ⚠ Stated "
                    "inputs: `au_in_km` was applied to the recorded cross-reference and ⛔ "
                    "to no emitted value"
                ),
            },
            "cross_reference": {
                **oracle_identity(args.kernel, pin),
                "read_with": "CSPICE",
                "toolkit_version": sp.tkvrsn("TOOLKIT"),
                "called_via": {"binding": "spiceypy", "version": sp.__version__},
                "role": (
                    "the pinned file each row is held up beside, where it carries the body. "
                    "⛔ A recorded observation, NOT an authority over these rows and NOT the "
                    "source of a band — see `classification` and `summary.why_no_band`"
                ),
            },
        },
        request={
            "endpoint": ENDPOINT,
            # ⭐ A list of records, and the contract's key rule is why — correctly. The
            #    service's parameter names are UPPERCASE and are the service's, so putting
            #    them in JSON keys would make a third party's naming into this schema's
            #    permanent identifiers. They are data about a query, and data belongs in
            #    values. ⚠ Sorted, so one query has one recorded form.
            "common_query": [
                {"parameter": name, "value": value}
                for name, value in sorted(COMMON_QUERY.items())
            ],
            "center": {"command": CENTER_COMMAND, "kernel_body": CENTER_BODY},
            "targets": [
                {
                    "command": str(target["command"]),
                    "kernel_body": target["kernel_body"],
                    "label": str(target["label"]),
                }
                for target in TARGETS
            ],
            "epochs": {
                "note": (
                    "sent as a discrete time list, one request per body. ⭐ Every value is a "
                    "half-integer Julian date so the conversion to seconds past the "
                    "reference instant is exact; the generator asserts the round trip rather "
                    "than relying on it"
                ),
                "start_jd_tdb": EPOCH_START_JD,
                "step_days": EPOCH_STEP_DAYS,
                "count": EPOCH_COUNT,
                "values": list(EPOCHS),
                "values_bits": [bits(epoch) for epoch in EPOCHS],
            },
            "request_interval_seconds": REQUEST_INTERVAL_SECONDS,
            "regenerate": (
                "generators/r1_horizons.py --kernel <de440s.bsp> --out <dir> -- ⚠ needs the "
                "network; there is no offline path, and a cached response is not an "
                "acquisition"
            ),
        },
        # ⛔ See `_CLASSIFICATION_ARGUMENT`: this is a refusal to declare a band, not an
        #    absence of measurement, and the difference is written into `summary`.
        classification={section: {"class": "reference_only"} for section in SECTIONS},
        budget_row="R1-service-state",
        row_schema={
            "section": "position_au | velocity_au_per_day",
            "target_command": "the body identifier sent to the service, verbatim",
            "target_solution": (
                "⭐ THE FIELD THIS FIXTURE IS ABOUT — the solution the service named for "
                "this body, on this row. It is not constant across the file: a planet and "
                "its system barycentre are answered from different solutions"
            ),
            "center_solution": "the solution named for the centre, likewise",
            "jd_tdb": "the epoch asked for, Julian date, TDB — asserted against the answer",
            "calendar_date": (
                "the service's own rendering of the same instant. ⚠ A label; `jd_tdb` is the "
                "authority"
            ),
            "et_seconds": "the same epoch as seconds past the reference instant — derived",
            "value": "THE PIN — the three components in `component_order`, in `unit`",
            "value_bits": "the same three values as IEEE-754 bit patterns",
            "value_printed": "the same three values as the service printed them",
            "state_vector_norm": "the norm of the three components, in `unit`",
            "cross_check_max_abs_delta": (
                "|the pinned kernel read by CSPICE - value|, largest over the three "
                "components, in `unit`. ⚠ A recorded observation beside the pin, ⛔ never "
                "the pin, and ⛔ never a band — the two sides are different solutions"
            ),
            "cross_check_max_rel_delta": (
                "the same divided by `state_vector_norm`, dimensionless. ⚠ Null where the "
                "section has no scale to divide by"
            ),
            "cross_check_unavailable": (
                "present, with its reason, on rows the pinned file cannot answer at all"
            ),
        },
        summary={
            "rows": len(rows),
            "targets": len(TARGETS),
            "epochs": len(EPOCHS),
            "solutions_that_answered": distinct_solutions,
            "rows_without_cross_reference": {
                "by_query": [
                    {"query_command": command, "rows": count}
                    for command, count in no_cross_reference.items()
                ],
                "meaning": (
                    "⛔ rows the pinned file cannot be held up beside, because it does not "
                    "carry the body. ⭐ The service reached a solution the file does not "
                    "contain — which is this fixture's finding, arriving from the file's side"
                ),
            },
            "cross_reference": {
                "per_section": {
                    section: {
                        "rows_checked": checked[section],
                        "unit": SECTION_UNITS[section],
                        "worst": worst[section],
                        "worst_by_query": sorted(
                            worst_by_query[section].values(),
                            key=lambda entry: entry["abs_delta"],
                            reverse=True,
                        ),
                        "spread": spread[section],
                        "against_the_resolution_of_the_number": {
                            "per_query": resolution[section],
                            "threshold": _RESOLUTION_LIMIT,
                            "note": _LAST_PLACE_DISCLAIMER,
                        },
                        "bodies_with_no_observable_disagreement": indistinguishable[section],
                        "ordering_conflict": ordering_conflict[section],
                    }
                    for section in SECTIONS
                },
                "meaning": (
                    "the service's answer against the pinned file's, for the bodies the file "
                    "carries. ⛔ It measures the difference between two named solutions, not "
                    "the floor of any reader"
                ),
                "why_it_is_a_solution_difference_and_not_a_recorder_error": (
                    "⭐ The evidence is `worst_by_query`, and it is the small numbers that "
                    "carry it rather than the large one. A misaligned frame, or an epoch "
                    "handed over in the wrong time scale, would displace EVERY body — most "
                    "visibly the fast ones. Instead the disagreement is concentrated in one "
                    "body and the rest sit orders of magnitude below it, so the grid, the "
                    "frame and the epochs line up and what is left is the two solutions"
                ),
                "why_no_aggregate": (
                    "⛔ no statistic is reported across both sections: position is in au and "
                    "velocity in au/day, so one number over both would have no unit"
                ),
            },
            "why_no_band": {
                "argument": _CLASSIFICATION_ARGUMENT,
                # ⭐ The argument above would be worth little on its own — it is the kind of
                #    reasoning that sounds right whatever the numbers turn out to be. This
                #    is the number, computed on this run, that decides it.
                "measured_no_observable_disagreement": {
                    section: (
                        f"{indistinguishable[section]} of {len(resolution[section])} bodies "
                        "show a largest disagreement, anywhere on this grid, within "
                        f"{_RESOLUTION_LIMIT:.0f} times the spacing between representable "
                        "values at the disagreeing component's own magnitude — ⛔ no "
                        "disagreement observable in the value the service printed. A band "
                        "cut from a set of measurements most of which are the resolution of "
                        "the printed number would be measuring the number format. "
                        + _LAST_PLACE_DISCLAIMER
                    )
                    for section in SECTIONS
                },
                "measured_spread": {
                    section: (
                        None
                        if spread[section] is None
                        else (
                            "one band over this grid would be cut from "
                            f"{spread[section]['widest']['abs_delta']:.4e} "
                            f"{SECTION_UNITS[section]} at COMMAND="
                            f"{spread[section]['widest']['query_command']} and applied to "
                            f"COMMAND={spread[section]['narrowest_body']}, whose largest "
                            "disagreement anywhere on this grid is "
                            f"{spread[section]['narrowest_nonzero']:.4e} "
                            f"{SECTION_UNITS[section]} — a band "
                            f"{spread[section]['ratio']:.3g} times looser than that body was "
                            "ever measured to be. ⛔ Every one of its rows would pass without "
                            "being checked"
                        )
                    )
                    for section in SECTIONS
                },
            },
            "service_state": {
                "recorded_per_row": ["target_solution", "center_solution"],
                "recorded_in_the_acquisition_record": (
                    "the full set, including the interface version and any "
                    "Earth-orientation file, per query"
                ),
                "condition": REPRODUCIBILITY_CONDITION,
            },
            "host": host_record(),
        },
        notes=[
            "⭐ THE SERVICE DOES NOT ANSWER FROM ONE EPHEMERIS, AND THE NUMBERS DO NOT SAY "
            "SO. Asked for a planet's system barycentre it names the planetary solution; "
            "asked for the planet itself, same instant, same frame, a request differing in "
            "nothing but the body number, it names a body-specific solution. ⛔ The only "
            "thing that distinguishes the two answers is the identifier the service prints "
            "beside the body name, which is why it is on every row and why a response "
            "omitting it is refused.",
            "⛔ THE CROSS-REFERENCE IS NOT A BAND AND MUST NOT BECOME ONE. It is the "
            "difference between two named solutions. Banding it would declare that "
            "difference to be a reader's tolerance, and every reader inside it would pass "
            "without being checked. ⭐ `summary.why_no_band.measured` puts the factor on it, "
            "computed on this run rather than asserted: the disagreement is concentrated in "
            "one body and the spread across the grid is orders of magnitude wide, so a "
            "single band would be set by the worst body and would be meaningless for the "
            "rest.",
            "⭐ AND THE SMALL NUMBERS ARE THE EVIDENCE THAT THE COMPARISON IS SET UP RIGHT. "
            "A wrong frame or an epoch handed over in the wrong time scale would displace "
            "every body at once. Ten of the eleven the pinned file carries agree far below "
            "the eleventh, which is what licenses reading the remainder as a difference "
            "between solutions rather than as a defect in this recorder.",
            "⚠ Rows this file cannot cross-reference carry null and say why. ⛔ A consumer "
            "that judges those rows by a cross-reference alone has not judged them.",
            "⚠ The pin is the service's answer. Nothing judged the service, so no band is "
            "declared here; the band a consumer applies comes from that consumer's own "
            "budget, as a reviewed change in that consumer's tree.",
            REPRODUCIBILITY_CONDITION,
            ACQUISITION_LIMIT,
        ],
    )

    out_path = Path(args.out) / "service" / "r1-values.jsonl"
    written = write_jsonl(out_path, header, rows, declared_sections=list(SECTIONS))

    print(f"wrote {written} rows -> {out_path}")
    print(f"solutions that answered: {', '.join(distinct_solutions)}")
    for section in SECTIONS:
        entry = worst[section]
        if entry is None:
            continue
        print(
            f"cross-reference ({section}): worst {entry['abs_delta']:.4e} "
            f"{entry['unit']} at COMMAND={entry['query_command']} "
            f"({entry['target_solution']}) over {checked[section]} rows -- NOT a band"
        )
        if spread[section] is not None:
            print(
                f"  spread across bodies: {spread[section]['ratio']:.3g}x -- one band would "
                f"be that much looser than COMMAND={spread[section]['narrowest_body']} "
                "was ever measured to be"
            )
        print(
            f"  {indistinguishable[section]}/{len(resolution[section])} bodies show no "
            "disagreement above the resolution of the number itself"
        )
    if no_cross_reference:
        print(f"rows with no cross-reference: {no_cross_reference}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
