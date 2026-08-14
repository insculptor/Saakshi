"""What it costs to cross from the interpreter into the ephemeris binding, as ratios.

⛔ **This file answers a question that had been asked in a form no measurement can answer.**
"What does one round trip through the binding cost?" has no single answer: an empty crossing,
a crossing carrying four arguments, and a crossing that computes a position differ by more
than two orders of magnitude, and the phrase covers all three. So the ladder below is
published rung by rung, each rung stating its arity, the form of its call site, and what the
callee does.

⭐ **Ratios, not nanoseconds.** A duration measured here is a fact about this workstation on
this date, and it moves with the way the harness wrote its own loop. What survives both is
the relationship between two rungs measured identically in one interleaved process. The
nanoseconds are recorded beside every ratio with the standing this repository gives its host
record: environment context, never a published figure.

⛔ **AND THIS FILE DOES NOT REGENERATE BYTE FOR BYTE.** Every other artifact this repository
writes does. This one cannot, and that is declared in the file itself rather than left for a
consumer to discover from a diff — see the `reproducibility` row.

⛔ **Recorder, never explainer.** Nothing here describes how the library computes anything.
Each rung is a callable, an argument tuple and an arity.
"""

from __future__ import annotations

import argparse
import platform
import sys
from importlib.metadata import version as _distribution_version
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import swisseph as swe  # noqa: E402

from saakshi.fixture import Header, describe_reserved_names, write_jsonl  # noqa: E402
from saakshi.provenance import generator_for, host_record, today  # noqa: E402
from saakshi.swiss import MODES, assert_reported, source_name  # noqa: E402
from saakshi.timing import (  # noqa: E402
    ANCHOR,
    ARGUMENTS,
    CALL_FORM_NOTES,
    CALL_FORMS,
    LOOP_SKELETON,
    MECHANISM_CONTROL_RUNGS,
    SEQUENCE_LOOP,
    SEQUENCE_VARIANT_NOTES,
    SEQUENCE_VARIANTS,
    SKELETON,
    SPAN_FLOOR_IN_CLOCK_STEPS,
    Operation,
    SequenceRung,
    call_site,
    clock_record,
    ordering_record,
    ratio,
    reproduction_record,
    refuse_unless_all_pass,
    run_interleaved,
    standard_controls,
    standard_operations,
    standard_sequence_rungs,
    summarise,
)

BINDING = "pyswisseph"
BINDING_VERSION = _distribution_version(BINDING)

#: How many times the whole ladder is traversed. ⚠ Every rung is measured once per round, so
#: a ratio is computed from two readings taken milliseconds apart rather than from two
#: summaries taken at opposite ends of the run.
ROUNDS = 11

#: Discarded. The interpreter specialises a call site after it has run a few times.
WARMUP_ROUNDS = 1

#: The instant every rung that takes one is asked about, and the site the house rung uses.
#: ⚠ Constants, so the request is part of the declared method rather than of the machine.
INSTANT_JD_UT = ARGUMENTS[3][0]
SITE_LATITUDE = 26.4
SITE_LONGITUDE = 80.3
HOUSE_METHOD = b"P"

#: ⛔ Requesting the analytical ephemeris is not the same as being answered by it, and this
#: probe times a computation rather than reading a value out of it — so an unnoticed
#: substitution would mean the ladder's top rung had timed a different computation from the
#: one it names.
ANALYTICAL = MODES["moshier"]
ANALYTICAL_FLAGS = ANALYTICAL.flag | swe.FLG_SPEED

#: A rung is called repetition-sensitive when asking distinct questions cost at least this
#: much more than asking one question repeatedly, **in every round**.
#:
#: ⛔ The verdict is bounded in one direction only. `false` means *not observable by this
#: harness at this repetition count*, never *the callee holds nothing between calls*.
SENSITIVITY_FLOOR = 1.25


# --------------------------------------------------------------------------------------
# The ladder
# --------------------------------------------------------------------------------------


