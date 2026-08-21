"""R3 - Swiss Ephemeris values, recorded once per ephemeris source.

Two fixtures of the same grid, one per ephemeris the library was asked for, plus a third
recording which of its entry points can be asked what actually answered.

⭐ **Every value in these files carries an assertion of its source, and no value is written
without one.** The library substitutes a different ephemeris, silently and successfully,
when the one requested is unavailable or does not cover the date. A row that could not be
attributed is recorded as a substitution in the header and is **not** written as a value --
so the two files can be compared without the comparison quietly becoming one ephemeris
against itself.

⚠ **Five of the six entry points sampled here return no usable source at all**: three
return no flag, one returns a flag that merely echoes the request, and one takes no
ephemeris argument in the first place. Among them are the house cusps and the rise/set
times -- which is to say the ascendant and the sunrise. Their source is asserted by proxy,
from an entry point that does report, at both ends of the interval the call may read; the
proxy is recorded on every row that relies on one.

⛔ **And for the time offset even that is refused.** `deltat_ex` and `deltat` consult an
ephemeris -- their answers move with one, measurably -- and return a bare float. The only
channel carrying anything about the basis is the tidal-acceleration constant in force, and
the library's own names for it give one number to two different sources and give the number
an actual data file puts in force to none of them. ⭐ So no `ephemeris_basis` is written for
either, and **the impossibility is published as the finding** rather than papered over with
a plausible name.

⛔ **Recorder, never explainer.** This script calls the library and writes down what it
returned, under which flags, and with what evidence of source. It contains no account of
how any ephemeris is evaluated.
"""

from __future__ import annotations

import argparse
import sys
import tempfile
from importlib.metadata import version as _distribution_version
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import swisseph as swe  # noqa: E402

from saakshi.fixture import (  # noqa: E402
    Header,
    bits,
    describe_reserved_names,
    redact_environment,
    write_jsonl,
)
from saakshi.provenance import generator_for, host_record, today  # noqa: E402
from saakshi.swiss import (  # noqa: E402
    MODES,
    EphemerisSubstitution,
    Mode,
    Session,
    assert_reported,
    assert_window,
    calendar_ut,
    coverage_edges,
    entry_point_records,
    ephe_set_identity,
    offset_attribution,
    source_name,
    state_dependence,
    verify_ephe_set,
)

#: The grid's identity. ⭐ Recorded in `request`; ⛔ never re-rolled -- a fixture whose
#: inputs move is not a fixture.
GRID_SEED = 20260804

#: ⭐ Read from what is installed, never copied from the pin file. A recorded oracle
#: identity that restates an intention rather than an observation is the same defect as a
#: provenance block stamped against a dirty tree: it looks discharged.
BINDING_VERSION = _distribution_version("pyswisseph")

#: ⚠ Julian day of J2000.0 in the library's own convention, used only to name one epoch.
JD_J2000 = 2451545.0

#: Days in a Julian year, for placing epochs relative to a measured coverage edge.
DAYS_PER_YEAR = 365.25

#: The bodies recorded at every epoch.
#:
#: ⭐ Both lunar node conventions are present deliberately. They are the two quantities most
#: likely to separate two ephemeris sources, and a fixture that carried only one of them
#: would understate the difference between the sources it records.
BODIES: tuple[tuple[int, str], ...] = (
    (swe.SUN, "sun"),
    (swe.MOON, "moon"),
    (swe.MERCURY, "mercury"),
    (swe.VENUS, "venus"),
    (swe.MARS, "mars"),
    (swe.JUPITER, "jupiter"),
    (swe.SATURN, "saturn"),
    (swe.URANUS, "uranus"),
    (swe.NEPTUNE, "neptune"),
    (swe.PLUTO, "pluto"),
    (swe.MEAN_NODE, "mean_node"),
    (swe.TRUE_NODE, "true_node"),
)

#: Sites, as geography. ⭐ Chosen for the call paths they exercise, not for where anyone
#: lives: the last two are at and above the polar circle, where one house method is
#: undefined and a day may contain no rising at all. ⚠ The labels are labels.
SITES: tuple[tuple[str, float, float, str], ...] = (
    ("north_inland", 26.4499, 80.3319, "northern subtropics, inland"),
    ("equatorial", -1.2921, 36.8219, "within two degrees of the equator"),
    ("southern_mid", -36.8485, 174.7633, "southern mid-latitude"),
    ("sub_polar", 64.1466, -21.9426, "just below the polar circle"),
    ("polar", 78.2232, 15.6267, "above the polar circle"),
)

#: Two house methods: one undefined at high latitude, one defined everywhere. ⭐ Keeping
#: both means the refusal is recorded beside a value taken at the same instant and place,
#: so a reader can see that the refusal is the method's and not the instant's.
HOUSE_SYSTEMS: tuple[tuple[bytes, str], ...] = ((b"P", "placidus"), (b"W", "whole_sign"))

#: Rising and setting, for the two bodies a calendar is built from.
RISE_EVENTS: tuple[tuple[int, str], ...] = (
    (swe.CALC_RISE, "rise"),
    (swe.CALC_SET, "set"),
)
RISE_BODIES: tuple[tuple[int, str], ...] = ((swe.SUN, "sun"), (swe.MOON, "moon"))

#: ⚠ Recorded as stated inputs on every rise/set row. Zero pressure and zero temperature
#: select a refraction treatment; they are not "no atmosphere", and a fixture that omitted
#: them would be unreproducible for a reason nothing in the file would show.
RISE_ATPRESS = 0.0
RISE_ATTEMP = 0.0

#: Which components of a section's `values` are angles that wrap at 360 degrees. ⛔ A plain
#: subtraction across the wrap reports 360 where the true difference is arc-seconds, which
#: would put the largest number in the file on the pair that agrees best.
ANGULAR: dict[str, Any] = {
    "longitude_tropical": frozenset({0}),
    "longitude_sidereal": frozenset({0}),
    "house_cusps": "all",
    "house_angles": "all",
    "ayanamsha": frozenset(),
    "rise_set": frozenset(),
}

SECTIONS: tuple[str, ...] = tuple(ANGULAR)


# --------------------------------------------------------------------------------------
# The grid, derived from where the data files were measured to stop answering
# --------------------------------------------------------------------------------------


