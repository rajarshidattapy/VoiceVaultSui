"""
VoiceVault Agent Network MCP server.

This exposes all deployed agents through one MCP endpoint. LiveKit voice agents
connect here to discover specialists, delegate a question, or invite another
agent into the current LiveKit room.
"""
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BACKEND_DIR))

load_dotenv(dotenv_path=BACKEND_DIR.parent / ".env")
load_dotenv(dotenv_path=BACKEND_DIR / ".env", override=True)

import httpx
from mcp.server.fastmcp import FastMCP

API_URL = os.getenv("BACKEND_URL", "http://localhost:8000").rstrip("/")
MCP_HOST = os.getenv("MCP_HOST", "127.0.0.1")
MCP_PORT = int(os.getenv("MCP_PORT", "8001"))

mcp = FastMCP(
    "VoiceVault Agent Network",
    instructions=(
        "Use these tools to collaborate with other deployed VoiceVault agents. "
        "Discover specialists by skill, delegate questions with context, and "
        "invite specialists into the current LiveKit room only when direct voice "
        "participation is useful."
    ),
    host=MCP_HOST,
    port=MCP_PORT,
)


@mcp.tool()
def discover_agents(skill: str, language: str = "", exclude_agent_id: str = "", limit: int = 5) -> dict:
    """Find live specialist agents by skill, prompt, name, or language."""
    params = {
        "skill": skill,
        "language": language,
        "exclude_agent_id": exclude_agent_id,
        "limit": max(1, min(int(limit), 20)),
    }
    with httpx.Client(timeout=10) as client:
        response = client.get(f"{API_URL}/api/agent/discover", params=params)
        response.raise_for_status()
        data = response.json()
        agents = data.get("agents", [])
        return {
            "success": True,
            "query": skill,
            "count": len(agents),
            "agents": agents,
            "message": "No matching live agents found." if not agents else "Matching live agents found.",
        }


@mcp.tool()
def get_agent_card(agent_id: str) -> dict:
    """Fetch public metadata for a deployed agent."""
    with httpx.Client(timeout=10) as client:
        response = client.get(f"{API_URL}/api/agent/{agent_id}")
        response.raise_for_status()
        return response.json().get("agent", {})


@mcp.tool()
def delegate_to_agent(
    agent_id: str,
    question: str,
    context_summary: str = "",
    recent_turns_json: str = "[]",
    source_agent_id: str = "",
    user_intent: str = "",
    max_delegation_depth: int = 2,
    current_depth: int = 0,
) -> dict:
    """
    Privately ask another agent for a text answer.

    Use this for most handoffs. The current speaking agent should summarize the
    returned answer to the user in its own voice.
    """
    payload = {
        "question": question,
        "context_summary": context_summary,
        "recent_turns_json": recent_turns_json,
        "source_agent_id": source_agent_id,
        "user_intent": user_intent,
        "max_delegation_depth": max_delegation_depth,
        "current_depth": current_depth,
    }
    with httpx.Client(timeout=40) as client:
        response = client.post(f"{API_URL}/api/agent/delegate/{agent_id}", json=payload)
        response.raise_for_status()
        return response.json()


@mcp.tool()
def invite_agent_to_room(
    agent_id: str,
    room_name: str,
    question: str,
    context_summary: str = "",
    recent_turns_json: str = "[]",
    source_agent_id: str = "",
    source_participant_identity: str = "",
    user_identity: str = "",
    handoff: bool = False,
    transfer: bool = False,
    max_delegation_depth: int = 2,
    current_depth: int = 0,
) -> dict:
    """
    Invite another deployed agent into the current LiveKit room.

    Use sparingly. Prefer delegate_to_agent when a private answer is enough.
    """
    payload = {
        "roomName": room_name,
        "question": question,
        "context_summary": context_summary,
        "recent_turns_json": recent_turns_json,
        "source_agent_id": source_agent_id,
        "source_participant_identity": source_participant_identity,
        "user_identity": user_identity,
        "handoff": handoff,
        "transfer": transfer,
        "max_delegation_depth": max_delegation_depth,
        "current_depth": current_depth,
    }
    with httpx.Client(timeout=20) as client:
        response = client.post(f"{API_URL}/api/agent/invite/{agent_id}", json=payload)
        response.raise_for_status()
        return response.json()


@mcp.tool()
def invite_best_agent_to_room(
    skill: str,
    room_name: str,
    question: str,
    language: str = "",
    context_summary: str = "",
    recent_turns_json: str = "[]",
    source_agent_id: str = "",
    source_participant_identity: str = "",
    user_identity: str = "",
    handoff: bool = False,
    transfer: bool = False,
    max_delegation_depth: int = 2,
    current_depth: int = 0,
) -> dict:
    """
    Find the best matching live agent and invite it into the current LiveKit room.

    Use this when the user asks to talk to another agent or asks for another
    agent to join the call.
    """
    effective_source_agent_id = source_agent_id
    if not effective_source_agent_id and room_name.startswith("vv-"):
        effective_source_agent_id = room_name[3:]

    params = {
        "skill": skill,
        "language": language,
        "exclude_agent_id": effective_source_agent_id,
        "limit": 5,
    }
    with httpx.Client(timeout=30) as client:
        discover_response = client.get(f"{API_URL}/api/agent/discover", params=params)
        discover_response.raise_for_status()
        agents = discover_response.json().get("agents", [])
        if not agents:
            return {
                "success": False,
                "query": skill,
                "roomName": room_name,
                "error": "No matching live agents found.",
            }

        target = agents[0]
        payload = {
            "roomName": room_name,
            "question": question,
            "context_summary": context_summary,
            "recent_turns_json": recent_turns_json,
            "source_agent_id": effective_source_agent_id,
            "source_participant_identity": source_participant_identity,
            "user_identity": user_identity,
            "handoff": handoff,
            "transfer": transfer,
            "max_delegation_depth": max_delegation_depth,
            "current_depth": current_depth,
        }
        invite_response = client.post(
            f"{API_URL}/api/agent/invite/{target['agent_id']}",
            json=payload,
        )
        invite_response.raise_for_status()
        invited = invite_response.json()
        invited["selected_from"] = agents
        return invited


if __name__ == "__main__":
    print(f"VoiceVault Agent Network MCP -> http://{MCP_HOST}:{MCP_PORT}/sse")
    mcp.run(transport="sse")
