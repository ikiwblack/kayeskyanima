import hashlib
import json
import os

CACHE_DIR = "cache/timelines"
os.makedirs(CACHE_DIR, exist_ok=True)

def script_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def load_cached_timeline(text: str):
    h = script_hash(text)
    path = os.path.join(CACHE_DIR, f"{h}.json")
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return None

def save_cached_timeline(text: str, timeline: dict):
    h = script_hash(text)
    path = os.path.join(CACHE_DIR, f"{h}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(timeline, f, indent=2, ensure_ascii=False)
