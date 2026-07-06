import io
from contextlib import contextmanager
from typing import Iterator

from pdfminer.pdfdocument import PDFPasswordIncorrect
from pdfplumber.utils.exceptions import PdfminerException


@contextmanager
def open_pdf(content: bytes, password: str | None = None) -> Iterator["pdfplumber.PDF"]:  # noqa: F821
    """Opens `content` with pdfplumber, normalizing its PdfminerException wrapper
    back into a plain PDFPasswordIncorrect when that's the underlying cause.

    pdfplumber wraps ALL exceptions from pdfminer (malformed PDFs, wrong/missing
    password, anything else) in its own PdfminerException, with the original
    exception as `e.args[0]`. Every parser in this codebase wants to treat
    "wrong/missing password" as a distinct, specific outcome (`PDFPasswordIncorrect`)
    from "this isn't a PDF this parser understands" (generic `Exception` → return
    False) — this helper is the one place that does the unwrapping so every
    parser's `except PDFPasswordIncorrect:` clause actually fires.
    """
    import pdfplumber

    try:
        with pdfplumber.open(io.BytesIO(content), password=password or "") as pdf:
            yield pdf
    except PdfminerException as e:
        if e.args and isinstance(e.args[0], PDFPasswordIncorrect):
            raise PDFPasswordIncorrect() from e
        raise
