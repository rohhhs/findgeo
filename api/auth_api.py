# File: ./api/auth_api.py
from typing import Optional, List, Dict
from datetime import datetime, timezone
from pathlib import Path
import os
import csv
import tempfile

from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel, Field

from api.encryption.password import encryptPassword, findUser, verifyPassword, saveUser
from api.encryption.token import encodeAccount, decodeAccount, checkToken
from api.form_table.writedata import writeDataBase
from api.definitions import *  # ASSET_DATA_DIR, ASSET_DATA_ENCRYPTION_DIR, etc.

router = APIRouter(prefix="/api/auth", tags=["auth"])

# ---------- Request / Response models ----------
class TokenCheckRequest(BaseModel):
    token: str = Field(..., example="eyJhbGciOiJI...")

class LoginRequest(BaseModel):
    username: str = Field(..., example="john_doe")
    password: str = Field(..., example="s3cr3t")

class RegisterRequest(BaseModel):
    username: str
    password: str
    name: str
    surname: str
    patronym: Optional[str] = ""
    birthdate: Optional[str] = None
    place: Optional[str] = None

class AuthResponse(BaseModel):
    username: str
    token: str
    date: str  # ISO datetime string (UTC)

# ---------- Helpers ----------
def _now_isoutc() -> str:
    return datetime.now(timezone.utc).isoformat()

def _get_encryption_users_file() -> str:
    enc_dir = globals().get("ASSET_DATA_ENCRYPTION_DIR", None) or globals().get("ASSET_DATA_DIR", None)
    if enc_dir is None:
        raise RuntimeError("No ASSET_DATA_ENCRYPTION_DIR or ASSET_DATA_DIR defined in definitions.")
    enc_path = Path(enc_dir) / "users.txt"
    enc_path.parent.mkdir(parents=True, exist_ok=True)
    return str(enc_path)

def _get_users_csv_path() -> str:
    data_dir = globals().get("ASSET_DATA_DIR", None)
    if data_dir is None:
        raise RuntimeError("ASSET_DATA_DIR not defined in definitions.")
    csv_path = Path(data_dir) / "users.csv"
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    return str(csv_path)

def _clean(val: Optional[str]) -> str:
    if val is None:
        return ""
    return str(val).replace("\r", " ").replace("\n", " ").strip()