def fixed_rungs() -> list[Operation]:
    """The rungs measured with one argument tuple, under all three call-site forms.

    ⚠ **Only callees whose cost cannot depend on which request is asked belong here**, and
    that is measured rather than assumed: every binding rung in this list also appears in
    the run-of-requests half, where the assumption is checked. ⛔ The two rungs that do real
    astronomical work appear **only** in that half, because for those the question "does
    repeating one request change what it costs" has been answered, and one of the two
    answers is yes.
    """
    return standard_operations() + [
        Operation(
            id="binding_arity_0",
            callee_kind="binding",
            callee="the ephemeris binding",
            does="returns a scalar the library is holding; takes no arguments",
            fn=swe.get_tid_acc,
            args=ARGUMENTS[0],
            repetitions=300_000,
            arity=0,
        ),
        Operation(
            id="binding_arity_1",
            callee_kind="binding",
            callee="the ephemeris binding",
            does="reduces one number into a stated range; one argument",
            fn=swe.degnorm,
            args=ARGUMENTS[1],
            repetitions=300_000,
            arity=1,
            mirror_of="binding_arity_0",
        ),
        Operation(
            id="binding_arity_4",
            callee_kind="binding",
            callee="the ephemeris binding",
            does="converts a calendar date to a day number; four arguments",
            fn=swe.julday,
            args=ARGUMENTS[4],
            repetitions=300_000,
            arity=4,
            mirror_of="binding_arity_0",
        ),
    ]


def sequence_rungs() -> list[SequenceRung]:
    """The rungs measured over a run of requests, each in both variants."""
    return standard_sequence_rungs() + [
        SequenceRung(
            id="binding_arity_1",
            callee_kind="binding",
            callee="the ephemeris binding",
            does="reduces one number into a stated range; one argument",
            fn=swe.degnorm,
            arity=1,
            repetitions=50_000,
            argument_at=lambda i: (ARGUMENTS[1][0] + i * 1e-3,),
            mirror_of="python_arity_1",
        ),
        SequenceRung(
            id="binding_arity_4",
            callee_kind="binding",
            callee="the ephemeris binding",
            does="converts a calendar date to a day number; four arguments",
            fn=swe.julday,
            arity=4,
            repetitions=50_000,
            argument_at=lambda i: (2000, 1, 1, 12.0 + i * 1e-3),
            mirror_of="python_arity_4",
        ),
        SequenceRung(
            id="binding_one_body_position",
            callee_kind="binding",
            callee="the ephemeris binding",
            does=(
                "one body's position and speed at one instant, from the analytical "
                "ephemeris; three arguments"
            ),
            fn=swe.calc_ut,
            arity=3,
            repetitions=15_000,
            argument_at=lambda i: (INSTANT_JD_UT + i * 1e-3, 0, ANALYTICAL_FLAGS),
            mirror_of="python_arity_3",
        ),
        SequenceRung(
            id="binding_house_cusps",
            callee_kind="binding",
            callee="the ephemeris binding",
            does="a full set of house cusps for one instant and one site; four arguments",
            fn=swe.houses_ex,
            arity=4,
            repetitions=6_000,
            argument_at=lambda i: (
                INSTANT_JD_UT + i * 1e-3,
                SITE_LATITUDE,
                SITE_LONGITUDE,
                HOUSE_METHOD,
            ),
            mirror_of="python_arity_4",
        ),
    ]


# --------------------------------------------------------------------------------------
# Which ephemeris answered — asserted before anything is timed
# --------------------------------------------------------------------------------------


def ephemeris_assertion() -> dict[str, Any]:
    """Establish that no data file can answer in this process, and that none did.

    ⭐ **Two statements, and the second is the one that needs measuring.** That the analytical
    source answered the call this probe times is read off the entry point's own returned
    flag. That no *other* source was available to answer the entry points which report
    nothing is established by requesting the data-file source and observing what came back:
    where a data file is unavailable the library substitutes silently, so the substitution is
    the evidence.
    """
    _, returned = swe.calc_ut(INSTANT_JD_UT, 0, ANALYTICAL_FLAGS)
    reported = assert_reported(ANALYTICAL, returned, where="the position rung")
    _, data_file_returned = swe.calc_ut(
        INSTANT_JD_UT, 0, swe.FLG_SWIEPH | swe.FLG_SPEED
    )
    answered_a_data_file_request = source_name(data_file_returned)
    if answered_a_data_file_request == "swiss_file":
        raise RuntimeError(
            "a data-file request was answered by the data files, so this process has an "
            "ephemeris directory available. The rungs below would then time a different "
            "computation from the one they name, and no path may be recorded to say which"
        )
    return {
        "position_rung": reported,
        "a_data_file_request_was_answered_by": answered_a_data_file_request,
        "meaning": (
            "no ephemeris data-file directory was set in this process, so no data file was "
            "available to answer any entry point — including the two that report no source "
            "at all. The path itself is deliberately not recorded anywhere in this file"
        ),
    }


# --------------------------------------------------------------------------------------
# Rows
# --------------------------------------------------------------------------------------

