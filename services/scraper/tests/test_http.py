import pytest

from protein_scraper.config import Settings
from protein_scraper.http import Fetcher


@pytest.mark.asyncio
async def test_cache_key_disambiguates_same_url(tmp_path, monkeypatch):
    """Same URL + different cache_key must not collide (e.g. eBay marketplaces,
    where the marketplace is a header, not part of the URL)."""
    settings = Settings(scraper_cache_dir=str(tmp_path))
    async with Fetcher(settings) as f:
        calls: list[str] = []

        async def fake_get(url: str, headers=None) -> str:
            calls.append(url)
            return f"resp-{len(calls)}"

        monkeypatch.setattr(f, "_get", fake_get)

        us = await f.get_text("https://api/search", cache_key="https://api/search|EBAY_US")
        gb = await f.get_text("https://api/search", cache_key="https://api/search|EBAY_GB")
        us_again = await f.get_text("https://api/search", cache_key="https://api/search|EBAY_US")

        assert us != gb  # distinct cache keys -> separate fetches
        assert us == us_again  # same key -> served from cache
        assert len(calls) == 2  # third call hit the cache
