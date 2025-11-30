import os
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

load_dotenv()

# Small helpers to standardize JSON success/error responses

def ok(message: str = "OK", data=None, status_code: int = 200):
    # return a successful JSONResponse with optional data
    return JSONResponse({"success": True, "message": message, "data": data}, status_code=status_code)

def bad(status_code: int, code: str, message: str, details=None):
    # return a standardized error JSONResponse including code and details
    return JSONResponse({"success": False, "error": {"code": code, "message": message, "details": details}}, status_code=status_code)
