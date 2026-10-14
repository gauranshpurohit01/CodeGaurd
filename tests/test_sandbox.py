"""Security and execution tests for the CodeGuard sandbox."""

import pytest
from app.execution.sandbox import Sandbox, MAX_OUTPUT_BYTES


@pytest.fixture
def sandbox():
    # Explicitly use local runner for fast isolated testing with realistic timeout
    return Sandbox(timeout_sec=5.0, memory_mb=64, use_docker=False)


def test_sandbox_normal_c_execution(sandbox):
    code = """
    #include <stdio.h>
    int main(void) {
        int a, b;
        if (scanf("%d %d", &a, &b) == 2) {
            printf("%d\\n", a + b);
        }
        return 0;
    }
    """
    res = sandbox.run("c", code, stdin_data="15 27")
    assert res.compile_ok is True
    assert res.timed_out is False
    assert res.stdout.strip() == "42"
    assert res.exit_code == 0


def test_sandbox_test_cases(sandbox):
    code = """
    #include <stdio.h>
    int main(void) {
        int n;
        if (scanf("%d", &n) == 1) {
            printf("%d\\n", n * n);
        }
        return 0;
    }
    """
    tests = [
        ("3", "9"),
        ("5", "25"),
        ("10", "100"),
        ("4", "99"),  # intentional failure
    ]
    res = sandbox.run("c", code, test_cases=tests)
    assert res.compile_ok is True
    assert len(res.test_results) == 4
    assert res.test_results[0].passed is True
    assert res.test_results[1].passed is True
    assert res.test_results[2].passed is True
    assert res.test_results[3].passed is False


def test_security_infinite_loop_timeout(sandbox):
    code = """
    int main(void) {
        while (1) {
            // spin indefinitely
        }
        return 0;
    }
    """
    res = sandbox.run("c", code)
    assert res.compile_ok is True
    assert res.timed_out is True
    assert res.killed_reason == "TimeLimitExceeded"


def test_security_huge_output_capped(sandbox):
    code = """
    #include <stdio.h>
    int main(void) {
        for (int i = 0; i < 50000; i++) {
            printf("ABCDEFGH12345678\\n");
        }
        return 0;
    }
    """
    res = sandbox.run("c", code)
    assert res.compile_ok is True
    assert len(res.stdout.encode("utf-8")) <= MAX_OUTPUT_BYTES + 500
    assert "[OUTPUT TRUNCATED AT 64KB]" in res.stdout


def test_security_reading_sensitive_files(sandbox):
    code = """
    #include <stdio.h>
    int main(void) {
        FILE *f = fopen("/etc/shadow", "r");
        if (f == NULL) {
            printf("ACCESS_DENIED\\n");
        } else {
            printf("LEAKED\\n");
            fclose(f);
        }
        return 0;
    }
    """
    res = sandbox.run("c", code)
    assert res.compile_ok is True
    assert "ACCESS_DENIED" in res.stdout


def test_sandbox_python_conversion_execution(sandbox):
    py_code = """
def multiply(x: int, y: int) -> int:
    return x * y

def main() -> int:
    print(multiply(6, 7))
    return 0
"""
    res = sandbox.run("python", py_code)
    assert res.compile_ok is True
    assert res.stdout.strip() == "42"
    assert res.converted_c_source is not None
