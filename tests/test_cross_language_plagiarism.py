"""Tests and matrix verification for cross-language plagiarism detection."""

import pytest
from app.frontends.converter import convert_to_c
from app.engine.c_parser import parse_c
from app.engine.ast_normalize import normalize_ast
from app.engine.ast_similarity import compute_ast_similarity


C_FACTORIAL = """
int factorial(int n) {
    int res = 1;
    for (int i = 1; i <= n; i++) {
        res = res * i;
    }
    return res;
}
"""

PY_FACTORIAL = """
def factorial(n: int) -> int:
    res = 1
    for i in range(1, n + 1):
        res = res * i
    return res
"""

JAVA_FACTORIAL = """
public class Solution {
    public static int factorial(int n) {
        int res = 1;
        for (int i = 1; i <= n; i++) {
            res = res * i;
        }
        return res;
    }
}
"""

C_FIBONACCI = """
int fib(int n) {
    if (n <= 1) return n;
    int a = 0;
    int b = 1;
    for (int i = 2; i <= n; i++) {
        int c = a + b;
        a = b;
        b = c;
    }
    return b;
}
"""

PY_FIBONACCI = """
def fib(n: int) -> int:
    if n <= 1:
        return n
    a = 0
    b = 1
    for i in range(2, n + 1):
        c = a + b
        a = b
        b = c
    return b
"""


def get_canonical_ast(lang: str, source: str):
    res = convert_to_c(lang, source)
    assert res.success is True, f"Failed converting {lang}: {res.diagnostics}"
    parsed = parse_c(res.c_source)
    return normalize_ast(parsed.ast)


def test_python_vs_c_factorial_plagiarism():
    ast_c = get_canonical_ast("c", C_FACTORIAL)
    ast_py = get_canonical_ast("python", PY_FACTORIAL)

    sim = compute_ast_similarity(ast_c, ast_py)
    print(f"\n[Cross-Language] Python vs C Factorial Logic Similarity: {sim.overall_logic_similarity:.4f}")
    assert sim.overall_logic_similarity >= 0.85, (
        f"Cross-language Python vs C similarity {sim.overall_logic_similarity} < 0.85"
    )


def test_java_vs_c_factorial_plagiarism():
    ast_c = get_canonical_ast("c", C_FACTORIAL)
    ast_java = get_canonical_ast("java", JAVA_FACTORIAL)

    sim = compute_ast_similarity(ast_c, ast_java)
    print(f"\n[Cross-Language] Java vs C Factorial Logic Similarity: {sim.overall_logic_similarity:.4f}")
    assert sim.overall_logic_similarity >= 0.85, (
        f"Cross-language Java vs C similarity {sim.overall_logic_similarity} < 0.85"
    )


def test_cross_language_matrix_separation():
    """Verify that same algorithms in different languages score significantly higher than different algorithms."""
    ast_c_fact = get_canonical_ast("c", C_FACTORIAL)
    ast_py_fact = get_canonical_ast("python", PY_FACTORIAL)
    ast_c_fib = get_canonical_ast("c", C_FIBONACCI)
    ast_py_fib = get_canonical_ast("python", PY_FIBONACCI)

    # Same algorithm across languages
    sim_fact_py_c = compute_ast_similarity(ast_py_fact, ast_c_fact).overall_logic_similarity
    sim_fib_py_c = compute_ast_similarity(ast_py_fib, ast_c_fib).overall_logic_similarity

    # Different algorithms across languages
    sim_diff_fact_fib = compute_ast_similarity(ast_py_fact, ast_c_fib).overall_logic_similarity

    print(f"\nCross-Language Matrix:")
    print(f"  Py(Fact) vs C(Fact): {sim_fact_py_c:.4f}")
    print(f"  Py(Fib)  vs C(Fib):  {sim_fib_py_c:.4f}")
    print(f"  Py(Fact) vs C(Fib):  {sim_diff_fact_fib:.4f}")

    assert sim_fact_py_c > sim_diff_fact_fib + 0.30
    assert sim_fib_py_c > sim_diff_fact_fib + 0.30
