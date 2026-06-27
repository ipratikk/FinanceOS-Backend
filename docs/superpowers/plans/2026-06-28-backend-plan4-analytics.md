# FinanceOS Backend — Plan 4: Analytics + Redis Cache

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the Python `/analytics` endpoint (port of `GRDBSpendingService`), add Redis caching with 5-minute TTL, invalidate cache on import, and wire the `analytics` GraphQL query in Node.js.

**Architecture:** Python computes `SpendingSummary` from raw Postgres queries (total spend/income, category breakdown, monthly breakdown). Redis key: `analytics:{ledger_id_or_all}:{from}:{to}` with 5-minute TTL. Cache is invalidated on every successful `/import` call for the affected ledger.

**Tech Stack:** Python 3.12 + asyncpg + redis-py[hiredis] + FastAPI; Node.js Axios client already wired in Plan 3.

---

## Prerequisite

Plan 3 complete. Full GraphQL schema live. `/parse` and `/import` working end-to-end.

---

## File Map

```
python_service/
├── analytics/
│   ├── __init__.py
│   └── spending.py             # SpendingSummary computation (port of GRDBSpendingService)
├── cache.py                    # Redis get/set/invalidate helpers
├── main.py                     # MODIFY: add /analytics, invalidate cache in /import
└── tests/
    ├── test_analytics.py
    └── test_cache.py
```

---

### Task 1: Redis cache module

**Files:**
- Create: `python_service/cache.py`
- Create: `python_service/tests/test_cache.py`

- [ ] **Step 1: Create `python_service/cache.py`**

```python
import json
import os
import redis.asyncio as aioredis

_client: aioredis.Redis | None = None
ANALYTICS_TTL = 300  # 5 minutes


def _redis_client() -> aioredis.Redis:
    global _client
    if _client is None:
        url = os.environ.get("REDIS_URL", "redis://localhost:6379")
        _client = aioredis.from_url(url, decode_responses=True)
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
    await _redis_client().setex(key, ANALYTICS_TTL, json.dumps(data))


async def invalidate_ledger_cache(ledger_id: str) -> None:
    """Delete all analytics keys for this ledger (and the all-ledgers key)."""
    client = _redis_client()
    pattern_ledger = f"analytics:{ledger_id}:*"
    pattern_all = "analytics:all:*"
    for pattern in (pattern_ledger, pattern_all):
        keys = await client.keys(pattern)
        if keys:
            await client.delete(*keys)
```

- [ ] **Step 2: Write cache tests (require Redis running)**

```python
# python_service/tests/test_cache.py
import pytest
import asyncio
from cache import get_analytics_cache, set_analytics_cache, invalidate_ledger_cache

@pytest.mark.asyncio
async def test_cache_miss_returns_none():
    result = await get_analytics_cache("missing-id", None, None)
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
```

- [ ] **Step 3: Install pytest-asyncio**

```bash
cd python_service
source .venv/bin/activate
pip install pytest-asyncio
echo "asyncio_mode = auto" >> pytest.ini
```

- [ ] **Step 4: Run cache tests (Redis must be running)**

```bash
REDIS_URL=redis://localhost:6379 pytest tests/test_cache.py -v
```

Expected: 3 tests pass.

- [ ] **Step 5: Commit**

```bash
git add python_service/cache.py python_service/tests/test_cache.py python_service/pytest.ini
git commit -m "feat: add Redis analytics cache with 5-minute TTL and ledger invalidation"
```

---

### Task 2: Spending analytics service

**Files:**
- Create: `python_service/analytics/__init__.py`
- Create: `python_service/analytics/spending.py`
- Create: `python_service/tests/test_analytics.py`

- [ ] **Step 1: Create `python_service/analytics/__init__.py`** (empty)

- [ ] **Step 2: Write failing test**

```python
# python_service/tests/test_analytics.py
# Uses in-memory data (no DB needed for unit tests)
import pytest
from datetime import datetime, timezone, timedelta
from analytics.spending import compute_summary

IST = timezone(timedelta(hours=5, minutes=30))

SAMPLE_ROWS = [
    # (date, amount, category)  amount in rupees (float), positive=debit, negative=credit
    (datetime(2026, 1, 15, tzinfo=IST), 500.0, "Food"),
    (datetime(2026, 1, 20, tzinfo=IST), 1200.0, "Shopping"),
    (datetime(2026, 2, 5, tzinfo=IST), -50000.0, None),    # salary credit
    (datetime(2026, 2, 10, tzinfo=IST), 300.0, "Food"),
    (datetime(2026, 2, 15, tzinfo=IST), 800.0, "Shopping"),
]

def test_total_spend():
    summary = compute_summary(SAMPLE_ROWS)
    assert summary["totalSpend"] == pytest.approx(2800.0)

def test_total_income():
    summary = compute_summary(SAMPLE_ROWS)
    assert summary["totalIncome"] == pytest.approx(50000.0)

def test_net_flow():
    summary = compute_summary(SAMPLE_ROWS)
    assert summary["netFlow"] == pytest.approx(50000.0 - 2800.0)

def test_by_category():
    summary = compute_summary(SAMPLE_ROWS)
    cats = {c["category"]: c for c in summary["byCategory"]}
    assert cats["Food"]["amount"] == pytest.approx(800.0)
    assert cats["Food"]["count"] == 2
    assert cats["Shopping"]["amount"] == pytest.approx(2000.0)

def test_by_month():
    summary = compute_summary(SAMPLE_ROWS)
    months = {m["month"]: m for m in summary["byMonth"]}
    assert "2026-01" in months
    assert "2026-02" in months
    assert months["2026-01"]["spend"] == pytest.approx(1700.0)
    assert months["2026-02"]["income"] == pytest.approx(50000.0)
```

