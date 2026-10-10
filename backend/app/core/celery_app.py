"""celery_app.py — Celery application with Redis broker"""
from celery import Celery
from celery.schedules import crontab
from app.core.config import settings

celery_app = Celery(
    "interview_platform",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.tasks.gdpr_tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    result_expires=3600,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    task_track_started=True,
    # Scheduled jobs (run a beat worker: celery -A app.core.celery_app worker -B)
    beat_schedule={
        "gdpr-purge-expired-daily": {
            "task": "app.tasks.gdpr_tasks.purge_expired_task",
            "schedule": crontab(hour=3, minute=0),  # daily 03:00 UTC
        },
    },
)
