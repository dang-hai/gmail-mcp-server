"""
Hybrid authentication for Gmail API.
Uses OAuth desktop flow for local development and service account for cloud deployment.
"""

import os
from .auth import GmailAuth
from .auth_service import GmailServiceAuth

def get_gmail_auth():
    """
    Get the appropriate Gmail authentication based on environment.
    Returns either OAuth or Service Account auth based on available credentials.
    """
    # Check if we're in a cloud environment (Railway sets PORT)
    is_cloud = os.getenv('PORT') or os.getenv('RAILWAY_ENVIRONMENT')
    
    if is_cloud:
        # Use service account for cloud deployment
        try:
            return GmailServiceAuth()
        except Exception as e:
            print(f"Service account auth failed: {e}")
            # Fallback to OAuth if service account fails
            return GmailAuth()
    else:
        # Use OAuth for local development
        return GmailAuth()