"""The conventions an ephemeris library applies without being asked.

Five questions, each answered by interrogating the library rather than by reading about it,
and each written out as its own fixture:

1. **the time offset** it applies to reach the dynamical scale, and whether that offset
   moves with an argument that names a source of *positions*;
2. **what a default position already has applied to it**, measured one term at a time;
3. ⭐ **which atmosphere a rise/set call uses when both atmospheric arguments are zero** —
   the convention a sunrise-based calendar rests on entirely;
4. **the leap seconds it knows**, where its table ends, and whether that table can be
   replaced from disk;
5. **which house methods refuse above the polar circle**, at exactly which latitude, and
   whether the refusal names what happened.

⛔ **Recorder, never explainer.** Every row is something a call returned. Nothing here says
any answer is correct — only that this library, at this version, under these flags,
returned it.

⚠ **Everything is `reference_only`.** These are one implementation's conventions. A
consumer that decides to adopt one, or to hold its own within some band of one, is making a
reviewed decision that this repository has no standing to make for it.
"""

from __future__ import annotations

import argparse
import shutil
import sys
import tempfile
from importlib.metadata import version as _distribution_version
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import swisseph as swe  # noqa: E402

from saakshi.conventions import (  # noqa: E402
    APPARENT_VARIANTS,
    ATMOSPHERES,
    HOUSE_SYSTEM_CONTROLS,
    HOUSE_SYSTEM_LETTERS,
    LEAP_SECOND_ENTRY_POINT,
    RISE_DEFINITIONS,
    NU_DOT_ADJUSTMENT_ENDS,
    SURVIVAL_LIMIT,
    SURVIVAL_TEST,
    TABULATED_SOURCE_CHANGES,
    Boundary,
    interval_edges,
    apparent_variants,
    atmosphere_equivalence,
    bracket_epochs,
    classify_boundaries,
    CONFIGURATION_CONTROL,
    DELTA_T_COMPARED_SECTION,
    DELTA_T_SECTIONS,
    DeltaTReading,
    boundary_character,
    delta_t_basis,
    delta_t_cause_controls,
    delta_t_classification,
    delta_t_sufficiency_controls,
    delta_t_flag_rows,
    delta_t_rows,
    delta_t_session_identity,
    measure_delta_t,
    mid_interval_epochs,
    unbounded_interval_coverage,
    global_state_records,
    house_system_survey,
    leap_override_probe,
    constant_offset_handover,
    leap_second_table,
    leap_table_bounds,
    polar_house_probe,
    refraction_probe,
    refusal_boundary,
    refusal_message,
    second_sixty_acceptance,
    system_class_records,
)
from saakshi.fixture import Header, bits, describe_reserved_names, write_jsonl  # noqa: E402
from saakshi.provenance import generator_for, host_record, today  # noqa: E402
from saakshi.swiss import (  # noqa: E402
    MODES,
    Mode,
    Session,
    ephe_set_identity,
    offset_epochs,
    verify_ephe_set,
)

BINDING_VERSION = _distribution_version("pyswisseph")

#: ⚠ Every fixture here maps to the same budget row. These are five questions about one
#: subject — what the library assumes when nobody says — and splitting them across rows
#: would suggest five independent bands, which is the opposite of the point.
BUDGET_ROW = "R3-convention"

# --------------------------------------------------------------------------------------
# The grids
# --------------------------------------------------------------------------------------

#: ⭐ The three epochs the time-offset question is asked at, one per century boundary. The
#: first is before the modern record, the second is the reference epoch, the third is beyond
#: any measurement — so the third is an extrapolation and the file says so.
DELTA_T_EPOCHS: tuple[tuple[str, str, int, int, int], ...] = (
    ("year_1900", "before_the_modern_record", 1900, 1, 1),
    ("year_2000", "reference_epoch", 2000, 1, 1),
    ("year_2100", "beyond_any_measurement", 2100, 1, 1),
)

#: ⭐ The dates the predecessor's own documentation makes conflicting statements about. Each
#: is bracketed rather than sampled: see the section on switchovers in `saakshi.conventions`
#: for why three round-number epochs cannot discriminate between the conflicting accounts.
#:
#: ⛔ These are the dates the *documentation* disputes, not dates this repository asserts are
#: real. Whether any of them is observable at all is the measurement.
#:
#: ⭐ Each carries what the documentation says changes there. Three are three statements of
#: ONE date — where the tidal-acceleration adjustment of earlier values stops — and 1974 is a
#: separate change of the tabulated values' source, which the survival test cannot see.
DELTA_T_BOUNDARIES: tuple[Boundary, ...] = (
    Boundary("switch_1948_01_01", 1948, 1, 1, NU_DOT_ADJUSTMENT_ENDS),
    Boundary("switch_1955_01_01", 1955, 1, 1, NU_DOT_ADJUSTMENT_ENDS),
    Boundary("switch_1955_12_01", 1955, 12, 1, NU_DOT_ADJUSTMENT_ENDS),
    Boundary("switch_1974_01_01", 1974, 1, 1, TABULATED_SOURCE_CHANGES),
)

#: Epochs for the position and house questions. ⚠ **Not J2000 alone**: at the reference
#: epoch the frame term is identically zero, so a sweep taken only there would report that
#: referring a position to a fixed frame changes nothing — which is true at that instant and
#: false everywhere else. A grid that hides a term is worse than a smaller one.
POSITION_EPOCHS: tuple[tuple[str, str, int, int, int, float], ...] = (
    ("epoch_2000", "reference_epoch", 2000, 1, 1, 12.0),
    ("epoch_1900", "a century before", 1900, 1, 1, 0.0),
    ("epoch_2026", "the present", 2026, 3, 20, 6.0),
    ("epoch_2100", "a century after", 2100, 1, 1, 0.0),
)

#: The bodies the position sweep covers. ⭐ The light source of the system, the fastest body
#: and a distant one: the three that separate the terms being measured.
POSITION_BODIES: tuple[tuple[int, str], ...] = (
    (swe.SUN, "sun"),
    (swe.MOON, "moon"),
    (swe.JUPITER, "jupiter"),
)

#: Where the rise/set question is asked. ⭐ Spread in latitude on purpose: a rise/set
#: convention expressed as a single number is set by its worst latitude, and the same
#: convention costs different amounts of time at different ones.
RISE_SITES: tuple[tuple[str, float, float, str], ...] = (
    ("north_inland", 26.4499, 80.3319, "northern subtropics, inland"),
    ("equatorial", -1.2921, 36.8219, "within two degrees of the equator"),
    ("southern_mid", -36.8485, 174.7633, "southern mid-latitude"),
    ("sub_polar", 64.1466, -21.9426, "just below the polar circle"),
    ("polar", 78.2232, 15.6267, "above the polar circle"),
)

#: Dates the rise/set question is asked on: an equinox, both solstices, and one ordinary
#: date, so the answer is not read off a single point of the year.
RISE_DATES: tuple[tuple[str, str, int, int, int], ...] = (
    ("equinox_march", "equinox", 2026, 3, 20),
    ("solstice_june", "solstice", 2026, 6, 21),
    ("solstice_december", "solstice", 2026, 12, 21),
    ("ordinary_day", "ordinary", 1985, 11, 3),
)

#: The years the leap-second scan walks. ⚠ It starts before the first insertion and runs
#: well past the last, because both ends are findings.
LEAP_FIRST_YEAR, LEAP_LAST_YEAR = 1961, 2060

