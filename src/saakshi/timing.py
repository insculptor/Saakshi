"""Timing as evidence — and the three things that make a duration nearly unpublishable.

This module measures how long a call takes and refuses to let the answer be mistaken for a
property of the thing called. Three facts about the method shape everything below, and each
of them is recorded on the rows rather than kept in the harness's head.

⛔ **1. THE CLOCK STEP IS COARSER THAN EVERY QUANTITY BEING MEASURED.** The best clock this
platform offers advances in steps of about a hundred nanoseconds, and the calls of interest
cost a few tens. **No individual call is ever timed here, and none can be.** Every figure is
an elapsed span divided by a declared repetition count — a mean, and a mean is a property of
the *method* as much as of the call. :func:`clock_step_ns` measures the step rather than
reading it off documentation, so the file states the limit it was written under.

⛔ **2. THE ABSOLUTE NUMBER MOVES WITH THE METHOD, SO ONLY RATIOS ARE PUBLISHED.** The same
do-nothing Python function measures differently depending on how the loop around it was
written. A figure in nanoseconds is therefore the wrong *shape* for a claim: it is the shape
of an environment reading, which is the standing this repository already gives its host
record. What survives the method is the relationship between two operations measured
**identically, in one interleaved process** — so ratios are the published quantity and
nanoseconds are recorded beside them as context.

⛔ **3. THE HARNESS MEASURES ITS OWN CALL CONVENTION.** Handing a pre-built argument tuple to
a call site is not the same act as compiling the arguments into it, and the difference was
measured to be comparable to the whole cost of an empty crossing for one family of callees
while vanishing for another. ⭐ **This is the general form of a defect this repository has
already paid for once, in a different domain: a recorder that transforms a value before
handing it to the thing being measured has made the transformation part of the measurement.**
So the call-site form is not an implementation detail of the harness — it is part of the
number, it is varied deliberately, and it is stated on every row. See :data:`CALL_FORMS`.

⚠ **Controls, not confidence.** A timing harness cannot be checked against a known answer,
because there is no known answer. What it *can* be checked against is its own ability to
report a difference that is there and to report none where there is none — so it carries a
null control, a same-arity control that separates the interpreter's cost from a binding's,
and a pair built to differ by a large stated factor. ⛔ A generator using this module refuses
to write when a control fails; see :func:`refuse_unless_all_pass`.

⛔ **Recorder, never explainer.** Nothing here describes how any measured callee does its
work. The module knows an operation as a callable, an argument tuple and an arity.
"""

from __future__ import annotations

import math
import statistics
import time
from dataclasses import dataclass
from typing import Any, Callable, Iterable, Mapping, Sequence

#: The clock. ⚠ Chosen for being the finest this platform admits, **not** for being fine
#: enough: see :func:`clock_step_ns`, which measures how far short of the subject it falls.
CLOCK_NAME = "perf_counter_ns"
_CLOCK: Callable[[], int] = time.perf_counter_ns


class TimingHarnessError(Exception):
    """A refusal from the harness itself, as opposed to a failed control."""


class CallSiteRefused(TimingHarnessError):
    """An argument that cannot be written into a call site as a literal.

    ⛔ Refused rather than quietly measured under a different form. Silently falling back to
    a form the caller did not ask for is the same defect the form distinction exists to
    expose: the harness would be reporting one method's number under another method's name.
    """


class ControlFailure(TimingHarnessError):
    """A control did not hold, so nothing measured beside it may be written."""


# --------------------------------------------------------------------------------------
# The call-site form, which is part of the number
# --------------------------------------------------------------------------------------

#: The three ways the same call is written, all measured, all reported separately.
#:
#: ⚠ These are not three implementations of one idea. They are three *different calls* that
#: happen to invoke the same callee with the same values, and the interpreter reaches the
#: callee by a different route in each. A harness that picks one and calls the result "the
#: cost of the call" has answered a question nobody asked.
CALL_FORMS: tuple[str, ...] = ("unpacked", "local_names", "literal")

CALL_FORM_NOTES: dict[str, str] = {
    "unpacked": (
        "the arguments are a tuple, built once before the loop and handed to the call site "
        "whole. ⚠ This is the form a generic harness writes without thinking about it, "
        "because it is the only one that works for an arbitrary arity"
    ),
    "local_names": (
        "the arguments are unpacked into local names before the loop and named individually "
        "at the call site — the form a caller writes by hand when the values come from "
        "variables"
    ),
    "literal": (
        "the arguments are compiled into the call site as literal constants — the form a "
        "caller writes when the values are known where the call is written"
    ),
}

#: The argument tuples every rung of a given arity is measured with.
#:
#: ⭐ **Shared on purpose, and it is what makes the comparison a comparison.** A rung's
#: figure is only informative beside a rung of the same arity holding arguments of the same
#: kinds; two rungs differing in both arity and argument kinds differ in a way no single
#: ratio can attribute. Where a callee cannot accept these values the row says so in
#: ``arguments_kind`` rather than pretending the mirror is exact.
ARGUMENTS: dict[int, tuple[Any, ...]] = {
    0: (),
    1: (370.5,),
    3: (2451545.0, 0, 260),
    4: (2000, 1, 1, 12.0),
}

#: What kinds of callee a rung may hold. ⚠ ``skeleton`` calls nothing at all: it is the loop
#: itself, measured, so a reader can see how much of every other rung is loop.
CALLEE_KINDS = frozenset({"skeleton", "pure_python", "stdlib_c", "binding"})


@dataclass(frozen=True)
class Operation:
    """One rung of the ladder: a callable, its arguments, and how many times to call it.

    ``repetitions`` is declared per rung rather than calibrated at run time. A calibrated
    count would make the method a function of the machine's mood, and the count is part of
    what a reader needs in order to know what the mean is a mean of.
    """

    id: str
    callee_kind: str
    callee: str
    does: str
    fn: Callable[..., Any] | None
    args: tuple[Any, ...]
    repetitions: int
    arity: int | None
    mirror_of: str | None = None

    def __post_init__(self) -> None:
        if self.callee_kind not in CALLEE_KINDS:
            raise TimingHarnessError(
                f"{self.id}: callee_kind {self.callee_kind!r} is not one of "
                f"{sorted(CALLEE_KINDS)}"
            )
        if self.repetitions < 1:
            raise TimingHarnessError(f"{self.id}: a rung is measured at least once")
        if self.callee_kind == "skeleton":
            if self.fn is not None or self.args:
                raise TimingHarnessError(
                    f"{self.id}: the skeleton rung calls nothing, so it carries no callable "
                    "and no arguments"
                )
        else:
            if self.fn is None:
                raise TimingHarnessError(f"{self.id}: no callable")
            if self.arity != len(self.args):
                raise TimingHarnessError(
                    f"{self.id}: declared arity {self.arity} does not match "
                    f"{len(self.args)} argument(s) — an arity that is asserted rather than "
                    "counted is an arity that can be wrong"
                )

    @property
    def arguments_kind(self) -> tuple[str, ...]:
        return tuple(type(a).__name__ for a in self.args)


