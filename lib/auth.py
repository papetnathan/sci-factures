import os
from fastapi import Request
from fastapi.responses import RedirectResponse
from lib.supabase import supabase

SESSION_COOKIE = "sci_session"

def get_session(request: Request):
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        return None
    try:
        user = supabase.auth.get_user(token)
        if user and user.user:
            return {"user": user.user, "token": token}
        return None
    except Exception:
        return None

def require_auth(request: Request):
    session = get_session(request)
    if not session:
        return RedirectResponse(url="/login", status_code=302)
    return None

def login_user(email: str, password: str):
    return supabase.auth.sign_in_with_password({
        "email": email,
        "password": password
    })

def logout_user(token: str):
    try:
        supabase.auth.sign_out()
    except Exception:
        pass