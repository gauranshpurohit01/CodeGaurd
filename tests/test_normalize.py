"""Unit tests for AST canonicalization (normalization) pass."""

from app.engine.c_parser import parse_c
from app.engine.ast_normalize import normalize_ast


def test_loop_canonicalization():
    # for loop converted to lifted init + Loop
    code_for = """
    void f(int n) {
        int s = 0;
        for (int i = 0; i < n; i++) {
            s += i;
        }
    }
    """
    code_while = """
    void f(int n) {
        int s = 0;
        int i = 0;
        while (i < n) {
            s = s + i;
            i = i + 1;
        }
    }
    """
    ast_for = normalize_ast(parse_c(code_for).ast)
    ast_while = normalize_ast(parse_c(code_while).ast)

    # Both function bodies should contain VarDecl for s, Assign for s, VarDecl for i, Assign for i, and a Loop!
    body_for = ast_for.children[0].children[2]
    body_while = ast_while.children[0].children[2]

    kinds_for = [s.kind for s in body_for.children]
    kinds_while = [s.kind for s in body_while.children]
    assert kinds_for == kinds_while
    assert "Loop" in kinds_for


def test_flatten_redundant_blocks():
    code = """
    void f() {
        {
            {
                int x = 1;
            }
        }
    }
    """
    norm = normalize_ast(parse_c(code).ast)
    body = norm.children[0].children[2]
    # No nested Block inside body
    assert all(child.kind != "Block" for child in body.children)


def test_compound_assign_and_increment():
    code1 = "void f() { a += b; i++; }"
    code2 = "void f() { a = a + b; i = i + 1; }"
    norm1 = normalize_ast(parse_c(code1).ast)
    norm2 = normalize_ast(parse_c(code2).ast)
    body1 = norm1.children[0].children[2]
    body2 = norm2.children[0].children[2]
    assert body1 == body2


def test_if_return_ternary_canonicalization():
    code_if = """
    int f(int c, int a, int b) {
        if (c > 0) return a; else return b;
    }
    """
    norm = normalize_ast(parse_c(code_if).ast)
    body = norm.children[0].children[2]
    assert len(body.children) == 1
    assert body.children[0].kind == "Return"
    assert body.children[0].children[0].kind == "Ternary"


def test_commutative_sorting():
    code1 = "int f(int a, int b) { return a + b; }"
    code2 = "int f(int a, int b) { return b + a; }"
    norm1 = normalize_ast(parse_c(code1).ast)
    norm2 = normalize_ast(parse_c(code2).ast)
    # The return expressions should be identical after commutative sorting
    ret1 = norm1.children[0].children[2].children[0].children[0]
    ret2 = norm2.children[0].children[2].children[0].children[0]
    assert ret1 == ret2


def test_de_morgan_and_relational_negation():
    code1 = "int f(int a, int b) { return !(a < b); }"
    norm1 = normalize_ast(parse_c(code1).ast)
    ret1 = norm1.children[0].children[2].children[0].children[0]
    # !(a < b) normalized to a >= b
    assert ret1.kind == "BinaryOp"
    assert ret1.value == ">="


def test_idempotence():
    """Verify that normalize(normalize(x)) == normalize(x)."""
    code = """
    int complex_func(int n) {
        int sum = 0, k = 1;
        for (int i = 0; i < n; ++i) {
            sum += i * k;
        }
        if (sum > 100) return sum; else return 0;
    }
    """
    raw_ast = parse_c(code).ast
    norm1 = normalize_ast(raw_ast)
    norm2 = normalize_ast(norm1)
    assert norm1 == norm2
