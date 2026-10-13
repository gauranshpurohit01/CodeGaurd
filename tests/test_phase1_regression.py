"""Test Phase 1.6: Reproduce and verify resolution of the for/while factorial regression."""

import sys
from pathlib import Path

# Add backend to sys.path
backend_path = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from app.engine.c_parser import parse_c
from app.engine.ast_normalize import normalize_ast
from app.engine.ast_similarity import compute_ast_similarity


FACT_FOR = """
int fact(int n) {
    int res = 1;
    for (int i = 1; i <= n; i++) {
        res = res * i;
    }
    return res;
}
"""

FACT_WHILE = """
int factorial(int num) {
    int ans = 1;
    int j = 1;
    while (j <= num) {
        ans = ans * j;
        j = j + 1;
    }
    return ans;
}
"""

FIBONACCI = """
int fib(int n) {
    if (n <= 1) {
        return n;
    }
    return fib(n - 1) + fib(n - 2);
}
"""


def test_regression_scores():
    # 1. Parse raw ASTs
    ast_fact_for = parse_c(FACT_FOR).ast
    ast_fact_while = parse_c(FACT_WHILE).ast
    ast_fib = parse_c(FIBONACCI).ast

    # Compute similarity BEFORE canonicalization
    raw_sim_fact = compute_ast_similarity(ast_fact_for, ast_fact_while)
    raw_sim_fib = compute_ast_similarity(ast_fact_for, ast_fib)

    print("--- BEFORE CANONICALIZATION ---")
    print(f"fact(for) vs fact(while) alignment: {raw_sim_fact.alignment_score:.4f}")
    print(f"fact(for) vs fibonacci   alignment: {raw_sim_fib.alignment_score:.4f}")
    print(f"fact(for) vs fact(while) overall:   {raw_sim_fact.overall_logic_similarity:.4f}")
    print(f"fact(for) vs fibonacci   overall:   {raw_sim_fib.overall_logic_similarity:.4f}")

    # 2. Canonicalize ASTs
    norm_fact_for = normalize_ast(ast_fact_for)
    norm_fact_while = normalize_ast(ast_fact_while)
    norm_fib = normalize_ast(ast_fib)

    # Compute similarity AFTER canonicalization
    norm_sim_fact = compute_ast_similarity(norm_fact_for, norm_fact_while)
    norm_sim_fib = compute_ast_similarity(norm_fact_for, norm_fib)

    print("\n--- AFTER CANONICALIZATION ---")
    print(f"fact(for) vs fact(while) alignment: {norm_sim_fact.alignment_score:.4f}")
    print(f"fact(for) vs fibonacci   alignment: {norm_sim_fib.alignment_score:.4f}")
    print(f"fact(for) vs fact(while) overall:   {norm_sim_fact.overall_logic_similarity:.4f}")
    print(f"fact(for) vs fibonacci   overall:   {norm_sim_fib.overall_logic_similarity:.4f}")

    # Check regression criteria:
    # 1. Without canonicalization, the prototype showed fact vs fact_while scoring lower or similar to fib
    # 2. With canonicalization, fact(for) vs fact(while) MUST score significantly higher than fact(for) vs fibonacci!
    assert norm_sim_fact.alignment_score > norm_sim_fib.alignment_score, (
        f"Restructured factorial score ({norm_sim_fact.alignment_score:.4f}) must be higher "
        f"than different Fibonacci score ({norm_sim_fib.alignment_score:.4f})"
    )
    assert norm_sim_fact.overall_logic_similarity > norm_sim_fib.overall_logic_similarity, (
        f"Restructured factorial overall ({norm_sim_fact.overall_logic_similarity:.4f}) must be higher "
        f"than different Fibonacci overall ({norm_sim_fib.overall_logic_similarity:.4f})"
    )
    print("\n[SUCCESS] Regression test passed: restructured logic scores higher than different algorithm!")


if __name__ == "__main__":
    test_regression_scores()
