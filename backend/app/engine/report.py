"""Plagiarism reporting and scoring engine for CodeGuard.

Combines Token-level Winnowing and AST-level logic similarity into an actionable,
evidence-based report with matched regions, subtree matches, and configurable verdicts.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional, Tuple
from app.engine.lexer import tokenize
from app.engine.winnowing import winnow_tokens, compare_fingerprints, WinnowingReport
from app.engine.c_parser import parse_c, ParseResult
from app.engine.ast_normalize import normalize_ast
from app.engine.ast_similarity import compute_ast_similarity, ASTSimilarityReport, MatchedSubtree
from app.engine.ast_nodes import Node


DEFAULT_TOKEN_WEIGHT: float = 0.4
DEFAULT_LOGIC_WEIGHT: float = 0.6

# Verdict thresholds
SUSPICIOUS_THRESHOLD: float = 0.50
LIKELY_COPIED_THRESHOLD: float = 0.75


@dataclass
class PlagiarismReport:
    token_similarity: float           # Winnowing Jaccard score (0.0 - 1.0)
    token_containment_a: float        # Containment of A in B
    token_containment_b: float        # Containment of B in A
    logic_similarity: float           # AST alignment & Merkle subtree similarity (0.0 - 1.0)
    ast_alignment_score: float        # Tree alignment DP score
    ast_coverage_a: float             # AST subtree coverage in A
    ast_coverage_b: float             # AST subtree coverage in B
    overall_similarity: float         # Weighted overall score
    verdict: str                      # "low", "suspicious", or "likely copied"
    matched_token_ranges_a: List[Tuple[int, int]] = field(default_factory=list)
    matched_token_ranges_b: List[Tuple[int, int]] = field(default_factory=list)
    matched_subtrees: List[MatchedSubtree] = field(default_factory=list)
    parse_errors_a: List[str] = field(default_factory=list)
    parse_errors_b: List[str] = field(default_factory=list)


def calculate_verdict(overall_score: float, token_score: float, logic_score: float) -> str:
    """Determine plagiarism verdict based on multi-level evidence."""
    if overall_score >= LIKELY_COPIED_THRESHOLD or logic_score >= 0.85 or token_score >= 0.85:
        return "likely copied"
    elif overall_score >= SUSPICIOUS_THRESHOLD or logic_score >= 0.60 or token_score >= 0.60:
        return "suspicious"
    return "low"


def check_plagiarism_c(
    source_a: str,
    source_b: str,
    token_weight: float = DEFAULT_TOKEN_WEIGHT,
    logic_weight: float = DEFAULT_LOGIC_WEIGHT,
) -> PlagiarismReport:
    """Run full two-level plagiarism check on two C/C++ source code submissions."""
    # 1. Token Level: Lexing and Winnowing
    tokens_a = tokenize(source_a)
    tokens_b = tokenize(source_b)

    fps_a = winnow_tokens(tokens_a)
    fps_b = winnow_tokens(tokens_b)

    winnow_rep: WinnowingReport = compare_fingerprints(fps_a, fps_b)
    token_sim = winnow_rep.jaccard

    # 2. Logic Level: Parsing, Canonicalization, and AST Similarity
    parse_a: ParseResult = parse_c(source_a)
    parse_b: ParseResult = parse_c(source_b)

    norm_ast_a: Node = normalize_ast(parse_a.ast)
    norm_ast_b: Node = normalize_ast(parse_b.ast)

    ast_sim: ASTSimilarityReport = compute_ast_similarity(norm_ast_a, norm_ast_b)
    logic_sim = ast_sim.overall_logic_similarity

    # 3. Overall Weighted Score
    overall = (token_weight * token_sim) + (logic_weight * logic_sim)
    verdict = calculate_verdict(overall, token_sim, logic_sim)

    return PlagiarismReport(
        token_similarity=round(token_sim, 4),
        token_containment_a=round(winnow_rep.containment_a_in_b, 4),
        token_containment_b=round(winnow_rep.containment_b_in_a, 4),
        logic_similarity=round(logic_sim, 4),
        ast_alignment_score=round(ast_sim.alignment_score, 4),
        ast_coverage_a=round(ast_sim.coverage_a, 4),
        ast_coverage_b=round(ast_sim.coverage_b, 4),
        overall_similarity=round(overall, 4),
        verdict=verdict,
        matched_token_ranges_a=winnow_rep.matched_ranges_a,
        matched_token_ranges_b=winnow_rep.matched_ranges_b,
        matched_subtrees=ast_sim.matched_subtrees,
        parse_errors_a=parse_a.errors,
        parse_errors_b=parse_b.errors,
    )
