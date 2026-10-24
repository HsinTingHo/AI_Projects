from fastapi import APIRouter, File, HTTPException, UploadFile, status
from starlette.concurrency import run_in_threadpool
from app.storage.dependencies import StorageDep
from app.reports import service
from app.reports.dependencies import ReportRepositoryDep
from app.reports.validation import is_file_pdf, is_file_size_valid, inspect_financial_document, FinancialDocumentCheck

router = APIRouter(prefix="/reports", tags=["reports"])

#report lifecycle: UI upload PDF -> validate PDF contents -> save file to storage -> create database record -> schedule chunking and embedding

@router.post("", status_code=status.HTTP_202_ACCEPTED)
async def upload_report(storage: StorageDep, repository: ReportRepositoryDep, file: UploadFile = File(...)):
    print(f"[upload.route] Received PDF upload: bytes={file.size}", flush=True)
    try:
        if not await is_file_pdf(file):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Uploaded file is not a valid PDF.",
            )
        print("[upload.route] PDF header accepted", flush=True)
        if not is_file_size_valid(file):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File size exceeds the maximum limit of 25 MB.",
            )
        print("[upload.route] Size accepted; inspecting financial content", flush=True)
        check = await run_in_threadpool(
            inspect_financial_document,
            file.file,
        )
        print(f"[upload.route] Inspection outcome={check.outcome}", flush=True)
        if check.outcome == "likely_unrelated":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=check.reasons[0] if check.reasons else "Uploaded file is likely unrelated to financial statements.",
            )
        elif check.outcome == "undetermined":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=check.reasons[0] if check.reasons else "Uploaded file could not be validated.",
            )
        
        result = await service.upload_report(file, storage, repository)
        print(f"[upload.route] Returning 202: report_id={result['id']}", flush=True)
        return result
    except HTTPException as error:
        print(f"[upload.route] Request failed: status={error.status_code}", flush=True)
        raise
    except Exception as e:
        print(f"[upload.route] Unexpected failure: {type(e).__name__}", flush=True)
        raise HTTPException(
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while processing the report: {str(e)}"
        )
       
    finally:
        await file.close()
        print("[upload.route] Upload stream closed", flush=True)
