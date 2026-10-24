"""Report upload orchestration."""
import asyncio
import logging
import re
from typing import Any
import uuid

import psycopg
from fastapi import HTTPException, UploadFile
from starlette.concurrency import run_in_threadpool

from app.storage.base import ReportStorage
from app.reports.repository import ReportRepository

logger = logging.getLogger(__name__)
METADATA_ATTEMPTS = 3
RETRY_DELAY_SECONDS = 0.2


async def upload_report(
    file: UploadFile, storage: ReportStorage, repository: ReportRepository,
) -> dict[str, Any]:
    report_id = str(uuid.uuid4())
    metadata = extract_report_metadata(file)
    metadata["id"] = report_id
    name = sanitize_report_name(str(metadata["report_year"] or ""), metadata["filename"])
    key = f"reports/{report_id}/{name}.pdf"
    await file.seek(0)
    print(f"[upload.service] report_id={report_id} Saving PDF via {type(storage).__name__}", flush=True)
    try:
        await run_in_threadpool(storage.save, key, file.file)
    except Exception as error:
        print(f"[upload.service] report_id={report_id} Storage failed: {type(error).__name__}", flush=True)
        raise
    print(f"[upload.service] report_id={report_id} PDF saved", flush=True)

    try:
        for attempt in range(METADATA_ATTEMPTS):
            try:
                print(f"[upload.service] report_id={report_id} Metadata attempt {attempt + 1}/{METADATA_ATTEMPTS}", flush=True)
                result = await repository.save_report_metadata(metadata, key)
                print(f"[upload.service] report_id={report_id} Metadata committed", flush=True)
                return result
            except (psycopg.errors.SerializationFailure, psycopg.errors.DeadlockDetected):
                print(f"[upload.service] report_id={report_id} Transaction conflict", flush=True)
                if attempt == METADATA_ATTEMPTS - 1:
                    raise
                print(f"[upload.service] Retry in {RETRY_DELAY_SECONDS * 2 ** attempt}s", flush=True)
                await asyncio.sleep(RETRY_DELAY_SECONDS * 2 ** attempt)
    except (psycopg.OperationalError, psycopg.InterfaceError) as error:
        # These may mean COMMIT succeeded but its acknowledgement was lost.
        # Transaction-aborted errors above have a known outcome and can be cleaned up.
        if not isinstance(error, (psycopg.errors.SerializationFailure, psycopg.errors.DeadlockDetected)):
            print(f"[upload.service] report_id={report_id} Commit uncertain; retaining PDF", flush=True)
            logger.exception("Metadata outcome uncertain; retain report %s at %s", report_id, key)
            raise HTTPException(503, "Report save could not be confirmed. Please contact support.") from error
        print(f"[upload.service] report_id={report_id} Metadata failed; cleaning up PDF", flush=True)
        await _cleanup(storage, key)
        raise HTTPException(503, "Could not save report metadata after three attempts.") from error
    except Exception as error:
        print(f"[upload.service] report_id={report_id} Metadata failed; cleaning up PDF", flush=True)
        await _cleanup(storage, key)
        raise HTTPException(500, "Could not save report metadata.") from error
    raise RuntimeError("Metadata retry loop finished without a result")


async def _cleanup(storage: ReportStorage, key: str) -> None:
    try:
        print(f"[upload.cleanup] report_id={key.split('/')[1]} Deleting PDF", flush=True)
        await run_in_threadpool(storage.delete, key)
        print("[upload.cleanup] PDF deleted", flush=True)
    except Exception:
        print("[upload.cleanup] Delete failed; see exception log", flush=True)
        # Preserve the original upload error and record the key for later cleanup.
        logger.exception("Failed to remove orphaned report at %s", key)


def extract_report_metadata(file: UploadFile) -> dict:
    return {
        "filename": file.filename or "report.pdf",
        "file_size_bytes": file.size,
        "report_type": "pdf",
        "sha256": None,
        "status": "queued",
        "report_year": int(year) if (year := extract_report_year(file.filename)) else None,
    }


def extract_report_year(filename: str) -> str:
    if not filename:
        return ""
    match = re.search(r"(?<!\d)(19|20)\d{2}(?!\d)", filename)
    return match.group(0) if match else ""

COMMON_WORDS = {
    "report", "reports", "annual", "earnings", "financial", "fiscal",
    "quarter", "q", "pdf"
}

def sanitize_report_name(year: str, filename: str) -> str:
    name = filename.lower()
    name = re.sub(r"\.[^.]+$", "", name)  # remove extension
    name = re.sub(r"[^a-z0-9]+", " ", name)  # normalize separators
    tokens = [t for t in name.split() if t]

    q = ""

    # find quarter
    for i, token in enumerate(tokens):
        if re.fullmatch(r"q[1-4]", token):
            q = token
            break
        if token == "quarter" and i + 1 < len(tokens):
            nxt = tokens[i + 1]
            if re.fullmatch(r"[1-4]", nxt):
                q = f"q{nxt}"
                break

    # company = everything except year and q and known filler words
    company_tokens = []
    for i, token in enumerate(tokens):
        if token == q or token == year:
            continue
        if token in COMMON_WORDS:
            continue
        company_tokens.append(token)

    company = "_".join(company_tokens).strip("_")
    if not company:
        company = "report"

    if q:
        return f"{company}_{year}_{q}"
    return f"{company}_{year}"