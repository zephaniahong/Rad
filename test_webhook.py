#!/usr/bin/env python3
"""
Test script to demonstrate Google Calendar webhook functionality
"""

import requests
import json
import time
from datetime import datetime, timedelta


def test_webhook_endpoint():
    """Test the webhook endpoint with simulated Google Calendar notifications"""

    # Test 1: Basic webhook notification
    print("=== Test 1: Basic webhook notification ===")
    notification = {
        "resourceId": "test-resource-123",
        "resourceUri": "https://www.googleapis.com/calendar/v3/calendars/primary/events",
        "state": "exists",
        "expiration": (datetime.now() + timedelta(hours=24)).isoformat() + "Z",
    }

    response = requests.post(
        "http://localhost:8000/webhook/google-calendar",
        json=notification,
        headers={"Content-Type": "application/json"},
    )

    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.json()}")

    if response.status_code == 200:
        task_id = response.json().get("task_id")
        print(f"Task ID: {task_id}")

        # Test 2: Check task status
        print("\n=== Test 2: Check task status ===")
        time.sleep(2)  # Wait a bit for task to process

        status_response = requests.get(
            f"http://localhost:8000/google-calendar/sync/status/{task_id}"
        )
        print(f"Status Code: {status_response.status_code}")
        print(f"Response: {status_response.json()}")


def test_manual_sync():
    """Test manual sync functionality"""
    print("\n=== Test 3: Manual sync ===")

    sync_request = {
        "username": "admin",
        "calendar_name": "default",
        "google_calendar_id": "primary",
        "sync_type": "full",
    }

    response = requests.post(
        "http://localhost:8000/google-calendar/sync",
        json=sync_request,
        headers={"Content-Type": "application/json"},
    )

    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.json()}")

    if response.status_code == 200:
        task_id = response.json().get("task_id")
        print(f"Sync Task ID: {task_id}")

        # Check sync status
        print("\n=== Test 4: Check sync status ===")
        time.sleep(2)

        status_response = requests.get(
            f"http://localhost:8000/google-calendar/sync/status/{task_id}"
        )
        print(f"Status Code: {status_response.status_code}")
        print(f"Response: {status_response.json()}")


def test_webhook_setup():
    """Test webhook setup (will fail with localhost but shows the process)"""
    print("\n=== Test 5: Webhook setup (will fail with localhost) ===")

    response = requests.post(
        "http://localhost:8000/google-calendar/setup-webhook?calendar_id=primary",
        headers={"Content-Type": "application/json"},
    )

    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.json()}")


def main():
    """Main test function"""
    print("Testing Google Calendar Webhook Functionality")
    print("=" * 50)

    try:
        # Test basic webhook functionality
        test_webhook_endpoint()

        # Test manual sync
        test_manual_sync()

        # Test webhook setup (will fail with localhost)
        test_webhook_setup()

    except requests.exceptions.ConnectionError:
        print("Error: Could not connect to FastAPI server at http://localhost:8000")
        print("Make sure the server is running with: python main.py")
    except Exception as e:
        print(f"Error during testing: {e}")


if __name__ == "__main__":
    main()
