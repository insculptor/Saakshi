"""The library's nutation and obliquity pseudo-body through calc, as a comparison section of one component, and the three controls it rests on.

Two files, written together from one clean commit, in the mean node's section's shape (``mean_node_section.py``),
whose epochs, directories, child program, admission rule, configuration identity and shared controls are used here
**by import** — ⛔ never by copy:

* a ``numeric_pin`` with one section — the library's pseudo-body for nutation and obliquity through ``calc`` under
  one declared configuration (the data-file request, the pinned files, and **no** ``FLG_NONUT``: the word is the
  request's ephemeris bit and nothing else), its rows read **warm**, every row in one fresh process in the order
  they are written, ``none`` asserted on every row and the tidal-acceleration constant read back after each call.
  ⭐ A row compares **one** value, the call's first; it carries every value the call returned beside it, nested,
  so that the controls can read them and nothing compares them;
* an R3 ``provenance_record`` of its controls, at **every** row:
  ① **invariance** — the pseudo-body read under each of five configurations, each reading the one call of a fresh
  process, **all its returned values** bit-identical to the row's; beside it a **witness**, the Moon at the same
  instant under the same five, whose returned word names a source other than the request where the request cannot
  answer, differs between two answering sources, and under the section's own configuration is the request
  honoured;
  ② **sufficiency** — the section read again warm in another order, every returned value bit-identical;
  ③ **nutation twin** — the same reading with ``FLG_NONUT`` added, in a fresh process: its first value must differ
  from the row's first, and must equal both its own second and the row's second.

⛔ **Recorder, never explainer.** Nothing here describes how the library computes anything. What each returned
position is called is the library's documentation's naming, quoted beside the values and never checked against
them; that the first value moves with ``FLG_NONUT`` and the second does not is recorded as bits.

⛔ **The rows are the mean node's section's rows**, the same instants derived the same way from a data profile
manifest's declared coverage — never a Julian day typed here. ⚠ Whether an instant lies near a zero of the fourth
returned value (where the twin's first value and the row's first can agree to the bit) is not chosen against
here; it is **measured** at every row and written into the record, and the twin control refuses any row where the
two agree.

⛔ **Refusals, each before anything is written**: everything the mean node's section refuses (a dirty or
commitless tree; a data directory that is not exactly the pinned set; an "empty" directory that is not empty; a
child that did not start without the library loaded, returned other than its readings, came back twice, or whose
recorded calls into the library are not exactly the sequence its rows declare; a reading not at its own part's
epochs and instants, or whose labels are not what they name; a returned word no reading requested; a section row
without its unit; a read-back that differs between rows; a witness failing at any row; a witness the files
answered within a day of its edge); and, of this section: a child whose readings do not carry every returned value
with the named three equal to the first three; a row whose compared value is not its first returned value; any
subject reading differing from its row at any returned position; a sufficiency row differing at any position; a
twin failing either clause; a configuration identity other than the one pinned below. ⚠ These guard honest error,
⛔ not forgery.

Usage::

    python nutation_obliquity_section.py --ephe-path DIR --empty-dir DIR --profile MANIFEST --survey FILE \
        --budget-row ID --out-dir DIR
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import struct
import sys
import tempfile
from fractions import Fraction
from pathlib import Path

HERE = os.path.dirname(os.path.realpath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
# ⛔ Importing the mean node's section must not write its bytecode beside it: an untracked file is a dirty tree,
#    and the commit this record names would not be the tree it ran from.
sys.dont_write_bytecode = True

# ⭐ The section's shape, by import: its epochs, directories, child program and admission rule, its identity, and
#    the controls a section of this shape keeps whatever its body and word.
import mean_node_section as node  # noqa: E402

Refusal = node.Refusal
bits, unbits, patterned = node.bits, node.unbits, node.patterned
CONFIGURATIONS = node.CONFIGURATIONS
SECTION_CONFIGURATION = node.SECTION_CONFIGURATION
ENTRY_POINT = node.ENTRY_POINT
SECTION_UNIT = node.SECTION_UNIT
ARCSECONDS_PER_DEGREE = node.ARCSECONDS_PER_DEGREE

SECTION = "true_obliquity"
OUTPUTS = ("nutation-obliquity-section.jsonl", "nutation-obliquity-section-controls.jsonl")

#: How many values the call returns for this body, every one of them read by the controls.
RETURNED_POSITIONS = 6
#: ⭐ What the library's documentation says each of this body's six returned values is, in its own words. ⚠
#: Recorded as the documentation's naming, ⛔ never checked against the values here (as the modes record does).
VALUE_POSITIONS: tuple[str, ...] = (
    "true obliquity of the Ecliptic (includes nutation)",
    "mean obliquity of the Ecliptic",
    "nutation in longitude",
    "nutation in obliquity",
    "0",
    "0",
)
VALUE_POSITIONS_SOURCE = ("the library's programmer's documentation, section 3.2.4 'Obliquity and nutation' "
                          "(www.astro.com/swisseph/swephprg.htm, read 2026-11-02)")
#: The one compared position, and the two the twin control reads.
COMPARED, MEAN, DELTA_EPSILON = 0, 1, 3

#: ⭐ The configuration's identity its consumer names it by — entry point calc, the data-file request, word 2 (no
#: FLG_NONUT), this library and binding, an explicit path holding the three pinned files, every state reset —
#: pinned here from the consumer's own rendering. ⛔ The generator refuses to write a section whose own rendering of
#: its configuration is anything else.
CONFIGURATION_IDENTITY = "c893013badb8338ed6de303033a6862f0a0564b357da1523f61d6c663bb22ac7"

#: ⭐ The band the consumer's row applies, in the row's unit, declared so that the consumer's reporter reads the
#: section's band as its row's: 0.05 arcsecond is exactly 1/72000 degree, and this is that ratio rounded once to the
#: nearest double. ⛔ Not a measurement and not this instrument's: the measured difference between a row and every
#: other reading of it is in the control record's summary.
CONSUMER_BAND_DEGREES = float(Fraction(1, 72000))


def ulps_apart(a: float, b: float) -> int:
    """How many doubles lie between two positive doubles, counting one end."""
    return abs(struct.unpack(">q", struct.pack(">d", a))[0] - struct.unpack(">q", struct.pack(">d", b))[0])


# ======================================================================================
# The parent — chooses each child's request, records what came back
# ======================================================================================


def every_value(reading: dict) -> list[str]:
    """⛔ A child's reading carries every value its call returned, the named three its first three."""
    values = reading.get("values_bits")
    if not isinstance(values, list) or len(values) != RETURNED_POSITIONS \
            or values[:3] != [reading["longitude_bits"], reading["latitude_bits"], reading["distance_bits"]]:
        raise Refusal(f"a child's reading carries {values!r} beside its named three; every one of the "
                      f"{RETURNED_POSITIONS} returned values, the named three first, is read here")
    return list(values)


