from fastapi import FastAPI, Request, Form
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse, Response
from starlette.middleware.base import BaseHTTPMiddleware
from routes.extract import router as extract_router
from routes.invoices import router as invoices_router
from routes.auth import router as auth_router
from lib.auth import require_auth, get_session
from routes.transactions import router as transactions_router
from routes.export import router as export_router
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import resend
import os

resend.api_key = os.environ.get("RESEND_API_KEY", "")

# Augmente la limite des champs de formulaire à 20MB (pour les photos base64)
import starlette.formparsers
starlette.formparsers.MAX_FIELD_SIZE = 20 * 1024 * 1024  # 20MB

# ── Rate limiter global ───────────────────────────────
limiter = Limiter(key_func=get_remote_address)

app = FastAPI(title="Papriso")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ── Middleware : Headers de sécurité HTTP ─────────────
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)

        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"

        # HSTS — force HTTPS (activé dès que ENVIRONMENT est défini)
        if os.environ.get("ENVIRONMENT"):
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com https://cdn.jsdelivr.net https://mozilla.github.io; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com; "
            "img-src 'self' data: blob: https://*.supabase.co; "
            "connect-src 'self' https://*.supabase.co; "
            "frame-ancestors 'none';"
        )

        return response

app.add_middleware(SecurityHeadersMiddleware)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

app.include_router(auth_router)
app.include_router(extract_router)
app.include_router(invoices_router)
app.include_router(transactions_router)
app.include_router(export_router)

MOIS_FR = {
    1: "Janvier", 2: "Février", 3: "Mars", 4: "Avril",
    5: "Mai", 6: "Juin", 7: "Juillet", 8: "Août",
    9: "Septembre", 10: "Octobre", 11: "Novembre", 12: "Décembre"
}

@app.get("/")
async def root(request: Request):
    guard = require_auth(request)
    if guard:
        return guard
    return RedirectResponse(url="/dashboard")

@app.get("/dashboard")
async def dashboard(request: Request):
    guard = require_auth(request)
    if guard:
        return guard

    from lib.supabase import supabase
    from datetime import date

    session = get_session(request)
    user_email = session["user"].email if session else ""

    result = supabase.table("invoices").select("*").order("invoice_date", desc=True).execute()
    invoices = result.data or []

    now = date.today()
    current_month = f"{now.year}-{now.month:02d}"

    achats_mois = [
        inv for inv in invoices
        if (inv.get("invoice_date") or "")[:7] == current_month
        and inv.get("type") == "achat"
    ]
    ventes_mois = [
        inv for inv in invoices
        if (inv.get("invoice_date") or "")[:7] == current_month
        and inv.get("type") == "vente"
    ]

    total_achats_mois = sum(inv["amount_ttc"] or 0 for inv in achats_mois)
    total_ventes_mois = sum(inv["amount_ttc"] or 0 for inv in ventes_mois)
    balance_mois = total_ventes_mois - total_achats_mois

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "user_email": user_email,
        "total_achats_mois": total_achats_mois,
        "total_ventes_mois": total_ventes_mois,
        "balance_mois": balance_mois,
        "current_month_label": f"{MOIS_FR[now.month]} {now.year}",
        "recent": invoices[:5],
    })


@app.post("/request-access")
@limiter.limit("3/hour")  # Max 3 demandes par IP par heure — anti-spam
async def request_access(
    request: Request,
    name: str = Form(...),
    email: str = Form(...),
):
    notification_email = os.environ.get("NOTIFICATION_EMAIL")
    success = False

    if notification_email and resend.api_key:
        try:
            resend.Emails.send({
                "from": "Papriso <onboarding@resend.dev>",
                "to": notification_email,
                "reply_to": email,
                "subject": f"🔑 Demande d'accès Papriso — {name}",
                "html": f"""
                <div style="font-family:sans-serif;max-width:480px;margin:0 auto;padding:32px 24px;background:#fff;border-radius:12px;border:1px solid #eee;">
                  <div style="display:flex;align-items:center;gap:10px;margin-bottom:24px;">
                    <div style="width:28px;height:28px;background:#0A0A0A;border-radius:7px;display:inline-flex;align-items:center;justify-content:center;">
                      <span style="color:white;font-weight:700;font-size:13px;">P</span>
                    </div>
                    <span style="font-weight:700;font-size:15px;color:#0A0A0A;">Papriso</span>
                  </div>
                  <h2 style="font-size:18px;font-weight:700;color:#0A0A0A;margin:0 0 6px;">Nouvelle demande d'accès</h2>
                  <p style="font-size:13px;color:#999;margin:0 0 24px;">Quelqu'un souhaite accéder à l'application.</p>
                  <div style="background:#F9F9F7;border:1px solid #E8E8E4;border-radius:8px;padding:16px 18px;margin-bottom:24px;">
                    <div style="margin-bottom:12px;">
                      <div style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:0.08em;color:#BBB;">Nom</div>
                      <div style="font-size:14px;color:#0A0A0A;font-weight:600;margin-top:3px;">{name}</div>
                    </div>
                    <div>
                      <div style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:0.08em;color:#BBB;">Email</div>
                      <div style="font-size:14px;color:#0A0A0A;font-weight:600;margin-top:3px;">{email}</div>
                    </div>
                  </div>
                  <a href="mailto:{email}?subject=Accès Papriso"
                     style="display:block;text-align:center;padding:12px;background:#0A0A0A;color:#fff;border-radius:8px;text-decoration:none;font-size:13px;font-weight:700;">
                    Répondre à {name} →
                  </a>
                  <p style="font-size:11px;color:#CCC;text-align:center;margin-top:16px;">Demande reçue via la page de connexion Papriso</p>
                </div>
                """,
            })
            success = True
        except Exception as e:
            print(f"Erreur envoi email demande accès: {e}")

    return templates.TemplateResponse("login.html", {
        "request": request,
        "access_request_sent": success,
        "access_request_error": not success,
    })