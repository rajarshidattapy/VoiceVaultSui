"""
VoiceVault LiveKit voice agent worker.

This process registers one named LiveKit agent server. The FastAPI backend
starts it on demand and explicitly dispatches it into vv-* rooms.
"""
from __future__ import annotations

import json
import logging
import os
import sys
import asyncio
import contextlib
from pathlib import Path

if sys.platform == "win32":
    os.environ.setdefault("PYTHONUTF8", "1")

import httpx
from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parent
load_dotenv(dotenv_path=BACKEND_DIR.parent / ".env")
load_dotenv(dotenv_path=BACKEND_DIR / ".env")
STORAGE_DIR = Path(os.getenv("VOICEVAULT_STORAGE_DIR", str(BACKEND_DIR / "storage"))).expanduser()

missing = [
    name
    for name in ("LIVEKIT_URL", "LIVEKIT_API_KEY", "LIVEKIT_API_SECRET", "OPENAI_API_KEY")
    if not os.getenv(name)
]
if missing:
    raise EnvironmentError(
        "Missing required environment variables for LiveKit agent worker: "
        + ", ".join(missing)
    )

from livekit import agents, rtc
from livekit.agents import Agent, AgentServer, AgentSession, function_tool
from livekit.agents.llm import StopResponse, ToolError
from livekit.agents.voice.room_io import RoomInputOptions
from livekit.plugins import openai as lk_openai
from livekit_lux_tts import WalrusLuxTTS

try:
    import mcp.client.streamable_http as mcp_streamable_http

    if not hasattr(mcp_streamable_http, "streamable_http_client") and hasattr(
        mcp_streamable_http, "streamablehttp_client"
    ):
        mcp_streamable_http.streamable_http_client = mcp_streamable_http.streamablehttp_client
    from livekit.agents import mcp as lk_mcp
except Exception:
    lk_mcp = None

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("voicevault-agent")

AGENTS_FILE = STORAGE_DIR / "agents.json"
LIVEKIT_AGENT_NAME = os.getenv("LIVEKIT_AGENT_NAME", "swaraos-voice-agent")
OPENAI_REALTIME_MODEL = os.getenv("OPENAI_REALTIME_MODEL", "gpt-realtime")
AGENT_NETWORK_MCP_URL = os.getenv("AGENT_NETWORK_MCP_URL", "http://127.0.0.1:8001/sse")
BACKEND_API_URL = os.getenv("BACKEND_URL", "http://localhost:8000").rstrip("/")
MAX_DELEGATION_DEPTH = int(os.getenv("MAX_DELEGATION_DEPTH", "2"))
HANDOFF_PARK_FALLBACK_SECONDS = float(os.getenv("AGENT_HANDOFF_PARK_FALLBACK_SECONDS", "8"))
INITIAL_REPLY_WAIT_SECONDS = float(os.getenv("AGENT_INITIAL_REPLY_WAIT_SECONDS", "120"))

server = AgentServer(port=int(os.getenv("LIVEKIT_AGENT_HTTP_PORT", "0")))


def _load_agent_config_by_id(agent_id: str) -> dict:
    if not agent_id:
        return {}

    try:
        if not AGENTS_FILE.exists():
            logger.warning("No agents.json found at %s", AGENTS_FILE)
            return {}

        data = json.loads(AGENTS_FILE.read_text(encoding="utf-8"))
        config = data.get(agent_id, {})
        if config:
            logger.info(
                "Loaded config for agent '%s' (id=%s)",
                config.get("agent_name", "?"),
                agent_id,
            )
        else:
            logger.warning("No config found for agent_id=%s", agent_id)
        return config
    except Exception as exc:
        logger.exception("Failed to read agent config: %s", exc)
        return {}


def _load_agent_config_from_room(room_name: str) -> dict:
    agent_id = room_name.split("vv-", 1)[-1] if room_name.startswith("vv-") else ""
    return _load_agent_config_by_id(agent_id)


def _job_metadata(ctx: agents.JobContext) -> dict:
    raw = ""
    try:
        raw = getattr(ctx.job, "metadata", "") or ""
    except Exception:
        raw = ""
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, dict) else {}
    except Exception:
        logger.warning("Invalid LiveKit dispatch metadata: %s", raw[:500])
        return {}


def _build_mcp_servers() -> list:
    if os.getenv("AGENT_NETWORK_MCP_ENABLED", "true").lower() in {"0", "false", "no"}:
        return []
    if lk_mcp is None:
        logger.warning("MCP integration unavailable; agent network tools disabled")
        return []
    return [
        lk_mcp.MCPServerHTTP(
            url=AGENT_NETWORK_MCP_URL,
            transport_type="sse",
            allowed_tools=[
                "discover_agents",
                "get_agent_card",
                "delegate_to_agent",
            ],
            timeout=8,
            sse_read_timeout=300,
        )
    ]


