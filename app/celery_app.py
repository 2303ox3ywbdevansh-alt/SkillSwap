import os
from celery import Celery

celery = Celery(
    "skillswap",
    broker=os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/1"),
    backend=os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/2"),
)
celery.conf.update(task_track_started=True, task_serializer="json", result_serializer="json", accept_content=["json"], timezone="UTC", enable_utc=True)


@celery.task(name="skillswap.ping")
def ping():
    return "SkillSwap worker is ready"
