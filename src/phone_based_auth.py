"""
Phone-based Gmail authentication system.
Integrates OAuth with phone number identification via WhatsApp.
"""

import os
import json
from typing import Optional, Dict, Any
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from dotenv import load_dotenv
from .database import Database
from .whatsapp_auth import WhatsAppAuthService

load_dotenv()

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly', 
          'https://www.googleapis.com/auth/gmail.send',
          'https://www.googleapis.com/auth/gmail.compose']

class PhoneBasedGmailAuth:
    def __init__(self):
        self.client_id = os.getenv('GOOGLE_CLIENT_ID')
        self.client_secret = os.getenv('GOOGLE_CLIENT_SECRET')
        self.redirect_uri = f"{os.getenv('DEPLOYMENT_URL', 'http://localhost:5000')}/auth/gmail/callback"
        self.db = Database()
        self.whatsapp_service = WhatsAppAuthService()
        self.current_user_id = None

        print("DEPLOYMENT_URL", os.getenv('DEPLOYMENT_URL'))
        
        if not all([self.client_id, self.client_secret]):
            raise ValueError("Missing Google OAuth credentials: GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET")
    
    def set_user_id(self, user_id: int):
        """Set the current user ID for this auth instance"""
        self.current_user_id = user_id
    
    def initiate_phone_auth(self, twilio_request_data: Dict[str, Any]) -> bool:
        """
        Initiate authentication process from Twilio WhatsApp call.
        
        Args:
            twilio_request_data: Data from Twilio webhook request
            
        Returns:
            True if auth link sent successfully, False otherwise
        """
        # Parse phone number from Twilio request
        phone_number = self.whatsapp_service.parse_phone_from_twilio_call(twilio_request_data)
        
        if not phone_number:
            print("Could not parse phone number from Twilio request")
            return False
        
        # Get or create user by phone number
        try:
            user = self.db.get_or_create_user_by_phone(phone_number)
            print(f"User found/created: {user['id']} for phone {phone_number}")
            
            # Check if user already has valid OAuth tokens
            existing_tokens = self.db.get_oauth_tokens(user['id'])
            if existing_tokens:
                creds = self._tokens_to_credentials(existing_tokens)
                if creds and creds.valid:
                    # User already authenticated, send success message
                    self._send_already_authenticated_message(phone_number)
                    return True
            
            # Send authentication link via WhatsApp
            success = self.whatsapp_service.send_auth_link_whatsapp(phone_number)
            
            if success:
                print(f"Authentication link sent to {phone_number}")
            else:
                print(f"Failed to send authentication link to {phone_number}")
            
            return success
            
        except Exception as e:
            print(f"Error in initiate_phone_auth: {e}")
            return False
    
    def create_oauth_flow(self, phone_token: str) -> Optional[Flow]:
        """
        Create OAuth flow for phone-based authentication.
        
        Args:
            phone_token: Token linking this auth to a phone number
            
        Returns:
            OAuth Flow object or None if token invalid
        """
        # Check phone token without marking as used
        phone_number = self.whatsapp_service.check_auth_token(phone_token)
        if not phone_number:
            return None
        
        # Store phone number for callback
        self.pending_phone_number = phone_number
        
        client_config = {
            "web": {
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [self.redirect_uri]
            }
        }
        
        flow = Flow.from_client_config(
            client_config,
            scopes=SCOPES
        )
        flow.redirect_uri = self.redirect_uri
        
        return flow
    
    def complete_oauth_flow(self, authorization_code: str, phone_token: str) -> bool:
        """
        Complete OAuth flow and save credentials for phone number.
        
        Args:
            authorization_code: OAuth authorization code from Google
            phone_token: Token linking this auth to a phone number
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Verify phone token and get phone number (this marks token as used)
            phone_number = self.whatsapp_service.verify_auth_token(phone_token)
            if not phone_number:
                print("Invalid or expired phone token")
                return False
            
            # Create OAuth flow directly without checking token again
            client_config = {
                "web": {
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [self.redirect_uri]
                }
            }
            
            flow = Flow.from_client_config(
                client_config,
                scopes=SCOPES
            )
            flow.redirect_uri = self.redirect_uri
            
            # Exchange authorization code for credentials
            flow.fetch_token(code=authorization_code)
            credentials = flow.credentials
            
            # Get or create user
            user = self.db.get_or_create_user_by_phone(phone_number)
            
            # Save credentials to database
            success = self.db.save_oauth_tokens(user['id'], credentials)
            
            if success:
                # Send success message via WhatsApp
                self._send_auth_success_message(phone_number)
                print(f"OAuth completed successfully for phone {phone_number}")
            
            return success
            
        except Exception as e:
            print(f"Error completing OAuth flow: {e}")
            return False
    
    def get_credentials(self, phone_number: Optional[str] = None) -> Optional[Credentials]:
        """
        Get valid credentials for a phone number.
        
        Args:
            phone_number: Phone number to get credentials for
            
        Returns:
            Valid Credentials object or None
        """
        try:
            if phone_number:
                # Get user by phone number
                user = self.db.get_or_create_user_by_phone(phone_number)
                user_id = user['id']
            elif self.current_user_id:
                user_id = self.current_user_id
            else:
                return None
            
            # Get tokens from database
            token_data = self.db.get_oauth_tokens(user_id)
            if not token_data:
                return None
            
            # Convert to credentials
            creds = self._tokens_to_credentials(token_data)
            
            # Check if credentials need refresh
            if creds and not creds.valid:
                if creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                    # Update database with refreshed token
                    self.db.update_oauth_tokens(user_id, creds.token, creds.expiry)
                else:
                    return None
            
            return creds
            
        except Exception as e:
            print(f"Error getting credentials: {e}")
            return None
    
    def _tokens_to_credentials(self, token_data: Dict[str, Any]) -> Optional[Credentials]:
        """Convert database token data to Credentials object"""
        try:
            return Credentials(
                token=token_data['access_token'],
                refresh_token=token_data['refresh_token'],
                token_uri="https://oauth2.googleapis.com/token",
                client_id=self.client_id,
                client_secret=self.client_secret,
                scopes=token_data['scope'].split(' ') if token_data['scope'] else SCOPES
            )
        except Exception as e:
            print(f"Error converting tokens to credentials: {e}")
            return None
    
    def _send_already_authenticated_message(self, phone_number: str):
        """Send message indicating user is already authenticated"""
        try:
            message_body = """
✅ Already Authenticated

Your Gmail account is already connected! You can now use voice messaging to interact with your Gmail.

Try saying: "Read my emails" or "Send an email"
            """.strip()
            
            whatsapp_to = f"whatsapp:{phone_number}"
            
            self.whatsapp_service.client.messages.create(
                body=message_body,
                from_=self.whatsapp_service.whatsapp_number,
                to=whatsapp_to
            )
        except Exception as e:
            print(f"Error sending already authenticated message: {e}")
    
    def _send_auth_success_message(self, phone_number: str):
        """Send success message after authentication"""
        try:
            message_body = """
🎉 Authentication Successful!

Your Gmail account has been successfully connected to our voice messaging service!

You can now:
• Call to read your emails
• Send emails via voice
• Search your messages

Your phone number is securely linked to your Gmail account.
            """.strip()
            
            whatsapp_to = f"whatsapp:{phone_number}"
            
            self.whatsapp_service.client.messages.create(
                body=message_body,
                from_=self.whatsapp_service.whatsapp_number,
                to=whatsapp_to
            )
        except Exception as e:
            print(f"Error sending success message: {e}")