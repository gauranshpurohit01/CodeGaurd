"""Recursive-descent parser for C with C++ tolerance and error recovery.

Parses functions, prototypes, variable declarations, control flow constructs,
and delegates expression precedence climbing to ExpressionParserMixin.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional, Set
from app.engine.lexer import Token, tokenize
from app.engine.ast_nodes import Node
from app.engine.c_expr_parser import ExpressionParserMixin


PRIMITIVE_TYPES: Set[str] = {
    "int", "char", "float", "double", "void", "short", "long",
    "signed", "unsigned", "bool", "_Bool", "size_t", "auto",
}

TYPE_QUALIFIERS: Set[str] = {
    "const", "static", "volatile", "extern", "register", "inline", "restrict",
}


@dataclass
class ParseResult:
    ast: Node
    errors: List[str] = field(default_factory=list)
    recovery_events: List[str] = field(default_factory=list)


class CParser(ExpressionParserMixin):
    def __init__(self, tokens: List[Token]) -> None:
        self.tokens: List[Token] = [t for t in tokens if t.kind != "PREPROCESSOR"]
        self.pos: int = 0
        self.errors: List[str] = []
        self.recovery_events: List[str] = []

    def _current(self) -> Token:
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return self.tokens[-1] if self.tokens else Token("EOF", "EOF", "", 1, 1)

    def _peek(self, offset: int = 1) -> Token:
        idx = self.pos + offset
        if idx < len(self.tokens):
            return self.tokens[idx]
        return self.tokens[-1] if self.tokens else Token("EOF", "EOF", "", 1, 1)

    def _is_at_end(self) -> bool:
        return self._current().kind == "EOF"

    def _advance(self) -> Token:
        tok = self._current()
        if not self._is_at_end():
            self.pos += 1
        return tok

    def _expect(self, expected: str, desc: str = "") -> Token:
        cur = self._current()
        if cur.value == expected or cur.raw == expected:
            return self._advance()
        msg = f"Expected '{expected}' {desc} but found '{cur.raw}' at line {cur.line}:{cur.col}"
        self.errors.append(msg)
        raise SyntaxError(msg)

    def _synchronize_statement(self) -> None:
        """Skip tokens until the next statement boundary (; or }) to resume parsing."""
        event = f"Recovering from syntax error near '{self._current().raw}' (L{self._current().line})"
        self.recovery_events.append(event)
        if not self._is_at_end():
            self._advance()
        while not self._is_at_end():
            if self._current().value in (";", "}"):
                self._advance()
                return
            self._advance()

    # -------------------------------------------------------------------------
    # Top-Level Program & Declarations
    # -------------------------------------------------------------------------

    def parse(self) -> ParseResult:
        root = Node(kind="TranslationUnit", line=1, col=1)
        while not self._is_at_end():
            try:
                if self._current().value == "using":
                    self._parse_using_directive()
                    continue

                decl = self._parse_external_declaration()
                if decl:
                    if isinstance(decl, list):
                        root.children.extend(decl)
                    else:
                        root.children.append(decl)
            except SyntaxError:
                self._synchronize_statement()
            except Exception as ex:
                self.errors.append(str(ex))
                self._synchronize_statement()

        return ParseResult(ast=root, errors=self.errors, recovery_events=self.recovery_events)

    def _parse_using_directive(self) -> None:
        self._advance()
        while not self._is_at_end() and self._current().value != ";":
            self._advance()
        if self._current().value == ";":
            self._advance()

    def _is_type_start(self, tok: Optional[Token] = None) -> bool:
        t = tok if tok is not None else self._current()
        if t.value in PRIMITIVE_TYPES or t.value in TYPE_QUALIFIERS:
            return True
        if t.value in ("struct", "union", "enum"):
            return True
        return False

    def _parse_type_specifier(self) -> Node:
        line, col = self._current().line, self._current().col
        parts: List[str] = []

        while not self._is_at_end() and (self._current().value in TYPE_QUALIFIERS or self._current().value in ("unsigned", "signed", "long", "short")):
            parts.append(self._advance().raw)

        if not self._is_at_end():
            cur = self._current()
            if cur.value in ("struct", "union", "enum"):
                parts.append(self._advance().raw)
                if not self._is_at_end() and (self._current().kind == "IDENTIFIER" or self._current().kind == "KEYWORD"):
                    parts.append(self._advance().raw)
            elif cur.value in PRIMITIVE_TYPES:
                parts.append(self._advance().raw)
            elif cur.kind == "IDENTIFIER":
                parts.append(self._advance().raw)

        while not self._is_at_end() and self._current().value in ("*", "&"):
            parts.append(self._advance().raw)

        type_str = " ".join(parts) if parts else "int"
        return Node(kind="Type", value=type_str, line=line, col=col)

    def _parse_external_declaration(self) -> Optional[Node | List[Node]]:
        type_node = self._parse_type_specifier()
        if self._is_at_end():
            return None

        name_tok = self._current()
        if name_tok.kind not in ("IDENTIFIER", "KEYWORD"):
            if name_tok.value == ";":
                self._advance()
                return None
            raise SyntaxError(f"Expected identifier at line {name_tok.line}:{name_tok.col}")

        ident_name = self._advance().raw
        line, col = name_tok.line, name_tok.col

        if self._current().value == "(":
            param_list = self._parse_parameter_list()
            if self._current().value == ";":
                self._advance()
                return Node(kind="FunctionDecl", value=ident_name, children=[type_node, param_list], line=line, col=col)

            if self._current().value == "{":
                body = self._parse_block()
                return Node(kind="FunctionDef", value=ident_name, children=[type_node, param_list, body], line=line, col=col)
            raise SyntaxError(f"Expected '{{' or ';' after function header at line {line}")

        return self._finish_var_decl(type_node, ident_name, line, col)

    def _parse_parameter_list(self) -> Node:
        paren_tok = self._expect("(", "for parameter list")
        param_nodes: List[Node] = []

        if self._current().value != ")":
            while True:
                if self._current().value == "void" and self._peek().value == ")":
                    self._advance()
                    break

                param_type = self._parse_type_specifier()
                param_name = ""
                p_line, p_col = self._current().line, self._current().col

                if self._current().kind in ("IDENTIFIER", "KEYWORD") and self._current().value not in (",", ")"):
                    param_name = self._advance().raw

                if self._current().value == "[":
                    self._advance()
                    if self._current().value != "]":
                        self._parse_expression()
                    self._expect("]", "closing bracket for array parameter")
                    param_type.value = f"{param_type.value}[]"

                param_nodes.append(Node(kind="Param", value=param_name, children=[param_type], line=p_line, col=p_col))

                if self._current().value == ",":
                    self._advance()
                else:
                    break

        self._expect(")", "closing parenthesis for parameter list")
        return Node(kind="ParamList", children=param_nodes, line=paren_tok.line, col=paren_tok.col)

    def _finish_var_decl(self, type_node: Node, first_name: str, line: int, col: int) -> List[Node]:
        decls: List[Node] = []
        cur_name = first_name
        cur_line, cur_col = line, col

        while True:
            dims: List[Node] = []
            while self._current().value == "[":
                self._advance()
                dim_expr = None
                if self._current().value != "]":
                    dim_expr = self._parse_expression()
                self._expect("]", "closing bracket for array dimension")
                if dim_expr:
                    dims.append(dim_expr)

            init_expr: Optional[Node] = None
            if self._current().value == "=":
                self._advance()
                if self._current().value == "{":
                    init_expr = self._parse_initializer_list()
                else:
                    init_expr = self._parse_expression()

            vtype = type_node.clone()
            if dims:
                vtype.value = f"{vtype.value}{'[]' * len(dims)}"

            children = [vtype]
            if dims:
                children.extend(dims)
            if init_expr:
                children.append(init_expr)

            decls.append(Node(kind="VarDecl", value=cur_name, children=children, line=cur_line, col=cur_col))

            if self._current().value == ",":
                self._advance()
                ptr_prefix = ""
                while self._current().value == "*":
                    ptr_prefix += self._advance().raw
                name_tok = self._current()
                if name_tok.kind in ("IDENTIFIER", "KEYWORD"):
                    cur_name = ptr_prefix + self._advance().raw
                    cur_line, cur_col = name_tok.line, name_tok.col
                else:
                    break
            else:
                break

        self._expect(";", "end of variable declaration")
        return decls

    def _parse_initializer_list(self) -> Node:
        brace = self._expect("{", "opening brace for initializer list")
        items: List[Node] = []
        if self._current().value != "}":
            while True:
                if self._current().value == "{":
                    items.append(self._parse_initializer_list())
                else:
                    items.append(self._parse_expression())
                if self._current().value == ",":
                    self._advance()
                    if self._current().value == "}":
                        break
                else:
                    break
        self._expect("}", "closing brace for initializer list")
        return Node(kind="InitList", children=items, line=brace.line, col=brace.col)

    # -------------------------------------------------------------------------
    # Statements & Control Flow
    # -------------------------------------------------------------------------

    def _parse_block(self) -> Node:
        brace = self._expect("{", "opening brace for block")
        stmts: List[Node] = []

        while not self._is_at_end() and self._current().value != "}":
            try:
                stmt = self._parse_statement()
                if stmt:
                    if isinstance(stmt, list):
                        stmts.extend(stmt)
                    else:
                        stmts.append(stmt)
            except SyntaxError:
                self._synchronize_statement()

        self._expect("}", "closing brace for block")
        return Node(kind="Block", children=stmts, line=brace.line, col=brace.col)

    def _parse_statement(self) -> Optional[Node | List[Node]]:
        cur = self._current()
        if cur.value == ";":
            self._advance()
            return None
        if cur.value == "{":
            return self._parse_block()

        if self._is_type_start():
            type_node = self._parse_type_specifier()
            if self._current().kind in ("IDENTIFIER", "KEYWORD"):
                name_tok = self._advance()
                return self._finish_var_decl(type_node, name_tok.raw, name_tok.line, name_tok.col)
            raise SyntaxError(f"Expected identifier at {self._current().line}:{self._current().col}")

        if cur.value == "if":
            return self._parse_if_statement()
        if cur.value == "while":
            return self._parse_while_statement()
        if cur.value == "for":
            return self._parse_for_statement()
        if cur.value == "do":
            return self._parse_do_while_statement()
        if cur.value == "switch":
            return self._parse_switch_statement()
        if cur.value == "case":
            return self._parse_case_statement()
        if cur.value == "default":
            return self._parse_default_statement()
        if cur.value == "break":
            tok = self._advance()
            self._expect(";", "after break")
            return Node(kind="Break", line=tok.line, col=tok.col)
        if cur.value == "continue":
            tok = self._advance()
            self._expect(";", "after continue")
            return Node(kind="Continue", line=tok.line, col=tok.col)
        if cur.value == "return":
            return self._parse_return_statement()

        expr = self._parse_expression()
        self._expect(";", "end of expression statement")
        return Node(kind="ExprStmt", children=[expr], line=expr.line, col=expr.col)

    def _parse_if_statement(self) -> Node:
        if_tok = self._advance()
        self._expect("(", "after if")
        cond = self._parse_expression()
        self._expect(")", "after if condition")

        then_block = self._ensure_block(self._parse_statement(), if_tok.line)
        children = [cond, then_block]

        if self._current().value == "else":
            self._advance()
            children.append(self._ensure_block(self._parse_statement(), if_tok.line))

        return Node(kind="If", children=children, line=if_tok.line, col=if_tok.col)

    def _parse_while_statement(self) -> Node:
        while_tok = self._advance()
        self._expect("(", "after while")
        cond = self._parse_expression()
        self._expect(")", "after while condition")
        body_block = self._ensure_block(self._parse_statement(), while_tok.line)
        return Node(kind="While", children=[cond, body_block], line=while_tok.line, col=while_tok.col)

    def _parse_do_while_statement(self) -> Node:
        do_tok = self._advance()
        body_block = self._ensure_block(self._parse_statement(), do_tok.line)
        self._expect("while", "after do block")
        self._expect("(", "after while in do-while")
        cond = self._parse_expression()
        self._expect(")", "after do-while condition")
        self._expect(";", "after do-while")
        return Node(kind="DoWhile", children=[body_block, cond], line=do_tok.line, col=do_tok.col)

    def _parse_for_statement(self) -> Node:
        for_tok = self._advance()
        self._expect("(", "after for")

        init_node: Optional[Node] = None
        if self._current().value != ";":
            if self._is_type_start():
                type_node = self._parse_type_specifier()
                name_tok = self._advance()
                if self._current().value == ":":
                    self._advance()
                    range_expr = self._parse_expression()
                    self._expect(")", "after range-based for")
                    body = self._parse_statement()
                    return Node(
                        kind="RangeFor",
                        children=[
                            Node(kind="VarDecl", value=name_tok.raw, children=[type_node], line=name_tok.line, col=name_tok.col),
                            range_expr,
                            self._ensure_block(body, for_tok.line),
                        ],
                        line=for_tok.line,
                        col=for_tok.col,
                    )
                init_node = Node(kind="Block", children=self._finish_var_decl(type_node, name_tok.raw, name_tok.line, name_tok.col))
            else:
                expr = self._parse_expression()
                self._expect(";", "after for init")
                init_node = Node(kind="ExprStmt", children=[expr], line=expr.line, col=expr.col)
        else:
            self._advance()

        cond_node = self._parse_expression() if self._current().value != ";" else Node(kind="Literal", value="1", line=for_tok.line, col=for_tok.col)
        self._expect(";", "after for condition")

        step_node: Optional[Node] = None
        if self._current().value != ")":
            step_expr = self._parse_expression()
            step_node = Node(kind="ExprStmt", children=[step_expr], line=step_expr.line, col=step_expr.col)
        self._expect(")", "after for step")

        body_block = self._ensure_block(self._parse_statement(), for_tok.line)

        children: List[Node] = [
            init_node or Node(kind="Empty", line=for_tok.line, col=for_tok.col),
            cond_node,
            step_node or Node(kind="Empty", line=for_tok.line, col=for_tok.col),
            body_block,
        ]
        return Node(kind="For", children=children, line=for_tok.line, col=for_tok.col)

    def _parse_switch_statement(self) -> Node:
        sw_tok = self._advance()
        self._expect("(", "after switch")
        expr = self._parse_expression()
        self._expect(")", "after switch condition")
        body_block = self._ensure_block(self._parse_statement(), sw_tok.line)
        return Node(kind="Switch", children=[expr, body_block], line=sw_tok.line, col=sw_tok.col)

    def _parse_case_statement(self) -> Node:
        c_tok = self._advance()
        val_expr = self._parse_expression()
        self._expect(":", "after case expression")
        return Node(kind="Case", children=[val_expr], line=c_tok.line, col=c_tok.col)

    def _parse_default_statement(self) -> Node:
        d_tok = self._advance()
        self._expect(":", "after default")
        return Node(kind="Default", line=d_tok.line, col=d_tok.col)

    def _parse_return_statement(self) -> Node:
        ret_tok = self._advance()
        children = [self._parse_expression()] if self._current().value != ";" else []
        self._expect(";", "after return expression")
        return Node(kind="Return", children=children, line=ret_tok.line, col=ret_tok.col)

    def _ensure_block(self, stmt: Optional[Node | List[Node]], fallback_line: int) -> Node:
        if stmt is None:
            return Node(kind="Block", line=fallback_line, col=1)
        if isinstance(stmt, list):
            return Node(kind="Block", children=stmt, line=fallback_line, col=1)
        if stmt.kind == "Block":
            return stmt
        return Node(kind="Block", children=[stmt], line=stmt.line, col=stmt.col)


def parse_c(source: str) -> ParseResult:
    tokens = tokenize(source)
    parser = CParser(tokens)
    return parser.parse()
