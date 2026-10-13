"""FastAPI routes for CodeGuard compiler and plagiarism platform."""

from __future__ import annotations
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.repository import SubmissionRepository
from app.api.schemas import (
    ConvertRequest,
    ConvertResponse,
    RunRequest,
    RunResponse,
    PlagiarismCheckRequest,
    PlagiarismCheckResponse,
    DirectCompareRequest,
    MatchReport,
    MatchedSubtreeSchema,
    SubmissionCreateRequest,
    SubmissionResponse,
    ASTViewResponse,
    TokenView,
)
from app.frontends.converter import convert_to_c
from app.execution.sandbox import Sandbox
from app.engine.lexer import tokenize
from app.engine.winnowing import winnow_tokens, compare_fingerprints
from app.engine.c_parser import parse_c
from app.engine.ast_normalize import normalize_ast
from app.engine.ast_similarity import compute_ast_similarity
from app.engine.report import check_plagiarism_c, calculate_verdict


router = APIRouter(prefix="/api", tags=["CodeGuard API"])
sandbox_instance = Sandbox()


@router.post("/convert", response_model=ConvertResponse)
def convert_code(req: ConvertRequest):
    """Convert Python or Java source code into compilable C."""
    res = convert_to_c(req.language, req.source)
    return ConvertResponse(
        c_source=res.c_source,
        diagnostics=res.diagnostics,
        success=res.success,
    )


@router.post("/run", response_model=RunResponse)
def run_code(req: RunRequest):
    """Compile and execute code inside the sandbox with strict resource limits."""
    res = sandbox_instance.run(
        language=req.language,
        source=req.source,
        stdin_data=req.stdin or "",
        test_cases=req.tests,
    )
    return RunResponse(
        compile_ok=res.compile_ok,
        compiler_messages=res.compiler_messages,
        stdout=res.stdout,
        stderr=res.stderr,
        exit_code=res.exit_code,
        time_ms=res.time_ms,
        memory_kb=res.memory_kb,
        timed_out=res.timed_out,
        killed_reason=res.killed_reason,
        converted_c_source=res.converted_c_source,
        test_results=[
            {
                "input": tr.input,
                "expected": tr.expected,
                "actual": tr.actual,
                "passed": tr.passed,
                "time_ms": tr.time_ms,
            }
            for tr in res.test_results
        ],
    )


@router.post("/plagiarism/check", response_model=PlagiarismCheckResponse)
def check_plagiarism(req: PlagiarismCheckRequest, db: Session = Depends(get_db)):
    """Check code against stored submissions at both token level and AST logic level."""
    repo = SubmissionRepository(db)

    # 1. Convert query to C
    conv_query = convert_to_c(req.language, req.source)
    c_query = conv_query.c_source if conv_query.success else req.source

    # 2. Extract query token fingerprints for inverted index
    tokens_query = tokenize(c_query)
    fps_query = winnow_tokens(tokens_query)
    query_hashes = [str(fp.hash_val) for fp in fps_query]

    # 3. Determine candidates to compare with
    if isinstance(req.compare_with, list) and req.compare_with:
        candidates = [repo.get_submission(sid) for sid in req.compare_with]
        candidates = [c for c in candidates if c is not None]
    else:
        # Check against database: shortlist using inverted index first
        candidate_ids = repo.find_candidate_ids(query_hashes, min_shared=1)
        if not candidate_ids:
            # Fall back to all if inverted index finds none or small corpus
            candidates = repo.get_all_submissions()[:50]
        else:
            candidates = [repo.get_submission(cid) for cid in candidate_ids if repo.get_submission(cid) is not None]

    matches: List[MatchReport] = []

    for cand in candidates:
        rep = check_plagiarism_c(c_query, cand.generated_c_source)
        matches.append(MatchReport(
            submission_id=cand.id,
            title=cand.title,
            language=cand.language,
            token_similarity=rep.token_similarity,
            token_containment_a=rep.token_containment_a,
            token_containment_b=rep.token_containment_b,
            logic_similarity=rep.logic_similarity,
            overall_similarity=rep.overall_similarity,
            verdict=rep.verdict,
            matched_ranges_a=rep.matched_token_ranges_a,
            matched_ranges_b=rep.matched_token_ranges_b,
            matched_subtrees=[
                MatchedSubtreeSchema(
                    kind=st.kind,
                    size=st.size,
                    line_a=st.line_a,
                    line_b=st.line_b,
                    hash_val=st.hash_val,
                )
                for st in rep.matched_subtrees
            ],
        ))

    # Sort matches by overall similarity descending
    matches.sort(key=lambda m: m.overall_similarity, reverse=True)
    return PlagiarismCheckResponse(query_language=req.language, matches=matches)


