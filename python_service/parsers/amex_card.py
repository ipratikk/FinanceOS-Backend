import csv
import io
from models.schemas import ParsedTransaction
from parsers.base import BaseBankParser
from parsers.utils import parse_amount, parse_date


class AmexCardParser(BaseBankParser):
    bank_code = "amex_card"

    def detect(self, content: bytes) -> bool:
        text = content.decode("utf-8", errors="ignore")
        reader = csv.reader(io.StringIO(text))
        rows = list(reader)
        if not rows:
            return False
        header = [c.lower().strip() for c in rows[0]]
        return (
            len(header) == 3
            and "date" in header
            and "description" in header
            and "amount" in header
        )

    def parse(self, content: bytes) -> list[ParsedTransaction]:
        text = content.decode("utf-8", errors="ignore")
        reader = csv.reader(io.StringIO(text))
        rows = list(reader)
        if len(rows) < 2:
            return []

        header = [c.lower().strip() for c in rows[0]]
        col = {h: i for i, h in enumerate(header)}

        results: list[ParsedTransaction] = []
        for i, row in enumerate(rows[1:]):
            if len(row) < 3:
                continue
            date_str = row[col["date"]].strip()
            date = parse_date(date_str, "%m/%d/%Y")
            if not date:
                continue
            amt = parse_amount(row[col["amount"]])
            if amt is None:
                continue
            desc = row[col["description"]].strip()
            fingerprint = f"{date_str}|{desc}|{amt}"
            results.append(ParsedTransaction(
                posted_at=date,
                description=desc,
                amount_minor_units=amt,
                currency_code="INR",
                source_fingerprint=fingerprint,
                statement_row_index=i,
            ))
        return results
