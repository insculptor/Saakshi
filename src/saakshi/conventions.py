"""The conventions a value carries without saying so.

An ephemeris library takes a flag, a date and a place, and returns a number. Between the
arguments and the number sit decisions nobody passed in: which time scale the date was
read as, which atmosphere a rising was defined against, which house method actually
answered when the one requested is undefined. ⭐ **Those decisions are conventions, and a
consumer that reproduces the number without reproducing the convention has reproduced
nothing.**

This module measures five of them. It answers each by **interrogating the library**, never
by reading its documentation:

* how much the library adds to a civil instant to reach dynamical time, and whether that
  quantity depends on an argument that has nothing to do with time;
* what a position returned under default flags already has applied to it, measured one
  effect at a time by switching each off;
* ⭐ **what atmosphere a rise/set call assumes when both atmospheric arguments are zero** —
  the convention a calendar built on sunrise rests on entirely;
* which leap seconds the library knows, where its table stops, and what it does either side
  of that edge;
* which house methods refuse above the polar circle, at exactly which latitude, and whether
  a refusal is reported as one.

⛔ **Recorder, never explainer.** Every statement here is something a call returned. There
is no account of how refraction, ΔT or a house cusp is computed, and no claim that any
answer is right — only that it is what this library, at this version, returned.
"""

from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from typing import Any

import swisseph as swe

from .swiss import (
    EphemerisSubstitution,
    Mode,
    Session,
    assert_reported,
    assert_window,
    calendar_ut,
)

class BoundaryNotStable(Exception):
    """A bisected boundary did not survive re-checking its own endpoints.

    ⛔ Raised rather than reported. A caller handed a verdict may record the boundary
    anyway; a caller handed an exception cannot.
    """


#: Seconds in a day, for turning a Julian-day difference into a duration a reader can weigh.
SECONDS_PER_DAY = 86_400.0

#: Degrees to arc-seconds and to arc-minutes. Rise/set conventions are conventionally
#: quoted in arc-minutes of altitude, and position differences in arc-seconds.
ARCSEC = 3_600.0
ARCMIN = 60.0


# ======================================================================================
# The state the library keeps, and what a reset does and does not put back
# ======================================================================================


@dataclass(frozen=True)
class GlobalState:
    """One piece of process-wide library state, and its measured behaviour under a reset.

    ⭐ This table exists because a reset that restores *some* state is worse than no reset
    at all: the part it drops is invisible, and every later value is a function of it.
    """

    name: str
    set_by: str
    restored_by_close: str
    consequence: str


#: ⛔ **Measured, and three of the four are not what a caller would assume.** The sidereal
#: mode was already known to be dropped by a close; these three were found while measuring
#: the conventions in this module, each by setting the state, closing the library, and
#: reading it back.
GLOBAL_STATE: tuple[GlobalState, ...] = (
    GlobalState(
        name="sidereal_mode",
        set_by="set_sid_mode",
        restored_by_close="dropped — reverts to the default",
        consequence=(
            "an ayanamsha read after a close that did not re-apply it was measured 0.88 "
            "degrees away from the right answer, which is a plausible number in the right "
            "range rather than an obvious failure"
        ),
    ),
    GlobalState(
        name="user_defined_delta_t",
        set_by="set_delta_t_userdef",
        restored_by_close=(
            "⛔ SURVIVES — a value set once answers every later call in the process, "
            "including after a close and a fresh path"
        ),
        consequence=(
            "every instant converted between the civil and dynamical scales carries it, so "
            "one call made anywhere in a process silently redefines time for all of it"
        ),
    ),
    GlobalState(
        name="tidal_acceleration",
        set_by="set_tid_acc, or implicitly by the first ephemeris consulted",
        restored_by_close=(
            "⚠ CHANGED, not restored — measured leaving a close holding neither the value "
            "it was set to nor the value it started at"
        ),
        consequence=(
            "it is an input to the historical part of the time conversion, so a close "
            "moves that conversion by an amount nothing reports"
        ),
    ),
    GlobalState(
        name="leap_second_table",
        set_by="a file in the ephemeris directory, read on first use",
        restored_by_close=(
            "⛔ SURVIVES, and is never re-read — a table loaded once answers for the rest "
            "of the process even after the file is deleted and the library closed"
        ),
        consequence=(
            "⭐ a probe of the table that runs after anything else has converted a civil "
            "instant is measuring the first caller's table, not the one on disk. This was "
            "measured the hard way: a first attempt to demonstrate the override reported "
            "that no override mechanism existed"
        ),
    ),
)


def global_state_records() -> list[dict[str, Any]]:
    """The state audit, as fixture rows."""
    return [
        {
            "finding": "process_global_state",
            "state": item.name,
            "set_by": item.set_by,
            "restored_by_close": item.restored_by_close,
            "consequence": item.consequence,
        }
        for item in GLOBAL_STATE
    ]


# ======================================================================================
# 1. What the library adds to a civil instant to reach dynamical time
# ======================================================================================

#: ⚠ The entry point returns **days**, not seconds. Recorded in both, with the day value's
#: bit pattern as the authoritative form — a duration quoted in the wrong unit is the
#: easiest of all reproduction failures and the hardest to see in a table.
DELTA_T_UNIT = "day"