def _instructions_for(config: dict, room_name: str, metadata: dict) -> str:
    system_prompt = config.get(
        "system_prompt",
        "You are a helpful voice assistant powered by VoiceVault. "
        "Keep your responses concise and conversational.",
    )
    agent_name = config.get("agent_name", "VoiceVault Agent")
    language = config.get("language", "en-IN")
    voice_name = config.get("voice_name", "")
    agent_id = config.get("id") or metadata.get("target_agent_id") or metadata.get("agent_id") or ""
    current_depth = int(metadata.get("current_depth", 0) or 0)

    voice_line = f"- The selected creator voice is '{voice_name}'.\n" if voice_name else ""
    handoff_line = ""
    if metadata.get("mode") == "room_invite":
        handoff_line = (
            "\n[Current handoff]\n"
            f"- You were invited by agent {metadata.get('source_agent_id', '')} into room {room_name}.\n"
            f"- User question to answer: {metadata.get('question', '')}\n"
            f"- Context summary: {metadata.get('context_summary', '')}\n"
            "- Answer the specific delegated question, then hand the floor back.\n"
        )

    return (
        f"{system_prompt}\n\n"
        "[Agent identity]\n"
        f"- Your name is {agent_name}.\n"
        f"- Your agent_id is {agent_id}.\n"
        f"- Current LiveKit room is {room_name}.\n"
        "- You were created on VoiceVault, a voice agent platform for owned voices.\n"
        f"{voice_line}"
        f"- The user's preferred language is {language}.\n"
        "- If the user speaks in another language, respond in that language.\n"
        "- Keep replies short and natural because this is a live voice call.\n"
        "\n[Agent collaboration]\n"
        "- You can use the VoiceVault Agent Network tools when you need specialist help.\n"
        "- discover_agents returns an object with an agents array; choose the best live match by name and skills.\n"
        "- For private specialist help, use delegate_to_agent, then speak the answer yourself.\n"
        "- If the user asks to talk to another agent, asks you to call another agent, says another agent should join, "
        "or asks to be connected/transferred, immediately use transfer_call_to_agent. This is a live handoff: "
        "the other agent joins the same room, and you stay in the room silently after introducing them.\n"
        "- When handing off, pass the user's latest request as question and a short context_summary.\n"
        "- After a handoff tool call, say only one short line like 'I have invited Tutor Agent. Over to you, Tutor Agent.' "
        "Then remain silent and let the invited agent answer.\n"
        f"- Never exceed delegation depth {MAX_DELEGATION_DEPTH}; your current depth is {current_depth}.\n"
        "- Do not delegate to yourself.\n"
        f"{handoff_line}"
    )


def _room_input_options(user_identity: str) -> RoomInputOptions:
    kwargs = {
        "participant_kinds": [rtc.ParticipantKind.PARTICIPANT_KIND_STANDARD],
    }
    # Dispatch metadata can be reused while the browser identity changes
    # between "user", a wallet address, or a generated LiveKit identity.
    # Filtering by participant kind keeps agent-to-agent audio out without
    # accidentally ignoring the human caller.
    strict_identity = os.getenv("AGENT_STRICT_USER_IDENTITY", "false").lower() in {
        "1",
        "true",
        "yes",
    }
    if strict_identity and user_identity:
        kwargs["participant_identity"] = user_identity
    return RoomInputOptions(**kwargs)


async def _set_livekit_participant_identity(
    ctx: agents.JobContext,
    *,
    agent_name: str,
    agent_id: str,
    mode: str,
    room_name: str,
) -> None:
    try:
        participant = ctx.room.local_participant
        await participant.set_name(agent_name)
        await participant.set_metadata(
            json.dumps(
                {
                    "agent_id": agent_id,
                    "agent_name": agent_name,
                    "room_name": room_name,
                    "mode": mode,
                    "role": "voicevault_agent",
                    "state": "active",
                },
                ensure_ascii=False,
            )
        )
        await participant.set_attributes(
            {
                "voicevault.agent_id": agent_id,
                "voicevault.agent_name": agent_name,
                "voicevault.role": "agent",
                "voicevault.mode": mode,
                "voicevault.state": "active",
            }
        )
    except Exception as exc:
        logger.warning("Could not set LiveKit participant display name: %s", exc)


