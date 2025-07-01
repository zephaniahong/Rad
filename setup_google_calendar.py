#!/usr/bin/env python3
"""
Setup script for Google Calendar integration with Radicale
"""

import os
import json
import sys
from pathlib import Path

def create_credentials_template():
    """Create a template credentials.json file"""
    template = {
        "installed": {
            "client_id": "YOUR_CLIENT_ID.apps.googleusercontent.com",
            "project_id": "your-project-id",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_secret": "YOUR_CLIENT_SECRET",
            "redirect_uris": ["http://localhost"]
        }
    }
    
    with open('credentials.json', 'w') as f:
        json.dump(template, f, indent=2)
    
    print("Created credentials.json template")
    print("Please update it with your actual Google Cloud Console credentials")

def create_env_template():
    """Create a .env template file"""
    env_template = """# Google Calendar Integration
GOOGLE_CALENDAR_CREDENTIALS_FILE=credentials.json
GOOGLE_CALENDAR_TOKEN_FILE=token.json

# Radicale Configuration
RADICALE_URL=http://localhost:5232
RADICALE_USERNAME=admin
RADICALE_PASSWORD=admin

# Webhook Configuration
WEBHOOK_BASE_URL=http://localhost:8000
DEFAULT_RADICALE_USER=admin
DEFAULT_CALENDAR_NAME=default

# Celery Configuration
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
"""
    
    with open('.env', 'w') as f:
        f.write(env_template)
    
    print("Created .env template")
    print("Please update it with your actual configuration values")

def print_setup_instructions():
    """Print setup instructions"""
    instructions = """
=== Google Calendar Integration Setup ===

1. Google Cloud Console Setup:
   - Go to https://console.cloud.google.com/
   - Create a new project or select existing one
   - Enable Google Calendar API
   - Create OAuth 2.0 credentials
   - Download credentials as JSON
   - Rename to 'credentials.json' and place in project root

2. Update Configuration:
   - Edit .env file with your Radicale and webhook settings
   - Update credentials.json with your actual Google credentials

3. Install Dependencies:
   pip install -r requirements.txt

4. Start Services:
   - Start Redis: redis-server
   - Start Celery worker: celery -A celery_app worker --loglevel=info
   - Start FastAPI: python main.py

5. Authenticate with Google:
   - Run: python -c "from google_calendar_sync import get_google_sync_instance; get_google_sync_instance().authenticate_google()"
   - Follow the browser authentication flow

6. Setup Webhook (Optional):
   - Call POST /google-calendar/setup-webhook to configure push notifications
   - Note: Requires proper Google Calendar API permissions

7. Manual Sync:
   - Call POST /google-calendar/sync with your username and calendar name
   - Check sync status with GET /google-calendar/sync/status/{task_id}

=== API Endpoints ===

POST /webhook/google-calendar
- Receives Google Calendar push notifications

POST /google-calendar/sync
- Manually trigger sync from Google Calendar to Radicale

GET /google-calendar/sync/status/{task_id}
- Check status of sync operations

POST /google-calendar/setup-webhook
- Setup Google Calendar webhook (requires API permissions)

=== Environment Variables ===

Required:
- RADICALE_URL: Your Radicale server URL
- RADICALE_USERNAME: Radicale username
- RADICALE_PASSWORD: Radicale password
- WEBHOOK_BASE_URL: Your webhook endpoint base URL

Optional:
- GOOGLE_CALENDAR_CREDENTIALS_FILE: Path to Google credentials (default: credentials.json)
- GOOGLE_CALENDAR_TOKEN_FILE: Path to Google token (default: token.json)
- DEFAULT_RADICALE_USER: Default Radicale user for webhooks
- DEFAULT_CALENDAR_NAME: Default calendar name for webhooks
- CELERY_BROKER_URL: Redis URL for Celery (default: redis://localhost:6379/0)
- CELERY_RESULT_BACKEND: Redis URL for Celery results (default: redis://localhost:6379/0)
"""
    print(instructions)

def main():
    """Main setup function"""
    print("Setting up Google Calendar integration with Radicale...")
    
    # Create template files
    create_credentials_template()
    create_env_template()
    
    # Print instructions
    print_setup_instructions()
    
    print("\nSetup complete! Please follow the instructions above to configure your integration.")

if __name__ == "__main__":
    main() 