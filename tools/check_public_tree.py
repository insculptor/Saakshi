"""Refuse to publish a reserved name.

This repository is public. Some of the projects that consume its output are not, and a
name that reaches a public commit cannot be recalled — deleting it forward leaves it in
the history, and rewriting the history after a push leaves it in every clone and in
GitHub's own dangling objects.

So this runs **before** a push, over four things:

* every **tracked file at HEAD**,
* every **commit reachable from any ref**, because a name removed in a later commit is
  still published by the earlier one,
* ⭐ every **path and every text file in the working tree**, tracked or not, ignored or
  not — see ``PRIVATE_BY_DESIGN`` for why git's opinion of a path buys it nothing, and
* every **commit message**, which is published with its commit — see
  ``PUBLISHED_BEFORE_MESSAGES_WERE_SCANNED``.

⭐ **The mechanism is public and the list is not.** The names come from
``config/reserved-names.txt``, which is git-ignored. ⛔ With no list, this exits non-zero
rather than passing: a check that silently has nothing to check is worse than no check,
because it reports success. Patterns whose shape is itself private — a consumer's row,
gate or iteration ids — come from ``config/reserved-patterns.txt``, also git-ignored and
optional; without it, the report says those ids are not checked.

    python tools/check_public_tree.py

⚠ Three of the four scopes read **committed** content, so run it after committing and
before pushing. The working tree is what is on disk right now, and a hit there is the cheap
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
PATTERNS_FILE = ROOT / "config" / "reserved-patterns.txt"

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
    "config/reserved-patterns.txt": "it IS the private pattern list this check reads",
    "config/predecessor-surface.toml": "names another tree's module paths, and is git-ignored for that reason",
    "docs/local": "cross-repository notes, git-ignored for that reason",
}

#: ⛔ **EXEMPT FROM THE CONTENT PASS ONLY. EVERY PATH BELOW IS STILL SCANNED AS A PATH.**
#:
#: The textual reference acquires other people's published texts into a cache, and the words
#: inside them were chosen by their authors. ⭐ Measured, on the first two texts acquired: one
#: of them contains a reserved name twice — as the name of a sage, in a work of the tradition
#: a consumer of this repository was itself named after. It is there by construction rather
#: than by accident, and the next classical text will contain it too.
#:
#: ⚠ **A check that always fires is a check nobody reads**, and the exemption that ends that
#: is the one that has to be argued rather than assumed. Three things make it safe:
#:
#: * nothing here is authored by this repository, and nothing here is ever committed — the
#:   two committed scopes are untouched, and it is a commit that cannot be recalled;
#: * ⭐ what this repository *writes* from these texts is scanned exactly as before. The
#:   fixtures quote from them, and a quotation carrying a reserved name is refused like any
#:   other content;
#: * ⛔ and the exemption is **content only**. The failure the working-tree scan exists for
#:   was a *directory bearing a reserved name*, planted by a parallel session. That failure
#:   is unchanged here: every path under the cache is still listed and still matched, so a
#:   consumer-named directory appearing inside it is refused exactly as it is anywhere else.
FOREIGN_CONTENT: dict[str, str] = {
    "cache": (
        "acquired third-party source material - not authored here, never committed, and "
        "digest-pinned in the fixtures. ⛔ Its PATHS are still scanned"
    ),
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
#: ⛔ **And no backslash escape of any kind, `\b` included.** `\b` is a GNU extension: the
#: git on a Linux runner honours it, and the git that ships with macOS (measured: Apple Git
#: 2.54.0) does not, so on a Mac both identifier patterns matched nothing and the self-test
#: refused every run. The word boundary is therefore spelled in POSIX classes, which both
#: regex libraries read the same way: start of line, or one character that is not a letter,
#: a digit or an underscore. `NON_PORTABLE_ESCAPE` below is the rule; `--self-test` refuses
#: any pattern it finds, before it asks git anything.
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

#: A word boundary before a word character, in POSIX ERE that BSD and GNU regex both read.
_WORD_START = "(^|[^[:alnum:]_])"

#: ⛔ No pattern this check hands to `git grep -E` may contain this: a backslash followed by
#: a letter, a digit, or one of the GNU anchor characters (`\b`, `\d`, `\s`, `\w`, `\<` and
#: their kin are each honoured by one regex library and not another). An escaped
#: punctuation character such as `\.` or `\-` is portable and is allowed.
NON_PORTABLE_ESCAPE = re.compile(r"\\[A-Za-z0-9<>`']")


def _identifier_patterns() -> list[tuple[str, str, str, str]]:
    """`(pattern, description, must_match, must_not_match)` for each entry."""
    entries = [
        (
            rf"{_WORD_START}{prefix}-[0-9]",
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

#: ⛔ **A COMMIT MESSAGE IS PUBLISHED WITH ITS COMMIT, AND UNTIL 2026-11-23 NOTHING HERE READ
#: ONE.** Every message is now scanned for every pattern this check holds, and for the
#: patterns below that apply to messages only. This repository's commits name one author, so
#: a co-author trailer is refused.
_TRAILER = "co-authored-by"
MESSAGE_PATTERNS = [
    (
        # ⚠ git's trailer parser accepts space before the colon and before the key.
        f"^[[:space:]]*{_TRAILER}[[:space:]]*:",
        "a co-author trailer",
        f"  {_TRAILER.title()} : A. Person <a.person@example.org>",
        # ⛔ must NOT match: the key in prose, not at the start of a line
        f"see the {_TRAILER}: line",
    )
]

#: ⚠ **THE BOUNDARY.** Messages, and the private patterns in history, were first scanned when
#: this commit was the tip. Everything reachable from it was already public, and only a
#: rewrite of public history could change it, so a hit there is reported as a count on every
#: run and never fails. ⛔ Every other commit is held to every pattern, in its message and in
#: its tree: its descendants, and any commit on another ref that it cannot reach — which fails
#: closed, and is reported as "after the boundary" although it may be older.
PUBLISHED_BEFORE_MESSAGES_WERE_SCANNED = "05b59644f429ff08568e8d3213b53380bf8e0532"


#: ⛔ **Decode what git prints, never let the locale decide.** `text=True` alone decodes with
#: the console's encoding, and this scan reads *every* text file on disk — the first byte
#: that a Windows cp1252 console cannot decode raises inside a reader thread and the check
#: dies without a verdict. That is the same shape as the marker-glyph abort this repository
#: already fixed on the output side: a check that cannot report is worse than a check that
#: fails, and it fails hardest where there is most to read.
_DECODE = {"encoding": "utf-8", "errors": "replace"}


def _git(*args: str, root: Path = ROOT, private: bool = False) -> str:
    """⚠ `private`: the arguments carry a pattern from the private list, so a failure names
    neither them nor git's message, which repeats them."""
    result = subprocess.run(
        ["git", *args], cwd=root, capture_output=True, check=False, **_DECODE
    )
    if result.returncode != 0:
        if private:
            raise SystemExit(f"⛔ git {args[0]} failed (exit {result.returncode}) on a pattern; "
                             "neither it nor git's message is printed. Check the pattern lists.")
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