# --------------------------------------------------------------------------------------
# Building a call site
# --------------------------------------------------------------------------------------

#: The loop the three forms share. Only the marked line differs between them, so a
#: difference between two forms is a difference at the call site and nowhere else.
LOOP_SKELETON = (
    "def _run(_fn, _args, _n, _clock):\n"
    "<the arguments are prepared here, or not, according to the form>\n"
    "    _t0 = _clock()\n"
    "    for _ in range(_n):\n"
    "        <the call site, which is the only line that differs between forms>\n"
    "    _t1 = _clock()\n"
    "    return _t1 - _t0\n"
)


def literal_text(value: Any) -> str:
    """`value` as source text that rebuilds it exactly, or a refusal.

    ⛔ The round trip is checked rather than assumed. A literal that rebuilds to a different
    value would put the harness in the position of measuring a call it did not describe, and
    of doing so under the one form whose whole purpose is to state the call site exactly.
    """
    text = repr(value)
    try:
        rebuilt = eval(text, {"__builtins__": {}}, {})  # noqa: S307 - text is repr's own
    except Exception as exc:  # pragma: no cover - repr of a builtin scalar always parses
        raise CallSiteRefused(f"{value!r} has no literal form: {exc}") from exc
    if type(rebuilt) is not type(value) or rebuilt != value:
        raise CallSiteRefused(
            f"{value!r} does not survive a round trip through its own repr, so it cannot be "
            "compiled into a call site as a literal"
        )
    return text


def call_site(op: Operation, form: str) -> tuple[str, str]:
    """`(preparation lines, the call-site line)` for one rung under one form."""
    if form not in CALL_FORMS:
        raise TimingHarnessError(f"{form!r} is not one of {list(CALL_FORMS)}")
    if op.callee_kind == "skeleton":
        return "", "pass"
    if form == "unpacked":
        return "", "_fn(*_args)"
    if form == "local_names":
        if not op.args:
            return "", "_fn()"
        names = ", ".join(f"_a{i}" for i in range(len(op.args)))
        trailing = "," if len(op.args) == 1 else ""
        return f"    {names}{trailing} = _args\n", f"_fn({names})"
    literals = ", ".join(literal_text(a) for a in op.args)
    return "", f"_fn({literals})"


def build_runner(op: Operation, form: str) -> tuple[Callable[..., int], str]:
    """Compile the timing loop for one rung under one form.

    ⚠ **The loop is compiled rather than parameterised, and that is the measurement.** A
    single loop taking the call site as data would make every form the same form — the one
    the harness happened to write — which is precisely the confusion this module exists to
    keep out of its own numbers.
    """
    prepare, line = call_site(op, form)
    source = (
        "def _run(_fn, _args, _n, _clock):\n"
        f"{prepare}"
        "    _t0 = _clock()\n"
        "    for _ in range(_n):\n"
        f"        {line}\n"
        "    _t1 = _clock()\n"
        "    return _t1 - _t0\n"
    )
    namespace: dict[str, Any] = {}
    exec(compile(source, f"<call site {op.id} {form}>", "exec"), namespace)  # noqa: S102
    return namespace["_run"], line


# --------------------------------------------------------------------------------------
# The clock, measured rather than read off documentation
# --------------------------------------------------------------------------------------


def clock_step_ns(samples: int = 400, clock: Callable[[], int] | None = None) -> int:
    """The smallest advance this clock was observed to make.

    ⚠ Measured by polling until the reading changes, `samples` times, and taking the
    smallest change. The reported resolution is recorded beside it; where the two disagree
    the measured one is the one that bounds what the harness can see.
    """
    tick = clock or _CLOCK
    steps: list[int] = []
    for _ in range(samples):
        first = tick()
        second = tick()
        while second == first:
            second = tick()
        steps.append(second - first)
    return min(steps)


def clock_record(*, samples: int = 400) -> dict[str, Any]:
    """The clock, as a row: what it says about itself, and what it was seen to do."""
    info = time.get_clock_info("perf_counter")
    step = clock_step_ns(samples=samples)
    return {
        "clock": CLOCK_NAME,
        "reported_resolution_nanoseconds": info.resolution * 1e9,
        "measured_step_nanoseconds": step,
        "measured_by": (
            f"polling the clock until the reading changed, {samples} times, and taking the "
            "smallest change observed"
        ),
        "monotonic": info.monotonic,
        "adjustable": info.adjustable,
        "consequence": (
            "the step is coarser than the quantities of interest, so no individual call was "
            "timed and none could be. Every figure in this file is an elapsed span divided "
            "by a declared repetition count"
        ),
    }


# --------------------------------------------------------------------------------------
# Running the ladder, interleaved
# --------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Batch:
    """One timed loop: one rung, one form, one round."""

    op_id: str
    form: str
    round_index: int
    repetitions: int
    elapsed_nanoseconds: int

    @property
    def mean_nanoseconds(self) -> float:
        return self.elapsed_nanoseconds / self.repetitions


#: How many clock steps an elapsed span must cover before it is a measurement at all.
#:
#: ⛔ A batch shorter than a handful of steps is quantised into meaninglessness, and a batch
#: shorter than one step reads **zero** — a duration of nothing, indistinguishable in every
#: later arithmetic from a call that costs nothing. ⚠ So a short batch is a refusal naming
#: the rung and the repetition count, never a small number carried forward.
SPAN_FLOOR_IN_CLOCK_STEPS = 100


