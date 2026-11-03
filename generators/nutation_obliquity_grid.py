"""The library's nutation and obliquity output through calc, every half day across a data profile's interval.

What one release of the ephemeris library returns for its nutation and obliquity pseudo-body through ``calc`` on
a dynamical-time Julian day, read black-box at every instant of a half-day lattice across the interval a data
profile manifest declares, under one configuration and one word; and, at a stated subset of those instants, read
again under every configuration and both words of the modes record (``nutation_obliquity_modes.py``). One R3
``provenance_record``, written only from a clean commit.

⭐ **The reading is the modes record's, by import, ⛔ never by copy.** Every reading is that generator's child
program: one call in a fresh ``-I`` interpreter, with every call into the library recorded inside the child with
the arguments it received. Every child is admitted by that generator's own rule, ``admit``: its calls must be
exactly the sequence its finished row declares. The epochs, the interval, the configurations, the directory checks
and the data-file pins are that generator's too. Nothing about a reading is written again here.

Two parts:

1. **grid** — the data-file request with the pinned files on the path, under the modes record's default word (no
   bit beside the ephemeris bits), at every instant of the lattice from the interval's start to its end in steps
   of ``STEP_DAYS``, and at the modes record's instants outside the interval. Its instants inside the interval
   are lattice instants, and the record is refused if one is not.
2. **invariance** — at every ``SUBSET_STRIDE``-th lattice instant from the start and at each of the modes record's
   instants, the five configurations under both words.

⛔ **Refusals, each before anything is written**: a dirty or commitless working tree, or either script away from its
path; an output that exists; a data directory that is not exactly the pinned set, or an "empty" directory that is
not empty (both checked before and after the run), or a working directory left holding anything; an interval
whose end is not on the lattice, or one of the modes record's instants inside it that is not; a modes record that
is not that generator's, read from another manifest, library or binding, or that lacks a reading this record ties
to; any child the modes rule refuses, and two readings carrying one child's nonce; a row whose names are not what
they name (its part, its configuration, its ephemeris label and nutation label to its word, its lattice index or
epoch to its instant); a grid or a subset that is not exactly the one built; and the four stop conditions:
⛔ a returned word other than the requested word; ⛔ six values that move across the configurations at a subset
instant under either word; ⛔ a reading at one of the modes record's instants that is not that record's bit for
bit; ⛔ and the nutation-off relation that record measured, not holding at a subset instant.

⛔ **Recorder, never explainer.** Nothing here describes how the library computes anything. What the library's
documentation says about its own models is quoted, attributed and dated, ⛔ never explained, and ⛔ nothing is
read from or about its source. A relation between readings is recorded as numbers, never as a mechanism.

The standard library, the binding, and the modes generator; ``git`` is called to read the commit.

Usage::

    python nutation_obliquity_grid.py --ephe-path DIR --empty-dir DIR --profile MANIFEST \\
        --modes-record FILE --out FILE [--workers N]
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import threading
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from importlib.metadata import PackageNotFoundError, version as _distribution_version

HERE = os.path.dirname(os.path.realpath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
# ⛔ Importing the modes generator must not write its bytecode beside it: an untracked file is a dirty tree, and
#    the commit this record names would not be the tree it ran from. Measured: in a tree that does not ignore
#    bytecode, the record is refused without this.
sys.dont_write_bytecode = True

# ⭐ The fresh-child reading, by import: its child program, its admission rule, its epochs and its pins.
import nutation_obliquity_modes as modes  # noqa: E402

REPO = modes.REPO
SCRIPT = "generators/nutation_obliquity_grid.py"
SCHEMA_VERSION = modes.SCHEMA_VERSION
Refusal = modes.Refusal
bits, unbits, patterned = modes.bits, modes.unbits, modes.patterned

#: ⭐ The step between lattice instants, in days. Why this one: `STEP_REASON`.
STEP_DAYS = 0.5
#: ⭐ The subset read under every configuration and both words: every `SUBSET_STRIDE`-th lattice instant counted
#: from the interval's start, and each of the modes record's instants.
SUBSET_STRIDE = 100
#: The grid's one configuration and word: the data-file request with the pinned files on the path, under the modes
#: record's default word. All six values of a grid row come from that one word.
GRID_CONFIGURATION = "swiss_file_present"
GRID_WORD = "default"
WORDS: tuple[str, ...] = ("default", "nonut")
#: Children at once unless told otherwise; each is its own process.
DEFAULT_WORKERS = 8
PROGRESS_EVERY = 25_000
ZERO_BITS = "0000000000000000"

#: ⭐ The published sources this record quotes, as retrieved. ⛔ Documentation only: nothing here is read from, or
#: says anything about, the library's source.
DOCUMENTS: tuple[dict, ...] = (
    {"document": "general_documentation",
     "title": "Swiss Ephemeris: Computer ephemeris for developers of astrological software",
     "url": "https://www.astro.com/swisseph/swisseph.htm", "retrieved": "2026-11-03",
     "sha256": "7ca3f8863d31001f3a1411139d4759813cc8c3d3c51312fbc45aa84382f05aa2",
     "release": "its release history ends at 2.10.03, dated 27-aug-2022"},
    {"document": "programmers_documentation",
     "title": "Programming interface to the Swiss Ephemeris",
     "url": "https://www.astro.com/swisseph/swephprg.htm", "retrieved": "2026-11-03",
     "sha256": "8fe1629b648eb86420f1ee80b1061c03c99e2d68c5b03c22fedc16819bdebff3",
     "release": "its list of changes ends at 'Changes from version 2.10.02 to 2.10.03'"},
    {"document": "iers_conventions_2010_chapter_5",
     "title": "IERS Conventions (2010), IERS Technical Note 36, chapter 5, version of 10 August 2012",
     "url": "https://iers-conventions.obspm.fr/content/chapter5/icc5.pdf", "retrieved": "2026-11-03",
     "sha256": "9ec6fac43f7037ff43896539d759333fc7e6007176cd72043b38d71cfd3e69c0",
     "release": "not the library's: the convention the step is chosen against"},
)

#: ⭐ What the library's documentation says about the models behind this output, in its own words, each quote
#: present exactly once in the document as retrieved. ⚠ Quoted, ⛔ not reconciled: the documentation names more than
#: one nutation model, and which one is in force is not established here.
DOCUMENTED_MODELS: dict[str, tuple[dict, ...]] = {
    "precession": (
        {"document": "general_documentation",
         "where": "2.1.3 'The details of coordinate transformation', the paragraph 'Precession'",
         "quote": "(From Swiss Ephemeris 1.78 on, we use the precession model Vondrák/Capitaine/Wallace 2011.)"},
        {"document": "programmers_documentation", "where": "29.25 'Changes from version 1.77 to 1.78'",
         "quote": "precession is now calculated according to Vondrák, Capitaine, and Wallace 2011."},
    ),
    "obliquity": (
        {"document": "general_documentation",
         "where": "2.1.2, item 4 'Differences between Swiss Ephemeris 1.78 and 1.77'",
         "quote": "Version 1.78 calculates precession and ecliptic obliquity according to Vondrák, Capitaine, and "
                  "Wallace, “New precession expressions, valid for long time intervals”, A&A 534, A22 (2011), which "
                  "is good for +- 200 millennia."},
    ),
    "nutation": (
        {"document": "general_documentation",
         "where": "2.1.3 'The details of coordinate transformation', the paragraph 'Nutation (true equinox of date)'",
         "quote": "(From Swiss Ephemeris 2.00, we use the nutation model IAU 2006. Since 1.70, we used nutation model "
                  "IAU 2000. Older versions used the nutation model IAU 1980 (Wahr).)"},
        {"document": "general_documentation",
         "where": "2.1.2, item 3 'Differences between Swiss Ephemeris 1.70 and older versions'",
         "quote": "Nutation IAU 2000B (could be switched to 2000A by the user);"},
        {"document": "programmers_documentation", "where": "29.36 'Changes from version 1.67 to version 1.70'",
         "quote": "the nutation model IAU2000B (can be switched to IAU2000A)"},
    ),
}
#: Searched in the programmer's documentation as retrieved, for a documented way to read or set the models.
DOCUMENTATION_SEARCH = {"document": "programmers_documentation", "searched_for": ["astro_models", "SEMOD", "SE_MODEL"],
                        "hits": 0}

STEP_SOURCE = {
    "document": "iers_conventions_2010_chapter_5",
    "where": "5.3.2 'Schematic representation of the motion of the Celestial Intermediate Pole (CIP)'",
    "quote": "the celestial motion of the CIP (precession-nutation), includes all the terms with periods greater "
             "than 2 days in the GCRS",
}
STEP_REASON = (
    "half a day. Its consumer will compare a periodic series, so no term may hide between samples. The library's "
    "documentation names IAU models of 2000 and 2006 for its nutation (summary.documented_models), and the IERS "
    "Conventions (2010) state that under the IAU 2000/2006 resolutions precession-nutation includes all the terms "
    "with periods greater than 2 days (step_source). At half a day every such term is read more than four times per "
    "period, so in every period some sample falls within an eighth of a period of the term's extreme and reads at "
    "least cos(45 degrees), about 0.71, of its amplitude. A daily step reads a two-day term twice per period, and "
    "both samples can fall on its zeros. And the half-day lattice from the interval's start (0h) holds J2000 (noon) "
    "and the interval's end exactly, so the modes record's three instants inside the interval are lattice instants "
    "rather than additions to it. ⛔ Whether the library's output holds a term of shorter period is not established "
    "here: the step is chosen against the convention, ⛔ not against the library"
)
SUBSET_RULE = (
    "every lattice instant whose index, counted from the interval's start, is a multiple of the stride (one every "
    "50 days, both ends among them), and each of the modes record's instants; at each, the five configurations "
    "under both words, every reading the one call of a fresh process"
)


# ======================================================================================
# The instants — the modes record's epochs, and a lattice across the manifest's interval
# ======================================================================================


def build_grid(interval: dict, epochs: list[dict]) -> list[dict]:
    """The lattice from the interval's start to its end, and the modes record's instants outside it."""
    start, end = interval["start"], interval["end"]
    steps = (end - start) / STEP_DAYS
    if steps != int(steps) or start + int(steps) * STEP_DAYS != end:
        raise Refusal(f"the interval's end is {steps!r} steps of {STEP_DAYS} days from its start; the lattice must "
                      "end on it")
    grid = [{"lattice_index": k, "jd": start + k * STEP_DAYS, "in_supported_interval": True}
            for k in range(int(steps) + 1)]
    on = {bits(i["jd"]): i for i in grid}
    if len(on) != len(grid):
        raise Refusal("two lattice instants share a Julian day")
    for epoch in epochs:
        if epoch["in_supported_interval"]:
            instant = on.get(bits(epoch["jd"]))
            if instant is None:
                raise Refusal(f"{epoch['epoch_id']} is inside the interval and not on the lattice")
            instant["epoch_id"] = epoch["epoch_id"]
        else:
            grid.append({"epoch_id": epoch["epoch_id"], "jd": epoch["jd"], "in_supported_interval": False})
    grid.sort(key=lambda i: i["jd"])
    return grid


def build_subset(grid: list[dict]) -> list[dict]:
    return [i for i in grid if "epoch_id" in i or i["lattice_index"] % SUBSET_STRIDE == 0]


def where(instant: dict) -> dict:
    """A row's instant: the modes record's name for it if it has one, its lattice index if it is on the lattice."""
    out: dict = {}
    if "epoch_id" in instant:
        out["epoch_id"] = instant["epoch_id"]
    if "lattice_index" in instant:
        out["lattice_index"] = instant["lattice_index"]
    out.update(patterned("jd", instant["jd"]))
    out["in_supported_interval"] = instant["in_supported_interval"]
    return out


def instant_key(row: dict) -> tuple:
    return (row.get("epoch_id"), row.get("lattice_index"), row["jd_bits"], row["in_supported_interval"])


# ======================================================================================
# The modes record — what the grid is tied to
# ======================================================================================


def read_modes_record(path: str, interval: dict, epochs: list[dict], library_version: str,
                      binding_version: str | None) -> dict:
    """The modes record's calc readings at its seven instants, keyed by configuration, word and instant. ⛔ Refused
    unless it is that generator's, from the same manifest, library and binding, at exactly these instants."""
    with open(path, "rb") as handle:
        raw = handle.read()
    lines = [json.loads(line) for line in raw.decode("ascii").splitlines()]
    header, rows = lines[0], lines[1:]
    if header.get("generator", {}).get("script") != modes.SCRIPT:
        raise Refusal(f"the modes record was written by {header.get('generator', {}).get('script')!r}, "
                      f"not {modes.SCRIPT}")
    summary = header.get("summary", {})
    if summary.get("epochs", {}).get("manifest_sha256") != interval["manifest_sha256"]:
        raise Refusal("the modes record read its instants from another manifest")
    oracle = header.get("oracle", {})
    if (oracle.get("library_version"), oracle.get("called_via", {}).get("version")) != (library_version,
                                                                                       binding_version):
        raise Refusal(f"the modes record read library {oracle.get('library_version')!r} through binding "
                      f"{oracle.get('called_via', {}).get('version')!r}")
    by_id = {e["epoch_id"]: e for e in epochs}
    if summary["epochs"].get("ids") != [e["epoch_id"] for e in epochs]:
        raise Refusal("the modes record's instants are not these")
    tie: dict[tuple, dict] = {}
    for row in rows:
        if (row.get("part"), row.get("entry_point")) != ("mode_invariance", "calc"):
            continue
        epoch = by_id.get(row["epoch_id"])
        if epoch is None or row["jd_bits"] != bits(epoch["jd"]):
            raise Refusal(f"a modes record row named {row['epoch_id']} is not that instant")
        tie[(row["configuration"], row["nutation"], row["jd_bits"])] = row
    wanted = {(c, w, bits(e["jd"])) for c, *_ in modes.CONFIGURATIONS for w in WORDS for e in epochs}
    if set(tie) != wanted:
        raise Refusal(f"the modes record holds {len(tie)} calc readings at its instants; this record ties to "
                      f"{len(wanted)}")
    return {"sha256": hashlib.sha256(raw).hexdigest(), "generator_commit": header["generator"]["commit"],
            "generated": header.get("generated"), "host": oracle.get("host"), "rows": len(rows), "tie": tie}


