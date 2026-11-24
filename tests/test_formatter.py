import unittest

from st_tidy import Options, format_source

SP = Options(indent="  ")


def fmt(src: str, opts: Options = SP) -> str:
    return format_source(src, opts)


class Indentation(unittest.TestCase):
    def test_nested_if(self):
        src = "IF a THEN\nIF b THEN\nx := 1;\nELSE\nx := 2;\nEND_IF;\nEND_IF;\n"
        self.assertEqual(fmt(src), "IF a THEN\n  IF b THEN\n    x := 1;\n  ELSE\n    x := 2;\n  END_IF;\nEND_IF;\n")

    def test_case_labels_and_bodies(self):
        src = "CASE s OF\n0:\nx := 1;\n1, 2: x := 2;\n10..20:\ny := 3;\nELSE\nx := 0;\nEND_CASE;\n"
        want = "CASE s OF\n  0:\n    x := 1;\n  1, 2: x := 2;\n  10..20:\n    y := 3;\n  ELSE\n    x := 0;\nEND_CASE;\n"
        self.assertEqual(fmt(src), want)

    def test_enum_style_labels(self):
        src = "CASE State OF\nSTATE_IDLE:\nIF go THEN\nState := STATE_RUN;\nEND_IF;\nEND_CASE;\n"
        want = "CASE State OF\n  STATE_IDLE:\n    IF go THEN\n      State := STATE_RUN;\n    END_IF;\nEND_CASE;\n"
        self.assertEqual(fmt(src), want)

    def test_loops(self):
        src = "FOR i := 0 TO 9 DO\nWHILE x DO\nx := FALSE;\nEND_WHILE;\nEND_FOR;\nREPEAT\ni := i + 1;\nUNTIL i > 5\nEND_REPEAT;\n"
        want = "FOR i := 0 TO 9 DO\n  WHILE x DO\n    x := FALSE;\n  END_WHILE;\nEND_FOR;\nREPEAT\n  i := i + 1;\nUNTIL i > 5\nEND_REPEAT;\n"
        self.assertEqual(fmt(src), want)

    def test_program_and_var_blocks(self):
        src = "FUNCTION_BLOCK Fb\nVAR_INPUT\nGo : BOOL;\nEND_VAR\nVAR CONSTANT\nN : INT := 3;\nEND_VAR\nOut := Go;\nEND_FUNCTION_BLOCK\n"
        want = "FUNCTION_BLOCK Fb\n  VAR_INPUT\n    Go : BOOL;\n  END_VAR\n  VAR CONSTANT\n    N : INT := 3;\n  END_VAR\n  Out := Go;\nEND_FUNCTION_BLOCK\n"
        self.assertEqual(fmt(src), want)

    def test_br_type_file(self):
        src = "TYPE\nCell : STRUCT\nrow : USINT;\nEND_STRUCT;\nEND_TYPE\n"
        self.assertEqual(fmt(src), "TYPE\n  Cell : STRUCT\n    row : USINT;\n  END_STRUCT;\nEND_TYPE\n")

    def test_one_line_if_does_not_change_depth(self):
        src = "PROGRAM _CYCLIC\nIF a THEN b := 1; END_IF;\nc := 2;\nEND_PROGRAM\n"
        self.assertEqual(fmt(src), "PROGRAM _CYCLIC\n  IF a THEN b := 1; END_IF;\n  c := 2;\nEND_PROGRAM\n")

    def test_tabs_by_default(self):
        self.assertEqual(format_source("IF a THEN\nb := 1;\nEND_IF;\n"), "IF a THEN\n\tb := 1;\nEND_IF;\n")


class Tidying(unittest.TestCase):
    def test_keywords_upper_case_identifiers_untouched(self):
        self.assertEqual(fmt("if motorOn and not fault then\nend_if;\n"), "IF motorOn AND NOT fault THEN\nEND_IF;\n")

    def test_spacing(self):
        self.assertEqual(fmt("Tmr(IN:=go,PT:=T#5s);\n"), "Tmr(IN := go, PT := T#5s);\n")
        self.assertEqual(fmt("Fb(Out=>x);\n"), "Fb(Out => x);\n")

    def test_aligned_columns_are_kept(self):
        src = "a     := 1;\nlong  := 2;\n"
        self.assertEqual(fmt(src), src)

    def test_typed_literals_are_left_alone(self):
        self.assertEqual(fmt("t := t#1h2m;\nmask := 16#ff;\n"), "t := t#1h2m;\nmask := 16#ff;\n")

    def test_comments_and_strings_are_never_changed(self):
        src = "msg := 'if a:=b then';  // if x:=y\n(* case of\n   end_case *)\n"
        self.assertEqual(fmt(src), src)

    def test_multiline_comment_keeps_its_own_layout(self):
        src = "IF a THEN\n(* line one\n      line two *)\nb := 1;\nEND_IF;\n"
        self.assertEqual(fmt(src), "IF a THEN\n  (* line one\n      line two *)\n  b := 1;\nEND_IF;\n")

    def test_blank_lines_and_whitespace(self):
        self.assertEqual(fmt("\n\na := 1;   \n\n\n\nb := 2;\n\n\n"), "a := 1;\n\nb := 2;\n")

    def test_windows_line_endings_are_kept(self):
        self.assertEqual(fmt("IF a THEN\r\nb:=1;\r\nEND_IF;\r\n"), "IF a THEN\r\n  b := 1;\r\nEND_IF;\r\n")

    def test_idempotent(self):
        src = "program _CYCLIC\ncase s of\n0: x:=1;\nelse\nif a then b:=2; end_if;\nend_case;\nEND_PROGRAM"
        once = fmt(src)
        self.assertEqual(fmt(once), once)


if __name__ == "__main__":
    unittest.main()
