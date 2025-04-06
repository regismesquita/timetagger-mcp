#!/usr/bin/env python3
"""
TimeTagger MCP Server

This MCP server provides tools to interact with a TimeTagger instance.
It allows querying records, updating records, and managing settings.
"""

import json
import os
import time
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any

import httpx
from fastmcp import FastMCP
from pydantic import BaseModel


class TimeRecord(BaseModel):
    """A TimeTagger record"""

    key: Optional[str] = None
    t1: int  # Start time (Unix timestamp) - when the activity began
    t2: int  # End time (Unix timestamp) - when the activity ended or 0 for ongoing activities
    ds: str  # Description
    mt: Optional[int] = None  # Modified time (set by client)
    st: Optional[float] = 0.0  # Server time (set by server)


class TimeSetting(BaseModel):
    """A TimeTagger setting"""

    key: str
    value: Any
    mt: Optional[int] = None  # Modified time (set by client)
    st: Optional[float] = 0.0  # Server time (set by server)


# Create the MCP server
mcp = FastMCP("TimeTagger MCP", dependencies=["httpx", "pydantic"])


# Configuration
# Get API base URL from environment variable, with a default value
# Example: https://timetagger.myhost.com/timetagger/api/v2
API_BASE_URL = os.environ.get("TIMETAGGER_API_URL")
if not API_BASE_URL:
    raise ValueError(
        "TIMETAGGER_API_URL environment variable is not set. Please set it to your TimeTagger API base URL."
    )

# Get API token from environment variable
API_TOKEN = os.environ.get("TIMETAGGER_API_KEY")
if not API_TOKEN:
    raise ValueError(
        "TIMETAGGER_API_KEY environment variable is not set. Please set it to your TimeTagger API key."
    )


def get_headers():
    """Get the HTTP headers for API requests"""
    return {"authtoken": API_TOKEN, "Content-Type": "application/json"}


@mcp.resource("timetagger://config")
def get_config() -> str:
    """Get the TimeTagger configuration"""
    # Validate and extract server from API base URL
    if not API_BASE_URL.startswith(("http://", "https://")):
        raise ValueError("Invalid API base URL. Must start with http:// or https://")

    parts = API_BASE_URL.split("/")
    if len(parts) < 3:
        raise ValueError(
            "Invalid API base URL format. Expected format: https://example.com/api/v2"
        )

    server = parts[2]
    if not server:
        raise ValueError("Invalid API base URL. Missing server/domain")

    return json.dumps({"api_base_url": API_BASE_URL, "server": server}, indent=2)


@mcp.resource("timetagger://records/{timerange}")
def get_records_resource(timerange: str) -> str:
    """
    Get TimeTagger records within a timerange.

    Format: start-end (Unix timestamps)
    Example: 1743700000-1743800000
    """
    response = httpx.get(
        f"{API_BASE_URL}/records?timerange={timerange}", headers=get_headers()
    )

    if response.status_code == 200:
        return json.dumps(response.json(), indent=2)
    else:
        return f"Error: {response.status_code} - {response.text}"


@mcp.resource("timetagger://settings")
def get_settings_resource() -> str:
    """Get all TimeTagger settings"""
    response = httpx.get(f"{API_BASE_URL}/settings", headers=get_headers())

    if response.status_code == 200:
        return json.dumps(response.json(), indent=2)
    else:
        return f"Error: {response.status_code} - {response.text}"


@mcp.resource("timetagger://updates/{since}")
def get_updates_resource(since: str) -> str:
    """
    Get TimeTagger updates since a specific timestamp.

    Example: 1743700000
    """
    response = httpx.get(f"{API_BASE_URL}/updates?since={since}", headers=get_headers())

    if response.status_code == 200:
        return json.dumps(response.json(), indent=2)
    else:
        return f"Error: {response.status_code} - {response.text}"


@mcp.tool()
def get_records(start_time: int, end_time: int) -> List[TimeRecord]:
    """
    Get TimeTagger records within a time range.

    Args:
        start_time: Start time as Unix timestamp (t1)
        end_time: End time as Unix timestamp (t2)

    Returns:
        List of TimeRecord objects, each containing:
        - key: Unique identifier for the record
        - t1: Start time (Unix timestamp) - when the activity began
        - t2: End time (Unix timestamp) - when the activity ended
        - ds: Description (including tags with # prefix)
        - mt: Modified time
        - st: Server time
    """
    response = httpx.get(
        f"{API_BASE_URL}/records?timerange={start_time}-{end_time}",
        headers=get_headers(),
    )

    if response.status_code == 200:
        data = response.json()
        return [TimeRecord(**record) for record in data["records"]]
    else:
        raise Exception(f"Error {response.status_code}: {response.text}")


