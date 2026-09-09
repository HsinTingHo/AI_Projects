from __future__ import annotations

import re
from pathlib import Path

from bs4 import BeautifulSoup, Comment

try:
    from pypdf import PdfReader
except ImportError:  # pragma: no cover
    PdfReader = None


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CORPUS_DIR = PROJECT_ROOT / "resources" / "corpus"


def get_original_directory() -> Path:
    """Return the available raw-corpus folder while supporting both common names."""
    requested_path = CORPUS_DIR / "original"
    existing_path = CORPUS_DIR / "originals/financialStatement" 
    return requested_path if requested_path.exists() else existing_path


def clean_html(html: str) -> str:
    """Remove page chrome and normalize visible HTML text for reliable chunking."""
    soup = BeautifulSoup(html, "html.parser")
    for element in soup(["script", "style", "noscript", "svg", "iframe", "footer", "nav", "aside"]):
        element.decompose()
    for comment in soup.find_all(string=lambda value: isinstance(value, Comment)):
        comment.extract()

    content = soup.find("main") or soup.find("article") or soup.body or soup
    text = content.get_text("\n", strip=True)
    lines = (re.sub(r"\s+", " ", line).strip() for line in text.splitlines())
    return "\n".join(line for line in lines if line)


def clean_pdf(path: Path) -> str:
    """Extract readable text from a PDF file and normalize it for chunking."""
    if PdfReader is None:
        raise ImportError("pypdf is required to process PDF files. Install it with: pip install pypdf")

    reader = PdfReader(str(path))
    print("Processing Metadata:", reader.metadata)
    pages = []
    for page in reader.pages:
        text = page.extract_text() or ""
        pages.append(text)
    return "\n".join(pages).strip()


def clean_document_file(source_path: Path) -> str:
    """Clean a document based on its file extension."""
    suffix = source_path.suffix.lower()

    if suffix in {".html", ".htm"}:
        return clean_html(source_path.read_text(encoding="utf-8", errors="ignore"))
    if suffix == ".pdf":
        return clean_pdf(source_path)
    raise ValueError(f"Unsupported file type: {source_path}")


def output_filename(source_path: Path) -> str:
    """Create a stable text filename from an HTML source filename."""
    safe_name = re.sub(r"[^A-Za-z0-9._-]+", "_", source_path.stem).strip("._")
    return f"{safe_name or 'document'}.txt"


def clean_documents(source_dir: Path | None = None, output_dir: Path | None = None) -> list[Path]:
    """Clean every HTML/PDF posting and write chunking-ready text files to disk."""
    source_dir = source_dir or get_original_directory()
    output_dir = output_dir or CORPUS_DIR / "cleaned"
    if not source_dir.exists():
        raise FileNotFoundError(f"Original corpus directory does not exist: {source_dir}")

    output_dir.mkdir(parents=True, exist_ok=True)
    cleaned_paths: list[Path] = []
   
    for source_path in sorted(source_dir.iterdir()):
        if source_path.suffix.lower() not in {".htm", ".html", ".pdf"}:
            continue

        cleaned_path = output_dir / output_filename(source_path)
        if cleaned_path.exists():
            continue

        cleaned_text = clean_document_file(source_path)
        if not cleaned_text:
            continue
       
        cleaned_path.write_text(cleaned_text + "\n", encoding="utf-8")
        cleaned_paths.append(cleaned_path)
    return cleaned_paths


def main() -> None:
    """Run HTML/PDF cleaning from the command line and report its result."""
    cleaned_paths = clean_documents()
    print(f"Cleaned {len(cleaned_paths)} document(s) into {CORPUS_DIR / 'cleaned'}")


if __name__ == "__main__":
    main()
