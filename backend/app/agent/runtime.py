"""Main agent runtime — tool-calling loop with Groq."""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from groq import AsyncGroq
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models import Activity, Run, Supervisor, RunStatus
from app.agent.prompts import MAIN_AGENT_SYSTEM_PROMPT, FINAL_SUMMARY_PROMPT
from app.agent.tools import TOOL_DEFINITIONS, get_filtered_tools, execute_tool
from app.database import AsyncSessionLocal

logger = logging.getLogger(__name__)


async def run_agent(run_id: uuid.UUID, wake_trigger: str = "scheduled_wake") -> None:
    """
    Execute one wake cycle of the agent for a given run.
    
    This is the main entry point called by:
    - Run creation (wake_trigger="run_start")
    - Event ingestion (wake_trigger="event: <event_type>")
    - Scheduled wake-up (wake_trigger="scheduled_wake")
    """
    async with AsyncSessionLocal() as db:
        try:
            await _execute_agent_cycle(db, run_id, wake_trigger)
        except Exception as e:
            logger.error(f"Agent error for run {run_id}: {e}", exc_info=True)
            # Record the error as an activity
            try:
                activity = Activity(
                    run_id=run_id,
                    type="system",
                    subtype="agent_error",
                    content={"error": str(e), "wake_trigger": wake_trigger},
                )
                db.add(activity)
                await db.commit()
            except Exception:
                pass


async def _execute_agent_cycle(
    db: AsyncSession, run_id: uuid.UUID, wake_trigger: str
) -> None:
    """Execute one complete agent reasoning cycle."""
    settings = get_settings()

    # Load run with supervisor
    result = await db.execute(select(Run).where(Run.id == run_id))
    run = result.scalar_one_or_none()
    if not run:
        logger.error(f"Run {run_id} not found")
        return

    # Skip if run is in a terminal state or paused
    if run.status in (RunStatus.COMPLETED.value, RunStatus.TERMINATED.value, RunStatus.PAUSED.value):
        logger.info(f"Run {run_id} is {run.status}, skipping agent cycle")
        return

    # Update status to running
    run.status = RunStatus.RUNNING.value
    await db.commit()

    # Load supervisor
    sup_result = await db.execute(select(Supervisor).where(Supervisor.id == run.supervisor_id))
    supervisor = sup_result.scalar_one_or_none()
    if not supervisor:
        logger.error(f"Supervisor {run.supervisor_id} not found for run {run_id}")
        return

    # Load recent activities (last 30)
    act_result = await db.execute(
        select(Activity)
        .where(Activity.run_id == run_id)
        .order_by(Activity.created_at.desc())
        .limit(30)
    )
    recent_activities = list(reversed(act_result.scalars().all()))

    # Build activity history string
    history_lines = []
    for act in recent_activities:
        ts = act.created_at.strftime("%Y-%m-%d %H:%M:%S UTC") if act.created_at else "?"
        content_str = json.dumps(act.content, default=str) if act.content else "{}"
        history_lines.append(f"[{ts}] {act.type}/{act.subtype}: {content_str}")
    recent_history = "\n".join(history_lines) if history_lines else "No activity yet."

    # Build additional instructions string
    additional_instructions = "\n".join(
        f"- {instr}" for instr in (run.additional_instructions or [])
    ) or "None."

    # Build available actions string
    available_actions = ", ".join(supervisor.available_actions or [])

    # Build system prompt
    system_prompt = MAIN_AGENT_SYSTEM_PROMPT.format(
        state_json=json.dumps(run.state or {}, indent=2, default=str),
        additional_instructions=additional_instructions,
        recent_history=recent_history,
        wake_trigger=wake_trigger,
        available_actions=available_actions,
    )

    # Get filtered tools
    tools = get_filtered_tools(supervisor.available_actions or [])

    # Initialize Groq client
    client = AsyncGroq(api_key=settings.GROQ_API_KEY)

    # Agent tool-calling loop
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"You have been woken up. Trigger: {wake_trigger}. Analyze the situation and decide what actions to take."},
    ]

    max_iterations = 10
    completion_recommended = False
    sleep_requested = False

    for iteration in range(max_iterations):
        try:
            response = await client.chat.completions.create(
                model=supervisor.model_config_data.get("model", settings.AGENT_MODEL) if supervisor.model_config_data else settings.AGENT_MODEL,
                messages=messages,
                tools=tools if tools else None,
                temperature=0.3,
                max_tokens=2000,
            )
        except Exception as e:
            logger.error(f"Groq API error: {e}")
            # Record reasoning error
            activity = Activity(
                run_id=run_id,
                type="system",
                subtype="llm_error",
                content={"error": str(e), "iteration": iteration},
            )
            db.add(activity)
            await db.commit()
            break

        choice = response.choices[0]

        # If the model wants to call tools
        if choice.message.tool_calls:
            messages.append(choice.message)

            for tool_call in choice.message.tool_calls:
                fn_name = tool_call.function.name
                try:
                    fn_args = json.loads(tool_call.function.arguments)
                except json.JSONDecodeError:
                    fn_args = {}

                logger.info(f"Run {run_id}: executing tool {fn_name} with args {fn_args}")

                # Execute the tool
                result = await execute_tool(fn_name, fn_args, run, db)

                # Check for special flags
                if result.get("_recommend_completion"):
                    completion_recommended = True
                if result.get("_sleep_until"):
                    sleep_requested = True

                # Add tool result to messages
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(result, default=str),
                })

        else:
            # No more tool calls — record final reasoning
            reasoning_content = choice.message.content or "No reasoning provided."

            activity = Activity(
                run_id=run_id,
                type="agent_reasoning",
                subtype="cycle_complete",
                content={
                    "reasoning": reasoning_content,
                    "iteration_count": iteration + 1,
                    "wake_trigger": wake_trigger,
                },
            )
            db.add(activity)
            await db.commit()
            break

    # Refresh run after tool executions may have modified it
    await db.refresh(run)

    # Handle completion recommendation
    if completion_recommended:
        state = run.state or {}
        order_status = state.get("order_status", "")
        terminal_statuses = {"delivered", "refunded", "cancelled"}
        if order_status in terminal_statuses:
            await _complete_run(db, run)
        else:
            # Agent recommended but order isn't terminal — record but don't complete
            activity = Activity(
                run_id=run_id,
                type="system",
                subtype="completion_denied",
                content={"reason": f"Agent recommended completion but order status is '{order_status}', not terminal."},
            )
            db.add(activity)
            await db.commit()

    # If no sleep was requested and run is still running, set a default wake-up
    if not sleep_requested and run.status == RunStatus.RUNNING.value:
        default_minutes = settings.DEFAULT_WAKE_INTERVAL_MINUTES
        run.next_wake_at = datetime.now(timezone.utc) + timedelta(minutes=default_minutes)
        run.status = RunStatus.SLEEPING.value
        activity = Activity(
            run_id=run_id,
            type="sleep_decision",
            subtype="default_sleep",
            content={
                "wake_at": run.next_wake_at.isoformat(),
                "reason": f"No explicit sleep requested. Defaulting to {default_minutes} minute wake-up.",
            },
        )
        db.add(activity)
        await db.commit()

    # Schedule the wake-up
    if run.next_wake_at and run.status == RunStatus.SLEEPING.value:
        from app.scheduler import schedule_wake_up
        schedule_wake_up(run_id, run.next_wake_at)


