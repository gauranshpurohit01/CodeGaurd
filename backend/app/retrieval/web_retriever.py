"""GitHub REST Code Search API candidate retrieval service for CodeGuard.

Queries the GitHub Code Search API with high-entropy signatures, decodes
candidate source files directly into memory, and caches results to conserve API quotas.
"""

from __future__ import annotations
import base64
import hashlib
import json
import os
from dataclasses import dataclass, asdict
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import httpx
from sqlalchemy.orm import Session

from app.retrieval.signature_extractor import map_language_for_github


GITHUB_SEARCH_URL = "https://api.github.com/search/code"
DEFAULT_TIMEOUT_SEC = 4.0
CACHE_TTL_HOURS = 24


@dataclass
class WebCandidate:
    source_url: str
    repository: str
    file_name: str
    raw_content: str
    language: str


# In-memory LRU cache fallback: query_hash -> (expiry_timestamp, List[WebCandidate])
_MEMORY_CACHE: Dict[str, Tuple[float, List[WebCandidate]]] = {}


def _load_env_github_token() -> Optional[str]:
    """Read GITHUB_TOKEN from environment or .env file."""
    token = os.getenv("GITHUB_TOKEN")
    if token:
        return token.strip()

    # Search common .env locations
    candidates = [
        Path(".env"),
        Path("../.env"),
        Path(__file__).resolve().parent.parent.parent / ".env",
        Path(__file__).resolve().parent.parent.parent.parent / ".env",
    ]
    for env_path in candidates:
        if env_path.exists():
            try:
                for line in env_path.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        if k.strip() == "GITHUB_TOKEN":
                            tok = v.strip().strip("'\"")
                            if tok:
                                os.environ["GITHUB_TOKEN"] = tok
                                return tok
            except Exception:
                pass
    return None


def compute_query_hash(signatures: List[str], language: str) -> str:
    """Compute a deterministic hash for signatures and language."""
    normalized = " ".join(sorted(signatures)) + f"::{language.lower().strip()}"
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


