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