# ======================================================================================
# Reading — the modes record's children, several at a time
# ======================================================================================


class Readers:
    """The modes record's children, several at once: one ``modes.Children`` per thread, each keeping the nonces it
    has seen, every nonce across them held distinct afterwards. ⛔ Each reading is still one fresh child."""

    def __init__(self, work: str, workers: int) -> None:
        if workers < 1:
            raise Refusal(f"{workers} children at once")
        self.work, self.workers = work, workers
        self.local = threading.local()
        self.lock = threading.Lock()
        self.pools: list = []

    def _children(self):
        children = getattr(self.local, "children", None)
        if children is None:
            children = self.local.children = modes.Children(self.work)
            with self.lock:
                self.pools.append(children)
        return children

    def _one(self, spec: dict) -> dict:
        return self._children().take_all([spec])[0]

    def take(self, specs: list[dict]):
        """Each spec's reading, in the specs' order — never the order the children finished."""
        pool = ThreadPoolExecutor(self.workers)
        try:
            yield from pool.map(self._one, specs)
        finally:
            pool.shutdown(wait=True, cancel_futures=True)

    def count(self) -> int:
        nonces = [n for children in self.pools for n in children.nonces]
        if len(set(nonces)) != len(nonces):
            raise Refusal("two readings came back from one child")
        return len(nonces)


