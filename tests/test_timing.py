"""The timing harness's own controls, and its refusals.

⛔ **NOT ONE ASSERTION HERE READS A WALL CLOCK.** A test that asserts a duration asserts a
property of the machine it happens to run on, and fails on a loaded one — which trains a
reader to re-run it until it passes, and a check that is re-run until it passes has stopped
being a check.

⭐ **So the clock is supplied.** :class:`Ledger` is a clock that only moves when a callee
moves it, and the synthetic callees below move it by amounts this file chooses. The harness
cannot tell it from a real one, every elapsed span is then exact, and a control that ought
to read 1.0 reads 1.0 — so these tests assert the harness's *arithmetic and its verdicts*,
which is what the harness is, rather than this machine's speed, which is not.

⚠ The one thing a synthetic clock cannot check is that the harness reads a real one
correctly. That is checked separately and cheaply — see the clock tests, which assert
properties of the measured step rather than its value.
"""

from __future__ import annotations

import time

import pytest

from saakshi.timing import (
    ANCHOR,
    ARGUMENTS,
    CALL_FORMS,
    HEAVY,
    HEAVY_MULTIPLE,
    MECHANISM_CONTROL_RUNGS,
    NULL_TWIN,
    SEPARATION_MARGIN,
    SEQUENCE_VARIANTS,
    CallSiteRefused,
    Control,
    ControlFailure,
    Operation,
    Reading,
    SequenceRung,
    TimingHarnessError,
    build_runner,
    build_sequences,
    call_site,
    clock_record,
    clock_step_ns,
    control_expected_difference,
    control_null,
    control_same_arity_stdlib,
    control_sequence_mechanism,
    literal_text,
    ordering_record,
    ratio,
    refuse_unless_all_pass,
    reproduction_record,
    run_interleaved,
    separated_pairs,
    standard_operations,
    standard_sequence_rungs,
    summarise,
)

# --------------------------------------------------------------------------------------
# A clock that only moves when something spends it
# --------------------------------------------------------------------------------------


class Ledger:
    """A clock, and the ledger the synthetic callees charge against it."""

    def __init__(self) -> None:
        self.now = 0

    def __call__(self) -> int:
        return self.now

    def spender(self, cost: int, arity: int = 0):
        """A callable of the given arity that costs exactly `cost` every time."""

        def spend(*args: object) -> None:
            assert len(args) == arity
            self.now += cost

        return spend

    def cacher(self, *, repeat_cost: int, fresh_cost: int, arity: int):
        """A callable that charges less when handed the request it was handed last.

        ⭐ The synthetic form of the one behaviour this harness exists to expose: a callee
        for which repeating a question is not the same work as asking a new one.

        ⚠ It remembers **one** request, not every request it has ever seen. A callee that
        remembered them all would be indistinguishable from a cheap callee after the first
        traversal — and the harness's warm-up round is a traversal, so a test built on the
        remember-everything model would measure the warm-up rather than the behaviour.
        """
        last: list[tuple[object, ...]] = [()]

        def spend(*args: object) -> None:
            assert len(args) == arity
            self.now += repeat_cost if args == last[0] else fresh_cost
            last[0] = args

        return spend


def _op(ledger: Ledger, name: str, cost: int, arity: int = 0, **kwargs) -> Operation:
    return Operation(
        id=name,
        callee_kind=kwargs.pop("callee_kind", "pure_python"),
        callee="a synthetic callable",
        does=f"charges {cost} against the ledger",
        fn=ledger.spender(cost, arity),
        args=ARGUMENTS[arity],
        repetitions=kwargs.pop("repetitions", 10),
        arity=arity,
        **kwargs,
    )


def _run(ops, ledger, *, rounds=4, sequence_rungs=()):
    batches = run_interleaved(
        ops,
        sequence_rungs=sequence_rungs,
        rounds=rounds,
        warmup_rounds=1,
        clock=ledger,
        minimum_span_nanoseconds=0,
    )
    return summarise(batches)


