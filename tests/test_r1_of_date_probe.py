"""The R1 of-date probe's own refusals, every one beside a twin it accepts.

⭐ No network, and no response the service ever sent. Every payload here is written below, by hand, in the shape
the probe reads, with numbers nobody measured. What is tested is that the probe refuses what it must and says
what answered on every row it writes.
"""

from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
import sys
import urllib.parse
from pathlib import Path

import pytest

from saakshi import acquisition, service
from saakshi.acquisition import USER_AGENT, Retrieval
from saakshi.service import ServiceFormatError

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "generators" / "r1_of_date_probe.py"


def _load():
    spec = importlib.util.spec_from_file_location("r1_of_date_probe", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules["r1_of_date_probe"] = module
    spec.loader.exec_module(module)
    return module


probe = _load()

RULE = "*" * 79
STAMP = "Ephemeris / API_USER Mon Jan  5 01:02:03 2026 Pasadena, USA      / Horizons    "

# --------------------------------------------------------------------------------------
# Synthetic responses
# --------------------------------------------------------------------------------------

_SHAPES = {
    "hms": ("12 34 56.78", "-12 34 56.7"),
    "hms_extra": ("12 34 56.789012", "-12 34 56.78901"),
    "deg": ("123.45679", "-12.34568"),
    "deg_extra": ("123.456789012", "-12.345678901"),
}


def header_line(variant: str) -> str:
    labels = [label for label, _ in next(v for v in probe.VARIANTS if v["variant"] == variant)["columns"]]
    return ", ".join(labels) + ","


def csv_line(variant: str, jd: float) -> str:
    ra, dec = _SHAPES[variant]
    return f"{jd:.9f}, , , {ra}, {dec},  124.5678901,  -1.2345678,"


def default_line(jd: float) -> str:
    stamp = probe.modes.civil(jd)
    month = list(probe._MONTHS)[int(stamp[5:7]) - 1]
    return f" {stamp[0:4]}-{month}-{stamp[8:10]} {stamp[11:19]}.000     12 34 56.78 -12 34 56.7  124.5678901  -1.2345678"


def observer_text(*, target: str = "Sun (10)", solution: str = "DE441", center: str = "DE441", columns: str,
                  rows: list[str], eop: bool = True, stamp: bool = True, extra_target: bool = False,
                  deflection: bool = True) -> str:
    lines = ["", RULE]
    if stamp:
        lines.append(STAMP)
    lines += [RULE, f"Target body name: {target}                        {{source: {solution}}}"]
    if extra_target:
        lines.append(f"Target body name: {target}                        {{source: {solution}}}")
    lines += [f"Center body name: Earth (399)                     {{source: {center}}}", RULE]
    if deflection:
        lines.append("Rel. light bend : Sun                             {source: DE441}")
    if eop:
        lines += ["EOP file        : eop.000101.p000301",
                  "EOP coverage    : DATA-BASED 1962-JAN-20 TO 2000-JAN-01. PREDICTS-> 2000-MAR-01"]
    lines += [RULE, columns, RULE, "$$SOE", *rows, "$$EOE", RULE, "Column meaning:", ""]
    return "\n".join(lines)


def payload(text: str, *, version: str = "1.2", source: str = "NASA/JPL Horizons API") -> bytes:
    return json.dumps({"signature": {"source": source, "version": version}, "result": text}).encode()


def vector_text(jd: float, *, solution: str = "mar099") -> str:
    return "\n".join([
        "", RULE, STAMP, RULE,
        f"Target body name: Mars (499)                      {{source: {solution}}}",
        "Center body name: Earth (399)                     {source: DE441}", RULE,
        "Output units    : AU-D", "Calendar mode   : Mixed Julian/Gregorian",
        "Output type     : GEOMETRIC cartesian states",
        "EOP file        : eop.000101.p000301",
        "EOP coverage    : DATA-BASED 1962-JAN-20 TO 2000-JAN-01. PREDICTS-> 2000-MAR-01",
        "Reference frame : ITRF93", RULE,
        "            JDTDB,            Calendar Date (TDB),      X,      Y,      Z,     VX,     VY,     VZ,",
        RULE, "$$SOE",
        f"{jd:.9f}, A.D. 2000-Jan-01 12:00:00.0000, -1.0E-01, 2.0E-01, 3.0E-01, 4.0E-03, 5.0E-03, 6.0E-03,",
        "$$EOE", RULE, "  Symbol meaning [1 au= 149597870.700 km, 1 day= 86400.0 s]:", RULE, ""])


def respond(query: dict[str, str], **overrides) -> bytes:
    """What a well-behaved service would print for a query this probe sends, synthetic throughout."""
    jds = [float(x) for x in query["TLIST"].strip("'").split(",")]
    command = query["COMMAND"].strip("'")
    labels = {t["command"]: t["label"] for t in probe.TARGETS}
    target = f"{labels[command]} ({command})"
    solution = probe.EXPECTED_SOLUTIONS[command]
    if query["EPHEM_TYPE"].strip("'") == "VECTORS":
        return payload(vector_text(jds[0], solution=solution))
    if "CSV_FORMAT" not in query:
        columns = " Date__(TT)__HR:MN:SC.fff     R.A.__(a-apparent)__DEC     ObsEcLon    ObsEcLat"
        rows = [default_line(jd) for jd in jds]
    else:
        variant = {("'HMS'", "'NO'"): "hms", ("'HMS'", "'YES'"): "hms_extra", ("'DEG'", "'NO'"): "deg",
                   ("'DEG'", "'YES'"): "deg_extra"}[(query["ANG_FORMAT"], query["EXTRA_PREC"])]
        columns, rows = header_line(variant), [csv_line(variant, jd) for jd in jds]
    return payload(observer_text(target=target, solution=solution, columns=columns, rows=rows, **overrides))


def retrieval_of(url: str, body: bytes, canonical_form) -> Retrieval:
    resource = canonical_form(body)
    return Retrieval(url=url, final_url=url, status=200, size_bytes=len(body),
                     sha256=hashlib.sha256(body).hexdigest(), validators={}, payload=body,
                     prior_copy_agreed=None, resource=resource,
                     resource_sha256=hashlib.sha256(resource).hexdigest())


class FakeService:
    """Answers every request from `respond`, recording each one, with per-request mutations."""

    def __init__(self, mutate=None) -> None:
        self.calls: list[tuple[str, Path]] = []
        self.mutate = mutate or {}

    def __call__(self, url: str, cache: Path, canonical_form) -> Retrieval:
        self.calls.append((url, cache))
        query = dict(urllib.parse.parse_qsl(urllib.parse.urlsplit(url).query))
        request_id = cache.stem
        body = self.mutate[request_id](query) if request_id in self.mutate else respond(query)
        return retrieval_of(url, body, canonical_form)


FAKE_VECTOR_QUERY = {"format": "json", "EPHEM_TYPE": "VECTORS", "CENTER": "'500@0'", "REF_PLANE": "'FRAME'",
                     "OUT_UNITS": "'AU-D'", "VEC_TABLE": "'2'", "CSV_FORMAT": "'YES'"}

MANIFEST = """\
[identity]
name = "synthetic"
version = 1

[[pinned.dataset]]
logical_id = "synthetic"
declared_coverage = { start = "1801-01-01T00:00:00", end = "2199-01-01T00:00:00", scale = "TDB" }
"""


@pytest.fixture
def interval(tmp_path):
    path = tmp_path / "manifest.toml"
    path.write_text(MANIFEST, encoding="utf-8")
    return probe.modes.read_interval(str(path))


@pytest.fixture
def requests(interval):
    return probe.plan(interval, FAKE_VECTOR_QUERY)


def request_named(requests, request_id):
    return next(r for r in requests if r["request_id"] == request_id)


# --------------------------------------------------------------------------------------
# By import, never by copy
# --------------------------------------------------------------------------------------


def _module_names(tree: ast.Module) -> set[str]:
    names = set()
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
            names.add(node.name)
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            for target in node.targets if isinstance(node, ast.Assign) else [node.target]:
                if isinstance(target, ast.Name):
                    names.add(target.id)
    return names


def test_no_bytecode_is_written_before_any_import_from_this_tree() -> None:
    source = SCRIPT.read_text(encoding="utf-8")
    first = source.index("sys.dont_write_bytecode = True")
    assert first < source.index("from saakshi import service")
    assert first < source.index("import nutation_obliquity_modes as modes")


def test_the_service_rules_are_imported_and_never_defined_here() -> None:
    defined = _module_names(ast.parse(SCRIPT.read_text(encoding="utf-8")))
    for name in ("ENDPOINT", "_SERVICE_STATE_PATTERNS", "_ENVELOPE_PATTERNS", "_SIGNATURE_KEYS", "_EXCLUDED",
                 "_locate", "build_url", "parse", "canonical_form", "retrieve", "USER_AGENT", "COMMON_QUERY",
                 "read_interval", "julian_day", "civil"):
        assert name not in defined, name
    assert probe.service is service
    assert probe.retrieve is acquisition.retrieve
    assert probe.ServiceFormatError is ServiceFormatError


def test_the_split_is_service_parse_over_a_vector_response() -> None:
    """⭐ The twin that licenses the split: over R1's own table it cuts what R1's reader cuts."""
    query = {"COMMAND": "'499'"}
    body = payload(vector_text(2451545.0))
    ours, theirs = probe.split(body, query=query), service.parse(body, query=query)
    assert ours.resource_text == theirs.resource_text
    assert ours.service_state == theirs.service_state
    assert ours.envelope_excluded == theirs.envelope_excluded


@pytest.mark.skipif(importlib.util.find_spec("spiceypy") is None, reason="R1's sampler imports the SPICE binding")
def test_the_vector_query_is_r1s_own_with_two_parameters_replaced(interval) -> None:
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(ROOT / "generators"))
    import r1_horizons

    common = probe.r1_vector_query()
    assert common == r1_horizons.COMMON_QUERY
    sent = probe.plan(interval, common)[0]["query"]
    moved = {k for k in set(sent) | set(common) if sent.get(k) != common.get(k)}
    assert moved == {"CENTER", "REF_PLANE", "COMMAND", "TLIST"}


