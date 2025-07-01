#!/usr/bin/env python3
"""
Script to test if a CalDAV server supports sync tokens.
This script performs PROPFIND requests to check for sync-token support.
"""

import requests
from requests.auth import HTTPDigestAuth
import xml.etree.ElementTree as ET
from urllib.parse import urljoin
import logging
from typing import Dict, Optional, List
import json

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# CalDAV namespace
CALDAV_NS = "urn:ietf:params:xml:ns:caldav"
DAV_NS = "DAV:"


class CalDAVSyncTokenTester:
    def __init__(
        self,
        base_url: str,
        username: Optional[str] = None,
        password: Optional[str] = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.username = username
        self.password = password
        self.session = requests.Session()

        if username and password:
            self.session.auth = HTTPDigestAuth(username, password)

    def _make_propfind_request(self, url: str, props: List[str]) -> requests.Response:
        """Make a PROPFIND request with specified properties"""
        # Create PROPFIND XML body
        root = ET.Element("propfind", {"xmlns": DAV_NS})
        prop = ET.SubElement(root, "prop")

        for prop_name in props:
            if prop_name.startswith("caldav:"):
                # CalDAV property
                prop_elem = ET.SubElement(
                    prop, prop_name.replace("caldav:", ""), {"xmlns": CALDAV_NS}
                )
            else:
                # DAV property
                prop_elem = ET.SubElement(prop, prop_name)

        xml_body = ET.tostring(root, encoding="unicode")

        headers = {"Content-Type": "application/xml; charset=utf-8", "Depth": "0"}

        logger.info(f"Making PROPFIND request to: {url}")
        logger.info(f"Request body:\n{xml_body}")

        response = self.session.request("PROPFIND", url, data=xml_body, headers=headers)

        logger.info(f"Response status: {response.status_code}")
        logger.info(f"Response headers: {dict(response.headers)}")

        if response.content:
            logger.info(f"Response body:\n{response.text}")

        return response

    def check_sync_token_support(self) -> Dict:
        """Check if the CalDAV server supports sync tokens"""
        results = {
            "url": self.base_url,
            "supports_sync_tokens": False,
            "sync_token_property": None,
            "current_sync_token": None,
            "supported_properties": [],
            "errors": [],
        }

        try:
            # Test 1: Check for sync-token property support
            logger.info("=== Test 1: Checking sync-token property support ===")
            props = [
                "caldav:sync-token",
                "caldav:supported-calendar-component-set",
                "caldav:supported-calendar-data",
                "caldav:supported-collation-set",
                "caldav:calendar-description",
                "caldav:calendar-timezone",
                "caldav:calendar-color",
                "resourcetype",
            ]

            response = self._make_propfind_request(self.base_url, props)

            if response.status_code == 200:
                # Parse XML response
                try:
                    root = ET.fromstring(response.content)

                    # Check for sync-token in response
                    sync_token_elem = root.find(f".//{{{CALDAV_NS}}}sync-token")
                    if sync_token_elem is not None:
                        results["supports_sync_tokens"] = True
                        results["sync_token_property"] = "caldav:sync-token"
                        results["current_sync_token"] = sync_token_elem.text
                        logger.info(f"✅ Sync token found: {sync_token_elem.text}")
                    else:
                        logger.info("❌ No sync-token property found in response")

                    # Check for other supported properties
                    for prop in props:
                        prop_name = prop.replace("caldav:", "")
                        prop_elem = root.find(f".//{{{CALDAV_NS}}}{prop_name}")
                        if prop_elem is not None:
                            results["supported_properties"].append(prop)
                            logger.info(f"✅ Supported property: {prop}")
                        else:
                            logger.info(f"❌ Not supported: {prop}")

                except ET.ParseError as e:
                    results["errors"].append(f"Failed to parse XML response: {e}")
                    logger.error(f"XML parsing error: {e}")
            else:
                results["errors"].append(
                    f"PROPFIND request failed with status {response.status_code}"
                )
                logger.error(f"PROPFIND request failed: {response.status_code}")

        except Exception as e:
            results["errors"].append(f"Exception during sync token check: {e}")
            logger.error(f"Exception: {e}")

        # Test 2: Try to get current sync token
        if results["supports_sync_tokens"]:
            logger.info("=== Test 2: Getting current sync token ===")
            try:
                props = ["caldav:sync-token"]
                response = self._make_propfind_request(self.base_url, props)

                if response.status_code == 200:
                    root = ET.fromstring(response.content)
                    sync_token_elem = root.find(f".//{{{CALDAV_NS}}}sync-token")
                    if sync_token_elem is not None:
                        results["current_sync_token"] = sync_token_elem.text
                        logger.info(f"✅ Current sync token: {sync_token_elem.text}")
                    else:
                        logger.warning("⚠️ Sync token property not found in response")
                else:
                    logger.warning(
                        f"⚠️ Failed to get sync token: {response.status_code}"
                    )

            except Exception as e:
                results["errors"].append(f"Exception getting sync token: {e}")
                logger.error(f"Exception getting sync token: {e}")

        # Test 3: Check server capabilities
        logger.info("=== Test 3: Checking server capabilities ===")
        try:
            # Try to get server capabilities via OPTIONS request
            response = self.session.options(self.base_url)
            logger.info(f"OPTIONS response status: {response.status_code}")
            logger.info(f"OPTIONS headers: {dict(response.headers)}")

            # Check for CalDAV headers
            dav_header = response.headers.get("DAV", "")
            if "calendar-access" in dav_header:
                logger.info("✅ Server supports calendar-access")
            if "calendar-schedule" in dav_header:
                logger.info("✅ Server supports calendar-schedule")
            if "extended-mkcol" in dav_header:
                logger.info("✅ Server supports extended-mkcol")

        except Exception as e:
            results["errors"].append(f"Exception checking server capabilities: {e}")
            logger.error(f"Exception checking capabilities: {e}")

        return results

    def test_sync_collection(self, sync_token: Optional[str] = None) -> Dict:
        """Test sync-collection REPORT request"""
        results = {"success": False, "sync_token": None, "changes": [], "errors": []}

        try:
            logger.info("=== Test 4: Testing sync-collection REPORT ===")

            # Create sync-collection REPORT XML
            root = ET.Element("sync-collection", {"xmlns": DAV_NS})

            if sync_token:
                sync_token_elem = ET.SubElement(root, "sync-token")
                sync_token_elem.text = sync_token
                logger.info(f"Using sync token: {sync_token}")
            else:
                logger.info("No sync token provided, will get initial sync")

            prop = ET.SubElement(root, "prop")
            ET.SubElement(prop, "getetag", {"xmlns": DAV_NS})
            ET.SubElement(prop, "calendar-data", {"xmlns": CALDAV_NS})

            xml_body = ET.tostring(root, encoding="unicode")

            headers = {"Content-Type": "application/xml; charset=utf-8", "Depth": "1"}

            logger.info(f"Making sync-collection REPORT request to: {self.base_url}")
            logger.info(f"Request body:\n{xml_body}")

            response = self.session.request(
                "REPORT", self.base_url, data=xml_body, headers=headers
            )

            logger.info(f"REPORT response status: {response.status_code}")
            logger.info(f"REPORT response headers: {dict(response.headers)}")

            if response.status_code == 200:
                results["success"] = True

                # Parse response
                try:
                    root = ET.fromstring(response.content)

                    # Get new sync token
                    sync_token_elem = root.find(f".//{{{DAV_NS}}}sync-token")
                    if sync_token_elem is not None:
                        results["sync_token"] = sync_token_elem.text
                        logger.info(f"✅ New sync token: {sync_token_elem.text}")

                    # Get changes
                    responses = root.findall(f".//{{{DAV_NS}}}response")
                    for resp in responses:
                        href_elem = resp.find(f".//{{{DAV_NS}}}href")
                        status_elem = resp.find(f".//{{{DAV_NS}}}status")

                        if href_elem is not None:
                            href = href_elem.text
                            status = (
                                status_elem.text
                                if status_elem is not None
                                else "unknown"
                            )
                            results["changes"].append({"href": href, "status": status})
                            logger.info(f"Change: {href} - {status}")

                    logger.info(f"Total changes: {len(results['changes'])}")

                except ET.ParseError as e:
                    results["errors"].append(f"Failed to parse REPORT response: {e}")
                    logger.error(f"XML parsing error: {e}")

            elif response.status_code == 400:
                results["errors"].append(
                    "Bad request - sync-collection not supported or invalid sync token"
                )
                logger.error("Bad request - sync-collection not supported")
            elif response.status_code == 403:
                results["errors"].append("Forbidden - insufficient permissions")
                logger.error("Forbidden - insufficient permissions")
            else:
                results["errors"].append(
                    f"Unexpected status code: {response.status_code}"
                )
                logger.error(f"Unexpected status: {response.status_code}")

            if response.content:
                logger.info(f"REPORT response body:\n{response.text}")

        except Exception as e:
            results["errors"].append(f"Exception during sync-collection test: {e}")
            logger.error(f"Exception: {e}")

        return results


def main():
    """Main function to test CalDAV sync token support"""
    print("CalDAV Sync Token Support Tester")
    print("=" * 40)

    # Configuration
    base_url = "https://caldav.pixeltools.sg/caldav/index.php/calendars/4qk7%40zkf786op41h6/default/"
    username = input("Enter username (or press Enter if not needed): ").strip() or None
    password = input("Enter password (or press Enter if not needed): ").strip() or None

    print(f"\nTesting CalDAV server: {base_url}")
    print(f"Username: {username or 'None'}")
    print(f"Password: {'*' * len(password) if password else 'None'}")
    print()

    # Create tester
    tester = CalDAVSyncTokenTester(base_url, username, password)

    # Test sync token support
    results = tester.check_sync_token_support()

    # Print results
    print("\n" + "=" * 50)
    print("SYNC TOKEN SUPPORT RESULTS")
    print("=" * 50)

    print(f"URL: {results['url']}")
    print(
        f"Supports sync tokens: {'✅ YES' if results['supports_sync_tokens'] else '❌ NO'}"
    )

    if results["sync_token_property"]:
        print(f"Sync token property: {results['sync_token_property']}")

    if results["current_sync_token"]:
        print(f"Current sync token: {results['current_sync_token']}")

    if results["supported_properties"]:
        print(
            f"Supported CalDAV properties: {', '.join(results['supported_properties'])}"
        )

    if results["errors"]:
        print(f"Errors: {len(results['errors'])}")
        for error in results["errors"]:
            print(f"  - {error}")

    # Test sync-collection if sync tokens are supported
    if results["supports_sync_tokens"] and results["current_sync_token"]:
        print("\n" + "=" * 50)
        print("TESTING SYNC-COLLECTION REPORT")
        print("=" * 50)

        sync_results = tester.test_sync_collection(results["current_sync_token"])

        print(
            f"Sync-collection success: {'✅ YES' if sync_results['success'] else '❌ NO'}"
        )

        if sync_results["sync_token"]:
            print(f"New sync token: {sync_results['sync_token']}")

        if sync_results["changes"]:
            print(f"Changes detected: {len(sync_results['changes'])}")
            for change in sync_results["changes"]:
                print(f"  - {change['href']}: {change['status']}")

        if sync_results["errors"]:
            print(f"Sync errors: {len(sync_results['errors'])}")
            for error in sync_results["errors"]:
                print(f"  - {error}")

    # Save results to file
    output_file = "caldav_sync_token_test_results.json"
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2)

    print(f"\nResults saved to: {output_file}")

    # Summary
    print("\n" + "=" * 50)
    print("SUMMARY")
    print("=" * 50)

    if results["supports_sync_tokens"]:
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
    main()