#: ⭐ Where the search for the *other* end begins: a date measured to be inside the region
#: where the conversion holds one constant offset, safely past the last insertion. The
#: search runs forward from here for the span below.
HANDOVER_SEARCH_FROM = (2020, 1, 1)
HANDOVER_SEARCH_YEARS = 60

#: Dates the sixty-first second is offered on: two the table is expected to know, and two it
#: cannot — one in the past, one in the future.
SECOND_SIXTY_DATES: tuple[tuple[int, int, int], ...] = (
    (2016, 12, 31),
    (2015, 6, 30),
    (2017, 6, 30),
    (2026, 6, 30),
)

#: An invented insertion date for the override probe. ⛔ Deliberately one the real table does
#: not contain, so a change in the answer can only have come from the file.
OVERRIDE_DATE = (2020, 6, 30)
OVERRIDE_FILE_NAME = "seleapsec.txt"
OVERRIDE_PROBE_YEAR = (2021, 1, 1)

#: Latitudes the house sweep visits, straddling the circle where two methods stop.
HOUSE_LATITUDES: tuple[float, ...] = (0.0, 45.0, 60.0, 66.0, 66.6, 67.0, 78.0, 89.0, -78.0)

#: The meridian the house sweep uses. ⛔ A label-free number: the question is latitude.
HOUSE_LONGITUDE = 15.0

#: A latitude at which the methods that refuse, refuse — for the message comparison.
HOUSE_REFUSAL_LATITUDE = 78.0

#: ⭐ The (instant, latitude) pairs the method-identity survey compares over. **Several, and
#: unrelated**: two methods that genuinely differ can coincide at one instant and one
#: latitude, and a survey taken at a single sample would merge them into one class and call
#: it an alias. Four samples, spread in season, century and latitude.
HOUSE_SURVEY_SAMPLES: tuple[tuple[float, float], ...] = (
    (swe.julday(2026, 3, 20, 6.0), 45.0),
    (swe.julday(2026, 6, 21, 18.0), 12.0),
    (swe.julday(1900, 1, 1, 3.0), 55.0),
    (swe.julday(2100, 9, 9, 21.0), -33.0),
)


def _epochs(rows: tuple[tuple[str, str, int, int, int], ...]) -> list[tuple[str, str, float]]:
    return [(eid, stratum, swe.julday(y, m, d, 0.0)) for eid, stratum, y, m, d in rows]


def _epochs_with_hour(
    rows: tuple[tuple[str, str, int, int, int, float], ...]
) -> list[tuple[str, str, float]]:
    return [(eid, stratum, swe.julday(y, m, d, h)) for eid, stratum, y, m, d, h in rows]


# --------------------------------------------------------------------------------------
# Shared header parts
# --------------------------------------------------------------------------------------


def _oracle(mode: Mode | None, ephe: dict[str, Any] | None, session: Session) -> dict[str, Any]:
    oracle: dict[str, Any] = {
        "implementation": "Swiss Ephemeris",
        "library_version": swe.version,
        "called_via": {"binding": "pyswisseph", "version": BINDING_VERSION},
        "session": session.identity(),
        "licence": (
            "the library is AGPL-3.0; it is called here, never redistributed by this "
            "repository"
        ),
        "host": host_record(),
    }
    if mode is not None:
        oracle["ephemeris_requested"] = mode.source
        oracle["ephemeris_requested_note"] = mode.label
    if ephe is not None:
        oracle["data_files"] = ephe
    return oracle


def _classification(sections: list[str]) -> dict[str, dict[str, str]]:
    # ⛔ `reference_only` everywhere, and it is the honest class: nothing here has been
    #    compared against an authority, so there is no band to declare. A consumer that
    #    measures its own residual against these rows is what would create one.
    return {section: {"class": "reference_only"} for section in sections}


def _write(
    *,
    name: str,
    title: str,
    rows: list[dict[str, Any]],
    request: dict[str, Any],
    oracle: dict[str, Any],
    row_schema: dict[str, str],
    notes: list[str],
    summary: dict[str, Any],
    out_dir: Path,
    script: Path,
    classification: dict[str, dict[str, str]] | None = None,
    budget_row: str = BUDGET_ROW,
) -> tuple[Path, int]:
    sections = sorted({str(row["section"]) for row in rows})
    header = Header(
        fixture_kind="numeric_pin",
        reference="R3",
        generator=generator_for(script),
        generated=today(),
        title=title,
        oracle=oracle,
        request=request,
        classification=(
            classification if classification is not None else _classification(sections)
        ),
        budget_row=budget_row,
        row_schema=row_schema,
        summary={
            **summary,
            "rows": len(rows),
            "rows_by_section": {
                section: sum(1 for row in rows if row["section"] == section)
                for section in sections
            },
        },
        notes=notes,
    )
    path = out_dir / "conventions" / f"{name}.jsonl"
    return path, write_jsonl(path, header, rows, declared_sections=sections)


_COMMON_SCHEMA: dict[str, str] = {
    "section": "which question within this file the row answers",
    "epoch_id": "stable id of the epoch within this grid",
    "stratum": "why this epoch is in the grid",
    "jd_ut": "Julian day, Universal Time — ⚠ display; `jd_ut_bits` is the value",
    "jd_ut_bits": "⭐ IEEE-754 bit pattern; the authoritative form of the input",
    "utc": "the same instant as a calendar string, for reading",
    "unit": "the unit of every component of `values`",
    "values": "⚠ display decimals; `values_bits` is the authoritative form",
    "values_bits": "⭐ IEEE-754 bit patterns of the same components",
    "value_labels": "what each component of `values` is, where there is more than one",
    "source_assertion": (
        "⭐ how this row's ephemeris was established. `reported` where the entry point "
        "returned a source flag; `proxy_window` where it did not and the source was "
        "asserted at both ends of the interval the call may read"
    ),
}

_BITS_NOTE = (
    "⛔ Every determinism-bearing double carries a hex bit pattern, and the decimal beside "
    "it is display. ⚠ A widely-used JSON library was measured mis-parsing 18.9% of "
    "shortest-round-tripping doubles by up to 2 ULP. ⭐ The inputs matter most: an output "
    "is compared, an input is replayed."
)

_REFERENCE_ONLY_NOTE = (
    "⛔ `reference_only` throughout. A convention this library applies is not thereby the "
    "right convention, and a difference between two of the rows here is a difference "
    "between two conventions rather than an error in either."
)


# --------------------------------------------------------------------------------------
# 1. the time offset
# --------------------------------------------------------------------------------------


#: ⭐ The budget row the compared section names. ⛔ Not the convention row every other file here
#: shares: a configuration admitted for comparison is judged against a row that names exactly
#: one configuration, and the consumer that judges it mints that row. This name is this file's
#: proposal for it, and nothing here asserts the row exists.
#:
#: ⚠ Named for the registry entry it verifies, not for its role: a role name ("the continuity
#: row") is a referent that moves the day a second continuity target arrives, and a row id is
#: permanent. It replaces the earlier proposal `delta-t-continuity` at the consumer's request.
DELTA_T_BUDGET_ROW = "swiss-ephemeris-match-1"


def _measure(epochs: list[tuple[str, str, float]], session: Session) -> list[DeltaTReading]:
    return measure_delta_t(
        epochs, ephe_path=session.ephe_path, sidereal_mode=session.sidereal_mode
    )


