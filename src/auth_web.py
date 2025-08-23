"""
Web-based OAuth authentication for Gmail API.
Suitable for cloud deployments where desktop flow doesn't work.
"""

import os
import json
from datetime import datetime, timezone
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from dotenv import load_dotenv
from .database import Database

load_dotenv()

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly', 
          'https://www.googleapis.com/auth/gmail.send',
          'https://www.googleapis.com/auth/gmail.compose']

class GmailWebAuth:
    def __init__(self, user_id=None):
        self.client_id = os.getenv('GOOGLE_CLIENT_ID')
        self.client_secret = os.getenv('GOOGLE_CLIENT_SECRET')
        self.user_id = user_id
        self.db = Database()
        
        # For web deployment, use the deployment URL as redirect
        self.redirect_uri = self._get_redirect_uri()
        
    def _get_redirect_uri(self):
        """Get the appropriate redirect URI based on environment"""
        # Check if we're on Railway or other cloud platform
        if os.getenv('RAILWAY_PUBLIC_DOMAIN'):
            return f"https://{os.getenv('RAILWAY_PUBLIC_DOMAIN')}/auth/callback"
        elif os.getenv('PORT'):  # Generic cloud deployment
            # You'll need to set DEPLOYMENT_URL manually for other platforms
            base_url = os.getenv('DEPLOYMENT_URL', 'http://localhost:8000')
            return f"{base_url}/auth/callback"
        else:
            # Local development
            return "http://localhost:5000/auth/callback"
    
    def get_authorization_url(self):
        """Get authorization URL for web OAuth flow"""
        client_config = {
            "web": {
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [self.redirect_uri]
            }
        }
        
        flow = Flow.from_client_config(client_config, scopes=SCOPES)
        flow.redirect_uri = self.redirect_uri
        
        authorization_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true'
        )
        
        return authorization_url, state
    
    def exchange_code_for_token(self, code, state, user_id):
        """Exchange authorization code for access token"""
        client_config = {
            "web": {
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [self.redirect_uri]
            }
        }
        
        flow = Flow.from_client_config(client_config, scopes=SCOPES, state=state)
        flow.redirect_uri = self.redirect_uri
        
        flow.fetch_token(code=code)
        credentials = flow.credentials
        
        # Save credentials to database
        self.user_id = user_id
        if self.db.save_oauth_tokens(user_id, credentials):
            return credentials
        else:
            return None
    
    def get_credentials(self):
        """Get existing credentials or return None"""
        if not self.user_id:
            return None
            
        token_data = self.db.get_oauth_tokens(self.user_id)
        if not token_data:
            return None
        
        # Reconstruct credentials from database
        creds = Credentials(
            token=token_data['access_token'],
            refresh_token=token_data['refresh_token'],
            token_uri="https://oauth2.googleapis.com/token",
            client_id=self.client_id,
            client_secret=self.client_secret,
            scopes=token_data['scope'].split(' ') if token_data['scope'] else SCOPES,
            expiry=token_data['token_expiry']
        )
        
        # Check if token needs refresh
        if not creds.valid:
            if creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                    # Update tokens in database
                    self.db.update_oauth_tokens(self.user_id, creds.token, creds.expiry)
                except Exception as e:
                    print(f"Failed to refresh token: {e}")
                    return None
            else:
                return None
        
        return creds
    
    def set_user_id(self, user_id):
        """Set the user ID for this auth instance"""
        self.user_id = user_id
        
    def logout(self):
        """Remove stored credentials for the user"""
        if self.user_id:
            return self.db.delete_oauth_tokens(self.user_id)
        return False