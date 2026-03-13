import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
STORAGE_BUCKET = "invoices"

supabase: Client = create_client(url, key)

# Durée de validité des liens signés (en secondes)
SIGNED_URL_EXPIRY = 60 * 60  # 1 heure


def get_public_url(photo_path: str) -> str:
    if not photo_path:
        return None
    try:
        result = supabase.storage.from_(STORAGE_BUCKET).create_signed_url(
            photo_path,
            SIGNED_URL_EXPIRY
        )
        # storage3 v2 retourne un objet avec attribut signed_url
        if hasattr(result, 'signed_url'):
            return result.signed_url
        # fallback dict (anciennes versions)
        if isinstance(result, dict):
            return result.get("signedURL") or result.get("signed_url")
        return None
    except Exception as e:
        print(f"Erreur génération signed URL pour {photo_path}: {e}")
        return None