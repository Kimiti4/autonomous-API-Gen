import json
from app.storage.atomic import atomic_write_json

FILE = "memory.json" 

def load():
    try:
        with open(FILE, "r") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Persistent memory is unreadable: {FILE}") from exc
    
def save(data):
    with open(FILE, "w") as f:
        json.dump(data, f, indent=2)