def write_delta_t(
    *, session: Session, ephe: dict[str, Any], out_dir: Path, script: Path
) -> list[tuple[Path, int]]:
    # ⭐ Two stages, because the second grid is a function of what the first measured. The
    #   century pins and the brackets are taken together; only then is it known which
    #   disputed dates are real, and therefore which intervals need a reading of their own.
    #   ⚠ Each stage is one fresh process, so a stage-two reading follows no stage-one call.
    century = _epochs(DELTA_T_EPOCHS)
    brackets = bracket_epochs(DELTA_T_BOUNDARIES)
    readings = _measure(century + brackets, session)

    verdicts = classify_boundaries(DELTA_T_BOUNDARIES, delta_t_flag_rows(readings))
    intervals = mid_interval_epochs(DELTA_T_BOUNDARIES, verdicts)
    coverage = unbounded_interval_coverage(DELTA_T_BOUNDARIES, verdicts, century)
    if intervals:
        readings = readings + _measure(intervals, session)

    epochs = century + brackets + intervals
    rows = delta_t_rows(readings)
    flag_rows = delta_t_flag_rows(readings)
    moved = [row for row in flag_rows if row["spread_seconds"] != 0.0]
    oracle = {
        **_oracle(None, ephe, session),
        "session": delta_t_session_identity(sidereal_mode=session.sidereal_mode),
        "ephemeris_basis": delta_t_basis(
            ephe=ephe,
            library_version=swe.version,
            binding="pyswisseph",
            binding_version=BINDING_VERSION,
            sidereal_mode=session.sidereal_mode,
        ),
    }
    written = _write(
        name="time-offset",
        title="What the library adds to a civil instant to reach the dynamical scale",
        rows=rows,
        classification=delta_t_classification(),
        budget_row=DELTA_T_BUDGET_ROW,
        request={
            "epochs": [
                {"epoch_id": eid, "stratum": stratum, "jd_ut": jd, "jd_ut_bits": bits(jd)}
                for eid, stratum, jd in epochs
            ],
            "entry_points": sorted({section.entry_point for section in DELTA_T_SECTIONS}),
            "disputed_switchovers": [
                {
                    "boundary_id": b.boundary_id,
                    "date": f"{b.year:04d}-{b.month:02d}-{b.day:02d}",
                    "jd_ut": b.jd,
                    "jd_ut_bits": bits(b.jd),
                }
                for b in DELTA_T_BOUNDARIES
            ],
            "grid_derivation": (
                "⚠ the mid-interval epochs are DERIVED, not declared: the disputed dates are "
                "bracketed first, and a date bounds an interval if the test observed a change "
                "across it, or if the change its documentation names is one the test cannot "
                "observe — its silence refutes nothing. Only the intervals those dates "
                "enclose are sampled. The rule is in `summary.switchovers` and the epochs it "
                "produced are all listed above"
            ),
            "regenerate": "generators/convention_probes.py --ephe-path <dir> --out <dir>",
        },
        oracle=oracle,
        row_schema={
            **_COMMON_SCHEMA,
            "section": (
                "one configuration — one entry point under one request: "
                + " | ".join(section.name for section in DELTA_T_SECTIONS)
            ),
            "ephemeris_requested": (
                "the source named in the call's flag — on the sections whose entry point "
                "takes one, and equal to that section's request"
            ),
            "seconds": "the same offset in seconds, for reading; the day value is the value",
            "state_read_back": (
                "⭐ the tidal-acceleration constant in force after the call, read back on "
                "every reading; `value_bits` is the value. It is the state through which an "
                "ephemeris reaches this quantity, and one configuration reads back one "
                "constant"
            ),
            "source_assertion": (
                "⛔ `none` on every row: a refusal to name a source, because no ephemeris "
                "answers this quantity — its `reason` says why"
            ),
        },
        notes=[
            "⭐ THE POINT OF THIS FILE. The entry point takes an argument naming a source of "
            "**positions**, and returns a quantity that is not a position — and at one of "
            "the three century epochs here the answer moves with it. So two callers "
            "converting the same civil instant, differing only in an ephemeris flag chosen "
            "for unrelated reasons, get two different instants and no notice of it.",
            "⭐ ONE SECTION PER CONFIGURATION. Each section is one entry point under one "
            "request, and declares its basis and its whole configuration: the data "
            "directory and every file in it, and the discipline for every process-wide "
            "state the library-state audit measured. ⛔ A row holding several requests' "
            "answers could declare none of them, so the comparison between configurations "
            "is in `summary.flag_dependence`, derived from the sections and never written "
            "as rows.",
            "⛔ NO ROW NAMES A SOURCE. The offset is not read from an ephemeris: the entry "
            "point returns a bare number with no statement of source, and an ephemeris "
            "reaches the value only through the tidal-acceleration constant, which every "
            "row reads back. A position call under the same flag says which ephemeris "
            "answered THAT call, which is a different quantity — so no proxy is asserted, "
            "and none is called.",
            "⚠ ONE SECTION IS CLASSIFIED FOR COMPARISON, AND THE REST ARE NOT. "
            f"`{DELTA_T_COMPARED_SECTION}` is `exact`: what this library returned under that "
            "declared configuration, bit for bit — a statement about the configuration, "
            "never about the Earth and never about which ephemeris the value came from. "
            "⛔ Classifying it does not make it comparable on its own: a consumer that "
            "admits it needs this configuration's controls and a row that names this "
            "configuration, and neither is in this file.",
            "⚠ The entry point returns DAYS. A duration recorded in the wrong unit is the "
            "easiest reproduction failure to make and the hardest to see in a table, so both "
            "forms are written and the day value is the authoritative one.",
            "⛔ The 2100 epoch is beyond any measurement of this quantity: the library "
            "answers, and its answer is a model's extrapolation. Published models disagree "
            "with each other far more at that epoch than any of the differences recorded "
            "here — this file pins what THIS library returns and makes no claim about which "
            "extrapolation is right.",
            "⭐ WHY THE CENTURY EPOCHS ARE NOT ENOUGH, AND WHAT THE BRACKETS ADD. 1900, 2000 "
            "and 2100 sit in three different eras and touch no disputed switchover, so each "
            "of them is consistent with every conflicting account of where the switchovers "
            "are. A reading consistent with both sides of a disputed question has not "
            "discriminated between them. Each disputed date is therefore measured one day "
            "before and one day after, and every interval the bounding dates enclose is "
            "measured in its middle — a date bounds one if a change was observed across it, "
            "or if its documented change is one the test cannot see.",
            "⛔ THE DATE ITSELF IS NOT MEASURED, DELIBERATELY. What is in question is which "
            "side of the date a behaviour lies on, and a reading taken on the date answers "
            "that for neither side.",
            SURVIVAL_LIMIT
            + ". ⚠ So `survives = false` bounds what this instrument can see, and says "
            "nothing about what the library does.",
            _BITS_NOTE,
        ],
        summary={
            "switchovers": {
                "test": SURVIVAL_TEST,
                "limit": SURVIVAL_LIMIT,
                "verdicts": verdicts,
                "observed": sorted(v["boundary_id"] for v in verdicts if v["survives"]),
                "not_observed": sorted(
                    v["boundary_id"] for v in verdicts if not v["survives"]
                ),
                "interval_edges": [
                    b.boundary_id for b in interval_edges(DELTA_T_BOUNDARIES, verdicts)
                ],
                "interval_edge_rule": (
                    "a date bounds an interval if a change was observed across it, or if its "
                    "documented change is one this test cannot observe. ⛔ An unobserved date "
                    "of the kind this test sees is refuted; one of a kind it cannot see is "
                    "not, because its silence is the limit above and not a measurement"
                ),
                "intervals_sampled_in_the_middle": [eid for eid, _s, _jd in intervals],
                "unbounded_intervals": coverage,
            },
            "flag_dependence": [
                {
                    "epoch_id": row["epoch_id"],
                    **boundary_character(row),
                    "spread_seconds": row["spread_seconds"],
                }
                for row in flag_rows
            ],
            "epochs_where_the_flag_changed_the_answer": [
                {
                    "epoch_id": row["epoch_id"],
                    "spread_seconds": row["spread_seconds"],
                    "unflagged_equals": row["unflagged_equals"],
                }
                for row in moved
            ],
            "meaning": (
                "⭐ a non-empty list here is the finding: at those epochs the time scale is "
                "a function of an argument about positions"
            ),
        },
        out_dir=out_dir,
        script=script,
    )
    controls = write_delta_t_controls(
        readings=readings, basis=oracle["ephemeris_basis"], session=session, ephe=ephe,
        out_dir=out_dir, script=script,
    )
    return [written, controls]


