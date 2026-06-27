import asyncio
import json
import os
import redis.asyncio as aioredis

_client: aioredis.Redis | None = None
_client_loop: asyncio.AbstractEventLoop | None = None
ANALYTICS_TTL = 300  # 5 minutes


def _redis_client() -> aioredis.Redis:
    global _client, _client_loop
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if _client is None or _client_loop is not loop:
        url = os.environ.get("REDIS_URL", "redis://localhost:6379")
        _client = aioredis.from_url(url, decode_responses=True)
        _client_loop = loop
    return _client


def _analytics_key(ledger_id: str | None, from_date: str | None, to_date: str | None) -> str:
    lid = ledger_id or "all"
    return f"analytics:{lid}:{from_date or ''}:{to_date or ''}"


async def get_analytics_cache(
    ledger_id: str | None, from_date: str | None, to_date: str | None
) -> dict | None:
    key = _analytics_key(ledger_id, from_date, to_date)
    raw = await _redis_client().get(key)
    return json.loads(raw) if raw else None


async def set_analytics_cache(
    ledger_id: str | None, from_date: str | None, to_date: str | None, data: dict
) -> None:
    key = _analytics_key(ledger_id, from_date, to_date)
    await _redis_client().set(key, json.dumps(data), ex=ANALYTICS_TTL)


async def invalidate_ledger_cache(ledger_id: str) -> None:
    """Delete all analytics keys for this ledger (and the all-ledgers key)."""
    client = _redis_client()
    pattern_ledger = f"analytics:{ledger_id}:*"
    pattern_all = "analytics:all:*"
    for pattern in (pattern_ledger, pattern_all):
        keys = await client.keys(pattern)
        if keys:
            await client.delete(*keys)