def delta_t_readings(
    epochs: list[tuple[str, str, float]], mode: Mode, session: Session
) -> list[dict[str, Any]]:
    """The time offset the library applies, per epoch, under one requested ephemeris.

    ⭐ **The measurement worth having is not the value; it is that the value moves with the
    ephemeris flag.** The entry point takes one, uses it, and reports nothing back — so a
    caller who passes a different flag for an unrelated reason gets a different time scale
    and no notice of it.

    ⛔ Every reading is taken from a reset state and carries a proxy source assertion,
    because this entry point is another that consults an ephemeris and returns no statement
    about which one answered.
    """
    rows: list[dict[str, Any]] = []
    for epoch_id, stratum, jd in epochs:
        where = f"{mode.id}/delta_t/{epoch_id}"
        session.reset()
        try:
            assertion = assert_window(mode, body=swe.SUN, jd_start=jd, jd_end=jd, where=where)
        except EphemerisSubstitution:
            continue
        value_days = float(swe.deltat_ex(jd, mode.flag))
        tid_acc = float(swe.get_tid_acc())
        rows.append(
            {
                "section": "delta_t",
                "epoch_id": epoch_id,
                "stratum": stratum,
                "jd_ut": jd,
                "jd_ut_bits": bits_of(jd),
                "utc": calendar_ut(jd),
                "ephemeris_requested": mode.source,
                "unit": DELTA_T_UNIT,
                "values": [value_days],
                "values_bits": [bits_of(value_days)],
                "seconds": value_days * SECONDS_PER_DAY,
                "tidal_acceleration_in_force": tid_acc,
                "source_assertion": assertion,
                "reported_by_entry_point": (
                    "⛔ nothing. This entry point accepts an ephemeris flag, uses it, and "
                    "returns no statement of which ephemeris supplied the constants behind "
                    "the answer"
                ),
            }
        )
    return rows


def delta_t_flag_dependence(
    epochs: list[tuple[str, str, float]], modes: dict[str, Mode], session: Session
) -> list[dict[str, Any]]:
    """The same instant, the same entry point, one argument changed — and the answer moves.

    ⭐ The unflagged entry point is called too, so the file records **which flagged answer
    the unflagged one silently equals**. A caller who never passes a flag has still chosen
    one.
    """
    rows: list[dict[str, Any]] = []
    for epoch_id, stratum, jd in epochs:
        session.reset()
        readings: dict[str, float] = {}
        for label, flag in (
            ("moshier", swe.FLG_MOSEPH),
            ("swiss_file", swe.FLG_SWIEPH),
            ("jpl_file", swe.FLG_JPLEPH),
        ):
            session.reset()
            readings[label] = float(swe.deltat_ex(jd, flag))
        session.reset()
        unflagged = float(swe.deltat(jd))
        matches = sorted(k for k, v in readings.items() if v == unflagged)
        spread = (max(readings.values()) - min(readings.values())) * SECONDS_PER_DAY
        rows.append(
            {
                "section": "flag_dependence",
                "epoch_id": epoch_id,
                "stratum": stratum,
                "jd_ut": jd,
                "jd_ut_bits": bits_of(jd),
                "utc": calendar_ut(jd),
                "unit": DELTA_T_UNIT,
                "values": [readings[k] for k in sorted(readings)],
                "values_bits": [bits_of(readings[k]) for k in sorted(readings)],
                "value_labels": sorted(readings),
                "unflagged_entry_point": unflagged,
                "unflagged_entry_point_bits": bits_of(unflagged),
                "unflagged_equals": matches,
                "spread_seconds": spread,
                "meaning": (
                    "⭐ where the spread is non-zero, an argument naming a source of "
                    "positions has changed a quantity that is not a position. Where it is "
                    "zero the three agree, which is a measurement and not a guarantee"
                ),
            }
        )
    return rows


# ======================================================================================
# 2. What a position returned under default flags already has applied to it
# ======================================================================================

#: Each entry switches **one** effect off. ⭐ The difference from the default answer is that
#: effect's size — which is how a claim about what "apparent" means becomes a number rather
#: than a reading of the manual.
#:
#: ⚠ A zero here means *this body, this epoch, this effect* moved nothing. It does **not**
#: mean the effect is disabled: a body is not deflected by its own gravity, so the light
#: source of the system reports zero for deflection at every epoch while the outer planets
#: report a real number.
APPARENT_VARIANTS: tuple[tuple[str, int, str], ...] = (
    ("no_light_time_or_aberration", swe.FLG_TRUEPOS, "the position without either travel-time term"),
    ("no_aberration", swe.FLG_NOABERR, "the observer's motion not applied"),
    ("no_gravitational_deflection", swe.FLG_NOGDEFL, "light not bent on its way in"),
    ("no_nutation", swe.FLG_NONUT, "the equinox of date without its short-period part"),
    ("j2000_frame", swe.FLG_J2000, "referred to a fixed frame instead of the equinox of date"),
    (
        "all_three_off",
        swe.FLG_TRUEPOS | swe.FLG_NOABERR | swe.FLG_NOGDEFL,
        "every term this sweep can switch off, switched off together",
    ),
)


def apparent_variants(
    epochs: list[tuple[str, str, float]],
    bodies: tuple[tuple[int, str], ...],
    mode: Mode,
    session: Session,
) -> list[dict[str, Any]]:
    """Measure each term in the default answer by removing it.

    ⛔ The default answer is the reference here, and every row records the returned flag of
    **both** calls — the reference and the variant. A variant answered by a substituted
    ephemeris would otherwise report the substitution as an effect size.
    """
    rows: list[dict[str, Any]] = []
    base_flags = mode.flag | swe.FLG_SPEED
    for epoch_id, stratum, jd in epochs:
        for body, body_name in bodies:
            where = f"{mode.id}/apparent/{epoch_id}/{body_name}"
            session.reset()
            try:
                reference, returned = swe.calc_ut(jd, body, base_flags)
                base_assertion = assert_reported(mode, returned, where=where)
            except Exception:
                continue
            for variant, extra, note in APPARENT_VARIANTS:
                session.reset()
                try:
                    values, variant_returned = swe.calc_ut(jd, body, base_flags | extra)
                    assertion = assert_reported(
                        mode, variant_returned, where=f"{where}/{variant}"
                    )
                except EphemerisSubstitution:
                    continue
                except Exception:
                    continue
                delta = _angular_delta(float(values[0]), float(reference[0]))
                rows.append(
                    {
                        "section": "variant_delta",
                        "epoch_id": epoch_id,
                        "stratum": stratum,
                        "jd_ut": jd,
                        "jd_ut_bits": bits_of(jd),
                        "utc": calendar_ut(jd),
                        "body": body_name,
                        "body_number": body,
                        "variant": variant,
                        "variant_note": note,
                        "unit": "degree",
                        "values": [float(values[0]), float(reference[0])],
                        "values_bits": [
                            bits_of(float(values[0])),
                            bits_of(float(reference[0])),
                        ],
                        "value_labels": ["variant_longitude", "default_longitude"],
                        "delta_arcseconds": delta * ARCSEC,
                        "source_assertion": assertion,
                        "reference_source_assertion": base_assertion,
                    }
                )
    return rows


