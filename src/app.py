from flask import Flask, request, redirect, session, jsonify, render_template_string
import secrets
import os
from .auth import GmailAuth
from .auth_web import GmailWebAuth
from .gmail_service import GmailService

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)

# Use web auth for cloud deployment, desktop auth for local
is_cloud = os.getenv('PORT') or os.getenv('RAILWAY_ENVIRONMENT') 
gmail_auth = GmailWebAuth() if is_cloud else GmailAuth()
gmail_service = GmailService()

@app.route('/')
def index():
    try:
        # Override the gmail_service auth with our selected auth method
        gmail_service.auth = gmail_auth
        
        if gmail_service.authenticate():
            return render_template_string('''
            <h1>Gmail Voice Messaging Server</h1>
            <p>✅ Connected to Gmail successfully!</p>
            <p><strong>Environment:</strong> {{ env_type }}</p>
            <p><a href="/messages">View Messages</a></p>
            <p><a href="/send">Send Message</a></p>
            <p><a href="/logout">Disconnect Gmail</a></p>
            ''', env_type='Cloud' if is_cloud else 'Local')
        else:
            auth_method = "web-based OAuth" if is_cloud else "desktop OAuth"
            return render_template_string('''
            <h1>Gmail Voice Messaging Server</h1>
            <p>❌ Not connected to Gmail</p>
            <p><strong>Environment:</strong> {{ env_type }}</p>
            <p><strong>Auth Method:</strong> {{ auth_method }}</p>
            {% if is_cloud %}
                <p><a href="/auth" style="background: #1a73e8; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">🔐 Connect Gmail Account</a></p>
            {% else %}
                <p>Run <code>python desktop_auth.py</code> first, then:</p>
            {% endif %}
            <p><a href="/messages">View Messages</a> | <a href="/send">Send Message</a></p>
            ''', env_type='Cloud' if is_cloud else 'Local', auth_method=auth_method, is_cloud=is_cloud)
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
        # Use web auth regardless of environment for this route
        web_auth = GmailWebAuth()
        authorization_url, state = web_auth.get_authorization_url()
        session['oauth_state'] = state
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
        
        # Exchange code for token
        web_auth = GmailWebAuth()
        credentials = web_auth.exchange_code_for_token(code, session['oauth_state'])
        
        if credentials:
            # Update the global auth instance
            global gmail_auth
            gmail_auth = web_auth
            gmail_service.auth = gmail_auth
            
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
        # Ensure we're using the correct auth method
        gmail_service.auth = gmail_auth
        
        if not gmail_service.authenticate():
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
        # Ensure we're using the correct auth method
        gmail_service.auth = gmail_auth
        
        if not gmail_service.authenticate():
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
    import os
    token_file = 'config/token.json'
    if os.path.exists(token_file):
        os.remove(token_file)
    return redirect('/')

if __name__ == '__main__':
    print("Starting Gmail Voice Messaging Server...")
    print("Please make sure to:")
    print("1. Copy .env.example to .env and fill in your Google OAuth credentials")
    print("2. Install dependencies: pip install -r requirements.txt")
    print("3. Visit http://localhost:5000 to connect your Gmail account")
    app.run(debug=True, port=5000)