def declared(row: dict, subject: int) -> dict:
    """The finished row as the modes rule reads it: the record's constants (every reading is ``calc`` of the
    pseudo-body), and, for a grid row, its configuration's directory — each written in the header."""
    fixed = {"finding": "nutation_obliquity_reading", "entry_point": "calc", "body": subject}
    if row["part"] == "grid":
        fixed["path_state"] = {name: state for name, _eph, state in modes.CONFIGURATIONS}[GRID_CONFIGURATION]
    return {**fixed, **row}


class ReadBack:
    """What every child read back beside its value — the tidal constant before and after, and the library's report
    of its open files — counted by part and configuration. ⚠ Recorded, never interpreted and never relied on."""

    def __init__(self) -> None:
        self.tidal: dict[str, Counter] = {}
        self.files: dict[str, Counter] = {}

    def add(self, row: dict, reading: dict) -> None:
        key = "grid" if row["part"] == "grid" else f"invariance_{row['configuration']}"
        self.tidal.setdefault(key, Counter())[(reading["tidal_constant_before_bits"],
                                               reading["tidal_constant_after_bits"])] += 1
        self.files.setdefault(key, Counter())[json.dumps(reading["current_file_data_after"], sort_keys=True)] += 1

    def summary(self) -> dict:
        out = {}
        for key in self.tidal:
            tidal = [{**patterned("tidal_constant_before", unbits(b)), **patterned("tidal_constant_after", unbits(a)),
                      "readings": n} for (b, a), n in sorted(self.tidal[key].items(), key=lambda kv: (-kv[1], kv[0]))]
            files = [{"current_file_data_after": [
                {"ifno": f["ifno"], "file": f["file"], **patterned("start", unbits(f["start_bits"])),
                 **patterned("end", unbits(f["end_bits"])), "denum": f["denum"]} for f in json.loads(rendered)],
                "readings": n} for rendered, n in sorted(self.files[key].items(), key=lambda kv: (-kv[1], kv[0]))]
            out[key] = {"tidal_constant": tidal, "open_files": files}
        return out


