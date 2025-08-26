#!/usr/bin/env python3
"""
Web server for OAuth and WhatsApp authentication.
Separate from MCP server for clean deployment.
"""

import os
import sys

# Add src to path
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(script_dir, 'src'))

from src.app import app

def main():
    port = int(os.environ.get("PORT", 5000))
    
    print("🌐 Gmail Web Server (OAuth & WhatsApp)", file=sys.stderr)
    print("=" * 50, file=sys.stderr)
    print(f"📡 Web Server Port: {port}", file=sys.stderr)
    print("", file=sys.stderr)
    print("Available endpoints:", file=sys.stderr)
    print("- / (home/status)", file=sys.stderr)
    print("- /auth/gmail (OAuth start)", file=sys.stderr)
    print("- /auth/gmail/callback (OAuth callback)", file=sys.stderr)
    print("- /twilio/webhook (WhatsApp auth)", file=sys.stderr)
    print("- /messages (view messages)", file=sys.stderr)
    print("- /send (send messages)", file=sys.stderr)
    print("- /logout (logout)", file=sys.stderr)
    print("", file=sys.stderr)
    
    try:
        print("🚀 Web Server started successfully!", file=sys.stderr)
        print("Ready for OAuth and WhatsApp authentication...", file=sys.stderr)
        app.run(host="0.0.0.0", port=port, debug=False)
        
    except KeyboardInterrupt:
        print("\n👋 Web Server stopped by user", file=sys.stderr)
    except Exception as e:
        print(f"❌ Web Server error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()