"""
Celery application configuration.

Initializes the Celery app with broker and backend settings from environment variables.
"""

import os
from celery import Celery

# Get broker URL from environment or use default
broker_url = os.getenv(
    "CELERY_BROKER_URL",
    "amqp://analyzer:analyzer@rabbitmq:5672//"
)

# Create Celery app
celery_app = Celery("repo_analyzer")

# Configure Celery
celery_app.conf.update(
    broker_url=broker_url,
    result_backend="rpc://",  # Use RabbitMQ as result backend
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes hard limit
    task_soft_time_limit=28 * 60,  # 28 minutes soft limit
)

# Auto-discover tasks
celery_app.autodiscover_tasks(["src.scheduler"])
