"""R1 — the drift control for the geocentric grid: whether the service still answers its queries as recorded.

The geocentric ICRF grid (`r1_geocentric_vectors.py`) regenerates byte for byte only while the service state it
recorded holds. This re-asks a sample of that grid's own recorded queries and says, per query, whether the
service answered as it did, and if not, what moved.

* ⛔ **DETECT AND PROPOSE. IT NEVER GATES.** It exits 0 on every outcome, including every kind of drift it can
  detect; it refuses nothing, adopts no band and edits no fixture. Each finding carries a proposal addressed to a
  human, from `src/saakshi/service.py`'s own vocabulary, ⛔ never applied. (The same decision, for the same
  reasons, as `r1_drift.py`'s.)
* ⭐ **The queries are the values file's own**, rebuilt from its `request.queries` block, never from a constant
  here — so every run also tests that block's claim to be sufficient to regenerate.
* ⭐ **A sample, stated.** By default the first chunk of every body under every correction, one request each;
  `--sample all` re-asks every query. The sample is written into the report.
* ⭐ **What is compared, per query**: the interface and the solutions named (these classify), the Earth-orientation
  file and coverage named (recorded, ⚠ and not classifying, because the values and the resource are compared
  directly beside them), the resource digest, every printed value at every instant, and the response's own output
  type, columns and paragraph stating its corrections.
* ⭐ **Each response is read through the grid generator's own reader** (its retrieval with back-off, its split),
  one request at a time, paced, into a directory that is discarded after the run.
* ⛔ **Recorder, never explainer.** It compares two observations and says how they differ.

Usage:
    python generators/r1_geocentric_drift.py --values out/service/r1-geocentric-vectors.jsonl --out out/
        [--sample first_chunk|all]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.dont_write_bytecode = True
for _path in (str(HERE.parent / "src"), str(HERE)):
    if _path not in sys.path:
        sys.path.insert(0, _path)

from saakshi.acquisition import USER_AGENT, AcquisitionError  # noqa: E402
from saakshi.fixture import Header, describe_reserved_names, redact_environment, write_jsonl  # noqa: E402
from saakshi.provenance import generator_for, host_record, today  # noqa: E402
from saakshi.service import (  # noqa: E402
    ACQUISITION_LIMIT,
    DRIFT_OUTCOMES,
    DRIFT_PROPOSALS,
    ENDPOINT,
    ServiceFormatError,
    classify_drift,
)

# ⭐ The grid's own reader, request shape and expectations, by import.
import r1_geocentric_vectors as grid  # noqa: E402

SCRIPT = "generators/r1_geocentric_drift.py"
REPORT_PATH = "service/r1-geocentric-vectors-drift.jsonl"

#: The state that classifies a query as moved: which interface answered, and which solutions.
CLASSIFYING_STATE: tuple[str, ...] = ("interface_source", "interface_version", "target_solution",
                                      "center_solution")
#: ⚠ State recorded and reported, but not classifying: a geocentric response names an Earth-orientation file that
#: the service replaces on its own schedule. Its change is listed on the row; the values and the resource digest,
#: compared directly, are what say whether the answer moved.
RECORDED_ONLY_STATE: tuple[str, ...] = ("earth_orientation_file", "earth_orientation_coverage")

SAMPLES: dict[str, str] = {
    "first_chunk": "the first chunk of every body under every correction: one request per body and correction",
    "all": "every query the values file recorded",
}


class Refusal(Exception):
    """An input that cannot be compared against. ⚠ Not a finding: drift is never a refusal."""


def load(path: Path) -> tuple[dict, list[dict]]:
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines:
        raise Refusal(f"{path}: empty")
    header = json.loads(lines[0])
    if header.get("record") != "header":
        raise Refusal(f"{path}: line 1 is not a header")
    return header, [json.loads(line) for line in lines[1:] if line.strip()]


def inputs(values_path: Path) -> tuple[dict, list[dict], dict, list[dict]]:
    """The values file and its acquisition record, ⛔ refused unless the record names this very values file."""
    values_header, values_rows = load(values_path)
    if values_header.get("generator", {}).get("script") != grid.SCRIPT:
        raise Refusal(f"{values_path}: not a file the geocentric grid generator wrote")
    root = values_path.resolve().parent
    for _ in Path(grid.VALUES_PATH).parts[:-1]:
        root = root.parent
    record_path = root / grid.ACQUISITION_PATH
    if not record_path.is_file():
        raise Refusal(f"{record_path}: the acquisition record beside the values file is absent")
    record_header, record_rows = load(record_path)
    digest = hashlib.sha256(values_path.read_bytes()).hexdigest()
    if record_header["oracle"]["values_file"]["sha256"] != digest:
        raise Refusal(f"{record_path}: names a values file of another digest; the two are not one emission")
    return values_header, values_rows, record_header, record_rows


def sample(values_header: dict, rule: str) -> list[dict]:
    queries = values_header["request"]["queries"]
    if rule == "all":
        return list(queries)
    if rule == "first_chunk":
        return [q for q in queries if q["chunk"] == 0]
    raise Refusal(f"sample {rule!r} is not one of {sorted(SAMPLES)}")


def compare(recorded: dict, response: "grid.Response", *, recorded_state: dict, recorded_values: dict,
            statements: dict, resource_sha256: str) -> dict:
    """One query's comparison. Returns the outcome and its detail."""
    state_now = dict(response.service_state)
    changes = {name: {"recorded": recorded_state.get(name), "now": state_now.get(name)}
               for name in sorted(set(recorded_state) | set(state_now))
               if recorded_state.get(name) != state_now.get(name)}
    classifying = {k: v for k, v in changes.items() if k in CLASSIFYING_STATE}
    recorded_only = {k: v for k, v in changes.items() if k not in CLASSIFYING_STATE}
    statement = statements[recorded["vec_corr"]]
    statement_changes = {
        name: {"recorded": then, "now": now}
        for name, then, now in (
            ("output_type", statement["output_type"], response.stated.get("output_type")),
            ("aberrations_and_corrections", statement["aberrations_and_corrections"],
             response.correction_paragraph),
            ("columns", list(grid.EXPECTED_COLUMNS), list(response.columns)),
        )
        if then != now
    }
    value_changes = []
    for fields in response.data_rows:
        row = recorded_values.get((recorded["target_command"], recorded["vec_corr"], float(fields[0])))
        if row is not None and list(fields[2:]) != row["value_printed"]:
            value_changes.append({"jd_tdb": float(fields[0]), "jd_tdb_bits": grid.bits(float(fields[0])),
                                  "recorded": row["value_printed"], "now": list(fields[2:])})
    digest_moved = resource_sha256 != recorded["resource_sha256"]
    if statement_changes:
        outcome = "classification_stale"
    else:
        outcome = classify_drift(values_changed=len(value_changes), service_state_changed=len(classifying),
                                 resource_digest_moved=digest_moved)
    return {
        "outcome": outcome,
        "resource_sha256_recorded": recorded["resource_sha256"],
        "resource_sha256_now": resource_sha256,
        "resource_digest_moved": digest_moved,
        "service_state_changes": classifying,
        "recorded_only_state_changes": recorded_only,
        "statement_changes": statement_changes,
        "instants_compared": len(response.data_rows),
        "values_changed": len(value_changes),
        "values_changed_sample": value_changes[:10],
        "values_changed_sample_bounded_at": 10,
    }


