"""
Searchable registry for deployed VoiceVault agents.

The registry is JSON-backed through agent_store for the hackathon MVP. It gives
voice agents a stable way to discover specialist agents by skills, prompt, or
name before delegating a question.
"""
from __future__ import annotations

import os
import re
from typing import List, Optional

import agent_store

_STOP_WORDS = {
    "a",
    "an",
    "and",
    "another",
    "any",
    "agent",
    "assistant",
    "bot",
    "call",
    "connect",
    "for",
    "i",
    "join",
    "me",
    "please",
    "talk",
    "the",
    "to",
    "want",
    "with",
}


def _tokens(value: str) -> list[str]:
    return [
        token
        for token in re.findall(r"[a-z0-9]+", value.lower())
        if len(token) > 1 and token not in _STOP_WORDS
    ]


def _token_matches(query_token: str, candidate_tokens: list[str]) -> bool:
    return any(
        query_token == candidate
        or query_token in candidate
        or candidate in query_token
        for candidate in candidate_tokens
    )


def discover(skill: str, language: Optional[str] = None, limit: int = 5, exclude_agent_id: str = "") -> List[dict]:
    skill_lc = skill.lower().strip()
    language_lc = language.lower().strip() if language else ""
    query_tokens = _tokens(skill_lc)

    with agent_store._lock:
        agents = list(agent_store._load().values())

    results = []
    for agent in agents:
        if agent.get("status") != "live":
            continue
        if exclude_agent_id and agent.get("id") == exclude_agent_id:
            continue

        searchable = " ".join(
            [
                agent.get("agent_name", ""),
                agent.get("agent_description", ""),
                agent.get("template_id", ""),
                agent.get("system_prompt", ""),
                " ".join(str(skill) for skill in agent.get("skills", [])),
            ]
        ).lower()
        searchable_tokens = _tokens(searchable)

        score = 0
        if not skill_lc or not query_tokens:
            score = 1
        elif skill_lc in searchable:
            score = 100
        else:
            matched = [token for token in query_tokens if _token_matches(token, searchable_tokens)]
            if not matched:
                continue
            score = len(matched) * 10
            skill_text = " ".join(str(skill) for skill in agent.get("skills", [])).lower()
            name_text = agent.get("agent_name", "").lower()
            score += sum(5 for token in matched if token in skill_text)
            score += sum(4 for token in matched if token in name_text)

        if language_lc and agent.get("language", "en-IN").lower() != language_lc:
            continue

        results.append((score, agent))

    results.sort(key=lambda item: (item[0], item[1].get("calls_count", 0)), reverse=True)
    return [_public_view(agent) for _, agent in results[: max(1, min(limit, 20))]]


def register_skills(agent_id: str, skills: List[str], language: str = "en-IN", description: str = "") -> Optional[dict]:
    if isinstance(skills, str):
        raw_skills = skills.split(",")
    elif isinstance(skills, list):
        raw_skills = skills
    else:
        raw_skills = []
    cleaned = sorted({str(skill).strip().lower() for skill in raw_skills if str(skill).strip()})
    updates = {"skills": cleaned, "language": language or "en-IN"}
    if description:
        updates["agent_description"] = description.strip()
    updated = agent_store.update_agent(agent_id, updates)
    return _public_view(updated) if updated else None


def increment_calls(agent_id: str, earned_amount: float = 0.0) -> None:
    agent = agent_store.get_agent(agent_id)
    if not agent:
        return
    agent_store.update_agent(
        agent_id,
        {
            "calls_count": agent.get("calls_count", 0) + 1,
            "total_earned_sui": round(agent.get("total_earned_sui", 0.0) + earned_amount, 6),
        },
    )


def _public_view(agent: dict) -> dict:
    base_url = os.getenv("BACKEND_URL", "http://localhost:8000").rstrip("/")
    return {
        "agent_id": agent["id"],
        "name": agent.get("agent_name", ""),
        "description": agent.get("agent_description", ""),
        "owner": agent.get("owner", ""),
        "status": agent.get("status", "idle"),
        "skills": agent.get("skills", []),
        "language": agent.get("language", "en-IN"),
        "endpoint": agent.get("endpoint") or f"{base_url}/api/agent/delegate/{agent['id']}",
        "price_per_call": agent.get("price_per_call", 0.0),
        "voice_id": agent.get("voice_id", ""),
        "voice_name": agent.get("voice_name", ""),
        "calls_count": agent.get("calls_count", 0),
        "llm_provider": agent.get("llm_provider", ""),
    }
