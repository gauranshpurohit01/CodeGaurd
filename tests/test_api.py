"""Integration tests for CodeGuard FastAPI REST endpoints."""

import pytest
from fastapi.testclient import TestClient
from app.main import app


client = TestClient(app)


def test_health_check():
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


def test_api_convert_python():
    py_code = "def add(a: int, b: int) -> int:\n    return a + b\n"
    res = client.post("/api/convert", json={"language": "python", "source": py_code})
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert "int add(int a, int b)" in data["c_source"]


def test_api_run_c():
    c_code = """
    #include <stdio.h>
    int main(void) {
        printf("Hello CodeGuard\\n");
        return 0;
    }
    """
    res = client.post("/api/run", json={"language": "c", "source": c_code})
    assert res.status_code == 200
    data = res.json()
    assert data["compile_ok"] is True
    assert "Hello CodeGuard" in data["stdout"]


def test_api_submissions_and_plagiarism():
    # 1. Create submission A
    sub_a = {
        "title": "Factorial For Loop",
        "language": "c",
        "source": "int fact(int n) { int res = 1; for (int i = 1; i <= n; i++) res = res * i; return res; }"
    }
    res_a = client.post("/api/submissions", json=sub_a)
    assert res_a.status_code == 200
    sub_id = res_a.json()["id"]

    # 2. Get submissions list
    res_list = client.get("/api/submissions")
    assert res_list.status_code == 200
    assert any(s["id"] == sub_id for s in res_list.json())

    # 3. Check plagiarism with query (restructured while loop)
    query = {
        "language": "c",
        "source": "int factorial(int num) { int ans = 1; int j = 1; while (j <= num) { ans = ans * j; j = j + 1; } return ans; }",
        "compare_with": "database"
    }
    res_check = client.post("/api/plagiarism/check", json=query)
    assert res_check.status_code == 200
    matches = res_check.json()["matches"]
    assert len(matches) > 0
    # Top match should have high logic similarity
    top_match = matches[0]
    assert top_match["logic_similarity"] >= 0.75


def test_api_ast_pipeline_view():
    code = "int square(int x) { return x * x; }"
    res = client.get("/api/ast", params={"language": "c", "source": code})
    assert res.status_code == 200
    data = res.json()
    assert "tokens" in data
    assert "raw_ast" in data
    assert "canonical_ast" in data
    assert "generated_c" in data
    assert data["raw_ast"]["kind"] == "TranslationUnit"


def test_api_direct_compare():
    req = {
        "language_a": "python",
        "source_a": "def fact(n: int) -> int:\n    res = 1\n    for i in range(1, n+1):\n        res = res * i\n    return res",
        "language_b": "c",
        "source_b": "int fact(int n) { int res = 1; for (int i = 1; i <= n; i++) res = res * i; return res; }",
    }
    res = client.post("/api/compare", json=req)
    assert res.status_code == 200
    data = res.json()
    assert data["logic_similarity"] >= 0.85
