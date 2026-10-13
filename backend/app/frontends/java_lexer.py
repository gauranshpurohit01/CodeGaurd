"""Hand-written character scanner (lexer) for Java subset."""

from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional, Set


class JavaLexerError(Exception):
    def __init__(self, message: str, line: int, col: int) -> None:
        super().__init__(f"{message} at line {line}:{col}")
        self.message = message
        self.line = line
        self.col = col


@dataclass
class JavaToken:
    kind: str      # KEYWORD, IDENTIFIER, NUMBER, STRING, CHAR, OPERATOR, PUNCTUATION, EOF
    value: str
    raw: str
    line: int
    col: int

    def __repr__(self) -> str:
        return f"JavaToken({self.kind}, {self.value!r}, L{self.line}:C{self.col})"


JAVA_KEYWORDS: Set[str] = {
    "abstract", "assert", "boolean", "break", "byte", "case", "catch", "char",
    "class", "const", "continue", "default", "do", "double", "else", "enum",
    "extends", "final", "finally", "float", "for", "goto", "if", "implements",
    "import", "instanceof", "int", "interface", "long", "native", "new", "package",
    "private", "protected", "public", "return", "short", "static", "strictfp",
    "super", "switch", "synchronized", "this", "throw", "throws", "transient",
    "try", "void", "volatile", "while", "true", "false", "null", "String",
}

JAVA_MULTI_OPS: List[str] = [
    "<<=", ">>=", ">>>=", "==", "!=", "<=", ">=", "&&", "||", "++", "--",
    "+=", "-=", "*=", "/=", "%=", "&=", "|=", "^=", "->", "::",
    "+", "-", "*", "/", "%", "=", "<", ">", "!", "~", "&", "|", "^", "?", ":",
]

JAVA_PUNCTUATION: Set[str] = {"(", ")", "{", "}", "[", "]", ";", ",", "."}


class JavaLexer:
    def __init__(self, source: str) -> None:
        self.source = source
        self.pos = 0
        self.length = len(source)
        self.line = 1
        self.col = 1

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

    def tokenize(self) -> List[JavaToken]:
        tokens: List[JavaToken] = []

        while self.pos < self.length:
            ch = self._peek()

            # Skip whitespace
            if ch.isspace():
                self._advance()
                continue

            start_line = self.line
            start_col = self.col

            # Single-line comment: // ...
            if ch == "/" and self._peek(1) == "/":
                self._advance()
                self._advance()
                while self.pos < self.length and self._peek() != "\n":
                    self._advance()
                continue

            # Multi-line comment: /* ... */
            if ch == "/" and self._peek(1) == "*":
                self._advance()
                self._advance()
                closed = False
                while self.pos < self.length:
                    if self._peek() == "*" and self._peek(1) == "/":
                        self._advance()
                        self._advance()
                        closed = True
                        break
                    self._advance()
                if not closed:
                    raise JavaLexerError("Unterminated block comment", start_line, start_col)
                continue

            # Strings: " ... "
            if ch == '"':
                str_val = self._read_string()
                tokens.append(JavaToken("STRING", str_val, f'"{str_val}"', start_line, start_col))
                continue

            # Chars: ' ... '
            if ch == "'":
                char_val = self._read_char()
                tokens.append(JavaToken("CHAR", char_val, f"'{char_val}'", start_line, start_col))
                continue

            # Numbers
            if ch.isdigit() or (ch == "." and self._peek(1).isdigit()):
                num_val = self._read_number()
                tokens.append(JavaToken("NUMBER", num_val, num_val, start_line, start_col))
                continue

            # Identifiers and keywords
            if ch.isalpha() or ch in ("_", "$"):
                ident = self._read_identifier()
                if ident in JAVA_KEYWORDS:
                    tokens.append(JavaToken("KEYWORD", ident, ident, start_line, start_col))
                else:
                    tokens.append(JavaToken("IDENTIFIER", ident, ident, start_line, start_col))
                continue

            # Multi-character operators
            matched_op = None
            for op in JAVA_MULTI_OPS:
                if self.source.startswith(op, self.pos):
                    matched_op = op
                    for _ in range(len(op)):
                        self._advance()
                    break

            if matched_op:
                tokens.append(JavaToken("OPERATOR", matched_op, matched_op, start_line, start_col))
                continue

            # Punctuation
            if ch in JAVA_PUNCTUATION:
                self._advance()
                tokens.append(JavaToken("PUNCTUATION", ch, ch, start_line, start_col))
                continue

            # Resiliently skip unknown characters
            self._advance()

        tokens.append(JavaToken("EOF", "EOF", "", self.line, self.col))
        return tokens

    def _read_string(self) -> str:
        self._advance()  # consume opening "
        chars = []
        while self.pos < self.length:
            ch = self._peek()
            if ch == "\\":
                chars.append(self._advance())
                if self.pos < self.length:
                    chars.append(self._advance())
                continue
            if ch == '"':
                self._advance()
                break
            chars.append(self._advance())
        return "".join(chars)

    def _read_char(self) -> str:
        self._advance()  # consume opening '
        chars = []
        while self.pos < self.length:
            ch = self._peek()
            if ch == "\\":
                chars.append(self._advance())
                if self.pos < self.length:
                    chars.append(self._advance())
                continue
            if ch == "'":
                self._advance()
                break
            chars.append(self._advance())
        return "".join(chars)

    def _read_number(self) -> str:
        chars = []
        has_dot = False
        while self.pos < self.length:
            ch = self._peek()
            if ch.isdigit():
                chars.append(self._advance())
            elif ch == "." and not has_dot:
                has_dot = True
                chars.append(self._advance())
            elif ch.lower() in ("f", "d", "l"):
                chars.append(self._advance())
                break
            else:
                break
        return "".join(chars)

    def _read_identifier(self) -> str:
        chars = []
        while self.pos < self.length:
            ch = self._peek()
            if ch.isalnum() or ch in ("_", "$"):
                chars.append(self._advance())
            else:
                break
        return "".join(chars)


def tokenize_java(source: str) -> List[JavaToken]:
    return JavaLexer(source).tokenize()
