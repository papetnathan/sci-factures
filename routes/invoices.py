from fastapi import APIRouter, Request, Form, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from lib.supabase import supabase, STORAGE_BUCKET, get_public_url
from lib.categories import CATEGORIES, get_category
from lib.auth import require_auth
from typing import Optional
import base64
import uuid
import re

router = APIRouter()
templates = Jinja2Templates(directory="templates")

# ─── Helpers ──────────────────────────────────────────

def upload_photo(photo_b64: str) -> Optional[str]:
    """Upload une photo base64 vers Supabase Storage, retourne le path."""
    try:
        match = re.match(r'data:(image/\w+);base64,(.+)', photo_b64, re.DOTALL)
        if not match:
            return None
        media_type = match.group(1)
        b64_data = match.group(2)
        image_bytes = base64.b64decode(b64_data)

        ext = media_type.split("/")[1].replace("jpeg", "jpg")
        filename = f"{uuid.uuid4()}.{ext}"

        supabase.storage.from_(STORAGE_BUCKET).upload(
            path=filename,
            file=image_bytes,
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

    return templates.TemplateResponse("factures.html", {
        "request": request,
        "invoices": invoices,
        "categories": CATEGORIES,
        "total": len(invoices),
        "filters": {"category": category, "status": status, "q": q, "type": type},
    })

# ─── Nouvelle facture (DOIT être avant /{invoice_id}) ──

@router.get("/factures/nouvelle")
async def nouvelle_facture(request: Request):
    guard = require_auth(request)
    if guard:
        return guard
    return templates.TemplateResponse("nouvelle.html", {"request": request, "categories": CATEGORIES})

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

    return templates.TemplateResponse("facture_detail.html", {
        "request": request,
        "invoice": invoice,
        "photo_url": photo_url,
        "category": category,
        "categories": CATEGORIES,
        "created": created == "1",
        "updated": updated == "1",
    })

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
):
    data = {
        "vendor_name": vendor_name.strip(),
        "detail": detail.strip() or None,
        "category": category or None,
        "amount_ttc": parse_float(amount_ttc),
        "amount_ht": parse_float(amount_ht),
        "tva_rate": parse_float(tva_rate),
        "invoice_date": invoice_date or None,
        "notes": notes.strip() or None,
        "status": status,
        "type": type,
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