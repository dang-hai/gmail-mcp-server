"""
Simplified authentication for Gmail API.
Uses OAuth for both local development and cloud deployment.
"""

import os
from .auth import GmailAuth

def get_gmail_auth():
    """
    Get Gmail authentication.
    Uses OAuth flow for both local and cloud environments.
    """
    return GmailAuth()