def private_patterns(path: Path = PATTERNS_FILE) -> list[tuple[str, str]] | None:
    """`(pattern, description)` per line of the private pattern list, or None with no list.

    One POSIX extended regular expression per line, read by `git grep -E` and `git log -E`;
    `#` starts a comment, so a pattern cannot contain one. ⚠ The description names the line,
    never the pattern: the shape of a consumer's ids is what the file keeps private.
    """
    if not path.is_file():
        return None
    found = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        pattern = line.split("#", 1)[0].strip()
        if not pattern:
            continue
        escape = NON_PORTABLE_ESCAPE.search(pattern)
        if escape:
            raise SystemExit(
                f"⛔ {path.name} line {number} uses {escape.group()!r}, which one regex library "
                "honours and another does not; on the one that does not, it matches nothing"
            )
        found.append((pattern, f"private pattern, line {number} of {path.name}"))
    return found


def scan_after_boundary(
    patterns: list[tuple[str, str]], boundary: str, *, contents: bool, root: Path = ROOT
) -> tuple[list[str], list[str], int]:
    """`(failures, published, commits scanned)` for commit messages, or for contents.

    ⛔ A hit in a commit after the boundary fails. A hit only in commits reachable from it is
    already public: it is counted under `published`, said on every run, and never fails.
    """
    if subprocess.run(["git", "cat-file", "-e", f"{boundary}^{{commit}}"], cwd=root,
                      capture_output=True, check=False).returncode != 0:
        raise SystemExit(
            f"⛔ the boundary commit {boundary[:12]} is not in this clone, so a published hit "
            "cannot be told from a new one; fetch it, or run this where it is"
        )
    every = _git("rev-list", "--all", root=root).split()
    after = set(_git("rev-list", "--all", f"^{boundary}", root=root).split())
    before = [r for r in every if r not in after]
    failures: list[str] = []
    published: list[str] = []
    for pattern, description in patterns:
        if contents:
            new = _git_grep(["-inE", "-e", pattern, *sorted(after), "--", "."], root) if after else []
            old = _git_grep(["-ilE", "-e", pattern, *before, "--", "."], root) if before else []
            old_count = len({hit.split(":", 1)[1] for hit in old})
            scope, unit = "in a commit after the boundary", "path(s)"
        else:
            lines = _git("log", "--all", "-E", "-i", f"--grep={pattern}", "--format=%H %s",
                         root=root, private=True).splitlines()
            new = [line for line in lines if line.split(" ", 1)[0] in after]
            old_count = sum(1 for line in lines if line.strip()) - len(new)
            scope, unit = "in a commit MESSAGE", "commit(s)"
        if new:
            failures.extend(_report(description, scope, new))
        if old_count:
            # ⚠ Said on every GREEN run, so it never names a reserved name: a report that only
            #    a failing run prints is read by the person fixing it; this one is read by all.
            label = "a reserved name" if description.startswith("the reserved name") else description
            published.append(f"{label}: {old_count} {unit} published at or before {boundary[:7]}")
    return failures, published, len(every)


