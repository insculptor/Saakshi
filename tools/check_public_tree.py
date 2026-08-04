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

# The console this runs on is not guaranteed to be UTF-8, and a check must never fail
# because it could not print its own verdict.
if hasattr(sys.stdout, "reconfigure"):  # pragma: no cover - platform dependent
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
NAMES_FILE = ROOT / "config" / "reserved-names.txt"

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


def _grep_no_index(pattern: str, path: Path) -> bool:
    result = subprocess.run(
        ["git", "grep", "--no-index", "-inE", pattern, "--", path.name],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    return bool(result.stdout.strip())


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
