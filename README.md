# Gmail Voice Messaging Server

A Flask server and MCP (Model Context Protocol) server that integrates with Gmail API to read and send messages using desktop authentication.

## Setup

1. **Install dependencies:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Set up Google OAuth credentials:**
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project or select an existing one
   - Enable the Gmail API
   - Create OAuth 2.0 credentials (**Desktop application**, not Web application)
   - Copy `.env.example` to `.env` and fill in your credentials

3. **Authenticate with Gmail:**
   ```bash
   python desktop_auth.py
   ```
   This will open your browser for Gmail authentication and save credentials locally.

## Usage Options

### Option 1: Web Interface

4. **Run the Flask server:**
   ```bash
   python run.py
   ```

5. **Use the web application:**
   - Visit http://localhost:5000
   - Access Gmail features through the web interface
   - Authentication happens automatically using saved credentials

### Option 2: MCP Server

4. **Run the MCP server:**
   ```bash
   python mcp_run.py
   ```

5. **Connect with MCP clients:**
   - The server provides Gmail tools via the Model Context Protocol
   - Connect using any MCP-compatible client or framework
   - Use the tools for reading and sending Gmail messages

## Features

- **Authentication**: Desktop OAuth authentication (no web callback required)
- **Gmail Operations**: Read messages, send messages, search with filters
- **Dual Interface**: Both web UI and MCP server functionality
- **Auto Refresh**: Automatic credential refresh
- **Search**: Advanced Gmail search with filters (sender, subject, attachments, etc.)

## Files

### Core Components
- `desktop_auth.py` - Standalone authentication script
- `src/auth.py` - Authentication module using InstalledAppFlow
- `src/gmail_service.py` - Gmail API operations

### Web Interface
- `src/app.py` - Flask web interface
- `run.py` - Flask server entry point

### MCP Server
- `src/mcp_server.py` - MCP server implementation
- `mcp_run.py` - MCP server entry point
- `mcp_config.json` - MCP server configuration

## Web API Endpoints

- `GET /` - Home page with connection status
- `GET /messages` - View recent messages
- `GET|POST /send` - Send message form/handler
- `GET /logout` - Disconnect Gmail account

## MCP Tools

The MCP server provides these tools for AI assistants and clients:

### `get_gmail_messages`
Retrieve Gmail messages with optional query filtering.
- **Parameters**: `query` (string), `max_results` (integer)
- **Returns**: List of message objects with id, subject, sender, date, body

### `send_gmail_message`
Send a Gmail message.
- **Parameters**: `to` (string), `subject` (string), `body` (string)
- **Returns**: Message status and ID

### `get_gmail_auth_status`
Check Gmail authentication status.
- **Parameters**: None
- **Returns**: Authentication status and expiry info

### `search_gmail_messages`
Search Gmail messages with specific criteria.
- **Parameters**: `from_email`, `subject_contains`, `has_attachment`, `is_unread`, `newer_than`, `max_results`
- **Returns**: List of matching messages

## Integration with Claude Desktop

To use this as an MCP server with Claude Desktop, add to your configuration:

```json
{
  "mcpServers": {
    "gmail-voice-messaging": {
      "command": "python",
      "args": ["/path/to/voice-messaging/python-server/mcp_run.py"],
      "env": {
        "PYTHONPATH": "/path/to/voice-messaging/python-server"
      }
    }
  }
}
```