def run_interleaved(
    ops: Sequence[Operation],
    forms: Sequence[str] = CALL_FORMS,
    *,
    sequence_rungs: Sequence["SequenceRung"] = (),
    rounds: int = 9,
    warmup_rounds: int = 1,
    clock: Callable[[], int] | None = None,
    minimum_span_nanoseconds: int | None = None,
) -> list[Batch]:
    """Measure every rung in every form, once per round, in one process.

    ⭐ **Interleaving is what makes a ratio mean anything.** A machine's speed drifts — other
    work arrives, the processor changes its clock, a cache fills. Measuring rung A to
    completion and then rung B compares two different machines that happen to share a
    serial number. Measuring both in every round means the drift is inside both terms of
    every ratio, and the spread of a ratio across rounds is then a statement about how much
    of it survived.

    ⚠ **The run-of-requests rungs are measured inside the same rounds**, not in a second
    pass. A ratio that crossed two passes would have exactly the defect interleaving exists
    to remove, and one such ratio is wanted: the same pure-Python callee measured both ways,
    which is what places the two halves of the ladder on one scale.

    ⚠ Warm-up rounds are run and discarded. The interpreter specialises a call site after it
    has been executed a few times, so the first traversal measures a state no later caller
    will be in.
    """
    tick = clock or _CLOCK
    if minimum_span_nanoseconds is None:
        if clock is not None:
            raise TimingHarnessError(
                "a caller supplying its own clock must state the span floor: this harness "
                "cannot derive one from a clock whose step it has not measured, and "
                "deriving one from a clock it is not using would check the wrong thing"
            )
        minimum_span_nanoseconds = SPAN_FLOOR_IN_CLOCK_STEPS * clock_step_ns()

    def record(op_id: str, form: str, index: int, repetitions: int, elapsed: int) -> None:
        if elapsed < minimum_span_nanoseconds:
            raise TimingHarnessError(
                f"{op_id} in form {form!r}: {repetitions} call(s) elapsed {elapsed} ns, "
                f"under the floor of {minimum_span_nanoseconds} ns. A span this short is "
                "quantised by the clock rather than measured by it. Raise the repetition "
                "count for this rung"
            )
        if index >= 0:
            batches.append(
                Batch(
                    op_id=op_id,
                    form=form,
                    round_index=index,
                    repetitions=repetitions,
                    elapsed_nanoseconds=elapsed,
                )
            )

    runners = {
        (op.id, form): build_runner(op, form)[0] for op in ops for form in forms
    }
    over_sequence = sequence_runner() if sequence_rungs else None
    sequences = {rung.id: build_sequences(rung) for rung in sequence_rungs}
    batches: list[Batch] = []
    for index in range(-warmup_rounds, rounds):
        for op in ops:
            for form in forms:
                record(
                    op.id,
                    form,
                    index,
                    op.repetitions,
                    runners[(op.id, form)](op.fn, op.args, op.repetitions, tick),
                )
        for rung in sequence_rungs:
            for variant in SEQUENCE_VARIANTS:
                record(
                    rung.id,
                    variant,
                    index,
                    rung.repetitions,
                    over_sequence(rung.fn, sequences[rung.id][variant], tick),
                )
    return batches


@dataclass(frozen=True)
class Reading:
    """Every round's mean for one rung under one form."""

    op_id: str
    form: str
    repetitions: int
    per_round_nanoseconds: tuple[float, ...]

    @property
    def rounds(self) -> int:
        return len(self.per_round_nanoseconds)

    @property
    def median_nanoseconds(self) -> float:
        return statistics.median(self.per_round_nanoseconds)

    @property
    def minimum_nanoseconds(self) -> float:
        return min(self.per_round_nanoseconds)

    @property
    def maximum_nanoseconds(self) -> float:
        return max(self.per_round_nanoseconds)

    def as_context(self) -> dict[str, Any]:
        """The nanoseconds, labelled with the standing they have.

        ⚠ Recorded, never published as a figure. A duration measured on one workstation is
        an indication of magnitude and moves with the method that took it — the same
        standing this repository gives its host record, and stated here so the two are not
        read differently.
        """
        return {
            "status": (
                "environment context, not a published figure: it moves with this machine and "
                "with the call-site form, and has the standing of the host record"
            ),
            "median": self.median_nanoseconds,
            "minimum": self.minimum_nanoseconds,
            "maximum": self.maximum_nanoseconds,
            "repetitions_per_round": self.repetitions,
            "rounds": self.rounds,
        }


def summarise(batches: Iterable[Batch]) -> dict[tuple[str, str], Reading]:
    """Group batches into one reading per rung per form, in round order."""
    collected: dict[tuple[str, str], list[tuple[int, float, int]]] = {}
    for batch in batches:
        collected.setdefault((batch.op_id, batch.form), []).append(
            (batch.round_index, batch.mean_nanoseconds, batch.repetitions)
        )
    readings: dict[tuple[str, str], Reading] = {}
    for key, items in collected.items():
        items.sort()
        readings[key] = Reading(
            op_id=key[0],
            form=key[1],
            repetitions=items[0][2],
            per_round_nanoseconds=tuple(value for _, value, _ in items),
        )
    return readings


# --------------------------------------------------------------------------------------
# ⛔ A repeated call is not a repeated computation
# --------------------------------------------------------------------------------------

#: The two ways a rung's arguments can arrive over a run of calls.
#:
#: ⛔ **A timing loop asks one question many times. Some callees answer the second asking
#: more cheaply than the first**, and a harness that only ever repeats one request cannot
#: tell that from a callee that is simply fast. The figure it reports is then a floor that
#: no caller asking different questions will ever see — and it is a floor wearing the label
#: of a measurement.
#:
#: ⭐ **The two variants run the identical compiled loop over two lists of the same length.**
#: Nothing differs but what the lists hold, so a difference between them is the callee's and
#: not the harness's — and where a callee is insensitive the two agree, which is what makes
#: the sensitive ones legible.
SEQUENCE_VARIANTS: tuple[str, ...] = ("one_request_repeated", "distinct_requests")

SEQUENCE_VARIANT_NOTES: dict[str, str] = {
    "one_request_repeated": (
        "the same argument tuple, the same object, every iteration — what an ordinary timing "
        "loop measures"
    ),
    "distinct_requests": (
        "a different argument tuple every iteration, all of them built before the clock "
        "starts, checked to be distinct"
    ),
}

#: The loop both variants run. ⚠ Compiled once and shared, deliberately: two loops that
#: merely look alike would leave a difference between the variants attributable to the
#: harness.
SEQUENCE_LOOP = (
    "def _run(_fn, _sequence, _clock):\n"
    "    _t0 = _clock()\n"
    "    for _args in _sequence:\n"
    "        _fn(*_args)\n"
    "    _t1 = _clock()\n"
    "    return _t1 - _t0\n"
)


