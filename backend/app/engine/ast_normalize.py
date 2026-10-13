"""AST Canonicalization (Normalization) pass for CodeGuard.

Collapses semantically equivalent constructs into canonical forms BEFORE similarity computation:
- for/while/do-while loops into canonical Loop shapes with lifted inits
- redundant nested blocks flattened
- compound assignments and ++/-- desugared into standard assignments
- if/else return or assign collapsed to ternary
- commutative binary operators sorted canonically
- boolean negations and De Morgan laws normalized
- declarations with initializers split and separated into decl + assign
"""

from __future__ import annotations
from typing import List, Optional, Set, Tuple
from app.engine.ast_nodes import Node


COMMUTATIVE_OPS: Set[str] = {"+", "*", "==", "!=", "&&", "||", "&", "|", "^"}

COMPOUND_ASSIGN_MAP = {
    "+=": "+",
    "-=": "-",
    "*=": "*",
    "/=": "/",
    "%=": "%",
    "&=": "&",
    "|=": "|",
    "^=": "^",
    "<<=": "<<",
    ">>=": ">>",
}


def node_order_key(node: Node) -> Tuple:
    """Deterministic structural ordering key for sorting commutative operands."""
    val_str = str(node.value) if node.value is not None else ""
    return (
        node.kind,
        val_str,
        len(node.children),
        tuple(node_order_key(c) for c in node.children)
    )


