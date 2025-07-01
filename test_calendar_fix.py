#!/usr/bin/env python3
"""
Test script to verify the calendar name construction fix
"""

import os
import sys
from google_calendar_sync import GoogleCalendarSync


def test_calendar_name_construction():
    """Test that calendar names are constructed correctly"""

    # Initialize the sync instance
    sync = GoogleCalendarSync(
        radicale_url=os.getenv("RADICALE_URL", "http://localhost:5232"),
        radicale_username=os.getenv("RADICALE_USERNAME", "admin"),
        radicale_password=os.getenv("RADICALE_PASSWORD", "admin"),
    )

    try:
        # Get Radicale client
        client = sync.get_radicale_client()
        principal = client.principal()
        calendars = principal.calendars()

        print(f"Found {len(calendars)} calendars in Radicale:")
        for cal in calendars:
            print(f"  - {cal.name}")

        # Test the calendar name construction
        username = "admin"
        calendar_name = "default"
        full_calendar_name = f"{username}/{calendar_name}"

        print(f"\nLooking for calendar: '{full_calendar_name}'")

        # Find the target calendar
        calendar = None
        for cal in calendars:
            if cal.name == full_calendar_name:
                calendar = cal
                break

        if calendar:
            print(f"✅ Found calendar: {calendar.name}")
            return True
        else:
            print(f"❌ Calendar '{full_calendar_name}' not found")
            print("Available calendars:")
            for cal in calendars:
                print(f"  - {cal.name}")
            return False

    except Exception as e:
        print(f"❌ Error testing calendar name construction: {str(e)}")
        return False


if __name__ == "__main__":
    print("Testing calendar name construction fix...")
    success = test_calendar_name_construction()

    if success:
        print("\n✅ Calendar name construction test passed!")
        sys.exit(0)
    else:
        print("\n❌ Calendar name construction test failed!")
        sys.exit(1)
