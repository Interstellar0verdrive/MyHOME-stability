#!/usr/bin/env python3
"""Print the CHANGELOG section of a version with paragraphs unwrapped.

GitHub release notes render a single newline as a line break, so the hard-wrapped
CHANGELOG would show ragged lines. Usage:

    python3 scripts/release_notes.py 0.4.0 > /tmp/notes.md
    gh release create v0.4.0 --title "v0.4.0 - ..." --notes-file /tmp/notes.md
"""

import re
import sys

REPO = "https://github.com/Interstellar0verdrive/MyHOME-stability/blob/master/"

# A list item, a heading or a table row starts a new block; anything else is a
# continuation line of the block above it.
BLOCK_START_RE = re.compile(r"^\s*([-*]|\d+\.)\s")

# Relative links the release page would otherwise resolve against its own URL.
RELATIVE_LINK_RE = re.compile(r"\]\(((?:docs/|CHANGELOG|README|blueprints/)[^)\s]+)\)")


def section(version):
    """The body of the ``## [version]`` section of CHANGELOG.md, or None."""
    with open("CHANGELOG.md", encoding="utf-8") as handle:
        text = handle.read()
    match = re.search(
        rf"## \[{re.escape(version)}\][^\n]*\n(.*?)(?=\n## \[|\Z)", text, re.S
    )
    return match.group(1).strip() if match else None


def unwrap(text):
    """Join the hard-wrapped lines of every paragraph, leaving code blocks alone."""
    out = []
    buf = []
    in_code = False

    def flush():
        if buf:
            first, *rest = buf
            out.append(" ".join([first.rstrip(), *(line.strip() for line in rest)]))
            buf.clear()

    for line in text.split("\n"):
        if line.strip().startswith("```"):
            flush()
            in_code = not in_code
            out.append(line)
            continue
        if in_code:
            out.append(line)
            continue
        if not line.strip():
            flush()
            out.append("")
            continue
        if BLOCK_START_RE.match(line) or line.startswith("#") or line.lstrip().startswith("|"):
            flush()
        buf.append(line)
    flush()
    return "\n".join(out)


def absolutize(text):
    """Release pages resolve relative links against the release URL, so point
    docs/... and CHANGELOG.md links at the repository explicitly."""
    return RELATIVE_LINK_RE.sub(lambda match: f"]({REPO}{match.group(1)})", text)


def main():
    version = sys.argv[1]
    body = section(version)
    if body is None:
        sys.exit(f"section {version} not found")
    print(absolutize(unwrap(body)))


if __name__ == "__main__":
    main()
