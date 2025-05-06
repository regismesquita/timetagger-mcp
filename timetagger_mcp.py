#!/usr/bin/env python3
"""
TimeTagger MCP Server

This MCP server provides tools to interact with a TimeTagger instance.
It allows querying records, updating records, and managing settings.

This version has been streamlined to reduce redundancy in the tools.
"""

import json
import os
import time
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any, Union

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
def get_records(
    start_time: Optional[int] = None, 
    end_time: Optional[int] = None,
    time_period: Optional[str] = None,
    tag: Optional[str] = None
) -> List[TimeRecord]:
    """
    Get TimeTagger records with flexible filtering options.

    Args:
        start_time: Start time as Unix timestamp (t1)
        end_time: End time as Unix timestamp (t2)
        time_period: Predefined time period - one of "today", "yesterday", "week", "month", "hours:N"
                    (where N is number of hours to look back)
        tag: Filter records by tag (with or without # prefix)

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
    
    # Handle predefined time periods
    if time_period:
        if time_period == "today":
            # Get today's start timestamp (midnight)
            today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            start_time = int(today.timestamp())
            end_time = now
        elif time_period == "yesterday":
            # Get yesterday's start and end timestamps
            today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            yesterday = today.timestamp() - 86400  # 24 hours in seconds
            start_time = int(yesterday)
            end_time = int(today.timestamp())
        elif time_period == "week":
            # Get start of week (last 7 days)
            start_time = now - (7 * 24 * 3600)
            end_time = now
        elif time_period == "month":
            # Get start of month (last 30 days)
            start_time = now - (30 * 24 * 3600)
            end_time = now
        elif time_period.startswith("hours:"):
            # Get records from the last N hours
            try:
                hours = int(time_period.split(":")[1])
                start_time = now - (hours * 3600)
                end_time = now
            except (IndexError, ValueError):
                raise ValueError("Invalid hours format. Use 'hours:N' where N is a number.")
    
    # Default to last 24 hours if no time parameters provided
    if start_time is None and end_time is None and not time_period:
        start_time = now - (24 * 3600)  # Default to last 24 hours
        end_time = now
    
    # Ensure both start and end times are set
    if start_time is None:
        start_time = 0  # Beginning of time
    if end_time is None:
        end_time = now
    
    # Get records from the API
    response = httpx.get(
        f"{API_BASE_URL}/records?timerange={start_time}-{end_time}",
        headers=get_headers(),
    )

    if response.status_code == 200:
        data = response.json()
        records = [TimeRecord(**record) for record in data["records"]]
        
        # Filter by tag if specified
        if tag:
            # Ensure tag has # prefix
            if not tag.startswith("#"):
                tag = f"#{tag}"
            
            # Filter records containing the tag
            records = [record for record in records if tag in record.ds]
            
        return records
    else:
        raise Exception(f"Error {response.status_code}: {response.text}")


@mcp.tool()
def manage_record(
    action: str,
    description: Optional[str] = None,
    start_time: Optional[int] = None,
    end_time: Optional[int] = None,
    key: Optional[str] = None,
) -> TimeRecord:
    """
    Create, update, or hide a TimeTagger record.

    Args:
        action: Action to perform - one of "create", "update", "hide", "start", "stop"
        description: Record description (can include tags with # prefix)
        start_time: Start time (t1) as Unix timestamp - when the activity began
        end_time: End time (t2) as Unix timestamp - when the activity ended
        key: Record unique identifier (required for update, hide, and stop actions)

    Returns:
        The created or updated TimeRecord
    """
    now = int(time.time())
    
    # Validate action
    valid_actions = ["create", "update", "hide", "start", "stop"]
    if action not in valid_actions:
        raise ValueError(f"Invalid action: {action}. Must be one of {valid_actions}")
    
    # Handle different actions
    if action == "create":
        if description is None:
            raise ValueError("Description is required for creating a record")
        
        # Set default times if not provided
        if start_time is None:
            start_time = now
        if end_time is None:
            end_time = start_time  # Ongoing record
            
        # Generate a random key
        record_key = str(uuid.uuid4().hex[:8])
        
        # Create the record object
        record = {
            "key": record_key,
            "t1": start_time,
            "t2": end_time,
            "ds": description,
            "mt": now,
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
            
    elif action == "start":
        # Start a timer (create an ongoing record)
        if description is None:
            raise ValueError("Description is required for starting a timer")
            
        # Create a record with t1 and t2 set to the current time
        return manage_record("create", description=description, start_time=now, end_time=now)
        
    elif action in ["update", "hide", "stop"]:
        if key is None:
            raise ValueError(f"Record key is required for {action} action")
            
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
            
        # Prepare the updated record based on the action
        if action == "hide":
            # By convention, records with description starting with "HIDDEN" are considered deleted
            if not current_record.ds.startswith("HIDDEN"):
                description = f"HIDDEN {current_record.ds}"
            else:
                description = current_record.ds
                
        elif action == "stop":
            # Stop a timer by setting the end time to now
            end_time = now
            description = current_record.ds
            
        # Update only the specified fields
        updated_record = {
            "key": key,
            "t1": start_time if start_time is not None else current_record.t1,
            "t2": end_time if end_time is not None else current_record.t2,
            "ds": description if description is not None else current_record.ds,
            "mt": now,
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
    
    # This should never happen due to the validation above
    raise ValueError(f"Unhandled action: {action}")


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
def manage_settings(
    action: str = "get",
    key: Optional[str] = None,
    value: Optional[Any] = None
) -> Union[List[TimeSetting], TimeSetting]:
    """
    Get or update TimeTagger settings.

    Args:
        action: Action to perform - one of "get" or "update"
        key: Setting key (required for update)
        value: New setting value (required for update)

    Returns:
        For "get" action: List of TimeSetting objects
        For "update" action: The updated TimeSetting
    """
    # Validate action
    valid_actions = ["get", "update"]
    if action not in valid_actions:
        raise ValueError(f"Invalid action: {action}. Must be one of {valid_actions}")
    
    if action == "get":
        # Get all settings
        response = httpx.get(f"{API_BASE_URL}/settings", headers=get_headers())

        if response.status_code == 200:
            data = response.json()
            return [TimeSetting(**setting) for setting in data["settings"]]
        else:
            raise Exception(f"Error {response.status_code}: {response.text}")
            
    elif action == "update":
        # Validate parameters
        if key is None:
            raise ValueError("Setting key is required for update action")
        if value is None:
            raise ValueError("Setting value is required for update action")
            
        # Create the setting object
        setting = {
            "key": key,
            "value": value,
            "mt": int(time.time()),
            "st": 0.0,  # Server will set this
        }

        # Send the setting to the server
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
    
    # This should never happen due to the validation above
    raise ValueError(f"Unhandled action: {action}")


@mcp.tool()
def analyze_time(
    analysis_type: str = "summary",
    time_period: str = "week",
    tag: Optional[str] = None
) -> Dict[str, Any]:
    """
    Analyze time records with various options.

    Args:
        analysis_type: Type of analysis - one of "summary", "daily", "hourly"
        time_period: Time period to analyze - one of "today", "yesterday", "week", "month", "hours:N"
        tag: Optional tag to filter by

    Returns:
        Dictionary with analysis results
    """
    # Get records for the specified time period
    records = get_records(time_period=time_period, tag=tag)
    
    # Skip hidden/deleted records
    records = [r for r in records if not r.ds.startswith("HIDDEN")]
    
    if analysis_type == "summary":
        # Extract tags from descriptions
        tag_hours = {}

        for record in records:
            # Calculate duration in hours
            duration = (record.t2 - record.t1) / 3600
            if duration < 0:
                continue  # Skip invalid records
                
            # Extract tags (words starting with #)
            tags = [word for word in record.ds.split() if word.startswith("#")]

            if not tags:
                # If no tags, count as "untagged"
                tag_key = "untagged"
                tag_hours[tag_key] = tag_hours.get(tag_key, 0) + duration
            else:
                # Add duration to each tag
                for tag_key in tags:
                    tag_hours[tag_key] = tag_hours.get(tag_key, 0) + duration

        return {"type": "summary", "data": tag_hours}
        
    elif analysis_type == "daily":
        # Group records by day
        daily_hours = {}
        
        for record in records:
            # Calculate duration in hours
            duration = (record.t2 - record.t1) / 3600
            if duration < 0:
                continue  # Skip invalid records
                
            # Get day from timestamp
            day = datetime.fromtimestamp(record.t1).strftime("%Y-%m-%d")
            
            # Add duration to day
            daily_hours[day] = daily_hours.get(day, 0) + duration
            
        return {"type": "daily", "data": daily_hours}
        
    elif analysis_type == "hourly":
        # Group records by hour of day
        hourly_distribution = {str(h): 0 for h in range(24)}
        
        for record in records:
            # Calculate duration in hours
            duration = (record.t2 - record.t1) / 3600
            if duration < 0:
                continue  # Skip invalid records
                
            # Get start and end hour
            start_hour = datetime.fromtimestamp(record.t1).hour
            end_hour = datetime.fromtimestamp(record.t2).hour
            
            # If record spans multiple hours, distribute proportionally
            if start_hour == end_hour:
                hourly_distribution[str(start_hour)] += duration
            else:
                # Simple distribution - just count start hour
                hourly_distribution[str(start_hour)] += duration
                
        return {"type": "hourly", "data": hourly_distribution}
        
    else:
        raise ValueError(f"Invalid analysis type: {analysis_type}")


def main():
    # Run the server
    mcp.run()

if __name__ == "__main__":
    main()
