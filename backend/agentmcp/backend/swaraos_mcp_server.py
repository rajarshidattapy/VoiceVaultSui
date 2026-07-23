"""
SwaraOS MCP Server — Agent Indexing & Delegation Tools

Exposes three tools over SSE so LiveKit agent workers can:
  1. discover_agents   — find specialist voice agents by skill keyword
  2. delegate_to_agent — call an agent with automatic x402 payment
  3. get_agent_card    — fetch full metadata for an agent

Run:
  python swaraos_mcp_server.py

Then configure your LiveKit agent worker to connect to:
  http://localhost:8001/sse
"""
from __future__ import annotations

import base64
import os
import sys
from pathlib import Path

# Make sure backend modules are importable
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")
load_dotenv(dotenv_path=Path(__file__).parent / ".env")

import httpx
from mcp.server.fastmcp import FastMCP

API_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
MCP_PORT = int(os.getenv("MCP_PORT", "8001"))

mcp = FastMCP(
    "SwaraOS",
    instructions=(
        "You have access to the SwaraOS agent network. "
        "Use discover_agents to find specialist voice agents by skill, "
        "then delegate_to_agent to have them generate speech. "
        "Use this when the user needs a language or voice style you don't cover."
    ),
)


@mcp.tool()
def discover_agents(skill: str, language: str = "", limit: int = 5) -> list:
    """
    Search the SwaraOS agent registry for live agents matching a skill keyword.

    Args:
        skill:    Keyword to search (e.g. "hindi", "tutoring", "sales").
        language: BCP-47 language code to filter by (e.g. "hi-IN"). Optional.
        limit:    Max results to return (default 5, max 20).

    Returns:
        List of agents with fields: agent_id, name, endpoint,
        price_per_call_wei, skills, language, voice_name, calls_count.
    """
    params: dict = {"skill": skill, "limit": limit}
    if language:
        params["language"] = language

    with httpx.Client(timeout=10) as client:
        resp = client.get(f"{API_URL}/api/agent/discover", params=params)
        resp.raise_for_status()
        return resp.json().get("agents", [])


@mcp.tool()
def delegate_to_agent(
    agent_id: str,
    text: str,
    requester_account: str = "",
    payment_proof: str = "",
    language_code: str = "en-IN",
) -> dict:
    """
    Send text to a specialist agent and get back WAV audio (base64-encoded).

    Handles HTTP 402 automatically — if a payment_proof (Monad tx hash) is
    supplied it will be forwarded; otherwise the 402 response body is returned
    so the caller can sign a transaction and retry.

    Args:
        agent_id:         ID of the target agent (from discover_agents).
        text:             Text the agent should speak.
        requester_account: Caller's Monad wallet address.
        payment_proof:    Monad tx hash proving payment (leave empty to get 402 info).
        language_code:    Override TTS language (default: agent's language).

    Returns:
        On success: { "audio_b64": "<base64 wav>", "agent_id": "...", "calls_count": N }
        On 402:     { "payment_required": true, "requirements": { ... } }
    """
    headers: dict = {"Content-Type": "application/json"}
    if payment_proof:
        headers["X-Payment-Proof"] = payment_proof

    body = {
        "text": text,
        "requester_account": requester_account,
        "language_code": language_code,
    }

    with httpx.Client(timeout=30) as client:
        resp = client.post(
            f"{API_URL}/api/agent/call/{agent_id}",
            json=body,
            headers=headers,
        )

        if resp.status_code == 402:
            return {"payment_required": True, "requirements": resp.json()}

        resp.raise_for_status()
        audio_b64 = base64.b64encode(resp.content).decode()
        return {
            "audio_b64": audio_b64,
            "agent_id": agent_id,
            "content_type": "audio/wav",
        }


@mcp.tool()
def get_agent_card(agent_id: str) -> dict:
    """
    Fetch full metadata for a specific agent.

    Args:
        agent_id: The agent's ID.

    Returns:
        Agent card with name, owner, skills, language, endpoint, status, etc.
    """
    with httpx.Client(timeout=10) as client:
        resp = client.get(f"{API_URL}/api/agent/{agent_id}")
        resp.raise_for_status()
        data = resp.json()
        return data.get("agent", data)


if __name__ == "__main__":
    print(f"SwaraOS MCP server → http://localhost:{MCP_PORT}/sse")
    mcp.run(transport="sse")