def measure(ephe_path: str, empty_dir: str, profile: str, work: str) -> tuple[list[dict], list[dict], dict]:
    """Returns (section rows, control rows, context)."""
    import swisseph as swe

    flag = {name: getattr(swe, constant) for name, constant in node.EPHEMERIS_NAMES}
    nonut = swe.FLG_NONUT
    paths = {"data_files": os.path.abspath(ephe_path), "empty_directory": os.path.abspath(empty_dir)}
    configurations = {name: (eph, state) for name, eph, state in CONFIGURATIONS}
    interval = node.read_interval(profile)
    epochs = node.build_epochs(interval)
    children = node.Children(work)
    c_eph, c_state = configurations[SECTION_CONFIGURATION]
    # ⭐ The data-file request's ephemeris bit, and nothing else: the section's word carries no FLG_NONUT.
    word = flag[c_eph]
    subject, witness = swe.ECL_NUT, swe.MOON

    def warm(order: list[dict]) -> list[dict]:
        return children.run({"path": paths[c_state], "body": subject, "word": word,
                             "jd_bits": [bits(e["jd"]) for e in order]})

    # ---- the section: warm, in row order; and ② the same rows read warm in the reverse order
    section = warm(epochs)
    reversed_order = list(reversed(epochs))
    permuted = dict(zip((e["epoch_id"] for e in reversed_order), warm(reversed_order), strict=True))

    rows = []
    for epoch, reading in zip(epochs, section, strict=True):
        returned_values = every_value(reading)
        rows.append({"section": SECTION, "epoch_id": epoch["epoch_id"], "body": subject,
                     "instant": {"scale": "tt", **patterned("jd", epoch["jd"])}, "unit": SECTION_UNIT,
                     "values": [unbits(returned_values[COMPARED])], "values_bits": [returned_values[COMPARED]],
                     "returned_values": {"values": [unbits(b) for b in returned_values],
                                         "values_bits": returned_values},
                     "state_read_back": {"state": "tidal_acceleration",
                                         **patterned("value", unbits(reading["tidal_constant_after_bits"]))},
                     "source_assertion": {"kind": "none", "reason": "request_invariant"}})

    def cold(control: str, configuration: str, body: int, request: int, epoch: dict, nutation: str,
             role: str | None) -> dict:
        eph, state = configurations[configuration]
        reading = children.run({"path": paths[state], "body": body, "word": request, "jd_bits": [bits(epoch["jd"])]})[0]
        row = {"finding": "configuration_control", "control": control, "entry_point": ENTRY_POINT,
               "configuration": configuration, "epoch_id": epoch["epoch_id"], "body": body,
               "body_name": swe.get_planet_name(body), **patterned("jd", epoch["jd"]), "requested": request,
               "returned": reading["returned"], "ephemeris_requested": eph, "nutation": nutation,
               "path_state": state}
        for key in ("longitude", "latitude", "distance", "tidal_constant_after"):
            row.update(patterned(key, unbits(reading[f"{key}_bits"])))
        if body == subject:
            # ⭐ Every value the call returned, the named three its first three — for the pseudo-body only; the
            #    witness's readings are the mean node's section's witness readings, named three alone.
            returned_values = every_value(reading)
            row["values"], row["values_bits"] = [unbits(b) for b in returned_values], returned_values
        row["call_history"] = "cold_process_per_row"
        if role is not None:
            row["role"] = role
        return row

    controls = []
    for epoch in epochs:
        for configuration, (eph, _state) in configurations.items():
            controls.append(cold("invariance", configuration, subject, flag[eph], epoch, "default", "subject"))
        for configuration, (eph, _state) in configurations.items():
            controls.append(cold("invariance", configuration, witness, flag[eph], epoch, "default", "witness"))
        controls.append(cold("nutation_twin", SECTION_CONFIGURATION, subject, word | nonut, epoch, "nonut", None))
    order = [e["epoch_id"] for e in reversed_order]
    for epoch in epochs:
        regenerated = every_value(permuted[epoch["epoch_id"]])
        # ⛔ No reading's fields on a sufficiency row (body, instant, words, path state): it is the section read
        #    again, never a reading of its own.
        controls.append({"finding": "configuration_control", "control": "sufficiency", "entry_point": ENTRY_POINT,
                         "epoch_id": epoch["epoch_id"], "call_history": "permuted", "call_order": order,
                         "values": [unbits(b) for b in regenerated], "values_bits": regenerated,
                         **patterned("tidal_constant_after",
                                     unbits(permuted[epoch["epoch_id"]]["tidal_constant_after_bits"]))})

    context = {"interval": interval, "epochs": epochs, "flag": flag, "nonut": nonut, "word": word,
               "children": len(children.nonces), "section_returned": [r["returned"] for r in section],
               "subject": subject, "witness": witness,
               "body_names": {subject: swe.get_planet_name(subject), witness: swe.get_planet_name(witness)},
               "library_version": swe.version}
    return rows, controls, context