_LOOP_LIMIT = (
    "the figure includes the loop the call sits in. That loop is measured as its own rung "
    "and is common to both terms of every ratio here, so it biases each of them toward one"
)


def _mirror_ids(ops: list[Operation]) -> dict[tuple[str, int], str]:
    return {("pure_python", op.arity): op.id for op in ops if op.callee_kind == "pure_python"
            and op.id in (ANCHOR, "python_arity_1", "python_arity_3", "python_arity_4")}


def ladder_rows(ops: list[Operation], readings: dict[tuple[str, str], Any]) -> list[dict[str, Any]]:
    mirrors = _mirror_ids(ops)
    arity_zero = {
        op.callee_kind: op.id
        for op in ops
        if op.arity == 0 and op.id in (ANCHOR, "stdlib_c_arity_0", "binding_arity_0")
    }
    rows: list[dict[str, Any]] = []
    for op in ops:
        for form in CALL_FORMS:
            reading = readings[(op.id, form)]
            _, line = call_site(op, form)
            row: dict[str, Any] = {
                "finding": "ladder",
                "rung": op.id,
                "callee_kind": op.callee_kind,
                "callee": op.callee,
                "does": op.does,
                "arity": op.arity,
                "arguments_kind": list(op.arguments_kind),
                "call_site_form": form,
                "call_site": line,
                "call_site_form_note": CALL_FORM_NOTES[form],
                "repetitions_per_round": op.repetitions,
                "rounds": reading.rounds,
                "nanoseconds": reading.as_context(),
                "limit": _LOOP_LIMIT,
            }
            if op.id != ANCHOR:
                row["ratio_to_anchor"] = ratio(
                    readings, numerator=op.id, denominator=ANCHOR, form=form
                ).as_json()
            # ⚠ Suppressed where the mirror IS the anchor. The two fields would carry the
            #   same division under two names, which reads as two measurements.
            mirror = mirrors.get(("pure_python", op.arity))
            if (
                mirror is not None
                and mirror != ANCHOR
                and op.callee_kind in ("stdlib_c", "binding")
            ):
                row["ratio_to_same_arity_pure_python"] = ratio(
                    readings, numerator=op.id, denominator=mirror, form=form
                ).as_json()
            base = arity_zero.get(op.callee_kind)
            if base is not None and op.arity not in (None, 0):
                row["ratio_to_arity_zero_of_the_same_callee_kind"] = ratio(
                    readings, numerator=op.id, denominator=base, form=form
                ).as_json()
            rows.append(row)
    return rows


def call_site_form_rows(readings: dict[tuple[str, str], Any]) -> list[dict[str, Any]]:
    """What changing only the call site does to the anchor — the method's own footprint."""
    reference_form = CALL_FORMS[0]
    rows = []
    for form in CALL_FORMS:
        row: dict[str, Any] = {
            "finding": "call_site_form",
            "call_site_form": form,
            "what_it_is": CALL_FORM_NOTES[form],
            "anchor_nanoseconds": readings[(ANCHOR, form)].as_context(),
        }
        if form != reference_form:
            row["anchor_ratio_to_the_first_form"] = ratio(
                readings,
                numerator=ANCHOR,
                denominator=ANCHOR,
                form=form,
                denominator_form=reference_form,
            ).as_json()
        row["meaning"] = (
            "one callable, one set of argument values, three ways of writing the call. The "
            "absolute figure moves between them, which is why no absolute figure is "
            "published here and why a ratio is only ever taken between two rungs sharing a "
            "form"
        )
        rows.append(row)
    return rows


def call_site_sensitivity_rows(
    ops: list[Operation], readings: dict[tuple[str, str], Any]
) -> list[dict[str, Any]]:
    """How much of a rung's ratio is the rung, and how much is how the call was written."""
    rows = []
    for op in ops:
        if op.id == ANCHOR:
            continue
        by_form = {
            form: ratio(readings, numerator=op.id, denominator=ANCHOR, form=form).median
            for form in CALL_FORMS
        }
        widest, narrowest = max(by_form.values()), min(by_form.values())
        rows.append(
            {
                "finding": "call_site_sensitivity",
                "rung": op.id,
                "callee_kind": op.callee_kind,
                "arity": op.arity,
                "ratio_to_anchor_by_form": by_form,
                "widest_minus_narrowest": widest - narrowest,
                "as_a_fraction_of_the_narrowest": (
                    (widest - narrowest) / narrowest if narrowest else None
                ),
                "meaning": (
                    "the same rung against the same anchor, measured three ways. Where this "
                    "spread is small the rung's ratio is a property of the rung; where it is "
                    "large the way the call was written is part of the number, and a figure "
                    "quoted without it is under-specified"
                ),
            }
        )
    return rows


