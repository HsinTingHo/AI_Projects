# connect to DB
# save report as UUID
# initiate chunking and embedding

from http.client import HTTPException
import re
import uuid
from fastapi import UploadFile, status


async def upload_report(file: UploadFile):
    try:
        report_id = str(uuid.uuid4())
        file_metadata = extract_report_metadata(file)
        sanitize_report_name(file_metadata.get('year'), file_metadata.get('filename'))
        report_key = f"reports/{report_id}/{sanitize_report_name(file_metadata.get('year'), file_metadata.get('filename'))}.pdf"
        #store file logic here
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while processing the report.",
        )

def extract_report_metadata(file: UploadFile) -> dict:
    return {
        "filename": file.filename,
        "file_size": file.size,
        "report_type": "pdf",  # Assuming PDF for now; can be extended
        "sha256_hash": "",  # Placeholder for hash calculation
        "status": "pending",
        "year": extract_report_year(file.filename),  # Extract year from filename
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
        if token == q:
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