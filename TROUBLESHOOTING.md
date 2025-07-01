# Troubleshooting Guide

## Google Calendar Authentication Issues

### 1. Missing Credentials File

**Error**: `FileNotFoundError: Credentials file 'credentials.json' not found`

**Solution**:
```bash
# Create credentials template
python setup_google_calendar.py

# Follow the instructions to get Google Cloud Console credentials
# 1. Go to https://console.cloud.google.com/
# 2. Create a new project or select existing one
# 3. Enable Google Calendar API
# 4. Create OAuth 2.0 credentials
# 5. Download credentials as JSON
# 6. Rename to 'credentials.json' and place in project root
```

### 2. OAuth Flow in Containerized Environment

**Error**: `could not locate runnable browser` or `OAuth flow not supported in containerized environment`

**Solution**:
```bash
# 1. Authenticate outside the container on your host machine
python authenticate_google.py

# 2. Copy the generated token.json file to the container
docker cp token.json <container_name>:/app/token.json

# 3. Restart the container
docker-compose restart
```

### 3. Invalid Client/Unauthorized Errors

**Error**: `invalid_client: Unauthorized` or `invalid_scope: Bad Request`

**Solutions**:

#### A. Check Redirect URI Configuration
1. Go to https://console.cloud.google.com/apis/credentials
2. Edit your OAuth 2.0 Client ID
3. Add `http://localhost:8080/` to the Authorized redirect URIs
4. Save the changes
5. Download the updated credentials.json file

#### B. Check API Permissions
1. Go to https://console.cloud.google.com/apis/library
2. Search for "Google Calendar API"
3. Enable it if not already enabled
4. Make sure your OAuth consent screen is configured

#### C. Regenerate Token
```bash
# Remove old token
rm token.json

# Re-authenticate
python authenticate_google.py
```

### 4. Token Refresh Issues

**Error**: `Failed to refresh token`

**Solution**:
```bash
# Remove the invalid token
rm token.json

# Re-authenticate
python authenticate_google.py
```

## Celery Issues

### 1. Celery Worker Not Starting

**Error**: `Connection refused` or `Redis connection failed`

**Solution**:
```bash
# Make sure Redis is running
docker-compose up redis -d

# Start Celery worker
docker-compose up celery-worker -d
```

### 2. Task Execution Failures

**Error**: Tasks failing with authentication errors

**Solution**:
1. Check the authentication setup above
2. Verify credentials.json and token.json are present
3. Test authentication manually:
   ```bash
   python test_google_auth.py
   ```

### 3. Task Retry Issues

**Error**: Tasks retrying indefinitely

**Solution**:
- Check the task logs for specific error messages
- Authentication errors are not retried automatically
- Other errors are retried up to 3 times with exponential backoff

## Webhook Issues

### 1. Webhook Not Receiving Notifications

**Check**:
1. Verify webhook URL is accessible from the internet (use ngrok or similar)
2. Check Google Calendar API permissions
3. Verify webhook is properly configured

**Test**:
```bash
# Test webhook endpoint manually
curl -X POST http://localhost:8000/test-webhook \
  -H "Content-Type: application/json" \
  -d '{"test": "data"}'
```

### 2. Webhook Processing Failures

**Check**:
1. Celery worker logs for authentication issues
2. Radicale connection status
3. Calendar permissions

## Environment Variables

Make sure these environment variables are set correctly:

```bash
# Required
RADICALE_URL=http://localhost:5232
RADICALE_USERNAME=admin
RADICALE_PASSWORD=admin
WEBHOOK_BASE_URL=http://localhost:8000

# Optional
DEFAULT_RADICALE_USER=admin
DEFAULT_CALENDAR_NAME=default
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
```

## Testing Steps

1. **Test Authentication**:
   ```bash
   python test_google_auth.py
   ```

2. **Test Webhook Endpoint**:
   ```bash
   curl -X POST http://localhost:8000/test-webhook
   ```

3. **Test Manual Sync**:
   ```bash
   curl -X POST http://localhost:8000/google-calendar/sync \
     -H "Content-Type: application/json" \
     -d '{"username": "admin", "calendar_name": "default"}'
   ```

4. **Check Sync Status**:
   ```bash
   curl http://localhost:8000/google-calendar/sync/status/<task_id>
   ```

## Common Log Messages

### Success Messages
- `✅ Google Calendar authentication successful`
- `✅ Successfully synced event to Radicale`
- `✅ Webhook processed successfully`

### Warning Messages
- `⚠️ Failed to refresh token` - Token refresh failed, re-authentication needed
- `⚠️ API call failed` - API permissions might be insufficient

### Error Messages
- `❌ Missing credentials file` - Need to set up Google Cloud credentials
- `❌ OAuth not supported in container` - Need to authenticate outside container
- `❌ Authentication error` - OAuth configuration issues

## Getting Help

If you're still having issues:

1. Check the logs for specific error messages
2. Run the test scripts to isolate the problem
3. Verify your Google Cloud Console configuration
4. Check that all required files are present and accessible 