def _angular_delta(a: float, b: float) -> float:
    """Difference of two longitudes, taken the short way round.

    ⛔ A plain subtraction across the wrap reports 360 where the real difference is
    arc-seconds, which would put the largest number in the file on the pair that agrees
    best.
    """
    delta = abs(a - b)
    return 360.0 - delta if delta > 180.0 else delta


# ======================================================================================
# 3. ⭐ The atmosphere a rising is defined against when nobody names one
# ======================================================================================

#: The atmospheric arguments a caller who omits them selects. ⛔ **The binding's declared
#: defaults are zero for both**, so *omitting* the arguments is not "no atmosphere" and not
#: "the standard atmosphere" — it is whatever the library does with a zero, and that is a
#: measurement rather than a reading.
OMITTED_ATPRESS = 0.0
OMITTED_ATTEMP = 0.0

#: Sea level, so the pressure question is asked without an altitude term in it.
SEA_LEVEL = 0.0

#: ⚠ The conventional sea-level atmosphere, present here **only as a hypothesis to test**
#: — never as an assumed default.
STANDARD_PRESSURE = 1013.25
STANDARD_TEMPERATURE = 15.0


@dataclass(frozen=True)
class Atmosphere:
    """One (pressure, temperature, observer height) the rise/set call is asked to use."""

    id: str
    atpress: float
    attemp: float
    geoalt: float
    note: str


#: ⭐ The matrix that answers the question. The first row is what a caller who passes
#: nothing gets; every later row is a hypothesis about what that row *means*, stated as an
#: explicit request so the two can be compared as numbers.
ATMOSPHERES: tuple[Atmosphere, ...] = (
    Atmosphere("omitted", OMITTED_ATPRESS, OMITTED_ATTEMP, SEA_LEVEL, "both arguments zero"),
    Atmosphere(
        "standard_pressure_standard_temperature",
        STANDARD_PRESSURE,
        STANDARD_TEMPERATURE,
        SEA_LEVEL,
        "the conventional sea-level atmosphere, stated explicitly",
    ),
    Atmosphere(
        "standard_pressure_zero_temperature",
        STANDARD_PRESSURE,
        0.0,
        SEA_LEVEL,
        "the conventional pressure with the temperature argument left at zero",
    ),
    Atmosphere(
        "standard_pressure_cold",
        STANDARD_PRESSURE,
        -20.0,
        SEA_LEVEL,
        "a cold atmosphere, to show the temperature term is live",
    ),
    Atmosphere(
        "zero_pressure_standard_temperature",
        0.0,
        STANDARD_TEMPERATURE,
        SEA_LEVEL,
        "the pressure argument zero, the temperature stated",
    ),
    Atmosphere(
        "half_pressure_zero_temperature", 500.0, 0.0, SEA_LEVEL, "a thin atmosphere"
    ),
    Atmosphere(
        "omitted_at_500_m", OMITTED_ATPRESS, OMITTED_ATTEMP, 500.0, "both zero, observer raised"
    ),
    Atmosphere(
        "omitted_at_2000_m",
        OMITTED_ATPRESS,
        OMITTED_ATTEMP,
        2000.0,
        "both zero, observer raised further",
    ),
)

#: The event definitions compared against the omitted-argument one. ⭐ Each is a different
#: answer to "when has it risen", and the differences between them are in **minutes**.
RISE_DEFINITIONS: tuple[tuple[str, int, str], ...] = (
    ("disc_centre", swe.CALC_RISE | swe.BIT_DISC_CENTER, "the centre of the disc at the horizon"),
    (
        "disc_centre_no_refraction",
        swe.CALC_RISE | swe.BIT_DISC_CENTER | swe.BIT_NO_REFRACTION,
        "the centre of the disc, with the atmosphere switched off entirely",
    ),
    (
        "upper_limb",
        swe.CALC_RISE | swe.BIT_DISC_BOTTOM,
        "the leading edge of the disc rather than its centre",
    ),
    (
        "library_named_convention",
        swe.CALC_RISE | swe.BIT_HINDU_RISING,
        "the composite the library itself offers under a name",
    ),
)


def horizon_depression(
    jd_event: float,
    body: int,
    site: tuple[float, float, float],
    atmosphere: Atmosphere,
    flag: int,
) -> float | None:
    """The true altitude of the body's centre at the instant the call called it a rising.

    ⭐ **This is what turns a returned time into a statement about a convention.** The event
    time on its own says nothing; the body's geometric altitude at that time says exactly
    how far below the horizon the library places a rising, in the units conventions are
    quoted in.

    ⚠ The same atmospheric arguments are handed to the horizontal-coordinate call, so the
    two are asked the same question. A mismatch there would measure the difference between
    two atmospheres rather than the rise convention.
    """
    longitude, latitude, height = site
    try:
        equatorial, _ = swe.calc_ut(jd_event, body, flag | swe.FLG_EQUATORIAL)
        _az, true_alt, _app_alt = swe.azalt(
            jd_event,
            swe.EQU2HOR,
            (longitude, latitude, height),
            atmosphere.atpress,
            atmosphere.attemp,
            (equatorial[0], equatorial[1], equatorial[2]),
        )
    except Exception:
        return None
    return float(true_alt)


