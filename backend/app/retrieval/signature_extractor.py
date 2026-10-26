"""High-entropy signature extraction module for CodeGuard web retrieval.

Extracts distinctive search tokens (custom function signatures, class names,
unique string literals, and high-entropy mathematical constants) from submitted
code to query public repositories on GitHub.
"""

from __future__ import annotations
import math
import re
from typing import List, Set, Tuple


COMMON_KEYWORDS: Set[str] = {
    # C/C++ keywords
    "auto", "break", "case", "char", "const", "continue", "default", "do",
    "double", "else", "enum", "extern", "float", "for", "goto", "if",
    "int", "long", "register", "return", "short", "signed", "sizeof", "static",
    "struct", "switch", "typedef", "union", "unsigned", "void", "volatile", "while",
    "bool", "class", "namespace", "using", "public", "private", "protected",
    "virtual", "template", "typename", "new", "delete", "this", "nullptr",
    "std", "cin", "cout", "endl", "string", "vector", "map", "set", "queue", "stack",
    "malloc", "free", "printf", "scanf", "include", "define", "ifdef", "endif",
    "stdio", "stdlib", "math", "string", "iostream", "sstream", "fstream", "algorithm",
    "utility", "memory", "chrono", "unistd", "stdbool", "fcntl", "time", "errno", "ctype",
    "limits", "stddef", "stdint",
    # Python keywords
    "def", "import", "from", "as", "class", "return", "pass", "raise", "yield",
    "try", "except", "finally", "with", "lambda", "global", "nonlocal", "assert",
    "del", "async", "await", "None", "True", "False", "self", "range", "len",
    "print", "input", "str", "list", "dict", "tuple", "int", "float", "bool",
    # Java keywords
    "public", "private", "protected", "static", "final", "abstract", "extends",
    "implements", "interface", "package", "import", "throws", "throw", "native",
    "synchronized", "transient", "volatile", "strictfp", "super", "null", "boolean",
    "byte", "char", "short", "int", "long", "float", "double", "System", "out", "println",
    # Generic and ubiquitous identifiers
    "main", "solve", "test", "tests", "init", "run", "start", "stop", "end", "begin",
    "helper", "check", "process", "compute", "get", "set", "read", "write", "data",
    "item", "items", "val", "value", "values", "res", "result", "results", "ans",
    "answer", "ret", "temp", "tmp", "swap", "foo", "bar", "baz", "qux", "node",
    "nodes", "head", "tail", "next", "prev", "curr", "current", "ptr", "idx",
    "index", "size", "length", "count", "cnt", "total", "sum", "diff", "prod",
    "num", "nums", "element", "elements", "arr", "array", "flag", "found", "ok",
    "done", "visited", "vis", "dp", "adj", "graph", "tree", "root", "leaf",
    "parent", "child", "left", "right", "top", "bottom", "low", "high", "mid",
    "min", "max", "step", "iter", "loop", "first", "second", "third", "last",
    "row", "col", "rows", "cols", "var", "param", "arg", "args", "kwargs",
}

DISTINCTIVE_ALGO_ROOTS: List[str] = [
    "dijkstra", "bellman", "kruskal", "prim", "floyd", "warshall", "tarjan",
    "kosaraju", "euler", "hamilton", "knapsack", "rabin", "karp", "boyer",
    "moore", "aho", "corasick", "segment_tree", "fenwick", "trie", "convex_hull",
    "graham", "jarvis", "levenshtein", "edit_distance", "lcs", "lis",
    "shortest_cycle", "shortest_path", "max_flow", "dinic", "ford_fulkerson",
    "topological_sort", "bipartite", "quicksort", "mergesort", "heapsort",
    "sieve_eratosthenes", "modular_inverse", "gaussian_elimination",
]

HIGH_ENTROPY_CONSTANTS: Set[str] = {
    "1000000007", "998244353", "2147483647", "1000000009", "1000000000",
    "0x5f3759df", "0x3f3f3f3f", "100005", "200005", "500005",
}


def _calculate_entropy(text: str) -> float:
    """Calculate Shannon character entropy for a token."""
    if not text:
        return 0.0
    freq = {}
    for ch in text.lower():
        freq[ch] = freq.get(ch, 0) + 1
    length = len(text)
    entropy = -sum((count / length) * math.log2(count / length) for count in freq.values())
    return entropy


