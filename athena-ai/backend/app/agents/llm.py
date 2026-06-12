"""Shared Anthropic Claude client helper for all agent nodes.

Provides `call_claude_json()` — sends a prompt to Claude and parses a strict
JSON object response matching the caller's expected schema.

If the API key is missing, the call fails, or the response cannot be parsed
as valid JSON, the caller-provided `fallback` dict is returned instead so the
pipeline never breaks (useful for demos / no-key environments).
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from anthropic import AsyncAnthropic

from app.core.settings import get_settings

logger = logging.getLogger(__name__)

_MODEL = "claude-sonnet-4-5-20250929"
_MAX_TOKENS = 1024

_client: AsyncAnthropic | None = None


def _get_client() -> AsyncAnthropic | None:
    """Return a cached AsyncAnthropic client, or None if no API key is set."""
    global _client
    settings = get_settings()
    api_key = getattr(settings, "anthropic_api_key", "") or ""
    if not api_key:
        return None
    if _client is None:
        _client = AsyncAnthropic(api_key=api_key)
    return _client


def _extract_json(text: str) -> dict[str, Any] | None:
    """Extract the first JSON object found in a text blob."""
    text = text.strip()
    # Strip markdown code fences if present
    fence_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fence_match:
        text = fence_match.group(1)

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Fallback: find the first balanced { ... } block
    start = text.find("{")
    if start == -1:
        return None
    depth = 0
    for i in range(start, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                candidate = text[start : i + 1]
                try:
                    return json.loads(candidate)
                except json.JSONDecodeError:
                    return None
    return None


async def call_claude_json(
    *,
    system_prompt: str,
    user_prompt: str,
    fallback: dict[str, Any],
) -> dict[str, Any]:
    """Call Claude and parse a JSON object response.

    Returns `fallback` (a copy) if:
      - no ANTHROPIC_API_KEY is configured
      - the API call raises any exception
      - the response cannot be parsed as a JSON object
    """
    client = _get_client()
    if client is None:
        logger.info("ANTHROPIC_API_KEY not set — using fallback agent output")
        return dict(fallback)

    try:
        response = await client.messages.create(
            model=_MODEL,
            max_tokens=_MAX_TOKENS,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )

        text_parts = [block.text for block in response.content if block.type == "text"]
        raw_text = "\n".join(text_parts)

        parsed = _extract_json(raw_text)
        if parsed is None:
            logger.warning("Could not parse JSON from Claude response — using fallback")
            return dict(fallback)

        # Merge over fallback so any missing keys are filled with safe defaults
        merged = dict(fallback)
        merged.update(parsed)
        return merged

    except Exception:
        logger.exception("Claude API call failed — using fallback agent output")
        return dict(fallback)