# --------------------------------------------------------------------------------------
# The split, and the stop
# --------------------------------------------------------------------------------------


def _deg_extra(**overrides) -> bytes:
    return payload(observer_text(columns=header_line("deg_extra"), rows=[csv_line("deg_extra", 2451545.0)],
                                 **overrides))


def test_an_observer_response_is_split_and_its_extra_solution_recorded() -> None:
    observed = probe.split(_deg_extra(), query={"COMMAND": "'10'"})
    assert observed.service_state["deflecting_body_solution"] == "DE441"
    assert observed.service_state["earth_orientation_file"] == "eop.000101.p000301"
    assert "<excluded:generation_stamp>" in observed.resource_text
    assert "<excluded:deflecting_body_solution>" in observed.resource_text
    assert "eop.000101" not in observed.resource_text


@pytest.mark.parametrize("damage, says", [
    ("no_version", "interface version"), ("no_stamp", "generation_stamp"), ("no_target_solution", "target_solution"),
    ("two_target_lines", "matched 2 times"), ("not_json", "not JSON"), ("no_result", "no 'result'"),
])
def test_the_split_refuses_what_r1s_split_refuses(damage, says) -> None:
    probe.split(_deg_extra(), query={"COMMAND": "'10'"})  # the twin
    if damage == "no_version":
        body = json.dumps({"signature": {"source": "x"}, "result": observer_text(
            columns=header_line("deg_extra"), rows=[csv_line("deg_extra", 2451545.0)])}).encode()
    elif damage == "no_stamp":
        body = _deg_extra(stamp=False)
    elif damage == "no_target_solution":
        body = _deg_extra().replace(b"{source: DE441}", b"", 1)
    elif damage == "two_target_lines":
        body = _deg_extra(extra_target=True)
    elif damage == "not_json":
        body = b"not json"
    else:
        body = json.dumps({"signature": {"source": "x", "version": "1.2"}}).encode()
    with pytest.raises(ServiceFormatError, match=says):
        probe.split(body, query={"COMMAND": "'10'"})


