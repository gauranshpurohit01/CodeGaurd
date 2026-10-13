"""Unit tests for hand-written C/C++ Lexer."""

import pytest
from app.engine.lexer import tokenize, normalized_token_string, LexerError


def test_token_types():
    code = "int x = 42; // comment\nfloat f = 3.14;"
    tokens = tokenize(code)
    kinds = [t.kind for t in tokens if t.kind != "EOF"]
    assert "KEYWORD" in kinds
    assert "IDENTIFIER" in kinds
    assert "OPERATOR" in kinds
    assert "NUMBER" in kinds
    assert "PUNCTUATION" in kinds


def test_normalization_for_plagiarism():
    code = 'int my_var = 123; char *msg = "hello";'
    tokens = tokenize(code)
    norm = normalized_token_string(tokens)
    assert norm == ["int", "ID", "=", "NUM", ";", "char", "*", "ID", "=", "STR", ";"]


def test_unterminated_block_comment_raises():
    code = "int a = 1; /* unclosed comment"
    with pytest.raises(LexerError) as exc_info:
        tokenize(code)
    assert "Unterminated block comment" in str(exc_info.value)


def test_preprocessor_line_continuation():
    code = "#define FOO \\\n  42\nint x = FOO;"
    tokens = tokenize(code)
    pp_tokens = [t for t in tokens if t.kind == "PREPROCESSOR"]
    assert len(pp_tokens) == 1
    assert "FOO" in pp_tokens[0].raw
    assert "42" in pp_tokens[0].raw


def test_escapes_in_string_and_char():
    code = 'char c = \'\\n\'; char *s = "Line 1\\n\\"Quote\\"\\tEnd";'
    tokens = tokenize(code)
    kinds = [t.kind for t in tokens]
    assert "CHAR" in kinds
    assert "STRING" in kinds


def test_number_formats_and_suffixes():
    code = "int h = 0x1A3f; int b = 0b1011; float f = 1.25e-3f; unsigned long u = 500ULL;"
    tokens = tokenize(code)
    num_tokens = [t for t in tokens if t.kind == "NUMBER"]
    assert len(num_tokens) == 4
    assert all(t.value == "NUM" for t in num_tokens)


def test_multi_char_operators_greedy():
    code = "a <<= 2; b >>= 1; p->x = 5; std::cout << ++i--;"
    tokens = tokenize(code)
    ops = [t.raw for t in tokens if t.kind == "OPERATOR"]
    assert "<<=" in ops
    assert ">>=" in ops
    assert "->" in ops
    assert "::" in ops
    assert "<<" in ops
    assert "++" in ops
    assert "--" in ops


def test_resilience_on_unknown_chars():
    code = "int a = 5; @#$` int b = 10;"
    tokens = tokenize(code)
    norm = normalized_token_string(tokens)
    assert "int" in norm
    assert "ID" in norm
    assert "NUM" in norm
