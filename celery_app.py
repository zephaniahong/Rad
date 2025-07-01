import os
from celery import Celery
from google_calendar_sync import get_google_sync_instance
import logging

# Celery configuration
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")

# Create Celery app
celery_app = Celery(
    "radicale_sync",
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND,
    include=["google_calendar_sync"],
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
    beat_schedule={
        "refresh-google-calendar-webhook": {
            "task": "celery_app.refresh_google_calendar_webhook",
            "schedule": 6 * 24 * 60 * 60,  # Every 6 days (in seconds)
        },
        "periodic-sync-task": {
            "task": "celery_app.periodic_sync_task",
            "schedule": 5 * 60,  # Every 5 minutes (in seconds)
        },
    },
)

logger = logging.getLogger(__name__)


@celery_app.task(bind=True)
def process_google_calendar_notification(
    self, notification_data, username, calendar_name
):
    """Background task to process Google Calendar notifications"""
    try:
        google_sync = get_google_sync_instance()
        result = google_sync.process_google_notification(
            notification_data, username, calendar_name
        )
        return {"success": result, "task_id": self.request.id}
    except FileNotFoundError as e:
        # Handle missing credentials file
        logger.error(f"Authentication failed - missing credentials: {str(e)}")
        return {
            "success": False,
            "error": "Missing Google Calendar credentials. Please run 'python setup_google_calendar.py' and configure credentials.json",
            "task_id": self.request.id,
        }
    except RuntimeError as e:
        # Handle OAuth flow issues in containers
        if "OAuth flow not supported" in str(e):
            logger.error(f"OAuth authentication failed in container: {str(e)}")
            return {
                "success": False,
                "error": "OAuth authentication not supported in container. Please authenticate outside container and copy token.json",
                "task_id": self.request.id,
            }
        else:
            raise
    except Exception as e:
        # Log the full error for debugging
        logger.error(f"Failed to process Google Calendar notification: {str(e)}")
        import traceback

        logger.error(f"Full traceback: {traceback.format_exc()}")

        # Check for specific authentication errors
        error_str = str(e).lower()
        if any(
            auth_error in error_str
            for auth_error in [
                "invalid_client",
                "unauthorized",
                "invalid_scope",
                "bad request",
                "invalid_grant",
            ]
        ):
            # Don't retry authentication errors - they need manual intervention
            logger.error(f"Authentication error detected: {str(e)}")
            return {
                "success": False,
                "error": f"Authentication error: {str(e)}. Please check your Google Calendar credentials and token.",
                "task_id": self.request.id,
                "needs_manual_intervention": True,
            }
        else:
            # Retry other errors (network issues, temporary API problems, etc.)
            # But limit retries to avoid infinite loops
            if self.request.retries >= 2:
                logger.error(f"Max retries reached for task {self.request.id}")
                return {
                    "success": False,
                    "error": f"Max retries reached: {str(e)}",
                    "task_id": self.request.id,
                }
            logger.info(f"Retrying task due to error: {str(e)}")
            raise self.retry(countdown=60, max_retries=2, exc=e)


@celery_app.task(bind=True)
def sync_google_calendar_to_radicale(
    self, username, calendar_name, calendar_id="primary"
):
    """Background task to sync Google Calendar to Radicale"""
    try:
        google_sync = get_google_sync_instance()

        # Use incremental sync for better performance
        events = google_sync.get_calendar_events_incremental(calendar_id)

        synced_count = 0
        for event in events:
            if google_sync.sync_event_to_radicale(event, username, calendar_name):
                synced_count += 1

        return {
            "success": True,
            "synced_events": synced_count,
            "total_events": len(events),
            "task_id": self.request.id,
            "sync_type": "incremental",
        }
    except FileNotFoundError as e:
        # Handle missing credentials file
        logger.error(f"Authentication failed - missing credentials: {str(e)}")
        return {
            "success": False,
            "error": "Missing Google Calendar credentials. Please run 'python setup_google_calendar.py' and configure credentials.json",
            "task_id": self.request.id,
        }
    except RuntimeError as e:
        # Handle OAuth flow issues in containers
        if "OAuth flow not supported" in str(e):
            logger.error(f"OAuth authentication failed in container: {str(e)}")
            return {
                "success": False,
                "error": "OAuth authentication not supported in container. Please authenticate outside container and copy token.json",
                "task_id": self.request.id,
            }
        else:
            raise
    except Exception as e:
        # Log the full error for debugging
        logger.error(f"Failed to sync Google Calendar: {str(e)}")
        import traceback

        logger.error(f"Full traceback: {traceback.format_exc()}")

        # Check for specific authentication errors
        error_str = str(e).lower()
        if any(
            auth_error in error_str
            for auth_error in [
                "invalid_client",
                "unauthorized",
                "invalid_scope",
                "bad request",
                "invalid_grant",
            ]
        ):
            # Don't retry authentication errors - they need manual intervention
            logger.error(f"Authentication error detected: {str(e)}")
            return {
                "success": False,
                "error": f"Authentication error: {str(e)}. Please check your Google Calendar credentials and token.",
                "task_id": self.request.id,
                "needs_manual_intervention": True,
            }
        else:
            # Retry other errors (network issues, temporary API problems, etc.)
            # But limit retries to avoid infinite loops
            if self.request.retries >= 2:
                logger.error(f"Max retries reached for task {self.request.id}")
                return {
                    "success": False,
                    "error": f"Max retries reached: {str(e)}",
                    "task_id": self.request.id,
                }
            logger.info(f"Retrying task due to error: {str(e)}")
            raise self.retry(countdown=60, max_retries=2, exc=e)


