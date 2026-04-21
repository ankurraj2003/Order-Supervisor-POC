"""Lightweight wake-up classifier using Groq LLM."""

from __future__ import annotations

import json
import logging
from typing import Any

from groq import AsyncGroq

from app.config import get_settings
from app.agent.prompts import CLASSIFIER_SYSTEM_PROMPT

logger = logging.getLogger(__name__)

# Events that ALWAYS wake the agent, regardless of classifier
ALWAYS_WAKE_EVENTS = {
    "order_created",
    "delivered",
    "refund_requested",
    "payment_failed",
    "customer_message_received",
}


async def should_wake_agent(
    event_type: str,
    event_payload: dict[str, Any],
    run_status: str,
    order_status: str,
    wake_guidance: str | None,
    next_wake_at: str | None,
) -> tuple[bool, str]:
    """
    Determine whether an incoming event should wake the main agent.

    Returns:
        (should_wake, reason)
    """
    # Hard-coded overrides — always wake for critical events
    if event_type in ALWAYS_WAKE_EVENTS:
        return True, f"Event '{event_type}' is classified as always-wake."

    # If run is paused, don't wake
    if run_status == "paused":
        return False, "Run is paused. Event will be stored but agent will not wake."

    # If no wake guidance, default to waking
    if not wake_guidance:
        return True, "No wake guidance set — defaulting to wake."

    # Use LLM classifier for borderline cases
    try:
        settings = get_settings()
        client = AsyncGroq(api_key=settings.GROQ_API_KEY)

        prompt = CLASSIFIER_SYSTEM_PROMPT.format(
            wake_guidance=wake_guidance or "No specific guidance set.",
            run_status=run_status,
            order_status=order_status or "unknown",
            next_wake_at=next_wake_at or "not scheduled",
        )

        response = await client.chat.completions.create(
            model=settings.CLASSIFIER_MODEL,
            messages=[
                {"role": "system", "content": prompt},
                {
                    "role": "user",
                    "content": f"Event type: {event_type}\nEvent payload: {json.dumps(event_payload)}",
                },
            ],
            temperature=0.1,
            max_tokens=200,
            response_format={"type": "json_object"},
        )

        result_text = response.choices[0].message.content
        result = json.loads(result_text)
        should_wake = result.get("wake", True)
        reason = result.get("reason", "No reason provided by classifier.")

        return should_wake, reason

    except Exception as e:
        logger.error(f"Classifier error: {e}. Defaulting to wake.")
        return True, f"Classifier error ({str(e)}). Defaulting to wake for safety."
