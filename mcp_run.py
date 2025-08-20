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
    
    # Quick auth test
    try:
        from src.auth_hybrid import get_gmail_auth
        gmail_auth = get_gmail_auth()
        creds = gmail_auth.get_credentials()
        if creds and creds.valid:
            print("✅ Authentication verified", file=sys.stderr)
            print(f"Auth type: {'Service Account' if os.getenv('PORT') else 'OAuth Desktop'}", file=sys.stderr)
        else:
            print("❌ Authentication failed", file=sys.stderr)
            if not os.getenv('PORT'):
                print("For local: run 'python desktop_auth.py' first", file=sys.stderr)
            else:
                print("For cloud: set GOOGLE_SERVICE_ACCOUNT_JSON env var", file=sys.stderr)
    except Exception as e:
        print(f"❌ Setup error: {str(e)}", file=sys.stderr)
    
    try:
        print("🚀 MCP Server started successfully!", file=sys.stderr)
        print("Ready to receive MCP requests...", file=sys.stderr)
        mcp.run()
        
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