# ======================================================================================
# The controls a section must pass before either file is written
# ======================================================================================

READING_FIELDS = ("body", "jd_bits", "returned", "path_state")


def check(rows: list[dict], controls: list[dict], context: dict, survey: dict) -> dict:
    """The section's own controls, at every row. Returns the summary; raises Refusal on any that fails."""
    epochs = {e["epoch_id"]: e for e in context["epochs"]}
    configurations = {name: (eph, state) for name, eph, state in CONFIGURATIONS}
    witness = context["witness"]
    # ⭐ The mean node's section's holds, with this section's bits: no non-ephemeris bit for the invariance part
    #    (the section's own word carries none), FLG_NONUT for the twin.
    readings, sufficiency, by = node.held(rows, controls, context, invariance_bits=0, twin_bits=context["nonut"])

    # ⛔ The row's shape: one compared value, which is the first of every value the call returned; and every returned
    #    value carried by every reading of the pseudo-body, its named three the first three.
    returned: dict[str, list[str]] = {}
    for row in rows:
        nested = row.get("returned_values")
        if not isinstance(nested, dict) or set(nested) != {"values", "values_bits"} \
                or not isinstance(nested["values_bits"], list) or len(nested["values_bits"]) != RETURNED_POSITIONS:
            raise Refusal(f"section row {row['epoch_id']} carries no {RETURNED_POSITIONS} returned values")
        if row["values_bits"] != [nested["values_bits"][COMPARED]] \
                or [k for k in row if k.endswith("_bits")] != ["values_bits"]:
            raise Refusal(f"section row {row['epoch_id']} compares other than its first returned value alone")
        returned[row["epoch_id"]] = nested["values_bits"]
    for r in readings:
        if r["body"] != context["subject"]:
            continue
        values = r.get("values_bits")
        if not isinstance(values, list) or len(values) != RETURNED_POSITIONS \
                or values[:3] != [r["longitude_bits"], r["latitude_bits"], r["distance_bits"]]:
            raise Refusal(f"a {r['control']} reading at {r['epoch_id']} under {r['configuration']} does not carry "
                          f"every returned value, its named three first")
    for s in sufficiency:
        if any(field in s for field in READING_FIELDS):
            raise Refusal(f"the sufficiency row at {s['epoch_id']} carries a reading's fields")

    # ⛔ ① (a) — every subject reading bit-identical to its row at every returned position.
    for (control, role, epoch_id, configuration), r in by.items():
        if role == "subject" and r["values_bits"] != returned[epoch_id]:
            moved = [p for p, (a, b) in enumerate(zip(r["values_bits"], returned[epoch_id])) if a != b]
            raise Refusal(f"① (a) fails at {epoch_id}: under {configuration} the pseudo-body differs from its row "
                          f"at position(s) {moved}")

    separations = node.witness_at_every_row(by, context)
    node.inside_the_interval(rows, context)

    # ⛔ ② — the permuted regeneration bit-identical at every position, in an order that differs.
    order = sufficiency[0]["call_order"]
    if order == [r["epoch_id"] for r in rows] or any(s["call_order"] != order for s in sufficiency):
        raise Refusal("② : the regeneration's order is the section's own, or not one order")
    for s in sufficiency:
        if s["values_bits"] != returned[s["epoch_id"]]:
            raise Refusal(f"② fails at {s['epoch_id']}: the permuted regeneration read {s['values_bits']}")

    # ⛔ ③ — the twin with FLG_NONUT added: (i) its first value differs from the row's first; (ii) its first equals
    #    its own second and the row's second.
    separation = []
    for epoch_id in epochs:
        t = by[("nutation_twin", None, epoch_id, SECTION_CONFIGURATION)]["values_bits"]
        row = returned[epoch_id]
        if t[COMPARED] == row[COMPARED]:
            raise Refusal(f"③ (i) fails at {epoch_id}: the reading with FLG_NONUT added equals the row at its first "
                          "value")
        if not t[COMPARED] == t[MEAN] == row[MEAN]:
            raise Refusal(f"③ (ii) fails at {epoch_id}: the twin's first value {t[COMPARED]} is not its own second "
                          f"{t[MEAN]} and the row's second {row[MEAN]}")
        separation.append((epoch_id, abs(unbits(row[COMPARED]) - unbits(t[COMPARED])) * ARCSECONDS_PER_DEGREE,
                           ulps_apart(unbits(row[COMPARED]), unbits(t[COMPARED])),
                           abs(unbits(row[DELTA_EPSILON])) * ARCSECONDS_PER_DEGREE))

    read_back = node.one_read_back(rows, context)
    edge, margin = node.witness_edge(survey, readings, context, subject_noun="the pseudo-body")

    smallest = min(separation, key=lambda s: s[1])
    return {
        "rows": len(rows),
        "readings": len(readings),
        "children": context["children"],
        "invariance": {"subject_readings": sum(1 for r in readings if r.get("role") == "subject"),
                       "positions_read": RETURNED_POSITIONS,
                       "differing_from_their_row_at_any_position": 0},
        "witness": {"body": witness, "readings": sum(1 for r in readings if r.get("role") == "witness"),
                    "smallest_separation_between_two_answering_sources_arcseconds": round(min(separations), 6),
                    "largest_separation_arcseconds": round(max(separations), 6),
                    "returned_word_by_configuration": {
                        c: sorted({by[("invariance", "witness", e, c)]["returned"] for e in epochs})
                        for c in configurations},
                    "smallest_margin_inside_its_coverage_edge_days": round(margin, 6)},
        "subject_returned_word_by_configuration": {
            c: sorted({by[("invariance", "subject", e, c)]["returned"] for e in epochs}) for c in configurations},
        "sufficiency": {"rows": len(sufficiency), "call_history": "permuted", "positions_read": RETURNED_POSITIONS,
                        "identical_to_their_row_at_every_position": len(sufficiency)},
        "nutation_twin": {
            "rows": len(epochs),
            "first_value_differs_from_the_rows_first": len(epochs),
            "first_value_equals_its_own_second_and_the_rows_second": len(epochs),
            "smallest_separation_of_the_first_values": {
                "epoch_id": smallest[0], "arcseconds": round(smallest[1], 9), "doubles_apart": smallest[2]},
            "largest_separation_of_the_first_values_arcseconds": round(max(s[1] for s in separation), 9),
            "smallest_magnitude_of_the_rows_fourth_value_arcseconds": round(min(s[3] for s in separation), 9),
            "meaning": "how far each row's first value lies from its twin's: where the two agree to the bit the "
                       "twin control refuses the row, so the smallest separation is what stood between this "
                       "section and that refusal. ⚠ Measured, ⛔ not a floor"},
        "state_read_back": {"state": "tidal_acceleration", **patterned("value", unbits(next(iter(read_back))))},
        "section_returned_word": context["word"],
        "survey_edge": {"survey_sha256": survey["sha256"], "body": witness,
                        **{f"{end}_bits": bits(v) for end, v in zip(node.EDGE_ENDS, edge)},
                        **dict(zip(node.EDGE_ENDS, edge))},
    }


