"""
MCP Server for Gmail operations using FastMCP.
Provides tools for reading and sending Gmail messages.
"""

import asyncio
from typing import Optional, List, Dict, Any
from fastmcp import FastMCP
from .auth_hybrid import get_gmail_auth
from .gmail_service import GmailService
from .phone_based_auth import PhoneBasedGmailAuth

# Create the FastMCP app instance
mcp = FastMCP("Gmail Voice Messaging Server")

def get_gmail_service():
    """Get Gmail service instance with hybrid authentication"""
    gmail_service = GmailService()
    # Override the auth with hybrid auth
    gmail_service.auth = get_gmail_auth()
    return gmail_service

def _initiate_phone_auth_helper(phone_number: str) -> Dict[str, Any]:
    """Helper function to initiate phone authentication"""
    try:
        phone_auth = PhoneBasedGmailAuth()
        twilio_request_data = {"From": f"whatsapp:{phone_number}"}
        success = phone_auth.initiate_phone_auth(twilio_request_data)
        
        if success:
            return {
                "status": "success",
                "message": "Authentication link sent via WhatsApp"
            }
        else:
            return {
                "status": "error", 
                "message": "Failed to send authentication link"
            }
            
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to initiate phone authentication: {str(e)}"
        }

# Note: Removed get_gmail_messages - use get_gmail_messages_by_phone instead

# Note: Removed send_gmail_message - use send_gmail_message_by_phone instead

# Note: Removed get_gmail_auth_status - use get_phone_auth_status instead

# Note: Removed search_gmail_messages - use get_gmail_messages_by_phone with query parameter instead

@mcp.tool()
def initiate_phone_authentication(
    twilio_request_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Initiate Gmail authentication process from Twilio WhatsApp call.
    Sends authentication link to user's phone via WhatsApp.
    
    Args:
        twilio_request_data: Request data from Twilio webhook containing phone number
    
    Returns:
        Dictionary with status and message
    """
    try:
        phone_auth = PhoneBasedGmailAuth()
        success = phone_auth.initiate_phone_auth(twilio_request_data)
        
        if success:
            return {
                "status": "success",
                "message": "Authentication link sent via WhatsApp"
            }
        else:
            return {
                "status": "error", 
                "message": "Failed to send authentication link"
            }
            
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to initiate phone authentication: {str(e)}"
        }

@mcp.tool()
def read_emails(
    phone_number: str,
    query: str = "",
    max_results: int = 5
) -> List[Dict[str, Any]]:
    """
    Read Gmail messages for the caller. Use this when user asks to read their emails.
    
    Args:
        phone_number: The caller's phone number (Vapi should provide this automatically)
        query: Optional Gmail search query (e.g., "is:unread", "from:someone@example.com")
        max_results: Maximum number of messages to return (1-10, default 5 for voice)
    
    Returns:
        List of email messages with sender, subject, date, and body
    """
    try:
        phone_auth = PhoneBasedGmailAuth()
        gmail_service = GmailService(phone_auth)
        
        # Authenticate using phone number
        if not gmail_service.authenticate(phone_number=phone_number):
            # Try to initiate auth if not authenticated
            auth_result = _initiate_phone_auth_helper(phone_number)
            if auth_result["status"] == "success":
                raise Exception("Gmail authentication required. I've sent you an authentication link via WhatsApp. Please click the link and try again.")
            else:
                raise Exception(f"Failed to send authentication link: {auth_result['message']}")
        
        # Validate max_results for voice (keep it small)
        max_results = max(1, min(max_results, 10))
        
        messages = gmail_service.get_messages(query=query, max_results=max_results)
        return messages
        
    except Exception as e:
        raise Exception(f"Could not read emails: {str(e)}")

@mcp.tool()
def send_email(
    phone_number: str,
    to: str,
    subject: str,
    body: str
) -> Dict[str, Any]:
    """
    Send an email via Gmail for the caller. Use this when user wants to send an email.
    
    Args:
        phone_number: The caller's phone number (Vapi should provide this automatically)
        to: Recipient email address
        subject: Email subject line
        body: Email message content
    
    Returns:
        Dictionary with success status and message details
    """
    try:
        phone_auth = PhoneBasedGmailAuth()
        gmail_service = GmailService(phone_auth)
        
        # Authenticate using phone number
        if not gmail_service.authenticate(phone_number=phone_number):
            # Try to initiate auth if not authenticated
            auth_result = _initiate_phone_auth_helper(phone_number)
            if auth_result["status"] == "success":
                raise Exception("Gmail authentication required. I've sent you an authentication link via WhatsApp. Please click the link and try again.")
            else:
                raise Exception(f"Failed to send authentication link: {auth_result['message']}")
        
        # Validate inputs
        if not to or not subject or not body:
            raise Exception("I need the recipient email, subject, and message content to send an email.")
        
        result = gmail_service.send_message(to, subject, body)
        
        if result:
            return {
                "status": "success",
                "message": f"Email sent successfully to {to}",
                "message_id": result.get("id", "unknown"),
                "to": to,
                "subject": subject
            }
        else:
            raise Exception("Failed to send the email. Please try again.")
            
    except Exception as e:
        raise Exception(f"Could not send email: {str(e)}")

@mcp.tool()
def check_authentication(
    phone_number: str
) -> Dict[str, Any]:
    """
    Check if the caller's Gmail is authenticated and ready to use.
    
    Args:
        phone_number: The caller's phone number (Vapi should provide this automatically)
    
    Returns:
        Dictionary with authentication status and guidance
    """
    try:
        phone_auth = PhoneBasedGmailAuth()
        creds = phone_auth.get_credentials(phone_number)
        
        if creds and creds.valid:
            return {
                "authenticated": True,
                "status": "ready",
                "message": "Your Gmail account is connected and ready to use!"
            }
        elif creds and creds.expired:
            return {
                "authenticated": False,
                "status": "expired", 
                "message": "Your Gmail authentication has expired. I'll send you a new authentication link."
            }
        else:
            return {
                "authenticated": False,
                "status": "not_connected",
                "message": "Your Gmail account is not connected yet. I can send you an authentication link via WhatsApp."
            }
            
    except Exception as e:
        return {
            "authenticated": False,
            "status": "error",
            "message": f"Could not check authentication status: {str(e)}"
        }