def repeated_call_rows(
    rungs: list[SequenceRung], readings: dict[tuple[str, str], Any]
) -> list[dict[str, Any]]:
    rows = []
    for rung in rungs:
        sensitivity = ratio(
            readings,
            numerator=rung.id,
            denominator=rung.id,
            form="distinct_requests",
            denominator_form="one_request_repeated",
        )
        row: dict[str, Any] = {
            "finding": "repeated_call",
            "rung": rung.id,
            "callee_kind": rung.callee_kind,
            "callee": rung.callee,
            "does": rung.does,
            "arity": rung.arity,
            "arguments_kind": list(rung.arguments_kind),
            "call_site_form": "over a pre-built run of argument tuples",
            "call_site": "_fn(*_args)",
            "both_variants_share": (
                "one compiled loop and one run length; only what the run holds differs"
            ),
            "repetitions_per_round": rung.repetitions,
            "rounds": len(sensitivity.per_round),
            "ratio_distinct_requests_to_one_request_repeated": sensitivity.as_json(),
            "repetition_sensitive": all(
                value >= SENSITIVITY_FLOOR for value in sensitivity.per_round
            ),
            "sensitivity_floor": SENSITIVITY_FLOOR,
            "verdict_limit": (
                "a negative verdict means not observable by this harness at this run length, "
                "never that the callee keeps nothing between calls"
            ),
            "nanoseconds": {
                variant: readings[(rung.id, variant)].as_context()
                for variant in SEQUENCE_VARIANTS
            },
        }
        if rung.mirror_of:
            row["ratio_to_same_arity_pure_python"] = {
                variant: ratio(
                    readings,
                    numerator=rung.id,
                    denominator=rung.mirror_of,
                    form=variant,
                ).as_json()
                for variant in SEQUENCE_VARIANTS
            }
        rows.append(row)
    return rows


def mechanism_bridge_rows(readings: dict[tuple[str, str], Any]) -> list[dict[str, Any]]:
    """The same callee measured by both loops, so the two halves sit on one ladder."""
    rows = []
    for rung in MECHANISM_CONTROL_RUNGS:
        rows.append(
            {
                "finding": "mechanism_bridge",
                "rung": rung,
                "ratio_run_of_requests_loop_to_fixed_argument_loop": ratio(
                    readings,
                    numerator=rung,
                    denominator=rung,
                    form="one_request_repeated",
                    denominator_form="unpacked",
                ).as_json(),
                "meaning": (
                    "one callable and one arity, measured by both of this file's loops in "
                    "the same rounds. Where this is one, a rung measured by one loop may be "
                    "read against a rung measured by the other; where it is not, the two "
                    "halves of the ladder are two ladders"
                ),
            }
        )
    return rows


def published_ratio_keys(
    ops: list[Operation], rungs: list[SequenceRung]
) -> list[tuple[str, str, str, str | None]]:
    """Every ratio this file publishes, enumerated once.

    ⛔ **Kept in step with the row builders by counting, not by care.** The reproduction check
    is only as wide as this list, so a ratio the rows publish and this list forgets would be
    a figure nobody re-measured — reported inside a file whose headline claim is about what
    reproduces. `main` counts the ratio objects in the built rows against this list and
    refuses on a mismatch.
    """
    mirrors = _mirror_ids(ops)
    arity_zero = {
        op.callee_kind: op.id
        for op in ops
        if op.arity == 0 and op.id in (ANCHOR, "stdlib_c_arity_0", "binding_arity_0")
    }
    keys: list[tuple[str, str, str, str | None]] = []
    for op in ops:
        for form in CALL_FORMS:
            if op.id != ANCHOR:
                keys.append((op.id, ANCHOR, form, None))
            mirror = mirrors.get(("pure_python", op.arity))
            if (
                mirror is not None
                and mirror != ANCHOR
                and op.callee_kind in ("stdlib_c", "binding")
            ):
                keys.append((op.id, mirror, form, None))
            base = arity_zero.get(op.callee_kind)
            if base is not None and op.arity not in (None, 0):
                keys.append((op.id, base, form, None))
    for form in CALL_FORMS[1:]:
        keys.append((ANCHOR, ANCHOR, form, CALL_FORMS[0]))
    for rung in rungs:
        keys.append((rung.id, rung.id, "distinct_requests", "one_request_repeated"))
        if rung.mirror_of:
            for variant in SEQUENCE_VARIANTS:
                keys.append((rung.id, rung.mirror_of, variant, None))
    for rung in MECHANISM_CONTROL_RUNGS:
        keys.append((rung, rung, "one_request_repeated", "unpacked"))
    return keys


