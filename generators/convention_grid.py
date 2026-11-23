"""Three conventions an ephemeris library applies, each read black-box across a stated grid, one call per process.

What is recorded, each as its own file:

1. **the ayanamsha, with and without nutation** — for eleven sidereal modes (three defined by a precession reference
   and eight anchored to a star or to the galactic centre, with no star catalogue anywhere on the path): the
   value the entry point without a flag returns, the value the entry point with a flag returns with and without
   the no-nutation bit, and the tropical and sidereal longitudes of the Sun and the Moon with and without that
   bit — so the ayanamsha a sidereal *position* carries can be read beside the ones the ayanamsha entry points
   return;
2. **house cusps from the instant and from the sidereal angle** — for twenty-one house methods at ten sites: the
   cusps of the entry point that takes an instant, tropical and under three sidereal modes, beside the cusps of the
   entry point that takes the sidereal angle (formed from the library's own sidereal time and the site's
   longitude) and an obliquity (each of the two the library returns), with the inputs read at the same instant;
3. **rising and setting** — the Sun and the Moon at the same ten sites on every day of a year: the disc-centre
   rise and set the analytical ephemeris returns under a stated atmosphere, beside the other disc definitions the
   library offers by name and the other atmospheres, and beside the same call made with the atmosphere left to
   the binding's defaults.

⭐ **Every reading is one call in its own fresh** ``-I`` **interpreter**, admitted only if the calls it made — every
call into the library, recorded inside the child with the arguments it received — are exactly the ones its row
declares: the path, the sidereal mode where there is one, and the reading. The library's global state therefore
cannot carry from one reading to the next. ⛔ No reading is taken in this process.

⭐ **Two conditions**, wherever both are read: ``files_absent`` — an empty directory on the path and the analytical
ephemeris requested; ``files_present`` — the pinned data files on the path and the data files requested. ⛔ No star
catalogue is in either directory, and the run is refused if any file other than the pinned three is present.

⛔ **Refused** before any reading, in this order: a dirty or commitless tree; an output that exists; a budget row not
given exactly; a binding or library that is not the pinned version, or one of whose constants is not the number
written here; a data directory that is not exactly the pinned set; a values file whose digest is not the one
given. While reading: a child that was not fresh, that repeated another's nonce, or whose calls were not its
declared ones; ⛔ a position or an ayanamsha whose returned ephemeris bits are not the requested ones (⚠ the ayanamsha's
returned word drops the no-nutation bit; that is recorded, not refused); a value that is not finite; a return whose shape is not the entry point's. After: an
empty directory or a work directory left holding anything; a reading count other than the plan's.
**Recorded, never refused**: the library raising (a method undefined at a latitude, a mode it cannot compute), a
rise or set that does not happen, two forms that return the same value.

⛔ **No band, no class but** ``reference_only``, **no verdict.** ⛔ Nothing here merges two conventions or says which
is right; a difference between two forms is a difference between two conventions, not an error in either.

⛔ **Recorder, never explainer.** Nothing here says how the library computes anything. Where its documentation names
a parameter, that name is quoted and attributed; nothing is read from or about its source.

⭐ **Rising and setting alone, at other sites**: given ``--rise-sites`` (a sites file, named by its digest), the run
reads the third file only, at the file's sites instead of the ten, and writes ``convention-rise-set.jsonl`` alone; its
header carries the file's digest and its sites. ⛔ A site whose coordinates come from a source that may not be
committed is given in such a file, outside the tracked tree, never in the list below.

Usage (a clean tree; the binding of ``requirements.txt``):
    python generators/convention_grid.py --ephe-path DIR --grid-values VALUES.jsonl \\
        --grid-values-sha256 HEX --budget-row ROW --out DIR [--workers N] \\
        [--rise-sites SITES.json --rise-sites-sha256 HEX]
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import math
import re
import os
import shutil
import struct
import subprocess
import sys
import tempfile
import threading
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field, replace
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _distribution_version
from pathlib import Path
from typing import Any, Callable, Iterable, Iterator, Mapping, Sequence

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from saakshi.fixture import Header, bits, describe_reserved_names, patterned, redact_environment, write_jsonl  # noqa: E402
from saakshi.provenance import generator_for, host_record, today  # noqa: E402


class Refusal(Exception):
    """A condition under which nothing may be recorded."""


# --------------------------------------------------------------------------------------------------------------
# What is asked, written as numbers — every constant checked against the binding before any reading
# --------------------------------------------------------------------------------------------------------------

#: The binding and library this file was written against. ⛔ Any other refuses the run before a reading.
BINDING_PIN = "2.10.3.2"
LIBRARY_PIN = "2.10.03"

#: The binding's constants this file uses, as the numbers the binding gave when it was written. ⭐ Written as
#: literals so the plan can be built where the binding is absent; ⛔ checked against the binding at run time.
CONSTANTS: dict[str, int] = {
    "FLG_SWIEPH": 2, "FLG_MOSEPH": 4, "FLG_SPEED": 256, "FLG_NONUT": 64, "FLG_SIDEREAL": 65536,
    "FLG_EQUATORIAL": 2048, "SUN": 0, "MOON": 1, "ECL_NUT": -1, "CALC_RISE": 1, "CALC_SET": 2,
    "BIT_DISC_CENTER": 256, "BIT_DISC_BOTTOM": 8192, "BIT_NO_REFRACTION": 512, "BIT_HINDU_RISING": 896,
    "SIDM_LAHIRI": 1, "SIDM_KRISHNAMURTI": 5, "SIDM_RAMAN": 3, "SIDM_TRUE_CITRA": 27, "SIDM_TRUE_REVATI": 28,
    "SIDM_TRUE_PUSHYA": 29, "SIDM_TRUE_MULA": 35, "SIDM_TRUE_SHEORAN": 39, "SIDM_GALCENT_0SAG": 17,
    "SIDM_GALCENT_RGILBRAND": 30, "SIDM_ALDEBARAN_15TAU": 14,
}
C = CONSTANTS

#: The ephemeris bits of a flag word. ⭐ A returned word is compared with the request on these bits only.
EPHEMERIS_BITS = 1 | C["FLG_SWIEPH"] | C["FLG_MOSEPH"]

#: The eleven sidereal modes, by the binding's constant name: ``(name, class)``. ⭐ The first three are defined by a
#: reference date and value; the other eight are anchored to a star or to the galactic centre, and no star
#: catalogue is present on either path.
MODES: tuple[tuple[str, str], ...] = (
    ("SIDM_LAHIRI", "reference_epoch"),
    ("SIDM_KRISHNAMURTI", "reference_epoch"),
    ("SIDM_RAMAN", "reference_epoch"),
    ("SIDM_TRUE_CITRA", "anchored"),
    ("SIDM_TRUE_REVATI", "anchored"),
    ("SIDM_TRUE_PUSHYA", "anchored"),
    ("SIDM_TRUE_MULA", "anchored"),
    ("SIDM_TRUE_SHEORAN", "anchored"),
    ("SIDM_GALCENT_0SAG", "anchored"),
    ("SIDM_GALCENT_RGILBRAND", "anchored"),
    ("SIDM_ALDEBARAN_15TAU", "anchored"),
)

#: The modes the house cusps are read under in sidereal form: the three defined by a reference.
HOUSE_MODES: tuple[str, ...] = ("SIDM_LAHIRI", "SIDM_KRISHNAMURTI", "SIDM_RAMAN")

#: The twenty-one house methods, by the single letter the library identifies each by, in the request's order.
HOUSE_SYSTEMS = "WEPKORCSTBMUVXHFDIYLQ"

#: ⭐ The one method whose sidereal-angle entry point takes a further argument, which the binding's documentation
#: names *"ascmc9: optional parameter for Sunshine"*. It is read both without it and with the Sun's declination.
SUNSHINE = "I"

#: The sites: ``(id, latitude, longitude, group)``, degrees north and east. ⚠ The ids are place names, used as labels.
SITES: tuple[tuple[str, float, float, str], ...] = (
    ("kanpur", 26.4499, 80.3319, "india"),
    ("delhi", 28.6139, 77.2090, "india"),
    ("meerut", 28.9845, 77.7064, "india"),
    ("varanasi", 25.3176, 82.9739, "india"),
    ("chennai", 13.0827, 80.2707, "india"),
    ("oslo", 59.9139, 10.7522, "high_latitude"),
    ("helsinki", 60.1699, 24.9384, "high_latitude"),
    ("sub_polar", 64.1466, -21.9426, "high_latitude"),
    ("tromso", 69.6492, 18.9553, "high_latitude"),
    ("longyearbyen", 78.2232, 15.6267, "high_latitude"),
)

#: The chart instant every file includes: 1992-11-11 01:10 UT.
CHART_INSTANT = ("chart_1992_11_11", (1992, 11, 11), 70.0)

#: The house file's dates; each is read at every whole hour, so the sidereal time takes every value at every site.
HOUSE_DATES: tuple[tuple[int, int, int], ...] = ((1900, 1, 1), (2000, 1, 1), (2026, 3, 20), (2100, 1, 1))

#: The rise and set file's year (every day of it) and the one further date.
RISE_YEAR = 2026
RISE_EXTRA_DATE = (1992, 11, 11)

#: ``(name, path state, ephemeris bit)``.
CONDITIONS: tuple[tuple[str, str, str], ...] = (
    ("files_absent", "empty_directory", "FLG_MOSEPH"),
    ("files_present", "data_files", "FLG_SWIEPH"),
)

#: The atmospheres a rise or set is asked under: ``(name, pressure, temperature)``.
ATMOSPHERES: tuple[tuple[str, float, float], ...] = (
    ("zero_zero", 0.0, 0.0),
    ("standard_pressure_15c", 1013.25, 15.0),
    ("standard_pressure_0c", 1013.25, 0.0),
)

#: The disc definitions, by the binding's bit names: ``(name, bits)``.
DISCS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("disc_center", ("BIT_DISC_CENTER",)),
    ("no_disc_bit", ()),
    ("disc_bottom", ("BIT_DISC_BOTTOM",)),
    ("hindu_rising", ("BIT_HINDU_RISING",)),
)

RISE_BODIES: tuple[str, ...] = ("SUN", "MOON")
RISE_EVENTS: tuple[str, ...] = ("CALC_RISE", "CALC_SET")

#: The data files the path may hold, by name, sorted — ⛔ checked against the pinned set before any reading.
DATA_FILES: tuple[str, ...] = ("seas_18.se1", "semo_18.se1", "sepl_18.se1")

#: The files, by stratum.
OUTPUTS: dict[str, str] = {
    "ayanamsha": "convention-ayanamsha.jsonl",
    "houses": "convention-houses.jsonl",
    "rise_set": "convention-rise-set.jsonl",
}
SECTIONS: dict[str, tuple[str, ...]] = {
    "ayanamsha": ("ayanamsha", "longitude", "nutation_obliquity"),
    "houses": ("house_inputs", "house_cusps"),
    "rise_set": ("rise_set", "source_proxy"),
}

CHILD_TIMEOUT_SECONDS = 60
CHUNK = 2000
PROGRESS_EVERY = 20000


# --------------------------------------------------------------------------------------------------------------
# The child: one call, recorded inside it
# --------------------------------------------------------------------------------------------------------------

_CHILD = r"""
import json
import os
import struct
import sys
import types

