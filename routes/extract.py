from fastapi import APIRouter, UploadFile, File, HTTPException, Request
from lib.auth import require_auth
from lib.openai_extract import extract_invoice_data, extract_invoice_data_from_text
import pdfplumber
import fitz  # PyMuPDF
import io

router = APIRouter()

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/heic", "image/heif"}
ALLOWED_TYPES = ALLOWED_IMAGE_TYPES | {"application/pdf"}
MAX_SIZE_MB = 10


@router.post("/api/extract")
async def extract(request: Request, file: UploadFile = File(...)):
    guard = require_auth(request)  # ← ajouté — protège l'usage de GPT-4o Vision
    if guard:
        return guard

    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Format non supporté : {file.content_type}. Utilisez JPG, PNG, WEBP ou PDF."
        )

    file_bytes = await file.read()
    size_mb = len(file_bytes) / (1024 * 1024)
    if size_mb > MAX_SIZE_MB:
        raise HTTPException(
            status_code=400,
            detail=f"Fichier trop lourd ({size_mb:.1f} MB). Maximum : {MAX_SIZE_MB} MB."
        )

    try:
        if file.content_type == "application/pdf":
            data = _handle_pdf(file_bytes)
        else:
            data = extract_invoice_data(file_bytes, file.content_type)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de l'extraction : {str(e)}")

    return {"success": True, "data": data}


def _handle_pdf(pdf_bytes: bytes) -> dict:
    text = _extract_pdf_text(pdf_bytes)
    if text.strip():
        return extract_invoice_data_from_text(text)
    image_bytes = _pdf_page_to_image(pdf_bytes)
    return extract_invoice_data(image_bytes, "image/png")


def _extract_pdf_text(pdf_bytes: bytes) -> str:
    text_parts = []
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages[:3]:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
    return "\n".join(text_parts)


def _pdf_page_to_image(pdf_bytes: bytes) -> bytes:
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    page = doc[0]
    mat = fitz.Matrix(200 / 72, 200 / 72)
    pix = page.get_pixmap(matrix=mat)
    return pix.tobytes("png")