from fastapi import APIRouter, File, HTTPException, UploadFile, status

router = APIRouter(prefix="/reports", tags=["reports"])

#report lifecycle: UI upload PDF -> validate PDF contents -> save file to storage -> create database record -> schedule chunking and embedding

@router.post("", status_code=status.HTTP_202_ACCEPTED)
async def upload_report(file: UploadFile = File(...)):
    try:
        PDF_MAGIC_NUMBER = b"%PDF-"
        header = await file.read(5)  # Read the first 5 bytes to check for PDF magic number
        await file.seek(0)  # Reset the file pointer to the beginning after reading
        if header != PDF_MAGIC_NUMBER:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Please upload a PDF file.",
            )
        if file.size > 25 * 1024 * 1024:  # 25 MB
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File size exceeds the maximum limit of 25 MB.",
            )
        # Next: call the report service to validate the PDF contents,
        # save the file, create its database record, and schedule processing.
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Report upload is not implemented yet.",
        )
    finally:
        await file.close()


# 