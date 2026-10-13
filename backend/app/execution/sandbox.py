"""Sandbox execution environment for CodeGuard.

Provides secure compilation and execution of C/C++ (and converted Python/Java) programs
using Docker with strict resource limits, falling back to a local resource-limited runner.
"""

from __future__ import annotations
import os
import resource
import shutil
import subprocess
import tempfile
import time
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from app.frontends.converter import convert_to_c


MAX_OUTPUT_BYTES = 64 * 1024  # 64 KB cap
DEFAULT_TIMEOUT_SEC = 5.0
DEFAULT_MEMORY_MB = 128


@dataclass
class TestCaseResult:
    input: str
    expected: str
    actual: str
    passed: bool
    time_ms: float


@dataclass
class ExecutionResult:
    compile_ok: bool
    compiler_messages: str
    stdout: str
    stderr: str
    exit_code: int
    time_ms: float
    memory_kb: int
    timed_out: bool
    killed_reason: Optional[str] = None
    converted_c_source: Optional[str] = None
    test_results: List[TestCaseResult] = field(default_factory=list)


class Sandbox:
    def __init__(
        self,
        timeout_sec: float = DEFAULT_TIMEOUT_SEC,
        memory_mb: int = DEFAULT_MEMORY_MB,
        docker_image: str = "codeguard-sandbox",
        use_docker: Optional[bool] = None,
    ) -> None:
        self.timeout_sec = timeout_sec
        self.memory_mb = memory_mb
        self.docker_image = docker_image
        self.use_docker = use_docker if use_docker is not None else self._check_docker_available()

    def _check_docker_available(self) -> bool:
        if not shutil.which("docker"):
            return False
        try:
            res = subprocess.run(["docker", "info"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=2)
            return res.returncode == 0
        except Exception:
            return False

    def run(
        self,
        language: str,
        source: str,
        stdin_data: str = "",
        test_cases: Optional[List[Tuple[str, str]]] = None,
    ) -> ExecutionResult:
        lang = language.lower().strip()
        c_code = source
        converted = None

        # Convert Python or Java to C first
        if lang in ("python", "py", "java"):
            conv_res = convert_to_c(lang, source)
            if not conv_res.success:
                return ExecutionResult(
                    compile_ok=False,
                    compiler_messages="\n".join(conv_res.diagnostics),
                    stdout="",
                    stderr="",
                    exit_code=1,
                    time_ms=0.0,
                    memory_kb=0,
                    timed_out=False,
                    killed_reason="ConversionError",
                )
            c_code = conv_res.c_source
            converted = c_code

        is_cpp = (lang in ("cpp", "c++"))

        if self.use_docker:
            return self._run_docker(c_code, is_cpp, stdin_data, test_cases, converted)
        else:
            return self._run_local(c_code, is_cpp, stdin_data, test_cases, converted)

    # -------------------------------------------------------------------------
    # Local Runner with setrlimit (Fallback)
    # -------------------------------------------------------------------------

    def _run_local(
        self,
        c_code: str,
        is_cpp: bool,
        stdin_data: str,
        test_cases: Optional[List[Tuple[str, str]]],
        converted: Optional[str],
    ) -> ExecutionResult:
        compiler = "g++" if is_cpp else "gcc"
        if not shutil.which(compiler):
            compiler = "clang++" if is_cpp else "clang"

        with tempfile.TemporaryDirectory() as tmpdir:
            src_file = os.path.join(tmpdir, "code.cpp" if is_cpp else "code.c")
            bin_file = os.path.join(tmpdir, "code.out")

            with open(src_file, "w", encoding="utf-8") as f:
                f.write(c_code)

            # Compile step
            compile_cmd = [compiler, "-O0", "-Wall", src_file, "-o", bin_file, "-lm"]
            comp_proc = subprocess.run(compile_cmd, capture_output=True, text=True)

            if comp_proc.returncode != 0:
                return ExecutionResult(
                    compile_ok=False,
                    compiler_messages=comp_proc.stderr,
                    stdout="",
                    stderr=comp_proc.stderr,
                    exit_code=comp_proc.returncode,
                    time_ms=0.0,
                    memory_kb=0,
                    timed_out=False,
                    killed_reason="CompileError",
                    converted_c_source=converted,
                )

            # If test cases provided, execute each test case
            if test_cases:
                test_results: List[TestCaseResult] = []
                total_time = 0.0
                all_passed = True
                last_exec = None

                for tc_in, tc_exp in test_cases:
                    last_exec = self._execute_local_binary(bin_file, tc_in)
                    total_time += last_exec.time_ms
                    actual_out = last_exec.stdout.strip()
                    passed = (actual_out == tc_exp.strip())
                    if not passed:
                        all_passed = False
                    test_results.append(TestCaseResult(
                        input=tc_in,
                        expected=tc_exp,
                        actual=actual_out,
                        passed=passed,
                        time_ms=last_exec.time_ms,
                    ))

                assert last_exec is not None
                return ExecutionResult(
                    compile_ok=True,
                    compiler_messages=comp_proc.stderr,
                    stdout=last_exec.stdout,
                    stderr=last_exec.stderr,
                    exit_code=0 if all_passed else 1,
                    time_ms=round(total_time, 2),
                    memory_kb=last_exec.memory_kb,
                    timed_out=last_exec.timed_out,
                    killed_reason=last_exec.killed_reason,
                    converted_c_source=converted,
                    test_results=test_results,
                )

            # Single execution
            exec_res = self._execute_local_binary(bin_file, stdin_data)
            exec_res.compiler_messages = comp_proc.stderr
            exec_res.converted_c_source = converted
            return exec_res

    def _execute_local_binary(self, bin_file: str, stdin_data: str) -> ExecutionResult:
        def set_limits() -> None:
            # Set CPU limit in seconds
            cpu_limit = int(self.timeout_sec) + 1
            resource.setrlimit(resource.RLIMIT_CPU, (cpu_limit, cpu_limit))
            # Set maximum file size (cap output write)
            max_bytes = MAX_OUTPUT_BYTES
            resource.setrlimit(resource.RLIMIT_FSIZE, (max_bytes, max_bytes))

        start_time = time.perf_counter()
        timed_out = False
        killed_reason = None
        stdout_bytes = b""
        stderr_bytes = b""
        exit_code = 0

        try:
            proc = subprocess.Popen(
                [bin_file],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                preexec_fn=set_limits,
            )
            try:
                stdout_bytes, stderr_bytes = proc.communicate(
                    input=stdin_data.encode("utf-8") if stdin_data else None,
                    timeout=self.timeout_sec,
                )
                exit_code = proc.returncode
            except subprocess.TimeoutExpired:
                proc.kill()
                stdout_bytes, stderr_bytes = proc.communicate()
                timed_out = True
                killed_reason = "TimeLimitExceeded"
                exit_code = -9
        except Exception as e:
            killed_reason = str(e)
            exit_code = 1

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0

        # Memory usage via getrusage
        usage = resource.getrusage(resource.RUSAGE_CHILDREN)
        memory_kb = usage.ru_maxrss
        # macOS returns bytes instead of KB in ru_maxrss
        if os.uname().sysname == "Darwin":
            memory_kb = memory_kb // 1024

        # Output capping
        if len(stdout_bytes) > MAX_OUTPUT_BYTES:
            stdout_bytes = stdout_bytes[:MAX_OUTPUT_BYTES] + b"\n... [OUTPUT TRUNCATED AT 64KB]"
            killed_reason = killed_reason or "OutputLimitExceeded"

        return ExecutionResult(
            compile_ok=True,
            compiler_messages="",
            stdout=stdout_bytes.decode("utf-8", errors="replace"),
            stderr=stderr_bytes.decode("utf-8", errors="replace"),
            exit_code=exit_code,
            time_ms=round(elapsed_ms, 2),
            memory_kb=memory_kb,
            timed_out=timed_out,
            killed_reason=killed_reason,
        )

    # -------------------------------------------------------------------------
    # Docker Sandbox Runner
    # -------------------------------------------------------------------------

    def _run_docker(
        self,
        c_code: str,
        is_cpp: bool,
        stdin_data: str,
        test_cases: Optional[List[Tuple[str, str]]],
        converted: Optional[str],
    ) -> ExecutionResult:
        with tempfile.TemporaryDirectory() as tmpdir:
            src_name = "code.cpp" if is_cpp else "code.c"
            with open(os.path.join(tmpdir, src_name), "w", encoding="utf-8") as f:
                f.write(c_code)

            compiler = "g++" if is_cpp else "gcc"
            # 1. Compile inside docker container
            compile_cmd = [
                "docker", "run", "--rm",
                "--net=none",
                "-v", f"{tmpdir}:/workspace:rw",
                "-w", "/workspace",
                self.docker_image,
                compiler, "-O0", "-Wall", src_name, "-o", "code.out", "-lm",
            ]
            comp_proc = subprocess.run(compile_cmd, capture_output=True, text=True, timeout=10)

            if comp_proc.returncode != 0:
                return ExecutionResult(
                    compile_ok=False,
                    compiler_messages=comp_proc.stderr,
                    stdout="",
                    stderr=comp_proc.stderr,
                    exit_code=comp_proc.returncode,
                    time_ms=0.0,
                    memory_kb=0,
                    timed_out=False,
                    killed_reason="CompileError",
                    converted_c_source=converted,
                )

            # 2. Execute inside locked down container
            run_cmd = [
                "docker", "run", "--rm", "-i",
                "--net=none",
                "--read-only",
                "--tmpfs", "/tmp:rw,noexec,nosuid,size=64m",
                "--memory", f"{self.memory_mb}m",
                "--pids-limit", "32",
                "--cpus", "1.0",
                "-v", f"{tmpdir}/code.out:/workspace/code.out:ro",
                "-w", "/workspace",
                self.docker_image,
                "./code.out",
            ]

            start_t = time.perf_counter()
            timed_out = False
            killed_reason = None
            stdout_bytes = b""
            stderr_bytes = b""
            exit_code = 0

            try:
                proc = subprocess.Popen(
                    run_cmd,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
                stdout_bytes, stderr_bytes = proc.communicate(
                    input=stdin_data.encode("utf-8") if stdin_data else None,
                    timeout=self.timeout_sec,
                )
                exit_code = proc.returncode
            except subprocess.TimeoutExpired:
                proc.kill()
                stdout_bytes, stderr_bytes = proc.communicate()
                timed_out = True
                killed_reason = "TimeLimitExceeded"
                exit_code = -9
            except Exception as e:
                killed_reason = str(e)
                exit_code = 1

            elapsed_ms = (time.perf_counter() - start_t) * 1000.0

            if len(stdout_bytes) > MAX_OUTPUT_BYTES:
                stdout_bytes = stdout_bytes[:MAX_OUTPUT_BYTES] + b"\n... [OUTPUT TRUNCATED AT 64KB]"
                killed_reason = killed_reason or "OutputLimitExceeded"

            return ExecutionResult(
                compile_ok=True,
                compiler_messages=comp_proc.stderr,
                stdout=stdout_bytes.decode("utf-8", errors="replace"),
                stderr=stderr_bytes.decode("utf-8", errors="replace"),
                exit_code=exit_code,
                time_ms=round(elapsed_ms, 2),
                memory_kb=0,
                timed_out=timed_out,
                killed_reason=killed_reason,
                converted_c_source=converted,
            )
