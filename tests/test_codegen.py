"""Unit tests for C code generator and round-trip fidelity."""

from app.engine.c_parser import parse_c
from app.codegen.c_codegen import generate_c
from app.engine.ast_normalize import normalize_ast
from app.engine.ast_similarity import compute_ast_similarity


def test_round_trip_c_ast_similarity():
    """Verify that C -> AST -> C -> AST gives similarity >= 0.95."""
    programs = [
        """
        int fact(int n) {
            int res = 1;
            for (int i = 1; i <= n; i++) {
                res = res * i;
            }
            return res;
        }
        """,
        """
        int gcd(int a, int b) {
            while (b != 0) {
                int t = a % b;
                a = b;
                b = t;
            }
            return a;
        }
        """,
        """
        int check(int x) {
            if (x > 0) return 1;
            else return 0;
        }
        """,
    ]

    for prog in programs:
        ast1 = parse_c(prog).ast
        c_code = generate_c(ast1)
        ast2 = parse_c(c_code).ast

        sim = compute_ast_similarity(normalize_ast(ast1), normalize_ast(ast2))
        assert sim.overall_logic_similarity >= 0.95, (
            f"Round trip similarity {sim.overall_logic_similarity} < 0.95 for:\n{c_code}"
        )


def test_header_emission():
    code = """
    int main(void) {
        printf("Hello World\\n");
        double p = pow(2.0, 3.0);
        bool b = true;
        return 0;
    }
    """
    ast = parse_c(code).ast
    c_out = generate_c(ast)
    assert "#include <stdio.h>" in c_out
    assert "#include <math.h>" in c_out
    assert "#include <stdbool.h>" in c_out
