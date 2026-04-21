"""SQLAlchemy ORM models for the Order Supervisor system."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    String,
    Text,
    DateTime,
    ForeignKey,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.orm import relationship
import enum

from app.database import Base


class RunStatus(str, enum.Enum):
    RUNNING = "running"
    SLEEPING = "sleeping"
    PAUSED = "paused"
    COMPLETED = "completed"
    TERMINATED = "terminated"


def utcnow():
    return datetime.now(timezone.utc)


class Supervisor(Base):
    __tablename__ = "supervisors"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    base_instruction = Column(Text, nullable=False)
    available_actions = Column(JSONB, nullable=False, default=list)
    default_wake_behavior = Column(JSONB, nullable=True, default=dict)
    model_config_data = Column("model_config", JSONB, nullable=True, default=dict)
    wake_guidance = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    # Relationships
    runs = relationship("Run", back_populates="supervisor", lazy="selectin")


class Run(Base):
    __tablename__ = "runs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    supervisor_id = Column(UUID(as_uuid=True), ForeignKey("supervisors.id"), nullable=False)
    order_id = Column(String(255), nullable=False)
    status = Column(
        String(20),
        nullable=False,
        default=RunStatus.RUNNING.value,
    )
    state = Column(JSONB, nullable=False, default=dict)
    wake_guidance = Column(Text, nullable=True)
    additional_instructions = Column(ARRAY(Text), nullable=False, default=list)
    next_wake_at = Column(DateTime(timezone=True), nullable=True)
    max_end_at = Column(DateTime(timezone=True), nullable=True)
    final_summary = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    # Relationships
    supervisor = relationship("Supervisor", back_populates="runs", lazy="selectin")
    activities = relationship("Activity", back_populates="run", lazy="selectin", order_by="Activity.created_at")


class Activity(Base):
    __tablename__ = "activities"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id = Column(UUID(as_uuid=True), ForeignKey("runs.id"), nullable=False)
    type = Column(String(50), nullable=False)  # event, wake_decision, sleep_decision, agent_action, agent_reasoning, instruction_added, state_update, final_output, system
    subtype = Column(String(100), nullable=True)  # e.g. message_customer, payment_confirmed, sleep_until
    content = Column(JSONB, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    # Relationships
    run = relationship("Run", back_populates="activities")
