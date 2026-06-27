import pathlib
from parsers.hdfc_bank_txt import HDFCBankTXTParser

FIXTURE = pathlib.Path(__file__).parent / "fixtures" / "hdfc_bank.txt"


def test_detect():
    content = FIXTURE.read_bytes()
    assert HDFCBankTXTParser().detect(content) is True


def test_parse_returns_transactions():
    txns = HDFCBankTXTParser().parse(FIXTURE.read_bytes())
    assert len(txns) == 4


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
    # fp_desc has all whitespace removed
    assert " " not in parts[1]