def binding_surface(swe) -> dict:
    """⭐ Measured: whether the binding offers a way to read or set the models in force, and the constants it exports
    under model names. ⛔ The constants are not a reading of what is in force."""
    def callables(module) -> list[str]:
        return sorted(n for n in dir(module) if not n.startswith("_") and callable(getattr(module, n))
                      and not isinstance(getattr(module, n), type))

    names = callables(swe)
    contrib = getattr(swe, "contrib", None)
    if contrib is not None:
        names += [f"contrib.{n}" for n in callables(contrib)]
    return {
        "callables": len(names),
        "callables_whose_name_names_a_model": [n for n in names if "model" in n.lower()],
        "exported_constants_named_for_models": [
            {"name": n, "value": getattr(swe, n)} for n in sorted(dir(swe))
            if n.startswith(("MOD_", "MODEL_", "NSE_MODELS")) and isinstance(getattr(swe, n), int)],
        "meaning": "every callable of the binding module and of its submodule, by name: none names a model, and the "
                   "binding's documented functions read or set no model either (documentation_search), so the "
                   "models in force were ⛔ not read and ⛔ none was changed. The constants are what the binding "
                   "exports under those names, ⛔ not a reading of what is in force, and ⛔ nothing here is decided "
                   "from them",
    }


def measure(ephe_path: str, empty_dir: str, profile: str, modes_record: str, work: str,
            workers: int) -> tuple[list[dict], dict]:
    import swisseph as swe

    try:
        binding_version = _distribution_version("pyswisseph")
    except PackageNotFoundError:
        binding_version = None
    flag = {name: getattr(swe, constant) for name, constant in modes.EPHEMERIS_NAMES}
    nonut, subject = swe.FLG_NONUT, swe.ECL_NUT
    extra = {"default": 0, "nonut": nonut}
    paths = {"data_files": os.path.abspath(ephe_path), "empty_directory": os.path.abspath(empty_dir)}
    configurations = {name: (eph, state) for name, eph, state in modes.CONFIGURATIONS}
    interval = modes.read_interval(profile)
    epochs = modes.build_epochs(interval)
    grid = build_grid(interval, epochs)
    subset = build_subset(grid)
    tied = read_modes_record(modes_record, interval, epochs, swe.version, binding_version)

    items: list[tuple[dict, dict]] = []
    eph, state = configurations[GRID_CONFIGURATION]
    for instant in grid:
        base = {"part": "grid", **where(instant), "requested": flag[eph] | extra[GRID_WORD]}
        items.append((base, modes.spec_for(path=paths[state], flags=base["requested"], entry_point="calc",
                                           jd=instant["jd"], body=subject)))
    for instant in subset:
        for configuration, (eph, state) in configurations.items():
            for word in WORDS:
                base = {"part": "invariance", "configuration": configuration, "ephemeris_requested": eph,
                        "path_state": state, "nutation": word, **where(instant), "requested": flag[eph] | extra[word]}
                items.append((base, modes.spec_for(path=paths[state], flags=base["requested"], entry_point="calc",
                                                   jd=instant["jd"], body=subject)))

    readers = Readers(work, workers)
    read_back = ReadBack()
    rows: list[dict] = []
    for (base, _spec), reading in zip(items, readers.take([s for _, s in items]), strict=True):
        row = {**base, "returned": reading["returned"], "values": [unbits(b) for b in reading["values_bits"]],
               "values_bits": list(reading["values_bits"])}
        # ⛔ The modes rule, on the row as it will be written: every call the child made, and nothing else.
        modes.admit(declared(row, subject), reading["calls"], paths)
        read_back.add(row, reading)
        rows.append(row)
        if len(rows) % PROGRESS_EVERY == 0:
            sys.stderr.write(f"{len(rows)} of {len(items)} readings\n")

    context = {"interval": interval, "epochs": epochs, "grid": grid, "subset": subset, "flag": flag,
               "nonut": nonut, "subject": subject, "children": readers.count(), "tied": tied,
               "read_back": read_back.summary(), "binding": binding_surface(swe), "workers": workers}
    return rows, context


# ======================================================================================
# The controls a record must pass before it is written
# ======================================================================================


