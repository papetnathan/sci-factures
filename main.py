from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from routes.extract import router as extract_router
from routes.invoices import router as invoices_router
from routes.auth import router as auth_router
from lib.auth import require_auth
from routes.transactions import router as transactions_router


app = FastAPI(title="SCI Factures")

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

app.include_router(auth_router)
app.include_router(extract_router)
app.include_router(invoices_router)
app.include_router(transactions_router)

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

    result = supabase.table("invoices").select("*").order("invoice_date", desc=True).execute()
    invoices = result.data or []

    now = date.today()
    current_month = f"{now.year}-{now.month:02d}"

    invoices_this_month = [
        inv for inv in invoices
        if (inv.get("invoice_date") or "")[:7] == current_month
    ]

    total_this_month = sum(inv["amount_ttc"] for inv in invoices_this_month)
    count_this_month = len(invoices_this_month)
    pending = [inv for inv in invoices if inv.get("status") == "pending"]
    total_pending = sum(inv["amount_ttc"] for inv in pending)
    total_year = sum(
        inv["amount_ttc"] for inv in invoices
        if (inv.get("invoice_date") or "")[:4] == str(now.year)
    )

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "total_this_month": total_this_month,
        "count_this_month": count_this_month,
        "total_pending": total_pending,
        "count_pending": len(pending),
        "total_year": total_year,
        "current_year": now.year,
        "recent": invoices[:5],
    })