def refraction_probe(
    *,
    sites: tuple[tuple[str, float, float, str], ...],
    epochs: list[tuple[str, str, float]],
    body: int,
    body_name: str,
    mode: Mode,
    session: Session,
) -> list[dict[str, Any]]:
    """Where the library puts a rising, under every atmosphere and every event definition.

    ⛔ Each event is attributed by proxy at both ends of the interval the call may read,
    exactly as any other value from an entry point that reports no source. An event the
    call did not find is recorded as not found, never as the zero the library leaves in the
    time slot.
    """
    rows: list[dict[str, Any]] = []
    for epoch_id, stratum, jd in epochs:
        for site_id, latitude, longitude, site_label in sites:
            baseline: float | None = None

            for definition, rsmi, definition_note in RISE_DEFINITIONS:
                for atmosphere in ATMOSPHERES:
                    # ⚠ Only the omitted-argument atmosphere is swept across every event
                    #   definition; the rest vary the atmosphere under the one definition a
                    #   caller who passes nothing actually gets.
                    if definition != "disc_centre" and atmosphere.id != "omitted":
                        continue
                    here = (longitude, latitude, atmosphere.geoalt)
                    where = (
                        f"{mode.id}/rise/{epoch_id}/{site_id}/{definition}/{atmosphere.id}"
                    )
                    session.reset()
                    try:
                        code, times = swe.rise_trans(
                            jd,
                            body,
                            rsmi,
                            here,
                            atmosphere.atpress,
                            atmosphere.attemp,
                            mode.flag,
                        )
                    except Exception:
                        continue
                    if code != 0:
                        rows.append(
                            {
                                "section": "no_event",
                                "epoch_id": epoch_id,
                                "stratum": stratum,
                                "jd_ut": jd,
                                "jd_ut_bits": bits_of(jd),
                                "utc": calendar_ut(jd),
                                "site": site_id,
                                "site_label": site_label,
                                "latitude": latitude,
                                "latitude_bits": bits_of(latitude),
                                "longitude": longitude,
                                "longitude_bits": bits_of(longitude),
                                "body": body_name,
                                "event_definition": definition,
                                "atmosphere": atmosphere.id,
                                "return_code": code,
                                "time_slot_left_in_place": float(times[0]),
                                "meaning": (
                                    "⛔ no event in the interval searched. The time slot "
                                    "holds an ordinary-looking Julian day rather than a "
                                    "sentinel, so a caller that reads it without reading "
                                    "the code gets a date in the fifth millennium BC"
                                ),
                            }
                        )
                        continue
                    event_jd = float(times[0])
                    try:
                        assertion = assert_window(
                            mode,
                            body=body,
                            jd_start=min(jd, event_jd),
                            jd_end=max(jd, event_jd) + 0.5,
                            where=where,
                        )
                    except Exception:
                        continue
                    depression = horizon_depression(
                        event_jd, body, here, atmosphere, mode.flag
                    )
                    if definition == "disc_centre" and atmosphere.id == "omitted":
                        baseline = event_jd
                    rows.append(
                        {
                            "section": "horizon_depression",
                            "epoch_id": epoch_id,
                            "stratum": stratum,
                            "jd_ut": jd,
                            "jd_ut_bits": bits_of(jd),
                            "utc": calendar_ut(jd),
                            "site": site_id,
                            "site_label": site_label,
                            "latitude": latitude,
                            "latitude_bits": bits_of(latitude),
                            "longitude": longitude,
                            "longitude_bits": bits_of(longitude),
                            "body": body_name,
                            "body_number": body,
                            "ephemeris_requested": mode.source,
                            "event_definition": definition,
                            "event_definition_note": definition_note,
                            "atmosphere": atmosphere.id,
                            "atmosphere_note": atmosphere.note,
                            "atpress": atmosphere.atpress,
                            "attemp": atmosphere.attemp,
                            "observer_height_m": atmosphere.geoalt,
                            "unit": "julian_day_ut",
                            "values": [event_jd],
                            "values_bits": [bits_of(event_jd)],
                            "event_utc": calendar_ut(event_jd),
                            "true_altitude_arcminutes": (
                                None if depression is None else depression * ARCMIN
                            ),
                            "seconds_from_omitted_arguments": (
                                None
                                if baseline is None
                                else (event_jd - baseline) * SECONDS_PER_DAY
                            ),
                            "source_assertion": assertion,
                        }
                    )
    return rows


def atmosphere_equivalence(
    *,
    site: tuple[float, float, float],
    epochs: list[tuple[str, str, float]],
    body: int,
    mode: Mode,
    session: Session,
) -> list[dict[str, Any]]:
    """Which *stated* atmosphere the omitted arguments turn out to be.

    ⭐ **The decisive test, and it is an identity rather than a tolerance.** If passing
    nothing is the same as passing some particular pressure and temperature, the two calls
    return the same instant — and *the same bits*. Comparing bit patterns rather than
    rounded times is what makes the answer a fact instead of an impression.
    """
    longitude, latitude, _ = site
    rsmi = swe.CALC_RISE | swe.BIT_DISC_CENTER
    rows: list[dict[str, Any]] = []

    def event(atpress: float, attemp: float, jd: float) -> float | None:
        session.reset()
        try:
            code, times = swe.rise_trans(
                jd, body, rsmi, (longitude, latitude, 0.0), atpress, attemp, mode.flag
            )
        except Exception:
            return None
        return float(times[0]) if code == 0 else None

    for epoch_id, stratum, jd in epochs:
        omitted = event(OMITTED_ATPRESS, OMITTED_ATTEMP, jd)
        if omitted is None:
            continue
        for candidate_id, atpress, attemp in (
            ("standard_pressure_zero_temperature", STANDARD_PRESSURE, 0.0),
            ("standard_pressure_standard_temperature", STANDARD_PRESSURE, STANDARD_TEMPERATURE),
            ("zero_pressure_zero_temperature", 0.0, 0.0),
        ):
            stated = event(atpress, attemp, jd)
            if stated is None:
                continue
            rows.append(
                {
                    "section": "atmosphere_equivalence",
                    "epoch_id": epoch_id,
                    "stratum": stratum,
                    "jd_ut": jd,
                    "jd_ut_bits": bits_of(jd),
                    "utc": calendar_ut(jd),
                    "candidate": candidate_id,
                    "candidate_atpress": atpress,
                    "candidate_attemp": attemp,
                    "unit": "julian_day_ut",
                    "values": [omitted, stated],
                    "values_bits": [bits_of(omitted), bits_of(stated)],
                    "value_labels": ["omitted_arguments", "stated_atmosphere"],
                    "bit_identical": bits_of(omitted) == bits_of(stated),
                    "seconds_apart": (stated - omitted) * SECONDS_PER_DAY,
                    "meaning": (
                        "⭐ a bit-identical pair means the omitted arguments select exactly "
                        "this stated atmosphere. ⚠ A near-miss is not an identity and is "
                        "recorded as the difference it is"
                    ),
                }
            )
    return rows


