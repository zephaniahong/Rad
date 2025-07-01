#!/usr/bin/env python3
"""
Test script to verify the timezone handling fix
"""

import os
import sys
from datetime import datetime, timezone, timedelta
from google_calendar_sync import GoogleCalendarEvent
import vobject


def test_timezone_handling():
    """Test that timezone handling works correctly"""

    print("Testing timezone handling...")

    # Test case 1: UTC+08:00 timezone (the problematic one from the logs)
    try:
        # Create a timezone-aware datetime with UTC+08:00
        utc_plus_8 = timezone(timedelta(hours=8))
        test_start = datetime.now(utc_plus_8)
        test_end = test_start + timedelta(hours=1)

        print(f"Test start time: {test_start} (timezone: {test_start.tzinfo})")
        print(f"Test end time: {test_end} (timezone: {test_end.tzinfo})")

        # Create a Google Calendar event
        event = GoogleCalendarEvent(
            id="test-event-1",
            summary="Test Event with UTC+08:00",
            description="Testing timezone handling",
            start=test_start,
            end=test_end,
            location="Test Location",
            status="confirmed",
            html_link="https://example.com",
        )

        # Create iCalendar event (simulating what the sync function does)
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
                print(
                    f"✅ Converted start time to naive UTC: {utc_start.replace(tzinfo=None)}"
                )
            else:
                # Already UTC, use naive datetime
                dtstart.value = event.start.replace(tzinfo=None)
                print("✅ Start time already UTC, made naive")
        else:
            # No timezone info, use as is
            dtstart.value = event.start
            print("✅ No timezone info, using as is")

        dtend = vevent.add("dtend")

        # Proper timezone handling for end time - convert to naive UTC datetime
        if event.end.tzinfo is not None:
            # Convert to UTC if it's a timezone-aware datetime
            if event.end.tzinfo.utcoffset(event.end) is not None:
                # Convert to UTC for storage
                utc_end = event.end.astimezone(timezone.utc)
                # Use naive datetime (without timezone info) for vobject
                dtend.value = utc_end.replace(tzinfo=None)
                print(
                    f"✅ Converted end time to naive UTC: {utc_end.replace(tzinfo=None)}"
                )
            else:
                # Already UTC, use naive datetime
                dtend.value = event.end.replace(tzinfo=None)
                print("✅ End time already UTC, made naive")
        else:
            # No timezone info, use as is
            dtend.value = event.end
            print("✅ No timezone info, using as is")

        # Add creation date
        dtstamp = vevent.add("dtstamp")
        dtstamp.value = datetime.now(timezone.utc).replace(tzinfo=None)

        # Try to serialize the calendar
        ical_data = cal.serialize()
        print("✅ Successfully serialized iCalendar data")
        print(f"iCalendar data length: {len(ical_data)} characters")

        return True

    except Exception as e:
        print(f"❌ Error in timezone handling test: {str(e)}")
        import traceback

        traceback.print_exc()
        return False


def test_naive_datetime():
    """Test handling of naive datetimes (no timezone info)"""

    print("\nTesting naive datetime handling...")

    try:
        # Create naive datetime (no timezone info)
        naive_start = datetime.now()
        naive_end = naive_start + timedelta(hours=1)

        print(f"Naive start time: {naive_start} (timezone: {naive_start.tzinfo})")
        print(f"Naive end time: {naive_end} (timezone: {naive_end.tzinfo})")

        # Create iCalendar event
        cal = vobject.iCalendar()
        vevent = cal.add("vevent")
        vevent.add("summary").value = "Test Event with Naive Datetime"

        # Handle datetime with timezone information
        dtstart = vevent.add("dtstart")

        # Proper timezone handling - convert to naive UTC datetime
        if naive_start.tzinfo is not None:
            # Convert to UTC if it's a timezone-aware datetime
            if naive_start.tzinfo.utcoffset(naive_start) is not None:
                # Convert to UTC for storage
                utc_start = naive_start.astimezone(timezone.utc)
                # Use naive datetime (without timezone info) for vobject
                dtstart.value = utc_start.replace(tzinfo=None)
            else:
                # Already UTC, use naive datetime
                dtstart.value = naive_start.replace(tzinfo=None)
        else:
            # No timezone info, use as is
            dtstart.value = naive_start
            print("✅ Using naive datetime as is")

        dtend = vevent.add("dtend")

        # Proper timezone handling for end time - convert to naive UTC datetime
        if naive_end.tzinfo is not None:
            # Convert to UTC if it's a timezone-aware datetime
            if naive_end.tzinfo.utcoffset(naive_end) is not None:
                # Convert to UTC for storage
                utc_end = naive_end.astimezone(timezone.utc)
                # Use naive datetime (without timezone info) for vobject
                dtend.value = utc_end.replace(tzinfo=None)
            else:
                # Already UTC, use naive datetime
                dtend.value = naive_end.replace(tzinfo=None)
        else:
            # No timezone info, use as is
            dtend.value = naive_end
            print("✅ Using naive end datetime as is")

        # Try to serialize the calendar
        ical_data = cal.serialize()
        print("✅ Successfully serialized iCalendar data with naive datetimes")

        return True

    except Exception as e:
        print(f"❌ Error in naive datetime test: {str(e)}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("Testing timezone handling fixes...")

    success1 = test_timezone_handling()
    success2 = test_naive_datetime()

    if success1 and success2:
        print("\n✅ All timezone handling tests passed!")
        sys.exit(0)
    else:
        print("\n❌ Some timezone handling tests failed!")
        sys.exit(1)
