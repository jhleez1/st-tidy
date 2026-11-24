"""Re-indent Structured Text and tidy keyword case and spacing.

Rules (only ever applied to code, never inside comments or strings):

* indent by block structure: IF/CASE/FOR/WHILE/REPEAT, VAR blocks, PROGRAM,
  FUNCTION_BLOCK, STRUCT, TYPE, ACTION ... CASE labels sit one level in and
  their statements two levels in
* keywords and standard types in UPPER CASE (ST is case-insensitive, so this
  never changes what the program does)
* at least one space either side of ``:=`` and ``=>`` (extra spaces used to
  line up columns are kept), one space after commas
* no trailing whitespace, exactly one newline at the end of the file
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from .blocks import analyse
from .lexer import CODE, STRING, Line, lex

KEYWORDS = {
    # control
    "IF", "THEN", "ELSIF", "ELSE", "END_IF", "CASE", "OF", "END_CASE", "FOR", "TO", "BY", "DO", "END_FOR",
    "WHILE", "END_WHILE", "REPEAT", "UNTIL", "END_REPEAT", "EXIT", "RETURN", "CONTINUE",
    # operators and literals
    "AND", "OR", "XOR", "NOT", "MOD", "TRUE", "FALSE", "AND_THEN", "OR_ELSE",
    # program units and declarations
    "PROGRAM", "END_PROGRAM", "FUNCTION", "END_FUNCTION", "FUNCTION_BLOCK", "END_FUNCTION_BLOCK",
    "ACTION", "END_ACTION", "METHOD", "END_METHOD", "INTERFACE", "END_INTERFACE", "PROPERTY", "END_PROPERTY",
    "VAR", "VAR_INPUT", "VAR_OUTPUT", "VAR_IN_OUT", "VAR_TEMP", "VAR_GLOBAL", "VAR_EXTERNAL", "VAR_STAT",
    "VAR_INST", "END_VAR", "CONSTANT", "RETAIN", "PERSISTENT", "AT",
    "TYPE", "END_TYPE", "STRUCT", "END_STRUCT", "ARRAY", "POINTER", "REFERENCE", "REF_TO", "EXTENDS", "IMPLEMENTS",
    # elementary types
    "BOOL", "BYTE", "WORD", "DWORD", "LWORD", "SINT", "INT", "DINT", "LINT", "USINT", "UINT", "UDINT", "ULINT",
    "REAL", "LREAL", "TIME", "DATE", "TIME_OF_DAY", "TOD", "DATE_AND_TIME", "DT", "STRING", "WSTRING", "CHAR",
}
WORD = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
# T#5s, t#1h2m and 16#ff are literals: leave their letters alone
LITERAL = re.compile(r"\b(?:[A-Za-z_]+|\d+)#[A-Za-z0-9_.#]*")


@dataclass
class Options:
    indent: str = "\t"           # B&R Automation Studio uses tabs
    uppercase_keywords: bool = True
    spacing: bool = True


def _tidy_code(code: str, opts: Options) -> str:
    # protect typed literals like T#350ms or 16#FF
    saved: list[str] = []

    def stash(m: re.Match) -> str:
        saved.append(m.group(0))
        return f"\x00{len(saved) - 1}\x00"

    code = LITERAL.sub(stash, code)
    if opts.uppercase_keywords:
        code = WORD.sub(lambda m: m.group(0).upper() if m.group(0).upper() in KEYWORDS else m.group(0), code)
    if opts.spacing:
        # only add missing spaces, so hand-aligned columns of ":=" survive
        for op in (":=", "=>"):
            code = re.sub(rf"(?<=\S){op}", f" {op}", code)
            code = re.sub(rf"{op}(?=\S)", f"{op} ", code)
        code = re.sub(r"[ \t]+,", ",", code)
        code = re.sub(r",(?=\S)", ", ", code)
    return re.sub(r"\x00(\d+)\x00", lambda m: saved[int(m.group(1))], code)


def _format_line(line: Line, level: int, opts: Options) -> str:
    if level < 0:                                     # inside a multi-line comment
        return line.text.rstrip()
    parts = []
    segs = line.segments
    for i, seg in enumerate(segs):
        if seg.kind != CODE:
            parts.append(seg.text)
            continue
        text = _tidy_code(seg.text, opts)
        # "msg:='hi'": the string is a separate segment, so add the space here
        if opts.spacing and i + 1 < len(segs) and segs[i + 1].kind == STRING and re.search(r"(:=|=>|,)$", text):
            text += " "
        parts.append(text)
    body = "".join(parts).strip()
    if not body:
        return ""
    return opts.indent * level + body


def format_source(source: str, opts: Options | None = None) -> str:
    opts = opts or Options()
    newline = "\r\n" if "\r\n" in source else "\n"
    lines = lex(source)
    info = analyse(lines)
    out = [_format_line(line, info.levels[line.number], opts) for line in lines]
    # no more than one blank line in a row, none at the end
    tidy: list[str] = []
    for text in out:
        if text == "" and (not tidy or tidy[-1] == ""):
            continue
        tidy.append(text)
    while tidy and tidy[-1] == "":
        tidy.pop()
    return newline.join(tidy) + newline