def count_published_ratios(node: Any) -> int:
    """How many ratio objects the built rows actually carry."""
    if isinstance(node, dict):
        if {"against", "median", "spread_fraction_of_median"} <= set(node):
            return 1
        return sum(count_published_ratios(value) for value in node.values())
    if isinstance(node, list):
        return sum(count_published_ratios(item) for item in node)
    return 0


def reproducibility_row(readings: dict[tuple[str, str], Any]) -> dict[str, Any]:
    return {
        "finding": "reproducibility",
        "regenerates_byte_for_byte": False,
        "why": (
            "the subject is a duration. A duration is not a property of the callee alone: it "
            "moves with the machine, with what else the machine is doing, and with the way "
            "this harness wrote its own loop. Every other artifact this repository writes "
            "regenerates byte for byte, and this one is declared as the exception rather "
            "than left to be discovered from a diff"
        ),
        "what_a_re_run_should_reproduce": [
            "each ratio, within the spread stated on its own row — checked, see the "
            "`reproduction` row",
            "every verdict: the controls, and each rung's repetition sensitivity — checked",
            "the ordering of the ladder, for every pair separated by at least the figure "
            "the `reproduction` row measured for that form — ⛔ NOT for every pair the "
            "`ordering` rows report as having held, and ⛔ not at the declared margin either",
        ],
        "what_a_re_run_will_not_reproduce": [
            "any figure in nanoseconds, including the anchor's",
            "the exact digits of any ratio",
            "the spreads themselves, which are a property of what else the machine was doing",
            "⛔ the ordering of any pair closer together than the separation the "
            "`reproduction` row measured — AND THAT IS WIDER THAN IT SOUNDS. Two claims were "
            "tried here and a second traversal disposed of both: the pairs that held in "
            "every round, and then the pairs separated by the declared margin. The claim is "
            "the measured separation, and it is a measurement rather than a guarantee",
        ],
        "how_to_compare_two_runs": (
            "for each ratio, check that the other run's median falls inside this file's "
            "per-round interval for it; then compare the orderings of the pairs that clear "
            "the measured separation, and the verdicts. ⛔ A byte comparison of this file "
            "reports a difference every time and means nothing by it"
        ),
        "how_to_use_a_ratio_on_another_machine": (
            "measure the anchor there — a Python function that takes no arguments and "
            "returns immediately, called in a loop — and multiply. A ratio published here "
            "with an anchor measured there is the only form of this measurement that "
            "transfers"
        ),
    }


# --------------------------------------------------------------------------------------


