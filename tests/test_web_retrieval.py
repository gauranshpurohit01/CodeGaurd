"""Unit and integration tests for Real-Time Web Candidate Retrieval Module."""

import base64
import json
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from app.main import app
from app.retrieval.signature_extractor import extract_signatures, map_language_for_github
from app.retrieval.web_retriever import GitHubWebRetriever, WebCandidate, compute_query_hash
from app.retrieval.web_plagiarism_runner import run_web_plagiarism_pipeline


client = TestClient(app)


# -----------------------------------------------------------------------------
# 1. Signature Extractor Tests
# -----------------------------------------------------------------------------

def test_signature_extraction_high_entropy():
    code = """
    #include <stdio.h>
    #define MAX_VERTICES_LIMIT 5000

    int find_shortest_cycle(int adj[MAX_VERTICES_LIMIT][MAX_VERTICES_LIMIT], int n) {
        if (n > MAX_VERTICES_LIMIT) {
            printf("Vertex limit exceeded in cycle search\\n");
            return -1;
        }
        return 0;
    }
    """
    sigs = extract_signatures("c", code)
    assert len(sigs) >= 2
    assert "find_shortest_cycle" in sigs
    assert "MAX_VERTICES_LIMIT" in sigs


def test_signature_extraction_generic_fallback():
    trivial_code = """
    #include <stdio.h>
    int main(void) {
        int a = 1;
        int b = 2;
        printf("%d\\n", a + b);
        return 0;
    }
    """
    sigs = extract_signatures("c", trivial_code)
    # Trivial code with generic keywords and single-letter vars must return []
    assert sigs == []


def test_signature_extraction_python_and_constants():
    py_code = """
    def compute_rabin_karp_rolling_hash(text: str, pattern: str) -> int:
        MOD_VAL = 1000000007
        base_multiplier = 257
        return 42
    """
    sigs = extract_signatures("python", py_code)
    assert len(sigs) >= 2
    assert any("rabin_karp" in s for s in sigs)
    assert "1000000007" in sigs or "MOD_VAL" in sigs


def test_map_language_for_github():
    assert map_language_for_github("c") == "C"
    assert map_language_for_github("cpp") == "C++"
    assert map_language_for_github("python") == "Python"
    assert map_language_for_github("java") == "Java"


# -----------------------------------------------------------------------------
# 2. Web Candidate Retrieval & Mocked GitHub API Tests
# -----------------------------------------------------------------------------

@pytest.fixture
def mock_github_items():
    code_content = """
    #include <stdio.h>
    int find_shortest_cycle(int n) {
        int res = 1;
        for (int i = 1; i <= n; i++) {
            res = res * i;
        }
        return res;
    }
    """
    b64_content = base64.b64encode(code_content.encode("utf-8")).decode("utf-8")
    return [
        {
            "html_url": "https://github.com/algorithms/graph-lib/blob/main/cycle.c",
            "name": "cycle.c",
            "path": "cycle.c",
            "repository": {"full_name": "algorithms/graph-lib"},
            "url": "https://api.github.com/repos/algorithms/graph-lib/contents/cycle.c",
        }
    ], b64_content, code_content


def test_web_retriever_query_and_decode(mock_github_items):
    items, b64_code, raw_code = mock_github_items

    retriever = GitHubWebRetriever(token="dummy_token_test")

    def mock_get(url, *args, **kwargs):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        if "api.github.com/search/code" in url:
            mock_resp.json.return_value = {"items": items}
        elif "contents/cycle.c" in url:
            mock_resp.text = raw_code
            mock_resp.json.return_value = {"content": b64_code, "encoding": "base64"}
        return mock_resp

    with patch("httpx.Client.get", side_effect=mock_get):
        candidates, status = retriever.retrieve(["find_shortest_cycle"], "c", max_candidates=1)
        assert len(candidates) == 1
        assert candidates[0].repository == "algorithms/graph-lib"
        assert candidates[0].source_url == "https://github.com/algorithms/graph-lib/blob/main/cycle.c"
        assert "find_shortest_cycle" in candidates[0].raw_content


def test_web_retriever_caching(mock_github_items):
    items, b64_code, raw_code = mock_github_items
    retriever = GitHubWebRetriever(token="dummy_token_test")

    call_count = 0

    def mock_get(url, *args, **kwargs):
        nonlocal call_count
        call_count += 1
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        if "search/code" in url:
            mock_resp.json.return_value = {"items": items}
        else:
            mock_resp.text = raw_code
        return mock_resp

    sigs = ["unique_cache_test_sig", "MAX_VERTICES_LIMIT"]
    with patch("httpx.Client.get", side_effect=mock_get):
        # 1. First call hits API
        cands1, _ = retriever.retrieve(sigs, "c", max_candidates=1)
        first_count = call_count
        assert len(cands1) == 1

        # 2. Second call must hit cache without invoking new API calls!
        cands2, status2 = retriever.retrieve(sigs, "c", max_candidates=1)
        assert len(cands2) == 1
        assert call_count == first_count  # No additional HTTP requests
        assert "cache" in status2.lower()


def test_web_retriever_rate_limit_handling():
    retriever = GitHubWebRetriever()

    def mock_get_403(*args, **kwargs):
        mock_resp = MagicMock()
        mock_resp.status_code = 403
        return mock_resp

    with patch("httpx.Client.get", side_effect=mock_get_403):
        candidates, status = retriever.retrieve(["test_rate_limit_query"], "c")
        assert candidates == []
        assert "rate limit exceeded" in status.lower()


