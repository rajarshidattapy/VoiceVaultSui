"""
Agent Indexing Engine — searchable registry for SwaraOS agents.

Agents register skill tags + language when deployed. Callers (human or agent)
query /api/agent/discover to find specialists, then delegate via /api/agent/call.
"""
from __future__ import annotations

from typing import List, Optional

import agent_store


def discover(skill: str, language: Optional[str] = None, limit: int = 5) -> List[dict]:
    """
    Find live agents matching skill keyword and optional language.
    Returns up to `limit` results sorted by calls_count desc (most proven first).
    """
    all_agents: List[dict] = []
    with agent_store._lock:
        data = agent_store._load()
        all_agents = list(data.values())

    skill_lc = skill.lower().strip()

    results = []
    for agent in all_agents:
        if agent.get("status") != "live":
            continue

        skills: List[str] = [s.lower() for s in agent.get("skills", [])]
        name_lc = agent.get("agent_name", "").lower()
        prompt_lc = agent.get("system_prompt", "").lower()

        skill_match = (
            any(skill_lc in s for s in skills)
            or skill_lc in name_lc
            or skill_lc in prompt_lc
        )
        if not skill_match:
            continue

        if language:
            agent_lang = agent.get("language", "en-IN")
            if agent_lang.lower() != language.lower():
                continue

        results.append(agent)

    results.sort(key=lambda a: a.get("calls_count", 0), reverse=True)
    return [_public_view(a) for a in results[:limit]]


def register_skills(agent_id: str, skills: List[str], language: str = "en-IN") -> Optional[dict]:
    """Add/replace skill tags and language on an existing agent."""
    cleaned = [s.strip().lower() for s in skills if s.strip()]
    updated = agent_store.update_agent(agent_id, {"skills": cleaned, "language": language})
    return _public_view(updated) if updated else None


def increment_calls(agent_id: str, earned_wei: int = 0) -> None:
    """Track a completed call — increments call count and earnings."""
    agent = agent_store.get_agent(agent_id)
    if not agent:
        return
    earned_mon = earned_wei / 1e18
    agent_store.update_agent(agent_id, {
        "calls_count": agent.get("calls_count", 0) + 1,
        "total_earned_sui": round(agent.get("total_earned_sui", 0.0) + earned_mon, 6),
    })


def _public_view(agent: dict) -> dict:
    """Strip internal fields before returning to callers."""
    return {
        "agent_id":         agent["id"],
        "name":             agent.get("agent_name", ""),
        "owner":            agent.get("owner", ""),
        "status":           agent.get("status", "idle"),
        "skills":           agent.get("skills", []),
        "language":         agent.get("language", "en-IN"),
        "endpoint":         agent.get("endpoint", ""),
        "price_per_call_wei": int(agent.get("price_per_call", 0.1) * 1e18),
        "voice_id":         agent.get("voice_id", ""),
        "voice_name":       agent.get("voice_name", ""),
        "calls_count":      agent.get("calls_count", 0),
        "llm_provider":     agent.get("llm_provider", ""),
    }
