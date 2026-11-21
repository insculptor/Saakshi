"""A reading that raises stops the generator before anything is written.

⛔ **The defect these exist for.** The source assertion gained three required keywords (the
body, the whole word, and the per-body attestation) and two callers were never updated. In
the apparent-position section the call sat inside ``except Exception: continue``, so its
``TypeError`` was swallowed for every row; the section came back empty, and the run failed
at write time with an error that named an empty classification instead of the cause, after
the time-offset section had already been written. In the binding-cost probe the same stale
call raised at once.

These read the code and need no ephemeris library, so they run everywhere. The tests that
call the binding are in ``test_reading_failures_binding.py``.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SOURCES = sorted([*ROOT.glob("generators/*.py"), *ROOT.glob("src/saakshi/*.py")])
REQUIRED = {"body", "word", "attested", "where"}


def _calls(tree: ast.AST, name: str) -> list[ast.Call]:
    return [
        node for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and ((isinstance(node.func, ast.Name) and node.func.id == name)
             or (isinstance(node.func, ast.Attribute) and node.func.attr == name))
    ]


def _function(path: Path, name: str) -> ast.FunctionDef:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == name)


# --- read from the code: no library needed ----------------------------------------------


def test_every_source_assertion_names_its_body_word_and_attestation():
    """⛔ Fails on every platform if a caller passes the old, three-keyword-short form."""
    sites = {}
    for path in SOURCES:
        for call in _calls(ast.parse(path.read_text(encoding="utf-8")), "assert_reported"):
            sites[f"{path.relative_to(ROOT).as_posix()}:{call.lineno}"] = {k.arg for k in call.keywords}
    # ⚠ The control: the three files that call it are all found, or this passes over nothing.
    assert {site.split(":")[0] for site in sites} == {
        "generators/r3_swiss.py", "generators/probe6b_ffi.py", "src/saakshi/conventions.py"
    }
    for site, keywords in sites.items():
        assert REQUIRED <= keywords, (site, sorted(REQUIRED - keywords))


def test_no_reading_in_the_apparent_section_is_caught():
    """⛔ No ``try`` at all: a failed call, a substitution or an unattested flag each propagate."""
    function = _function(ROOT / "src" / "saakshi" / "conventions.py", "apparent_variants")
    assert not [n for n in ast.walk(function) if isinstance(n, ast.Try)]


def test_the_probe_generator_stages_every_section_and_publishes_last():
    """⭐ Every section writes into the staging directory, never into ``--out``, and the one
    call that touches ``--out`` comes after the loop that reads every section."""
    main = _function(ROOT / "generators" / "convention_probes.py", "main")
    writes = [c for c in ast.walk(main) if isinstance(c, ast.Call)
              and isinstance(c.func, ast.Name) and c.func.id.startswith("write_")]
    assert len(writes) == 6
    for call in writes:
        out_dir = {k.arg: k.value for k in call.keywords}["out_dir"]
        assert isinstance(out_dir, ast.Name) and out_dir.id == "staging", ast.unparse(call)
    loop = next(n for n in ast.walk(main) if isinstance(n, ast.For)
                and any(isinstance(c, ast.Call) and c in writes for c in ast.walk(n)))
    publish = _calls(main, "publish")
    assert len(publish) == 1 and publish[0].lineno > loop.end_lineno
