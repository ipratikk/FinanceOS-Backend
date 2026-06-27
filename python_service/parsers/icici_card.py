import csv
import io
from models.schemas import ParsedTransaction
from parsers.base import BaseBankParser
from parsers.utils import parse_amount, parse_date


class ICICICardParser(BaseBankParser):
    bank_code = "icici_card"

    def detect(self, content: bytes) -> bool:
        text = content.decode("utf-8", errors="ignore").lower()
        return "billingamountsign" in text.replace(" ", "")

    def parse(self, content: bytes) -> list[ParsedTransaction]:
        text = content.decode("utf-8", errors="ignore")
        reader = csv.reader(io.StringIO(text))
        rows = list(reader)

        header_idx = None
        for i, row in enumerate(rows):
            lower = [c.lower().strip() for c in row]
            if any("billingamountsign" in c.replace(" ", "") for c in lower):
                header_idx = i
                break
        if header_idx is None:
            return []

        header = [c.lower().strip() for c in rows[header_idx]]
        col = {h: i for i, h in enumerate(header)}
        date_key = next((k for k in col if k == "date"), None)
        desc_key = next(
            (k for k in col if "description" in k or "particulars" in k or "transaction details" in k),
            None,
        )
        amt_key = next((k for k in col if "amount" in k and "sign" not in k), None)
        sign_key = next((k for k in col if "sign" in k), None)

        if None in (date_key, desc_key, amt_key):
            return []

        results: list[ParsedTransaction] = []
        for i, row in enumerate(rows[header_idx + 1:]):
            if len(row) <= max(col[k] for k in [date_key, desc_key, amt_key] if k in col):
                continue
            date_str = row[col[date_key]].strip()
            date = parse_date(date_str, "%d/%m/%Y")
            if not date:
                continue
            abs_amt = parse_amount(row[col[amt_key]])
            if abs_amt is None:
                continue
            sign = row[col[sign_key]].upper().strip() if sign_key and col[sign_key] < len(row) else ""
            amount = -abs_amt if sign == "CR" else abs_amt
            desc = row[col[desc_key]].strip()
            fingerprint = f"{date_str}|{desc}|{abs_amt}"
            results.append(ParsedTransaction(
                posted_at=date, description=desc, amount_minor_units=amount,
                currency_code="INR", source_fingerprint=fingerprint, statement_row_index=i,
            ))
        return results
