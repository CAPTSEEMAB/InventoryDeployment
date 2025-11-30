import os
import boto3
from typing import List, Dict, Any
from pathlib import Path
from dotenv import load_dotenv

# Notification service helpers and factory for queuing product notifications
load_dotenv(dotenv_path=Path(__file__).resolve().parents[2] / ".env", override=True)


class NotificationService:
    # NotificationService: prepares and enqueues notifications for downstream delivery
    def __init__(self):
        # initialize the SQS-backed notification queue client
        from ..sqs.notification_queue import NotificationQueueService
        self.queue = NotificationQueueService()

    def notify(self, action: str, resource: str, data: Dict[str, Any], priority="normal"):
        # format a human-readable notification and enqueue it; returns True on success, False on failure
        try:
            name = data.get('name', data.get('id', 'Item'))
            subject = f"{resource.title()} {action.title()}: {name}"
            details = "\n".join([f"{k.replace('_', ' ').title()}: {v}" for k, v in data.items()])
            message = f"{resource.upper()} {action.upper()}\n\n{details}"
            
            from ..sqs.interfaces import NotificationPayload
            payload = NotificationPayload(
                recipient_email="all_subscribers", 
                subject=subject,
                message=message,
                notification_type="broadcast"
            )
            self.queue.queue_notification(payload, priority=priority)
            print(f"Notification queued: {subject}")
            return True
        except Exception as e:
            # log failure and return False so callers can continue
            print(f"Failed to queue notification: {e}")
            return False


_service = None

def get_notification_service():
    # return shared NotificationService instance
    global _service
    if not _service:
        _service = NotificationService()
    return _service