def _reading(op_id: str, form: str, values: tuple[float, ...]) -> Reading:
    return Reading(op_id=op_id, form=form, repetitions=1, per_round_nanoseconds=values)


# --------------------------------------------------------------------------------------
# The call site, which is part of the number
# --------------------------------------------------------------------------------------


def test_the_three_forms_write_three_different_call_sites():
    ledger = Ledger()
    op = _op(ledger, "one_argument", 5, arity=1)
    assert call_site(op, "unpacked")[1] == "_fn(*_args)"
    assert call_site(op, "local_names") == ("    _a0, = _args\n", "_fn(_a0)")
    assert call_site(op, "literal")[1] == "_fn(370.5)"


def test_a_zero_argument_rung_still_differs_between_forms():
    """⚠ Even with nothing to pass, the three routes into the callee are not one route."""
    ledger = Ledger()
    op = _op(ledger, "no_arguments", 5)
    sites = {form: call_site(op, form)[1] for form in CALL_FORMS}
    assert sites["unpacked"] == "_fn(*_args)"
    assert sites["local_names"] == "_fn()"
    assert sites["literal"] == "_fn()"


def test_the_skeleton_rung_calls_nothing_in_every_form():
    skeleton = Operation(
        id="loop_only",
        callee_kind="skeleton",
        callee="nothing",
        does="the loop",
        fn=None,
        args=(),
        repetitions=10,
        arity=None,
    )
    for form in CALL_FORMS:
        assert call_site(skeleton, form)[1] == "pass"


def test_a_value_with_no_literal_form_is_refused_not_quietly_measured():
    """⛔ Falling back to another form would report one method under another's name."""

    class Opaque:
        pass

    with pytest.raises(CallSiteRefused):
        literal_text(Opaque())


def test_a_literal_that_does_not_rebuild_its_own_value_is_refused():
    class Liar:
        def __repr__(self) -> str:
            return "1"

    with pytest.raises(CallSiteRefused):
        literal_text(Liar())


def test_every_scalar_the_ladder_passes_survives_its_own_repr():
    for arity, args in ARGUMENTS.items():
        for value in args:
            assert eval(literal_text(value)) == value, arity


def test_the_compiled_loop_calls_the_callee_exactly_as_many_times_as_declared():
    ledger = Ledger()
    op = _op(ledger, "counted", 7, arity=1, repetitions=13)
    for form in CALL_FORMS:
        run, _ = build_runner(op, form)
        before = ledger.now
        elapsed = run(op.fn, op.args, op.repetitions, ledger)
        assert elapsed == 13 * 7
        assert ledger.now - before == 13 * 7


# --------------------------------------------------------------------------------------
# What a rung may declare about itself
# --------------------------------------------------------------------------------------


def test_a_declared_arity_that_does_not_match_the_arguments_is_refused():
    """⛔ An arity that is asserted rather than counted is an arity that can be wrong."""
    with pytest.raises(TimingHarnessError, match="arity"):
        Operation(
            id="wrong",
            callee_kind="pure_python",
            callee="x",
            does="x",
            fn=lambda a: None,
            args=(1.0, 2.0),
            repetitions=10,
            arity=1,
        )


def test_the_skeleton_rung_may_not_carry_a_callable():
    with pytest.raises(TimingHarnessError, match="calls nothing"):
        Operation(
            id="loop_only",
            callee_kind="skeleton",
            callee="nothing",
            does="the loop",
            fn=lambda: None,
            args=(),
            repetitions=10,
            arity=None,
        )


def test_an_unknown_callee_kind_is_refused():
    with pytest.raises(TimingHarnessError, match="callee_kind"):
        Operation(
            id="x",
            callee_kind="mystery",
            callee="x",
            does="x",
            fn=lambda: None,
            args=(),
            repetitions=10,
            arity=0,
        )


# --------------------------------------------------------------------------------------
# Interleaving, and the arithmetic on top of it
# --------------------------------------------------------------------------------------


