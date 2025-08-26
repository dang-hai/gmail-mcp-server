"""
Voice LLM Handler for processing voice calls and executing Gmail operations.
Integrates speech recognition, LLM processing, and MCP tool calls.
"""

import os
import json
import openai
from typing import Dict, Any, List, Optional
from twilio.twiml import VoiceResponse
from .phone_based_auth import PhoneBasedGmailAuth
from .gmail_service import GmailService
from dotenv import load_dotenv

load_dotenv()

class VoiceLLMHandler:
    def __init__(self):
        self.openai_client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        self.phone_auth = PhoneBasedGmailAuth()
        
    def process_voice_call(self, twilio_request_data: Dict[str, Any]) -> str:
        """
        Process incoming voice call and return TwiML response.
        
        Args:
            twilio_request_data: Twilio webhook data
            
        Returns:
            TwiML response string
        """
        phone_number = self._extract_phone_number(twilio_request_data)
        
        if not phone_number:
            return self._create_error_response("Could not identify your phone number.")
        
        # Check if user is authenticated
        if not self._is_user_authenticated(phone_number):
            return self._create_auth_response(phone_number)
        
        # Create interactive voice response for authenticated user
        return self._create_interactive_response(phone_number)
    
    def process_speech_input(self, phone_number: str, speech_result: str) -> str:
        """
        Process speech input using LLM and execute appropriate actions.
        
        Args:
            phone_number: User's phone number
            speech_result: Transcribed speech text
            
        Returns:
            TwiML response with action results
        """
        try:
            # Parse user intent using LLM
            intent = self._parse_user_intent(speech_result)
            
            # Execute the appropriate action
            result = self._execute_gmail_action(phone_number, intent)
            
            # Convert result to speech response
            response_text = self._format_response_for_speech(result, intent['action'])
            
            return self._create_speech_response(response_text)
            
        except Exception as e:
            error_msg = f"Sorry, I encountered an error: {str(e)}"
            return self._create_speech_response(error_msg)
    
    def _extract_phone_number(self, twilio_data: Dict[str, Any]) -> Optional[str]:
        """Extract phone number from Twilio request data."""
        phone = twilio_data.get('From', '')
        return phone.replace('whatsapp:', '') if phone else None
    
    def _is_user_authenticated(self, phone_number: str) -> bool:
        """Check if user has valid Gmail authentication."""
        try:
            creds = self.phone_auth.get_credentials(phone_number)
            return creds is not None and creds.valid
        except:
            return False
    
    def _parse_user_intent(self, speech_text: str) -> Dict[str, Any]:
        """
        Use LLM to parse user speech and extract intent and parameters.
        """
        system_prompt = """
        You are a Gmail voice assistant. Parse user speech and extract their intent and parameters.
        
        Available actions:
        1. READ_EMAILS - Read recent emails (optionally filtered)
        2. SEND_EMAIL - Send a new email
        3. CHECK_UNREAD - Check unread messages
        4. SEARCH_EMAILS - Search emails with specific criteria
        5. HELP - Provide help information
        
        Respond with JSON format:
        {
            "action": "READ_EMAILS|SEND_EMAIL|CHECK_UNREAD|SEARCH_EMAILS|HELP",
            "parameters": {
                "query": "search query if applicable",
                "to": "recipient email if sending",
                "subject": "email subject if sending", 
                "body": "email body if sending",
                "max_results": number,
                "from_email": "sender filter if searching"
            },
            "confidence": 0.0-1.0
        }
        
        Examples:
        "Read my emails" -> {"action": "READ_EMAILS", "parameters": {"max_results": 5}, "confidence": 0.9}
        "Send email to john@example.com about meeting" -> {"action": "SEND_EMAIL", "parameters": {"to": "john@example.com", "subject": "meeting"}, "confidence": 0.8}
        "Check unread messages" -> {"action": "CHECK_UNREAD", "parameters": {}, "confidence": 0.9}
        """
        
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": speech_text}
                ],
                temperature=0.1
            )
            
            intent_json = response.choices[0].message.content
            intent = json.loads(intent_json)
            
            # Validate and set defaults
            if intent.get('confidence', 0) < 0.6:
                return {
                    "action": "HELP",
                    "parameters": {},
                    "confidence": 1.0,
                    "unclear_request": speech_text
                }
            
            return intent
            
        except Exception as e:
            print(f"Error parsing intent: {e}")
            return {
                "action": "HELP", 
                "parameters": {},
                "confidence": 0.0,
                "error": str(e)
            }
    
    def _execute_gmail_action(self, phone_number: str, intent: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute Gmail action based on parsed intent.
        """
        action = intent['action']
        params = intent.get('parameters', {})
        
        try:
            gmail_service = GmailService(self.phone_auth)
            
            if not gmail_service.authenticate(phone_number=phone_number):
                return {"error": "Authentication failed", "action": action}
            
            if action == "READ_EMAILS":
                max_results = params.get('max_results', 5)
                query = params.get('query', '')
                messages = gmail_service.get_messages(query=query, max_results=max_results)
                return {"action": action, "messages": messages, "count": len(messages)}
            
            elif action == "CHECK_UNREAD":
                messages = gmail_service.get_messages(query='is:unread', max_results=10)
                return {"action": action, "unread_messages": messages, "count": len(messages)}
            
            elif action == "SEND_EMAIL":
                to = params.get('to')
                subject = params.get('subject', 'Voice Message')
                body = params.get('body', 'Sent via voice assistant')
                
                if not to:
                    return {"error": "Recipient email required", "action": action}
                
                result = gmail_service.send_message(to, subject, body)
                return {"action": action, "result": result, "to": to, "subject": subject}
            
            elif action == "SEARCH_EMAILS":
                query = params.get('query', '')
                from_email = params.get('from_email')
                max_results = params.get('max_results', 5)
                
                search_query = query
                if from_email:
                    search_query += f" from:{from_email}"
                
                messages = gmail_service.get_messages(query=search_query, max_results=max_results)
                return {"action": action, "messages": messages, "count": len(messages), "query": search_query}
            
            elif action == "HELP":
                return {"action": action, "help_text": self._get_help_text()}
            
            else:
                return {"error": f"Unknown action: {action}", "action": action}
                
        except Exception as e:
            return {"error": str(e), "action": action}
    
    def _format_response_for_speech(self, result: Dict[str, Any], action: str) -> str:
        """
        Format action result into natural speech response.
        """
        if 'error' in result:
            return f"Sorry, there was an error: {result['error']}"
        
        if action == "READ_EMAILS":
            messages = result.get('messages', [])
            count = result.get('count', 0)
            
            if count == 0:
                return "You have no emails to read."
            
            response = f"You have {count} emails. Here they are: "
            for i, msg in enumerate(messages[:3], 1):  # Limit to 3 for voice
                sender = msg.get('sender', 'Unknown sender')
                subject = msg.get('subject', 'No subject')
                response += f"Email {i}: From {sender}. Subject: {subject}. "
            
            if count > 3:
                response += f"And {count - 3} more emails."
            
            return response
        
        elif action == "CHECK_UNREAD":
            count = result.get('count', 0)
            if count == 0:
                return "You have no unread messages."
            else:
                return f"You have {count} unread messages. Would you like me to read them?"
        
        elif action == "SEND_EMAIL":
            if result.get('result'):
                to = result.get('to')
                return f"Email sent successfully to {to}."
            else:
                return "Failed to send email."
        
        elif action == "SEARCH_EMAILS":
            count = result.get('count', 0)
            query = result.get('query', '')
            return f"Found {count} emails matching your search for {query}."
        
        elif action == "HELP":
            return result.get('help_text', self._get_help_text())
        
        return "Action completed successfully."
    
    def _get_help_text(self) -> str:
        """Get help text for voice response."""
        return """
        I can help you with Gmail. You can say:
        Read my emails,
        Check unread messages,
        Send email to someone at example dot com,
        Search emails from someone,
        Or ask for help.
        What would you like to do?
        """
    
    def _create_auth_response(self, phone_number: str) -> str:
        """Create TwiML response for unauthenticated users."""
        # Send auth link via WhatsApp
        success = self.phone_auth.initiate_phone_auth({'From': f'whatsapp:{phone_number}'})
        
        if success:
            message = """
            Hello! I've sent you a Gmail authentication link via WhatsApp. 
            Please check your messages and click the link to connect your Gmail account.
            Once authenticated, call back to use voice commands for your emails.
            """
        else:
            message = """
            Hello! There was an error sending your authentication link. 
            Please try calling again or contact support.
            """
        
        response = VoiceResponse()
        response.say(message)
        return str(response)
    
    def _create_interactive_response(self, phone_number: str) -> str:
        """Create TwiML response for authenticated users with voice input."""
        response = VoiceResponse()
        
        gather = response.gather(
            input='speech',
            action=f'/voice/process?phone={phone_number}',
            method='POST',
            speech_timeout='3',
            language='en-US'
        )
        
        gather.say("""
        Hello! Your Gmail is connected. 
        You can say things like: Read my emails, Check unread messages, 
        Send email to someone, or Search emails from someone.
        What would you like to do?
        """)
        
        # Fallback if no speech detected
        response.say("I didn't hear anything. Please call back and try again.")
        
        return str(response)
    
    def _create_speech_response(self, text: str) -> str:
        """Create TwiML response with speech output."""
        response = VoiceResponse()
        response.say(text)
        
        # Ask if they want to do something else
        gather = response.gather(
            input='speech',
            action='/voice/process',
            method='POST',
            speech_timeout='3',
            language='en-US'
        )
        
        gather.say("Is there anything else you'd like me to help you with?")
        response.say("Thank you for using Gmail voice assistant. Goodbye!")
        
        return str(response)
    
    def _create_error_response(self, error_message: str) -> str:
        """Create TwiML error response."""
        response = VoiceResponse()
        response.say(f"Error: {error_message}")
        return str(response)