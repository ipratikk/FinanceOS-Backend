import io
import re
from models.schemas import ParsedTransaction
from parsers.base import BaseBankParser
from parsers.utils import parse_amount, parse_date

_V1_TX = re.compile(r'^(\d{2}/\d{2}/\d{4} \d{2}:\d{2}:\d{2})\s+(.+?)\s+([\d,]+\.\d{2})(Cr)?$')
_V2_AMT = re.compile(r'\s+(?:\+\s+(\d+)\s+|\+\s+)?C\s+([\d,]+\.\d{2})\s+l$')
_V2_DT = re.compile(r'^(\d{2}/\d{2}/\d{4})\|\s+(\d{2}:\d{2})\s+')


class HDFCCardPDFParser(BaseBankParser):
    bank_code = "hdfc_card_pdf"

    def detect(self, content: bytes) -> bool:
        if content[:4] != b'%PDF':
            return False
        try:
            import pdfplumber
            with pdfplumber.open(io.BytesIO(content)) as pdf:
                text = (pdf.pages[0].extract_text() or "") if pdf.pages else ""
            return (
                ('HDFC' in text or 'Hdfc' in text)
                and ('Card No' in text or 'Credit Card No.' in text)
            )
        except Exception:
            return False

    def _parse_v1(self, full_text: str) -> list[ParsedTransaction]:
        results: list[ParsedTransaction] = []
        in_tx = False
        for line in full_text.splitlines():
            stripped = line.strip()
            if 'Domestic Transactions' in stripped or 'International Transactions' in stripped:
                in_tx = True
                continue
            if 'Reward Points Summary' in stripped:
                in_tx = False
                continue
            if not in_tx:
                continue
            m = _V1_TX.match(stripped)
            if not m:
                continue
            date_str, desc, amt_str, cr = m.groups()
            date = parse_date(date_str, '%d/%m/%Y %H:%M:%S')
            if not date:
                continue
            amt = parse_amount(amt_str)
            if amt is None:
                continue
            if cr and cr.lower() == 'cr':
                amt = -amt
            results.append(ParsedTransaction(
                posted_at=date,
                description=desc.strip(),
                amount_minor_units=amt,
                currency_code='INR',
                source_fingerprint=f"{date_str}|{desc.strip()}|{amt_str}",
                statement_row_index=len(results),
            ))
        return results

    def _parse_v2(self, full_text: str) -> list[ParsedTransaction]:
        results: list[ParsedTransaction] = []
        for line in full_text.splitlines():
            dt_m = _V2_DT.match(line.strip())
            if not dt_m:
                continue
            rest = line.strip()[dt_m.end():]
            amt_m = _V2_AMT.search(rest)
            if not amt_m:
                continue
            date_str = dt_m.group(1)
            time_str = dt_m.group(2)
            desc = rest[:amt_m.start()].strip()
            reward_pts_str = amt_m.group(1)
            amt_str = amt_m.group(2)
            date = parse_date(date_str, '%d/%m/%Y')
            if not date:
                continue
            amt = parse_amount(amt_str)
            if amt is None:
                continue
            # Credit: '+' before C with no reward points digit
            is_credit = amt_m.group(0).lstrip().startswith('+') and reward_pts_str is None
            if is_credit:
                amt = -amt
            results.append(ParsedTransaction(
                posted_at=date,
                description=desc,
                amount_minor_units=amt,
                currency_code='INR',
                source_fingerprint=f"{date_str}|{time_str}|{desc}|{amt_str}",
                reward_points=int(reward_pts_str) if reward_pts_str else None,
                statement_row_index=len(results),
            ))
        return results

    def parse(self, content: bytes) -> list[ParsedTransaction]:
        import pdfplumber
        pages_text: list[str] = []
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            for page in pdf.pages:
                t = page.extract_text()
                if t:
                    pages_text.append(t)
        full_text = '\n'.join(pages_text)

        # V2 check first: date+pipe is unique to V2; "Domestic Transactions" appears in both
        if re.search(r'\d{2}/\d{2}/\d{4}\|', full_text):
            return self._parse_v2(full_text)
        if 'Domestic Transactions' in full_text or 'International Transactions' in full_text:
            return self._parse_v1(full_text)
        return []