def test_warmup_rounds_are_run_and_discarded():
    ledger = Ledger()
    ops = [_op(ledger, "a", 3), _op(ledger, "b", 5)]
    batches = run_interleaved(
        ops, rounds=4, warmup_rounds=2, clock=ledger, minimum_span_nanoseconds=0
    )
    assert {b.round_index for b in batches} == {0, 1, 2, 3}
    assert len(batches) == 4 * len(ops) * len(CALL_FORMS)
    # ⚠ The discarded rounds really ran: the ledger holds six traversals, not four.
    assert ledger.now == 6 * len(CALL_FORMS) * 10 * (3 + 5)


def test_every_rung_is_measured_once_per_round_in_every_form():
    ledger = Ledger()
    ops = [_op(ledger, "a", 3), _op(ledger, "b", 5)]
    readings = _run(ops, ledger, rounds=4)
    assert set(readings) == {(op.id, form) for op in ops for form in CALL_FORMS}
    for reading in readings.values():
        assert reading.rounds == 4


def test_a_ratio_is_computed_per_round_and_not_between_two_summaries():
    left = _reading("left", "unpacked", (10.0, 40.0))
    right = _reading("right", "unpacked", (5.0, 40.0))
    computed = ratio(
        {("left", "unpacked"): left, ("right", "unpacked"): right},
        numerator="left",
        denominator="right",
        form="unpacked",
    )
    assert computed.per_round == (2.0, 1.0)
    assert computed.median == 1.5
    # ⛔ Dividing the two medians instead would give 25.0 / 22.5, which is neither round.
    assert computed.median != 25.0 / 22.5


def test_a_ratio_between_rungs_measured_over_different_rounds_is_refused():
    readings = {
        ("left", "unpacked"): _reading("left", "unpacked", (1.0, 2.0)),
        ("right", "unpacked"): _reading("right", "unpacked", (1.0,)),
    }
    with pytest.raises(TimingHarnessError, match="same rounds"):
        ratio(readings, numerator="left", denominator="right", form="unpacked")


def test_a_span_too_short_for_the_clock_is_refused_rather_than_recorded():
    """⛔ A batch under one clock step reads zero, and zero is not a small measurement."""
    ledger = Ledger()
    ops = [_op(ledger, "a", 1, repetitions=10)]
    with pytest.raises(TimingHarnessError, match="under the floor"):
        run_interleaved(
            ops, rounds=1, warmup_rounds=0, clock=ledger, minimum_span_nanoseconds=1_000
        )


def test_a_caller_supplying_a_clock_must_state_the_span_floor():
    """⚠ Deriving a floor from a clock the run is not using would check the wrong thing."""
    ledger = Ledger()
    with pytest.raises(TimingHarnessError, match="span floor"):
        run_interleaved([_op(ledger, "a", 3)], rounds=1, warmup_rounds=0, clock=ledger)


# --------------------------------------------------------------------------------------
# The ordering — the half of the artifact a re-run is expected to reproduce
# --------------------------------------------------------------------------------------


def test_a_pair_that_never_changed_places_is_reported_apart_from_one_that_did():
    readings = {
        ("cheap", "unpacked"): _reading("cheap", "unpacked", (10.0, 10.0, 10.0)),
        ("dear", "unpacked"): _reading("dear", "unpacked", (90.0, 90.0, 90.0)),
        ("twin", "unpacked"): _reading("twin", "unpacked", (11.0, 9.0, 10.0)),
    }
    record = ordering_record(readings, form="unpacked")
    assert record["identical_in_every_round"] is False
    swapped = [entry["pair"] for entry in record["pairs_that_changed_places"]]
    assert swapped == [["cheap", "twin"]]
    assert record["pairs_that_held_in_every_round"] == 2
    assert record["ordering_cheapest_first"][-1] == "dear"


def test_an_ordering_that_held_everywhere_says_so():
    readings = {
        ("cheap", "unpacked"): _reading("cheap", "unpacked", (10.0, 11.0)),
        ("dear", "unpacked"): _reading("dear", "unpacked", (90.0, 99.0)),
    }
    record = ordering_record(readings, form="unpacked")
    assert record["identical_in_every_round"] is True
    assert record["pairs_that_changed_places"] == []