# ======================================================================================
# 4. The leap seconds the library knows, and the edges of what it knows
# ======================================================================================

#: ⛔ This entry point takes **no ephemeris flag at all**, so no source assertion is
#: possible or meaningful. Recorded explicitly rather than left as an absence, because an
#: absent assertion and an impossible one are different facts.
LEAP_SECOND_ENTRY_POINT = "utc_to_jd"


def tt_minus_utc(year: int, month: int, day: int) -> float:
    """The whole offset between the civil and dynamical scales at civil midnight, seconds.

    ⭐ **The smooth part is removed on purpose.** The conversion's output carries both a
    modelled long-term drift and the leap-second steps; differencing against the same
    calendar instant read as a plain Julian day leaves the step function alone, so a step
    of exactly one second is visible against a drift that would otherwise swamp it.
    """
    jd_tt, _jd_ut = swe.utc_to_jd(year, month, day, 0, 0, 0.0, swe.GREG_CAL)
    return (jd_tt - swe.julday(year, month, day, 0.0)) * SECONDS_PER_DAY


#: The two dates a leap second may be inserted at. ⚠ Scanned rather than assumed: a step at
#: any other date would be recorded, not skipped.
INSERTION_DATES: tuple[tuple[int, int], ...] = ((1, 1), (7, 1))

#: What counts as a step rather than drift. ⚠ The drift between two scan points is of order
#: microseconds once the smooth part is removed, and a leap second is a whole second, so
#: this threshold sits four orders of magnitude away from both.
STEP_THRESHOLD_SECONDS = 1e-4


def leap_second_table(first_year: int, last_year: int) -> list[dict[str, Any]]:
    """Extract the library's own table by walking the conversion, not by reading a file.

    ⚠ **Every step found is recorded, including the ones that are not leap seconds.** The
    scan does not know in advance which era it is in, and filtering to whole seconds would
    hide the two eras where the conversion is not a leap-second conversion at all — one
    before the table's first entry and one, measured here, well after its last.
    """
    rows: list[dict[str, Any]] = []
    previous: tuple[int, int, int, float] | None = None
    whole_steps: list[str] = []
    for year in range(first_year, last_year + 1):
        for month, day in INSERTION_DATES:
            value = tt_minus_utc(year, month, day)
            if previous is not None:
                step = value - previous[3]
                if abs(step) > STEP_THRESHOLD_SECONDS:
                    is_whole = abs(abs(step) - 1.0) < 1e-4
                    date = f"{year:04d}-{month:02d}-{day:02d}"
                    if is_whole:
                        whole_steps.append(date)
                    rows.append(
                        {
                            "section": "leap_step",
                            "effective_from": date,
                            "regime": _regime(date, whole_steps),
                            "unit": "second",
                            "values": [previous[3], value],
                            "values_bits": [bits_of(previous[3]), bits_of(value)],
                            "value_labels": ["before", "after"],
                            "step_seconds": step,
                            "is_whole_second": is_whole,
                        }
                    )
            previous = (year, month, day, value)
    return rows


def _regime(date: str, whole_steps_so_far: list[str]) -> str:
    """Which of the three eras a step falls in, decided from the steps already seen.

    ⛔ Named from the data rather than from a constant. A hard-coded first and last
    insertion date would keep classifying correctly long after the installed table stopped
    matching it, which is the failure this whole file is about.
    """
    if not whole_steps_so_far:
        return "before_the_first_whole_second_step"
    if whole_steps_so_far[-1] == date:
        return "within_the_table"
    return "after_the_last_whole_second_step_seen_so_far"


def _calendar(jd: float) -> tuple[int, int, int]:
    year, month, day, _hour = swe.revjul(jd)
    return int(year), int(month), int(day)


def constant_offset_handover(
    after_date: tuple[int, int, int], search_years: int
) -> dict[str, Any] | None:
    """The day the conversion stops holding the table's offset and starts drifting.

    ⭐ **This is a bound nothing announces.** Past its last insertion the conversion holds
    one constant offset — for years, exactly, to the bit. Then, on a day the library names
    nowhere, it hands over to a smoothly varying model and the offset begins to move. The
    handover itself is a discontinuity of about a second that is **not** a leap second.

    ⛔ Located by bisection on "is the offset still the constant", from a day known to be
    inside the flat region, and both endpoints re-verified. Returns `None` where no handover
    lies inside the searched span — which is a finding too, not an absence of one.
    """
    year, month, day = after_date
    start_jd = swe.julday(year, month, day, 0.0)
    constant = tt_minus_utc(year, month, day)

    def flat(jd: float) -> bool:
        return abs(tt_minus_utc(*_calendar(jd)) - constant) <= STEP_THRESHOLD_SECONDS

    if not flat(start_jd):
        return None
    end_jd = start_jd + search_years * 365.25
    if flat(end_jd):
        return None

    inside, outside = start_jd, end_jd
    while outside - inside > 1.0:
        middle = inside + (outside - inside) // 2
        if middle in (inside, outside):
            break
        if flat(middle):
            inside = middle
        else:
            outside = middle
    if not flat(inside) or flat(outside):
        raise BoundaryNotStable(
            "the offset-handover search produced a pair that does not have the property it "
            "assigned them, so no handover date may be reported from it"
        )

    last_flat = _calendar(inside)
    first_moved = _calendar(outside)
    before = tt_minus_utc(*last_flat)
    after = tt_minus_utc(*first_moved)
    return {
        "section": "table_bound",
        "bound": "constant_offset_handover",
        "date": "%04d-%02d-%02d" % first_moved,
        "last_date_holding_the_constant": "%04d-%02d-%02d" % last_flat,
        "unit": "second",
        "values": [before, after],
        "values_bits": [bits_of(before), bits_of(after)],
        "value_labels": ["last_constant_offset", "first_moved_offset"],
        "step_seconds": after - before,
        "is_whole_second": abs(abs(after - before) - 1.0) < 1e-4,
        "note": (
            "⛔ THE OFFSET IS NOT CONSTANT FOREVER. Past the last insertion the conversion "
            "holds one value exactly — and then, on this day, hands over to a model that "
            "drifts. ⭐ The handover is a jump of about a second that is not a leap second, "
            "is announced nowhere, and falls in the middle of the range a long-dated "
            "calculation would cross"
        ),
    }


