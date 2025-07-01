#!/usr/bin/env python3
"""
Test script to debug webhook data and test improved notification processing
"""

import requests
import json
import time
from datetime import datetime

# Configuration
BASE_URL = "http://localhost:8000"


def test_webhook_with_different_payloads():
    """Test webhook with different payload formats to see what data we receive"""

    test_cases = [
        {
            "name": "Google Calendar headers only",
            "headers": {
                "X-Goog-Resource-State": "exists",
                "X-Goog-Resource-Id": "test-resource-id-123",
                "X-Goog-Resource-Uri": "https://www.googleapis.com/calendar/v3/calendars/primary/events",
                "X-Goog-Channel-Id": "test-channel-123",
                "X-Goog-Message-Number": "1",
            },
            "body": {},
        },
        {
            "name": "Google Calendar headers with event ID in URI",
            "headers": {
                "X-Goog-Resource-State": "exists",
                "X-Goog-Resource-Id": "test-resource-id-456",
                "X-Goog-Resource-Uri": "https://www.googleapis.com/calendar/v3/calendars/primary/events/abc123event456",
                "X-Goog-Channel-Id": "test-channel-456",
                "X-Goog-Message-Number": "2",
            },
            "body": {},
        },
        {
            "name": "JSON payload with event ID",
            "headers": {},
            "body": {
                "resourceId": "test-resource-id-789",
                "resourceUri": "https://www.googleapis.com/calendar/v3/calendars/primary/events",
                "state": "exists",
                "eventId": "def789event123",
            },
        },
        {
            "name": "JSON payload with event_id",
            "headers": {},
            "body": {
                "resourceId": "test-resource-id-101",
                "resourceUri": "https://www.googleapis.com/calendar/v3/calendars/primary/events",
                "state": "exists",
                "event_id": "ghi101event456",
            },
        },
        {
            "name": "Event deletion notification",
            "headers": {
                "X-Goog-Resource-State": "not_exists",
                "X-Goog-Resource-Id": "test-resource-id-202",
                "X-Goog-Resource-Uri": "https://www.googleapis.com/calendar/v3/calendars/primary/events/jkl202event789",
                "X-Goog-Channel-Id": "test-channel-202",
                "X-Goog-Message-Number": "3",
            },
            "body": {},
        },
    ]

    print("Testing webhook with different payload formats...")
    print("=" * 60)

    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{i}. {test_case['name']}")
        print("-" * 40)

        try:
            # Make the webhook request
            response = requests.post(
                f"{BASE_URL}/webhook/google-calendar",
                headers=test_case["headers"],
                json=test_case["body"] if test_case["body"] else None,
            )

            print(f"Status Code: {response.status_code}")
            print(f"Response: {response.json()}")

            if response.status_code == 200:
                data = response.json()
                task_id = data.get("task_id")
                if task_id:
                    print(f"Task ID: {task_id}")
                    # Wait a moment and check task status
                    time.sleep(2)
                    check_task_status(task_id)

        except Exception as e:
            print(f"Error: {str(e)}")

        print()


def check_task_status(task_id):
    """Check the status of a Celery task"""
    try:
        response = requests.get(f"{BASE_URL}/google-calendar/sync/status/{task_id}")
        if response.status_code == 200:
            data = response.json()
            status = data.get("status")
            print(f"Task Status: {status}")

            if status == "completed":
                result = data.get("result", {})
                if result.get("success"):
                    print("✅ Task completed successfully")
                else:
                    print(f"❌ Task failed: {result.get('error', 'Unknown error')}")
            elif status == "failed":
                print(f"❌ Task failed: {data.get('error', 'Unknown error')}")
        else:
            print(f"❌ Failed to check task status: {response.status_code}")
    except Exception as e:
        print(f"❌ Error checking task status: {str(e)}")


def test_single_event_sync():
    """Test syncing a single event by ID"""
    print("\nTesting single event sync...")
    print("=" * 40)

    # This would require a real Google Calendar event ID
    # For now, we'll just test the endpoint structure
    test_event_id = "test_event_123"

    try:
        # Test the manual sync endpoint
        response = requests.post(
            f"{BASE_URL}/google-calendar/sync",
            json={
                "username": "admin",
                "calendar_name": "default",
                "google_calendar_id": "primary",
                "sync_type": "incremental",
            },
        )

        print(f"Manual sync response: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Task ID: {data.get('task_id')}")
            print(f"Status: {data.get('status')}")
    except Exception as e:
        print(f"Error testing manual sync: {str(e)}")


if __name__ == "__main__":
    print("Webhook Debug Test Script")
    print("=" * 60)

    # Test webhook with different payloads
    test_webhook_with_different_payloads()

    # Test single event sync
    test_single_event_sync()

    print("\nDebug test completed!")
