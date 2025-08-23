from flask import Flask, request, redirect, session, jsonify, render_template_string
import secrets
import os
import uuid
from .auth import GmailAuth
from .auth_web import GmailWebAuth
from .gmail_service import GmailService
from .database import Database

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', secrets.token_hex(16))

# Initialize database
db = Database()

# Use web auth for cloud deployment, desktop auth for local
is_cloud = os.getenv('PORT') or os.getenv('RAILWAY_ENVIRONMENT')

def get_user_session():
    """Get or create user session"""
    if 'user_session_id' not in session:
        session['user_session_id'] = str(uuid.uuid4())
    return session['user_session_id']

def get_current_user():
    """Get current user from database"""
    session_id = get_user_session()
    return db.get_or_create_user(session_id)

def get_auth_instance(user_id=None):
    """Get appropriate auth instance for current environment"""
    if is_cloud:
        return GmailWebAuth(user_id)
    else:
        return GmailAuth()

def get_gmail_service(user_id=None):
    """Get Gmail service with proper auth instance"""
    auth_instance = get_auth_instance(user_id)
    return GmailService(auth_instance)

@app.route('/')
def index():
    try:
        # Initialize database tables
        db.create_tables()
        
        # Get current user
        user = get_current_user()
        gmail_service = get_gmail_service(user['id'])
        
        if gmail_service.authenticate(user['id']):
            return render_template_string('''
            <h1>Gmail Voice Messaging Server</h1>
            <p>✅ Connected to Gmail successfully!</p>
            <p><strong>Environment:</strong> {{ env_type }}</p>
            <p><strong>User Session:</strong> {{ user_session }}</p>
            {% if user_email %}
                <p><strong>Gmail Account:</strong> {{ user_email }}</p>
            {% endif %}
            <p><a href="/messages">View Messages</a></p>
            <p><a href="/send">Send Message</a></p>
            <p><a href="/logout">Disconnect Gmail</a></p>
            ''', env_type='Cloud' if is_cloud else 'Local', 
                 user_session=user['session_id'][:8] + '...', 
                 user_email=user.get('email'))
        else:
            auth_method = "web-based OAuth" if is_cloud else "desktop OAuth"
            return render_template_string('''
            <h1>Gmail Voice Messaging Server</h1>
            <p>❌ Not connected to Gmail</p>
            <p><strong>Environment:</strong> {{ env_type }}</p>
            <p><strong>Auth Method:</strong> {{ auth_method }}</p>
            <p><strong>User Session:</strong> {{ user_session }}</p>
            {% if is_cloud %}
                <p><a href="/auth" style="background: #1a73e8; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">🔐 Connect Gmail Account</a></p>
            {% else %}
                <p>Run <code>python desktop_auth.py</code> first, then:</p>
            {% endif %}
            <p><a href="/messages">View Messages</a> | <a href="/send">Send Message</a></p>
            ''', env_type='Cloud' if is_cloud else 'Local', 
                 auth_method=auth_method, 
                 is_cloud=is_cloud,
                 user_session=user['session_id'][:8] + '...')
    except Exception as e:
        return render_template_string('''
        <h1>Gmail Voice Messaging Server</h1>
        <p>❌ Authentication error: {{ error }}</p>
        <p><a href="/auth">Try Web Authentication</a></p>
        ''', error=str(e))

@app.route('/auth')
def auth():
    """Start Gmail OAuth authentication"""
    try:
        # Ensure we have a user session
        user = get_current_user()
        
        # Use web auth regardless of environment for this route
        web_auth = GmailWebAuth(user['id'])
        authorization_url, state = web_auth.get_authorization_url()
        session['oauth_state'] = state
        session['auth_user_id'] = user['id']
        return redirect(authorization_url)
    except Exception as e:
        return render_template_string('''
        <h1>Authentication Error</h1>
        <p>Failed to start authentication: {{ error }}</p>
        <p><a href="/">← Back to Home</a></p>
        ''', error=str(e))

@app.route('/auth/callback')
def auth_callback():
    """Handle OAuth callback"""
    try:
        # Check state parameter
        if request.args.get('state') != session.get('oauth_state'):
            return render_template_string('''
            <h1>Authentication Error</h1>
            <p>Invalid state parameter. Please try again.</p>
            <p><a href="/auth">Restart Authentication</a></p>
            '''), 400
        
        code = request.args.get('code')
        if not code:
            return render_template_string('''
            <h1>Authentication Error</h1>
            <p>No authorization code received.</p>
            <p><a href="/auth">Try Again</a></p>
            '''), 400
        
        # Get user ID from session
        user_id = session.get('auth_user_id')
        if not user_id:
            return render_template_string('''
            <h1>Authentication Error</h1>
            <p>Session expired. Please try again.</p>
            <p><a href="/auth">Try Again</a></p>
            '''), 400
        
        # Exchange code for token
        web_auth = GmailWebAuth(user_id)
        credentials = web_auth.exchange_code_for_token(code, session['oauth_state'], user_id)
        
        if credentials:
            # Try to get user's email from credentials if available
            try:
                from googleapiclient.discovery import build
                service = build('gmail', 'v1', credentials=credentials)
                profile = service.users().getProfile(userId='me').execute()
                email = profile.get('emailAddress')
                if email:
                    db.update_user_email(user_id, email)
            except Exception as e:
                print(f"Could not get user email: {e}")
            
            return render_template_string('''
            <h1>✅ Authentication Successful!</h1>
            <p>Your Gmail account has been connected successfully.</p>
            <p><a href="/">← Back to Home</a></p>
            <p><a href="/messages">View Messages</a> | <a href="/send">Send Message</a></p>
            ''')
        else:
            return render_template_string('''
            <h1>Authentication Failed</h1>
            <p>Failed to exchange authorization code for access token.</p>
            <p><a href="/auth">Try Again</a></p>
            '''), 400
            
    except Exception as e:
        return render_template_string('''
        <h1>Authentication Error</h1>
        <p>Error during authentication: {{ error }}</p>
        <p><a href="/auth">Try Again</a></p>
        ''', error=str(e)), 500

