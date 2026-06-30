import io
import re
from models.schemas import ParsedTransaction
from parsers.base import BaseBankParser
from parsers.utils import parse_amount, parse_date

# DD-MM-YYYY·HH:MM DESCRIPTION [+]₹AMOUNT [REWARD_POINTS]
_TX_RE = re.compile(
    r'^(\d{2}-\d{2}-\d{4})[^\d:](\d{2}:\d{2})\s+(.+?)\s+([+-]?₹[\d,]+\.\d{2})(?:\s+\d+)?$'
)


class ScapiaCardParser(BaseBankParser):
    bank_code = "scapia_card"

    def detect(self, content: bytes) -> bool:
        if content[:4] != b'%PDF':
            return False
        try:
            import pdfplumber
            with pdfplumber.open(io.BytesIO(content)) as pdf:
                text = (pdf.pages[0].extract_text() or "") if pdf.pages else ""
            return 'ScapiaCoins' in text or ('Scapia' in text and 'BillingCycle' in text)
        except Exception:
            return False

    def parse(self, content: bytes) -> list[ParsedTransaction]:
        import pdfplumber

        results: list[ParsedTransaction] = []
        in_tx = False

        with pdfplumber.open(io.BytesIO(content)) as pdf:
            for page in pdf.pages:
                text = page.extract_text() or ""
                for line in text.splitlines():
                    stripped = line.strip()
                    if 'Your Transactions' in stripped:
                        in_tx = True
                        continue
                    if not in_tx:
                        continue
                    # Stop at non-transaction section headers
                    if stripped and not stripped[0].isdigit() and 'Your Transactions' not in stripped:
                        if re.match(r'^[A-Za-z]', stripped) and not re.match(r'^\d{2}-', stripped):
                            # Could be a section header; check if no ₹ in this line
                            if '₹' not in stripped:
                                in_tx = False
                                continue

                    m = _TX_RE.match(stripped)
                    if not m:
                        continue
                    date_str, time_str, desc, raw_amt = m.groups()
                    is_credit = raw_amt.startswith('+')
                    amt_str = raw_amt.lstrip('+')
                    date = parse_date(date_str, '%d-%m-%Y')
                    if not date:
                        continue
                    amt = parse_amount(amt_str)
                    if amt is None:
                        continue
                    if is_credit:
                        amt = -amt
                    fp = f"{date_str}|{time_str}|{desc}|{raw_amt}"
                    results.append(ParsedTransaction(
                        posted_at=date,
                        description=desc.strip(),
                        amount_minor_units=amt,
                        currency_code='INR',
                        source_fingerprint=fp,
                        statement_row_index=len(results),
                    ))

        return results
