#!/usr/bin/env python3
"""
Standalone desktop authentication script for Gmail API.
Run this script to authenticate your Gmail account.
"""

import sys
import os

# Add the src directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.auth import GmailAuth

def main():
    print("Gmail Desktop Authentication")
    print("=" * 40)
    print()
    print("This will open your browser to authenticate with Gmail.")
    print("Make sure you have:")
    print("1. Created a Google Cloud project")
    print("2. Enabled the Gmail API") 
    print("3. Created OAuth 2.0 credentials (Desktop application)")
    print("4. Set up your .env file with GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET")
    print()
    
    input("Press Enter to continue...")
    
    try:
        auth = GmailAuth()
        
        if not auth.client_id or not auth.client_secret:
            print("❌ Error: Missing Google OAuth credentials!")
            print("Please copy .env.example to .env and fill in your credentials.")
            return
        
        print("🔐 Starting authentication flow...")
        print("Your browser will open automatically.")
        
        credentials = auth.authenticate_desktop()
        
        if credentials:
            print("✅ Authentication successful!")
            print("Your credentials have been saved to config/token.json")
            print("You can now use the Gmail server application.")
        else:
            print("❌ Authentication failed!")
            
    except Exception as e:
        print(f"❌ Error during authentication: {str(e)}")
        print("\nTroubleshooting:")
        print("1. Make sure your .env file has the correct credentials")
        print("2. Ensure your OAuth app is configured for 'Desktop application'")
        print("3. Check that the Gmail API is enabled in Google Cloud Console")

if __name__ == '__main__':
    main()