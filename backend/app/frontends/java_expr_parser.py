"""Expression parsing mixin for recursive-descent Java parser."""

from __future__ import annotations
from typing import TYPE_CHECKING, List, Optional
from app.frontends.java_lexer import JavaToken

if TYPE_CHECKING:
    from app.frontends.java_parser import JavaNode


class JavaExpressionParserMixin:
    """Precedence climbing and primary expression parsing for Java."""

    def _current(self) -> JavaToken:
        raise NotImplementedError

    def _peek(self, offset: int = 1) -> JavaToken:
        raise NotImplementedError

    def _is_at_end(self) -> bool:
        raise NotImplementedError

    def _advance(self) -> JavaToken:
        raise NotImplementedError

    def _expect(self, expected: str, desc: str = "") -> JavaToken:
        raise NotImplementedError

    def _parse_expr(self) -> any:
        return self._parse_assignment()

    def _parse_assignment(self) -> any:
        from app.frontends.java_parser import JavaNode
        left = self._parse_ternary()
        if self._current().value in ("=", "+=", "-=", "*=", "/=", "%=", "&=", "|=", "^="):
            op_tok = self._advance()
            right = self._parse_assignment()
            return JavaNode(kind="Assign", value=op_tok.value, line=op_tok.line, col=op_tok.col, children=[left, right])
        return left

    def _parse_ternary(self) -> any:
        from app.frontends.java_parser import JavaNode
        cond = self._parse_logical_or()
        if self._current().value == "?":
            q_tok = self._advance()
            true_expr = self._parse_expr()
            self._expect(":", "in ternary operator")
            false_expr = self._parse_ternary()
            return JavaNode(kind="Ternary", line=q_tok.line, col=q_tok.col, children=[cond, true_expr, false_expr])
        return cond

    def _parse_logical_or(self) -> any:
        from app.frontends.java_parser import JavaNode
        left = self._parse_logical_and()
        while self._current().value == "||":
            op_tok = self._advance()
            right = self._parse_logical_and()
            left = JavaNode(kind="BinaryOp", value="||", line=op_tok.line, col=op_tok.col, children=[left, right])
        return left

    def _parse_logical_and(self) -> any:
        from app.frontends.java_parser import JavaNode
        left = self._parse_bitwise_or()
        while self._current().value == "&&":
            op_tok = self._advance()
            right = self._parse_bitwise_or()
            left = JavaNode(kind="BinaryOp", value="&&", line=op_tok.line, col=op_tok.col, children=[left, right])
        return left

    def _parse_bitwise_or(self) -> any:
        from app.frontends.java_parser import JavaNode
        left = self._parse_bitwise_xor()
        while self._current().value == "|":
            op_tok = self._advance()
            right = self._parse_bitwise_xor()
            left = JavaNode(kind="BinaryOp", value="|", line=op_tok.line, col=op_tok.col, children=[left, right])
        return left

    def _parse_bitwise_xor(self) -> any:
        from app.frontends.java_parser import JavaNode
        left = self._parse_bitwise_and()
        while self._current().value == "^":
            op_tok = self._advance()
            right = self._parse_bitwise_and()
            left = JavaNode(kind="BinaryOp", value="^", line=op_tok.line, col=op_tok.col, children=[left, right])
        return left

    def _parse_bitwise_and(self) -> any:
        from app.frontends.java_parser import JavaNode
        left = self._parse_equality()
        while self._current().value == "&":
            op_tok = self._advance()
            right = self._parse_equality()
            left = JavaNode(kind="BinaryOp", value="&", line=op_tok.line, col=op_tok.col, children=[left, right])
        return left

    def _parse_equality(self) -> any:
        from app.frontends.java_parser import JavaNode
        left = self._parse_relational()
        while self._current().value in ("==", "!="):
            op_tok = self._advance()
            right = self._parse_relational()
            left = JavaNode(kind="BinaryOp", value=op_tok.value, line=op_tok.line, col=op_tok.col, children=[left, right])
        return left

    def _parse_relational(self) -> any:
        from app.frontends.java_parser import JavaNode
        left = self._parse_additive()
        while self._current().value in ("<", "<=", ">", ">="):
            op_tok = self._advance()
            right = self._parse_additive()
            left = JavaNode(kind="BinaryOp", value=op_tok.value, line=op_tok.line, col=op_tok.col, children=[left, right])
        return left

    def _parse_additive(self) -> any:
        from app.frontends.java_parser import JavaNode
        left = self._parse_multiplicative()
        while self._current().value in ("+", "-"):
            op_tok = self._advance()
            right = self._parse_multiplicative()
            left = JavaNode(kind="BinaryOp", value=op_tok.value, line=op_tok.line, col=op_tok.col, children=[left, right])
        return left

    def _parse_multiplicative(self) -> any:
        from app.frontends.java_parser import JavaNode
        left = self._parse_unary()
        while self._current().value in ("*", "/", "%"):
            op_tok = self._advance()
            right = self._parse_unary()
            left = JavaNode(kind="BinaryOp", value=op_tok.value, line=op_tok.line, col=op_tok.col, children=[left, right])
        return left

    def _parse_unary(self) -> any:
        from app.frontends.java_parser import JavaNode
        cur = self._current()
        if cur.value in ("++", "--", "+", "-", "!", "~"):
            op_tok = self._advance()
            operand = self._parse_unary()
            return JavaNode(kind="UnaryOp", value=op_tok.value, line=op_tok.line, col=op_tok.col, children=[operand])
        return self._parse_postfix()

    def _parse_postfix(self) -> any:
        from app.frontends.java_parser import JavaNode
        expr = self._parse_primary()

        while True:
            cur = self._current()
            if cur.value in ("++", "--"):
                op_tok = self._advance()
                expr = JavaNode(kind="PostfixOp", value=op_tok.value, line=op_tok.line, col=op_tok.col, children=[expr])
            elif cur.value == "(":
                self._advance()
                args = []
                if self._current().value != ")":
                    while True:
                        args.append(self._parse_expr())
                        if self._current().value == ",":
                            self._advance()
                        else:
                            break
                self._expect(")", "closing parenthesis for call")
                expr = JavaNode(kind="Call", line=expr.line, col=expr.col, children=[expr, JavaNode(kind="ArgList", line=cur.line, col=cur.col, children=args)])
            elif cur.value == "[":
                self._advance()
                idx = self._parse_expr()
                self._expect("]", "closing bracket for index")
                expr = JavaNode(kind="Index", line=expr.line, col=expr.col, children=[expr, idx])
            elif cur.value == ".":
                self._advance()
                mem_tok = self._advance()
                expr = JavaNode(kind="Member", value=f".{mem_tok.value}", line=expr.line, col=expr.col, children=[expr])
            else:
                break

        return expr

    def _parse_primary(self) -> any:
        from app.frontends.java_parser import JavaNode
        cur = self._current()

        if cur.value == "(":
            self._advance()
            expr = self._parse_expr()
            self._expect(")", "closing parenthesis")
            return expr

        if cur.kind == "NUMBER":
            self._advance()
            return JavaNode(kind="Literal", value=cur.value, line=cur.line, col=cur.col)

        if cur.kind == "STRING":
            self._advance()
            return JavaNode(kind="Literal", value=cur.raw, line=cur.line, col=cur.col)

        if cur.kind == "CHAR":
            self._advance()
            return JavaNode(kind="Literal", value=cur.raw, line=cur.line, col=cur.col)

        if cur.value in ("true", "false"):
            self._advance()
            return JavaNode(kind="Literal", value=cur.value, line=cur.line, col=cur.col)

        if cur.kind in ("IDENTIFIER", "KEYWORD"):
            self._advance()
            return JavaNode(kind="Identifier", value=cur.value, line=cur.line, col=cur.col)

        self._advance()
        return JavaNode(kind="Unknown", value=cur.value, line=cur.line, col=cur.col)
