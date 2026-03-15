"""Tests for JSONCache service."""

import pytest

from linkedin_mcp.services.cache import JSONCache


@pytest.fixture
def cache(tmp_path):
    return JSONCache(tmp_path / "cache", ttl_hours=1)


@pytest.mark.asyncio
async def test_set_and_get(cache):
    await cache.set("ns", "key1", {"value": 42})
    result = await cache.get("ns", "key1")
    assert result == {"value": 42}


@pytest.mark.asyncio
async def test_get_missing_returns_none(cache):
    result = await cache.get("ns", "missing")
    assert result is None


@pytest.mark.asyncio
async def test_delete(cache):
    await cache.set("ns", "key1", {"value": 1})
    await cache.delete("ns", "key1")
    result = await cache.get("ns", "key1")
    assert result is None


@pytest.mark.asyncio
async def test_clear_namespace(cache):
    await cache.set("ns", "a", {"v": 1})
    await cache.set("ns", "b", {"v": 2})
    await cache.set("other", "c", {"v": 3})
    await cache.clear("ns")
    assert await cache.get("ns", "a") is None
    assert await cache.get("ns", "b") is None
    assert await cache.get("other", "c") == {"v": 3}


@pytest.mark.asyncio
async def test_expired_cache_returns_none(tmp_path):
    from unittest.mock import patch
    cache = JSONCache(tmp_path / "cache", ttl_hours=1)
    await cache.set("ns", "key1", {"value": 1})
    # Simulate time passing beyond the TTL
    with patch("time.time", return_value=9999999999.0):
        result = await cache.get("ns", "key1")
    assert result is None


@pytest.mark.asyncio
async def test_clear_all_namespaces(cache):
    await cache.set("ns1", "a", {"v": 1})
    await cache.set("ns2", "b", {"v": 2})
    await cache.clear()
    assert await cache.get("ns1", "a") is None
    assert await cache.get("ns2", "b") is None


@pytest.mark.asyncio
async def test_delete_nonexistent_key_no_error(cache):
    # Should not raise even if the key never existed
    await cache.delete("ns", "nonexistent")


@pytest.mark.asyncio
async def test_corrupt_json_returns_none(tmp_path):
    cache = JSONCache(tmp_path / "cache", ttl_hours=1)
    # Write a valid entry first to create the directory
    await cache.set("ns", "corrupt", {"v": 1})
    # Now corrupt the file
    path = cache._get_path("ns", "corrupt")
    path.write_text("not valid json{{{", encoding="utf-8")
    result = await cache.get("ns", "corrupt")
    assert result is None


@pytest.mark.asyncio
async def test_concurrent_writes_no_crash(tmp_path):
    import asyncio
    cache = JSONCache(tmp_path / "cache", ttl_hours=1)
    # Multiple concurrent writes to different keys should not crash
    tasks = [cache.set("ns", f"key_{i}", {"v": i}) for i in range(10)]
    await asyncio.gather(*tasks)
    # All values should be readable
    for i in range(10):
        result = await cache.get("ns", f"key_{i}")
        assert result == {"v": i}
