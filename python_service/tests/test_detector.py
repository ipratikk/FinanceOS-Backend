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