def _score_identifier(name: str) -> float:
    """Score an identifier's distinctiveness for code search queries."""
    clean = name.strip()
    if clean in COMMON_KEYWORDS or clean.lower() in COMMON_KEYWORDS:
        return 0.0
    if len(clean) < 5:
        return 0.0

    score = 1.0

    # Length factor (longer names are typically more unique)
    score += min(len(clean), 25) / 5.0

    # Snake_case or camelCase with multiple components
    has_underscore = "_" in clean
    has_camel = bool(re.search(r"[a-z][A-Z]", clean))
    if has_underscore or has_camel:
        score += 2.0

    # Contains domain-specific algorithm keywords
    clean_lower = clean.lower()
    for root in DISTINCTIVE_ALGO_ROOTS:
        if root in clean_lower:
            score += 3.5
            break

    # Shannon entropy bonus
    entropy = _calculate_entropy(clean)
    score += entropy * 0.8

    # High-entropy constant names (e.g. MAX_VERTICES_LIMIT)
    if clean.isupper() and len(clean) >= 8 and "_" in clean:
        score += 2.5

    return score


def _extract_string_literals(source: str) -> List[Tuple[str, float]]:
    """Extract and score distinctive string literals from code."""
    results = []
    # Match double-quoted and single-quoted strings
    matches = re.findall(r'"([^"\\]*(?:\\.[^"\\]*)*)"|\'([^\'\\]*(?:\\.[^\'\\]*)*)\'', source)
    for m1, m2 in matches:
        lit = m1 or m2
        lit = lit.strip()
        # Remove common escape sequences
        lit_clean = re.sub(r"\\[nrtvf0]", " ", lit).strip()
        # Filter trivial or format-only strings
        if len(lit_clean) < 10 or len(lit_clean) > 80:
            continue
        if re.match(r"^%[-+0-9#]*[a-zA-Z\s]+$", lit_clean):
            continue
        words = [w for w in re.split(r"[^a-zA-Z0-9_]+", lit_clean) if len(w) >= 3]
        if len(words) < 2:
            continue

        # Score the string phrase
        phrase = " ".join(words[:5])
        score = 2.5 + min(len(words), 5) * 0.6
        for w in words:
            if w.lower() in COMMON_KEYWORDS:
                score -= 0.3
        if score >= 3.0:
            results.append((phrase, score))

    return results


def extract_signatures(language: str, source: str, max_tokens: int = 4) -> List[str]:
    """Extract 2 to 4 high-entropy search tokens from user code.

    Returns an empty list if code contains only generic boilerplate,
    signaling the caller to gracefully fallback to local-only search.
    """
    if not source or not source.strip():
        return []

    scored_candidates: List[Tuple[str, float]] = []
    seen: Set[str] = set()

    # 1. Custom function and class names (regex patterns per language)
    func_patterns = [
        # C / C++ / Java: return_type func_name(
        r"\b(?:[A-Za-z_][A-Za-z0-9_<>\*&\s]+)\s+([A-Za-z_][A-Za-z0-9_]{4,})\s*\(",
        # Python: def func_name(
        r"\bdef\s+([A-Za-z_][A-Za-z0-9_]{4,})\s*\(",
        # Java/Python: class ClassName
        r"\bclass\s+([A-Za-z_][A-Za-z0-9_]{4,})\b",
    ]
    for pattern in func_patterns:
        for match in re.finditer(pattern, source):
            name = match.group(1).strip()
            if name not in seen:
                score = _score_identifier(name)
                if score >= 3.0:
                    scored_candidates.append((name, score))
                    seen.add(name)

    # 2. General identifiers (variables, constants, struct fields)
    all_identifiers = set(re.findall(r"\b[A-Za-z_][A-Za-z0-9_]{4,}\b", source))
    for name in all_identifiers:
        if name not in seen:
            score = _score_identifier(name)
            if score >= 3.5:
                scored_candidates.append((name, score))
                seen.add(name)

    # 3. High-entropy constants (numbers like 1000000007, 0x5f3759df)
    for num_pattern in [r"\b0x[0-9a-fA-F]+\b", r"\b\d{6,}\b"]:
        for match in re.finditer(num_pattern, source):
            val = match.group(0).lower()
            if val in HIGH_ENTROPY_CONSTANTS or len(val) >= 7:
                if val not in seen:
                    scored_candidates.append((val, 4.0))
                    seen.add(val)

    # 4. Distinctive string literals
    for phrase, score in _extract_string_literals(source):
        if phrase not in seen:
            scored_candidates.append((f'"{phrase}"', score))
            seen.add(phrase)

    # Sort candidates by score descending
    scored_candidates.sort(key=lambda x: x[1], reverse=True)

    # Select top 2 to 4 tokens with score >= 3.0
    selected = [token for token, score in scored_candidates if score >= 3.0]
    if len(selected) < 1:
        # No identifiable unique strings or custom names -> graceful fallback
        return []

    return selected[:max_tokens]


def map_language_for_github(lang: str) -> str:
    """Map CodeGuard supported language code to GitHub Search language filter."""
    mapping = {
        "c": "C",
        "cpp": "C++",
        "c++": "C++",
        "python": "Python",
        "py": "Python",
        "java": "Java",
    }
    return mapping.get(lang.lower().strip(), "C")
