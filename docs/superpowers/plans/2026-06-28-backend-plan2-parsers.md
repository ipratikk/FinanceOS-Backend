# FinanceOS Backend — Plan 2: Python Parsers + Import Pipeline

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Port all 9 bank parsers from Swift to Python, implement `/parse` and `/import` endpoints with deduplication, and validate against existing fixture files from the iOS repo.

**Architecture:** `python_service/parsers/` holds one file per bank. A `detector.py` tries each parser's `detect()` in order of specificity. The `/parse` endpoint auto-detects or uses the provided `bank_code`. The `/import` endpoint writes deduplicated rows to Postgres via `asyncpg`.

**Tech Stack:** Python 3.12 + FastAPI + asyncpg + pytest; fixture files copied from `FinanceOS/Packages/FinanceParsers/Tests/Fixtures/`

---

## Prerequisite

Plan 1 complete: `docker compose up` shows all 4 services healthy.

---

## File Map

```
python_service/
├── models/
│   └── schemas.py              # ParsedTransaction, ImportRequest, ImportResult
├── parsers/
│   ├── __init__.py
│   ├── base.py                 # BaseBankParser ABC
│   ├── utils.py                # parse_amount(), parse_date(), IST timezone
│   ├── detector.py             # detect_parser(content) → BaseBankParser
│   ├── hdfc_card.py
│   ├── hdfc_bank_txt.py
│   ├── icici_card.py
│   ├── icici_bank.py
│   ├── amex_card.py
│   ├── axis_bank.py
│   ├── axis_card.py
│   ├── sbi_bank.py
│   └── sbi_card.py
├── pipeline/
│   └── deduplicator.py         # pre-check fingerprints, return new/duplicate split
├── tests/
│   ├── fixtures/               # copied from FinanceOS/Packages/FinanceParsers/Tests/Fixtures/
│   │   ├── hdfc_card.csv
│   │   ├── hdfc_bank.txt
│   │   ├── icici_card.csv
│   │   ├── icici_bank.csv
│   │   └── amex_card.csv
│   ├── test_hdfc_card.py
│   ├── test_hdfc_bank_txt.py
│   ├── test_icici.py
│   ├── test_amex.py
│   ├── test_axis_sbi.py
│   └── test_detector.py
├── main.py                     # add /parse and /import routes
└── database.py                 # existing
```

---

### Task 1: Schemas + base parser

**Files:**
- Create: `python_service/models/__init__.py`
- Create: `python_service/models/schemas.py`
- Create: `python_service/parsers/__init__.py`
- Create: `python_service/parsers/base.py`
- Create: `python_service/parsers/utils.py`

- [ ] **Step 1: Create `python_service/models/__init__.py`** (empty)

- [ ] **Step 2: Create `python_service/models/schemas.py`**

```python
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class ParsedTransaction:
    posted_at: datetime
    description: str
    amount_minor_units: int   # positive = debit (money out), negative = credit (money in)
    currency_code: str
    source_fingerprint: str
    reward_points: int | None = None
    closing_balance_minor_units: int | None = None
    statement_row_index: int | None = None


@dataclass
class ImportRequest:
    ledger_id: str
    transactions: list[ParsedTransaction]


@dataclass
class ImportResult:
    imported: int
    duplicates: int
    errors: list[str] = field(default_factory=list)
```

- [ ] **Step 3: Create `python_service/parsers/__init__.py`** (empty)

- [ ] **Step 4: Create `python_service/parsers/utils.py`**

```python
from datetime import datetime, timezone, timedelta

# All Indian bank dates are in IST (UTC+5:30)
IST = timezone(timedelta(hours=5, minutes=30))


def parse_amount(s: str) -> int | None:
    """Convert bank amount string to paise (amount × 100). Returns None if unparseable."""
    cleaned = s.strip().replace("₹", "").replace(",", "").strip()
    if not cleaned:
        return None
    try:
        return int(round(float(cleaned) * 100))
    except ValueError:
        return None


def parse_date(s: str, *fmts: str) -> datetime | None:
    """Try each format in order; return first successful parse in IST, or None."""
    stripped = s.strip()
    for fmt in fmts:
        try:
            return datetime.strptime(stripped, fmt).replace(tzinfo=IST)
        except ValueError:
            continue
    return None
```

- [ ] **Step 5: Create `python_service/parsers/base.py`**

