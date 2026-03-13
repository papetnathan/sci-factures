import os
import logging
from fastapi import APIRouter, Request, Form
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from lib.auth import login_user, logout_user, SESSION_COOKIE, SESSION_MAX_AGE, get_session, get_client_ip, security_logger
from slowapi import Limiter
from slowapi.util import get_remote_address

router = APIRouter()
templates = Jinja2Templates(directory="templates")
limiter = Limiter(key_func=get_remote_address)

is_prod = os.environ.get("ENVIRONMENT") == "production"

@router.get("/login")
async def login_page(request: Request):
    token = request.cookies.get(SESSION_COOKIE)
    if token:
        session = get_session(request)
        if session:
            return RedirectResponse(url="/dashboard", status_code=302)
        response = templates.TemplateResponse("login.html", {"request": request, "error": None})
        response.delete_cookie(
            key=SESSION_COOKIE,
            secure=is_prod,
            samesite="strict",
            httponly=True,
        )
        return response
    return templates.TemplateResponse("login.html", {"request": request, "error": None})

@router.post("/login")
@limiter.limit("5/15minutes")  # Max 5 tentatives par IP par 15 min
async def login_submit(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
):
    ip = get_client_ip(request)

    try:
        result = login_user(email, password)
        token = result.session.access_token

        security_logger.info(f"Connexion réussie | email={email} | IP={ip}")

        response = RedirectResponse(url="/dashboard", status_code=303)
        response.set_cookie(
            key=SESSION_COOKIE,
            value=token,
            httponly=True,           # Inaccessible via JS
            secure=is_prod,          # HTTPS uniquement en prod
            samesite="strict",       # Strict : bloque CSRF cross-site
            max_age=SESSION_MAX_AGE, # 8h
        )
        return response

    except Exception:
        security_logger.warning(f"Échec de connexion | email={email} | IP={ip}")
        return templates.TemplateResponse("login.html", {
            "request": request,
            "error": "Email ou mot de passe incorrect."
        })

@router.post("/logout")
async def logout(request: Request):
    token = request.cookies.get(SESSION_COOKIE)
    ip = get_client_ip(request)
    session = get_session(request)

    if session:
        email = session["user"].email
        security_logger.info(f"Déconnexion | email={email} | IP={ip}")

    if token:
        logout_user(token)

    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie(
        key=SESSION_COOKIE,
        secure=is_prod,
        samesite="strict",
        httponly=True,
    )
    return response