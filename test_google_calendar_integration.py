#!/usr/bin/env python3
"""
Test script for Google Calendar integration with Radicale
"""

import os
import sys
import json
import requests
from datetime import datetime, timedelta

# Configuration
BASE_URL = "http://localhost:8000"
RADICALE_URL = os.getenv("RADICALE_URL", "http://localhost:5232")

def test_health_check():
    """Test if the FastAPI application is running"""
    print("Testing health check...")
    try:
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code == 200:
            print("✅ Health check passed")
            return True
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Health check failed: {str(e)}")
        return False

def test_radicale_status():
    """Test Radicale connection"""
    print("Testing Radicale connection...")
    try:
        response = requests.get(f"{BASE_URL}/radicale/status")
        if response.status_code == 200:
            data = response.json()
            if data.get("connected"):
                print("✅ Radicale connection successful")
                return True
            else:
                print("❌ Radicale connection failed")
                return False
        else:
            print(f"❌ Radicale status check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Radicale status check failed: {str(e)}")
        return False

def test_google_calendar_sync():
    """Test Google Calendar sync endpoint"""
    print("Testing Google Calendar sync endpoint...")
    try:
        sync_data = {
            "username": "admin",
            "calendar_name": "default",
            "google_calendar_id": "primary",
            "sync_type": "full"
        }
        
        response = requests.post(f"{BASE_URL}/google-calendar/sync", json=sync_data)
        if response.status_code == 200:
            data = response.json()
            task_id = data.get("task_id")
            print(f"✅ Sync started successfully, task_id: {task_id}")
            return task_id
        else:
            print(f"❌ Sync failed: {response.status_code}")
            print(f"Response: {response.text}")
            return None
    except Exception as e:
        print(f"❌ Sync test failed: {str(e)}")
        return None

def test_sync_status(task_id):
    """Test sync status endpoint"""
    if not task_id:
        return False
    
    print(f"Testing sync status for task {task_id}...")
    try:
        response = requests.get(f"{BASE_URL}/google-calendar/sync/status/{task_id}")
        if response.status_code == 200:
            data = response.json()
            status = data.get("status")
            print(f"✅ Sync status: {status}")
            if status == "completed":
                result = data.get("result", {})
                synced = result.get("synced_events", 0)
                total = result.get("total_events", 0)
                print(f"   Synced {synced}/{total} events")
            return True
        else:
            print(f"❌ Status check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Status check failed: {str(e)}")
        return False

def test_webhook_endpoint():
    """Test webhook endpoint"""
    print("Testing webhook endpoint...")
    try:
        webhook_data = {
            "resourceId": "test-resource-id",
            "resourceUri": "https://www.googleapis.com/calendar/v3/calendars/primary/events",
            "state": "sync"
        }
        
        response = requests.post(f"{BASE_URL}/webhook/google-calendar", json=webhook_data)
        if response.status_code == 200:
            data = response.json()
            task_id = data.get("task_id")
            print(f"✅ Webhook test successful, task_id: {task_id}")
            return True
        else:
            print(f"❌ Webhook test failed: {response.status_code}")
            print(f"Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Webhook test failed: {str(e)}")
        return False

def test_google_calendar_setup():
    """Test Google Calendar setup endpoint"""
    print("Testing Google Calendar setup endpoint...")
    try:
        response = requests.post(f"{BASE_URL}/google-calendar/setup-webhook?calendar_id=primary")
        if response.status_code == 200:
            data = response.json()
            webhook_url = data.get("webhook_url")
            print(f"✅ Setup endpoint working, webhook_url: {webhook_url}")
            return True
        else:
            print(f"❌ Setup test failed: {response.status_code}")
            print(f"Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Setup test failed: {str(e)}")
        return False

def check_credentials():
    """Check if Google Calendar credentials are available"""
    print("Checking Google Calendar credentials...")
    
    credentials_file = "credentials.json"
    token_file = "token.json"
    
    if not os.path.exists(credentials_file):
        print(f"❌ {credentials_file} not found")
        print("   Please run: python setup_google_calendar.py")
        return False
    
    if not os.path.exists(token_file):
        print(f"⚠️  {token_file} not found")
        print("   Please authenticate with Google Calendar API")
        return False
    
    print("✅ Google Calendar credentials found")
    return True

def main():
    """Run all tests"""
    print("=== Google Calendar Integration Test ===")
    print(f"Testing against: {BASE_URL}")
    print()
    
    # Check prerequisites
    if not check_credentials():
        print("\nPlease set up Google Calendar credentials first.")
        return
    
    # Run tests
    tests = [
        ("Health Check", test_health_check),
        ("Radicale Status", test_radicale_status),
        ("Webhook Endpoint", test_webhook_endpoint),
        ("Google Calendar Setup", test_google_calendar_setup),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n--- {test_name} ---")
        if test_func():
            passed += 1
        print()
    
    # Test sync if other tests pass
    if passed == total:
        print("--- Google Calendar Sync ---")
        task_id = test_google_calendar_sync()
        if task_id:
            print("--- Sync Status ---")
            test_sync_status(task_id)
            passed += 1
        total += 1
    
    # Summary
    print("\n=== Test Summary ===")
    print(f"Passed: {passed}/{total}")
    
    if passed == total:
        print("✅ All tests passed! Google Calendar integration is working.")
    else:
        print("❌ Some tests failed. Please check the configuration and try again.")
        print("\nTroubleshooting tips:")
        print("1. Ensure all services are running (FastAPI, Redis, Celery, Radicale)")
        print("2. Check environment variables and configuration")
        print("3. Verify Google Calendar credentials")
        print("4. Check logs for detailed error messages")

if __name__ == "__main__":
    main() 