def self_test() -> int:
    """Prove every pattern is live, through the same engine the check uses.

    ⭐ Needs no reserved-name list, so CI can run it: the names are private, the matcher
    is not, and it is the matcher that was broken.
    """
    probe = ROOT / ".matcher-probe.tmp"
    failures: list[str] = []
    for pattern, description, _positive, _negative in EXTRA_PATTERNS + MESSAGE_PATTERNS:
        escape = NON_PORTABLE_ESCAPE.search(pattern)
        if escape:
            failures.append(
                f"⛔ {description}: pattern {pattern!r} uses {escape.group()!r}, which one "
                "regex library honours and another does not. On the one that does not, the "
                "pattern matches nothing and this check goes green over an empty set."
            )
    try:
        for pattern, description, positive, negative in EXTRA_PATTERNS + MESSAGE_PATTERNS:
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
    print(f"✅ all {len(EXTRA_PATTERNS) + len(MESSAGE_PATTERNS)} public patterns match what they must, and "
          "nothing they must not")
    return 0


def _git_grep(args: list[str], root: Path) -> list[str]:
    """The matching lines. ⛔ Exit 1 is "no match"; anything above it is git refusing — a
    malformed pattern, an unknown option — and it stops the run, because an empty result from
    a refusal reads exactly like a clean tree. The message prints no pattern."""
    result = subprocess.run(
        ["git", "grep", *args], cwd=root, capture_output=True, check=False, **_DECODE
    )
    if result.returncode > 1:
        raise SystemExit(f"⛔ git grep failed (exit {result.returncode}) on a pattern; neither it "
                         "nor git's message is printed. Check the pattern lists.")
    return [line for line in result.stdout.splitlines() if line.strip()]


def _grep_file(pattern: str, path: Path, root: Path = ROOT) -> list[str]:
    return _git_grep(["--no-index", "-inE", "-e", pattern, "--", path.name], root)


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


def _under(relative_path: str, listed: dict[str, str]) -> str | None:
    """⚠ Matched by whole path component, never by string prefix: `docs/local` must not
    quietly exempt a `docs/local-notes/` somebody creates next to it."""
    for path, reason in listed.items():
        if relative_path == path or relative_path.startswith(path + "/"):
            return reason
    return None


