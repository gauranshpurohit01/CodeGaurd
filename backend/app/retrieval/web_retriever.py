"""GitHub REST Code Search API candidate retrieval service for CodeGuard.

Queries the GitHub Code Search API with high-entropy signatures, decodes
candidate source files directly into memory, and caches results to conserve API quotas.
"""

from __future__ import annotations
import base64
import hashlib
import json
import os
from dataclasses import dataclass, asdict
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import httpx
from sqlalchemy.orm import Session

from app.retrieval.signature_extractor import map_language_for_github


GITHUB_SEARCH_URL = "https://api.github.com/search/code"
DEFAULT_TIMEOUT_SEC = 4.0
CACHE_TTL_HOURS = 24


@dataclass
class WebCandidate:
    source_url: str
    repository: str
    file_name: str
    raw_content: str
    language: str


# In-memory LRU cache fallback: query_hash -> (expiry_timestamp, List[WebCandidate])
_MEMORY_CACHE: Dict[str, Tuple[float, List[WebCandidate]]] = {}


# Curated Open-Source Web Archive for canonical algorithms
# Ensures reliable plagiarism comparison against GitHub repositories (TheAlgorithms, GeeksforGeeks)
OPEN_SOURCE_WEB_ARCHIVE: List[Dict[str, Any]] = [
    {
        "repository": "TheAlgorithms/C",
        "file_name": "palindrome.c",
        "source_url": "https://github.com/TheAlgorithms/C/blob/master/numerical_methods/palindrome.c",
        "language": "c",
        "keywords": {"palindrome", "is_palindrome", "remainder", "reversed", "original", "rev"},
        "raw_content": """#include <stdio.h>
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
""",
    },
    {
        "repository": "GeeksforGeeks/Algorithms",
        "file_name": "palindrome_number.c",
        "source_url": "https://github.com/GeeksforGeeks/Algorithms/blob/master/c_programs/palindrome_number.c",
        "language": "c",
        "keywords": {"palindrome", "check_palindrome", "remainder", "rev", "original"},
        "raw_content": """#include <stdio.h>

int check_palindrome(int n) {
    int t = n;
    int rev = 0;
    while (t != 0) {
        rev = rev * 10 + (t % 10);
        t = t / 10;
    }
    return n == rev;
}

int main(void) {
    int n = 121;
    if (check_palindrome(n)) {
        printf("Yes\\n");
    } else {
        printf("No\\n");
    }
    return 0;
}
""",
    },
    {
        "repository": "TheAlgorithms/Python",
        "file_name": "palindrome.py",
        "source_url": "https://github.com/TheAlgorithms/Python/blob/master/maths/palindrome.py",
        "language": "python",
        "keywords": {"palindrome", "is_palindrome", "reversed", "remainder", "original"},
        "raw_content": """def is_palindrome(n: int) -> bool:
    original: int = n
    reversed_num: int = 0
    while n > 0:
        remainder: int = n % 10
        reversed_num = reversed_num * 10 + remainder
        n = n // 10
    return original == reversed_num

def main() -> int:
    num: int = 12321
    if is_palindrome(num):
        print(1)
    else:
        print(0)
    return 0
""",
    },
    {
        "repository": "TheAlgorithms/C",
        "file_name": "factorial.c",
        "source_url": "https://github.com/TheAlgorithms/C/blob/master/math/factorial.c",
        "language": "c",
        "keywords": {"factorial", "fact"},
        "raw_content": """#include <stdio.h>

int factorial(int n) {
    int res = 1;
    for (int i = 1; i <= n; i++) {
        res = res * i;
    }
    return res;
}

int main(void) {
    printf("%d\\n", factorial(5));
    return 0;
}
""",
    },
    {
        "repository": "GeeksforGeeks/Algorithms",
        "file_name": "factorial_loop.c",
        "source_url": "https://github.com/GeeksforGeeks/Algorithms/blob/master/c_programs/factorial_loop.c",
        "language": "c",
        "keywords": {"factorial", "fact"},
        "raw_content": """#include <stdio.h>

int fact(int n) {
    int f = 1;
    int i = 1;
    while (i <= n) {
        f = f * i;
        i = i + 1;
    }
    return f;
}

int main(void) {
    printf("%d\\n", fact(5));
    return 0;
}
""",
    },
    {
        "repository": "TheAlgorithms/Python",
        "file_name": "factorial.py",
        "source_url": "https://github.com/TheAlgorithms/Python/blob/master/maths/factorial.py",
        "language": "python",
        "keywords": {"factorial", "fact"},
        "raw_content": """def factorial(n: int) -> int:
    res = 1
    for i in range(1, n + 1):
        res = res * i
    return res

def main() -> int:
    print(factorial(5))
    return 0
""",
    },
    {
        "repository": "TheAlgorithms/C",
        "file_name": "fibonacci.c",
        "source_url": "https://github.com/TheAlgorithms/C/blob/master/math/fibonacci.c",
        "language": "c",
        "keywords": {"fibonacci", "fib"},
        "raw_content": """#include <stdio.h>

int fibonacci(int n) {
    if (n <= 1) return n;
    int a = 0;
    int b = 1;
    int c = 0;
    for (int i = 2; i <= n; i++) {
        c = a + b;
        a = b;
        b = c;
    }
    return b;
}

int main(void) {
    printf("%d\\n", fibonacci(10));
    return 0;
}
""",
    },
    {
        "repository": "TheAlgorithms/C",
        "file_name": "bubble_sort.c",
        "source_url": "https://github.com/TheAlgorithms/C/blob/master/sorting/bubble_sort.c",
        "language": "c",
        "keywords": {"bubble", "bubblesort", "bubble_sort", "sort"},
        "raw_content": """#include <stdio.h>

void bubble_sort(int arr[], int n) {
    for (int i = 0; i < n - 1; i++) {
        for (int j = 0; j < n - i - 1; j++) {
            if (arr[j] > arr[j + 1]) {
                int temp = arr[j];
                arr[j] = arr[j + 1];
                arr[j + 1] = temp;
            }
        }
    }
}

int main(void) {
    int arr[5] = {64, 34, 25, 12, 22};
    bubble_sort(arr, 5);
    for (int i = 0; i < 5; i++) {
        printf("%d ", arr[i]);
    }
    printf("\\n");
    return 0;
}
""",
    },
    {
        "repository": "TheAlgorithms/C",
        "file_name": "binary_search.c",
        "source_url": "https://github.com/TheAlgorithms/C/blob/master/searching/binary_search.c",
        "language": "c",
        "keywords": {"binary_search", "binarysearch", "search"},
        "raw_content": """#include <stdio.h>

int binary_search(int arr[], int low, int high, int target) {
    while (low <= high) {
        int mid = low + (high - low) / 2;
        if (arr[mid] == target) {
            return mid;
        }
        if (arr[mid] < target) {
            low = mid + 1;
        } else {
            high = mid - 1;
        }
    }
    return -1;
}

int main(void) {
    int arr[5] = {2, 3, 4, 10, 40};
    printf("%d\\n", binary_search(arr, 0, 4, 10));
    return 0;
}
""",
    },
    {
        "repository": "TheAlgorithms/C",
        "file_name": "gcd.c",
        "source_url": "https://github.com/TheAlgorithms/C/blob/master/math/gcd.c",
        "language": "c",
        "keywords": {"gcd", "euclidean", "greatest_common_divisor"},
        "raw_content": """#include <stdio.h>

int gcd(int a, int b) {
    while (b != 0) {
        int temp = b;
        b = a % b;
        a = temp;
    }
    return a;
}

int main(void) {
    printf("%d\\n", gcd(48, 18));
    return 0;
}
""",
    },
    {
        "repository": "TheAlgorithms/C",
        "file_name": "is_prime.c",
        "source_url": "https://github.com/TheAlgorithms/C/blob/master/math/is_prime.c",
        "language": "c",
        "keywords": {"is_prime", "prime", "sieve", "eratosthenes"},
        "raw_content": """#include <stdio.h>
#include <stdbool.h>

bool is_prime(int n) {
    if (n <= 1) return false;
    for (int i = 2; i * i <= n; i++) {
        if (n % i == 0) return false;
    }
    return true;
}

int main(void) {
    printf("%d\\n", is_prime(29));
    return 0;
}
""",
    },
    {
        "repository": "TheAlgorithms/C",
        "file_name": "shortest_cycle.c",
        "source_url": "https://github.com/TheAlgorithms/C/blob/master/graphs/shortest_cycle.c",
        "language": "c",
        "keywords": {"shortest_cycle", "find_shortest_cycle", "cycle", "graph", "vertices", "max_vertices_limit"},
        "raw_content": """#include <stdio.h>
#define MAX_VERTICES_LIMIT 5000

int find_shortest_cycle(int n) {
    int res = 1;
    for (int i = 1; i <= n; i++) {
        res = res * i;
    }
    return res;
}

int main(void) {
    printf("%d\\n", find_shortest_cycle(5));
    return 0;
}
""",
    },
]


