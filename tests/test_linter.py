import io
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from st_tidy import lint_source
from st_tidy.cli import main


def codes(src: str) -> list[tuple[int, str]]:
    return [(p.line, p.code) for p in lint_source(src)]


class Blocks(unittest.TestCase):
    def test_clean_code_has_no_problems(self):
        src = "PROGRAM _CYCLIC\nIF a THEN\n  b := 1;\nEND_IF;\nCASE s OF\n  0: x := 1;\nELSE\n  x := 0;\nEND_CASE;\nEND_PROGRAM\n"
        self.assertEqual(codes(src), [])

    def test_closer_without_opener(self):
        self.assertEqual(codes("x := 1;\nEND_IF;\n"), [(2, "E001")])

    def test_wrong_closer(self):
        src = "IF a THEN\nCASE s OF\n0: x := 1;\nELSE x := 2;\nEND_IF;\n"
        self.assertIn((5, "E002"), codes(src))

    def test_unclosed_block(self):
        self.assertEqual(codes("WHILE a DO\nx := 1;\n"), [(1, "E003")])

    def test_case_without_else_is_info(self):
        self.assertEqual(codes("CASE s OF\n0: x := 1;\nEND_CASE;\n"), [(1, "I201")])


class Statements(unittest.TestCase):
    def test_equals_instead_of_assign(self):
        self.assertEqual(codes("Count = Count + 1;\n"), [(1, "W101")])

    def test_comparisons_in_conditions_are_fine(self):
        self.assertEqual(codes("IF a = b THEN\nx := a = b;\nEND_IF;\n"), [])

    def test_missing_semicolon(self):
        self.assertEqual(codes("a := 1\nb := 2;\n"), [(1, "W102")])

    def test_multiline_expressions_are_not_missing_semicolons(self):
        src = "a := b AND\n  c;\nx := y\n  OR z;\nTmr(IN := go,\n    PT := T#1s);\n"
        self.assertEqual(codes(src), [])

    def test_declaration_missing_semicolon(self):
        self.assertEqual(codes("VAR\nx : INT := 0\ny : BOOL;\nEND_VAR\n"), [(2, "W102")])

    def test_struct_header_is_not_a_missing_semicolon(self):
        self.assertEqual(codes("TYPE\nCell : STRUCT\nrow : USINT;\nEND_STRUCT;\nEND_TYPE\n"), [])

    def test_text_in_comments_and_strings_is_ignored(self):
        self.assertEqual(codes("(* END_IF\n x = 1; *)\nmsg := 'END_CASE x = 1';  // END_FOR\n"), [])

    def test_long_lines(self):
        self.assertEqual(codes("x := " + "1 + " * 40 + "1;\n"), [(1, "W103")])


class CommandLine(unittest.TestCase):
    def run_cli(self, *args):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = main(list(args))
        return code, out.getvalue(), err.getvalue()

    def test_check_write_and_lint(self):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "Cyclic.st"
            f.write_text("if a then\nb:=1;\nend_if;\n", encoding="utf-8")
            self.assertEqual(self.run_cli("--check", d)[0], 1)
            self.assertEqual(self.run_cli("--write", d)[0], 0)
            self.assertEqual(f.read_text(encoding="utf-8"), "IF a THEN\n\tb := 1;\nEND_IF;\n")
            self.assertEqual(self.run_cli("--check", d)[0], 0)
            f.write_text("IF a THEN\n", encoding="utf-8")
            code, out, _ = self.run_cli("--lint-only", str(f))
            self.assertEqual(code, 1)
            self.assertIn("E003", out)

    def test_keeps_windows_1252_files(self):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "Init.st"
            f.write_bytes("(* Temperatur in °C *)\nt:=1;\n".encode("cp1252"))
            self.run_cli("--write", str(f))
            self.assertEqual(f.read_bytes(), "(* Temperatur in °C *)\nt := 1;\n".encode("cp1252"))

    def test_missing_path(self):
        self.assertEqual(self.run_cli("nope.st")[0], 2)


if __name__ == "__main__":
    unittest.main()
