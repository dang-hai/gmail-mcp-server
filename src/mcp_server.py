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

@mcp.get("/")
def health_check():
    """Health check endpoint for Railway deployment"""
    return {
        "status": "healthy",
        "service": "Gmail Voice Messaging MCP Server", 
        "version": "1.0.0",
        "endpoints": {
            "mcp": "/mcp",
            "health": "/",
            "tools": [
                "get_gmail_messages",
                "send_gmail_message", 
                "get_gmail_auth_status",
                "search_gmail_messages",
                "initiate_phone_authentication",
                "get_gmail_messages_by_phone",
                "send_gmail_message_by_phone", 
                "get_phone_auth_status"
            ]
        },
        "integrations": [
            "WhatsApp Authentication",
            "Vapi Voice AI",
            "Supabase Database"
        ]
    }

@mcp.get("/health")
def health():
    """Simple health check"""
    return {"status": "ok", "service": "mcp-gmail-server"}

def get_gmail_service():
    """Get Gmail service instance with hybrid authentication"""
    gmail_service = GmailService()
    # Override the auth with hybrid auth
    gmail_service.auth = get_gmail_auth()
    return gmail_service

@mcp.tool()
def get_gmail_messages(
    query: str = "",
    max_results: int = 10
) -> List[Dict[str, Any]]:
    """
    Retrieve Gmail messages with optional query filtering.
    
    Args:
        query: Gmail search query (e.g., "from:example@gmail.com", "is:unread")
        max_results: Maximum number of messages to return (1-50)
    
    Returns:
        List of message dictionaries with id, subject, sender, date, and body
    """
    try:
        gmail_service = get_gmail_service()
        
        # Ensure authentication
        if not gmail_service.authenticate():
            raise Exception("Failed to authenticate with Gmail")
        
        # Validate max_results
        max_results = max(1, min(max_results, 50))
        
        messages = gmail_service.get_messages(query=query, max_results=max_results)
        return messages
        
    except Exception as e:
        raise Exception(f"Failed to retrieve Gmail messages: {str(e)}")

@mcp.tool()
def send_gmail_message(
    to: str,
    subject: str,
    body: str
) -> Dict[str, Any]:
    """
    Send a Gmail message.
    
    Args:
        to: Recipient email address
        subject: Email subject line
        body: Email body content
    
    Returns:
        Dictionary with message ID and status
    """
    try:
        gmail_service = get_gmail_service()
        
        # Ensure authentication
        if not gmail_service.authenticate():
            raise Exception("Failed to authenticate with Gmail")
        
        # Validate inputs
        if not to or not subject or not body:
            raise Exception("All fields (to, subject, body) are required")
        
        result = gmail_service.send_message(to, subject, body)
        
        if result:
            return {
                "status": "success",
                "message_id": result.get("id", "unknown"),
                "to": to,
                "subject": subject
            }
        else:
            raise Exception("Failed to send message - no result returned")
            
    except Exception as e:
        raise Exception(f"Failed to send Gmail message: {str(e)}")

@mcp.tool()
def get_gmail_auth_status() -> Dict[str, Any]:
    """
    Check Gmail authentication status.
    
    Returns:
        Dictionary with authentication status and user info
    """
    try:
        gmail_auth = get_gmail_auth()
        creds = gmail_auth.get_credentials()
        
        if creds and creds.valid:
            return {
                "authenticated": True,
                "status": "valid",
                "expires_at": creds.expiry.isoformat() if creds.expiry else None
            }
        elif creds and creds.expired:
            return {
                "authenticated": False,
                "status": "expired",
                "message": "Credentials have expired and need refresh"
            }
        else:
            return {
                "authenticated": False,
                "status": "not_authenticated",
                "message": "No valid credentials found"
            }
            
    except Exception as e:
        return {
            "authenticated": False,
            "status": "error",
            "message": f"Error checking auth status: {str(e)}"
        }

