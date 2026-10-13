"""Translates typed Python AST into the shared CodeGuard Node IR.

Performs local type inference for variables, lowers range() loops into canonical C For loops,
and translates Python print() into C printf() with appropriate format specifiers.
"""

from __future__ import annotations
from typing import Dict, List, Optional, Set, Tuple
from app.frontends.py_parser import PyNode
from app.engine.ast_nodes import Node


TYPE_MAP = {
    "int": "int",
    "float": "double",
    "bool": "bool",
    "str": "char*",
    "None": "void",
    "void": "void",
}

OP_MAP = {
    "and": "&&",
    "or": "||",
    "not": "!",
    "//": "/",
    "//=": "/=",
}


class PythonToIRTranslator:
    def __init__(self) -> None:
        self.scopes: List[Dict[str, str]] = []  # variable name -> type
        self.func_signatures: Dict[str, Tuple[str, List[str]]] = {}

    def translate(self, root: PyNode) -> Node:
        # Pre-scan function signatures for inter-procedural type inference
        for child in root.children:
            if child.kind == "FunctionDef":
                ret_t = self._map_type(child.children[0].value)
                param_types = [self._map_type(p.children[0].value) for p in child.children[1].children]
                self.func_signatures[str(child.value)] = (ret_t, param_types)

        ir_root = Node(kind="TranslationUnit", line=root.line, col=root.col)
        for child in root.children:
            ir_child = self._translate_top_level(child)
            if ir_child:
                ir_root.children.append(ir_child)

        return ir_root

    def _map_type(self, py_type: str) -> str:
        if py_type.endswith("[]"):
            inner = py_type[:-2]
            return f"{self._map_type(inner)}[]"
        return TYPE_MAP.get(py_type, py_type)

    def _enter_scope(self) -> None:
        self.scopes.append({})

    def _exit_scope(self) -> None:
        if self.scopes:
            self.scopes.pop()

    def _declare_var(self, name: str, vtype: str) -> bool:
        if not self.scopes:
            return True
        cur_scope = self.scopes[-1]
        if name in cur_scope:
            return False
        cur_scope[name] = vtype
        return True

    def _get_var_type(self, name: str) -> str:
        for scope in reversed(self.scopes):
            if name in scope:
                return scope[name]
        return "int"

    def _translate_top_level(self, node: PyNode) -> Optional[Node]:
        if node.kind == "FunctionDef":
            return self._translate_function(node)
        return None

    def _translate_function(self, node: PyNode) -> Node:
        func_name = str(node.value)
        ret_type_val = self._map_type(node.children[0].value)
        ret_type_node = Node(kind="Type", value=ret_type_val, line=node.line, col=node.col)

        self._enter_scope()

        # Parameters
        param_list_ir = Node(kind="ParamList", line=node.children[1].line, col=node.children[1].col)
        for param in node.children[1].children:
            pname = str(param.value)
            ptype_val = self._map_type(param.children[0].value)
            self._declare_var(pname, ptype_val)
            param_list_ir.children.append(Node(
                kind="Param",
                value=pname,
                line=param.line,
                col=param.col,
                children=[Node(kind="Type", value=ptype_val, line=param.line, col=param.col)],
            ))

        body_ir = self._translate_block(node.children[2])
        self._exit_scope()

        return Node(
            kind="FunctionDef",
            value=func_name,
            line=node.line,
            col=node.col,
            children=[ret_type_node, param_list_ir, body_ir],
        )

    def _translate_block(self, node: PyNode) -> Node:
        ir_block = Node(kind="Block", line=node.line, col=node.col)
        for child in node.children:
            stmt_ir = self._translate_stmt(child)
            if stmt_ir:
                if isinstance(stmt_ir, list):
                    ir_block.children.extend(stmt_ir)
                else:
                    ir_block.children.append(stmt_ir)
        return ir_block

    def _translate_stmt(self, node: PyNode) -> Optional[Node | List[Node]]:
        if node.kind == "Assign":
            return self._translate_assign(node)
        elif node.kind == "ExprStmt":
            expr_ir = self._translate_expr(node.children[0])
            return Node(kind="ExprStmt", line=node.line, col=node.col, children=[expr_ir])
        elif node.kind == "If":
            cond_ir = self._translate_expr(node.children[0])
            then_ir = self._translate_block(node.children[1])
            children = [cond_ir, then_ir]
            if len(node.children) > 2:
                else_ir = self._translate_block(node.children[2])
                children.append(else_ir)
            return Node(kind="If", line=node.line, col=node.col, children=children)
        elif node.kind == "While":
            cond_ir = self._translate_expr(node.children[0])
            body_ir = self._translate_block(node.children[1])
            return Node(kind="While", line=node.line, col=node.col, children=[cond_ir, body_ir])
        elif node.kind == "For":
            return self._translate_for(node)
        elif node.kind == "Return":
            if node.children:
                ret_expr = self._translate_expr(node.children[0])
                return Node(kind="Return", line=node.line, col=node.col, children=[ret_expr])
            return Node(kind="Return", line=node.line, col=node.col)
        elif node.kind == "Break":
            return Node(kind="Break", line=node.line, col=node.col)
        elif node.kind == "Continue":
            return Node(kind="Continue", line=node.line, col=node.col)
        elif node.kind == "Pass":
            return None
        return None

    def _translate_assign(self, node: PyNode) -> Node | List[Node]:
        target_py = node.children[0]
        val_py = node.children[1]

        val_ir = self._translate_expr(val_py)
        inferred_type = self._infer_type(val_py)

        # Check if list initialization: arr = [1, 2, 3]
        if val_py.kind == "ListLiteral":
            name = str(target_py.value)
            self._declare_var(name, f"{inferred_type}[]")
            type_node = Node(kind="Type", value=f"{inferred_type}[]", line=node.line, col=node.col)
            return Node(kind="VarDecl", value=name, line=node.line, col=node.col, children=[type_node, val_ir])

        if target_py.kind == "Identifier" and node.value == "=":
            name = str(target_py.value)
            is_new = self._declare_var(name, inferred_type)
            if is_new:
                # Declare variable with initializer
                type_node = Node(kind="Type", value=inferred_type, line=node.line, col=node.col)
                return Node(kind="VarDecl", value=name, line=node.line, col=node.col, children=[type_node, val_ir])

        # Standard assignment
        target_ir = self._translate_expr(target_py)
        op = OP_MAP.get(str(node.value), str(node.value))
        return Node(
            kind="ExprStmt",
            line=node.line,
            col=node.col,
            children=[Node(kind="Assign", value=op, line=node.line, col=node.col, children=[target_ir, val_ir])],
        )

    def _translate_for(self, node: PyNode) -> Node:
        var_name = str(node.value)
        iterable_py = node.children[1]
        body_py = node.children[2]

        # Handle range(...)
        if iterable_py.kind == "Call" and iterable_py.children[0].value == "range":
            args = iterable_py.children[1].children
            start_ir = Node(kind="Literal", value="0", line=node.line, col=node.col)
            step_ir = Node(kind="Literal", value="1", line=node.line, col=node.col)

            if len(args) == 1:
                stop_ir = self._translate_expr(args[0])
            elif len(args) == 2:
                start_ir = self._translate_expr(args[0])
                stop_ir = self._translate_expr(args[1])
            elif len(args) == 3:
                start_ir = self._translate_expr(args[0])
                stop_ir = self._translate_expr(args[1])
                step_ir = self._translate_expr(args[2])
            else:
                stop_ir = Node(kind="Literal", value="0", line=node.line, col=node.col)

            self._declare_var(var_name, "int")

            init_node = Node(
                kind="VarDecl",
                value=var_name,
                line=node.line,
                col=node.col,
                children=[Node(kind="Type", value="int", line=node.line, col=node.col), start_ir],
            )
            cond_node = Node(
                kind="BinaryOp",
                value="<",
                line=node.line,
                col=node.col,
                children=[Node(kind="Identifier", value=var_name, line=node.line, col=node.col), stop_ir],
            )
            step_node = Node(
                kind="ExprStmt",
                line=node.line,
                col=node.col,
                children=[
                    Node(
                        kind="Assign",
                        value="+=",
                        line=node.line,
                        col=node.col,
                        children=[Node(kind="Identifier", value=var_name, line=node.line, col=node.col), step_ir],
                    )
                ],
            )

            body_ir = self._translate_block(body_py)
            return Node(kind="For", line=node.line, col=node.col, children=[init_node, cond_node, step_node, body_ir])

        # Fallback for general loops
        body_ir = self._translate_block(body_py)
        return Node(kind="While", line=node.line, col=node.col, children=[Node(kind="Literal", value="1"), body_ir])

    def _translate_expr(self, node: PyNode) -> Node:
        if node.kind == "BinaryOp":
            op = OP_MAP.get(str(node.value), str(node.value))
            if op == "**":
                # Lower x ** y to pow(x, y)
                base = self._translate_expr(node.children[0])
                exp = self._translate_expr(node.children[1])
                return Node(
                    kind="Call",
                    line=node.line,
                    col=node.col,
                    children=[
                        Node(kind="Identifier", value="pow", line=node.line, col=node.col),
                        Node(kind="ArgList", line=node.line, col=node.col, children=[base, exp]),
                    ],
                )
            left = self._translate_expr(node.children[0])
            right = self._translate_expr(node.children[1])
            return Node(kind="BinaryOp", value=op, line=node.line, col=node.col, children=[left, right])

        elif node.kind == "UnaryOp":
            op = OP_MAP.get(str(node.value), str(node.value))
            operand = self._translate_expr(node.children[0])
            return Node(kind="UnaryOp", value=op, line=node.line, col=node.col, children=[operand])

        elif node.kind == "Call":
            callee_name = str(node.children[0].value)
            args_py = node.children[1].children

            if callee_name == "print":
                return self._translate_print(args_py, node.line, node.col)
            elif callee_name == "input":
                # Convert input() to scanf read into a buffer or expression
                return Node(kind="Call", line=node.line, col=node.col, children=[
                    Node(kind="Identifier", value="scanf", line=node.line, col=node.col),
                    Node(kind="ArgList", line=node.line, col=node.col, children=[Node(kind="Literal", value='"%d"')]),
                ])
            elif callee_name == "len":
                # len(arr) -> sizeof(arr)/sizeof(arr[0]) or identifier
                arr_ir = self._translate_expr(args_py[0])
                return Node(kind="Call", line=node.line, col=node.col, children=[
                    Node(kind="Identifier", value="sizeof", line=node.line, col=node.col),
                    Node(kind="ArgList", line=node.line, col=node.col, children=[arr_ir]),
                ])

            args_ir = [self._translate_expr(a) for a in args_py]
            return Node(
                kind="Call",
                line=node.line,
                col=node.col,
                children=[
                    Node(kind="Identifier", value=callee_name, line=node.line, col=node.col),
                    Node(kind="ArgList", line=node.line, col=node.col, children=args_ir),
                ],
            )

        elif node.kind == "ListLiteral":
            items_ir = [self._translate_expr(c) for c in node.children]
            return Node(kind="InitList", line=node.line, col=node.col, children=items_ir)

        elif node.kind == "Index":
            arr_ir = self._translate_expr(node.children[0])
            idx_ir = self._translate_expr(node.children[1])
            return Node(kind="Index", line=node.line, col=node.col, children=[arr_ir, idx_ir])

        elif node.kind == "Literal":
            return Node(kind="Literal", value=str(node.value), line=node.line, col=node.col)

        elif node.kind == "Identifier":
            return Node(kind="Identifier", value=str(node.value), line=node.line, col=node.col)

        return Node(kind="Literal", value=str(node.value or "0"), line=node.line, col=node.col)

    def _translate_print(self, args_py: List[PyNode], line: int, col: int) -> Node:
        fmt_parts: List[str] = []
        fmt_args: List[Node] = []

        for arg in args_py:
            arg_t = self._infer_type(arg)
            if arg.kind == "Literal" and str(arg.value).startswith('"'):
                raw_str = str(arg.value).strip('"')
                fmt_parts.append(raw_str)
            else:
                arg_ir = self._translate_expr(arg)
                fmt_args.append(arg_ir)
                if arg_t == "int":
                    fmt_parts.append("%d")
                elif arg_t == "double":
                    fmt_parts.append("%f")
                elif arg_t == "char*":
                    fmt_parts.append("%s")
                else:
                    fmt_parts.append("%d")

        fmt_str = " ".join(fmt_parts) + "\\n"
        call_args = [Node(kind="Literal", value=f'"{fmt_str}"', line=line, col=col)] + fmt_args

        return Node(
            kind="Call",
            line=line,
            col=col,
            children=[
                Node(kind="Identifier", value="printf", line=line, col=col),
                Node(kind="ArgList", line=line, col=col, children=call_args),
            ],
        )

    def _infer_type(self, node: PyNode) -> str:
        if node.kind == "Literal":
            val = str(node.value)
            if val.startswith('"') or val.startswith("'"):
                return "char*"
            if "." in val:
                return "double"
            if val in ("true", "false"):
                return "bool"
            return "int"
        elif node.kind == "Identifier":
            return self._get_var_type(str(node.value))
        elif node.kind == "BinaryOp":
            if node.value in ("/",):
                return "double"
            if node.value in ("<", "<=", ">", ">=", "==", "!=", "and", "or"):
                return "bool"
            t_left = self._infer_type(node.children[0])
            t_right = self._infer_type(node.children[1])
            if "double" in (t_left, t_right):
                return "double"
            return "int"
        elif node.kind == "ListLiteral":
            elem_t = self._infer_type(node.children[0]) if node.children else "int"
            return elem_t
        elif node.kind == "Call":
            fname = str(node.children[0].value)
            if fname in self.func_signatures:
                return self.func_signatures[fname][0]
        return "int"


def python_to_ir(root: PyNode) -> Node:
    return PythonToIRTranslator().translate(root)
