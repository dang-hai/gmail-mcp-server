"""
Web-based OAuth authentication for Gmail API.
Suitable for cloud deployments where desktop flow doesn't work.
"""

import os
import json
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from dotenv import load_dotenv

load_dotenv()

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly', 
          'https://www.googleapis.com/auth/gmail.send',
          'https://www.googleapis.com/auth/gmail.compose']

class GmailWebAuth:
    def __init__(self):
        self.client_id = os.getenv('GOOGLE_CLIENT_ID')
        self.client_secret = os.getenv('GOOGLE_CLIENT_SECRET')
        self.token_file = 'config/token.json'
        
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
    
    def exchange_code_for_token(self, code, state):
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
        
        # Save credentials
        os.makedirs('config', exist_ok=True)
        with open(self.token_file, 'w') as token:
            token.write(credentials.to_json())
            
        return credentials
    
    def get_credentials(self):
        """Get existing credentials or return None"""
        creds = None
        if os.path.exists(self.token_file):
            creds = Credentials.from_authorized_user_file(self.token_file, SCOPES)
        
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                    with open(self.token_file, 'w') as token:
                        token.write(creds.to_json())
                except Exception as e:
                    print(f"Failed to refresh token: {e}")
                    return None
            else:
                return None
        
        return creds