"""
Generic MCP Server using FastMCP.
Provides a generic inbox tool that uses OpenAI to handle inbox requests.
"""

import os
from typing import Dict, Any, List
from fastmcp import FastMCP
from .phone_based_auth import PhoneBasedGmailAuth
from .gmail_service import GmailService
from .auth import GmailAuth

# Create the FastMCP app instance
mcp = FastMCP("Generic Inbox Server")

def get_gmail_service():
    """Get Gmail service instance with hybrid authentication"""
    gmail_service = GmailService()
    # Override the auth with hybrid auth
    gmail_service.auth = GmailAuth()
    return gmail_service

def _initiate_phone_auth_helper(phone_number: str) -> Dict[str, Any]:
    """Helper function to initiate phone authentication"""
    try:
        print(f"=== PHONE AUTH DEBUG ===")
        print(f"Attempting to send auth link to: '{phone_number}'")
        
        phone_auth = PhoneBasedGmailAuth()
        twilio_request_data = {"From": f"whatsapp:{phone_number}"}
        success = phone_auth.initiate_phone_auth(twilio_request_data)
        
        if success:
            return {
                "status": "success",
                "message": "Authentication link sent!"
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
def initiate_phone_authentication(
    phone_number: str
) -> Dict[str, Any]:
    """
    Initiate Gmail authentication process for phone number.
    Sends authentication link to user's phone.
    
    Args:
        phone_number: User's phone number (including country code, e.g., +1234567890)
    
    Returns:
        Dictionary with status and message
    """
    try:
        print(f"=== INITIATE AUTH DEBUG ===")
        print(f"Phone number received: '{phone_number}'")
        
        phone_auth = PhoneBasedGmailAuth()
        # Convert phone number to Twilio request format
        twilio_request_data = {"From": f"whatsapp:{phone_number}"}
        success = phone_auth.initiate_phone_auth(twilio_request_data)
        
        if success:
            return {
                "status": "success",
                "message": "Authentication link sent!"
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
        print(f"=== READ EMAILS DEBUG ===")
        print(f"Phone number received from Vapi: '{phone_number}'")
        print(f"Phone number type: {type(phone_number)}")
        print(f"Phone number length: {len(phone_number)}")
        print(f"Query: '{query}'")
        print(f"Max results: {max_results}")
        phone_auth = PhoneBasedGmailAuth()
        gmail_service = GmailService(phone_auth)
        
        # Authenticate using phone number
        if not gmail_service.authenticate(phone_number=phone_number):
            # Try to initiate auth if not authenticated
            auth_result = _initiate_phone_auth_helper(phone_number)
            if auth_result["status"] == "success":
                raise Exception("Gmail authentication required. I've sent you an authentication link. Please click the link and try again.")
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
                raise Exception("Gmail authentication required. I've sent you an authentication link. Please click the link and try again.")
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
                "message": "Your Gmail account is not connected yet. I can send you an authentication link."
            }
            
    except Exception as e:
        return {
            "authenticated": False,
            "status": "error",
            "message": f"Could not check authentication status: {str(e)}"
        }

@mcp.tool()
def mark_email_read_status(
    phone_number: str,
    message_id: str,
    mark_as_read: bool = True
) -> Dict[str, Any]:
    """
    Mark an email as read or unread. Use this when user wants to mark emails as read/unread.
    
    Args:
        phone_number: The caller's phone number (Vapi should provide this automatically)
        message_id: The ID of the email message to mark
        mark_as_read: True to mark as read, False to mark as unread (default: True)
    
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
                raise Exception("Gmail authentication required. I've sent you an authentication link. Please click the link and try again.")
            else:
                raise Exception(f"Failed to send authentication link: {auth_result['message']}")
        
        # Validate inputs
        if not message_id:
            raise Exception("I need the email message ID to mark it as read or unread.")
        
        result = gmail_service.mark_message_read_status(message_id, mark_as_read)
        
        if result:
            status_text = "read" if mark_as_read else "unread"
            return {
                "status": "success",
                "message": f"Email marked as {status_text} successfully",
                "message_id": message_id,
                "marked_as_read": mark_as_read
            }
        else:
            raise Exception("Failed to update the email status. Please try again.")
            
    except Exception as e:
        raise Exception(f"Could not mark email as read/unread: {str(e)}")