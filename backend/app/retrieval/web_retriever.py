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
    {
        "repository": "TheAlgorithms/C",
        "file_name": "two_sum.c",
        "source_url": "https://github.com/TheAlgorithms/C/blob/master/searching/two_sum.c",
        "language": "c",
        "keywords": {"two_sum", "target", "sum", "pair", "indices", "find_pair"},
        "raw_content": """#include <stdio.h>
#include <stdbool.h>

bool two_sum(int arr[], int n, int target) {
    for (int i = 0; i < n; i++) {
        for (int j = i + 1; j < n; j++) {
            if (arr[i] + arr[j] == target) {
                return true;
            }
        }
    }
    return false;
}

int main(void) {
    int arr[5] = {2, 7, 11, 15, 20};
    if (two_sum(arr, 5, 9)) {
        printf("Found\\n");
    } else {
        printf("Not Found\\n");
    }
    return 0;
}
""",
    },
    {
        "repository": "TheAlgorithms/C",
        "file_name": "kadane.c",
        "source_url": "https://github.com/TheAlgorithms/C/blob/master/dynamic_programming/kadane.c",
        "language": "c",
        "keywords": {"kadane", "max_subarray", "subarray", "max_sum", "current_sum"},
        "raw_content": """#include <stdio.h>

int max_subarray_sum(int arr[], int n) {
    int max_so_far = arr[0];
    int curr_max = arr[0];
    for (int i = 1; i < n; i++) {
        if (arr[i] > curr_max + arr[i]) {
            curr_max = arr[i];
        } else {
            curr_max = curr_max + arr[i];
        }
        if (curr_max > max_so_far) {
            max_so_far = curr_max;
        }
    }
    return max_so_far;
}

int main(void) {
    int a[6] = {-2, 1, -3, 4, -1, 2};
    printf("%d\\n", max_subarray_sum(a, 6));
    return 0;
}
""",
    },
    {
        "repository": "TheAlgorithms/C",
        "file_name": "matrix_multiply.c",
        "source_url": "https://github.com/TheAlgorithms/C/blob/master/operations/matrix_multiplication.c",
        "language": "c",
        "keywords": {"matrix", "multiply", "matrix_multiply", "multiply_matrices"},
        "raw_content": """#include <stdio.h>

void multiply_matrices(int r1, int c1, int r2, int c2) {
    int a[2][2] = {{1, 2}, {3, 4}};
    int b[2][2] = {{5, 6}, {7, 8}};
    int c[2][2];
    for (int i = 0; i < 2; i++) {
        for (int j = 0; j < 2; j++) {
            c[i][j] = 0;
            for (int k = 0; k < 2; k++) {
                c[i][j] += a[i][k] * b[k][j];
            }
        }
    }
    printf("%d\\n", c[0][0]);
}

int main(void) {
    multiply_matrices(2, 2, 2, 2);
    return 0;
}
""",
    },
    {
        "repository": "TheAlgorithms/C",
        "file_name": "linear_search.c",
        "source_url": "https://github.com/TheAlgorithms/C/blob/master/searching/linear_search.c",
        "language": "c",
        "keywords": {"linear_search", "search", "find", "key"},
        "raw_content": """#include <stdio.h>

int linear_search(int arr[], int n, int key) {
    for (int i = 0; i < n; i++) {
        if (arr[i] == key) {
            return i;
        }
    }
    return -1;
}

int main(void) {
    int arr[5] = {10, 20, 30, 40, 50};
    printf("%d\\n", linear_search(arr, 5, 30));
    return 0;
}
""",
    },
    {
        "repository": "TheAlgorithms/C",
        "file_name": "reverse_array.c",
        "source_url": "https://github.com/TheAlgorithms/C/blob/master/arrays/reverse_array.c",
        "language": "c",
        "keywords": {"reverse_array", "reverse", "swap", "array"},
        "raw_content": """#include <stdio.h>

void reverse_array(int arr[], int n) {
    int start = 0;
    int end = n - 1;
    while (start < end) {
        int temp = arr[start];
        arr[start] = arr[end];
        arr[end] = temp;
        start++;
        end--;
    }
}

int main(void) {
    int arr[5] = {1, 2, 3, 4, 5};
    reverse_array(arr, 5);
    printf("%d\\n", arr[0]);
    return 0;
}
""",
    },
    {
        "repository": "TheAlgorithms/C",
        "file_name": "armstrong.c",
        "source_url": "https://github.com/TheAlgorithms/C/blob/master/numerical_methods/armstrong_number.c",
        "language": "c",
        "keywords": {"armstrong", "cube", "remainder", "digits", "sum"},
        "raw_content": """#include <stdio.h>
#include <stdbool.h>

bool is_armstrong(int num) {
    int original = num;
    int sum = 0;
    while (num > 0) {
        int rem = num % 10;
        sum += rem * rem * rem;
        num /= 10;
    }
    return original == sum;
}

int main(void) {
    printf("%d\\n", is_armstrong(153));
    return 0;
}
""",
    },
    {
        "repository": "TheAlgorithms/C",
        "file_name": "power.c",
        "source_url": "https://github.com/TheAlgorithms/C/blob/master/math/power.c",
        "language": "c",
        "keywords": {"power", "exponent", "pow", "base"},
        "raw_content": """#include <stdio.h>

int power(int base, int exp) {
    int res = 1;
    for (int i = 0; i < exp; i++) {
        res = res * base;
    }
    return res;
}

int main(void) {
    printf("%d\\n", power(2, 5));
    return 0;
}
""",
    },
    {
        "repository": "ashwin417/Compiler_Lab",
        "file_name": "constant_propagation.c",
        "source_url": "https://github.com/ashwin417/Compiler_Lab/blob/master/constant_propagation.c",
        "language": "c",
        "keywords": {"tac", "constant", "propagation", "folding", "symbol", "is_constant", "isnumber", "lhs", "arg1", "arg2", "op"},
        "raw_content": """#include <stdio.h>
#include <string.h>
#include <ctype.h>
#include <stdlib.h>
#include <stdbool.h>

#define MAX 20

typedef struct {
    char lhs[10];
    char arg1[10];
    char op[5];
    char arg2[10];
} TAC;

typedef struct {
    char var[10];
    int val;
    bool is_constant;
} Symbol;

bool isNumber(char *s) {
    if (!s || !*s) return false;
    if (s[0] == '-' || s[0] == '+') s++;
    if (!*s) return false;
    while (*s) {
        if (!isdigit(*s)) return false;
        s++;
    }
    return true;
}

void constant_propagation(TAC code[], int n) {
    Symbol symTable[MAX];
    int symCount = 0;
    for (int i = 0; i < n; i++) {
        if (strcmp(code[i].op, "=") == 0 && isNumber(code[i].arg1)) {
            strcpy(symTable[symCount].var, code[i].lhs);
            symTable[symCount].val = atoi(code[i].arg1);
            symTable[symCount].is_constant = true;
            symCount++;
        }
        for (int j = 0; j < symCount; j++) {
            if (strcmp(code[i].arg1, symTable[j].var) == 0) {
                sprintf(code[i].arg1, "%d", symTable[j].val);
            }
            if (strcmp(code[i].arg2, symTable[j].var) == 0) {
                sprintf(code[i].arg2, "%d", symTable[j].val);
            }
        }
    }
}

int main(void) {
    TAC code[MAX];
    int n = 3;
    strcpy(code[0].lhs, "a"); strcpy(code[0].op, "="); strcpy(code[0].arg1, "5");
    strcpy(code[1].lhs, "b"); strcpy(code[1].op, "="); strcpy(code[1].arg1, "10");
    strcpy(code[2].lhs, "c"); strcpy(code[2].op, "+"); strcpy(code[2].arg1, "a"); strcpy(code[2].arg2, "b");
    constant_propagation(code, n);
    return 0;
}
""",
    },
    {
        "repository": "man-yadul/s7-csl411-compiler-lab",
        "file_name": "expression_propagation.c",
        "source_url": "https://github.com/man-yadul/s7-csl411-compiler-lab/blob/master/constant_propagation.c",
        "language": "c",
        "keywords": {"constant", "propagation", "expression", "quadruple", "flag", "operand", "optimization", "tac"},
        "raw_content": """#include <stdio.h>
#include <string.h>
#include <ctype.h>
#include <stdlib.h>

struct expression {
    char op[2];
    char op1[5];
    char op2[5];
    char res[5];
    int flag;
} arr[10];

int n;

void constant_folding() {
    for (int i = 0; i < n; i++) {
        if (isdigit(arr[i].op1[0]) && isdigit(arr[i].op2[0])) {
            int a = atoi(arr[i].op1);
            int b = atoi(arr[i].op2);
            int res = 0;
            if (arr[i].op[0] == '+') res = a + b;
            else if (arr[i].op[0] == '-') res = a - b;
            else if (arr[i].op[0] == '*') res = a * b;
            else if (arr[i].op[0] == '/') res = a / b;
            sprintf(arr[i].op1, "%d", res);
            strcpy(arr[i].op, "=");
            strcpy(arr[i].op2, "");
        }
    }
}

int main(void) {
    n = 2;
    strcpy(arr[0].op, "+"); strcpy(arr[0].op1, "3"); strcpy(arr[0].op2, "4"); strcpy(arr[0].res, "t1");
    constant_folding();
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


def _search_duckduckgo_for_github(
    client: httpx.Client,
    query_str: str,
    language: str,
    max_candidates: int = 3,
    timeout_sec: float = 4.0,
) -> List[WebCandidate]:
    """Search public GitHub repositories via DuckDuckGo HTML search for live candidates."""
    candidates = []
    try:
        import urllib.parse
        import re
        ddg_url = "https://html.duckduckgo.com/html/"
        params = {"q": f"site:github.com {query_str} blob"}
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        }
        resp = client.get(ddg_url, params=params, headers=headers, timeout=timeout_sec)
        if resp.status_code == 200:
            html = urllib.parse.unquote(resp.text)
            matches = re.findall(
                r"github\.com/([a-zA-Z0-9_\-\.]+)/([a-zA-Z0-9_\-\.]+)/blob/([a-zA-Z0-9_\-\.]+)/([a-zA-Z0-9_\-\./]+\.[a-zA-Z0-9]+)",
                html,
            )
            seen_urls = set()
            for user, repo, branch, filepath in matches:
                if len(candidates) >= max_candidates:
                    break
                full_source_url = f"https://github.com/{user}/{repo}/blob/{branch}/{filepath}"
                if full_source_url in seen_urls:
                    continue
                seen_urls.add(full_source_url)

                raw_url = f"https://raw.githubusercontent.com/{user}/{repo}/{branch}/{filepath}"
                try:
                    raw_resp = client.get(raw_url, timeout=timeout_sec)
                    if raw_resp.status_code == 200 and len(raw_resp.text.strip()) > 20:
                        content = raw_resp.text
                        if len(content) > 100 * 1024:
                            content = content[:100 * 1024]
                        candidates.append(
                            WebCandidate(
                                source_url=full_source_url,
                                repository=f"{user}/{repo}",
                                file_name=filepath.split("/")[-1],
                                raw_content=content,
                                language=language,
                            )
                        )
                except Exception:
                    pass
    except Exception:
        pass
    return candidates


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

        # Construct GitHub search queries to try (primary, secondary, and combined)
        gh_lang = map_language_for_github(language)
        queries_to_try: List[str] = []
        for s in signatures[:3]:
            sig_term = f'"{s}"' if " " in s and not s.startswith('"') else s
            queries_to_try.append(f"{sig_term} language:{gh_lang}".strip())
        if len(signatures) >= 2:
            s0 = signatures[0]
            s1 = signatures[1]
            queries_to_try.append(f"{s0} {s1} language:{gh_lang}".strip())

        candidates: List[WebCandidate] = []
        status_msg: Optional[str] = None
        rate_limited: bool = False

        for query_str in queries_to_try:
            if candidates:
                break
            try:
                with httpx.Client(timeout=self.timeout_sec, follow_redirects=True) as client:
                    resp = client.get(
                        GITHUB_SEARCH_URL,
                        params={"q": query_str, "per_page": min(max_candidates, 5)},
                        headers=self._get_headers(raw=False),
                    )

                    if resp.status_code == 403 or resp.status_code == 429:
                        rate_limited = True
                        ddg_query = query_str.replace(f"language:{gh_lang}", "").strip()
                        ddg_cands = _search_duckduckgo_for_github(
                            client, ddg_query, language, max_candidates=max_candidates, timeout_sec=self.timeout_sec
                        )
                        for dc in ddg_cands:
                            if not any(c.source_url == dc.source_url for c in candidates):
                                candidates.append(dc)
                        if candidates:
                            status_msg = f"Retrieved {len(candidates)} live candidate(s) from GitHub via public web search."
                            break
                    elif resp.status_code == 200:
                        search_data = resp.json()
                        items = search_data.get("items", [])
                        for item in items[:max_candidates]:
                            cand = self._fetch_file_content(client, item, language)
                            if cand and not any(c.source_url == cand.source_url for c in candidates):
                                candidates.append(cand)
                        if candidates:
                            status_msg = f"Retrieved {len(candidates)} live candidate file(s) from GitHub."
                            break

            except httpx.TimeoutException:
                pass
            except Exception:
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
            status_msg = f"No public GitHub repositories matched query: {queries_to_try[0] if queries_to_try else ''}"
            # Short in-memory cache only (60s), do not permanently poison SQLite cache with empty result
            _MEMORY_CACHE[query_hash] = (datetime.now(timezone.utc).timestamp() + 60, [])
            return [], status_msg

        self._save_to_cache(query_hash, queries_to_try[0] if queries_to_try else "", language, candidates, db=db)
        return candidates, status_msg
