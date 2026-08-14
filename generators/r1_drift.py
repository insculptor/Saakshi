"""The drift job — watching the condition a service fixture's reproducibility rests on.

A fixture sampled from a *file* needs no such job: the file's digest is the whole condition
and a consumer checks it. A fixture sampled from a **service** regenerates byte-for-byte
only *while the recorded service state holds*, and a conditional guarantee with nothing
watching the condition is a guarantee nobody checks. This is what watches it.

⛔ **DETECT AND PROPOSE. IT NEVER GATES.** It fails nothing, refuses nothing, adopts no band
and edits no fixture. It re-asks the questions a fixture recorded, reports what came back
differently, and proposes what a human might do about it. ⚠ **It exits 0 on every outcome,
including every kind of drift it can detect** — and that is a design decision, not an
oversight:

* ⭐ A job that fails a build on drift is a job somebody switches off. It would fire on the
  day a public service updated a data file — an event nobody here controls, at a time nobody
  here chose — and the fixture it fired about would still be perfectly good evidence of what
  the service said when it was asked.
* ⛔ And drift is not a defect. A service that answers from a newer solution has not
  malfunctioned; the recorded rows have not become wrong. What has changed is that they are
  now a record of a *past* state, which is a thing to know and not a thing to fail.

⚠ **The reverse mistake is worth naming too.** Detect-only would be too weak: a report that
says "something moved" and stops leaves the reader to work out which of four quite different
things happened. So each finding carries the proposal that fits it, and ⛔ the proposals are
addressed to a human, never applied.

⭐ **The finding this job exists for is the one that is invisible in the numbers**: a
response whose values are unchanged and whose *solution identifier* has moved. The rows
still verify, and they are a different claim.

⛔ **Recorder, never explainer.** It compares two observations and says how they differ.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from saakshi.acquisition import AcquisitionError, USER_AGENT, retrieve  # noqa: E402
from saakshi.fixture import (  # noqa: E402
    Header,
    describe_reserved_names,
    redact_environment,
    write_jsonl,
)
from saakshi.provenance import generator_for, host_record, today  # noqa: E402
from saakshi.service import (  # noqa: E402
    ACQUISITION_LIMIT,
    DRIFT_OUTCOMES,
    DRIFT_PROPOSALS,
    ENDPOINT,
    ServiceFormatError,
    build_url,
    canonical_form,
    classify_drift,
    parse,
)

#: ⭐ The vocabulary and the classification live in `src/saakshi/service.py`, not here. Two
#: of them are decisions worth testing — the precedence between outcomes, and the fact that
#: no proposal ever proposes widening a band — and a decision that only exists inside a
#: script that needs the network to run is a decision nothing checks.
OUTCOMES = DRIFT_OUTCOMES
PROPOSALS = DRIFT_PROPOSALS


def _load(path: Path) -> tuple[dict, list[dict]]:
    """A fixture, as header and rows. ⚠ Read-only; this job writes to neither input."""
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines:
        raise SystemExit(f"{path}: empty")
    header = json.loads(lines[0])
    if header.get("record") != "header":
        raise SystemExit(f"{path}: line 1 is not a header")
    return header, [json.loads(line) for line in lines[1:] if line.strip()]


def _resolve_acquisition(values_header: dict, values_path: Path) -> tuple[dict, list[dict]]:
    """Follow the value fixture's pointer at its acquisition record, and check the digest.

    ⭐ The pointer is written relative to the fixture root precisely so it resolves after a
    copy into a consuming tree. Following it here is not incidental — it is the same
    resolution a consumer's loader performs, exercised on every drift run.
    """
    pointer = values_header.get("oracle", {}).get("acquisition_record") or {}
    relative = pointer.get("path")
    if not relative:
        raise SystemExit(
            f"{values_path}: the header names no acquisition record. ⛔ This job compares "
            "resource digests, and those live in that record."
        )
    # The fixture root is the directory the relative path is anchored at.
    root = values_path.resolve().parent
    for _ in Path(relative).parts[:-1]:
        root = root.parent
    record_path = root / relative
    if not record_path.is_file():
        raise SystemExit(f"{record_path}: the acquisition record the fixture points at is absent")

    digest = hashlib.sha256(record_path.read_bytes()).hexdigest()
    if digest != pointer.get("sha256"):
        raise SystemExit(
            f"{record_path}: sha256 {digest} != the {pointer.get('sha256')} the value "
            "fixture cites. ⛔ The two files are not from one emission, so a comparison "
            "against them would be against two different runs."
        )
    return _load(record_path)


def _recorded(acquisition_rows: list[dict]) -> dict[str, dict]:
    """`command -> {resource_sha256, service_state}`, as the fixture recorded them."""
    return {
        str(row["query_command"]): {
            "resource_sha256": row["resource_sha256"],
            "service_state": row.get("service_state", {}),
        }
        for row in acquisition_rows
        if row.get("finding") == "retrieval"
    }


def _query_for(command: str, request: dict) -> dict[str, str]:
    """Rebuild one recorded query. ⭐ From the fixture's own `request` block, never from a
    constant in this file — `request` means *sufficient to regenerate*, and a job that
    rebuilds the query from its own copy of the parameters is not testing that claim."""
    query = {entry["parameter"]: entry["value"] for entry in request["common_query"]}
    query["COMMAND"] = f"'{command}'"
    query["TLIST"] = "'" + ",".join(repr(epoch) for epoch in request["epochs"]["values"]) + "'"
    return query


def _values_by_key(value_rows: list[dict]) -> dict[tuple, dict]:
    return {
        (row["target_command"], row["section"], row["jd_tdb"]): row for row in value_rows
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", required=True, type=Path, help="an emitted r1-values.jsonl")
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--cache", default=Path("cache/drift"), type=Path)
    parser.add_argument("--allow-dirty", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()

    generator = generator_for(Path(__file__), allow_dirty=args.allow_dirty)
    print(describe_reserved_names())

    values_header, value_rows = _load(args.fixture)
    _acquisition_header, acquisition_rows = _resolve_acquisition(values_header, args.fixture)
    recorded = _recorded(acquisition_rows)
    by_key = _values_by_key(value_rows)
    request = values_header["request"]
    print(
        f"comparing against {args.fixture} "
        f"({len(value_rows)} rows, {len(recorded)} queries, "
        f"generated {values_header['generated']} at {values_header['generator']['commit'][:12]})"
    )

    rows: list[dict] = []
    tally: dict[str, int] = {}

    for target in request["targets"]:
        command = str(target["command"])
        baseline = recorded.get(command)
        if baseline is None:
            continue
        query = _query_for(command, request)

        outcome: str
        detail: dict[str, object] = {}
        try:
            retrieval = retrieve(
                build_url(query),
                cache=args.cache / f"r1-{command}.txt",
                canonical=canonical_form(query),
            )
            response = parse(retrieval.payload, query=query)
        except ServiceFormatError as exc:
            outcome = "classification_stale"
            detail = {"refusal": redact_environment(str(exc))}
        except AcquisitionError as exc:
            # ⚠ This one quotes a cache path, so it is the likeliest of the three to name
            #   the machine rather than the service.
            outcome = "not_observed"
            detail = {"refusal": redact_environment(str(exc))}
        else:
            state_now = dict(response.service_state)
            state_then = dict(baseline["service_state"])
            state_changes = {
                name: {"recorded": state_then.get(name), "now": state_now.get(name)}
                for name in sorted(set(state_then) | set(state_now))
                if state_then.get(name) != state_now.get(name)
            }

            value_changes: list[dict] = []
            for epoch_index, fields in enumerate(response.data_rows):
                jd_tdb = float(fields[0])
                for section, columns in (
                    ("position_au", (2, 3, 4)),
                    ("velocity_au_per_day", (5, 6, 7)),
                ):
                    row = by_key.get((command, section, jd_tdb))
                    if row is None:
                        continue
                    printed = [fields[column] for column in columns]
                    now = [float(text) for text in printed]
                    if now != [float(value) for value in row["value"]]:
                        value_changes.append(
                            {
                                "section": section,
                                "jd_tdb": jd_tdb,
                                "recorded": row["value_printed"],
                                "now": printed,
                                # ⚠ The largest component move, so a reader can tell a last-place
                                # difference from a different answer at a glance.
                                "max_abs_delta": max(
                                    abs(now[i] - float(row["value"][i])) for i in range(3)
                                ),
                            }
                        )

            digest_moved = retrieval.resource_sha256 != baseline["resource_sha256"]
            outcome = classify_drift(
                values_changed=len(value_changes),
                service_state_changed=len(state_changes),
                resource_digest_moved=digest_moved,
            )

            detail = {
                "resource_sha256_recorded": baseline["resource_sha256"],
                "resource_sha256_now": retrieval.resource_sha256,
                "resource_digest_moved": digest_moved,
                "service_state_changes": state_changes,
                "values_changed": len(value_changes),
                # ⚠ Bounded, and the bound is stated. A report that silently truncates
                #   reads as a complete one.
                "values_changed_sample": value_changes[:10],
                "values_changed_sample_bounded_at": 10,
            }

        tally[outcome] = tally.get(outcome, 0) + 1
        rows.append(
            {
                "finding": "query_compared",
                "query_command": command,
                "target_label": str(target["label"]),
                "outcome": outcome,
                "outcome_meaning": OUTCOMES[outcome],
                "proposal": PROPOSALS[outcome],
                **detail,
            }
        )
        print(f"  COMMAND={command:>4} -> {outcome}")

    rows.append(
        {
            "finding": "summary",
            "compared_against": {
                "fixture": str(args.fixture.name),
                "generated": values_header["generated"],
                "commit": values_header["generator"]["commit"],
            },
            "queries_compared": len(rows),
            "outcomes": tally,
            "proposals": sorted({PROPOSALS[outcome] for outcome in tally}),
            "evidence": (
                "⛔ This job gates nothing. It exited successfully whatever is above, it "
                "adopted no band, and it edited no fixture. Every proposal is addressed to a "
                "human"
            ),
        }
    )

    header = Header(
        fixture_kind="provenance_record",
        reference="instrument",
        generator=generator,
        generated=today(),
        title="Whether the service still answers as a recorded fixture says it did",
        oracle={
            "implementation": "python urllib.request over HTTPS",
            "python": host_record()["python"],
            "user_agent": USER_AGENT,
            "endpoint": ENDPOINT,
            "method": (
                "the queries a value fixture recorded, re-issued and compared against the "
                "rows and the resource digests that fixture emitted. ⭐ The queries are "
                "rebuilt from the fixture's own `request` block, so a run of this job is "
                "also a test of that block's claim to be sufficient to regenerate"
            ),
        },
        attests=(
            "whether a recorded service fixture's values, the service state it recorded, and "
            "the resource digests of the responses it was built from are what the service "
            "returns today — and, where they are not, which of them moved"
        ),
        authority={
            "held_by": "this instrument, as the party that re-issued the queries",
            "kind": "direct observation, compared against an earlier direct observation",
            "scope": (
                "⛔ DETECTION AND PROPOSAL ONLY. This record gates nothing, adopts no band, "
                "and licenses no change to any fixture. A finding here is a line for a human "
                "to read and act on. ⚠ It also cannot establish WHY anything moved: it "
                "observes that two answers to one question differ, and the service's reasons "
                "are not observable from outside. "
                + ACQUISITION_LIMIT
            ),
        },
        record_date=today(),
        row_schema={
            "finding": "query_compared | summary",
            "outcome": " | ".join(OUTCOMES),
            "outcome_meaning": "what that outcome means, in full",
            "proposal": "⛔ what a human might do. Nothing here was applied",
            "resource_digest_moved": (
                "whether the digest of the extracted resource differs from the recorded one"
            ),
            "service_state_changes": (
                "⭐ per named piece of service state, what was recorded and what answers now"
            ),
            "values_changed": "how many recorded values came back different",
            "values_changed_sample": "up to the stated bound of them, in full",
        },
        summary={
            "outcomes": tally,
            "outcome_vocabulary": OUTCOMES,
            "gating": (
                "⛔ NONE. This job exits successfully on every outcome it can reach, "
                "deliberately. A job that fails a build the day a public service updates a "
                "data file is a job somebody switches off — and the fixture it would have "
                "failed is still exactly good evidence of what the service said when it was "
                "asked"
            ),
            "host": host_record(),
        },
        notes=[
            "⛔ DETECT AND PROPOSE. Nothing here gates, and nothing here was applied.",
            "⭐ The finding this job exists for is the one the numbers cannot show: a "
            "response whose values are unchanged and whose solution identifier has moved. "
            "The rows still verify and they are a different claim.",
            "⚠ `not_observed` is its own outcome. A query that could not be issued is not a "
            "query that agreed, and collapsing the two would make an outage read as a pass.",
        ],
    )

    out_path = Path(args.out) / "service" / "r1-drift-report.jsonl"
    written = write_jsonl(out_path, header, rows)
    print(f"wrote {written} rows -> {out_path}")
    print(f"outcomes: {tally}")
    print("this job gates nothing; exiting 0 whatever the outcome above")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
