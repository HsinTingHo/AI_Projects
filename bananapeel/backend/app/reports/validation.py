"""Screen PDF content for financial-statement relevance before storage.

This module is independent of FastAPI. The router interprets the result and
decides whether to accept the upload or return an actionable HTTP error.
"""
from fastapi import UploadFile
from dataclasses import dataclass
from typing import BinaryIO, Literal

import pymupdf
import re


FinancialDocumentOutcome = Literal[
    "likely_financial", "likely_unrelated", "undetermined"
]


@dataclass(frozen=True)
class FinancialDocumentCheck:
    outcome: FinancialDocumentOutcome
    reasons: list[str]


def inspect_financial_document(source: BinaryIO) -> FinancialDocumentCheck:
    """Inspect a readable, seekable PDF stream without closing it.

    This synchronous function should run in a worker thread from an async route.
    The caller must rewind the stream before saving the upload.
    A relevance result does not establish document authenticity.
    """
    try:
        source.seek(0)
        pdf_bytes = source.read()
        with pymupdf.open(stream=pdf_bytes, filetype="pdf") as doc:
            patterns = {
                "balance_sheet": re.compile(r"consolidated\s+(?:financial\s+)?position|balance\s+sheet", re.IGNORECASE),
                "income_statement": re.compile(r"consolidated\s+statements?\s+of\s+(?:operations|income|earnings|loss)", re.IGNORECASE),
                "cash_flow": re.compile(r"consolidated\s+statements?\s+of\s+cash\s+flows", re.IGNORECASE)
            }

            date_pattern = re.compile(r"(?:ended|as\s+of)\s+(?:december|march|june|september|\d{2}/\d{2})|20\d{2}", re.IGNORECASE)
            detected = {k: False for k in patterns}

            for page_num in range(len(doc)):
                page = doc[page_num]
                text = page.get_text("text")
                if not text:
                    continue
                # 1. Structural Check using PyMuPDF metrics
                total_chars = len(text)
                digits_count = sum(c.isdigit() for c in text)
                digit_density = digits_count / total_chars if total_chars > 0 else 0

                has_dates = bool(date_pattern.search(text))

                # Target pages that look like heavy financial grids
                if digit_density > 0.08 and has_dates:
                    for statement_type, regex in patterns.items():
                        if not detected[statement_type] and regex.search(text):
                            detected[statement_type] = True
                # Early exit optimization: Stop parsing the moment all three are found
                if all(detected.values()):
                    break

            
            if all(detected.values()):
                return FinancialDocumentCheck(outcome="likely_financial", reasons=["All three key financial statements detected."])
            elif any(detected.values()):
                detected_statements = [k for k, v in detected.items() if v]
                return FinancialDocumentCheck(
                    outcome="likely_financial",
                    reasons=[f"Detected statements: {', '.join(detected_statements)}."]
                )
            else:
                return FinancialDocumentCheck(
                    outcome="likely_unrelated",
                    reasons=["No key financial statements detected."]
                )

    except (pymupdf.EmptyFileError, pymupdf.FileDataError) as e:
        return FinancialDocumentCheck(
            outcome="undetermined",
            reasons=[f"PDF is empty or unreadable. Error: {str(e)}"]
        )
    except Exception as e:
        return FinancialDocumentCheck(
            outcome="undetermined",
            reasons=[f"Error during PDF inspection: {str(e)}"]
        )

async def is_file_pdf(file: UploadFile) -> bool:
    PDF_MAGIC_NUMBER = b"%PDF-"
    header = await file.read(5)  # Read the first 5 bytes to check for PDF magic number
    await file.seek(0)  # Reset the file pointer to the beginning after reading
    return header == PDF_MAGIC_NUMBER

def is_file_size_valid(file: UploadFile, max_size_mb: int = 25) -> bool:
    if file.size is not None and file.size > max_size_mb * 1024 * 1024:  # Convert MB to bytes
        return False
    return True