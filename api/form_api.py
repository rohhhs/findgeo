# File: ./api/form_api.py
from typing import Optional
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from api.auth_api import verify_bearer_token
from api.findgeo.findcoordinate import FindGeoCoordinate
from api.definitions import *  # ASSET_DATA_DIR

router = APIRouter(prefix="/api/form", tags=["form"])

class CoordinateRequest(BaseModel):
    latitude: str
    longitude: str
    filepath: str

@router.post("/coordinate", status_code=200)
async def api_form_coordinate(req: CoordinateRequest, token: str = Depends(verify_bearer_token)):
    """
    POST /api/form/coordinate
    Header: Authorization: Bearer <token>
    Body: {"latitude": "<lat>", "longitude": "<lng>", "filepath": "<csv-or-xlsx>"}
    """
    try:
        latitude = float(req.latitude)
        longitude = float(req.longitude)
    except Exception:
        raise HTTPException(status_code=400, detail="Latitude and longitude must be valid numbers")

    filepath = req.filepath
    if not filepath or not isinstance(filepath, str):
        raise HTTPException(status_code=400, detail="filepath is required and must be a string")

    p = Path(filepath)
    if not p.is_absolute():
        base = globals().get("ASSET_DATA_DIR")
        if base is None:
            raise HTTPException(status_code=500, detail="ASSET_DATA_DIR not configured")
        p = Path(base) / filepath

    filepath_resolved = str(p)

    try:
        result = FindGeoCoordinate(latitude=latitude, longitude=longitude, CsvFilepath=filepath_resolved)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"FindGeoCoordinate failure: {exc}") from exc

    return result
