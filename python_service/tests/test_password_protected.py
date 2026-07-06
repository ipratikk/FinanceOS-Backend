import pathlib
import pytest
from pdfminer.pdfdocument import PDFPasswordIncorrect
from parsers.base import BaseBankParser
from parsers.detector import detect_parser
from parsers.hdfc_bank_pdf import HDFCBankPDFParser

FIXTURES = pathlib.Path(__file__).parent / "fixtures"
LOCKED_PDF = (FIXTURES / "hdfc_bank_pdf_locked.pdf").read_bytes()


def test_detect_raises_password_incorrect_with_no_password():
    with pytest.raises(PDFPasswordIncorrect):
        HDFCBankPDFParser().detect(LOCKED_PDF)


def test_detect_raises_password_incorrect_with_wrong_password():
    with pytest.raises(PDFPasswordIncorrect):
        HDFCBankPDFParser().detect(LOCKED_PDF, password="wrongpassword")


def test_detect_succeeds_with_correct_password():
    assert HDFCBankPDFParser().detect(LOCKED_PDF, password="secret123") is True


def test_detector_raises_password_incorrect_for_locked_pdf():
    with pytest.raises(PDFPasswordIncorrect):
        detect_parser(LOCKED_PDF)


def test_detector_finds_parser_with_correct_password():
    parser = detect_parser(LOCKED_PDF, password="secret123")
    assert isinstance(parser, HDFCBankPDFParser)


def test_csv_parsers_ignore_password_param():
    # Mechanical signature check: every parser accepts (and can ignore) `password`.
    content = (FIXTURES / "hdfc_card.csv").read_bytes()
    from parsers.hdfc_card import HDFCCardParser
    assert HDFCCardParser().detect(content, password="irrelevant") is True


def test_open_pdf_unwraps_password_incorrect():
    from parsers.pdf_utils import open_pdf
    with pytest.raises(PDFPasswordIncorrect):
        with open_pdf(LOCKED_PDF):
            pass


def test_open_pdf_succeeds_with_correct_password():
    from parsers.pdf_utils import open_pdf
    with open_pdf(LOCKED_PDF, password="secret123") as pdf:
        text = pdf.pages[0].extract_text() or ""
    assert "WithdrawalAmt." in text