def write_delta_t_controls(
    *,
    readings: list[DeltaTReading],
    basis: dict[str, Any],
    session: Session,
    ephe: dict[str, Any],
    out_dir: Path,
    script: Path,
) -> tuple[Path, int]:
    """The two controls on the compared section's configuration, as a provenance record."""
    cause, not_controlled = delta_t_cause_controls(
        readings,
        compared=DELTA_T_COMPARED_SECTION,
        basis=basis,
        survey_epochs=offset_epochs(),
        ephe_path=session.ephe_path,
        sidereal_mode=session.sidereal_mode,
    )
    sufficiency = delta_t_sufficiency_controls(
        readings,
        compared=DELTA_T_COMPARED_SECTION,
        basis=basis,
        ephe_path=session.ephe_path,
        sidereal_mode=session.sidereal_mode,
    )
    rows = cause + sufficiency
    identity = rows[0]["configuration_sha256"] if rows else None
    header = Header(
        fixture_kind="provenance_record",
        reference="R3",
        generator=generator_for(script),
        generated=today(),
        title=(
            "Whether the time offset follows the one state it is said to follow, and "
            "nothing else"
        ),
        oracle={
            **_oracle(None, ephe, session),
            "session": delta_t_session_identity(sidereal_mode=session.sidereal_mode),
            "method": (
                "the compared section of the time-offset file, under its declared "
                "configuration: the tidal-acceleration constant forced to another constant "
                "this file measured in force and the call made, in a fresh process each; and "
                "the section regenerated in a fresh process with every reading of the file "
                "taken in reverse, and again with each of its readings alone in a process of "
                "its own"
            ),
        },
        attests=(
            "two controls on one declared configuration of the time offset: that forcing the "
            "state its value is said to follow moves the value, and that regenerating the "
            "section under other call histories does not"
        ),
        authority={
            "held_by": "the library itself, as observed",
            "kind": (
                "direct observation under a forced state, and under permuted and isolated "
                "call histories"
            ),
            "scope": (
                "⚠ this version of the library and this binding, and only the one "
                "configuration every row names by its identity"
            ),
        },
        record_date=today(),
        row_schema={
            "finding": CONFIGURATION_CONTROL,
            "control": "cause | sufficiency",
            "entry_point": "the entry point of the controlled section",
            "configuration_sha256": (
                "⭐ the controlled section's configuration identity, computed from its "
                "declared configuration and never typed"
            ),
            "epoch_id": "the controlled section's epoch the row speaks for",
            "state": "cause: the state forced — the one the section reads back",
            "forced_value": "cause: the constant forced; `forced_value_bits` is the value",
            "read_back_after_call": (
                "cause: the constant read back after the call. ⛔ Where it differs from the "
                "forced value the call overwrote it, and the control is void — written as "
                "measured"
            ),
            "baseline_value": "cause: the section's own value at that epoch",
            "value": "cause: what the call returned with the constant forced",
            "call_history": "sufficiency: permuted | cold_process_per_row",
            "call_order": "sufficiency, permuted: the section's epochs in the order called",
            "values": "sufficiency: what the regeneration returned; `values_bits` is the value",
        },
        summary={
            "controlled_section": DELTA_T_COMPARED_SECTION,
            "controlled_file": "conventions/time-offset.jsonl",
            "configuration_sha256": identity,
            "cause": {"rows": len(cause), "not_controlled": not_controlled},
            "sufficiency": {
                "rows": len(sufficiency),
                "call_histories": sorted({row["call_history"] for row in sufficiency}),
            },
        },
        notes=[
            "⭐ CAUSE. The section reads its constant back on every row; forcing ANOTHER "
            "constant and seeing the value move is what shows the value follows it. It is "
            "placed only where it can fail both ways: at an epoch the offset survey read, so "
            "the survey's readings under the forced constant predict the moved value; with a "
            "constant another configuration of the time-offset file put in force there; and "
            "never where every configuration holding that constant returned the baseline, "
            "because a value that cannot move cannot show anything. `summary.cause."
            "not_controlled` lists what was left out and why.",
            "⭐ SUFFICIENCY. A state nobody has measured would move a value only when the "
            "calls before it change, so the section is regenerated under two other call "
            "histories: every reading of the file in reverse in one fresh process, and each "
            "of the section's readings alone in a process of its own. ⛔ A same-order re-run "
            "is not one of them — this file's byte-identical regeneration is exactly the run "
            "that cannot see such a state.",
            "⛔ MEASURED, NEVER DECLARED. Every control taken is written as taken — a void one, "
            "an unmoved one or a mismatched one included. Whether each passes is decided by "
            "a consumer against the section and the survey, not here.",
            _BITS_NOTE,
        ],
    )
    path = out_dir / "conventions" / "time-offset-controls.jsonl"
    return path, write_jsonl(path, header, rows)


# --------------------------------------------------------------------------------------
# 2. what a default position already carries
# --------------------------------------------------------------------------------------


