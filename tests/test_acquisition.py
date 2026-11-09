"""What `retrieve()` tells the server it is.

⭐ No network. The request `retrieve()` builds is captured before it would be sent, so what is
under test is the header itself rather than whether a server happened to accept it.
"""

from __future__ import annotations

import inspect
import urllib.request
from email.message import Message

import pytest

from saakshi import acquisition
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


def test_the_default_is_what_every_generator_already_sent(sent, tmp_path) -> None:
    """⛔ A caller that passes nothing must send exactly the header it sent before."""
    retrieve("https://example.invalid/a", cache=tmp_path / "a")
    assert sent[0].get_header("User-agent") == USER_AGENT == "saakshi/0.1"
    assert inspect.signature(retrieve).parameters["user_agent"].default == USER_AGENT


def test_a_caller_names_its_own_client(sent, tmp_path) -> None:
    named = USER_AGENT + " (+https://example.invalid/contact)"
    retrieve("https://example.invalid/b", cache=tmp_path / "b", user_agent=named)
    assert sent[0].get_header("User-agent") == named


def test_the_header_is_the_only_thing_the_keyword_moves(sent, tmp_path) -> None:
    """⭐ Twins: one address, one payload, two client names. Everything recorded agrees."""
    first = retrieve("https://example.invalid/c", cache=tmp_path / "c1")
    second = retrieve("https://example.invalid/c", cache=tmp_path / "c2", user_agent="other/1")
    assert sent[0].full_url == sent[1].full_url
    assert first.as_record() == second.as_record()
    assert sent[0].get_header("User-agent") != sent[1].get_header("User-agent")
