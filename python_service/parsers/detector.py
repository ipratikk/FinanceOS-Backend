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
