from fastapi import APIRouter, Request, Form
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from lib.auth import login_user, logout_user, SESSION_COOKIE

router = APIRouter()
templates = Jinja2Templates(directory="templates")

@router.get("/login")
async def login_page(request: Request):
    # Si déjà connecté, redirige vers dashboard
    token = request.cookies.get(SESSION_COOKIE)
    if token:
        return RedirectResponse(url="/dashboard", status_code=302)
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
            httponly=True,       # Inaccessible depuis JS
            secure=True,         # HTTPS uniquement en prod
            samesite="lax",      # Protection CSRF basique
            max_age=60 * 60 * 24 * 7  # 7 jours
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
    response.delete_cookie(SESSION_COOKIE)
    return response