def build_header(
    *,
    script: Path,
    ops: list[Operation],
    rungs: list[SequenceRung],
    assertion: dict[str, Any],
    clock: dict[str, Any],
    rounds: int,
    span_floor: int,
    summary: dict[str, Any],
) -> Header:
    return Header(
        fixture_kind="provenance_record",
        reference="instrument",
        generator=generator_for(script),
        generated=today(),
        title=(
            "What crossing into the ephemeris binding costs, as ratios between operations "
            "measured identically in one process"
        ),
        oracle={
            "instrument": (
                "a timing harness in this repository; the ladder, the controls and the "
                "loops are at src/saakshi/timing.py"
            ),
            "interpreter": {
                "implementation": sys.implementation.name,
                "version": platform.python_version(),
                "build": list(platform.python_build()),
                "compiler": platform.python_compiler(),
            },
            "called_via": {"binding": BINDING, "version": BINDING_VERSION},
            "library_version": swe.version,
            "ephemeris_source": assertion,
            "host": host_record(),
            "deliberately_not_recorded": (
                "no filesystem path of any kind: not the interpreter's, not this "
                "repository's, not an ephemeris directory's. A path describes the machine "
                "that ran the recorder rather than the subject, and the writer refuses one "
                "in any value"
            ),
            "licence": (
                "the library is AGPL-3.0; it is called here, never redistributed by this "
                "repository"
            ),
        },
        attests=(
            "what this instrument observed, on this machine and on this date, about the "
            "relative cost of calling the ephemeris binding: that an empty crossing costs "
            "what the interpreter's own call protocol costs, that what is attributable to "
            "the binding is the marshalling of arguments and it grows with their number, "
            "that a call which does astronomical work is larger than either by orders of "
            "magnitude, and that for one such call the cost measured by repeating a single "
            "request is not the cost of asking a different question each time"
        ),
        authority={
            "held_by": "no one; this record has no authority and confers none",
            "kind": (
                "direct observation by a named harness, under a declared method, on one "
                "machine on one date"
            ),
            "scope": (
                "⛔ these are not published performance figures and no consumer may adopt a "
                "number from this file as a budget, a threshold or a guarantee. What the "
                "file supports is a comparison: which of two operations is larger, and by "
                "roughly what factor. ⚠ One interpreter, one binding, one build of the "
                "library, one machine, one date"
            ),
        },
        record_date=today(),
        request={
            "rounds": rounds,
            "traversals": 2,
            "traversals_note": (
                "the whole ladder is measured twice. The first traversal is what the rows "
                "report; the second exists only to measure what the first reproduces, and "
                "is reported in the `reproduction` row"
            ),
            "warmup_rounds_discarded": WARMUP_ROUNDS,
            "clock": clock["clock"],
            "anchor": ANCHOR,
            "anchor_is": (
                "a Python function taking no arguments and returning immediately, measured "
                "in the same round and the same call-site form as whatever is divided by it"
            ),
            "call_site_forms": list(CALL_FORMS),
            "loop_with_a_fixed_argument_tuple": LOOP_SKELETON,
            "loop_over_a_run_of_requests": SEQUENCE_LOOP,
            "run_of_requests_variants": dict(SEQUENCE_VARIANT_NOTES),
            "loop_measured_as_a_rung": SKELETON,
            "minimum_elapsed_span_nanoseconds": span_floor,
            "minimum_elapsed_span_is": (
                f"{SPAN_FLOOR_IN_CLOCK_STEPS} clock steps. A batch elapsing less than this "
                "is refused rather than recorded: it would be quantised by the clock rather "
                "than measured by it, and a batch under one step reads zero, which is "
                "indistinguishable afterwards from a call that costs nothing"
            ),
            "interleaving": (
                "every rung, in every form, is measured once per round, in a fixed order, "
                "in one process. A ratio is computed inside a round and then summarised "
                "across rounds — never between two summaries"
            ),
            "repetitions_per_round": {
                **{op.id: op.repetitions for op in ops},
                **{f"{r.id}_over_a_run": r.repetitions for r in rungs},
            },
            "instant_jd_ut": INSTANT_JD_UT,
            "site_latitude_degrees": SITE_LATITUDE,
            "site_longitude_degrees": SITE_LONGITUDE,
            "house_method_letter": HOUSE_METHOD.decode("ascii"),
        },
        row_schema={
            "clock": "what the clock says about itself, and what it was seen to do",
            "call_site_form": "the anchor under each of the three ways of writing a call",
            "ladder": "one rung, one call-site form: its ratios, and its nanoseconds as context",
            "call_site_sensitivity": "how much of a rung's ratio is how the call was written",
            "repeated_call": (
                "one rung measured over one request repeated and over distinct requests"
            ),
            "mechanism_bridge": "the same callee measured by both loops, in the same rounds",
            "ordering": "which pairs of rungs held their order in every round",
            "control": "a check on the harness, with what it measured and whether it held",
            "reproduction": "the second traversal, compared against the first",
            "reproducibility": "⛔ what a re-run will and will not reproduce",
        },
        summary=summary,
        notes=[
            "⛔⛔ THIS FILE DOES NOT REGENERATE BYTE FOR BYTE, AND IT IS THE ONLY ONE THIS "
            "REPOSITORY WRITES THAT DOES NOT. Its subject is a duration, so a second run "
            "moves every figure in it. The `reproducibility` row states what a re-run should "
            "reproduce instead, and how to compare two runs without comparing bytes.",
            "⛔ RATIOS ARE THE PUBLISHED QUANTITY. Every figure in nanoseconds in this file "
            "sits inside a `nanoseconds` object that states its own standing: environment "
            "context, the same standing as the host record. A number of nanoseconds is the "
            "wrong shape for a claim about a binding, in the same way a band expressed in "
            "an absolute distance was the wrong shape for a claim about a state vector.",
            "⛔ NO INDIVIDUAL CALL WAS TIMED, AND NONE COULD BE. The finest clock this "
            "platform offers advances in steps of about a hundred nanoseconds and the calls "
            "of interest cost a few tens. Every figure is an elapsed span divided by a "
            "declared repetition count, so it is a mean, and the count is on every row.",
            "⭐ THE CALL-SITE FORM IS PART OF THE NUMBER. Handing a callee a pre-built "
            "argument tuple is not the same act as compiling the arguments into the call "
            "site, and the difference was measured to be small for a Python callee and "
            "large for this binding. So each rung is measured all three ways and the form "
            "is stated on every row. ⚠ A figure quoted without its form is under-specified, "
            "and this is the general case of a defect this repository has already paid for: "
            "a recorder that transforms a value before handing it to the thing being "
            "measured has made the transformation part of the measurement.",
            "⛔ A REPEATED CALL IS NOT A REPEATED COMPUTATION. A timing loop asks one "
            "question many times; a callee may answer the second asking more cheaply. Every "
            "rung whose cost could depend on which question is asked is therefore measured "
            "twice — over one request repeated, and over a run of distinct requests — and "
            "both figures are published. ⚠ Of the two rungs here that do real astronomical "
            "work, one is strongly sensitive and the other is not, so measuring either "
            "alone would have licensed a wrong general conclusion in one direction or the "
            "other.",
            "⚠ A NEGATIVE SENSITIVITY VERDICT IS BOUNDED. It says the difference was not "
            "observable by this harness at this run length. It does not say the callee "
            "keeps nothing between calls.",
            "⛔ NOTHING HERE MAY BE ADOPTED AS A BUDGET. The file records what one "
            "instrument saw once. To use a ratio on another machine, measure the anchor "
            "there and multiply; a ratio published here with an anchor measured there is "
            "the only form of this measurement that transfers.",
        ],
    )


