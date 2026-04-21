"""Supervisor CRUD API endpoints."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Supervisor
from app.schemas import SupervisorCreate, SupervisorUpdate, SupervisorResponse

router = APIRouter(prefix="/api/supervisors", tags=["supervisors"])

# Default supervisor templates that get seeded
DEFAULT_SUPERVISORS = [
    {
        "name": "Standard Order Supervisor",
        "base_instruction": (
            "You are a balanced order supervisor. Monitor the order lifecycle, "
            "take action when genuinely needed, but avoid over-intervening. "
            "Prioritize customer satisfaction while maintaining operational efficiency. "
            "Escalate issues only when they require human attention. "
            "Sleep for reasonable intervals (15-30 minutes) when waiting for expected events."
        ),
        "available_actions": [
            "message_fulfillment_team",
            "message_payments_team",
            "message_logistics_team",
            "message_customer",
            "create_internal_note",
        ],
        "default_wake_behavior": {
            "wake_interval_minutes": 30,
            "aggressiveness": "balanced",
        },
        "model_config_data": {"model": "llama-3.3-70b-versatile", "temperature": 0.3},
        "wake_guidance": (
            "Wake me for: payment issues, shipment delays, customer messages, "
            "delivery confirmations. Let me sleep through: routine status pings, "
            "minor updates that don't change the order trajectory."
        ),
    },
    {
        "name": "High-Priority Supervisor",
        "base_instruction": (
            "You are a high-priority order supervisor for VIP or time-sensitive orders. "
            "Be proactive and aggressive in monitoring. Escalate early rather than late. "
            "Message teams promptly when there are any delays or issues. "
            "Keep the customer informed at every significant milestone. "
            "Sleep for short intervals (5-10 minutes) to stay on top of the situation."
        ),
        "available_actions": [
            "message_fulfillment_team",
            "message_payments_team",
            "message_logistics_team",
            "message_customer",
            "create_internal_note",
        ],
        "default_wake_behavior": {
            "wake_interval_minutes": 10,
            "aggressiveness": "high",
        },
        "model_config_data": {"model": "llama-3.3-70b-versatile", "temperature": 0.2},
        "wake_guidance": (
            "Wake me for ALL events. This is a high-priority order and I need to "
            "be aware of every update. Only skip routine system heartbeats."
        ),
    },
]


@router.get("", response_model=list[SupervisorResponse])
async def list_supervisors(db: AsyncSession = Depends(get_db)):
    """List all supervisor configurations."""
    result = await db.execute(select(Supervisor).order_by(Supervisor.created_at.desc()))
    supervisors = result.scalars().all()

    # Seed defaults if none exist
    if not supervisors:
        for template in DEFAULT_SUPERVISORS:
            sup = Supervisor(**template)
            db.add(sup)
        await db.commit()

        result = await db.execute(select(Supervisor).order_by(Supervisor.created_at.desc()))
        supervisors = result.scalars().all()

    return supervisors


@router.get("/{supervisor_id}", response_model=SupervisorResponse)
async def get_supervisor(supervisor_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Get a supervisor configuration by ID."""
    result = await db.execute(select(Supervisor).where(Supervisor.id == supervisor_id))
    supervisor = result.scalar_one_or_none()
    if not supervisor:
        raise HTTPException(status_code=404, detail="Supervisor not found")
    return supervisor


@router.post("", response_model=SupervisorResponse, status_code=201)
async def create_supervisor(data: SupervisorCreate, db: AsyncSession = Depends(get_db)):
    """Create a new supervisor configuration."""
    supervisor = Supervisor(
        name=data.name,
        base_instruction=data.base_instruction,
        available_actions=data.available_actions,
        default_wake_behavior=data.default_wake_behavior,
        model_config_data=data.model_config_data,
        wake_guidance=data.wake_guidance,
    )
    db.add(supervisor)
    await db.commit()
    await db.refresh(supervisor)
    return supervisor


@router.put("/{supervisor_id}", response_model=SupervisorResponse)
async def update_supervisor(
    supervisor_id: uuid.UUID,
    data: SupervisorUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update a supervisor configuration."""
    result = await db.execute(select(Supervisor).where(Supervisor.id == supervisor_id))
    supervisor = result.scalar_one_or_none()
    if not supervisor:
        raise HTTPException(status_code=404, detail="Supervisor not found")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(supervisor, key, value)

    await db.commit()
    await db.refresh(supervisor)
    return supervisor