```python
from abc import ABC, abstractmethod
from models.schemas import ParsedTransaction


class BaseBankParser(ABC):
    bank_code: str  # unique identifier, e.g. "hdfc_card"

    @abstractmethod
    def detect(self, content: bytes) -> bool:
        """Return True if this parser can handle the given file content."""

    @abstractmethod
    def parse(self, content: bytes) -> list[ParsedTransaction]:
        """Parse file content and return list of transactions."""
```

- [ ] **Step 6: Write test to verify imports work**

```python
# tests/test_schemas.py
from models.schemas import ParsedTransaction, ImportResult
from parsers.base import BaseBankParser
from parsers.utils import parse_amount, parse_date
from datetime import datetime, timezone, timedelta

def test_parse_amount_basic():
    assert parse_amount("350.00") == 35000
    assert parse_amount("1,200.50") == 120050
    assert parse_amount("₹649.00") == 64900
    assert parse_amount("") is None
    assert parse_amount("abc") is None

def test_parse_amount_negative():
    assert parse_amount("-649.00") == -64900

def test_parse_date_single_fmt():
    IST = timezone(timedelta(hours=5, minutes=30))
    result = parse_date("01/04/2026", "%d/%m/%Y")
    assert result is not None
    assert result.day == 1 and result.month == 4 and result.year == 2026
    assert result.tzinfo == IST

def test_parse_date_fallback():
    result = parse_date("01/04/26", "%d/%m/%Y", "%d/%m/%y")
    assert result is not None
    assert result.day == 1
```

- [ ] **Step 7: Run tests**

```bash
cd python_service
source .venv/bin/activate
pip install pytest
pytest tests/test_schemas.py -v
```

Expected: 4 tests pass.

- [ ] **Step 8: Commit**

```bash
git add python_service/models/ python_service/parsers/base.py python_service/parsers/utils.py python_service/parsers/__init__.py
git add python_service/tests/test_schemas.py
git commit -m "feat: add ParsedTransaction schema, BaseBankParser ABC, and amount/date utils"
```

---

### Task 2: Copy fixtures + HDFC Card parser

**Files:**
- Create: `python_service/tests/fixtures/` (copied from iOS repo)
- Create: `python_service/parsers/hdfc_card.py`
- Create: `python_service/tests/test_hdfc_card.py`

- [ ] **Step 1: Copy fixtures from iOS repo**

```bash
mkdir -p python_service/tests/fixtures
cp ../FinanceOS/Packages/FinanceParsers/Tests/Fixtures/hdfc_card.csv python_service/tests/fixtures/
cp ../FinanceOS/Packages/FinanceParsers/Tests/Fixtures/hdfc_bank.txt python_service/tests/fixtures/
cp ../FinanceOS/Packages/FinanceParsers/Tests/Fixtures/icici_card.csv python_service/tests/fixtures/
cp ../FinanceOS/Packages/FinanceParsers/Tests/Fixtures/icici_bank.csv python_service/tests/fixtures/
cp ../FinanceOS/Packages/FinanceParsers/Tests/Fixtures/amex_card.csv python_service/tests/fixtures/
```

- [ ] **Step 2: Write failing test first**

```python
# python_service/tests/test_hdfc_card.py
import pathlib
import pytest
from parsers.hdfc_card import HDFCCardParser

FIXTURE = pathlib.Path(__file__).parent / "fixtures" / "hdfc_card.csv"

def test_detect():
    content = FIXTURE.read_bytes()
    assert HDFCCardParser().detect(content) is True

def test_parse_returns_transactions():
    content = FIXTURE.read_bytes()
    txns = HDFCCardParser().parse(content)
    assert len(txns) == 4  # 4 data rows in fixture

def test_parse_first_transaction():
    txns = HDFCCardParser().parse(FIXTURE.read_bytes())
    t = txns[0]
    assert t.description == "Swiggy Order"
    assert t.amount_minor_units == 35000  # 350.00 debit = positive
    assert t.currency_code == "INR"
    assert "Swiggy Order" in t.source_fingerprint

def test_parse_credit_is_negative():
    txns = HDFCCardParser().parse(FIXTURE.read_bytes())
    # Third row: "Refund - Flipkart" with Cr sign
    refund = next(t for t in txns if "Refund" in t.description)
    assert refund.amount_minor_units == -50000  # 500.00 credit = negative

def test_fingerprint_format():
    txns = HDFCCardParser().parse(FIXTURE.read_bytes())
    t = txns[0]
    # Format: "{dateStr}|{description}|{absAmountMinorUnits}"
    parts = t.source_fingerprint.split("|")
    assert len(parts) == 3
    assert parts[1] == t.description
```