def test_a_pair_can_hold_in_every_round_and_still_not_be_separated():
    """⛔ The distinction the second run forced. `held` is not a claim about a re-run.

    ⭐ Two rungs four per cent apart, never once out of order, and still inside the margin —
    so the artifact reports them as ordered *in this run* and not as an ordering a re-run is
    expected to see. Measured on the real ladder, pairs of exactly this kind changed places
    between two runs at one commit.
    """
    readings = {
        ("cheap", "unpacked"): _reading("cheap", "unpacked", (100.0, 100.0, 100.0)),
        ("barely_dearer", "unpacked"): _reading("barely_dearer", "unpacked", (104.0,) * 3),
        ("clearly_dearer", "unpacked"): _reading("clearly_dearer", "unpacked", (400.0,) * 3),
    }
    record = ordering_record(readings, form="unpacked", margin=SEPARATION_MARGIN)
    assert record["pairs_that_held_in_every_round"] == 3
    assert record["pairs_separated_by_the_margin"] == 2
    assert ["cheap", "barely_dearer"] not in record["separated_pairs"]
    assert ["cheap", "clearly_dearer"] in record["separated_pairs"]


def test_the_separated_set_is_a_subset_of_the_set_that_held():
    ledger = Ledger()
    ops = [_op(ledger, "a", 3), _op(ledger, "b", 5), _op(ledger, "c", 50)]
    readings = _run(ops, ledger)
    for form in CALL_FORMS:
        record = ordering_record(readings, form=form)
        assert record["pairs_separated_by_the_margin"] <= record["pairs_that_held_in_every_round"]
        assert record["pairs_that_held_in_every_round"] <= record["pairs_compared"]


def test_separation_uses_the_worst_round_not_the_typical_one():
    """⚠ One round out of the margin disqualifies the pair; a median would hide it."""
    readings = {
        ("cheap", "unpacked"): _reading("cheap", "unpacked", (100.0, 100.0, 100.0)),
        ("dear", "unpacked"): _reading("dear", "unpacked", (200.0, 200.0, 105.0)),
    }
    assert separated_pairs(readings, form="unpacked", margin=1.10) == []
    assert ordering_record(readings, form="unpacked")["pairs_that_held_in_every_round"] == 1


# --------------------------------------------------------------------------------------
# ⛔ A file that cannot regenerate has to measure what it does reproduce
# --------------------------------------------------------------------------------------


def test_a_second_traversal_identical_to_the_first_reports_no_movement():
    readings = {
        ("a", "unpacked"): _reading("a", "unpacked", (10.0, 12.0)),
        ("b", "unpacked"): _reading("b", "unpacked", (40.0, 44.0)),
    }
    record = reproduction_record(
        readings,
        readings,
        [("b", "a", "unpacked", None)],
        ordering_forms=["unpacked"],
        what_was_checked="one ratio",
    )
    assert record["ratios_checked"] == 1
    assert record["ratios_whose_second_median_fell_inside_the_first_per_round_interval"] == 1
    assert record["largest_movement_of_a_median"] == 0.0
    assert record["ordering"][0]["separated_in_the_first_and_not_the_second"] == []


def test_a_second_traversal_landing_outside_the_first_interval_is_counted_as_outside():
    """⭐ The check has to be able to fail, or reporting that it passed says nothing."""
    first = {
        ("a", "unpacked"): _reading("a", "unpacked", (10.0, 10.0)),
        ("b", "unpacked"): _reading("b", "unpacked", (40.0, 40.0)),
    }
    second = {
        ("a", "unpacked"): _reading("a", "unpacked", (10.0, 10.0)),
        ("b", "unpacked"): _reading("b", "unpacked", (90.0, 90.0)),
    }
    record = reproduction_record(
        first,
        second,
        [("b", "a", "unpacked", None)],
        ordering_forms=["unpacked"],
        what_was_checked="one ratio",
    )
    assert record["ratios_whose_second_median_fell_inside_the_first_per_round_interval"] == 0
    assert record["largest_movement_of_a_median"] == pytest.approx(1.25)


