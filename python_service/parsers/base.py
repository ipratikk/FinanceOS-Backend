from abc import ABC, abstractmethod
from models.schemas import ParsedTransaction


class BaseBankParser(ABC):
    bank_code: str  # unique identifier, e.g. "hdfc_card"

    @abstractmethod
    def detect(self, content: bytes) -> bool:
        """Return True if this parser can handle the given file content."""

    @abstractmethod
    def parse(self, content: bytes) -> list[ParsedTransaction]:
        """Parse file content and return list of transactions."""
