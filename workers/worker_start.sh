#!/bin/bash
# Celery Worker Startup Script
# This script starts a Celery worker with appropriate configuration

set -e

# Default values
CONCURRENCY=${CELERY_WORKER_CONCURRENCY:-4}
LOG_LEVEL=${LOG_LEVEL:-INFO}
QUEUES=${CELERY_QUEUES:-default,extraction,analysis}

echo "Starting Celery worker..."
echo "  Concurrency: $CONCURRENCY"
echo "  Log Level: $LOG_LEVEL"
echo "  Queues: $QUEUES"

exec celery -A src.tasks worker \
    --loglevel="$LOG_LEVEL" \
    --concurrency="$CONCURRENCY" \
    --queues="$QUEUES" \
    --hostname="worker@%h"
