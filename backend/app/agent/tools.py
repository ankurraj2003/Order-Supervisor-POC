"""Tool definitions and executors for the AI agent."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Activity, Run


# ── OpenAI Tool Schemas ────────────────────────────────────────────────────

TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "message_fulfillment_team",
            "description": "Send a message to the fulfillment team about this order. Use when you need to communicate about packing, inventory, or order preparation.",
            "parameters": {
                "type": "object",
                "properties": {
                    "message": {
                        "type": "string",
                        "description": "The message content to send to the fulfillment team"
                    },
                    "priority": {
                        "type": "string",
                        "enum": ["low", "medium", "high", "urgent"],
                        "description": "Priority level of the message"
                    }
                },
                "required": ["message", "priority"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "message_payments_team",
            "description": "Send a message to the payments team about this order. Use when there are payment issues, refund requests, or billing questions.",
            "parameters": {
                "type": "object",
                "properties": {
                    "message": {
                        "type": "string",
                        "description": "The message content to send to the payments team"
                    },
                    "priority": {
                        "type": "string",
                        "enum": ["low", "medium", "high", "urgent"],
                        "description": "Priority level of the message"
                    }
                },
                "required": ["message", "priority"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "message_logistics_team",
            "description": "Send a message to the logistics team about this order. Use for shipping, delivery, and tracking issues.",
            "parameters": {
                "type": "object",
                "properties": {
                    "message": {
                        "type": "string",
                        "description": "The message content to send to the logistics team"
                    },
                    "priority": {
                        "type": "string",
                        "enum": ["low", "medium", "high", "urgent"],
                        "description": "Priority level of the message"
                    }
                },
                "required": ["message", "priority"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "message_customer",
            "description": "Send a message to the customer about their order. Be professional, empathetic, and clear.",
            "parameters": {
                "type": "object",
                "properties": {
                    "message": {
                        "type": "string",
                        "description": "The message content to send to the customer"
                    },
                    "subject": {
                        "type": "string",
                        "description": "Subject line for the customer message"
                    }
                },
                "required": ["message", "subject"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_internal_note",
            "description": "Create an internal note about this order. Use to record observations, reasoning, risk assessments, or important context.",
            "parameters": {
                "type": "object",
                "properties": {
                    "note": {
                        "type": "string",
                        "description": "The internal note content"
                    },
                    "category": {
                        "type": "string",
                        "enum": ["observation", "risk", "decision", "escalation", "general"],
                        "description": "Category of the internal note"
                    }
                },
                "required": ["note", "category"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "sleep_until",
            "description": "Put the supervisor to sleep until a specified time or for a duration. The supervisor will wake up at the specified time or when an important event arrives.",
            "parameters": {
                "type": "object",
                "properties": {
                    "minutes": {
                        "type": "integer",
                        "description": "Number of minutes to sleep for. Use this OR wake_at, not both."
                    },
                    "wake_at": {
                        "type": "string",
                        "description": "ISO 8601 timestamp to wake at. Use this OR minutes, not both."
                    },
                    "reason": {
                        "type": "string",
                        "description": "Why the supervisor is going to sleep"
                    }
                },
                "required": ["reason"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_state",
            "description": "Update the supervisor's state/memory for this order. Use this to track order progress, flags, and important context that should persist across wake cycles.",
            "parameters": {
                "type": "object",
                "properties": {
                    "updates": {
                        "type": "object",
                        "description": "Key-value pairs to merge into the current state. Existing keys will be overwritten."
                    }
                },
                "required": ["updates"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "set_wake_guidance",
            "description": "Update the wake-up guidance for the event classifier. This tells the classifier how to handle future events while the supervisor is sleeping.",
            "parameters": {
                "type": "object",
                "properties": {
                    "guidance": {
                        "type": "string",
                        "description": "Instructions for the event classifier on when to wake the supervisor"
                    }
                },
                "required": ["guidance"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "recommend_completion",
            "description": "Recommend that this supervision run should be completed. The system will verify this against completion rules before actually ending the run.",
            "parameters": {
                "type": "object",
                "properties": {
                    "reason": {
                        "type": "string",
                        "description": "Why the run should be completed"
                    }
                },
                "required": ["reason"],
                "additionalProperties": False,
            },
        },
    },
]


def get_filtered_tools(available_actions: list[str]) -> list[dict]:
    """Return only the tools that are enabled for this supervisor."""
    # Runtime tools are always available
    runtime_tools = {"sleep_until", "update_state", "set_wake_guidance", "recommend_completion"}
    allowed = set(available_actions) | runtime_tools
    return [t for t in TOOL_DEFINITIONS if t["function"]["name"] in allowed]


# ── Tool Executors ──────────────────────────────────────────────────────────

async def execute_tool(
    tool_name: str,
    arguments: dict[str, Any],
    run: Run,
    db: AsyncSession,
) -> dict[str, Any]:
    """Execute a tool call and return the result."""

    if tool_name in ("message_fulfillment_team", "message_payments_team", "message_logistics_team"):
        return await _execute_message_team(tool_name, arguments, run, db)
    elif tool_name == "message_customer":
        return await _execute_message_customer(arguments, run, db)
    elif tool_name == "create_internal_note":
        return await _execute_internal_note(arguments, run, db)
    elif tool_name == "sleep_until":
        return await _execute_sleep(arguments, run, db)
    elif tool_name == "update_state":
        return await _execute_update_state(arguments, run, db)
    elif tool_name == "set_wake_guidance":
        return await _execute_set_wake_guidance(arguments, run, db)
    elif tool_name == "recommend_completion":
        return await _execute_recommend_completion(arguments, run, db)
    else:
        return {"success": False, "error": f"Unknown tool: {tool_name}"}


async def _execute_message_team(
    tool_name: str, arguments: dict, run: Run, db: AsyncSession
) -> dict:
    """Record a team message as an activity."""
    team = tool_name.replace("message_", "").replace("_team", "")
    activity = Activity(
        run_id=run.id,
        type="agent_action",
        subtype=tool_name,
        content={
            "team": team,
            "message": arguments["message"],
            "priority": arguments["priority"],
            "order_id": run.order_id,
        },
    )
    db.add(activity)
    await db.commit()
    return {
        "success": True,
        "message": f"Message sent to {team} team with {arguments['priority']} priority.",
    }


async def _execute_message_customer(
    arguments: dict, run: Run, db: AsyncSession
) -> dict:
    """Record a customer message as an activity."""
    activity = Activity(
        run_id=run.id,
        type="agent_action",
        subtype="message_customer",
        content={
            "subject": arguments["subject"],
            "message": arguments["message"],
            "order_id": run.order_id,
        },
    )
    db.add(activity)
    await db.commit()
    return {
        "success": True,
        "message": f"Message sent to customer: {arguments['subject']}",
    }


async def _execute_internal_note(
    arguments: dict, run: Run, db: AsyncSession
) -> dict:
    """Record an internal note as an activity."""
    activity = Activity(
        run_id=run.id,
        type="agent_action",
        subtype="create_internal_note",
        content={
            "note": arguments["note"],
            "category": arguments["category"],
        },
    )
    db.add(activity)
    await db.commit()
    return {"success": True, "message": "Internal note created."}


async def _execute_sleep(
    arguments: dict, run: Run, db: AsyncSession
) -> dict:
    """Set the run to sleep until a specified time."""
    now = datetime.now(timezone.utc)

    if "minutes" in arguments and arguments["minutes"]:
        wake_at = now + timedelta(minutes=arguments["minutes"])
    elif "wake_at" in arguments and arguments["wake_at"]:
        wake_at = datetime.fromisoformat(arguments["wake_at"])
        if wake_at.tzinfo is None:
            wake_at = wake_at.replace(tzinfo=timezone.utc)
    else:
        # Default: sleep for 30 minutes
        wake_at = now + timedelta(minutes=30)

    run.next_wake_at = wake_at
    run.status = "sleeping"

    activity = Activity(
        run_id=run.id,
        type="sleep_decision",
        subtype="sleep_until",
        content={
            "wake_at": wake_at.isoformat(),
            "reason": arguments.get("reason", "No reason given"),
        },
    )
    db.add(activity)
    await db.commit()

    return {
        "success": True,
        "message": f"Supervisor will sleep until {wake_at.isoformat()}. Reason: {arguments.get('reason', '')}",
        "_sleep_until": wake_at.isoformat(),
    }


async def _execute_update_state(
    arguments: dict, run: Run, db: AsyncSession
) -> dict:
    """Merge updates into the run's state."""
    current_state = run.state or {}
    updates = arguments.get("updates", {})
    current_state.update(updates)
    run.state = current_state

    activity = Activity(
        run_id=run.id,
        type="state_update",
        subtype="update_state",
        content={"updates": updates, "new_state": current_state},
    )
    db.add(activity)
    await db.commit()

    return {"success": True, "message": "State updated.", "current_state": current_state}


async def _execute_set_wake_guidance(
    arguments: dict, run: Run, db: AsyncSession
) -> dict:
    """Update the wake-up guidance for the classifier."""
    run.wake_guidance = arguments["guidance"]

    activity = Activity(
        run_id=run.id,
        type="state_update",
        subtype="set_wake_guidance",
        content={"guidance": arguments["guidance"]},
    )
    db.add(activity)
    await db.commit()

    return {"success": True, "message": "Wake guidance updated."}


async def _execute_recommend_completion(
    arguments: dict, run: Run, db: AsyncSession
) -> dict:
    """Record the agent's recommendation to complete the run."""
    activity = Activity(
        run_id=run.id,
        type="agent_action",
        subtype="recommend_completion",
        content={"reason": arguments["reason"]},
    )
    db.add(activity)
    await db.commit()

    return {
        "success": True,
        "message": "Completion recommendation recorded. The system will evaluate this against completion rules.",
        "_recommend_completion": True,
        "_reason": arguments["reason"],
    }