# ======================================================================================
# The configuration identity — refused unless it is the one pinned
# ======================================================================================


def section_identity(library: tuple[str, str, str], word: int) -> str:
    """The section's configuration identity, refused unless it is :data:`CONFIGURATION_IDENTITY`.

    ⭐ Rendered by the mean node's section's renderer, whose rendering without the word line is held here, too, to
    this repository's shared one — so two renderers agree on everything but the word line before the literal is.
    """
    configuration = node.section_configuration()
    identity = node.configuration_identity(entry_point=ENTRY_POINT, requested="swiss_file", word=word,
                                           library=library, configuration=configuration)
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
    from saakshi.conventions import configuration_sha256

    shared = configuration_sha256(entry_point=ENTRY_POINT, requested="swiss_file", library_version=library[0],
                                  binding=library[1], binding_version=library[2], configuration=configuration)
    without_word = node.configuration_identity(entry_point=ENTRY_POINT, requested="swiss_file", word=None,
                                               library=library, configuration=configuration)
    if shared != without_word:
        raise Refusal(f"the two renderers disagree before the word line: {shared} and {without_word}")
    if identity != CONFIGURATION_IDENTITY:
        raise Refusal(f"the section's configuration renders {identity}, not the pinned {CONFIGURATION_IDENTITY}")
    return identity


