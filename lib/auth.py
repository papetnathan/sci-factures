import os
import logging
from fastapi import Request
from fastapi.responses import RedirectResponse
from lib.supabase import supabase

SESSION_COOKIE = "sci_session"
SESSION_MAX_AGE = 60 * 60 * 8  # 8h (au lieu de 7 jours)

# Logger dédié sécurité
security_logger = logging.getLogger("security")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)

def get_client_ip(request: Request) -> str:
    """Récupère l'IP réelle même derrière un proxy."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"

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
        ip = get_client_ip(request)
        security_logger.warning(f"Accès non authentifié bloqué | IP={ip} | path={request.url.path}")
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