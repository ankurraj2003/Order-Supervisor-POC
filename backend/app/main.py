"""FastAPI application entry point with lifespan management."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.scheduler import init_scheduler, check_expired_runs

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application startup and shutdown."""
    logger.info("Starting Order Supervisor backend...")

    # Initialize and start scheduler
    sched = init_scheduler()
    sched.start()
    logger.info("APScheduler started.")

    # Add periodic job to check for expired runs (every 5 minutes)
    sched.add_job(
        check_expired_runs,
        "interval",
        minutes=5,
        id="check_expired_runs",
        replace_existing=True,
    )

    yield

    # Shutdown
    sched.shutdown(wait=False)
    logger.info("APScheduler shut down.")
    logger.info("Order Supervisor backend stopped.")


app = FastAPI(
    title="Order Supervisor API",
    description="AI-powered long-running order supervision system",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000", 
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
from app.api.supervisors import router as supervisors_router
from app.api.runs import router as runs_router
from app.api.events import router as events_router

app.include_router(supervisors_router)
app.include_router(runs_router)
app.include_router(events_router)


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "order-supervisor"}
