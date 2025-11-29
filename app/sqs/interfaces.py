from typing import Dict, Any, Optional
from pydantic import BaseModel
from datetime import datetime


class QueueMessage(BaseModel):
    id: str
    message_type: str
    payload: Dict[str, Any]
    retry_count: int = 0
    max_retries: int = 3
    created_at: datetime
    processed_at: Optional[datetime] = None
    error_message: Optional[str] = None


class NotificationPayload(BaseModel):
    recipient_email: str
    subject: str
    message: str
    notification_type: str = "product_notification"
    product_data: Optional[Dict[str, Any]] = None
    user_data: Optional[Dict[str, Any]] = None


class QueueStats(BaseModel):
    queue_name: str
    visible_messages: int
    in_flight_messages: int
    delayed_messages: int = 0
    dead_letter_messages: int = 0
    created_timestamp: Optional[datetime] = None