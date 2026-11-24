"""Split Structured Text source into lines of code, string and comment pieces.

Formatting must never change text inside comments or strings, so every line
is cut into segments first. Block comments ``(* ... *)`` can span lines, so
the lexer carries that state from one line to the next.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

CODE, STRING, COMMENT = "code", "string", "comment"


@dataclass
class Segment:
    kind: str
    text: str


@dataclass
class Line:
    number: int
    segments: list[Segment] = field(default_factory=list)
    # True when the line starts inside a block comment opened on an earlier line
    starts_in_comment: bool = False

    @property
    def code(self) -> str:
        """Only the code parts, with strings replaced by a placeholder."""
        return "".join(s.text if s.kind == CODE else ("''" if s.kind == STRING else " ") for s in self.segments)

    @property
    def text(self) -> str:
        return "".join(s.text for s in self.segments)

    @property
    def is_blank(self) -> bool:
        return not self.text.strip()

    @property
    def has_code(self) -> bool:
        return any(s.kind in (CODE, STRING) and s.text.strip() for s in self.segments)


def _add(segs: list[Segment], kind: str, text: str) -> None:
    if not text:
        return
    if segs and segs[-1].kind == kind:
        segs[-1].text += text
    else:
        segs.append(Segment(kind, text))


def lex(source: str) -> list[Line]:
    """Return one ``Line`` per physical line (line endings removed)."""
    lines: list[Line] = []
    in_comment = False
    for number, raw in enumerate(re.split(r"\r\n|\n|\r", source), start=1):
        line = Line(number, starts_in_comment=in_comment)
        segs = line.segments
        i, n = 0, len(raw)
        while i < n:
            if in_comment:
                end = raw.find("*)", i)
                if end < 0:
                    _add(segs, COMMENT, raw[i:])
                    i = n
                else:
                    _add(segs, COMMENT, raw[i:end + 2])
                    i = end + 2
                    in_comment = False
                continue
            ch = raw[i]
            if raw.startswith("(*", i):
                in_comment = True
                _add(segs, COMMENT, "(*")
                i += 2
            elif raw.startswith("//", i):
                _add(segs, COMMENT, raw[i:])
                i = n
            elif ch in "'\"":
                j = i + 1
                while j < n:
                    if raw[j] == "$":          # IEC escape: $' $" $$ $N ...
                        j += 2
                        continue
                    if raw[j] == ch:
                        break
                    j += 1
                _add(segs, STRING, raw[i:j + 1])
                i = j + 1
            else:
                j = i
                while j < n and raw[j] not in "'\"" and not raw.startswith("(*", j) and not raw.startswith("//", j):
                    j += 1
                _add(segs, CODE, raw[i:j])
                i = j
        lines.append(line)
    return lines


WORD = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


def words(code: str) -> list[str]:
    """Upper-cased identifiers and keywords in a piece of code, in order."""
    return [w.upper() for w in WORD.findall(code)]