- [ ] **Step 3: Run failing test**

```bash
cd python_service
pytest tests/test_hdfc_card.py -v
```

Expected: `ImportError` (module not found).

- [ ] **Step 4: Create `python_service/parsers/hdfc_card.py`**

```python
from datetime import datetime
from models.schemas import ParsedTransaction
from parsers.base import BaseBankParser
from parsers.utils import IST, parse_amount, parse_date


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
```

- [ ] **Step 5: Run tests — expect pass**

```bash
pytest tests/test_hdfc_card.py -v
```

Expected: 5 tests pass.

- [ ] **Step 6: Commit**

```bash
git add python_service/parsers/hdfc_card.py python_service/tests/
git commit -m "feat: add HDFCCardParser with fixture tests"
```

---

### Task 3: HDFC Bank TXT parser

**Files:**
- Create: `python_service/parsers/hdfc_bank_txt.py`
- Create: `python_service/tests/test_hdfc_bank_txt.py`

- [ ] **Step 1: Write failing test**

```python
# python_service/tests/test_hdfc_bank_txt.py
import pathlib
from parsers.hdfc_bank_txt import HDFCBankTXTParser

FIXTURE = pathlib.Path(__file__).parent / "fixtures" / "hdfc_bank.txt"

def test_detect():
    content = FIXTURE.read_bytes()
    assert HDFCBankTXTParser().detect(content) is True

def test_parse_returns_transactions():
    txns = HDFCBankTXTParser().parse(FIXTURE.read_bytes())
    assert len(txns) == 4  # fixture has 4 data rows

def test_debit_is_positive():
    txns = HDFCBankTXTParser().parse(FIXTURE.read_bytes())
    debit = next(t for t in txns if "Grocery" in t.description)
    assert debit.amount_minor_units == 50000  # 500.00 debit

def test_credit_is_negative():
    txns = HDFCBankTXTParser().parse(FIXTURE.read_bytes())
    credit = next(t for t in txns if "Salary" in t.description)
    assert credit.amount_minor_units == -5000000  # 50000.00 credit

def test_fingerprint_has_no_spaces_in_desc():
    txns = HDFCBankTXTParser().parse(FIXTURE.read_bytes())
    t = txns[0]
    parts = t.source_fingerprint.split("|")
    # fpDesc: whitespace stripped from description (no spaces between words)
    assert " " not in parts[1]
```

- [ ] **Step 2: Run — expect ImportError**

```bash
pytest tests/test_hdfc_bank_txt.py -v
```

- [ ] **Step 3: Create `python_service/parsers/hdfc_bank_txt.py`**

```python
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
            # Normalise: collapse whitespace for display, remove for fingerprint
            desc = " ".join(desc_raw.split())
            fp_desc = "".join(desc.split())

            # Column variants: "debit amount" / "withdrawal amt." etc.
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
```

- [ ] **Step 4: Run tests — expect pass**

```bash
pytest tests/test_hdfc_bank_txt.py -v
```

Expected: 5 tests pass.

- [ ] **Step 5: Commit**

```bash
git add python_service/parsers/hdfc_bank_txt.py python_service/tests/test_hdfc_bank_txt.py
git commit -m "feat: add HDFCBankTXTParser with fixture tests"
```

---

### Task 4: ICICI Card + ICICI Bank parsers

**Files:**
- Create: `python_service/parsers/icici_card.py`
- Create: `python_service/parsers/icici_bank.py`
- Create: `python_service/tests/test_icici.py`

- [ ] **Step 1: Write failing tests**

```python
# python_service/tests/test_icici.py
import pathlib
from parsers.icici_card import ICICICardParser
from parsers.icici_bank import ICICIBankParser

CARD_FIXTURE = pathlib.Path(__file__).parent / "fixtures" / "icici_card.csv"
BANK_FIXTURE = pathlib.Path(__file__).parent / "fixtures" / "icici_bank.csv"

# --- ICICI Card ---
def test_icici_card_detect():
    assert ICICICardParser().detect(CARD_FIXTURE.read_bytes()) is True

def test_icici_card_does_not_detect_bank():
    assert ICICICardParser().detect(BANK_FIXTURE.read_bytes()) is False

def test_icici_card_parse():
    txns = ICICICardParser().parse(CARD_FIXTURE.read_bytes())
    assert len(txns) > 0
    assert txns[0].currency_code == "INR"

def test_icici_card_credit_negative():
    txns = ICICICardParser().parse(CARD_FIXTURE.read_bytes())
    credits = [t for t in txns if t.amount_minor_units < 0]
    assert len(credits) > 0

# --- ICICI Bank ---
def test_icici_bank_detect():
    assert ICICIBankParser().detect(BANK_FIXTURE.read_bytes()) is True

def test_icici_bank_parse():
    txns = ICICIBankParser().parse(BANK_FIXTURE.read_bytes())
    assert len(txns) > 0

def test_icici_bank_credit_negative():
    txns = ICICIBankParser().parse(BANK_FIXTURE.read_bytes())
    credits = [t for t in txns if t.amount_minor_units < 0]
    assert len(credits) > 0
```