def check(rows: list[dict], context: dict) -> dict:
    """The record's own controls and the four stop conditions. Returns the summary; raises Refusal on any."""
    flag, nonut = context["flag"], context["nonut"]
    extra = {"default": 0, "nonut": nonut}
    configurations = {name: (eph, state) for name, eph, state in modes.CONFIGURATIONS}
    epochs = {e["epoch_id"]: e for e in context["epochs"]}
    start = context["interval"]["start"]
    lattice = sum(1 for i in context["grid"] if "lattice_index" in i)
    if context["children"] != len(rows):
        raise Refusal(f"{len(rows)} readings from {context['children']} children")

    # ⛔ Held, each to what it names: a row's part; its configuration to the table defining it; its ephemeris label
    #    and nutation label to its word; its lattice index and its epoch to its instant and in-interval flag; its six
    #    values to their patterns.
    for row in rows:
        part = row["part"]
        if part == "grid":
            if {"configuration", "ephemeris_requested", "path_state", "nutation"} & set(row):
                raise Refusal("a grid row names a configuration; the grid's is the header's")
            eph, word = configurations[GRID_CONFIGURATION][0], GRID_WORD
        elif part == "invariance":
            if configurations.get(row["configuration"]) != (row["ephemeris_requested"], row["path_state"]):
                raise Refusal(f"a row named {row['configuration']} is not that configuration")
            eph, word = row["ephemeris_requested"], row["nutation"]
        else:
            raise Refusal(f"a row in part {part!r}")
        if word not in extra or row["requested"] != flag[eph] | extra[word]:
            raise Refusal(f"a {part} row labelled {eph} {word} requested {row['requested']}")
        if len(row["values_bits"]) != len(modes.VALUE_POSITIONS) or [bits(v) for v in row["values"]] != row[
                "values_bits"]:
            raise Refusal(f"a {part} row's values are not six values and their patterns")
        index, epoch_id = row.get("lattice_index"), row.get("epoch_id")
        instant = None
        if index is not None and 0 <= index < lattice:
            instant = {"jd": start + index * STEP_DAYS, "in_supported_interval": True}
        if epoch_id is not None:
            epoch = epochs.get(epoch_id)
            instant = None if epoch is None or (instant is not None and instant["jd"] != epoch["jd"]) else epoch
        if instant is None or bits(instant["jd"]) != row["jd_bits"] or row["jd"] != instant["jd"] or row[
                "in_supported_interval"] != instant["in_supported_interval"]:
            raise Refusal(f"a {part} row at JD {row['jd']!r} is not the instant its index or epoch names")

    grid_rows = [r for r in rows if r["part"] == "grid"]
    invariance_rows = [r for r in rows if r["part"] == "invariance"]
    expected_grid = [instant_key(where(i)) for i in context["grid"]]
    if [instant_key(r) for r in grid_rows] != expected_grid:
        raise Refusal(f"the grid part holds {len(grid_rows)} rows that are not the grid's {len(expected_grid)} "
                      "instants in order")
    expected_invariance = [(instant_key(where(i)), c, w) for i in context["subset"]
                           for c, *_ in modes.CONFIGURATIONS for w in WORDS]
    if [(instant_key(r), r["configuration"], r["nutation"]) for r in invariance_rows] != expected_invariance:
        raise Refusal(f"the invariance part holds {len(invariance_rows)} rows that are not the subset's "
                      f"{len(expected_invariance)} readings in order")

    # ⛔ STOP 1: a returned word other than the requested word.
    for row in rows:
        if row["returned"] != row["requested"]:
            raise Refusal(f"⛔ STOP: a {row['part']} reading at JD {row['jd']!r} requested word {row['requested']} "
                          f"and returned {row['returned']}; the modes record measured every word handed back")

    # ⛔ STOP 2: six values that move across the configurations at a subset instant, under either word.
    sets: dict[tuple, set] = {}
    for row in invariance_rows:
        sets.setdefault((row["jd_bits"], row["nutation"]), set()).add(tuple(row["values_bits"]))
    for (jd_bits, word), found in sets.items():
        if len(found) != 1:
            raise Refusal(f"⛔ STOP: at JD {unbits(jd_bits)!r} under the {word} word the values moved across the "
                          f"configurations ({len(found)} sets of six)")
    one = {w: sum(1 for (_, word), found in sets.items() if word == w and len(found) == 1) for w in WORDS}

    # ⛔ A grid row and its subset twin — the same configuration and word, another fresh child — are one reading.
    twins = {(r["jd_bits"], r["configuration"], r["nutation"]): r for r in invariance_rows}
    repeated = 0
    for row in grid_rows:
        twin = twins.get((row["jd_bits"], GRID_CONFIGURATION, GRID_WORD))
        if twin is None:
            continue
        if twin["values_bits"] != row["values_bits"]:
            raise Refusal(f"at JD {row['jd']!r} the grid's reading and its subset twin, two fresh children under "
                          "one configuration and word, differ")
        repeated += 1

    # ⛔ STOP 3: a reading at one of the modes record's instants that is not that record's, bit for bit.
    tie = context["tied"]["tie"]
    tied = {"grid": 0, "invariance": 0}
    for row in rows:
        if "epoch_id" not in row:
            continue
        key = ((GRID_CONFIGURATION, GRID_WORD) if row["part"] == "grid" else (row["configuration"], row["nutation"]))
        theirs = tie.get((*key, row["jd_bits"]))
        if theirs is None or (theirs["requested"], theirs["returned"], theirs["values_bits"]) != (
                row["requested"], row["returned"], row["values_bits"]):
            raise Refusal(f"⛔ STOP: the {row['part']} reading at {row['epoch_id']} under {key} is not the modes "
                          "record's, bit for bit")
        tied[row["part"]] += 1
    if tied["invariance"] != len(tie) or tied["grid"] != len(context["epochs"]):
        raise Refusal(f"tied {tied} of the modes record's {len(tie)} readings at {len(context['epochs'])} instants")

    # ⛔ STOP 4: the nutation-off relation the modes record measured — under the nonut word position 1 is its default
    #    twin's, position 0 is position 1, positions 2 and 3 are zero; and the default word's positions 0, 2 and 3
    #    are not the nonut word's.
    pairs: dict[tuple, dict] = {}
    for row in invariance_rows:
        pairs.setdefault((row["jd_bits"], row["configuration"]), {})[row["nutation"]] = row["values_bits"]
    equal_at = [0] * len(modes.VALUE_POSITIONS)
    for (jd_bits, configuration), pair in pairs.items():
        default, off = pair["default"], pair["nonut"]
        for i, (a, b) in enumerate(zip(default, off)):
            equal_at[i] += a == b
        if not (off[1] == default[1] and off[0] == off[1] and off[2] == off[3] == ZERO_BITS
                and all(default[i] != off[i] for i in (0, 2, 3))):
            raise Refusal(f"⛔ STOP: at JD {unbits(jd_bits)!r} under {configuration} the nutation-off relation the "
                          "modes record measured does not hold")

    return summarise(rows, context, grid_rows, invariance_rows, one, sets, repeated, tied, pairs, equal_at)


