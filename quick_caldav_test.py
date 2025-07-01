#!/usr/bin/env python3
"""
Quick test to check if CalDAV API supports sync tokens.
This is a simplified version that doesn't require user input.
"""

import requests
from requests.auth import HTTPDigestAuth
import xml.etree.ElementTree as ET
import json

# CalDAV namespace
CALDAV_NS = "urn:ietf:params:xml:ns:caldav"
DAV_NS = "DAV:"


def test_caldav_sync_tokens():
    """Test if CalDAV server supports sync tokens"""

    # Configuration
    base_url = "https://caldav.pixeltools.sg/caldav/index.php/calendars/4qk7%40zkf786op41h6/default/"

    print("Testing CalDAV sync token support...")
    print(f"URL: {base_url}")
    print()

    # Get credentials
    username = input("Enter username: ").strip()
    password = input("Enter password: ").strip()

    print(f"Username: {username}")
    print(f"Password: {'*' * len(password)}")
    print()

    # Create session with digest authentication
    session = requests.Session()
    session.auth = HTTPDigestAuth(username, password)

    # Test 1: Basic PROPFIND to check sync-token property
    print("=== Test 1: Checking sync-token property ===")

    # Create PROPFIND XML
    root = ET.Element("propfind", {"xmlns": DAV_NS})
    prop = ET.SubElement(root, "prop")
    ET.SubElement(prop, "sync-token", {"xmlns": CALDAV_NS})
    ET.SubElement(prop, "resourcetype", {"xmlns": DAV_NS})

    xml_body = ET.tostring(root, encoding="unicode")

    headers = {"Content-Type": "application/xml; charset=utf-8", "Depth": "0"}

    try:
        response = session.request("PROPFIND", base_url, data=xml_body, headers=headers)

        print(f"Response status: {response.status_code}")
        print(f"Response headers: {dict(response.headers)}")

        if response.status_code == 200:
            print("✅ PROPFIND request successful")

            # Parse response
            try:
                root = ET.fromstring(response.content)

                # Check for sync-token
                sync_token_elem = root.find(f".//{{{CALDAV_NS}}}sync-token")
                if sync_token_elem is not None:
                    print(f"✅ Sync token found: {sync_token_elem.text}")
                    supports_sync_tokens = True
                else:
                    print("❌ No sync-token property found")
                    supports_sync_tokens = False

                # Check resource type
                resourcetype_elem = root.find(f".//{{{DAV_NS}}}resourcetype")
                if resourcetype_elem is not None:
                    calendar_elem = resourcetype_elem.find(
                        f".//{{{CALDAV_NS}}}calendar"
                    )
                    if calendar_elem is not None:
                        print("✅ Resource is a calendar")
                    else:
                        print("⚠️ Resource type not identified as calendar")

            except ET.ParseError as e:
                print(f"❌ Failed to parse XML response: {e}")
                supports_sync_tokens = False

        else:
            print(f"❌ PROPFIND request failed: {response.status_code}")
            supports_sync_tokens = False

        if response.content:
            print(f"Response body:\n{response.text}")

    except Exception as e:
        print(f"❌ Exception during PROPFIND: {e}")
        supports_sync_tokens = False

    print()

    # Test 2: Check server capabilities via OPTIONS
    print("=== Test 2: Checking server capabilities ===")

    try:
        response = session.options(base_url)
        print(f"OPTIONS response status: {response.status_code}")

        # Check for CalDAV headers
        dav_header = response.headers.get("DAV", "")
        print(f"DAV header: {dav_header}")

        if "calendar-access" in dav_header:
            print("✅ Server supports calendar-access")
        if "calendar-schedule" in dav_header:
            print("✅ Server supports calendar-schedule")
        if "extended-mkcol" in dav_header:
            print("✅ Server supports extended-mkcol")

    except Exception as e:
        print(f"❌ Exception during OPTIONS: {e}")

    print()

    # Test 3: Try sync-collection REPORT if sync tokens are supported
    if supports_sync_tokens:
        print("=== Test 3: Testing sync-collection REPORT ===")

        # Create sync-collection REPORT XML
        root = ET.Element("sync-collection", {"xmlns": DAV_NS})
        prop = ET.SubElement(root, "prop")
        ET.SubElement(prop, "getetag", {"xmlns": DAV_NS})
        ET.SubElement(prop, "calendar-data", {"xmlns": CALDAV_NS})

        xml_body = ET.tostring(root, encoding="unicode")

        headers = {"Content-Type": "application/xml; charset=utf-8", "Depth": "1"}

        try:
            response = session.request(
                "REPORT", base_url, data=xml_body, headers=headers
            )

            print(f"REPORT response status: {response.status_code}")

            if response.status_code == 200:
                print("✅ Sync-collection REPORT successful")

                # Parse response
                try:
                    root = ET.fromstring(response.content)

                    # Get sync token
                    sync_token_elem = root.find(f".//{{{DAV_NS}}}sync-token")
                    if sync_token_elem is not None:
                        print(f"✅ New sync token: {sync_token_elem.text}")

                    # Count responses
                    responses = root.findall(f".//{{{DAV_NS}}}response")
                    print(f"✅ Found {len(responses)} calendar items")

                except ET.ParseError as e:
                    print(f"❌ Failed to parse REPORT response: {e}")

            elif response.status_code == 400:
                print("❌ Bad request - sync-collection not supported")
            elif response.status_code == 403:
                print("❌ Forbidden - insufficient permissions")
            else:
                print(f"❌ Unexpected status: {response.status_code}")

        except Exception as e:
            print(f"❌ Exception during REPORT: {e}")

    print()
    print("=" * 50)
    print("SUMMARY")
    print("=" * 50)

    if supports_sync_tokens:
        print("✅ This CalDAV server supports sync tokens!")
        print(
            "✅ You can implement incremental sync using sync-collection REPORT requests"
        )
        print("✅ This will be much more efficient than full calendar downloads")
    else:
        print("❌ This CalDAV server does not support sync tokens")
        print("❌ You'll need to implement full calendar sync (less efficient)")
        print(
            "❌ Consider polling for changes or implementing your own change detection"
        )


if __name__ == "__main__":
    test_caldav_sync_tokens()
