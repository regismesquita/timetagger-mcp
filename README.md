# TimeTagger MCP Server

This is a Model Context Protocol (MCP) server for interacting with TimeTagger. It provides tools to query and manage your time records through Claude or other MCP-compatible AI assistants.

## Features

- Query time records with flexible filtering options (by time period, tags, etc.)
- Manage records with a unified interface (create, update, hide, start/stop timers)
- Analyze time data with various views (summary by tag, daily breakdown, hourly distribution)
- Manage TimeTagger settings
- Access server information and updates

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

- `get_records(start_time, end_time, time_period, tag)`: Get records with flexible filtering options
- `manage_record(action, description, start_time, end_time, key)`: Create, update, hide, start, or stop records
- `get_updates_since(since)`: Get records updated since a specific timestamp
- `get_server_time()`: Get the current server time
- `manage_settings(action, key, value)`: Get or update TimeTagger settings
- `analyze_time(analysis_type, time_period, tag)`: Analyze time records with various options

## Available Resources

- `timetagger://config`: Get the TimeTagger configuration
- `timetagger://records/{timerange}`: Get records within a timerange
- `timetagger://settings`: Get all settings
- `timetagger://updates/{since}`: Get updates since a specific timestamp
