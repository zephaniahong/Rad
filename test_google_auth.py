#!/usr/bin/env python3
"""
Test script to verify Google Calendar authentication
"""

import os
import sys
from google_calendar_sync import get_google_sync_instance


def test_google_auth():
    """Test Google Calendar authentication"""
    print("🧪 Testing Google Calendar Authentication")
    print("=" * 50)

    try:
        # Get the sync instance
        google_sync = get_google_sync_instance()
        print("✅ Google sync instance created")

        # Try to authenticate
        service = google_sync.authenticate_google()
        print("✅ Google Calendar authentication successful")

        # Test a simple API call
        try:
            calendar_list = service.calendarList().list().execute()
            calendars = calendar_list.get("items", [])
            print(f"✅ Successfully fetched {len(calendars)} calendars")

            for calendar in calendars[:3]:  # Show first 3 calendars
                print(
                    f"   📅 {calendar.get('summary', 'No name')} ({calendar.get('id', 'No ID')})"
                )

        except Exception as e:
            print(f"⚠️  API call failed: {e}")
            print("   This might be due to insufficient permissions")

        return True

    except FileNotFoundError as e:
        print(f"❌ Missing credentials file: {e}")
        print("\n📋 To fix this:")
        print("1. Run 'python setup_google_calendar.py' to create a template")
        print("2. Update credentials.json with your Google Cloud Console credentials")
        print("3. Run 'python authenticate_google.py' to authenticate")
        return False

    except RuntimeError as e:
        if "OAuth flow not supported" in str(e):
            print(f"❌ OAuth not supported in container: {e}")
            print("\n📋 To fix this:")
            print("1. Run 'python authenticate_google.py' on your host machine")
            print("2. Copy the generated token.json file to the container")
            print("3. Restart the container")
            return False
        else:
            print(f"❌ Runtime error: {e}")
            return False

    except Exception as e:
        print(f"❌ Authentication failed: {e}")
        return False


if __name__ == "__main__":
    success = test_google_auth()
    if success:
        print("\n🎉 All tests passed! Google Calendar integration is ready.")
    else:
        print("\n❌ Tests failed. Please fix the issues above.")
        sys.exit(1)
