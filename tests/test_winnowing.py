"""Unit tests for Winnowing token fingerprinting."""

from app.engine.lexer import tokenize
from app.engine.winnowing import (
    winnow_tokens,
    compare_fingerprints,
    fnv1a_hash,
)


def test_hash_determinism():
    text = "int ID = NUM ;"
    h1 = fnv1a_hash(text)
    h2 = fnv1a_hash(text)
    assert h1 == h2
    assert isinstance(h1, int)


def test_winnowing_identical_code():
    code = "int calc(int a, int b) { return a + b * 2; }"
    tokens1 = tokenize(code)
    tokens2 = tokenize(code)
    fps1 = winnow_tokens(tokens1)
    fps2 = winnow_tokens(tokens2)
    rep = compare_fingerprints(fps1, fps2)
    assert rep.jaccard == 1.0
    assert rep.containment_a_in_b == 1.0
    assert rep.containment_b_in_a == 1.0
    assert rep.matched_fingerprint_count == len(fps1)


def test_winnowing_renamed_code():
    code1 = "int sum(int x, int y) { int res = x + y; return res; }"
    code2 = "int total(int first, int second) { int ans = first + second; return ans; }"
    fps1 = winnow_tokens(tokenize(code1))
    fps2 = winnow_tokens(tokenize(code2))
    rep = compare_fingerprints(fps1, fps2)
    # Identifiers normalize to 'ID', so normalized streams are identical!
    assert rep.jaccard == 1.0


def test_winnowing_reformatted_whitespace():
    code1 = "int f(int x){return x*x;}"
    code2 = "int    f (  int  x )  \n{\n    return   x * x ;\n}"
    fps1 = winnow_tokens(tokenize(code1))
    fps2 = winnow_tokens(tokenize(code2))
    rep = compare_fingerprints(fps1, fps2)
    assert rep.jaccard == 1.0


def test_winnowing_different_code():
    code1 = "int gcd(int a, int b) { while (b != 0) { int t = b; b = a % b; a = t; } return a; }"
    code2 = 'void print_msg() { printf("Hello World\\n"); }'
    fps1 = winnow_tokens(tokenize(code1))
    fps2 = winnow_tokens(tokenize(code2))
    rep = compare_fingerprints(fps1, fps2)
    assert rep.jaccard < 0.2


def test_winnowing_match_coordinates():
    code1 = "int f(int a, int b) { int c = a + b; return c; }"
    code2 = "int f(int a, int b) { int c = a + b; return c; }"
    fps1 = winnow_tokens(tokenize(code1))
    fps2 = winnow_tokens(tokenize(code2))
    rep = compare_fingerprints(fps1, fps2)
    assert len(rep.matched_ranges_a) > 0
    assert len(rep.matched_ranges_b) > 0
    assert len(rep.matched_positions) > 0
