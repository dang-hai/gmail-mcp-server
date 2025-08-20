import base64
import email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from googleapiclient.discovery import build
from .auth import GmailAuth

class GmailService:
    def __init__(self):
        self.auth = GmailAuth()
        self.service = None
        
    def authenticate(self):
        creds = self.auth.get_credentials()
        if creds:
            self.service = build('gmail', 'v1', credentials=creds)
            return True
        return False
    
    def get_messages(self, query='', max_results=10):
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
            
        except Exception as error:
            print(f'An error occurred: {error}')
            return None