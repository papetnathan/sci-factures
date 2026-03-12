from fastapi import APIRouter, Request, Form, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from lib.supabase import supabase, STORAGE_BUCKET, get_public_url
from lib.categories import CATEGORIES, get_category
from lib.auth import require_auth, get_session
from typing import Optional
from datetime import datetime, timedelta
import base64
import uuid
import re

router = APIRouter()
templates = Jinja2Templates(directory="templates")

# ─── Helpers ──────────────────────────────────────────

def get_user_email(request: Request) -> str:
    session = get_session(request)
    return session["user"].email if session else ""

def upload_photo(photo_b64: str) -> Optional[str]:
    try:
        match = re.match(r'data:([\w/]+);base64,(.+)', photo_b64, re.DOTALL)
        if not match:
            return None
        media_type = match.group(1)
        b64_data = match.group(2)
        file_bytes = base64.b64decode(b64_data)

        if media_type == 'application/pdf':
            ext = 'pdf'
        else:
            ext = media_type.split("/")[1].replace("jpeg", "jpg")

        filename = f"{uuid.uuid4()}.{ext}"

        supabase.storage.from_(STORAGE_BUCKET).upload(
            path=filename,
            file=file_bytes,
            file_options={"content-type": media_type}
        )
        return filename
    except Exception as e:
        print(f"Erreur upload photo: {e}")
        return None

def parse_float(value: str) -> Optional[float]:
    try:
        return float(value) if value and value.strip() else None
    except ValueError:
        return None

def find_matching_transactions(invoice: dict) -> list:
    amount = invoice.get("amount_ttc")
    invoice_date = invoice.get("invoice_date")
    invoice_type = invoice.get("type", "achat")

    if not amount or not invoice_date:
        return []

    try:
        date_obj = datetime.strptime(invoice_date, "%Y-%m-%d")
        date_min = (date_obj - timedelta(days=30)).strftime("%Y-%m-%d")
        date_max = (date_obj + timedelta(days=30)).strftime("%Y-%m-%d")
    except ValueError:
        return []

    tx_type = "debit" if invoice_type == "achat" else "credit"

    result = supabase.table("bank_transactions")\
        .select("*")\
        .eq("amount", amount)\
        .eq("type", tx_type)\
        .eq("matched", False)\
        .gte("transaction_date", date_min)\
        .lte("transaction_date", date_max)\
        .order("transaction_date")\
        .execute()

    return result.data or []

# ─── Liste des factures ────────────────────────────────

@router.get("/factures")
async def list_factures(request: Request, category: str = "", status: str = "", q: str = "", type: str = "achat"):
    guard = require_auth(request)
    if guard:
        return guard

    query = supabase.table("invoices").select("*").order("invoice_date", desc=True)

    if category:
        query = query.eq("category", category)
    if status:
        query = query.eq("status", status)
    if type:
        query = query.eq("type", type)

    result = query.execute()
    invoices = result.data or []

    if q:
        q_lower = q.lower()
        invoices = [
            inv for inv in invoices
            if q_lower in (inv.get("vendor_name") or "").lower()
            or q_lower in (inv.get("detail") or "").lower()
        ]

    tx_ids = [inv.get("transaction_id") for inv in invoices if inv.get("transaction_id")]
    transactions_map = {}
    if tx_ids:
        tx_result = supabase.table("bank_transactions").select("id, label, transaction_date, amount").in_("id", tx_ids).execute()
        for tx in (tx_result.data or []):
            transactions_map[tx["id"]] = tx

    for inv in invoices:
        inv["transaction"] = transactions_map.get(inv.get("transaction_id"))

    return templates.TemplateResponse("factures.html", {
        "request": request,
        "user_email": get_user_email(request),
        "invoices": invoices,
        "categories": CATEGORIES,
        "total": len(invoices),
        "filters": {"category": category, "status": status, "q": q, "type": type},
    })

# ─── Nouvelle facture ──────────────────────────────────

@router.get("/factures/nouvelle")
async def nouvelle_facture(request: Request):
    guard = require_auth(request)
    if guard:
        return guard
    return templates.TemplateResponse("nouvelle.html", {
        "request": request,
        "user_email": get_user_email(request),
        "categories": CATEGORIES,
    })

# ─── Créer une facture ─────────────────────────────────

@router.post("/factures")
async def create_facture(
    request: Request,
    vendor_name: str = Form(...),
    detail: str = Form(""),
    category: str = Form(""),
    amount_ttc: str = Form(...),
    amount_ht: str = Form(""),
    tva_rate: str = Form(""),
    invoice_date: str = Form(""),
    notes: str = Form(""),
    photo_data: str = Form(""),
    type: str = Form("achat"),
):
    photo_path = None
    if photo_data:
        photo_path = upload_photo(photo_data)

    data = {
        "vendor_name": vendor_name.strip(),
        "detail": detail.strip() or None,
        "category": category or None,
        "amount_ttc": parse_float(amount_ttc),
        "amount_ht": parse_float(amount_ht),
        "tva_rate": parse_float(tva_rate),
        "invoice_date": invoice_date or None,
        "notes": notes.strip() or None,
        "photo_url": photo_path,
        "status": "pending",
        "type": type,
    }

    result = supabase.table("invoices").insert(data).execute()

    if not result.data:
        raise HTTPException(status_code=500, detail="Erreur lors de la sauvegarde")

    new_id = result.data[0]["id"]
    return RedirectResponse(url=f"/factures/{new_id}?created=1", status_code=303)

