from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from routes.extract import router as extract_router
from routes.invoices import router as invoices_router
from routes.auth import router as auth_router
from lib.auth import require_auth, get_session
from routes.transactions import router as transactions_router
from routes.export import router as export_router

# Augmente la limite des champs de formulaire à 20MB (pour les photos base64)
import starlette.formparsers
starlette.formparsers.MAX_FIELD_SIZE = 20 * 1024 * 1024  # 20MB

app = FastAPI(title="SCI Factures")

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