- [ ] **Step 2: Run — expect ImportError**

```bash
pytest tests/test_icici.py -v
```

- [ ] **Step 3: Create `python_service/parsers/icici_card.py`**

```python
import csv, io
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
        desc_key = next((k for k in col if "description" in k or "particulars" in k), None)
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
```

- [ ] **Step 4: Create `python_service/parsers/icici_bank.py`**

```python
import csv, io
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
```

- [ ] **Step 5: Run tests — expect pass**

```bash
pytest tests/test_icici.py -v
```

- [ ] **Step 6: Commit**

```bash
git add python_service/parsers/icici_card.py python_service/parsers/icici_bank.py python_service/tests/test_icici.py
git commit -m "feat: add ICICICardParser and ICICIBankParser with fixture tests"
```

---

### Task 5: Amex + Axis parsers

**Files:**
- Create: `python_service/parsers/amex_card.py`
- Create: `python_service/parsers/axis_bank.py`
- Create: `python_service/parsers/axis_card.py`
- Create: `python_service/tests/test_amex.py`
- Create: `python_service/tests/test_axis_sbi.py` (partial — Axis portion)

- [ ] **Step 1: Write failing Amex test**

```python
# python_service/tests/test_amex.py
import pathlib
from parsers.amex_card import AmexCardParser

FIXTURE = pathlib.Path(__file__).parent / "fixtures" / "amex_card.csv"

def test_detect():
    assert AmexCardParser().detect(FIXTURE.read_bytes()) is True

def test_parse():
    txns = AmexCardParser().parse(FIXTURE.read_bytes())
    assert len(txns) == 4

def test_refund_negative():
    txns = AmexCardParser().parse(FIXTURE.read_bytes())
    refund = next(t for t in txns if "Netflix" in t.description)
    assert refund.amount_minor_units < 0  # -649.00 → -64900

def test_date_format_mm_dd_yyyy():
    txns = AmexCardParser().parse(FIXTURE.read_bytes())
    # Fixture: 04/01/2026 = April 1 (MM/dd/yyyy)
    assert txns[0].posted_at.month == 4
    assert txns[0].posted_at.day == 1
```

- [ ] **Step 2: Create `python_service/parsers/amex_card.py`**

```python
import csv, io
from models.schemas import ParsedTransaction
from parsers.base import BaseBankParser
from parsers.utils import parse_amount, parse_date


class AmexCardParser(BaseBankParser):
    bank_code = "amex_card"

    def detect(self, content: bytes) -> bool:
        text = content.decode("utf-8", errors="ignore")
        reader = csv.reader(io.StringIO(text))
        rows = list(reader)
        if not rows:
            return False
        header = [c.lower().strip() for c in rows[0]]
        return (len(header) == 3
                and "date" in header
                and "description" in header
                and "amount" in header)

    def parse(self, content: bytes) -> list[ParsedTransaction]:
        text = content.decode("utf-8", errors="ignore")
        reader = csv.reader(io.StringIO(text))
        rows = list(reader)
        if len(rows) < 2:
            return []

        header = [c.lower().strip() for c in rows[0]]
        col = {h: i for i, h in enumerate(header)}

        results: list[ParsedTransaction] = []
        for i, row in enumerate(rows[1:]):
            if len(row) < 3:
                continue
            date_str = row[col["date"]].strip()
            date = parse_date(date_str, "%m/%d/%Y")
            if not date:
                continue
            amt = parse_amount(row[col["amount"]])
            if amt is None:
                continue
            desc = row[col["description"]].strip()
            fingerprint = f"{date_str}|{desc}|{amt}"
            results.append(ParsedTransaction(
                posted_at=date, description=desc, amount_minor_units=amt,
                currency_code="INR", source_fingerprint=fingerprint, statement_row_index=i,
            ))
        return results
```

