from supabase import create_client, Client
from app.config import settings

if not settings.supabase_url or not settings.supabase_key:
    raise ValueError("Missing SUPABASE_URL or SUPABASE_KEY in environment.")

supabase: Client = create_client(settings.supabase_url, settings.supabase_key)