async def _park_agent_session(
    ctx: agents.JobContext,
    session: AgentSession,
    *,
    agent_name: str,
    agent_id: str,
    target_agent_id: str,
) -> None:
    """Keep the agent participant in the room, but stop it from hearing or speaking."""
    try:
        with contextlib.suppress(Exception):
            await session.interrupt(force=True)

        session.input.set_audio_enabled(False)
        session.input.set_video_enabled(False)
        session.output.set_audio_enabled(False)
        session.output.set_transcription_enabled(False)

        with contextlib.suppress(Exception):
            session.input.audio = None
        with contextlib.suppress(Exception):
            session.input.video = None
        with contextlib.suppress(Exception):
            session.output.audio = None

        with contextlib.suppress(Exception):
            session.room_io.unset_participant()

        with contextlib.suppress(Exception):
            await ctx.room.local_participant.set_attributes(
                {
                    "voicevault.agent_id": agent_id,
                    "voicevault.agent_name": agent_name,
                    "voicevault.role": "agent",
                    "voicevault.state": "silent_handoff",
                    "voicevault.handoff_target_agent_id": target_agent_id,
                }
            )

        logger.info(
            "Parked agent '%s' (id=%s) in room '%s' after handoff to agent_id=%s",
            agent_name,
            agent_id,
            ctx.room.name,
            target_agent_id,
        )
    except Exception as exc:
        logger.exception("Failed to park handoff source agent: %s", exc)


async def _queue_initial_reply(
    session: AgentSession,
    *,
    agent_name: str,
    room_name: str,
    metadata: dict,
) -> None:
    try:
        try:
            await asyncio.wait_for(session.room_io.wait_for_ready(), timeout=INITIAL_REPLY_WAIT_SECONDS)
        except asyncio.TimeoutError:
            logger.warning(
                "Timed out waiting for the target user participant before initial reply "
                "(room=%s, user=%s)",
                room_name,
                metadata.get("user_identity", ""),
            )
            return

        if metadata.get("mode") == "room_invite" and metadata.get("question"):
            speech = session.generate_reply(
                instructions=(
                    f"You are {agent_name}. Briefly answer this delegated question now: "
                    f"{metadata.get('question')}"
                ),
                tool_choice="none",
            )
            logger.info(
                "Queued delegated opening reply for agent '%s' in room '%s' (speech_id=%s)",
                agent_name,
                room_name,
                speech.id,
            )
        else:
            speech = session.generate_reply(
                instructions=(
                    f"Greet the user briefly as {agent_name} and ask how you can help. "
                    "Do not use tools for this greeting."
                ),
                tool_choice="none",
            )
            logger.info(
                "Queued opening greeting for agent '%s' in room '%s' (speech_id=%s)",
                agent_name,
                room_name,
                speech.id,
            )
    except RuntimeError as exc:
        logger.warning("Initial reply skipped because the session is no longer active: %s", exc)
    except Exception as exc:
        logger.exception("Failed to queue initial reply: %s", exc)


def _transfer_tool(
    ctx: agents.JobContext,
    session: AgentSession,
    *,
    room_name: str,
    source_agent_id: str,
    source_participant_identity: str,
    source_agent_name: str,
    user_identity: str,
    language: str,
):
    @function_tool(
        name="transfer_call_to_agent",
        description=(
            "Invite the best matching live VoiceVault agent into the current LiveKit room, "
            "introduce that agent, then keep this agent silently parked in the room."
        ),
    )
    async def transfer_call_to_agent(
        skill: str,
        question: str,
        context_summary: str = "",
        target_agent_id: str = "",
    ) -> dict:
        if not skill and not target_agent_id:
            raise ToolError("skill or target_agent_id is required")

        async with httpx.AsyncClient(timeout=30) as client:
            selected_agent_id = target_agent_id.strip()
            selected_agent = None
            candidates = []
            if not selected_agent_id:
                response = await client.get(
                    f"{BACKEND_API_URL}/api/agent/discover",
                    params={
                        "skill": skill,
                        "language": language,
                        "exclude_agent_id": source_agent_id,
                        "limit": 5,
                    },
                )
                response.raise_for_status()
                candidates = response.json().get("agents", [])
                if not candidates:
                    raise ToolError(f"No live agent found for '{skill}'")
                selected_agent = candidates[0]
                selected_agent_id = selected_agent["agent_id"]

            if selected_agent_id == source_agent_id:
                raise ToolError("Cannot transfer the call to yourself")

            invite_response = await client.post(
                f"{BACKEND_API_URL}/api/agent/invite/{selected_agent_id}",
                json={
                    "roomName": room_name,
                    "question": question,
                    "context_summary": context_summary,
                    "source_agent_id": source_agent_id,
                    "source_participant_identity": source_participant_identity,
                    "user_identity": user_identity,
                    "handoff": True,
                    "transfer": False,
                    "current_depth": 0,
                    "max_delegation_depth": MAX_DELEGATION_DEPTH,
                },
            )
            invite_response.raise_for_status()
            result = invite_response.json()

        invited_agent = result.get("agent", {}) or {}
        invited_name = invited_agent.get("name") or (
            selected_agent.get("name") if selected_agent else ""
        )
        invited_name = invited_name or "the specialist agent"
        logger.info(
            "Handed off room '%s' from agent_id=%s participant=%s to agent_id=%s",
            room_name,
            source_agent_id,
            source_participant_identity,
            selected_agent_id,
        )

        async def park_after_handoff_line() -> None:
            parked = False

            async def park_once() -> None:
                nonlocal parked
                if parked:
                    return
                parked = True
                await _park_agent_session(
                    ctx,
                    session,
                    agent_name=source_agent_name,
                    agent_id=source_agent_id,
                    target_agent_id=selected_agent_id,
                )

            handoff_text = f"I have invited {invited_name}. Over to you, {invited_name}."
            try:
                speech = session.generate_reply(
                    instructions=(
                        f"Say exactly this short handoff line and nothing else: {handoff_text}"
                    ),
                    tool_choice="none",
                )

                def on_handoff_done(_speech) -> None:
                    asyncio.create_task(park_once())

                speech.add_done_callback(on_handoff_done)
                await asyncio.sleep(HANDOFF_PARK_FALLBACK_SECONDS)
                if not speech.done():
                    logger.warning("Handoff line did not finish in time; parking source agent anyway")
                await park_once()
            except Exception as exc:
                logger.exception("Failed during handoff line; parking source agent: %s", exc)
                await park_once()

        asyncio.create_task(park_after_handoff_line())
        raise StopResponse()

    return transfer_call_to_agent