- [ ] **Step 3: Create `python_service/parsers/axis_bank.py`**

```python
import csv, io
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
            if ("tran. date" in lower or "transaction date" in lower) and \
               "description" in lower and \
               ("deposit" in lower or "credit" in lower) and \
               ("withdrawal" in lower or "debit" in lower):
                return True
        return False

    def parse(self, content: bytes) -> list[ParsedTransaction]:
        text = content.decode("utf-8", errors="ignore")
        reader = csv.reader(io.StringIO(text))
        rows = list(reader)

        header_idx = None
        for i, row in enumerate(rows):
            lower = [c.lower().strip() for c in row]
            if ("tran. date" in lower or "transaction date" in lower) and \
               "description" in lower and \
               (("deposit" in lower or "credit" in lower) and
                ("withdrawal" in lower or "debit" in lower)):
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
            credit = parse_amount(row[col[credit_key]]) or 0 if credit_key and col[credit_key] < len(row) else 0
            debit = parse_amount(row[col[debit_key]]) or 0 if debit_key and col[debit_key] < len(row) else 0
            if credit == 0 and debit == 0:
                continue
            amount = -credit if credit > 0 else debit
            fingerprint = f"{date_str}|{desc}|{credit}|{debit}"
            closing = parse_amount(row[col[balance_key]]) if balance_key and col[balance_key] < len(row) else None
            results.append(ParsedTransaction(
                posted_at=date, description=desc, amount_minor_units=amount,
                currency_code="INR", source_fingerprint=fingerprint,
                closing_balance_minor_units=closing, statement_row_index=i,
            ))
        return results
```

- [ ] **Step 4: Create `python_service/parsers/axis_card.py`**

```python
import csv, io
from models.schemas import ParsedTransaction
from parsers.base import BaseBankParser
from parsers.utils import parse_amount, parse_date


class AxisCardParser(BaseBankParser):
    bank_code = "axis_card"

    def detect(self, content: bytes) -> bool:
        text = content.decode("utf-8", errors="ignore")
        reader = csv.reader(io.StringIO(text))
        for row in reader:
            lower = [c.lower().strip() for c in row]
            # Axis Card: "transaction date" (not "tran. date") + description + amount/debit
            # Exclude Axis Bank signal (which has both deposit AND withdrawal columns)
            has_txn_date = "transaction date" in lower
            has_desc = "description" in lower
            has_amount = "amount" in lower or "debit" in lower
            has_bank_signals = ("deposit" in lower or "credit" in lower) and ("withdrawal" in lower)
            if has_txn_date and has_desc and has_amount and not has_bank_signals:
                return True
        return False

    def parse(self, content: bytes) -> list[ParsedTransaction]:
        text = content.decode("utf-8", errors="ignore")
        reader = csv.reader(io.StringIO(text))
        rows = list(reader)

        header_idx = None
        for i, row in enumerate(rows):
            lower = [c.lower().strip() for c in row]
            if "transaction date" in lower and "description" in lower and \
               ("amount" in lower or "debit" in lower):
                header_idx = i
                break
        if header_idx is None:
            return []

        header = [c.lower().strip() for c in rows[header_idx]]
        col = {h: i for i, h in enumerate(header)}
        date_key = "transaction date"
        desc_key = next((k for k in col if k == "description"), None)
        credit_key = next((k for k in col if k in ("credit", "deposit")), None)
        debit_key = next((k for k in col if k in ("debit", "amount")), None)

        results: list[ParsedTransaction] = []
        for i, row in enumerate(rows[header_idx + 1:]):
            if not row or row[0].strip().upper().startswith("CLOSING"):
                continue
            date_str = row[col[date_key]].strip()
            date = parse_date(date_str, "%d/%m/%Y", "%d-%b-%Y")
            if not date:
                continue
            desc = row[col[desc_key]].strip() if desc_key else ""
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
```

- [ ] **Step 5: Run Amex tests**

```bash
pytest tests/test_amex.py -v
```

Expected: 4 tests pass.

- [ ] **Step 6: Commit**

```bash
git add python_service/parsers/amex_card.py python_service/parsers/axis_bank.py python_service/parsers/axis_card.py python_service/tests/test_amex.py
git commit -m "feat: add AmexCardParser, AxisBankParser, AxisCardParser"
```

---

### Task 6: SBI parsers

**Files:**
- Create: `python_service/parsers/sbi_bank.py`
- Create: `python_service/parsers/sbi_card.py`

