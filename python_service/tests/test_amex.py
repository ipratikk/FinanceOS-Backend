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
    # 04/01/2026 = April 1 (MM/DD/YYYY format)
    assert txns[0].posted_at.month == 4
    assert txns[0].posted_at.day == 1
