import asyncpg
from datetime import timezone
from models.schemas import ParsedTransaction


async def split_new_and_duplicates(
    pool: asyncpg.Pool,
    ledger_id: str,
    transactions: list[ParsedTransaction],
) -> tuple[list[ParsedTransaction], int]:
    """Return (new_transactions, duplicate_count). Checks existing fingerprints in Postgres."""
    if not transactions:
        return [], 0

    fingerprints = [t.source_fingerprint for t in transactions]
    existing = await pool.fetch(
        'SELECT "sourceFingerprint" FROM "Transaction" WHERE "ledgerId" = $1 AND "sourceFingerprint" = ANY($2)',
        ledger_id,
        fingerprints,
    )
    existing_set = {row["sourceFingerprint"] for row in existing}
    new_txns = [t for t in transactions if t.source_fingerprint not in existing_set]
    return new_txns, len(transactions) - len(new_txns)


async def bulk_insert(pool: asyncpg.Pool, ledger_id: str, transactions: list[ParsedTransaction]) -> list[str]:
    """Insert transactions. Returns list of error strings for failed rows."""
    if not transactions:
        return []

    errors: list[str] = []
    async with pool.acquire() as conn:
        for t in transactions:
            try:
                # Strip timezone for timestamp without time zone column (convert to UTC first)
                posted_at = t.posted_at
                if posted_at.tzinfo is not None:
                    posted_at = posted_at.astimezone(timezone.utc).replace(tzinfo=None)
                await conn.execute(
                    """
                    INSERT INTO "Transaction" (id, date, narration, amount, "ledgerId", category, merchant, "sourceFingerprint", "createdAt")
                    VALUES (gen_random_uuid()::text, $1, $2, $3, $4, NULL, NULL, $5, NOW())
                    ON CONFLICT ("ledgerId", "sourceFingerprint") DO NOTHING
                    """,
                    posted_at,
                    t.description,
                    t.amount_minor_units / 100.0,
                    ledger_id,
                    t.source_fingerprint,
                )
            except Exception as e:
                errors.append(f"Row {t.statement_row_index}: {e}")
    return errors