def write_apparent(
    *, session: Session, ephe: dict[str, Any], out_dir: Path, script: Path
) -> tuple[Path, int]:
    epochs = _epochs_with_hour(POSITION_EPOCHS)
    rows: list[dict[str, Any]] = []
    for mode_id in ("moshier", "swiss_file"):
        rows.extend(apparent_variants(epochs, POSITION_BODIES, MODES[mode_id], session))

    per_variant: dict[str, float] = {}
    for row in rows:
        variant = str(row["variant"])
        per_variant[variant] = max(
            per_variant.get(variant, 0.0), abs(float(row["delta_arcseconds"]))
        )
    return _write(
        name="apparent-position",
        title="What a position returned under default flags already has applied to it",
        rows=rows,
        request={
            "epochs": [
                {"epoch_id": eid, "stratum": stratum, "jd_ut": jd, "jd_ut_bits": bits(jd)}
                for eid, stratum, jd in epochs
            ],
            "bodies": [name for _, name in POSITION_BODIES],
            "variants": [
                {"variant": name, "flag": flag, "note": note}
                for name, flag, note in APPARENT_VARIANTS
            ],
            "method": (
                "the default answer is taken as the reference, and each variant switches one "
                "term off. The difference is that term's size"
            ),
            "regenerate": "generators/convention_probes.py --ephe-path <dir> --out <dir>",
        },
        oracle=_oracle(None, ephe, session),
        row_schema={
            **_COMMON_SCHEMA,
            "section": "variant_delta",
            "body": "the body this row is about",
            "body_number": "the library's own number for that body",
            "variant": "which term was switched off",
            "variant_note": "what switching it off means",
            "delta_arcseconds": (
                "⭐ the size of the term that was removed, in arc-seconds of longitude"
            ),
            "reference_source_assertion": (
                "the source assertion of the DEFAULT call this row is measured against — "
                "⛔ a reference answered by a substituted ephemeris would report the "
                "substitution as an effect size"
            ),
        },
        notes=[
            "⭐ This turns a sentence about what 'apparent' means into a set of numbers. Each "
            "row is one term of the default answer, measured by removing it.",
            "⚠ A ZERO IS NOT AN ABSENCE. The light source of the system reports zero for "
            "gravitational deflection at every epoch while a distant planet reports a real "
            "number — a body is not deflected by its own gravity. Reading that zero as "
            "'deflection is switched off in the default' would be wrong, and the outer "
            "planet's row in the same file is what shows it.",
            "⚠ The frame term is identically zero at the reference epoch and grows away from "
            "it, which is why this grid is not one epoch. A sweep taken only at the "
            "reference epoch reports that the frame choice costs nothing.",
            _BITS_NOTE,
            _REFERENCE_ONLY_NOTE,
        ],
        summary={
            "largest_term_arcseconds": dict(sorted(per_variant.items())),
            "meaning": (
                "the worst case each removed term is worth over this grid, in arc-seconds "
                "of longitude. ⛔ Not an error budget: these are the sizes of terms the "
                "default answer contains, not disagreements with anything"
            ),
        },
        out_dir=out_dir,
        script=script,
    )


# --------------------------------------------------------------------------------------
# 3. ⭐ the atmosphere nobody named
# --------------------------------------------------------------------------------------


def write_refraction(
    *, session: Session, ephe: dict[str, Any], out_dir: Path, script: Path
) -> tuple[Path, int]:
    epochs = _epochs(RISE_DATES)
    rows: list[dict[str, Any]] = []
    for mode_id in ("moshier", "swiss_file"):
        mode = MODES[mode_id]
        rows.extend(
            refraction_probe(
                sites=RISE_SITES,
                epochs=epochs,
                body=swe.SUN,
                body_name="sun",
                mode=mode,
                session=session,
            )
        )
    reference_site = RISE_SITES[0]
    rows.extend(
        atmosphere_equivalence(
            site=(reference_site[2], reference_site[1], 0.0),
            epochs=epochs,
            body=swe.SUN,
            mode=MODES["moshier"],
            session=session,
        )
    )

    identities = [
        row
        for row in rows
        if row["section"] == "atmosphere_equivalence" and row["bit_identical"]
    ]
    identical_candidates = sorted({str(row["candidate"]) for row in identities})
    # ⚠ A list of records, not a keyed object. The natural key here would be the pair
    #   (definition, atmosphere), and a key built by joining two names is neither
    #   lower_snake_case nor a name anything else in the file uses — the contract refuses it,
    #   and widening the contract to admit it would be the wrong repair.
    at_one_site = [
        {
            "event_definition": row["event_definition"],
            "atmosphere": row["atmosphere"],
            "true_altitude_arcminutes": row["true_altitude_arcminutes"],
            "seconds_from_omitted_arguments": row["seconds_from_omitted_arguments"],
        }
        for row in rows
        if row["section"] == "horizon_depression"
        and row["site"] == "north_inland"
        and row["epoch_id"] == "equinox_march"
        and row["ephemeris_requested"] == "moshier"
    ]
    return _write(
        name="rise-refraction",
        title="Which atmosphere a rise/set call uses when both atmospheric arguments are zero",
        rows=rows,
        request={
            "epochs": [
                {"epoch_id": eid, "stratum": stratum, "jd_ut": jd, "jd_ut_bits": bits(jd)}
                for eid, stratum, jd in epochs
            ],
            "sites": [
                {"site": s, "latitude": la, "longitude": lo, "site_label": lab}
                for s, la, lo, lab in RISE_SITES
            ],
            "atmospheres": [
                {
                    "atmosphere": a.id,
                    "atpress": a.atpress,
                    "attemp": a.attemp,
                    "observer_height_m": a.geoalt,
                    "note": a.note,
                }
                for a in ATMOSPHERES
            ],
            "event_definitions": [
                {"event_definition": name, "rsmi": rsmi, "note": note}
                for name, rsmi, note in RISE_DEFINITIONS
            ],
            "body": "sun",
            "method": (
                "the returned event time is converted into a statement about the convention "
                "by computing the body's true altitude at that instant"
            ),
            "regenerate": "generators/convention_probes.py --ephe-path <dir> --out <dir>",
        },
        oracle=_oracle(None, ephe, session),
        row_schema={
            **_COMMON_SCHEMA,
            "section": "horizon_depression | atmosphere_equivalence | no_event",
            "site": "stable id of the place",
            "site_label": "⛔ a label; never an input",
            "latitude": "degrees north — ⚠ display; `latitude_bits` is the value",
            "latitude_bits": "⭐ IEEE-754 bit pattern of the input",
            "longitude": "degrees east — ⚠ display; `longitude_bits` is the value",
            "longitude_bits": "⭐ IEEE-754 bit pattern of the input",
            "event_definition": "which definition of 'risen' the call was asked for",
            "atmosphere": "which pressure, temperature and observer height were passed",
            "atpress": "the pressure argument, as a stated input",
            "attemp": "the temperature argument, as a stated input",
            "observer_height_m": "the observer height in the position argument",
            "event_utc": "the found event as a calendar string, for reading",
            "true_altitude_arcminutes": (
                "⭐ the body's true altitude at the instant the call called it a rising. "
                "This is the convention, in the units conventions are quoted in"
            ),
            "seconds_from_omitted_arguments": (
                "⭐ what this row's convention costs in TIME against the one a caller who "
                "passes nothing gets, at the same place and date"
            ),
            "candidate": "for an equivalence row: the stated atmosphere being tested",
            "bit_identical": (
                "⭐ whether the omitted arguments and the stated atmosphere returned the "
                "very same double. An identity, not a tolerance"
            ),
            "return_code": "the code the call returned when it found no event",
            "time_slot_left_in_place": (
                "⛔ what the call left in the time slot on 'no event' — an ordinary-looking "
                "Julian day, not a sentinel"
            ),
        },
        notes=[
            "⭐ THE QUESTION THIS FILE EXISTS FOR. Passing nothing for pressure and "
            "temperature is neither 'no atmosphere' nor the conventional sea-level "
            "atmosphere. The equivalence rows say which stated atmosphere it actually is, "
            "and they say it as a bit-identity rather than an approximation.",
            "⛔ THE TEMPERATURE IS THE TRAP, NOT THE PRESSURE. The temperature argument is "
            "taken literally — a zero passed for it is zero degrees Celsius, a cold "
            "atmosphere that refracts more than a temperate one, not a stand-in for a "
            "default. Anyone who assumed the conventional pair would be wrong on one half "
            "of it and would move sunrise by a measurable number of seconds.",
            "⚠ AND THE OBSERVER HEIGHT IS LIVE. With the pressure argument at zero the model "
            "still reads the height in the position argument, so a site given an elevation "
            "gets a different sunrise from the same site given none.",
            "⚠ THE SAME QUESTION HAS TWO ANSWERS IN THIS LIBRARY. The entry point that "
            "converts an altitude to a refracted one treats a zero pressure as no "
            "atmosphere and returns exactly zero refraction, while the rise/set entry point "
            "treats it as a real atmosphere. ⛔ So calibrating the rise/set convention "
            "through the refraction entry point returns the wrong answer, confidently.",
            "⭐ The event-definition rows put the disc, the atmosphere and the library's own "
            "named composite on one scale. They differ from each other by minutes, not "
            "seconds — a calendar keyed to a rising inherits whichever one was chosen, and "
            "the choice is usually made by omission.",
            _BITS_NOTE,
            _REFERENCE_ONLY_NOTE,
        ],
        summary={
            "omitted_arguments_are_identical_to": identical_candidates,
            "at_one_temperate_site_on_one_date": at_one_site,
            "meaning": (
                "⭐ the first entry answers the question in the title: the atmosphere a "
                "caller gets by saying nothing is exactly this stated one. The table below "
                "is the convention in altitude and in time, at one temperate site on one "
                "date, so the magnitudes can be read without opening the rows"
            ),
        },
        out_dir=out_dir,
        script=script,
    )


