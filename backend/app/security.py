"""Auth admin: login sederhana + cookie sesi bertanda."""
import hmac
import json
import time
from typing import Optional

from fastapi import Cookie, HTTPException, Response
from itsdangerous import BadSignature, URLSafeTimedSerializer

from app.config import get_settings

settings = get_settings()
_signer = URLSafeTimedSerializer(settings.secret_key, salt="arena-admin")
COOKIE_NAME = "arena_admin"
MAX_AGE = 60 * 60 * 12  # 12 jam


def make_session_token() -> str:
    payload = {"user": settings.admin_username, "exp": int(time.time()) + MAX_AGE}
    return _signer.dumps(payload)


def verify_password(username: str, password: str) -> bool:
    return hmac.compare_digest(username, settings.admin_username) and hmac.compare_digest(
        password, settings.admin_password
    )


def validate_token(token: str) -> bool:
    try:
        data = _signer.loads(token, max_age=MAX_AGE)
        return data.get("user") == settings.admin_username
    except BadSignature:
        return False


def set_admin_cookie(response: Response, token: str):
    response.set_cookie(
        COOKIE_NAME,
        token,
        max_age=MAX_AGE,
        httponly=True,
        samesite="lax",
        secure=False,  # set True di production via env/nginx bila HTTPS
    )


def clear_admin_cookie(response: Response):
    response.delete_cookie(COOKIE_NAME)


def require_admin(arena_admin: Optional[str] = Cookie(default=None)) -> None:
    if not arena_admin or not validate_token(arena_admin):
        raise HTTPException(status_code=401, detail="Unauthorized")
