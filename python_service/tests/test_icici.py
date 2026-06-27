import pathlib
from parsers.icici_card import ICICICardParser
from parsers.icici_bank import ICICIBankParser

CARD_FIXTURE = pathlib.Path(__file__).parent / "fixtures" / "icici_card.csv"
BANK_FIXTURE = pathlib.Path(__file__).parent / "fixtures" / "icici_bank.csv"


def test_icici_card_detect():
    assert ICICICardParser().detect(CARD_FIXTURE.read_bytes()) is True


def test_icici_card_does_not_detect_bank():
    assert ICICICardParser().detect(BANK_FIXTURE.read_bytes()) is False


def test_icici_card_parse():
    txns = ICICICardParser().parse(CARD_FIXTURE.read_bytes())
    assert len(txns) == 4
    assert txns[0].currency_code == "INR"


def test_icici_card_credit_negative():
    txns = ICICICardParser().parse(CARD_FIXTURE.read_bytes())
    credits = [t for t in txns if t.amount_minor_units < 0]
    assert len(credits) == 1  # only "Refund Flipkart"


def test_icici_bank_detect():
    assert ICICIBankParser().detect(BANK_FIXTURE.read_bytes()) is True


def test_icici_bank_parse():
    txns = ICICIBankParser().parse(BANK_FIXTURE.read_bytes())
    assert len(txns) == 4


def test_icici_bank_credit_negative():
    txns = ICICIBankParser().parse(BANK_FIXTURE.read_bytes())
    credits = [t for t in txns if t.amount_minor_units < 0]
    assert len(credits) == 2  # Salary + Refund Credit deposits
