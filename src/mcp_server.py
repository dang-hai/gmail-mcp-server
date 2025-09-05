"""
Generic MCP Server using FastMCP.
Provides a generic inbox tool that uses OpenAI to handle inbox requests.
"""

import os
from typing import Dict, Any
from fastmcp import FastMCP
from .inbox_handler import InboxHandler
from .phone_based_auth import PhoneBasedGmailAuth

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


@mcp.tool()
def initiate_gmail_auth(
    phone_number: str,
    from_number: str = None,
    message_type: str = "sms"
) -> Dict[str, Any]:
    """
    Initiate phone-based Gmail authentication flow.
    Sends an authentication link to the user's phone via SMS or WhatsApp.
    
    Args:
        phone_number: The user's phone number (in international format, e.g., +1234567890)
        from_number: The number the request is coming from (optional, for validation)
        message_type: Type of message to send ("sms" or "whatsapp", defaults to "sms")
    
    Returns:
        Dictionary indicating success/failure and next steps
    """
    try:
        phone_auth = PhoneBasedGmailAuth()
        
        # Create mock Twilio request data for compatibility
        twilio_request_data = {
            "From": from_number or phone_number,
            "To": phone_number
        }
        
        success = phone_auth.initiate_phone_auth(twilio_request_data)
        
        if success:
            return {
                "success": True,
                "message": f"Authentication link sent to {phone_number}. Please check your messages and follow the link to connect your Gmail account.",
                "next_steps": "Click the authentication link sent to your phone to complete Gmail setup."
            }
        else:
            return {
                "success": False,
                "error": "Failed to send authentication link",
                "message": "Unable to send authentication link. Please try again or contact support."
            }
            
    except Exception as e:
        return {
            "success": False,
            "error": f"Authentication initiation failed: {str(e)}",
            "message": "Sorry, there was an error starting the authentication process. Please try again."
        }