def build_epochs(edges: dict[str, Any]) -> list[tuple[str, str, float]]:
    """`(epoch_id, stratum, jd_ut)`, placed relative to the **measured** coverage edges.

    ⭐ The grid is a function of the edges rather than of a published date range, so a
    different data-file set produces a grid that still straddles its own boundary. A
    hard-coded range would silently stop testing the boundary the moment the files changed.
    """
    low = float(edges["lower_edge_first_inside_jd_ut"])
    high = float(edges["upper_edge_first_inside_jd_ut"])
    low_out = float(edges["lower_edge_last_outside_jd_ut"])
    high_out = float(edges["upper_edge_last_outside_jd_ut"])

    out: list[tuple[str, str, float]] = [
        ("epoch_zero", "epoch_zero", JD_J2000),
        # The edges themselves, from both sides. ⭐ These are the epochs at which a source
        # assertion is the only thing separating a value from a mislabelled one.
        ("edge_lower_inside", "coverage_edge", low),
        ("edge_lower_outside", "coverage_edge", low_out),
        ("edge_upper_inside", "coverage_edge", high),
        ("edge_upper_outside", "coverage_edge", high_out),
        # ⚠ Half a day inside the lower edge: measured to be the region where a rise/set
        #   call started outside coverage and found its event inside it.
        ("edge_lower_plus_half_day", "coverage_edge", low + 0.5),
        ("edge_lower_minus_half_day", "coverage_edge", low - 0.5),
    ]

    for years, tag in ((100.0, "century"), (300.0, "three_centuries")):
        out.append((f"before_coverage_{tag}", "outside_coverage", low - years * DAYS_PER_YEAR))
        out.append((f"after_coverage_{tag}", "outside_coverage", high + years * DAYS_PER_YEAR))

    # A deterministic spread strictly inside coverage.
    span = high - low
    for i in range(12):
        fraction = (i + 0.5) / 12.0
        out.append((f"in_coverage_{i:02d}", "in_coverage", low + fraction * span))

    return out


# --------------------------------------------------------------------------------------
# Sampling one mode
# --------------------------------------------------------------------------------------


def _values_row(
    *,
    section: str,
    epoch_id: str,
    stratum: str,
    jd: float,
    unit: str,
    values: list[float],
    assertion: dict[str, Any],
    identity: dict[str, Any],
) -> dict[str, Any]:
    return {
        "section": section,
        "epoch_id": epoch_id,
        "stratum": stratum,
        "jd_ut": jd,
        "jd_ut_bits": bits(jd),
        "utc": calendar_ut(jd),
        **identity,
        "unit": unit,
        "values": values,
        "values_bits": [bits(v) for v in values],
        "source_assertion": assertion,
    }


