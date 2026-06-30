import io
import re
from collections import defaultdict
from models.schemas import ParsedTransaction
from parsers.base import BaseBankParser
from parsers.utils import parse_amount, parse_date

_SERIAL_RE = re.compile(r'^\d+$')
_DATE_RE = re.compile(r'^\d{2}\.\d{2}\.\d{4}$')


class ICICIBankPDFParser(BaseBankParser):
    bank_code = "icici_bank_pdf"

    def detect(self, content: bytes) -> bool:
        if content[:4] != b'%PDF':
            return False
        try:
            import pdfplumber
            with pdfplumber.open(io.BytesIO(content)) as pdf:
                text = (pdf.pages[0].extract_text() or "") if pdf.pages else ""
            return (
                'ICICI' in text
                and 'Saving Account' in text
                and 'Withdrawal' in text
                and 'Deposit' in text
            )
        except Exception:
            return False

    def parse(self, content: bytes) -> list[ParsedTransaction]:
        import pdfplumber

        results: list[ParsedTransaction] = []

        with pdfplumber.open(io.BytesIO(content)) as pdf:
            for page in pdf.pages:
                words = page.extract_words()

                # Locate column header: find "Withdrawal" at x0 > 380
                header_top = withdrawal_x = deposit_x = balance_x = None
                for w in words:
                    if w['text'] == 'Withdrawal' and w['x0'] > 380:
                        withdrawal_x = w['x0']
                        header_top = w['top']
                    elif w['text'] == 'Deposit' and w['x0'] > 450 and deposit_x is None:
                        deposit_x = w['x0']
                    elif w['text'] == 'Balance' and w['x0'] > 520 and balance_x is None:
                        balance_x = w['x0']

                if header_top is None or withdrawal_x is None:
                    continue

                wd_mid = (withdrawal_x + deposit_x) / 2 if deposit_x else withdrawal_x + 35
                db_mid = (deposit_x + balance_x) / 2 if (deposit_x and balance_x) else withdrawal_x + 70

                # Words below header
                tx_words = [w for w in words if w['top'] > header_top + 10]

                # Group by row (round top to nearest pixel)
                buckets: dict[int, list] = defaultdict(list)
                for w in tx_words:
                    buckets[round(w['top'])].append(w)

                sorted_ys = sorted(buckets)

                # Identify transaction rows: has serial (int, x0<40) AND date (x0∈[55,115])
                txn_ys: list[int] = []
                for y in sorted_ys:
                    row = buckets[y]
                    has_serial = any(_SERIAL_RE.match(w['text']) and w['x0'] < 40 for w in row)
                    has_date = any(_DATE_RE.match(w['text']) and 55 <= w['x0'] <= 115 for w in row)
                    if has_serial and has_date:
                        txn_ys.append(y)

                for i, sy in enumerate(txn_ys):
                    row = buckets[sy]
                    date_str = None
                    withdrawal = deposit = balance = None

                    for w in row:
                        x = w['x0']
                        if _DATE_RE.match(w['text']) and 55 <= x <= 115:
                            date_str = w['text']
                        elif x >= db_mid - 5:
                            balance = parse_amount(w['text'])
                        elif x >= wd_mid:
                            deposit = parse_amount(w['text'])
                        elif x >= withdrawal_x - 10:
                            withdrawal = parse_amount(w['text'])

                    if not date_str:
                        continue
                    date = parse_date(date_str, '%d.%m.%Y')
                    if not date:
                        continue

                    # Narration: words at x0∈[150, withdrawal_x-10) in range (lower_cut, upper_cut)
                    prev_sy = txn_ys[i - 1] if i > 0 else (sy - 60)
                    next_sy = txn_ys[i + 1] if i < len(txn_ys) - 1 else (sy + 60)
                    lower_cut = prev_sy + 0.75 * (sy - prev_sy)
                    upper_cut = sy + 0.75 * (next_sy - sy)

                    narration_parts: list[str] = []
                    for y in sorted_ys:
                        if y < lower_cut or y > upper_cut:
                            continue
                        if y == sy:
                            continue  # transaction row has no narration-column words
                        for w in sorted(buckets[y], key=lambda w: w['x0']):
                            if 150 <= w['x0'] < withdrawal_x - 10:
                                narration_parts.append(w['text'])

                    desc = ' '.join(narration_parts)

                    if withdrawal is not None:
                        amount = withdrawal
                    elif deposit is not None:
                        amount = -deposit
                    else:
                        continue

                    fp = f"{date_str}|{''.join(desc.split())}|{withdrawal or 0}|{deposit or 0}"
                    results.append(ParsedTransaction(
                        posted_at=date,
                        description=desc,
                        amount_minor_units=amount,
                        currency_code='INR',
                        source_fingerprint=fp,
                        closing_balance_minor_units=balance,
                        statement_row_index=len(results),
                    ))

        return results