class ASTNormalizer:
    def __init__(self) -> None:
        pass

    def normalize(self, root: Node) -> Node:
        """Run normalization passes until reaching a fixed point (idempotent)."""
        prev = root.clone()
        while True:
            curr = self._transform(prev)
            if curr == prev:
                break
            prev = curr
        return prev

    def _transform(self, node: Node) -> Node:
        # First recursively transform children
        transformed_children: List[Node] = []
        for child in node.children:
            transformed_children.append(self._transform(child))

        new_node = Node(
            kind=node.kind,
            value=node.value,
            children=transformed_children,
            line=node.line,
            col=node.col,
        )

        # Apply transformations based on kind
        if new_node.kind == "TranslationUnit":
            return self._normalize_sequence(new_node)
        elif new_node.kind == "Block":
            return self._normalize_block(new_node)
        elif new_node.kind == "For":
            return self._normalize_for(new_node)
        elif new_node.kind == "While":
            return self._normalize_while(new_node)
        elif new_node.kind == "DoWhile":
            return self._normalize_do_while(new_node)
        elif new_node.kind == "Assign":
            return self._normalize_assign(new_node)
        elif new_node.kind in ("UnaryOp", "PostfixOp"):
            return self._normalize_inc_dec(new_node)
        elif new_node.kind == "BinaryOp":
            return self._normalize_binary_op(new_node)
        elif new_node.kind == "If":
            return self._normalize_if(new_node)
        elif new_node.kind == "ExprStmt":
            return self._normalize_expr_stmt(new_node)

        return new_node

    # -------------------------------------------------------------------------
    # Block & Sequence Normalization
    # -------------------------------------------------------------------------

    def _normalize_block(self, block: Node) -> Node:
        """Flatten redundant nested blocks, expand declarations with initializers and loops."""
        flattened: List[Node] = []
        for child in block.children:
            if child.kind == "Block":
                # Flatten nested block
                flattened.extend(child.children)
            elif child.kind == "VarDecl" and len(child.children) > 1:
                # VarDecl with initializer: split into VarDecl (type only) + Assign
                vtype = child.children[0]
                init_val = child.children[-1]
                flattened.append(Node(
                    kind="VarDecl",
                    value=child.value,
                    children=[vtype],
                    line=child.line,
                    col=child.col,
                ))
                flattened.append(Node(
                    kind="ExprStmt",
                    children=[
                        Node(
                            kind="Assign",
                            value="=",
                            children=[
                                Node(kind="Identifier", value=child.value, line=child.line, col=child.col),
                                init_val,
                            ],
                            line=child.line,
                            col=child.col,
                        )
                    ],
                    line=child.line,
                    col=child.col,
                ))
            elif child.kind == "For":
                # Expand for into init + Loop
                init_node = child.children[0]
                cond_node = child.children[1]
                step_node = child.children[2]
                body_node = child.children[3]

                # If init is not empty, add init statements
                if init_node.kind == "Block":
                    flattened.extend(self._normalize_block(init_node).children)
                elif init_node.kind != "Empty":
                    flattened.append(init_node)

                # Step goes to end of body
                body_stmts = body_node.children if body_node.kind == "Block" else [body_node]
                new_body_stmts = list(body_stmts)
                if step_node.kind != "Empty":
                    new_body_stmts.append(step_node)

                flattened.append(Node(
                    kind="Loop",
                    children=[cond_node, Node(kind="Block", children=new_body_stmts, line=body_node.line, col=body_node.col)],
                    line=child.line,
                    col=child.col,
                ))
            else:
                flattened.append(child)

        # Second pass to ensure any nested blocks created during expansion are flattened
        res_stmts: List[Node] = []
        for stmt in flattened:
            if stmt.kind == "Block":
                res_stmts.extend(stmt.children)
            else:
                res_stmts.append(stmt)

        return Node(kind="Block", children=res_stmts, line=block.line, col=block.col)

    def _normalize_sequence(self, seq: Node) -> Node:
        """Normalize translation unit top-level declarations."""
        new_children: List[Node] = []
        for child in seq.children:
            if child.kind == "VarDecl" and len(child.children) > 1:
                # Top level var decl with init
                vtype = child.children[0]
                init_val = child.children[-1]
                new_children.append(Node(kind="VarDecl", value=child.value, children=[vtype], line=child.line, col=child.col))
                new_children.append(Node(
                    kind="ExprStmt",
                    children=[Node(
                        kind="Assign",
                        value="=",
                        children=[Node(kind="Identifier", value=child.value, line=child.line, col=child.col), init_val],
                        line=child.line,
                        col=child.col,
                    )],
                    line=child.line,
                    col=child.col,
                ))
            else:
                new_children.append(child)
        return Node(kind=seq.kind, value=seq.value, children=new_children, line=seq.line, col=seq.col)

    # -------------------------------------------------------------------------
    # Loop Canonicalization
    # -------------------------------------------------------------------------

    def _normalize_for(self, for_node: Node) -> Node:
        """Standalone for-loop (not inside a block): wrap in Block([init, Loop])."""
        init_node = for_node.children[0]
        cond_node = for_node.children[1]
        step_node = for_node.children[2]
        body_node = for_node.children[3]

        body_stmts = body_node.children if body_node.kind == "Block" else [body_node]
        new_body_stmts = list(body_stmts)
        if step_node.kind != "Empty":
            new_body_stmts.append(step_node)

        loop_node = Node(
            kind="Loop",
            children=[cond_node, Node(kind="Block", children=new_body_stmts, line=body_node.line, col=body_node.col)],
            line=for_node.line,
            col=for_node.col,
        )

        if init_node.kind == "Empty":
            return loop_node
        elif init_node.kind == "Block":
            return Node(kind="Block", children=init_node.children + [loop_node], line=for_node.line, col=for_node.col)
        else:
            return Node(kind="Block", children=[init_node, loop_node], line=for_node.line, col=for_node.col)

    def _normalize_while(self, while_node: Node) -> Node:
        cond = while_node.children[0]
        body = while_node.children[1]
        body_block = body if body.kind == "Block" else Node(kind="Block", children=[body], line=body.line, col=body.col)
        return Node(kind="Loop", children=[cond, body_block], line=while_node.line, col=while_node.col)

    def _normalize_do_while(self, do_while_node: Node) -> Node:
        body = do_while_node.children[0]
        cond = do_while_node.children[1]
        body_block = body if body.kind == "Block" else Node(kind="Block", children=[body], line=body.line, col=body.col)
        return Node(kind="Loop", children=[cond, body_block], line=do_while_node.line, col=do_while_node.col)

    # -------------------------------------------------------------------------
    # Compound Assignments, Increments, and Commutative Operators
    # -------------------------------------------------------------------------

    def _normalize_assign(self, assign_node: Node) -> Node:
        op = str(assign_node.value)
        if op in COMPOUND_ASSIGN_MAP:
            target = assign_node.children[0]
            val = assign_node.children[1]
            bin_op = COMPOUND_ASSIGN_MAP[op]
            expanded_expr = Node(
                kind="BinaryOp",
                value=bin_op,
                children=[target.clone(), val],
                line=assign_node.line,
                col=assign_node.col,
            )
            # Re-normalize the binary op (sorting operands if commutative)
            norm_bin = self._normalize_binary_op(expanded_expr)
            return Node(
                kind="Assign",
                value="=",
                children=[target, norm_bin],
                line=assign_node.line,
                col=assign_node.col,
            )
        return assign_node

    def _normalize_inc_dec(self, op_node: Node) -> Node:
        """Desugar i++ / ++i into i = i + 1, and i-- / --i into i = i - 1."""
        op = str(op_node.value)
        if op in ("++", "--"):
            target = op_node.children[0]
            bin_op = "+" if op == "++" else "-"
            val_one = Node(kind="Literal", value="1", line=op_node.line, col=op_node.col)
            bin_node = Node(
                kind="BinaryOp",
                value=bin_op,
                children=[target.clone(), val_one],
                line=op_node.line,
                col=op_node.col,
            )
            return Node(
                kind="Assign",
                value="=",
                children=[target, bin_node],
                line=op_node.line,
                col=op_node.col,
            )
        elif op == "!":
            # De Morgan and relational negation
            inner = op_node.children[0]
            return self._negate_condition(inner, op_node.line, op_node.col)
        return op_node

    def _negate_condition(self, node: Node, line: int, col: int) -> Node:
        # Relational operator inversions
        inv_map = {
            "<": ">=",
            "<=": ">",
            ">": "<=",
            ">=": "<",
            "==": "!=",
            "!=": "==",
        }
        if node.kind == "BinaryOp" and node.value in inv_map:
            return Node(
                kind="BinaryOp",
                value=inv_map[str(node.value)],
                children=node.children,
                line=line,
                col=col,
            )
        # De Morgan: !(a && b) -> !a || !b; !(a || b) -> !a && !b
        if node.kind == "BinaryOp" and node.value == "&&":
            left_neg = self._negate_condition(node.children[0], line, col)
            right_neg = self._negate_condition(node.children[1], line, col)
            return Node(kind="BinaryOp", value="||", children=[left_neg, right_neg], line=line, col=col)
        if node.kind == "BinaryOp" and node.value == "||":
            left_neg = self._negate_condition(node.children[0], line, col)
            right_neg = self._negate_condition(node.children[1], line, col)
            return Node(kind="BinaryOp", value="&&", children=[left_neg, right_neg], line=line, col=col)
        # !!a -> a
        if node.kind == "UnaryOp" and node.value == "!":
            return node.children[0]
        # Fallback to !node
        return Node(kind="UnaryOp", value="!", children=[node], line=line, col=col)

    def _normalize_binary_op(self, bin_node: Node) -> Node:
        op = str(bin_node.value)
        left = bin_node.children[0]
        right = bin_node.children[1]

        if op in COMMUTATIVE_OPS:
            # Sort operands deterministically
            if node_order_key(right) < node_order_key(left):
                return Node(
                    kind="BinaryOp",
                    value=op,
                    children=[right, left],
                    line=bin_node.line,
                    col=bin_node.col,
                )
        return bin_node

    # -------------------------------------------------------------------------
    # If Statement Canonicalization (Ternary equivalence)
    # -------------------------------------------------------------------------

    def _normalize_if(self, if_node: Node) -> Node:
        if len(if_node.children) < 3:
            return if_node

        cond = if_node.children[0]
        then_block = if_node.children[1]
        else_block = if_node.children[2]

        then_stmts = then_block.children if then_block.kind == "Block" else [then_block]
        else_stmts = else_block.children if else_block.kind == "Block" else [else_block]

        # Case 1: if (c) return A; else return B; -> return (c ? A : B);
        if (
            len(then_stmts) == 1 and then_stmts[0].kind == "Return"
            and len(else_stmts) == 1 and else_stmts[0].kind == "Return"
            and len(then_stmts[0].children) == 1 and len(else_stmts[0].children) == 1
        ):
            val_a = then_stmts[0].children[0]
            val_b = else_stmts[0].children[0]
            ternary = Node(kind="Ternary", children=[cond, val_a, val_b], line=if_node.line, col=if_node.col)
            return Node(kind="Return", children=[ternary], line=if_node.line, col=if_node.col)

        # Case 2: if (c) v = A; else v = B; -> v = (c ? A : B);
        if (
            len(then_stmts) == 1 and then_stmts[0].kind == "ExprStmt"
            and len(else_stmts) == 1 and else_stmts[0].kind == "ExprStmt"
        ):
            e_then = then_stmts[0].children[0]
            e_else = else_stmts[0].children[0]
            if (
                e_then.kind == "Assign" and e_then.value == "="
                and e_else.kind == "Assign" and e_else.value == "="
                and e_then.children[0] == e_else.children[0]  # Same target variable
            ):
                target = e_then.children[0]
                val_a = e_then.children[1]
                val_b = e_else.children[1]
                ternary = Node(kind="Ternary", children=[cond, val_a, val_b], line=if_node.line, col=if_node.col)
                assign = Node(kind="Assign", value="=", children=[target, ternary], line=if_node.line, col=if_node.col)
                return Node(kind="ExprStmt", children=[assign], line=if_node.line, col=if_node.col)

        return if_node

    def _normalize_expr_stmt(self, stmt_node: Node) -> Node:
        # Unpack if nested
        return stmt_node


def normalize_ast(root: Node) -> Node:
    """Entry point for AST canonicalization pass."""
    normalizer = ASTNormalizer()
    return normalizer.normalize(root)
