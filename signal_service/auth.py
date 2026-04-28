"""
SentinelChain — Authentication Module (SQLite-backed)
JWT-based auth using SQLite user database instead of flat JSON file.
"""
import bcrypt
from datetime import datetime, timedelta
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from typing import List, Optional
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
from database import (
    get_user_by_email, get_user_by_id, create_user,
    get_all_users, record_feedback as db_record_feedback,
    get_user_trust_score as db_get_trust_score, init_db
)

SECRET_KEY = os.getenv("SECRET_KEY", "sentinelchain-secret-key-india-2026")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")


# --- Pydantic Models ---
class UserRegister(BaseModel):
    name: str
    email: str
    password: str
    business_name: str
    business_type: str
    location: str
    language: str = "english"
    alert_channel: str = "app"
    phone: str = ""
    suppliers: List[str] = []
    highways: List[str] = []


class LoginRequest(BaseModel):
    email: str
    password: str


# --- Core auth functions ---
def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode('utf-8'), hashed.encode('utf-8'))
    except Exception:
        return False


def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')


def create_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def _safe_user(user: dict) -> dict:
    """Strip hashed_password from user dict before returning to client."""
    return {k: v for k, v in user.items() if k != "hashed_password"}


def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if not email:
            raise exc
    except JWTError:
        raise exc

    user = get_user_by_email(email)
    if not user:
        raise exc
    return user


def require_admin(current_user: dict = Depends(get_current_user)) -> dict:
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


def register_user(data: UserRegister) -> dict:
    existing = get_user_by_email(data.email)
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    user = create_user({
        "name": data.name,
        "email": data.email,
        "hashed_password": hash_password(data.password),
        "business_name": data.business_name,
        "business_type": data.business_type,
        "location": data.location,
        "language": data.language,
        "alert_channel": data.alert_channel,
        "phone": data.phone,
        "suppliers": data.suppliers,
        "highways": data.highways,
    })

    token = create_token({"sub": data.email})
    return {"access_token": token, "token_type": "bearer", "user": _safe_user(user)}


def login_user(email: str, password: str) -> dict:
    user = get_user_by_email(email)
    if not user or not verify_password(password, user["hashed_password"]):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    token = create_token({"sub": email})
    return {"access_token": token, "token_type": "bearer", "user": _safe_user(user)}


def load_users() -> dict:
    """Compat shim — returns dict keyed by email."""
    users = get_all_users()
    return {u["email"]: u for u in users}
