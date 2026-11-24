"""Work out the block structure (IF ... END_IF and friends) line by line.

``analyse()`` walks the lexed lines once and records, for every line, the
indent level it should have. Problems such as an ``END_IF`` that closes a
``CASE`` are collected on the way, so the linter can report them.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from .lexer import Line, words

OPENERS = {
    "IF": "END_IF", "CASE": "END_CASE", "FOR": "END_FOR", "WHILE": "END_WHILE",
    "REPEAT": "END_REPEAT", "PROGRAM": "END_PROGRAM", "FUNCTION": "END_FUNCTION",
    "FUNCTION_BLOCK": "END_FUNCTION_BLOCK", "STRUCT": "END_STRUCT", "TYPE": "END_TYPE",
    "ACTION": "END_ACTION", "METHOD": "END_METHOD", "INTERFACE": "END_INTERFACE",
    "PROPERTY": "END_PROPERTY",
    "VAR": "END_VAR", "VAR_INPUT": "END_VAR", "VAR_OUTPUT": "END_VAR", "VAR_IN_OUT": "END_VAR",
    "VAR_TEMP": "END_VAR", "VAR_GLOBAL": "END_VAR", "VAR_EXTERNAL": "END_VAR", "VAR_STAT": "END_VAR",
    "VAR_INST": "END_VAR",
}
CLOSERS = set(OPENERS.values())
MIDDLE = {"ELSE", "ELSIF", "UNTIL"}          # sit one level out, like the opener
DECLARATION_BLOCKS = {k for k, v in OPENERS.items() if v == "END_VAR"} | {"STRUCT", "TYPE"}

# "1:", "STATE_IDLE:", "1, 2, 5:", "10..20:" at the start of a line inside CASE
CASE_LABEL = re.compile(r"^\s*[A-Za-z0-9_#.+\-]+(\s*(,|\.\.)\s*[A-Za-z0-9_#.+\-]+)*\s*:(?!=)")


@dataclass
class Block:
    keyword: str
    line: int
    weight: int = 1          # CASE bodies indent twice: labels at +1, statements at +2
    has_else: bool = False


@dataclass
class Problem:
    line: int
    code: str
    message: str


@dataclass
class Analysis:
    levels: dict[int, int] = field(default_factory=dict)        # line number -> indent level
    in_declaration: dict[int, bool] = field(default_factory=dict)
    problems: list[Problem] = field(default_factory=list)


def _depth(stack: list[Block]) -> int:
    return sum(b.weight for b in stack)


def analyse(lines: list[Line]) -> Analysis:
    out = Analysis()
    stack: list[Block] = []

    def close(word: str, line_no: int) -> None:
        if not stack:
            out.problems.append(Problem(line_no, "E001", f"{word} without a matching opener"))
            return
        top = stack[-1]
        if OPENERS[top.keyword] == word:
            stack.pop()
            if top.keyword == "CASE" and not top.has_else:
                out.problems.append(Problem(top.line, "I201", "CASE has no ELSE branch; unexpected values are silently ignored"))
            return
        # Mismatch: if something further down matches, assume the blocks above were left open.
        for k in range(len(stack) - 2, -1, -1):
            if OPENERS[stack[k].keyword] == word:
                for b in reversed(stack[k + 1:]):
                    out.problems.append(Problem(line_no, "E002", f"{word} closes {stack[k].keyword} from line {stack[k].line}, but {b.keyword} from line {b.line} is still open"))
                del stack[k:]
                return
        out.problems.append(Problem(line_no, "E002", f"{word} does not match {top.keyword} from line {top.line}"))

    for line in lines:
        if line.starts_in_comment and not line.has_code:
            out.levels[line.number] = -1                  # inside a block comment: leave alone
            continue
        code = line.code
        ws = words(code)
        # the keyword that starts the line, if the line starts with a word
        first = ws[0] if ws and re.match(r"[A-Za-z_]", code.lstrip()) else None
        rest = ws

        if first in CLOSERS:
            close(first, line.number)
            level = _depth(stack)
            rest = ws[1:]
        elif first in MIDDLE:
            level = _depth(stack) - 1
            if first == "ELSE" and stack and stack[-1].keyword == "CASE":
                stack[-1].has_else = True
        elif stack and stack[-1].keyword == "CASE" and line.has_code and CASE_LABEL.match(code):
            level = _depth(stack) - 1
        else:
            level = _depth(stack)

        out.levels[line.number] = max(level, 0)
        out.in_declaration[line.number] = bool(stack) and stack[-1].keyword in DECLARATION_BLOCKS

        for w in rest:
            if w in OPENERS:
                # "VAR CONSTANT" / "VAR RETAIN" are one opener; STRUCT inside TYPE nests normally.
                stack.append(Block(w, line.number, 2 if w == "CASE" else 1))
            elif w in CLOSERS:
                close(w, line.number)

    for b in stack:
        out.problems.append(Problem(b.line, "E003", f"{b.keyword} is never closed (expected {OPENERS[b.keyword]})"))
    return out
