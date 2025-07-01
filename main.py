from fastapi import FastAPI, HTTPException, Depends, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import uvicorn
import os
import httpx
from datetime import datetime, timedelta, timezone
import vobject
import caldav
from urllib.parse import urljoin
import json
import logging

# Import Google Calendar sync functionality
from google_calendar_sync import get_google_sync_instance
from celery_app import (
    process_google_calendar_notification,
    sync_google_calendar_to_radicale,
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app instance
app = FastAPI(
    title="FastAPI Dev Container",
    description="A FastAPI application running in a dev container with Radicale integration",
    version="1.0.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Radicale configuration
RADICALE_URL = os.getenv("RADICALE_URL", "http://localhost:5232")
RADICALE_USERNAME = os.getenv("RADICALE_USERNAME", "admin")
RADICALE_PASSWORD = os.getenv("RADICALE_PASSWORD", "admin")


# Pydantic models
class Item(BaseModel):
    id: Optional[int] = None
    name: str
    description: Optional[str] = None
    price: float
    is_offer: Optional[bool] = None


class ItemResponse(BaseModel):
    message: str
    item: Item


class CalendarEvent(BaseModel):
    summary: str
    description: Optional[str] = None
    start: datetime
    end: datetime
    location: Optional[str] = None


class Contact(BaseModel):
    first_name: str
    last_name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    organization: Optional[str] = None


class RadicaleStatus(BaseModel):
    status: str
    url: str
    connected: bool


class GoogleCalendarWebhook(BaseModel):
    """Model for Google Calendar webhook notifications"""

    resourceId: str
    resourceUri: str
    state: str
    expiration: Optional[str] = None


class GoogleCalendarSyncRequest(BaseModel):
    """Model for manual sync requests"""

    username: str
    calendar_name: str
    google_calendar_id: str = "primary"
    sync_type: str = "full"  # "full" or "incremental"


# In-memory storage (replace with database in production)
items_db = []
item_id_counter = 1


# Radicale client helper
async def get_radicale_client():
    """Get Radicale client with authentication"""
    try:
        client = caldav.DAVClient(
            url=RADICALE_URL, username=RADICALE_USERNAME, password=RADICALE_PASSWORD
        )
        return client
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to connect to Radicale: {str(e)}"
        )


@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "Hello from FastAPI in Dev Container!", "status": "running"}


@app.get("/health")
async def health_check():
    print("=== ENTERING health_check ===")
    """Health check endpoint"""
    return {"status": "healthy", "service": "FastAPI"}


@app.get("/radicale/status", response_model=RadicaleStatus)
async def radicale_status():
    """Check Radicale connection status"""
    try:
        # Use the CalDAV client to test connection, similar to other endpoints
        client = await get_radicale_client()
        principal = client.principal()
        # Try to get calendars to verify connection
        calendars = principal.calendars()
        return RadicaleStatus(status="connected", url=RADICALE_URL, connected=True)
    except Exception as e:
        return RadicaleStatus(status="disconnected", url=RADICALE_URL, connected=False)


@app.get("/radicale/calendars")
async def get_calendars():
    """Get all calendars from Radicale"""
    try:
        client = await get_radicale_client()
        principal = client.principal()
        calendars = principal.calendars()
        return {
            "calendars": [
                {"name": cal.name, "url": cal.url, "color": getattr(cal, "color", None)}
                for cal in calendars
            ]
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get calendars: {str(e)}"
        )


@app.post("/radicale/calendars/{username}/{calendar_name}/events")
async def create_calendar_event(
    username: str, calendar_name: str, event: CalendarEvent
):
    """Create a new calendar event"""
    print(f"=== ENTERING create_calendar_event ===")
    print(f"username: {username}")
    print(f"calendar_name: {calendar_name}")
    print(f"event: {event}")
    try:
        print("creating event")
        client = await get_radicale_client()
        print("got radicale client")
        principal = client.principal()
        print("got principal")
        calendars = principal.calendars()
        print("calendars", calendars)
        print("calendar name", calendar_name)
        print("event", event)
        # Find the calendar
        calendar = None
        full_calendar_name = f"{username}/{calendar_name}"
        for cal in calendars:
            print(f"checking calendar: {cal.name}")
            if cal.name == full_calendar_name:
                calendar = cal
                print(f"found calendar: {cal.name}")
                break

        if not calendar:
            print(f"Calendar '{full_calendar_name}' not found")
            raise HTTPException(status_code=404, detail="Calendar not found")

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

        # Add UID for the event (required for CalDAV)
        import uuid

        vevent.add("uid").value = str(uuid.uuid4())

        # Add creation date
        dtstamp = vevent.add("dtstamp")
        dtstamp.value = datetime.now(timezone.utc).replace(tzinfo=None)

        # Save event using the correct caldav method
        event_id = f"event_{datetime.now().strftime('%Y%m%d_%H%M%S')}.ics"
        print(f"about to save event with id: {event_id}")
        calendar.save_event(cal.serialize(), obj_id=event_id)
        print("event saved successfully")

        return {"message": "Event created successfully", "event_id": event_id}
    except Exception as e:
        print(f"Error creating event: {str(e)}")
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to create event: {str(e)}")