- [ ] **Step 1: Create `python_service/parsers/sbi_bank.py`**

```python
import csv, io
from models.schemas import ParsedTransaction
from parsers.base import BaseBankParser
from parsers.utils import parse_amount, parse_date


class SBIBankParser(BaseBankParser):
    bank_code = "sbi_bank"

    def detect(self, content: bytes) -> bool:
        text = content.decode("utf-8", errors="ignore")
        reader = csv.reader(io.StringIO(text))
        for row in reader:
            lower = [c.lower().strip() for c in row]
            if ("value date" in lower or "date" in lower) and \
               ("description" in lower or "narration" in lower) and \
               ("debit" in lower or "credit" in lower):
                return True
        return False

    def parse(self, content: bytes) -> list[ParsedTransaction]:
        text = content.decode("utf-8", errors="ignore")
        reader = csv.reader(io.StringIO(text))
        rows = list(reader)

        header_idx = None
        for i, row in enumerate(rows):
            lower = [c.lower().strip() for c in row]
            if ("value date" in lower or "date" in lower) and \
               ("description" in lower or "narration" in lower) and \
               ("debit" in lower or "credit" in lower):
                header_idx = i
                break
        if header_idx is None:
            return []

        header = [c.lower().strip() for c in rows[header_idx]]
        col = {h: i for i, h in enumerate(header)}
        date_key = next((k for k in col if k in ("value date", "date")), None)
        desc_key = next((k for k in col if k in ("description", "narration")), None)
        credit_key = next((k for k in col if k == "credit"), None)
        debit_key = next((k for k in col if k == "debit"), None)
        balance_key = next((k for k in col if "balance" in k), None)

        results: list[ParsedTransaction] = []
        for i, row in enumerate(rows[header_idx + 1:]):
            if not row or row[0].strip().lower().startswith("closing"):
                continue
            date_str = row[col[date_key]].strip() if date_key else ""
            date = parse_date(date_str, "%d/%m/%Y", "%d-%b-%Y")
            if not date:
                continue
            desc = row[col[desc_key]].strip() if desc_key else ""
            credit = parse_amount(row[col[credit_key]]) or 0 if credit_key and col[credit_key] < len(row) else 0
            debit = parse_amount(row[col[debit_key]]) or 0 if debit_key and col[debit_key] < len(row) else 0
            if credit == 0 and debit == 0:
                continue
            amount = -credit if credit > 0 else debit
            fingerprint = f"{date_str}|{desc}|{credit}|{debit}"
            closing = parse_amount(row[col[balance_key]]) if balance_key and col[balance_key] < len(row) else None
            results.append(ParsedTransaction(
                posted_at=date, description=desc, amount_minor_units=amount,
                currency_code="INR", source_fingerprint=fingerprint,
                closing_balance_minor_units=closing, statement_row_index=i,
            ))
        return results
```

- [ ] **Step 2: Create `python_service/parsers/sbi_card.py`**

```python
import csv, io
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
            if "transaction date" in lower and "description" in lower and \
               ("amount" in lower or "debit" in lower) and \
               "value date" not in lower:  # exclude SBI Bank
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
```

- [ ] **Step 3: Run all parser tests**

```bash
pytest tests/ -v --ignore=tests/test_detector.py
```

Expected: All tests pass.

- [ ] **Step 4: Commit**

```bash
git add python_service/parsers/sbi_bank.py python_service/parsers/sbi_card.py
git commit -m "feat: add SBIBankParser and SBICardParser"
```

---

### Task 7: Format detector

**Files:**
- Create: `python_service/parsers/detector.py`
- Create: `python_service/tests/test_detector.py`

- [ ] **Step 1: Write failing test**

```python
# python_service/tests/test_detector.py
import pathlib
from parsers.detector import detect_parser
from parsers.hdfc_card import HDFCCardParser
from parsers.hdfc_bank_txt import HDFCBankTXTParser
from parsers.icici_card import ICICICardParser
from parsers.icici_bank import ICICIBankParser
from parsers.amex_card import AmexCardParser

FIXTURES = pathlib.Path(__file__).parent / "fixtures"

def test_detect_hdfc_card():
    content = (FIXTURES / "hdfc_card.csv").read_bytes()
    assert isinstance(detect_parser(content), HDFCCardParser)

def test_detect_hdfc_bank():
    content = (FIXTURES / "hdfc_bank.txt").read_bytes()
    assert isinstance(detect_parser(content), HDFCBankTXTParser)

def test_detect_icici_card():
    content = (FIXTURES / "icici_card.csv").read_bytes()
    assert isinstance(detect_parser(content), ICICICardParser)

def test_detect_icici_bank():
    content = (FIXTURES / "icici_bank.csv").read_bytes()
    assert isinstance(detect_parser(content), ICICIBankParser)

def test_detect_amex():
    content = (FIXTURES / "amex_card.csv").read_bytes()
    assert isinstance(detect_parser(content), AmexCardParser)

def test_detect_unknown_returns_none():
    assert detect_parser(b"random,data,here\n1,2,3") is None
```

