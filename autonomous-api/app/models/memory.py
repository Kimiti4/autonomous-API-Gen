import json
from app.storage.atomic import atomic_write_json

FILE = "memory.json" 

def load():
    try:
        with open(FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Persistent memory is unreadable: {FILE}") from exc
    
def save(data):
    atomic_write_json(FILE, data)
