import pathlib
from parse_service import build_parse_response

FIXTURES = pathlib.Path(__file__).parent / "fixtures"
LOCKED_PDF = (FIXTURES / "hdfc_bank_pdf_locked.pdf").read_bytes()


def test_password_required_when_none_given():
    result = build_parse_response(LOCKED_PDF)
    assert result["password_required"] is True
    assert result["bank_code"] == ""
    assert result["transactions"] == []


def test_password_required_when_wrong():
    result = build_parse_response(LOCKED_PDF, password="wrongpassword")
    assert result["password_required"] is True


def test_succeeds_with_correct_password():
    result = build_parse_response(LOCKED_PDF, password="secret123")
    assert result["password_required"] is False
    assert result["bank_code"] == "hdfc_bank_pdf"


def test_unrecognized_format_returns_none():
    assert build_parse_response(b"random,data,here\n1,2,3") is None


def test_recognized_unencrypted_file_unchanged():
    content = (FIXTURES / "hdfc_card.csv").read_bytes()
    result = build_parse_response(content)
    assert result["password_required"] is False
    assert result["bank_code"] == "hdfc_card"