# ======================================================================================
# The two files
# ======================================================================================

SECTION_ROW_SCHEMA = {
    "section": "the one section: the call's first returned value for the nutation and obliquity pseudo-body, "
               "through calc",
    "epoch_id": "which instant",
    "body": "the library's own body integer: the pseudo-body for nutation and obliquity",
    "instant": "⭐ the dynamical-time Julian day passed to calc -- `scale` tt, `jd_bits` the value, `jd` display",
    "unit": "⭐ the unit of every component of `values`, `degree`, on every row",
    "values": "[the call's first returned value] in degrees -- ⚠ display; `values_bits` is the value. The "
              "documentation calls it the true obliquity of the ecliptic (header summary.value_positions)",
    "values_bits": "⭐ its bit pattern: the one value the row compares",
    "returned_values": "⭐ every value the call returned, in order -- `values_bits` the values, `values` display; "
                       "the first is the compared value. Nested, so that nothing compares the others: the controls "
                       "read them",
    "state_read_back": "the tidal-acceleration constant read back after the call -- `value_bits` the value",
    "source_assertion": "⭐ `none`, reason `request_invariant`: the pseudo-body's returned word hands the request "
                        "back, and none of its returned values moved with the request across the declared "
                        "configurations (the control record). ⛔ Never `reported`: its word cannot report",
}

CONTROL_ROW_SCHEMA = {
    "finding": "configuration_control",
    "control": "invariance (①) | sufficiency (②) | nutation_twin (③)",
    "role": "for an invariance row: subject (the pseudo-body) | witness (the Moon, at the same instant)",
    "entry_point": "the library function called",
    "configuration_sha256": "the identity of the section's configuration these rows control",
    "configuration": "which configuration of the declared set the reading was taken under",
    "epoch_id": "the section row the reading is at",
    "body": "the library's own body integer",
    "body_name": "the library's own name for it, exactly as returned",
    "jd": "the dynamical-time Julian day passed -- ⚠ display; `jd_bits` is the value",
    "jd_bits": "⭐ the instant's bit pattern, as the call received it",
    "requested": "⭐ the WHOLE word passed",
    "returned": "the whole word the call returned",
    "ephemeris_requested": "moshier | swiss_file | jpl_file -- the source the request names",
    "nutation": "default (no non-ephemeris bit) | nonut (FLG_NONUT and nothing else)",
    "path_state": "data_files (exactly the pinned set) | empty_directory (verified empty)",
    "longitude": "⚠ the call's first returned value, under the name a reading's first value is read by, whatever "
                 "the body -- for the pseudo-body ⛔ not a longitude; `longitude_bits` is the value",
    "longitude_bits": "⭐ its bit pattern",
    "latitude": "⚠ the call's second returned value -- for the pseudo-body ⛔ not a latitude",
    "latitude_bits": "⭐ its bit pattern",
    "distance": "⚠ the call's third returned value -- for the pseudo-body ⛔ not a distance",
    "distance_bits": "⭐ its bit pattern",
    "tidal_constant_after": "the tidal-acceleration constant read back after the call",
    "tidal_constant_after_bits": "⭐ its bit pattern",
    "call_history": "cold_process_per_row (the reading was the only call of a fresh interpreter) | permuted (the "
                    "section read warm, in `call_order`)",
    "call_order": "for a sufficiency row: the section's epochs in the order the regeneration read them",
    "values": "⭐ for a reading of the pseudo-body: every value the call returned, in order, the first three the "
              "named three; for a sufficiency row: every value the regeneration read at the row's epoch -- "
              "`values_bits` the values, the decimals display",
    "values_bits": "⭐ their bit patterns",
}