# -----------------------------------------------------------------------------
# 3. Plagiarism Runner Integration Tests
# -----------------------------------------------------------------------------

def test_web_plagiarism_runner_matching(mock_github_items):
    items, _, raw_code = mock_github_items

    query_code = """
    #include <stdio.h>
    int find_shortest_cycle(int num) {
        int ans = 1;
        int k = 1;
        while (k <= num) {
            ans = ans * k;
            k = k + 1;
        }
        return ans;
    }
    """

    mock_retriever = MagicMock()
    mock_retriever.retrieve.return_value = (
        [
            WebCandidate(
                source_url="https://github.com/algorithms/graph-lib/blob/main/cycle.c",
                repository="algorithms/graph-lib",
                file_name="cycle.c",
                raw_content=raw_code,
                language="c",
            )
        ],
        "Found 1 candidate from GitHub",
    )

    report = run_web_plagiarism_pipeline(
        language="c",
        source=query_code,
        threshold=0.35,
        retriever=mock_retriever,
    )

    assert report.checked is True
    assert len(report.matches) == 1
    match = report.matches[0]
    assert match.repository == "algorithms/graph-lib"
    assert "%" in match.composite_score
    assert "%" in match.token_similarity
    assert "%" in match.logic_similarity
    assert match.composite_score_num >= 0.35
    assert match.target_source is not None


# -----------------------------------------------------------------------------
# 4. API Endpoints Integration Tests
# -----------------------------------------------------------------------------

def test_api_plagiarism_check_web_structure():
    query = {
        "language": "c",
        "source": """
        int find_shortest_cycle(int n) {
            return n * 2;
        }
        """,
        "compare_with": "database",
        "check_web": True,
    }

    # Mock the web pipeline to return a deterministic web match
    mock_web_report = MagicMock()
    mock_web_report.checked = True
    mock_web_report.search_queries_used = ["find_shortest_cycle"]
    mock_web_report.status_message = "Retrieved 1 candidate"
    mock_web_report.matches = [
        MagicMock(
            source_url="https://github.com/owner/repo/blob/main/algo.c",
            repository="owner/repo",
            token_similarity="84.2%",
            logic_similarity="91.0%",
            composite_score="88.3%",
            token_similarity_num=0.842,
            logic_similarity_num=0.910,
            composite_score_num=0.883,
            verdict="likely copied",
            matched_ranges_a=[(2, 4)],
            matched_ranges_b=[(2, 4)],
            target_source="int find_shortest_cycle(int n) { return n * 2; }",
        )
    ]

    with patch("app.api.routes.run_web_plagiarism_pipeline", return_value=mock_web_report):
        resp = client.post("/api/plagiarism/check", json=query)
        assert resp.status_code == 200
        data = resp.json()
        assert "matches" in data
        assert "local_plagiarism" in data
        assert "web_plagiarism" in data

        web_data = data["web_plagiarism"]
        assert web_data["checked"] is True
        assert web_data["search_queries_used"] == ["find_shortest_cycle"]
        assert len(web_data["matches"]) == 1
        first_match = web_data["matches"][0]
        assert first_match["repository"] == "owner/repo"
        assert first_match["token_similarity"] == "84.2%"
        assert first_match["logic_similarity"] == "91.0%"
        assert first_match["composite_score"] == "88.3%"


def test_api_analyze_endpoint():
    req_body = {
        "language": "c",
        "source": """
        #include <stdio.h>
        int main(void) {
            printf("Running CodeGuard Full Analysis\\n");
            return 0;
        }
        """,
        "check_web": False,
    }
    resp = client.post("/api/analyze", json=req_body)
    assert resp.status_code == 200
    data = resp.json()

    # Verify exact schema from requirement
    assert "execution" in data
    assert "local_plagiarism" in data
    assert "web_plagiarism" in data

    assert data["execution"]["compile_ok"] is True
    assert "Running CodeGuard Full Analysis" in data["execution"]["stdout"]
    assert data["execution"]["exit_code"] == 0
    assert "matches" in data["local_plagiarism"]


def test_open_source_archive_fallback():
    from app.retrieval.web_retriever import search_open_source_archive
    cands = search_open_source_archive(["is_palindrome", "remainder", "reversed"], "c")
    assert len(cands) >= 1
    repos = [c.repository for c in cands]
    assert any("TheAlgorithms" in r for r in repos)
    assert any("palindrome" in c.file_name.lower() for c in cands)


def test_palindrome_web_plagiarism_detection():
    palindrome_code = """
    #include <stdio.h>
    #include <stdbool.h>

    bool is_palindrome(int n) {
        int reversed = 0;
        int remainder = 0;
        int original = n;
        while (n > 0) {
            remainder = n % 10;
            reversed = reversed * 10 + remainder;
            n = n / 10;
        }
        return original == reversed;
    }

    int main(void) {
        int num = 12321;
        if (is_palindrome(num)) {
            printf("Palindrome\\n");
        } else {
            printf("Not Palindrome\\n");
        }
        return 0;
    }
    """
    report = run_web_plagiarism_pipeline(
        language="c",
        source=palindrome_code,
        threshold=0.20,
    )
    assert report.checked is True
    assert len(report.matches) >= 1
    top_match = report.matches[0]
    assert "TheAlgorithms" in top_match.repository or "GeeksforGeeks" in top_match.repository
    assert top_match.composite_score_num >= 0.70
    assert top_match.verdict in ("likely copied", "suspicious")
    assert top_match.target_source is not None
    assert len(top_match.matched_ranges_a) > 0
    assert len(top_match.matched_ranges_b) > 0