def main(argv: list[str] | None = None, *, sleep=None, fetch=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--values", required=True, type=Path, help="an emitted r1-geocentric-vectors.jsonl")
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--sample", default="first_chunk", choices=sorted(SAMPLES))
    args = parser.parse_args(argv)
    sleep = sleep or time.sleep

    generator = generator_for(HERE / Path(SCRIPT).name)
    print(describe_reserved_names())
    report_path = args.out / REPORT_PATH
    if report_path.exists():
        raise Refusal(f"{report_path} exists; a record is never overwritten")
    values_header, values_rows, record_header, record_rows = inputs(args.values)
    chosen = sample(values_header, args.sample)
    recorded_state = {row["request_id"]: row["service_state"] for row in record_rows if row["finding"] == "retrieval"}
    recorded_values = {(r["target_command"], r["vec_corr"], float(r["jd_tdb"])): r for r in values_rows}
    statements = {s["vec_corr"]: s for s in values_header["oracle"]["the_service_on_each_correction"]}
    print(f"re-asking {len(chosen)} of {len(values_header['request']['queries'])} recorded queries "
          f"({args.sample}), one at a time, as {USER_AGENT}")

    rows, tally = [], {}
    with tempfile.TemporaryDirectory(prefix="r1-geocentric-drift-") as scratch:
        for index, recorded in enumerate(chosen):
            if index:
                sleep(grid.REQUEST_INTERVAL_SECONDS)
            query = {entry["parameter"]: entry["value"] for entry in recorded["query"]}
            request = {"request_id": recorded["request_id"], "query": query}
            try:
                got = grid.read_live(request, Path(scratch) / recorded["request_id"], sleep=sleep, fetch=fetch)
                response = grid.split(got.payload, query=query)
            except ServiceFormatError as exc:
                detail = {"outcome": "classification_stale", "refusal": redact_environment(str(exc))}
            except AcquisitionError as exc:
                detail = {"outcome": "not_observed", "refusal": redact_environment(str(exc))}
            else:
                detail = compare(recorded, response, recorded_state=recorded_state[recorded["request_id"]],
                                 recorded_values=recorded_values, statements=statements,
                                 resource_sha256=got.resource_sha256)
            outcome = detail["outcome"]
            tally[outcome] = tally.get(outcome, 0) + 1
            rows.append({"finding": "query_compared", "request_id": recorded["request_id"],
                         "target_command": recorded["target_command"], "vec_corr": recorded["vec_corr"],
                         **detail, "outcome_meaning": DRIFT_OUTCOMES[outcome], "proposal": DRIFT_PROPOSALS[outcome]})
            print(f"  {recorded['request_id']}: {outcome}")

    compared_against = {"values_file": args.values.name,
                        "values_sha256": record_header["oracle"]["values_file"]["sha256"],
                        "generated": values_header["generated"], "commit": values_header["generator"]["commit"],
                        "acquired_on": values_header["oracle"]["acquired_on"]}
    rows.append({"finding": "summary", "compared_against": compared_against, "sample": args.sample,
                 "queries_compared": len(chosen), "outcomes": tally,
                 "proposals": sorted({DRIFT_PROPOSALS[o] for o in tally}),
                 "evidence": "⛔ This job gates nothing. It exits successfully whatever is above, adopted no band and "
                             "edited no fixture. Every proposal is addressed to a human."})
    header = Header(
        fixture_kind="provenance_record",
        reference="instrument",
        generator=generator,
        generated=today(),
        title="Whether the service still answers the geocentric grid's queries as that grid recorded",
        oracle={"implementation": "python urllib.request over HTTPS", "python": host_record()["python"],
                "user_agent": USER_AGENT, "endpoint": ENDPOINT, "run_on": today(),
                "compared_against": compared_against,
                "method": "a stated sample of the values file's own recorded queries, re-issued one at a time and "
                          "compared against the values, the service state and the resource digests that emission "
                          "recorded"},
        attests=("whether a recorded service fixture's values, the service state it recorded, its resource digests "
                 "and the service's own statement of each correction are what the service returns on this date for "
                 "the sampled queries, and where they are not, which of them moved"),
        authority={"held_by": "this instrument, as the party that re-issued the queries",
                   "kind": "direct observation, compared against an earlier direct observation",
                   "scope": ACQUISITION_LIMIT},
        record_date=today(),
        row_schema={"finding": "query_compared | summary",
                    "outcome": f"one of {sorted(DRIFT_OUTCOMES)}",
                    "service_state_changes": "interface or solution named differently: these classify",
                    "recorded_only_state_changes": "the Earth-orientation file or coverage named differently: "
                                                   "listed, not classifying",
                    "statement_changes": "the response's output type, columns or statement of its corrections, "
                                         "where they differ from the values file's; any classifies as stale",
                    "values_changed_sample": "the first ten instants whose printed values differ, recorded and now"},
        summary={"sample": {"rule": args.sample, "meaning": SAMPLES[args.sample]}, "outcomes": tally,
                 "host": host_record()},
        notes=["⛔ Detect and propose, never gate. A quiet report is the report this job expects to produce, and "
               "its silence is not evidence of freshness: its run date is.",
               "⚠ The copies read in this run were kept only for the run and discarded; the digests above are "
               "what was compared."],
    )
    write_jsonl(report_path, header, rows)
    print(f"outcomes {tally} -> {report_path}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (Refusal, grid.Refusal) as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        raise SystemExit(2)
