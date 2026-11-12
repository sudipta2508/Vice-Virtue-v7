import hashlib
import json
from pathlib import Path


CACHE_DIR = Path(__file__).resolve().parents[1] / "cache"


def _hash_key(*parts: str) -> str:
    h = hashlib.sha256()
    for part in parts:
        h.update(part.encode("utf-8"))
        h.update(b"|")
    return h.hexdigest()


def get_cache(narrative: str, agent_name: str, dimension: str):
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = CACHE_DIR / f"{_hash_key(narrative, agent_name, dimension)}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def set_cache(narrative: str, agent_name: str, dimension: str, data):
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = CACHE_DIR / f"{_hash_key(narrative, agent_name, dimension)}.json"
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