GOOD_STATE = {"interface_source": "NASA/JPL Horizons API", "interface_version": "1.2",
              "target_solution": "DE441", "center_solution": "DE441"}


@pytest.mark.parametrize("key, value, target", [
    ("interface_version", "1.3", "10"), ("interface_source", "another", "10"),
    ("target_solution", "DE440", "10"), ("target_solution", "DE441", "499"), ("center_solution", "DE440", "10"),
])
def test_a_service_answering_otherwise_than_r1_recorded_is_a_stop(key, value, target) -> None:
    good = dict(GOOD_STATE, target_solution=probe.EXPECTED_SOLUTIONS[target])
    probe.expect_service(good, target=target, where="twin")
    with pytest.raises(probe.Refusal, match="STOP"):
        probe.expect_service(dict(good, **{key: value}), target=target, where="damaged")


def test_the_stop_is_against_what_r1_recorded() -> None:
    assert probe.EXPECTED_INTERFACE == {"interface_source": "NASA/JPL Horizons API", "interface_version": "1.2"}
    assert probe.EXPECTED_SOLUTIONS["499"] == "mar099"
    assert {probe.EXPECTED_SOLUTIONS[c] for c in ("10", "301", "399", "5", "9")} == {"DE441"}


# --------------------------------------------------------------------------------------
# The tables
# --------------------------------------------------------------------------------------

