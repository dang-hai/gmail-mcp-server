"""
WhatsApp authentication service using Twilio.
Handles phone number parsing and sending authentication links via WhatsApp.
"""

import os
import uuid
import urllib.parse
from twilio.rest import Client
from typing import Optional, Dict, Any
from dotenv import load_dotenv

load_dotenv()

class WhatsAppAuthService:
    def __init__(self):
        self.account_sid = os.getenv('TWILIO_ACCOUNT_SID')
        self.auth_token = os.getenv('TWILIO_AUTH_TOKEN')
        self.whatsapp_number = os.getenv('TWILIO_WHATSAPP_NUMBER')  # e.g., 'whatsapp:+14155238886'
        self.base_url = os.getenv('DEPLOYMENT_URL', 'http://localhost:5000')
        
        if not all([self.account_sid, self.auth_token, self.whatsapp_number]):
            raise ValueError("Missing required Twilio environment variables: TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_WHATSAPP_NUMBER")
        
        self.client = Client(self.account_sid, self.auth_token)
        self.pending_auths = {}  # Store pending authentications in memory (use Redis in production)
    
    def parse_phone_from_twilio_call(self, twilio_request_data: Dict[str, Any]) -> Optional[str]:
        """
        Parse phone number from Twilio WhatsApp call request data.
        
        Args:
            twilio_request_data: Request data from Twilio webhook
            
        Returns:
            Formatted phone number or None if not found
        """
        # Twilio sends the phone number in 'From' field
        phone_number = twilio_request_data.get('From')
        
        if not phone_number:
            return None
        
        # Remove 'whatsapp:' prefix if present
        if phone_number.startswith('whatsapp:'):
            phone_number = phone_number[9:]
        
        return phone_number
    
    def generate_auth_token(self, phone_number: str) -> str:
        """Generate a unique authentication token for the phone number"""
        auth_token = str(uuid.uuid4())
        self.pending_auths[auth_token] = {
            'phone_number': phone_number,
            'used': False
        }
        return auth_token
    
    def create_gmail_auth_url(self, phone_number: str) -> str:
        """
        Create Gmail OAuth authentication URL with phone number context.
        
        Args:
            phone_number: User's phone number
            
        Returns:
            Authentication URL to send to user
        """
        auth_token = self.generate_auth_token(phone_number)
        
        # Create the authentication URL that includes the phone context
        auth_url = f"{self.base_url}/auth/gmail?phone_token={auth_token}"
        
        return auth_url
    
    def send_auth_link_whatsapp(self, phone_number: str) -> bool:
        """
        Send Gmail authentication link to user via WhatsApp.
        
        Args:
            phone_number: User's phone number (including country code)
            
        Returns:
            True if message sent successfully, False otherwise
        """
        try:
            auth_url = self.create_gmail_auth_url(phone_number)
            
            message_body = f"""
🔐 Gmail Authentication Required

Hi! To access your Gmail through our voice messaging service, please authenticate your account by clicking the link below:

{auth_url}

This link is secure and will connect your phone number to your Gmail account for voice messaging.

⚠️ This link expires in 15 minutes for security.
            """.strip()
            
            # Format phone number for WhatsApp
            whatsapp_to = f"whatsapp:{phone_number}"
            
            message = self.client.messages.create(
                body=message_body,
                from_=self.whatsapp_number,
                to=whatsapp_to
            )
            
            print(f"WhatsApp auth message sent successfully. SID: {message.sid}")
            return True
            
        except Exception as e:
            print(f"Error sending WhatsApp message: {e}")
            return False
    
    def verify_auth_token(self, auth_token: str) -> Optional[str]:
        """
        Verify authentication token and return associated phone number.
        
        Args:
            auth_token: Authentication token from URL
            
        Returns:
            Phone number if token is valid and unused, None otherwise
        """
        auth_data = self.pending_auths.get(auth_token)
        
        if not auth_data or auth_data['used']:
            return None
        
        # Mark token as used
        auth_data['used'] = True
        
        return auth_data['phone_number']
    
    def cleanup_expired_tokens(self):
        """Clean up expired authentication tokens (call periodically)"""
        # In production, implement with expiration timestamps
        # For now, tokens stay in memory until server restart
        pass