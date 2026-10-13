"""Tests for Python frontend: type-checking, C translation, and execution parity."""

import subprocess
import tempfile
import pytest

from app.frontends.converter import convert_to_c
from app.frontends.py_parser import PySyntaxError, parse_python


PYTHON_TEST_PROGRAMS = [
    # 1. Factorial
    """
def factorial(n: int) -> int:
    res = 1
    for i in range(1, n + 1):
        res = res * i
    return res

def main() -> int:
    print(factorial(5))
    return 0
""",
    # 2. Fibonacci
    """
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

def main() -> int:
    print(fib(7))
    return 0
""",
    # 3. GCD
    """
def gcd(a: int, b: int) -> int:
    while b != 0:
        t = a % b
        a = b
        b = t
    return a

def main() -> int:
    print(gcd(48, 18))
    return 0
""",
    # 4. Prime check
    """
def is_prime(n: int) -> int:
    if n <= 1:
        return 0
    i = 2
    while i * i <= n:
        if n % i == 0:
            return 0
        i = i + 1
    return 1

def main() -> int:
    print(is_prime(29))
    print(is_prime(30))
    return 0
""",
    # 5. Power / Exponentiation
    """
def power(base: int, exp: int) -> int:
    res = 1
    for i in range(exp):
        res = res * base
    return res

def main() -> int:
    print(power(2, 6))
    return 0
""",
    # 6. Sum of natural numbers with break/continue
    """
def sum_evens(limit: int) -> int:
    total = 0
    for i in range(limit + 1):
        if i % 2 != 0:
            continue
        total = total + i
    return total

def main() -> int:
    print(sum_evens(10))
    return 0
""",
    # 7. Nested if/elif/else
    """
def sign(x: int) -> int:
    if x > 0:
        return 1
    elif x < 0:
        return -1
    else:
        return 0

def main() -> int:
    print(sign(42))
    print(sign(-5))
    print(sign(0))
    return 0
""",
    # 8. List indexing and sum
    """
def sum_list() -> int:
    arr = [10, 20, 30, 40]
    total = 0
    for i in range(4):
        total = total + arr[i]
    return total

def main() -> int:
    print(sum_list())
    return 0
""",
    # 9. Float arithmetic
    """
def circle_area(r: float) -> float:
    pi = 3.14159
    return pi * r * r

def main() -> int:
    print(circle_area(2.0))
    return 0
""",
    # 10. String literal and print
    """
def main() -> int:
    print("CodeGuard is active")
    return 0
""",
]


@pytest.mark.parametrize("idx,py_code", list(enumerate(PYTHON_TEST_PROGRAMS)))
def test_python_to_c_compilation_and_execution(idx: int, py_code: str):
    res = convert_to_c("python", py_code)
    assert res.success is True, f"Failed converting program {idx}: {res.diagnostics}"
    c_source = res.c_source

    # 1. Compile with gcc -Wall -Werror
    with tempfile.NamedTemporaryFile("w", suffix=".c", delete=False) as f:
        f.write(c_source)
        c_path = f.name
    bin_path = c_path + ".out"

    try:
        compile_cmd = ["gcc", "-Wall", "-Werror", c_path, "-o", bin_path]
        subprocess.check_call(compile_cmd, stderr=subprocess.PIPE)

        # 2. Execute compiled C binary
        c_out = subprocess.check_output([bin_path]).decode().strip()

        # 3. Execute reference Python code
        py_runner = py_code + "\nif __name__ == '__main__': main()\n"
        py_out = subprocess.check_output(["python3", "-c", py_runner]).decode().strip()

        # Compare outputs (handle float formatting differences)
        try:
            assert float(c_out) == pytest.approx(float(py_out), rel=1e-4)
        except ValueError:
            assert c_out == py_out, f"Output mismatch for program {idx}:\nC: {c_out}\nPy: {py_out}"
    finally:
        subprocess.run(["rm", "-f", c_path, bin_path])


def test_missing_type_hints_diagnostic():
    # Missing param type hint
    bad_code1 = "def add(a, b: int) -> int:\n    return a + b\n"
    res1 = convert_to_c("python", bad_code1)
    assert res1.success is False
    assert any("Missing type hint for parameter 'a'" in d for d in res1.diagnostics)

    # Missing return type hint
    bad_code2 = "def add(a: int, b: int):\n    return a + b\n"
    res2 = convert_to_c("python", bad_code2)
    assert res2.success is False
    assert any("Missing return type hint for function 'add'" in d for d in res2.diagnostics)


def test_unsupported_python_constructs_diagnostic():
    bad_class = "class Animal:\n    pass\n"
    res = convert_to_c("python", bad_class)
    assert res.success is False
    assert any("unsupported construct: classes" in d for d in res.diagnostics)

    bad_try = "def f() -> int:\n    try:\n        return 1\n    except:\n        return 0\n"
    res_try = convert_to_c("python", bad_try)
    assert res_try.success is False
    assert any("unsupported construct: exception" in d for d in res_try.diagnostics)

    bad_import = "import os\n"
    res_imp = convert_to_c("python", bad_import)
    assert res_imp.success is False
    assert any("unsupported construct: import of non-math module 'os'" in d for d in res_imp.diagnostics)
