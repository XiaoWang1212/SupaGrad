import os
from functools import lru_cache

from supabase import Client, create_client


class SupabaseConfigError(RuntimeError):
    pass


@lru_cache(maxsize=1)
def get_supabase_client() -> Client:
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SECRET_KEY")

    if not supabase_url:
        raise SupabaseConfigError("SUPABASE_URL is not configured")
    if not supabase_key:
        raise SupabaseConfigError("SUPABASE_SECRET_KEY is not configured")

    return create_client(supabase_url, supabase_key)