# ─── Détail d'une facture ──────────────────────────────

@router.get("/factures/{invoice_id}")
async def detail_facture(request: Request, invoice_id: str, created: str = "", updated: str = ""):
    guard = require_auth(request)
    if guard:
        return guard

    result = supabase.table("invoices").select("*").eq("id", invoice_id).execute()

    if not result.data:
        raise HTTPException(status_code=404, detail="Facture introuvable")

    invoice = result.data[0]

    photo_url = None
    if invoice.get("photo_url"):
        photo_url = get_public_url(invoice["photo_url"])

    category = get_category(invoice.get("category") or "autre")

    linked_transaction = None
    if invoice.get("transaction_id"):
        tx_result = supabase.table("bank_transactions").select("*").eq("id", invoice["transaction_id"]).execute()
        if tx_result.data:
            linked_transaction = tx_result.data[0]

    suggested_transactions = []
    if not linked_transaction and invoice.get("status") == "pending":
        suggested_transactions = find_matching_transactions(invoice)

    return templates.TemplateResponse("facture_detail.html", {
        "request": request,
        "user_email": get_user_email(request),
        "invoice": invoice,
        "photo_url": photo_url,
        "category": category,
        "categories": CATEGORIES,
        "created": created == "1",
        "updated": updated == "1",
        "linked_transaction": linked_transaction,
        "suggested_transactions": suggested_transactions,
    })

# ─── Lier une transaction à une facture ───────────────

@router.post("/factures/{invoice_id}/match")
async def match_transaction(invoice_id: str, transaction_id: str = Form(...)):
    supabase.table("invoices").update({
        "transaction_id": transaction_id,
        "status": "paid",
    }).eq("id", invoice_id).execute()

    supabase.table("bank_transactions").update({
        "invoice_id": invoice_id,
        "matched": True,
    }).eq("id", transaction_id).execute()

    return RedirectResponse(url=f"/factures/{invoice_id}?updated=1", status_code=303)

# ─── Dissocier une transaction ─────────────────────────

@router.post("/factures/{invoice_id}/unmatch")
async def unmatch_transaction(invoice_id: str):
    result = supabase.table("invoices").select("transaction_id").eq("id", invoice_id).execute()
    if result.data and result.data[0].get("transaction_id"):
        tx_id = result.data[0]["transaction_id"]
        supabase.table("bank_transactions").update({
            "invoice_id": None,
            "matched": False,
        }).eq("id", tx_id).execute()

    supabase.table("invoices").update({
        "transaction_id": None,
        "status": "pending",
    }).eq("id", invoice_id).execute()

    return RedirectResponse(url=f"/factures/{invoice_id}?updated=1", status_code=303)

# ─── Modifier une facture ──────────────────────────────

@router.post("/factures/{invoice_id}/edit")
async def edit_facture(
    request: Request,
    invoice_id: str,
    vendor_name: str = Form(...),
    detail: str = Form(""),
    category: str = Form(""),
    amount_ttc: str = Form(...),
    amount_ht: str = Form(""),
    tva_rate: str = Form(""),
    invoice_date: str = Form(""),
    notes: str = Form(""),
    status: str = Form("pending"),
    type: str = Form("achat"),
    payment_date: str = Form(""),
    payment_account: str = Form(""),
):
    effective_status = "paid" if (payment_date or payment_account.strip()) else status

    data = {
        "vendor_name": vendor_name.strip(),
        "detail": detail.strip() or None,
        "category": category or None,
        "amount_ttc": parse_float(amount_ttc),
        "amount_ht": parse_float(amount_ht),
        "tva_rate": parse_float(tva_rate),
        "invoice_date": invoice_date or None,
        "notes": notes.strip() or None,
        "status": effective_status,
        "type": type,
        "payment_date": payment_date or None,
        "payment_account": payment_account.strip() or None,
    }

    supabase.table("invoices").update(data).eq("id", invoice_id).execute()
    return RedirectResponse(url=f"/factures/{invoice_id}?updated=1", status_code=303)

# ─── Supprimer une facture ─────────────────────────────

@router.post("/factures/{invoice_id}/delete")
async def delete_facture(invoice_id: str):
    result = supabase.table("invoices").select("photo_url").eq("id", invoice_id).execute()
    if result.data and result.data[0].get("photo_url"):
        try:
            supabase.storage.from_(STORAGE_BUCKET).remove([result.data[0]["photo_url"]])
        except Exception:
            pass

    supabase.table("invoices").delete().eq("id", invoice_id).execute()
    return RedirectResponse(url="/factures?deleted=1", status_code=303)