def refuse_existing(out_dir: str) -> dict[str, str]:
    """The two paths, ⛔ refused if either exists: each emission goes to a new path."""
    paths = {name: os.path.join(out_dir, name) for name in OUTPUTS}
    for path in paths.values():
        if os.path.exists(path):
            raise Refusal(f"{path} exists; each emission goes to a new path")
    return paths


def write_files(rows: list[dict], controls: list[dict], context: dict, summary: dict, out_dir: str,
                budget_row: str) -> dict:
    """Both files through the fixture contract; ⛔ refused if either exists or the identity is not the pinned one."""
    paths = refuse_existing(out_dir)
    fixture, provenance = node._contract()
    from importlib.metadata import version as distribution_version

    generator = provenance.generator_for(Path(__file__))
    host = provenance.host_record()
    binding = distribution_version("pyswisseph")
    library = (context["library_version"], "pyswisseph", binding)
    configuration = node.section_configuration()
    identity = section_identity(library, context["word"])
    for c in controls:
        c["configuration_sha256"] = identity
    controls = [{k: c[k] for k in ("finding", "control", "entry_point", "configuration_sha256")}
                | {k: v for k, v in c.items() if k not in ("finding", "control", "entry_point", "configuration_sha256")}
                for c in controls]
    interval = context["interval"]
    today = provenance.today()
    data_files = {"directory_contents_verified": True, "files": [dict(pin) for pin in node.EPHE_PINS],
                  "unpinned_file_policy": "refused. The library reads the directory, so a file nobody passed can "
                                          "still answer"}
    common = {"implementation": "Swiss Ephemeris", "library_version": library[0],
              "called_via": {"binding": "pyswisseph", "version": binding}, "host": host}
    epochs_summary = {
        "source": "a data profile manifest's declared coverage, read from the file given and converted back to its own "
                  "strings -- never a typed Julian day; the instants inside it are the mean node's section's rows, "
                  "by import: the mean-node record's calc epochs inside the coverage",
        "profile": interval["profile"], "manifest_sha256": interval["manifest_sha256"], "dataset": interval["dataset"],
        "declared_coverage": interval["declared_coverage"],
        **patterned("start_jd", interval["start"]), **patterned("end_jd", interval["end"]),
        "used_as": "dynamical-time Julian days passed to calc; the coverage's scale is TDB and its difference from TT, "
                   "milliseconds, is not applied",
        "count": len(context["epochs"]),
    }
    value_positions = {
        "documented_as": list(VALUE_POSITIONS), "documented_in": VALUE_POSITIONS_SOURCE,
        "compared": COMPARED,
        "meaning": "every row carries all six values the call returned in `returned_values`, and compares the first "
                   "alone; the controls read all six. ⚠ The naming is the documentation's, ⛔ never checked here",
    }
    child = "generators/mean_node_section.py"
    section_header = fixture.Header(
        fixture_kind="numeric_pin", reference="R3", generator=generator, generated=today,
        title="The nutation and obliquity pseudo-body's first returned value through calc, under the data-file "
              "request without FLG_NONUT, read warm",
        oracle={
            **common,
            "session": {"generation": "warm: every row read in one fresh child interpreter (-I), in row order, the "
                                      "library's calls recorded inside it and held to the rows",
                        "child_program": f"{child}'s, at the same commit, by import",
                        "removed_environment_variables": sorted(k for k in os.environ if k.startswith("SE_"))},
            "data_files": data_files,
            "ephemeris_basis": {
                "library_version": library[0], "called_via": {"binding": "pyswisseph", "version": binding},
                "data_files": {"files": [{"dataset": p["dataset"], "sha256": p["sha256"]} for p in node.EPHE_PINS]},
                "sections": {SECTION: {"entry_point": ENTRY_POINT, "requested": "swiss_file",
                                       "returned": "swiss_file", "requested_word": context["word"],
                                       "claimed_class": "request_invariant", "generation": "warm_in_row_order",
                                       "configuration": configuration}},
            },
            "licence": "the library is AGPL-3.0; the generator that wrote this file calls it and redistributes none "
                       "of it",
        },
        request={"entry_point": ENTRY_POINT, "body": context["subject"], "requested_word": context["word"],
                 "configuration": SECTION_CONFIGURATION,
                 "epochs": [{"epoch_id": e["epoch_id"], **patterned("jd", e["jd"])} for e in context["epochs"]],
                 "regenerate": "generators/nutation_obliquity_section.py --ephe-path <the pinned files' directory> "
                               "--empty-dir <an empty directory> --profile <the data profile manifest> --survey <the "
                               "survey> --budget-row <the row's id> --out-dir <a directory>"},
        classification={SECTION: {"class": "tolerance", "band": CONSUMER_BAND_DEGREES, "unit": SECTION_UNIT}},
        budget_row=budget_row,
        row_schema=SECTION_ROW_SCHEMA,
        summary={"configuration_sha256": identity, "epochs": epochs_summary, "value_positions": value_positions,
                 "controls": {"record": OUTPUTS[1], "invariance": summary["invariance"],
                              "sufficiency": summary["sufficiency"], "nutation_twin": summary["nutation_twin"]},
                 "state_read_back": summary["state_read_back"], "returned_word_every_row": summary["section_returned_word"],
                 "classification": "⚠ the band is the one the consumer's row applies, in the row's unit (0.05 "
                                   "arcsecond as 1/72000 degree, rounded once), declared so that the consumer reads "
                                   "one band; ⛔ this instrument measured no band and judges nothing",
                 "budget_row": "the id of the row this section is compared against, as given when the section was "
                               "written. ⛔ The row is the consumer's; nothing here asserts it exists"},
        notes=[
            "⭐ A COMPARISON OF A CONVENTION, NEVER OF THE SKY. What one release of the library returned as the first "
            "value for its nutation and obliquity pseudo-body through calc under one declared configuration, at "
            "instants inside a data profile's coverage.",
            "⛔ EVERY ROW ASSERTS `none`. The pseudo-body's returned word hands the request back under every condition "
            "built so that the request cannot be answered, so it reports nothing; what this section stands on instead "
            "is that none of its returned values moved with the request, which the control record shows at every row.",
            "⭐ ONE VALUE COMPARED, SIX CARRIED. Each row compares the call's first returned value and carries all six "
            "beside it, nested, so that the controls can read every one of them and nothing compares the others.",
            "⚠ The band is its consumer's, declared as it asked; ⛔ it is not a measurement. What this instrument "
            "measured between a row and every other reading of it -- no difference at any position -- is in the "
            "control record.",
            "⚠ Dated, versioned and placed deliberately: one release, one binding, one host.",
        ],
    )
    control_header = fixture.Header(
        fixture_kind="provenance_record", reference="R3", generator=generator, generated=today,
        title="The invariance, sufficiency and nutation-twin controls of the nutation and obliquity pseudo-body's calc "
              "section, at every row",
        oracle={
            **common,
            "session": {
                "isolation": "⛔ each invariance and nutation_twin reading is the one call of a fresh child interpreter "
                             "(-I); each sufficiency row was read warm, every row of the section in one fresh child, in "
                             "its call_order; the children run in an empty working directory verified empty after the "
                             "run, and the parent takes no reading",
                "checked": "every call each child made into the library, through the module's and its submodule's "
                           "callables after they were wrapped, was recorded inside it and had to be exactly the "
                           "sequence its rows declare: the directory, then per reading the call with the row's "
                           "instant, body and whole word, and the constant read back. ⚠ Honest error, not forgery",
                "child_program": f"{child}'s, at the same commit, by import",
                "removed_environment_variables": sorted(k for k in os.environ if k.startswith("SE_")),
            },
            "data_files": data_files,
            "empty_directory": {"verified_empty": True, "checked": "before the first reading and after the last"},
            "method": "the pseudo-body and the Moon read through calc at each section row's instant under each "
                      "configuration of the declared set with no non-ephemeris bit, the pseudo-body with FLG_NONUT "
                      "added under the section's own, and the section read again warm in the reverse order",
            "survey": {"sha256": summary["survey_edge"]["survey_sha256"],
                       "read": "the witness's coverage_edge row, as bits, to place every witness reading the files "
                               "answered more than a day inside it"},
            "licence": "the library is AGPL-3.0; the generator that wrote this file calls it and redistributes none "
                       "of it",
        },
        attests="that at every row of the nutation and obliquity pseudo-body's calc section the pseudo-body read "
                "bit-identically at all six returned values under each of five configurations of request and "
                "data-file state, each reading in a fresh process; that at each such instant the Moon's returned word "
                "named a source other than the request where the request could not be answered, differed between two "
                "answering sources, and under the section's configuration was the request honoured; that the section "
                "read again warm in another order was bit-identical at all six; and that each row read with FLG_NONUT "
                "added differed from it at the first value and equalled, there, its own second value and the row's",
        authority={"held_by": "the library itself, as observed",
                   "kind": "black-box observation of return values under declared configurations",
                   "scope": "⚠ this version of the library and this binding only, run on the recorded host"},
        record_date=today,
        row_schema=CONTROL_ROW_SCHEMA,
        summary={"configuration_sha256": identity, "section": OUTPUTS[0], "epochs": epochs_summary,
                 "value_positions": value_positions,
                 **{k: v for k, v in summary.items() if k != "survey_edge"}, "survey_edge": summary["survey_edge"]},
        notes=[
            "⛔ A PROVENANCE RECORD; IT GATES NOTHING ON ITS OWN. It holds what the section's controls read, and every "
            "control passed at every row before either file was written.",
            "⭐ EVERY READING OF THE PSEUDO-BODY CARRIES ALL SIX RETURNED VALUES, the first three again under the names "
            "a reading's first three are read by; the witness's readings carry those three alone.",
            "⭐ THE WITNESS IS NOT A SUBJECT. The Moon is read so that each row's instant is shown to be one where the "
            "requested source can be told from another; nothing is asserted about the Moon on any row of the section.",
            "⚠ THE TWIN'S FIRST VALUE IS COMPARED TO THE BIT. Where the row's first value and the twin's agree, the "
            "twin control refuses the row; how far apart they were at the closest row is in summary.nutation_twin, "
            "measured, ⛔ not a floor.",
            "⚠ The sufficiency regeneration is warm and permuted, never cold, and carries none of a reading's fields: "
            "it is the section read again, and a cold reading under the section's configuration is already the "
            "invariance part's.",
        ],
    )
    os.makedirs(out_dir, exist_ok=True)
    fixture.write_jsonl(Path(paths[OUTPUTS[0]]), section_header, rows, declared_sections=[SECTION])
    fixture.write_jsonl(Path(paths[OUTPUTS[1]]), control_header, controls)
    out = {"commit": generator.commit, "configuration_sha256": identity, "budget_row": budget_row}
    for name, path in paths.items():
        with open(path, "rb") as handle:
            out[name] = hashlib.sha256(handle.read()).hexdigest()
    return out


