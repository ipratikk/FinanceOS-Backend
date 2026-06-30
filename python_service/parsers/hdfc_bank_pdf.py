import io
import re
from collections import defaultdict
from models.schemas import ParsedTransaction
from parsers.base import BaseBankParser
from parsers.utils import parse_amount, parse_date

_DATE_RE = re.compile(r'^\d{2}/\d{2}/\d{2}$')
_REF_RE = re.compile(r'^\d{8,}$')


class HDFCBankPDFParser(BaseBankParser):
    bank_code = "hdfc_bank_pdf"

    def detect(self, content: bytes) -> bool:
        if content[:4] != b'%PDF':
            return False
        try:
            import pdfplumber
            with pdfplumber.open(io.BytesIO(content)) as pdf:
                text = (pdf.pages[0].extract_text() or "") if pdf.pages else ""
            return 'WithdrawalAmt.' in text and 'DepositAmt.' in text and 'Narration' in text
        except Exception:
            return False

    def parse(self, content: bytes) -> list[ParsedTransaction]:
        import pdfplumber

        results: list[ParsedTransaction] = []
        row_idx = 0

        # Column positions from the first page that has the header; reused for all subsequent pages
        withdrawal_x = withdrawal_x1 = deposit_x = deposit_x1 = closing_x = None
        wd_mid = dc_mid = None

        with pdfplumber.open(io.BytesIO(content)) as pdf:
            for page in pdf.pages:
                words = page.extract_words()

                # Update column positions if header found on this page
                for w in words:
                    if w['text'] == 'WithdrawalAmt.':
                        withdrawal_x = w['x0']
                        withdrawal_x1 = w['x1']
                    elif w['text'] == 'DepositAmt.' and deposit_x is None:
                        deposit_x = w['x0']
                        deposit_x1 = w['x1']
                    elif w['text'] == 'ClosingBalance' and closing_x is None:
                        closing_x = w['x0']

                if withdrawal_x is None:
                    continue  # haven't found header on any page yet

                if wd_mid is None:
                    # Use right edge of WithdrawalAmt. header to avoid misclassifying
                    # wide withdrawal amounts that extend past the column x0 midpoint
                    wd_mid = (withdrawal_x1 + deposit_x) / 2 if (withdrawal_x1 and deposit_x) else withdrawal_x + 60
                    dc_mid = (deposit_x1 + closing_x) / 2 if (deposit_x1 and closing_x) else withdrawal_x + 100

                # All words on page (account info rows don't have date-pattern at x0<70)
                tx_words = words

                # Group by row (round top to nearest pixel)
                buckets: dict[int, list] = defaultdict(list)
                for w in tx_words:
                    buckets[round(w['top'])].append(w)

                current: dict | None = None

                def _flush(txn: dict | None) -> ParsedTransaction | None:
                    if txn is None:
                        return None
                    date = parse_date(txn['date'], '%d/%m/%y', '%d/%m/%Y')
                    if not date:
                        return None
                    w_amt = txn.get('withdrawal')
                    d_amt = txn.get('deposit')
                    if w_amt is not None:
                        amount = w_amt
                    elif d_amt is not None:
                        amount = -d_amt
                    else:
                        return None
                    desc = ' '.join(txn['narration'])
                    fp = f"{txn['date']}|{''.join(desc.split())}|{w_amt or 0}|{d_amt or 0}"
                    return ParsedTransaction(
                        posted_at=date,
                        description=desc,
                        amount_minor_units=amount,
                        currency_code='INR',
                        source_fingerprint=fp,
                        closing_balance_minor_units=txn.get('closing'),
                        statement_row_index=txn['idx'],
                    )

                for bucket_y in sorted(buckets):
                    row = sorted(buckets[bucket_y], key=lambda w: w['x0'])
                    leftmost = row[0]

                    if _DATE_RE.match(leftmost['text']) and leftmost['x0'] < 70:
                        # New transaction row
                        if current:
                            t = _flush(current)
                            if t:
                                results.append(t)
                                row_idx += 1

                        current = {
                            'date': leftmost['text'],
                            'narration': [],
                            'withdrawal': None,
                            'deposit': None,
                            'closing': None,
                            'idx': row_idx,
                        }

                        for w in row[1:]:
                            x = w['x0']
                            if closing_x and x >= dc_mid:
                                current['closing'] = parse_amount(w['text'])
                            elif x >= wd_mid:
                                current['deposit'] = parse_amount(w['text'])
                            elif x >= withdrawal_x - 10:
                                current['withdrawal'] = parse_amount(w['text'])
                            elif x < 265 and not _DATE_RE.match(w['text']) and not _REF_RE.match(w['text']):
                                current['narration'].append(w['text'])
                    else:
                        # Continuation row — add narration-column words to current transaction
                        if current:
                            for w in row:
                                if 70 <= w['x0'] < 265 and not _REF_RE.match(w['text']):
                                    current['narration'].append(w['text'])

                # Flush last transaction on page
                if current:
                    t = _flush(current)
                    if t:
                        results.append(t)
                        row_idx += 1
                    current = None

        return results
