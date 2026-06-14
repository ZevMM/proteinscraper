"""Content-addressed file cache for fetched payloads.

Keeps scraping polite and cheap: an unchanged page is served from disk, so we
neither re-hit the source nor re-run LLM extraction on identical content.
"""

from __future__ import annotations

import hashlib
import time
from pathlib import Path


class FileCache:
    def __init__(self, root: str | Path, ttl_seconds: float = 24 * 3600) -> None:
        self.root = Path(root)
        self.ttl_seconds = ttl_seconds
        self.root.mkdir(parents=True, exist_ok=True)

    def _path_for(self, key: str) -> Path:
        digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
        # Shard into subdirs to avoid huge flat directories.
        return self.root / digest[:2] / f"{digest}.txt"

    def get(self, key: str) -> str | None:
        path = self._path_for(key)
        if not path.exists():
            return None
        if self.ttl_seconds >= 0 and (time.time() - path.stat().st_mtime) > self.ttl_seconds:
            return None
        return path.read_text(encoding="utf-8")

    def set(self, key: str, value: str) -> None:
        path = self._path_for(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(value, encoding="utf-8")


def content_hash(text: str) -> str:
    """Stable hash of page content, used to skip re-extraction of unchanged pages."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