@dataclass(frozen=True)
class SequenceRung:
    """A rung measured over a run of requests rather than over one request repeated."""

    id: str
    callee_kind: str
    callee: str
    does: str
    fn: Callable[..., Any]
    arity: int
    repetitions: int
    argument_at: Callable[[int], tuple[Any, ...]]
    mirror_of: str | None = None

    def __post_init__(self) -> None:
        if self.callee_kind not in CALLEE_KINDS or self.callee_kind == "skeleton":
            raise TimingHarnessError(f"{self.id}: callee_kind {self.callee_kind!r}")
        if self.arity < 1:
            raise TimingHarnessError(
                f"{self.id}: an arity-zero callee has exactly one possible request, so "
                "'the same request repeated' and 'a distinct request each time' are the "
                "same run and the distinction does not arise"
            )
        if len(self.argument_at(0)) != self.arity:
            raise TimingHarnessError(f"{self.id}: argument count does not match arity")

    @property
    def arguments_kind(self) -> tuple[str, ...]:
        return tuple(type(a).__name__ for a in self.argument_at(0))


def build_sequences(rung: SequenceRung) -> dict[str, list[tuple[Any, ...]]]:
    """Both argument runs for one rung, built before any clock starts.

    ⛔ **The distinct run is checked to be distinct.** A builder that returns the same tuple
    for every index would produce two runs that are the same run, the comparison would read
    as no difference, and *no difference* is exactly the answer the comparison exists to
    distinguish from *a difference*. So a run that is not distinct is a refusal.
    """
    first = rung.argument_at(0)
    distinct = [rung.argument_at(i) for i in range(rung.repetitions)]
    if len(set(distinct)) != rung.repetitions:
        raise TimingHarnessError(
            f"{rung.id}: the run built as distinct holds {len(set(distinct))} different "
            f"requests over {rung.repetitions} calls. A run that is not distinct measures "
            "the repeated case under the name of the distinct one"
        )
    return {
        "one_request_repeated": [first] * rung.repetitions,
        "distinct_requests": distinct,
    }


def sequence_runner() -> Callable[..., int]:
    """The one compiled loop both variants of every run-of-requests rung go through."""
    namespace: dict[str, Any] = {}
    exec(compile(SEQUENCE_LOOP, "<call site over a run of requests>", "exec"), namespace)  # noqa: S102
    return namespace["_run"]


def run_sequence_interleaved(
    rungs: Sequence[SequenceRung],
    *,
    rounds: int = 9,
    warmup_rounds: int = 1,
    clock: Callable[[], int] | None = None,
    minimum_span_nanoseconds: int | None = None,
) -> list[Batch]:
    """Measure every rung under both variants, once per round, in one process."""
    return run_interleaved(
        (),
        sequence_rungs=rungs,
        rounds=rounds,
        warmup_rounds=warmup_rounds,
        clock=clock,
        minimum_span_nanoseconds=minimum_span_nanoseconds,
    )


# --------------------------------------------------------------------------------------
# Ratios — the published quantity
# --------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Ratio:
    """One rung against another, computed per round and then summarised.

    ⛔ **Per round, never from the two summaries.** Dividing one rung's median by another's
    median throws away the pairing that interleaving exists to create: the two medians can
    come from rounds a second apart, and then the ratio carries the drift instead of
    cancelling it.
    """

    numerator: str
    denominator: str
    form: str
    per_round: tuple[float, ...]
    denominator_form: str | None = None

    @property
    def median(self) -> float:
        return statistics.median(self.per_round)

    @property
    def minimum(self) -> float:
        return min(self.per_round)

    @property
    def maximum(self) -> float:
        return max(self.per_round)

    @property
    def spread_fraction(self) -> float:
        """How wide the ratio was, as a fraction of its own median."""
        median = self.median
        if median == 0:
            return math.inf
        return (self.maximum - self.minimum) / median

    def as_json(self) -> dict[str, Any]:
        out = {
            "against": self.denominator,
            "median": self.median,
            "minimum": self.minimum,
            "maximum": self.maximum,
            "spread_fraction_of_median": self.spread_fraction,
            "rounds": len(self.per_round),
        }
        if self.denominator_form is not None and self.denominator_form != self.form:
            out["against_measured_as"] = self.denominator_form
        return out


def ratio(
    readings: Mapping[tuple[str, str], Reading],
    *,
    numerator: str,
    denominator: str,
    form: str,
    denominator_form: str | None = None,
) -> Ratio:
    """One rung over another, paired round by round.

    ⚠ ``denominator_form`` exists for the one comparison that legitimately crosses forms:
    the same rung measured under two ways of supplying its arguments. Everywhere else the
    two terms must be the same form, because a ratio between two different call-site forms
    is a statement about the harness rather than about either callee.
    """
    against = denominator_form or form
    top = readings[(numerator, form)]
    bottom = readings[(denominator, against)]
    if top.rounds != bottom.rounds:
        raise TimingHarnessError(
            f"{numerator} and {denominator} were not measured over the same rounds, so no "
            "per-round ratio between them exists"
        )
    return Ratio(
        numerator=numerator,
        denominator=denominator,
        form=form,
        denominator_form=against,
        per_round=tuple(
            a / b
            for a, b in zip(top.per_round_nanoseconds, bottom.per_round_nanoseconds)
        ),
    )


def ladder_order(
    readings: Mapping[tuple[str, str], Reading], *, form: str, round_index: int
) -> tuple[str, ...]:
    """The rungs of one form, ordered by what they cost in one round."""
    rungs = [r for key, r in readings.items() if key[1] == form]
    rungs.sort(key=lambda r: r.per_round_nanoseconds[round_index])
    return tuple(r.op_id for r in rungs)


#: How far apart two rungs must be before their order is expected to survive a re-run.
#:
#: ⛔ **Measured, not chosen for looking sensible.** "Held in every round" was the first
#: reproducible-ordering claim this harness made, and a second run at the same commit broke
#: three to four pairs per form — every one of them a pair whose ratio is one within its own
#: spread. A pair that held in every round of *one* run is a separation that run could see;
#: it is not a separation the next run will see. So the artifact publishes both, and the
#: claim it makes about a re-run is about the separated set.
SEPARATION_MARGIN = 1.10


def separated_pairs(
    readings: Mapping[tuple[str, str], Reading],
    *,
    form: str,
    margin: float = SEPARATION_MARGIN,
) -> list[list[str]]:
    """The pairs one rung is dearer than another by at least `margin`, in every round."""
    order = [
        r.op_id
        for r in sorted(
            (r for key, r in readings.items() if key[1] == form),
            key=lambda r: r.median_nanoseconds,
        )
    ]
    found: list[list[str]] = []
    for i, cheaper in enumerate(order):
        for dearer in order[i + 1 :]:
            if ratio(readings, numerator=dearer, denominator=cheaper, form=form).minimum >= margin:
                found.append([cheaper, dearer])
    return found