# --------------------------------------------------------------------------------------
# 4. the leap seconds
# --------------------------------------------------------------------------------------


def write_leap_seconds(
    *, session: Session, ephe: dict[str, Any], out_dir: Path, script: Path
) -> tuple[Path, int]:
    steps = leap_second_table(LEAP_FIRST_YEAR, LEAP_LAST_YEAR)
    rows: list[dict[str, Any]] = list(steps)
    rows.extend(leap_table_bounds(LEAP_FIRST_YEAR, LEAP_LAST_YEAR, steps))
    handover = constant_offset_handover(HANDOVER_SEARCH_FROM, HANDOVER_SEARCH_YEARS)
    if handover is not None:
        rows.append(handover)
    rows.extend(second_sixty_acceptance(SECOND_SIXTY_DATES))

    # ⛔ The override probe writes a file, and it writes it in a directory of its own —
    #    never into the pinned data directory, whose every byte is verified before use.
    scratch = Path(tempfile.mkdtemp(prefix="leap-probe-"))
    try:
        with_file = scratch / "with"
        without_file = scratch / "without"
        working = scratch / "working"
        for directory in (with_file, without_file, working):
            directory.mkdir(parents=True, exist_ok=True)
        year, month, day = OVERRIDE_DATE
        entry = f"{year:04d}{month:02d}{day:02d}\n"
        (with_file / OVERRIDE_FILE_NAME).write_text(entry, encoding="ascii")
        (working / OVERRIDE_FILE_NAME).write_text(entry, encoding="ascii")
        rows.extend(
            leap_override_probe(
                directory_with_file=str(with_file),
                directory_without_file=str(without_file),
                working_directory=str(working),
                probe_date=OVERRIDE_PROBE_YEAR,
            )
        )
    finally:
        shutil.rmtree(scratch, ignore_errors=True)

    whole = [row for row in steps if row["is_whole_second"]]
    fractional = [row for row in steps if not row["is_whole_second"]]
    return _write(
        name="leap-seconds",
        title="The leap seconds the library knows, where its table ends, and what replaces it",
        rows=rows,
        request={
            "scan_years": [LEAP_FIRST_YEAR, LEAP_LAST_YEAR],
            "insertion_dates_scanned": ["01-01", "07-01"],
            "second_sixty_dates": [f"{y:04d}-{m:02d}-{d:02d}" for y, m, d in SECOND_SIXTY_DATES],
            "override_file_name": OVERRIDE_FILE_NAME,
            "override_invented_date": "%04d-%02d-%02d" % OVERRIDE_DATE,
            "entry_point": LEAP_SECOND_ENTRY_POINT,
            "method": (
                "the table is extracted by walking the conversion and differencing against "
                "the same calendar instant read as a plain Julian day, which removes the "
                "smooth drift and leaves the steps"
            ),
            "regenerate": "generators/convention_probes.py --ephe-path <dir> --out <dir>",
        },
        oracle={
            **_oracle(None, ephe, session),
            "ephemeris_requested": "none — ⛔ this entry point takes no ephemeris flag at all",
            "source_assertion": (
                "⛔ impossible here, and recorded as impossible rather than omitted. The "
                "conversion accepts no ephemeris flag, so there is nothing to assert and no "
                "substitution it could hide"
            ),
        },
        row_schema={
            "section": "leap_step | table_bound | second_sixty | override",
            "effective_from": "the date at which the step was found",
            "step_seconds": "the size of the discontinuity",
            "is_whole_second": (
                "⚠ whether the step is one second. The era before the table's own regime "
                "steps by fractions, and those rows are kept rather than filtered"
            ),
            "bound": (
                "first_whole_second_step | last_whole_second_step | "
                "constant_offset_handover"
            ),
            "regime": (
                "⭐ which of the three eras a step falls in — decided from the steps already "
                "seen rather than from a hard-coded date, so it stays correct against a "
                "table this scan has never met"
            ),
            "last_date_holding_the_constant": (
                "the last day the offset was still the table's, for the handover row"
            ),
            "date": "the date of that bound, or of the second-sixty offer",
            "accepted": (
                "⭐ whether the conversion accepted the sixty-first second of that minute"
            ),
            "refusal": "what it said when it did not",
            "case": "which of the three override configurations the row reports",
            "case_note": "what that configuration is",
            "differs_from_built_in": "⭐ whether the file changed the answer",
            "unit": "the unit of every component of `values`",
            "values": "⚠ display decimals; `values_bits` is the authoritative form",
            "values_bits": "⭐ IEEE-754 bit patterns of the same components",
            "value_labels": "what each component of `values` is",
        },
        notes=[
            "⭐ The table is EXTRACTED, not transcribed. Every step here is a discontinuity "
            "the conversion actually exhibits, found by walking it — so this file records "
            "what the installed build believes rather than what any published list says.",
            "⛔ THE TABLE HAS A LAST ENTRY AND THE LIBRARY DOES NOT SAY SO. Past it the "
            "conversion keeps answering, with a constant offset, as though no further "
            "second will ever be inserted. ⭐ A table with a runway needs an alarm on the "
            "runway, and the library provides neither the alarm nor the length.",
            "⛔ AND THAT CONSTANT IS ITSELF TEMPORARY — THIS IS THE ROW TO READ TWICE. The "
            "held offset lasts exactly, to the bit, for over a decade past the last "
            "insertion, and then on one measured day it hands over to a smoothly drifting "
            "model. ⭐ Two civil instants a day apart across that day convert with about a "
            "second between them, and nothing announces it. ⚠ The row carries the date it "
            "falls on and the dates every insertion in this table falls on, so a reader can "
            "judge for themselves whether it is an insertion — this file does not assert "
            "the negative, it hands over the two facts the judgement needs.",
            "⭐ BUT IT FAILS LOUDLY IN THE ONE PLACE IT COULD FAIL QUIETLY. Offered the "
            "sixty-first second of a minute the table does not know, the conversion refuses "
            "outright instead of absorbing it. So a real future insertion arrives in an old "
            "build as an error rather than as a value that is silently one second wrong — "
            "which is the better of the two failures by a wide margin.",
            "⚠ THE TABLE IS REPLACEABLE FROM DISK, and only from the directory the library "
            "was explicitly pointed at. ⭐ That bounds where a table can have come from: a "
            "caller that never names such a directory used the built-in one, which makes "
            "the table a property of the installed build and recoverable from a version pin "
            "alone — no running machine required.",
            "⛔ AND THE TABLE IS READ ONCE PER PROCESS. It is not re-read when the library is "
            "closed and re-opened, so it survives the reset that puts every other piece of "
            "state back. The override rows above are each measured in a FRESH process for "
            "that reason: a first attempt at this measurement, taken in a process that had "
            "already converted one instant, reported that no override mechanism existed.",
            _BITS_NOTE,
            _REFERENCE_ONLY_NOTE,
        ],
        summary={
            "whole_second_steps": len(whole),
            "first_whole_second_step": whole[0]["effective_from"] if whole else None,
            "last_whole_second_step": whole[-1]["effective_from"] if whole else None,
            # ⚠ Counted per regime, and named for what they are. An earlier version of this
            #   block called every fractional step one from "before the regime" — and the
            #   rows themselves said otherwise, because the era AFTER the table's last entry
            #   produces them too. A summary that contradicts its own rows is worse than no
            #   summary; this one is derived from the rows' own regime field.
            "fractional_steps_by_regime": [
                {
                    "regime": regime,
                    "count": sum(
                        1 for row in fractional if row["regime"] == regime
                    ),
                }
                for regime in sorted({str(row["regime"]) for row in fractional})
            ],
            "constant_offset_handover": (
                None
                if handover is None
                else {
                    "date": handover["date"],
                    "last_date_holding_the_constant": handover[
                        "last_date_holding_the_constant"
                    ],
                    "step_seconds": handover["step_seconds"],
                }
            ),
            "meaning": (
                "⭐ a fixed number of insertions with a first and a last — and then TWO more "
                "eras, not one. Past the last insertion the offset is held exactly constant "
                "for years, and then handed over to a drifting model on a date the library "
                "names nowhere, with a jump of about a second that is not a leap second"
            ),
        },
        out_dir=out_dir,
        script=script,
    )