- [ ] **Step 3: Run — expect ImportError**

```bash
pytest tests/test_analytics.py -v
```

- [ ] **Step 4: Create `python_service/analytics/spending.py`**

```python
from collections import defaultdict
from datetime import datetime


def compute_summary(
    rows: list[tuple[datetime, float, str | None]],
) -> dict:
    """
    Compute SpendingSummary from a list of (date, amount_rupees, category) tuples.
    amount > 0 = debit (spend), amount < 0 = credit (income).
    """
    total_spend = 0.0
    total_income = 0.0
    category_spend: dict[str, float] = defaultdict(float)
    category_count: dict[str, int] = defaultdict(int)
    monthly_spend: dict[str, float] = defaultdict(float)
    monthly_income: dict[str, float] = defaultdict(float)

    for date, amount, category in rows:
        month_key = date.strftime("%Y-%m")
        if amount > 0:
            total_spend += amount
            monthly_spend[month_key] += amount
            cat = category or "Uncategorised"
            category_spend[cat] += amount
            category_count[cat] += 1
        else:
            income = abs(amount)
            total_income += income
            monthly_income[month_key] += income

    all_months = sorted(set(list(monthly_spend.keys()) + list(monthly_income.keys())))

    return {
        "totalSpend": round(total_spend, 2),
        "totalIncome": round(total_income, 2),
        "netFlow": round(total_income - total_spend, 2),
        "byCategory": [
            {"category": cat, "amount": round(amt, 2), "count": category_count[cat]}
            for cat, amt in sorted(category_spend.items(), key=lambda x: -x[1])
        ],
        "byMonth": [
            {
                "month": m,
                "spend": round(monthly_spend.get(m, 0.0), 2),
                "income": round(monthly_income.get(m, 0.0), 2),
            }
            for m in all_months
        ],
    }


async def fetch_and_compute(
    pool,
    ledger_id: str | None,
    from_date: str | None,
    to_date: str | None,
) -> dict:
    """Fetch transactions from Postgres and compute summary."""
    conditions = []
    args: list = []
    arg_idx = 1

    if ledger_id:
        conditions.append(f'"ledgerId" = ${arg_idx}')
        args.append(ledger_id)
        arg_idx += 1
    if from_date:
        conditions.append(f'"date" >= ${arg_idx}')
        args.append(from_date)
        arg_idx += 1
    if to_date:
        conditions.append(f'"date" <= ${arg_idx}')
        args.append(to_date)
        arg_idx += 1

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    query = f'SELECT date, amount, category FROM "Transaction" {where}'

    rows_db = await pool.fetch(query, *args)
    rows = [(r["date"], float(r["amount"]), r["category"]) for r in rows_db]
    return compute_summary(rows)
```

- [ ] **Step 5: Run tests — expect pass**

```bash
pytest tests/test_analytics.py -v
```

Expected: 5 tests pass.

- [ ] **Step 6: Commit**

```bash
git add python_service/analytics/ python_service/tests/test_analytics.py
git commit -m "feat: add spending analytics service with category + monthly breakdown"
```

---

### Task 3: `/analytics` endpoint + cache integration

**Files:**
- Modify: `python_service/main.py`

- [ ] **Step 1: Add `/analytics` route and update `/import` to invalidate cache**

Add to `python_service/main.py` (after existing routes):

```python
# Add these imports at the top of main.py:
# from cache import get_analytics_cache, set_analytics_cache, invalidate_ledger_cache
# from analytics.spending import fetch_and_compute

@app.get("/analytics")
async def analytics(
    ledger_id: str | None = None,
    from_date: str | None = None,
    to_date: str | None = None,
):
    cached = await get_analytics_cache(ledger_id, from_date, to_date)
    if cached:
        return cached

    pool = await get_pool()
    summary = await fetch_and_compute(pool, ledger_id, from_date, to_date)
    await set_analytics_cache(ledger_id, from_date, to_date, summary)
    return summary
```

Also update the `/import` route to call `invalidate_ledger_cache(body.ledger_id)` after a successful bulk insert.

The full updated `main.py`:

