"""Polite async HTTP client: per-host rate limiting, retries, caching, a real UA."""

from __future__ import annotations

import asyncio
import time
from collections import defaultdict

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from .cache import FileCache
from .config import Settings


class RateLimiter:
    """Simple per-host minimum-interval limiter."""

    def __init__(self, requests_per_second: float) -> None:
        self._min_interval = 1.0 / requests_per_second if requests_per_second > 0 else 0.0
        self._last: dict[str, float] = defaultdict(float)
        self._locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)

    async def wait(self, host: str) -> None:
        if self._min_interval <= 0:
            return
        async with self._locks[host]:
            elapsed = time.monotonic() - self._last[host]
            if elapsed < self._min_interval:
                await asyncio.sleep(self._min_interval - elapsed)
            self._last[host] = time.monotonic()


class Fetcher:
    """Fetches text/JSON over HTTP with caching + rate limiting.

    Use as an async context manager so the underlying connection pool is closed.
    """

    def __init__(self, settings: Settings, *, use_cache: bool = True) -> None:
        self._settings = settings
        self._limiter = RateLimiter(settings.scraper_requests_per_second)
        self._cache = FileCache(settings.scraper_cache_dir) if use_cache else None
        self._client = httpx.AsyncClient(
            headers={"User-Agent": settings.scraper_user_agent},
            timeout=httpx.Timeout(30.0),
            follow_redirects=True,
        )

    async def __aenter__(self) -> Fetcher:
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self._client.aclose()

    @retry(
        retry=retry_if_exception_type((httpx.TransportError, httpx.HTTPStatusError)),
        wait=wait_exponential(multiplier=1, min=1, max=20),
        stop=stop_after_attempt(3),
        reraise=True,
    )
    async def _get(self, url: str, headers: dict[str, str] | None = None) -> str:
        host = httpx.URL(url).host or ""
        await self._limiter.wait(host)
        resp = await self._client.get(url, headers=headers)
        resp.raise_for_status()
        return resp.text

    async def get_text(self, url: str, headers: dict[str, str] | None = None) -> str:
        if self._cache is not None:
            cached = self._cache.get(url)
            if cached is not None:
                return cached
        text = await self._get(url, headers)
        if self._cache is not None:
            self._cache.set(url, text)
        return text

    @retry(
        retry=retry_if_exception_type((httpx.TransportError, httpx.HTTPStatusError)),
        wait=wait_exponential(multiplier=1, min=1, max=20),
        stop=stop_after_attempt(3),
        reraise=True,
    )
    async def post_text(
        self,
        url: str,
        *,
        data: str | dict[str, str] | None = None,
        headers: dict[str, str] | None = None,
    ) -> str:
        """POST a request and return the response body.

        Not cached (POSTs are typically auth/token calls). Still rate-limited per
        host and retried on transient failures, like ``get_text``.
        """
        host = httpx.URL(url).host or ""
        await self._limiter.wait(host)
        resp = await self._client.post(url, content=data if isinstance(data, str) else None,
                                       data=data if isinstance(data, dict) else None,
                                       headers=headers)
        resp.raise_for_status()
        return resp.text