@celery_app.task(bind=True)
def refresh_google_calendar_webhook(self):
    """Scheduled task to refresh Google Calendar webhook before expiration"""
    try:
        logger.info("Refreshing Google Calendar webhook...")
        google_sync = get_google_sync_instance()

        # Setup new webhook
        result = google_sync.setup_webhook()

        logger.info(f"Successfully refreshed webhook: {result}")
        return {
            "success": True,
            "webhook_url": result["webhook_url"],
            "resource_id": result["resource_id"],
            "expiration": result["expiration"],
            "task_id": self.request.id,
        }
    except Exception as e:
        logger.error(f"Failed to refresh Google Calendar webhook: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "task_id": self.request.id,
        }


@celery_app.task(bind=True)
def periodic_sync_task(self):
    """Periodic task that runs every 5 minutes"""
    try:
        logger.info("Running periodic sync task...")

        # Get default configuration from environment
        username = os.getenv("DEFAULT_RADICALE_USER", "admin")
        calendar_name = os.getenv("DEFAULT_CALENDAR_NAME", "default")
        calendar_id = "primary"

        # Perform the sync
        google_sync = get_google_sync_instance()
        events = google_sync.get_calendar_events_incremental(calendar_id)

        synced_count = 0
        for event in events:
            if google_sync.sync_event_to_radicale(event, username, calendar_name):
                synced_count += 1

        logger.info(f"Periodic sync completed: {synced_count} events synced")

        from datetime import datetime, timezone

        return {
            "success": True,
            "synced_events": synced_count,
            "total_events": len(events),
            "task_id": self.request.id,
            "sync_type": "periodic",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    except FileNotFoundError as e:
        logger.error(f"Authentication failed - missing credentials: {str(e)}")
        return {
            "success": False,
            "error": "Missing Google Calendar credentials. Please run 'python setup_google_calendar.py' and configure credentials.json",
            "task_id": self.request.id,
        }
    except RuntimeError as e:
        if "OAuth flow not supported" in str(e):
            logger.error(f"OAuth authentication failed in container: {str(e)}")
            return {
                "success": False,
                "error": "OAuth authentication not supported in container. Please authenticate outside container and copy token.json",
                "task_id": self.request.id,
            }
        else:
            raise
    except Exception as e:
        logger.error(f"Failed to run periodic sync task: {str(e)}")
        import traceback

        logger.error(f"Full traceback: {traceback.format_exc()}")

        # Check for specific authentication errors
        error_str = str(e).lower()
        if any(
            auth_error in error_str
            for auth_error in [
                "invalid_client",
                "unauthorized",
                "invalid_scope",
                "bad request",
                "invalid_grant",
            ]
        ):
            logger.error(f"Authentication error detected: {str(e)}")
            return {
                "success": False,
                "error": f"Authentication error: {str(e)}. Please check your Google Calendar credentials and token.",
                "task_id": self.request.id,
                "needs_manual_intervention": True,
            }
        else:
            # Retry other errors (network issues, temporary API problems, etc.)
            if self.request.retries >= 2:
                logger.error(f"Max retries reached for task {self.request.id}")
                return {
                    "success": False,
                    "error": f"Max retries reached: {str(e)}",
                    "task_id": self.request.id,
                }
            logger.info(f"Retrying task due to error: {str(e)}")
            raise self.retry(countdown=60, max_retries=2, exc=e)