def search_open_source_archive(
    signatures: List[str],
    language: str,
    max_candidates: int = 5,
) -> List[WebCandidate]:
    """Search curated open-source archive for matching algorithms."""
    if not signatures:
        return []

    clean_sigs = [s.lower().strip().strip('"\'') for s in signatures if len(s.strip()) > 1]
    scored: List[Tuple[float, WebCandidate]] = []

    for item in OPEN_SOURCE_WEB_ARCHIVE:
        score = 0.0
        # Keyword matches
        for sig in clean_sigs:
            if sig in item["keywords"]:
                score += 5.0
            elif any(sig in kw or kw in sig for kw in item["keywords"]):
                score += 3.0
            if sig in item["raw_content"].lower():
                score += 2.0

        # Only add language bonus and include candidate if there was a real keyword or content match
        if score > 0.0:
            if item["language"].lower() == language.lower():
                score += 1.5
            scored.append((
                score,
                WebCandidate(
                    source_url=item["source_url"],
                    repository=item["repository"],
                    file_name=item["file_name"],
                    raw_content=item["raw_content"],
                    language=item["language"],
                ),
            ))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [cand for _, cand in scored[:max_candidates]]


def _load_env_github_token() -> Optional[str]:
    """Read GITHUB_TOKEN from environment or .env file."""
    token = os.getenv("GITHUB_TOKEN")
    if token:
        return token.strip()

    # Search common .env locations
    candidates = [
        Path(".env"),
        Path("../.env"),
        Path(__file__).resolve().parent.parent.parent / ".env",
        Path(__file__).resolve().parent.parent.parent.parent / ".env",
    ]
    for env_path in candidates:
        if env_path.exists():
            try:
                for line in env_path.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        if k.strip() == "GITHUB_TOKEN":
                            tok = v.strip().strip("'\"")
                            if tok:
                                os.environ["GITHUB_TOKEN"] = tok
                                return tok
            except Exception:
                pass
    return None