# --------------------------------------------------------------------------------------
# 5. the house methods that stop
# --------------------------------------------------------------------------------------


def write_polar_houses(
    *, session: Session, ephe: dict[str, Any], out_dir: Path, script: Path
) -> tuple[Path, int]:
    epochs = _epochs_with_hour(POSITION_EPOCHS)
    mode = MODES["moshier"]
    session.reset()
    # ⭐ The survey comes first, because the sweep below would otherwise be a sweep over
    #   aliases: this build answers to every name, so "which names does it accept" has the
    #   answer "all of them" and tells you nothing.
    classes, systems, fallback = house_system_survey(
        HOUSE_SURVEY_SAMPLES, HOUSE_LONGITUDE, mode.flag
    )
    rows: list[dict[str, Any]] = system_class_records(classes, fallback)

    rows.extend(
        polar_house_probe(
            systems=systems,
            latitudes=HOUSE_LATITUDES,
            epochs=epochs,
            longitude=HOUSE_LONGITUDE,
            mode=mode,
            session=session,
        )
    )
    boundaries = refusal_boundary(
        systems=systems,
        epochs=epochs,
        longitude=HOUSE_LONGITUDE,
        mode=mode,
        session=session,
    )
    rows.extend(boundaries)
    refusing = sorted({str(row["house_system_letter"]) for row in boundaries})
    session.reset()
    rows.extend(
        refusal_message(
            systems=tuple(refusing),
            jd=epochs[0][2],
            latitude=HOUSE_REFUSAL_LATITUDE,
            longitude=HOUSE_LONGITUDE,
            flag=mode.flag,
        )
    )

    # ⚠ A list of records again. Keying this by the method's letter would put a capital
    #   letter in a permanent identifier, which the contract refuses — and rightly: a
    #   single-letter key carries no meaning outside this library's own vocabulary.
    per_epoch = [
        {
            "epoch_id": row["epoch_id"],
            "house_system_letter": row["house_system_letter"],
            "last_latitude_answered": row["values"][0],
            "obliquity_of_date": row["obliquity_of_date"],
            "boundary_minus_ninety_minus_obliquity": row[
                "boundary_minus_ninety_minus_obliquity"
            ],
        }
        for row in boundaries
        if row["hemisphere"] == "north"
    ]
    return _write(
        name="polar-houses",
        title="Which house methods stop above the polar circle, exactly where, and how they say so",
        rows=rows,
        request={
            "epochs": [
                {"epoch_id": eid, "stratum": stratum, "jd_ut": jd, "jd_ut_bits": bits(jd)}
                for eid, stratum, jd in epochs
            ],
            "distinguishable_methods_swept": list(systems),
            "identity_survey_samples": [
                {"jd_ut": jd, "jd_ut_bits": bits(jd), "latitude": latitude}
                for jd, latitude in HOUSE_SURVEY_SAMPLES
            ],
            "names_that_are_not_methods": list(HOUSE_SYSTEM_CONTROLS),
            "latitudes": list(HOUSE_LATITUDES),
            "longitude": HOUSE_LONGITUDE,
            "refusal_message_latitude": HOUSE_REFUSAL_LATITUDE,
            "method": (
                "the names are first grouped by the numbers they return, over several "
                "unrelated samples, because this build accepts every name it is handed. One "
                "representative of each class is then called at every latitude, and the "
                "boundary is bisected rather than read from a published limit"
            ),
            "regenerate": "generators/convention_probes.py --ephe-path <dir> --out <dir>",
        },
        oracle=_oracle(mode, ephe, session),
        row_schema={
            **_COMMON_SCHEMA,
            "section": (
                "system_identity | system_at_latitude | refusal_boundary | "
                "entry_point_message"
            ),
            "members": "the names that returned identical cusps at every sample",
            "member_count": "how many",
            "contains_a_name_that_is_not_a_method": (
                "⭐ whether one of the control names landed in this class — which identifies "
                "the class as what the build answers with for a name it does not know"
            ),
            "samples_agreed_on": "how many (instant, latitude) samples the class held over",
            "is_the_fallback_class": "whether this is that class",
            "house_system_letter": "the single letter this build identifies the method by",
            "latitude": "degrees north — ⚠ display; `latitude_bits` is the value",
            "latitude_bits": "⭐ IEEE-754 bit pattern of the input",
            "longitude": "degrees east — ⚠ display; `longitude_bits` is the value",
            "longitude_bits": "⭐ IEEE-754 bit pattern of the input",
            "answered": "whether the method returned cusps at this latitude",
            "cusp_count": "how many cusps it returned — ⚠ not the same for every method",
            "identical_to": (
                "⭐ every other method whose cusps are bit-identical to this one's at the "
                "same instant and place. A method answering with another method's numbers "
                "has not computed what its name says"
            ),
            "refusal": "what the call raised when it did not answer",
            "hemisphere": "which side of the equator the boundary was bisected on",
            "obliquity_of_date": "the obliquity the library reported at that instant",
            "ninety_minus_obliquity": "the quarter-turn less that obliquity",
            "boundary_minus_ninety_minus_obliquity": (
                "⭐ how far the measured boundary sits from that quantity"
            ),
            "houses_ex_outcome": "what the entry point that returns cusps did",
            "houses_ex_message": "and what it said",
            "houses_ex2_outcome": "what the entry point that also returns a message did",
            "houses_ex2_message": (
                "⛔ and what IT said — which is not the same thing, and is the finding"
            ),
        },
        notes=[
            "⛔ THIS BUILD ACCEPTS EVERY NAME IT IS HANDED. A punctuation mark, a digit and a "
            "lower-case letter were each offered as a house method, and each was answered — "
            "with cusps identical to a real method's, at every sample. ⭐ So a name this "
            "library does not implement does not fail: it silently becomes one particular "
            "method, and a caller carrying a typo or a method this build lacks gets numbers "
            "that are correct for a method nobody asked for.",
            "⭐ AND THAT IS WHY THE NAMES ARE GROUPED RATHER THAN LISTED. 'Which names does "
            "it accept' has the answer 'all of them' and is not a question worth asking. "
            "'Which names can be told apart' is, and the control names — the ones that could "
            "not possibly be methods — are what identify the fallback without consulting any "
            "documentation.",
            "⛔ THE POLAR SUBSTITUTION IS REAL AND IT IS ONLY VISIBLE FROM ONE OF THE TWO ENTRY "
            "POINTS. Above the limit the library switches the undefined method for a "
            "different one and says so — in a sentence, returned by the entry point that "
            "carries a message. The entry point that returns the cusps reports a bare "
            "failure that names neither the substitution nor the method that answered.",
            "⭐ THE LIMIT IS NOT A ROUND NUMBER AND IT MOVES. It was bisected at each epoch "
            "rather than assumed, and the answers differ between epochs — including between "
            "two dates in the same year. So the limit is not a property of the site: a place "
            "just inside it today can be just outside it in another century, and the method "
            "that answers there changes with no change to the place.",
            "⚠ Methods whose cusps are identical to another method's are recorded as such. "
            "Some of those pairs are two names for one method rather than a substitution — "
            "the file records the identity and leaves the distinction to a reader who can "
            "see both rows.",
            "⚠ Not every method returns twelve cusps. A consumer that assumes a fixed count "
            "reads one method's numbers off the end of another's.",
            _BITS_NOTE,
            _REFERENCE_ONLY_NOTE,
        ],
        summary={
            "names_offered": len(HOUSE_SYSTEM_LETTERS) + len(HOUSE_SYSTEM_CONTROLS),
            "distinguishable_classes": len(classes),
            "names_indistinguishable_from_the_fallback": list(fallback),
            "methods_that_refuse_above_a_latitude": refusing,
            "boundary_per_epoch_north": per_epoch,
            "meaning": (
                "⭐ the first three entries are one finding: far more names are accepted than "
                "can be told apart, and the class holding the names that are not methods is "
                "what an unrecognised name becomes. ⭐ In the last entry, compare "
                "`last_latitude_answered` against `ninety_minus_obliquity`: the boundary "
                "tracks a quantity that changes with the epoch, which is why it is measured "
                "per epoch and never quoted as a constant"
            ),
        },
        out_dir=out_dir,
        script=script,
    )