def build_summary(
    ops: list[Operation], rungs: list[SequenceRung], readings: dict[tuple[str, str], Any]
) -> dict[str, Any]:
    def median(numerator: str, denominator: str, form: str, denominator_form: str | None = None) -> float:
        return ratio(
            readings,
            numerator=numerator,
            denominator=denominator,
            form=form,
            denominator_form=denominator_form,
        ).median

    return {
        "the_empty_crossing_is_not_the_bindings_cost": {
            "ratio_binding_arity_0_to_the_anchor": {
                form: median("binding_arity_0", ANCHOR, form) for form in CALL_FORMS
            },
            "ratio_a_standard_library_c_call_to_the_anchor": {
                form: median("stdlib_c_arity_0", ANCHOR, form) for form in CALL_FORMS
            },
            "meaning": (
                "⭐ a crossing carrying nothing costs about what a Python function call "
                "costs. So the empty round trip is the interpreter's call protocol, and a "
                "figure reported as 'the cost of the binding' that is really this one has "
                "attributed the interpreter's cost to the binding"
            ),
        },
        "what_is_attributable_is_marshalling_and_it_grows_with_arity": {
            "ratio_to_the_same_arity_pure_python_callee": {
                rung: {form: median(rung, mirror, form) for form in CALL_FORMS}
                for rung, mirror in (
                    ("binding_arity_1", "python_arity_1"),
                    ("binding_arity_4", "python_arity_4"),
                )
            },
            "ratio_within_the_binding_to_its_own_arity_zero_rung": {
                rung: {form: median(rung, "binding_arity_0", form) for form in CALL_FORMS}
                for rung in ("binding_arity_1", "binding_arity_4")
            },
            "the_same_within_pure_python": {
                rung: {form: median(rung, ANCHOR, form) for form in CALL_FORMS}
                for rung in ("python_arity_1", "python_arity_4")
            },
        },
        "a_call_that_does_work_dwarfs_the_crossing": {
            "ratio_to_the_same_arity_pure_python_callee_over_distinct_requests": {
                "binding_one_body_position": median(
                    "binding_one_body_position", "python_arity_3", "distinct_requests"
                ),
                "binding_house_cusps": median(
                    "binding_house_cusps", "python_arity_4", "distinct_requests"
                ),
            }
        },
        "a_repeated_call_is_not_a_repeated_computation": {
            "ratio_distinct_requests_to_one_request_repeated": {
                rung.id: median(
                    rung.id, rung.id, "distinct_requests", "one_request_repeated"
                )
                for rung in rungs
            },
            "meaning": (
                "⭐ two rungs here do real astronomical work. One of them answers a repeated "
                "request far more cheaply than a new one and the other does not, so a "
                "harness that only ever repeats one request would have reported the first "
                "as the smaller of the two by an order of magnitude it does not have"
            ),
        },
        "reproducibility": (
            "⛔ this file does not regenerate byte for byte. See the reproducibility row"
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument(
        "--rounds",
        type=int,
        default=ROUNDS,
        help="traversals of the whole ladder; the default is what the artifact declares",
    )
    args = parser.parse_args()

    script = Path(__file__)
    generator_for(script)  # ⛔ refuse a dirty tree before anything is measured

    print(describe_reserved_names())

    assertion = ephemeris_assertion()
    print(
        "ephemeris source asserted: the position rung was answered by "
        f"{assertion['position_rung']['answered']}; a data-file request was answered by "
        f"{assertion['a_data_file_request_was_answered_by']}"
    )

    ops = fixed_rungs()
    rungs = sequence_rungs()
    clock = clock_record()
    print(
        f"clock {clock['clock']}: measured step {clock['measured_step_nanoseconds']} ns - "
        "coarser than every quantity below, so no individual call is timed"
    )
    print(f"measuring {len(ops)} rung(s) x {len(CALL_FORMS)} call-site form(s) and "
          f"{len(rungs)} rung(s) x {len(SEQUENCE_VARIANTS)} request run(s), "
          f"{args.rounds} round(s)")

    span_floor = SPAN_FLOOR_IN_CLOCK_STEPS * clock["measured_step_nanoseconds"]

    def traverse() -> dict[tuple[str, str], Any]:
        return summarise(
            run_interleaved(
                ops,
                sequence_rungs=rungs,
                rounds=args.rounds,
                warmup_rounds=WARMUP_ROUNDS,
                minimum_span_nanoseconds=span_floor,
            )
        )

    readings = traverse()
    controls = standard_controls(readings, ops, sequence_readings=readings)
    for control in controls:
        print(f"control {control.id}: {'held' if control.passed else 'FAILED'}")
    refuse_unless_all_pass(controls)  # ⛔ nothing is written beside a control that failed

    # ⭐ The second traversal is not a repeat for confidence. This file's headline claim is
    #    about what survives a re-run, and a claim of that kind made in prose is untested.
    print("second traversal, to measure what this file reproduces")
    second = traverse()
    keys = published_ratio_keys(ops, rungs)
    ordering_forms = list(CALL_FORMS) + list(SEQUENCE_VARIANTS)
    reproduction = reproduction_record(
        readings,
        second,
        keys,
        ordering_forms=ordering_forms,
        what_was_checked=(
            "every ratio this file publishes: each rung against the anchor and against its "
            "same-arity pure-Python and same-kind zero-argument comparators, in every "
            "call-site form; the anchor across forms; every repetition sensitivity and its "
            "mirror ratios; and the loop bridge"
        ),
    )
    print(
        "reproduction: "
        f"{reproduction['ratios_whose_second_median_fell_inside_the_first_per_round_interval']}"
        f" of {reproduction['ratios_checked']} ratios inside; largest median moved "
        f"{reproduction['largest_movement_of_a_median'] * 100:.1f} percent"
    )

    rows: list[dict[str, Any]] = [{"finding": "clock", **clock}]
    rows += call_site_form_rows(readings)
    rows += ladder_rows(ops, readings)
    rows += call_site_sensitivity_rows(ops, readings)
    rows += repeated_call_rows(rungs, readings)
    rows += mechanism_bridge_rows(readings)
    rows += [ordering_record(readings, form=form) for form in ordering_forms]
    rows += [control.as_row() for control in controls]
    rows.append(reproduction)
    rows.append(reproducibility_row(readings))

    # ⛔ The reproduction check is only as wide as the enumerated key list, so a ratio the
    #    rows publish and that list forgets is a figure nobody re-measured — inside a file
    #    whose headline claim is about what reproduces. Counted, not trusted.
    published = count_published_ratios(rows)
    if published != len(keys):
        raise RuntimeError(
            f"the rows carry {published} ratio(s) and the reproduction check enumerated "
            f"{len(keys)}. Every published ratio must be re-measured, so this mismatch is a "
            "refusal rather than a partial check"
        )

    header = build_header(
        script=script,
        ops=ops,
        rungs=rungs,
        assertion=assertion,
        clock=clock,
        rounds=args.rounds,
        span_floor=span_floor,
        summary=build_summary(ops, rungs, readings),
    )
    path = args.out / "binding" / "ffi-round-trip.jsonl"
    count = write_jsonl(path, header, rows)
    print(f"wrote {count} rows -> {path}")
    print(
        "NOTE: this artifact does not regenerate byte for byte. Compare orderings and "
        "ratio intervals between runs, never bytes."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
