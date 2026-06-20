"""
SwaraOS — LiveKit Voice Agent Worker

Runs as a standalone process alongside the FastAPI server.
Connects to LiveKit Cloud and automatically joins voice rooms
when users click "Talk" on a deployed agent.

Pipeline:
    User Speech → Silero VAD → OpenAI Whisper STT → GPT-4o LLM → OpenAI TTS → Agent Speech

Usage:
    python agent_worker.py dev      # Development mode (auto-reload)
    python agent_worker.py start    # Production mode

Environment Variables Required:
    LIVEKIT_URL          - LiveKit Cloud WebSocket URL  (e.g. wss://xxx.livekit.cloud)
    LIVEKIT_API_KEY      - LiveKit API key
    LIVEKIT_API_SECRET   - LiveKit API secret
    OPENAI_API_KEY       - OpenAI API key (for Whisper STT, GPT-4o, TTS)
"""

from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path

# Force UTF-8 on Windows to avoid cp1252 encoding crashes with Rich logger
if sys.platform == "win32":
    os.environ.setdefault("PYTHONUTF8", "1")

from dotenv import load_dotenv

# ── Load environment ──────────────────────────────────────────────────────────
BACKEND_DIR = Path(__file__).resolve().parent
load_dotenv(dotenv_path=BACKEND_DIR.parent / ".env")
load_dotenv(dotenv_path=BACKEND_DIR / ".env", override=True)

# ── Validate critical env vars early ─────────────────────────────────────────
_missing = []
for var in ("LIVEKIT_URL", "LIVEKIT_API_KEY", "LIVEKIT_API_SECRET", "OPENAI_API_KEY"):
    if not os.getenv(var):
        _missing.append(var)
if _missing:
    raise EnvironmentError(
        f"Missing required environment variables: {', '.join(_missing)}\n"
        f"Add them to your .env file in {BACKEND_DIR} or {BACKEND_DIR.parent}"
    )

# ── LiveKit Agents Framework ────────────────────────────────────────────────
from livekit import agents
from livekit.agents import AgentSession, Agent, JobContext, WorkerOptions

try:
    from livekit.plugins import openai as lk_openai
except ImportError:
    raise ImportError(
        "Missing livekit-plugins-openai. "
        "Install with:  pip install livekit-plugins-openai"
    )

try:
    from livekit.plugins import silero
except ImportError:
    raise ImportError(
        "Missing livekit-plugins-silero. "
        "Install with:  pip install livekit-plugins-silero"
    )

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("swaraos-agent")

AGENTS_FILE = BACKEND_DIR / "storage" / "agents.json"


# ── Helpers ──────────────────────────────────────────────────────────────────

def _load_agent_config(room_name: str) -> dict:
    """
    Load agent configuration from agents.json using the room name.
    Room names follow the pattern  vv-{agent_id}.
    """
    agent_id = room_name.split("vv-", 1)[-1] if "vv-" in room_name else ""
    if not agent_id:
        return {}
    try:
        if AGENTS_FILE.exists():
            data = json.loads(AGENTS_FILE.read_text(encoding="utf-8"))
            config = data.get(agent_id, {})
            if config:
                logger.info(
                    "Loaded config for agent '%s' (id=%s)",
                    config.get("agent_name", "?"),
                    agent_id,
                )
                return config
        logger.warning("No config found for agent_id=%s -- using defaults", agent_id)
    except Exception as exc:
        logger.error("Failed to read agents.json: %s", exc)
    return {}


# ── Entrypoint — called by LiveKit when a user joins a room ─────────────────

async def entrypoint(ctx: JobContext):
    """Main voice-agent entrypoint dispatched by LiveKit Cloud."""

    room_name = ctx.room.name

    # Only handle SwaraOS voice rooms (vv-* prefix)
    if not room_name.startswith("vv-"):
        logger.info("Ignoring non-SwaraOS room: %s", room_name)
        return

    # Connect to the LiveKit room
    await ctx.connect()

    # ── Load agent personality ───────────────────────────────────────────────
    config = _load_agent_config(room_name)

    system_prompt = config.get(
        "system_prompt",
        "You are a helpful voice assistant powered by SwaraOS. "
        "Keep your responses concise and conversational.",
    )
    agent_name = config.get("agent_name", "SwaraOS Agent")
    language = config.get("language", "en-IN")
    voice_name = config.get("voice_name", "")

    logger.info("[MIC] Agent '%s' joining room '%s' (lang=%s)", agent_name, room_name, language)

    # ── Build the voice pipeline ─────────────────────────────────────────────
    session = AgentSession(
        stt=lk_openai.STT(model="whisper-1"),
        llm=lk_openai.LLM(model="gpt-4o"),
        tts=lk_openai.TTS(voice="alloy"),
        vad=silero.VAD.load(),
    )

    # Enrich system prompt with agent identity + language preference
    full_instructions = (
        f"{system_prompt}\n\n"
        f"[Agent identity]\n"
        f"- Your name is {agent_name}.\n"
        f"- You were created on SwaraOS, a voice-sovereign agent platform on Monad.\n"
        + (f"- Your voice model is '{voice_name}'.\n" if voice_name else "")
        + f"- The user's preferred language is {language}.\n"
        f"- If the user speaks in a language other than English, respond in their language.\n"
        f"- Keep responses brief and natural — this is a live voice call, not a chat.\n"
    )

    await session.start(
        room=ctx.room,
        agent=Agent(instructions=full_instructions),
    )

    logger.info("[OK] Agent '%s' is now active in room '%s'", agent_name, room_name)

    # Greet the user so they know the agent is ready
    try:
        greeting = f"Hi! I'm {agent_name}. How can I help you today?"
        await session.say(greeting, allow_interruptions=True)
    except Exception:
        # session.say() may not exist in all livekit-agents versions
        logger.debug("Greeting skipped (session.say not available)")


# ── CLI entry ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    agents.cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            agent_name="swaraos-voice-agent",
        ),
    )