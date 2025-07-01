#!/usr/bin/env python3
"""
Script to regenerate Google Calendar token when authentication issues occur
"""

import os
import sys
from google_calendar_sync import get_google_sync_instance


def regenerate_token():
    """Regenerate Google Calendar token"""
    print("🔄 Regenerating Google Calendar Token")
    print("=" * 50)

    # Remove existing token
    token_file = "token.json"
    if os.path.exists(token_file):
        try:
            os.remove(token_file)
            print(f"🗑️  Removed existing token file: {token_file}")
        except Exception as e:
            print(f"⚠️  Failed to remove token file: {e}")

    # Check if credentials file exists
    credentials_file = "credentials.json"
    if not os.path.exists(credentials_file):
        print(f"❌ Credentials file '{credentials_file}' not found.")
        print("\n📋 To fix this:")
        print("1. Run 'python setup_google_calendar.py' to create a template")
        print("2. Update credentials.json with your Google Cloud Console credentials")
        return False

    try:
        # Get sync instance and authenticate
        google_sync = get_google_sync_instance()
        service = google_sync.authenticate_google()

        print("✅ Token regenerated successfully!")
        print(f"📁 New token file: {os.path.abspath(token_file)}")

        # Test the authentication
        try:
            calendar_list = service.calendarList().list().execute()
            calendars = calendar_list.get("items", [])
            print(
                f"✅ Successfully tested authentication - found {len(calendars)} calendars"
            )
            return True
        except Exception as e:
            print(f"⚠️  Authentication test failed: {e}")
            return False

    except Exception as e:
        print(f"❌ Failed to regenerate token: {e}")
        print("\n📋 Common solutions:")
        print("1. Check your credentials.json file is valid")
        print(
            "2. Make sure redirect URI is set to 'http://localhost:8080/' in Google Cloud Console"
        )
        print("3. Try running 'python authenticate_google.py' instead")
        return False


if __name__ == "__main__":
    success = regenerate_token()
    if success:
        print(
            "\n🎉 Token regeneration successful! Your Google Calendar integration should now work."
        )
    else:
        print("\n❌ Token regeneration failed. Please check the issues above.")
        sys.exit(1)
