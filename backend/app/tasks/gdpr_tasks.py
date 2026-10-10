"""gdpr_tasks.py — background retention purge.

Registers a Celery task `purge_expired_task` against the existing `celery_app`
(see app/core/celery_app.py). Falls back to a plain callable if Celery is unavailable
so importing this module never breaks.

Scheduling (Celery beat) — add to app/core/celery_app.py:

    from celery.schedules import crontab
    celery_app.conf.beat_schedule = {
        "gdpr-purge-expired-daily": {
            "task": "app.tasks.gdpr_tasks.purge_expired_task",
            "schedule": crontab(hour=3, minute=0),   # daily at 03:00 UTC
        },
    }

and ensure "app.tasks.gdpr_tasks" is in the celery_app `include=[...]` list.
Then run a worker + beat:  celery -A app.core.celery_app.celery_app worker -B
"""
from __future__ import annotations

import asyncio
import logging

from app.services.gdpr_service import purge_expired

logger = logging.getLogger(__name__)


def _run_purge(retention_days: int | None = None) -> dict:
    """Platform-wide retention purge. Safe to call directly or from a Celery worker."""
    result = asyncio.run(purge_expired(retention_days=retention_days))
    logger.info("gdpr purge_expired result: %s", result)
    return result


try:
    from app.core.celery_app import celery_app

    @celery_app.task(name="app.tasks.gdpr_tasks.purge_expired_task")
    def purge_expired_task(retention_days: int | None = None) -> dict:
        """Celery task: anonymize candidates past the retention window (platform-wide)."""
        return _run_purge(retention_days)

except Exception:  # noqa: BLE001 — celery not configured; expose a plain callable instead
    logger.warning("Celery unavailable; purge_expired_task is a plain function (schedule via beat once configured).")

    def purge_expired_task(retention_days: int | None = None) -> dict:  # type: ignore[misc]
        """Fallback (no Celery): run the retention purge synchronously."""
        return _run_purge(retention_days)