def sample_mode(
    mode: Mode, epochs: list[tuple[str, str, float]], session: Session
) -> dict[str, Any]:
    """Call every entry point at every grid point, and attribute or refuse each result.

    ⛔ **The library's state is reset before each recorded call group**, so a row is a
    function of its own request rather than of where the generator had got to. Measured:
    without the reset, the ephemeris that answers a given instant changes after a single
    unrelated call, and sweeping a range in the two directions moved the boundary ten days.
    Within a group the calls run in one session on purpose -- a proxy must observe the same
    state as the call it stands for.
    """
    rows: list[dict[str, Any]] = []
    substitutions: list[dict[str, Any]] = []
    refusals: list[dict[str, Any]] = []
    by_key: dict[str, tuple[str, list[float]]] = {}

    def keep(row: dict[str, Any], key: str) -> None:
        rows.append(row)
        by_key[key] = (str(row["section"]), [float(v) for v in row["values"]])

    def substituted(section: str, epoch_id: str, where: str, exc: Exception) -> None:
        # ⛔ Recorded, never written as a value. A substituted result is a valid value of an
        #    ephemeris nobody asked for, and filing it under the requested one is exactly
        #    the mislabelling this generator exists to prevent.
        substitutions.append(
            {
                "section": section,
                "epoch_id": epoch_id,
                "where": where,
                # ⛔ Redact before truncating. The other order can cut a path in half and
                #    leave the half that still names the machine.
                "detail": redact_environment(str(exc))[:300],
            }
        )

    def refused(section: str, epoch_id: str, where: str, exc: Exception) -> None:
        refusals.append(
            {
                "section": section,
                "epoch_id": epoch_id,
                "where": where,
                "error": type(exc).__name__,
                "detail": redact_environment(str(exc))[:200],
            }
        )

    for epoch_id, stratum, jd in epochs:
        # --- positions: the one entry point that reports its own source -----------------
        for section, extra in (
            ("longitude_tropical", 0),
            ("longitude_sidereal", swe.FLG_SIDEREAL),
        ):
            for body, body_name in BODIES:
                where = f"{mode.id}/{section}/{epoch_id}/{body_name}"
                session.reset()
                try:
                    xx, returned = swe.calc_ut(
                        jd, body, mode.flag | swe.FLG_SPEED | extra
                    )
                except Exception as exc:
                    refused(section, epoch_id, where, exc)
                    continue
                try:
                    assertion = assert_reported(mode, returned, where=where)
                except EphemerisSubstitution as exc:
                    substituted(section, epoch_id, where, exc)
                    continue
                keep(
                    _values_row(
                        section=section,
                        epoch_id=epoch_id,
                        stratum=stratum,
                        jd=jd,
                        unit="degree, degree, au, degree/day, degree/day, au/day",
                        values=[float(v) for v in xx],
                        assertion=assertion,
                        identity={"body": body_name, "body_number": body},
                    ),
                    f"longitude|{section}|{epoch_id}|{body_name}",
                )

        # --- the ayanamsha: an entry point whose returned flag is the request ------------
        where = f"{mode.id}/ayanamsha/{epoch_id}"
        session.reset()
        try:
            assertion = assert_window(
                mode, body=swe.SUN, jd_start=jd, jd_end=jd, where=where
            )
        except EphemerisSubstitution as exc:
            substituted("ayanamsha", epoch_id, where, exc)
        except Exception as exc:
            refused("ayanamsha", epoch_id, where, exc)
        else:
            echoed, value = swe.get_ayanamsa_ex_ut(jd, mode.flag)
            keep(
                _values_row(
                    section="ayanamsha",
                    epoch_id=epoch_id,
                    stratum=stratum,
                    jd=jd,
                    unit="degree",
                    values=[float(value)],
                    assertion={
                        **assertion,
                        # ⛔ Recorded so nobody mistakes it for evidence. This flag was
                        #    measured coming back unchanged from a request the library
                        #    could not have honoured.
                        "returned_flag_is_an_echo": echoed,
                    },
                    identity={"sidereal_mode": "lahiri"},
                ),
                f"ayanamsha|{epoch_id}",
            )

        # --- houses and rise/set: entry points that return no source at all -------------
        for site_id, latitude, longitude, site_label in SITES:
            site_identity = {
                "site": site_id,
                "site_label": site_label,
                "latitude": latitude,
                "latitude_bits": bits(latitude),
                "longitude": longitude,
                "longitude_bits": bits(longitude),
            }

            for hsys, hsys_name in HOUSE_SYSTEMS:
                where = f"{mode.id}/houses/{epoch_id}/{site_id}/{hsys_name}"
                session.reset()
                try:
                    assertion = assert_window(
                        mode, body=swe.SUN, jd_start=jd, jd_end=jd, where=where
                    )
                except EphemerisSubstitution as exc:
                    substituted("house_cusps", epoch_id, where, exc)
                    substituted("house_angles", epoch_id, where, exc)
                    continue
                except Exception as exc:
                    refused("house_cusps", epoch_id, where, exc)
                    refused("house_angles", epoch_id, where, exc)
                    continue
                try:
                    cusps, ascmc = swe.houses_ex(jd, latitude, longitude, hsys, mode.flag)
                except Exception as exc:
                    # ⚠ A method that is undefined at this latitude. Recorded as a fact
                    #   about the library, not as an error in this recorder.
                    refused("house_cusps", epoch_id, where, exc)
                    continue
                identity = {**site_identity, "house_system": hsys_name}
                keep(
                    _values_row(
                        section="house_cusps",
                        epoch_id=epoch_id,
                        stratum=stratum,
                        jd=jd,
                        unit="degree",
                        values=[float(v) for v in cusps],
                        assertion=assertion,
                        identity=identity,
                    ),
                    f"house_cusps|{epoch_id}|{site_id}|{hsys_name}",
                )
                keep(
                    _values_row(
                        section="house_angles",
                        epoch_id=epoch_id,
                        stratum=stratum,
                        jd=jd,
                        unit="degree",
                        values=[float(v) for v in ascmc],
                        assertion=assertion,
                        identity=identity,
                    ),
                    f"house_angles|{epoch_id}|{site_id}|{hsys_name}",
                )

            for body, body_name in RISE_BODIES:
                for rsmi, event in RISE_EVENTS:
                    where = f"{mode.id}/rise_set/{epoch_id}/{site_id}/{body_name}/{event}"
                    session.reset()
                    try:
                        code, times = swe.rise_trans(
                            jd,
                            body,
                            rsmi | swe.BIT_DISC_CENTER,
                            (longitude, latitude, 0.0),
                            RISE_ATPRESS,
                            RISE_ATTEMP,
                            mode.flag,
                        )
                    except Exception as exc:
                        refused("rise_set", epoch_id, where, exc)
                        continue
                    if code != 0:
                        # ⚠ No event in the interval searched -- above the polar circle
                        #   that is the answer, not a failure.
                        # ⛔ The time slot is 0.0 here, not a sentinel: an ordinary-looking
                        #   Julian day in 4713 BC. A caller that reads the value without
                        #   reading the return code gets a number, not an error.
                        refusals.append(
                            {
                                "section": "rise_set",
                                "epoch_id": epoch_id,
                                "where": where,
                                "error": "no_event",
                                "detail": f"return code {code}",
                                "time_slot_on_no_event": float(times[0]),
                            }
                        )
                        continue
                    event_jd = float(times[0])
                    if event_jd < jd:
                        # The search runs forward from the instant given. An event before it
                        # is not an event this call found, whatever the return code said.
                        refusals.append(
                            {
                                "section": "rise_set",
                                "epoch_id": epoch_id,
                                "where": where,
                                "error": "event_before_search_start",
                                "detail": f"returned {event_jd!r} for a search from {jd!r}",
                            }
                        )
                        continue
                    # ⭐ The window is the interval the call may have read: from the instant
                    #    it was given to just past the event it found. Both ends must report
                    #    the requested source, because either end alone was measured to be
                    #    insufficient across a coverage edge.
                    try:
                        assertion = assert_window(
                            mode,
                            body=body,
                            jd_start=min(jd, event_jd),
                            jd_end=max(jd, event_jd) + 0.5,
                            where=where,
                        )
                    except EphemerisSubstitution as exc:
                        substituted("rise_set", epoch_id, where, exc)
                        continue
                    except Exception as exc:
                        refused("rise_set", epoch_id, where, exc)
                        continue
                    keep(
                        _values_row(
                            section="rise_set",
                            epoch_id=epoch_id,
                            stratum=stratum,
                            jd=jd,
                            unit="julian_day_ut",
                            values=[event_jd],
                            assertion=assertion,
                            identity={
                                **site_identity,
                                "body": body_name,
                                "body_number": body,
                                "event": event,
                                "disc": "centre",
                                "atpress": RISE_ATPRESS,
                                "attemp": RISE_ATTEMP,
                                "event_utc": calendar_ut(event_jd),
                            },
                        ),
                        f"rise_set|{epoch_id}|{site_id}|{body_name}|{event}",
                    )

    return {
        "rows": rows,
        "substitutions": substitutions,
        "refusals": refusals,
        "by_key": by_key,
    }


# --------------------------------------------------------------------------------------
# Comparing the two modes, over the rows that were attributed on both sides
# --------------------------------------------------------------------------------------


def _component_delta(section: str, index: int, a: float, b: float) -> float:
    angular = ANGULAR[section]
    is_angle = angular == "all" or (angular != "all" and index in angular)
    delta = abs(a - b)
    if is_angle and delta > 180.0:
        delta = 360.0 - delta
    return delta


