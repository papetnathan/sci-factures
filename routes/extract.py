from fastapi import APIRouter, UploadFile, File, HTTPException
from lib.openai_extract import extract_invoice_data

router = APIRouter()

ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp", "image/heic", "image/heif"}
MAX_SIZE_MB = 10

@router.post("/api/extract")
async def extract(file: UploadFile = File(...)):
    # Vérification du type
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Format non supporté : {file.content_type}. Utilisez JPG, PNG ou WEBP."
        )

    # Lecture et vérification taille
    image_bytes = await file.read()
    size_mb = len(image_bytes) / (1024 * 1024)
    if size_mb > MAX_SIZE_MB:
        raise HTTPException(
            status_code=400,
            detail=f"Fichier trop lourd ({size_mb:.1f} MB). Maximum : {MAX_SIZE_MB} MB."
        )

    try:
        data = extract_invoice_data(image_bytes, file.content_type)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de l'extraction : {str(e)}"
        )

    return {"success": True, "data": data}