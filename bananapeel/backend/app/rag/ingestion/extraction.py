"""Extract page text from a PDF for the chunking stage.

Storage downloads belong in the ingestion service. This module receives a
readable, seekable binary stream and returns page records in memory.
"""

from dataclasses import dataclass
from typing import BinaryIO

import pymupdf

#need to add table, header extraction logic
@dataclass(frozen=True)
class ExtractedPage:
    page_number: int  # One-based PDF page position, used for citations.
    text: str


class ExtractionError(Exception):
    """The PDF cannot be extracted or requires unsupported processing."""


def extract_pages(source: BinaryIO) -> list[ExtractedPage]:
    """Extract pages in PDF order without closing the caller's stream.

    Preserve original page numbers even when a page has no readable text.
    This is synchronous; the ingestion runner should execute it appropriately.
    OCR and chunking are separate concerns.
    """
    original_position = source.tell()
    try:
        source.seek(0)
        pdf_bytes = source.read()
        with pymupdf.open(stream=pdf_bytes, filetype="pdf") as document:
            if document.needs_pass:
                raise ExtractionError("Please provide a PDF without password protection.")
            result = []
            for page_number, page in enumerate(document, start=1):
                text = page.get_text("text")
                if not text:
                    continue
                result.append(ExtractedPage(page_number=page_number, text=text))
            if not result:
                raise ExtractionError("The PDF has no readable text; it may require OCR.")
            return result
          
    except pymupdf.FileDataError as error:
        # EmptyFileError is also a FileDataError.
        raise ExtractionError("The PDF is empty, damaged, or unreadable.") from error
    finally:
        source.seek(original_position)
