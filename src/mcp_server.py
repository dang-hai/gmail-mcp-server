"""
Generic MCP Server using FastMCP.
Provides a generic inbox tool that uses OpenAI to handle inbox requests.
"""

import os
from typing import Dict, Any
from fastmcp import FastMCP
from .inbox_handler import InboxHandler

# Create the FastMCP app instance
mcp = FastMCP("Generic Inbox Server")

def get_inbox_handler():
    """Get inbox handler instance with OpenAI integration"""
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        raise Exception("OPENAI_API_KEY environment variable is required")
    return InboxHandler(openai_api_key)


@mcp.tool()
def handle_inbox_request(
    phone_number: str,
    request: str
) -> Dict[str, Any]:
    """
    Generic inbox tool that handles inbox requests using natural language.
    Uses OpenAI with tool calling to interpret requests and perform Gmail operations.
    
    Args:
        phone_number: The caller's phone number (Vapi should provide this automatically)
        request: Natural language description of what the user wants to do with their inbox
                (e.g., "read my unread emails", "send an email to john@example.com")
    
    Returns:
        Dictionary with the response and any tool execution results
    """
    try:
        inbox_handler = get_inbox_handler()
        result = inbox_handler.handle_inbox_request(phone_number, request)
        return result
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Could not process inbox request: {str(e)}",
            "response": "I'm sorry, I encountered an error while processing your inbox request."
        }