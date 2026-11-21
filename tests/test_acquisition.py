"""What `retrieve()` tells the server it is.

⭐ No network. The request `retrieve()` builds is captured before it would be sent, so what is
under test is the header itself rather than whether a server happened to accept it.
"""

from __future__ import annotations

import inspect
import re
import tomllib
import urllib.request
from email.message import Message
from pathlib import Path

import pytest

from saakshi import acquisition, provenance
from saakshi.acquisition import USER_AGENT, retrieve


class _Response:
    def __init__(self, payload: bytes) -> None:
        self._payload = payload
        self.status = 200
        self.headers = Message()

    def read(self) -> bytes:
        return self._payload

    def geturl(self) -> str:
        return "https://example.invalid/answered"

    def __enter__(self) -> "_Response":
        return self

    def __exit__(self, *exc: object) -> None:
        return None


@pytest.fixture
def sent(monkeypatch: pytest.MonkeyPatch) -> list[urllib.request.Request]:
    """Every request `retrieve()` would have sent, in order."""
    requests: list[urllib.request.Request] = []

    def fake_urlopen(request: urllib.request.Request, timeout: float) -> _Response:
        requests.append(request)
        return _Response(b"payload")

    monkeypatch.setattr(acquisition.urllib.request, "urlopen", fake_urlopen)
    return requests


#: ⭐ The string the owner approved for the service's requests (2026-11-09, again 2026-11-21), written out so a
#: change to any part of it is a failing test rather than a quiet edit.
APPROVED = "saakshi/0.1 (+https://github.com/insculptor/Saakshi)"

ROOT = Path(__file__).resolve().parents[1]


def test_every_request_names_the_product_its_version_and_a_contact(sent, tmp_path) -> None:
    """⛔ The Fair Use Policy's three parts, each present: product name, version, contact."""
    retrieve("https://example.invalid/a", cache=tmp_path / "a")
    assert sent[0].get_header("User-agent") == USER_AGENT == APPROVED
    assert re.fullmatch(r"[a-z]+/[0-9]+\.[0-9]+ \(\+https://[^ ()]+\)", USER_AGENT)
    assert "@" not in USER_AGENT


def test_the_contact_is_this_repositorys_public_address() -> None:
    assert acquisition.CONTACT == f"https://{provenance.REPO}"


def test_the_version_is_this_packages_own() -> None:
    """⚠ "Correct" version: the header's version is the package's, so a release that moves one moves both."""
    with (ROOT / "pyproject.toml").open("rb") as fh:
        project = tomllib.load(fh)["project"]
    assert acquisition.PRODUCT == project["name"]
    assert project["version"].split(".")[:2] == acquisition.VERSION.split(".")


def test_there_is_no_per_call_override(sent, tmp_path) -> None:
    """⛔ One client name: no caller can send a header the policy does not accept, or one its record does not
    name."""
    assert "user_agent" not in inspect.signature(retrieve).parameters
    with pytest.raises(TypeError):
        retrieve("https://example.invalid/b", cache=tmp_path / "b", user_agent="other/1")  # type: ignore[call-arg]
    assert sent == []


def test_every_request_sends_the_same_header(sent, tmp_path) -> None:
    """⭐ Twins: two addresses, one client name."""
    retrieve("https://example.invalid/c", cache=tmp_path / "c")
    retrieve("https://example.invalid/d", cache=tmp_path / "d")
    assert [r.get_header("User-agent") for r in sent] == [USER_AGENT, USER_AGENT]


#: Every source that calls the network through `retrieve()`.
CALLERS = ("generators/r1_horizons.py", "generators/r1_drift.py", "generators/publisher_testpo.py",
           "generators/r1_of_date_probe.py", "src/saakshi/texts.py")


def test_the_callers_were_found() -> None:
    """⚠ The control for the two tests below: a caller missing from the list is a caller nobody checks."""
    found = sorted(
        path.relative_to(ROOT).as_posix()
        for path in [*ROOT.glob("generators/*.py"), *ROOT.glob("src/saakshi/*.py"), *ROOT.glob("tools/*.py")]
        if re.search(r"(?<![\w.`])retrieve\([^)]", path.read_text(encoding="utf-8"))  # a call, not a mention
        and path.name != "acquisition.py"
    )
    assert found == sorted(CALLERS)


@pytest.mark.parametrize("caller", CALLERS)
def test_every_caller_records_the_header_it_sent(caller) -> None:
    """⭐ The record names what was sent: the constant itself, never a copy of its text."""
    text = (ROOT / caller).read_text(encoding="utf-8")
    assert '"user_agent": USER_AGENT' in text
    assert "user_agent=" not in text
