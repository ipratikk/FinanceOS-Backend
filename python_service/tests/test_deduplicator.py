import os
import uuid
from datetime import datetime, timezone

import asyncpg
import pytest

from models.schemas import ParsedTransaction
from pipeline.deduplicator import bulk_insert, split_new_and_duplicates

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/financeos")


@pytest.fixture
async def pool():
    p = await asyncpg.create_pool(DATABASE_URL)
    yield p
    await p.close()


@pytest.fixture
async def test_ledger(pool):
    bank_id = str(uuid.uuid4())
    ledger_id = str(uuid.uuid4())
    async with pool.acquire() as conn:
        await conn.execute(
            'INSERT INTO "Bank" (id, name, code) VALUES ($1, $2, $3)',
            bank_id, "Dedup Test Bank", f"DEDUPTEST{uuid.uuid4().hex[:8]}",
        )
        await conn.execute(
            'INSERT INTO "Ledger" (id, "displayName", kind, "bankId", "updatedAt") VALUES ($1, $2, $3, $4, NOW())',
            ledger_id, "Dedup Test Ledger", "BANK_ACCOUNT", bank_id,
        )
    yield ledger_id
    async with pool.acquire() as conn:
        await conn.execute('DELETE FROM "Transaction" WHERE "ledgerId" = $1', ledger_id)
        await conn.execute('DELETE FROM "Ledger" WHERE id = $1', ledger_id)
        await conn.execute('DELETE FROM "Bank" WHERE id = $1', bank_id)


def make_txn(desc: str, fingerprint: str) -> ParsedTransaction:
    return ParsedTransaction(
        posted_at=datetime(2026, 1, 15, tzinfo=timezone.utc),
        description=desc,
        amount_minor_units=50000,
        currency_code="INR",
        source_fingerprint=fingerprint,
    )


async def test_bulk_insert_stores_encrypted_narration_and_hashed_fingerprint(pool, test_ledger):
    txn = make_txn("SWIGGY BANGALORE", "15/03/24|SWIGGY BANGALORE|50000|0")
    errors = await bulk_insert(pool, test_ledger, [txn])
    assert errors == []

    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            'SELECT narration, "sourceFingerprint" FROM "Transaction" WHERE "ledgerId" = $1',
            test_ledger,
        )
    assert row["narration"] != "SWIGGY BANGALORE"
    assert row["sourceFingerprint"] != "15/03/24|SWIGGY BANGALORE|50000|0"

    from crypto.database_encryption import decrypt
    assert decrypt(row["narration"]) == "SWIGGY BANGALORE"


async def test_split_new_and_duplicates_detects_reimport_after_encryption(pool, test_ledger):
    txn = make_txn("SWIGGY BANGALORE", "15/03/24|SWIGGY BANGALORE|50000|0")
    await bulk_insert(pool, test_ledger, [txn])

    # Re-"import" the exact same transaction — should be detected as a duplicate
    # even though the stored fingerprint is now a hash, not the raw string.
    new_txns, dup_count = await split_new_and_duplicates(pool, test_ledger, [txn])
    assert dup_count == 1
    assert new_txns == []


async def test_split_new_and_duplicates_allows_genuinely_new_transaction(pool, test_ledger):
    txn1 = make_txn("SWIGGY BANGALORE", "15/03/24|SWIGGY BANGALORE|50000|0")
    await bulk_insert(pool, test_ledger, [txn1])

    txn2 = make_txn("ZOMATO DELHI", "16/03/24|ZOMATO DELHI|30000|0")
    new_txns, dup_count = await split_new_and_duplicates(pool, test_ledger, [txn2])
    assert dup_count == 0
    assert len(new_txns) == 1
