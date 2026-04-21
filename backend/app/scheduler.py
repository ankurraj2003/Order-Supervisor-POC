"""APScheduler setup for scheduled wake-ups."""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.triggers.date import DateTrigger

from app.config import get_settings

logger = logging.getLogger(__name__)

# Global scheduler instance
scheduler: AsyncIOScheduler | None = None


def init_scheduler() -> AsyncIOScheduler:
    """Initialize and return the APScheduler instance."""
    global scheduler
    settings = get_settings()

    jobstores = {
        "default": SQLAlchemyJobStore(url=settings.DATABASE_URL_SYNC)
    }

    scheduler = AsyncIOScheduler(
        jobstores=jobstores,
        job_defaults={
            "coalesce": True,
            "max_instances": 1,
            "misfire_grace_time": 300,  # 5 minutes grace for missed jobs
        },
    )
    return scheduler


def get_scheduler() -> AsyncIOScheduler | None:
    return scheduler


def schedule_wake_up(run_id: uuid.UUID, wake_at: datetime) -> None:
    """Schedule a wake-up job for a run."""
    global scheduler
    if not scheduler:
        logger.warning("Scheduler not initialized, cannot schedule wake-up")
        return

    job_id = f"wake_{run_id}"

    # Remove existing job if any
    try:
        scheduler.remove_job(job_id)
    except Exception:
        pass

    # Ensure wake_at is timezone-aware
    if wake_at.tzinfo is None:
        wake_at = wake_at.replace(tzinfo=timezone.utc)

    # Don't schedule in the past
    now = datetime.now(timezone.utc)
    if wake_at <= now:
        # Wake immediately
        logger.info(f"Wake time for run {run_id} is in the past, waking immediately")
        asyncio.create_task(_wake_run(run_id))
        return

    scheduler.add_job(
        _wake_run,
        trigger=DateTrigger(run_date=wake_at),
        id=job_id,
        args=[run_id],
        replace_existing=True,
    )
    logger.info(f"Scheduled wake-up for run {run_id} at {wake_at.isoformat()}")


def cancel_wake_up(run_id: uuid.UUID) -> None:
    """Cancel a scheduled wake-up for a run."""
    global scheduler
    if not scheduler:
        return

    job_id = f"wake_{run_id}"
    try:
        scheduler.remove_job(job_id)
        logger.info(f"Cancelled wake-up for run {run_id}")
    except Exception:
        pass


async def _wake_run(run_id: uuid.UUID) -> None:
    """Callback executed when a scheduled wake-up fires."""
    logger.info(f"Scheduled wake-up firing for run {run_id}")
    from app.agent.runtime import run_agent
    await run_agent(run_id, wake_trigger="scheduled_wake")


async def check_expired_runs() -> None:
    """Periodic job to check for runs that have exceeded max age."""
    from app.database import AsyncSessionLocal
    from app.models import Run, RunStatus, Activity
    from app.config import get_settings
    from sqlalchemy import select

    settings = get_settings()

    async with AsyncSessionLocal() as db:
        now = datetime.now(timezone.utc)

        result = await db.execute(
            select(Run).where(
                Run.status.in_([RunStatus.RUNNING.value, RunStatus.SLEEPING.value]),
                Run.max_end_at <= now,
            )
        )
        expired_runs = result.scalars().all()

        for run in expired_runs:
            logger.info(f"Run {run.id} has exceeded max age, completing...")
            activity = Activity(
                run_id=run.id,
                type="system",
                subtype="max_age_reached",
                content={"message": "Run exceeded maximum age limit and is being completed."},
            )
            db.add(activity)
            await db.commit()

            from app.agent.runtime import generate_final_summary_and_complete
            await generate_final_summary_and_complete(run.id)
