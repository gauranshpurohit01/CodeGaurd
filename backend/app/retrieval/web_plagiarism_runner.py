"""Plagiarism runner pipeline for live web/GitHub candidates.

Coordinates high-entropy signature extraction, GitHub code retrieval,
caching, and two-tier (token Winnowing & AST alignment) plagiarism analysis.
"""

from __future__ import annotations
import asyncio
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Any, List, Optional, Tuple

from sqlalchemy.orm import Session

from app.frontends.converter import convert_to_c
from app.engine.report import check_plagiarism_c
from app.retrieval.signature_extractor import extract_signatures
from app.retrieval.web_retriever import GitHubWebRetriever, WebCandidate


WEB_SIMILARITY_THRESHOLD: float = 0.20  # Match threshold (20%)


@dataclass
class WebMatchResult:
    source_url: str
    repository: str
    token_similarity: str       # e.g. "84.2%"
    logic_similarity: str       # e.g. "91.0%"
    composite_score: str        # e.g. "88.3%"
    token_similarity_num: float
    logic_similarity_num: float
    composite_score_num: float
    verdict: str
    matched_ranges_a: List[Tuple[int, int]] = field(default_factory=list)
    matched_ranges_b: List[Tuple[int, int]] = field(default_factory=list)
    matched_subtrees: List[Any] = field(default_factory=list)
    target_source: Optional[str] = None


@dataclass
class WebPlagiarismReport:
    checked: bool
    search_queries_used: List[str]
    matches: List[WebMatchResult] = field(default_factory=list)
    status_message: Optional[str] = None


_EXECUTOR = ThreadPoolExecutor(max_workers=4)


def run_web_plagiarism_pipeline(
    language: str,
    source: str,
    threshold: float = WEB_SIMILARITY_THRESHOLD,
    db: Optional[Session] = None,
    retriever: Optional[GitHubWebRetriever] = None,
) -> WebPlagiarismReport:
    """Run full web candidate retrieval and plagiarism comparison pipeline."""
    # 1. Extract distinctive signatures
    signatures = extract_signatures(language, source)
    if not signatures and source and source.strip():
        # Fallback: extract any identifier tokens from source so any code is checked
        import re
        tokens = [t for t in re.findall(r"\b[A-Za-z_][A-Za-z0-9_]{1,}\b", source) if t.lower() not in {"include", "stdio", "return", "int", "void", "main"}]
        if tokens:
            signatures = tokens[:3]

    if not signatures:
        return WebPlagiarismReport(
            checked=True,
            search_queries_used=[],
            matches=[],
            status_message="No distinctive code signatures found to query on GitHub (code is empty or trivial boilerplate).",
        )

    # 2. Retrieve candidate source files from GitHub
    client = retriever or GitHubWebRetriever()
    candidates, status_msg = client.retrieve(signatures, language, max_candidates=5, db=db)
    if not candidates:
        return WebPlagiarismReport(
            checked=True,
            search_queries_used=signatures,
            matches=[],
            status_message=status_msg or "No matching repositories found on GitHub.",
        )

    # 3. Convert query code to C for comparison
    conv_query = convert_to_c(language, source)
    c_query = conv_query.c_source if conv_query.success else source

    matches: List[WebMatchResult] = []

    # 4. Compare query against each candidate using token & AST engines
    for cand in candidates:
        try:
            conv_cand = convert_to_c(cand.language, cand.raw_content)
            c_cand = conv_cand.c_source if conv_cand.success else cand.raw_content

            rep = check_plagiarism_c(c_query, c_cand)

            token_pct = rep.token_similarity * 100.0
            logic_pct = rep.logic_similarity * 100.0
            overall_pct = rep.overall_similarity * 100.0

            # Retain matches meeting threshold
            subtrees = [
                {
                    "kind": st.kind,
                    "size": st.size,
                    "line_a": st.line_a,
                    "line_b": st.line_b,
                    "hash_val": st.hash_val,
                }
                for st in getattr(rep, "matched_subtrees", [])
            ]

            if rep.overall_similarity >= threshold or rep.token_similarity >= threshold or rep.logic_similarity >= threshold:
                matches.append(
                    WebMatchResult(
                        source_url=cand.source_url,
                        repository=cand.repository,
                        token_similarity=f"{token_pct:.1f}%",
                        logic_similarity=f"{logic_pct:.1f}%",
                        composite_score=f"{overall_pct:.1f}%",
                        token_similarity_num=round(rep.token_similarity, 4),
                        logic_similarity_num=round(rep.logic_similarity, 4),
                        composite_score_num=round(rep.overall_similarity, 4),
                        verdict=rep.verdict,
                        matched_ranges_a=rep.matched_token_ranges_a,
                        matched_ranges_b=rep.matched_token_ranges_b,
                        matched_subtrees=subtrees,
                        target_source=cand.raw_content,
                    )
                )
        except Exception:
            continue

    # If no candidates met threshold, surface top open-source candidate so the user can inspect closest match
    if not matches and candidates:
        best_cand = None
        best_rep = None
        best_score = -1.0
        for cand in candidates:
            try:
                conv_cand = convert_to_c(cand.language, cand.raw_content)
                c_cand = conv_cand.c_source if conv_cand.success else cand.raw_content
                rep = check_plagiarism_c(c_query, c_cand)
                if rep.overall_similarity > best_score:
                    best_score = rep.overall_similarity
                    best_cand = cand
                    best_rep = rep
            except Exception:
                pass
        if best_cand and best_rep:
            matches.append(
                WebMatchResult(
                    source_url=best_cand.source_url,
                    repository=best_cand.repository,
                    token_similarity=f"{best_rep.token_similarity * 100.0:.1f}%",
                    logic_similarity=f"{best_rep.logic_similarity * 100.0:.1f}%",
                    composite_score=f"{best_rep.overall_similarity * 100.0:.1f}%",
                    token_similarity_num=round(best_rep.token_similarity, 4),
                    logic_similarity_num=round(best_rep.logic_similarity, 4),
                    composite_score_num=round(best_rep.overall_similarity, 4),
                    verdict=best_rep.verdict,
                    matched_ranges_a=best_rep.matched_token_ranges_a,
                    matched_ranges_b=best_rep.matched_token_ranges_b,
                    matched_subtrees=[
                        {
                            "kind": st.kind,
                            "size": st.size,
                            "line_a": st.line_a,
                            "line_b": st.line_b,
                            "hash_val": st.hash_val,
                        }
                        for st in getattr(best_rep, "matched_subtrees", [])
                    ],
                    target_source=best_cand.raw_content,
                )
            )

    # Sort matches by composite score descending
    matches.sort(key=lambda m: m.composite_score_num, reverse=True)

    summary = (
        f"Retrieved {len(candidates)} GitHub open-source candidate(s); "
        f"found {len(matches)} match(es) for side-by-side plagiarism inspection."
    )

    return WebPlagiarismReport(
        checked=True,
        search_queries_used=signatures,
        matches=matches,
        status_message=summary,
    )


async def run_web_plagiarism_pipeline_async(
    language: str,
    source: str,
    threshold: float = WEB_SIMILARITY_THRESHOLD,
    db: Optional[Session] = None,
    retriever: Optional[GitHubWebRetriever] = None,
) -> WebPlagiarismReport:
    """Asynchronous wrapper to execute web candidate retrieval without blocking the event loop."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        _EXECUTOR,
        run_web_plagiarism_pipeline,
        language,
        source,
        threshold,
        db,
        retriever,
    )
