"""Indentation-aware character scanner (lexer) for typed Python subset.

Maintains an indentation stack to emit INDENT, DEDENT, and NEWLINE tokens.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional, Set


class PyLexerError(Exception):
    def __init__(self, message: str, line: int, col: int) -> None:
        super().__init__(f"{message} at line {line}, col {col}")
        self.message = message
        self.line = line
        self.col = col


@dataclass
class PyToken:
    kind: str      # KEYWORD, IDENTIFIER, NUMBER, STRING, OPERATOR, PUNCTUATION, INDENT, DEDENT, NEWLINE, EOF
    value: str
    raw: str
    line: int
    col: int

    def __repr__(self) -> str:
        return f"PyToken({self.kind}, {self.value!r}, L{self.line}:C{self.col})"


PY_KEYWORDS: Set[str] = {
    "def", "return", "if", "elif", "else", "while", "for", "in", "range",
    "break", "continue", "pass", "and", "or", "not", "True", "False", "None",
    "import", "from", "math",
}

MULTI_OPS: List[str] = [
    "//=", "**=", "==", "!=", "<=", ">=", "+=", "-=", "*=", "/=", "%=",
    "//", "**", "->",
    "+", "-", "*", "/", "%", "=", "<", ">",
]

PUNCTUATIONS: Set[str] = {":", ",", "(", ")", "[", "]", "."}


class PyLexer:
    def __init__(self, source: str) -> None:
        self.source = source
        self.pos = 0
        self.length = len(source)
        self.line = 1
        self.col = 1
        self.indent_stack: List[int] = [0]
        self.at_line_start = True

    def _peek(self, offset: int = 0) -> str:
        idx = self.pos + offset
        if idx < self.length:
            return self.source[idx]
        return ""

    def _advance(self) -> str:
        if self.pos >= self.length:
            return ""
        ch = self.source[self.pos]
        self.pos += 1
        if ch == "\n":
            self.line += 1
            self.col = 1
        else:
            self.col += 1
        return ch

    def tokenize(self) -> List[PyToken]:
        tokens: List[PyToken] = []

        while self.pos < self.length:
            # Handle indentation at the beginning of a line
            if self.at_line_start:
                indent = 0
                start_col = self.col
                while self.pos < self.length and self._peek() in (" ", "\t"):
                    ch = self._advance()
                    indent += 4 if ch == "\t" else 1

                # If blank line or comment line, skip without changing indentation
                if self._peek() == "\n":
                    self._advance()
                    continue
                elif self._peek() == "\r" and self._peek(1) == "\n":
                    self._advance()
                    self._advance()
                    continue
                elif self._peek() == "#":
                    # Comment till end of line
                    while self.pos < self.length and self._peek() not in ("\n", "\r"):
                        self._advance()
                    continue

                if self.pos >= self.length:
                    break

                # Compare indentation with stack top
                last_indent = self.indent_stack[-1]
                if indent > last_indent:
                    self.indent_stack.append(indent)
                    tokens.append(PyToken("INDENT", "", "", self.line, start_col))
                elif indent < last_indent:
                    while self.indent_stack and indent < self.indent_stack[-1]:
                        self.indent_stack.pop()
                        tokens.append(PyToken("DEDENT", "", "", self.line, start_col))
                    if not self.indent_stack or indent != self.indent_stack[-1]:
                        raise PyLexerError("Unindent does not match any outer indentation level", self.line, start_col)

                self.at_line_start = False

            ch = self._peek()

            # Skip spaces on current line
            if ch in (" ", "\t", "\r"):
                self._advance()
                continue

            # Newline
            if ch == "\n":
                self._advance()
                self.at_line_start = True
                # Only emit NEWLINE if last token was not already a NEWLINE or INDENT
                if tokens and tokens[-1].kind not in ("NEWLINE", "INDENT"):
                    tokens.append(PyToken("NEWLINE", "\n", "\n", self.line - 1, self.col))
                continue

            # Comments: # ...
            if ch == "#":
                while self.pos < self.length and self._peek() != "\n":
                    self._advance()
                continue

            start_line = self.line
            start_col = self.col

            # Strings: '...' or "..." (single line)
            if ch in ('"', "'"):
                quote = self._advance()
                chars = []
                while self.pos < self.length:
                    cur = self._peek()
                    if cur == "\\":
                        chars.append(self._advance())
                        if self.pos < self.length:
                            chars.append(self._advance())
                        continue
                    if cur == quote:
                        self._advance()
                        break
                    chars.append(self._advance())
                str_val = "".join(chars)
                tokens.append(PyToken("STRING", str_val, f"{quote}{str_val}{quote}", start_line, start_col))
                continue

            # Numbers
            if ch.isdigit() or (ch == "." and self._peek(1).isdigit()):
                num_val = self._read_number()
                tokens.append(PyToken("NUMBER", num_val, num_val, start_line, start_col))
                continue

            # Identifiers and keywords
            if ch.isalpha() or ch == "_":
                ident = self._read_identifier()
                if ident in PY_KEYWORDS:
                    tokens.append(PyToken("KEYWORD", ident, ident, start_line, start_col))
                else:
                    tokens.append(PyToken("IDENTIFIER", ident, ident, start_line, start_col))
                continue

            # Multi-character operators
            matched_op = None
            for op in MULTI_OPS:
                if self.source.startswith(op, self.pos):
                    matched_op = op
                    for _ in range(len(op)):
                        self._advance()
                    break

            if matched_op:
                tokens.append(PyToken("OPERATOR", matched_op, matched_op, start_line, start_col))
                continue

            # Punctuation
            if ch in PUNCTUATIONS:
                self._advance()
                tokens.append(PyToken("PUNCTUATION", ch, ch, start_line, start_col))
                continue

            # Skip unsupported / unrecognized character
            self._advance()

        # Emit closing DEDENTs
        while len(self.indent_stack) > 1:
            self.indent_stack.pop()
            tokens.append(PyToken("DEDENT", "", "", self.line, self.col))

        tokens.append(PyToken("EOF", "EOF", "", self.line, self.col))
        return tokens

    def _read_number(self) -> str:
        chars = []
        has_dot = False
        while self.pos < self.length:
            ch = self._peek()
            if ch.isdigit():
                chars.append(self._advance())
            elif ch == "." and not has_dot and self._peek(1).isdigit():
                has_dot = True
                chars.append(self._advance())
            else:
                break
        return "".join(chars)

    def _read_identifier(self) -> str:
        chars = []
        while self.pos < self.length:
            ch = self._peek()
            if ch.isalnum() or ch == "_":
                chars.append(self._advance())
            else:
                break
        return "".join(chars)


def tokenize_python(source: str) -> List[PyToken]:
    return PyLexer(source).tokenize()
