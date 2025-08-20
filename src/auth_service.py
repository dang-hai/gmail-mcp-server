"""
Service Account authentication for Gmail API (for cloud deployment).
This avoids OAuth desktop flow and uses service account credentials.
"""

import os
import json
from google.auth import service_account
from google.auth.transport.requests import Request
from dotenv import load_dotenv

load_dotenv()

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly', 
          'https://www.googleapis.com/auth/gmail.send',
          'https://www.googleapis.com/auth/gmail.compose']

class GmailServiceAuth:
    def __init__(self):
        self.service_account_info = None
        self.user_email = os.getenv('GMAIL_USER_EMAIL')  # Email to impersonate
        self._load_service_account()
        
    def _load_service_account(self):
        """Load service account from environment variable or file"""
        # Try to load from environment variable first (for Railway)
        sa_json = os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON')
        if sa_json:
            try:
                self.service_account_info = json.loads(sa_json)
                return
            except json.JSONDecodeError:
                pass
        
        # Fallback to file
        sa_file = os.getenv('GOOGLE_SERVICE_ACCOUNT_FILE', 'config/service-account.json')
        if os.path.exists(sa_file):
            with open(sa_file, 'r') as f:
                self.service_account_info = json.load(f)
    
    def get_credentials(self):
        """Get service account credentials with domain-wide delegation"""
        if not self.service_account_info:
            raise Exception("No service account credentials found")
            
        if not self.user_email:
            raise Exception("GMAIL_USER_EMAIL environment variable not set")
        
        credentials = service_account.Credentials.from_service_account_info(
            self.service_account_info, scopes=SCOPES
        )
        
        # Delegate to the user email
        delegated_credentials = credentials.with_subject(self.user_email)
        
        return delegated_credentials