"""A dirty tree cannot be stamped, and nothing offers a way round that.

⛔ **The defect these exist for.** `generator_for` took a keyword that skipped its refusal, and
four generators exposed it as a command-line flag hidden from their own help. With it, a dirty
tree came out with a `generator` block identical to a clean one's — the commit named, nothing
to say the code that ran was not the code at that commit. That is the one failure the
refusal was written to make impossible, and it was one undocumented flag away.
"""

from __future__ import annotations

import inspect
import re
import subprocess
from pathlib import Path

import pytest

from saakshi import provenance, surface
from saakshi.fixture import FixtureContractError, Generator

ROOT = Path(__file__).resolve().parents[1]

#: Every source that runs: the generators, the package, the tools.
SOURCES = sorted([*ROOT.glob("generators/*.py"), *ROOT.glob("src/saakshi/*.py"), *ROOT.glob("tools/*.py")])


def _committed_copy(where: Path) -> Path:
    """A repository with this package's layout and one committed generator script."""
    (where / "generators").mkdir(parents=True)
    (where / "generators" / "g.py").write_text("print('a generator')\n", encoding="utf-8")
    for args in (["init", "-q"], ["add", "generators/g.py"],
                 ["-c", "user.name=t", "-c", "user.email=t@example.invalid", "commit", "-qm", "one"]):
        subprocess.run(["git", *args], cwd=where, check=True, capture_output=True)
    return where


def test_the_sources_were_found():
    """⚠ The control for the scan below: an empty list would pass it vacuously."""
    names = {path.name for path in SOURCES}
    assert {"provenance.py", "r1_horizons.py", "r1_drift.py", "publisher_testpo.py",
            "r2_kernel_states.py", "check_public_tree.py"} <= names


@pytest.mark.parametrize("path", SOURCES, ids=lambda p: p.relative_to(ROOT).as_posix())
def test_no_source_offers_a_way_past_the_dirty_tree_refusal(path):
    """⛔ No override by keyword and no flag hidden from `--help`. Fails on every platform if either
    comes back, and needs none of the oracle libraries the generators import."""
    text = path.read_text(encoding="utf-8")
    assert not re.search(r"allow[_-]dirty", text), "an override of the dirty-tree refusal"
    assert "argparse.SUPPRESS" not in text, "a command-line option hidden from its own help"


def test_generator_for_takes_no_override():
    assert list(inspect.signature(provenance.generator_for).parameters) == ["script"]
    assert list(inspect.signature(surface.load).parameters) == ["path"]


def test_a_committed_tree_is_stamped_with_its_commit(tmp_path):
    tree = _committed_copy(tmp_path / "tree")
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=tree, capture_output=True, text=True,
                          check=True).stdout.strip()
    generator = provenance.generator_for(tree / "generators" / "g.py")
    assert generator.as_json() == {"repo": provenance.REPO, "script": "generators/g.py", "commit": head}
    assert generator.dirty is False


@pytest.mark.parametrize("dirt", ["a modified tracked file", "an untracked file"])
def test_a_dirty_tree_is_refused_and_cannot_be_talked_past(tmp_path, dirt):
    tree = _committed_copy(tmp_path / "tree")
    if dirt == "an untracked file":
        (tree / "notes.txt").write_text("x\n", encoding="utf-8")
    else:
        (tree / "generators" / "g.py").write_text("print('changed')\n", encoding="utf-8")
    script = tree / "generators" / "g.py"
    with pytest.raises(RuntimeError, match="dirty"):
        provenance.generator_for(script)
    with pytest.raises(TypeError):
        provenance.generator_for(script, allow_dirty=True)  # type: ignore[call-arg]


def test_the_fixture_writer_still_refuses_a_dirty_identity():
    """⭐ The second wall, unchanged: an identity marked dirty is never written."""
    with pytest.raises(FixtureContractError, match="dirty"):
        Generator(repo="r", script="s", commit="c", dirty=True).as_json()
