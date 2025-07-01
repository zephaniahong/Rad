import os
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any, Union
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import vobject
import caldav
from pydantic import BaseModel
import time
import json
from enum import Enum

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Google Calendar API configuration
SCOPES = [
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/calendar.events",
]
CREDENTIALS_FILE = "credentials.json"
TOKEN_FILE = "token.json"
SYNC_TOKENS_FILE = "sync_tokens.json"  # New file to store sync tokens per calendar


class GoogleCalendarResourceState(Enum):
    SYNC = "sync"
    EXISTS = "exists"
    NOT_EXISTS = "not_exists"


class GoogleCalendarEvent(BaseModel):
    id: str
    summary: str
    description: Optional[str] = None
    start: datetime
    end: datetime
    location: Optional[str] = None
    status: str
    html_link: str


class GoogleCalendarSync:
    def __init__(
        self, radicale_url: str, radicale_username: str, radicale_password: str
    ):
        self.radicale_url = radicale_url
        self.radicale_username = radicale_username
        self.radicale_password = radicale_password
        self.service = None
        self.sync_tokens = self._load_sync_tokens()

    def _load_sync_tokens(self) -> Dict[str, str]:
        """Load sync tokens from file"""
        try:
            if os.path.exists(SYNC_TOKENS_FILE):
                with open(SYNC_TOKENS_FILE, "r") as f:
                    tokens = json.load(f)
                    logger.info(
                        f"Loaded {len(tokens)} sync tokens from {SYNC_TOKENS_FILE}"
                    )
                    return tokens
            else:
                logger.info(
                    f"Sync tokens file {SYNC_TOKENS_FILE} does not exist, starting fresh"
                )
        except Exception as e:
            logger.warning(f"Failed to load sync tokens: {e}")
        return {}

    def _save_sync_tokens(self):
        """Save sync tokens to file with atomic write to handle concurrent access"""
        try:
            import tempfile
            import shutil

            # Write to temporary file first
            temp_file = tempfile.NamedTemporaryFile(mode="w", delete=False)
            json.dump(self.sync_tokens, temp_file, indent=2)
            temp_file.close()

            # Atomically move to final location
            shutil.move(temp_file.name, SYNC_TOKENS_FILE)
            logger.debug(f"Successfully saved sync tokens to {SYNC_TOKENS_FILE}")
        except Exception as e:
            logger.error(f"Failed to save sync tokens: {e}")
            # Clean up temp file if it exists
            try:
                os.unlink(temp_file.name)
            except:
                pass

    def _get_sync_token(self, calendar_id: str) -> Optional[str]:
        """Get sync token for a specific calendar"""
        return self.sync_tokens.get(calendar_id)

    def _set_sync_token(self, calendar_id: str, sync_token: str):
        """Set sync token for a specific calendar"""
        old_token = self.sync_tokens.get(calendar_id)
        self.sync_tokens[calendar_id] = sync_token
        self._save_sync_tokens()
        logger.info(
            f"Updated sync token for calendar '{calendar_id}': {old_token[:20] if old_token else 'None'}... -> {sync_token[:20]}..."
        )

    def authenticate_google(self):
        """Authenticate with Google Calendar API"""
        creds = None

        # Load existing token if it exists and is a file
        if os.path.exists(TOKEN_FILE) and os.path.isfile(TOKEN_FILE):
            try:
                creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
                logger.info("Loaded existing token from file")
            except Exception as e:
                logger.warning(f"Failed to load existing token: {e}")
                # Remove invalid token file
                try:
                    os.remove(TOKEN_FILE)
                except:
                    pass
                creds = None

        # If no valid credentials available, let user log in
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                    logger.info("Refreshed expired token")
                except Exception as e:
                    logger.warning(f"Failed to refresh token: {e}")
                    # Try to remove the invalid token file
                    try:
                        os.remove(TOKEN_FILE)
                    except:
                        pass
                    creds = None

            if not creds:
                if not os.path.exists(CREDENTIALS_FILE):
                    logger.error(
                        f"Credentials file '{CREDENTIALS_FILE}' not found. "
                        "Please download it from Google Cloud Console and place it in the project root.\n"
                        "Make sure to configure the redirect URI as 'http://localhost:8080/' in your OAuth credentials.\n"
                        "You can run 'python setup_google_calendar.py' to create a template."
                    )
                    raise FileNotFoundError(
                        f"Credentials file '{CREDENTIALS_FILE}' not found. "
                        "Please run 'python setup_google_calendar.py' to create a template."
                    )

                logger.info("Starting OAuth flow...")
                try:
                    # Use a fixed port to avoid redirect URI mismatch
                    flow = InstalledAppFlow.from_client_secrets_file(
                        CREDENTIALS_FILE, SCOPES
                    )

                    # Check if we're in a containerized environment
                    if os.getenv("DOCKER_ENV") or os.getenv("CONTAINER_ENV"):
                        logger.warning(
                            "Running in containerized environment. OAuth flow may not work properly.\n"
                            "Please authenticate outside the container and copy the token.json file."
                        )
                        # Try to use a headless approach or provide instructions
                        raise RuntimeError(
                            "OAuth flow not supported in containerized environment. "
                            "Please authenticate outside the container and copy token.json file."
                        )
                    else:
                        creds = flow.run_local_server(port=8080, prompt="consent")
                        logger.info("OAuth flow completed successfully")

                except Exception as e:
                    if "redirect_uri_mismatch" in str(e).lower():
                        logger.error(
                            "Redirect URI mismatch error. Please update your Google Cloud Console OAuth credentials:\n"
                            "1. Go to https://console.cloud.google.com/apis/credentials\n"
                            "2. Edit your OAuth 2.0 Client ID\n"
                            "3. Add 'http://localhost:8080/' to the Authorized redirect URIs\n"
                            "4. Save the changes\n"
                            "5. Download the updated credentials.json file"
                        )
                    elif "could not locate runnable browser" in str(e).lower():
                        logger.error(
                            "Browser not available for OAuth flow. This is expected in containerized environments.\n"
                            "Please authenticate outside the container:\n"
                            "1. Run 'python authenticate_google.py' on your host machine\n"
                            "2. Copy the generated token.json file to the container\n"
                            "3. Restart the container"
                        )
                    else:
                        logger.error(f"OAuth flow failed: {e}")
                    raise

            # Save credentials for next run (with error handling for concurrent access)
            if creds:
                try:
                    # Use atomic write to avoid corruption from multiple workers
                    import tempfile
                    import shutil

                    # Write to temporary file first
                    temp_file = tempfile.NamedTemporaryFile(mode="w", delete=False)
                    temp_file.write(creds.to_json())
                    temp_file.close()

                    # Atomically move to final location
                    shutil.move(temp_file.name, TOKEN_FILE)
                    logger.info(f"Saved token to {TOKEN_FILE}")
                except Exception as e:
                    logger.error(f"Failed to save token: {e}")
                    # Clean up temp file if it exists
                    try:
                        os.unlink(temp_file.name)
                    except:
                        pass

        self.service = build("calendar", "v3", credentials=creds)
        logger.info("Google Calendar service initialized successfully")
        return self.service

    def get_calendar_events(
        self,
        calendar_id: str = "primary",
        time_min: Optional[datetime] = None,
        time_max: Optional[datetime] = None,
    ) -> List[GoogleCalendarEvent]:
        """Fetch events from Google Calendar"""
        if not self.service:
            self.authenticate_google()

        # Use proper timezone handling
        if not time_min:
            time_min = datetime.now(timezone.utc)
        if not time_max:
            time_max = time_min + timedelta(days=30)
        if self.service is None:
            raise RuntimeError(
                "Google Calendar service is not initialized. Call authenticate_google() first."
            )

        try:
            # Format dates properly for Google Calendar API
            # Google Calendar API expects RFC3339 format
            time_min_str = time_min.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
            time_max_str = time_max.strftime("%Y-%m-%dT%H:%M:%S.%fZ")

            logger.info(f"Fetching events from {time_min_str} to {time_max_str}")

            events_result = (
                self.service.events()
                .list(
                    calendarId=calendar_id,
                )
                .execute()
            )

            logger.info(f"Events result: {events_result}")
            events = events_result.get("items", [])
            calendar_events = []

            for event in events:
                start = event["start"].get("dateTime", event["start"].get("date"))
                end = event["end"].get("dateTime", event["end"].get("date"))

                # Convert string to datetime
                if isinstance(start, str):
                    start = datetime.fromisoformat(start.replace("Z", "+00:00"))
                if isinstance(end, str):
                    end = datetime.fromisoformat(end.replace("Z", "+00:00"))

                calendar_events.append(
                    GoogleCalendarEvent(
                        id=event["iCalUID"],
                        summary=event.get("summary", "No Title"),
                        description=event.get("description"),
                        start=start,
                        end=end,
                        location=event.get("location"),
                        status=event.get("status", "confirmed"),
                        html_link=event.get("htmlLink", ""),
                    )
                )

            initial_sync_token = events_result.get("nextSyncToken")
            if initial_sync_token:
                self._set_sync_token(calendar_id, initial_sync_token)
                logger.info(f"Stored initial sync token: {initial_sync_token[:20]}...")

            logger.info(f"Fetched {len(calendar_events)} events from Google Calendar")
            return calendar_events

        except HttpError as error:
            logger.error(f"Error fetching Google Calendar events: {error}")
            raise

    def get_calendar_events_incremental(
        self,
        calendar_id: str = "primary",
        time_min: Optional[datetime] = None,
        time_max: Optional[datetime] = None,
    ) -> List[GoogleCalendarEvent]:
        """Fetch events from Google Calendar using incremental sync with sync tokens"""
        if not self.service:
            self.authenticate_google()

        if self.service is None:
            raise RuntimeError(
                "Google Calendar service is not initialized. Call authenticate_google() first."
            )

        try:
            # Get the stored sync token for this calendar
            sync_token = self._get_sync_token(calendar_id)

            # Prepare request parameters
            # Request params cannot contain fields like timeMin, timeMax, orderBy, etc. in order to get a sync token
            request_params = {
                "calendarId": calendar_id,
            }

            # If we have a sync token, use it for incremental sync
            if sync_token:
                logger.info(
                    f"Using sync token for incremental sync: {sync_token[:20]}..."
                )
                request_params["syncToken"] = sync_token
            else:
                # No sync token available, do a full sync with time range
                logger.info("No sync token available, performing full sync")
                # if not time_min:
                #     time_min = datetime.now(timezone.utc) - timedelta(days=7)
                # if not time_max:
                #     time_max = datetime.now(timezone.utc) + timedelta(days=30)

                # time_min_str = time_min.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
                # time_max_str = time_max.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
                # request_params["timeMin"] = time_min_str
                # request_params["timeMax"] = time_max_str

            logger.info(
                f"Fetching events with incremental sync for calendar {calendar_id}"
            )

            events_result = self.service.events().list(**request_params).execute()
            logger.info(f"Events Result for incremental sync: {events_result}")

            events = events_result.get("items", [])
            calendar_events: List[GoogleCalendarEvent] = []

            for event in events:
                start = event["start"].get("dateTime", event["start"].get("date"))
                end = event["end"].get("dateTime", event["end"].get("date"))

                # Convert string to datetime
                if isinstance(start, str):
                    start = datetime.fromisoformat(start.replace("Z", "+00:00"))
                if isinstance(end, str):
                    end = datetime.fromisoformat(end.replace("Z", "+00:00"))

                calendar_events.append(
                    GoogleCalendarEvent(
                        id=event["id"],
                        summary=event.get("summary", "No Title"),
                        description=event.get("description"),
                        start=start,
                        end=end,
                        location=event.get("location"),
                        status=event.get("status", "confirmed"),
                        html_link=event.get("htmlLink", ""),
                    )
                )

            # Store the next sync token for future incremental syncs
            next_sync_token = events_result.get("nextSyncToken")
            if next_sync_token:
                self._set_sync_token(calendar_id, next_sync_token)
                logger.info(f"Stored next sync token: {next_sync_token[:20]}...")

            logger.info(f"Fetched {len(calendar_events)} events using incremental sync")
            return calendar_events

        except HttpError as error:
            # If we get a 410 error, the sync token is invalid/expired
            if error.resp.status == 410:
                logger.warning(
                    "Sync token expired, clearing and retrying with full sync"
                )
                # Clear the invalid sync token
                self._set_sync_token(calendar_id, "")
                # Retry with full sync
                return self.get_calendar_events(calendar_id, time_min, time_max)
            else:
                logger.error(f"Error fetching Google Calendar events: {error}")
                raise

    def get_radicale_client(self):
        """Get Radicale client with authentication"""
        try:
            client = caldav.DAVClient(
                url=self.radicale_url,
                username=self.radicale_username,
                password=self.radicale_password,
            )
            return client
        except Exception as e:
            logger.error(f"Failed to connect to Radicale: {str(e)}")
            raise

    def sync_event_to_radicale(
        self, event: GoogleCalendarEvent, username: str, calendar_name: str
    ):

        if event.status == "cancelled":
            self.delete_event_from_radicale(event.id, calendar_name)
            return True

        """Sync a single Google Calendar event to Radicale"""
        logger.info(f"Syncing event: {event.summary} with status: {event.status}")
        try:
            client = self.get_radicale_client()
            principal = client.principal()
            calendars = principal.calendars()

            # Find the target calendar
            calendar = None
            for cal in calendars:
                if cal.name == calendar_name:
                    calendar = cal
                    break

            if not calendar:
                logger.error(f"Calendar '{calendar_name}' not found in Radicale")
                return False

            # Create iCalendar event
            cal = vobject.iCalendar()
            vevent = cal.add("vevent")
            vevent.add("summary").value = event.summary

            if event.description:
                vevent.add("description").value = event.description

            # Handle datetime with timezone information
            dtstart = vevent.add("dtstart")

            # Proper timezone handling - convert to naive UTC datetime
            if event.start.tzinfo is not None:
                # Convert to UTC if it's a timezone-aware datetime
                if event.start.tzinfo.utcoffset(event.start) is not None:
                    # Convert to UTC for storage
                    utc_start = event.start.astimezone(timezone.utc)
                    # Use naive datetime (without timezone info) for vobject
                    dtstart.value = utc_start.replace(tzinfo=None)
                else:
                    # Already UTC, use naive datetime
                    dtstart.value = event.start.replace(tzinfo=None)
            else:
                # No timezone info, use as is
                dtstart.value = event.start

            dtend = vevent.add("dtend")

            # Proper timezone handling for end time - convert to naive UTC datetime
            if event.end.tzinfo is not None:
                # Convert to UTC if it's a timezone-aware datetime
                if event.end.tzinfo.utcoffset(event.end) is not None:
                    # Convert to UTC for storage
                    utc_end = event.end.astimezone(timezone.utc)
                    # Use naive datetime (without timezone info) for vobject
                    dtend.value = utc_end.replace(tzinfo=None)
                else:
                    # Already UTC, use naive datetime
                    dtend.value = event.end.replace(tzinfo=None)
            else:
                # No timezone info, use as is
                dtend.value = event.end

            if event.location:
                vevent.add("location").value = event.location

            # Use Google Calendar event ID as UID for consistency
            vevent.add("uid").value = event.id

            # Add creation date
            dtstamp = vevent.add("dtstamp")
            dtstamp.value = datetime.now(timezone.utc).replace(tzinfo=None)

            # Add Google Calendar link as URL
            if event.html_link:
                vevent.add("url").value = event.html_link

            # Save event to Radicale
            event_id = f"{event.id}.ics"
            calendar.save_event(cal.serialize(), obj_id=event_id)

            logger.info(f"Successfully synced event '{event.summary}' to Radicale")
            return True

        except Exception as e:
            logger.error(
                f"Failed to sync event '{event.summary}' to Radicale: {str(e)}"
            )
            return False

    def process_google_notification(
        self, notification_data: Dict[str, Any], username: str, calendar_name: str
    ):
        """Process a Google Calendar push notification"""
        try:
            # Extract relevant information from notification
            resource_id = notification_data.get("resourceId")
            resource_uri = notification_data.get("resourceUri")
            state = GoogleCalendarResourceState(notification_data.get("state"))

            # Log all notification data for debugging
            logger.info(f"Full notification data: {notification_data}")
            logger.info(f"Resource ID: {resource_id}")
            logger.info(f"Resource URI: {resource_uri}")
            logger.info(f"State: {state}")

            logger.info(
                f"Processing Google Calendar notification: {state} for resource {resource_id}"
            )

            if state == GoogleCalendarResourceState.SYNC:
                # Full sync - fetch all events
                logger.info("Full sync - fetching all events")
                events = self.get_calendar_events()
                for event in events:
                    self.sync_event_to_radicale(event, username, calendar_name)
            elif state == GoogleCalendarResourceState.EXISTS:
                # Event was modified - try to identify and sync the specific event
                logger.info(
                    "Event modification detected - attempting to sync specific event"
                )
                events = self.get_calendar_events_incremental()
                for event in events:
                    self.sync_event_to_radicale(event, username, calendar_name)
            elif state == GoogleCalendarResourceState.NOT_EXISTS:
                logger.warning(
                    "Calendar has been deleted. This feature is not implemented yet."
                )
            else:
                logger.warning(f"Unknown notification state: {state}")
            return True

        except Exception as e:
            logger.error(f"Failed to process Google Calendar notification: {str(e)}")
            return False

    def delete_event_from_radicale(self, event_id: str, calendar_name: str):
        """Delete an event from Radicale by Google Calendar event ID"""
        try:
            client = self.get_radicale_client()
            principal = client.principal()
            calendars = principal.calendars()

            # Find the target calendar
            calendar = None
            for cal in calendars:
                if cal.name == calendar_name:
                    calendar = cal
                    break

            if not calendar:
                logger.error(f"Calendar '{calendar_name}' not found in Radicale")
                return False

            event_to_be_deleted = calendar.event_by_uid(event_id)
            if event_to_be_deleted:
                event_to_be_deleted.delete()
                logger.info(f"Successfully deleted event '{event_id}' from Radicale")
                return True
            else:
                logger.warning(f"Event '{event_id}' not found in Radicale")
                return False

        except Exception as e:
            logger.error(f"Failed to connect to Radicale for event deletion: {str(e)}")
            return False

    def setup_webhook(
        self, calendar_id: str = "primary", webhook_url: Union[str, None] = None
    ):
        """Setup Google Calendar webhook for push notifications"""
        if not self.service:
            self.authenticate_google()

        if not webhook_url:
            webhook_url = f"{os.getenv('WEBHOOK_BASE_URL', 'http://localhost:8000')}/webhook/google-calendar"

        if self.service is None:
            raise RuntimeError(
                "Google Calendar service is not initialized. Call authenticate_google() first."
            )

        try:
            # Create unique channel ID with timestamp
            unique_id = f"radicale-sync-{calendar_id}-{int(time.time())}"

            # Set up webhook using Google Calendar API watch method
            watch_request = {
                "id": unique_id,
                "type": "web_hook",
                "address": webhook_url,
                "params": {"ttl": "604800"},  # 7 days in seconds (maximum allowed)
            }

            # Start watching the calendar
            result = (
                self.service.events()
                .watch(calendarId=calendar_id, body=watch_request)
                .execute()
            )

            logger.info(f"Successfully set up webhook for calendar {calendar_id}")
            logger.info(f"Webhook URL: {webhook_url}")
            logger.info(f"Resource ID: {result.get('id')}")
            logger.info(f"Expiration: {result.get('expiration')}")

            return {
                "success": True,
                "resource_id": result.get("id"),
                "expiration": result.get("expiration"),
                "webhook_url": webhook_url,
            }

        except HttpError as error:
            logger.error(f"Failed to setup webhook: {error}")
            if error.resp.status == 403:
                logger.error(
                    "Permission denied. Make sure your Google Calendar API has write permissions."
                )
            elif error.resp.status == 400:
                logger.error("Invalid request. Check your webhook URL and calendar ID.")
            raise
        except Exception as e:
            logger.error(f"Unexpected error setting up webhook: {str(e)}")
            raise

    def stop_webhook(self, resource_id: str):
        """Stop a Google Calendar webhook"""
        if not self.service:
            self.authenticate_google()

        if self.service is None:
            raise RuntimeError(
                "Google Calendar service is not initialized. Call authenticate_google() first."
            )

        try:
            # Stop watching the calendar
            self.service.events().stop().execute()
            logger.info(f"Successfully stopped webhook with resource ID: {resource_id}")
            return True

        except HttpError as error:
            logger.error(f"Failed to stop webhook: {error}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error stopping webhook: {str(e)}")
            raise


# Global instance for use in FastAPI endpoints
google_sync = None


def get_google_sync_instance():
    """Get or create Google Calendar sync instance"""
    global google_sync
    if google_sync is None:
        google_sync = GoogleCalendarSync(
            radicale_url=os.getenv("RADICALE_URL", "http://localhost:5232"),
            radicale_username=os.getenv("RADICALE_USERNAME", "admin"),
            radicale_password=os.getenv("RADICALE_PASSWORD", "admin"),
        )
    return google_sync
