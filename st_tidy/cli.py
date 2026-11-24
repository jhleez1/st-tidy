"""Command line: st-tidy [options] FILE_OR_FOLDER ..."""
from __future__ import annotations

import argparse
import difflib
import sys
from pathlib import Path

from . import __version__
from .formatter import Options, format_source
from .linter import lint_source

EXTENSIONS = {".st", ".var", ".typ", ".fun"}   # B&R Automation Studio file types


def find_files(paths: list[str]) -> list[Path]:
    files: list[Path] = []
    for p in map(Path, paths):
        if p.is_dir():
            files += sorted(f for f in p.rglob("*") if f.suffix.lower() in EXTENSIONS and f.is_file())
        elif p.is_file():
            files.append(p)
        else:
            raise FileNotFoundError(p)
    return files


def read(path: Path) -> tuple[str, str]:
    """Automation Studio projects can be UTF-8 or Windows-1252; keep whichever it was."""
    data = path.read_bytes()
    for enc in ("utf-8", "cp1252"):
        try:
            return data.decode(enc), enc
        except UnicodeDecodeError:
            pass
    return data.decode("latin-1"), "latin-1"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="st-tidy", description="Format and lint IEC 61131-3 Structured Text (.st .var .typ .fun).")
    ap.add_argument("paths", nargs="+", help="files or folders (folders are searched for .st/.var/.typ/.fun)")
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("-w", "--write", action="store_true", help="rewrite files in place")
    mode.add_argument("-c", "--check", action="store_true", help="only report files that would change (exit 1 if any)")
    mode.add_argument("-d", "--diff", action="store_true", help="show what would change")
    ap.add_argument("-l", "--lint", action="store_true", help="also report likely mistakes")
    ap.add_argument("--lint-only", action="store_true", help="only lint, do not format")
    ap.add_argument("--spaces", type=int, metavar="N", help="indent with N spaces instead of tabs")
    ap.add_argument("--keep-case", action="store_true", help="do not upper-case keywords")
    ap.add_argument("--max-line", type=int, default=120, metavar="N", help="line length for W103 (default 120)")
    ap.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    args = ap.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(newline="")   # we print the file's own line endings; don't add \r on Windows

    opts = Options(indent=" " * args.spaces if args.spaces else "\t", uppercase_keywords=not args.keep_case)
    try:
        files = find_files(args.paths)
    except FileNotFoundError as e:
        print(f"st-tidy: no such file or folder: {e}", file=sys.stderr)
        return 2

    changed = errors = 0
    for path in files:
        text, enc = read(path)
        if args.lint or args.lint_only:
            for p in lint_source(text, args.max_line):
                print(f"{path}:{p.line}: {p.code} {p.message}")
                errors += p.code.startswith("E")
        if args.lint_only:
            continue
        new = format_source(text, opts)
        if new == text:
            continue
        changed += 1
        if args.write:
            path.write_bytes(new.encode(enc))
            print(f"formatted {path}")
        elif args.check:
            print(f"would format {path}")
        elif args.diff:
            for d in difflib.unified_diff(text.splitlines(True), new.splitlines(True), str(path), str(path) + " (formatted)"):
                sys.stdout.write(d if d.endswith("\n") else d + "\n\\ No newline at end of file\n")
        else:
            sys.stdout.write(new if len(files) == 1 else f"--- {path}\n{new}")

    if not args.lint_only and (args.write or args.check):
        print(f"{changed} of {len(files)} file(s) {'reformatted' if args.write else 'would be reformatted'}", file=sys.stderr)
    if errors or (args.check and changed):
        return 1
    return 0
