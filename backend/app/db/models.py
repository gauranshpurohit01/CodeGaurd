"""SQLAlchemy database models for CodeGuard submissions and inverted indexes."""

from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, Index
from app.db.database import Base


class Submission(Base):
    __tablename__ = "submissions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    title = Column(String(255), nullable=False, default="Untitled Submission")
    language = Column(String(50), nullable=False)
    original_source = Column(Text, nullable=False)
    generated_c_source = Column(Text, nullable=False)
    token_fingerprints = Column(JSON, nullable=False)  # List of int hashes
    subtree_hashes = Column(JSON, nullable=False)      # List of int Merkle hashes
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class FingerprintIndex(Base):
    __tablename__ = "fingerprint_index"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    hash_val = Column(String(64), nullable=False, index=True)
    submission_id = Column(Integer, nullable=False, index=True)

    __table_args__ = (
        Index("idx_hash_submission", "hash_val", "submission_id"),
    )
