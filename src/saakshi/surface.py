"""The call surface of an engine this repository samples, declared as data.

⭐ **Why this is a config file and not code.** A continuity recorder has to name the
functions it calls. Those names describe the *shape* of somebody else's tree, and the engine
sampled for continuity is by definition one that is not public. Writing them into a script
here would publish that shape; so the script is generic and the names live in a local file,
exactly as the reserved-name list does. **The mechanism is public and the surface is not.**

⛔ **Recorder, never explainer.** Nothing here knows what an atom means. The loader resolves
a dotted path, calls it, and hands back whatever came out. There is no per-atom logic, no
argument special-casing and no interpretation — which is what keeps the driver from becoming
an account of how the sampled engine works.

⛔ **Fail-closed throughout.** A missing file, an unresolvable path, a duplicate id, an id
that would violate the fixture contract's key rules — every one refuses. A recorder that
silently samples less than it was asked to produces a fixture that *looks* complete, which is
the failure this repository exists to prevent.
"""

from __future__ import annotations

import importlib
import re
import subprocess
import sys
import tomllib
from dataclasses import dataclass, field as dc_field
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from .fixture import reserved_names

#: The resolved-input vocabulary a surface may bind a builder argument to.
#:
#: ⭐ **This list is the gate.** Every name in it is a value the recorder has already
#: resolved, so an engine call built only from these names consumes nothing that a
#: deployment holds — no timezone lookup, no place-name resolution. A surface cannot ask
#: for an unresolved input because there is no name for one.
RESOLVED_FIELDS = frozenset(
    {
        "civil_local_naive",  # datetime, tz-naive — the local clock reading
        "civil_local_iso",  # the same, as text
        "utc_aware",  # datetime, tz-aware UTC
        "utc_iso",  # the same, as text
        "zone",  # IANA key — ⚠ explicable, but the offset is the authority
        "utc_offset_seconds",
        "latitude",
        "longitude",
        "place_label",  # ⛔ a label; passing it as an input defeats the point
    }
)

#: Atom ids become fixture `section` values and must therefore satisfy the same key law.
_ID_RE = re.compile(r"^[a-z][a-z0-9_]*$")

#: `module.path:attribute`, the one accepted spelling for a call target.
_TARGET_RE = re.compile(r"^[A-Za-z_][\w.]*:[A-Za-z_]\w*$")

DEFAULT_SURFACE = Path("config") / "predecessor-surface.toml"


class SurfaceError(Exception):
    """Raised when a surface declaration cannot be trusted to sample what it claims."""


def _resolve_target(target: str, *, where: str) -> Callable[..., Any]:
    if not _TARGET_RE.match(target):
        raise SurfaceError(
            f"{where}: {target!r} is not `module.path:attribute` — the one accepted spelling"
        )
    module_name, _, attribute = target.partition(":")
    try:
        module = importlib.import_module(module_name)
    except Exception as exc:
        raise SurfaceError(f"{where}: cannot import {module_name!r}: {exc}") from exc
    try:
        return getattr(module, attribute)
    except AttributeError as exc:
        raise SurfaceError(f"{where}: {module_name!r} has no {attribute!r}") from exc


@dataclass(frozen=True)
class Atom:
    """One sampled call, and every variation of it that is to be recorded.

    `vary` expands to one call per value, so a family of related calls — the same function
    over a list of modes — is declared once and counted honestly. ⚠ Exactly one axis: a
    second one would multiply silently, and a grid whose size is not obvious from its
    declaration is the thing the manifest exists to stop.
    """

    id: str
    target: str
    call: Callable[..., Any]
    kwargs: Mapping[str, Any] = dc_field(default_factory=dict)
    vary_key: str | None = None
    vary_values: Sequence[Any] = dc_field(default_factory=tuple)
    settings: Mapping[str, Any] | None = None

    def variations(self) -> list[tuple[str, dict[str, Any]]]:
        """`(section, kwargs)` per call. The section is the id, suffixed by the variation."""
        if self.vary_key is None:
            return [(self.id, dict(self.kwargs))]
        out: list[tuple[str, dict[str, Any]]] = []
        for value in self.vary_values:
            token = str(value).lower()
            if not _ID_RE.match(token):
                raise SurfaceError(
                    f"atom {self.id!r}: variation {value!r} does not form a usable section "
                    "name; a section is lower_snake_case because it is a fixture key"
                )
            out.append((f"{self.id}__{token}", {**self.kwargs, self.vary_key: value}))
        return out


