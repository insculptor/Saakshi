"""The oracle declaration's three states, read without installing or removing a library.

⛔ The failure the third state exists for: an environment declared ``absent`` gains one of
the oracle libraries. With two states it still read ``absent`` and the declaration passed,
while the tests that call that library began to run under a badge that says they do not.
"""

from __future__ import annotations

import re
from pathlib import Path

import conftest
import pytest

TESTS = Path(__file__).resolve().parent

#: A module a test may skip without that is not an oracle: a data package, said so in the README.
NOT_AN_ORACLE = {"tzdata"}


def _found(monkeypatch, present):
    monkeypatch.setattr(conftest, "find_spec", lambda name: object() if name in present else None)


def test_every_library_found_is_present(monkeypatch):
    _found(monkeypatch, set(conftest.ORACLE_MODULES))
    assert conftest.oracle_state() == (conftest.PRESENT, ())


def test_no_library_found_is_absent(monkeypatch):
    _found(monkeypatch, set())
    assert conftest.oracle_state() == (conftest.ABSENT, conftest.ORACLE_MODULES)


@pytest.mark.parametrize("declared", [conftest.ABSENT, conftest.PRESENT])
def test_one_library_added_to_an_absent_environment_is_partial_and_refused(monkeypatch, declared):
    _found(monkeypatch, {conftest.ORACLE_MODULES[0]})
    state, missing = conftest.oracle_state()
    assert state == conftest.PARTIAL and missing == conftest.ORACLE_MODULES[1:]
    monkeypatch.setenv(conftest.DECLARATION, declared)
    with pytest.raises(pytest.UsageError, match="'partial'"):
        conftest.pytest_configure(None)


def test_every_module_a_test_skips_without_is_declared():
    """The declaration covers what the suite actually skips on, not a list kept by hand beside it."""
    skipped = set()
    for path in TESTS.glob("test_*.py"):
        text = path.read_text(encoding="utf-8")
        skipped |= set(re.findall(r'importorskip\(\s*"([A-Za-z_][A-Za-z0-9_]*)"', text))
        skipped |= set(re.findall(r'find_spec\(\s*"([A-Za-z_][A-Za-z0-9_]*)"', text))
    assert skipped, "the scan found no skip at all, so it is not reading the suite"
    assert skipped - NOT_AN_ORACLE == set(conftest.ORACLE_MODULES)