def leap_table_bounds(
    first_year: int, last_year: int, steps: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Where the table starts, where it stops, and what the conversion does past the end.

    ⭐ **The end of the table is the finding, and it has two ends.** Past its last insertion
    the conversion goes on answering with a fixed offset and no statement that it has run
    out of table — a prediction that no further second will ever be inserted, which the
    library is in no position to make and does not label as one. ⚠ And that fixed offset is
    itself temporary: see :func:`constant_offset_handover`.
    """
    whole = [row for row in steps if row["is_whole_second"]]
    first_whole = whole[0]["effective_from"] if whole else None
    last_whole = whole[-1]["effective_from"] if whole else None
    at_start = tt_minus_utc(first_year, 1, 1)
    just_after = whole[-1]["values"][1] if whole else None
    at_end = tt_minus_utc(last_year, 1, 1)
    rows: list[dict[str, Any]] = [
        {
            "section": "table_bound",
            "bound": "first_whole_second_step",
            "date": first_whole,
            "unit": "second",
            "values": [at_start],
            "values_bits": [bits_of(at_start)],
            "note": (
                "⚠ the steps before this one are not whole seconds. They are recorded as "
                "found rather than filtered out, because a fractional step is a fact about "
                "how the library treats the era before the table's own regime"
            ),
        },
        {
            "section": "table_bound",
            "bound": "last_whole_second_step",
            "date": last_whole,
            "unit": "second",
            "values": [v for v in (just_after, at_end) if v is not None],
            "values_bits": [
                bits_of(v) for v in (just_after, at_end) if v is not None
            ],
            "value_labels": ["offset_just_after_the_last_insertion", "offset_at_scan_end"],
            "note": (
                "⛔ the conversion answers past this date without a word about having run "
                "out of table. ⭐ Compare the two values: they are NOT the same, so the "
                "answer past the table is not simply the table's last offset held forever"
            ),
        },
    ]
    return rows


def second_sixty_acceptance(dates: tuple[tuple[int, int, int], ...]) -> list[dict[str, Any]]:
    """Whether the conversion accepts the sixty-first second of a minute, per date.

    ⭐ **The table is enforced, not merely consulted.** A leap second the table knows is
    accepted; one it does not know is refused outright rather than absorbed — which means a
    future insertion, once real, arrives as a hard failure in a build whose table predates
    it, rather than as a value that is quietly one second wrong.
    """
    rows: list[dict[str, Any]] = []
    for year, month, day in dates:
        record: dict[str, Any] = {
            "section": "second_sixty",
            "date": f"{year:04d}-{month:02d}-{day:02d}",
            "unit": "julian_day",
        }
        try:
            jd_tt, jd_ut = swe.utc_to_jd(year, month, day, 23, 59, 60.0, swe.GREG_CAL)
        except Exception as exc:
            record.update(
                {
                    "accepted": False,
                    "refusal": f"{type(exc).__name__}: {str(exc)[:200]}",
                    "values": [],
                }
            )
        else:
            record.update(
                {
                    "accepted": True,
                    "values": [float(jd_tt), float(jd_ut)],
                    "values_bits": [bits_of(float(jd_tt)), bits_of(float(jd_ut))],
                    "value_labels": ["dynamical", "universal"],
                }
            )
        rows.append(record)
    return rows


#: The child program that measures the override. ⛔ **It must be a fresh process.** The
#: table is read once and never re-read, so a measurement taken in a process that has
#: already converted anything reports the table that process started with — which is how a
#: first attempt at this measurement concluded, wrongly, that no override existed.
_OVERRIDE_CHILD = """
import sys
import swisseph as swe

path, year, month, day = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4])
if path != "-":
    swe.set_ephe_path(path)
