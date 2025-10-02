# File: ./api/data_api.py
from typing import Optional, List, Any, Dict
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from api.auth_api import verify_bearer_token  # token dependency exported by auth module
from api.form_table.formdata import readDataBase
from api.definitions import *  # ASSET_DATA_DIR

router = APIRouter(tags=["data"])

class UserReadRequest(BaseModel):
    username: str

@router.post("/api/data/read/user", status_code=200)
async def api_data_read_user(req: UserReadRequest, token: str = Depends(verify_bearer_token)):
    """
    POST /api/data/read/user
    Body: {"username": "<username>"}
    Header: Authorization: Bearer <token>
    Returns single user record as {"username": "<>", "record": {...}, "_log": "..."}
    """
    username = (req.username or "").strip()
    if not username:
        raise HTTPException(status_code=400, detail="username is required")

    users_csv = Path(globals().get("ASSET_DATA_DIR")) / "users.csv"
    users_csv_path = str(users_csv)

    try:
        result = readDataBase(filepath=users_csv_path, columnKey="username", fieldValue=username)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"readDataBase failure: {exc}") from exc

    if not isinstance(result, list) or len(result) == 0:
        raise HTTPException(status_code=500, detail="readDataBase returned invalid payload")

    log = None
    if isinstance(result[-1], list) and len(result[-1]) >= 1 and str(result[-1][0]) == "__LOG__":
        log = result[-1][1] if len(result[-1]) > 1 else ""
        result = result[:-1]

    header = result[0] if len(result) >= 1 else []
    rows = result[1:] if len(result) > 1 else []

    if not rows:
        raise HTTPException(status_code=404, detail="user not found")

    row = rows[0]
    mapped = { (header[i] if i < len(header) else f"col{i}"): (row[i] if i < len(row) else "") for i in range(max(len(header), len(row))) }

    response: Dict[str, Any] = {"username": username, "record": mapped}
    if log:
        response["_log"] = log
    return response

class DataReadRequest(BaseModel):
    filepath: str
    start: Optional[int] = 0
    amount: Optional[int] = 10000
    columnKey: Optional[str] = None
    fieldValue: Optional[str] = None
    secondColumnKey: Optional[str] = None
    header_override: Optional[List[str]] = None

@router.post("/api/data/read", status_code=200)
async def api_data_read(req: DataReadRequest, token: str = Depends(verify_bearer_token)):
    """
    POST /api/data/read
    Header: Authorization: Bearer <token>
    """
    if not req.filepath or not isinstance(req.filepath, str):
        raise HTTPException(status_code=400, detail="filepath is required and must be a string")

    p = Path(req.filepath)
    if not p.is_absolute():
        base = globals().get("ASSET_DATA_DIR")
        if base is None:
            raise HTTPException(status_code=500, detail="ASSET_DATA_DIR not configured")
        p = Path(base) / req.filepath

    filepath_resolved = str(p)

    try:
        result = readDataBase(
            filepath=filepath_resolved,
            start=req.start,
            amount=req.amount,
            columnKey=req.columnKey,
            fieldValue=req.fieldValue,
            secondColumnKey=req.secondColumnKey,
            header_override=req.header_override
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"readDataBase failure: {exc}") from exc

    if not isinstance(result, list) or len(result) == 0:
        raise HTTPException(status_code=500, detail="readDataBase returned invalid payload")

    log = None
    if isinstance(result[-1], list) and len(result[-1]) >= 1 and str(result[-1][0]) == "__LOG__":
        log = result[-1][1] if len(result[-1]) > 1 else ""
        result = result[:-1]

    header = result[0] if len(result) >= 1 else []
    rows = result[1:] if len(result) > 1 else []

    cleaned_header = [col.strip().lstrip('\ufeff') for col in header]

    resp: Dict[str, Any] = {"header": cleaned_header, "rows": rows}
    if log:
        resp["_log"] = log
    return resp