WANTED = [{"jd": 2451545.0}, {"jd": 2451545.5}]


def _csv(variant: str, rows=None, columns=None) -> str:
    rows = rows if rows is not None else [csv_line(variant, w["jd"]) for w in WANTED]
    return observer_text(columns=columns or header_line(variant), rows=rows)


@pytest.mark.parametrize("variant", ["hms", "hms_extra", "deg", "deg_extra"])
def test_each_variants_table_is_read_with_every_field_as_printed(variant) -> None:
    spec = next(v for v in probe.VARIANTS if v["variant"] == variant)
    labels, rows = probe.read_csv_table(_csv(variant), variant=spec, wanted=WANTED, where="twin")
    assert labels == [label for label, _ in spec["columns"]]
    assert rows[0][3:5] == list(_SHAPES[variant]) and rows[1][0] == "2451545.500000000"


def _damaged_csv(damage: str) -> str:
    v = "deg_extra"
    good = [csv_line(v, w["jd"]) for w in WANTED]
    if damage == "reordered_columns":
        return _csv(v, columns="Date_________JDTT, , , DEC___(a-app), R.A.__(a-app),     ObsEcLon,   ObsEcLat,")
    if damage == "short_answer":
        return _csv(v, rows=good[:1])
    if damage == "field_count":
        return _csv(v, rows=[good[0], good[1].replace("  -1.2345678,", "")])
    if damage == "not_available":
        return _csv(v, rows=[good[0], good[1].replace("123.456789012", "n.a.")])
    if damage == "other_instant":
        return _csv(v, rows=[good[0], csv_line(v, 2451546.0)])
    if damage == "two_blocks":
        return _csv(v) + "\n$$SOE\n$$EOE\n"
    if damage == "two_date_lines":
        return _csv(v).replace("Column meaning:", "Date of something:")
    if damage == "no_rule_line":
        return _csv(v).replace(RULE + "\n$$SOE", "-" * 79 + "\n$$SOE")
    raise AssertionError(damage)


@pytest.mark.parametrize("damage, says", [
    ("reordered_columns", "columns"), ("short_answer", "data lines for"), ("field_count", "fields, not"),
    ("not_available", "not the shape"), ("other_instant", "answered for JD"), ("two_blocks", "single pair"),
    ("two_date_lines", "begins 'Date'"), ("no_rule_line", "rule line"),
])
def test_a_table_not_as_asked_is_refused(damage, says) -> None:
    spec = next(v for v in probe.VARIANTS if v["variant"] == "deg_extra")
    probe.read_csv_table(_csv("deg_extra"), variant=spec, wanted=WANTED, where="twin")
    with pytest.raises(ServiceFormatError, match=says):
        probe.read_csv_table(_damaged_csv(damage), variant=spec, wanted=WANTED, where="damaged")


DEFAULT_COLUMNS = " Date__(TT)__HR:MN:SC.fff     R.A.__(a-apparent)__DEC     ObsEcLon    ObsEcLat"


def test_the_default_format_table_is_read_as_five_printed_fields() -> None:
    text = observer_text(columns=DEFAULT_COLUMNS, rows=[default_line(w["jd"]) for w in WANTED])
    labels, rows = probe.read_default_table(text, wanted=WANTED, where="twin")
    assert labels == list(probe.DEFAULT_FORMAT_LABELS)
    assert rows[0] == ["2000-Jan-01 12:00:00.000", "12 34 56.78", "-12 34 56.7", "124.5678901", "-1.2345678"]
    assert probe.default_fields(labels)[1:3] == ["R.A.__(a-apparent)__DEC [ra]", "R.A.__(a-apparent)__DEC [dec]"]