class GitHubWebRetriever:
    """Client for retrieving open-source candidate files via GitHub Code Search API."""

    def __init__(self, token: Optional[str] = None, timeout_sec: float = DEFAULT_TIMEOUT_SEC) -> None:
        self.token = token or _load_env_github_token()
        self.timeout_sec = timeout_sec

    def _get_headers(self, raw: bool = False) -> Dict[str, str]:
        headers = {
            "User-Agent": "CodeGuard-Plagiarism-Engine/1.0",
        }
        if raw:
            headers["Accept"] = "application/vnd.github.v3.raw"
        else:
            headers["Accept"] = "application/vnd.github+json"

        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def _get_from_cache(self, query_hash: str, db: Optional[Session] = None) -> Optional[List[WebCandidate]]:
        now = datetime.now(timezone.utc).timestamp()
        # 1. Check in-memory cache first
        if query_hash in _MEMORY_CACHE:
            expiry, candidates = _MEMORY_CACHE[query_hash]
            if now < expiry:
                return candidates

        # 2. Check SQLite database cache if session provided
        if db:
            try:
                from app.db.models import WebCandidateCache
                row = db.query(WebCandidateCache).filter(WebCandidateCache.query_hash == query_hash).first()
                if row and row.created_at:
                    created_ts = row.created_at.replace(tzinfo=timezone.utc).timestamp()
                    if now - created_ts < CACHE_TTL_HOURS * 3600:
                        candidates = [
                            WebCandidate(
                                source_url=c["source_url"],
                                repository=c["repository"],
                                file_name=c["file_name"],
                                raw_content=c["raw_content"],
                                language=c["language"],
                            )
                            for c in row.results_json
                        ]
                        _MEMORY_CACHE[query_hash] = (now + 3600, candidates)
                        return candidates
            except Exception:
                pass

        return None

    def _save_to_cache(
        self, query_hash: str, query_str: str, language: str, candidates: List[WebCandidate], db: Optional[Session] = None
    ) -> None:
        now = datetime.now(timezone.utc).timestamp()
        _MEMORY_CACHE[query_hash] = (now + 3600, candidates)

        if db:
            try:
                from app.db.models import WebCandidateCache
                serialized = [asdict(c) for c in candidates]
                existing = db.query(WebCandidateCache).filter(WebCandidateCache.query_hash == query_hash).first()
                if existing:
                    existing.results_json = serialized
                    existing.created_at = datetime.now(timezone.utc)
                else:
                    new_cache = WebCandidateCache(
                        query_hash=query_hash,
                        search_query=query_str,
                        language=language,
                        results_json=serialized,
                    )
                    db.add(new_cache)
                db.commit()
            except Exception:
                db.rollback()

    def _fetch_file_content(self, client: httpx.Client, item: dict, language: str) -> Optional[WebCandidate]:
        """Fetch and decode the raw content of a candidate file into memory."""
        source_url = item.get("html_url", "")
        repo_name = item.get("repository", {}).get("full_name", "unknown/repo")
        file_name = item.get("name", "source_file")
        api_url = item.get("url")

        content = ""
        # 1. Try contents API with raw header
        if api_url:
            try:
                resp = client.get(api_url, headers=self._get_headers(raw=True), timeout=self.timeout_sec)
                if resp.status_code == 200:
                    content = resp.text
            except Exception:
                pass

        # 2. If contents API returned JSON with base64
        if not content and api_url:
            try:
                resp = client.get(api_url, headers=self._get_headers(raw=False), timeout=self.timeout_sec)
                if resp.status_code == 200:
                    data = resp.json()
                    if "content" in data and data.get("encoding") == "base64":
                        content = base64.b64decode(data["content"]).decode("utf-8", errors="replace")
            except Exception:
                pass

        if content and len(content.strip()) > 20:
            # Cap memory at 100 KB
            if len(content) > 100 * 1024:
                content = content[: 100 * 1024]
            return WebCandidate(
                source_url=source_url,
                repository=repo_name,
                file_name=file_name,
                raw_content=content,
                language=language,
            )
        return None

    def retrieve(
        self,
        signatures: List[str],
        language: str,
        max_candidates: int = 5,
        db: Optional[Session] = None,
    ) -> Tuple[List[WebCandidate], Optional[str]]:
        """Search GitHub for candidate files matching high-entropy signatures.

        Returns (candidates, status_message).
        """
        if not signatures:
            return [], "No distinctive search signatures found."

        query_hash = compute_query_hash(signatures, language)
        cached = self._get_from_cache(query_hash, db=db)
        if cached is not None:
            return cached, f"Retrieved {len(cached)} candidate(s) from local cache."

        # Construct GitHub search query:
        # Combine top 2 high-entropy signatures with language qualifier
        gh_lang = map_language_for_github(language)
        # Wrap signatures with quotes if they contain spaces
        formatted_sigs = [s if (" " not in s or s.startswith('"')) else f'"{s}"' for s in signatures[:2]]
        query_str = f"{' '.join(formatted_sigs)} language:{gh_lang}"

        candidates: List[WebCandidate] = []
        status_msg: Optional[str] = None

        try:
            with httpx.Client(timeout=self.timeout_sec, follow_redirects=True) as client:
                resp = client.get(
                    GITHUB_SEARCH_URL,
                    params={"q": query_str, "per_page": min(max_candidates, 5)},
                    headers=self._get_headers(raw=False),
                )

                if resp.status_code == 403 or resp.status_code == 429:
                    msg = "GitHub API rate limit exceeded. Set GITHUB_TOKEN in .env for higher rate limits."
                    return [], msg

                if resp.status_code != 200:
                    return [], f"GitHub Code Search API returned HTTP {resp.status_code}."

                search_data = resp.json()
                items = search_data.get("items", [])
                if not items:
                    # Save empty cache so we don't repeatedly query the same negative result
                    self._save_to_cache(query_hash, query_str, language, [], db=db)
                    return [], f"No public GitHub repositories matched query: {query_str}"

                for item in items[:max_candidates]:
                    cand = self._fetch_file_content(client, item, language)
                    if cand:
                        candidates.append(cand)

            self._save_to_cache(query_hash, query_str, language, candidates, db=db)
            status_msg = f"Retrieved {len(candidates)} live candidate file(s) from GitHub."

        except httpx.TimeoutException:
            status_msg = f"GitHub API request timed out after {self.timeout_sec}s."
        except Exception as e:
            status_msg = f"Web retrieval error: {str(e)}"

        return candidates, status_msg
