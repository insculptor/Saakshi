"""Flatten a returned object into leaf records — the one representation a recorder may use.

⭐ **The sampled engine's names become fixture *values*, never fixture *keys*.** A recorder
that serialises a returned object as-is copies that object's field names straight into the
evidence file: they become permanent identifiers, they break the contract's key law the
moment one of them is capitalised or numeric, and a rename in the sampled tree silently
renames the evidence. Flattening to `{"path": "...", "number": ...}` puts every one of those
names on the value side, where it is data about what was sampled rather than structure the
fixture is committed to.

⚠ It is also the only shape a continuity comparison can actually use. Continuity is asked
one leaf at a time — *"did this number move?"* — so a corpus that has to be re-walked before
it can be diffed answers the question later and more expensively than one that is already a
list of addressed values.

⛔ **No interpretation.** Nothing here knows what a leaf means, and no leaf is rounded,
reordered or dropped. Types this module does not recognise are recorded as unrepresentable,
by name, rather than coerced into something printable.
"""

from __future__ import annotations

import dataclasses
import datetime as _dt
import enum
import hashlib
import json
from typing import Any, Iterator, Mapping, Sequence

from .fixture import bits

#: How deep a path may go before the walk refuses. A cycle in a returned object would
#: otherwise spin forever; a legitimately deeper structure is a finding worth stopping on.
MAX_DEPTH = 64


class LeafError(Exception):
    """Raised when a returned object cannot be walked."""


def _unwrap(node: Any) -> Any:
    """Reduce a container-ish object to a mapping or sequence, without interpreting it."""
    if dataclasses.is_dataclass(node) and not isinstance(node, type):
        return {f.name: getattr(node, f.name) for f in dataclasses.fields(node)}
    dump = getattr(node, "model_dump", None)  # a widely-used model protocol
    if callable(dump):
        try:
            return dump(mode="python")
        except Exception:  # pragma: no cover - a model that refuses is left alone
            return None
    as_dict = getattr(node, "_asdict", None)  # named tuples
    if callable(as_dict):
        return as_dict()
    return None


def walk(node: Any, *, path: str = "", depth: int = 0) -> Iterator[dict[str, Any]]:
    """Yield one record per leaf, in deterministic order.

    Mapping keys are sorted, so two runs over structurally equal objects produce identical
    files even if the sampled engine's iteration order moves.
    """
    if depth > MAX_DEPTH:
        raise LeafError(f"{path or '<root>'}: deeper than {MAX_DEPTH} — refusing to walk on")

    if node is None:
        yield {"path": path, "null": True}
        return
    if isinstance(node, bool):  # ⚠ before int: bool is an int, and conflating them loses a fact
        yield {"path": path, "flag": node}
        return
    if isinstance(node, int):
        yield {"path": path, "integer": node}
        return
    if isinstance(node, float):
        # ⭐ The bit pattern travels beside the decimal, as everywhere else in this
        #    repository: a consumer that disagrees on one and agrees on the other has a
        #    formatting difference, not a numeric one.
        yield {"path": path, "number": node, "bits": bits(node)}
        return
    if isinstance(node, str):
        yield {"path": path, "text": node}
        return
    if isinstance(node, enum.Enum):
        yield from walk(node.value, path=path, depth=depth + 1)
        return
    if isinstance(node, (_dt.datetime, _dt.date, _dt.time)):
        yield {"path": path, "text": node.isoformat(), "temporal": True}
        return
    if isinstance(node, _dt.timedelta):
        yield {"path": path, "number": node.total_seconds(), "bits": bits(node.total_seconds())}
        return

    unwrapped = _unwrap(node)
    if unwrapped is not None:
        yield from walk(unwrapped, path=path, depth=depth + 1)
        return

    if isinstance(node, Mapping):
        for key in sorted(node, key=str):
            child = f"{path}.{key}" if path else str(key)
            yield from walk(node[key], path=child, depth=depth + 1)
        return
    if isinstance(node, (set, frozenset)):
        # Sets have no order to preserve, so one is imposed and said out loud.
        for index, item in enumerate(sorted(node, key=str)):
            yield from walk(item, path=f"{path}{{{index}}}", depth=depth + 1)
        return
    if isinstance(node, Sequence):
        for index, item in enumerate(node):
            yield from walk(item, path=f"{path}[{index}]", depth=depth + 1)
        return

    # ⛔ Not coerced. `str(node)` here would write a memory address into a fixture and it
    #    would look like a value.
    yield {"path": path, "unrepresentable": type(node).__name__}


def flatten(node: Any) -> list[dict[str, Any]]:
    return list(walk(node))


#: Fields excluded from the digest because they are display, not value.
#:
#: ⭐ `number` is the decimal rendering of a double whose authoritative form is `bits`
#: alongside it. Hashing the decimal would make the digest reproducible only by a consumer
#: that also reproduces this writer's float formatting — and, worse, checkable only through
#: the very decimal path that must never be load-bearing. A widely-used JSON library was
#: measured mis-parsing 18.9 % of shortest-round-tripping doubles by up to 2 ULP; a consumer
#: on that path would fail the digest while holding the correct value, or pass it while
#: holding a wrong one.
_DISPLAY_ONLY = frozenset({"number"})


def digest(leaves: Sequence[Mapping[str, Any]]) -> str:
    """A content digest over the leaf set — `sha256:...`.

    Computed over the **authoritative** form of every leaf: bit patterns for doubles, and
    the literal for everything that crosses a text boundary exactly (integers, strings,
    flags). It changes when a value changes, when a leaf appears or disappears, and when one
    is renamed.

    ⚠ It is a digest of *what was recorded*, which is what a consumer needs; it is not a
    digest of the sampled engine's internal state and says nothing about how the value was
    produced.
    """
    authoritative = [
        {key: value for key, value in leaf.items() if key not in _DISPLAY_ONLY}
        for leaf in leaves
    ]
    canonical = json.dumps(
        authoritative, sort_keys=True, ensure_ascii=True, separators=(",", ":")
    )
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()