def test_a_pair_that_stopped_being_separated_is_named_not_merely_counted():
    first = {
        ("a", "unpacked"): _reading("a", "unpacked", (10.0, 10.0)),
        ("b", "unpacked"): _reading("b", "unpacked", (40.0, 40.0)),
    }
    second = {
        ("a", "unpacked"): _reading("a", "unpacked", (10.0, 10.0)),
        ("b", "unpacked"): _reading("b", "unpacked", (10.2, 10.2)),
    }
    record = reproduction_record(
        first,
        second,
        [("b", "a", "unpacked", None)],
        ordering_forms=["unpacked"],
        what_was_checked="one ratio",
    )
    assert record["ordering"][0]["separated_in_the_first_and_not_the_second"] == [["a", "b"]]


# --------------------------------------------------------------------------------------
# Control 1 — identical against identical must read as no difference
# --------------------------------------------------------------------------------------


def test_the_null_control_holds_for_two_readings_of_one_operation():
    ledger = Ledger()
    ops = [_op(ledger, ANCHOR, 4), _op(ledger, NULL_TWIN, 4)]
    control = control_null(_run(ops, ledger), left=ANCHOR, right=NULL_TWIN)
    assert control.passed
    assert all(value == 1.0 for value in control.measured["median_ratio_per_form"].values())


def test_the_null_control_fails_when_the_two_readings_do_not_agree():
    """⭐ The control that would catch a harness reporting a difference it manufactured."""
    ledger = Ledger()
    ops = [_op(ledger, ANCHOR, 4), _op(ledger, NULL_TWIN, 9)]
    control = control_null(_run(ops, ledger), left=ANCHOR, right=NULL_TWIN)
    assert not control.passed


# --------------------------------------------------------------------------------------
# Control 2 — a comparator at every arity a binding is measured at
# --------------------------------------------------------------------------------------


def test_the_comparator_control_holds_for_the_standard_ladder_plus_a_binding_rung():
    ledger = Ledger()
    ops = standard_operations() + [
        _op(ledger, "binding_arity_1", 9, arity=1, callee_kind="binding")
    ]
    control = control_same_arity_stdlib(ops)
    assert control.passed
    assert control.measured["binding_arities"] == [1]


def test_the_comparator_control_fails_at_an_arity_nothing_else_was_measured_at():
    """⛔ Without a same-arity comparator the interpreter's cost is charged to the binding."""
    ledger = Ledger()
    ops = [
        _op(ledger, "python_arity_0", 4),
        _op(ledger, "stdlib_c_arity_0", 4, callee_kind="stdlib_c"),
        _op(ledger, "binding_arity_4", 9, arity=4, callee_kind="binding"),
    ]
    control = control_same_arity_stdlib(ops)
    assert not control.passed
    assert control.measured["binding_arities_without_a_pure_python_comparator"] == [4]
    assert control.measured["binding_arities_without_a_stdlib_c_comparator"] == [4]


# --------------------------------------------------------------------------------------
# Control 3 — an expected difference is the control
# --------------------------------------------------------------------------------------


def test_a_pair_built_to_differ_is_reported_as_differing():
    ledger = Ledger()
    ops = [_op(ledger, ANCHOR, 4), _op(ledger, HEAVY, 4 * HEAVY_MULTIPLE)]
    control = control_expected_difference(_run(ops, ledger), heavy=HEAVY, light=ANCHOR)
    assert control.passed
    assert set(control.measured["median_ratio_per_form"].values()) == {
        float(HEAVY_MULTIPLE)
    }


def test_a_harness_that_reports_no_difference_fails_the_expected_difference_control():
    """⭐ A null control alone is satisfied by a harness that measures nothing at all."""
    ledger = Ledger()
    ops = [_op(ledger, ANCHOR, 4), _op(ledger, HEAVY, 4)]
    control = control_expected_difference(_run(ops, ledger), heavy=HEAVY, light=ANCHOR)
    assert not control.passed


# --------------------------------------------------------------------------------------
# Control 4 — distinct arguments must cost nothing by themselves
# --------------------------------------------------------------------------------------


