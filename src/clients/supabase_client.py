import os
from functools import lru_cache

from supabase import Client, create_client

class SupabaseConfigError(RuntimeError):
    pass

@lru_cache(maxsize=1)
def get_supabase_client() -> Client:
    url: str = os.environ.get("SUPABASE_URL", "").strip()
    key: str = os.environ.get("SUPABASE_KEY", "").strip()

    if not url or not key:
        raise RuntimeError(
            "缺少 SUPABASE_URL 或 SUPABASE_KEY，請確認 .env 設定"
        )

    return create_client(url, key)


def check_supabase_connection() -> dict:
    url = os.environ.get("SUPABASE_URL", "")
    key = os.environ.get("SUPABASE_KEY", "")
    return {
        "url_set": bool(url),
        "key_set": bool(key),
        "key_prefix": key[:15] + "..." if len(key) > 15 else "(empty)",
        "url_prefix": url[:30] + "..." if len(url) > 30 else "(empty)",
    }