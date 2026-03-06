import os
import base64
import json
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

_JSON_SCHEMA = """{
  "vendor_name": "nom de l'entreprise émettrice de la facture",
  "detail": "liste courte et concrète des articles ou matériaux achetés, séparés par des virgules (ex: carrelage, colle, joint, essence, béton, scie). Maximum 6 éléments. Ne mets pas de descriptions vagues comme 'fournitures' ou 'matériaux' — cite les produits réels. Si c'est un loyer ou honoraire, indique le type (ex: loyer septembre, honoraires comptables).",
  "invoice_date": "date de la facture au format YYYY-MM-DD, null si absente",
  "amount_ttc": "nombre décimal (montant TTC en euros, null si absent)",
  "amount_ht": "nombre décimal (montant HT en euros, null si absent)",
  "tva_rate": "nombre décimal (taux de TVA en pourcentage ex: 20.0, null si absent)"
}"""

_RULES = """Règles :
- Si plusieurs taux de TVA, prends le taux principal (celui avec le montant le plus élevé)
- Si tu ne trouves pas une information, mets null
- Les montants sont des nombres sans symbole €
- vendor_name et detail sont des chaînes de caractères courtes et propres
- Réponds UNIQUEMENT avec un objet JSON valide, sans texte avant ni après, sans balises markdown"""

IMAGE_PROMPT = f"""Tu es un assistant comptable. Analyse cette facture et extrais les informations suivantes.

{_JSON_SCHEMA}

{_RULES}"""

TEXT_PROMPT = f"""Tu es un assistant comptable. Analyse le texte de cette facture et extrais les informations suivantes.

{_JSON_SCHEMA}

{_RULES}"""


def extract_invoice_data(image_bytes: bytes, media_type: str = "image/jpeg") -> dict:
    """Extraction depuis une image via GPT-4o Vision."""
    b64 = base64.standard_b64encode(image_bytes).decode("utf-8")

    response = client.chat.completions.create(
        model="gpt-4o",
        max_tokens=500,
        messages=[{
            "role": "user",
            "content": [
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:{media_type};base64,{b64}",
                        "detail": "high"
                    }
                },
                {"type": "text", "text": IMAGE_PROMPT}
            ]
        }]
    )

    return _parse_response(response.choices[0].message.content)


def extract_invoice_data_from_text(text: str) -> dict:
    """Extraction depuis le texte d'un PDF via GPT-4o."""
    response = client.chat.completions.create(
        model="gpt-4o",
        max_tokens=500,
        messages=[{
            "role": "user",
            "content": f"{TEXT_PROMPT}\n\n---\n{text}"
        }]
    )

    return _parse_response(response.choices[0].message.content)


def _parse_response(raw: str) -> dict:
    raw = raw.strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        cleaned = raw.replace("```json", "").replace("```", "").strip()
        return json.loads(cleaned)