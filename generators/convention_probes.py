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
    apparent_variants,
    atmosphere_equivalence,
    delta_t_flag_dependence,
    delta_t_readings,
    global_state_records,
    house_system_survey,
    leap_override_probe,
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
        classification=_classification(sections),
        budget_row=BUDGET_ROW,
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


def write_delta_t(
    *, session: Session, ephe: dict[str, Any], out_dir: Path, script: Path
) -> tuple[Path, int]:
    epochs = _epochs(DELTA_T_EPOCHS)
    rows: list[dict[str, Any]] = []
    for mode_id in ("moshier", "swiss_file"):
        rows.extend(delta_t_readings(epochs, MODES[mode_id], session))
    rows.extend(delta_t_flag_dependence(epochs, MODES, session))

    spread = [row for row in rows if row["section"] == "flag_dependence"]
    moved = [row for row in spread if row["spread_seconds"] != 0.0]
    return _write(
        name="time-offset",
        title="What the library adds to a civil instant to reach the dynamical scale",
        rows=rows,
        request={
            "epochs": [
                {"epoch_id": eid, "stratum": stratum, "jd_ut": jd, "jd_ut_bits": bits(jd)}
                for eid, stratum, jd in epochs
            ],
            "entry_points": ["deltat_ex", "deltat"],
            "regenerate": "generators/convention_probes.py --ephe-path <dir> --out <dir>",
        },
        oracle=_oracle(None, ephe, session),
        row_schema={
            **_COMMON_SCHEMA,
            "section": "delta_t | flag_dependence",
            "ephemeris_requested": "the source named in the call's flag",
            "seconds": "the same offset in seconds, for reading; the day value is the value",
            "tidal_acceleration_in_force": (
                "⚠ the constant the library held when the reading was taken. It is an input "
                "to the historical part of the conversion, and a close changes it"
            ),
            "unflagged_entry_point": "what the entry point that takes no flag returned",
            "unflagged_equals": (
                "⭐ which of the flagged answers the unflagged one is identical to — a "
                "caller who passes no flag has still chosen one"
            ),
            "spread_seconds": "the largest disagreement between the three flagged answers",
            "reported_by_entry_point": (
                "⛔ what the call itself said about which ephemeris supplied its constants"
            ),
        },
        notes=[
            "⭐ THE POINT OF THIS FILE. The entry point takes an argument naming a source of "
            "**positions**, and returns a quantity that is not a position — and at one of "
            "the three epochs here the answer moves with it. So two callers converting the "
            "same civil instant, differing only in an ephemeris flag chosen for unrelated "
            "reasons, get two different instants and no notice of it.",
            "⚠ The entry point returns DAYS. A duration recorded in the wrong unit is the "
            "easiest reproduction failure to make and the hardest to see in a table, so both "
            "forms are written and the day value is the authoritative one.",
            "⛔ The third epoch is beyond any measurement of this quantity: the library "
            "answers, and its answer is a model's extrapolation. Published models disagree "
            "with each other far more at that epoch than any of the differences recorded "
            "here — this file pins what THIS library returns and makes no claim about which "
            "extrapolation is right.",
            _BITS_NOTE,
            _REFERENCE_ONLY_NOTE,
        ],
        summary={
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
            "bound": "first_whole_second_step | last_whole_second_step",
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
            "conversion keeps answering, with a constant offset, for as far ahead as it is "
            "asked. That is a prediction that no further second will ever be inserted. ⭐ A "
            "table with a runway needs an alarm on the runway, and the library provides "
            "neither the alarm nor the length.",
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
            "fractional_steps_before_the_regime": len(fractional),
            "meaning": (
                "⭐ the count and the two ends are the whole finding: a fixed number of "
                "insertions, a first, a last, and nothing after the last but silence"
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
        path, count = call()
        written.append((path, count))
        print(f"{label}: wrote {count} rows -> {path}")

    print(f"{len(written)} file(s), {sum(count for _, count in written)} rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
