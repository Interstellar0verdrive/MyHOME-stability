#!/usr/bin/env python3
"""Print the CHANGELOG section of a version with paragraphs unwrapped.

GitHub release notes render a single newline as a line break, so the hard-wrapped
CHANGELOG would show ragged lines. Usage:

    python3 scripts/release_notes.py 0.4.0 > /tmp/notes.md
    gh release create v0.4.0 --title "v0.4.0 - ..." --notes-file /tmp/notes.md
"""
import re, sys
def section(version):
    s=open('CHANGELOG.md').read()
    m=re.search(r"## \[%s\][^\n]*\n(.*?)(?=\n## \[|\Z)" % re.escape(version), s, re.S)
    return m.group(1).strip() if m else None
def unwrap(text):
    out=[]; buf=[]; in_code=False
    def flush():
        if buf:
            first=buf[0]; rest=[l.strip() for l in buf[1:]]
            out.append(" ".join([first.rstrip()]+rest)); buf.clear()
    for line in text.split("\n"):
        if line.strip().startswith("```"):
            flush(); in_code=not in_code; out.append(line); continue
        if in_code: out.append(line); continue
        if not line.strip(): flush(); out.append(""); continue
        # nuova voce di lista, titolo o tabella: inizia un blocco
        if re.match(r"^\s*([-*]|\d+\.)\s", line) or line.startswith("#") or line.lstrip().startswith("|"):
            flush(); buf.append(line)
        else:
            if buf: buf.append(line)
            else: buf.append(line)
    flush()
    return "\n".join(out)
v=sys.argv[1]; sec=section(v)
if sec is None: sys.exit("sezione %s non trovata" % v)
print(unwrap(sec))
