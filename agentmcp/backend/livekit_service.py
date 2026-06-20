"""
LiveKit room token generation for VoiceVault Deploy.
Gracefully degrades to demo mode when credentials are not configured.
"""
from __future__ import annotations

import os
import time
from typing import Optional

LIVEKIT_URL = os.getenv("LIVEKIT_URL", "").rstrip("/")
LIVEKIT_API_KEY = os.getenv("LIVEKIT_API_KEY", "")
LIVEKIT_API_SECRET = os.getenv("LIVEKIT_API_SECRET", "")


def is_configured() -> bool:
    return bool(LIVEKIT_URL and LIVEKIT_API_KEY and LIVEKIT_API_SECRET)


def create_token(room_name: str, identity: str) -> str:
    """Generate a LiveKit access token for the given room and identity."""
    if not is_configured():
        # Demo placeholder — real connection requires LiveKit credentials
        return f"demo-token-{room_name}"

    try:
        from livekit.api import AccessToken, VideoGrants
        token = (
            AccessToken(api_key=LIVEKIT_API_KEY, api_secret=LIVEKIT_API_SECRET)
            .with_identity(identity)
            .with_name(identity)
            .with_grants(
                VideoGrants(
                    room_join=True,
                    room=room_name,
                    can_publish=True,
                    can_subscribe=True,
                    can_publish_data=True,
                )
            )
            .to_jwt()
        )
        return token
    except Exception as err:
        print(f"[livekit] token generation failed: {err}")
        return f"demo-token-{room_name}"


def get_join_url(room_name: str, token: str) -> str:
    """Return a URL the user can open to join the LiveKit room."""
    if not is_configured() or token.startswith("demo-token"):
        return ""
    base = LIVEKIT_URL.replace("wss://", "https://").replace("ws://", "http://")
    return f"https://meet.livekit.io/custom?liveKitUrl={LIVEKIT_URL}&token={token}"


def agent_start_command(room_name: str, agent_file: str = "agent_worker.py") -> str:
    """Return the shell command to start the LiveKit agent worker for this room."""
    return (
        f"LIVEKIT_URL={LIVEKIT_URL} "
        f"LIVEKIT_API_KEY={LIVEKIT_API_KEY} "
        f"LIVEKIT_API_SECRET={LIVEKIT_API_SECRET} "
        f"ROOM_NAME={room_name} "
        f"python {agent_file} dev"
    )
