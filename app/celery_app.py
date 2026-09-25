"""Celery application shared by the web app (enqueue, read results) and the worker (run tasks).

Kept free of heavy imports: the web process uses it to send tasks by name and read their
results without loading pdfplumber, the LLM SDKs or SQLAlchemy.
"""

from typing import Any

from celery import Celery

from app.config import Settings, get_settings

PROCESS_DOCUMENT_TASK = "process_document"
SWEEP_ORPHANS_TASK = "sweep_orphan_uploads"
RECONCILE_SUBSCRIPTIONS_TASK = "reconcile_subscriptions"


def celery_config(settings: Settings) -> dict[str, Any]:
    return {
        "broker_url": settings.celery_broker_url,
        "result_backend": settings.celery_result_backend,
        "result_expires": settings.result_ttl_seconds,  # ephemeral data disappears from Redis after this
        "task_track_started": True,  # reports STARTED, so the UI can show "Processing"
        "task_acks_late": True,  # a task is removed from the queue only after it finishes
        "worker_prefetch_multiplier": 1,  # never reserve more than the task in progress
        "task_serializer": "json",
        "result_serializer": "json",
        "accept_content": ["json"],  # never unpickle messages
        "broker_connection_retry_on_startup": True,
        # A PDF built to make the parser loop forever is stopped: the soft limit raises inside the
        # task (it fails cleanly and gives its pages back), the hard one kills the child if needed.
        "task_soft_time_limit": 300,
        "task_time_limit": 330,
        # Embedded beat (worker --beat): the orphan sweep every 30 minutes, and a check of PayPal
        # subscriptions every 6 hours in case a webhook was lost.
        "beat_schedule": {
            "sweep-orphan-uploads": {"task": SWEEP_ORPHANS_TASK, "schedule": 30 * 60},
            "reconcile-subscriptions": {"task": RECONCILE_SUBSCRIPTIONS_TASK, "schedule": 6 * 3600},
        },
    }


celery_app = Celery("pdf_process_pipeline")
# A callable is evaluated lazily: .env is read when Celery first needs its config, not on import.
celery_app.add_defaults(lambda: celery_config(get_settings()))