fresh = "swisseph" not in sys.modules
import swisseph as swe


def enc(x):
    if isinstance(x, bool):
        raise TypeError("a boolean")
    if isinstance(x, float):
        return {"number": x, "bits": struct.pack(">d", x).hex()}
    if isinstance(x, int):
        return {"integer": x}
    if isinstance(x, bytes):
        return {"letter": x.decode("ascii")}
    if isinstance(x, str):
        return {"text": x}
    if isinstance(x, (tuple, list)):
        return {"sequence": [enc(i) for i in x]}
    raise TypeError("an unencodable value: " + type(x).__name__)


def dec(x):
    if "bits" in x:
        return struct.unpack(">d", bytes.fromhex(x["bits"]))[0]
    if "integer" in x:
        return x["integer"]
    if "letter" in x:
        return x["letter"].encode("ascii")
    if "text" in x:
        return x["text"]
    return tuple(dec(i) for i in x["sequence"])


calls = []


def recorded(name, function):
    def call(*args, **keywords):
        calls.append({"function": name, "args": [enc(a) for a in args],
                      "keywords": {k: enc(v) for k, v in sorted(keywords.items())}})
        return function(*args, **keywords)
    return call


for name in dir(swe):
    member = getattr(swe, name)
    if name.startswith("_") or isinstance(member, (type, types.ModuleType)) or not callable(member):
        continue
    setattr(swe, name, recorded(name, member))

spec = json.loads(sys.stdin.read())
swe.set_ephe_path(spec["path"])
if spec["sidereal_mode"] is not None:
    swe.set_sid_mode(spec["sidereal_mode"], 0.0, 0.0)
call = spec["call"]
function = getattr(swe, call["function"])
try:
    out = {"returned": enc(function(*[dec(a) for a in call["args"]],
                                    **{k: dec(v) for k, v in call["keywords"].items()}))}
except swe.Error as exc:
    out = {"library_error": str(exc)}
sys.stdout.write(json.dumps({"nonce": os.urandom(16).hex(), "fresh_interpreter": fresh, "calls": calls, **out}))
"""


def enc(x: Any) -> dict[str, Any]:
    """An argument as the child records it. ⭐ A double carries its bit pattern; a letter, a sequence and an integer
    say what they are."""
    if isinstance(x, bool):
        raise Refusal("a boolean argument")
    if isinstance(x, float):
        return {"number": x, "bits": bits(x)}
    if isinstance(x, int):
        return {"integer": x}
    if isinstance(x, bytes):
        return {"letter": x.decode("ascii")}
    if isinstance(x, str):
        return {"text": x}
    if isinstance(x, (tuple, list)):
        return {"sequence": [enc(i) for i in x]}
    raise Refusal(f"an unencodable argument: {type(x).__name__}")


def unbits(pattern: str) -> float:
    return struct.unpack(">d", bytes.fromhex(pattern))[0]


@dataclass(frozen=True)
class Call:
    """One reading's call: the entry point, its positional arguments and its keywords, as the child receives them."""

    function: str
    args: tuple[Any, ...]
    keywords: tuple[tuple[str, Any], ...] = ()

    def encoded(self) -> dict[str, Any]:
        return {"function": self.function, "args": [enc(a) for a in self.args],
                "keywords": {k: enc(v) for k, v in sorted(self.keywords)}}


@dataclass(frozen=True)
class Item:
    """One planned reading: what its row says before the reading, the path state, the mode, the call."""

    base: Mapping[str, Any]
    path_state: str
    sidereal_mode: int | None
    call: Call


