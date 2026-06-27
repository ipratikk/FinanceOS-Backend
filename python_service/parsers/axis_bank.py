import csv
import io
from models.schemas import ParsedTransaction
from parsers.base import BaseBankParser
from parsers.utils import parse_amount, parse_date


class AxisBankParser(BaseBankParser):
    bank_code = "axis_bank"

    def detect(self, content: bytes) -> bool:
        text = content.decode("utf-8", errors="ignore")
        reader = csv.reader(io.StringIO(text))
        for row in reader:
            lower = [c.lower().strip() for c in row]
            if (
                ("tran. date" in lower or "transaction date" in lower)
                and "description" in lower
                and ("deposit" in lower or "credit" in lower)
                and ("withdrawal" in lower or "debit" in lower)
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
            if (
                ("tran. date" in lower or "transaction date" in lower)
                and "description" in lower
                and (
                    ("deposit" in lower or "credit" in lower)
                    and ("withdrawal" in lower or "debit" in lower)
                )
            ):
                header_idx = i
                break
        if header_idx is None:
            return []

        header = [c.lower().strip() for c in rows[header_idx]]
        col = {h: i for i, h in enumerate(header)}
        date_key = next((k for k in col if k in ("tran. date", "transaction date")), None)
        desc_key = next((k for k in col if k == "description"), None)
        credit_key = next((k for k in col if k in ("deposit", "credit")), None)
        debit_key = next((k for k in col if k in ("withdrawal", "debit")), None)
        balance_key = next((k for k in col if "balance" in k), None)

        if None in (date_key, desc_key):
            return []

        results: list[ParsedTransaction] = []
        for i, row in enumerate(rows[header_idx + 1:]):
            if not row or row[0].strip().upper().startswith("CLOSING BALANCE"):
                continue
            date_str = row[col[date_key]].strip()
            date = parse_date(date_str, "%d/%m/%Y", "%d-%b-%Y")
            if not date:
                continue
            desc = row[col[desc_key]].strip()
            credit = (
                parse_amount(row[col[credit_key]]) or 0
                if credit_key and col[credit_key] < len(row)
                else 0
            )
            debit = (
                parse_amount(row[col[debit_key]]) or 0
                if debit_key and col[debit_key] < len(row)
                else 0
            )
            if credit == 0 and debit == 0:
                continue
            amount = -credit if credit > 0 else debit
            fingerprint = f"{date_str}|{desc}|{credit}|{debit}"
            closing = (
                parse_amount(row[col[balance_key]])
                if balance_key and col[balance_key] < len(row)
                else None
            )
            results.append(ParsedTransaction(
                posted_at=date,
                description=desc,
                amount_minor_units=amount,
                currency_code="INR",
                source_fingerprint=fingerprint,
                closing_balance_minor_units=closing,
                statement_row_index=i,
            ))
        return results