def _sequence_rung(ledger: Ledger, name: str, fn, arity: int, repetitions: int = 8):
    return SequenceRung(
        id=name,
        callee_kind="pure_python",
        callee="a synthetic callable",
        does="charges against the ledger",
        fn=fn,
        arity=arity,
        repetitions=repetitions,
        argument_at=lambda i: tuple(float(i) + j for j in range(arity)),
    )


def test_the_mechanism_control_holds_where_the_callee_cannot_be_sensitive():
    ledger = Ledger()
    rungs = [
        _sequence_rung(ledger, name, ledger.spender(5, arity), arity)
        for name, arity in zip(MECHANISM_CONTROL_RUNGS, (1, 3, 4))
    ]
    readings = _run([], ledger, sequence_rungs=rungs)
    control = control_sequence_mechanism(readings, insensitive=MECHANISM_CONTROL_RUNGS)
    assert control.passed
    assert set(control.measured["median_ratio_per_rung"].values()) == {1.0}


def test_the_mechanism_control_fails_if_distinct_arguments_cost_anything_by_themselves():
    ledger = Ledger()
    rungs = [
        _sequence_rung(
            ledger,
            MECHANISM_CONTROL_RUNGS[0],
            ledger.cacher(repeat_cost=2, fresh_cost=20, arity=1),
            1,
            repetitions=30,
        )
    ]
    readings = _run([], ledger, sequence_rungs=rungs)
    control = control_sequence_mechanism(
        readings, insensitive=(MECHANISM_CONTROL_RUNGS[0],)
    )
    assert not control.passed


# --------------------------------------------------------------------------------------
# ⛔ A repeated call is not a repeated computation
# --------------------------------------------------------------------------------------


def test_a_callee_that_answers_a_repeated_request_cheaply_is_seen_to_do_so():
    """⭐ The finding, in synthetic form: one loop, two runs, an order of magnitude apart."""
    ledger = Ledger()
    rung = _sequence_rung(
        ledger,
        "cacher",
        ledger.cacher(repeat_cost=1, fresh_cost=30, arity=1),
        1,
        repetitions=30,
    )
    readings = _run([], ledger, sequence_rungs=[rung])
    sensitivity = ratio(
        readings,
        numerator="cacher",
        denominator="cacher",
        form="distinct_requests",
        denominator_form="one_request_repeated",
    )
    # ⚠ Not exactly thirty: the first call of each run is charged against whatever the
    #   previous run left behind, and that is the honest arithmetic rather than a defect.
    assert sensitivity.median > 5.0
    assert len(set(sensitivity.per_round)) == 1, "the synthetic callee is deterministic"


def test_a_callee_indifferent_to_which_request_it_is_asked_reads_the_same_both_ways():
    ledger = Ledger()
    rung = _sequence_rung(ledger, "steady", ledger.spender(11, 1), 1)
    readings = _run([], ledger, sequence_rungs=[rung])
    for variant in SEQUENCE_VARIANTS:
        assert readings[("steady", variant)].median_nanoseconds == 11.0


def test_a_run_built_as_distinct_that_is_not_distinct_is_refused():
    """⛔ Otherwise the repeated case is measured under the distinct one's name."""
    ledger = Ledger()
    rung = SequenceRung(
        id="not_really_distinct",
        callee_kind="pure_python",
        callee="a synthetic callable",
        does="charges against the ledger",
        fn=ledger.spender(3, 1),
        arity=1,
        repetitions=8,
        argument_at=lambda i: (1.0,),
    )
    with pytest.raises(TimingHarnessError, match="not distinct"):
        build_sequences(rung)


def test_both_variants_are_the_same_length_and_hold_the_same_first_request():
    ledger = Ledger()
    rung = _sequence_rung(ledger, "rung", ledger.spender(3, 1), 1, repetitions=6)
    built = build_sequences(rung)
    assert len(built["one_request_repeated"]) == len(built["distinct_requests"]) == 6
    assert built["one_request_repeated"][0] == built["distinct_requests"][0]
    assert len(set(built["one_request_repeated"])) == 1


