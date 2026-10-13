"""Recursive-descent parser for typed Python subset.

Enforces static type hints on functions and parameters, rejecting untyped constructs
with informative, actionable compiler diagnostics.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, List, Optional, Union
from app.frontends.py_lexer import PyToken, tokenize_python, PyLexerError


class PySyntaxError(Exception):
    def __init__(self, message: str, line: int, col: int) -> None:
        super().__init__(f"{message} at line {line}:{col}")
        self.message = message
        self.line = line
        self.col = col


# -----------------------------------------------------------------------------
# Typed Python AST Nodes
# -----------------------------------------------------------------------------

@dataclass
class PyNode:
    kind: str
    line: int
    col: int
    value: Any = None
    children: List[PyNode] = field(default_factory=list)


class PyParser:
    def __init__(self, tokens: List[PyToken]) -> None:
        self.tokens = tokens
        self.pos = 0
        self.diagnostics: List[str] = []

    def _current(self) -> PyToken:
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return self.tokens[-1] if self.tokens else PyToken("EOF", "EOF", "", 1, 1)

    def _peek(self, offset: int = 1) -> PyToken:
        idx = self.pos + offset
        if idx < len(self.tokens):
            return self.tokens[idx]
        return self.tokens[-1] if self.tokens else PyToken("EOF", "EOF", "", 1, 1)

    def _is_at_end(self) -> bool:
        return self._current().kind == "EOF"

    def _advance(self) -> PyToken:
        tok = self._current()
        if not self._is_at_end():
            self.pos += 1
        return tok

    def _match(self, *expected: str) -> bool:
        if self._current().value in expected:
            self._advance()
            return True
        return False

    def _expect(self, expected: str, desc: str = "") -> PyToken:
        cur = self._current()
        if cur.kind == expected or cur.value == expected:
            return self._advance()
        msg = f"Expected '{expected}' {desc} but found '{cur.value or cur.kind}' at line {cur.line}:{cur.col}"
        self.diagnostics.append(msg)
        raise PySyntaxError(msg, cur.line, cur.col)

    def _skip_newlines(self) -> None:
        while not self._is_at_end() and self._current().kind == "NEWLINE":
            self._advance()

    # -------------------------------------------------------------------------
    # Program & Statement Parsing
    # -------------------------------------------------------------------------

    def parse(self) -> PyNode:
        root = PyNode(kind="Module", line=1, col=1)
        self._skip_newlines()

        while not self._is_at_end():
            cur = self._current()
            # Check for unsupported top-level constructs
            if cur.value == "class":
                raise PySyntaxError("unsupported construct: classes are not supported in CodeGuard C converter", cur.line, cur.col)
            if cur.value in ("try", "except"):
                raise PySyntaxError("unsupported construct: exception handling is not supported in CodeGuard C converter", cur.line, cur.col)
            if cur.value == "@":
                raise PySyntaxError("unsupported construct: decorators are not supported in CodeGuard C converter", cur.line, cur.col)

            stmt = self._parse_statement()
            if stmt:
                root.children.append(stmt)
            self._skip_newlines()

        return root

    def _parse_block(self) -> PyNode:
        self._skip_newlines()
        self._expect("INDENT", "at start of indented block")
        block = PyNode(kind="Block", line=self._current().line, col=self._current().col)

        while not self._is_at_end() and self._current().kind != "DEDENT":
            self._skip_newlines()
            if self._current().kind == "DEDENT":
                break
            stmt = self._parse_statement()
            if stmt:
                block.children.append(stmt)
            self._skip_newlines()

        self._expect("DEDENT", "at end of indented block")
        return block

    def _parse_statement(self) -> Optional[PyNode]:
        cur = self._current()

        if cur.value == "def":
            return self._parse_function_def()
        if cur.value == "if":
            return self._parse_if_stmt()
        if cur.value == "while":
            return self._parse_while_stmt()
        if cur.value == "for":
            return self._parse_for_stmt()
        if cur.value == "return":
            tok = self._advance()
            val = None
            if self._current().kind != "NEWLINE" and not self._is_at_end():
                val = self._parse_expr()
            self._consume_end_of_statement()
            return PyNode(kind="Return", line=tok.line, col=tok.col, children=[val] if val else [])
        if cur.value == "break":
            tok = self._advance()
            self._consume_end_of_statement()
            return PyNode(kind="Break", line=tok.line, col=tok.col)
        if cur.value == "continue":
            tok = self._advance()
            self._consume_end_of_statement()
            return PyNode(kind="Continue", line=tok.line, col=tok.col)
        if cur.value == "pass":
            tok = self._advance()
            self._consume_end_of_statement()
            return PyNode(kind="Pass", line=tok.line, col=tok.col)
        if cur.value in ("import", "from"):
            return self._parse_import()

        # Expression or assignment
        expr = self._parse_expr()
        if self._current().value in ("=", "+=", "-=", "*=", "/=", "%=", "//="):
            op_tok = self._advance()
            val = self._parse_expr()
            self._consume_end_of_statement()
            return PyNode(kind="Assign", value=op_tok.value, line=op_tok.line, col=op_tok.col, children=[expr, val])

        self._consume_end_of_statement()
        return PyNode(kind="ExprStmt", line=expr.line, col=expr.col, children=[expr])

    def _consume_end_of_statement(self) -> None:
        if not self._is_at_end() and self._current().kind == "NEWLINE":
            self._advance()

    def _parse_import(self) -> Optional[PyNode]:
        tok = self._advance()
        mod_name = self._advance().value
        if mod_name != "math":
            raise PySyntaxError(f"unsupported construct: import of non-math module '{mod_name}'", tok.line, tok.col)
        self._consume_end_of_statement()
        return None

    def _parse_function_def(self) -> PyNode:
        def_tok = self._advance()  # 'def'
        name_tok = self._advance()
        name = name_tok.value

        self._expect("(", "after function name")
        params: List[PyNode] = []

        if self._current().value != ")":
            while True:
                if self._current().value in ("*", "**"):
                    raise PySyntaxError("unsupported construct: *args/**kwargs not supported in CodeGuard C converter", self._current().line, self._current().col)

                pname_tok = self._advance()
                pname = pname_tok.value

                # Check required parameter type hint
                if self._current().value != ":":
                    msg = (
                        f"Missing type hint for parameter '{pname}' at line {pname_tok.line}. "
                        f"Fix by adding type annotation, e.g. '{pname}: int'. "
                        f"Translating dynamic Python to C requires static types."
                    )
                    raise PySyntaxError(msg, pname_tok.line, pname_tok.col)

                self._advance()  # consume ':'
                ptype = self._parse_type_annotation()

                params.append(PyNode(kind="Param", value=pname, line=pname_tok.line, col=pname_tok.col, children=[ptype]))

                if self._current().value == ",":
                    self._advance()
                else:
                    break

        self._expect(")", "after parameter list")

        # Check required return type hint ->
        if self._current().value != "->":
            msg = (
                f"Missing return type hint for function '{name}' at line {def_tok.line}. "
                f"Fix by adding return annotation, e.g. 'def {name}(...) -> int:'. "
                f"Translating dynamic Python to C requires static types."
            )
            raise PySyntaxError(msg, def_tok.line, def_tok.col)

        self._advance()  # consume '->'
        ret_type = self._parse_type_annotation()

        self._expect(":", "after function signature")
        body = self._parse_block()

        return PyNode(
            kind="FunctionDef",
            value=name,
            line=def_tok.line,
            col=def_tok.col,
            children=[ret_type, PyNode(kind="ParamList", line=def_tok.line, col=def_tok.col, children=params), body],
        )

    def _parse_type_annotation(self) -> PyNode:
        tok = self._advance()
        tname = tok.value

        # Support list[int] or list[float]
        if tname == "list" and self._current().value == "[":
            self._advance()
            elem_type = self._advance().value
            self._expect("]", "closing bracket for list type")
            return PyNode(kind="Type", value=f"{elem_type}[]", line=tok.line, col=tok.col)

        if tname in ("int", "float", "bool", "str", "None"):
            return PyNode(kind="Type", value=tname, line=tok.line, col=tok.col)

        raise PySyntaxError(f"Unsupported or unknown type '{tname}' at line {tok.line}:{tok.col}", tok.line, tok.col)

    def _parse_if_stmt(self) -> PyNode:
        if_tok = self._advance()
        cond = self._parse_expr()
        self._expect(":", "after if condition")
        then_block = self._parse_block()

        self._skip_newlines()
        else_block = None

        if self._current().value == "elif":
            nested_if = self._parse_if_stmt()
            else_block = PyNode(kind="Block", line=nested_if.line, col=nested_if.col, children=[nested_if])
        elif self._current().value == "else":
            self._advance()
            self._expect(":", "after else")
            else_block = self._parse_block()

        children = [cond, then_block]
        if else_block:
            children.append(else_block)

        return PyNode(kind="If", line=if_tok.line, col=if_tok.col, children=children)

    def _parse_while_stmt(self) -> PyNode:
        while_tok = self._advance()
        cond = self._parse_expr()
        self._expect(":", "after while condition")
        body = self._parse_block()
        return PyNode(kind="While", line=while_tok.line, col=while_tok.col, children=[cond, body])

    def _parse_for_stmt(self) -> PyNode:
        for_tok = self._advance()
        var_tok = self._advance()
        var_name = var_tok.value
        self._expect("in", "in for loop header")

        iterable = self._parse_expr()
        self._expect(":", "after for loop header")
        body = self._parse_block()

        return PyNode(
            kind="For",
            value=var_name,
            line=for_tok.line,
            col=for_tok.col,
            children=[PyNode(kind="Identifier", value=var_name, line=var_tok.line, col=var_tok.col), iterable, body],
        )

    # -------------------------------------------------------------------------
    # Expressions
    # -------------------------------------------------------------------------

    def _parse_expr(self) -> PyNode:
        return self._parse_or()

    def _parse_or(self) -> PyNode:
        left = self._parse_and()
        while self._current().value == "or":
            op_tok = self._advance()
            right = self._parse_and()
            left = PyNode(kind="BinaryOp", value="or", line=op_tok.line, col=op_tok.col, children=[left, right])
        return left

    def _parse_and(self) -> PyNode:
        left = self._parse_not()
        while self._current().value == "and":
            op_tok = self._advance()
            right = self._parse_not()
            left = PyNode(kind="BinaryOp", value="and", line=op_tok.line, col=op_tok.col, children=[left, right])
        return left

    def _parse_not(self) -> PyNode:
        if self._current().value == "not":
            op_tok = self._advance()
            operand = self._parse_not()
            return PyNode(kind="UnaryOp", value="not", line=op_tok.line, col=op_tok.col, children=[operand])
        return self._parse_comparison()

    def _parse_comparison(self) -> PyNode:
        left = self._parse_arithmetic()
        while self._current().value in ("==", "!=", "<", "<=", ">", ">="):
            op_tok = self._advance()
            right = self._parse_arithmetic()
            left = PyNode(kind="BinaryOp", value=op_tok.value, line=op_tok.line, col=op_tok.col, children=[left, right])
        return left

    def _parse_arithmetic(self) -> PyNode:
        left = self._parse_term()
        while self._current().value in ("+", "-"):
            op_tok = self._advance()
            right = self._parse_term()
            left = PyNode(kind="BinaryOp", value=op_tok.value, line=op_tok.line, col=op_tok.col, children=[left, right])
        return left

    def _parse_term(self) -> PyNode:
        left = self._parse_power()
        while self._current().value in ("*", "/", "//", "%"):
            op_tok = self._advance()
            right = self._parse_power()
            left = PyNode(kind="BinaryOp", value=op_tok.value, line=op_tok.line, col=op_tok.col, children=[left, right])
        return left

    def _parse_power(self) -> PyNode:
        left = self._parse_unary()
        if self._current().value == "**":
            op_tok = self._advance()
            right = self._parse_power()
            return PyNode(kind="BinaryOp", value="**", line=op_tok.line, col=op_tok.col, children=[left, right])
        return left

    def _parse_unary(self) -> PyNode:
        if self._current().value in ("+", "-"):
            op_tok = self._advance()
            operand = self._parse_unary()
            return PyNode(kind="UnaryOp", value=op_tok.value, line=op_tok.line, col=op_tok.col, children=[operand])
        return self._parse_primary()

    def _parse_primary(self) -> PyNode:
        cur = self._current()

        if cur.value == "(":
            self._advance()
            expr = self._parse_expr()
            self._expect(")", "closing parenthesis")
            return expr

        if cur.value == "[":
            # List literal: [1, 2, 3]
            open_tok = self._advance()
            items = []
            if self._current().value != "]":
                while True:
                    items.append(self._parse_expr())
                    if self._current().value == ",":
                        self._advance()
                        if self._current().value == "]":
                            break
                    else:
                        break
            self._expect("]", "closing bracket for list")
            return PyNode(kind="ListLiteral", line=open_tok.line, col=open_tok.col, children=items)

        if cur.kind == "NUMBER":
            tok = self._advance()
            return PyNode(kind="Literal", value=tok.value, line=tok.line, col=tok.col)

        if cur.kind == "STRING":
            tok = self._advance()
            return PyNode(kind="Literal", value=tok.raw, line=tok.line, col=tok.col)

        if cur.value in ("True", "False"):
            tok = self._advance()
            return PyNode(kind="Literal", value=tok.value.lower(), line=tok.line, col=tok.col)

        if cur.kind == "IDENTIFIER" or cur.value in ("print", "input", "len", "range"):
            tok = self._advance()
            node = PyNode(kind="Identifier", value=tok.value, line=tok.line, col=tok.col)

            # Check calls or indexing
            while True:
                if self._current().value == "(":
                    self._advance()
                    args = []
                    if self._current().value != ")":
                        while True:
                            args.append(self._parse_expr())
                            if self._current().value == ",":
                                self._advance()
                            else:
                                break
                    self._expect(")", "closing parenthesis for function call")
                    node = PyNode(kind="Call", line=tok.line, col=tok.col, children=[node, PyNode(kind="ArgList", line=tok.line, col=tok.col, children=args)])
                elif self._current().value == "[":
                    self._advance()
                    idx = self._parse_expr()
                    self._expect("]", "closing bracket for index")
                    node = PyNode(kind="Index", line=tok.line, col=tok.col, children=[node, idx])
                else:
                    break
            return node

        tok = self._advance()
        return PyNode(kind="Unknown", value=tok.value, line=tok.line, col=tok.col)


def parse_python(source: str) -> PyNode:
    tokens = tokenize_python(source)
    return PyParser(tokens).parse()