```python
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from analytics.spending import fetch_and_compute
from cache import get_analytics_cache, invalidate_ledger_cache, set_analytics_cache
from database import close_pool, get_pool
from parsers.detector import detect_parser
from pipeline.deduplicator import bulk_insert, split_new_and_duplicates


@asynccontextmanager
async def lifespan(app: FastAPI):
    await get_pool()
    yield
    await close_pool()


app = FastAPI(title="FinanceOS Parser Service", version="0.3.0", lifespan=lifespan)


@app.get("/health")
async def health():
    pool = await get_pool()
    await pool.fetchval("SELECT 1")
    return {"status": "ok", "db": "connected"}


@app.post("/parse")
async def parse_file(
    file: UploadFile = File(...),
    bank_code: str | None = Form(default=None),
):
    content = await file.read()
    parser = detect_parser(content, bank_code)
    if parser is None:
        raise HTTPException(status_code=422, detail="Unrecognised statement format. Provide bank_code.")
    transactions = parser.parse(content)
    return {
        "bank_code": parser.bank_code,
        "count": len(transactions),
        "transactions": [
            {
                "postedAt": t.posted_at.isoformat(),
                "description": t.description,
                "amountMinorUnits": t.amount_minor_units,
                "currencyCode": t.currency_code,
                "sourceFingerprint": t.source_fingerprint,
                "rewardPoints": t.reward_points,
                "closingBalanceMinorUnits": t.closing_balance_minor_units,
                "statementRowIndex": t.statement_row_index,
            }
            for t in transactions
        ],
    }


class ImportBody(BaseModel):
    ledger_id: str
    bank_code: str | None = None
    transactions: list[dict]


@app.post("/import")
async def import_transactions(body: ImportBody):
    from models.schemas import ParsedTransaction
    from datetime import datetime, timezone, timedelta

    IST = timezone(timedelta(hours=5, minutes=30))
    parsed = []
    for t in body.transactions:
        posted_at = datetime.fromisoformat(t["postedAt"]) if isinstance(t["postedAt"], str) else t["postedAt"]
        if posted_at.tzinfo is None:
            posted_at = posted_at.replace(tzinfo=IST)
        parsed.append(ParsedTransaction(
            posted_at=posted_at,
            description=t["description"],
            amount_minor_units=t["amountMinorUnits"],
            currency_code=t.get("currencyCode", "INR"),
            source_fingerprint=t["sourceFingerprint"],
        ))

    pool = await get_pool()
    new_txns, duplicates = await split_new_and_duplicates(pool, body.ledger_id, parsed)
    errors = await bulk_insert(pool, body.ledger_id, new_txns)

    # Invalidate analytics cache for this ledger
    if new_txns:
        await invalidate_ledger_cache(body.ledger_id)

    return {
        "imported": len(new_txns) - len(errors),
        "duplicates": duplicates,
        "errors": errors,
    }


@app.get("/analytics")
async def analytics(
    ledger_id: str | None = None,
    from_date: str | None = None,
    to_date: str | None = None,
):
    cached = await get_analytics_cache(ledger_id, from_date, to_date)
    if cached:
        return cached

    pool = await get_pool()
    summary = await fetch_and_compute(pool, ledger_id, from_date, to_date)
    await set_analytics_cache(ledger_id, from_date, to_date, summary)
    return summary
```

- [ ] **Step 2: Smoke test `/analytics` (requires transactions in DB from Plan 3 upload)**

```bash
curl "http://localhost:8000/analytics"
```

Expected: JSON with `totalSpend`, `totalIncome`, `netFlow`, `byCategory`, `byMonth`.

- [ ] **Step 3: Verify cache works (second call is faster)**

```bash
time curl "http://localhost:8000/analytics"
time curl "http://localhost:8000/analytics"
```

Both return same data; second call should be faster (Redis hit).

- [ ] **Step 4: Commit**

```bash
git add python_service/main.py
git commit -m "feat: add /analytics endpoint with Redis caching and cache invalidation on import"
```

---

### Task 4: Verify `analytics` GraphQL query end-to-end

**Files:** No new files (Node.js resolver already wired in Plan 3).

- [ ] **Step 1: Rebuild Docker services**

```bash
docker compose down && docker compose up --build
```

- [ ] **Step 2: Query analytics via GraphQL**

```bash
curl -X POST http://localhost:4000/graphql \
  -H "Content-Type: application/json" \
  -d '{"query":"{ analytics { totalSpend totalIncome netFlow byCategory { category amount count } byMonth { month spend income } } }"}'
```

Expected: JSON with all fields populated. No errors.

- [ ] **Step 3: Query with ledger filter**

```bash
# Replace <LEDGER_ID> with an actual ledger UUID from the DB
curl -X POST http://localhost:4000/graphql \
  -H "Content-Type: application/json" \
  -d '{"query":"{ analytics(ledgerId: \"<LEDGER_ID>\", from: \"2026-01-01\", to: \"2026-12-31\") { totalSpend totalIncome } }"}'
```

Expected: Returns spend/income for that ledger only.

- [ ] **Step 4: Run full Python test suite**

```bash
cd python_service
REDIS_URL=redis://localhost:6379 DATABASE_URL=postgresql://financeOS:financeOS@localhost:5432/financeOS pytest tests/ -v
```

Expected: All tests pass.

- [ ] **Step 5: Final commit**

```bash
git tag v0.4.0-analytics
```
