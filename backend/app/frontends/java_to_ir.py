"""Translates Java AST into the shared CodeGuard Node IR.

Maps Java methods, primitive types, System.out.println, Math functions, Scanner reads,
and array declarations into equivalent C constructs.
"""

from __future__ import annotations
from typing import Dict, List, Optional, Tuple
from app.frontends.java_parser import JavaNode
from app.engine.ast_nodes import Node


JAVA_TO_C_TYPE = {
    "int": "int",
    "double": "double",
    "float": "float",
    "boolean": "bool",
    "char": "char",
    "byte": "signed char",
    "short": "short",
    "long": "long long",
    "void": "void",
    "String": "char*",
}


class JavaToIRTranslator:
    def __init__(self) -> None:
        self.scopes: List[Dict[str, str]] = []  # variable -> type
        self.array_lengths: Dict[str, str] = {}  # array variable -> size expression

    def translate(self, root: JavaNode) -> Node:
        ir_root = Node(kind="TranslationUnit", line=root.line, col=root.col)
        for child in root.children:
            if child.kind == "MethodDef":
                ir_func = self._translate_method(child)
                if ir_func:
                    ir_root.children.append(ir_func)
        return ir_root

    def _map_type(self, jtype: str) -> str:
        if jtype.endswith("[]"):
            inner = jtype[:-2]
            return f"{self._map_type(inner)}[]"
        return JAVA_TO_C_TYPE.get(jtype, jtype)

    def _enter_scope(self) -> None:
        self.scopes.append({})

    def _exit_scope(self) -> None:
        if self.scopes:
            self.scopes.pop()

    def _declare_var(self, name: str, vtype: str) -> None:
        if self.scopes:
            self.scopes[-1][name] = vtype

    def _get_var_type(self, name: str) -> str:
        for s in reversed(self.scopes):
            if name in s:
                return s[name]
        return "int"

    def _translate_method(self, node: JavaNode) -> Node:
        method_name = str(node.value)
        ret_type_str = self._map_type(node.children[0].value)

        # Convert Java main method signature to C main
        is_main = (method_name == "main")
        if is_main:
            ret_type_str = "int"

        ret_type_ir = Node(kind="Type", value=ret_type_str, line=node.line, col=node.col)
        self._enter_scope()

        param_list_ir = Node(kind="ParamList", line=node.children[1].line, col=node.children[1].col)
        if not is_main:
            for p in node.children[1].children:
                pname = str(p.value)
                ptype = self._map_type(p.children[0].value)
                self._declare_var(pname, ptype)
                param_list_ir.children.append(Node(
                    kind="Param",
                    value=pname,
                    line=p.line,
                    col=p.col,
                    children=[Node(kind="Type", value=ptype, line=p.line, col=p.col)],
                ))

        body_ir = self._translate_block(node.children[2])

        # If main in C does not end with return, add return 0;
        if is_main:
            has_return = any(s.kind == "Return" for s in body_ir.children)
            if not has_return:
                body_ir.children.append(Node(
                    kind="Return",
                    line=node.line,
                    col=node.col,
                    children=[Node(kind="Literal", value="0", line=node.line, col=node.col)],
                ))

        self._exit_scope()
        return Node(
            kind="FunctionDef",
            value=method_name,
            line=node.line,
            col=node.col,
            children=[ret_type_ir, param_list_ir, body_ir],
        )

    def _translate_block(self, node: JavaNode) -> Node:
        ir_block = Node(kind="Block", line=node.line, col=node.col)
        for child in node.children:
            stmt_ir = self._translate_stmt(child)
            if stmt_ir:
                if isinstance(stmt_ir, list):
                    ir_block.children.extend(stmt_ir)
                else:
                    ir_block.children.append(stmt_ir)
        return ir_block

    def _translate_stmt(self, node: JavaNode) -> Optional[Node | List[Node]]:
        if node.kind == "VarDecl":
            return self._translate_var_decl(node)
        elif node.kind == "ExprStmt":
            expr_ir = self._translate_expr(node.children[0])
            if expr_ir is None:
                return None
            return Node(kind="ExprStmt", line=node.line, col=node.col, children=[expr_ir])
        elif node.kind == "If":
            cond_ir = self._translate_expr(node.children[0])
            then_ir = self._translate_block(node.children[1])
            children = [cond_ir, then_ir]
            if len(node.children) > 2:
                children.append(self._translate_block(node.children[2]))
            return Node(kind="If", line=node.line, col=node.col, children=children)
        elif node.kind == "While":
            cond_ir = self._translate_expr(node.children[0])
            body_ir = self._translate_block(node.children[1])
            return Node(kind="While", line=node.line, col=node.col, children=[cond_ir, body_ir])
        elif node.kind == "DoWhile":
            body_ir = self._translate_block(node.children[0])
            cond_ir = self._translate_expr(node.children[1])
            return Node(kind="DoWhile", line=node.line, col=node.col, children=[body_ir, cond_ir])
        elif node.kind == "For":
            return self._translate_for(node)
        elif node.kind == "EnhancedFor":
            return self._translate_enhanced_for(node)
        elif node.kind == "Switch":
            expr_ir = self._translate_expr(node.children[0])
            body_ir = self._translate_block(node.children[1])
            return Node(kind="Switch", line=node.line, col=node.col, children=[expr_ir, body_ir])
        elif node.kind == "Case":
            val_ir = self._translate_expr(node.children[0])
            return Node(kind="Case", line=node.line, col=node.col, children=[val_ir])
        elif node.kind == "Default":
            return Node(kind="Default", line=node.line, col=node.col)
        elif node.kind == "Return":
            if node.children:
                ret_ir = self._translate_expr(node.children[0])
                return Node(kind="Return", line=node.line, col=node.col, children=[ret_ir])
            return Node(kind="Return", line=node.line, col=node.col)
        elif node.kind == "Break":
            return Node(kind="Break", line=node.line, col=node.col)
        elif node.kind == "Continue":
            return Node(kind="Continue", line=node.line, col=node.col)
        return None

    def _translate_var_decl(self, node: JavaNode) -> Optional[Node]:
        raw_type = node.children[0].value
        name = str(node.value)

        # Skip Scanner sc = new Scanner(...) declaration
        if raw_type == "Scanner":
            return None

        ctype = self._map_type(raw_type)
        self._declare_var(name, ctype)

        children = [Node(kind="Type", value=ctype, line=node.line, col=node.col)]

        if len(node.children) > 1:
            init_val = node.children[1]
            if init_val.kind == "NewArray":
                # int[] arr = new int[10]; -> int arr[10];
                size_expr = self._translate_expr(init_val.children[0])
                # Track array length for arr.length
                self.array_lengths[name] = str(size_expr.value if size_expr.kind == "Literal" else "")
                return Node(
                    kind="VarDecl",
                    value=name,
                    line=node.line,
                    col=node.col,
                    children=[
                        Node(kind="Type", value=ctype.replace("[]", ""), line=node.line, col=node.col),
                        size_expr,
                    ],
                )
            elif init_val.kind == "ArrayInit":
                items = [self._translate_expr(c) for c in init_val.children]
                children.append(Node(kind="InitList", line=node.line, col=node.col, children=items))
            else:
                children.append(self._translate_expr(init_val))

        return Node(kind="VarDecl", value=name, line=node.line, col=node.col, children=children)

    def _translate_for(self, node: JavaNode) -> Node:
        init_node = self._translate_stmt(node.children[0]) if node.children[0].children else Node(kind="Empty")
        cond_node = self._translate_expr(node.children[1])
        step_node = self._translate_stmt(node.children[2]) if node.children[2].children else Node(kind="Empty")
        body_node = self._translate_block(node.children[3])

        if isinstance(init_node, list):
            init_node = Node(kind="Block", line=node.line, col=node.col, children=init_node)

        return Node(
            kind="For",
            line=node.line,
            col=node.col,
            children=[init_node, cond_node, step_node, body_node],
        )

    def _translate_enhanced_for(self, node: JavaNode) -> Node:
        # for (int x : arr) { body }
        vname = str(node.value)
        vtype = self._map_type(node.children[0].value)
        iterable_ir = self._translate_expr(node.children[1])
        body_ir = self._translate_block(node.children[2])

        arr_name = str(iterable_ir.value)
        idx_var = f"_{arr_name}_idx"
        len_val = self.array_lengths.get(arr_name, "sizeof(%s)/sizeof(%s[0])" % (arr_name, arr_name))

        # Build C for-loop: for (int _i = 0; _i < len; _i++) { int x = arr[_i]; body }
        init_ir = Node(
            kind="VarDecl",
            value=idx_var,
            line=node.line,
            col=node.col,
            children=[Node(kind="Type", value="int"), Node(kind="Literal", value="0")],
        )
        cond_ir = Node(
            kind="BinaryOp",
            value="<",
            line=node.line,
            col=node.col,
            children=[Node(kind="Identifier", value=idx_var), Node(kind="Literal", value=len_val)],
        )
        step_ir = Node(
            kind="ExprStmt",
            line=node.line,
            col=node.col,
            children=[Node(kind="PostfixOp", value="++", children=[Node(kind="Identifier", value=idx_var)])],
        )

        extract_elem = Node(
            kind="VarDecl",
            value=vname,
            line=node.line,
            col=node.col,
            children=[
                Node(kind="Type", value=vtype),
                Node(kind="Index", children=[iterable_ir, Node(kind="Identifier", value=idx_var)]),
            ],
        )
        body_ir.children.insert(0, extract_elem)

        return Node(kind="For", line=node.line, col=node.col, children=[init_ir, cond_ir, step_ir, body_ir])

    def _translate_expr(self, node: JavaNode) -> Optional[Node]:
        if node.kind == "BinaryOp":
            left = self._translate_expr(node.children[0])
            right = self._translate_expr(node.children[1])
            return Node(kind="BinaryOp", value=str(node.value), line=node.line, col=node.col, children=[left, right])

        elif node.kind == "UnaryOp":
            operand = self._translate_expr(node.children[0])
            return Node(kind="UnaryOp", value=str(node.value), line=node.line, col=node.col, children=[operand])

        elif node.kind == "PostfixOp":
            operand = self._translate_expr(node.children[0])
            return Node(kind="PostfixOp", value=str(node.value), line=node.line, col=node.col, children=[operand])

        elif node.kind == "Assign":
            target = self._translate_expr(node.children[0])
            val = self._translate_expr(node.children[1])
            return Node(kind="Assign", value=str(node.value), line=node.line, col=node.col, children=[target, val])

        elif node.kind == "Ternary":
            cond = self._translate_expr(node.children[0])
            true_e = self._translate_expr(node.children[1])
            false_e = self._translate_expr(node.children[2])
            return Node(kind="Ternary", line=node.line, col=node.col, children=[cond, true_e, false_e])

        elif node.kind == "Call":
            return self._translate_call(node)

        elif node.kind == "Member":
            # arr.length
            base = self._translate_expr(node.children[0])
            mem = str(node.value)
            if mem == ".length":
                arr_n = str(base.value)
                len_v = self.array_lengths.get(arr_n, "sizeof(%s)/sizeof(%s[0])" % (arr_n, arr_n))
                return Node(kind="Literal", value=len_v, line=node.line, col=node.col)
            return Node(kind="Member", value=mem, line=node.line, col=node.col, children=[base])

        elif node.kind == "Index":
            base = self._translate_expr(node.children[0])
            idx = self._translate_expr(node.children[1])
            return Node(kind="Index", line=node.line, col=node.col, children=[base, idx])

        elif node.kind == "Literal":
            return Node(kind="Literal", value=str(node.value), line=node.line, col=node.col)

        elif node.kind == "Identifier":
            return Node(kind="Identifier", value=str(node.value), line=node.line, col=node.col)

        return None

    def _translate_call(self, node: JavaNode) -> Optional[Node]:
        callee = node.children[0]
        args_py = node.children[1].children

        # Full callee string (e.g. System.out.println, Math.max, sc.nextInt)
        callee_chain = self._extract_chain(callee)

        # 1. System.out.println / print / printf
        if callee_chain in ("System.out.println", "out.println"):
            return self._translate_println(args_py, node.line, node.col, newline=True)
        elif callee_chain in ("System.out.print", "out.print"):
            return self._translate_println(args_py, node.line, node.col, newline=False)
        elif callee_chain in ("System.out.printf", "out.printf"):
            args_ir = [self._translate_expr(a) for a in args_py]
            return Node(kind="Call", line=node.line, col=node.col, children=[
                Node(kind="Identifier", value="printf"),
                Node(kind="ArgList", children=args_ir),
            ])

        # 2. Scanner reads: sc.nextInt(), sc.nextDouble()
        elif callee_chain.endswith(".nextInt"):
            return Node(kind="Call", line=node.line, col=node.col, children=[
                Node(kind="Identifier", value="scanf"),
                Node(kind="ArgList", children=[Node(kind="Literal", value='"%d"')]),
            ])
        elif callee_chain.endswith(".nextDouble") or callee_chain.endswith(".nextFloat"):
            return Node(kind="Call", line=node.line, col=node.col, children=[
                Node(kind="Identifier", value="scanf"),
                Node(kind="ArgList", children=[Node(kind="Literal", value='"%lf"')]),
            ])

        # 3. Math functions
        elif callee_chain.startswith("Math."):
            math_func = callee_chain.split(".", 1)[1]
            args_ir = [self._translate_expr(a) for a in args_py]
            if math_func == "max" and len(args_ir) == 2:
                return Node(kind="Ternary", line=node.line, col=node.col, children=[
                    Node(kind="BinaryOp", value=">", children=[args_ir[0], args_ir[1]]),
                    args_ir[0],
                    args_ir[1],
                ])
            elif math_func == "min" and len(args_ir) == 2:
                return Node(kind="Ternary", line=node.line, col=node.col, children=[
                    Node(kind="BinaryOp", value="<", children=[args_ir[0], args_ir[1]]),
                    args_ir[0],
                    args_ir[1],
                ])
            c_math_name = {"pow": "pow", "sqrt": "sqrt", "abs": "abs", "floor": "floor", "ceil": "ceil"}.get(math_func, math_func)
            return Node(kind="Call", line=node.line, col=node.col, children=[
                Node(kind="Identifier", value=c_math_name),
                Node(kind="ArgList", children=args_ir),
            ])

        # Standard function call
        args_ir = [self._translate_expr(a) for a in args_py]
        func_name = callee_chain.split(".")[-1]
        return Node(kind="Call", line=node.line, col=node.col, children=[
            Node(kind="Identifier", value=func_name),
            Node(kind="ArgList", children=args_ir),
        ])

    def _extract_chain(self, node: JavaNode) -> str:
        if node.kind == "Identifier":
            return str(node.value)
        if node.kind == "Member":
            base = self._extract_chain(node.children[0])
            return f"{base}{node.value}"
        return ""

    def _translate_println(self, args_j: List[JavaNode], line: int, col: int, newline: bool = True) -> Node:
        nl_str = "\\n" if newline else ""
        if not args_j:
            return Node(kind="Call", line=line, col=col, children=[
                Node(kind="Identifier", value="printf"),
                Node(kind="ArgList", children=[Node(kind="Literal", value=f'"{nl_str}"')]),
            ])

        arg0 = args_j[0]
        arg0_ir = self._translate_expr(arg0)

        # String literal directly printed
        if arg0.kind == "Literal" and str(arg0.value).startswith('"'):
            content = str(arg0.value).strip('"')
            return Node(kind="Call", line=line, col=col, children=[
                Node(kind="Identifier", value="printf"),
                Node(kind="ArgList", children=[Node(kind="Literal", value=f'"{content}{nl_str}"')]),
            ])

        # Determine specifier: int -> %d, double -> %f, etc.
        vtype = self._get_var_type(str(arg0_ir.value if arg0_ir.kind == "Identifier" else ""))
        fmt = "%d"
        if vtype in ("double", "float"):
            fmt = "%f"
        elif vtype in ("char*", "String"):
            fmt = "%s"
        elif vtype == "char":
            fmt = "%c"

        return Node(kind="Call", line=line, col=col, children=[
            Node(kind="Identifier", value="printf"),
            Node(kind="ArgList", children=[Node(kind="Literal", value=f'"{fmt}{nl_str}"'), arg0_ir]),
        ])


def java_to_ir(root: JavaNode) -> Node:
    return JavaToIRTranslator().translate(root)
