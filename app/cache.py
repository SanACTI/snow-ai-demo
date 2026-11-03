import sqlite3
import hashlib
import json
from pathlib import Path

# --- Cache database location ---
CACHE_DB = Path("outputs/cache.db")

def get_cache_key(sanitized_json: dict, prompt_version: str) -> str:
    """Generate a unique hash for this incident + prompt version."""
    content = json.dumps(sanitized_json, sort_keys=True) + prompt_version
    return hashlib.sha256(content.encode()).hexdigest()

def init_cache():
    """Create cache table if it doesn't exist."""
    CACHE_DB.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(CACHE_DB)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS llm_cache (
            cache_key TEXT PRIMARY KEY,
            incident_number TEXT,
            prompt_version TEXT,
            response TEXT,
            created_at TEXT
        )
    """)
    conn.commit()
    conn.close()

def get_cached_response(cache_key: str) -> dict | None:
    """Return cached LLM response if it exists."""
    try:
        conn = sqlite3.connect(CACHE_DB)
        row = conn.execute(
            "SELECT response FROM llm_cache WHERE cache_key = ?",
            (cache_key,)
        ).fetchone()
        conn.close()
        if row:
            print(f"[cache] ✅ Cache hit for key: {cache_key[:12]}...")
            return json.loads(row[0])
        return None
    except Exception as e:
        print(f"[cache] ⚠️  Cache read error: {e}")
        return None

def save_to_cache(cache_key: str, incident_number: str, prompt_version: str, response: dict):
    """Save LLM response to cache."""
    try:
        from datetime import datetime, timezone
        conn = sqlite3.connect(CACHE_DB)
        conn.execute(
            """INSERT OR REPLACE INTO llm_cache 
               (cache_key, incident_number, prompt_version, response, created_at)
               VALUES (?, ?, ?, ?, ?)""",
            (
                cache_key,
                incident_number,
                prompt_version,
                json.dumps(response),
                datetime.now(timezone.utc).isoformat()
            )
        )
        conn.commit()
        conn.close()
        print(f"[cache] 💾 Saved to cache: {incident_number}")
    except Exception as e:
        print(f"[cache] ⚠️  Cache write error: {e}")