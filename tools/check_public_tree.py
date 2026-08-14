"""Refuse to publish a reserved name.

This repository is public. Some of the projects that consume its output are not, and a
name that reaches a public commit cannot be recalled — deleting it forward leaves it in
the history, and rewriting the history after a push leaves it in every clone and in
GitHub's own dangling objects.

So this runs **before** a push, over three things:

* every **tracked file at HEAD**,
* every **commit reachable from any ref**, because a name removed in a later commit is
  still published by the earlier one, and
* ⭐ every **path and every text file in the working tree**, tracked or not, ignored or
  not — see ``PRIVATE_BY_DESIGN`` for why git's opinion of a path buys it nothing.

⭐ **The mechanism is public and the list is not.** The names come from
``config/reserved-names.txt``, which is git-ignored. ⛔ With no list, this exits non-zero
rather than passing: a check that silently has nothing to check is worse than no check,
because it reports success.

    python tools/check_public_tree.py

⚠ Two of the three scopes read **committed** content, so run it after committing and
before pushing. The third reads what is on disk right now, and a hit there is the cheap
kind: nothing has been published yet, so deleting the path is the whole fix.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

# The console this runs on is not guaranteed to be UTF-8, and a check must never fail
# because it could not print its own verdict.
if hasattr(sys.stdout, "reconfigure"):  # pragma: no cover - platform dependent
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
NAMES_FILE = ROOT / "config" / "reserved-names.txt"

#: git's own storage. Not part of the working tree, and every commit inside it is already
#: read by the history scope, through git rather than by walking loose objects.
GIT_DIR = ".git"

#: Where the working-tree path listing is staged so the **same matcher** can read it. ⭐ One
#: engine everywhere: a second regex dialect for paths would be a second thing to keep alive,
#: and the whole point of the self-test below is that a dead pattern reports success.
PATH_LISTING = ".working-tree-paths.tmp"

#: ⛔ **THE EXEMPTION LIST, AND IT IS DELIBERATELY SHORT.**
#:
#: The working-tree scan does **not** consult `.gitignore`, and that is the design rather
#: than an oversight. The failure it exists for was an untracked directory bearing a
#: reserved name, written into this clone by a parallel session working on the consumer;
#: it was never tracked and never ignored, so the tracked-files scope and the history scope
#: were both blind to it, and a single `git add -A` would have published it. ⛔ The fix that
#: was refused was to git-ignore that one path — the same failure returns under a different
#: name in a different path, and a scan that skipped ignored paths would then be silenced by
#: exactly the fix that was refused. **So being ignored buys a path nothing here.**
#:
#: What is exempt is the short list of paths that exist *to hold* the private names. Each is
#: named in full and each is reported on every run: an exemption nobody reads is an
#: exemption nobody can withdraw.
PRIVATE_BY_DESIGN: dict[str, str] = {
    "config/reserved-names.txt": "it IS the list this check reads, not a leak of it",
    "config/predecessor-surface.toml": "names another tree's module paths, and is git-ignored for that reason",
    "docs/local": "cross-repository notes, git-ignored for that reason",
}

#: ⚠ Patterns beyond the names themselves. A public repository can leak an unreleased
#: project's *shape* without ever naming it — internal document identifiers are the usual
#: way. These are the ones this estate uses.
#:
#: ⛔ **POSIX ERE, not Perl.** `git grep -E` has no `\d` and no `\s`; a pattern using them
#: matches nothing at all and the check goes green over an empty set. Both identifier
#: patterns here were originally written with `\d` and were **silently dead** until the
#: self-test below was added. Every entry therefore carries a sample that must match and a
#: sample that must not, and `--self-test` proves both.
#:
#: ⭐ **The samples are BUILT, never written out.** A literal positive sample would be a
#: string this file must not contain — the scan would flag the code that enforces it. ⛔ The
#: answer is not to exempt this file: an exemption would also silence a real leak that
#: happened to land here, and this is a public repository where such a leak is permanent.
#: Instead each entry stores its *prefix* once, the regex and the samples are derived from
#: it, and the assembled identifier exists only at runtime. Check for yourself: the pattern
#: `adr-[0-9]` does not match the text `adr-[0-9]`, because `[` is not a digit.
_SECTION = "§"

_IDENTIFIER_PREFIXES = [
    ("adr", "an internal decision-record identifier"),
    ("rfc", "an internal proposal identifier"),
]


def _identifier_patterns() -> list[tuple[str, str, str, str]]:
    """`(pattern, description, must_match, must_not_match)` for each entry."""
    entries = [
        (
            rf"\b{prefix}-[0-9]",
            description,
            f"see {prefix.upper()}-0015 for the rule",
            # ⛔ must NOT match: no word boundary before the prefix
            f"the qu{prefix}-1 coefficient",
        )
        for prefix, description in _IDENTIFIER_PREFIXES
    ]
    entries.append(
        (
            # ⚠ A section symbol followed by a digit, never a bare one. The bare form
            #   matched this file's own pattern list, which is how the exemption
            #   temptation starts.
            rf"{_SECTION}[[:space:]]*[0-9]",
            "a section reference into an internal document",
            f"as {_SECTION}7.7.1 requires",
            f"the {_SECTION} symbol on its own",
        )
    )
    return entries


EXTRA_PATTERNS = _identifier_patterns()


#: ⛔ **Decode what git prints, never let the locale decide.** `text=True` alone decodes with
#: the console's encoding, and this scan reads *every* text file on disk — the first byte
#: that a Windows cp1252 console cannot decode raises inside a reader thread and the check
#: dies without a verdict. That is the same shape as the marker-glyph abort this repository
#: already fixed on the output side: a check that cannot report is worse than a check that
#: fails, and it fails hardest where there is most to read.
_DECODE = {"encoding": "utf-8", "errors": "replace"}


def _git(*args: str) -> str:
    result = subprocess.run(
        ["git", *args], cwd=ROOT, capture_output=True, check=False, **_DECODE
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


def self_test() -> int:
    """Prove every pattern is live, through the same engine the check uses.

    ⭐ Needs no reserved-name list, so CI can run it: the names are private, the matcher
    is not, and it is the matcher that was broken.
    """
    probe = ROOT / ".matcher-probe.tmp"
    failures: list[str] = []
    try:
        for pattern, description, positive, negative in EXTRA_PATTERNS:
            probe.write_text(positive + "\n", encoding="utf-8")
            if not _grep_no_index(pattern, probe):
                failures.append(
                    f"⛔ {description}: pattern {pattern!r} did NOT match {positive!r}. "
                    "A pattern that matches nothing makes this check green over an empty "
                    "set."
                )
            probe.write_text(negative + "\n", encoding="utf-8")
            if _grep_no_index(pattern, probe):
                failures.append(
                    f"⛔ {description}: pattern {pattern!r} matched {negative!r}, which it "
                    "must not. An over-broad matcher gets exempted, and an exemption is "
                    "how a real leak gets waved through."
                )
    finally:
        probe.unlink(missing_ok=True)

    if failures:
        print("\n".join(failures))
        return 1
    print(f"✅ all {len(EXTRA_PATTERNS)} identifier patterns match what they must, and "
          "nothing they must not")
    return 0


def _git_grep(args: list[str], root: Path) -> list[str]:
    result = subprocess.run(
        ["git", "grep", *args], cwd=root, capture_output=True, check=False, **_DECODE
    )
    return [line for line in result.stdout.splitlines() if line.strip()]


def _grep_file(pattern: str, path: Path, root: Path = ROOT) -> list[str]:
    return _git_grep(["--no-index", "-inE", pattern, "--", path.name], root)


def _grep_no_index(pattern: str, path: Path) -> bool:
    return bool(_grep_file(pattern, path))


def _relative_paths(root: Path) -> list[str]:
    """Every path under `root`, relative and slash-separated. Git is not consulted.

    ⚠ **Directories are listed too.** The failure this was written for was a *directory*
    name, and a directory that holds no file of its own appears in no listing of files.
    """
    found: list[str] = []
    for parent, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d != GIT_DIR)
        here = Path(parent)
        for name in dirnames + sorted(filenames):
            found.append((here / name).relative_to(root).as_posix())
    return found


def exemption(relative_path: str) -> str | None:
    """The reason `relative_path` is private by design, or `None` if it is not.

    ⚠ Matched by whole path component, never by string prefix: `docs/local` must not
    quietly exempt a `docs/local-notes/` somebody creates next to it.
    """
    for path, reason in PRIVATE_BY_DESIGN.items():
        if relative_path == path or relative_path.startswith(path + "/"):
            return reason
    return None


def _report(description: str, scope: str, hits: list[str]) -> list[str]:
    lines = [f"⛔ {description} — {scope}:"]
    lines.extend(f"     {hit[:160]}" for hit in hits[:12])
    if len(hits) > 12:
        lines.append(f"     ... and {len(hits) - 12} more")
    return lines


def scan_working_tree(
    patterns: list[tuple[str, str]], root: Path = ROOT
) -> tuple[list[str], int]:
    """`(failures, paths examined)` for what is on disk right now.

    Two passes, because they catch different things and the original failure was the second
    kind: the **contents** of every text file, and the **paths** themselves.
    """
    failures: list[str] = []

    for pattern, description in patterns:
        hits = []
        for line in _git_grep(["--no-index", "-I", "-inE", pattern, "--", "."], root):
            relative_path = line.split(":", 1)[0]
            if exemption(relative_path) is None:
                hits.append(line)
        if hits:
            failures.extend(_report(description, "in the working tree", hits))

    paths = [p for p in _relative_paths(root) if exemption(p) is None]
    listing = root / PATH_LISTING
    try:
        listing.write_text("\n".join(paths) + "\n", encoding="utf-8")
        for pattern, description in patterns:
            # `file:lineno:text` — the text is the path, and the first two fields are this
            # staging file, which is about to stop existing.
            hits = [
                line.split(":", 2)[2] for line in _grep_file(pattern, listing, root=root)
            ]
            if hits:
                failures.extend(_report(description, "a working-tree PATH", hits))
    finally:
        listing.unlink(missing_ok=True)

    return failures, len(paths)


def main() -> int:
    if "--self-test" in sys.argv:
        return self_test()

    if self_test() != 0:
        print("⛔ refusing to report on a matcher that does not work")
        return 1

    names = reserved_names()
    # ⛔ This repository's OWN name is excluded here, and only here: `generator.repo` must
    #    carry it, the README is about it, and the package is called it. The fixture
    #    contract still forbids it in a fixture key or filename, which is the place the
    #    rule is actually about.
    own = "saakshi"
    scan_for = [n for n in names if n != own]

    patterns = [(re.escape(n), f"the reserved name {n!r}") for n in scan_for]
    patterns += [(p, d) for p, d, _positive, _negative in EXTRA_PATTERNS]
    if not patterns:
        raise SystemExit("⛔ nothing to scan for beyond this repository's own name")

    revisions = _git("rev-list", "--all").split()
    if not revisions:
        raise SystemExit("⛔ no commits — commit before checking")

    failures: list[str] = []
    for pattern, description in patterns:
        # HEAD's tree, then every reachable commit. The second subsumes the first, but
        # reporting them apart makes "still at the tip" and "only in history"
        # distinguishable, and they need different fixes.
        for scope, args in (
            ("tracked at HEAD", ["grep", "-inE", pattern, "HEAD", "--"]),
            ("in history", ["grep", "-inE", pattern, *revisions, "--"]),
        ):
            hits = _git_grep([*args[1:], "."], ROOT)
            if hits:
                failures.extend(_report(description, scope, hits))
                break  # history covers HEAD; one report per pattern is enough

    # ⛔ NOT part of that break-chain. An untracked path is in neither committed scope, so a
    #    scope that "subsumes" it does not exist and skipping this on a committed hit would
    #    hide the one failure this pass was added for.
    working_tree_failures, examined = scan_working_tree(patterns)
    failures.extend(working_tree_failures)

    print(
        f"scanned {len(revisions)} commit(s) and {examined} working-tree path(s) "
        f"for {len(patterns)} pattern(s)"
    )
    print(
        "  working tree: every path, and the contents of every file git reads as text "
        "(binary files are skipped)"
    )
    for path, reason in PRIVATE_BY_DESIGN.items():
        present = "" if (ROOT / path).exists() else "  [absent]"
        print(f"  exempt: {path} — {reason}{present}")
    if failures:
        print()
        print("\n".join(failures))
        print()
        print(
            "⚠ A name in HISTORY is not fixed by a new commit. Nothing here has been "
            "pushed if this is the first run —\n"
            "  rewrite instead, then drop refs/original and expire the reflog.\n"
            "⭐ A name in the WORKING TREE is the cheap kind: nothing is published yet, so "
            "delete the path.\n"
            "  ⛔ Do not git-ignore it. The next one arrives under a different name in a "
            "different path,\n"
            "  and an ignored path is scanned here exactly like any other."
        )
        return 1
    print("✅ no reserved name and no internal document identifier reaches a commit, or sits in the working tree")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
