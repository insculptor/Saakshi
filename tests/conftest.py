"""What this test run can and cannot prove, said out loud before it runs.

The suite has two halves. One exercises the fixture contract and needs nothing but Python.
The other calls the ephemeris libraries and needs them installed — and continuous
integration deliberately does **not** install them, because a green run there is meant to
say *the schema is sound*, not *the oracles happened to be present*.

⛔ **A skipped half must never be a silent half.** Skipping the oracle tests where the
library is absent is correct; letting the run report success without saying which half it
proved is the same defect this repository keeps finding elsewhere — a check that has
nothing to check and reports a pass. So the reduction is announced in the report header,
restated in the summary, and — where the caller has declared what it expects — **checked**.

⭐ ``ORACLE_LIBRARIES`` is that declaration. Set it to ``absent`` or ``present`` and the
session refuses to run unless reality agrees. Continuous integration sets ``absent``, so
the day somebody adds an ephemeris library to that environment the disagreement is a
failure rather than a quiet change in what the badge means.
"""

from __future__ import annotations

import os
from importlib.util import find_spec

import pytest

#: The libraries the oracle half calls. ⚠ Names only — nothing is imported here, because a
#: conftest that imports an optional dependency fails collection for the half that does not
#: need it.
ORACLE_MODULES: tuple[str, ...] = ("swisseph",)

#: The environment variable a caller uses to declare what it expects to find.
DECLARATION = "ORACLE_LIBRARIES"

PRESENT, ABSENT = "present", "absent"


def oracle_state() -> tuple[str, tuple[str, ...]]:
    """`(present|absent, the modules that are missing)`."""
    missing = tuple(name for name in ORACLE_MODULES if find_spec(name) is None)
    return (ABSENT if missing else PRESENT), missing


def pytest_report_header() -> list[str]:
    state, missing = oracle_state()
    if state is PRESENT:
        return [f"oracle libraries: present ({', '.join(ORACLE_MODULES)})"]
    return [
        f"oracle libraries: ABSENT ({', '.join(missing)}) - this run proves the fixture "
        "contract only; the tests that call an ephemeris cannot run here"
    ]


def pytest_configure(config: pytest.Config) -> None:
    """Refuse to run against an environment that is not the one the caller declared.

    ⚠ Unset means undeclared, and undeclared is allowed: a developer running the suite
    locally has made no claim about it. A caller that *does* make the claim gets it checked.
    """
    declared = os.environ.get(DECLARATION)
    if declared is None:
        return
    declared = declared.strip().lower()
    if declared not in (PRESENT, ABSENT):
        raise pytest.UsageError(
            f"{DECLARATION}={declared!r} is neither {PRESENT!r} nor {ABSENT!r}"
        )
    state, missing = oracle_state()
    if declared != state:
        raise pytest.UsageError(
            f"{DECLARATION} declares {declared!r} and this environment is {state!r} "
            f"(missing: {', '.join(missing) or 'nothing'}). ⛔ The declaration is what "
            "makes a reduced run honest; a run that disagrees with it is reporting on a "
            "suite other than the one the caller thinks it asked for."
        )


def pytest_terminal_summary(terminalreporter: pytest.TerminalReporter) -> None:
    """Say it again at the end, where a reader of a green run will actually see it."""
    state, missing = oracle_state()
    if state is PRESENT:
        return
    terminalreporter.write_sep(
        "=",
        f"REDUCED RUN - no {', '.join(missing)}: the fixture contract was tested and the "
        "ephemeris behaviour was not",
        yellow=True,
    )
