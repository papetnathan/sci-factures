import os
from fastapi import APIRouter, Request, Form
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from lib.auth import login_user, logout_user, SESSION_COOKIE, get_session

router = APIRouter()
templates = Jinja2Templates(directory="templates")

is_prod = os.environ.get("ENVIRONMENT") == "production"

@router.get("/login")
async def login_page(request: Request):
    token = request.cookies.get(SESSION_COOKIE)
    if token:
        session = get_session(request)
        if session:
            # Token valide → dashboard
            return RedirectResponse(url="/dashboard", status_code=302)
        # Token expiré → supprime le cookie et affiche login
        response = templates.TemplateResponse("login.html", {"request": request, "error": None})
        response.delete_cookie(key=SESSION_COOKIE, secure=is_prod, samesite="lax")
        return response
    return templates.TemplateResponse("login.html", {"request": request, "error": None})

@router.post("/login")
async def login_submit(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
):
    try:
        result = login_user(email, password)
        token = result.session.access_token

        response = RedirectResponse(url="/dashboard", status_code=303)
        response.set_cookie(
            key=SESSION_COOKIE,
            value=token,
            httponly=True,
            secure=is_prod,
            samesite="lax",
            max_age=60 * 60 * 24 * 7
        )
        return response

    except Exception:
        return templates.TemplateResponse("login.html", {
            "request": request,
            "error": "Email ou mot de passe incorrect."
        })

@router.post("/logout")
async def logout(request: Request):
    token = request.cookies.get(SESSION_COOKIE)
    if token:
        logout_user(token)

    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie(key=SESSION_COOKIE, secure=is_prod, samesite="lax")
    return response