- [ ] **Step 2: Run — expect ImportError**

```bash
pytest tests/test_detector.py -v
```

- [ ] **Step 3: Create `python_service/parsers/detector.py`**

```python
from parsers.base import BaseBankParser
from parsers.hdfc_card import HDFCCardParser
from parsers.hdfc_bank_txt import HDFCBankTXTParser
from parsers.icici_card import ICICICardParser
from parsers.icici_bank import ICICIBankParser
from parsers.amex_card import AmexCardParser
from parsers.axis_bank import AxisBankParser
from parsers.axis_card import AxisCardParser
from parsers.sbi_card import SBICardParser
from parsers.sbi_bank import SBIBankParser

# Order matters: more specific detectors first to avoid false positives
_PARSERS: list[BaseBankParser] = [
    HDFCCardParser(),      # unique: ~|~ + Card No:
    HDFCBankTXTParser(),   # unique: narration + closing balance
    ICICICardParser(),     # unique: billingamountsign
    ICICIBankParser(),     # unique: particulars + deposits + withdrawals
    AmexCardParser(),      # unique: exactly 3 cols Date/Description/Amount
    AxisBankParser(),      # unique: tran. date (Axis Bank only)
    SBICardParser(),       # transaction date (no value date)
    AxisCardParser(),      # transaction date (no deposit+withdrawal pair)
    SBIBankParser(),       # most generic: value date / date
]

_BY_CODE: dict[str, BaseBankParser] = {p.bank_code: p for p in _PARSERS}


def detect_parser(content: bytes, bank_code: str | None = None) -> BaseBankParser | None:
    """Return the appropriate parser. If bank_code given, use it directly."""
    if bank_code and bank_code in _BY_CODE:
        return _BY_CODE[bank_code]
    for parser in _PARSERS:
        if parser.detect(content):
            return parser
    return None
```

- [ ] **Step 4: Run tests — expect pass**

```bash
pytest tests/test_detector.py -v
```

Expected: 6 tests pass.

- [ ] **Step 5: Run full test suite**

```bash
pytest tests/ -v
```

Expected: All tests pass.

- [ ] **Step 6: Commit**

```bash
git add python_service/parsers/detector.py python_service/tests/test_detector.py
git commit -m "feat: add format detector with ordered parser chain"
```

---

### Task 8: Deduplicator + `/parse` endpoint

**Files:**
- Create: `python_service/pipeline/__init__.py`
- Create: `python_service/pipeline/deduplicator.py`
- Modify: `python_service/main.py`

- [ ] **Step 1: Create `python_service/pipeline/__init__.py`** (empty)

- [ ] **Step 2: Create `python_service/pipeline/deduplicator.py`**

```python
import asyncpg
from models.schemas import ParsedTransaction


async def split_new_and_duplicates(
    pool: asyncpg.Pool,
    ledger_id: str,
    transactions: list[ParsedTransaction],
) -> tuple[list[ParsedTransaction], int]:
    """Return (new_transactions, duplicate_count). Checks existing fingerprints in Postgres."""
    if not transactions:
        return [], 0

    fingerprints = [t.source_fingerprint for t in transactions]
    existing = await pool.fetch(
        'SELECT "sourceFingerprint" FROM "Transaction" WHERE "ledgerId" = $1 AND "sourceFingerprint" = ANY($2)',
        ledger_id,
        fingerprints,
    )
    existing_set = {row["sourceFingerprint"] for row in existing}
    new_txns = [t for t in transactions if t.source_fingerprint not in existing_set]
    return new_txns, len(transactions) - len(new_txns)


async def bulk_insert(pool: asyncpg.Pool, ledger_id: str, transactions: list[ParsedTransaction]) -> list[str]:
    """Insert transactions. Returns list of error strings for failed rows."""
    if not transactions:
        return []

    errors: list[str] = []
    async with pool.acquire() as conn:
        for t in transactions:
            try:
                await conn.execute(
                    """
                    INSERT INTO "Transaction" (id, date, narration, amount, "ledgerId", category, merchant, "sourceFingerprint", "createdAt")
                    VALUES (gen_random_uuid(), $1, $2, $3, $4, NULL, NULL, $5, NOW())
                    ON CONFLICT ("ledgerId", "sourceFingerprint") DO NOTHING
                    """,
                    t.posted_at,
                    t.description,
                    t.amount_minor_units / 100.0,  # store as decimal (rupees)
                    ledger_id,
                    t.source_fingerprint,
                )
            except Exception as e:
                errors.append(f"Row {t.statement_row_index}: {e}")
    return errors
```

