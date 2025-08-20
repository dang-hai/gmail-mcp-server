from flask import Flask, request, redirect, session, jsonify, render_template_string
import secrets
from .auth import GmailAuth
from .gmail_service import GmailService

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)

gmail_auth = GmailAuth()
gmail_service = GmailService()

@app.route('/')
def index():
    try:
        if gmail_service.authenticate():
            return render_template_string('''
            <h1>Gmail Voice Messaging Server</h1>
            <p>✅ Connected to Gmail successfully!</p>
            <p><a href="/messages">View Messages</a></p>
            <p><a href="/send">Send Message</a></p>
            <p><a href="/logout">Disconnect Gmail</a></p>
            ''')
        else:
            return render_template_string('''
            <h1>Gmail Voice Messaging Server</h1>
            <p>❌ Not connected to Gmail</p>
            <p>Authentication will happen automatically when you access Gmail features.</p>
            <p><a href="/messages">View Messages (will prompt for auth)</a></p>
            <p><a href="/send">Send Message (will prompt for auth)</a></p>
            ''')
    except Exception as e:
        return render_template_string(f'''
        <h1>Gmail Voice Messaging Server</h1>
        <p>❌ Authentication error: {str(e)}</p>
        <p><a href="/messages">Try accessing messages</a></p>
        ''')


@app.route('/messages')
def messages():
    try:
        if not gmail_service.authenticate():
            return render_template_string('''
            <h1>Authentication Required</h1>
            <p>Please check your terminal/console for authentication prompts.</p>
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
        if not gmail_service.authenticate():
            return render_template_string('''
            <h1>Authentication Required</h1>
            <p>Please check your terminal/console for authentication prompts.</p>
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