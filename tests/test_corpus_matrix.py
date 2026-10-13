"""Corpus Similarity Matrix Runner and Validator for CodeGuard.

Evaluates all 8 problem families (32 source files) and prints the comprehensive similarity matrix,
validating the fundamental CodeGuard ordering invariant:
    Identical >= Renamed >= Restructured > Different
"""

import sys
from pathlib import Path

# Ensure backend directory is in sys.path
backend_path = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(backend_path))

import pytest
from app.engine.report import check_plagiarism_c


CORPUS_DIR = Path(__file__).resolve().parent / "corpus"
FAMILIES = [
    "factorial",
    "fibonacci",
    "gcd",
    "prime_check",
    "bubble_sort",
    "binary_search",
    "array_sum",
    "string_reverse",
]


def run_matrix_and_verify():
    print("\n" + "=" * 90)
    print("CODEGUARD CORPUS SIMILARITY MATRIX (Phase 1 Acceptance)")
    print("=" * 90)
    print(f"{'Family':<16} | {'Identical':<14} | {'Renamed':<14} | {'Restructured':<14} | {'Different':<14} | {'Status':<8}")
    print("-" * 90)

    all_passed = True
    results = []

    for family in FAMILIES:
        fam_dir = CORPUS_DIR / family
        orig = (fam_dir / "original.c").read_text(encoding="utf-8")
        ren = (fam_dir / "renamed.c").read_text(encoding="utf-8")
        rest = (fam_dir / "restructured.c").read_text(encoding="utf-8")
        diff = (fam_dir / "different.c").read_text(encoding="utf-8")

        rep_ident = check_plagiarism_c(orig, orig)
        rep_ren = check_plagiarism_c(orig, ren)
        rep_rest = check_plagiarism_c(orig, rest)
        rep_diff = check_plagiarism_c(orig, diff)

        score_ident = rep_ident.overall_similarity
        score_ren = rep_ren.overall_similarity
        score_rest = rep_rest.overall_similarity
        score_diff = rep_diff.overall_similarity

        logic_ident = rep_ident.logic_similarity
        logic_ren = rep_ren.logic_similarity
        logic_rest = rep_rest.logic_similarity
        logic_diff = rep_diff.logic_similarity

        # Invariant check: identical >= renamed >= restructured > different
        # 1. Overall scores must decrease monotonically: ident >= ren >= rest > diff
        # 2. Logic score for restructured must be strictly higher than different
        passed = (
            score_ident >= score_ren - 0.01
            and score_ren >= score_rest - 0.01
            and score_rest > score_diff
            and logic_rest > logic_diff
        )

        status_str = "PASS" if passed else "FAIL"
        if not passed:
            all_passed = False

        results.append({
            "family": family,
            "ident": score_ident,
            "ren": score_ren,
            "rest": score_rest,
            "diff": score_diff,
            "logic_rest": logic_rest,
            "logic_diff": logic_diff,
            "passed": passed,
        })

        print(
            f"{family:<16} | "
            f"O: {score_ident:.2f} (L:{logic_ident:.2f}) | "
            f"O: {score_ren:.2f} (L:{logic_ren:.2f}) | "
            f"O: {score_rest:.2f} (L:{logic_rest:.2f}) | "
            f"O: {score_diff:.2f} (L:{logic_diff:.2f}) | "
            f"{status_str:<8}"
        )

    print("=" * 90)
    print("Legend: O = Overall Score, L = Logic (AST) Score\n")

    assert all_passed, "Corpus invariant (Identical >= Renamed >= Restructured > Different) failed for one or more families!"
    print("[SUCCESS] All 8 problem families strictly satisfy the ordering invariant!")
    return results


def test_corpus_similarity_matrix():
    run_matrix_and_verify()


if __name__ == "__main__":
    run_matrix_and_verify()
