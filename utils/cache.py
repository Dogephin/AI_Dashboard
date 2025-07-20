import hashlib
import json

from flask_caching import Cache

cache = Cache()


def init_cache(app):
    cache.init_app(app)


def generate_cache_key(prefix: str, data: dict) -> str:
    try:
        normalized = json.dumps(
            data, sort_keys=True, separators=(",", ":")
        )  # remove whitespace
        hash_digest = hashlib.sha256(normalized.encode()).hexdigest()
        return f"{prefix}::{hash_digest}"
    except Exception as e:
        print(f"[Cache Key Error] Failed to serialize data: {e}")
        return f"{prefix}::fallback"