@mcp.tool()
def get_recent_records(hours: int = 24) -> List[TimeRecord]:
    """
    Get TimeTagger records from the last N hours.

    Args:
        hours: Number of hours to look back

    Returns:
        List of TimeRecord objects, each containing:
        - key: Unique identifier for the record
        - t1: Start time (Unix timestamp) - when the activity began
        - t2: End time (Unix timestamp) - when the activity ended
        - ds: Description (including tags with # prefix)
        - mt: Modified time
        - st: Server time
    """
    now = int(time.time())
    start_time = now - (hours * 3600)

    return get_records(start_time, now)


@mcp.tool()
def get_today_records() -> List[TimeRecord]:
    """
    Get TimeTagger records from today.

    Returns:
        List of TimeRecord objects, each containing:
        - key: Unique identifier for the record
        - t1: Start time (Unix timestamp) - when the activity began
        - t2: End time (Unix timestamp) - when the activity ended
        - ds: Description (including tags with # prefix)
        - mt: Modified time
        - st: Server time
    """
    # Get today's start timestamp (midnight)
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    start_time = int(today.timestamp())
    now = int(time.time())

    return get_records(start_time, now)


@mcp.tool()
def create_record(
    description: str, start_time: int, end_time: Optional[int] = None
) -> TimeRecord:
    """
    Create a new TimeTagger record.

    Args:
        description: Record description (can include tags with # prefix)
        start_time: Start time (t1) as Unix timestamp - when the activity began
        end_time: End time (t2) as Unix timestamp - when the activity ended (None for ongoing records)

    Returns:
        The created TimeRecord
    """
    # Generate a random key
    record_key = str(uuid.uuid4().hex[:8])

    # Set end_time to the same as start_time if not provided (ongoing record)
    if end_time is None:
        end_time = start_time

    # Create the record object
    record = {
        "key": record_key,
        "t1": start_time,
        "t2": end_time,
        "ds": description,
        "mt": int(time.time()),
        "st": 0.0,  # Server will set this
    }

    # Send the record to the server
    response = httpx.put(
        f"{API_BASE_URL}/records", headers=get_headers(), json=[record]
    )

    if response.status_code == 200:
        result = response.json()
        if record_key in result.get("accepted", []):
            return TimeRecord(**record)
        else:
            errors = result.get("errors", ["Unknown error"])
            raise Exception(f"Failed to create record: {', '.join(errors)}")
    else:
        raise Exception(f"Error {response.status_code}: {response.text}")


@mcp.tool()
def update_record(
    key: str,
    description: Optional[str] = None,
    start_time: Optional[int] = None,
    end_time: Optional[int] = None,
) -> TimeRecord:
    """
    Update an existing TimeTagger record.

    Args:
        key: Record unique identifier
        description: New description (if None, keep existing)
        start_time: New start time (t1) - when the activity began (if None, keep existing)
        end_time: New end time (t2) - when the activity ended (if None, keep existing)

    Returns:
        The updated TimeRecord
    """
    # First, get the current record to update only specified fields
    records = get_updates_since(0)

    # Find the record with the matching key
    current_record = None
    for record in records:
        if record.key == key:
            current_record = record
            break

    if not current_record:
        raise Exception(f"Record with key {key} not found")

    # Update only the specified fields
    updated_record = {
        "key": key,
        "t1": start_time if start_time is not None else current_record.t1,
        "t2": end_time if end_time is not None else current_record.t2,
        "ds": description if description is not None else current_record.ds,
        "mt": int(time.time()),
        "st": 0.0,  # Server will set this
    }

    # Send the updated record to the server
    response = httpx.put(
        f"{API_BASE_URL}/records", headers=get_headers(), json=[updated_record]
    )

    if response.status_code == 200:
        result = response.json()
        if key in result.get("accepted", []):
            return TimeRecord(**updated_record)
        else:
            errors = result.get("errors", ["Unknown error"])
            raise Exception(f"Failed to update record: {', '.join(errors)}")
    else:
        raise Exception(f"Error {response.status_code}: {response.text}")


@mcp.tool()
def hide_record(key: str) -> TimeRecord:
    """
    Hide a TimeTagger record (marks it as deleted).

    Args:
        key: Record unique identifier

    Returns:
        The hidden TimeRecord
    """
    # Get the current record
    records = get_updates_since(0)

    # Find the record with the matching key
    current_record = None
    for record in records:
        if record.key == key:
            current_record = record
            break

    if not current_record:
        raise Exception(f"Record with key {key} not found")

    # By convention, records with description starting with "HIDDEN" are considered deleted
    description = current_record.ds
    if not description.startswith("HIDDEN"):
        description = f"HIDDEN {description}"

    # Update the record with the HIDDEN prefix
    return update_record(key, description=description)


