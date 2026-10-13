"""Token fingerprinting using the Winnowing local-minimum algorithm.

Implements a rolling polynomial hash over normalized token k-grams using a deterministic,
process-independent FNV-1a hash function.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Set, Tuple
from app.engine.lexer import Token, normalized_token_string


# Algorithm parameters per CodeGuard specification
DEFAULT_K: int = 5
DEFAULT_W: int = 4
BASE: int = 257
MODULUS: int = (1 << 61) - 1  # Mersenne prime 2^61 - 1

# FNV-1a 64-bit constants
FNV_OFFSET_BASIS: int = 14695981039346656037
FNV_PRIME: int = 1099511628211


def fnv1a_hash(text: str) -> int:
    """Stable, deterministic 64-bit hash independent of Python process salting."""
    h = FNV_OFFSET_BASIS
    for b in text.encode("utf-8"):
        h ^= b
        h = (h * FNV_PRIME) & 0xFFFFFFFFFFFFFFFF
    return h


@dataclass(frozen=True)
class Fingerprint:
    hash_val: int
    pos: int            # K-gram start index in normalized token stream
    token_start_idx: int
    token_end_idx: int
    start_line: int
    end_line: int


@dataclass
class WinnowingReport:
    jaccard: float
    containment_a_in_b: float
    containment_b_in_a: float
    matched_fingerprint_count: int
    total_fingerprints_a: int
    total_fingerprints_b: int
    matched_positions: List[Tuple[int, int]]  # (posA, posB)
    matched_ranges_a: List[Tuple[int, int]]   # (start_line, end_line) in A
    matched_ranges_b: List[Tuple[int, int]]   # (start_line, end_line) in B


def compute_kgram_hashes(
    token_hashes: List[int],
    k: int = DEFAULT_K,
    base: int = BASE,
    modulus: int = MODULUS
) -> List[int]:
    """Compute rolling polynomial hashes for all k-grams in token_hashes."""
    n = len(token_hashes)
    if n < k:
        if n == 0:
            return []
        # Fallback for short programs: single hash of all tokens
        acc = 0
        for th in token_hashes:
            acc = (acc * base + (th % modulus)) % modulus
        return [acc]

    # Precompute base^(k-1) % modulus
    base_k_minus_1 = pow(base, k - 1, modulus)

    # First k-gram
    current_hash = 0
    for i in range(k):
        current_hash = (current_hash * base + (token_hashes[i] % modulus)) % modulus

    hashes = [current_hash]

    # Rolling computation for remaining k-grams
    for i in range(1, n - k + 1):
        prev_token_contrib = ((token_hashes[i - 1] % modulus) * base_k_minus_1) % modulus
        current_hash = (current_hash - prev_token_contrib) % modulus
        current_hash = (current_hash * base + (token_hashes[i + k - 1] % modulus)) % modulus
        hashes.append(current_hash)

    return hashes


def winnow_tokens(
    tokens: List[Token],
    k: int = DEFAULT_K,
    w: int = DEFAULT_W
) -> List[Fingerprint]:
    """Extract winnowed fingerprints from a list of tokens."""
    # Filter tokens (skip EOF and Preprocessor)
    valid_tokens = [t for t in tokens if t.kind not in ("EOF", "PREPROCESSOR")]
    if not valid_tokens:
        return []

    token_hashes = [fnv1a_hash(t.value) for t in valid_tokens]
    kgram_hashes = compute_kgram_hashes(token_hashes, k=k)

    if not kgram_hashes:
        return []

    fingerprints: List[Fingerprint] = []
    last_added_pos: int = -1

    # If kgram_hashes length is smaller than window w, select minimum of all
    if len(kgram_hashes) < w:
        min_idx = 0
        min_val = kgram_hashes[0]
        for i in range(1, len(kgram_hashes)):
            if kgram_hashes[i] <= min_val:  # Rightmost on ties
                min_val = kgram_hashes[i]
                min_idx = i
        end_idx = min(min_idx + k - 1, len(valid_tokens) - 1)
        return [Fingerprint(
            hash_val=min_val,
            pos=min_idx,
            token_start_idx=min_idx,
            token_end_idx=end_idx,
            start_line=valid_tokens[min_idx].line,
            end_line=valid_tokens[end_idx].line,
        )]

    # Sliding window of size w
    for i in range(len(kgram_hashes) - w + 1):
        window = kgram_hashes[i : i + w]
        # Find minimum in window, rightmost on ties
        min_val = window[0]
        min_offset = 0
        for j in range(1, w):
            if window[j] <= min_val:
                min_val = window[j]
                min_offset = j

        abs_pos = i + min_offset
        if abs_pos != last_added_pos:
            end_idx = min(abs_pos + k - 1, len(valid_tokens) - 1)
            fingerprints.append(Fingerprint(
                hash_val=min_val,
                pos=abs_pos,
                token_start_idx=abs_pos,
                token_end_idx=end_idx,
                start_line=valid_tokens[abs_pos].line,
                end_line=valid_tokens[end_idx].line,
            ))
            last_added_pos = abs_pos

    return fingerprints


def compare_fingerprints(
    fps_a: List[Fingerprint],
    fps_b: List[Fingerprint]
) -> WinnowingReport:
    """Compare two sets of fingerprints and generate similarity metrics."""
    if not fps_a and not fps_b:
        return WinnowingReport(
            jaccard=1.0,
            containment_a_in_b=1.0,
            containment_b_in_a=1.0,
            matched_fingerprint_count=0,
            total_fingerprints_a=0,
            total_fingerprints_b=0,
            matched_positions=[],
            matched_ranges_a=[],
            matched_ranges_b=[],
        )

    if not fps_a or not fps_b:
        return WinnowingReport(
            jaccard=0.0,
            containment_a_in_b=0.0,
            containment_b_in_a=0.0,
            matched_fingerprint_count=0,
            total_fingerprints_a=len(fps_a),
            total_fingerprints_b=len(fps_b),
            matched_positions=[],
            matched_ranges_a=[],
            matched_ranges_b=[],
        )

    hashes_a = {fp.hash_val for fp in fps_a}
    hashes_b = {fp.hash_val for fp in fps_b}

    common_hashes = hashes_a.intersection(hashes_b)
    union_hashes = hashes_a.union(hashes_b)

    jaccard = len(common_hashes) / len(union_hashes) if union_hashes else 0.0
    containment_a = len(common_hashes) / len(hashes_a) if hashes_a else 0.0
    containment_b = len(common_hashes) / len(hashes_b) if hashes_b else 0.0

    # Build match positions and ranges
    hash_to_fps_b: Dict[int, List[Fingerprint]] = {}
    for fp in fps_b:
        hash_to_fps_b.setdefault(fp.hash_val, []).append(fp)

    matched_positions: List[Tuple[int, int]] = []
    matched_ranges_a_set: Set[Tuple[int, int]] = set()
    matched_ranges_b_set: Set[Tuple[int, int]] = set()

    for fp_a in fps_a:
        if fp_a.hash_val in hash_to_fps_b:
            matched_ranges_a_set.add((fp_a.start_line, fp_a.end_line))
            for fp_b in hash_to_fps_b[fp_a.hash_val]:
                matched_positions.append((fp_a.pos, fp_b.pos))
                matched_ranges_b_set.add((fp_b.start_line, fp_b.end_line))

    # Merge overlapping line ranges
    def merge_ranges(ranges: Set[Tuple[int, int]]) -> List[Tuple[int, int]]:
        if not ranges:
            return []
        sorted_r = sorted(ranges, key=lambda r: (r[0], r[1]))
        merged: List[Tuple[int, int]] = [sorted_r[0]]
        for cur_start, cur_end in sorted_r[1:]:
            last_start, last_end = merged[-1]
            if cur_start <= last_end + 1:
                merged[-1] = (last_start, max(last_end, cur_end))
            else:
                merged.append((cur_start, cur_end))
        return merged

    return WinnowingReport(
        jaccard=jaccard,
        containment_a_in_b=containment_a,
        containment_b_in_a=containment_b,
        matched_fingerprint_count=len(common_hashes),
        total_fingerprints_a=len(hashes_a),
        total_fingerprints_b=len(hashes_b),
        matched_positions=matched_positions,
        matched_ranges_a=merge_ranges(matched_ranges_a_set),
        matched_ranges_b=merge_ranges(matched_ranges_b_set),
    )
