# Google Calendar Integration with Radicale

This guide explains how to set up push notifications from Google Calendar to automatically sync events to your Radicale server.

## Overview

The integration consists of:
1. **Google Calendar API** - Fetches calendar events and handles authentication
2. **Webhook Endpoint** - Receives push notifications from Google Calendar
3. **Background Processing** - Uses Celery to handle sync operations asynchronously
4. **Radicale Sync** - Updates your Radicale server with Google Calendar events

## Architecture

```
Google Calendar → Webhook → FastAPI → Celery → Radicale
     ↓              ↓         ↓        ↓        ↓
  Events        Notifications  Queue  Worker   Calendar
```

## Setup Instructions

### 1. Prerequisites

- Python 3.8+
- Redis server
- Google Cloud Console account
- Radicale server running

### 2. Google Cloud Console Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the Google Calendar API:
   - Go to "APIs & Services" > "Library"
   - Search for "Google Calendar API"
   - Click "Enable"
4. Create OAuth 2.0 credentials:
   - Go to "APIs & Services" > "Credentials"
   - Click "Create Credentials" > "OAuth 2.0 Client IDs"
   - Choose "Desktop application"
   - Download the JSON file
   - Rename to `credentials.json` and place in project root

### 3. Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run the setup script:
```bash
python setup_google_calendar.py
```

3. Update the generated files:
   - Edit `credentials.json` with your actual Google credentials
   - Edit `.env` with your configuration values

### 4. Start Services

#### Option A: Using Docker Compose (Recommended)

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f app
docker-compose logs -f celery-worker
```

#### Option B: Manual Setup

1. Start Redis:
```bash
redis-server
```

2. Start Celery worker:
```bash
celery -A celery_app worker --loglevel=info
```

3. Start FastAPI application:
```bash
python main.py
```

### 5. Google Authentication

Run the authentication command:
```bash
python -c "from google_calendar_sync import get_google_sync_instance; get_google_sync_instance().authenticate_google()"
```

Follow the browser authentication flow. This will create a `token.json` file.

## API Endpoints

### Webhook Endpoint

**POST** `/webhook/google-calendar`

Receives push notifications from Google Calendar.

**Request Body:**
```json
{
  "resourceId": "unique-resource-id",
  "resourceUri": "https://www.googleapis.com/calendar/v3/calendars/primary/events",
  "state": "sync"
}
```

**Response:**
```json
{
  "message": "Notification received and queued for processing",
  "task_id": "celery-task-id",
  "status": "queued"
}
```

### Manual Sync

**POST** `/google-calendar/sync`

Manually trigger a sync from Google Calendar to Radicale.

**Request Body:**
```json
{
  "username": "admin",
  "calendar_name": "default",
  "google_calendar_id": "primary",
  "sync_type": "full"
}
```

**Response:**
```json
{
  "message": "Sync started",
  "task_id": "celery-task-id",
  "status": "started",
  "sync_type": "full"
}
```

### Sync Status

**GET** `/google-calendar/sync/status/{task_id}`

Check the status of a sync operation.

**Response:**
```json
{
  "task_id": "celery-task-id",
  "status": "completed",
  "result": {
    "success": true,
    "synced_events": 5,
    "total_events": 5
  }
}
```

### Webhook Setup

**POST** `/google-calendar/setup-webhook?calendar_id=primary`

Setup Google Calendar webhook (requires proper API permissions).

**Response:**
```json
{
  "message": "Webhook setup initiated",
  "webhook_url": "http://localhost:8000/webhook/google-calendar",
  "calendar_id": "primary",
  "note": "This requires proper Google Calendar API setup with write permissions"
}
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `RADICALE_URL` | Radicale server URL | `http://localhost:5232` |
| `RADICALE_USERNAME` | Radicale username | `admin` |
| `RADICALE_PASSWORD` | Radicale password | `admin` |
| `WEBHOOK_BASE_URL` | Your webhook endpoint base URL | `http://localhost:8000` |
| `DEFAULT_RADICALE_USER` | Default Radicale user for webhooks | `admin` |
| `DEFAULT_CALENDAR_NAME` | Default calendar name for webhooks | `default` |
| `CELERY_BROKER_URL` | Redis URL for Celery | `redis://localhost:6379/0` |
| `CELERY_RESULT_BACKEND` | Redis URL for Celery results | `redis://localhost:6379/0` |

### Google Calendar Configuration

- `credentials.json`: Google OAuth 2.0 credentials
- `token.json`: Google authentication token (auto-generated)

## Usage Examples

### 1. Manual Sync

```bash
curl -X POST "http://localhost:8000/google-calendar/sync" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "calendar_name": "default",
    "google_calendar_id": "primary"
  }'
```

### 2. Check Sync Status

```bash
curl "http://localhost:8000/google-calendar/sync/status/{task_id}"
```

### 3. Test Webhook (Simulate Google Calendar notification)

```bash
curl -X POST "http://localhost:8000/webhook/google-calendar" \
  -H "Content-Type: application/json" \
  -d '{
    "resourceId": "test-resource-id",
    "resourceUri": "https://www.googleapis.com/calendar/v3/calendars/primary/events",
    "state": "sync"
  }'
```

## Troubleshooting

### Common Issues

1. **Authentication Errors**
   - Ensure `credentials.json` is properly configured
   - Delete `token.json` and re-authenticate
   - Check Google Cloud Console API permissions

2. **Radicale Connection Issues**
   - Verify Radicale server is running
   - Check `RADICALE_URL`, `RADICALE_USERNAME`, and `RADICALE_PASSWORD`
   - Ensure calendar exists in Radicale

3. **Celery Worker Issues**
   - Verify Redis is running
   - Check Celery worker logs
   - Ensure all dependencies are installed

4. **Webhook Not Receiving Notifications**
   - Verify webhook URL is publicly accessible
   - Check Google Calendar API setup
   - Ensure proper authentication

### Logs

Check logs for debugging:

```bash
# Docker Compose logs
docker-compose logs -f app
docker-compose logs -f celery-worker

# Manual setup logs
tail -f celery.log
```

### Testing

1. **Test Google Calendar API:**
```python
from google_calendar_sync import get_google_sync_instance
google_sync = get_google_sync_instance()
events = google_sync.get_calendar_events()
print(f"Found {len(events)} events")
```

2. **Test Radicale Connection:**
```python
from google_calendar_sync import get_google_sync_instance
google_sync = get_google_sync_instance()
client = google_sync.get_radicale_client()
principal = client.principal()
calendars = principal.calendars()
print(f"Found {len(calendars)} calendars")
```

## Security Considerations

1. **Credentials Security**
   - Never commit `credentials.json` or `token.json` to version control
   - Use environment variables for sensitive configuration
   - Rotate credentials regularly

2. **Webhook Security**
   - Implement webhook signature verification
   - Use HTTPS for production webhooks
   - Rate limit webhook endpoints

3. **API Permissions**
   - Use minimal required permissions
   - Regularly review API access
   - Monitor API usage

## Production Deployment

For production deployment:

1. **Use HTTPS** for webhook endpoints
2. **Implement authentication** for API endpoints
3. **Use environment variables** for all configuration
4. **Set up monitoring** for Celery tasks
5. **Configure logging** for debugging
6. **Use a proper database** instead of in-memory storage
7. **Set up backup** for Radicale data

## Support

For issues and questions:
1. Check the troubleshooting section
2. Review logs for error messages
3. Verify configuration settings
4. Test individual components 