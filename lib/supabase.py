import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
STORAGE_BUCKET = "invoices"

supabase: Client = create_client(url, key)

def get_public_url(photo_path: str) -> str:
    """Retourne l'URL publique permanente d'une photo."""
    return f"{url}/storage/v1/object/public/{STORAGE_BUCKET}/{photo_path}"