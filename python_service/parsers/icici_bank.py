import csv
import io
from models.schemas import ParsedTransaction
from parsers.base import BaseBankParser
from parsers.utils import parse_amount, parse_date


class ICICIBankParser(BaseBankParser):
    bank_code = "icici_bank"

    def detect(self, content: bytes) -> bool:
        text = content.decode("utf-8", errors="ignore").lower()
        return "particulars" in text and "deposits" in text and "withdrawals" in text

    def parse(self, content: bytes) -> list[ParsedTransaction]:
        text = content.decode("utf-8", errors="ignore")
        reader = csv.reader(io.StringIO(text))
        rows = list(reader)

        header_idx = None
        for i, row in enumerate(rows):
            lower = [c.lower().strip() for c in row]
            if "particulars" in lower and "deposits" in lower and "withdrawals" in lower:
                header_idx = i
                break
        if header_idx is None:
            return []

        header = [c.lower().strip() for c in rows[header_idx]]
        col = {h: i for i, h in enumerate(header)}

        results: list[ParsedTransaction] = []
        for i, row in enumerate(rows[header_idx + 1:]):
            if not row or row[0].strip().upper().startswith("B/F"):
                continue
            date_str = row[col.get("date", 0)].strip() if "date" in col else ""
            date = parse_date(date_str, "%d-%m-%Y")
            if not date:
                continue
            desc = row[col["particulars"]].strip() if "particulars" in col else ""
            credit_str = row[col["deposits"]].strip() if "deposits" in col and col["deposits"] < len(row) else ""
            debit_str = row[col["withdrawals"]].strip() if "withdrawals" in col and col["withdrawals"] < len(row) else ""
            credit = parse_amount(credit_str) or 0
            debit = parse_amount(debit_str) or 0
            if credit == 0 and debit == 0:
                continue
            amount = -credit if credit > 0 else debit
            fingerprint = f"{date_str}|{desc}|{credit}|{debit}"
            closing = parse_amount(row[col["balance"]]) if "balance" in col and col["balance"] < len(row) else None
            results.append(ParsedTransaction(
                posted_at=date, description=desc, amount_minor_units=amount,
                currency_code="INR", source_fingerprint=fingerprint,
                closing_balance_minor_units=closing, statement_row_index=i,
            ))
        return results
