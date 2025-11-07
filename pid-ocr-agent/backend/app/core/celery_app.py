"""
Celery Application Configuration
For autonomous task processing
"""
from celery import Celery
from app.config.settings import settings

# Create Celery app
celery_app = Celery(
    "pid_ocr_agent",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "app.core.tasks"
    ]
)

# Configure Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hour hard limit
    task_soft_time_limit=3000,  # 50 minutes soft limit
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=100,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    result_expires=86400,  # Results expire after 24 hours
)

# Task routes (can be extended for different queues)
celery_app.conf.task_routes = {
    "app.core.tasks.process_pid_document": {"queue": "ocr"},
    "app.core.tasks.generate_hazop": {"queue": "hazop"},
    "app.core.tasks.generate_instrument_index": {"queue": "instruments"},
    "app.core.tasks.export_documents": {"queue": "exports"},
}

# Beat schedule for periodic tasks (optional)
celery_app.conf.beat_schedule = {
    "cleanup-old-documents": {
        "task": "app.core.tasks.cleanup_old_documents",
        "schedule": 86400.0,  # Once per day
    },
}