# ---------- Token dependency (exported) ----------
async def verify_bearer_token(authorization: Optional[str] = Header(None)) -> str:
    """
    FastAPI dependency to validate Authorization: Bearer <token>.
    Returns the token string when valid, raises 401 when missing/invalid.
    Can be imported as: from api.auth_api import verify_bearer_token
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(status_code=401, detail="Authorization header must be: Bearer <token>")
    token = parts[1]
    try:
        if not checkToken(token):
            raise HTTPException(status_code=401, detail="Invalid token")
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")
    return token

# ---------- Auth endpoints ----------
@router.post("/", response_model=bool, status_code=200)
async def api_auth_check(req: TokenCheckRequest):
    """
    POST /api/auth/  <-- checks raw token inside JSON body {"token": "..."}
    """
    token = req.token
    try:
        is_valid = bool(checkToken(token))
    except Exception as exc:
        raise HTTPException(status_code=401, detail="Invalid token") from exc
    if not is_valid:
        raise HTTPException(status_code=401, detail="Invalid token")
    return True

@router.post("/read", response_model=AuthResponse, status_code=200)
async def api_auth_read(req: LoginRequest):
    """
    POST /api/auth/read  (login)
    """
    username = req.username.strip()
    password = req.password

    users_txt = _get_encryption_users_file()
    stored_password = findUser(username, users_txt)
    if not stored_password:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    try:
        if not verifyPassword(stored_password, password):
            raise HTTPException(status_code=401, detail="Invalid credentials")
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    try:
        token = encodeAccount(username, stored_password)
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Failed to encode token") from exc

    return AuthResponse(username=username, token=token, date=_now_isoutc())

@router.post("/write", response_model=AuthResponse, status_code=200)
async def api_auth_write(req: RegisterRequest):
    """
    POST /api/auth/write  (register)
    - Writes encrypted credentials to users.txt and ensures a single canonical row in users.csv
    """
    username = _clean(req.username)
    password = req.password or ""
    name = _clean(req.name)
    surname = _clean(req.surname)
    patronym = _clean(req.patronym)
    birthdate = _clean(req.birthdate)
    place = _clean(req.place)

    if not username or not password or not name or not surname:
        raise HTTPException(status_code=400, detail="Missing required registration fields: username, password, name, surname")

    users_txt = _get_encryption_users_file()
    users_csv = _get_users_csv_path()

    if findUser(username, users_txt):
        raise HTTPException(status_code=409, detail="Username already exists")

    try:
        encrypted = encryptPassword(password)
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Password encryption failed") from exc

    try:
        saveUser(username, encrypted, users_txt)
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Failed to save user to encryption store") from exc

    head = ["username", "name", "surname", "patronym", "birthdate", "place", "status", "request", "json_log"]
    canonical_row = [username, name, surname, patronym, birthdate, place, "User", "0", f"user_log/{username}.json"]

    # Best-effort using helper, but always perform dedupe/update to ensure single canonical row.
    helper_failed = False
    try:
        writeDataBase(filepath=users_csv, head=head, data=[canonical_row])
    except Exception:
        helper_failed = True

    # Read existing CSV and build canonical map (username -> most complete row)
    users_map = {}
    order = []
    try:
        if Path(users_csv).exists():
            with open(users_csv, newline="", encoding="utf-8") as f:
                reader = csv.reader(f)
                file_header = None
                for i, r in enumerate(reader):
                    if i == 0:
                        normalized = [c.strip().lower() for c in r]
                        if normalized[:len(head)] == [h.lower() for h in head]:
                            file_header = r
                            continue
                    if not any(cell.strip() for cell in r):
                        continue
                    uname = r[0].strip() if len(r) > 0 else ""
                    if not uname:
                        continue
                    row_norm = [(r[i].strip() if i < len(r) else "") for i in range(len(head))]
                    filled_count = sum(1 for c in row_norm[1:] if c)
                    if uname not in users_map:
                        users_map[uname] = (row_norm, filled_count)
                        order.append(uname)
                    else:
                        _, existing_filled = users_map[uname]
                        if filled_count > existing_filled:
                            users_map[uname] = (row_norm, filled_count)
    except Exception:
        users_map = {}
        order = []

    # Ensure canonical row for new user
    canonical_filled = sum(1 for c in canonical_row[1:] if c)
    users_map[username] = (canonical_row, canonical_filled)
    if username not in order:
        order.append(username)

    # Build final rows preserving order (no duplicates)
    final_rows = []
    for uname in order:
        row_entry, _ = users_map.get(uname, (None, 0))
        if row_entry:
            final_rows.append(row_entry)
    if not final_rows:
        final_rows = [canonical_row]

    # Atomic write
    try:
        tmp_fd, tmp_path = tempfile.mkstemp(prefix="users_csv_", suffix=".tmp", dir=Path(users_csv).parent)
        os.close(tmp_fd)
        with open(tmp_path, "w", newline="", encoding="utf-8") as outf:
            writer = csv.writer(outf)
            writer.writerow(head)
            for r in final_rows:
                row_to_write = [(r[i] if i < len(r) else "") for i in range(len(head))]
                writer.writerow(row_to_write)
        os.replace(tmp_path, users_csv)
    except Exception as exc:
        try:
            if 'tmp_path' in locals() and Path(tmp_path).exists():
                Path(tmp_path).unlink(missing_ok=True)
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=f"Failed to persist deduplicated users CSV: {exc}") from exc

    try:
        token = encodeAccount(username, encrypted)
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Failed to encode token") from exc

    return AuthResponse(username=username, token=token, date=_now_isoutc())
