# TimeTagger MCP Server

This is a Model Context Protocol (MCP) server for interacting with TimeTagger. It provides tools to query and manage your time records through Claude or other MCP-compatible AI assistants.

## Features

- Query time records within specific timeframes
- Create new time records
- Update existing records
- Hide/delete records
- Get time summaries by tags
- Start and stop timers
- Manage TimeTagger settings

## Claude Desktop Installation
Add this to your `claude_desktop_config.json`:
```json
"timetagger": {
  "command": "uvx",
  "args": [
    "--from",
    "git+https://github.com/regismesquita/timetagger-mcp",
    "timetagger-mcp"
  ],
  "env": {
    "TIMETAGGER_API_KEY": "your-api-key-here",
    "TIMETAGGER_API_URL": "https://your-timetagger-instance.com/api/v2"
  }
}
```

## Manual Installation

1. Ensure you have [uv](https://github.com/astral-sh/uv) installed:
   ```
   brew install uv
   ```

2. Install the required dependencies:
   ```
   uv pip install -r requirements.txt
   ```

## Configuration

The server requires your TimeTagger API key to be set as an environment variable:

```
export TIMETAGGER_API_KEY="your-api-key-here"
export TIMETAGGER_API_URL="https://your-timetagger-instance.com/api/v2"
```

## Usage

### Running in Development Mode

For testing and development, use:

```
fastmcp dev timetagger_mcp.py
```

This will launch the MCP Inspector interface where you can test the tools and resources.

### Installing for Claude Desktop

To use with Claude Desktop:

```
fastmcp install timetagger_mcp.py
```

## Available Tools

- `get_records(start_time, end_time)`: Get records within a time range
- `get_recent_records(hours)`: Get records from the last N hours
- `get_today_records()`: Get today's records
- `create_record(description, start_time, end_time)`: Create a new record
- `update_record(key, description, start_time, end_time)`: Update an existing record
- `hide_record(key)`: Hide/delete a record
- `start_timer(description)`: Start a new timer
- `stop_timer(key)`: Stop an ongoing timer
- `find_records_by_tag(tag, days)`: Find records with a specific tag
- `get_time_summary(days)`: Get a summary of time spent on different tags
- `get_settings()`: Get all TimeTagger settings
- `update_setting(key, value)`: Update a TimeTagger setting

## Available Resources

- `timetagger://config`: Get the TimeTagger configuration
- `timetagger://records/{timerange}`: Get records within a timerange
- `timetagger://settings`: Get all settings
- `timetagger://updates/{since}`: Get updates since a specific timestamp
