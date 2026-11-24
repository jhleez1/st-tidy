"""Find common mistakes in Structured Text.

Codes
  E001  END_x without an opener
  E002  END_x closes the wrong block (e.g. END_IF for a CASE)
  E003  block never closed
  W101  "=" used where ":=" was probably meant
  W102  statement or declaration probably missing its ";"
  W103  line longer than the limit
  I201  CASE without ELSE
"""
from __future__ import annotations

import re

from .blocks import Problem, analyse
from .lexer import Line, lex, words

STATEMENT_START_KEYWORDS = {"IF", "ELSIF", "WHILE", "UNTIL", "CASE", "FOR", "RETURN", "EXIT", "CONTINUE", "REPEAT", "ELSE"}
# a line that ends like this continues on the next line
CONTINUES = re.compile(r"(\b(AND|OR|XOR|NOT|MOD|THEN|DO|OF|ELSE|REPEAT|AND_THEN|OR_ELSE)|[-+*/(,=<>&:\[])\s*$", re.I)
STARTS_AS_CONTINUATION = re.compile(r"^\s*(\b(AND|OR|XOR|MOD|THEN|DO|OF|AND_THEN|OR_ELSE)\b|[-+*/)=<>&\]])", re.I)
WRONG_ASSIGN = re.compile(r"^\s*[A-Za-z_][\w.]*(\[[^\]]*\])?(\.[\w]+)*\s*=(?!=)\s*[^;]*;\s*$")
DECLARATION = re.compile(r"^\s*[A-Za-z_]\w*(\s*,\s*[A-Za-z_]\w*)*\s*(AT\s+%\S+\s*)?:(?!=)\s*\S")


def _next_code_line(lines: list[Line], i: int) -> Line | None:
    for nxt in lines[i + 1:]:
        if nxt.has_code:
            return nxt
    return None


def lint_source(source: str, max_line: int = 120) -> list[Problem]:
    lines = lex(source)
    info = analyse(lines)
    problems = list(info.problems)

    for i, line in enumerate(lines):
        if len(line.text.expandtabs(4)) > max_line:
            problems.append(Problem(line.number, "W103", f"line is {len(line.text.expandtabs(4))} characters (limit {max_line})"))
        if not line.has_code:
            continue
        code = line.code.rstrip()
        ws = words(code)
        first = ws[0] if ws else ""
        declaring = info.in_declaration.get(line.number, False)

        if not declaring and first not in STATEMENT_START_KEYWORDS and WRONG_ASSIGN.match(code):
            problems.append(Problem(line.number, "W101", 'comparison "=" used as a statement; did you mean ":="?'))

        nxt = _next_code_line(lines, i)
        if code.endswith(";") or CONTINUES.search(code) or (nxt and STARTS_AS_CONTINUATION.match(nxt.code)):
            continue
        if declaring and DECLARATION.match(code) and ws[-1] != "STRUCT":   # "Name : STRUCT" opens a block
            problems.append(Problem(line.number, "W102", "declaration is missing ';'"))
        elif not declaring and ":=" in code and first not in STATEMENT_START_KEYWORDS:
            problems.append(Problem(line.number, "W102", "statement is missing ';'"))

    return sorted(problems, key=lambda p: (p.line, p.code))
