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
    assert len(txns) == 4


def test_parse_first_transaction():
    txns = HDFCCardParser().parse(FIXTURE.read_bytes())
    t = txns[0]
    assert t.description == "Swiggy Order"
    assert t.amount_minor_units == 35000  # 350.00 debit = positive
    assert t.currency_code == "INR"
    assert "Swiggy Order" in t.source_fingerprint


def test_parse_credit_is_negative():
    txns = HDFCCardParser().parse(FIXTURE.read_bytes())
    refund = next(t for t in txns if "Refund" in t.description)
    assert refund.amount_minor_units == -50000  # 500.00 credit = negative


def test_fingerprint_format():
    txns = HDFCCardParser().parse(FIXTURE.read_bytes())
    t = txns[0]
    parts = t.source_fingerprint.split("|")
    assert len(parts) == 3
    assert parts[1] == t.description
