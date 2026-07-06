from pdfminer.pdfdocument import PDFPasswordIncorrect
from parsers.detector import detect_parser


def build_parse_response(
    content: bytes, bank_code: str | None = None, password: str | None = None
) -> dict | None:
    """Detect and parse a statement. Returns None if no parser recognizes the
    format at all (caller should raise a 422). Returns a password-required
    response dict (never None) if the file is an encrypted PDF and the given
    password (or lack of one) didn't open it.
    """
    try:
        parser = detect_parser(content, bank_code, password)
    except PDFPasswordIncorrect:
        return _password_required_response()

    if parser is None:
        return None

    try:
        transactions = parser.parse(content, password=password)
    except PDFPasswordIncorrect:
        return _password_required_response()

    return {
        "bank_code": parser.bank_code,
        "count": len(transactions),
        "last4": parser.extract_last4(content),
        "password_required": False,
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


def _password_required_response() -> dict:
    return {
        "bank_code": "",
        "count": 0,
        "last4": None,
        "password_required": True,
        "transactions": [],
    }
