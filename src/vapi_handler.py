"""
Vapi AI Voice Assistant Handler for Gmail operations.
Integrates with Vapi for voice processing and connects to Gmail MCP tools.
"""

import os
import json
import requests
from typing import Dict, Any, List, Optional
from flask import request, jsonify
from .phone_based_auth import PhoneBasedGmailAuth
from .gmail_service import GmailService
from dotenv import load_dotenv

load_dotenv()

class VapiGmailHandler:
    def __init__(self):
        self.vapi_api_key = os.getenv('VAPI_API_KEY')
        self.vapi_phone_number_id = os.getenv('VAPI_PHONE_NUMBER_ID')
        self.phone_auth = PhoneBasedGmailAuth()
        self.base_url = os.getenv('DEPLOYMENT_URL', 'http://localhost:5000')
        
        if not self.vapi_api_key:
            raise ValueError("VAPI_API_KEY environment variable is required")
    
    def create_gmail_assistant(self) -> Dict[str, Any]:
        """
        Create a Vapi assistant configured for Gmail operations.
        """
        assistant_config = {
            "name": "Gmail Voice Assistant",
            "model": {
                "provider": "openai",
                "model": "gpt-4",
                "temperature": 0.1,
                "systemMessage": """You are a helpful Gmail voice assistant. You can:

1. Read emails - say "read emails" or "check messages"
2. Check unread emails - say "check unread" or "any new messages"
3. Send emails - say "send email to [email] about [subject]"
4. Search emails - say "search emails from [sender]" or "find emails about [topic]"

When users want to send emails, always ask for:
- Recipient email address
- Subject (if not provided)
- Message content

Be conversational and helpful. Always confirm actions before executing them.
If authentication is needed, guide users through the process.

You have access to these functions:
- get_gmail_messages_by_phone: Read emails for authenticated users
- send_gmail_message_by_phone: Send emails for authenticated users  
- get_phone_auth_status: Check if user is authenticated
- initiate_phone_authentication: Start authentication process

Always get the user's phone number from the call context before making function calls."""
            },
            "voice": {
                "provider": "11labs",
                "voiceId": "21m00Tcm4TlvDq8ikWAM",  # Rachel voice
                "speed": 1.0,
                "stability": 0.5,
                "similarityBoost": 0.75
            },
            "functions": [
                {
                    "name": "get_gmail_messages_by_phone",
                    "description": "Get Gmail messages for a user by phone number",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "phone_number": {
                                "type": "string",
                                "description": "User's phone number with country code"
                            },
                            "query": {
                                "type": "string", 
                                "description": "Gmail search query (optional)"
                            },
                            "max_results": {
                                "type": "integer",
                                "description": "Maximum number of messages (1-10)",
                                "default": 5
                            }
                        },
                        "required": ["phone_number"]
                    }
                },
                {
                    "name": "send_gmail_message_by_phone",
                    "description": "Send Gmail message for a user by phone number",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "phone_number": {
                                "type": "string",
                                "description": "User's phone number with country code"
                            },
                            "to": {
                                "type": "string",
                                "description": "Recipient email address"
                            },
                            "subject": {
                                "type": "string",
                                "description": "Email subject"
                            },
                            "body": {
                                "type": "string", 
                                "description": "Email body content"
                            }
                        },
                        "required": ["phone_number", "to", "subject", "body"]
                    }
                },
                {
                    "name": "get_phone_auth_status",
                    "description": "Check Gmail authentication status for a phone number",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "phone_number": {
                                "type": "string",
                                "description": "User's phone number with country code"
                            }
                        },
                        "required": ["phone_number"]
                    }
                },
                {
                    "name": "initiate_phone_authentication",
                    "description": "Start Gmail authentication process for a phone number",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "phone_number": {
                                "type": "string", 
                                "description": "User's phone number with country code"
                            }
                        },
                        "required": ["phone_number"]
                    }
                }
            ],
            "endCallFunctionEnabled": True,
            "recordingEnabled": False,
            "firstMessage": "Hi! I'm your Gmail voice assistant. I can help you read emails, send messages, and manage your Gmail account. What would you like to do?",
            "serverUrl": f"{self.base_url}/vapi/functions"
        }
        
        return assistant_config
    
    def create_assistant_api(self) -> str:
        """
        Create assistant via Vapi API and return assistant ID.
        """
        headers = {
            "Authorization": f"Bearer {self.vapi_api_key}",
            "Content-Type": "application/json"
        }
        
        assistant_config = self.create_gmail_assistant()
        
        response = requests.post(
            "https://api.vapi.ai/assistant",
            headers=headers,
            json=assistant_config
        )
        
        if response.status_code == 201:
            assistant = response.json()
            return assistant["id"]
        else:
            raise Exception(f"Failed to create assistant: {response.text}")
    
    def make_call(self, phone_number: str, assistant_id: str) -> Dict[str, Any]:
        """
        Initiate a call using Vapi.
        """
        headers = {
            "Authorization": f"Bearer {self.vapi_api_key}",
            "Content-Type": "application/json"
        }
        
        call_config = {
            "phoneNumberId": self.vapi_phone_number_id,
            "customer": {
                "number": phone_number
            },
            "assistantId": assistant_id
        }
        
        response = requests.post(
            "https://api.vapi.ai/call",
            headers=headers,
            json=call_config
        )
        
        if response.status_code == 201:
            return response.json()
        else:
            raise Exception(f"Failed to make call: {response.text}")
    
    def handle_function_call(self, function_call: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle function calls from Vapi assistant.
        """
        function_name = function_call.get("name")
        parameters = function_call.get("parameters", {})
        
        try:
            if function_name == "get_gmail_messages_by_phone":
                return self._get_gmail_messages(parameters)
            
            elif function_name == "send_gmail_message_by_phone":
                return self._send_gmail_message(parameters)
            
            elif function_name == "get_phone_auth_status":
                return self._get_auth_status(parameters)
            
            elif function_name == "initiate_phone_authentication":
                return self._initiate_auth(parameters)
            
            else:
                return {
                    "error": f"Unknown function: {function_name}"
                }
                
        except Exception as e:
            return {
                "error": f"Function execution failed: {str(e)}"
            }
    
    def _get_gmail_messages(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get Gmail messages for phone number."""
        phone_number = params.get("phone_number")
        query = params.get("query", "")
        max_results = min(params.get("max_results", 5), 10)  # Limit for voice
        
        try:
            gmail_service = GmailService(self.phone_auth)
            
            if not gmail_service.authenticate(phone_number=phone_number):
                return {
                    "error": "Gmail authentication required",
                    "message": "You need to authenticate your Gmail account first. I'll send you an authentication link."
                }
            
            messages = gmail_service.get_messages(query=query, max_results=max_results)
            
            # Format for voice response
            if not messages:
                return {
                    "success": True,
                    "message": "You have no messages" + (f" matching '{query}'" if query else ""),
                    "count": 0
                }
            
            # Summarize messages for voice
            summaries = []
            for i, msg in enumerate(messages[:5], 1):
                sender = msg.get('sender', 'Unknown sender').split('<')[0].strip()
                subject = msg.get('subject', 'No subject')
                summaries.append(f"Message {i}: From {sender}. Subject: {subject}")
            
            message = f"You have {len(messages)} messages. " + ". ".join(summaries)
            if len(messages) > 5:
                message += f" And {len(messages) - 5} more messages."
            
            return {
                "success": True,
                "message": message,
                "count": len(messages)
            }
            
        except Exception as e:
            return {"error": str(e)}
    
    def _send_gmail_message(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Send Gmail message for phone number."""
        phone_number = params.get("phone_number")
        to = params.get("to")
        subject = params.get("subject")
        body = params.get("body")
        
        if not all([phone_number, to, subject, body]):
            return {
                "error": "Missing required parameters",
                "message": "I need the recipient email, subject, and message content to send an email."
            }
        
        try:
            gmail_service = GmailService(self.phone_auth)
            
            if not gmail_service.authenticate(phone_number=phone_number):
                return {
                    "error": "Gmail authentication required", 
                    "message": "You need to authenticate your Gmail account first."
                }
            
            result = gmail_service.send_message(to, subject, body)
            
            if result:
                return {
                    "success": True,
                    "message": f"Email sent successfully to {to} with subject '{subject}'"
                }
            else:
                return {
                    "error": "Send failed",
                    "message": "Sorry, I couldn't send your email. Please try again."
                }
                
        except Exception as e:
            return {"error": str(e)}
    
    def _get_auth_status(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Check authentication status for phone number."""
        phone_number = params.get("phone_number")
        
        try:
            creds = self.phone_auth.get_credentials(phone_number)
            
            if creds and creds.valid:
                return {
                    "success": True,
                    "authenticated": True,
                    "message": "Your Gmail account is connected and ready to use."
                }
            else:
                return {
                    "success": True,
                    "authenticated": False,
                    "message": "Your Gmail account is not connected. I can send you an authentication link."
                }
                
        except Exception as e:
            return {"error": str(e)}
    
    def _initiate_auth(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Initiate authentication for phone number."""
        phone_number = params.get("phone_number")
        
        try:
            # Create fake Twilio request data
            twilio_data = {"From": f"whatsapp:{phone_number}"}
            
            success = self.phone_auth.initiate_phone_auth(twilio_data)
            
            if success:
                return {
                    "success": True,
                    "message": "I've sent you a Gmail authentication link via WhatsApp. Please check your messages and click the link to connect your account, then call back."
                }
            else:
                return {
                    "error": "Auth failed",
                    "message": "Sorry, I couldn't send the authentication link. Please try again later."
                }
                
        except Exception as e:
            return {"error": str(e)}
    
    def process_webhook(self, webhook_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process webhook from Vapi for function calls.
        """
        message_type = webhook_data.get("message", {}).get("type")
        
        if message_type == "function-call":
            function_call = webhook_data.get("message", {}).get("functionCall", {})
            result = self.handle_function_call(function_call)
            
            return {
                "result": result.get("message", str(result))
            }
        
        # Handle other webhook types if needed
        return {"result": "Webhook processed"}