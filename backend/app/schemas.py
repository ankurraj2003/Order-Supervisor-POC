"""Pydantic schemas for API request/response models."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


# ── Supervisor Schemas ──────────────────────────────────────────────────────

class SupervisorCreate(BaseModel):
    name: str
    base_instruction: str
    available_actions: list[str] = Field(default_factory=lambda: [
        "message_fulfillment_team",
        "message_payments_team",
        "message_logistics_team",
        "message_customer",
        "create_internal_note",
    ])
    default_wake_behavior: dict[str, Any] | None = None
    model_config_data: dict[str, Any] | None = None
    wake_guidance: str | None = None


class SupervisorUpdate(BaseModel):
    name: str | None = None
    base_instruction: str | None = None
    available_actions: list[str] | None = None
    default_wake_behavior: dict[str, Any] | None = None
    model_config_data: dict[str, Any] | None = None
    wake_guidance: str | None = None


class SupervisorResponse(BaseModel):
    id: uuid.UUID
    name: str
    base_instruction: str
    available_actions: list[str]
    default_wake_behavior: dict[str, Any] | None
    model_config_data: dict[str, Any] | None
    wake_guidance: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Run Schemas ─────────────────────────────────────────────────────────────

class RunCreate(BaseModel):
    supervisor_id: uuid.UUID
    order_id: str
    initial_context: dict[str, Any] | None = None


class RunResponse(BaseModel):
    id: uuid.UUID
    supervisor_id: uuid.UUID
    order_id: str
    status: str
    state: dict[str, Any]
    wake_guidance: str | None
    additional_instructions: list[str]
    next_wake_at: datetime | None
    max_end_at: datetime | None
    final_summary: dict[str, Any] | None
    created_at: datetime
    updated_at: datetime
    supervisor: SupervisorResponse | None = None

    model_config = {"from_attributes": True}


class RunListResponse(BaseModel):
    id: uuid.UUID
    supervisor_id: uuid.UUID
    order_id: str
    status: str
    next_wake_at: datetime | None
    created_at: datetime
    updated_at: datetime
    supervisor_name: str | None = None

    model_config = {"from_attributes": True}


# ── Activity Schemas ────────────────────────────────────────────────────────

class ActivityResponse(BaseModel):
    id: uuid.UUID
    run_id: uuid.UUID
    type: str
    subtype: str | None
    content: dict[str, Any]
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Event Schemas ───────────────────────────────────────────────────────────

class EventInject(BaseModel):
    event_type: str
    payload: dict[str, Any] = Field(default_factory=dict)


class InstructionAdd(BaseModel):
    instruction: str


# ── Simulator Schemas ───────────────────────────────────────────────────────

class SimulatorScenario(BaseModel):
    scenario: str = "happy_path"  # happy_path, delayed_shipment, payment_failure, refund


# ── Generic Responses ───────────────────────────────────────────────────────

class StatusResponse(BaseModel):
    status: str
    message: str


class DashboardStats(BaseModel):
    total_runs: int
    active_runs: int
    completed_runs: int
    total_events: int
    total_actions: int