def summarise(rows, context, grid_rows, invariance_rows, one, sets, repeated, tied, pairs, equal_at) -> dict:
    interval = context["interval"]
    lattice = [i for i in context["grid"] if "lattice_index" in i]
    eph, state = {n: (e, s) for n, e, s in modes.CONFIGURATIONS}[GRID_CONFIGURATION]
    instants = {w: sum(1 for (_, word) in sets if word == w) for w in WORDS}
    tied_record = context["tied"]
    return {
        "readings": len(rows),
        "children": context["children"],
        "rows_by_part": {"grid": len(grid_rows), "invariance": len(invariance_rows)},
        "entry_point": "calc",
        "body": context["subject"],
        "value_positions": {"documented_as": list(modes.VALUE_POSITIONS),
                            "documented_in": modes.VALUE_POSITIONS_SOURCE},
        "interval": {
            "profile": interval["profile"],
            "manifest_sha256": interval["manifest_sha256"],
            "dataset": interval["dataset"],
            "declared_coverage": interval["declared_coverage"],
            **patterned("start_jd", interval["start"]),
            **patterned("end_jd", interval["end"]),
            "used_as": "Julian days passed to calc as dynamical time; the coverage's scale is TDB and its difference "
                       "from TT, milliseconds, is not applied",
        },
        "grid": {
            "configuration": GRID_CONFIGURATION, "ephemeris_requested": eph, "path_state": state,
            "nutation": GRID_WORD, "requested": context["flag"][eph] | {"default": 0, "nonut": context["nonut"]}[GRID_WORD],
            **patterned("step_days", STEP_DAYS),
            "step_reason": STEP_REASON,
            "step_source": STEP_SOURCE,
            "lattice": {"instants": len(lattice), "rule": "jd = start_jd + lattice_index * step_days, lattice_index "
                        "from 0, its last instant the interval's end",
                        **patterned("first_jd", lattice[0]["jd"]), **patterned("last_jd", lattice[-1]["jd"])},
            "the_modes_records_instants": {
                "on_the_lattice": [i["epoch_id"] for i in context["grid"] if "epoch_id" in i and "lattice_index" in i],
                "outside_the_interval": [i["epoch_id"] for i in context["grid"] if "lattice_index" not in i]},
            "instants": len(context["grid"]),
        },
        "returned_word": {"readings": len(rows),
                          "returned_exactly_the_requested_word": sum(1 for r in rows if r["returned"] == r["requested"])},
        "invariance": {
            "subset": {"rule": SUBSET_RULE, "stride": SUBSET_STRIDE, "instants": len(context["subset"]),
                       "of_which_the_modes_records": sum(1 for i in context["subset"] if "epoch_id" in i),
                       "readings": len(invariance_rows)},
            "instants_with_one_set_of_six_values_across_the_five_configurations": {
                w: {"instants": one[w], "of": instants[w]} for w in WORDS},
            "grid_rows_bit_identical_to_their_subset_twin": {
                "rows": repeated, "of": sum(1 for i in context["subset"])},
        },
        "nonut": {
            "pairs": len(pairs),
            "pairs_bit_identical_at_position": equal_at,
            "relation": "under the nonut word position 1 is its default twin's, position 0 is position 1, positions 2 "
                        "and 3 are zero; and the default word's positions 0, 2 and 3 are not the nonut word's -- held "
                        "at every pair, numbers, ⛔ not a mechanism",
        },
        "tie": {
            "modes_record": {"sha256": tied_record["sha256"], "generator_commit": tied_record["generator_commit"],
                             "generated": tied_record["generated"], "host": tied_record["host"],
                             "rows": tied_record["rows"]},
            "readings_tied": {"grid": tied["grid"], "invariance": tied["invariance"]},
            "meaning": "every reading here at one of the modes record's instants -- the grid's, and the subset's under "
                       "all five configurations and both words -- carries that record's requested word, returned "
                       "word and six values, bit for bit",
        },
        "documented_models": {
            "documents": [dict(d) for d in DOCUMENTS],
            **{quantity: [dict(q) for q in quotes] for quantity, quotes in DOCUMENTED_MODELS.items()},
            "documentation_search": dict(DOCUMENTATION_SEARCH),
            "meaning": "what the library's published documentation says about its models, quoted from the documents "
                       "as retrieved, each quote present in its document exactly once. ⚠ Quoted, ⛔ not reconciled: the "
                       "documentation names more than one nutation model. ⛔ Nothing is read from or about the "
                       "library's source",
        },
        "binding": context["binding"],
        "read_back": context["read_back"],
    }


# ======================================================================================
# The record
# ======================================================================================


