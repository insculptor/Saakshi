"""The working-tree half of the reserved-name check.

⛔ **The failure this exists for.** A parallel session working on a consumer wrote a
directory bearing that consumer's name into this clone. It was never tracked and never
git-ignored, so the tracked-files scope and the history scope were both blind to it, and a
single ``git add -A`` — which this repository's own workflow uses — would have published
it permanently.

⛔ **And the fix that was refused.** Git-ignoring that one path silences the report without
removing the hazard: the next one arrives under a different name in a different path. So
the scan does not consult ``.gitignore`` at all, and these tests pin that: an ignored path
is scanned exactly like any other.

⚠ Every test here uses the synthetic name ``acme``. The real list is private, and a test
that hard-coded a real one would be the leak it is testing for.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

import check_public_tree as check  # noqa: E402

PATTERNS = [(re.escape("acme"), "the reserved name 'acme'")]


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A real git repository, because "ignored" is a git verdict and must be a real one."""
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    (tmp_path / ".gitignore").write_text("out/\n", encoding="utf-8")
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "clean.py").write_text("value = 1\n", encoding="utf-8")
    return tmp_path


def failures(repo: Path) -> list[str]:
    found, _examined = check.scan_working_tree(PATTERNS, root=repo)
    return found


def test_a_clean_tree_is_green(repo):
    assert failures(repo) == []


def test_an_untracked_directory_bearing_the_name_is_refused(repo):
    """The original failure, in the shape it actually arrived in."""
    planted = repo / "crates" / "acme-validation" / "testdata"
    planted.mkdir(parents=True)
    (planted / "rows.jsonl").write_text('{"row": 1}\n', encoding="utf-8")

    report = "\n".join(failures(repo))
    assert "a working-tree PATH" in report
    assert "crates/acme-validation" in report


def test_an_empty_directory_bearing_the_name_is_refused(repo):
    """⭐ Git cannot see this one at all — it tracks no empty directory, so it appears in
    no status, no diff and no commit. The scan walks the filesystem for exactly this."""
    (repo / "docs" / "acme-notes").mkdir(parents=True)

    status = subprocess.run(
        ["git", "status", "--porcelain"], cwd=repo, capture_output=True, text=True, check=True
    )
    assert "acme" not in status.stdout  # the blindness, demonstrated rather than asserted

    assert "a working-tree PATH" in "\n".join(failures(repo))


def test_removing_the_path_makes_it_green_again(repo):
    """⚠ The control. A check that only ever reds has not been shown to measure anything."""
    planted = repo / "crates" / "acme-validation"
    planted.mkdir(parents=True)
    (planted / "rows.jsonl").write_text('{"row": 1}\n', encoding="utf-8")
    assert failures(repo)

    (planted / "rows.jsonl").unlink()
    planted.rmdir()
    (repo / "crates").rmdir()
    assert failures(repo) == []


def test_the_name_in_an_untracked_file_body_is_refused(repo):
    (repo / "notes.md").write_text("generated for acme\n", encoding="utf-8")

    report = "\n".join(failures(repo))
    assert "in the working tree" in report
    assert "notes.md" in report


def test_a_git_ignored_path_is_scanned_like_any_other(repo):
    """⛔ The rule that makes git-ignoring useless as a way to silence this."""
    # ⚠ A clean filename and a dirty body, so this tests the CONTENT scan reaching an
    #   ignored file rather than the path scan finding a name in its filename.
    (repo / "out").mkdir()
    (repo / "out" / "values.jsonl").write_text('{"generated_by": "acme"}\n', encoding="utf-8")

    ignored = subprocess.run(
        ["git", "check-ignore", "out/values.jsonl"], cwd=repo, capture_output=True, text=True
    )
    assert ignored.returncode == 0  # git really does ignore it

    report = "\n".join(failures(repo))
    assert "in the working tree" in report
    assert "out/values.jsonl" in report


def test_a_path_private_by_design_is_exempt(repo):
    (repo / "docs" / "local").mkdir(parents=True)
    (repo / "docs" / "local" / "handoff.md").write_text("acme owes us\n", encoding="utf-8")

    assert failures(repo) == []


