"""
Messaging service using Twilio for SMS and WhatsApp.
Handles phone number parsing and sending authentication links via SMS (preferred) or WhatsApp.
"""

import os
import uuid
import urllib.parse
from twilio.rest import Client
from typing import Optional, Dict, Any
from dotenv import load_dotenv
from .database import Database

load_dotenv()

class MessagingService:
    def __init__(self):
        self.account_sid = os.getenv('TWILIO_ACCOUNT_SID')
        self.auth_token = os.getenv('TWILIO_AUTH_TOKEN')
        self.whatsapp_number = os.getenv('TWILIO_WHATSAPP_NUMBER')  # e.g., 'whatsapp:+14155238886'
        self.sms_number = os.getenv('TWILIO_SMS_NUMBER')  # e.g., '+14155238886'
        self.base_url = os.getenv('DEPLOYMENT_URL', 'http://localhost:5000')
        
        if not all([self.account_sid, self.auth_token]):
            raise ValueError("Missing required Twilio environment variables: TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN")
        
        if not self.sms_number and not self.whatsapp_number:
            raise ValueError("At least one messaging service required: TWILIO_SMS_NUMBER or TWILIO_WHATSAPP_NUMBER")
        
        self.client = Client(self.account_sid, self.auth_token)
        self.db = Database()  # Use Supabase database for token storage
    
    def parse_phone_from_twilio_call(self, twilio_request_data: Dict[str, Any]) -> Optional[str]:
        """
        Parse phone number from Twilio call request data.
        
        Args:
            twilio_request_data: Request data from Twilio webhook
            
        Returns:
            Formatted phone number or None if not found
        """
        print(f"=== PHONE PARSING DEBUG ===")
        print(f"Twilio request data: {twilio_request_data}")
        
        # Twilio sends the phone number in 'From' field
        phone_number = twilio_request_data.get('From')
        print(f"Raw phone number from 'From' field: '{phone_number}'")
        
        if not phone_number:
            print("No phone number found in 'From' field")
            return None
        
        # Remove 'whatsapp:' prefix if present
        if phone_number.startswith('whatsapp:'):
            phone_number = phone_number[9:]
            print(f"Removed 'whatsapp:' prefix, result: '{phone_number}'")
        
        print(f"Final parsed phone number: '{phone_number}'")
        return phone_number
    
    def generate_auth_token(self, phone_number: str) -> str:
        """Generate a unique authentication token for the phone number"""
        auth_token = str(uuid.uuid4())
        
        # Save token to database
        success = self.db.save_auth_token(auth_token, phone_number)
        if not success:
            raise Exception("Failed to save authentication token")
        
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
    
    def send_auth_link_sms(self, phone_number: str) -> bool:
        """
        Send Gmail authentication link to user via SMS.
        
        Args:
            phone_number: User's phone number (including country code)
            
        Returns:
            True if message sent successfully, False otherwise
        """
        try:
            print(f"=== SMS SEND DEBUG ===")
            print(f"Phone number: '{phone_number}'")
            print(f"Account SID: {self.account_sid}")
            print(f"SMS number: {self.sms_number}")
            print(f"Base URL: {self.base_url}")
            
            if not self.sms_number:
                print("SMS number not configured, cannot send SMS")
                return False
            
            auth_url = self.create_gmail_auth_url(phone_number)
            print(f"Generated auth URL: {auth_url}")
            
            message_body = f"""Gmail Authentication Required

Hi! To access your Gmail through our voice messaging service, please authenticate your account by clicking the link below:

{auth_url}

This link is secure and will connect your phone number to your Gmail account for voice messaging.

This link expires in 15 minutes for security.""".strip()
            
            print(f"Sending to: {phone_number}")
            print(f"From: {self.sms_number}")
            
            message = self.client.messages.create(
                body=message_body,
                from_=self.sms_number,
                to=phone_number
            )
            
            print(f"SMS auth message sent successfully. SID: {message.sid}")
            print(f"Message status: {message.status}")
            return True
            
        except Exception as e:
            print(f"Error sending SMS message: {e}")
            print(f"Error type: {type(e).__name__}")
            if hasattr(e, 'code'):
                print(f"Twilio error code: {e.code}")
            if hasattr(e, 'msg'):
                print(f"Twilio error message: {e.msg}")
            return False
    
    def send_auth_link_whatsapp(self, phone_number: str) -> bool:
        """
        Send Gmail authentication link to user via WhatsApp.
        
        Args:
            phone_number: User's phone number (including country code)
            
        Returns:
            True if message sent successfully, False otherwise
        """
        try:
            print(f"=== WHATSAPP SEND DEBUG ===")
            print(f"Phone number: '{phone_number}'")
            print(f"Account SID: {self.account_sid}")
            print(f"WhatsApp number: {self.whatsapp_number}")
            print(f"Base URL: {self.base_url}")
            
            if not self.whatsapp_number:
                print("WhatsApp number not configured, cannot send WhatsApp message")
                return False
            
            auth_url = self.create_gmail_auth_url(phone_number)
            print(f"Generated auth URL: {auth_url}")
            
            message_body = f"""
🔐 Gmail Authentication Required

Hi! To access your Gmail through our voice messaging service, please authenticate your account by clicking the link below:

{auth_url}

This link is secure and will connect your phone number to your Gmail account for voice messaging.

⚠️ This link expires in 15 minutes for security.
            """.strip()
            
            # Format phone number for WhatsApp
            whatsapp_to = f"whatsapp:{phone_number}"
            
            print(f"Sending to: {whatsapp_to}")
            print(f"From: {self.whatsapp_number}")
            
            message = self.client.messages.create(
                body=message_body,
                from_=self.whatsapp_number,
                to=whatsapp_to
            )
            
            print(f"WhatsApp auth message sent successfully. SID: {message.sid}")
            print(f"Message status: {message.status}")
            return True
            
        except Exception as e:
            print(f"Error sending WhatsApp message: {e}")
            print(f"Error type: {type(e).__name__}")
            if hasattr(e, 'code'):
                print(f"Twilio error code: {e.code}")
            if hasattr(e, 'msg'):
                print(f"Twilio error message: {e.msg}")
            return False
    
    def check_auth_token(self, auth_token: str) -> Optional[str]:
        """
        Check authentication token validity without marking as used.
        
        Args:
            auth_token: Authentication token from URL
            
        Returns:
            Phone number if token is valid and unused, None otherwise
        """
        return self.db.check_auth_token(auth_token)
    
    def verify_auth_token(self, auth_token: str) -> Optional[str]:
        """
        Verify authentication token and mark as used if valid.
        
        Args:
            auth_token: Authentication token from URL
            
        Returns:
            Phone number if token is valid and unused, None otherwise
        """
        # Verify token using database
        return self.db.verify_auth_token(auth_token)
    
    def cleanup_expired_tokens(self):
        """Clean up expired authentication tokens (call periodically)"""
        deleted_count = self.db.cleanup_expired_auth_tokens()
        if deleted_count > 0:
            print(f"Cleaned up {deleted_count} expired auth tokens")