@dataclass(frozen=True)
class Surface:
    """A whole declared surface, with the sampled tree's identity."""

    root: Path
    atoms: tuple[Atom, ...]
    native_builder: Callable[..., Any]
    native_builder_target: str
    native_fields: Mapping[str, str]
    settings_builder: Callable[..., Any] | None
    settings_builder_target: str | None
    commit: str
    dirty: bool
    label: str

    def oracle_identity(self) -> dict[str, Any]:
        """The `oracle` block: what answered, at which state.

        ⛔ The path is **not** recorded. It is a fact about this workstation, and a fixture
        that carries it publishes a directory layout for no evidential gain.
        """
        return {
            "kind": "predecessor_engine",
            "label": self.label,
            "commit": self.commit,
            "role": (
                "continuity only — what the earlier implementation answered. ⛔ Never "
                "astronomical truth, and never an authority on a convention"
            ),
        }

    def section_names(self) -> list[str]:
        names: list[str] = []
        for atom in self.atoms:
            names.extend(section for section, _ in atom.variations())
        return names


def _git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args], cwd=root, capture_output=True, text=True, check=False
    )
    if result.returncode != 0:
        raise SurfaceError(f"git {' '.join(args)} in the sampled tree failed: {result.stderr.strip()}")
    return result.stdout.strip()


