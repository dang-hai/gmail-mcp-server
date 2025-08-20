#!/usr/bin/env python3
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.app import app

if __name__ == '__main__':
    # Use Railway's PORT environment variable
    port = int(os.environ.get("PORT", 5000))
    debug = not os.environ.get("PORT")  # Only debug in local development
    
    print(f"Starting server on port {port}")
    app.run(host="0.0.0.0", port=port, debug=debug)