@mcp.tool()
def search_gmail_messages(
    from_email: Optional[str] = None,
    subject_contains: Optional[str] = None,
    has_attachment: Optional[bool] = None,
    is_unread: Optional[bool] = None,
    newer_than: Optional[str] = None,
    max_results: int = 10
) -> List[Dict[str, Any]]:
    """
    Search Gmail messages with specific criteria.
    
    Args:
        from_email: Filter by sender email address
        subject_contains: Filter by text in subject line
        has_attachment: Filter messages with/without attachments
        is_unread: Filter read/unread messages
        newer_than: Filter messages newer than date (format: YYYY/MM/DD)
        max_results: Maximum number of messages to return (1-50)
    
    Returns:
        List of matching message dictionaries
    """
    try:
        gmail_service = get_gmail_service()
        
        # Build Gmail search query
        query_parts = []
        
        if from_email:
            query_parts.append(f"from:{from_email}")
        if subject_contains:
            query_parts.append(f"subject:({subject_contains})")
        if has_attachment is not None:
            query_parts.append("has:attachment" if has_attachment else "-has:attachment")
        if is_unread is not None:
            query_parts.append("is:unread" if is_unread else "-is:unread")
        if newer_than:
            query_parts.append(f"newer_than:{newer_than}")
        
        query = " ".join(query_parts)
        
        # Ensure authentication
        if not gmail_service.authenticate():
            raise Exception("Failed to authenticate with Gmail")
        
        # Validate max_results
        max_results = max(1, min(max_results, 50))
        
        messages = gmail_service.get_messages(query=query, max_results=max_results)
        return messages
        
    except Exception as e:
        raise Exception(f"Failed to search Gmail messages: {str(e)}")

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
def get_gmail_messages_by_phone(
    phone_number: str,
    query: str = "",
    max_results: int = 10
) -> List[Dict[str, Any]]:
    """
    Retrieve Gmail messages for a user identified by phone number.
    
    Args:
        phone_number: User's phone number (with country code)
        query: Gmail search query (e.g., "from:example@gmail.com", "is:unread")  
        max_results: Maximum number of messages to return (1-50)
    
    Returns:
        List of message dictionaries with id, subject, sender, date, and body
    """
    try:
        phone_auth = PhoneBasedGmailAuth()
        gmail_service = GmailService(phone_auth)
        
        # Authenticate using phone number
        if not gmail_service.authenticate(phone_number=phone_number):
            raise Exception("Failed to authenticate with Gmail for this phone number")
        
        # Validate max_results
        max_results = max(1, min(max_results, 50))
        
        messages = gmail_service.get_messages(query=query, max_results=max_results)
        return messages
        
    except Exception as e:
        raise Exception(f"Failed to retrieve Gmail messages for phone {phone_number}: {str(e)}")

@mcp.tool()
def send_gmail_message_by_phone(
    phone_number: str,
    to: str,
    subject: str,
    body: str
) -> Dict[str, Any]:
    """
    Send a Gmail message for a user identified by phone number.
    
    Args:
        phone_number: User's phone number (with country code)
        to: Recipient email address
        subject: Email subject line
        body: Email body content
    
    Returns:
        Dictionary with message ID and status
    """
    try:
        phone_auth = PhoneBasedGmailAuth()
        gmail_service = GmailService(phone_auth)
        
        # Authenticate using phone number
        if not gmail_service.authenticate(phone_number=phone_number):
            raise Exception("Failed to authenticate with Gmail for this phone number")
        
        # Validate inputs
        if not to or not subject or not body:
            raise Exception("All fields (to, subject, body) are required")
        
        result = gmail_service.send_message(to, subject, body)
        
        if result:
            return {
                "status": "success",
                "message_id": result.get("id", "unknown"),
                "to": to,
                "subject": subject,
                "phone_number": phone_number
            }
        else:
            raise Exception("Failed to send message - no result returned")
            
    except Exception as e:
        raise Exception(f"Failed to send Gmail message for phone {phone_number}: {str(e)}")

@mcp.tool()
def get_phone_auth_status(
    phone_number: str
) -> Dict[str, Any]:
    """
    Check Gmail authentication status for a phone number.
    
    Args:
        phone_number: User's phone number (with country code)
    
    Returns:
        Dictionary with authentication status and user info
    """
    try:
        phone_auth = PhoneBasedGmailAuth()
        creds = phone_auth.get_credentials(phone_number)
        
        if creds and creds.valid:
            return {
                "authenticated": True,
                "status": "valid",
                "phone_number": phone_number,
                "expires_at": creds.expiry.isoformat() if creds.expiry else None
            }
        elif creds and creds.expired:
            return {
                "authenticated": False,
                "status": "expired",
                "phone_number": phone_number,
                "message": "Credentials have expired and need refresh"
            }
        else:
            return {
                "authenticated": False,
                "status": "not_authenticated", 
                "phone_number": phone_number,
                "message": "No valid credentials found for this phone number"
            }
            
    except Exception as e:
        return {
            "authenticated": False,
            "status": "error",
            "phone_number": phone_number,
            "message": f"Error checking auth status: {str(e)}"
        }