#!/bin/bash
# Railway startup script

echo "Starting Gmail MCP Server..."
echo "Environment: Railway"
echo "PORT: ${PORT:-8000}"

# Set up environment
export PYTHONPATH="${PYTHONPATH}:."

# Start the MCP server
python mcp_run.py