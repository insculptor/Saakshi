"""Generator identity — the `generator` field of every fixture.

⛔ **A dirty tree cannot be stamped.** `generator.commit` is a promise that the code which
produced these numbers can be read at that commit. If the tree has uncommitted changes the
promise is false, and a false provenance field is worse than a missing one because it
looks discharged.

⚠ Dirty means **cannot run**, never "run with a warning". A guard that proceeds against a
dirty tree does not merely weaken its own report — it produces a *pass* that is wrong
about the thing it was written to establish.
"""

from __future__ import annotations

import datetime as _dt
import platform
import subprocess
import sys
from pathlib import Path

from .fixture import Generator

REPO = "github.com/insculptor/Saakshi"


def _git(repo_root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout.strip()


def repo_root(start: Path | None = None) -> Path:
    here = (start or Path(__file__)).resolve()
    for candidate in (here, *here.parents):
        if (candidate / ".git").exists():
            return candidate
    raise RuntimeError("not inside a git working tree; provenance cannot be recorded")


def generator_for(script: Path, *, allow_dirty: bool = False) -> Generator:
    """Identify the generator, refusing to stamp an uncommitted state.

    `allow_dirty` exists only for the schema's own tests, which must be able to exercise
    the refusal. ⛔ No generator passes it.
    """
    root = repo_root(script)
    try:
        commit = _git(root, "rev-parse", "HEAD")
    except RuntimeError as exc:  # no commit yet
        raise RuntimeError(
            "this repository has no commit, so `generator.commit` has nothing to name. "
            "Commit the generator, then generate."
        ) from exc
    status = _git(root, "status", "--porcelain")
    dirty = bool(status.strip())
    if dirty and not allow_dirty:
        raise RuntimeError(
            "the working tree is dirty, so `generator.commit` would name a state that does "
            "not exist. Commit first, then generate.\n"
            + "\n".join(f"    {line}" for line in status.splitlines()[:20])
        )
    return Generator(
        repo=REPO,
        script=str(script.resolve().relative_to(root)).replace("\\", "/"),
        commit=commit,
        dirty=dirty and not allow_dirty,
    )


def today() -> str:
    """The `generated` date, UTC, ISO-8601."""
    return _dt.datetime.now(_dt.timezone.utc).date().isoformat()


def host_record() -> dict[str, str]:
    """The environment a measurement was taken on.

    ⚠ Recorded as *context*, never as a claim. A number measured on one workstation is an
    indication of magnitude; it is not a published performance figure.
    """
    return {
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "machine": platform.machine(),
    }
