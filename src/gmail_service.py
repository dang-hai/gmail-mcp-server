import base64
import email
import re
from collections import defaultdict
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from .auth import GmailAuth

class GmailService:
    def __init__(self, auth_instance=None):
        self.auth = auth_instance or GmailAuth()
        self.service = None
        self.user_id = None
        
    def authenticate(self, user_id=None, phone_number=None):
        """Authenticate with automatic token refresh"""
        if user_id:
            self.user_id = user_id
            if hasattr(self.auth, 'set_user_id'):
                self.auth.set_user_id(user_id)
        
        # Support phone number authentication
        if phone_number:
            creds = self.auth.get_credentials(phone_number)
        else:
            creds = self.auth.get_credentials()
            
        if creds and creds.valid:
            try:
                self.service = build('gmail', 'v1', credentials=creds)
                return True
            except Exception as e:
                print(f"Error building Gmail service: {e}")
                return False
        return False
    
    def get_messages(self, query='', max_results=10):
        """Get messages with automatic token refresh on auth failure"""
        if not self.service:
            raise Exception("Not authenticated")
            
        try:
            results = self.service.users().messages().list(
                userId='me', q=query, maxResults=max_results
            ).execute()
            
            messages = results.get('messages', [])
            detailed_messages = []
            
            for message in messages:
                msg = self.service.users().messages().get(
                    userId='me', id=message['id']
                ).execute()
                
                payload = msg['payload']
                headers = payload.get('headers', [])
                
                subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
                sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown')
                date = next((h['value'] for h in headers if h['name'] == 'Date'), 'Unknown')
                
                body = self._extract_body(payload)
                
                detailed_messages.append({
                    'id': message['id'],
                    'subject': subject,
                    'sender': sender,
                    'date': date,
                    'body': body
                })
                
            return detailed_messages
            
        except HttpError as error:
            if error.resp.status == 401:  # Unauthorized - token expired
                print("Token expired, attempting to re-authenticate...")
                if self.authenticate(self.user_id):
                    return self.get_messages(query, max_results)  # Retry
            print(f'HTTP error occurred: {error}')
            return []
        except Exception as error:
            print(f'An error occurred: {error}')
            return []
    
    def _extract_body(self, payload):
        body = ""
        if 'parts' in payload:
            for part in payload['parts']:
                if part['mimeType'] == 'text/plain':
                    if 'data' in part['body']:
                        body = base64.urlsafe_b64decode(
                            part['body']['data']
                        ).decode('utf-8')
                        break
        else:
            if payload['mimeType'] == 'text/plain':
                if 'data' in payload['body']:
                    body = base64.urlsafe_b64decode(
                        payload['body']['data']
                    ).decode('utf-8')
        
        return body
    
    def send_message(self, to, subject, body):
        """Send message with automatic token refresh on auth failure"""
        if not self.service:
            raise Exception("Not authenticated")
            
        try:
            message = MIMEText(body)
            message['to'] = to
            message['subject'] = subject
            
            raw_message = base64.urlsafe_b64encode(
                message.as_bytes()
            ).decode('utf-8')
            
            send_message = self.service.users().messages().send(
                userId='me', 
                body={'raw': raw_message}
            ).execute()
            
            return send_message
            
        except HttpError as error:
            if error.resp.status == 401:  # Unauthorized - token expired
                print("Token expired, attempting to re-authenticate...")
                if self.authenticate(self.user_id):
                    return self.send_message(to, subject, body)  # Retry
            print(f'HTTP error occurred: {error}')
            return None
        except Exception as error:
            print(f'An error occurred: {error}')
            return None
    
    def list_contacts(self, query='', max_results=20):
        """
        List approximate contacts based on a query by searching email history.
        Searches both From and To fields in recent emails to find matching contacts.
        
        Args:
            query: Search query to match against contact names/emails (case-insensitive)
            max_results: Maximum number of contacts to return (default: 20)
            
        Returns:
            List of contact dictionaries with name, email, and interaction count
        """
        if not self.service:
            raise Exception("Not authenticated")
            
        try:
            # Search recent emails to build contact list (last 500 messages for better coverage)
            search_query = f'in:sent OR in:inbox'
            results = self.service.users().messages().list(
                userId='me', q=search_query, maxResults=500
            ).execute()
            
            messages = results.get('messages', [])
            contacts = defaultdict(lambda: {'name': '', 'email': '', 'count': 0})
            
            for message in messages:
                try:
                    msg = self.service.users().messages().get(
                        userId='me', id=message['id'], format='metadata',
                        metadataHeaders=['From', 'To', 'Cc', 'Bcc']
                    ).execute()
                    
                    headers = msg['payload'].get('headers', [])
                    
                    # Extract email addresses from various header fields
                    for header in headers:
                        if header['name'] in ['From', 'To', 'Cc', 'Bcc']:
                            email_addresses = self._extract_email_addresses(header['value'])
                            
                            for email_addr, name in email_addresses:
                                # Skip own email address (approximate check)
                                if 'me' in email_addr.lower() or not email_addr:
                                    continue
                                    
                                contacts[email_addr]['email'] = email_addr
                                contacts[email_addr]['name'] = name or email_addr.split('@')[0]
                                contacts[email_addr]['count'] += 1
                                
                except Exception:
                    # Skip messages that can't be processed
                    continue
            
            # Filter contacts based on query if provided
            filtered_contacts = []
            query_lower = query.lower() if query else ''
            
            for contact_data in contacts.values():
                if not query or (
                    query_lower in contact_data['name'].lower() or 
                    query_lower in contact_data['email'].lower()
                ):
                    filtered_contacts.append({
                        'name': contact_data['name'],
                        'email': contact_data['email'],
                        'interaction_count': contact_data['count']
                    })
            
            # Sort by interaction count (most frequent contacts first)
            filtered_contacts.sort(key=lambda x: x['interaction_count'], reverse=True)
            
            return filtered_contacts[:max_results]
            
        except HttpError as error:
            if error.resp.status == 401:  # Unauthorized - token expired
                print("Token expired, attempting to re-authenticate...")
                if self.authenticate(self.user_id):
                    return self.list_contacts(query, max_results)  # Retry
            print(f'HTTP error occurred: {error}')
            return []
        except Exception as error:
            print(f'An error occurred while listing contacts: {error}')
            return []
    
    def _extract_email_addresses(self, header_value):
        """
        Extract email addresses and names from email header values.
        Handles formats like: "Name <email@domain.com>", "email@domain.com", "Name <email>, Another <email2>"
        
        Returns:
            List of tuples (email, name)
        """
        addresses = []
        
        # Split by comma for multiple addresses
        parts = [part.strip() for part in header_value.split(',')]
        
        for part in parts:
            # Match patterns like "Name <email@domain.com>" or just "email@domain.com"
            email_pattern = r'([^<>]+?)\s*<([^<>]+@[^<>]+)>|([^\s,]+@[^\s,]+)'
            matches = re.findall(email_pattern, part)
            
            for match in matches:
                if match[1] and match[0]:  # "Name <email>" format
                    name = match[0].strip().strip('"\'')
                    email_addr = match[1].strip()
                    addresses.append((email_addr, name))
                elif match[2]:  # Just "email" format
                    email_addr = match[2].strip()
                    addresses.append((email_addr, ''))
        
        return addresses