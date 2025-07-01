#!/usr/bin/env python3
"""
Script to manage Google Calendar sync tokens for incremental syncing.
"""

import os
import json
import logging
from google_calendar_sync import GoogleCalendarSync

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SYNC_TOKENS_FILE = "sync_tokens.json"


def show_sync_tokens():
    """Display current sync tokens"""
    try:
        if os.path.exists(SYNC_TOKENS_FILE):
            with open(SYNC_TOKENS_FILE, "r") as f:
                tokens = json.load(f)

            print("Current sync tokens:")
            print("=" * 50)
            for calendar_id, token in tokens.items():
                print(f"Calendar: {calendar_id}")
                print(
                    f"Token: {token[:30]}..." if len(token) > 30 else f"Token: {token}"
                )
                print("-" * 30)
        else:
            print("No sync tokens file found. Run a sync first to generate tokens.")
    except Exception as e:
        print(f"Error reading sync tokens: {e}")


def get_initial_sync_token(calendar_id="primary"):
    """Get initial sync token by performing a full sync"""
    try:
        print(f"Getting initial sync token for calendar: {calendar_id}")

        # Initialize Google Calendar sync
        google_sync = GoogleCalendarSync(
            radicale_url=os.getenv("RADICALE_URL", "http://localhost:5232"),
            radicale_username=os.getenv("RADICALE_USERNAME", "admin"),
            radicale_password=os.getenv("RADICALE_PASSWORD", "admin"),
        )

        # Authenticate
        google_sync.authenticate_google()

        # Perform initial sync to get sync token
        print("Performing initial sync to generate sync token...")
        events = google_sync.get_calendar_events_incremental(calendar_id)

        # Check if sync token was generated
        sync_token = google_sync._get_sync_token(calendar_id)
        if sync_token:
            print(f"✅ Successfully generated sync token: {sync_token[:30]}...")
            print(f"Synced {len(events)} events")
        else:
            print("❌ No sync token generated")

        return sync_token

    except Exception as e:
        print(f"❌ Error getting sync token: {e}")
        return None


def clear_sync_tokens():
    """Clear all sync tokens (forces full sync on next run)"""
    try:
        if os.path.exists(SYNC_TOKENS_FILE):
            os.remove(SYNC_TOKENS_FILE)
            print("✅ Sync tokens cleared")
        else:
            print("No sync tokens file to clear")
    except Exception as e:
        print(f"❌ Error clearing sync tokens: {e}")


def test_incremental_sync(calendar_id="primary"):
    """Test incremental sync functionality"""
    try:
        print(f"Testing incremental sync for calendar: {calendar_id}")

        # Initialize Google Calendar sync
        google_sync = GoogleCalendarSync(
            radicale_url=os.getenv("RADICALE_URL", "http://localhost:5232"),
            radicale_username=os.getenv("RADICALE_USERNAME", "admin"),
            radicale_password=os.getenv("RADICALE_PASSWORD", "admin"),
        )

        # Authenticate
        google_sync.authenticate_google()

        # Check if we have a sync token
        sync_token = google_sync._get_sync_token(calendar_id)
        if sync_token:
            print(f"Using existing sync token: {sync_token[:30]}...")
        else:
            print("No sync token found, will perform full sync")

        # Perform incremental sync
        events = google_sync.get_calendar_events_incremental(calendar_id)

        # Show results
        print(f"✅ Incremental sync completed")
        print(f"Events fetched: {len(events)}")

        # Show new sync token
        new_sync_token = google_sync._get_sync_token(calendar_id)
        if new_sync_token:
            print(f"New sync token: {new_sync_token[:30]}...")

        return events

    except Exception as e:
        print(f"❌ Error testing incremental sync: {e}")
        return None


def main():
    """Main function with menu"""
    print("Google Calendar Sync Token Manager")
    print("=" * 40)

    while True:
        print("\nOptions:")
        print("1. Show current sync tokens")
        print("2. Get initial sync token")
        print("3. Test incremental sync")
        print("4. Clear all sync tokens")
        print("5. Exit")

        choice = input("\nEnter your choice (1-5): ").strip()

        if choice == "1":
            show_sync_tokens()
        elif choice == "2":
            calendar_id = (
                input("Enter calendar ID (default: primary): ").strip() or "primary"
            )
            get_initial_sync_token(calendar_id)
        elif choice == "3":
            calendar_id = (
                input("Enter calendar ID (default: primary): ").strip() or "primary"
            )
            test_incremental_sync(calendar_id)
        elif choice == "4":
            confirm = (
                input("Are you sure you want to clear all sync tokens? (y/N): ")
                .strip()
                .lower()
            )
            if confirm == "y":
                clear_sync_tokens()
        elif choice == "5":
            print("Goodbye!")
            break
        else:
            print("Invalid choice. Please try again.")


if __name__ == "__main__":
    main()