def ordering_record(
    readings: Mapping[tuple[str, str], Reading],
    *,
    form: str,
    margin: float = SEPARATION_MARGIN,
) -> dict[str, Any]:
    """Whether the ladder's ordering held, pair by pair — measured, not claimed.

    ⭐ **This is the half of the file that survives a re-run, so it is the half that has to
    be stated precisely.** A consumer cannot compare this file's bytes against a re-run's;
    the ordering is one of the two things it *can* compare, and a bare "the ordering is
    stable" would be false — rungs the harness cannot separate change places between rounds
    for no reason but noise.

    ⛔ So the claim is made pair by pair rather than over the whole list. A pair that held in
    every round is a separation this harness can see; a pair that swapped is one it cannot,
    ⚠ and the two are reported side by side with the pair's own ratio, so a reader can check
    the obvious hypothesis — that the pairs which swap are exactly the pairs whose ratio is
    one within its own spread — instead of being asked to take it.
    """
    rounds = next(iter(readings.values())).rounds
    order = [
        r.op_id
        for r in sorted(
            (r for key, r in readings.items() if key[1] == form),
            key=lambda r: r.median_nanoseconds,
        )
    ]
    held: list[list[str]] = []
    swapped: list[dict[str, Any]] = []
    for i, cheaper in enumerate(order):
        for dearer in order[i + 1 :]:
            pair_ratio = ratio(readings, numerator=dearer, denominator=cheaper, form=form)
            if all(value > 1.0 for value in pair_ratio.per_round):
                held.append([cheaper, dearer])
            else:
                swapped.append(
                    {
                        "pair": [cheaper, dearer],
                        "median_ratio": pair_ratio.median,
                        "minimum_ratio": pair_ratio.minimum,
                    }
                )
    separated = separated_pairs(readings, form=form, margin=margin)
    return {
        "finding": "ordering",
        "form": form,
        "rounds": rounds,
        "ordering_cheapest_first": order,
        "identical_in_every_round": not swapped,
        "pairs_compared": len(held) + len(swapped),
        "pairs_that_held_in_every_round": len(held),
        "pairs_that_changed_places": swapped,
        "separation_margin": margin,
        "pairs_separated_by_the_margin": len(separated),
        "separated_pairs": separated,
        "meaning": (
            "⚠ THREE NESTED SETS, AND NONE OF THEM IS A CLAIM ABOUT A RE-RUN ON ITS OWN. "
            "Every pair was compared. A pair that held in every round is a separation THIS "
            "run could see — and a second traversal at this commit reordered several of "
            "them, all pairs whose ratio is one within its own spread. A pair separated by "
            "the margin is a stronger statement, ⛔ and it was measured to be not strong "
            "enough either. The figure to read for an ordering claim is "
            "`smallest_separation_at_which_every_pair_kept_its_order` in the `reproduction` "
            "row, because it was measured rather than chosen"
        ),
    }


# --------------------------------------------------------------------------------------
# ⛔ A file that cannot regenerate has to carry the measurement of what it does reproduce
# --------------------------------------------------------------------------------------


