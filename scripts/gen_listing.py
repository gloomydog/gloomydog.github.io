#!/usr/bin/env python3
"""Generate ls-style index.html pages for books/ and every directory below it,
and refresh the books/ section of the top-level index.html.

Run from the repository root:  python3 scripts/gen_listing.py
"""
import datetime
import html
import os
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parent.parent
SECTIONS = ["blog", "tips", "projects", "books"]  # top-level dirs that get auto-generated listings
USER = "gloomydog"


def last_modified(path: Path) -> str:
    """Date of the last commit touching path; falls back to mtime."""
    try:
        out = subprocess.run(
            ["git", "log", "-1", "--format=%cs", "--", str(path)],
            cwd=ROOT, capture_output=True, text=True, check=True,
        ).stdout.strip()
        if out:
            return out
    except Exception:
        pass
    return datetime.date.fromtimestamp(path.stat().st_mtime).isoformat()


def human_size(n: int) -> str:
    size = float(n)
    for unit in ("B", "K", "M", "G"):
        if size < 1024 or unit == "G":
            return f"{int(size)}{unit}" if unit == "B" else f"{size:.1f}{unit}"
        size /= 1024
    return f"{n}B"


def entries(directory: Path):
    """Visible children (no dotfiles, no index.html): dirs first, then files."""
    items = [
        p for p in directory.iterdir()
        if not p.name.startswith(".") and p.name != "index.html"
    ]
    dirs = sorted((p for p in items if p.is_dir()), key=lambda p: p.name.lower())
    files = sorted((p for p in items if p.is_file()), key=lambda p: p.name.lower())
    return dirs, files


DESC_DEFAULT = "-"
DESC_SECTIONS = ["blog", "tips", "projects"]  # sections whose top-level entries carry a hand-written Description


def read_descriptions(section: str) -> dict:
    """Descriptions typed by hand in the top page's projects table (name -> text).
    They are kept across regenerations; new files get DESC_DEFAULT."""
    top = ROOT / "index.html"
    if not top.exists():
        return {}
    text = top.read_text(encoding="utf-8")
    start, end = f"<!-- {section.upper()}:START -->", f"<!-- {section.upper()}:END -->"
    if start not in text or end not in text:
        return {}
    block = text.split(start, 1)[1].split(end, 1)[0]
    out = {}
    for m in re.finditer(
        r'<td><a[^>]*href="' + section + r'/([^"]+?)/?">.*?</a></td>.*?<td class="meta">(.*?)</td>',
        block,
    ):
        out[html.unescape(m.group(1))] = m.group(2)
    return out


def rows_html(directory: Path, with_parent: bool, with_size: bool = True, descs=None):
    """descs: dict (name -> raw html text) adds a Description column; None disables it."""
    dirs, files = entries(directory)
    rows = []

    def extra(size_text, name):
        if descs is not None:
            return f'<td class="meta">{descs.get(name, DESC_DEFAULT)}</td>'
        return f'<td class="meta hide-sm">{size_text}</td>' if with_size else ""

    if with_parent:
        rows.append(
            '      <tr><td><a class="dir" href="../">../</a></td>'
            '<td class="meta hide-sm">-</td>'
            + ('<td class="meta">Parent Directory</td>' if descs is not None
               else ('<td class="meta hide-sm">-</td>' if with_size else ""))
            + "</tr>"
        )
    for d in dirs:
        rows.append(
            f'      <tr><td><a class="dir" href="{quote(d.name)}/">{html.escape(d.name)}/</a></td>'
            f'<td class="meta hide-sm">{last_modified(d)}</td>'
            + extra("-", d.name)
            + "</tr>"
        )
    for f in files:
        rows.append(
            f'      <tr><td><a href="{quote(f.name)}">{html.escape(f.name)}</a></td>'
            f'<td class="meta hide-sm">{last_modified(f)}</td>'
            + extra(human_size(f.stat().st_size), f.name)
            + "</tr>"
        )
    return "\n".join(rows), len(dirs) + len(files)


def table_html(rows: str, desc: bool = False) -> str:
    last = '<th>Description</th>' if desc else '<th class="hide-sm">Size</th>'
    return (
        "  <table>\n"
        "    <thead>\n"
        f'      <tr><th>Name</th><th class="hide-sm">Last modified</th>{last}</tr>\n'
        "    </thead>\n"
        "    <tbody>\n"
        f"{rows}\n"
        "    </tbody>\n"
        "  </table>"
    )


def build_page(directory: Path, descs=None) -> str:
    rel = directory.relative_to(ROOT)  # e.g. books/Chemistry
    depth = len(rel.parts)
    css = "../" * depth + "style.css"
    shown = "~/" + rel.as_posix()
    rows, count = rows_html(directory, with_parent=True, descs=descs)
    body = table_html(rows, desc=descs is not None)
    total = f'  <p class="meta">total {count}</p>\n' if count == 0 else ""
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Index of /{html.escape(rel.as_posix())}/ | {USER}</title>
<link rel="stylesheet" href="{css}">
</head>
<body>
<main>
  <div class="prompt"><span class="user">{USER}</span>:<span class="path">{html.escape(shown)}</span>$ ls -l</div>
{body}
{total}  <div class="prompt"><span class="user">{USER}</span>:<span class="path">{html.escape(shown)}</span>$ <span class="cursor"></span></div>
  <footer>&copy; 2026 {USER}</footer>
</main>
</body>
</html>
"""


def update_top_page(section: str, descs=None) -> None:
    top = ROOT / "index.html"
    text = top.read_text(encoding="utf-8")
    START = f"<!-- {section.upper()}:START -->"
    END = f"<!-- {section.upper()}:END -->"
    if START not in text or END not in text:
        print(f"index.html has no {section.upper()} markers; skipping", file=sys.stderr)
        return
    rows, count = rows_html(ROOT / section, with_parent=False, with_size=False, descs=descs)
    if count == 0 and descs is None:
        block = '  <p class="meta">total 0</p>'
    else:
        block = (
            "  <table>\n"
            "    <thead>\n"
            '      <tr><th>Name</th><th class="hide-sm">Last modified</th>'
            + ("<th>Description</th>" if descs is not None else "")
            + "</tr>\n"
            "    </thead>\n"
            "    <tbody>\n"
            f"{rows}\n"
            "    </tbody>\n"
            "  </table>"
        )
    # top-level links must be prefixed with the section dir
    block = block.replace('href="', f'href="{section}/')
    head, rest = text.split(START, 1)
    _, tail = rest.split(END, 1)
    new = f"{head}{START}\n{block}\n  {END}{tail}"
    if new != text:
        top.write_text(new, encoding="utf-8")


def main() -> None:
    total = 0
    for section in SECTIONS:
        # read before anything is rewritten
        descs = read_descriptions(section) if section in DESC_SECTIONS else None
        base = ROOT / section
        base.mkdir(exist_ok=True)
        dirs = [base] + sorted(p for p in base.rglob("*") if p.is_dir() and not p.name.startswith("."))
        for d in dirs:
            page = build_page(d, descs if d == base else None)
            target = d / "index.html"
            if not target.exists() or target.read_text(encoding="utf-8") != page:
                target.write_text(page, encoding="utf-8")
        total += len(dirs)
        update_top_page(section, descs)
    print(f"generated {total} listing page(s)")


if __name__ == "__main__":
    main()
