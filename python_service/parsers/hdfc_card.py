from models.schemas import ParsedTransaction
from parsers.base import BaseBankParser
from parsers.utils import parse_amount, parse_date


class HDFCCardParser(BaseBankParser):
    bank_code = "hdfc_card"

    def detect(self, content: bytes) -> bool:
        text = content.decode("utf-8", errors="ignore")
        return "~|~" in text and "Card No:" in text

    def parse(self, content: bytes) -> list[ParsedTransaction]:
        text = content.decode("utf-8", errors="ignore")
        lines = text.splitlines()

        rows: list[list[str]] = []
        collecting = False
        header: list[str] | None = None

        for line in lines:
            if "Domestic / International" in line:
                collecting = True
                continue
            if not collecting:
                continue
            row = [c.strip() for c in line.split("~|~")]
            if header is None and any("transaction" in c.lower() for c in row):
                header = [c.lower() for c in row]
                continue
            if header and row and row[0]:
                rows.append(row)

        if not header:
            return []

        date_idx = next((i for i, h in enumerate(header) if h == "date"), None)
        desc_idx = next(
            (i for i, h in enumerate(header) if h in ("description", "transaction details")), None
        )
        amt_idx = next((i for i, h in enumerate(header) if h == "amt"), None)
        sign_idx = next((i for i, h in enumerate(header) if h == "debit /credit"), None)

        if None in (date_idx, desc_idx, amt_idx):
            return []

        results: list[ParsedTransaction] = []
        for i, row in enumerate(rows):
            needed = max(x for x in [date_idx, desc_idx, amt_idx] if x is not None)
            if len(row) <= needed:
                continue
            date_str = row[date_idx]
            date = parse_date(date_str, "%d/%m/%Y %H:%M:%S")
            if not date:
                continue
            abs_amt = parse_amount(row[amt_idx])
            if abs_amt is None:
                continue
            sign = row[sign_idx].lower() if sign_idx is not None and sign_idx < len(row) else ""
            is_credit = sign == "cr"
            amount = -abs_amt if is_credit else abs_amt
            desc = row[desc_idx].strip()
            fingerprint = f"{date_str}|{desc}|{abs_amt}"
            results.append(ParsedTransaction(
                posted_at=date,
                description=desc,
                amount_minor_units=amount,
                currency_code="INR",
                source_fingerprint=fingerprint,
                statement_row_index=i,
            ))
        return results
