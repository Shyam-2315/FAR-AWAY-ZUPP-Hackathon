"""Investigation Agent — second node in the Athena AI workflow.

Performs root-cause analysis based on the observation.
Calls Claude (Anthropic) to generate a real analysis; falls back to
deterministic mock logic if the API is unavailable.
"""

from __future__ import annotations

import json

from app.agents.llm import call_claude_json
from app.agents.state import AgentState, InvestigationOutput

_SYSTEM_PROMPT = (
    "You are the Investigation Agent in an operational incident-response "
    "pipeline called Athena AI. Given an event record and the Observer "
    "Agent's observation, perform a root-cause investigation. Respond with "
    "ONLY a single JSON object — no markdown, no commentary — with exactly "
    "these keys: "
    '"root_cause" (string, your best assessment of the underlying cause), '
    '"impact" (string, describing the operational/business impact), '
    '"evidence" (array of short strings, specific evidence points '
    "supporting your root cause), "
    '"confidence" (number between 0 and 1).'
)


async def investigation_agent(state: AgentState) -> AgentState:
    """Produce a root-cause investigation from the observation."""
    event = state["event"]
    observation = state.get("observation")

    fallback: InvestigationOutput = {
        "root_cause": "Initial root cause analysis generated from event context",
        "impact": "Potential operational delay and customer impact",
        "evidence": [],
        "confidence": 0.80,
    }

    user_prompt = (
        "Here is the event record (JSON):\n"
        f"{json.dumps(event, default=str, indent=2)}\n\n"
        "Here is the Observer Agent's observation (JSON):\n"
        f"{json.dumps(observation, default=str, indent=2)}\n\n"
        "Investigate the root cause and return your findings as the JSON "
        "object described in the system prompt."
    )

    result = await call_claude_json(
        system_prompt=_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        fallback=dict(fallback),
    )

    investigation: InvestigationOutput = {
        "root_cause": str(result.get("root_cause", fallback["root_cause"])),
        "impact": str(result.get("impact", fallback["impact"])),
        "evidence": list(result.get("evidence") or []),
        "confidence": float(result.get("confidence", fallback["confidence"])),
    }

    return {**state, "investigation": investigation}