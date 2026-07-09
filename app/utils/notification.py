import os
import json
from flask import current_app
from ..models.notification import Notification
from ..models.push_subscription import PushSubscription
from ..extensions import db
from ..utils.logging import get_logger
from pywebpush import webpush, WebPushException

logger = get_logger(__name__)

def send_web_push(subscription, payload):
    """
    Send a web push notification to a specific subscription.
    """
    try:
        webpush(
            subscription_info={
                "endpoint": subscription.endpoint,
                "keys": {
                    "p256dh": subscription.p256dh,
                    "auth": subscription.auth
                }
            },
            data=json.dumps(payload),
            vapid_private_key=os.environ.get("VAPID_PRIVATE_KEY"),
            vapid_claims={"sub": os.environ.get("VAPID_CLAIM_EMAIL", "mailto:admin@camanage.com")}
        )
        return True
    except WebPushException as ex:
        logger.error(f"Web push failed: {repr(ex)}")
        if ex.response and ex.response.status_code in [404, 410]:
            # Subscription is no longer valid, delete it
            db.session.delete(subscription)
            db.session.commit()
            logger.info("Deleted expired web push subscription.")
        return False
    except Exception as e:
        logger.error(f"Web push error: {str(e)}")
        return False

def create_notification(user_id, message, link=None, title=None, category='system', priority='normal', entity_type=None, entity_id=None):
    """
    Creates an in-app notification and attempts to send a Web Push notification to all
    registered devices for the user.
    """
    try:
        # Create In-App Notification
        notification = Notification(
            user_id=user_id,
            title=title,
            message=message,
            category=category,
            priority=priority,
            entity_type=entity_type,
            entity_id=str(entity_id) if entity_id else None,
            link=link
        )
        db.session.add(notification)
        db.session.commit()
        
        # Prepare Push Payload
        payload = {
            "title": title or "Sumit N Garg & Associates Notification",
            "body": message,
            "url": link or "/"
        }
        
        # Send Web Push to all devices
        subscriptions = PushSubscription.query.filter_by(user_id=user_id).all()
        for sub in subscriptions:
            send_web_push(sub, payload)
            
        logger.info(f"[NOTIFICATION] Sent to user_id={user_id} category={category}")
    except Exception as e:
        logger.error(f"Failed to create notification: {e}")

def notify_admins(message, link=None, title=None, category='system', priority='normal', entity_type=None, entity_id=None):
    """
    Sends a notification to all active administrators.
    """
    from ..models.user import User
    admins = User.query.filter_by(role=User.ROLE_ADMIN, is_active=True).all()
    for admin in admins:
        create_notification(
            admin.id, message, link=link, title=title, 
            category=category, priority=priority, 
            entity_type=entity_type, entity_id=entity_id
        )
