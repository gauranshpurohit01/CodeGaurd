"""Real-Time Web Candidate Retrieval Module for CodeGuard."""

from app.retrieval.signature_extractor import extract_signatures, map_language_for_github
from app.retrieval.web_retriever import GitHubWebRetriever, WebCandidate
from app.retrieval.web_plagiarism_runner import (
    run_web_plagiarism_pipeline,
    run_web_plagiarism_pipeline_async,
    WebMatchResult,
    WebPlagiarismReport,
)

__all__ = [
    "extract_signatures",
    "map_language_for_github",
    "GitHubWebRetriever",
    "WebCandidate",
    "run_web_plagiarism_pipeline",
    "run_web_plagiarism_pipeline_async",
    "WebMatchResult",
    "WebPlagiarismReport",
]
