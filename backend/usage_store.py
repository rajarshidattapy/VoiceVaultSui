"""JSON-backed store for x402 UsagePasses (local tracking)."""
import json
import threading
import time
import uuid
from pathlib import Path

USAGE_FILE = Path(__file__).parent / "storage" / "usage_passes.json"
_lock = threading.Lock()


def _load() -> dict:
    if not USAGE_FILE.exists():
        return {}
    with open(USAGE_FILE) as f:
        return json.load(f)


def _save(data: dict) -> None:
    USAGE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(USAGE_FILE, "w") as f:
        json.dump(data, f, indent=2)


def create_pass(
    user: str,
    voice_id: str,
    uses: int = 2,
    expires_in_hours: int = 24,
    tx_digest: str = "",
) -> dict:
    with _lock:
        data = _load()
        pass_id = str(uuid.uuid4())
        now = time.time()
        record = {
            "id": pass_id,
            "user": user.lower(),
            "voice_id": voice_id.lower(),
            "uses_remaining": uses,
            "expires_at": now + expires_in_hours * 3600,
            "created_at": now,
            "tx_digest": tx_digest,
        }
        data[pass_id] = record
        _save(data)
        return record


def has_access(user: str, voice_id: str) -> tuple[bool, dict | None]:
    """Return (True, record) if user has an active pass for voice_id."""
    with _lock:
        data = _load()
        now = time.time()
        for record in data.values():
            if (
                record["user"] == user.lower()
                and record["voice_id"] == voice_id.lower()
                and record["uses_remaining"] > 0
                and record["expires_at"] > now
            ):
                return True, record
        return False, None


def consume_pass(pass_id: str) -> dict | None:
    """Decrement uses_remaining. Returns updated record, or None if invalid."""
    with _lock:
        data = _load()
        record = data.get(pass_id)
        if not record or record["uses_remaining"] <= 0:
            return None
        record["uses_remaining"] -= 1
        _save(data)
        return record


def get_pass(pass_id: str) -> dict | None:
    with _lock:
        return _load().get(pass_id)


def list_passes_for_user(user: str) -> list[dict]:
    with _lock:
        data = _load()
        return [r for r in data.values() if r["user"] == user.lower()]
