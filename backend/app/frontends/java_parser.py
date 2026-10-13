"""Recursive-descent parser for Java subset.

Extracts static methods and main from class wrappers, translating statements and control flow
while delegating expression precedence parsing to JavaExpressionParserMixin.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, List, Optional
from app.frontends.java_lexer import JavaToken, tokenize_java
from app.frontends.java_expr_parser import JavaExpressionParserMixin


class JavaSyntaxError(Exception):
    def __init__(self, message: str, line: int, col: int) -> None:
        super().__init__(f"{message} at line {line}:{col}")
        self.message = message
        self.line = line
        self.col = col


@dataclass
class JavaNode:
    kind: str
    line: int
    col: int
    value: Any = None
    children: List[JavaNode] = field(default_factory=list)


JAVA_PRIMITIVE_TYPES = {
    "int", "double", "float", "boolean", "char", "byte", "short", "long", "void", "String",
}


class JavaParser(JavaExpressionParserMixin):
    def __init__(self, tokens: List[JavaToken]) -> None:
        self.tokens = tokens
        self.pos = 0
        self.diagnostics: List[str] = []

    def _current(self) -> JavaToken:
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return self.tokens[-1] if self.tokens else JavaToken("EOF", "EOF", "", 1, 1)

    def _peek(self, offset: int = 1) -> JavaToken:
        idx = self.pos + offset
        if idx < len(self.tokens):
            return self.tokens[idx]
        return self.tokens[-1] if self.tokens else JavaToken("EOF", "EOF", "", 1, 1)

    def _is_at_end(self) -> bool:
        return self._current().kind == "EOF"

    def _advance(self) -> JavaToken:
        tok = self._current()
        if not self._is_at_end():
            self.pos += 1
        return tok

    def _expect(self, expected: str, desc: str = "") -> JavaToken:
        cur = self._current()
        if cur.value == expected:
            return self._advance()
        msg = f"Expected '{expected}' {desc} but found '{cur.value}' at line {cur.line}:{cur.col}"
        self.diagnostics.append(msg)
        raise JavaSyntaxError(msg, cur.line, cur.col)

    # -------------------------------------------------------------------------
    # Class & Method Parsing
    # -------------------------------------------------------------------------

    def parse(self) -> JavaNode:
        root = JavaNode(kind="CompilationUnit", line=1, col=1)

        while not self._is_at_end():
            if self._current().value in ("package", "import"):
                while not self._is_at_end() and self._current().value != ";":
                    self._advance()
                if self._current().value == ";":
                    self._advance()
                continue

            if self._is_class_start():
                methods = self._parse_class_body()
                root.children.extend(methods)
                continue

            if self._is_method_start():
                m = self._parse_method()
                if m:
                    root.children.append(m)
                continue

            self._advance()

        return root

    def _is_class_start(self) -> bool:
        idx = self.pos
        while idx < len(self.tokens) and self.tokens[idx].value in ("public", "final", "abstract"):
            idx += 1
        return idx < len(self.tokens) and self.tokens[idx].value == "class"

    def _parse_class_body(self) -> List[JavaNode]:
        while not self._is_at_end() and self._current().value != "class":
            self._advance()
        self._advance()  # consume 'class'
        self._advance()  # consume class name

        if self._current().value in ("extends", "implements"):
            raise JavaSyntaxError(
                f"unsupported construct: inheritance/interfaces ('{self._current().value}') at line {self._current().line}",
                self._current().line, self._current().col,
            )

        self._expect("{", "opening brace of class body")
        methods: List[JavaNode] = []

        while not self._is_at_end() and self._current().value != "}":
            if self._current().value in ("try", "catch", "finally"):
                raise JavaSyntaxError("unsupported construct: exception handling", self._current().line, self._current().col)
            if self._current().value == "<":
                raise JavaSyntaxError("unsupported construct: generics", self._current().line, self._current().col)

            if self._is_method_start():
                m = self._parse_method()
                if m:
                    methods.append(m)
            else:
                self._advance()

        self._expect("}", "closing brace of class body")
        return methods

    def _is_method_start(self) -> bool:
        idx = self.pos
        while idx < len(self.tokens) and self.tokens[idx].value in ("public", "private", "protected", "static", "final"):
            idx += 1
        if idx < len(self.tokens) and (self.tokens[idx].value in JAVA_PRIMITIVE_TYPES or self.tokens[idx].kind == "IDENTIFIER"):
            idx += 1
            while idx < len(self.tokens) and self.tokens[idx].value == "[" and idx + 1 < len(self.tokens) and self.tokens[idx + 1].value == "]":
                idx += 2
            if idx < len(self.tokens) and self.tokens[idx].kind == "IDENTIFIER" and idx + 1 < len(self.tokens) and self.tokens[idx + 1].value == "(":
                return True
        return False

    def _parse_method(self) -> Optional[JavaNode]:
        start_tok = self._current()
        while not self._is_at_end() and self._current().value in ("public", "private", "protected", "static", "final"):
            self._advance()

        ret_type = self._parse_type()
        name_tok = self._advance()
        name = name_tok.value

        self._expect("(", "opening parenthesis for parameters")
        params: List[JavaNode] = []

        if self._current().value != ")":
            while True:
                ptype = self._parse_type()
                pname = self._advance().value
                params.append(JavaNode(kind="Param", value=pname, line=ptype.line, col=ptype.col, children=[ptype]))
                if self._current().value == ",":
                    self._advance()
                else:
                    break

        self._expect(")", "closing parenthesis for parameters")
        body = self._parse_block()

        param_list = JavaNode(kind="ParamList", line=start_tok.line, col=start_tok.col, children=params)
        return JavaNode(
            kind="MethodDef",
            value=name,
            line=start_tok.line,
            col=start_tok.col,
            children=[ret_type, param_list, body],
        )

    def _parse_type(self) -> JavaNode:
        tok = self._advance()
        tname = tok.value
        dims = 0
        while not self._is_at_end() and self._current().value == "[":
            self._advance()
            self._expect("]", "closing bracket for array type")
            dims += 1

        full_type = f"{tname}{'[]' * dims}"
        return JavaNode(kind="Type", value=full_type, line=tok.line, col=tok.col)

    # -------------------------------------------------------------------------
    # Statements
    # -------------------------------------------------------------------------

    def _parse_block(self) -> JavaNode:
        open_brace = self._expect("{", "opening brace for block")
        stmts: List[JavaNode] = []

        while not self._is_at_end() and self._current().value != "}":
            stmt = self._parse_statement()
            if stmt:
                if isinstance(stmt, list):
                    stmts.extend(stmt)
                else:
                    stmts.append(stmt)

        self._expect("}", "closing brace for block")
        return JavaNode(kind="Block", line=open_brace.line, col=open_brace.col, children=stmts)

    def _parse_statement(self) -> Optional[JavaNode | List[JavaNode]]:
        cur = self._current()

        if cur.value == ";":
            self._advance()
            return None

        if cur.value in ("try", "catch", "throw", "finally"):
            raise JavaSyntaxError("unsupported construct: exception handling", cur.line, cur.col)

        if cur.value == "{":
            return self._parse_block()

        if self._is_var_decl_start():
            return self._parse_var_decl()

        if cur.value == "if":
            return self._parse_if()
        if cur.value == "while":
            return self._parse_while()
        if cur.value == "for":
            return self._parse_for()
        if cur.value == "do":
            return self._parse_do_while()
        if cur.value == "switch":
            return self._parse_switch()
        if cur.value == "case":
            self._advance()
            val = self._parse_expr()
            self._expect(":", "after case")
            return JavaNode(kind="Case", line=cur.line, col=cur.col, children=[val])
        if cur.value == "default":
            self._advance()
            self._expect(":", "after default")
            return JavaNode(kind="Default", line=cur.line, col=cur.col)
        if cur.value == "return":
            self._advance()
            ret_val = self._parse_expr() if self._current().value != ";" else None
            self._expect(";", "after return")
            return JavaNode(kind="Return", line=cur.line, col=cur.col, children=[ret_val] if ret_val else [])
        if cur.value == "break":
            self._advance()
            self._expect(";", "after break")
            return JavaNode(kind="Break", line=cur.line, col=cur.col)
        if cur.value == "continue":
            self._advance()
            self._expect(";", "after continue")
            return JavaNode(kind="Continue", line=cur.line, col=cur.col)

        expr = self._parse_expr()
        self._expect(";", "after expression")
        return JavaNode(kind="ExprStmt", line=expr.line, col=expr.col, children=[expr])

    def _is_var_decl_start(self) -> bool:
        cur = self._current()
        if cur.value in JAVA_PRIMITIVE_TYPES:
            return True
        if cur.kind == "IDENTIFIER" and cur.value in ("Scanner", "String"):
            return True
        return False

    def _parse_var_decl(self) -> List[JavaNode]:
        vtype = self._parse_type()
        decls: List[JavaNode] = []

        while True:
            name_tok = self._advance()
            name = name_tok.value
            init_val = None
            if self._current().value == "=":
                self._advance()
                if self._current().value == "new":
                    init_val = self._parse_new_expr()
                elif self._current().value == "{":
                    init_val = self._parse_array_initializer()
                else:
                    init_val = self._parse_expr()

            children = [vtype]
            if init_val:
                children.append(init_val)

            decls.append(JavaNode(kind="VarDecl", value=name, line=name_tok.line, col=name_tok.col, children=children))

            if self._current().value == ",":
                self._advance()
            else:
                break

        self._expect(";", "after variable declaration")
        return decls

    def _parse_new_expr(self) -> JavaNode:
        new_tok = self._advance()
        type_tok = self._advance()
        if type_tok.value == "Scanner":
            self._expect("(", "after new Scanner")
            while not self._is_at_end() and self._current().value != ")":
                self._advance()
            self._expect(")", "closing parenthesis for new Scanner")
            return JavaNode(kind="NewScanner", line=new_tok.line, col=new_tok.col)
        elif self._current().value == "[":
            self._advance()
            size_expr = self._parse_expr()
            self._expect("]", "closing bracket for array allocation")
            return JavaNode(kind="NewArray", value=type_tok.value, line=new_tok.line, col=new_tok.col, children=[size_expr])
        return JavaNode(kind="NewExpr", value=type_tok.value, line=new_tok.line, col=new_tok.col)

    def _parse_array_initializer(self) -> JavaNode:
        open_brace = self._expect("{", "opening brace for array init")
        items = []
        if self._current().value != "}":
            while True:
                if self._current().value == "{":
                    items.append(self._parse_array_initializer())
                else:
                    items.append(self._parse_expr())
                if self._current().value == ",":
                    self._advance()
                    if self._current().value == "}":
                        break
                else:
                    break
        self._expect("}", "closing brace for array init")
        return JavaNode(kind="ArrayInit", line=open_brace.line, col=open_brace.col, children=items)

    def _parse_if(self) -> JavaNode:
        if_tok = self._advance()
        self._expect("(", "after if")
        cond = self._parse_expr()
        self._expect(")", "after if condition")
        then_branch = self._parse_statement()
        children = [cond, self._ensure_block(then_branch, if_tok.line)]

        if self._current().value == "else":
            self._advance()
            else_branch = self._parse_statement()
            children.append(self._ensure_block(else_branch, if_tok.line))

        return JavaNode(kind="If", line=if_tok.line, col=if_tok.col, children=children)

    def _parse_while(self) -> JavaNode:
        while_tok = self._advance()
        self._expect("(", "after while")
        cond = self._parse_expr()
        self._expect(")", "after while condition")
        body = self._parse_statement()
        return JavaNode(kind="While", line=while_tok.line, col=while_tok.col, children=[cond, self._ensure_block(body, while_tok.line)])

    def _parse_do_while(self) -> JavaNode:
        do_tok = self._advance()
        body = self._parse_statement()
        self._expect("while", "after do block")
        self._expect("(", "after while in do-while")
        cond = self._parse_expr()
        self._expect(")", "after condition")
        self._expect(";", "after do-while")
        return JavaNode(kind="DoWhile", line=do_tok.line, col=do_tok.col, children=[self._ensure_block(body, do_tok.line), cond])

    def _parse_for(self) -> JavaNode:
        for_tok = self._advance()
        self._expect("(", "after for")

        if self._is_var_decl_start():
            vtype = self._parse_type()
            vname = self._advance().value
            if self._current().value == ":":
                self._advance()
                iterable = self._parse_expr()
                self._expect(")", "after enhanced for header")
                body = self._parse_statement()
                return JavaNode(
                    kind="EnhancedFor",
                    value=vname,
                    line=for_tok.line,
                    col=for_tok.col,
                    children=[vtype, iterable, self._ensure_block(body, for_tok.line)],
                )

            self._expect("=", "in for init")
            init_val = self._parse_expr()
            self._expect(";", "after for init")
            init_node = JavaNode(kind="VarDecl", value=vname, line=for_tok.line, col=for_tok.col, children=[vtype, init_val])
        else:
            init_expr = self._parse_expr() if self._current().value != ";" else None
            self._expect(";", "after for init")
            init_node = JavaNode(kind="ExprStmt", line=for_tok.line, col=for_tok.col, children=[init_expr] if init_expr else [])

        cond_node = self._parse_expr() if self._current().value != ";" else JavaNode(kind="Literal", value="1", line=for_tok.line, col=for_tok.col)
        self._expect(";", "after for cond")

        step_expr = self._parse_expr() if self._current().value != ")" else None
        self._expect(")", "after for step")
        step_node = JavaNode(kind="ExprStmt", line=for_tok.line, col=for_tok.col, children=[step_expr] if step_expr else [])

        body = self._parse_statement()
        return JavaNode(kind="For", line=for_tok.line, col=for_tok.col, children=[init_node, cond_node, step_node, self._ensure_block(body, for_tok.line)])

    def _parse_switch(self) -> JavaNode:
        sw_tok = self._advance()
        self._expect("(", "after switch")
        expr = self._parse_expr()
        self._expect(")", "after switch condition")
        body = self._parse_statement()
        return JavaNode(kind="Switch", line=sw_tok.line, col=sw_tok.col, children=[expr, self._ensure_block(body, sw_tok.line)])

    def _ensure_block(self, stmt: Optional[JavaNode | List[JavaNode]], fallback_line: int) -> JavaNode:
        if stmt is None:
            return JavaNode(kind="Block", line=fallback_line, col=1)
        if isinstance(stmt, list):
            return JavaNode(kind="Block", line=fallback_line, col=1, children=stmt)
        if stmt.kind == "Block":
            return stmt
        return JavaNode(kind="Block", line=stmt.line, col=stmt.col, children=[stmt])


def parse_java(source: str) -> JavaNode:
    tokens = tokenize_java(source)
    return JavaParser(tokens).parse()
