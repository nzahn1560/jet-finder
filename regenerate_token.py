#!/usr/bin/env python3
"""
Regenerate token.json from credentials.json for Google OAuth
This script will open a browser for authentication and save the token.
"""

import os
import json
from pathlib import Path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']

def regenerate_token():
    """Regenerate token.json from credentials.json"""
    creds = None
    token_path = Path('token.json')
    creds_path = Path('credentials.json')
    
    # Check if credentials.json exists
    if not creds_path.exists():
        print("❌ Error: credentials.json not found!")
        print("   Please make sure credentials.json is in the current directory.")
        return False
    
    # The file token.json stores the user's access and refresh tokens.
    # It's created automatically when the authorization flow completes for the first time.
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
    
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("🔄 Refreshing expired token...")
            creds.refresh(Request())
        else:
            print("🔐 Starting OAuth flow...")
            print("   A browser window will open for authentication.")
            flow = InstalledAppFlow.from_client_secrets_file(
                str(creds_path), SCOPES)
            creds = flow.run_local_server(port=0)
        
        # Save the credentials for the next run
        with open(token_path, 'w') as token:
            token.write(creds.to_json())
        print("✅ Token saved to token.json")
        return True
    else:
        print("✅ Token is still valid. No regeneration needed.")
        return True

if __name__ == '__main__':
    print("Google OAuth Token Regeneration")
    print("=" * 40)
    regenerate_token()