def reproduction_record(
    first: Mapping[tuple[str, str], Reading],
    second: Mapping[tuple[str, str], Reading],
    ratio_keys: Sequence[tuple[str, str, str, str | None]],
    *,
    ordering_forms: Sequence[str],
    margin: float = SEPARATION_MARGIN,
    what_was_checked: str,
) -> dict[str, Any]:
    """Run the whole ladder a second time and report what survived.

    ⭐ **An artifact that states it cannot be compared byte for byte owes a statement of what
    *can* be compared, and a statement of that kind is a claim like any other.** Made in
    prose it is untested; made here it is a measurement the file carries about itself, taken
    by the same instrument in the same process on the same day.

    ⚠ **And that is its limit, stated rather than left to be inferred.** Two traversals
    minutes apart on one machine is the weakest form of this check. It cannot speak for a
    different day, a different load, a different processor or a different interpreter build.
    A consumer re-running the generator is performing the stronger version of exactly this
    comparison, which is why the file publishes the intervals it would be compared against.
    """
    inside = 0
    outside: list[str] = []
    movements: list[tuple[float, str]] = []
    for numerator, denominator, form, denominator_form in ratio_keys:
        a = ratio(
            first,
            numerator=numerator,
            denominator=denominator,
            form=form,
            denominator_form=denominator_form,
        )
        b = ratio(
            second,
            numerator=numerator,
            denominator=denominator,
            form=form,
            denominator_form=denominator_form,
        )
        label = (
            f"{numerator} ({form}) over {denominator} "
            f"({denominator_form or form})"
        )
        if a.minimum <= b.median <= a.maximum:
            inside += 1
        else:
            outside.append(label)
        movements.append((abs(b.median - a.median) / a.median, label))
    movements.sort(reverse=True)
    fractions = sorted(value for value, _ in movements)

    ordering = []
    for form in ordering_forms:
        held_first = {tuple(p) for p in _held_pairs(first, form=form)}
        held_second = {tuple(p) for p in _held_pairs(second, form=form)}
        separated_first = {tuple(p) for p in separated_pairs(first, form=form, margin=margin)}
        separated_second = {tuple(p) for p in separated_pairs(second, form=form, margin=margin)}
        measured_margin = margin_that_held(first, second, form=form)
        ordering.append(
            {
                "form": form,
                "pairs_that_held_in_every_round_first": len(held_first),
                "pairs_that_held_in_every_round_second": len(held_second),
                "held_in_the_first_and_not_the_second": sorted(
                    list(pair) for pair in held_first - held_second
                ),
                "declared_margin": margin,
                "pairs_separated_by_the_declared_margin_first": len(separated_first),
                "pairs_separated_by_the_declared_margin_second": len(separated_second),
                "separated_in_the_first_and_not_the_second": sorted(
                    list(pair) for pair in separated_first - separated_second
                ),
                "smallest_separation_at_which_every_pair_kept_its_order": measured_margin,
                "margin_note": (
                    "⭐ MEASURED, NOT CHOSEN. The declared margin is what the ordering rows "
                    "publish; the figure beside it is the smallest separation such that "
                    "EVERY pair the first traversal separated by at least that much was "
                    "still in the same order in the second. ⚠ Where it exceeds the declared "
                    "margin, the declared margin did not hold even across two traversals of "
                    "one process, and a reader wanting an ordering claim should take the "
                    "measured figure. ⛔ It is itself a measurement: a further run may need "
                    "a larger one"
                ),
            }
        )
    return {
        "finding": "reproduction",
        "method": (
            "the whole ladder was traversed a second time, in the same process and at the "
            "same commit, and the second traversal was compared against the first"
        ),
        "what_was_checked": what_was_checked,
        "ratios_checked": len(ratio_keys),
        "ratios_whose_second_median_fell_inside_the_first_per_round_interval": inside,
        "ratios_that_fell_outside": outside,
        "largest_movement_of_a_median": movements[0][0] if movements else None,
        "largest_movement_was": movements[0][1] if movements else None,
        "median_movement_of_a_median": (
            fractions[len(fractions) // 2] if fractions else None
        ),
        "ordering": ordering,
        "limit": (
            "⚠ two traversals minutes apart on one machine is the weakest form of this "
            "check. It says nothing about a different day, a different load, a different "
            "processor or a different interpreter build. A consumer re-running the generator "
            "is performing the stronger version of the same comparison"
        ),
    }


def margin_that_held(
    first: Mapping[tuple[str, str], Reading],
    second: Mapping[tuple[str, str], Reading],
    *,
    form: str,
) -> float | None:
    """The smallest separation margin that survived both traversals, or `None`.

    ⭐ **The margin is measured rather than chosen, because a chosen one was measured to be
    wrong.** It answers the question a consumer actually has — *how far apart must two rungs
    be in this file before their order reproduces?* — by finding the smallest separation `m`
    such that **every** pair the first traversal separated by at least `m` was still in the
    same order in the second.

    ⚠ It is not a guarantee and cannot be one: it is the value two traversals of one process
    support. A run on another day may need a larger one, which is exactly why the figure is
    published beside its own method instead of being folded into a constant.
    """
    order = [
        r.op_id
        for r in sorted(
            readings_of(first, form).values(), key=lambda r: r.median_nanoseconds
        )
    ]
    pairs: list[tuple[float, bool]] = []
    for i, cheaper in enumerate(order):
        for dearer in order[i + 1 :]:
            separation = ratio(
                first, numerator=dearer, denominator=cheaper, form=form
            ).minimum
            kept = all(
                value > 1.0
                for value in ratio(
                    second, numerator=dearer, denominator=cheaper, form=form
                ).per_round
            )
            pairs.append((separation, kept))
    if not pairs:
        return None
    for candidate in sorted({1.0, *(separation for separation, _ in pairs)}):
        if all(kept for separation, kept in pairs if separation >= candidate):
            return candidate
    return None


def readings_of(
    readings: Mapping[tuple[str, str], Reading], form: str
) -> dict[str, Reading]:
    """The readings of one form, by rung."""
    return {key[0]: value for key, value in readings.items() if key[1] == form}


def _held_pairs(
    readings: Mapping[tuple[str, str], Reading], *, form: str
) -> list[list[str]]:
    order = [
        r.op_id
        for r in sorted(
            (r for key, r in readings.items() if key[1] == form),
            key=lambda r: r.median_nanoseconds,
        )
    ]
    found: list[list[str]] = []
    for i, cheaper in enumerate(order):
        for dearer in order[i + 1 :]:
            pair = ratio(readings, numerator=dearer, denominator=cheaper, form=form)
            if all(value > 1.0 for value in pair.per_round):
                found.append([cheaper, dearer])
    return found


# --------------------------------------------------------------------------------------
# Controls — ⛔ the generator refuses to write when one of these fails
# --------------------------------------------------------------------------------------

#: How far the ratio of a rung to an identical copy of itself may sit from one.
#:
#: ⚠ Wide on purpose. This is a bound on the harness, not on the machine, and a narrow bound
#: would turn other work arriving on the machine into a failed control — which would train a
#: reader to re-run until it passes, and a control that is re-run until it passes is not one.
NULL_TOLERANCE = 0.25

#: The factor the constructed pair must be seen to differ by, against a construction that
#: makes it about a hundred. ⚠ Also loose on purpose, for the same reason.
SCALE_FLOOR = 20.0

#: How many times the heavy control performs the light one. ⭐ The pair is built out of the
#: light operation itself, so the expected ratio is a property of the construction rather
#: than a number somebody chose to expect.
HEAVY_MULTIPLE = 100


@dataclass(frozen=True)
class Control:
    """One check on the harness, with what it measured and whether it held."""

    id: str
    question: str
    expectation: str
    measured: Mapping[str, Any]
    passed: bool
    why_it_matters: str

    def as_row(self) -> dict[str, Any]:
        return {
            "finding": "control",
            "control": self.id,
            "question": self.question,
            "expectation": self.expectation,
            "measured": dict(self.measured),
            "held": self.passed,
            "why_it_matters": self.why_it_matters,
        }


def refuse_unless_all_pass(controls: Sequence[Control]) -> None:
    """⛔ Nothing is written beside a control that did not hold."""
    failed = [c for c in controls if not c.passed]
    if failed:
        raise ControlFailure(
            "refusing to write: "
            + "; ".join(f"{c.id} — expected {c.expectation}, measured {dict(c.measured)}" for c in failed)
        )


def control_null(
    readings: Mapping[tuple[str, str], Reading],
    *,
    left: str,
    right: str,
    forms: Sequence[str] = CALL_FORMS,
    tolerance: float = NULL_TOLERANCE,
) -> Control:
    """The same operation under two names must not appear to differ.

    ⭐ **The control that catches a harness reporting a difference it manufactured.** Two
    rungs holding the identical callable and the identical arguments are measured in the
    same interleave; if their ratio is not one, the difference came from the harness or from
    the machine, and every other difference in the file is suspect by the same amount.
    """
    measured = {
        form: ratio(readings, numerator=left, denominator=right, form=form).median
        for form in forms
    }
    passed = all(abs(value - 1.0) <= tolerance for value in measured.values())
    return Control(
        id="identical_pair_reads_as_no_difference",
        question=(
            f"measured in the same interleave, does {left!r} differ from {right!r} — which "
            "hold the same callable and the same arguments?"
        ),
        expectation=f"a ratio within {tolerance:.2f} of 1.0 in every call-site form",
        measured={"median_ratio_per_form": measured, "tolerance": tolerance},
        passed=passed,
        why_it_matters=(
            "a harness that reports a difference between two measurements of one operation "
            "reports differences that are its own. This bounds how large such a difference "
            "could be without being noticed"
        ),
    )


def control_same_arity_stdlib(ops: Sequence[Operation]) -> Control:
    """Every arity a binding is measured at must also carry a pure-Python and a C rung.

    ⛔ **Structural, and it is the control that keeps a number attributable.** An empty
    crossing costs what the interpreter's own call protocol costs; without a rung of the
    same arity in each of the other two families, a binding's figure cannot be separated
    into what the interpreter charged and what the binding added, and the whole figure gets
    attributed to the binding.
    """
    by_kind: dict[str, set[int]] = {}
    for op in ops:
        if op.arity is None:
            continue
        by_kind.setdefault(op.callee_kind, set()).add(op.arity)
    binding = by_kind.get("binding", set())
    pure = by_kind.get("pure_python", set())
    c_calls = by_kind.get("stdlib_c", set())
    missing_pure = sorted(binding - pure)
    missing_c = sorted(binding - c_calls)
    return Control(
        id="every_binding_arity_has_a_same_arity_comparator",
        question=(
            "is every arity at which a binding is measured also measured on a pure-Python "
            "callable and on a C callable from the standard library?"
        ),
        expectation="no arity missing a comparator in either family",
        measured={
            "binding_arities": sorted(binding),
            "pure_python_arities": sorted(pure),
            "stdlib_c_arities": sorted(c_calls),
            "binding_arities_without_a_pure_python_comparator": missing_pure,
            "binding_arities_without_a_stdlib_c_comparator": missing_c,
        },
        passed=not missing_pure and not missing_c,
        why_it_matters=(
            "the cost of crossing into a C callable is not the binding's cost until the "
            "interpreter's own share of it has been measured separately at the same arity"
        ),
    )


def control_expected_difference(
    readings: Mapping[tuple[str, str], Reading],
    *,
    heavy: str,
    light: str,
    forms: Sequence[str] = CALL_FORMS,
    floor: float = SCALE_FLOOR,
    built_multiple: int = HEAVY_MULTIPLE,
) -> Control:
    """A pair built to differ by a large factor must be seen to differ by one.

    ⭐ **An expected difference is the control.** A null control alone is satisfied by a
    harness that reports nothing at all: measure zero everywhere and every identical pair
    agrees perfectly. The pair below is constructed so that one member performs the other a
    stated number of times, so the difference is a property of the construction and the only
    question is whether the harness can see it.
    """
    measured = {
        form: ratio(readings, numerator=heavy, denominator=light, form=form).median
        for form in forms
    }
    passed = all(value >= floor for value in measured.values())
    return Control(
        id="a_pair_built_to_differ_is_seen_to_differ",
        question=(
            f"{heavy!r} performs {light!r} {built_multiple} times by construction. Does the "
            "harness report it as substantially more expensive?"
        ),
        expectation=f"a ratio of at least {floor:.0f} in every call-site form",
        measured={"median_ratio_per_form": measured, "floor": floor, "built_multiple": built_multiple},
        passed=passed,
        why_it_matters=(
            "a harness that measures nothing passes every null control. This is the check "
            "that it is measuring at all, and it is the only one of the three that can fail "
            "by the harness being silent rather than by it being noisy"
        ),
    )


def control_sequence_mechanism(
    readings: Mapping[tuple[str, str], Reading],
    *,
    insensitive: Sequence[str],
    tolerance: float = NULL_TOLERANCE,
) -> Control:
    """Supplying distinct arguments must not, by itself, cost anything.

    ⛔ **Without this the sensitivity measurement proves nothing.** A run of distinct
    argument tuples touches more memory than a run of one tuple repeated, so a difference
    between the two variants could be the machine's rather than the callee's. The rungs
    named here call a Python function that does nothing at all with its arguments — so
    whatever the mechanism costs, it costs there too, and if they read alike the mechanism
    is not what a sensitive rung is showing.
    """
    measured = {
        rung: ratio(
            readings,
            numerator=rung,
            denominator=rung,
            form="distinct_requests",
            denominator_form="one_request_repeated",
        ).median
        for rung in insensitive
    }
    passed = all(abs(value - 1.0) <= tolerance for value in measured.values())
    return Control(
        id="supplying_distinct_arguments_costs_nothing_by_itself",
        question=(
            "measured over a run of distinct argument tuples rather than one tuple repeated, "
            "do callees that cannot be sensitive to the difference read alike?"
        ),
        expectation=f"a ratio within {tolerance:.2f} of 1.0 for every such rung",
        measured={"median_ratio_per_rung": measured, "tolerance": tolerance},
        passed=passed,
        why_it_matters=(
            "a run of distinct tuples touches more memory than a run of one tuple repeated. "
            "Unless that costs nothing where it cannot matter, a rung that does differ "
            "between the two runs has not been shown to differ for a reason of its own"
        ),
    )


# --------------------------------------------------------------------------------------
# The rungs that need no third-party library
# --------------------------------------------------------------------------------------


def _pure_arity_0() -> None:
    return None


def _pure_arity_1(a: Any) -> None:  # noqa: ARG001 - the point is that it does nothing
    return None


def _pure_arity_3(a: Any, b: Any, c: Any) -> None:  # noqa: ARG001
    return None


def _pure_arity_4(a: Any, b: Any, c: Any, d: Any) -> None:  # noqa: ARG001
    return None


def _heavy_by_construction() -> None:
    """The light rung, performed :data:`HEAVY_MULTIPLE` times."""
    for _ in range(HEAVY_MULTIPLE):
        _pure_arity_0()


#: The identifiers the standard rungs use, so a generator and a test name the same things.
ANCHOR = "python_arity_0"
NULL_TWIN = "python_arity_0_second_reading"
HEAVY = "control_heavy_by_construction"
SKELETON = "loop_only"


def standard_operations(*, repetitions: int = 300_000, heavy_repetitions: int = 4_000) -> list[Operation]:
    """The rungs that measure the interpreter rather than any third party.

    ⭐ **These are the ladder's floor, and they are what makes the rest of it readable.** A
    binding's figure means nothing on its own; beside a pure-Python callable of the same
    arity and a C callable of the same arity, it separates into a share the interpreter
    charges everybody and a share that is the binding's.

    ⚠ The C rungs use a standard-library function that does a small amount of real
    arithmetic, so each is an **upper** bound on what the interpreter's own protocol costs
    at that arity, never a floor.
    """
    return [
        Operation(
            id=SKELETON,
            callee_kind="skeleton",
            callee="nothing",
            does="the timing loop with no call in it",
            fn=None,
            args=(),
            repetitions=repetitions,
            arity=None,
        ),
        Operation(
            id=ANCHOR,
            callee_kind="pure_python",
            callee="a Python function defined in this repository",
            does="returns immediately, taking no arguments",
            fn=_pure_arity_0,
            args=ARGUMENTS[0],
            repetitions=repetitions,
            arity=0,
        ),
        Operation(
            id=NULL_TWIN,
            callee_kind="pure_python",
            callee="a Python function defined in this repository",
            does=(
                "the same callable and the same arguments as the anchor, measured a second "
                "time in the same interleave — the null control"
            ),
            fn=_pure_arity_0,
            args=ARGUMENTS[0],
            repetitions=repetitions,
            arity=0,
        ),
        Operation(
            id="python_arity_1",
            callee_kind="pure_python",
            callee="a Python function defined in this repository",
            does="returns immediately, taking one argument",
            fn=_pure_arity_1,
            args=ARGUMENTS[1],
            repetitions=repetitions,
            arity=1,
            mirror_of=ANCHOR,
        ),
        Operation(
            id="python_arity_3",
            callee_kind="pure_python",
            callee="a Python function defined in this repository",
            does="returns immediately, taking three arguments",
            fn=_pure_arity_3,
            args=ARGUMENTS[3],
            repetitions=repetitions,
            arity=3,
            mirror_of=ANCHOR,
        ),
        Operation(
            id="python_arity_4",
            callee_kind="pure_python",
            callee="a Python function defined in this repository",
            does="returns immediately, taking four arguments",
            fn=_pure_arity_4,
            args=ARGUMENTS[4],
            repetitions=repetitions,
            arity=4,
            mirror_of=ANCHOR,
        ),
        Operation(
            id="stdlib_c_arity_0",
            callee_kind="stdlib_c",
            callee="a C function in the standard library, taking no arguments",
            does="reads a monotonic clock",
            fn=time.monotonic,
            args=ARGUMENTS[0],
            repetitions=repetitions,
            arity=0,
        ),
        Operation(
            id="stdlib_c_arity_1",
            callee_kind="stdlib_c",
            callee="a C function in the standard library, taking a variable count",
            does="a small floating-point calculation over its arguments",
            fn=math.hypot,
            args=ARGUMENTS[1],
            repetitions=repetitions,
            arity=1,
            mirror_of="stdlib_c_arity_0",
        ),
        Operation(
            id="stdlib_c_arity_3",
            callee_kind="stdlib_c",
            callee="a C function in the standard library, taking a variable count",
            does="a small floating-point calculation over its arguments",
            fn=math.hypot,
            args=ARGUMENTS[3],
            repetitions=repetitions,
            arity=3,
            mirror_of="stdlib_c_arity_0",
        ),
        Operation(
            id="stdlib_c_arity_4",
            callee_kind="stdlib_c",
            callee="a C function in the standard library, taking a variable count",
            does="a small floating-point calculation over its arguments",
            fn=math.hypot,
            args=ARGUMENTS[4],
            repetitions=repetitions,
            arity=4,
            mirror_of="stdlib_c_arity_0",
        ),
        Operation(
            id=HEAVY,
            callee_kind="pure_python",
            callee="a Python function defined in this repository",
            does=(
                f"performs the anchor operation {HEAVY_MULTIPLE} times — the pair built to "
                "differ"
            ),
            fn=_heavy_by_construction,
            args=ARGUMENTS[0],
            repetitions=heavy_repetitions,
            arity=0,
            mirror_of=ANCHOR,
        ),
    ]


def standard_sequence_rungs(*, repetitions: int = 50_000) -> list[SequenceRung]:
    """The pure-Python rungs that check the run-of-requests mechanism itself.

    ⭐ One per arity that a measured binding uses, so the mechanism is controlled at the
    arity it is being read at rather than at a convenient one.
    """
    return [
        SequenceRung(
            id="python_arity_1",
            callee_kind="pure_python",
            callee="a Python function defined in this repository",
            does="returns immediately, taking one argument and looking at nothing",
            fn=_pure_arity_1,
            arity=1,
            repetitions=repetitions,
            argument_at=lambda i: (ARGUMENTS[1][0] + i * 1e-3,),
        ),
        SequenceRung(
            id="python_arity_3",
            callee_kind="pure_python",
            callee="a Python function defined in this repository",
            does="returns immediately, taking three arguments and looking at none of them",
            fn=_pure_arity_3,
            arity=3,
            repetitions=repetitions,
            argument_at=lambda i: (ARGUMENTS[3][0] + i * 1e-3, ARGUMENTS[3][1], ARGUMENTS[3][2]),
        ),
        SequenceRung(
            id="python_arity_4",
            callee_kind="pure_python",
            callee="a Python function defined in this repository",
            does="returns immediately, taking four arguments and looking at none of them",
            fn=_pure_arity_4,
            arity=4,
            repetitions=repetitions,
            argument_at=lambda i: (
                ARGUMENTS[4][0],
                ARGUMENTS[4][1],
                ARGUMENTS[4][2],
                ARGUMENTS[4][3] + i * 1e-3,
            ),
        ),
    ]


#: The rungs :func:`control_sequence_mechanism` reads. ⚠ They are pure-Python no-ops, so
#: sensitivity to *which* request is asked is not merely unexpected there — it is impossible.
MECHANISM_CONTROL_RUNGS: tuple[str, ...] = (
    "python_arity_1",
    "python_arity_3",
    "python_arity_4",
)


def standard_controls(
    readings: Mapping[tuple[str, str], Reading],
    ops: Sequence[Operation],
    *,
    forms: Sequence[str] = CALL_FORMS,
    sequence_readings: Mapping[tuple[str, str], Reading] | None = None,
    insensitive: Sequence[str] = MECHANISM_CONTROL_RUNGS,
) -> list[Control]:
    """The controls, in the order a reader should read them.

    ⚠ The fourth is present only when a run-of-requests measurement was taken. It is not
    optional in the sense of "nice to have": a file carrying a sensitivity figure without it
    is carrying an unattributed difference.
    """
    controls = [
        control_null(readings, left=ANCHOR, right=NULL_TWIN, forms=forms),
        control_same_arity_stdlib(ops),
        control_expected_difference(readings, heavy=HEAVY, light=ANCHOR, forms=forms),
    ]
    if sequence_readings is not None:
        controls.append(
            control_sequence_mechanism(sequence_readings, insensitive=insensitive)
        )
    return controls