- [ ] **Step 3: Add `/parse` and `/import` routes to `python_service/main.py`**

Replace the existing `main.py` content:

```python
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from database import close_pool, get_pool
from models.schemas import ImportResult
from parsers.detector import detect_parser
from pipeline.deduplicator import bulk_insert, split_new_and_duplicates


@asynccontextmanager
async def lifespan(app: FastAPI):
    await get_pool()
    yield
    await close_pool()


app = FastAPI(title="FinanceOS Parser Service", version="0.2.0", lifespan=lifespan)


@app.get("/health")
async def health():
    pool = await get_pool()
    await pool.fetchval("SELECT 1")
    return {"status": "ok", "db": "connected"}


@app.post("/parse")
async def parse_file(
    file: UploadFile = File(...),
    bank_code: str | None = Form(default=None),
):
    """Auto-detect or use bank_code to parse a statement file. Returns ParsedTransaction list."""
    content = await file.read()
    parser = detect_parser(content, bank_code)
    if parser is None:
        raise HTTPException(status_code=422, detail="Unrecognised statement format. Provide bank_code.")

    transactions = parser.parse(content)
    return {
        "bank_code": parser.bank_code,
        "count": len(transactions),
        "transactions": [
            {
                "postedAt": t.posted_at.isoformat(),
                "description": t.description,
                "amountMinorUnits": t.amount_minor_units,
                "currencyCode": t.currency_code,
                "sourceFingerprint": t.source_fingerprint,
                "rewardPoints": t.reward_points,
                "closingBalanceMinorUnits": t.closing_balance_minor_units,
                "statementRowIndex": t.statement_row_index,
            }
            for t in transactions
        ],
    }


class ImportBody(BaseModel):
    ledger_id: str
    bank_code: str | None = None
    transactions: list[dict]


@app.post("/import")
async def import_transactions(body: ImportBody):
    """Dedup and persist transactions to Postgres. Returns ImportResult counts."""
    from models.schemas import ParsedTransaction
    from datetime import datetime, timezone, timedelta

    IST = timezone(timedelta(hours=5, minutes=30))

    parsed = []
    for t in body.transactions:
        posted_at = datetime.fromisoformat(t["postedAt"]) if isinstance(t["postedAt"], str) else t["postedAt"]
        if posted_at.tzinfo is None:
            posted_at = posted_at.replace(tzinfo=IST)
        parsed.append(ParsedTransaction(
            posted_at=posted_at,
            description=t["description"],
            amount_minor_units=t["amountMinorUnits"],
            currency_code=t.get("currencyCode", "INR"),
            source_fingerprint=t["sourceFingerprint"],
        ))

    pool = await get_pool()
    new_txns, duplicates = await split_new_and_duplicates(pool, body.ledger_id, parsed)
    errors = await bulk_insert(pool, body.ledger_id, new_txns)

    return {
        "imported": len(new_txns) - len(errors),
        "duplicates": duplicates,
        "errors": errors,
    }
```

- [ ] **Step 4: Restart Python service and smoke test `/parse`**

```bash
# From repo root:
docker compose restart python-parser
# Or locally:
cd python_service && uvicorn main:app --reload
```

```bash
curl -X POST http://localhost:8000/parse \
  -F "file=@../FinanceOS/Packages/FinanceParsers/Tests/Fixtures/hdfc_card.csv"
```

Expected: JSON with `bank_code: "hdfc_card"`, `count: 4`, and transaction list.

- [ ] **Step 5: Run full test suite**

```bash
pytest tests/ -v
```

Expected: All tests pass.

- [ ] **Step 6: Commit**

```bash
git add python_service/pipeline/ python_service/main.py
git commit -m "feat: add /parse and /import endpoints with deduplication pipeline"
```
