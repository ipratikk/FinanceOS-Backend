import asyncpg
import secrets
from datetime import timezone
from crypto.database_encryption import encrypt, hmac_fingerprint
from models.schemas import ParsedTransaction


def tx_id() -> str:
    return f"TX-{secrets.token_hex(4).upper()}"


async def split_new_and_duplicates(
    pool: asyncpg.Pool,
    ledger_id: str,
    transactions: list[ParsedTransaction],
) -> tuple[list[ParsedTransaction], int]:
    """Return (new_transactions, duplicate_count). Checks existing fingerprint
    hashes in Postgres — sourceFingerprint is stored as an HMAC-SHA256 hash,
    not the raw fingerprint string, so incoming fingerprints are hashed the
    same way before comparison."""
    if not transactions:
        return [], 0

    fingerprint_hashes = [hmac_fingerprint(t.source_fingerprint) for t in transactions]
    existing = await pool.fetch(
        'SELECT "sourceFingerprint" FROM "Transaction" WHERE "ledgerId" = $1 AND "sourceFingerprint" = ANY($2)',
        ledger_id,
        fingerprint_hashes,
    )
    existing_hashes = {row["sourceFingerprint"] for row in existing}
    new_txns = [
        t for t in transactions
        if hmac_fingerprint(t.source_fingerprint) not in existing_hashes
    ]
    return new_txns, len(transactions) - len(new_txns)


async def bulk_insert(pool: asyncpg.Pool, ledger_id: str, transactions: list[ParsedTransaction]) -> list[str]:
    """Insert transactions. Returns list of error strings for failed rows.

    narration is encrypted and sourceFingerprint is hashed (HMAC-SHA256) before
    the INSERT — Postgres never stores either in plaintext. merchant has no
    source anywhere in this pipeline (ParsedTransaction has no merchant field)
    and stays NULL, exactly as before this change.
    """
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
                    INSERT INTO "Transaction" (id, date, narration, "amountMinorUnits", "currencyCode", "ledgerId", category, merchant, "sourceFingerprint", "createdAt")
                    VALUES ($6, $1, $2, $3, $4, $5, NULL, NULL, $7, NOW())
                    ON CONFLICT ("ledgerId", "sourceFingerprint") DO NOTHING
                    """,
                    posted_at,
                    encrypt(t.description),
                    t.amount_minor_units,
                    t.currency_code or "INR",
                    ledger_id,
                    tx_id(),
                    hmac_fingerprint(t.source_fingerprint),
                )
            except Exception as e:
                errors.append(f"Row {t.statement_row_index}: {e}")
    return errors