def spec_for(item: Item, paths: Mapping[str, str]) -> dict[str, Any]:
    return {"path": paths[item.path_state], "sidereal_mode": item.sidereal_mode, "call": item.call.encoded()}


def declared_calls(spec: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Every call a reading's child may make, in order: the path, the mode where there is one, the reading."""
    calls: list[dict[str, Any]] = [{"function": "set_ephe_path", "args": [{"text": spec["path"]}], "keywords": {}}]
    if spec["sidereal_mode"] is not None:
        calls.append({"function": "set_sid_mode", "args": [{"integer": spec["sidereal_mode"]}, enc(0.0), enc(0.0)],
                      "keywords": {}})
    calls.append(dict(spec["call"]))
    return calls


def child_environment() -> dict[str, str]:
    """This process's environment, less every ``SE_`` name the library reads."""
    return {k: v for k, v in os.environ.items() if not k.startswith("SE_")}


def run_child(spec: Mapping[str, Any], work_dir: str) -> dict[str, Any]:
    """One reading in one fresh interpreter."""
    proc = subprocess.run([sys.executable, "-I", "-c", _CHILD], input=json.dumps(dict(spec)), cwd=work_dir,
                          env=child_environment(), capture_output=True, text=True,
                          timeout=CHILD_TIMEOUT_SECONDS, check=False)
    if proc.returncode != 0:
        raise Refusal(f"a reading child failed ({proc.returncode}): {redact_environment(proc.stderr.strip())[-400:]}")
    return json.loads(proc.stdout)


class Readers:
    """Children several at once. ⛔ Each reading is still one fresh child; results come back in the plan's order."""

    def __init__(self, work_dir: str, workers: int, run: Callable[[Mapping[str, Any], str], dict[str, Any]]):
        if workers < 1:
            raise Refusal(f"{workers} children at once")
        self.work_dir, self.workers, self.run = work_dir, workers, run
        self.nonces: set[str] = set()
        self.lock = threading.Lock()

    def admit(self, spec: Mapping[str, Any], result: Mapping[str, Any]) -> Mapping[str, Any]:
        if result.get("fresh_interpreter") is not True:
            raise Refusal("a reading child had the library loaded before it was asked")
        if result.get("calls") != declared_calls(spec):
            made = [c.get("function") for c in result.get("calls") or []]
            raise Refusal(f"a reading child's calls were {made}; its row declares "
                          f"{[c['function'] for c in declared_calls(spec)]}")
        with self.lock:
            if result["nonce"] in self.nonces:
                raise Refusal("two readings came back from one child")
            self.nonces.add(result["nonce"])
        return result

    def take(self, specs: Sequence[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
        with ThreadPoolExecutor(self.workers) as pool:
            return [self.admit(spec, result)
                    for spec, result in zip(specs, pool.map(lambda s: self.run(s, self.work_dir), specs), strict=True)]


# --------------------------------------------------------------------------------------------------------------
# The instants
# --------------------------------------------------------------------------------------------------------------


def jd_ut(date: tuple[int, int, int], minutes: float = 0.0) -> float:
    """A Gregorian date and minutes past 0h UT, as a Julian day: whole days from 1970-01-01 plus the minutes."""
    days = (datetime.date(*date) - datetime.date(1970, 1, 1)).days
    return 2440587.5 + days + minutes / 1440.0


def grid_instants(values_path: Path, expected_sha256: str) -> list[float]:
    """The distinct ``jd_tdb`` of a geocentric-vector values file, ascending — refused unless its digest is given."""
    data = values_path.read_bytes()
    actual = hashlib.sha256(data).hexdigest()
    if actual != expected_sha256:
        raise Refusal(f"the values file's sha256 is {actual}, not {expected_sha256}")
    seen: dict[str, float] = {}
    for number, line in enumerate(data.decode("utf-8").splitlines()):
        record = json.loads(line)
        if record.get("record") != "row":
            continue
        value, pattern = record["jd_tdb"], record["jd_tdb_bits"]
        if bits(float(value)) != pattern:
            raise Refusal(f"line {number + 1}: jd_tdb and its pattern are different numbers")
        seen[pattern] = float(value)
    if not seen:
        raise Refusal("the values file holds no instant")
    return sorted(seen.values())


#: A site id or group from a sites file: a lower-case ASCII label, as the built-in ones are.
SITE_LABEL = re.compile(r"[a-z][a-z0-9_]*\Z")
SITE_KEYS = frozenset({"site", "latitude", "longitude", "group"})


def _no_repeated_key(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    """⛔ A JSON object with a key twice: the digest pins the bytes, but which value they mean depends on the
    parser, so a reader of the file and this run could see different sites."""
    keys = [k for k, _v in pairs]
    if len(keys) != len(set(keys)):
        raise Refusal(f"the sites file repeats a key in one object: {sorted(k for k in set(keys) if keys.count(k) > 1)}")
    return dict(pairs)


def rise_sites(sites_path: Path, expected_sha256: str) -> tuple[tuple[str, float, float, str], ...]:
    """The sites of a sites file, in its order — refused unless its digest is the one given.

    JSON: ``{"sites": [{"site": ..., "latitude": ..., "longitude": ..., "group": ...}, ...]}``, degrees north and
    east; any other top-level key is not read. ⛔ Refused: a key repeated in any object; an entry whose keys are not
    exactly those four; an id or a group that is not a lower-case ASCII label; an id that repeats or that names a
    built-in site (it would read as that site at other coordinates); a coordinate that is not a finite number within
    its range (the bounds themselves admitted).
    """
    data = sites_path.read_bytes()
    actual = hashlib.sha256(data).hexdigest()
    if actual != expected_sha256:
        raise Refusal(f"the sites file's sha256 is {actual}, not {expected_sha256}")
    try:
        document = json.loads(data.decode("utf-8"), object_pairs_hook=_no_repeated_key)
    except (UnicodeDecodeError, ValueError) as exc:  # ValueError covers a JSON error and an over-long integer
        raise Refusal(f"the sites file is not JSON this run reads: {exc}") from exc
    listed = document.get("sites") if isinstance(document, dict) else None
    if not isinstance(listed, list) or not listed:
        raise Refusal("the sites file lists no site")
    sites: list[tuple[str, float, float, str]] = []
    for number, entry in enumerate(listed, 1):
        if not isinstance(entry, dict) or set(entry) != SITE_KEYS:
            raise Refusal(f"site {number}: its keys are not exactly {sorted(SITE_KEYS)}")
        sid, group = entry["site"], entry["group"]
        if not isinstance(sid, str) or not SITE_LABEL.match(sid):
            raise Refusal(f"site {number}: the id {sid!r} is not a lower-case label")
        if any(sid == other for other, *_rest in sites):
            raise Refusal(f"site {number}: the id {sid!r} is listed twice")
        if any(sid == builtin for builtin, *_rest in SITES):
            raise Refusal(f"site {number}: the id {sid!r} names a built-in site")
        coordinates = []
        for name, bound in (("latitude", 90.0), ("longitude", 180.0)):
            value = entry[name]
            try:
                degrees = float(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else None
            except OverflowError:
                degrees = None
            if degrees is None or not math.isfinite(degrees) or abs(degrees) > bound:
                raise Refusal(f"site {number}: the {name} {value!r} is not a finite number within ±{bound:g}")
            coordinates.append(degrees)
        if not isinstance(group, str) or not SITE_LABEL.match(group):
            raise Refusal(f"site {number}: the group {group!r} is not a lower-case label")
        sites.append((sid, coordinates[0], coordinates[1], group))
    return tuple(sites)


@dataclass
class Grid:
    """The instants and lists one run reads. ⭐ The full grid is :func:`full_grid`; a test builds a smaller one."""

    ayanamsha_instants: list[tuple[str, float]]
    house_instants: list[tuple[str, float]]
    rise_dates: list[tuple[str, float]]
    modes: Sequence[tuple[str, str]] = MODES
    house_modes: Sequence[str] = HOUSE_MODES
    house_systems: str = HOUSE_SYSTEMS
    sites: Sequence[tuple[str, float, float, str]] = SITES
    #: Set when the sites came from a sites file: its digest and count, written into the header.
    sites_file: Mapping[str, Any] | None = None


def chart_instant() -> tuple[str, float]:
    iid, date, minutes = CHART_INSTANT
    return iid, jd_ut(date, minutes)


def full_grid(values: Sequence[float]) -> Grid:
    ayanamsha = [(f"g{index}", jd) for index, jd in enumerate(values)] + [chart_instant()]
    houses = [(f"h{y:04d}{m:02d}{d:02d}_{hour:02d}", jd_ut((y, m, d), 60.0 * hour))
              for y, m, d in HOUSE_DATES for hour in range(24)] + [chart_instant()]
    first = datetime.date(RISE_YEAR, 1, 1)
    days = (datetime.date(RISE_YEAR + 1, 1, 1) - first).days
    dates = [(first + datetime.timedelta(days=n)) for n in range(days)] + [datetime.date(*RISE_EXTRA_DATE)]
    rise = [(f"d{day.isoformat().replace('-', '')}", jd_ut((day.year, day.month, day.day))) for day in dates]
    return Grid(ayanamsha_instants=ayanamsha, house_instants=houses, rise_dates=rise)


# --------------------------------------------------------------------------------------------------------------
# The plan
# --------------------------------------------------------------------------------------------------------------


def _mode(name: str) -> dict[str, Any]:
    return {"sidereal_mode": C[name], "sidereal_mode_name": name}


def plan_ayanamsha(grid: Grid) -> list[Item]:
    items: list[Item] = []
    speed, nonut, sidereal = C["FLG_SPEED"], C["FLG_NONUT"], C["FLG_SIDEREAL"]
    for iid, jd in grid.ayanamsha_instants:
        for condition, path_state, bit in CONDITIONS:
            e = C[bit]
            at = {"condition": condition, "instant_id": iid, **patterned("jd_ut", jd)}
            for body in ("SUN", "MOON"):
                for nut, word in (("with_nutation", e | speed), ("no_nutation", e | speed | nonut)):
                    items.append(Item({"section": "longitude", "form": f"{body.lower()}_tropical_{nut}", **at,
                                       "requested": word}, path_state, None, Call("calc_ut", (jd, C[body], word))))
            items.append(Item({"section": "nutation_obliquity", "form": "nutation_obliquity", **at, "requested": e},
                              path_state, None, Call("calc_ut", (jd, C["ECL_NUT"], e))))
            for name, _klass in grid.modes:
                m = {**at, **_mode(name)}
                items.append(Item({"section": "ayanamsha", "form": "ayanamsha_unflagged", **m}, path_state, C[name],
                                  Call("get_ayanamsa_ut", (jd,))))
                for nut, word in (("with_nutation", e), ("no_nutation", e | nonut)):
                    items.append(Item({"section": "ayanamsha", "form": f"ayanamsha_flagged_{nut}", **m,
                                       "requested": word}, path_state, C[name], Call("get_ayanamsa_ex_ut", (jd, word))))
                for body in ("SUN", "MOON"):
                    for nut, word in (("with_nutation", e | sidereal | speed),
                                      ("no_nutation", e | sidereal | speed | nonut)):
                        items.append(Item({"section": "longitude", "form": f"{body.lower()}_sidereal_{nut}", **m,
                                           "requested": word}, path_state, C[name],
                                          Call("calc_ut", (jd, C[body], word))))
    return items


def plan_house_inputs(grid: Grid) -> list[Item]:
    items: list[Item] = []
    for iid, jd in grid.house_instants:
        for condition, path_state, bit in CONDITIONS:
            e = C[bit]
            at = {"section": "house_inputs", "condition": condition, "instant_id": iid, **patterned("jd_ut", jd)}
            items.append(Item({**at, "form": "sidereal_time"}, path_state, None, Call("sidtime", (jd,))))
            items.append(Item({**at, "form": "nutation_obliquity", "requested": e}, path_state, None,
                              Call("calc_ut", (jd, C["ECL_NUT"], e))))
            items.append(Item({**at, "form": "sun_source_proxy", "requested": e}, path_state, None,
                              Call("calc_ut", (jd, C["SUN"], e))))
            word = e | C["FLG_EQUATORIAL"]
            items.append(Item({**at, "form": "sun_equatorial", "requested": word}, path_state, None,
                              Call("calc_ut", (jd, C["SUN"], word))))
            for name in grid.house_modes:
                for nut, flag in (("with_nutation", e), ("no_nutation", e | C["FLG_NONUT"])):
                    items.append(Item({**at, **_mode(name), "form": f"ayanamsha_flagged_{nut}", "requested": flag},
                                      path_state, C[name], Call("get_ayanamsa_ex_ut", (jd, flag))))
    return items


def armc_of(sidereal_time_hours: float, longitude: float) -> float:
    """The sidereal angle handed to the angle entry point: the library's sidereal time in degrees plus the site's
    east longitude, reduced to [0, 360). ⭐ An input formed from a reading's bits, written with its own."""
    armc = math.fmod(sidereal_time_hours * 15.0 + longitude, 360.0)
    return armc + 360.0 if armc < 0.0 else armc


@dataclass(frozen=True)
class HouseInputs:
    sidereal_time: float
    obliquity_true: float
    obliquity_mean: float
    sun_declination: float


def house_inputs_from(items: Sequence[Item], rows: Sequence[Mapping[str, Any]]) -> dict[tuple[str, str], HouseInputs]:
    """The angle entry point's inputs, per instant and condition, from the input readings' own bits."""
    got: dict[tuple[str, str], dict[str, float]] = {}
    for item, row in zip(items, rows, strict=True):
        if "values_bits" not in row:
            raise Refusal(f"an input reading returned no value: {item.base['form']} at {item.base['instant_id']}")
        values = [unbits(p) for p in row["values_bits"]]
        slot = got.setdefault((item.base["instant_id"], item.base["condition"]), {})
        form = item.base["form"]
        if form == "sidereal_time":
            slot["sidereal_time"] = values[0]
        elif form == "nutation_obliquity":
            slot["obliquity_true"], slot["obliquity_mean"] = values[0], values[1]
        elif form == "sun_equatorial":
            slot["sun_declination"] = values[1]
    needed = {"sidereal_time", "obliquity_true", "obliquity_mean", "sun_declination"}
    for key, slot in got.items():
        if set(slot) != needed:
            raise Refusal(f"the inputs at {key} are {sorted(slot)}, not {sorted(needed)}")
    return {key: HouseInputs(**slot) for key, slot in got.items()}


def plan_houses(grid: Grid, inputs: Mapping[tuple[str, str], HouseInputs]) -> list[Item]:
    items: list[Item] = []
    sidereal = C["FLG_SIDEREAL"]
    for iid, jd in grid.house_instants:
        for condition, path_state, bit in CONDITIONS:
            e = C[bit]
            got = inputs[(iid, condition)]
            for sid, lat, lon, _group in grid.sites:
                armc = armc_of(got.sidereal_time, lon)
                for letter in grid.house_systems:
                    hs = letter.encode("ascii")
                    at = {"section": "house_cusps", "condition": condition, "instant_id": iid,
                          **patterned("jd_ut", jd), "site": sid, "house_system": letter}
                    items.append(Item({**at, "form": "instant_tropical", "requested": e}, path_state, None,
                                      Call("houses_ex", (jd, lat, lon, hs, e))))
                    for name in grid.house_modes:
                        items.append(Item({**at, **_mode(name), "form": "instant_sidereal",
                                           "requested": e | sidereal}, path_state, C[name],
                                          Call("houses_ex", (jd, lat, lon, hs, e | sidereal))))
                    items.append(Item({**at, "form": "angle_obliquity_true"}, path_state, None,
                                      Call("houses_armc", (armc, lat, got.obliquity_true, hs))))
                    items.append(Item({**at, "form": "angle_obliquity_mean"}, path_state, None,
                                      Call("houses_armc", (armc, lat, got.obliquity_mean, hs))))
                    if letter == SUNSHINE:
                        items.append(Item({**at, "form": "angle_obliquity_true_sun_declination"}, path_state, None,
                                          Call("houses_armc", (armc, lat, got.obliquity_true, hs,
                                                               got.sun_declination))))
                    if condition == "files_absent":
                        for name in grid.house_modes:
                            items.append(Item({**at, **_mode(name), "form": "instant_sidereal_no_ephemeris_bit",
                                               "requested": sidereal}, path_state, C[name],
                                              Call("houses_ex", (jd, lat, lon, hs, sidereal))))
    return items


def rise_forms() -> list[tuple[str, int, tuple[Any, ...] | None]]:
    """``(name, disc bits, (pressure, temperature) or None for the binding's defaults)``, the first the call made
    with the atmosphere and flags passed by keyword and the atmosphere left out."""
    forms: list[tuple[str, int, tuple[Any, ...] | None]] = [("disc_center_atmosphere_omitted", C["BIT_DISC_CENTER"],
                                                             None)]
    for disc, names in DISCS:
        word = 0
        for name in names:
            word |= C[name]
        for atmosphere, pressure, temperature in ATMOSPHERES:
            forms.append((f"{disc}_{atmosphere}", word, (pressure, temperature)))
    forms.append(("disc_center_no_refraction_zero_zero", C["BIT_DISC_CENTER"] | C["BIT_NO_REFRACTION"], (0.0, 0.0)))
    return forms


def plan_rise(grid: Grid) -> list[Item]:
    items: list[Item] = []
    moshier = C["FLG_MOSEPH"]
    condition, path_state, _bit = CONDITIONS[0]
    for did, jd0 in grid.rise_dates:
        for at_jd, form in ((jd0, "sun_source_proxy_day_start"), (jd0 + 1.0, "sun_source_proxy_day_end")):
            items.append(Item({"section": "source_proxy", "form": form, "condition": condition, "date_id": did,
                               **patterned("jd_ut", at_jd), "requested": moshier}, path_state, None,
                              Call("calc_ut", (at_jd, C["SUN"], moshier))))
        for sid, lat, lon, _group in grid.sites:
            start = jd0 - lon / 360.0
            geopos = (lon, lat, 0.0)
            for body in RISE_BODIES:
                for event in RISE_EVENTS:
                    for form, disc, atmosphere in rise_forms():
                        rsmi = C[event] | disc
                        base = {"section": "rise_set", "form": form, "condition": condition, "date_id": did,
                                **patterned("search_start_jd_ut", start), "site": sid, "body": body.lower(),
                                "event": "rise" if event == "CALC_RISE" else "set", "rsmi": rsmi,
                                "requested": moshier}
                        if atmosphere is None:
                            call = Call("rise_trans", (start, C[body]),
                                        (("rsmi", rsmi), ("geopos", geopos), ("flags", moshier)))
                        else:
                            call = Call("rise_trans", (start, C[body], rsmi, geopos, *atmosphere, moshier))
                        items.append(Item(base, path_state, None, call))
    return items


def planned_counts(grid: Grid) -> dict[str, int]:
    """The reading count each file's plan holds, by arithmetic on the grid — ⛔ checked against the plan itself."""
    n_modes, n_hm, n_sys = len(grid.modes), len(grid.house_modes), len(grid.house_systems)
    n_sites, sunshine = len(grid.sites), grid.house_systems.count(SUNSHINE)
    return {
        "ayanamsha": len(grid.ayanamsha_instants) * len(CONDITIONS) * (5 + 7 * n_modes),
        "house_inputs": len(grid.house_instants) * len(CONDITIONS) * (4 + 2 * n_hm),
        "house_cusps": len(grid.house_instants) * n_sites * (
            len(CONDITIONS) * (n_sys * (3 + n_hm) + sunshine) + n_sys * n_hm),
        "rise_set": len(grid.rise_dates) * (2 + n_sites * len(RISE_BODIES) * len(RISE_EVENTS) * len(rise_forms())),
    }


# --------------------------------------------------------------------------------------------------------------
# From a child's return to a row
# --------------------------------------------------------------------------------------------------------------

#: Per entry point: how many integers its return carries, and how many doubles.
RETURN_SHAPES: dict[str, tuple[int, int]] = {
    "calc_ut": (1, 6), "get_ayanamsa_ex_ut": (1, 1), "get_ayanamsa_ut": (0, 1), "sidtime": (0, 1),
    "houses_ex": (0, 20), "houses_armc": (0, 20), "rise_trans": (1, 10),
}


def _flatten(node: Mapping[str, Any], floats: list[float], ints: list[int]) -> str:
    """The return's doubles and integers in order, and its layout as text. ⛔ A double whose two forms differ refuses."""
    if "bits" in node:
        value = unbits(node["bits"])
        if bits(float(node["number"])) != node["bits"]:
            raise Refusal("a returned double and its pattern are different numbers")
        floats.append(value)
        return "double"
    if "integer" in node:
        ints.append(int(node["integer"]))
        return "integer"
    if "sequence" in node:
        parts = [_flatten(child, floats, ints) for child in node["sequence"]]
        grouped: list[str] = []
        for part in parts:
            if grouped and grouped[-1].split(" ", 1)[-1] == part and grouped[-1][0].isdigit():
                count, _ = grouped[-1].split(" ", 1)
                grouped[-1] = f"{int(count) + 1} {part}"
            else:
                grouped.append(f"1 {part}")
        return "(" + ", ".join(grouped) + ")"
    raise Refusal(f"a returned element of no known kind: {sorted(node)}")


def clean(text: str, paths: Mapping[str, str]) -> str:
    """A message the library wrote, with the run's directories named by their role and any other path removed."""
    for role, path in sorted(paths.items(), key=lambda kv: -len(kv[1])):
        text = text.replace(path.rstrip("/") + "/", f"<{role}>/").replace(path.rstrip("/"), f"<{role}>")
    return redact_environment(text)


def row_of(item: Item, result: Mapping[str, Any], paths: Mapping[str, str]) -> dict[str, Any]:
    row: dict[str, Any] = {**item.base, "call": item.call.encoded()}
    if "library_error" in result:
        row["library_error"] = clean(str(result["library_error"]), paths)
        return row
    floats: list[float] = []
    ints: list[int] = []
    row["return_layout"] = _flatten(result["returned"], floats, ints)
    where = f"{item.base['form']} at {item.base.get('instant_id', item.base.get('date_id'))}"
    want = RETURN_SHAPES[item.call.function]
    if (len(ints), len(floats)) != want:
        raise Refusal(f"{where}: {item.call.function} returned {len(ints)} integers and {len(floats)} doubles, "
                      f"not {want[0]} and {want[1]}")
    if not all(math.isfinite(v) for v in floats):
        raise Refusal(f"{where}: a value that is not finite")
    requested = item.base.get("requested")
    if item.call.function == "calc_ut" and (ints[0] & EPHEMERIS_BITS) != (requested & EPHEMERIS_BITS):
        raise Refusal(f"{where}: the returned ephemeris bits are {ints[0] & EPHEMERIS_BITS}, "
                      f"not the requested {requested & EPHEMERIS_BITS}")
    if item.call.function == "get_ayanamsa_ex_ut" and (ints[0] & EPHEMERIS_BITS) != (requested & EPHEMERIS_BITS):
        # ⚠ The whole word is NOT compared: measured, the returned word drops FLG_NONUT from a request that carries
        #   it, and that is recorded on every row beside the request — it is not a substitution of the ephemeris.
        raise Refusal(f"{where}: the returned ephemeris bits are {ints[0] & EPHEMERIS_BITS}, "
                      f"not the requested {requested & EPHEMERIS_BITS}")
    row.update(patterned("values", floats))
    if item.call.function == "rise_trans":
        row["return_code"] = ints[0]
    elif ints:
        row["returned_flag"] = ints[0]
    return row


# --------------------------------------------------------------------------------------------------------------
# Measuring, staged; nothing written until every reading is in
# --------------------------------------------------------------------------------------------------------------


@dataclass
class Staged:
    path: Path
    rows: int = 0
    by_form: Counter = field(default_factory=Counter)
    errors: Counter = field(default_factory=Counter)
    codes: Counter = field(default_factory=Counter)

    def add(self, row: Mapping[str, Any], fh) -> None:
        fh.write(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n")
        self.rows += 1
        self.by_form[(row["section"], row["form"], row["condition"])] += 1
        if "library_error" in row:
            self.errors[(row["form"], row.get("house_system", ""), row.get("site", ""),
                         row.get("sidereal_mode_name", ""), row["library_error"])] += 1
        if "return_code" in row:
            self.codes[(row["form"], row["site"], row["body"], row["event"], row["return_code"])] += 1

    def rows_back(self) -> Iterator[dict[str, Any]]:
        with self.path.open(encoding="utf-8") as fh:
            for line in fh:
                yield json.loads(line)


def measure(items: Sequence[Item], readers: Readers, paths: Mapping[str, str], staged: Staged | None,
            keep: bool = False) -> list[dict[str, Any]]:
    """Every item read, in order; each row staged (or kept, for the inputs the next plan is built from)."""
    kept: list[dict[str, Any]] = []
    fh = staged.path.open("a", encoding="utf-8") if staged is not None else None
    try:
        for start in range(0, len(items), CHUNK):
            chunk = items[start:start + CHUNK]
            specs = [spec_for(item, paths) for item in chunk]
            for item, result in zip(chunk, readers.take(specs), strict=True):
                row = row_of(item, result, paths)
                if staged is not None:
                    staged.add(row, fh)
                if keep:
                    kept.append(row)
            done = start + len(chunk)
            if done % PROGRESS_EVERY < CHUNK or done == len(items):
                sys.stderr.write(f"{done} of {len(items)} readings\n")
    finally:
        if fh is not None:
            fh.close()
    return kept


# --------------------------------------------------------------------------------------------------------------
# The header
# --------------------------------------------------------------------------------------------------------------

ROW_SCHEMA: dict[str, str] = {
    "section": "which question within this file the row answers",
    "form": "the call form: which entry point, under which word or arguments (named in the header's request)",
    "condition": "files_absent: an empty directory on the path and the analytical ephemeris requested; "
                 "files_present: the pinned data files on the path and the data files requested",
    "instant_id": "the instant's id within this file's grid (ayanamsha and house files)",
    "date_id": "the date's id (rise and set file): d<yyyymmdd>",
    "jd_ut": "the instant, a Julian day in UT, as handed to the entry point — ⚠ display; jd_ut_bits is the value",
    "search_start_jd_ut": "rise and set: where the search starts — the date's 0h UT less the site's east "
                          "longitude over 360 days (its local mean midnight)",
    "site": "the site id; its coordinates are in the header's request",
    "house_system": "the single letter the library identifies the house method by",
    "sidereal_mode": "the sidereal mode set before the reading, as set_sid_mode(mode, 0.0, 0.0)",
    "sidereal_mode_name": "the binding's name for that constant",
    "body": "sun | moon", "event": "rise | set", "rsmi": "the event word handed to the rise and set entry point",
    "requested": "the flag word handed to the entry point, where it takes one",
    "call": "⭐ the reading's call exactly as the child received it: entry point, positional arguments and "
            "keywords; a double as {number, bits}, a letter, an integer, a sequence",
    "return_layout": "the shape of what the entry point returned, in order (doubles and integers)",
    "values": "every double the entry point returned, in its order — ⚠ display; values_bits is the value",
    "returned_flag": "the integer the entry point returned beside its values (a position, an ayanamsha)",
    "return_code": "rise and set: the integer the entry point returned (0, or what it returned instead)",
    "library_error": "the library raised instead of returning: its message, with the run's directories named "
                     "by role. ⭐ Recorded, never refused",
}


def oracle_block(swe_version: str, binding_version: str, data_files: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "implementation": "Swiss Ephemeris",
        "library_version": swe_version,
        "called_via": {"binding": "pyswisseph", "version": binding_version},
        "isolation": "every reading is one call in a fresh -I interpreter whose calls are recorded inside it and "
                     "admitted only if exactly the declared ones: the path, the sidereal mode where there is one, "
                     "the reading",
        "data_files": dict(data_files),
        "empty_directory": "a directory made for the run, empty before and after it",
        "star_catalogue": "none: neither directory holds any file but the pinned data files (the empty one none)",
        "licence": "the library is AGPL-3.0; it is called here, never redistributed by this repository",
    }


def request_block(stratum: str, grid: Grid, grid_values: Mapping[str, Any], budget_row: str) -> dict[str, Any]:
    common = {
        "conditions": [{"condition": c, "path": p, "ephemeris_bit": b, "ephemeris_bit_value": C[b]}
                       for c, p, b in CONDITIONS],
        "constants": [{"name": n, "value": v} for n, v in CONSTANTS.items()],
        "regenerate": "generators/convention_grid.py --ephe-path <the pinned data files> --grid-values <values "
                      f"file> --grid-values-sha256 {grid_values['values_sha256']} --budget-row {budget_row} "
                      "--out <a new dir>" + ("" if grid.sites_file is None else
                                             " --rise-sites <the sites file> --rise-sites-sha256 "
                                             f"{grid.sites_file['sha256']}"),
    }
    if stratum == "ayanamsha":
        return {**common, "modes": [{"name": n, "number": C[n], "class": k} for n, k in grid.modes],
                "instants": {**grid_values, "count": len(grid.ayanamsha_instants),
                             "rule": "the distinct jd_tdb of the values file named by its sha256, each checked "
                                     "against its bits and used as a UT Julian day; and the chart instant, "
                                     "1992-11-11 01:10 UT"},
                "forms": "per instant and condition: the Sun and the Moon, tropical, with and without FLG_NONUT; "
                         "the nutation and obliquity pseudo-body. Per mode as well: get_ayanamsa_ut; "
                         "get_ayanamsa_ex_ut with and without FLG_NONUT; the Sun and the Moon with FLG_SIDEREAL, "
                         "with and without FLG_NONUT. FLG_SPEED on every position"}
    sites = [{"site": s, **patterned("latitude", la), **patterned("longitude", lo), "group": g}
             for s, la, lo, g in grid.sites]
    if stratum == "houses":
        return {**common, "sites": sites, "house_systems": grid.house_systems,
                "modes": [{"name": n, "number": C[n]} for n in grid.house_modes],
                "instants": {"count": len(grid.house_instants),
                             "rule": "every whole hour UT of " + ", ".join(f"{y:04d}-{m:02d}-{d:02d}"
                                                                          for y, m, d in HOUSE_DATES)
                                     + "; and the chart instant, 1992-11-11 01:10 UT"},
                "forms": "inputs per instant and condition: sidtime; the nutation and obliquity pseudo-body; the "
                         "Sun (the source proxy: the house entry points return no flag); the Sun with "
                         "FLG_EQUATORIAL; get_ayanamsa_ex_ut with and without FLG_NONUT per mode. Cusps per site "
                         "and method: houses_ex tropical; houses_ex with FLG_SIDEREAL per mode; houses_armc with "
                         "the angle and components 0 and 1 of the obliquity return; for the method "
                         f"{SUNSHINE!r} also with the Sun's declination (component 1 of the equatorial return) "
                         "as the fifth argument; and, files absent only, houses_ex with FLG_SIDEREAL and no "
                         "ephemeris bit, per mode",
                "angle": "the sidtime reading in degrees plus the site's east longitude, reduced to [0, 360)"}
    if grid.sites_file is not None:
        common = {**common, "sites_file": dict(grid.sites_file)}
    return {**common, "sites": sites, "bodies": [b.lower() for b in RISE_BODIES],
            "events": ["rise", "set"], "condition": CONDITIONS[0][0],
            "dates": {"count": len(grid.rise_dates),
                      "rule": f"every day of {RISE_YEAR}; and {RISE_EXTRA_DATE[0]:04d}-{RISE_EXTRA_DATE[1]:02d}-"
                              f"{RISE_EXTRA_DATE[2]:02d}"},
            "forms": [{"form": name, "disc_word": disc,
                       "atmosphere": "omitted (pressure, temperature and flags by keyword; the binding's defaults)"
                       if atm is None else {**patterned("pressure", atm[0]), **patterned("temperature", atm[1])}}
                      for name, disc, atm in rise_forms()],
            "geopos": "(longitude, latitude, 0.0)",
            "source_proxy": "the Sun at each date's 0h UT and one day later, under the same word"}


TITLES = {
    "ayanamsha": "the ayanamsha with and without nutation, eleven modes, beside the longitudes it is applied to",
    "houses": "house cusps from the instant and from the sidereal angle, twenty-one methods at ten sites",
    "rise_set": "rising and setting of the Sun and the Moon under every disc definition and three atmospheres",
}


def build_header(*, stratum: str, generator, grid: Grid, oracle: Mapping[str, Any], grid_values: Mapping[str, Any],
                 staged: Sequence[Staged], planned: int, budget_row: str) -> Header:
    by_form = Counter()
    errors = Counter()
    codes = Counter()
    for s in staged:
        by_form.update(s.by_form)
        errors.update(s.errors)
        codes.update(s.codes)
    summary: dict[str, Any] = {
        "readings": sum(s.rows for s in staged),
        "readings_planned": planned,
        "rows_by_form": [{"section": a, "form": b, "condition": c, "rows": n}
                         for (a, b, c), n in sorted(by_form.items())],
        "library_errors": [{"form": f, "house_system": h, "site": s, "sidereal_mode_name": m, "message": t,
                            "rows": n} for (f, h, s, m, t), n in sorted(errors.items())],
        "host": host_record(),
    }
    if codes:
        summary["return_codes"] = [{"form": f, "site": s, "body": b, "event": e, "return_code": c, "rows": n}
                                   for (f, s, b, e, c), n in sorted(codes.items())]
    return Header(
        fixture_kind="numeric_pin",
        reference="R3",
        generator=generator,
        generated=today(),
        title=TITLES[stratum] + ("" if grid.sites_file is None else ", at the sites of a sites file"),
        oracle=dict(oracle),
        request=request_block(stratum, grid, grid_values, budget_row),
        classification={name: {"class": "reference_only"} for name in SECTIONS[stratum]},
        budget_row=budget_row,
        row_schema=ROW_SCHEMA,
        summary=summary,
        notes=[
            "⛔ reference_only throughout: a convention this library applies is not thereby the right one, and a "
            "difference between two forms is a difference between two conventions rather than an error in either.",
            "⛔ No band and no verdict. Nothing here merges two conventions.",
            "⭐ Every double carries its bit pattern; the decimal beside it is display.",
            "⭐ A library error is a recorded answer, not a failure of the recorder.",
        ],
    )


# --------------------------------------------------------------------------------------------------------------
# The run
# --------------------------------------------------------------------------------------------------------------


def require_binding() -> tuple[str, str]:
    """The binding's version, the library's and every constant used — ⛔ refused unless the pinned ones."""
    try:
        binding = _distribution_version("pyswisseph")
    except PackageNotFoundError as exc:
        raise Refusal("the binding is not installed") from exc
    if binding != BINDING_PIN:
        raise Refusal(f"the binding is {binding}, not {BINDING_PIN}")
    import swisseph as swe

    if swe.version != LIBRARY_PIN:
        raise Refusal(f"the library is {swe.version}, not {LIBRARY_PIN}")
    wrong = {n: getattr(swe, n, None) for n, v in CONSTANTS.items() if getattr(swe, n, None) != v}
    if wrong:
        raise Refusal(f"the binding's constants differ from the numbers written here: {wrong}")
    return swe.version, binding


def require_data_directory(directory: Path) -> dict[str, Any]:
    """⛔ Exactly the pinned data files and nothing else — no star catalogue, no leap-second file."""
    names = sorted(p.name for p in directory.iterdir())
    if names != list(DATA_FILES):
        raise Refusal(f"the data directory holds {names}, not exactly {list(DATA_FILES)}")
    from saakshi.kernels import KernelIdentityError
    from saakshi.swiss import EPHE_PINS, ephe_set_identity, verify_ephe_set

    if sorted(EPHE_PINS) != list(DATA_FILES):
        raise Refusal(f"the pinned data files are {sorted(EPHE_PINS)}, not the {list(DATA_FILES)} written here")
    try:
        return ephe_set_identity(directory, verify_ephe_set(directory))
    except KernelIdentityError as exc:
        raise Refusal(f"a data file is not its pin: {exc}") from exc


def require_empty(directory: Path, role: str) -> None:
    left = sorted(p.name for p in directory.iterdir())
    if left:
        raise Refusal(f"the {role} holds {left}")


#: Which plan counts each output's stratum holds.
STRATUM_PLANS: dict[str, tuple[str, ...]] = {
    "ayanamsha": ("ayanamsha",), "houses": ("house_inputs", "house_cusps"), "rise_set": ("rise_set",)}


def run(grid: Grid, *, paths: Mapping[str, str], work_dir: str, staging: Path, workers: int,
        runner: Callable[[Mapping[str, Any], str], dict[str, Any]] = run_child,
        strata: Sequence[str] = tuple(OUTPUTS)) -> tuple[dict[str, list[Staged]], dict[str, int]]:
    """Every reading of the strata asked for, staged under ``staging``. Returns the staged files per output and the
    plan's counts, for those strata only. ⛔ Nothing of a stratum not asked for is planned or read."""
    if not strata or len(set(strata)) != len(strata) or not set(strata) <= set(OUTPUTS):
        raise Refusal(f"the strata {list(strata)} are not distinct names among {list(OUTPUTS)}")
    readers = Readers(work_dir, workers, runner)
    counts = planned_counts(grid)
    planned = {name: counts[name] for stratum in OUTPUTS if stratum in strata for name in STRATUM_PLANS[stratum]}
    staged: dict[str, list[Staged]] = {}

    plans = {"ayanamsha": plan_ayanamsha(grid) if "ayanamsha" in strata else None,
             "house_inputs": plan_house_inputs(grid) if "houses" in strata else None,
             "rise_set": plan_rise(grid) if "rise_set" in strata else None}
    for name, plan in plans.items():
        if plan is not None and len(plan) != planned[name]:
            raise Refusal(f"the {name} plan holds {len(plan)} readings; the grid's arithmetic says {planned[name]}")

    if "ayanamsha" in strata:
        s_a = Staged(staging / "ayanamsha.rows")
        measure(plans["ayanamsha"], readers, paths, s_a)
        staged["ayanamsha"] = [s_a]

    if "houses" in strata:
        hi = plans["house_inputs"]
        s_hi = Staged(staging / "house_inputs.rows")
        input_rows = measure(hi, readers, paths, s_hi, keep=True)
        h = plan_houses(grid, house_inputs_from(hi, input_rows))
        if len(h) != planned["house_cusps"]:
            raise Refusal(f"the house plan holds {len(h)} readings; the grid's arithmetic says "
                          f"{planned['house_cusps']}")
        s_h = Staged(staging / "house_cusps.rows")
        measure(h, readers, paths, s_h)
        staged["houses"] = [s_hi, s_h]

    if "rise_set" in strata:
        s_r = Staged(staging / "rise_set.rows")
        measure(plans["rise_set"], readers, paths, s_r)
        staged["rise_set"] = [s_r]

    read = len(readers.nonces)
    if read != sum(planned.values()):
        raise Refusal(f"{read} readings were taken; the plan holds {sum(planned.values())}")
    return staged, planned


def emit(out_dir: Path, *, staged: Mapping[str, Sequence[Staged]], planned: Mapping[str, int], generator, grid: Grid,
         oracle: Mapping[str, Any], grid_values: Mapping[str, Any], budget_row: str) -> list[tuple[Path, int]]:
    written = []
    for stratum, output in OUTPUTS.items():
        if not all(name in planned for name in STRATUM_PLANS[stratum]):
            if stratum in staged:
                raise Refusal(f"the {stratum} stratum was staged but not planned")
            continue  # ⭐ a stratum that was not planned writes no file
        if stratum not in staged:
            raise Refusal(f"the {stratum} stratum was planned but nothing was staged")
        parts = staged[stratum]
        header = build_header(stratum=stratum, generator=generator, grid=grid, oracle=oracle, grid_values=grid_values,
                              staged=parts, planned=sum(planned[n] for n in STRATUM_PLANS[stratum]),
                              budget_row=budget_row)

        def rows() -> Iterator[dict[str, Any]]:
            for part in parts:
                yield from part.rows_back()

        path = out_dir / output
        written.append((path, write_jsonl(path, header, rows(), declared_sections=list(SECTIONS[stratum]))))
    return written


def grid_for(values: Sequence[float], sites_path: str | None,
             sites_sha256: str | None) -> tuple[Grid, tuple[str, ...]]:
    """The grid one run reads, and its strata: the full grid and every stratum; or, given a sites file, rising and
    setting alone, at the file's sites instead of the ten."""
    grid = full_grid(values)
    if sites_path is None:
        return grid, tuple(OUTPUTS)
    sites = rise_sites(Path(sites_path), sites_sha256)
    return replace(grid, sites=sites, sites_file={"sha256": sites_sha256, "count": len(sites)}), ("rise_set",)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    for name in ("--ephe-path", "--grid-values", "--grid-values-sha256", "--budget-row", "--out"):
        parser.add_argument(name, required=True)
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--rise-sites", help="a sites file: read rising and setting alone, at its sites")
    parser.add_argument("--rise-sites-sha256", help="the sites file's sha256; required with --rise-sites")
    args = parser.parse_args(argv)
    if (args.rise_sites is None) != (args.rise_sites_sha256 is None):
        parser.error("--rise-sites and --rise-sites-sha256 are given together or not at all")
    print(describe_reserved_names())
    out_dir = Path(args.out)
    temp_root = Path(tempfile.mkdtemp(prefix="convention-grid-")).resolve()
    try:
        generator = generator_for(Path(__file__))
        for output in OUTPUTS.values():
            if (out_dir / output).exists():
                raise Refusal(f"{output} exists in the output directory; each emission goes to a new one")
        if not args.budget_row or args.budget_row != args.budget_row.strip():
            raise Refusal("--budget-row is the consumer's row id, given exactly")
        swe_version, binding = require_binding()
        ephe = Path(args.ephe_path).resolve()
        data_files = require_data_directory(ephe)
        values = grid_instants(Path(args.grid_values), args.grid_values_sha256)
        grid, strata = grid_for(values, args.rise_sites, args.rise_sites_sha256)
        empty, work, staging = temp_root / "empty", temp_root / "work", temp_root / "staging"
        for d in (empty, work, staging):
            d.mkdir()
        paths = {"empty_directory": str(empty), "data_files": str(ephe)}
        counts = planned_counts(grid)
        print(f"planned: { {n: counts[n] for s in strata for n in STRATUM_PLANS[s]} }")
        staged, planned = run(grid, paths=paths, work_dir=str(work), staging=staging, workers=args.workers,
                              strata=strata)
        require_empty(empty, "empty directory")
        require_empty(work, "work directory")
        if sorted(p.name for p in ephe.iterdir()) != sorted(data_files_names(data_files)):
            raise Refusal("the data directory changed during the run")
        grid_values = {"values_sha256": args.grid_values_sha256, "distinct_instants": len(values)}
        written = emit(out_dir, staged=staged, planned=planned, generator=generator, grid=grid,
                       oracle=oracle_block(swe_version, binding, data_files), grid_values=grid_values,
                       budget_row=args.budget_row)
    except (Refusal, OSError) as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)
    for path, rows in written:
        print(f"wrote {rows} rows -> {path} (sha256 {hashlib.sha256(path.read_bytes()).hexdigest()})")
    return 0


def data_files_names(data_files: Mapping[str, Any]) -> list[str]:
    return [f["dataset"] for f in data_files["files"]]


if __name__ == "__main__":
    raise SystemExit(main())
