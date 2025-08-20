# Railway Deployment Guide for Gmail MCP Server

## ⚠️ Security First

**BEFORE DEPLOYING**: 
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Navigate to APIs & Services > Credentials
3. **DELETE** your current OAuth credentials (they're compromised)
4. Create new OAuth credentials

## Option 1: Quick Deploy (OAuth - Simpler but less secure)

### 1. Update OAuth Credentials
- In Google Cloud Console, edit your OAuth 2.0 Client
- Change application type to "Web application"
- Add authorized redirect URI: `https://your-app.railway.app/auth/callback`

### 2. Deploy to Railway
```bash
# Install Railway CLI
npm install -g @railway/cli

# Login to Railway
railway login

# In your python-server directory
railway init

# Set environment variables in Railway dashboard:
# GOOGLE_CLIENT_ID=your_new_client_id
# GOOGLE_CLIENT_SECRET=your_new_client_secret

# Deploy
railway up
```

## Option 2: Service Account (Recommended for production)

### 1. Create Service Account
1. In Google Cloud Console, go to IAM & Admin > Service Accounts
2. Click "Create Service Account"
3. Name it "gmail-mcp-server"
4. Grant role: "Service Account User"
5. Create and download the JSON key file

### 2. Enable Domain-Wide Delegation
1. Edit the service account
2. Check "Enable Google Workspace Domain-wide Delegation"  
3. Note the Client ID

### 3. Configure Google Workspace (if using G Suite)
1. Go to Google Admin Console
2. Security > API Controls > Domain-wide Delegation
3. Add the service account Client ID
4. Scopes: 
   ```
   https://www.googleapis.com/auth/gmail.readonly,
   https://www.googleapis.com/auth/gmail.send,
   https://www.googleapis.com/auth/gmail.compose
   ```

### 4. Deploy to Railway
```bash
railway init

# Set environment variables in Railway dashboard:
# GOOGLE_SERVICE_ACCOUNT_JSON={"type":"service_account",...} (entire JSON content)
# GMAIL_USER_EMAIL=your-gmail@domain.com

railway up
```

## Environment Variables for Railway

Set these in your Railway project dashboard:

### For OAuth (Option 1):
- `GOOGLE_CLIENT_ID`: Your new OAuth client ID
- `GOOGLE_CLIENT_SECRET`: Your new OAuth client secret

### For Service Account (Option 2):
- `GOOGLE_SERVICE_ACCOUNT_JSON`: Full JSON content of service account key
- `GMAIL_USER_EMAIL`: The Gmail address to access

## Testing Your Deployment

Once deployed, your MCP server will be available at:
`https://your-app.railway.app`

Test the auth endpoint:
```bash
curl https://your-app.railway.app/tools
```

## Using with Claude Code

Update your `.mcp.json`:
```json
{
  "servers": {
    "gmail-voice-messaging": {
      "command": "curl",
      "args": ["-X", "POST", "https://your-app.railway.app/mcp"]
    }
  }
}
```

## Troubleshooting

- Check Railway logs: `railway logs`
- Verify environment variables are set
- For service account: ensure domain-wide delegation is properly configured
- For OAuth: ensure redirect URIs match exactly