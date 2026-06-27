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