def generate(ephe_path: str, empty_dir: str, profile: str, survey_path: str, out_dir: str, budget_row: str) -> dict:
    if not budget_row or budget_row != budget_row.strip():
        raise Refusal(f"the row id {budget_row!r} is empty or padded")
    _fixture, provenance = node._contract()
    provenance.generator_for(Path(__file__))  # ⛔ refuse a dirty tree before anything is measured
    refuse_existing(out_dir)
    node.verify_data_directory(ephe_path)
    node.verify_empty_directory(empty_dir)
    survey = node.read_survey_edges(survey_path)
    work = tempfile.mkdtemp(prefix="nutation-obliquity-section-")
    try:
        rows, controls, context = measure(ephe_path, empty_dir, profile, work)
        node.verify_empty_directory(work)
    finally:
        shutil.rmtree(work, ignore_errors=True)
    node.verify_data_directory(ephe_path)
    node.verify_empty_directory(empty_dir)
    summary = check(rows, controls, context, survey)
    return write_files(rows, controls, context, summary, out_dir, budget_row)


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--ephe-path", required=True, help="the pinned data files' directory, and nothing else")
    parser.add_argument("--empty-dir", required=True, help="an empty directory")
    parser.add_argument("--profile", required=True, help="the data profile manifest whose coverage bounds the rows")
    parser.add_argument("--survey", required=True, help="the survey whose coverage_edge rows place the witness")
    parser.add_argument("--budget-row", required=True, help="the id of the row the section is compared against: the "
                                                            "consumer's, ⛔ never chosen here")
    parser.add_argument("--out-dir", required=True, help="where the two files are written; neither may exist")
    args = parser.parse_args(argv)
    try:
        written = generate(args.ephe_path, args.empty_dir, args.profile, args.survey, args.out_dir, args.budget_row)
    except Refusal as refusal:
        sys.stderr.write(f"refused: {refusal}\n")
        return 2
    sys.stderr.write(json.dumps(written, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
