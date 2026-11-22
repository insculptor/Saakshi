"""The continuity exporter, run end to end: what a dry run promises, and what it may not depend on.

⭐ **A dry run is a prediction of the write, or it is nothing.** One passed while the write it
was meant to price was refused — it never built the header the writer validates — so the
operator learnt the grid's size and nothing about whether the file could exist. Every test
here pairs the dry run with the write it predicts, on the same tree and the same input.

The exporter runs from a committed copy (a dirty tree cannot be stamped), against a sampled
tree whose calls are the standard library's own: nothing here samples a real implementation.
"""

from __future__ import annotations

import hashlib
import os
import re
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "generators" / "r5_continuity.py"


def _git(repo: Path, *args: str) -> str:
    environment = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@example.invalid",
                       GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@example.invalid")
    return subprocess.run(["git", "-c", "commit.gpgsign=false", *args], cwd=repo, env=environment,
                          capture_output=True, text=True, check=True).stdout


def _committed(repo: Path, populate) -> Path:
    repo.mkdir(parents=True)
    populate(repo)
    _git(repo, "init", "-q")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "one")
    return repo


def _exporter(base: Path) -> Path:
    """The generator and the package it imports, committed — and ⚠ no ignore file."""
    def populate(repo: Path) -> None:
        (repo / "generators").mkdir()
        shutil.copy2(SCRIPT, repo / "generators" / SCRIPT.name)
        shutil.copytree(ROOT / "src", repo / "src", ignore=shutil.ignore_patterns("__pycache__"))
    return _committed(base / "exporter", populate)


#: A sampled surface built from the standard library: the builder makes a mapping of the two
#: resolved coordinates, and the one call hands it back. Its leaves are doubles with patterns.
_PLAIN = """
    [engine]
    root = "{root}"
    label = "{label}"
    native_builder = "builtins:dict"
    [engine.native_fields]
    latitude = "latitude"
    longitude = "longitude"
    [[atom]]
    id = "a"
    call = "copy:copy"
    """

#: ⚠ A surface whose one call returns a path made absolute against the working directory:
#: a value the writer must refuse in a ROW, after the header has passed.
_ROW_REFUSED = """
    [engine]
    root = "{root}"
    label = "an implementation"
    native_builder = "builtins:str"
    [engine.native_fields]
    object = "place_label"
    [[atom]]
    id = "a"
    call = "os.path:abspath"
    """


def _surface(base: Path, body: str = _PLAIN, *, label: str = "an implementation") -> Path:
    sampled = _committed(base / "sampled", lambda repo: (repo / "README").write_text("t\n", encoding="ascii"))
    path = base / "surface.toml"
    path.write_text(textwrap.dedent(body).format(root=sampled.as_posix(), label=label), encoding="utf-8")
    return path


def _run(exporter: Path, surface: Path, out: Path, *extra: str, tzpath: str = "") -> subprocess.CompletedProcess:
    # ⭐ `-B`: a cache directory written into the copy would make it dirty, and the refusal
    #    under test would then be the dirty-tree one. The empty search path keeps a machine's
    #    own rule-set directory out of the header, where the writer refuses an absolute path.
    environment = dict(os.environ, PYTHONTZPATH=tzpath, PYTHONDONTWRITEBYTECODE="1")
    return subprocess.run(
        [sys.executable, "-B", str(exporter / "generators" / SCRIPT.name), "--surface", str(surface),
         "--out", str(out), "--natives", "3", *extra],
        cwd=exporter, env=environment, capture_output=True, text=True, timeout=300, check=False,
    )


def _corpus(out: Path) -> Path:
    return out / "continuity" / "corpus.jsonl"


def test_a_dry_run_states_the_bytes_the_write_then_writes(tmp_path):
    """⭐ The prediction is checkable: the dry run names the digest, and the write produces it."""
    exporter, surface = _exporter(tmp_path), _surface(tmp_path)
    out = tmp_path / "out"
    dry = _run(exporter, surface, out, "--report-only")
    assert dry.returncode == 0, dry.stderr[-2000:]
    assert not out.exists(), "a dry run wrote something"
    stated = re.search(r"sha256 ([0-9a-f]{64})", dry.stdout)
    assert stated, dry.stdout[-2000:]
    wet = _run(exporter, surface, out)
    assert wet.returncode == 0, wet.stderr[-2000:]
    assert hashlib.sha256(_corpus(out).read_bytes()).hexdigest() == stated.group(1)


def test_a_dry_run_refuses_a_header_the_write_refuses(tmp_path):
    """⛔ The defect itself: an absolute path in the header passed the dry run and failed the write."""
    exporter = _exporter(tmp_path)
    surface = _surface(tmp_path, label="the implementation at /opt/sampled/tree")
    out = tmp_path / "out"
    dry = _run(exporter, surface, out, "--report-only")
    assert dry.returncode != 0 and "absolute path" in dry.stderr, dry.stdout[-1500:]
    assert not out.exists()
    wet = _run(exporter, surface, out)  # ⭐ the control: the write is refused for the same reason
    assert wet.returncode != 0 and "absolute path" in wet.stderr


def test_a_dry_run_refuses_a_row_the_write_refuses(tmp_path):
    """⛔ A header that passes is not a file that passes: every row is held to the writer's law."""
    exporter, surface = _exporter(tmp_path), _surface(tmp_path, _ROW_REFUSED)
    out = tmp_path / "out"
    dry = _run(exporter, surface, out, "--report-only")
    assert dry.returncode != 0 and "absolute path" in dry.stderr and "row[0]" in dry.stderr, dry.stdout[-1500:]
    assert not out.exists()
    wet = _run(exporter, surface, out)
    assert wet.returncode != 0 and "absolute path" in wet.stderr


def test_a_dry_run_on_a_dirty_tree_is_refused_as_the_write_would_be(tmp_path):
    """⛔ No stand-in identity is built for a dirty tree, so a dry run there says what the write says.

    It still samples and prices the grid first — the size is printed — and then stops where the
    write would stop. Nothing is stamped either way, because nothing is written.
    """
    exporter, surface = _exporter(tmp_path), _surface(tmp_path)
    (exporter / "untracked.txt").write_text("x", encoding="ascii")
    out = tmp_path / "out"
    dry = _run(exporter, surface, out, "--report-only")
    assert dry.returncode != 0 and "dirty" in dry.stderr, dry.stdout[-1500:]
    assert "size:" in dry.stdout
    assert not out.exists()
    wet = _run(exporter, surface, out)
    assert wet.returncode != 0 and "dirty" in wet.stderr and not out.exists()

