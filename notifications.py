import logging

logger = logging.getLogger(__name__)

def send_alert(title: str, message: str, severity: str = "info"):
    """
    Send an alert notification.
    """
    logger.info(f"ALERT [{severity}] {title}: {message}")
    # Placeholder for email/slack integration