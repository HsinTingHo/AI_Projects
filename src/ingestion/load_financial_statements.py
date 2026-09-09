#!/usr/bin/env python3

"""
Parse a PDF annual report into retrieval-friendly chunks.

Chunking rules
--------------
1. Narrative:
   - ~400-700 tokens
   - never intentionally crosses a detected section/subsection boundary

2. Risk factors:
   - one individual risk/subsection per chunk
   - preserves all paragraphs belonging to that risk

3. Financial tables:
   - table-aware chunks
   - table rows/columns are kept together
   - large tables can be split by row groups

4. Footnotes:
   - table footnotes are attached to their corresponding table
   - standalone footnotes remain attached to the nearest preceding content

Metadata on every chunk
-----------------------
document
year
section
subsection
page
content_type
table_name

Output
------
JSONL, one chunk per line.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Optional

import fitz # PyMuPDF
import pdfplumber
import requests

try:
    import tiktoken

    ENCODER = tiktoken.get_encoding("cl100k_base")
except Exception:
    ENCODER = None


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DEFAULT_URL = (
    "s26.q4cdn.com/747928648/…/ar"
    "American-Express-Annual-Report-2025.pdf"
)

DOCUMENT_NAME = "American Express Annual Report 2025"
REPORT_YEAR = 2025

MIN_NARRATIVE_TOKENS = 400
TARGET_NARRATIVE_TOKENS = 550
MAX_NARRATIVE_TOKENS = 700

# Used to decide whether text immediately below a table is likely a footnote.
FOOTNOTE_LOOKAHEAD_PT = 130

# Approximate maximum number of table rows in one table chunk.
MAX_TABLE_ROWS = 80


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass
class TextBlock:
    page: int
    text: str
    x0: float
    y0: float
    x1: float
    y1: float
    font_size: float = 0.0
    bold: bool = False


@dataclass
class TableInfo:
    page: int
    bbox: tuple[float, float, float, float]
    rows: list[list[str]]
    name: str = ""


@dataclass
class Chunk:
    document: str
    year: int
    section: str
    subsection: str
    page: int | str
    content_type: str
    table_name: str
    text: str
    token_count: int


# ---------------------------------------------------------------------------
# Token helpers
# ---------------------------------------------------------------------------

def token_count(text: str) -> int:
    """Count tokens using tiktoken when available, otherwise approximate."""
    if ENCODER is not None:
        return len(ENCODER.encode(text))

    # Reasonable fallback for environments without tiktoken.
    # English annual reports are roughly 1.3 tokens/word.
    words = re.findall(r"\S+", text)
    return int(math.ceil(len(words) * 1.3))


def split_by_tokens(
    text: str,
    min_tokens: int = MIN_NARRATIVE_TOKENS,
    target_tokens: int = TARGET_NARRATIVE_TOKENS,
    max_tokens: int = MAX_NARRATIVE_TOKENS,
) -> list[str]:
    """
    Split prose without splitting sentences unless a single sentence is too
    large.

    The target is ~550 tokens with a hard upper bound near 700.
    """
    paragraphs = [
        p.strip()
        for p in re.split(r"\n\s*\n", text)
        if p.strip()
    ]

    if not paragraphs:
        return []

    chunks: list[str] = []
    current: list[str] = []
    current_tokens = 0

    def flush() -> None:
        nonlocal current, current_tokens
        if current:
            chunks.append("\n\n".join(current).strip())
            current = []
            current_tokens = 0

    for paragraph in paragraphs:
        p_tokens = token_count(paragraph)

        # Very long paragraph: fall back to sentence-level splitting.
        if p_tokens > max_tokens:
            sentences = re.split(
                r"(?<=[.!?])\s+(?=[A-Z0-9])",
                paragraph
            )

            for sentence in sentences:
                sentence = sentence.strip()
                if not sentence:
                    continue

                s_tokens = token_count(sentence)

                if (
                    current
                    and current_tokens + s_tokens > max_tokens
                ):
                    flush()

                current.append(sentence)
                current_tokens += s_tokens

                if current_tokens >= target_tokens:
                    flush()

            continue

        proposed = current_tokens + p_tokens

        if current and proposed > max_tokens:
            flush()

        current.append(paragraph)
        current_tokens += p_tokens

        # Don't close tiny chunks prematurely.
        if current_tokens >= target_tokens:
            flush()

    flush()

    # Merge tiny tail chunks with the previous chunk where practical.
    if len(chunks) >= 2:
        last_tokens = token_count(chunks[-1])

        if last_tokens < min_tokens:
            candidate = chunks[-2] + "\n\n" + chunks[-1]

            if token_count(candidate) <= max_tokens:
                chunks[-2] = candidate
                chunks.pop()

    return chunks


# ---------------------------------------------------------------------------
# Heading detection
# ---------------------------------------------------------------------------

PART_RE = re.compile(
    r"^\s*PART\s+(I|II|III|IV)\s*$",
    re.IGNORECASE,
)

ITEM_RE = re.compile(
    r"^\s*ITEM\s+(\d+[A-Z]?)\.\s*(.+?)\s*$",
    re.IGNORECASE,
)

NOTE_RE = re.compile(
    r"^\s*NOTE\s+(\d+[A-Z]?)\s*$",
    re.IGNORECASE,
)

TABLE_NAME_RE = re.compile(
    r"^\s*TABLE\s+"
    r"(\d+(?:\.\d+)?)"
    r"\s*:\s*(.+?)\s*$",
    re.IGNORECASE,
)

# Risk category headings in the AmEx report.
RISK_CATEGORY_RE = re.compile(
    r"^\s*(Strategic and Reputational Risks|"
    r"Operational and Compliance Risks|"
    r"Credit, Market and Liquidity Risks)\s*$",
    re.IGNORECASE,
)

# Common financial-statement headings.
FINANCIAL_STATEMENT_RE = re.compile(
    r"^\s*(CONSOLIDATED\s+"
    r"(?:STATEMENTS|BALANCE SHEETS|NOTES|FINANCIAL STATEMENTS|"
    r"CASH FLOWS|COMPREHENSIVE INCOME|SHAREHOLDERS.? EQUITY)|"
    r"NOTES TO CONSOLIDATED FINANCIAL STATEMENTS)\s*$",
    re.IGNORECASE,
)

# Lines that are normally page furniture and should be discarded.
PAGE_NUMBER_RE = re.compile(
    r"^\s*(?:\d+|[ivxlcdm]+|A-\d+)\s*$",
    re.IGNORECASE,
)

# Typical PDF footer artifacts.
FOOTER_RE = re.compile(
    r"^\s*(?:Table of Contents|"
    r"American Express Company|"
    r"American Express Annual Report 2025)\s*$",
    re.IGNORECASE,
)

FOOTNOTE_RE = re.compile(
    r"^\s*(?:"
    r"\([a-z]\)"
    r"|[a-z]\)"
    r"|\([0-9]+\)"
    r"|[0-9]+\)"
    r"|[A-Z]\."
    r")\s+",
    re.IGNORECASE,
)


def normalize_text(text: str) -> str:
    """Normalize common PDF extraction artifacts."""
    text = text.replace("\u00ad", "") # soft hyphen
    text = text.replace("\u2010", "-")
    text = text.replace("\u2011", "-")
    text = text.replace("\u2012", "-")
    text = text.replace("\u2013", "-")
    text = text.replace("\u2014", "-")

    # Fix words broken at line boundaries: "signifi-\ncant" -> "significant".
    text = re.sub(r"(\w)-\s*\n\s*(\w)", r"\1\2", text)

    # Convert remaining newlines inside blocks to spaces.
    text = re.sub(r"[ \t]*\n[ \t]*", " ", text)

    # Collapse whitespace.
    text = re.sub(r"[ \t]+", " ", text)

    return text.strip()


def is_probable_heading(block: TextBlock) -> bool:
    """
    Detect headings using both lexical patterns and PDF typography.
    """
    text = block.text.strip()

    if not text:
        return False

    if PART_RE.match(text):
        return True

    if ITEM_RE.match(text):
        return True

    if NOTE_RE.match(text):
        return True

    if RISK_CATEGORY_RE.match(text):
        return True

    if FINANCIAL_STATEMENT_RE.match(text):
        return True

    if TABLE_NAME_RE.match(text):
        return True

    # Very short bold lines are usually subsection headings.
    if block.bold and len(text) <= 140:
        return True

    # Uppercase headings in SEC filings are often semantic headings.
    letters = re.sub(r"[^A-Za-z]", "", text)
    if (
        len(letters) >= 8
        and letters.upper() == letters
        and len(text) <= 140
    ):
        return True

    return False


def heading_level(text: str, block: TextBlock) -> int:
    """
    Assign an approximate semantic level.

    1 = Part / Item
    2 = major section / Note
    3 = subsection / risk heading
    """
    text_clean = text.strip()

    if PART_RE.match(text_clean):
        return 1

    if ITEM_RE.match(text_clean):
        return 1

    if NOTE_RE.match(text_clean):
        return 2

    if FINANCIAL_STATEMENT_RE.match(text_clean):
        return 2

    if RISK_CATEGORY_RE.match(text_clean):
        return 2

    if TABLE_NAME_RE.match(text_clean):
        return 3

    if block.bold or text_clean.upper() == text_clean:
        return 3

    return 3


# ---------------------------------------------------------------------------
# PDF extraction
# ---------------------------------------------------------------------------

def download_pdf(url: str, output_path: Path) -> None:
    """Download the source PDF."""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (compatible; AnnualReportChunker/1.0)"
        )
    }

    with requests.get(
        url,
        headers=headers,
        timeout=60,
        stream=True,
    ) as response:
        response.raise_for_status()

        content_type = response.headers.get("content-type", "")
        if "pdf" not in content_type.lower():
            print(
                f"Warning: server returned Content-Type={content_type}",
                file=sys.stderr,
            )

        with output_path.open("wb") as f:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    f.write(chunk)


def extract_text_blocks(pdf_path: Path) -> list[TextBlock]:
    """
    Extract reasonably ordered text blocks using PyMuPDF.

    Blocks keep coordinates so tables can later be excluded from normal
    narrative extraction.
    """
    doc = fitz.open(pdf_path)

    all_blocks: list[TextBlock] = []

    for page_index, page in enumerate(doc):
        page_number = page_index + 1

        page_dict = page.get_text(
            "dict",
            flags=fitz.TEXTFLAGS_TEXT,
        )

        raw_blocks = page_dict.get("blocks", [])

        for b in raw_blocks:
            if b.get("type") != 0:
                continue

            lines = b.get("lines", [])
            text_parts: list[str] = []

            sizes: list[float] = []
            bold_count = 0
            span_count = 0

            for line in lines:
                for span in line.get("spans", []):
                    txt = span.get("text", "")
                    if not txt.strip():
                        continue

                    text_parts.append(txt)

                    size = span.get("size", 0.0)
                    sizes.append(size)

                    flags = span.get("flags", 0)
                    # PyMuPDF bit 4 is commonly associated with bold.
                    if flags & 16:
                        bold_count += 1

                    span_count += 1

            raw_text = " ".join(text_parts).strip()

            if not raw_text:
                continue

            normalized = normalize_text(raw_text)

            x0, y0, x1, y1 = b["bbox"]

            all_blocks.append(
                TextBlock(
                    page=page_number,
                    text=normalized,
                    x0=x0,
                    y0=y0,
                    x1=x1,
                    y1=y1,
                    font_size=max(sizes) if sizes else 0.0,
                    bold=(
                        span_count > 0
                        and bold_count / span_count >= 0.5
                    ),
                )
            )

    return all_blocks


# ---------------------------------------------------------------------------
# Table extraction
# ---------------------------------------------------------------------------

def clean_table_cell(value: Any) -> str:
    if value is None:
        return ""

    value = str(value)
    value = normalize_text(value)
    return value


def guess_table_name(rows: list[list[str]]) -> str:
    """
    Infer table title from the first one or two rows.

    Actual AmEx tables generally have a 'TABLE x.x: ...' label immediately
    above them. The caller also attempts to capture that label separately.
    """
    if not rows:
        return ""

    first_row = " ".join(cell for cell in rows[0] if cell).strip()

    if TABLE_NAME_RE.match(first_row):
        match = TABLE_NAME_RE.match(first_row)
        if match:
            return f"TABLE {match.group(1)}: {match.group(2)}"

    return ""


def extract_tables(pdf_path: Path) -> list[TableInfo]:
    """
    Extract tables using pdfplumber.

    Tables are kept separately from prose so financial statements do not get
    destroyed by paragraph-oriented chunking.
    """
    tables: list[TableInfo] = []

    with pdfplumber.open(pdf_path) as pdf:
        for page_number, page in enumerate(pdf.pages, start=1):

            try:
                page_tables = page.find_tables()
            except Exception as exc:
                print(
                    f"Warning: table detection failed on page "
                    f"{page_number}: {exc}",
                    file=sys.stderr,
                )
                continue

            for table_obj in page_tables:
                bbox = tuple(table_obj.bbox)

                try:
                    rows_raw = table_obj.extract()
                except Exception as exc:
                    print(
                        f"Warning: table extraction failed on page "
                        f"{page_number}: {exc}",
                        file=sys.stderr,
                    )
                    continue

                if not rows_raw:
                    continue

                rows = [
                    [clean_table_cell(cell) for cell in row]
                    for row in rows_raw
                ]

                # Remove completely empty rows.
                rows = [
                    row for row in rows
                    if any(cell.strip() for cell in row)
                ]

                if not rows:
                    continue

                tables.append(
                    TableInfo(
                        page=page_number,
                        bbox=bbox,
                        rows=rows,
                        name=guess_table_name(rows),
                    )
                )

    return tables


def block_inside_table(
    block: TextBlock,
    table: TableInfo,
    tolerance: float = 3.0,
) -> bool:
    """Return True when a text block overlaps the table bounding box."""
    tx0, ty0, tx1, ty1 = table.bbox

    horizontal_overlap = (
        block.x0 < tx1 + tolerance
        and block.x1 > tx0 - tolerance
    )

    vertical_overlap = (
        block.y0 < ty1 + tolerance
        and block.y1 > ty0 - tolerance
    )

    return horizontal_overlap and vertical_overlap


def table_to_markdown(table: TableInfo) -> str:
    """
    Convert extracted rows into a compact table representation.

    A markdown representation is convenient for downstream LLM/RAG use while
    preserving row/column relationships.
    """
    rows = table.rows

    if not rows:
        return ""

    max_cols = max(len(r) for r in rows)

    padded = [
        r + [""] * (max_cols - len(r))
        for r in rows
    ]

    header = padded[0]

    out = [
        "| " + " | ".join(header) + " |",
        "| " + " | ".join("---" for _ in header) + " |",
    ]

    for row in padded[1:]:
        out.append("| " + " | ".join(row) + " |")

    return "\n".join(out)


# ---------------------------------------------------------------------------
# Financial/report hierarchy
# ---------------------------------------------------------------------------

def clean_heading_text(text: str) -> str:
    """
    Turn 'ITEM 1A. RISK FACTORS' into a useful semantic label.
    """
    text = text.strip()

    match = ITEM_RE.match(text)
    if match:
        return match.group(2).strip()

    match = PART_RE.match(text)
    if match:
        return f"PART {match.group(1).upper()}"

    return text


def is_risk_section(section: str) -> bool:
    normalized = re.sub(r"[^a-z0-9]+", " ", section.lower()).strip()
    return normalized == "risk factors"


def is_risk_heading_candidate(block: TextBlock) -> bool:
    """
    Identify an individual risk heading.

    In this report, risk descriptions are formatted as standalone sentences
    followed by explanatory paragraphs. A simple typography+sentence heuristic
    works better than requiring title case.
    """
    text = block.text.strip()

    if not text:
        return False

    if RISK_CATEGORY_RE.match(text):
        return False

    if is_probable_heading(block):
        return True

    # Risk headings frequently end with a period and occupy a single block.
    if (
        len(text) <= 300
        and text.endswith(".")
        and block.bold
    ):
        return True

    return False


# ---------------------------------------------------------------------------
# Footnotes
# ---------------------------------------------------------------------------

def looks_like_footnote(text: str) -> bool:
    text = text.strip()

    if not text:
        return False

    # Typical SEC annual-report note forms: (a), (b), 1), etc.
    if FOOTNOTE_RE.match(text):
        return True

    # Sometimes PDF extraction loses the parenthesis.
    if re.match(r"^[a-z]\s+", text, re.IGNORECASE):
        return len(text) > 20

    return False


def find_nearest_table(
    block: TextBlock,
    tables_by_page: dict[int, list[TableInfo]],
) -> Optional[TableInfo]:
    """
    Find the table immediately above a likely footnote.
    """
    candidates = tables_by_page.get(block.page, [])

    best: Optional[TableInfo] = None
    best_distance = float("inf")

    for table in candidates:
        _, ty0, _, ty1 = table.bbox

        # Footnote should be below the table, not above it.
        if block.y0 >= ty1:
            distance = block.y0 - ty1

            if distance <= FOOTNOTE_LOOKAHEAD_PT and distance < best_distance:
                best = table
                best_distance = distance

    return best


# ---------------------------------------------------------------------------
# Main chunk builder
# ---------------------------------------------------------------------------

class ReportChunker:
    def __init__(
        self,
        pdf_path: Path,
        document: str = DOCUMENT_NAME,
        year: int = REPORT_YEAR,
    ):
        self.pdf_path = pdf_path
        self.document = document
        self.year = year

        self.blocks = extract_text_blocks(pdf_path)
        self.tables = extract_tables(pdf_path)

        self.tables_by_page: dict[int, list[TableInfo]] = {}
        for table in self.tables:
            self.tables_by_page.setdefault(table.page, []).append(table)

        self.blocks_by_page: dict[int, list[TextBlock]] = {}
        for block in self.blocks:
            self.blocks_by_page.setdefault(block.page, []).append(block)

        # Sort in reading order.
        for blocks in self.blocks_by_page.values():
            blocks.sort(key=lambda b: (b.y0, b.x0))

        self.chunks: list[Chunk] = []

    def build(self) -> list[Chunk]:
        current_section = ""
        current_subsection = ""

        # Track table footnotes for later attachment.
        table_footnotes: dict[int, list[str]] = {}

        # Track text accumulated for narrative chunks.
        narrative_parts: list[str] = []
        narrative_pages: list[int] = []

        def flush_narrative() -> None:
            nonlocal narrative_parts, narrative_pages

            if not narrative_parts:
                return

            text = "\n\n".join(narrative_parts).strip()

            if not text:
                narrative_parts = []
                narrative_pages = []
                return

            pieces = split_by_tokens(text)

            for piece in pieces:
                self.chunks.append(
                    Chunk(
                        document=self.document,
                        year=self.year,
                        section=current_section,
                        subsection=current_subsection,
                        page=(
                            narrative_pages[0]
                            if len(set(narrative_pages)) == 1
                            else f"{min(narrative_pages)}-{max(narrative_pages)}"
                        ),
                        content_type="risk" if is_risk_section(current_section) else "narrative",
                        table_name="",
                        text=piece,
                        token_count=token_count(piece),
                    )
                )

            narrative_parts = []
            narrative_pages = []

        # First pass: process page by page.
        for page_number in sorted(self.blocks_by_page):
            blocks = self.blocks_by_page[page_number]

            for block in blocks:
                text = block.text.strip()

                if not text:
                    continue

                # Strip common page artifacts.
                if PAGE_NUMBER_RE.match(text):
                    continue

                if FOOTER_RE.match(text):
                    continue

                # Do not feed table text into narrative extraction.
                containing_table = None
                for table in self.tables_by_page.get(page_number, []):
                    if block_inside_table(block, table):
                        containing_table = table
                        break

                if containing_table is not None:
                    continue

                # Detect table-name labels.
                table_match = TABLE_NAME_RE.match(text)
                if table_match:
                    flush_narrative()
                    current_subsection = clean_heading_text(text)
                    continue

                # Detect hierarchy headings.
                if is_probable_heading(block):
                    # Risk headings need special handling because each risk
                    # becomes an independent chunk.
                    if is_risk_section(current_section):
                        if (
                            is_risk_heading_candidate(block)
                            and not RISK_CATEGORY_RE.match(text)
                        ):
                            flush_narrative()
                            current_subsection = text
                            continue

                    level = heading_level(text, block)
                    flush_narrative()

                    heading = clean_heading_text(text)

                    if level <= 1:
                        current_section = heading
                        current_subsection = ""

                    elif level == 2:
                        current_section = (
                            current_section
                            if current_section
                            and not ITEM_RE.match(text)
                            else heading
                        )
                        if ITEM_RE.match(text) or NOTE_RE.match(text):
                            current_section = heading

                        current_subsection = ""

                    else:
                        current_subsection = heading

                    continue

                # Detect footnote candidates.
                if looks_like_footnote(text):
                    nearest_table = find_nearest_table(
                        block,
                        self.tables_by_page,
                    )

                    if nearest_table is not None:
                        table_id = id(nearest_table)
                        table_footnotes.setdefault(
                            table_id,
                            []
                        ).append(text)
                        continue

                narrative_parts.append(text)
                narrative_pages.append(page_number)

                # Risk chunks are handled by looking ahead for the next
                # risk heading. We therefore don't close them just based
                # on token count.
                if not is_risk_section(current_section):
                    current_tokens = token_count(
                        "\n\n".join(narrative_parts)
                    )

                    if current_tokens >= TARGET_NARRATIVE_TOKENS:
                        flush_narrative()

        flush_narrative()

        # Add financial tables as separate chunks.
        table_chunks = self.build_table_chunks(table_footnotes)

        # Re-sort by page while retaining natural chunk order.
        combined = self.chunks + table_chunks

        # Sort tables and narrative by first page, with tables following
        # the surrounding prose on the same page.
        combined.sort(
            key=lambda c: (
                self.page_start(c.page),
                1 if c.content_type == "table" else 0,
            )
        )

        # Re-numbering isn't necessary, but keep deterministic order.
        self.chunks = combined

        return self.chunks

    @staticmethod
    def page_start(page: int | str) -> int:
        if isinstance(page, int):
            return page

        match = re.match(r"(\d+)", str(page))
        return int(match.group(1)) if match else 0

    def build_table_chunks(
        self,
        table_footnotes: dict[int, list[str]],
    ) -> list[Chunk]:
        output: list[Chunk] = []

        for table in self.tables:
            # Find the closest semantic context from text above the table.
            section, subsection = self.context_before_table(table)

            table_name = table.name

            # Search nearby page text for a "TABLE x.x: ..." label.
            if not table_name:
                table_name = self.find_table_label(table)

            markdown = table_to_markdown(table)

            footnotes = table_footnotes.get(id(table), [])
            if footnotes:
                markdown += "\n\nFootnotes:\n"
                markdown += "\n".join(
                    f"- {note}" for note in footnotes
                )

            rows = table.rows

            # Keep small tables intact.
            if len(rows) <= MAX_TABLE_ROWS:
                output.append(
                    Chunk(
                        document=self.document,
                        year=self.year,
                        section=section,
                        subsection=subsection,
                        page=table.page,
                        content_type="table",
                        table_name=table_name,
                        text=markdown,
                        token_count=token_count(markdown),
                    )
                )
                continue

            # Split very large tables by row groups while retaining the
            # header on each chunk.
            header = rows[0]
            data_rows = rows[1:]

            for start in range(0, len(data_rows), MAX_TABLE_ROWS):
                row_group = [header] + data_rows[
                    start:start + MAX_TABLE_ROWS
                ]

                temp_table = TableInfo(
                    page=table.page,
                    bbox=table.bbox,
                    rows=row_group,
                    name=table_name,
                )

                chunk_text = table_to_markdown(temp_table)

                if start == 0 and footnotes:
                    chunk_text += "\n\nFootnotes:\n"
                    chunk_text += "\n".join(
                        f"- {note}" for note in footnotes
                    )

                output.append(
                    Chunk(
                        document=self.document,
                        year=self.year,
                        section=section,
                        subsection=subsection,
                        page=table.page,
                        content_type="table",
                        table_name=table_name,
                        text=chunk_text,
                        token_count=token_count(chunk_text),
                    )
                )

        return output

    def context_before_table(
        self,
        table: TableInfo,
    ) -> tuple[str, str]:
        """
        Find semantic context by inspecting text blocks above the table.
        """
        blocks = self.blocks_by_page.get(table.page, [])

        relevant = [
            b for b in blocks
            if b.y1 <= table.bbox[1] + 5
        ]

        relevant.sort(key=lambda b: (b.y0, b.x0))

        section = ""
        subsection = ""

        for block in relevant[-20:]:
            text = block.text.strip()

            if not is_probable_heading(block):
                continue

            if ITEM_RE.match(text) or PART_RE.match(text):
                section = clean_heading_text(text)
                subsection = ""

            elif NOTE_RE.match(text):
                section = text
                subsection = ""

            elif RISK_CATEGORY_RE.match(text):
                subsection = text

            else:
                subsection = text

        return section, subsection

    def find_table_label(self, table: TableInfo) -> str:
        """
        Look immediately above a detected table for:
            TABLE 2.1: CARD MEMBER AND OTHER LOANS
        """
        blocks = self.blocks_by_page.get(table.page, [])

        candidates = [
            b for b in blocks
            if b.y1 <= table.bbox[1] + 10
            and b.y1 >= table.bbox[1] - 80
        ]

        candidates.sort(key=lambda b: b.y0, reverse=True)

        for block in candidates:
            match = TABLE_NAME_RE.match(block.text.strip())
            if match:
                return f"TABLE {match.group(1)}: {match.group(2)}"

        return ""


# ---------------------------------------------------------------------------
# Serialization
# ---------------------------------------------------------------------------

def chunk_to_dict(chunk: Chunk, chunk_id: int) -> dict[str, Any]:
    return {
        "chunk_id": chunk_id,
        "metadata": {
            "document": chunk.document,
            "year": chunk.year,
            "section": chunk.section,
            "subsection": chunk.subsection,
            "page": chunk.page,
            "content_type": chunk.content_type,
            "table_name": chunk.table_name,
        },
        "text": chunk.text,
        "token_count": chunk.token_count,
    }


def write_jsonl(
    chunks: list[Chunk],
    output_path: Path,
) -> None:
    with output_path.open(
        "w",
        encoding="utf-8",
    ) as f:
        for idx, chunk in enumerate(chunks, start=1):
            obj = chunk_to_dict(chunk, idx)
            f.write(
                json.dumps(
                    obj,
                    ensure_ascii=False,
                )
                + "\n"
            )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Chunk an annual-report PDF for RAG/vector search."
    )

    parser.add_argument(
        "--url",
        default=DEFAULT_URL,
        help="PDF URL",
    )

    parser.add_argument(
        "--pdf",
        default="/Users/eva/Desktop/Projects/AI_Project/resources/corpus/originals/financialStatement/American-Express-Annual-Report-2025.pdf",
        help="Local PDF path",
    )

    parser.add_argument(
        "--output",
        default="/Users/eva/Desktop/Projects/AI_Project/resources/corpus/american_express_2025_chunks.jsonl",
        help="Output JSONL path",
    )

    parser.add_argument(
        "--no-download",
        action="store_true",
        help="Use --pdf as an existing local PDF instead of downloading.",
    )

    return parser.parse_args()


def main() -> int:
    args = parse_args()

    pdf_path = Path(args.pdf)
    output_path = Path(args.output)

    if not args.no_download:
        print(f"Downloading PDF -> {pdf_path}")
        download_pdf(args.url, pdf_path)

    if not pdf_path.exists():
        print(
            f"ERROR: PDF not found: {pdf_path}",
            file=sys.stderr,
        )
        return 1

    print("Extracting and chunking...")
    chunker = ReportChunker(
        pdf_path=pdf_path,
        document=DOCUMENT_NAME,
        year=REPORT_YEAR,
    )

    chunks = chunker.build()

    print(f"Writing {len(chunks)} chunks -> {output_path}")
    write_jsonl(chunks, output_path)

    # Small validation summary.
    content_types: dict[str, int] = {}

    for chunk in chunks:
        content_types[chunk.content_type] = (
            content_types.get(chunk.content_type, 0) + 1
        )

    print("\nChunk summary:")
    for content_type, count in sorted(content_types.items()):
        print(f" {content_type:12s}: {count}")

    risk_chunks = [
        c for c in chunks
        if c.content_type == "risk"
    ]

    print(f" risk chunks : {len(risk_chunks)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())