"""Plagiarism runner pipeline for live web/GitHub candidates.

Coordinates high-entropy signature extraction, GitHub code retrieval,
caching, and two-tier (token Winnowing & AST alignment) plagiarism analysis.
"""

from __future__ import annotations
import asyncio
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from sqlalchemy.orm import Session

from app.frontends.converter import convert_to_c
from app.engine.report import check_plagiarism_c
from app.retrieval.signature_extractor import extract_signatures
from app.retrieval.web_retriever import GitHubWebRetriever, WebCandidate


WEB_SIMILARITY_THRESHOLD: float = 0.35  # Match threshold (35%)


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
    # 1. Extract high-entropy signatures
    signatures = extract_signatures(language, source)
    if not signatures:
        return WebPlagiarismReport(
            checked=False,
            search_queries_used=[],
            matches=[],
            status_message="No high-entropy code signatures identified for web retrieval; local database search only.",
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

            # Only retain matches exceeding threshold
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
                        target_source=cand.raw_content,
                    )
                )
        except Exception:
            continue

    # Sort matches by composite score descending
    matches.sort(key=lambda m: m.composite_score_num, reverse=True)

    summary = (
        f"Retrieved {len(candidates)} GitHub candidate(s); "
        f"found {len(matches)} match(es) exceeding {int(threshold * 100)}% threshold."
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
