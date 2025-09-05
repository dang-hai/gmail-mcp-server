"""
Generic inbox handler using LiteLLM with tool calling.
Handles inbox requests by interpreting natural language and calling Gmail service directly.
Supports multiple AI providers including Anthropic Claude and OpenAI GPT models.
"""

import json
import os
from typing import Dict, Any, List
import litellm
from .gmail_service import GmailService
from .phone_based_auth import PhoneBasedGmailAuth

class InboxHandler:
    def __init__(self, openai_api_key: str = None, model: str = "anthropic/claude-3-5-sonnet-latest"):
        # Set up API keys
        if openai_api_key:
            os.environ["OPENAI_API_KEY"] = openai_api_key
        
        # Configure LiteLLM
        self.model = model
        
        # Set Anthropic API key if available
        anthropic_key = os.getenv("ANTHROPIC_API_KEY")
        if anthropic_key:
            os.environ["ANTHROPIC_API_KEY"] = anthropic_key
        
    def _get_tool_definitions(self) -> List[Dict[str, Any]]:
        """Define available Gmail operations for LiteLLM"""
        return [
            {
                "type": "function",
                "function": {
                    "name": "read_emails",
                    "description": "Read Gmail messages with optional search query",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string", 
                                "description": "Gmail search query (e.g., 'is:unread', 'from:someone@example.com')"
                            },
                            "max_results": {
                                "type": "integer",
                                "description": "Maximum number of messages to return (1-10, default 5)"
                            }
                        },
                        "required": []
                    }
                }
            },
            {
                "type": "function", 
                "function": {
                    "name": "send_email",
                    "description": "Send an email via Gmail",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "to": {
                                "type": "string",
                                "description": "Recipient email address"
                            },
                            "subject": {
                                "type": "string", 
                                "description": "Email subject line"
                            },
                            "body": {
                                "type": "string",
                                "description": "Email message content"
                            }
                        },
                        "required": ["to", "subject", "body"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "check_auth",
                    "description": "Check Gmail authentication status",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "list_contacts",
                    "description": "List contacts from Gmail history based on a search query",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Search query to filter contacts by name or email (case-insensitive)"
                            },
                            "max_results": {
                                "type": "integer", 
                                "description": "Maximum number of contacts to return (1-50, default 20)"
                            }
                        },
                        "required": []
                    }
                }
            }
        ]
    
    def _execute_tool(self, tool_name: str, tool_args: Dict[str, Any], phone_number: str) -> Dict[str, Any]:
        """Execute a tool using Gmail service directly"""
        try:
            phone_auth = PhoneBasedGmailAuth()
            gmail_service = GmailService(phone_auth)
            
            if tool_name == "read_emails":
                # Authenticate
                if not gmail_service.authenticate(phone_number=phone_number):
                    return {
                        "success": False,
                        "error": "Gmail authentication required. Please authenticate first."
                    }
                
                query = tool_args.get("query", "")
                max_results = tool_args.get("max_results", 5)
                max_results = max(1, min(max_results, 10))  # Validate range
                
                messages = gmail_service.get_messages(query=query, max_results=max_results)
                return {
                    "success": True,
                    "result": messages
                }
                
            elif tool_name == "send_email":
                # Authenticate
                if not gmail_service.authenticate(phone_number=phone_number):
                    return {
                        "success": False,
                        "error": "Gmail authentication required. Please authenticate first."
                    }
                
                to = tool_args.get("to")
                subject = tool_args.get("subject") 
                body = tool_args.get("body")
                
                if not all([to, subject, body]):
                    return {
                        "success": False,
                        "error": "Missing required fields: to, subject, and body are all required"
                    }
                
                result = gmail_service.send_message(to, subject, body)
                if result:
                    return {
                        "success": True,
                        "result": {
                            "message": f"Email sent successfully to {to}",
                            "message_id": result.get("id", "unknown"),
                            "to": to,
                            "subject": subject
                        }
                    }
                else:
                    return {
                        "success": False,
                        "error": "Failed to send email"
                    }
                    
            elif tool_name == "check_auth":
                creds = phone_auth.get_credentials(phone_number)
                
                if creds and creds.valid:
                    return {
                        "success": True,
                        "result": {
                            "authenticated": True,
                            "status": "ready",
                            "message": "Gmail account is connected and ready!"
                        }
                    }
                elif creds and creds.expired:
                    return {
                        "success": True,
                        "result": {
                            "authenticated": False,
                            "status": "expired",
                            "message": "Gmail authentication has expired"
                        }
                    }
                else:
                    return {
                        "success": True,
                        "result": {
                            "authenticated": False,
                            "status": "not_connected", 
                            "message": "Gmail account is not connected"
                        }
                    }
                    
            elif tool_name == "list_contacts":
                # Authenticate
                if not gmail_service.authenticate(phone_number=phone_number):
                    return {
                        "success": False,
                        "error": "Gmail authentication required. Please authenticate first."
                    }
                
                query = tool_args.get("query", "")
                max_results = tool_args.get("max_results", 20)
                max_results = max(1, min(max_results, 50))  # Validate range
                
                contacts = gmail_service.list_contacts(query=query, max_results=max_results)
                return {
                    "success": True,
                    "result": {
                        "contacts": contacts,
                        "query": query,
                        "total_found": len(contacts)
                    }
                }
            else:
                return {
                    "success": False,
                    "error": f"Unknown tool: {tool_name}"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"Error executing {tool_name}: {str(e)}"
            }
    
    def handle_inbox_request(self, phone_number: str, request_description: str) -> Dict[str, Any]:
        """
        Handle inbox request using LiteLLM tool calling with direct Gmail service integration.
        
        Args:
            phone_number: The caller's phone number
            request_description: Natural language description of what the user wants to do
            
        Returns:
            Dictionary with the result of the operation
        """
        try:
            # System prompt for inbox operations
            system_prompt = f"""
            You are an intelligent inbox assistant that helps users manage their inbox using only the provided tools.
            The user's phone number is: {phone_number}
            The user's request is: {request_description}
            
            Analyze what the user wants to do with their inbox and use only the following tools to fulfill the user's request:
            - read_emails: Read Gmail messages with optional search queries
            - send_email: Send emails (requires to, subject, body)
            - check_auth: Check Gmail authentication status
            - list_contacts: Find contacts from email history based on name or email queries
            
            For reading emails:
            - Use Gmail search queries when helpful (e.g., "is:unread", "from:example@gmail.com")
            - Keep max_results reasonable for voice (default 5)
            
            For sending emails:
            - Extract recipient, subject, and body from user's request
            - Ensure all required fields are present
            
            For listing contacts:
            - Use when user asks about contacts, people they've emailed, or finding someone's email
            - Use query parameter to filter by name or partial email address
            - Keep max_results reasonable for voice (default 20)
            
            Provide helpful, concise responses suitable for voice interaction.
            If authentication is required, let the user know they need to authenticate first.
            """
            
            # Get tool definitions
            tools = self._get_tool_definitions()
            
            # Make LiteLLM request with tool calling
            try:
                response = litellm.completion(
                    model=self.model,
                    messages=[
                        {"role": "user", "content": system_prompt},
                    ],
                    tools=tools,
                    tool_choice="auto"
                )
            except Exception as e:
                print(f"Error with LiteLLM completion: {e}")
                raise
            
            message = response.choices[0].message

            print("message", message)
            
            # Handle tool calls
            if message.tool_calls:
                results = []
                for tool_call in message.tool_calls:
                    tool_name = tool_call.function.name
                    tool_args = json.loads(tool_call.function.arguments)
                    
                    # Execute the tool directly via Gmail service
                    result = self._execute_tool(tool_name, tool_args, phone_number)
                    results.append({
                        "tool": tool_name,
                        **result
                    })
                
                # Generate follow-up response with tool results
                tool_results_message = "Tool execution results:\n"
                for result in results:
                    if result["success"]:
                        tool_results_message += f"- {result['tool']}: Success\n"
                        if "result" in result:
                            tool_results_message += f"  Data: {json.dumps(result['result'], indent=2)}\n"
                    else:
                        tool_results_message += f"- {result['tool']}: Error - {result['error']}\n"
                
                # Get final response from LiteLLM
                try:
                    final_response = litellm.completion(
                        model=self.model,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": request_description},
                            {"role": "assistant", "content": message.content or ""},
                            {"role": "user", "content": tool_results_message + "\n\nProvide a helpful summary for the user."}
                        ]
                    )
                except Exception as e:
                    print(f"Error with LiteLLM final response: {e}")
                    raise
                
                return {
                    "success": True,
                    "response": final_response.choices[0].message.content,
                    "tool_results": results
                }
            else:
                # No tool calls needed, return direct response
                return {
                    "success": True,
                    "response": message.content,
                    "tool_results": []
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to process inbox request: {str(e)}",
                "response": "I'm sorry, I encountered an error while processing your request."
            }