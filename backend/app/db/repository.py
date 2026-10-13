"""Database repository for submissions and inverted index fast candidate retrieval."""

from __future__ import annotations
from typing import List, Optional, Set
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.db.models import Submission, FingerprintIndex
from app.frontends.converter import convert_to_c
from app.engine.lexer import tokenize
from app.engine.winnowing import winnow_tokens
from app.engine.c_parser import parse_c
from app.engine.ast_normalize import normalize_ast
from app.engine.ast_similarity import ASTSimilarityEngine


class SubmissionRepository:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.ast_engine = ASTSimilarityEngine()

    def create_submission(self, title: str, language: str, source: str) -> Submission:
        # Convert to C if needed
        conv_res = convert_to_c(language, source)
        c_code = conv_res.c_source if conv_res.success else source

        # Extract tokens and fingerprints
        tokens = tokenize(c_code)
        fps = winnow_tokens(tokens)
        token_hashes = [str(fp.hash_val) for fp in fps]

        # Extract canonical AST and subtree hashes
        parse_res = parse_c(c_code)
        norm_ast = normalize_ast(parse_res.ast)
        hashes_dict, sizes_dict, nodes_by_hash = self.ast_engine._compute_subtree_hashes(norm_ast)
        subtree_hashes = [str(h) for h in nodes_by_hash.keys()]

        submission = Submission(
            title=title,
            language=language,
            original_source=source,
            generated_c_source=c_code,
            token_fingerprints=token_hashes,
            subtree_hashes=subtree_hashes,
        )
        self.db.add(submission)
        self.db.commit()
        self.db.refresh(submission)

        # Update inverted index for fast lookup
        index_entries = []
        for h in set(token_hashes):
            index_entries.append(FingerprintIndex(hash_val=h, submission_id=submission.id))
        if index_entries:
            self.db.bulk_save_objects(index_entries)
            self.db.commit()

        return submission

    def get_submission(self, sub_id: int) -> Optional[Submission]:
        return self.db.query(Submission).filter(Submission.id == sub_id).first()

    def get_all_submissions(self) -> List[Submission]:
        return self.db.query(Submission).order_by(Submission.id.desc()).all()

    def find_candidate_ids(self, query_hashes: List[str], min_shared: int = 1) -> Set[int]:
        """Fast inverted index query to find candidate submission IDs sharing fingerprints."""
        if not query_hashes:
            return set()

        rows = (
            self.db.query(FingerprintIndex.submission_id)
            .filter(FingerprintIndex.hash_val.in_(query_hashes))
            .group_by(FingerprintIndex.submission_id)
            .having(func.count(FingerprintIndex.id) >= min_shared)
            .all()
        )
        return {r[0] for r in rows}
