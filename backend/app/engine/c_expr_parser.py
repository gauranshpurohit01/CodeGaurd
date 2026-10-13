"""Expression parsing mixin for recursive-descent C parser with operator precedence."""

from __future__ import annotations
from typing import TYPE_CHECKING, List, Optional
from app.engine.ast_nodes import Node
from app.engine.lexer import Token

if TYPE_CHECKING:
    from app.engine.c_parser import CParserBase

ASSIGNMENT_OPS = {
    "=", "+=", "-=", "*=", "/=", "%=", "&=", "|=", "^=", "<<=", ">>=",
}


class ExpressionParserMixin:
    """Precedence climbing and postfix / primary expression parsing."""

    def _current(self) -> Token:
        raise NotImplementedError

    def _peek(self, offset: int = 1) -> Token:
        raise NotImplementedError

    def _is_at_end(self) -> bool:
        raise NotImplementedError

    def _advance(self) -> Token:
        raise NotImplementedError

    def _expect(self, expected: str, desc: str = "") -> Token:
        raise NotImplementedError

    def _is_type_start(self, tok: Optional[Token] = None) -> bool:
        raise NotImplementedError

    def _parse_type_specifier(self) -> Node:
        raise NotImplementedError

    def _parse_expression(self) -> Node:
        return self._parse_assignment()

    def _parse_assignment(self) -> Node:
        left = self._parse_ternary()
        if self._current().value in ASSIGNMENT_OPS:
            op_tok = self._advance()
            right = self._parse_assignment()
            return Node(kind="Assign", value=op_tok.value, children=[left, right], line=op_tok.line, col=op_tok.col)
        return left

    def _parse_ternary(self) -> Node:
        cond = self._parse_logical_or()
        if self._current().value == "?":
            q_tok = self._advance()
            true_expr = self._parse_expression()
            self._expect(":", "in ternary conditional operator")
            false_expr = self._parse_ternary()
            return Node(kind="Ternary", children=[cond, true_expr, false_expr], line=q_tok.line, col=q_tok.col)
        return cond

    def _parse_logical_or(self) -> Node:
        left = self._parse_logical_and()
        while self._current().value == "||":
            op_tok = self._advance()
            right = self._parse_logical_and()
            left = Node(kind="BinaryOp", value=op_tok.value, children=[left, right], line=op_tok.line, col=op_tok.col)
        return left

    def _parse_logical_and(self) -> Node:
        left = self._parse_bitwise_or()
        while self._current().value == "&&":
            op_tok = self._advance()
            right = self._parse_bitwise_or()
            left = Node(kind="BinaryOp", value=op_tok.value, children=[left, right], line=op_tok.line, col=op_tok.col)
        return left

    def _parse_bitwise_or(self) -> Node:
        left = self._parse_bitwise_xor()
        while self._current().value == "|":
            op_tok = self._advance()
            right = self._parse_bitwise_xor()
            left = Node(kind="BinaryOp", value=op_tok.value, children=[left, right], line=op_tok.line, col=op_tok.col)
        return left

    def _parse_bitwise_xor(self) -> Node:
        left = self._parse_bitwise_and()
        while self._current().value == "^":
            op_tok = self._advance()
            right = self._parse_bitwise_and()
            left = Node(kind="BinaryOp", value=op_tok.value, children=[left, right], line=op_tok.line, col=op_tok.col)
        return left

    def _parse_bitwise_and(self) -> Node:
        left = self._parse_equality()
        while self._current().value == "&":
            op_tok = self._advance()
            right = self._parse_equality()
            left = Node(kind="BinaryOp", value=op_tok.value, children=[left, right], line=op_tok.line, col=op_tok.col)
        return left

    def _parse_equality(self) -> Node:
        left = self._parse_relational()
        while self._current().value in ("==", "!="):
            op_tok = self._advance()
            right = self._parse_relational()
            left = Node(kind="BinaryOp", value=op_tok.value, children=[left, right], line=op_tok.line, col=op_tok.col)
        return left

    def _parse_relational(self) -> Node:
        left = self._parse_shift()
        while self._current().value in ("<", "<=", ">", ">="):
            op_tok = self._advance()
            right = self._parse_shift()
            left = Node(kind="BinaryOp", value=op_tok.value, children=[left, right], line=op_tok.line, col=op_tok.col)
        return left

    def _parse_shift(self) -> Node:
        left = self._parse_additive()
        while self._current().value in ("<<", ">>"):
            op_tok = self._advance()
            right = self._parse_additive()
            left = Node(kind="BinaryOp", value=op_tok.value, children=[left, right], line=op_tok.line, col=op_tok.col)
        return left

    def _parse_additive(self) -> Node:
        left = self._parse_multiplicative()
        while self._current().value in ("+", "-"):
            op_tok = self._advance()
            right = self._parse_multiplicative()
            left = Node(kind="BinaryOp", value=op_tok.value, children=[left, right], line=op_tok.line, col=op_tok.col)
        return left

    def _parse_multiplicative(self) -> Node:
        left = self._parse_unary()
        while self._current().value in ("*", "/", "%"):
            op_tok = self._advance()
            right = self._parse_unary()
            left = Node(kind="BinaryOp", value=op_tok.value, children=[left, right], line=op_tok.line, col=op_tok.col)
        return left

    def _parse_unary(self) -> Node:
        cur = self._current()

        # Prefix ++, --, +, -, !, ~, *, &
        if cur.value in ("++", "--", "+", "-", "!", "~", "*", "&"):
            op_tok = self._advance()
            operand = self._parse_unary()
            return Node(kind="UnaryOp", value=op_tok.value, children=[operand], line=op_tok.line, col=op_tok.col)

        # sizeof operator
        if cur.value == "sizeof":
            self._advance()
            if self._current().value == "(":
                self._advance()
                if self._is_type_start():
                    type_arg = self._parse_type_specifier()
                    self._expect(")", "after sizeof type")
                    return Node(kind="Sizeof", children=[type_arg], line=cur.line, col=cur.col)
                expr_arg = self._parse_expression()
                self._expect(")", "after sizeof expression")
                return Node(kind="Sizeof", children=[expr_arg], line=cur.line, col=cur.col)
            arg = self._parse_unary()
            return Node(kind="Sizeof", children=[arg], line=cur.line, col=cur.col)

        # Cast: (type) expr
        if cur.value == "(":
            next_tok = self._peek(1)
            if self._is_type_start(next_tok):
                saved_pos = getattr(self, "pos", 0)
                try:
                    self._advance()  # consume '('
                    type_node = self._parse_type_specifier()
                    if self._current().value == ")":
                        self._advance()  # consume ')'
                        target_expr = self._parse_unary()
                        return Node(kind="Cast", children=[type_node, target_expr], line=cur.line, col=cur.col)
                except Exception:
                    pass
                setattr(self, "pos", saved_pos)

        return self._parse_postfix()

    def _parse_postfix(self) -> Node:
        expr = self._parse_primary()

        while True:
            cur = self._current()
            if cur.value in ("++", "--"):
                op_tok = self._advance()
                expr = Node(kind="PostfixOp", value=op_tok.value, children=[expr], line=op_tok.line, col=op_tok.col)
            elif cur.value == "(":
                self._advance()
                args: List[Node] = []
                if self._current().value != ")":
                    while True:
                        args.append(self._parse_expression())
                        if self._current().value == ",":
                            self._advance()
                        else:
                            break
                self._expect(")", "closing parenthesis for call arguments")
                expr = Node(kind="Call", children=[expr, Node(kind="ArgList", children=args, line=cur.line, col=cur.col)], line=expr.line, col=expr.col)
            elif cur.value == "[":
                self._advance()
                idx_expr = self._parse_expression()
                self._expect("]", "closing bracket for array index")
                expr = Node(kind="Index", children=[expr, idx_expr], line=expr.line, col=expr.col)
            elif cur.value in (".", "->", "::"):
                op_tok = self._advance()
                member_name = self._expect("ID" if self._current().kind == "IDENTIFIER" else self._current().raw, "member identifier")
                expr = Node(kind="Member", value=f"{op_tok.value}{member_name.raw}", children=[expr], line=expr.line, col=expr.col)
            else:
                break

        return expr

    def _parse_primary(self) -> Node:
        cur = self._current()

        if cur.value == "(":
            self._advance()
            expr = self._parse_expression()
            self._expect(")", "closing parenthesis")
            return expr

        if cur.kind == "NUMBER":
            self._advance()
            return Node(kind="Literal", value=cur.raw, line=cur.line, col=cur.col)

        if cur.kind == "STRING":
            self._advance()
            return Node(kind="Literal", value=cur.raw, line=cur.line, col=cur.col)

        if cur.kind == "CHAR":
            self._advance()
            return Node(kind="Literal", value=cur.raw, line=cur.line, col=cur.col)

        if cur.value in ("true", "false"):
            self._advance()
            return Node(kind="Literal", value=cur.raw, line=cur.line, col=cur.col)

        if cur.kind in ("IDENTIFIER", "KEYWORD"):
            self._advance()
            return Node(kind="Identifier", value=cur.raw, line=cur.line, col=cur.col)

        self._advance()
        return Node(kind="Unknown", value=cur.raw, line=cur.line, col=cur.col)
