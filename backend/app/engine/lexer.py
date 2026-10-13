"""Hand-written character scanner (lexer) for C and C++ source code.

Tokenizes source text into structured tokens, supporting plagiarism normalization,
preprocessor handling, escape sequences, number formats, and multi-char operators.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional, Set


class LexerError(Exception):
    def __init__(self, message: str, line: int, col: int) -> None:
        super().__init__(f"{message} at line {line}, col {col}")
        self.message = message
        self.line = line
        self.col = col


@dataclass
class Token:
    kind: str           # KEYWORD, IDENTIFIER, NUMBER, STRING, CHAR, OPERATOR, PUNCTUATION, PREPROCESSOR, EOF
    value: str          # Normalized token representation
    raw: str            # Original exact text
    line: int
    col: int

    def __repr__(self) -> str:
        return f"Token({self.kind}, {self.value!r}, raw={self.raw!r}, line={self.line}, col={self.col})"


KEYWORDS: Set[str] = {
    # C keywords
    "auto", "break", "case", "char", "const", "continue", "default", "do",
    "double", "else", "enum", "extern", "float", "for", "goto", "if",
    "int", "long", "register", "return", "short", "signed", "sizeof", "static",
    "struct", "switch", "typedef", "union", "unsigned", "void", "volatile", "while",
    # C99 / C11 / C++ keywords
    "inline", "restrict", "_Bool", "_Complex", "bool", "true", "false",
    "class", "public", "private", "protected", "virtual", "namespace", "using",
    "new", "delete", "this", "try", "catch", "throw", "template", "typename",
    "cin", "cout", "endl", "std",
}

MULTI_CHAR_OPS: List[str] = [
    # 3-character operators
    "<<=", ">>=", "...", "->*",
    # 2-character operators
    "::", "->", "++", "--", "<<", ">>", "<=", ">=", "==", "!=",
    "&&", "||", "+=", "-=", "*=", "/=", "%=", "&=", "|=", "^=",
    # 1-character operators
    "+", "-", "*", "/", "%", "=", "<", ">", "!", "~", "&", "|", "^", "?", ":",
]

PUNCTUATION_CHARS: Set[str] = {"(", ")", "{", "}", "[", "]", ";", ",", "."}


class Lexer:
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

    def _match(self, prefix: str) -> bool:
        if self.source.startswith(prefix, self.pos):
            for _ in prefix:
                self._advance()
            return True
        return False

    def tokenize(self) -> List[Token]:
        tokens: List[Token] = []

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
                    raise LexerError("Unterminated block comment", start_line, start_col)
                continue

            # Preprocessor directive: # ...
            if ch == "#":
                pp_raw = self._read_preprocessor()
                tokens.append(Token("PREPROCESSOR", "PP", pp_raw, start_line, start_col))
                continue

            # String literal: " ... "
            if ch == '"':
                str_val = self._read_string()
                tokens.append(Token("STRING", "STR", str_val, start_line, start_col))
                continue

            # Character literal: ' ... '
            if ch == "'":
                char_val = self._read_char()
                tokens.append(Token("CHAR", "CHAR", char_val, start_line, start_col))
                continue

            # Numbers: decimal, hex (0x), binary (0b), floats (.5 or 12.3e4)
            if ch.isdigit() or (ch == "." and self._peek(1).isdigit()):
                num_val = self._read_number()
                tokens.append(Token("NUMBER", "NUM", num_val, start_line, start_col))
                continue

            # Identifiers and Keywords
            if ch.isalpha() or ch == "_":
                ident_val = self._read_identifier()
                if ident_val in KEYWORDS:
                    tokens.append(Token("KEYWORD", ident_val, ident_val, start_line, start_col))
                else:
                    tokens.append(Token("IDENTIFIER", "ID", ident_val, start_line, start_col))
                continue

            # Operators (longest-match greedy check)
            op_match = self._try_read_operator()
            if op_match is not None:
                tokens.append(Token("OPERATOR", op_match, op_match, start_line, start_col))
                continue

            # Punctuation
            if ch in PUNCTUATION_CHARS:
                self._advance()
                tokens.append(Token("PUNCTUATION", ch, ch, start_line, start_col))
                continue

            # Unknown character: skip resiliently without crashing
            self._advance()

        tokens.append(Token("EOF", "EOF", "", self.line, self.col))
        return tokens

    def _read_preprocessor(self) -> str:
        chars: List[str] = []
        while self.pos < self.length:
            ch = self._peek()
            if ch == "\\":
                # Line continuation: backslash followed by newline
                if self._peek(1) == "\n":
                    chars.append(self._advance())
                    chars.append(self._advance())
                    continue
                elif self._peek(1) == "\r" and self._peek(2) == "\n":
                    chars.append(self._advance())
                    chars.append(self._advance())
                    chars.append(self._advance())
                    continue
            if ch == "\n":
                break
            chars.append(self._advance())
        return "".join(chars)

    def _read_string(self) -> str:
        chars: List[str] = [self._advance()]  # opening quote "
        while self.pos < self.length:
            ch = self._peek()
            if ch == "\\":
                chars.append(self._advance())
                if self.pos < self.length:
                    chars.append(self._advance())
                continue
            chars.append(self._advance())
            if ch == '"':
                break
        return "".join(chars)

    def _read_char(self) -> str:
        chars: List[str] = [self._advance()]  # opening quote '
        while self.pos < self.length:
            ch = self._peek()
            if ch == "\\":
                chars.append(self._advance())
                if self.pos < self.length:
                    chars.append(self._advance())
                continue
            chars.append(self._advance())
            if ch == "'":
                break
        return "".join(chars)

    def _read_number(self) -> str:
        chars: List[str] = []
        is_hex = False
        is_bin = False

        if self._peek() == "0" and (self._peek(1).lower() == "x"):
            chars.append(self._advance())
            chars.append(self._advance())
            is_hex = True
        elif self._peek() == "0" and (self._peek(1).lower() == "b"):
            chars.append(self._advance())
            chars.append(self._advance())
            is_bin = True

        has_dot = False
        has_exp = False

        while self.pos < self.length:
            ch = self._peek()
            if is_hex:
                if ch.isalnum():
                    chars.append(self._advance())
                else:
                    break
            elif is_bin:
                if ch in ("0", "1"):
                    chars.append(self._advance())
                else:
                    break
            else:
                if ch.isdigit():
                    chars.append(self._advance())
                elif ch == "." and not has_dot and not has_exp:
                    if self._peek(1).isdigit() or len(chars) > 0:
                        has_dot = True
                        chars.append(self._advance())
                    else:
                        break
                elif ch.lower() == "e" and not has_exp and len(chars) > 0:
                    has_exp = True
                    chars.append(self._advance())
                    if self._peek() in ("+", "-"):
                        chars.append(self._advance())
                elif ch.lower() in ("u", "l", "f"):
                    chars.append(self._advance())
                else:
                    break

        return "".join(chars)

    def _read_identifier(self) -> str:
        chars: List[str] = []
        while self.pos < self.length:
            ch = self._peek()
            if ch.isalnum() or ch == "_":
                chars.append(self._advance())
            else:
                break
        return "".join(chars)

    def _try_read_operator(self) -> Optional[str]:
        for op in MULTI_CHAR_OPS:
            if self.source.startswith(op, self.pos):
                for _ in range(len(op)):
                    self._advance()
                return op
        return None


def tokenize(source: str) -> List[Token]:
    return Lexer(source).tokenize()


def normalized_token_string(tokens: List[Token]) -> List[str]:
    """Return the list of normalized token values excluding EOF and PREPROCESSOR tokens."""
    return [t.value for t in tokens if t.kind not in ("EOF", "PREPROCESSOR")]
