from fastapi import APIRouter, File, UploadFile, Depends
from .auth import get_current_user
from .utils import ok, bad
from .s3.service import BulkDataService

router = APIRouter(prefix="/s3", tags=["S3"])

try:
    file_service = BulkDataService()
except:
    file_service = None

@router.post("/upload")
async def upload_file(file: UploadFile = File(...), current=Depends(get_current_user)):
    if not file_service:
        return bad(503, "SERVICE_UNAVAILABLE", "S3 not configured")
    
    if not file.filename or not file_service.validate_file_type(file.filename):
        return bad(400, "INVALID_FILE", "Invalid file")
    
    try:
        content = await file.read()
        result = file_service.upload_bulk_file(content, file.filename)
        
        if not result or not result.get('success'):
            return bad(500, "UPLOAD_FAILED", "Upload failed")
        
        return ok("File uploaded", {"file_key": result['file_key'], "size": len(content)})
    except Exception as e:
        return bad(500, "UPLOAD_ERROR", str(e))

@router.get("/files")
async def list_files(current=Depends(get_current_user)):
    if not file_service:
        return bad(503, "SERVICE_UNAVAILABLE", "S3 not configured")
    
    try:
        files = file_service.list_files()
        return ok(f"Retrieved {len(files)} files", files)
    except Exception as e:
        return bad(500, "LIST_ERROR", str(e))

@router.get("/download/{file_key:path}")
async def download_file(file_key: str, current=Depends(get_current_user)):
    if not file_service:
        return bad(503, "SERVICE_UNAVAILABLE", "S3 not configured")
    
    try:
        url = file_service.get_download_url(file_key)
        if not url:
            return bad(404, "FILE_NOT_FOUND", "File not found")
        
        return ok("Download URL generated", {"download_url": url, "file_key": file_key})
    except Exception as e:
        return bad(500, "DOWNLOAD_ERROR", str(e))
