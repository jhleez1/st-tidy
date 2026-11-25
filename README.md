# st-tidy

![tests](https://github.com/jhleez1/st-tidy/actions/workflows/test.yml/badge.svg)

A formatter and linter for **IEC 61131-3 Structured Text**, the language of B&R Automation Studio, CODESYS, TwinCAT and Siemens SCL.

Automation Studio has no auto-formatter, so code from different people (or the same person on different days) ends up with mixed indentation and keyword case. st-tidy fixes that, and catches a few classic mistakes before you download to the PLC.

```
$ st-tidy examples/messy.st --diff --lint
examples\messy.st:10: I201 CASE has no ELSE branch; unexpected values are silently ignored
examples\messy.st:18: W101 comparison "=" used as a statement; did you mean ":="?
examples\messy.st:19: W102 statement is missing ';'
--- examples\messy.st
+++ examples\messy.st (formatted)
-program _CYCLIC
-if diStart and not diStop then
-state:=1;
+PROGRAM _CYCLIC
+	IF diStart AND NOT diStop THEN
+		state := 1;
 ...
```

## Install

Needs Python 3.10 or newer. There are no dependencies.

```
pip install git+https://github.com/jhleez1/st-tidy
```

Or, from a clone, run it without installing: `python -m st_tidy ...`

## Use

```
st-tidy Cyclic.st                 # print the formatted file
st-tidy --diff Logical/           # show what would change in a whole Automation Studio project
st-tidy --write Logical/          # format in place
st-tidy --check Logical/          # exit code 1 if anything would change (for CI)
st-tidy --lint-only Logical/      # only look for mistakes
```

Folders are searched for `.st`, `.var`, `.typ` and `.fun` files.

| Option | |
| --- | --- |
| `--spaces N` | indent with N spaces instead of tabs (tabs are the Automation Studio default) |
| `--keep-case` | don't upper-case keywords |
| `--lint` | report mistakes as well as formatting |
| `--max-line N` | line length for W103 (default 120) |

## What the formatter does

- **Indents by structure:** `IF`, `CASE`, `FOR`, `WHILE`, `REPEAT`, `VAR` blocks, `PROGRAM`, `FUNCTION_BLOCK`, `STRUCT`, `TYPE` and `ACTION`. `CASE` labels go one level in and their statements two.
- **Upper-cases keywords and standard types.** ST is case-insensitive, so this never changes behaviour.
- **Adds missing spaces** around `:=` and `=>` and after commas. Extra spaces you used to line up columns are kept.
- **Tidies whitespace:** removes trailing spaces, collapses runs of blank lines and ends the file with one newline.
- **Leaves alone:** comments, strings and typed literals such as `T#350ms` or `16#FF`.
- **Keeps file details:** Windows line endings and Windows-1252 encoded files (common in older projects) stay as they were.

Formatting is idempotent: running it twice gives the same result as running it once.

## What the linter finds

| Code | Problem |
| --- | --- |
| E001 | `END_IF` (or any `END_…`) with nothing to close |
| E002 | `END_…` that closes the wrong block, e.g. `END_IF` for a `CASE` |
| E003 | Block that is never closed |
| W101 | `x = 1;`: a comparison used as a statement, almost always a typo for `:=` |
| W102 | Statement or declaration missing its `;` |
| W103 | Line longer than the limit |
| I201 | `CASE` without `ELSE`: an unexpected state value does nothing, silently |

It reports problems as `file:line: CODE message`. Any `E` problem makes the exit code 1.

## How it works

1. **Lexer** (`lexer.py`): splits each line into code, string and comment pieces, and tracks `(* … *)` comments across lines. Everything after this only touches code.
2. **Block analysis** (`blocks.py`): one pass with a stack of open blocks. It gives each line its indent level and records mismatched or unclosed blocks.
3. **Formatter** (`formatter.py`) and **linter** (`linter.py`): both built on those two steps.

I tested it on my own [PLC Sudoku Solver](https://github.com/jhleez1/Structured-Text-ST-language-PLC-Sudoku-Solver): no false errors, and formatting it twice changes nothing.

## Tests

```
python -m unittest discover -s tests
```

---

Built by [Jihan Lee](https://github.com/jhleez1)