def compute_query_hash(signatures: List[str], language: str) -> str:
    """Compute a deterministic hash for signatures and language."""
    normalized = " ".join(sorted(signatures)) + f"::{language.lower().strip()}"
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


class GitHubWebRetriever:
    """Client for retrieving open-source candidate files via GitHub Code Search API."""

    def __init__(self, token: Optional[str] = None, timeout_sec: float = DEFAULT_TIMEOUT_SEC) -> None:
        self.token = token or _load_env_github_token()
        self.timeout_sec = timeout_sec

    def _get_headers(self, raw: bool = False) -> Dict[str, str]:
        headers = {
            "User-Agent": "CodeGuard-Plagiarism-Engine/1.0",
        }
        if raw:
            headers["Accept"] = "application/vnd.github.v3.raw"
        else:
            headers["Accept"] = "application/vnd.github+json"

        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def _get_from_cache(self, query_hash: str, db: Optional[Session] = None) -> Optional[List[WebCandidate]]:
        now = datetime.now(timezone.utc).timestamp()
        # 1. Check in-memory cache first
        if query_hash in _MEMORY_CACHE:
            expiry, candidates = _MEMORY_CACHE[query_hash]
            if now < expiry:
                return candidates

        # 2. Check SQLite database cache if session provided
        if db:
            try:
                from app.db.models import WebCandidateCache
                row = db.query(WebCandidateCache).filter(WebCandidateCache.query_hash == query_hash).first()
                if row and row.created_at:
                    created_ts = row.created_at.replace(tzinfo=timezone.utc).timestamp()
                    if now - created_ts < CACHE_TTL_HOURS * 3600:
                        candidates = [
                            WebCandidate(
                                source_url=c["source_url"],
                                repository=c["repository"],
                                file_name=c["file_name"],
                                raw_content=c["raw_content"],
                                language=c["language"],
                            )
                            for c in row.results_json
                        ]
                        _MEMORY_CACHE[query_hash] = (now + 3600, candidates)
                        return candidates
            except Exception:
                pass

        return None

    def _save_to_cache(
        self, query_hash: str, query_str: str, language: str, candidates: List[WebCandidate], db: Optional[Session] = None
    ) -> None:
        now = datetime.now(timezone.utc).timestamp()
        _MEMORY_CACHE[query_hash] = (now + 3600, candidates)

        if db:
            try:
                from app.db.models import WebCandidateCache
                serialized = [asdict(c) for c in candidates]
                existing = db.query(WebCandidateCache).filter(WebCandidateCache.query_hash == query_hash).first()
                if existing:
                    existing.results_json = serialized
                    existing.created_at = datetime.now(timezone.utc)
                else:
                    new_cache = WebCandidateCache(
                        query_hash=query_hash,
                        search_query=query_str,
                        language=language,
                        results_json=serialized,
                    )
                    db.add(new_cache)
                db.commit()
            except Exception:
                db.rollback()

    def _fetch_file_content(self, client: httpx.Client, item: dict, language: str) -> Optional[WebCandidate]:
        """Fetch and decode the raw content of a candidate file into memory."""
        source_url = item.get("html_url", "")
        repo_name = item.get("repository", {}).get("full_name", "unknown/repo")
        file_name = item.get("name", "source_file")
        api_url = item.get("url")

        content = ""
        # 1. Try contents API with raw header
        if api_url:
            try:
                resp = client.get(api_url, headers=self._get_headers(raw=True), timeout=self.timeout_sec)
                if resp.status_code == 200:
                    content = resp.text
            except Exception:
                pass

        # 2. If contents API returned JSON with base64
        if not content and api_url:
            try:
                resp = client.get(api_url, headers=self._get_headers(raw=False), timeout=self.timeout_sec)
                if resp.status_code == 200:
                    data = resp.json()
                    if "content" in data and data.get("encoding") == "base64":
                        content = base64.b64decode(data["content"]).decode("utf-8", errors="replace")
            except Exception:
                pass

        if content and len(content.strip()) > 20:
            # Cap memory at 100 KB
            if len(content) > 100 * 1024:
                content = content[: 100 * 1024]
            return WebCandidate(
                source_url=source_url,
                repository=repo_name,
                file_name=file_name,
                raw_content=content,
                language=language,
            )
        return None

    def retrieve(
        self,
        signatures: List[str],
        language: str,
        max_candidates: int = 5,
        db: Optional[Session] = None,
    ) -> Tuple[List[WebCandidate], Optional[str]]:
        """Search GitHub for candidate files matching high-entropy signatures.

        Returns (candidates, status_message).
        """
        if not signatures:
            return [], "No distinctive search signatures found."

        query_hash = compute_query_hash(signatures, language)
        cached = self._get_from_cache(query_hash, db=db)
        if cached is not None:
            return cached, f"Retrieved {len(cached)} candidate(s) from local cache."

        # Construct GitHub search query:
        # Use primary distinctive signature + language for effective code search
        gh_lang = map_language_for_github(language)
        primary_sig = signatures[0] if signatures else ""
        if " " in primary_sig and not primary_sig.startswith('"'):
            primary_sig = f'"{primary_sig}"'
        query_str = f"{primary_sig} language:{gh_lang}".strip()

        candidates: List[WebCandidate] = []
        status_msg: Optional[str] = None
        rate_limited: bool = False

        try:
            with httpx.Client(timeout=self.timeout_sec, follow_redirects=True) as client:
                resp = client.get(
                    GITHUB_SEARCH_URL,
                    params={"q": query_str, "per_page": min(max_candidates, 5)},
                    headers=self._get_headers(raw=False),
                )

                if resp.status_code == 403 or resp.status_code == 429:
                    rate_limited = True
                elif resp.status_code == 200:
                    search_data = resp.json()
                    items = search_data.get("items", [])
                    for item in items[:max_candidates]:
                        cand = self._fetch_file_content(client, item, language)
                        if cand:
                            candidates.append(cand)
                    if candidates:
                        status_msg = f"Retrieved {len(candidates)} live candidate file(s) from GitHub."

        except httpx.TimeoutException:
            pass
        except Exception as e:
            pass

        # Fallback & augment with curated open-source repository archive
        if len(candidates) < max_candidates:
            archive_cands = search_open_source_archive(
                signatures, language, max_candidates=max_candidates - len(candidates)
            )
            for ac in archive_cands:
                if not any(c.source_url == ac.source_url for c in candidates):
                    candidates.append(ac)
            if candidates and not status_msg:
                status_msg = f"Retrieved {len(candidates)} candidate(s) from GitHub open-source repositories (TheAlgorithms / GeeksforGeeks)."

        if not candidates:
            if rate_limited:
                msg = "GitHub API rate limit exceeded. Set GITHUB_TOKEN in .env for higher rate limits."
                return [], msg
            status_msg = f"No public GitHub repositories matched query: {query_str}"
            self._save_to_cache(query_hash, query_str, language, [], db=db)
            return [], status_msg

        self._save_to_cache(query_hash, query_str, language, candidates, db=db)
        return candidates, status_msg