@mcp.tool()
def get_updates_since(since: int) -> List[TimeRecord]:
    """
    Get TimeTagger updates since a specific timestamp.

    Args:
        since: Timestamp to get updates from

    Returns:
        List of TimeRecord objects that have changed since the timestamp, each containing:
        - key: Unique identifier for the record
        - t1: Start time (Unix timestamp) - when the activity began
        - t2: End time (Unix timestamp) - when the activity ended
        - ds: Description (including tags with # prefix)
        - mt: Modified time
        - st: Server time
    """
    response = httpx.get(f"{API_BASE_URL}/updates?since={since}", headers=get_headers())

    if response.status_code == 200:
        data = response.json()
        return [TimeRecord(**record) for record in data["records"]]
    else:
        raise Exception(f"Error {response.status_code}: {response.text}")


@mcp.tool()
def get_server_time() -> float:
    """
    Get the current server time.

    Returns:
        Server time as Unix timestamp
    """
    response = httpx.get(
        f"{API_BASE_URL}/updates?since={int(time.time())}", headers=get_headers()
    )

    if response.status_code == 200:
        data = response.json()
        return data["server_time"]
    else:
        raise Exception(f"Error {response.status_code}: {response.text}")


@mcp.tool()
def get_settings() -> List[TimeSetting]:
    """
    Get all TimeTagger settings.

    Returns:
        List of TimeSetting objects, each containing:
        - key: Setting identifier
        - value: The setting value (can be any JSON-compatible type)
        - mt: Modified time
        - st: Server time
    """
    response = httpx.get(f"{API_BASE_URL}/settings", headers=get_headers())

    if response.status_code == 200:
        data = response.json()
        return [TimeSetting(**setting) for setting in data["settings"]]
    else:
        raise Exception(f"Error {response.status_code}: {response.text}")


@mcp.tool()
def update_setting(key: str, value: Any) -> TimeSetting:
    """
    Update a TimeTagger setting.

    Args:
        key: Setting key
        value: New setting value

    Returns:
        The updated TimeSetting
    """
    setting = {
        "key": key,
        "value": value,
        "mt": int(time.time()),
        "st": 0.0,  # Server will set this
    }

    response = httpx.put(
        f"{API_BASE_URL}/settings", headers=get_headers(), json=[setting]
    )

    if response.status_code == 200:
        result = response.json()
        if key in result.get("accepted", []):
            return TimeSetting(**setting)
        else:
            errors = result.get("errors", ["Unknown error"])
            raise Exception(f"Failed to update setting: {', '.join(errors)}")
    else:
        raise Exception(f"Error {response.status_code}: {response.text}")


@mcp.tool()
def start_timer(description: str) -> TimeRecord:
    """
    Start a new timer (create an ongoing record).

    Args:
        description: Record description (can include tags with # prefix)

    Returns:
        The created TimeRecord with t1 and t2 set to the current time
    """
    now = int(time.time())
    return create_record(description, now, now)


@mcp.tool()
def stop_timer(key: str) -> TimeRecord:
    """
    Stop an ongoing timer.

    Args:
        key: Record unique identifier

    Returns:
        The updated TimeRecord with t2 set to the current time
    """
    now = int(time.time())
    return update_record(key, end_time=now)


@mcp.tool()
def find_records_by_tag(tag: str, days: int = 30) -> List[TimeRecord]:
    """
    Find records with a specific tag.

    Args:
        tag: Tag to search for (without # prefix)
        days: Number of days to look back

    Returns:
        List of TimeRecord objects that match the tag, each containing:
        - key: Unique identifier for the record
        - t1: Start time (Unix timestamp) - when the activity began
        - t2: End time (Unix timestamp) - when the activity ended
        - ds: Description (including tags with # prefix)
        - mt: Modified time
        - st: Server time
    """
    # Ensure tag has # prefix
    if not tag.startswith("#"):
        tag = f"#{tag}"

    # Get records from the last N days
    now = int(time.time())
    start_time = now - (days * 24 * 3600)

    records = get_records(start_time, now)

    # Filter records containing the tag
    return [record for record in records if tag in record.ds]


@mcp.tool()
def get_time_summary(days: int = 7) -> Dict[str, float]:
    """
    Get a summary of time spent on different tags.

    Args:
        days: Number of days to include in the summary

    Returns:
        Dictionary mapping tags to hours spent
    """
    # Get records from the last N days
    now = int(time.time())
    start_time = now - (days * 24 * 3600)

    records = get_records(start_time, now)

    # Extract tags from descriptions
    tag_hours = {}

    for record in records:
        # Skip hidden/deleted records
        if record.ds.startswith("HIDDEN"):
            continue

        # Calculate duration in hours
        duration = (record.t2 - record.t1) / 3600

        # Extract tags (words starting with #)
        tags = [word for word in record.ds.split() if word.startswith("#")]

        if not tags:
            # If no tags, count as "untagged"
            tag = "untagged"
            tag_hours[tag] = tag_hours.get(tag, 0) + duration
        else:
            # Add duration to each tag
            for tag in tags:
                tag_hours[tag] = tag_hours.get(tag, 0) + duration

    return tag_hours


def main():
    # Run the server
    mcp.run()

if __name__ == "__main__":
    main()
