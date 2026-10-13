"""Tests for Java frontend: translation to C, gcc compilation, and execution parity."""

import subprocess
import tempfile
import pytest

from app.frontends.converter import convert_to_c


JAVA_TEST_PROGRAMS = [
    # 1. Factorial
    ("""
public class Factorial {
    public static int factorial(int n) {
        int res = 1;
        for (int i = 1; i <= n; i++) {
            res = res * i;
        }
        return res;
    }

    public static void main(String[] args) {
        System.out.println(factorial(5));
    }
}
""", "120"),

    # 2. Fibonacci
    ("""
public class Fib {
    public static int fib(int n) {
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

    public static void main(String[] args) {
        System.out.println(fib(7));
    }
}
""", "13"),

    # 3. GCD
    ("""
public class GCD {
    public static int gcd(int a, int b) {
        while (b != 0) {
            int t = a % b;
            a = b;
            b = t;
        }
        return a;
    }

    public static void main(String[] args) {
        System.out.println(gcd(54, 24));
    }
}
""", "6"),

    # 4. Prime check
    ("""
public class Prime {
    public static int isPrime(int n) {
        if (n <= 1) return 0;
        for (int d = 2; d * d <= n; d++) {
            if (n % d == 0) return 0;
        }
        return 1;
    }

    public static void main(String[] args) {
        System.out.println(isPrime(37));
        System.out.println(isPrime(38));
    }
}
""", "1\n0"),

    # 5. Exponentiation
    ("""
public class Power {
    public static int power(int base, int exp) {
        int res = 1;
        while (exp > 0) {
            res = res * base;
            exp--;
        }
        return res;
    }

    public static void main(String[] args) {
        System.out.println(power(3, 4));
    }
}
""", "81"),

    # 6. Array sum
    ("""
public class ArraySum {
    public static int sum() {
        int[] arr = {1, 2, 3, 4, 5};
        int total = 0;
        for (int i = 0; i < 5; i++) {
            total += arr[i];
        }
        return total;
    }

    public static void main(String[] args) {
        System.out.println(sum());
    }
}
""", "15"),

    # 7. Math.max and Math.min
    ("""
public class MathTest {
    public static void main(String[] args) {
        int m1 = Math.max(10, 20);
        int m2 = Math.min(10, 20);
        System.out.println(m1);
        System.out.println(m2);
    }
}
""", "20\n10"),

    # 8. Switch statement
    ("""
public class SwitchTest {
    public static int getCode(int opt) {
        switch (opt) {
            case 1: return 100;
            case 2: return 200;
            default: return 999;
        }
    }

    public static void main(String[] args) {
        System.out.println(getCode(2));
    }
}
""", "200"),

    # 9. Do-while loop
    ("""
public class DoWhileTest {
    public static void main(String[] args) {
        int count = 0;
        do {
            count++;
        } while (count < 3);
        System.out.println(count);
    }
}
""", "3"),

    # 10. String literal and print
    ("""
public class Hello {
    public static void main(String[] args) {
        System.out.println("CodeGuard Java Pipeline");
    }
}
""", "CodeGuard Java Pipeline"),
]


@pytest.mark.parametrize("idx,item", list(enumerate(JAVA_TEST_PROGRAMS)))
def test_java_to_c_compilation_and_execution(idx: int, item):
    java_code, expected_output = item
    res = convert_to_c("java", java_code)
    assert res.success is True, f"Failed converting Java program {idx}: {res.diagnostics}"
    c_source = res.c_source

    with tempfile.NamedTemporaryFile("w", suffix=".c", delete=False) as f:
        f.write(c_source)
        c_path = f.name
    bin_path = c_path + ".out"

    try:
        # Compile with gcc -Wall -Werror
        compile_cmd = ["gcc", "-Wall", "-Werror", c_path, "-o", bin_path]
        subprocess.check_call(compile_cmd, stderr=subprocess.PIPE)

        # Execute compiled binary
        c_out = subprocess.check_output([bin_path]).decode().strip()
        assert c_out == expected_output.strip(), f"Output mismatch for Java program {idx}:\nExpected: {expected_output}\nGot: {c_out}"
    finally:
        subprocess.run(["rm", "-f", c_path, bin_path])


def test_unsupported_java_constructs():
    # Inheritance extends
    bad_extends = "public class Dog extends Animal { public static void main(String[] args) {} }"
    res = convert_to_c("java", bad_extends)
    assert res.success is False
    assert any("unsupported construct: inheritance/interfaces" in d for d in res.diagnostics)

    # Interfaces implements
    bad_impl = "public class Dog implements Runnable { public static void main(String[] args) {} }"
    res_impl = convert_to_c("java", bad_impl)
    assert res_impl.success is False
    assert any("unsupported construct: inheritance/interfaces" in d for d in res_impl.diagnostics)

    # Exceptions try/catch
    bad_try = "public class Ex { public static void main(String[] args) { try { int x = 1; } catch (Exception e) {} } }"
    res_try = convert_to_c("java", bad_try)
    assert res_try.success is False
    assert any("unsupported construct: exception handling" in d for d in res_try.diagnostics)
