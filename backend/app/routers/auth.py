"""Router: auth admin."""
from fastapi import APIRouter, Depends, Response
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from app.schemas import LoginIn
from app.security import clear_admin_cookie, make_session_token, set_admin_cookie, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])

_basic = HTTPBasic()


@router.post("/login")
async def login(body: LoginIn, response: Response):
    if not verify_password(body.username, body.password):
        return {"ok": False, "msg": "Kredensial salah"}
    set_admin_cookie(response, make_session_token())
    return {"ok": True}


@router.post("/logout")
async def logout(response: Response):
    clear_admin_cookie(response)
    return {"ok": True}


@router.get("/check")
async def check(creds: HTTPBasicCredentials = Depends(_basic)):
    return {"ok": True}