def source_commit() -> str:
    """The clean commit this script and the modes generator are at. ⛔ Refused on a dirty or commitless tree."""
    def git(*args: str, cwd: str = HERE) -> str:
        proc = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=False)
        if proc.returncode != 0:
            raise Refusal(f"git {' '.join(args)}: {proc.stderr.strip()[:200]}")
        return proc.stdout

    top = os.path.realpath(git("rev-parse", "--show-toplevel").strip())
    status = git("status", "--porcelain", "--untracked-files=all", cwd=top)
    if status.strip():
        raise Refusal("the working tree is dirty; generator.commit would name a state that does not "
                      "exist. Commit the generator, then generate:\n" + status[:800])
    for path, expected in ((os.path.realpath(__file__), SCRIPT), (os.path.realpath(modes.__file__), modes.SCRIPT)):
        script = os.path.relpath(path, top).replace(os.sep, "/")
        if script != expected:
            raise Refusal(f"this reading runs {script}, not {expected}")
        git("ls-files", "--error-unmatch", "--", script, cwd=top)
    return git("rev-parse", "HEAD", cwd=top).strip()


ROW_SCHEMA = {
    "part": "grid (the header's configuration and word, at every instant of the grid) | invariance (the subset, "
            "under every configuration and both words)",
    "configuration": "invariance: which ephemeris was requested and which directory was on the path -- the modes "
                     "record's names. A grid row carries none: the grid's is summary.grid",
    "ephemeris_requested": "invariance: moshier | swiss_file | jpl_file -- the source the request names",
    "path_state": "invariance: data_files (exactly the pinned set) | empty_directory (verified empty)",
    "nutation": "invariance: default (no bit beside the ephemeris bits) | nonut (FLG_NONUT and nothing else)",
    "epoch_id": "present only at one of the modes record's instants: that record's name for it",
    "lattice_index": "present only on the lattice: jd = summary.grid.lattice.first_jd + lattice_index * "
                     "summary.grid.step_days",
    "jd": "the dynamical-time Julian day passed to calc; `jd_bits` is that value",
    "in_supported_interval": "whether the instant lies inside the data profile's declared coverage",
    "requested": "⭐ the WHOLE flag word passed, every bit of it",
    "returned": "the whole flag word the call returned",
    "values": "⭐ all six values the call returned, in the order returned; `values_bits` are the values, the decimals "
              "are display. What the documentation calls each is in summary.value_positions",
}


def notes(summary: dict) -> list[str]:
    """The record's notes. ⭐ Each finding is stated from the summary it is about, never typed beside it."""
    grid, words, inv, nonut, tie = (summary["grid"], summary["returned_word"], summary["invariance"],
                                    summary["nonut"], summary["tie"])
    one = inv["instants_with_one_set_of_six_values_across_the_five_configurations"]
    twins = inv["grid_rows_bit_identical_to_their_subset_twin"]
    return [
        "⛔ A PROVENANCE RECORD, AND IT GATES NOTHING. It states what was observed and compares nothing: no tolerance, "
        "no reference value, no verdict, no band, no unit, no class. It is this instrument's own record, ⛔ not any "
        "consumer's shape.",
        f"⭐ THE GRID: the pseudo-body through calc at {grid['instants']} instants -- {grid['lattice']['instants']} on "
        f"a lattice every {grid['step_days']} day across the interval, and the modes record's "
        f"{len(grid['the_modes_records_instants']['outside_the_interval'])} instants outside it -- under the "
        f"{grid['configuration']} configuration and the {grid['nutation']} word, all six values from that one word. "
        "Why that step: summary.grid.step_reason.",
        f"⭐ THE RETURNED WORD WAS THE REQUESTED WORD in {words['returned_exactly_the_requested_word']} of "
        f"{words['readings']} readings (summary.returned_word). ⚠ For this body the word hands the request back (the "
        "modes record), so it does not say which ephemeris answered.",
        f"⭐ THROUGH calc THE SIX VALUES DID NOT MOVE across the five configurations at {one['default']['instants']} "
        f"of {one['default']['of']} subset instants under the default word and {one['nonut']['instants']} of "
        f"{one['nonut']['of']} under the nonut word; and the grid's reading equalled its subset twin, another fresh "
        f"child, at {twins['rows']} of {twins['of']} (summary.invariance).",
        f"⭐ TIED TO THE MODES RECORD ({tie['modes_record']['sha256'][:16]}...): {tie['readings_tied']['invariance']} "
        f"subset readings and {tie['readings_tied']['grid']} grid readings at its instants carry its words and six "
        "values bit for bit (summary.tie).",
        f"⚠ NONUT: at {nonut['pairs']} pairs the nutation-off relation the modes record measured held "
        f"(summary.nonut) -- numbers, ⛔ not a mechanism.",
        "⚠ THE MODELS ARE QUOTED, NOT READ. The library's documentation is quoted for its precession, obliquity and "
        "nutation models, ⛔ not reconciled where it names more than one; the binding offers no way to read or set "
        "the models in force, so none was read and none was changed (summary.documented_models, summary.binding).",
        "⚠ Not measured: calc_ut, any other entry point, the speed or sidereal words, any other library version or "
        "host. Every reading is the one call of a fresh process, admitted by the modes record's own rule.",
        "⚠ Dated, versioned and placed deliberately. This is an observation of one release through one binding on "
        "one machine, not a claim about the software in general.",
    ]


FRESHNESS = ("⛔ every reading is one call in a fresh child interpreter (-I); the children run in an empty working "
             "directory that is not the parent's, verified empty after the run; the parent takes no reading")