class VoiceVaultAgent(Agent):
    def __init__(self, instructions: str, tools: list | None = None, mcp_servers: list | None = None) -> None:
        super().__init__(instructions=instructions, tools=tools or None, mcp_servers=mcp_servers or None)


@server.rtc_session(agent_name=LIVEKIT_AGENT_NAME)
async def voicevault_agent(ctx: agents.JobContext):
    room_name = ctx.room.name
    if not room_name.startswith("vv-"):
        logger.info("Ignoring non-VoiceVault room: %s", room_name)
        ctx.shutdown()
        return

    metadata = _job_metadata(ctx)
    target_agent_id = metadata.get("target_agent_id") or metadata.get("agent_id") or ""
    config = _load_agent_config_by_id(target_agent_id) if target_agent_id else _load_agent_config_from_room(room_name)
    agent_name = config.get("agent_name", "VoiceVault Agent")
    user_identity = metadata.get("user_identity", "")
    source_agent_id = config.get("id") or target_agent_id or metadata.get("agent_id") or ""
    voice_uri = str(config.get("voice_uri") or "").strip()

    if not voice_uri:
        logger.error(
            "Refusing to start agent '%s' (id=%s): its deployed config has no registered voice_uri",
            agent_name,
            source_agent_id or "unknown",
        )
        ctx.shutdown()
        return

    try:
        creator_tts = WalrusLuxTTS(voice_uri=voice_uri, agent_id=source_agent_id)
        await creator_tts.preload_reference()
    except Exception as exc:
        logger.exception(
            "Refusing to start agent '%s' (id=%s): creator voice reference is unavailable: %s",
            agent_name,
            source_agent_id or "unknown",
            exc,
        )
        ctx.shutdown()
        return

    session = AgentSession(
        # Realtime still handles live listening/reasoning, but text-only output
        # ensures no fixed OpenAI voice is published. WalrusLuxTTS speaks every
        # response using the creator's registered Walrus preview.wav instead.
        llm=lk_openai.realtime.RealtimeModel(
            model=OPENAI_REALTIME_MODEL,
            modalities=["text"],
        ),
        tts=creator_tts,
    )

    await ctx.connect()
    source_participant_identity = ctx.room.local_participant.identity
    await _set_livekit_participant_identity(
        ctx,
        agent_name=agent_name,
        agent_id=source_agent_id,
        mode=metadata.get("mode", "primary"),
        room_name=room_name,
    )
    logger.info(
        "Starting agent '%s' in room '%s' (mode=%s, participant=%s, user=%s)",
        agent_name,
        room_name,
        metadata.get("mode", "primary"),
        source_participant_identity,
        user_identity or "auto",
    )

    await session.start(
        room=ctx.room,
        agent=VoiceVaultAgent(
            _instructions_for(config, room_name, metadata),
            tools=[
                _transfer_tool(
                    ctx,
                    session,
                    room_name=room_name,
                    source_agent_id=source_agent_id,
                    source_participant_identity=source_participant_identity,
                    source_agent_name=agent_name,
                    user_identity=user_identity,
                    language=config.get("language", "en-IN"),
                )
            ],
            mcp_servers=_build_mcp_servers(),
        ),
        room_input_options=_room_input_options(user_identity),
    )

    logger.info("Agent '%s' is active in room '%s'", agent_name, room_name)
    asyncio.create_task(
        _queue_initial_reply(
            session,
            agent_name=agent_name,
            room_name=room_name,
            metadata=metadata,
        )
    )


if __name__ == "__main__":
    agents.cli.run_app(server)