@app.get("/radicale/calendars/{username}/{calendar_name}/events")
async def get_calendar_events(
    username: str,
    calendar_name: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
):
    """Get events from a calendar"""
    try:
        client = await get_radicale_client()
        principal = client.principal()
        calendars = principal.calendars()

        # Find the calendar
        calendar = None
        full_calendar_name = f"{username}/{calendar_name}"
        for cal in calendars:
            if cal.name == full_calendar_name:
                calendar = cal
                break

        if not calendar:
            raise HTTPException(status_code=404, detail="Calendar not found")

        # Get events
        events = calendar.events()

        # Filter by date if provided
        if start_date or end_date:
            filtered_events = []
            for event in events:
                event_start = event.instance.vevent.dtstart.value
                if start_date and event_start < datetime.fromisoformat(start_date):
                    continue
                if end_date and event_start > datetime.fromisoformat(end_date):
                    continue
                filtered_events.append(event)
            events = filtered_events

        return {
            "events": [
                {
                    "summary": event.instance.vevent.summary.value,
                    "description": getattr(event.instance.vevent, "description", None),
                    "start": event.instance.vevent.dtstart.value.isoformat(),
                    "end": event.instance.vevent.dtend.value.isoformat(),
                    "location": getattr(event.instance.vevent, "location", None),
                }
                for event in events
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get events: {str(e)}")


@app.get("/radicale/addressbooks")
async def get_addressbooks():
    """Get all address books from Radicale"""
    try:
        client = await get_radicale_client()
        principal = client.principal()
        # Note: addressbooks() method might not be available in all caldav versions
        # This is a simplified implementation
        return {
            "addressbooks": [],
            "message": "Address books functionality requires additional setup",
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get address books: {str(e)}"
        )


@app.post("/radicale/addressbooks/{addressbook_name}/contacts")
async def create_contact(addressbook_name: str, contact: Contact):
    """Create a new contact"""
    try:
        client = await get_radicale_client()
        principal = client.principal()

        # Create vCard contact
        card = vobject.vCard()
        card.add("n")
        card.n.value = vobject.vCard.Name(
            family=contact.last_name, given=contact.first_name
        )
        card.add("fn")
        card.fn.value = f"{contact.first_name} {contact.last_name}"

        if contact.email:
            card.add("email")
            card.email.value = contact.email
            card.email.type_param = "INTERNET"

        if contact.phone:
            card.add("tel")
            card.tel.value = contact.phone
            card.tel.type_param = "CELL"

        if contact.organization:
            card.add("org")
            card.org.value = [contact.organization]

        # For now, return the vCard data
        # In a full implementation, you would save this to the address book
        contact_id = f"contact_{datetime.now().strftime('%Y%m%d_%H%M%S')}.vcf"

        return {
            "message": "Contact created successfully",
            "contact_id": contact_id,
            "vcard_data": card.serialize(),
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to create contact: {str(e)}"
        )


@app.get("/items", response_model=List[Item])
async def get_items():
    """Get all items"""
    return items_db


@app.get("/items/{item_id}", response_model=Item)
async def get_item(item_id: int):
    """Get a specific item by ID"""
    for item in items_db:
        if item.id == item_id:
            return item
    raise HTTPException(status_code=404, detail="Item not found")


@app.post("/items", response_model=ItemResponse)
async def create_item(item: Item):
    """Create a new item"""
    global item_id_counter
    item.id = item_id_counter
    item_id_counter += 1
    items_db.append(item)
    return ItemResponse(message="Item created successfully", item=item)


@app.put("/items/{item_id}", response_model=ItemResponse)
async def update_item(item_id: int, item: Item):
    """Update an existing item"""
    for i, existing_item in enumerate(items_db):
        if existing_item.id == item_id:
            item.id = item_id
            items_db[i] = item
            return ItemResponse(message="Item updated successfully", item=item)
    raise HTTPException(status_code=404, detail="Item not found")


@app.delete("/items/{item_id}")
async def delete_item(item_id: int):
    """Delete an item"""
    for i, item in enumerate(items_db):
        if item.id == item_id:
            deleted_item = items_db.pop(i)
            return {
                "message": "Item deleted successfully",
                "deleted_item": deleted_item,
            }
    raise HTTPException(status_code=404, detail="Item not found")


@app.post("/test-webhook")
async def test_webhook(request: Request):
    """Test endpoint to simulate Google Calendar webhook without Google API"""
    try:
        # Get the raw request body
        body = await request.body()
        logger.info(f"Test webhook body: {body}")

        # Simulate successful webhook processing
        logger.info("Test webhook received - simulating successful processing")

        return {
            "message": "Test webhook processed successfully",
            "status": "success",
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error in test webhook: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Test webhook failed: {str(e)}")


# Google Calendar webhook endpoints
@app.post("/webhook/google-calendar")
async def google_calendar_webhook(request: Request):
    """Webhook endpoint for Google Calendar push notifications"""
    try:
        logger.info("REQUEST", request)
        # Get the raw request body
        body = await request.body()
        logger.info(f"Raw webhook body: {body}")

        # Check for Google Calendar headers (Google sends notifications via headers)
        headers = dict(request.headers)
        logger.info(f"Webhook headers: {headers}")

        # Extract Google Calendar notification data from headers
        resource_state = headers.get("X-Goog-Resource-State") or headers.get(
            "x-goog-resource-state"
        )
        resource_id = headers.get("X-Goog-Resource-Id") or headers.get(
            "x-goog-resource-id"
        )
        resource_uri = headers.get("X-Goog-Resource-Uri") or headers.get(
            "x-goog-resource-uri"
        )
        channel_id = headers.get("X-Goog-Channel-Id") or headers.get(
            "x-goog-channel-id"
        )
        message_number = headers.get("X-Goog-Message-Number") or headers.get(
            "x-goog-message-number"
        )

        # Debug logging to see what we're extracting
        logger.info(
            f"Extracted headers - resource_state: '{resource_state}', resource_id: '{resource_id}'"
        )
        logger.info(
            f"All Google headers found: resource_state='{resource_state}', resource_id='{resource_id}', resource_uri='{resource_uri}', channel_id='{channel_id}', message_number='{message_number}'"
        )

        # Try to parse as JSON to get additional data from body
        webhook_body_data = {}
        try:
            if body:
                webhook_body_data = await request.json()
                logger.info(f"Parsed webhook body data: {webhook_body_data}")
        except Exception as e:
            logger.info(f"Could not parse webhook body as JSON: {str(e)}")
            # Try to decode as string if it's not JSON
            try:
                body_str = body.decode("utf-8") if body else ""
                logger.info(f"Webhook body as string: {body_str}")
                webhook_body_data = {"raw_body": body_str}
            except Exception as e2:
                logger.info(f"Could not decode webhook body: {str(e2)}")

        # If we have Google Calendar headers, use them
        if resource_state and resource_id:
            logger.info(
                f"Google Calendar notification via headers: state={resource_state}, resource_id={resource_id}"
            )

            notification = {
                "resourceId": resource_id,
                "resourceUri": resource_uri
                or "https://www.googleapis.com/calendar/v3/calendars/primary/events",
                "state": resource_state,
                "channelId": channel_id,
                "messageNumber": message_number,
                # Include any additional data from the webhook body
                **webhook_body_data,
            }

            logger.info(
                f"Processed Google Calendar webhook from headers: {notification}"
            )

            # Extract username and calendar name
            username = os.getenv("DEFAULT_RADICALE_USER", "admin")
            calendar_name = os.getenv("DEFAULT_CALENDAR_NAME", "default")

            # Process the notification asynchronously
            task = process_google_calendar_notification.delay(
                notification, username, calendar_name
            )

            return {
                "message": "Google Calendar notification received and queued for processing",
                "task_id": task.id,
                "status": "queued",
                "resource_state": resource_state,
                "resource_id": resource_id,
            }

        # Try to parse as JSON (fallback for manual testing)
        try:
            data = await request.json()
            logger.info(f"Parsed webhook data: {data}")
        except Exception as e:
            logger.error(f"Failed to parse JSON: {str(e)}")
            data = {}

        # Handle different webhook formats
        if not data and not resource_state:
            # Empty body and no headers - might be a test ping
            logger.info(
                "Received empty webhook body and no Google headers - treating as test ping"
            )
            return {"message": "Test ping received", "status": "ok"}

        # Try to extract webhook data in different formats
        resource_id = data.get("resourceId") or data.get("resource_id")
        resource_uri = data.get("resourceUri") or data.get("resource_uri")
        state = data.get("state", "sync")
        expiration = data.get("expiration")

        if not resource_id:
            logger.warning(f"Missing resourceId in webhook data: {data}")
            return {
                "message": "Webhook received but missing required data",
                "status": "warning",
                "data": data,
            }

        # Create notification object
        notification = {
            "resourceId": resource_id,
            "resourceUri": resource_uri
            or "https://www.googleapis.com/calendar/v3/calendars/primary/events",
            "state": state,
            "expiration": expiration,
            # Include any additional data from the webhook body
            **webhook_body_data,
        }

        logger.info(f"Processed Google Calendar webhook from JSON: {notification}")

        # Extract username and calendar name from resource URI
        username = os.getenv("DEFAULT_RADICALE_USER", "admin")
        calendar_name = os.getenv("DEFAULT_CALENDAR_NAME", "default")

        # Process the notification asynchronously
        task = process_google_calendar_notification.delay(
            notification, username, calendar_name
        )

        return {
            "message": "Notification received and queued for processing",
            "task_id": task.id,
            "status": "queued",
        }

    except Exception as e:
        logger.error(f"Error processing Google Calendar webhook: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Failed to process webhook: {str(e)}"
        )


@app.post("/google-calendar/sync")
async def sync_google_calendar(sync_request: GoogleCalendarSyncRequest):
    """Manually trigger Google Calendar sync to Radicale"""
    try:
        logger.info(f"Manual sync request: {sync_request}")

        # Start background sync task
        task = sync_google_calendar_to_radicale.delay(
            sync_request.username,
            sync_request.calendar_name,
            sync_request.google_calendar_id,
        )

        return {
            "message": "Sync started",
            "task_id": task.id,
            "status": "started",
            "sync_type": sync_request.sync_type,
        }

    except Exception as e:
        logger.error(f"Error starting Google Calendar sync: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to start sync: {str(e)}")


@app.post("/google-calendar/trigger-periodic-sync")
async def trigger_periodic_sync():
    """Manually trigger the periodic sync task"""
    try:
        from celery_app import periodic_sync_task

        logger.info("Manually triggering periodic sync task...")

        # Start the periodic sync task
        task = periodic_sync_task.delay()

        return {
            "message": "Periodic sync task triggered",
            "task_id": task.id,
            "status": "started",
            "sync_type": "periodic",
        }

    except Exception as e:
        logger.error(f"Error triggering periodic sync: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Failed to trigger periodic sync: {str(e)}"
        )


@app.get("/google-calendar/sync/status/{task_id}")
async def get_sync_status(task_id: str):
    """Get the status of a sync task"""
    try:
        from celery.result import AsyncResult

        result = AsyncResult(task_id)

        if result.ready():
            if result.successful():
                return {
                    "task_id": task_id,
                    "status": "completed",
                    "result": result.get(),
                }
            else:
                return {
                    "task_id": task_id,
                    "status": "failed",
                    "error": str(result.info),
                }
        else:
            return {"task_id": task_id, "status": "running", "progress": "unknown"}

    except Exception as e:
        logger.error(f"Error getting sync status: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get sync status: {str(e)}"
        )


@app.post("/google-calendar/setup-webhook")
async def setup_google_calendar_webhook(calendar_id: str = "primary"):
    """Setup Google Calendar webhook (requires Google Calendar API setup)"""
    try:
        google_sync = get_google_sync_instance()

        # Setup webhook using the new method
        result = google_sync.setup_webhook(calendar_id)

        return {
            "message": "Webhook setup successful",
            "webhook_url": result["webhook_url"],
            "calendar_id": calendar_id,
            "resource_id": result["resource_id"],
            "expiration": result["expiration"],
        }

    except Exception as e:
        logger.error(f"Error setting up Google Calendar webhook: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Failed to setup webhook: {str(e)}"
        )


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True, log_level="info")
