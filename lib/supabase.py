import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

url = os.environ["SUPABASE_URL"]
key = os.environ["SUPABASE_SERVICE_ROLE_KEY"]

supabase: Client = create_client(url, key)

STORAGE_BUCKET = "invoices"