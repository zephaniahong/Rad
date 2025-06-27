#!/usr/bin/env python3
"""
Test script for Radicale integration
Verifies that the FastAPI endpoints work correctly with Radicale
"""

import asyncio
import httpx
import json
from datetime import datetime, timedelta

BASE_URL = "http://localhost:8000"
RADICALE_URL = "http://localhost:5232"

async def test_radicale_status():
    """Test Radicale status endpoint"""
    print("Testing Radicale status...")
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/radicale/status")
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Radicale status: {data['status']}")
            return data['connected']
        else:
            print(f"✗ Failed to get Radicale status: {response.status_code}")
            return False

async def test_calendar_operations():
    """Test calendar operations"""
    print("\nTesting calendar operations...")
    async with httpx.AsyncClient() as client:
        # Get calendars
        response = await client.get(f"{BASE_URL}/radicale/calendars")
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Found {len(data['calendars'])} calendars")
            
            if data['calendars']:
                calendar_name = data['calendars'][0]['name']
                
                # Create an event
                event_data = {
                    "summary": "Test Event",
                    "description": "This is a test event",
                    "start": (datetime.now() + timedelta(hours=1)).isoformat(),
                    "end": (datetime.now() + timedelta(hours=2)).isoformat(),
                    "location": "Test Location"
                }
                
                response = await client.post(
                    f"{BASE_URL}/radicale/calendars/{calendar_name}/events",
                    json=event_data
                )
                
                if response.status_code == 200:
                    print("✓ Created test event")
                    
                    # Get events
                    response = await client.get(f"{BASE_URL}/radicale/calendars/{calendar_name}/events")
                    if response.status_code == 200:
                        events_data = response.json()
                        print(f"✓ Found {len(events_data['events'])} events")
                    else:
                        print(f"✗ Failed to get events: {response.status_code}")
                else:
                    print(f"✗ Failed to create event: {response.status_code}")
            else:
                print("⚠ No calendars found")
        else:
            print(f"✗ Failed to get calendars: {response.status_code}")

async def test_contact_operations():
    """Test contact operations"""
    print("\nTesting contact operations...")
    async with httpx.AsyncClient() as client:
        # Get address books
        response = await client.get(f"{BASE_URL}/radicale/addressbooks")
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Address books response: {data['message']}")
            
            # Create a contact
            contact_data = {
                "first_name": "Test",
                "last_name": "User",
                "email": "test@example.com",
                "phone": "+1-555-123-4567",
                "organization": "Test Corp"
            }
            
            response = await client.post(
                f"{BASE_URL}/radicale/addressbooks/default/contacts",
                json=contact_data
            )
            
            if response.status_code == 200:
                print("✓ Created test contact")
                data = response.json()
                print(f"  Contact ID: {data['contact_id']}")
            else:
                print(f"✗ Failed to create contact: {response.status_code}")
        else:
            print(f"✗ Failed to get address books: {response.status_code}")

async def test_radicale_direct():
    """Test direct connection to Radicale"""
    print("\nTesting direct Radicale connection...")
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(RADICALE_URL, timeout=5.0)
            if response.status_code == 200:
                print("✓ Radicale is accessible directly")
            else:
                print(f"⚠ Radicale returned status: {response.status_code}")
        except Exception as e:
            print(f"✗ Cannot connect to Radicale directly: {str(e)}")

async def main():
    """Run all tests"""
    print("Testing Radicale Integration")
    print("=" * 40)
    
    # Test direct Radicale connection
    await test_radicale_direct()
    
    # Test FastAPI integration
    await test_radicale_status()
    await test_calendar_operations()
    await test_contact_operations()
    
    print("\n" + "=" * 40)
    print("Test completed!")

if __name__ == "__main__":
    asyncio.run(main()) 