def test_an_arity_zero_rung_cannot_be_measured_over_a_run_of_requests():
    """⚠ It has exactly one possible request, so the two variants are the same run."""
    ledger = Ledger()
    with pytest.raises(TimingHarnessError, match="one possible request"):
        SequenceRung(
            id="nothing_to_vary",
            callee_kind="pure_python",
            callee="a synthetic callable",
            does="charges against the ledger",
            fn=ledger.spender(3, 0),
            arity=0,
            repetitions=4,
            argument_at=lambda i: (),
        )


# --------------------------------------------------------------------------------------
# The refusal the generator depends on
# --------------------------------------------------------------------------------------


def test_a_failed_control_stops_everything_and_names_itself():
    held = Control(
        id="held",
        question="?",
        expectation="1",
        measured={"value": 1},
        passed=True,
        why_it_matters="-",
    )
    failed = Control(
        id="did_not_hold",
        question="?",
        expectation="1",
        measured={"value": 9},
        passed=False,
        why_it_matters="-",
    )
    refuse_unless_all_pass([held])
    with pytest.raises(ControlFailure, match="did_not_hold"):
        refuse_unless_all_pass([held, failed])


def test_a_control_row_carries_what_it_measured_and_not_only_its_verdict():
    control = Control(
        id="c",
        question="q",
        expectation="e",
        measured={"value": 2},
        passed=False,
        why_it_matters="w",
    )
    row = control.as_row()
    assert row["finding"] == "control"
    assert row["held"] is False
    assert row["measured"] == {"value": 2}


# --------------------------------------------------------------------------------------
# The standard ladder's own shape
# --------------------------------------------------------------------------------------


def test_the_standard_ladder_carries_a_comparator_at_every_arity_it_measures():
    ops = standard_operations()
    arities = {op.arity for op in ops if op.arity is not None}
    for kind in ("pure_python", "stdlib_c"):
        assert {op.arity for op in ops if op.callee_kind == kind} >= arities - {None}


def test_the_heavy_control_performs_the_light_one_by_construction():
    """⚠ The expected ratio is a property of the construction, not a number chosen."""
    ops = {op.id: op for op in standard_operations()}
    ledger = Ledger()
    counted = 0

    def counting() -> None:
        nonlocal counted
        counted += 1

    import saakshi.timing as timing

    original = timing._pure_arity_0
    timing._pure_arity_0 = counting
    try:
        ops[HEAVY].fn()
    finally:
        timing._pure_arity_0 = original
    assert counted == HEAVY_MULTIPLE


def test_the_null_twin_holds_the_same_callable_and_arguments_as_the_anchor():
    ops = {op.id: op for op in standard_operations()}
    assert ops[NULL_TWIN].fn is ops[ANCHOR].fn
    assert ops[NULL_TWIN].args == ops[ANCHOR].args
    assert ops[NULL_TWIN].repetitions == ops[ANCHOR].repetitions


def test_the_mechanism_control_rungs_all_exist_in_the_standard_run_of_requests():
    ids = {rung.id for rung in standard_sequence_rungs()}
    assert set(MECHANISM_CONTROL_RUNGS) <= ids


# --------------------------------------------------------------------------------------
# The real clock, asserted for its properties rather than its speed
# --------------------------------------------------------------------------------------


def test_the_measured_step_is_a_positive_advance_this_clock_really_made():
    step = clock_step_ns(samples=20)
    assert step > 0


def test_the_clock_record_states_the_consequence_of_its_own_coarseness():
    record = clock_record(samples=20)
    assert record["clock"] == "perf_counter_ns"
    assert record["measured_step_nanoseconds"] > 0
    assert record["reported_resolution_nanoseconds"] > 0
    assert "no individual call was timed" in record["consequence"]


def test_the_clock_the_harness_names_is_the_clock_it_uses():
    assert clock_record(samples=5)["clock"] == "perf_counter_ns"
    assert time.get_clock_info("perf_counter").monotonic is True
