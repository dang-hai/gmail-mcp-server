#!/usr/bin/env python3
"""
MCP Server entry point for Gmail Voice Messaging.
Run this to start the MCP server that provides Gmail tools.
"""

import sys
import os

# Ensure we're in the correct working directory
script_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(script_dir)

# Add the src directory to Python path
sys.path.insert(0, script_dir)

from src.mcp_server import mcp

def main():

    port = int(os.environ.get("PORT", 8001))

    print("Gmail Voice Messaging MCP Server", file=sys.stderr)
    print("=" * 40, file=sys.stderr)
    print(f"Working directory: {os.getcwd()}", file=sys.stderr)
    print("Starting MCP server for Gmail operations...", file=sys.stderr)
    print("Available tools:", file=sys.stderr)
    print("- get_gmail_messages: Retrieve Gmail messages", file=sys.stderr)
    print("- send_gmail_message: Send Gmail messages", file=sys.stderr)
    print("- get_gmail_auth_status: Check authentication status", file=sys.stderr)
    print("- search_gmail_messages: Search messages with filters", file=sys.stderr)
    print("", file=sys.stderr)
    
    try:
        print("🚀 MCP Server started successfully!", file=sys.stderr)
        print("Ready to receive MCP requests...", file=sys.stderr)
        mcp.run(transport="http", host="0.0.0.0", port=port)
        
    except KeyboardInterrupt:
        print("\n👋 MCP Server stopped by user", file=sys.stderr)
    except Exception as e:
        print(f"❌ Error starting MCP server: {str(e)}", file=sys.stderr)
        print("\nTroubleshooting:", file=sys.stderr)
        print("1. Make sure your .env file has the correct credentials", file=sys.stderr)
        print("2. Run 'python desktop_auth.py' to authenticate with Gmail", file=sys.stderr)
        print("3. Install dependencies: pip install -r requirements.txt", file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()