async def _complete_run(db: AsyncSession, run: Run) -> None:
    """Complete a run and generate final summary."""
    settings = get_settings()

    # Load all activities for final summary
    act_result = await db.execute(
        select(Activity)
        .where(Activity.run_id == run.id)
        .order_by(Activity.created_at.asc())
    )
    all_activities = act_result.scalars().all()

    # Build full history
    history_lines = []
    for act in all_activities:
        ts = act.created_at.strftime("%Y-%m-%d %H:%M:%S UTC") if act.created_at else "?"
        content_str = json.dumps(act.content, default=str) if act.content else "{}"
        history_lines.append(f"[{ts}] {act.type}/{act.subtype}: {content_str}")
    full_history = "\n".join(history_lines)

    # Generate final summary using LLM
    try:
        client = AsyncGroq(api_key=settings.GROQ_API_KEY)

        prompt = FINAL_SUMMARY_PROMPT.format(
            state_json=json.dumps(run.state or {}, indent=2, default=str),
            full_history=full_history,
        )

        response = await client.chat.completions.create(
            model=settings.AGENT_MODEL,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": "Generate the final summary report for this order supervision run."},
            ],
            temperature=0.3,
            max_tokens=2000,
            response_format={"type": "json_object"},
        )

        summary_text = response.choices[0].message.content
        final_summary = json.loads(summary_text)
    except Exception as e:
        logger.error(f"Error generating final summary: {e}")
        final_summary = {
            "summary": "Final summary generation failed.",
            "actions_taken": [],
            "key_learnings": [],
            "recommendations": [],
            "error": str(e),
        }

    # Update run
    run.status = RunStatus.COMPLETED.value
    run.final_summary = final_summary
    run.next_wake_at = None

    # Record final output
    activity = Activity(
        run_id=run.id,
        type="final_output",
        subtype="run_completed",
        content=final_summary,
    )
    db.add(activity)
    await db.commit()

    # Cancel any scheduled wake-ups
    from app.scheduler import cancel_wake_up
    cancel_wake_up(run.id)


async def generate_final_summary_and_complete(run_id: uuid.UUID) -> None:
    """Public function to complete a run (called from API for manual termination)."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Run).where(Run.id == run_id))
        run = result.scalar_one_or_none()
        if run:
            await _complete_run(db, run)
