"""Run lifecycle API endpoints."""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, case
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Run, Supervisor, Activity, RunStatus
from app.schemas import (
    RunCreate,
    RunResponse,
    RunListResponse,
    ActivityResponse,
    InstructionAdd,
    StatusResponse,
    DashboardStats,
)
from app.config import get_settings

router = APIRouter(prefix="/api/runs", tags=["runs"])


@router.post("", response_model=RunResponse, status_code=201)
async def create_run(data: RunCreate, db: AsyncSession = Depends(get_db)):
    """Create and start a new run for an order."""
    settings = get_settings()

    # Verify supervisor exists
    sup_result = await db.execute(select(Supervisor).where(Supervisor.id == data.supervisor_id))
    supervisor = sup_result.scalar_one_or_none()
    if not supervisor:
        raise HTTPException(status_code=404, detail="Supervisor not found")

    # Check for existing active run for this order
    existing = await db.execute(
        select(Run).where(
            Run.order_id == data.order_id,
            Run.status.in_([RunStatus.RUNNING.value, RunStatus.SLEEPING.value, RunStatus.PAUSED.value]),
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=409,
            detail=f"An active run already exists for order {data.order_id}",
        )

    # Initialize state with order context
    initial_state = {
        "order_id": data.order_id,
        "order_status": "created",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "events_received": [],
        "actions_taken": 0,
        "priority": "normal",
    }
    if data.initial_context:
        initial_state.update(data.initial_context)

    # Create run
    run = Run(
        supervisor_id=data.supervisor_id,
        order_id=data.order_id,
        status=RunStatus.RUNNING.value,
        state=initial_state,
        wake_guidance=supervisor.wake_guidance,
        additional_instructions=[],
        max_end_at=datetime.now(timezone.utc) + timedelta(hours=settings.MAX_RUN_AGE_HOURS),
    )
    db.add(run)
    await db.commit()
    await db.refresh(run)

    # Record run start activity
    activity = Activity(
        run_id=run.id,
        type="system",
        subtype="run_started",
        content={
            "order_id": data.order_id,
            "supervisor_name": supervisor.name,
            "initial_state": initial_state,
        },
    )
    db.add(activity)
    await db.commit()

    # Trigger initial agent run in background
    asyncio.create_task(_run_agent_background(run.id, "run_start"))

    # Reload with relationships
    result = await db.execute(select(Run).where(Run.id == run.id))
    run = result.scalar_one()

    return run


@router.get("", response_model=list[RunListResponse])
async def list_runs(
    status: str | None = Query(None, description="Filter by status"),
    db: AsyncSession = Depends(get_db),
):
    """List all runs, optionally filtered by status."""
    query = select(Run).order_by(Run.created_at.desc())
    if status:
        query = query.where(Run.status == status)

    result = await db.execute(query)
    runs = result.scalars().all()

    # Build response with supervisor names
    response = []
    for run in runs:
        sup_result = await db.execute(select(Supervisor.name).where(Supervisor.id == run.supervisor_id))
        sup_name = sup_result.scalar_one_or_none()

        response.append(RunListResponse(
            id=run.id,
            supervisor_id=run.supervisor_id,
            order_id=run.order_id,
            status=run.status if isinstance(run.status, str) else run.status.value,
            next_wake_at=run.next_wake_at,
            created_at=run.created_at,
            updated_at=run.updated_at,
            supervisor_name=sup_name,
        ))

    return response


@router.get("/stats", response_model=DashboardStats)
async def get_dashboard_stats(db: AsyncSession = Depends(get_db)):
    """Get dashboard statistics."""
    # Total runs
    total_result = await db.execute(select(func.count(Run.id)))
    total_runs = total_result.scalar() or 0

    # Active runs
    active_result = await db.execute(
        select(func.count(Run.id)).where(
            Run.status.in_([RunStatus.RUNNING.value, RunStatus.SLEEPING.value, RunStatus.PAUSED.value])
        )
    )
    active_runs = active_result.scalar() or 0

    # Completed runs
    completed_result = await db.execute(
        select(func.count(Run.id)).where(
            Run.status.in_([RunStatus.COMPLETED.value, RunStatus.TERMINATED.value])
        )
    )
    completed_runs = completed_result.scalar() or 0

    # Total events
    events_result = await db.execute(
        select(func.count(Activity.id)).where(Activity.type == "event")
    )
    total_events = events_result.scalar() or 0

    # Total actions
    actions_result = await db.execute(
        select(func.count(Activity.id)).where(Activity.type == "agent_action")
    )
    total_actions = actions_result.scalar() or 0

    return DashboardStats(
        total_runs=total_runs,
        active_runs=active_runs,
        completed_runs=completed_runs,
        total_events=total_events,
        total_actions=total_actions,
    )


@router.get("/{run_id}", response_model=RunResponse)
async def get_run(run_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Get run details."""
    result = await db.execute(select(Run).where(Run.id == run_id))
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return run


@router.get("/{run_id}/activities", response_model=list[ActivityResponse])
async def get_run_activities(
    run_id: uuid.UUID,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    activity_type: str | None = Query(None, description="Filter by activity type"),
    db: AsyncSession = Depends(get_db),
):
    """Get activity log for a run."""
    # Verify run exists
    run_result = await db.execute(select(Run.id).where(Run.id == run_id))
    if not run_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Run not found")

    query = (
        select(Activity)
        .where(Activity.run_id == run_id)
        .order_by(Activity.created_at.asc())
        .offset(offset)
        .limit(limit)
    )
    if activity_type:
        query = query.where(Activity.type == activity_type)

    result = await db.execute(query)
    return result.scalars().all()


@router.post("/{run_id}/instructions", response_model=StatusResponse)
async def add_instruction(
    run_id: uuid.UUID,
    data: InstructionAdd,
    db: AsyncSession = Depends(get_db),
):
    """Add a run-specific instruction."""
    result = await db.execute(select(Run).where(Run.id == run_id))
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    if run.status in (RunStatus.COMPLETED.value, RunStatus.TERMINATED.value):
        raise HTTPException(status_code=400, detail="Cannot add instructions to a completed/terminated run")

    # Append instruction
    current = list(run.additional_instructions or [])
    current.append(data.instruction)
    run.additional_instructions = current

    # Record activity
    activity = Activity(
        run_id=run.id,
        type="instruction_added",
        subtype="user_instruction",
        content={"instruction": data.instruction},
    )
    db.add(activity)
    await db.commit()

    return StatusResponse(status="success", message="Instruction added to run context.")


@router.post("/{run_id}/pause", response_model=StatusResponse)
async def pause_run(run_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Pause a run."""
    result = await db.execute(select(Run).where(Run.id == run_id))
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    if run.status in (RunStatus.COMPLETED.value, RunStatus.TERMINATED.value):
        raise HTTPException(status_code=400, detail="Cannot pause a completed/terminated run")

    run.status = RunStatus.PAUSED.value

    activity = Activity(
        run_id=run.id,
        type="system",
        subtype="run_paused",
        content={"message": "Run paused by user."},
    )
    db.add(activity)
    await db.commit()

    # Cancel scheduled wake-up
    from app.scheduler import cancel_wake_up
    cancel_wake_up(run.id)

    return StatusResponse(status="success", message="Run paused.")


@router.post("/{run_id}/resume", response_model=StatusResponse)
async def resume_run(run_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Resume a paused run."""
    result = await db.execute(select(Run).where(Run.id == run_id))
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    if run.status != RunStatus.PAUSED.value:
        raise HTTPException(status_code=400, detail="Run is not paused")

    run.status = RunStatus.RUNNING.value

    activity = Activity(
        run_id=run.id,
        type="system",
        subtype="run_resumed",
        content={"message": "Run resumed by user."},
    )
    db.add(activity)
    await db.commit()

    # Trigger agent to re-evaluate
    asyncio.create_task(_run_agent_background(run.id, "run_resumed"))

    return StatusResponse(status="success", message="Run resumed.")


@router.post("/{run_id}/terminate", response_model=StatusResponse)
async def terminate_run(run_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Terminate a run and generate final summary."""
    result = await db.execute(select(Run).where(Run.id == run_id))
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    if run.status in (RunStatus.COMPLETED.value, RunStatus.TERMINATED.value):
        raise HTTPException(status_code=400, detail="Run is already completed/terminated")

    # Record termination
    activity = Activity(
        run_id=run.id,
        type="system",
        subtype="run_terminating",
        content={"message": "Run terminated by user. Generating final summary..."},
    )
    db.add(activity)
    await db.commit()

    # Cancel scheduled wake-up
    from app.scheduler import cancel_wake_up
    cancel_wake_up(run.id)

    # Generate final summary and complete
    from app.agent.runtime import generate_final_summary_and_complete
    asyncio.create_task(generate_final_summary_and_complete(run.id))

    return StatusResponse(status="success", message="Run termination initiated. Final summary being generated.")


async def _run_agent_background(run_id: uuid.UUID, trigger: str) -> None:
    """Run the agent in the background."""
    try:
        from app.agent.runtime import run_agent
        await run_agent(run_id, wake_trigger=trigger)
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Background agent error: {e}", exc_info=True)
