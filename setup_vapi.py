#!/usr/bin/env python3
"""
Setup script for Vapi Gmail voice assistant.
Run this once to create your assistant and get the configuration.
"""

import os
import sys
import requests
from dotenv import load_dotenv

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

load_dotenv()

def main():
    print("🎙️  Gmail Voice Assistant Setup with Vapi")
    print("=" * 50)
    
    # Check environment variables
    required_vars = [
        'VAPI_API_KEY',
        'DEPLOYMENT_URL',
        'GOOGLE_CLIENT_ID',
        'GOOGLE_CLIENT_SECRET'
    ]
    
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        print(f"❌ Missing environment variables: {', '.join(missing_vars)}")
        print("Please check your .env file")
        return
    
    print("✅ Environment variables loaded")
    
    # Create Vapi assistant
    try:
        from src.vapi_handler import VapiGmailHandler
        
        vapi_handler = VapiGmailHandler()
        print("\n🤖 Creating Vapi assistant...")
        
        assistant_id = vapi_handler.create_assistant_api()
        
        print(f"✅ Assistant created successfully!")
        print(f"📋 Assistant ID: {assistant_id}")
        
        # Save assistant ID to .env file
        env_file = '.env'
        if os.path.exists(env_file):
            with open(env_file, 'r') as f:
                content = f.read()
            
            # Add or update VAPI_ASSISTANT_ID
            if 'VAPI_ASSISTANT_ID=' in content:
                lines = content.split('\n')
                for i, line in enumerate(lines):
                    if line.startswith('VAPI_ASSISTANT_ID='):
                        lines[i] = f'VAPI_ASSISTANT_ID={assistant_id}'
                        break
                content = '\n'.join(lines)
            else:
                content += f'\nVAPI_ASSISTANT_ID={assistant_id}\n'
            
            with open(env_file, 'w') as f:
                f.write(content)
            
            print(f"💾 Assistant ID saved to {env_file}")
        
        print("\n🎯 Next Steps:")
        print("1. Go to Vapi dashboard: https://dashboard.vapi.ai")
        print("2. Buy/configure a phone number")
        print("3. Set the assistant ID for inbound calls")
        print("4. Test by calling your Vapi number!")
        
        print(f"\n📞 When users call, they can say:")
        print("   • 'Read my emails'")
        print("   • 'Check unread messages'") 
        print("   • 'Send email to john@example.com about meeting'")
        print("   • 'Search emails from sarah'")
        
        print(f"\n🔗 Webhook URL for Vapi:")
        print(f"   {os.getenv('DEPLOYMENT_URL')}/vapi/functions")
        
    except Exception as e:
        print(f"❌ Error creating assistant: {e}")
        print("Check your VAPI_API_KEY and network connection")

if __name__ == "__main__":
    main()