from models.schemas import ParsedTransaction
from parsers.base import BaseBankParser
from parsers.utils import parse_amount, parse_date


class HDFCBankTXTParser(BaseBankParser):
    bank_code = "hdfc_bank_txt"

    def detect(self, content: bytes) -> bool:
        text = content.decode("utf-8", errors="ignore").lower()
        return "narration" in text and "closing balance" in text

    def parse(self, content: bytes) -> list[ParsedTransaction]:
        text = content.decode("utf-8", errors="ignore")
        lines = text.splitlines()

        header: list[str] | None = None
        col: dict[str, int] = {}
        results: list[ParsedTransaction] = []
        row_idx = 0

        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue
            parts = [p.strip() for p in stripped.split(",")]
            if header is None:
                lower = [p.lower() for p in parts]
                if "narration" in lower and "closing balance" in lower:
                    header = lower
                    col = {h: i for i, h in enumerate(header)}
                continue

            date_str = parts[col.get("date", 0)] if "date" in col else ""
            date = parse_date(date_str, "%d/%m/%y", "%d/%m/%Y")
            if not date:
                continue

            desc_raw = parts[col["narration"]] if "narration" in col else ""
            desc = " ".join(desc_raw.split())
            fp_desc = "".join(desc.split())

            debit_key = next((k for k in col if "debit" in k or "withdrawal" in k), None)
            credit_key = next((k for k in col if "credit" in k or "deposit" in k), None)
            balance_key = next((k for k in col if "closing" in k or "balance" in k), None)

            debit_str = parts[col[debit_key]] if debit_key and col[debit_key] < len(parts) else ""
            credit_str = parts[col[credit_key]] if credit_key and col[credit_key] < len(parts) else ""

            credit = parse_amount(credit_str) or 0
            debit = parse_amount(debit_str) or 0

            if credit == 0 and debit == 0:
                continue

            amount = -credit if credit > 0 else debit
            fingerprint = f"{date_str}|{fp_desc}|{credit}|{debit}"

            closing = None
            if balance_key and col[balance_key] < len(parts):
                closing = parse_amount(parts[col[balance_key]])

            results.append(ParsedTransaction(
                posted_at=date,
                description=desc,
                amount_minor_units=amount,
                currency_code="INR",
                source_fingerprint=fingerprint,
                closing_balance_minor_units=closing,
                statement_row_index=row_idx,
            ))
            row_idx += 1

        return results