jd_tt, _ = swe.utc_to_jd(year, month, day, 0, 0, 0.0, swe.GREG_CAL)
offset = (jd_tt - swe.julday(year, month, day, 0.0)) * 86400.0
print(repr(offset))
"""


def leap_override_probe(
    *, directory_with_file: str, directory_without_file: str, working_directory: str,
    probe_date: tuple[int, int, int],
) -> list[dict[str, Any]]:
    """Whether a file on disk can replace the built-in table, and from where.

    ⭐ Three fresh processes, differing only in where a file of the documented name sits.
    The answer decides whether the table a deployment used is a property of the **installed
    library** — recoverable from a version pin forever — or of a **directory that
    deployment happened to hold**, which a decommissioned deployment takes with it.

    ⛔ Each reading is taken in a child process for the reason in `_OVERRIDE_CHILD`, and
    nothing is written into the pinned data directory: the file under test sits in a
    directory of its own.
    """
    year, month, day = probe_date

    def child(path: str, cwd: str | None = None) -> float | None:
        result = subprocess.run(
            [sys.executable, "-c", _OVERRIDE_CHILD, path, str(year), str(month), str(day)],
            capture_output=True,
            text=True,
            cwd=cwd,
            check=False,
        )
        if result.returncode != 0:
            return None
        try:
            return float(result.stdout.strip())
        except ValueError:
            return None

    baseline = child(directory_without_file)
    overridden = child(directory_with_file)
    from_working_directory = child("-", cwd=working_directory)

    rows: list[dict[str, Any]] = []
    for case, value, description in (
        (
            "no_file",
            baseline,
            "a directory holding no file of that name — the built-in table answers",
        ),
        (
            "file_in_the_named_directory",
            overridden,
            "⭐ a file of the documented name in the directory the library was pointed at",
        ),
        (
            "file_in_the_working_directory_only",
            from_working_directory,
            "⚠ the same file where a process happens to be running, with no directory named",
        ),
    ):
        rows.append(
            {
                "section": "override",
                "case": case,
                "case_note": description,
                "probe_date": f"{year:04d}-{month:02d}-{day:02d}",
                "unit": "second",
                "values": [] if value is None else [value],
                "values_bits": [] if value is None else [bits_of(value)],
                "measured": value is not None,
                "differs_from_built_in": (
                    None
                    if value is None or baseline is None
                    else abs(value - baseline) > STEP_THRESHOLD_SECONDS
                ),
            }
        )
    rows.append(
        {
            "section": "override",
            "case": "conclusion",
            "case_note": (
                "⭐ the table is replaceable from a file, and only from the directory the "
                "library was explicitly pointed at. ⛔ So a caller that never names such a "
                "directory cannot be carrying a replaced table, and the table it used is a "
                "property of the installed build — reproducible from a version pin, without "
                "the machine that ran it"
                if (
                    overridden is not None
                    and baseline is not None
                    and abs(overridden - baseline) > STEP_THRESHOLD_SECONDS
                    and (
                        from_working_directory is None
                        or baseline is None
                        or abs(from_working_directory - baseline) <= STEP_THRESHOLD_SECONDS
                    )
                )
                else "⚠ the override did not behave as the three cases were built to "
                "distinguish; the rows above are the measurement and this conclusion is "
                "withheld"
            ),
            "unit": "none",
            "values": [],
        }
    )
    return rows


# ======================================================================================
# 5. Which house methods refuse above the polar circle, and whether they say so
# ======================================================================================

#: Every letter a method might be named by.
HOUSE_SYSTEM_LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

#: ⭐ **The controls, and they are what makes this probe work.** These are not house
#: methods and could not be: a punctuation mark, a digit, a lower-case letter. Asking the
#: library for them establishes what it does with a name it does not know — and it was
#: measured **answering** rather than refusing, with numbers identical to a real method's.
#:
#: ⛔ So an inventory built by "call it and see whether it works" is not an inventory. It
#: returns every letter, because every letter works.
HOUSE_SYSTEM_CONTROLS = ("@", "1", "z", "#")


@dataclass(frozen=True)
class SystemClass:
    """A set of method names this build could not be made to distinguish."""

    members: tuple[str, ...]
    contains_control: bool
    samples_agreed: int


def house_system_survey(
    samples: tuple[tuple[float, float], ...], longitude: float, flag: int
) -> tuple[tuple[SystemClass, ...], tuple[str, ...], tuple[str, ...]]:
    """Group method names by the numbers they return, and find the one nobody asked for.

    ⭐ **The question is not "which names does the build accept" — it accepts everything.**
    It is "which names are distinguishable from one another", and the answer is an
    equivalence relation over the cusps they return, taken at several unrelated instants and
    latitudes so a coincidence at one of them cannot create a class.

    ⭐ **The control names carry the finding.** They are not methods, so whichever class
    they land in is the one this build silently answers with when handed a name it does not
    recognise — identified without consulting any documentation, and named here as the
    fallback.

    ⚠ Two names in one class are *indistinguishable over these samples*, which is a weaker
    statement than *the same method*. Some pairs are two published names for one method.
    Returns `(classes, one representative per class, the fallback's members)`.
    """
    names = tuple(HOUSE_SYSTEM_LETTERS) + HOUSE_SYSTEM_CONTROLS
    signature: dict[str, list[tuple[float, ...] | None]] = {name: [] for name in names}
    for jd, latitude in samples:
        for name in names:
            try:
                cusps, _ascmc = swe.houses_ex(jd, latitude, longitude, name.encode(), flag)
            except Exception:
                signature[name].append(None)
                continue
            signature[name].append(tuple(float(c) for c in cusps))

    grouped: dict[tuple[Any, ...], list[str]] = {}
    for name in names:
        grouped.setdefault(tuple(signature[name]), []).append(name)

    classes = tuple(
        SystemClass(
            members=tuple(sorted(members)),
            contains_control=any(m in HOUSE_SYSTEM_CONTROLS for m in members),
            samples_agreed=len(samples),
        )
        for _, members in sorted(grouped.items(), key=lambda item: sorted(item[1]))
    )
    # ⚠ The representative is the first upper-case letter in the class where there is one,
    #   so a class is never represented by a control.
    representatives: list[str] = []
    for item in classes:
        real = [m for m in item.members if m in HOUSE_SYSTEM_LETTERS]
        if real:
            representatives.append(real[0])
    fallback = next(
        (item.members for item in classes if item.contains_control),
        (),
    )
    return classes, tuple(representatives), tuple(fallback)


def system_class_records(
    classes: tuple[SystemClass, ...], fallback: tuple[str, ...]
) -> list[dict[str, Any]]:
    """The equivalence classes, as fixture rows."""
    return [
        {
            "section": "system_identity",
            "members": list(item.members),
            "member_count": len(item.members),
            "contains_a_name_that_is_not_a_method": item.contains_control,
            "samples_agreed_on": item.samples_agreed,
            "unit": "none",
            "values": [],
            "meaning": (
                "⛔ this class contains a name that could not be a method, so it is what "
                "this build answers with when handed a name it does not recognise. Every "
                "other member of this class is indistinguishable from that fallback here — "
                "including, where present, a real method's own letter"
                if item.contains_control
                else "these names returned identical cusps at every sample. ⚠ "
                "Indistinguishable over these samples is weaker than identical in general, "
                "and some such pairs are two published names for one method"
            ),
            "is_the_fallback_class": tuple(item.members) == tuple(fallback),
        }
        for item in classes
    ]


def polar_house_probe(
    *,
    systems: tuple[str, ...],
    latitudes: tuple[float, ...],
    epochs: list[tuple[str, str, float]],
    longitude: float,
    mode: Mode,
    session: Session,
) -> list[dict[str, Any]]:
    """Every method at every latitude: answered, or refused, and identical to what.

    ⭐ **The silent-substitution check is the point.** A method that is undefined at a
    latitude may refuse, or may quietly answer with a different method's numbers. So every
    answer is compared against every other method's answer at the same instant and place,
    and a match is recorded — a method whose cusps are another method's cusps has not
    computed what its name says.
    """
    rows: list[dict[str, Any]] = []
    for epoch_id, stratum, jd in epochs:
        for latitude in latitudes:
            session.reset()
            try:
                assert_window(
                    mode, body=swe.SUN, jd_start=jd, jd_end=jd, where=f"houses/{epoch_id}"
                )
            except Exception:
                continue
            answers: dict[str, tuple[float, ...]] = {}
            refusals: dict[str, str] = {}
            for letter in systems:
                session.reset()
                try:
                    cusps, _ascmc = swe.houses_ex(
                        jd, latitude, longitude, letter.encode(), mode.flag
                    )
                except Exception as exc:
                    refusals[letter] = f"{type(exc).__name__}: {str(exc)[:160]}"
                    continue
                answers[letter] = tuple(float(c) for c in cusps)

            for letter in systems:
                identical = sorted(
                    other
                    for other, values in answers.items()
                    if other != letter and letter in answers and values == answers[letter]
                )
                row: dict[str, Any] = {
                    "section": "system_at_latitude",
                    "epoch_id": epoch_id,
                    "stratum": stratum,
                    "jd_ut": jd,
                    "jd_ut_bits": bits_of(jd),
                    "utc": calendar_ut(jd),
                    "house_system_letter": letter,
                    "latitude": latitude,
                    "latitude_bits": bits_of(latitude),
                    "longitude": longitude,
                    "longitude_bits": bits_of(longitude),
                    "answered": letter in answers,
                    "unit": "degree",
                }
                if letter in answers:
                    row["values"] = list(answers[letter])
                    row["values_bits"] = [bits_of(v) for v in answers[letter]]
                    row["cusp_count"] = len(answers[letter])
                    row["identical_to"] = identical
                else:
                    row["values"] = []
                    row["refusal"] = refusals[letter]
                rows.append(row)
    return rows


def refusal_boundary(
    *,
    systems: tuple[str, ...],
    epochs: list[tuple[str, str, float]],
    longitude: float,
    mode: Mode,
    session: Session,
) -> list[dict[str, Any]]:
    """The exact latitude at which a method stops answering, north and south.

    ⭐ **Bisected rather than assumed, and taken per epoch, because it moves.** A boundary
    quoted as a round number would hide that: the same method refuses at slightly different
    latitudes at different instants, so it is not a property of the site alone and a site
    close to it can be inside the limit in one century and outside it in another.
    """
    rows: list[dict[str, Any]] = []

    def answers(letter: str, latitude: float, jd: float) -> bool:
        session.reset()
        try:
            swe.houses_ex(jd, latitude, longitude, letter.encode(), mode.flag)
        except Exception:
            return False
        return True

    for epoch_id, stratum, jd in epochs:
        obliquity: float | None = None
        session.reset()
        try:
            nutation, _ = swe.calc_ut(jd, swe.ECL_NUT, mode.flag)
            obliquity = float(nutation[0])
        except Exception:
            obliquity = None
        for letter in systems:
            for hemisphere, sign in (("north", 1.0), ("south", -1.0)):
                inside, outside = 45.0 * sign, 89.9 * sign
                if not answers(letter, inside, jd) or answers(letter, outside, jd):
                    continue  # no boundary in the searched range for this method
                for _ in range(80):
                    middle = (inside + outside) / 2.0
                    if middle in (inside, outside):
                        break
                    if answers(letter, middle, jd):
                        inside = middle
                    else:
                        outside = middle
                # ⛔ Re-verify both ends. A bisection needs a stable predicate, and a search
                #    that reports an interval it has not re-checked is the same defect as a
                #    value recorded without its provenance: it looks like a measurement.
                if not answers(letter, inside, jd) or answers(letter, outside, jd):
                    raise BoundaryNotStable(
                        f"house method {letter!r} at epoch {epoch_id}: the bisected pair "
                        f"({inside!r}, {outside!r}) does not have the property the search "
                        "assigned it, so no boundary may be reported from it"
                    )
                rows.append(
                    {
                        "section": "refusal_boundary",
                        "epoch_id": epoch_id,
                        "stratum": stratum,
                        "jd_ut": jd,
                        "jd_ut_bits": bits_of(jd),
                        "utc": calendar_ut(jd),
                        "house_system_letter": letter,
                        "hemisphere": hemisphere,
                        "unit": "degree",
                        "values": [inside, outside],
                        "values_bits": [bits_of(inside), bits_of(outside)],
                        "value_labels": ["last_latitude_answered", "first_latitude_refused"],
                        "obliquity_of_date": obliquity,
                        "ninety_minus_obliquity": (
                            None if obliquity is None else 90.0 - obliquity
                        ),
                        "boundary_minus_ninety_minus_obliquity": (
                            None if obliquity is None else abs(inside) - (90.0 - obliquity)
                        ),
                    }
                )
    return rows


def refusal_message(
    *, systems: tuple[str, ...], jd: float, latitude: float, longitude: float, flag: int
) -> list[dict[str, Any]]:
    """What each entry point says when the method is undefined at the latitude.

    ⛔ **The two entry points do not say the same thing, and the difference is the finding.**
    One reports a bare failure. The other names, in prose, a *different method* that
    answered — so the substitution is discoverable, but only by calling something else, and
    only by reading a sentence.
    """
    rows: list[dict[str, Any]] = []
    for letter in systems:
        record: dict[str, Any] = {
            "section": "entry_point_message",
            "house_system_letter": letter,
            "latitude": latitude,
            "latitude_bits": bits_of(latitude),
            "jd_ut": jd,
            "jd_ut_bits": bits_of(jd),
            "unit": "none",
            "values": [],
        }
        for entry_point, call in (
            ("houses_ex", lambda: swe.houses_ex(jd, latitude, longitude, letter.encode(), flag)),
            ("houses_ex2", lambda: swe.houses_ex2(jd, latitude, longitude, letter.encode(), flag)),
        ):
            try:
                call()
            except Exception as exc:
                record[f"{entry_point}_outcome"] = "refused"
                record[f"{entry_point}_message"] = str(exc)[:200]
            else:
                record[f"{entry_point}_outcome"] = "answered"
                record[f"{entry_point}_message"] = ""
        rows.append(record)
    return rows


# ======================================================================================


def bits_of(value: float) -> str:
    """The bit pattern of a double. Re-exported so a probe never imports two writers."""
    from .fixture import bits

    return bits(value)
