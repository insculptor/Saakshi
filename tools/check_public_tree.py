"""Refuse to publish a reserved name.

This repository is public. Some of the projects that consume its output are not, and a
name that reaches a public commit cannot be recalled — deleting it forward leaves it in
the history, and rewriting the history after a push leaves it in every clone and in
GitHub's own dangling objects.

So this runs **before** a push, over two things:

* every **tracked file at HEAD**, and
* every **commit reachable from any ref**, because a name removed in a later commit is
  still published by the earlier one.

⭐ **The mechanism is public and the list is not.** The names come from
``config/reserved-names.txt``, which is git-ignored. ⛔ With no list, this exits non-zero
rather than passing: a check that silently has nothing to check is worse than no check,
because it reports success.

    python tools/check_public_tree.py

⚠ It scans **committed** content, so run it after committing and before pushing. It has
nothing to say about your working tree.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NAMES_FILE = ROOT / "config" / "reserved-names.txt"

#: ⚠ Patterns beyond the names themselves. A public repository can leak an unreleased
#: project's *shape* without ever naming it — internal document identifiers are the usual
#: way. These are the ones this estate uses.
EXTRA_PATTERNS = [
    (r"\badr-\d", "an internal decision-record identifier"),
    (r"\brfc-\d", "an internal proposal identifier"),
    (r"§", "a section reference into an internal document"),
]


def _git(*args: str) -> str:
    result = subprocess.run(
        ["git", *args], cwd=ROOT, capture_output=True, text=True, check=False
    )
    if result.returncode != 0:
        raise SystemExit(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout


def reserved_names() -> list[str]:
    if not NAMES_FILE.is_file():
        raise SystemExit(
            f"⛔ {NAMES_FILE.relative_to(ROOT)} does not exist, so this check has nothing "
            "to check and would pass vacuously.\n"
            "   Copy config/reserved-names.txt.example to config/reserved-names.txt and "
            "add every consumer's name."
        )
    names = []
    for line in NAMES_FILE.read_text(encoding="utf-8").splitlines():
        line = line.split("#", 1)[0].strip().lower()
        if line:
            names.append(line)
    if not names:
        raise SystemExit(f"⛔ {NAMES_FILE.relative_to(ROOT)} is empty")
    return names


def main() -> int:
    names = reserved_names()
    # ⛔ This repository's OWN name is excluded here, and only here: `generator.repo` must
    #    carry it, the README is about it, and the package is called it. The fixture
    #    contract still forbids it in a fixture key or filename, which is the place the
    #    rule is actually about.
    own = "saakshi"
    scan_for = [n for n in names if n != own]

    patterns = [(re.escape(n), f"the reserved name {n!r}") for n in scan_for]
    patterns += EXTRA_PATTERNS
    if not patterns:
        raise SystemExit("⛔ nothing to scan for beyond this repository's own name")

    revisions = _git("rev-list", "--all").split()
    if not revisions:
        raise SystemExit("⛔ no commits — commit before checking")

    failures: list[str] = []
    for pattern, description in patterns:
        # HEAD's tree, then every reachable commit. The second subsumes the first, but
        # reporting them apart makes "still in the working tree" and "only in history"
        # distinguishable, and they need different fixes.
        for scope, args in (
            ("tracked at HEAD", ["grep", "-inE", pattern, "HEAD", "--"]),
            ("in history", ["grep", "-inE", pattern, *revisions, "--"]),
        ):
            result = subprocess.run(
                ["git", *args, "."], cwd=ROOT, capture_output=True, text=True, check=False
            )
            hits = [line for line in result.stdout.splitlines() if line.strip()]
            if hits:
                failures.append(f"⛔ {description} — {scope}:")
                failures.extend(f"     {line}" for line in hits[:12])
                if len(hits) > 12:
                    failures.append(f"     ... and {len(hits) - 12} more")
                break  # history covers HEAD; one report per pattern is enough

    print(f"scanned {len(revisions)} commit(s) for {len(patterns)} pattern(s)")
    if failures:
        print()
        print("\n".join(failures))
        print()
        print(
            "⚠ A name in HISTORY is not fixed by a new commit. Nothing here has been "
            "pushed if this is the first run —\n"
            "  rewrite instead, then drop refs/original and expire the reflog."
        )
        return 1
    print("✅ no reserved name and no internal document identifier reaches a commit")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