def exemption(relative_path: str) -> str | None:
    """The reason `relative_path` is exempt from **both** passes, or `None`."""
    return _under(relative_path, PRIVATE_BY_DESIGN)


def content_exemption(relative_path: str) -> str | None:
    """The reason `relative_path`'s **contents** are not scanned, or `None`.

    ⛔ A path exempt here is still listed and still matched *as a path*. The two passes catch
    different things and only one of them is being narrowed.
    """
    return exemption(relative_path) or _under(relative_path, FOREIGN_CONTENT)


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
        for line in _git_grep(["--no-index", "-I", "-inE", "-e", pattern, "--", "."], root):
            relative_path = line.split(":", 1)[0]
            if content_exemption(relative_path) is None:
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
    privates = private_patterns()
    message_only = [(p, d) for p, d, _positive, _negative in MESSAGE_PATTERNS]
    boundary = PUBLISHED_BEFORE_MESSAGES_WERE_SCANNED

    revisions = _git("rev-list", "--all").split()
    if not revisions:
        raise SystemExit("⛔ no commits — commit before checking")

    failures: list[str] = []
    for pattern, description in patterns:
        # HEAD's tree, then every reachable commit. The second subsumes the first, but
        # reporting them apart makes "still at the tip" and "only in history"
        # distinguishable, and they need different fixes.
        for scope, args in (
            ("tracked at HEAD", ["grep", "-inE", "-e", pattern, "HEAD", "--"]),
            ("in history", ["grep", "-inE", "-e", pattern, *revisions, "--"]),
        ):
            hits = _git_grep([*args[1:], "."], ROOT)
            if hits:
                failures.extend(_report(description, scope, hits))
                break  # history covers HEAD; one report per pattern is enough

    # The private patterns: HEAD in full; history only after the boundary, because before it
    # the hits are published and counted (see `scan_after_boundary`).
    published: list[str] = []
    for pattern, description in privates or []:
        hits = _git_grep(["-inE", "-e", pattern, "HEAD", "--", "."], ROOT)
        if hits:
            failures.extend(_report(description, "tracked at HEAD", hits))
    if privates:
        found, counted, _ = scan_after_boundary(privates, boundary, contents=True)
        failures.extend(found)
        published.extend(counted)

    found, counted, messages = scan_after_boundary(
        patterns + (privates or []) + message_only, boundary, contents=False)
    failures.extend(found)
    published.extend(counted)

    # ⛔ NOT part of that break-chain. An untracked path is in neither committed scope, so a
    #    scope that "subsumes" it does not exist and skipping this on a committed hit would
    #    hide the one failure this pass was added for.
    working_tree_failures, examined = scan_working_tree(patterns + (privates or []))
    failures.extend(working_tree_failures)

    print(
        f"scanned {len(revisions)} commit(s) and {examined} working-tree path(s) "
        f"for {len(patterns)} pattern(s) and {len(privates or [])} private pattern(s)"
    )
    print(
        "  working tree: every path, and the contents of every file git reads as text "
        "(binary files are skipped)"
    )
    print(f"  commit messages: {messages}, for every pattern and {len(message_only)} more "
          "that apply to messages only")
    if not privates:
        why = "absent" if privates is None else "holds no pattern"
        print(f"  ⚠ private patterns: NONE ({PATTERNS_FILE.relative_to(ROOT)} {why}) - row, "
              "gate and iteration ids are NOT checked")
    else:
        print(f"  private patterns: {len(privates)} in force (not printed)")
    for line in published:
        print(f"  published, not failed: {line}")
    for path, reason in PRIVATE_BY_DESIGN.items():
        present = "" if (ROOT / path).exists() else "  [absent]"
        print(f"  exempt: {path} — {reason}{present}")
    for path, reason in FOREIGN_CONTENT.items():
        present = "" if (ROOT / path).exists() else "  [absent]"
        print(f"  exempt (contents only, PATHS still scanned): {path} — {reason}{present}")
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
    print("✅ no reserved name, internal document identifier, private pattern or co-author trailer "
          "reaches a commit or a message after the boundary, or sits in the working tree")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
