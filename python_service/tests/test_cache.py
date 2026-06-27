import pytest
from cache import get_analytics_cache, set_analytics_cache, invalidate_ledger_cache


@pytest.mark.asyncio
async def test_cache_miss_returns_none():
    result = await get_analytics_cache("missing-id-xyz", None, None)
    assert result is None


@pytest.mark.asyncio
async def test_set_and_get():
    data = {"totalSpend": 1000.0, "totalIncome": 500.0}
    await set_analytics_cache("ledger-1", "2026-01-01", "2026-01-31", data)
    result = await get_analytics_cache("ledger-1", "2026-01-01", "2026-01-31")
    assert result == data


@pytest.mark.asyncio
async def test_invalidate_clears_ledger():
    data = {"totalSpend": 999.0}
    await set_analytics_cache("ledger-x", None, None, data)
    await invalidate_ledger_cache("ledger-x")
    result = await get_analytics_cache("ledger-x", None, None)
    assert result is None
