"""C Code Generator for CodeGuard.

Translates the shared Node IR into readable, standards-compliant, compilable C source code.
Emits necessary standard library headers, forward declarations, and indents code cleanly.
"""

from __future__ import annotations
from typing import List, Optional, Set
from app.engine.ast_nodes import Node


class CCodeGenerator:
    def __init__(self, indent_size: int = 4) -> None:
        self.indent_size = indent_size
        self.headers: Set[str] = set()

    def generate(self, root: Node) -> str:
        """Entry point: converts shared IR root into complete C source text."""
        self.headers.clear()

        # First pass: generate code body and collect required headers
        body_lines: List[str] = []
        if root.kind == "TranslationUnit":
            for child in root.children:
                code = self._generate_node(child, indent_level=0)
                if code.strip():
                    body_lines.append(code)
        else:
            code = self._generate_node(root, indent_level=0)
            if code.strip():
                body_lines.append(code)

        # Build final source with headers at top
        header_lines: List[str] = []
        # Standard default headers
        std_headers = sorted(list(self.headers))
        for h in std_headers:
            header_lines.append(f"#include <{h}>")

        full_parts = []
        if header_lines:
            full_parts.append("\n".join(header_lines))
        if body_lines:
            full_parts.append("\n\n".join(body_lines))

        return "\n\n".join(full_parts) + "\n"

    def _indent(self, level: int) -> str:
        return " " * (level * self.indent_size)

    def _generate_node(self, node: Node, indent_level: int = 0) -> str:
        pad = self._indent(indent_level)

        if node.kind == "FunctionDef":
            ret_type = self._generate_type(node.children[0])
            name = str(node.value)
            param_list = self._generate_param_list(node.children[1])
            body_block = self._generate_node(node.children[2], indent_level)
            return f"{pad}{ret_type} {name}({param_list}) {body_block.lstrip()}"

        elif node.kind == "FunctionDecl":
            ret_type = self._generate_type(node.children[0])
            name = str(node.value)
            param_list = self._generate_param_list(node.children[1])
            return f"{pad}{ret_type} {name}({param_list});"

        elif node.kind == "Block":
            lines = [f"{pad}{{"]
            for child in node.children:
                stmt_code = self._generate_node(child, indent_level + 1)
                if stmt_code.strip():
                    lines.append(stmt_code)
            lines.append(f"{pad}}}")
            return "\n".join(lines)

        elif node.kind == "VarDecl":
            vtype = self._generate_type(node.children[0])
            name = str(node.value)
            if vtype.endswith("[]"):
                vtype = vtype[:-2]
                name = f"{name}[]"
            init_code = ""
            if len(node.children) > 1:
                # Could be dims or initializer
                last_child = node.children[-1]
                if last_child.kind == "InitList":
                    init_code = f" = {self._generate_node(last_child)}"
                elif last_child.kind != "Type":
                    init_code = f" = {self._generate_node(last_child)}"
            return f"{pad}{vtype} {name}{init_code};"

        elif node.kind == "ExprStmt":
            expr_code = self._generate_node(node.children[0], 0)
            return f"{pad}{expr_code};"

        elif node.kind == "If":
            cond = self._generate_node(node.children[0], 0)
            then_block = self._generate_node(node.children[1], indent_level)
            code = f"{pad}if ({cond}) {then_block.lstrip()}"
            if len(node.children) > 2:
                else_block = self._generate_node(node.children[2], indent_level)
                code += f" else {else_block.lstrip()}"
            return code

        elif node.kind in ("While", "Loop"):
            cond = self._generate_node(node.children[0], 0)
            body = self._generate_node(node.children[1], indent_level)
            return f"{pad}while ({cond}) {body.lstrip()}"

        elif node.kind == "For":
            init_node = node.children[0]
            cond_node = node.children[1]
            step_node = node.children[2]
            body_node = node.children[3]

            init_str = self._generate_for_init(init_node)
            cond_str = self._generate_node(cond_node, 0) if cond_node.kind != "Empty" else ""
            step_str = self._generate_for_step(step_node)
            body_str = self._generate_node(body_node, indent_level)
            return f"{pad}for ({init_str}; {cond_str}; {step_str}) {body_str.lstrip()}"

        elif node.kind == "DoWhile":
            body = self._generate_node(node.children[0], indent_level)
            cond = self._generate_node(node.children[1], 0)
            return f"{pad}do {body.lstrip()} while ({cond});"

        elif node.kind == "Switch":
            expr = self._generate_node(node.children[0], 0)
            body = self._generate_node(node.children[1], indent_level)
            return f"{pad}switch ({expr}) {body.lstrip()}"

        elif node.kind == "Case":
            val = self._generate_node(node.children[0], 0)
            return f"{pad}case {val}:"

        elif node.kind == "Default":
            return f"{pad}default:"

        elif node.kind == "Return":
            if node.children:
                ret_val = self._generate_node(node.children[0], 0)
                return f"{pad}return {ret_val};"
            return f"{pad}return;"

        elif node.kind == "Break":
            return f"{pad}break;"

        elif node.kind == "Continue":
            return f"{pad}continue;"

        elif node.kind == "BinaryOp":
            left = self._generate_node(node.children[0], 0)
            right = self._generate_node(node.children[1], 0)
            op = str(node.value)
            return f"({left} {op} {right})"

        elif node.kind == "UnaryOp":
            operand = self._generate_node(node.children[0], 0)
            op = str(node.value)
            return f"{op}({operand})"

        elif node.kind == "PostfixOp":
            operand = self._generate_node(node.children[0], 0)
            op = str(node.value)
            return f"{operand}{op}"

        elif node.kind == "Assign":
            target = self._generate_node(node.children[0], 0)
            val = self._generate_node(node.children[1], 0)
            op = str(node.value)
            return f"{target} {op} {val}"

        elif node.kind == "Ternary":
            cond = self._generate_node(node.children[0], 0)
            true_expr = self._generate_node(node.children[1], 0)
            false_expr = self._generate_node(node.children[2], 0)
            return f"({cond} ? {true_expr} : {false_expr})"

        elif node.kind == "Call":
            callee = self._generate_node(node.children[0], 0)
            arg_list = node.children[1]
            args_str = ", ".join(self._generate_node(arg, 0) for arg in arg_list.children)
            if callee in ("printf", "scanf", "puts"):
                self.headers.add("stdio.h")
            elif callee in ("malloc", "free", "abs", "exit"):
                self.headers.add("stdlib.h")
            elif callee in ("pow", "sqrt", "sin", "cos", "tan", "floor", "ceil"):
                self.headers.add("math.h")
            return f"{callee}({args_str})"

        elif node.kind == "Index":
            arr = self._generate_node(node.children[0], 0)
            idx = self._generate_node(node.children[1], 0)
            return f"{arr}[{idx}]"

        elif node.kind == "Member":
            obj = self._generate_node(node.children[0], 0)
            mem = str(node.value)
            return f"{obj}{mem}"

        elif node.kind == "Sizeof":
            arg = self._generate_node(node.children[0], 0)
            return f"sizeof({arg})"

        elif node.kind == "Cast":
            ctype = self._generate_type(node.children[0])
            val = self._generate_node(node.children[1], 0)
            return f"(({ctype}) {val})"

        elif node.kind == "InitList":
            items = ", ".join(self._generate_node(c, 0) for c in node.children)
            return f"{{{items}}}"

        elif node.kind == "Literal":
            val = str(node.value)
            if val in ("true", "false"):
                self.headers.add("stdbool.h")
            return val

        elif node.kind == "Identifier":
            return str(node.value)

        elif node.kind == "Empty":
            return ""

        return str(node.value or "")

    def _generate_type(self, node: Node) -> str:
        t_val = str(node.value) if node.value else "int"
        if "bool" in t_val:
            self.headers.add("stdbool.h")
        return t_val

    def _generate_param_list(self, node: Node) -> str:
        if not node.children:
            return "void"
        parts = []
        for param in node.children:
            ptype = self._generate_type(param.children[0])
            pname = str(param.value)
            parts.append(f"{ptype} {pname}".strip())
        return ", ".join(parts)

    def _generate_for_init(self, node: Node) -> str:
        if node.kind == "Empty":
            return ""
        if node.kind == "VarDecl":
            return self._generate_node(node, 0).rstrip(";")
        if node.kind == "Block":
            # Multi-declarators or sequence
            stmts = [self._generate_node(s, 0).rstrip(";") for s in node.children]
            return ", ".join(stmts)
        if node.kind == "ExprStmt":
            return self._generate_node(node.children[0], 0)
        return self._generate_node(node, 0).rstrip(";")

    def _generate_for_step(self, node: Node) -> str:
        if node.kind == "Empty":
            return ""
        if node.kind == "ExprStmt":
            return self._generate_node(node.children[0], 0)
        return self._generate_node(node, 0).rstrip(";")


def generate_c(root: Node) -> str:
    """Convenience helper to convert Node IR into C code."""
    generator = CCodeGenerator()
    return generator.generate(root)
