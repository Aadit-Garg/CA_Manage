from flask import current_app
from ..models.timeline import TimelineEvent
from ..extensions import db
from ..utils.logging import get_logger

logger = get_logger(__name__)

def create_timeline_event(client_id, event_type, description, user_id=None, document_id=None):
    """
    Creates a standardized timeline event for a client.
    
    Args:
        client_id (int): ID of the client to attach the event to.
        event_type (str): Short, standardized string categorizing the event.
        description (str): Human-readable description of the event.
        user_id (int, optional): ID of the user who performed the action.
        document_id (int, optional): ID of the related document.
    """
    try:
        event = TimelineEvent(
            client_id=client_id,
            event_type=event_type,
            description=description,
            performed_by_id=user_id,
            document_id=document_id
        )
        db.session.add(event)
        # We don't commit here so that the calling function can commit everything in one transaction,
        # ensuring the event and the actual action succeed or fail together.
        
        logger.info(f"[TIMELINE] client_id={client_id} event={event_type} user_id={user_id}")
    except Exception as e:
        logger.error(f"Failed to create timeline event: {e}")
        # Note: we do not raise the exception to prevent timeline tracking from crashing main logic