def load(path: Path | str = DEFAULT_SURFACE, *, allow_dirty: bool = False) -> Surface:
    """Load and validate a surface declaration, importing the tree it names.

    ⚠ **This mutates `sys.path`.** Sampling an engine means importing it, and it is not a
    dependency of this repository and never will be — so its root is prepended at call time
    and nothing about it is installed. ⛔ It is imported to be *called*, never read: no code
    here derives anything from what it finds there.
    """
    path = Path(path)
    if not path.is_file():
        raise SurfaceError(
            f"{path}: no surface declaration. ⛔ There is no default surface — a recorder "
            "with nothing declared would write an empty fixture, and an empty evidence file "
            f"reads as evidence. Copy {path.name}.example and fill it in."
        )

    with path.open("rb") as fh:
        raw = tomllib.load(fh)

    engine = raw.get("engine")
    if not isinstance(engine, Mapping):
        raise SurfaceError(f"{path}: no [engine] table")

    root_value = engine.get("root")
    if not root_value:
        raise SurfaceError(f"{path}: [engine].root is required — the tree to import from")
    root = Path(str(root_value)).expanduser()
    if not root.is_dir():
        raise SurfaceError(f"{path}: [engine].root {root} is not a directory")
    root = root.resolve()

    label = str(engine.get("label") or "").strip()
    if not label:
        raise SurfaceError(
            f"{path}: [engine].label is required — the fixture must say what answered, and "
            "a label is what a consumer reads when the name itself cannot be published"
        )
    for name in reserved_names():
        if name in label.lower():
            raise SurfaceError(
                f"{path}: [engine].label may not contain the reserved name {name!r}; the "
                "label is written into every fixture this surface produces"
            )

    # ⛔ Same law as this repository's own provenance: a commit that names an uncommitted
    #    state is a false statement, and it is false about the one thing R5 evidence is for.
    commit = _git(root, "rev-parse", "HEAD")
    status = _git(root, "status", "--porcelain")
    dirty = bool(status.strip())
    if dirty and not allow_dirty:
        raise SurfaceError(
            f"{path}: the sampled tree at {root.name} is dirty, so `oracle.commit` would "
            "name a state nobody can check out. Commit it, then sample.\n"
            + "\n".join(f"    {line}" for line in status.splitlines()[:20])
        )

    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

    native_target = str(engine.get("native_builder") or "")
    if not native_target:
        raise SurfaceError(
            f"{path}: [engine].native_builder is required — it turns a resolved grid point "
            "into whatever the sampled calls take as their first argument"
        )
    native_builder = _resolve_target(native_target, where=f"{path} [engine].native_builder")

    native_fields = engine.get("native_fields")
    if not isinstance(native_fields, Mapping) or not native_fields:
        raise SurfaceError(
            f"{path}: [engine.native_fields] is required — it binds the builder's argument "
            "names to resolved inputs"
        )
    for argument, source in native_fields.items():
        if not isinstance(source, str) or source not in RESOLVED_FIELDS:
            raise SurfaceError(
                f"{path}: [engine.native_fields].{argument} = {source!r} is not a resolved "
                f"input. ⛔ Permitted: {sorted(RESOLVED_FIELDS)}. There is deliberately no "
                "name for an unresolved input — that is what keeps a sampled call from "
                "depending on state the engine's deployment holds"
            )

    settings_target = engine.get("settings_builder")
    settings_builder = None
    if settings_target:
        settings_builder = _resolve_target(
            str(settings_target), where=f"{path} [engine].settings_builder"
        )

    atom_specs = raw.get("atom")
    if not isinstance(atom_specs, list) or not atom_specs:
        raise SurfaceError(f"{path}: no [[atom]] entries — nothing would be sampled")

    atoms: list[Atom] = []
    seen: set[str] = set()
    for index, spec in enumerate(atom_specs):
        where = f"{path} [[atom]] #{index + 1}"
        if not isinstance(spec, Mapping):
            raise SurfaceError(f"{where}: not a table")
        atom_id = str(spec.get("id") or "")
        if not _ID_RE.match(atom_id):
            raise SurfaceError(
                f"{where}: id {atom_id!r} must be lower_snake_case — it becomes a fixture key"
            )
        for name in reserved_names():
            if name in atom_id:
                raise SurfaceError(f"{where}: id may not contain the reserved name {name!r}")
        if atom_id in seen:
            raise SurfaceError(f"{where}: duplicate id {atom_id!r}")
        seen.add(atom_id)

        target = str(spec.get("call") or "")
        call = _resolve_target(target, where=where)

        kwargs = spec.get("kwargs") or {}
        if not isinstance(kwargs, Mapping):
            raise SurfaceError(f"{where}: kwargs must be a table")

        vary = spec.get("vary") or {}
        if not isinstance(vary, Mapping):
            raise SurfaceError(f"{where}: vary must be a table")
        if len(vary) > 1:
            raise SurfaceError(
                f"{where}: vary declares {len(vary)} axes. ⛔ One axis only — two would "
                "multiply, and a grid whose size is not obvious from its declaration is "
                "exactly what the export manifest exists to bound"
            )
        vary_key = next(iter(vary), None)
        vary_values = tuple(vary[vary_key]) if vary_key else ()
        if vary_key and not vary_values:
            raise SurfaceError(f"{where}: vary.{vary_key} is empty")

        settings = spec.get("settings")
        if settings is not None:
            if not isinstance(settings, Mapping):
                raise SurfaceError(f"{where}: settings must be a table")
            if settings_builder is None:
                raise SurfaceError(
                    f"{where}: declares settings, but [engine].settings_builder is absent"
                )

        atoms.append(
            Atom(
                id=atom_id,
                target=target,
                call=call,
                kwargs=dict(kwargs),
                vary_key=vary_key,
                vary_values=vary_values,
                settings=dict(settings) if settings is not None else None,
            )
        )

    return Surface(
        root=root,
        atoms=tuple(atoms),
        native_builder=native_builder,
        native_builder_target=native_target,
        native_fields=dict(native_fields),
        settings_builder=settings_builder,
        settings_builder_target=str(settings_target) if settings_target else None,
        commit=commit,
        dirty=dirty and not allow_dirty,
        label=label,
    )
