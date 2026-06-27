import csv
import io
from models.schemas import ParsedTransaction
from parsers.base import BaseBankParser
from parsers.utils import parse_amount, parse_date


class SBICardParser(BaseBankParser):
    bank_code = "sbi_card"

    def detect(self, content: bytes) -> bool:
        text = content.decode("utf-8", errors="ignore")
        reader = csv.reader(io.StringIO(text))
        for row in reader:
            lower = [c.lower().strip() for c in row]
            if (
                "transaction date" in lower
                and "description" in lower
                and ("amount" in lower or "debit" in lower)
                and "value date" not in lower
            ):
                return True
        return False

    def parse(self, content: bytes) -> list[ParsedTransaction]:
        text = content.decode("utf-8", errors="ignore")
        reader = csv.reader(io.StringIO(text))
        rows = list(reader)

        header_idx = None
        for i, row in enumerate(rows):
            lower = [c.lower().strip() for c in row]
            if "transaction date" in lower and "description" in lower:
                header_idx = i
                break
        if header_idx is None:
            return []

        header = [c.lower().strip() for c in rows[header_idx]]
        col = {h: i for i, h in enumerate(header)}
        credit_key = next((k for k in col if k in ("credit", "deposit")), None)
        debit_key = next((k for k in col if k in ("debit", "amount")), None)

        results: list[ParsedTransaction] = []
        for i, row in enumerate(rows[header_idx + 1:]):
            if not row or row[0].strip().lower().startswith("total"):
                continue
            date_str = row[col["transaction date"]].strip()
            date = parse_date(date_str, "%d/%m/%Y", "%d-%b-%Y")
            if not date:
                continue
            desc = row[col["description"]].strip() if "description" in col else ""
            credit = parse_amount(row[col[credit_key]]) or 0 if credit_key and col[credit_key] < len(row) else 0
            debit = parse_amount(row[col[debit_key]]) or 0 if debit_key and col[debit_key] < len(row) else 0
            if credit == 0 and debit == 0:
                continue
            amount = -credit if credit > 0 else debit
            fingerprint = f"{date_str}|{desc}|{credit}|{debit}"
            results.append(ParsedTransaction(
                posted_at=date, description=desc, amount_minor_units=amount,
                currency_code="INR", source_fingerprint=fingerprint, statement_row_index=i,
            ))
        return results