def build_record(rows: list[dict], context: dict, summary: dict, commit: str) -> list[str]:
    import swisseph as swe

    try:
        binding_version = _distribution_version("pyswisseph")
    except PackageNotFoundError:
        binding_version = None
    today = datetime.datetime.now(datetime.timezone.utc).date().isoformat()
    header = {
        "record": "header",
        "schema_version": SCHEMA_VERSION,
        "fixture_kind": "provenance_record",
        "reference": "R3",
        "generator": {"repo": REPO, "script": SCRIPT, "commit": commit},
        "generated": today,
        "oracle": {
            "implementation": "Swiss Ephemeris",
            "library_version": swe.version,
            "called_via": {"binding": "pyswisseph", "version": binding_version},
            "session": {
                "isolation": FRESHNESS,
                "child_program": f"{modes.SCRIPT}'s, by import: its child, its spec, its admission rule",
                "why": "the library keeps process-wide state, and a reading taken after another call reports that "
                       "call's state as well as its own",
                "children_at_once": context["workers"],
                "concurrency": "several children run at once, each its own process and its own reading; rows are "
                               "written in the order of the grid and the subset, never the order children finished",
                "checked": "every call each child made through the callables of the library module and of its "
                           "submodule, after they were wrapped, was recorded inside the child and is the sequence its "
                           "finished row declares under the modes record's own rule -- the row as written here with "
                           "the header's constants (calc, the pseudo-body, the grid's directory); each child started "
                           "from an interpreter that had not loaded the library and returned one reading, and no two "
                           "readings carry one child's nonce. ⚠ Honest error, not forgery, as in the modes record",
                "removed_environment_variables": sorted(k for k in os.environ if k.startswith("SE_")),
            },
            "licence": "the library is AGPL-3.0; it is called here, never redistributed by this repository",
            "host": {"python": sys.version.split()[0], "platform": platform.platform(),
                     "machine": platform.machine()},
            "data_files": {
                "directory_contents_verified": True,
                "files": [dict(pin) for pin in modes.EPHE_PINS],
                "unpinned_file_policy": "refused. The library reads the directory, so a file nobody passed can still "
                                        "answer",
            },
            "empty_directory": {"verified_empty": True,
                                "checked": "before the first reading and after the last, as the data directory"},
            "method": "calc of the pseudo-body on a dynamical-time Julian day under a declared configuration, and "
                      "what came back read: all six returned values and the whole returned word; the "
                      "tidal-acceleration constant and the library's report of its open files read back beside each "
                      "and counted in summary.read_back",
        },
        "title": "What one release of the ephemeris library returns for its nutation and obliquity pseudo-body through "
                 "calc, every half day across a data profile's interval, and under every request at a subset of it",
        "attests": "a vendor_convention attestation: what this release of the ephemeris library returned for its "
                   "pseudo-body for nutation and obliquity through calc on a dynamical-time Julian day, every half "
                   "day across the declared interval and at the modes record's instants outside it, under the "
                   "data-file request with the pinned files and the default word; at a stated subset, under five "
                   "configurations and both words; with every returned value and the whole requested and returned "
                   "words, tied to the modes record at its instants",
        "authority": {
            "held_by": "the library itself, as observed",
            "kind": "black-box observation of return values under declared configurations, every reading in a fresh "
                    "process",
            "scope": "⚠ this version of the library and this binding only, run on the recorded host. A later "
                     "version, or the same version built for another machine, may return different bits, which is "
                     "why the observation is dated, versioned and placed rather than stated as a property of the "
                     "software in general",
        },
        "record_date": today,
        "row_schema": ROW_SCHEMA,
        "summary": summary,
        "notes": notes(summary),
    }
    lines = [json.dumps(header, ensure_ascii=True)]
    lines.extend(json.dumps({"record": "row", **row}, ensure_ascii=True) for row in rows)
    return lines


def generate(ephe_path: str, empty_dir: str, profile: str, modes_record: str, out: str,
             workers: int = DEFAULT_WORKERS) -> str:
    """Measure, check and write. Returns the commit the record names."""
    commit = source_commit()
    if os.path.exists(out):
        raise Refusal(f"{out} exists; each emission goes to a new path")
    modes.verify_data_directory(ephe_path)
    modes.verify_empty_directory(empty_dir)
    work = tempfile.mkdtemp(prefix="nutation-obliquity-grid-")
    try:
        rows, context = measure(ephe_path, empty_dir, profile, modes_record, work, workers)
        modes.verify_empty_directory(work)
    finally:
        shutil.rmtree(work, ignore_errors=True)
    modes.verify_data_directory(ephe_path)
    modes.verify_empty_directory(empty_dir)
    summary = check(rows, context)
    lines = build_record(rows, context, summary, commit)
    with open(out, "x", encoding="ascii", newline="\n") as handle:
        handle.write("\n".join(lines) + "\n")
    return commit


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--ephe-path", required=True, help="the pinned data files' directory, and nothing else")
    parser.add_argument("--empty-dir", required=True, help="an empty directory")
    parser.add_argument("--profile", required=True, help="the data profile manifest whose coverage sets the grid")
    parser.add_argument("--modes-record", required=True, help="the modes record the grid is tied to")
    parser.add_argument("--out", required=True, help="the record to write; must not exist")
    parser.add_argument("--workers", type=int, default=DEFAULT_WORKERS, help="children at once")
    args = parser.parse_args(argv)
    try:
        commit = generate(args.ephe_path, args.empty_dir, args.profile, args.modes_record, args.out, args.workers)
    except Refusal as refusal:
        sys.stderr.write(f"refused: {refusal}\n")
        return 2
    with open(args.out, "rb") as handle:
        digest = hashlib.sha256(handle.read()).hexdigest()
    sys.stderr.write(f"commit {commit}\nwrote {args.out}\nsha256 {digest}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