@router.post("/compare", response_model=MatchReport)
def compare_direct(req: DirectCompareRequest):
    """Direct two-source plagiarism comparison across languages."""
    conv_a = convert_to_c(req.language_a, req.source_a)
    conv_b = convert_to_c(req.language_b, req.source_b)

    c_a = conv_a.c_source if conv_a.success else req.source_a
    c_b = conv_b.c_source if conv_b.success else req.source_b

    rep = check_plagiarism_c(c_a, c_b)
    return MatchReport(
        token_similarity=rep.token_similarity,
        token_containment_a=rep.token_containment_a,
        token_containment_b=rep.token_containment_b,
        logic_similarity=rep.logic_similarity,
        overall_similarity=rep.overall_similarity,
        verdict=rep.verdict,
        matched_ranges_a=rep.matched_token_ranges_a,
        matched_ranges_b=rep.matched_token_ranges_b,
        matched_subtrees=[
            MatchedSubtreeSchema(
                kind=st.kind,
                size=st.size,
                line_a=st.line_a,
                line_b=st.line_b,
                hash_val=st.hash_val,
            )
            for st in rep.matched_subtrees
        ],
    )


@router.post("/submissions", response_model=SubmissionResponse)
def create_submission(req: SubmissionCreateRequest, db: Session = Depends(get_db)):
    """Store a code submission into the database and update fingerprint inverted indexes."""
    repo = SubmissionRepository(db)
    sub = repo.create_submission(title=req.title, language=req.language, source=req.source)
    return sub


@router.get("/submissions", response_model=List[SubmissionResponse])
def list_submissions(db: Session = Depends(get_db)):
    """List all stored code submissions."""
    repo = SubmissionRepository(db)
    return repo.get_all_submissions()


@router.get("/submissions/{sub_id}", response_model=SubmissionResponse)
def get_submission_by_id(sub_id: int, db: Session = Depends(get_db)):
    """Get a specific submission by ID."""
    repo = SubmissionRepository(db)
    sub = repo.get_submission(sub_id)
    if not sub:
        raise HTTPException(status_code=404, detail="Submission not found")
    return sub


@router.get("/ast", response_model=ASTViewResponse)
def view_pipeline(language: str, source: str):
    """Pipeline visualizer endpoint: decomposes code into tokens, raw AST, canonical AST, and generated C."""
    conv_res = convert_to_c(language, source)
    c_source = conv_res.c_source if conv_res.success else source

    tokens = tokenize(c_source)
    token_views = [
        TokenView(kind=t.kind, value=t.value, raw=t.raw, line=t.line, col=t.col)
        for t in tokens
    ]

    parse_res = parse_c(c_source)
    raw_ast_dict = parse_res.ast.to_dict()
    canonical_ast = normalize_ast(parse_res.ast)
    canonical_ast_dict = canonical_ast.to_dict()

    return ASTViewResponse(
        tokens=token_views,
        raw_ast=raw_ast_dict,
        canonical_ast=canonical_ast_dict,
        generated_c=c_source,
    )
