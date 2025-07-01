#!/usr/bin/env python3
"""
Script to authenticate with Google Calendar API outside of Docker
"""

import os
import sys
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

# Google Calendar API scopes
SCOPES = ["https://www.googleapis.com/auth/calendar"]

# File paths
CREDENTIALS_FILE = "credentials.json"
TOKEN_FILE = "token.json"


def authenticate_google():
    """Authenticate with Google Calendar API"""
    creds = None

    # Check if credentials file exists
    if not os.path.exists(CREDENTIALS_FILE):
        print(f"❌ Credentials file '{CREDENTIALS_FILE}' not found.")
        print("\n📋 Setup Instructions:")
        print("1. Go to https://console.cloud.google.com/")
        print("2. Create a new project or select existing one")
        print("3. Enable Google Calendar API")
        print("4. Create OAuth 2.0 credentials")
        print("5. Download credentials as JSON")
        print("6. Rename to 'credentials.json' and place in project root")
        print("7. Make sure redirect URI is set to 'http://localhost:8080/'")
        print(
            "\n💡 You can also run 'python setup_google_calendar.py' to create a template"
        )
        sys.exit(1)

    # Load existing token if it exists
    if os.path.exists(TOKEN_FILE):
        try:
            creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
            print("✅ Loaded existing token from file")
        except Exception as e:
            print(f"⚠️  Failed to load existing token: {e}")
            try:
                os.remove(TOKEN_FILE)
                print("🗑️  Removed invalid token file")
            except:
                pass
            creds = None

    # If no valid credentials available, let user log in
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                print("🔄 Refreshed expired token")
            except Exception as e:
                print(f"⚠️  Failed to refresh token: {e}")
                creds = None

        if not creds:
            print("🔐 Starting OAuth flow...")
            print("📝 This will open a browser window for authentication")
            try:
                flow = InstalledAppFlow.from_client_secrets_file(
                    CREDENTIALS_FILE, SCOPES
                )
                creds = flow.run_local_server(port=8080, prompt="consent")
                print("✅ OAuth flow completed successfully")
            except Exception as e:
                if "redirect_uri_mismatch" in str(e).lower():
                    print("❌ Redirect URI mismatch error!")
                    print("\n🔧 Fix Instructions:")
                    print("1. Go to https://console.cloud.google.com/apis/credentials")
                    print("2. Edit your OAuth 2.0 Client ID")
                    print(
                        "3. Add 'http://localhost:8080/' to the Authorized redirect URIs"
                    )
                    print("4. Save the changes")
                    print("5. Download the updated credentials.json file")
                else:
                    print(f"❌ OAuth flow failed: {e}")
                sys.exit(1)

        # Save credentials for next run
        try:
            with open(TOKEN_FILE, "w") as token:
                token.write(creds.to_json())
            print(f"💾 Saved token to {TOKEN_FILE}")
        except Exception as e:
            print(f"❌ Failed to save token: {e}")

    print("🎉 Google Calendar authentication successful!")
    print(f"📁 Token file: {os.path.abspath(TOKEN_FILE)}")
    print("\n📋 Next steps:")
    print("1. Copy the token.json file to your container if using Docker")
    print("2. Restart your application")
    print("3. Test the integration with a manual sync")
    return creds


if __name__ == "__main__":
    print("🔐 Google Calendar Authentication Script")
    print("=" * 50)
    authenticate_google()