def test_an_exemption_matches_whole_components_only(repo):
    """⚠ `docs/local` must not quietly exempt a `docs/local-notes/` created beside it."""
    (repo / "docs" / "local-notes").mkdir(parents=True)
    (repo / "docs" / "local-notes" / "x.md").write_text("acme owes us\n", encoding="utf-8")

    assert failures(repo)


def test_every_exemption_is_reported_so_it_can_be_withdrawn():
    """⭐ An exemption nobody reads is an exemption nobody removes."""
    for path, reason in check.PRIVATE_BY_DESIGN.items():
        assert check.exemption(path) == reason
        assert check.exemption(path + "/inside") == reason
    assert check.exemption("src/saakshi/fixture.py") is None


def test_the_path_listing_does_not_survive_the_scan(repo):
    """⚠ It carries every path in the tree, so leaving it behind would plant the leak."""
    (repo / "crates" / "acme-validation").mkdir(parents=True)
    failures(repo)
    assert not (repo / check.PATH_LISTING).exists()


def test_undecodable_bytes_do_not_abort_the_scan(repo):
    """⛔ Measured, not imagined: the first run of this scan died here.

    ``text=True`` decodes what git prints using the console's encoding, and this scan reads
    every text file on disk. One byte a Windows cp1252 console cannot decode raised inside
    a reader thread and the check exited with no verdict at all — the same shape as the
    marker-glyph abort this repository already fixed on the output side.
    """
    (repo / "odd.txt").write_bytes(b"acme \x90\xff and more\n")

    assert "in the working tree" in "\n".join(failures(repo))


# --- the content-only exemption for acquired source material ---------------------------


def test_a_reserved_name_inside_an_acquired_text_is_not_reported(repo):
    """⭐ The false positive that would otherwise fire forever.

    ⛔ Measured on the first two texts the textual reference acquired: one of them names a
    sage whose name is also a reserved name, twice. It is a work of the tradition the
    consumer was itself named after, so the collision is there by construction rather than
    by accident, and the next classical text carries it too. A check that always fires is a
    check nobody reads.
    """
    cache = repo / "cache" / "textual"
    cache.mkdir(parents=True)
    (cache / "some-published-text.txt").write_text(
        "the sage acme also opines that the third house\n", encoding="utf-8"
    )

    assert failures(repo) == []


def test_a_planted_directory_under_the_cache_is_still_refused(repo):
    """⛔ The narrowing is CONTENT ONLY, and this is the failure it must not touch.

    The working-tree scan exists because a parallel session wrote a consumer-named directory
    into this clone. Exempting the cache wholesale would have reopened exactly that hole in
    the one directory a parallel session is most likely to write into.
    """
    planted = repo / "cache" / "acme-fixtures"
    planted.mkdir(parents=True)
    (planted / "rows.jsonl").write_text('{"row": 1}\n', encoding="utf-8")

    report = "\n".join(failures(repo))
    assert "a working-tree PATH" in report
    assert "acme" in report


def test_what_the_repository_writes_from_an_acquired_text_is_still_scanned(repo):
    """⛔ A fixture quotes its sources, and a quotation carrying a reserved name is a leak."""
    (repo / "out" / "textual").mkdir(parents=True)
    (repo / "out" / "textual" / "rules.jsonl").write_text(
        '{"quoted": "the sage acme also opines"}\n', encoding="utf-8"
    )

    assert "in the working tree" in "\n".join(failures(repo))


def test_the_content_only_exemption_does_not_exempt_the_path(repo):
    """⚠ The two passes are separate, and only one of them was narrowed."""
    for path in check.FOREIGN_CONTENT:
        assert check.content_exemption(path) is not None
        assert check.exemption(path) is None


def test_the_content_exemption_also_covers_the_fully_private_paths(repo):
    """A path exempt from both passes must not be reported by the content pass either."""
    for path in check.PRIVATE_BY_DESIGN:
        assert check.content_exemption(path) is not None


def test_the_content_only_exemption_matches_whole_components_only(repo):
    """⚠ `cache` must not quietly exempt a `cache-of-consumer-notes/` created beside it."""
    (repo / "cache-notes").mkdir(parents=True)
    (repo / "cache-notes" / "x.md").write_text("acme owes us\n", encoding="utf-8")

    assert failures(repo)