# --------------------------------------------------------------------------------------
# The state audit, which is an attestation rather than a measurement
# --------------------------------------------------------------------------------------


def write_state_audit(
    *, session: Session, ephe: dict[str, Any], out_dir: Path, script: Path
) -> tuple[Path, int]:
    rows = global_state_records()
    header = Header(
        fixture_kind="provenance_record",
        reference="R3",
        generator=generator_for(script),
        generated=today(),
        title="What the library keeps between calls, and what closing it does not put back",
        oracle={
            **_oracle(None, ephe, session),
            "method": (
                "each state was set, the library closed and re-opened, and the state read "
                "back — the same procedure for all four, so the differences between them are "
                "differences in the library rather than in the probe"
            ),
        },
        attests=(
            "which pieces of the ephemeris library's process-wide state survive a close and "
            "re-open, which are dropped by it, and which are changed by it into a third "
            "value that is neither what they were set to nor what they started as; and that "
            "one of them is never re-read at all, so a measurement of it taken after any "
            "other call in the same process reports the earlier call's state"
        ),
        authority={
            "held_by": "the library itself, as observed",
            "kind": "direct observation of state under controlled set-close-read cycles",
            "scope": (
                "⚠ this version of the library and this binding only. A later version may "
                "behave differently, which is why the observation is dated and versioned "
                "rather than stated as a property of the software in general"
            ),
        },
        record_date=today(),
        row_schema={
            "finding": "process_global_state",
            "state": "the piece of state",
            "set_by": "what puts it in place",
            "restored_by_close": "⭐ what a close and re-open actually does to it",
            "consequence": "what a caller that assumed otherwise would get",
        },
        notes=[
            "⭐ THE RULE THIS FILE SUPPORTS. Resetting the library between recorded calls is "
            "necessary and not sufficient: the reset restores some of this state, drops "
            "some, and changes one into a third value. A reset that restores only part of "
            "the state is worse than none, because the part it drops is invisible in every "
            "value that follows.",
            "⛔ One of these is never re-read after the first use in a process. A probe of it "
            "must therefore run in a fresh process, and a probe that does not will report "
            "the state its own process started with — confidently, and with no sign that it "
            "measured the wrong thing.",
        ],
    )
    path = out_dir / "conventions" / "library-state.jsonl"
    return path, write_jsonl(path, header, rows)


# --------------------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--ephe-path",
        required=True,
        type=Path,
        help="directory of the library's data files; every file in it is hashed",
    )
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()

    script = Path(__file__)
    generator_for(script)  # ⛔ refuse a dirty tree before anything is measured

    print(describe_reserved_names())

    pins = verify_ephe_set(args.ephe_path)
    print(f"data files verified: {len(pins)} file(s), sha256 ok")
    ephe = ephe_set_identity(args.ephe_path, pins)

    session = Session(ephe_path=str(args.ephe_path), sidereal_mode=swe.SIDM_LAHIRI)
    session.reset()

    written: list[tuple[Path, int]] = []
    for label, call in (
        ("the time offset", lambda: write_delta_t(
            session=session, ephe=ephe, out_dir=args.out, script=script)),
        ("apparent position", lambda: write_apparent(
            session=session, ephe=ephe, out_dir=args.out, script=script)),
        ("rise/set refraction", lambda: write_refraction(
            session=session, ephe=ephe, out_dir=args.out, script=script)),
        ("leap seconds", lambda: write_leap_seconds(
            session=session, ephe=ephe, out_dir=args.out, script=script)),
        ("polar houses", lambda: write_polar_houses(
            session=session, ephe=ephe, out_dir=args.out, script=script)),
        ("library state", lambda: write_state_audit(
            session=session, ephe=ephe, out_dir=args.out, script=script)),
    ):
        result = call()
        for path, count in result if isinstance(result, list) else [result]:
            written.append((path, count))
            print(f"{label}: wrote {count} rows -> {path}")

    print(f"{len(written)} file(s), {sum(count for _, count in written)} rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
