"""Scripted demonstration of CodeGuard end-to-end capabilities."""

import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.frontends.converter import convert_to_c
from app.execution.sandbox import Sandbox
from app.engine.report import check_plagiarism_c


PYTHON_FACTORIAL = """
def factorial(n: int) -> int:
    res = 1
    for i in range(1, n + 1):
        res = res * i
    return res

def main() -> int:
    print(factorial(5))
    return 0
"""

RESTRUCTURED_C_FACTORIAL = """
#include <stdio.h>

int factorial_while(int num) {
    int ans = 1;
    int j = 1;
    while (j <= num) {
        ans = ans * j;
        j = j + 1;
    }
    return ans;
}

int main(void) {
    printf("%d\\n", factorial_while(5));
    return 0;
}
"""

DIFFERENT_C_FIBONACCI = """
#include <stdio.h>

int fib(int n) {
    if (n <= 1) return n;
    return fib(n - 1) + fib(n - 2);
}

int main(void) {
    printf("%d\\n", fib(7));
    return 0;
}
"""


def run_demo():
    print("=" * 80)
    print("CODEGUARD END-TO-END DEMO: Python Conversion -> Execution -> Plagiarism")
    print("=" * 80)

    # 1. Convert Python Factorial to C
    print("\n[STEP 1] Converting typed Python source to C...")
    print("--- Python Source ---")
    print(PYTHON_FACTORIAL.strip())

    conv_res = convert_to_c("python", PYTHON_FACTORIAL)
    assert conv_res.success, f"Conversion failed: {conv_res.diagnostics}"
    print("\n--- Generated C Source ---")
    print(conv_res.c_source.strip())

    # 2. Compile & Run in Sandbox
    print("\n[STEP 2] Compiling and running generated C in Sandbox...")
    sandbox = Sandbox(use_docker=False)
    run_res = sandbox.run("c", conv_res.c_source)
    print(f"Compilation: {'SUCCESS' if run_res.compile_ok else 'FAILED'}")
    print(f"Execution Output: {run_res.stdout.strip()}")
    print(f"Execution Time:   {run_res.time_ms} ms")
    print(f"Memory:           {run_res.memory_kb} KB")

    # 3. Check Plagiarism against Restructured C Version
    print("\n[STEP 3] Comparing converted Python against Restructured C Factorial (while loop)...")
    rep_same = check_plagiarism_c(conv_res.c_source, RESTRUCTURED_C_FACTORIAL)
    print(f"Token Similarity (Winnowing):       {rep_same.token_similarity * 100:.1f}%")
    print(f"Logic Similarity (AST Alignment):   {rep_same.logic_similarity * 100:.1f}%")
    print(f"Overall Plagiarism Score:           {rep_same.overall_similarity * 100:.1f}%")
    print(f"Verdict:                            {rep_same.verdict.upper()}")
    print(f"Matched Subtrees Count:             {len(rep_same.matched_subtrees)}")

    # 4. Compare against Different Algorithm (Fibonacci)
    print("\n[STEP 4] Comparing converted Python against Different Algorithm (C Fibonacci)...")
    rep_diff = check_plagiarism_c(conv_res.c_source, DIFFERENT_C_FIBONACCI)
    print(f"Token Similarity (Winnowing):       {rep_diff.token_similarity * 100:.1f}%")
    print(f"Logic Similarity (AST Alignment):   {rep_diff.logic_similarity * 100:.1f}%")
    print(f"Overall Plagiarism Score:           {rep_diff.overall_similarity * 100:.1f}%")
    print(f"Verdict:                            {rep_diff.verdict.upper()}")

    print("\n" + "=" * 80)
    print("[SUCCESS] Demonstration complete!")
    print(f"Restructured logic scored {rep_same.logic_similarity*100:.1f}% (Verdict: {rep_same.verdict})")
    print(f"Different logic scored    {rep_diff.logic_similarity*100:.1f}% (Verdict: {rep_diff.verdict})")
    print("=" * 80)


if __name__ == "__main__":
    run_demo()
