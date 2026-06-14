"""Connector interface shared by every source type."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from ..extract.llm import LlmExtractor
from ..http import Fetcher
from ..models import ProductRecord


class Connector(ABC):
    """Pluggable per-source pipeline stage.

    ``discover`` returns lightweight references (raw product payloads or URLs);
    ``extract`` turns one reference into a normalized :class:`ProductRecord`
    (or ``None`` if it should be skipped, e.g. not a protein powder).
    """

    #: matches Source.type in the database
    source_type: str

    def __init__(
        self, source: dict[str, Any], fetcher: Fetcher, llm: LlmExtractor | None = None
    ) -> None:
        self.source = source
        self.fetcher = fetcher
        self.llm = llm
        self.base_url: str = str(source["baseUrl"]).rstrip("/")
        self.config: dict[str, Any] = source.get("config") or {}

    @abstractmethod
    async def discover(self) -> list[Any]:
        """Return references to candidate products."""

    @abstractmethod
    async def extract(self, ref: Any) -> ProductRecord | None:
        """Normalize one reference into a ProductRecord, or None to skip."""