@pytest.mark.parametrize("damage, says", [
    ("labels", "columns"), ("tokens", "tokens, not"), ("shape", "not the shape"), ("other_instant", "answered for"),
    ("fraction", "fraction of a second"), ("short", "data lines for"),
])
def test_a_default_format_table_not_as_asked_is_refused(damage, says) -> None:
    good = [default_line(w["jd"]) for w in WANTED]
    columns, rows = DEFAULT_COLUMNS, list(good)
    if damage == "short":
        rows = good[:1]
    elif damage == "labels":
        columns = DEFAULT_COLUMNS.replace("ObsEcLon", "ObsEcLng")
    elif damage == "tokens":
        rows[1] = rows[1] + "  extra"
    elif damage == "shape":
        rows[1] = rows[1].replace("124.5678901", "n.a.")
    elif damage == "other_instant":
        rows[1] = default_line(2451546.0)
    else:
        rows[1] = rows[1].replace("00:00:00.000", "00:00:00.500")
    probe.read_default_table(observer_text(columns=DEFAULT_COLUMNS, rows=good), wanted=WANTED, where="twin")
    with pytest.raises(ServiceFormatError, match=says):
        probe.read_default_table(observer_text(columns=columns, rows=rows), wanted=WANTED, where="damaged")


@pytest.mark.parametrize("printed, digits", [
    ("281.277554826", 9), ("18 45 06.61", 2), ("-23 01 56.96054", 5), ("2451545.000000000", 9),
    ("-8.860273046975009E-01", 15), ("A.D. 2000-Jan-01 12:00:00.0000", 4), ("12", 0), ("", None),
])
def test_digits_are_counted_on_the_last_component(printed, digits) -> None:
    assert probe.decimals(printed) == digits


# --------------------------------------------------------------------------------------
# The instants and the plan
# --------------------------------------------------------------------------------------


def test_every_instant_is_inside_and_the_ends_a_day_in(interval) -> None:
    named, window = probe.instants(interval)
    assert named[0]["jd"] == interval["start"] + 1.0 and named[-1]["jd"] == interval["end"] - 1.0
    assert len(window) == 65 and window[32]["jd"] == probe.modes.julian_day("1962-01-20T00:00:00")
    assert {round(b["jd"] - a["jd"], 9) for a, b in zip(window, window[1:])} == {0.0625}
    assert any(i["jd"] == 2451545.0 for i in named)
    assert all(interval["start"] < i["jd"] < interval["end"] for i in named + window)


def test_an_instant_outside_the_interval_is_refused(interval, monkeypatch) -> None:
    monkeypatch.setattr(probe, "NAMED_INSTANTS", ("1800-06-01T00:00:00",))
    with pytest.raises(probe.Refusal, match="not inside"):
        probe.instants(interval)


def test_two_instants_that_coincide_are_refused(interval, monkeypatch) -> None:
    probe.instants(interval)
    monkeypatch.setattr(probe, "NAMED_INSTANTS", ("1962-01-20T00:00:00",))
    with pytest.raises(probe.Refusal, match="coincide"):
        probe.instants(interval)


def test_the_plan(requests) -> None:
    assert [r["part"] for r in requests] == ["vectors"] + ["observer"] * 14 + ["observer_default_format"]
    vector = requests[0]["query"]
    assert vector["CENTER"] == "'500@399'" and vector["REF_PLANE"] == "'BODY'" and vector["COMMAND"] == "'499'"
    for request in requests[1:-1]:
        variant = next(v for v in probe.VARIANTS if v["variant"] == request["variant"])
        assert request["query"] == {**probe.OBSERVER_QUERY, **variant["params"], "COMMAND": request["query"]["COMMAND"],
                                    "TLIST": probe.tlist([i["jd"] for i in request["instants"]])}
        assert len(request["instants"]) == (75 if variant["window"] else 10)
    default = requests[-1]["query"]
    assert not {"ANG_FORMAT", "EXTRA_PREC", "CSV_FORMAT", "CAL_FORMAT"} & set(default)
    assert len({r["request_id"] for r in requests}) == len(requests) == 16


# --------------------------------------------------------------------------------------
# Reading
# --------------------------------------------------------------------------------------


