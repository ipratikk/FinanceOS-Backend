from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class ParsedTransaction:
    posted_at: datetime
    description: str
    amount_minor_units: int   # positive = debit (money out), negative = credit (money in)
    currency_code: str
    source_fingerprint: str
    reward_points: int | None = None
    closing_balance_minor_units: int | None = None
    statement_row_index: int | None = None


@dataclass
class ImportRequest:
    ledger_id: str
    transactions: list[ParsedTransaction]


@dataclass
class ImportResult:
    imported: int
    duplicates: int
    errors: list[str] = field(default_factory=list)