@app.route('/messages')
def messages():
    try:
        user = get_current_user()
        gmail_service = get_gmail_service(user['id'])
        
        if not gmail_service.authenticate(user['id']):
            if is_cloud:
                return render_template_string('''
                <h1>Authentication Required</h1>
                <p>You need to connect your Gmail account first.</p>
                <p><a href="/auth" style="background: #1a73e8; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">🔐 Connect Gmail Account</a></p>
                <p><a href="/">← Back to Home</a></p>
                ''')
            else:
                return render_template_string('''
                <h1>Authentication Required</h1>
                <p>Please run <code>python desktop_auth.py</code> first to authenticate.</p>
                <p><a href="/">← Back to Home</a></p>
                ''')
    
        # If we get here, authentication was successful
        messages = gmail_service.get_messages(max_results=5)
        html = '<h1>Recent Messages</h1><a href="/">← Back</a><br><br>'
        
        if not messages:
            html += '<p>No messages found or unable to fetch messages.</p>'
        else:
            for msg in messages:
                html += f'''
                <div style="border: 1px solid #ccc; padding: 10px; margin: 10px 0;">
                    <strong>From:</strong> {msg['sender']}<br>
                    <strong>Subject:</strong> {msg['subject']}<br>
                    <strong>Date:</strong> {msg['date']}<br>
                    <strong>Body:</strong> {msg['body'][:200]}...
                </div>
                '''
        
        return html
        
    except Exception as e:
        return f'Error fetching messages: {str(e)}'

@app.route('/send', methods=['GET', 'POST'])
def send():
    try:
        user = get_current_user()
        gmail_service = get_gmail_service(user['id'])
        
        if not gmail_service.authenticate(user['id']):
            if is_cloud:
                return render_template_string('''
                <h1>Authentication Required</h1>
                <p>You need to connect your Gmail account first.</p>
                <p><a href="/auth" style="background: #1a73e8; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">🔐 Connect Gmail Account</a></p>
                <p><a href="/">← Back to Home</a></p>
                ''')
            else:
                return render_template_string('''
                <h1>Authentication Required</h1>
                <p>Please run <code>python desktop_auth.py</code> first to authenticate.</p>
                <p><a href="/">← Back to Home</a></p>
                ''')
    
        if request.method == 'GET':
            return render_template_string('''
            <h1>Send Message</h1>
            <a href="/">← Back</a>
            <form method="POST">
                <p>To: <input type="email" name="to" required style="width: 300px;"></p>
                <p>Subject: <input type="text" name="subject" required style="width: 300px;"></p>
                <p>Message:<br><textarea name="body" rows="10" cols="50" required></textarea></p>
                <p><input type="submit" value="Send Message"></p>
            </form>
            ''')
    
        # POST request - send the message
        to = request.form['to']
        subject = request.form['subject']
        body = request.form['body']
        
        result = gmail_service.send_message(to, subject, body)
        if result:
            return '<h1>Message Sent Successfully!</h1><a href="/">← Back</a>'
        else:
            return '<h1>Failed to Send Message</h1><a href="/send">← Try Again</a>'
            
    except Exception as e:
        return f'Error sending message: {str(e)}'

@app.route('/logout')
def logout():
    """Logout user and remove their OAuth tokens"""
    try:
        user = get_current_user()
        auth_instance = get_auth_instance(user['id'])
        
        # Remove OAuth tokens from database
        if hasattr(auth_instance, 'logout'):
            auth_instance.logout()
        
        # Clear session
        session.clear()
        
        return render_template_string('''
        <h1>Logged Out Successfully</h1>
        <p>Your Gmail connection has been removed.</p>
        <p><a href="/">Return to Home</a></p>
        ''')
    except Exception as e:
        return render_template_string('''
        <h1>Logout Error</h1>
        <p>Error during logout: {{ error }}</p>
        <p><a href="/">Return to Home</a></p>
        ''', error=str(e))

if __name__ == '__main__':
    print("Starting Gmail Voice Messaging Server...")
    print("Please make sure to:")
    print("1. Copy .env.example to .env and fill in your Google OAuth credentials")
    print("2. Install dependencies: pip install -r requirements.txt")
    print("3. Visit http://localhost:5000 to connect your Gmail account")
    app.run(debug=True, port=5000)