def test_one_request_at_a_time_with_the_pause_between(requests, tmp_path) -> None:
    pauses: list[float] = []
    fetch = FakeService()
    events: list[str] = []

    def sleep(seconds: float) -> None:
        pauses.append(seconds)
        events.append("pause")

    def recorded_fetch(url, cache, canonical_form):
        events.append("request")
        return fetch(url, cache, canonical_form)

    request_rows, reading_rows = probe.read(requests, cache=tmp_path, fetch=recorded_fetch, sleep=sleep)
    assert events == ["request"] + ["pause", "request"] * (len(requests) - 1)
    assert pauses == [probe.REQUEST_INTERVAL_SECONDS] * (len(requests) - 1)
    assert len(request_rows) == 16 and len(reading_rows) == 1 + 9 * 10 + 5 * 75 + 10
    probe.check(request_rows, reading_rows, requests)
    for row in reading_rows:
        assert all(row[name] for name in probe.ROW_STATE)
    assert {r["target_solution"] for r in reading_rows if r["target_command"] == "499"} == {"mar099"}


def test_the_record_names_r1s_canonical_form_for_the_vectors(requests, tmp_path) -> None:
    seen = []

    def fetch(url, cache, canonical_form):
        seen.append(canonical_form)
        return FakeService()(url, cache, canonical_form)

    probe.read(requests[:2], cache=tmp_path, fetch=fetch, sleep=lambda s: None)
    body = respond(requests[0]["query"])
    assert seen[0](body) == service.canonical_form(requests[0]["query"])(body)
    assert seen[1](respond(requests[1]["query"])) == probe.split(respond(requests[1]["query"]),
                                                                 query=requests[1]["query"]).resource_text.encode()


def test_an_observer_response_without_its_earth_orientation_is_refused(requests, tmp_path) -> None:
    twin = FakeService()
    probe.read(requests[1:2], cache=tmp_path / "a", fetch=twin, sleep=lambda s: None)
    damaged = FakeService({requests[1]["request_id"]: lambda q: respond(q, eop=False)})
    with pytest.raises(ServiceFormatError, match="earth_orientation_file"):
        probe.read(requests[1:2], cache=tmp_path / "b", fetch=damaged, sleep=lambda s: None)


def test_a_vector_answer_for_another_instant_is_refused(requests, tmp_path) -> None:
    probe.read(requests[:1], cache=tmp_path / "a", fetch=FakeService(), sleep=lambda s: None)
    damaged = FakeService({requests[0]["request_id"]: lambda q: payload(vector_text(2451546.0))})
    with pytest.raises(ServiceFormatError, match="answered for JD"):
        probe.read(requests[:1], cache=tmp_path / "b", fetch=damaged, sleep=lambda s: None)


def test_a_vector_answer_with_more_lines_than_instants_is_refused(requests, tmp_path) -> None:
    def two_lines(query):
        text = vector_text(2451545.0)
        line = next(x for x in text.splitlines() if x.startswith("2451545.000000000"))
        return payload(text.replace(line, line + "\n" + line.replace("2451545.000000000", "2451546.000000000")))

    with pytest.raises(ServiceFormatError, match="lines for"):
        probe.read(requests[:1], cache=tmp_path, fetch=FakeService({requests[0]["request_id"]: two_lines}),
                   sleep=lambda s: None)


def test_a_service_that_moved_stops_the_read(requests, tmp_path) -> None:
    damaged = FakeService({requests[1]["request_id"]: lambda q: payload(
        json.loads(respond(q))["result"], version="1.3")})
    with pytest.raises(probe.Refusal, match="STOP"):
        probe.read(requests[:2], cache=tmp_path, fetch=damaged, sleep=lambda s: None)


def test_check_refuses_a_row_that_does_not_say_what_answered(requests, tmp_path) -> None:
    request_rows, reading_rows = probe.read(requests, cache=tmp_path, fetch=FakeService(), sleep=lambda s: None)
    probe.check(request_rows, reading_rows, requests)
    with pytest.raises(probe.Refusal, match="without"):
        probe.check(request_rows, [dict(reading_rows[0], earth_orientation_file=None), *reading_rows[1:]], requests)
    with pytest.raises(probe.Refusal, match="in order"):
        probe.check(list(reversed(request_rows)), reading_rows, requests)
    with pytest.raises(probe.Refusal, match="one per instant"):
        probe.check(request_rows, reading_rows[1:], requests)


# --------------------------------------------------------------------------------------
# The client, and where nothing may be written
# --------------------------------------------------------------------------------------


