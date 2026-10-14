"""Pydantic schemas for CodeGuard API endpoints."""

from __future__ import annotations
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union
from pydantic import BaseModel, Field


class ConvertRequest(BaseModel):
    language: str = Field(..., json_schema_extra={"example": "python"})
    source: str = Field(..., json_schema_extra={"example": "def fact(n: int) -> int:\n    res = 1\n    for i in range(1, n+1):\n        res = res * i\n    return res"})


class ConvertResponse(BaseModel):
    c_source: str
    diagnostics: List[str] = []
    success: bool = True


class RunRequest(BaseModel):
    language: str = Field(..., json_schema_extra={"example": "c"})
    source: str
    stdin: Optional[str] = ""
    tests: Optional[List[Tuple[str, str]]] = None


class TestCaseResultSchema(BaseModel):
    input: str
    expected: str
    actual: str
    passed: bool
    time_ms: float


class RunResponse(BaseModel):
    compile_ok: bool
    compiler_messages: str
    stdout: str
    stderr: str
    exit_code: int
    time_ms: float
    memory_kb: int
    timed_out: bool
    killed_reason: Optional[str] = None
    converted_c_source: Optional[str] = None
    test_results: List[TestCaseResultSchema] = []


class MatchedSubtreeSchema(BaseModel):
    kind: str
    size: int
    line_a: int
    line_b: int
    hash_val: int


class MatchReport(BaseModel):
    submission_id: Optional[int] = None
    title: Optional[str] = None
    language: Optional[str] = None
    token_similarity: float
    token_containment_a: float
    token_containment_b: float
    logic_similarity: float
    overall_similarity: float
    verdict: str
    matched_ranges_a: List[Tuple[int, int]] = []
    matched_ranges_b: List[Tuple[int, int]] = []
    matched_subtrees: List[MatchedSubtreeSchema] = []
    target_source: Optional[str] = None


class PlagiarismCheckRequest(BaseModel):
    language: str
    source: str
    compare_with: Union[str, List[int]] = "database"


class PlagiarismCheckResponse(BaseModel):
    query_language: str
    matches: List[MatchReport]


class DirectCompareRequest(BaseModel):
    source_a: str
    language_a: str
    source_b: str
    language_b: str


class SubmissionCreateRequest(BaseModel):
    title: str = "Untitled Submission"
    language: str
    source: str


class SubmissionResponse(BaseModel):
    id: int
    title: str
    language: str
    original_source: str
    generated_c_source: str
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class TokenView(BaseModel):
    kind: str
    value: str
    raw: str
    line: int
    col: int


class ASTViewResponse(BaseModel):
    tokens: List[TokenView]
    raw_ast: Dict[str, Any]
    canonical_ast: Dict[str, Any]
    generated_c: str
