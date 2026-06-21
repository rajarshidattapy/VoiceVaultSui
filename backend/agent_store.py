"""
Simple JSON-backed agent store for VoiceVault Deploy.
"""
from __future__ import annotations

import json
import os
import threading
import time
import uuid
from pathlib import Path
from typing import Dict, List, Optional

AGENTS_FILE = Path(__file__).parent / "storage" / "agents.json"
_lock = threading.Lock()


def _load() -> Dict[str, dict]:
    if not AGENTS_FILE.exists():
        return {}
    try:
        return json.loads(AGENTS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save(data: Dict[str, dict]) -> None:
    AGENTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    AGENTS_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")


def create_agent(owner: str, config: dict) -> dict:
    with _lock:
        data = _load()
        agent_id = uuid.uuid4().hex[:8]
        base_url = os.getenv("BACKEND_URL", "http://localhost:8000").rstrip("/")
        agent = {
            "id": agent_id,
            "owner": owner,
            "status": "idle",            # idle | live | paused
            "room_name": f"vv-{agent_id}",
            "calls_count": 0,
            "total_earned_sui": 0.0,
            "created_at": int(time.time()),
            "skills": [],
            "language": "en-IN",
            "agent_description": "",
            "endpoint": f"{base_url}/api/agent/delegate/{agent_id}",
            **config,
        }
        data[agent_id] = agent
        _save(data)
        return agent


def get_agent(agent_id: str) -> Optional[dict]:
    with _lock:
        return _load().get(agent_id)


def get_agent_by_room(room_name: str) -> Optional[dict]:
    with _lock:
        for agent in _load().values():
            if agent.get("room_name") == room_name:
                return agent
        return None


def list_agents(owner: str) -> List[dict]:
    with _lock:
        return [a for a in _load().values() if a.get("owner") == owner]


def update_agent(agent_id: str, updates: dict) -> Optional[dict]:
    with _lock:
        data = _load()
        if agent_id not in data:
            return None
        data[agent_id].update(updates)
        _save(data)
        return data[agent_id]


def delete_agent(agent_id: str) -> bool:
    with _lock:
        data = _load()
        if agent_id not in data:
            return False
        del data[agent_id]
        _save(data)
        return True