def test_the_client_names_itself_and_how_to_reach_it_and_no_person() -> None:
    assert probe.CONTACT_USER_AGENT == f"{USER_AGENT} (+https://github.com/insculptor/Saakshi)"
    assert "@" not in probe.CONTACT_USER_AGENT


def test_every_live_request_is_sent_under_that_name(monkeypatch, tmp_path) -> None:
    sent = {}

    def fake_retrieve(url, **kwargs):
        sent.update(kwargs, url=url)
        return "retrieval"

    monkeypatch.setattr(probe, "retrieve", fake_retrieve)
    assert probe.fetch_live("https://example.invalid/x", tmp_path / "c", probe.canonical({})) == "retrieval"
    assert sent["user_agent"] == probe.CONTACT_USER_AGENT and sent["cache"] == tmp_path / "c"


def _generate(tmp_path, out, cache, fetch=None):
    tmp_path.mkdir(parents=True, exist_ok=True)
    manifest = tmp_path / "manifest.toml"
    manifest.write_text(MANIFEST, encoding="utf-8")
    return probe.generate(str(manifest), cache, out, fetch=fetch or FakeService(), sleep=lambda s: None,
                          vector_query=FAKE_VECTOR_QUERY, allow_dirty=True)


def test_the_record_is_written_outside_the_tree_and_holds_the_contract(tmp_path) -> None:
    out = tmp_path / "record" / "r1-of-date-probe.jsonl"
    written = _generate(tmp_path, out, tmp_path / "cache")
    lines = out.read_text(encoding="utf-8").splitlines()
    header = json.loads(lines[0])
    assert written == len(lines) - 1 == 16 + 476
    assert (header["fixture_kind"], header["reference"]) == ("provenance_record", "R1")
    assert not {"classification", "budget_row"} & set(header)
    assert header["oracle"]["user_agent"] == probe.CONTACT_USER_AGENT
    assert header["summary"]["stated_terms"] and header["summary"]["documents"]
    readings = [json.loads(line) for line in lines[1:] if json.loads(line)["finding"] == "reading"]
    assert all(all(r[name] for name in probe.ROW_STATE) for r in readings)
    assert {p["field"] for p in header["summary"]["precision"]} >= {"ObsEcLon", "R.A.__(a-app)"}


@pytest.fixture
def stand_in_tree(tmp_path, monkeypatch) -> Path:
    """⛔ A stand-in for this working tree, so a run whose refusal has been planted out writes into a temporary
    directory and never into the real one. It has no repository, so nothing past the refusal can succeed."""
    tree = tmp_path / "stand-in-tree"
    (tree / "generators").mkdir(parents=True)
    monkeypatch.setattr(probe, "HERE", tree / "generators")
    return tree


@pytest.mark.parametrize("where", ["out", "cache"])
def test_nothing_read_is_written_into_this_tree(tmp_path, where, monkeypatch) -> None:
    _generate(tmp_path / "twin", tmp_path / "twin" / "x.jsonl", tmp_path / "twin" / "c")
    tree = tmp_path / "stand-in-tree"
    (tree / "generators").mkdir(parents=True)
    monkeypatch.setattr(probe, "HERE", tree / "generators")
    inside = tree / "out" / "never-written"
    out, cache = (inside / "x.jsonl", tmp_path / "c") if where == "out" else (tmp_path / "x.jsonl", inside)
    with pytest.raises(probe.Refusal, match="inside this working tree"):
        _generate(tmp_path, out, cache)
    assert not inside.exists()


def test_a_record_is_never_overwritten(tmp_path) -> None:
    out = tmp_path / "x.jsonl"
    out.write_text("earlier", encoding="utf-8")
    with pytest.raises(probe.Refusal, match="exists"):
        _generate(tmp_path, out, tmp_path / "c")
    assert out.read_text(encoding="utf-8") == "earlier"


def test_main_reports_a_refusal_and_returns_two(tmp_path, capsys, stand_in_tree) -> None:
    manifest = tmp_path / "manifest.toml"
    manifest.write_text(MANIFEST, encoding="utf-8")
    code = probe.main(["--profile", str(manifest), "--cache", str(tmp_path / "c"),
                       "--out", str(stand_in_tree / "out" / "never.jsonl")])
    assert code == 2 and "REFUSED" in capsys.readouterr().err
    assert not (stand_in_tree / "out").exists()
