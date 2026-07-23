"""
LiveKit room token generation for VoiceVault Deploy.
Gracefully degrades to demo mode when credentials are not configured.
"""
from __future__ import annotations

import os
import json
from typing import Optional
from urllib.parse import urlencode

LIVEKIT_URL = os.getenv("LIVEKIT_URL", "").rstrip("/")
LIVEKIT_API_KEY = os.getenv("LIVEKIT_API_KEY", "")
LIVEKIT_API_SECRET = os.getenv("LIVEKIT_API_SECRET", "")
LIVEKIT_AGENT_NAME = os.getenv("LIVEKIT_AGENT_NAME", "swaraos-voice-agent")


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
    query = urlencode({"liveKitUrl": LIVEKIT_URL, "token": token})
    return f"https://meet.livekit.io/custom?{query}"


async def ensure_agent_dispatch(
    room_name: str,
    metadata: Optional[str] = None,
    dispatch_key: Optional[str] = None,
) -> tuple[bool, Optional[str]]:
    """Explicitly dispatch the configured LiveKit agent worker to a room."""
    if not is_configured():
        return False, "LiveKit credentials are not configured"

    try:
        from livekit import api

        metadata_payload = metadata or ""
        if dispatch_key:
            try:
                data = json.loads(metadata_payload) if metadata_payload else {}
                data["dispatch_key"] = dispatch_key
                metadata_payload = json.dumps(data)
            except Exception:
                metadata_payload = json.dumps({"dispatch_key": dispatch_key, "metadata": metadata_payload})

        lkapi = api.LiveKitAPI(
            url=LIVEKIT_URL,
            api_key=LIVEKIT_API_KEY,
            api_secret=LIVEKIT_API_SECRET,
        )
        try:
            dispatches = []
            try:
                dispatches = await lkapi.agent_dispatch.list_dispatch(room_name=room_name)
            except Exception as err:
                # A room can be created by create_dispatch, so a failed list on a
                # fresh room should not prevent dispatch.
                print(f"[livekit] dispatch list skipped for {room_name}: {err}")

            for dispatch in dispatches:
                if dispatch_key:
                    try:
                        existing = json.loads(getattr(dispatch, "metadata", "") or "{}")
                    except Exception:
                        existing = {}
                    if existing.get("dispatch_key") == dispatch_key:
                        return True, None
                elif getattr(dispatch, "agent_name", "") == LIVEKIT_AGENT_NAME:
                    return True, None

            await lkapi.agent_dispatch.create_dispatch(
                api.CreateAgentDispatchRequest(
                    agent_name=LIVEKIT_AGENT_NAME,
                    room=room_name,
                    metadata=metadata_payload,
                )
            )
            return True, None
        finally:
            await lkapi.aclose()
    except Exception as err:
        code = getattr(err, "code", None)
        if code == "already_exists":
            return True, None
        print(f"[livekit] agent dispatch failed for {room_name}: {err}")
        return False, str(err)


async def remove_participant(room_name: str, identity: str) -> tuple[bool, Optional[str]]:
    """Remove a participant from a room, used to transfer the speaking floor."""
    if not is_configured():
        return False, "LiveKit credentials are not configured"
    if not identity:
        return False, "participant identity is required"

    try:
        from livekit import api

        lkapi = api.LiveKitAPI(
            url=LIVEKIT_URL,
            api_key=LIVEKIT_API_KEY,
            api_secret=LIVEKIT_API_SECRET,
        )
        try:
            await lkapi.room.remove_participant(
                api.RoomParticipantIdentity(room=room_name, identity=identity)
            )
            return True, None
        finally:
            await lkapi.aclose()
    except Exception as err:
        code = getattr(err, "code", None)
        if code == "not_found":
            return True, None
        print(f"[livekit] remove participant failed for {room_name}/{identity}: {err}")
        return False, str(err)


def agent_start_command(room_name: str, agent_file: str = "agent_worker.py") -> str:
    """Return the shell command to start the LiveKit agent worker for this room."""
    return (
        f"LIVEKIT_URL={LIVEKIT_URL} "
        f"LIVEKIT_API_KEY={LIVEKIT_API_KEY} "
        f"LIVEKIT_API_SECRET={LIVEKIT_API_SECRET} "
        f"LIVEKIT_AGENT_NAME={LIVEKIT_AGENT_NAME} "
        f"ROOM_NAME={room_name} "
        f"python {agent_file} start"
    )
