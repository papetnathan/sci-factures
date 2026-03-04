import os
from functools import wraps
from fastapi import Request
from fastapi.responses import RedirectResponse
from lib.supabase import supabase

SESSION_COOKIE = "sci_session"

def get_session(request: Request) -> dict | None:
    """Récupère et valide le token de session depuis le cookie."""
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

def require_auth(request: Request) -> RedirectResponse | None:
    """Retourne une redirect si pas connecté, None si ok."""
    session = get_session(request)
    if not session:
        return RedirectResponse(url="/login", status_code=302)
    return None

def login_user(email: str, password: str) -> dict:
    """Authentifie l'utilisateur, retourne la session Supabase."""
    result = supabase.auth.sign_in_with_password({
        "email": email,
        "password": password
    })
    return result

def logout_user(token: str):
    """Révoque la session côté Supabase."""
    try:
        supabase.auth.sign_out()
    except Exception:
        pass