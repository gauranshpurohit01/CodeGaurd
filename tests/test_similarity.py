"""Unit tests for AST similarity engine and ordering invariant."""

from app.engine.c_parser import parse_c
from app.engine.ast_normalize import normalize_ast
from app.engine.ast_similarity import compute_ast_similarity, ASTSimilarityEngine
from app.engine.ast_nodes import Node


def test_identical_similarity():
    code = "int square(int x) { return x * x; }"
    ast1 = normalize_ast(parse_c(code).ast)
    ast2 = normalize_ast(parse_c(code).ast)
    sim = compute_ast_similarity(ast1, ast2)
    assert sim.alignment_score == 1.0
    assert sim.overall_logic_similarity == 1.0


def test_renamed_similarity():
    code1 = "int square(int x) { return x * x; }"
    code2 = "int multiply(int val) { return val * val; }"
    ast1 = normalize_ast(parse_c(code1).ast)
    ast2 = normalize_ast(parse_c(code2).ast)
    sim = compute_ast_similarity(ast1, ast2)
    # Different identifier names still yield high alignment score (>= 0.80)
    assert sim.alignment_score >= 0.80


def test_similarity_ordering():
    """Verify invariant: identical >= renamed >= restructured > different."""
    original = """
    int fact(int n) {
        int res = 1;
        for (int i = 1; i <= n; i++) {
            res = res * i;
        }
        return res;
    }
    """
    renamed = """
    int factorial(int num) {
        int ans = 1;
        for (int idx = 1; idx <= num; idx++) {
            ans = ans * idx;
        }
        return ans;
    }
    """
    restructured = """
    int factorial_while(int num) {
        int ans = 1;
        int j = 1;
        while (j <= num) {
            ans = ans * j;
            j = j + 1;
        }
        return ans;
    }
    """
    different = """
    int fib(int n) {
        if (n <= 1) return n;
        return fib(n - 1) + fib(n - 2);
    }
    """
    ast_orig = normalize_ast(parse_c(original).ast)
    ast_ren = normalize_ast(parse_c(renamed).ast)
    ast_rest = normalize_ast(parse_c(restructured).ast)
    ast_diff = normalize_ast(parse_c(different).ast)

    sim_ident = compute_ast_similarity(ast_orig, ast_orig).overall_logic_similarity
    sim_ren = compute_ast_similarity(ast_orig, ast_ren).overall_logic_similarity
    sim_rest = compute_ast_similarity(ast_orig, ast_rest).overall_logic_similarity
    sim_diff = compute_ast_similarity(ast_orig, ast_diff).overall_logic_similarity

    print(f"Similarity scores: ident={sim_ident:.3f}, ren={sim_ren:.3f}, rest={sim_rest:.3f}, diff={sim_diff:.3f}")

    assert sim_ident >= sim_ren, f"{sim_ident} not >= {sim_ren}"
    assert sim_ren >= sim_rest, f"{sim_ren} not >= {sim_rest}"
    assert sim_rest > sim_diff, f"{sim_rest} not > {sim_diff}"


def test_size_guard_triggered():
    # Construct synthetic large AST with > 3000 nodes
    engine = ASTSimilarityEngine(size_guard=50)  # low threshold for testing
    root = Node(kind="Block")
    for i in range(60):
        root.children.append(Node(kind="Literal", value=str(i)))

    sim = engine.compare(root, root)
    assert sim.size_guard_triggered is True
    assert sim.alignment_score == 0.0  # skipped alignment
    assert sim.overall_logic_similarity > 0.0  # fell back to hashing
