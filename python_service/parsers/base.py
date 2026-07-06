from abc import ABC, abstractmethod
from models.schemas import ParsedTransaction


class BaseBankParser(ABC):
    bank_code: str  # unique identifier, e.g. "hdfc_card"

    @abstractmethod
    def detect(self, content: bytes, password: str | None = None) -> bool:
        """Return True if this parser can handle the given file content.

        Raises pdfminer.pdfdocument.PDFPasswordIncorrect if the content is an
        encrypted PDF and `password` is missing or wrong.
        """

    @abstractmethod
    def parse(self, content: bytes, password: str | None = None) -> list[ParsedTransaction]:
        """Parse file content and return list of transactions."""

    def extract_last4(self, content: bytes) -> str | None:
        """Return the last 4 digits of the card/account number, if present in the statement."""
        return None
