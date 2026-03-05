from fastapi import APIRouter, Request, UploadFile, File, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse, JSONResponse
from lib.supabase import supabase
from lib.auth import require_auth
from lib.parser import parse_credit_mutuel_pdf, hash_pdf

router = APIRouter()
templates = Jinja2Templates(directory="templates")

@router.get("/transactions")
async def list_transactions(request: Request):
    guard = require_auth(request)
    if guard:
        return guard

    result = supabase.table("imported_files").select("*").order("imported_at", desc=True).execute()
    imported_files = result.data or []

    return templates.TemplateResponse("transactions.html", {
        "request": request,
        "imported_files": imported_files,
    })

@router.post("/transactions/import")
async def import_transactions(request: Request, file: UploadFile = File(...)):
    guard = require_auth(request)
    if guard:
        return guard

    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Fichier PDF requis")

    content = await file.read()
    content_hash = hash_pdf(content)

    # Vérifie si déjà importé
    existing = supabase.table("imported_files").select("id, filename").eq("content_hash", content_hash).execute()
    if existing.data:
        raise HTTPException(
            status_code=409,
            detail=f"Ce relevé a déjà été importé (fichier original : {existing.data[0]['filename']})"
        )

    # Parse le PDF
    try:
        result = parse_credit_mutuel_pdf(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur parsing PDF : {e}")

    if not result["transactions"]:
        raise HTTPException(status_code=400, detail="Aucune transaction trouvée dans le PDF")

    # Insère les transactions
    inserted = 0
    for tx in result["transactions"]:
        existing_tx = supabase.table("bank_transactions")\
            .select("id")\
            .eq("transaction_date", tx["transaction_date"])\
            .eq("label", tx["label"])\
            .eq("amount", tx["amount"])\
            .execute()
        if not existing_tx.data:
            supabase.table("bank_transactions").insert(tx).execute()
            inserted += 1

    # Enregistre le fichier importé
    supabase.table("imported_files").insert({
        "filename": file.filename,
        "content_hash": content_hash,
        "account_name": result["account_name"],
        "date_min": result["date_min"],
        "date_max": result["date_max"],
        "transaction_count": result["transaction_count"],
    }).execute()

    return JSONResponse({
        "inserted": inserted,
        "total": result["transaction_count"],
        "date_min": result["date_min"],
        "date_max": result["date_max"],
    })

@router.post("/transactions/files/{file_id}/delete")
async def delete_imported_file(file_id: str):
    # Récupère les infos du fichier pour supprimer les transactions associées
    file_result = supabase.table("imported_files").select("date_min, date_max, account_name").eq("id", file_id).execute()

    if file_result.data:
        f = file_result.data[0]
        # Supprime les transactions de cette période et ce compte
        supabase.table("bank_transactions")\
            .delete()\
            .gte("transaction_date", f["date_min"])\
            .lte("transaction_date", f["date_max"])\
            .eq("account_name", f["account_name"])\
            .execute()

    supabase.table("imported_files").delete().eq("id", file_id).execute()
    return RedirectResponse(url="/transactions", status_code=303)