def compare_modes(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    """Per-section agreement between the two sources, over comparable rows only.

    ⭐ **The exclusion is the point.** A row that either side could not attribute never
    became a value, so it cannot enter this comparison -- which is what stops a pair of
    epochs outside the data files' coverage from contributing a run of exact zeros that
    would read as agreement and mean only that both requests were answered by the same
    substituted ephemeris.
    """
    per_section: dict[str, dict[str, Any]] = {}
    left_keys, right_keys = left["by_key"], right["by_key"]
    shared = sorted(set(left_keys) & set(right_keys))

    for key in shared:
        section, a_values = left_keys[key]
        _, b_values = right_keys[key]
        entry = per_section.setdefault(
            section,
            {"compared": 0, "identical": 0, "max_abs_delta": 0.0, "worst_key": None},
        )
        entry["compared"] += 1
        worst = 0.0
        for index, (a, b) in enumerate(zip(a_values, b_values)):
            worst = max(worst, _component_delta(section, index, a, b))
        if worst == 0.0:
            entry["identical"] += 1
        if worst > entry["max_abs_delta"]:
            entry["max_abs_delta"] = worst
            entry["worst_key"] = key

    only_left = sorted(set(left_keys) - set(right_keys))
    only_right = sorted(set(right_keys) - set(left_keys))
    return {
        "per_section": per_section,
        "rows_compared": len(shared),
        "rows_only_in_one_source": {
            "moshier_only": len(only_left),
            "swiss_file_only": len(only_right),
            "sample": (only_left + only_right)[:10],
        },
        "meaning": (
            "the same grid point answered by two different ephemerides. ⛔ NOT a tolerance "
            "and NOT an error bound: it is the difference between two sources, and neither "
            "of them is an authority over the other. A consumer's band is a separate, "
            "reviewed decision"
        ),
        "why_rows_are_excluded": (
            "a row either source could not attribute was never written as a value, so it "
            "cannot be compared. ⭐ Without that exclusion, every epoch outside the data "
            "files' coverage would contribute an exact zero -- both requests answered by "
            "the same substituted ephemeris -- and the file would report agreement it had "
            "not measured"
        ),
    }


# --------------------------------------------------------------------------------------
# Writing
# --------------------------------------------------------------------------------------


def attribution_by_stratum(
    sampled: dict[str, Any], epochs: list[tuple[str, str, float]]
) -> dict[str, Any]:
    """Where in the grid values could be attributed, and where they could not.

    ⭐ Recorded because the asymmetry is measured rather than expected. Outside the data
    files' coverage most calls are substituted -- but not all of them: at least one body
    needs no data file and is reported as answered by the requested source at every epoch.
    A reader who assumed "outside coverage" and "unattributable" were the same set would be
    wrong about that body, and the count here says so without anyone having to name it.
    """
    strata = {eid: stratum for eid, stratum, _ in epochs}
    out: dict[str, dict[str, Any]] = {}
    for row in sampled["rows"]:
        entry = out.setdefault(
            strata[str(row["epoch_id"])],
            {"written": 0, "substituted": 0, "refused": 0, "bodies_written": set()},
        )
        entry["written"] += 1
        if "body" in row:
            entry["bodies_written"].add(str(row["body"]))
    for name, key in (("substitutions", "substituted"), ("refusals", "refused")):
        for record in sampled[name]:
            entry = out.setdefault(
                strata[str(record["epoch_id"])],
                {"written": 0, "substituted": 0, "refused": 0, "bodies_written": set()},
            )
            entry[key] += 1
    return {
        stratum: {**entry, "bodies_written": sorted(entry["bodies_written"])}
        for stratum, entry in sorted(out.items())
    }


def _oracle(mode: Mode, ephe: dict[str, Any] | None, session: Session) -> dict[str, Any]:
    oracle: dict[str, Any] = {
        "implementation": "Swiss Ephemeris",
        "library_version": swe.version,
        "called_via": {"binding": "pyswisseph", "version": BINDING_VERSION},
        "session": session.identity(),
        "ephemeris_requested": mode.source,
        "ephemeris_requested_note": mode.label,
        "source_assertion": (
            "every row carries how its source was established. ⛔ A row whose source could "
            "not be established was not written; the header lists those instead"
        ),
        "sidereal_mode": "lahiri, with the library's own default reference date",
        "time_scale": "Julian day, Universal Time, as the entry points take it",
        "licence": (
            "the library is AGPL-3.0; it is called here, never redistributed by this "
            "repository"
        ),
    }
    if ephe is not None:
        oracle["data_files"] = ephe
    else:
        oracle["data_files"] = {
            "used": False,
            "note": (
                "this ephemeris reads no data file. ⚠ A data-file path was nevertheless set "
                "for the process, and every row's returned flag was checked, so a row here "
                "is one the library reported as answered analytically"
            ),
        }
    return oracle


def _row_schema() -> dict[str, str]:
    return {
        "section": " | ".join(SECTIONS),
        "epoch_id": "stable id of the epoch within this grid",
        "stratum": "why this epoch is in the grid",
        "jd_ut": "Julian day, Universal Time -- ⚠ display; `jd_ut_bits` is the value",
        "jd_ut_bits": "⭐ IEEE-754 bit pattern; the authoritative form of the input",
        "utc": "the same instant as a calendar string, for reading",
        "body": "the body this row is about, where the section has one",
        "body_number": "the library's own number for that body",
        "site": "stable id of the place, where the section has one",
        "site_label": "⛔ a label; never an input",
        "latitude": "degrees north -- ⚠ display; `latitude_bits` is the value",
        "latitude_bits": "⭐ IEEE-754 bit pattern of the input",
        "longitude": "degrees east -- ⚠ display; `longitude_bits` is the value",
        "longitude_bits": "⭐ IEEE-754 bit pattern of the input",
        "house_system": "the house method, where the section has one",
        "sidereal_mode": "the sidereal reference, where the section has one",
        "event": "rise | set, for the rise/set section",
        "disc": "which part of the disc the event is defined by",
        "atpress": "pressure passed to the rise/set call, as a stated input",
        "attemp": "temperature passed to the rise/set call, as a stated input",
        "event_utc": "the found event as a calendar string, for reading",
        "unit": "the unit of every component of `values`",
        "values": "⚠ display decimals; `values_bits` is the authoritative form",
        "values_bits": "⭐ IEEE-754 bit patterns of the same components",
        "source_assertion": (
            "⭐ how this row's ephemeris was established. `kind` is `reported` when the "
            "entry point returned a source flag, or `proxy_window` when it did not and the "
            "source was asserted at both ends of the interval the call may read. A "
            "`proxy_window` row is weaker evidence and says so"
        ),
    }


def _notes() -> list[str]:
    return [
        "⛔ The library substitutes a different ephemeris, silently and successfully, when "
        "the one requested is unavailable or does not cover the date. Every value here "
        "carries evidence of which one answered; a value that could not be attributed was "
        "not written.",
        "⚠ Only one of the four entry points sampled reports the ephemeris that answered. "
        "The ayanamsha call returns a flag that ECHOES the request -- measured returning a "
        "data-file bit with no data-file path set at all -- and the house and rise/set "
        "calls return no flag whatsoever. A rule that says merely `assert the returned "
        "flag` is satisfied by the echo and learns nothing from it.",
        "⭐ A `proxy_window` assertion is bounded, not sound. It establishes that the whole "
        "interval the call may read was covered by the requested ephemeris; it does not "
        "establish that the call read only inside that interval.",
        "R3 records what one implementation returned under stated flags. ⛔ It is not an "
        "authority on the sky, and a difference between the two files here is a difference "
        "between two ephemerides, not an error in either.",
        "⛔ Every determinism-bearing double carries a hex bit pattern, and the decimal "
        "beside it is display. ⚠ A widely-used JSON library was measured mis-parsing 18.9% "
        "of shortest-round-tripping doubles by up to 2 ULP. ⭐ The inputs matter most: an "
        "output is compared, an input is replayed.",
    ]


def write_mode_fixture(
    *,
    mode: Mode,
    sampled: dict[str, Any],
    epochs: list[tuple[str, str, float]],
    comparison: dict[str, Any],
    edges: dict[str, Any],
    ephe: dict[str, Any] | None,
    session: Session,
    out_dir: Path,
    script: Path,
) -> tuple[Path, int]:
    rows = sampled["rows"]
    sections_present = sorted({str(row["section"]) for row in rows})
    header = Header(
        fixture_kind="numeric_pin",
        reference="R3",
        generator=generator_for(script),
        generated=today(),
        title=f"Swiss Ephemeris values, {mode.source} requested and asserted on every row",
        oracle=_oracle(mode, ephe, session),
        request={
            "grid": "stratified, placed relative to the measured coverage edges",
            "grid_seed": GRID_SEED,
            "epoch_count": len(epochs),
            "strata": sorted({stratum for _, stratum, _ in epochs}),
            "epochs": [
                {"epoch_id": eid, "stratum": stratum, "jd_ut": jd, "jd_ut_bits": bits(jd)}
                for eid, stratum, jd in epochs
            ],
            "bodies": [name for _, name in BODIES],
            "sites": [
                {"site": s, "latitude": la, "longitude": lo, "site_label": lab}
                for s, la, lo, lab in SITES
            ],
            "house_systems": [name for _, name in HOUSE_SYSTEMS],
            "rise_set": {
                "bodies": [name for _, name in RISE_BODIES],
                "events": [name for _, name in RISE_EVENTS],
                "disc": "centre",
                "atpress": RISE_ATPRESS,
                "attemp": RISE_ATTEMP,
            },
            "ephemeris_flag_requested": mode.flag,
            "regenerate": (
                "generators/r3_swiss.py --ephe-path <directory of data files> --out <dir> "
                "-- the tables above fix the grid, and the coverage edges are re-measured"
            ),
        },
        # ⛔ `reference_only` throughout, and it is the honest class. These are the values
        #    one implementation returned under stated flags. Nothing here has been compared
        #    against an authority, so no band exists to declare; a consumer measuring its
        #    own residual against these rows is what would set one, once, as a reviewed
        #    change in that consumer's tree.
        classification={section: {"class": "reference_only"} for section in sections_present},
        budget_row="R3-convention",
        row_schema=_row_schema(),
        summary={
            "rows": len(rows),
            "rows_by_section": {
                section: sum(1 for r in rows if r["section"] == section)
                for section in sections_present
            },
            "source_assertion": {
                "reported": sum(
                    1 for r in rows if r["source_assertion"]["kind"] == "reported"
                ),
                "proxy_window": sum(
                    1 for r in rows if r["source_assertion"]["kind"] == "proxy_window"
                ),
                "meaning": (
                    "how each written value's ephemeris was established. ⚠ A proxy_window "
                    "row relies on a different entry point, because the one that produced "
                    "the value reports no source"
                ),
            },
            "substitutions": {
                "count": len(sampled["substitutions"]),
                "sample": sampled["substitutions"][:20],
                "meaning": (
                    "⛔ calls answered by an ephemeris other than the one requested. Their "
                    "values were NOT written. Each is a value that would have been "
                    "indistinguishable from a correct one in the file"
                ),
            },
            "refusals": {
                "count": len(sampled["refusals"]),
                "sample": sampled["refusals"][:20],
                "meaning": (
                    "a call the library declined, or an event it found none of. Recorded "
                    "because a refusal is a fact about the library; ⚠ NOT an error here"
                ),
            },
            "coverage_edges": edges,
            "attribution_by_stratum": attribution_by_stratum(sampled, epochs),
            "mode_comparison": comparison,
            "host": host_record(),
        },
        notes=_notes(),
    )
    path = out_dir / "swiss" / mode.id / "r3-values.jsonl"
    written = write_jsonl(path, header, rows, declared_sections=sections_present)
    return path, written


def write_audit_fixture(
    *,
    edges: dict[str, Any],
    demonstration: list[dict[str, Any]],
    state_rows: list[dict[str, Any]],
    offset_rows: list[dict[str, Any]],
    session: Session,
    out_dir: Path,
    script: Path,
    ephe: dict[str, Any],
) -> tuple[Path, int]:
    """The audit: which entry points can be asked what answered, and what it costs when none can.

    ⭐ A `provenance_record`, not a `numeric_pin`. It attests a property of the library
    rather than comparing a value against a reference, and the contract's own kind
    discipline is what keeps the two from being confused.
    """
    rows: list[dict[str, Any]] = entry_point_records()
    rows.append(
        {
            "finding": "coverage_edge",
            "note": (
                "where the supplied data files stop answering, located by bisection on the "
                "returned flag of the one entry point that reports it"
            ),
            **{k: v for k, v in edges.items()},
        }
    )
    rows.extend(state_rows)
    rows.extend(offset_rows)
    rows.extend(demonstration)

    header = Header(
        fixture_kind="provenance_record",
        reference="R3",
        generator=generator_for(script),
        generated=today(),
        title="Which Swiss Ephemeris entry points report the ephemeris that answered",
        oracle={
            "implementation": "Swiss Ephemeris",
            "library_version": swe.version,
            "called_via": {"binding": "pyswisseph", "version": BINDING_VERSION},
            "method": (
                "each entry point was called under conditions where the requested "
                "ephemeris was known to be unavailable, and what came back was read"
            ),
            "session": session.identity(),
            "data_files": ephe,
        },
        attests=(
            "which entry points of the ephemeris library report the ephemeris that actually "
            "answered a call, which merely echo the flag they were handed, and which return "
            "no statement of source at all; that the answering ephemeris depends on the "
            "preceding call and not only on the call's own arguments; that for the two "
            "entry points returning the offset from civil to dynamical time NO source can "
            "be stated at all, and why; and what a comparison reports when the substitution "
            "goes unchecked"
        ),
        authority={
            "held_by": "the library itself, as observed",
            "kind": "direct observation of return values under controlled conditions",
            "scope": (
                "⚠ this version of the library and this binding only. A later version may "
                "report differently, which is why the observation is dated and versioned "
                "rather than stated as a property of the software in general"
            ),
        },
        record_date=today(),
        row_schema={
            "finding": (
                "flag_reporting | coverage_edge | state_dependence | "
                "offset_attribution | substitution_demonstration"
            ),
            "sweep": (
                "for a state_dependence row: the order the same instants were visited in, "
                "and whether the library's state was reset between them"
            ),
            "first_substituted_jd_ut": (
                "⭐ where that sweep first saw a substitution. The three sweeps disagree, "
                "and the disagreement is the finding"
            ),
            "ordering_changed_the_answer": (
                "⛔ true when the first call of the naive pair changed which ephemeris "
                "answered the second -- the comparison destroying one of its own operands"
            ),
            "moon_longitude_delta_arcseconds": (
                "the difference the obvious comparison reports: two calls, one session"
            ),
            "moon_longitude_delta_arcseconds_isolated": (
                "⭐ the same difference with each call taken from a reset session. Where "
                "this is non-zero and the one above is zero, the obvious comparison "
                "reported agreement it had not measured"
            ),
            "entry_point": "the library function, for a flag_reporting row",
            "quantity_returned": (
                "⭐ what the entry point returns a value OF. Recorded because the proxy "
                "that stands in for a missing report is a call about a POSITION, and not "
                "every silent entry point returns one"
            ),
            "accepts_ephemeris_flag": "whether the call takes an ephemeris flag at all",
            "reports_answering_ephemeris": (
                "⭐ whether its return value distinguishes the ephemeris that answered from "
                "the one requested"
            ),
            "returns": "the shape of its return value",
            "evidence": "what was observed, and under what conditions",
            "assertion_available": (
                "reported | proxy_window | none -- the strongest source assertion a "
                "recorder can make for this entry point. ⛔ `none` is not a weaker "
                "proxy: it is the refusal owed where nothing was requested"
            ),
            "assertion_caveat": (
                "⛔ what the available assertion does NOT establish. Empty only where "
                "the entry point reports its own source"
            ),
            "row": (
                "for an offset_attribution row: harness_control | per_flag | unflagged | "
                "verdict"
            ),
            "regime": (
                "data_files_present | data_files_absent -- ⚠ the second is a state "
                "`verify_ephe_set` REFUSES for recording, constructed here deliberately "
                "because it is the condition being surveyed"
            ),
            "tidal_constant_in_force": (
                "⭐ the only channel that carries anything at all about what the time "
                "offset was computed from. It is read AFTER the call, from the library"
            ),
            "library_names_for_that_constant": (
                "every name the library itself gives that number, read out of the library "
                "rather than typed here"
            ),
            "sources_that_constant_could_name": (
                "⛔ THE REFUSAL, IN THE LIBRARY'S OWN VOCABULARY. Which of the three "
                "ephemeris sources the constant could belong to. Two entries hold one "
                "number, and the number an actual data file puts in force belongs to none "
                "of them"
            ),
            "position_call_under_the_same_flag_answered_by": (
                "⚠ EVIDENCE, NEVER A BASIS. What a reporting call answered under the "
                "same flag in the same session state. It is a fact about a position"
            ),
            "agreement_verdict": (
                "which of the three ways the constant fails to corroborate the reported "
                "source, or that it corroborates it"
            ),
            "equals_the_flagged_answer_for": (
                "⭐ for the unflagged entry point: which flagged answer it silently "
                "turned out to be. A caller who never passed a flag has still chosen one"
            ),
            "this_epoch_has_the_property_under_test": (
                "⛔ whether the ephemeris flag changes the offset AT THIS EPOCH. It "
                "does not everywhere, and a survey confined to where it does not would "
                "report no dependence and would look exactly like one that found none"
            ),
            "ephemeris_basis": (
                "⛔ ALWAYS A REFUSAL ON THESE ROWS, and the refusal is the finding. No "
                "honest value exists for this field for either offset entry point"
            ),
        },
        notes=[
            "⭐ THE POINT OF THIS FILE. A rule that says `assert the returned flag` is "
            "necessary and not sufficient: one entry point here returns a flag that is the "
            "request handed back, and two return no flag at all. Among the silent ones are "
            "the house cusps and the rise/set times.",
            "⛔ AND THE FLAG MUST BE READ PER CALL, because the ephemeris that answers is "
            "not a function of the call's arguments. The same instant, body and flags were "
            "answered by the data files in a fresh session, by the substituted ephemeris "
            "after one unrelated call outside coverage, and by the data files again after "
            "one call inside it. Sweeping a range upwards and downwards moved the apparent "
            "boundary by ten days. ⚠ So a recorder that decides once which instants are "
            "covered, and then trusts that decision, is wrong across that whole interval.",
            "⛔ An unchecked comparison between two ephemerides degenerates exactly where it "
            "matters most -- outside the data files' coverage both requests are answered by "
            "the same substituted ephemeris, so the difference is identically zero and reads "
            "as perfect agreement.",
            "⛔⛔ THE TIME OFFSET CANNOT BE ATTRIBUTED AT ALL, AND THAT IS THIS FILE'S "
            "NEWEST FINDING RATHER THAN A GAP IN IT. `deltat_ex` and `deltat` return a bare "
            "float -- no flag, no code, no error channel -- and their answers move with the "
            "ephemeris anyway. The only channel carrying anything about the basis is the "
            "tidal-acceleration constant in force, and it is not an identifier: the "
            "library's own names give ONE number to both file-backed sources, and the "
            "number an actual pinned data file puts in force is the named constant of no "
            "source at all. ⭐ So `ephemeris_basis` is a refusal on every offset row, and "
            "the proxy that stands in its place for the flagged entry point is recorded as "
            "a bound on a window and ⛔ never as the value's source.",
            "⛔ ONE FLAG, ONE SESSION, ONE INSTANT -- AND THE OFFSET AND THE POSITION DID "
            "NOT REST ON THE SAME EPHEMERIS. With the data files removed, a data-file "
            "request for a position was reported as answered by the analytical ephemeris "
            "while the offset under that same flag was computed on the library's default "
            "constant, which is not the analytical one. ⚠ So a proxy taken from a "
            "reporting position call bounds the window and establishes nothing about what "
            "the offset was computed from.",
            "⛔ AND THE ONE ENTRY POINT HERE THAT TAKES NO EPHEMERIS ARGUMENT HAS AN "
            "EPHEMERIS ANYWAY. `deltat` returned two different numbers for one instant with "
            "nothing changed but a directory path handed to an unrelated call. ⭐ A caller "
            "who never passed a flag has still chosen one, and this file records which.",
            "⚠ The binding documents that calling `deltat_ex` before any path is set "
            "'will raise'. Measured, it returns a value computed on the default constant. A "
            "recorder relying on that documented refusal to notice that no ephemeris was "
            "established gets a plausible number instead.",
            "⭐ THE CONTROLS SIT INSIDE THE OFFSET SURVEY, because a silence and a deaf "
            "reader are the same observation from outside. The same blind reader is run "
            "over a return known to carry a flag, over one carrying an integer that is not "
            "a flag, and over the two bare floats; the survey refuses a grid on which the "
            "ephemeris flag changes nothing, AND refuses one on which it always does.",
            "⚠ Dated and versioned deliberately. This is an observation of one release "
            "through one binding, not a claim about the software in general.",
        ],
    )
    path = out_dir / "swiss" / "r3-flag-reporting.jsonl"
    written = write_jsonl(path, header, rows)
    return path, written


# --------------------------------------------------------------------------------------
# The demonstration: what the unchecked comparison would have reported
# --------------------------------------------------------------------------------------


def substitution_demonstration(
    epochs: list[tuple[str, str, float]], session: Session
) -> list[dict[str, Any]]:
    """Compare the two modes **without** asserting anything, and record what that reports.

    ⭐ This is the counter-measurement that justifies the whole mechanism. The same two
    requests are compared twice over the same grid: once the obvious way -- call one, call
    the other, subtract -- and once with each call taken from a reset session.

    ⛔ **The two comparisons do not agree, and the obvious one is the wrong one.** Where the
    data files do not cover the epoch, both requests are answered by the same ephemeris and
    the difference is exactly zero; the zero is not agreement, it is the comparison not
    having happened. ⚠ And at the boundary it is worse than that: the *first* call of the
    pair changes which ephemeris answers the second, so the act of computing the comparison
    destroys one of its own operands.
    """
    moshier, swiss_file = MODES["moshier"], MODES["swiss_file"]
    source_bits = swe.FLG_SWIEPH | swe.FLG_MOSEPH | swe.FLG_JPLEPH
    out: list[dict[str, Any]] = []

    def sunrise(jd: float, mode_flag: int) -> tuple[int, float]:
        code, times = swe.rise_trans(
            jd, swe.SUN, swe.CALC_RISE | swe.BIT_DISC_CENTER,
            (80.3319, 26.4499, 0.0), RISE_ATPRESS, RISE_ATTEMP, mode_flag,
        )
        return code, float(times[0])

    for epoch_id, stratum, jd in epochs:
        if stratum not in ("in_coverage", "outside_coverage", "coverage_edge"):
            continue
        try:
            # --- the comparison as anyone would write it: one session, two calls ---------
            session.reset()
            naive_a, _ = swe.calc_ut(jd, swe.MOON, moshier.flag | swe.FLG_SPEED)
            naive_b, naive_ret = swe.calc_ut(jd, swe.MOON, swiss_file.flag | swe.FLG_SPEED)
            naive_rise_a = sunrise(jd, moshier.flag)
            naive_rise_b = sunrise(jd, swiss_file.flag)

            # --- the same comparison with each call taken from a reset session -----------
            session.reset()
            iso_a, _ = swe.calc_ut(jd, swe.MOON, moshier.flag | swe.FLG_SPEED)
            session.reset()
            iso_b, iso_ret = swe.calc_ut(jd, swe.MOON, swiss_file.flag | swe.FLG_SPEED)
            session.reset()
            iso_rise_a = sunrise(jd, moshier.flag)
            session.reset()
            iso_rise_b = sunrise(jd, swiss_file.flag)
        except Exception:
            continue
        # ⚠ All four searches must have found an event, or the row compares a time against
        #   the 0.0 the library leaves in the slot when it found none.
        if any(code != 0 for code, _ in (naive_rise_a, naive_rise_b, iso_rise_a, iso_rise_b)):
            continue

        naive_delta = _component_delta(
            "longitude_tropical", 0, float(naive_a[0]), float(naive_b[0])
        )
        iso_delta = _component_delta(
            "longitude_tropical", 0, float(iso_a[0]), float(iso_b[0])
        )
        naive_honoured = (naive_ret & source_bits) == swiss_file.flag
        iso_honoured = (iso_ret & source_bits) == swiss_file.flag
        out.append(
            {
                "finding": "substitution_demonstration",
                "epoch_id": epoch_id,
                "stratum": stratum,
                "jd_ut": jd,
                "jd_ut_bits": bits(jd),
                "utc": calendar_ut(jd),
                "data_file_request_honoured": naive_honoured,
                "data_file_request_honoured_when_isolated": iso_honoured,
                # ⭐ When these two disagree, the first call of the pair changed which
                #    ephemeris answered the second.
                "ordering_changed_the_answer": naive_honoured != iso_honoured,
                "moon_longitude_delta_degrees": naive_delta,
                "moon_longitude_delta_arcseconds": naive_delta * 3600.0,
                "moon_longitude_delta_arcseconds_isolated": iso_delta * 3600.0,
                "sunrise_delta_seconds": (naive_rise_b[1] - naive_rise_a[1]) * 86400.0,
                "sunrise_delta_seconds_isolated": (
                    iso_rise_b[1] - iso_rise_a[1]
                ) * 86400.0,
                "reading": (
                    "the two requests were answered by different ephemerides, so this "
                    "difference is a measurement"
                    if naive_honoured
                    else "⛔ the data-file request was substituted, so both sides are the "
                    "SAME ephemeris and this difference is not a measurement of anything"
                ),
            }
        )
    return out


# --------------------------------------------------------------------------------------
# ⛔ The time offset: the two entry points the survey did not reach
# --------------------------------------------------------------------------------------

#: The epochs the offset survey runs on, by calendar year. ⛔ **Both are load-bearing and
#: for opposite reasons.** Before the modern record the offset is extrapolated from a
#: tidal-acceleration constant, so the ephemeris flag moves it; at a tabulated instant all
#: three flags return one number. A survey confined to the second kind would report no
#: dependence and would be indistinguishable from one that looked and found none, so the
#: grid carries a case of each and `offset_attribution` refuses a grid that does not.
OFFSET_EPOCH_YEARS: tuple[int, ...] = (1900, 2000)


def offset_survey(session: Session, ephe_path: Path) -> list[dict[str, Any]]:
    """Survey `deltat_ex` and `deltat`, then put the library back and check that it went.

    ⚠ **The second regime is a state this repository refuses to record in.**
    `verify_ephe_set` rejects a directory with no data file precisely because every
    data-file request would then be answered analytically without a word — which is the
    condition being surveyed here, so it is constructed on purpose, held in a temporary
    directory, and never named in the fixture.

    ⛔ **The restoration is measured, not assumed.** Leaving the library pointed at an empty
    directory would make every later call analytical and successful. The check is the tidal
    constant and a reporting call, read back after the survey: both must be what they were.
    """
    before_constant = float(swe.get_tid_acc())
    session.reset()
    _, before_flag = swe.calc_ut(JD_J2000, swe.SUN, swe.FLG_SWIEPH | swe.FLG_SPEED)

    epochs = [
        (f"year_{year}", float(swe.julday(year, 1, 1, 0.0))) for year in OFFSET_EPOCH_YEARS
    ]
    with tempfile.TemporaryDirectory() as empty:
        rows = offset_attribution(
            epochs=epochs,
            with_files=session,
            without_files=Session(ephe_path=empty, sidereal_mode=session.sidereal_mode),
        )

    session.reset()
    after_constant = float(swe.get_tid_acc())
    _, after_flag = swe.calc_ut(JD_J2000, swe.SUN, swe.FLG_SWIEPH | swe.FLG_SPEED)
    if after_constant != before_constant or after_flag != before_flag:
        raise EphemerisSubstitution(
            "offset_survey: the library did not come back. The tidal constant read "
            f"{before_constant!r} before the survey and {after_constant!r} after it, and a "
            f"data-file request was answered by {source_name(before_flag)} before and "
            f"{source_name(after_flag)} after. ⛔ Every later measurement in this run would "
            "have been taken against the wrong ephemeris, successfully and silently."
        )
    return rows


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

    # ⛔ Before any data-file request. Without this the library answers every one of them
    #    analytically, successfully, and without saying so. ⚠ The sidereal mode belongs to
    #    the same state, and closing the library drops it -- so both live in one object that
    #    re-applies them together.
    session = Session(ephe_path=str(args.ephe_path), sidereal_mode=swe.SIDM_LAHIRI)
    session.reset()

    swiss_file = MODES["swiss_file"]
    edges = coverage_edges(
        swiss_file,
        body=swe.MOON,
        jd_low=swe.julday(1000, 1, 1, 0.0),
        jd_high=swe.julday(3000, 1, 1, 0.0),
        session=session,
    )
    print(
        "coverage measured: "
        f"{edges['lower_edge_calendar_ut']} .. {edges['upper_edge_calendar_ut']}"
    )

    state_rows = state_dependence(
        swiss_file,
        body=swe.MOON,
        jd_first_outside=float(edges["upper_edge_last_outside_jd_ut"]),
        session=session,
    )
    sweeps = {
        str(row["sweep"]): row.get("first_substituted_jd_ut")
        for row in state_rows
        if row["sweep"] != "single_intervening_call"
    }
    print("state dependence: first substitution seen at " + ", ".join(
        f"{name}={value!r}" for name, value in sorted(sweeps.items())
    ))
    flip = next(row for row in state_rows if row["sweep"] == "single_intervening_call")
    print(
        "state dependence: one instant answered by the request "
        f"fresh={flip['answered_by_request_when_fresh']} "
        f"after_outside_call={flip['answered_by_request_after_a_call_outside_coverage']} "
        f"after_inside_call={flip['answered_by_request_after_a_call_inside_coverage']}"
    )

    epochs = build_epochs(edges)
    print(f"epochs: {len(epochs)}   bodies: {len(BODIES)}   sites: {len(SITES)}")

    sampled = {
        mode_id: sample_mode(MODES[mode_id], epochs, session)
        for mode_id in ("moshier", "swiss_file")
    }
    for mode_id, result in sampled.items():
        print(
            f"{mode_id}: {len(result['rows'])} row(s), "
            f"{len(result['substitutions'])} substitution(s), "
            f"{len(result['refusals'])} refusal(s)"
        )

    comparison = compare_modes(sampled["moshier"], sampled["swiss_file"])
    print(f"comparable rows: {comparison['rows_compared']}")
    for section in sorted(comparison["per_section"]):
        entry = comparison["per_section"][section]
        print(
            f"    {section}: {entry['identical']}/{entry['compared']} identical, "
            f"worst {entry['max_abs_delta']!r}"
        )

    # ⛔ The ordered prerequisite: the two entry points the survey did not reach.
    #    Run LAST among the measurements, because the second regime it needs is one this
    #    repository otherwise refuses -- a directory with no data file in it -- and nothing
    #    after this point may be measured in that state. ⭐ The real session is restored
    #    and the restoration is CHECKED rather than assumed.
    offset_rows = offset_survey(session, args.ephe_path)
    verdict = next(row for row in offset_rows if row["row"] == "verdict")
    print(
        "offset attribution: "
        f"{verdict['combinations_where_the_constant_identifies_one_source']} of "
        f"{sum(1 for r in offset_rows if r['row'] == 'per_flag')} flag/regime "
        "combinations let the tidal constant name one source; "
        f"{verdict['combinations_where_it_and_the_position_report_disagree']} disagree "
        "with the reporting call"
    )
    for epoch_id, moved in sorted(
        verdict["unflagged_entry_point_moved_between_the_two_regimes_seconds"].items()
    ):
        print(
            f"    deltat (no flag) at {epoch_id}: moved {moved!r} s between the two regimes"
        )

    demonstration = substitution_demonstration(epochs, session)
    unchecked_zeros = sum(
        1
        for row in demonstration
        if not row["data_file_request_honoured"] and row["sunrise_delta_seconds"] == 0.0
    )
    print(
        f"unchecked comparison: {len(demonstration)} epoch(s), "
        f"{unchecked_zeros} of them reporting an exact zero because both sides were "
        "the same substituted ephemeris"
    )

    for mode_id, result in sampled.items():
        mode = MODES[mode_id]
        path, written = write_mode_fixture(
            mode=mode,
            sampled=result,
            epochs=epochs,
            comparison=comparison,
            edges=edges,
            ephe=ephe if mode.needs_data_files else None,
            session=session,
            out_dir=args.out,
            script=script,
        )
        print(f"wrote {written} rows -> {path}")

    path, written = write_audit_fixture(
        edges=edges,
        demonstration=demonstration,
        state_rows=state_rows,
        offset_rows=offset_rows,
        session=session,
        out_dir=args.out,
        script=script,
        ephe=ephe,
    )
    print(f"wrote {written} rows -> {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
