#!/usr/bin/env python3
"""
Upload Paper 1 v2.0 External PDF to Google Drive
Run this script locally on your machine
"""

import os
import sys
from google.auth.transport.requests import Request
from google.oauth2.service_account import Credentials
from google.auth.oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials as UserCredentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# Google Drive API scope
SCOPES = ['https://www.googleapis.com/auth/drive.file']

def authenticate_drive():
    """Authenticate with Google Drive using OAuth"""
    creds = None

    # Check for existing token.json
    if os.path.exists('token.json'):
        creds = UserCredentials.from_authorized_user_file('token.json', SCOPES)

    # If no valid credentials, create new ones
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # Download credentials.json from Google Cloud Console first
            if not os.path.exists('credentials.json'):
                print("ERROR: credentials.json not found")
                print("Steps:")
                print("1. Go to https://console.cloud.google.com/")
                print("2. Create OAuth 2.0 credentials (Desktop app)")
                print("3. Save as 'credentials.json' in this directory")
                sys.exit(1)

            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)

        # Save token for next time
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    return creds

def upload_to_drive(file_path, folder_name='Tofoo'):
    """Upload PDF to Google Drive"""
    try:
        creds = authenticate_drive()
        service = build('drive', 'v3', credentials=creds)

        # Check if folder exists
        results = service.files().list(
            q=f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false",
            spaces='drive',
            pageSize=1,
            fields='files(id, name)'
        ).execute()

        folder_id = None
        if results.get('files'):
            folder_id = results['files'][0]['id']
            print(f"✓ Found folder: {folder_name}")
        else:
            # Create folder if it doesn't exist
            file_metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder'
            }
            folder = service.files().create(body=file_metadata, fields='id').execute()
            folder_id = folder.get('id')
            print(f"✓ Created folder: {folder_name}")

        # Upload file
        file_name = os.path.basename(file_path)
        file_metadata = {
            'name': file_name,
            'parents': [folder_id]
        }

        media = MediaFileUpload(
            file_path,
            mimetype='application/pdf',
            resumable=True
        )

        print(f"Uploading {file_name}...")
        file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id, webViewLink'
        ).execute()

        print(f"✓ Upload successful!")
        print(f"  File: {file_name}")
        print(f"  Link: {file.get('webViewLink')}")

    except Exception as e:
        print(f"✗ Error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    pdf_file = 'Paper1_v2.0_External_Public.pdf'

    if not os.path.exists(pdf_file):
        print(f"ERROR: {pdf_file} not found in current directory")
        sys.exit(1)

    print("Google Drive Upload Script")
    print("=" * 50)
    print(f"File to upload: {pdf_file}")
    print()

    upload_to_drive(pdf_file)
