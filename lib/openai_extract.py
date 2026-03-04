import os
import base64
import json
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

PROMPT = """Tu es un assistant comptable. Analyse cette facture et extrais les informations suivantes.

Réponds UNIQUEMENT avec un objet JSON valide, sans texte avant ni après, sans balises markdown.

{
  "vendor_name": "nom de l'entreprise émettrice de la facture",
  "detail": "description courte des travaux ou services (ex: carrelage, plomberie, honoraires...)",
  "invoice_date": "date de la facture au format YYYY-MM-DD, null si absente",
  "amount_ttc": nombre décimal (montant TTC en euros, null si absent),
  "amount_ht": nombre décimal (montant HT en euros, null si absent),
  "tva_rate": nombre décimal (taux de TVA en pourcentage ex: 20.0, null si absent)
}

Règles :
- Si plusieurs taux de TVA, prends le taux principal (celui avec le montant le plus élevé)
- Si tu ne trouves pas une information, mets null
- Les montants sont des nombres sans symbole €
- vendor_name et detail sont des chaînes de caractères courtes et propres
"""

def extract_invoice_data(image_bytes: bytes, media_type: str = "image/jpeg") -> dict:
    """
    Envoie l'image à GPT-4o Vision et retourne les données extraites.
    """
    b64 = base64.standard_b64encode(image_bytes).decode("utf-8")

    response = client.chat.completions.create(
        model="gpt-4o",
        max_tokens=500,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{media_type};base64,{b64}",
                            "detail": "high"
                        }
                    },
                    {
                        "type": "text",
                        "text": PROMPT
                    }
                ]
            }
        ]
    )

    raw = response.choices[0].message.content.strip()

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        # Tentative de nettoyage si GPT a quand même ajouté des backticks
        cleaned = raw.replace("```json", "").replace("```", "").strip()
        data = json.loads(cleaned)

    return data