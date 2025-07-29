import os
from google.oauth2 import service_account
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from django.conf import settings

#THIS FILE IS USED TO GET GOOGLE API CREDENTIAL OBJECTS
#returns sheets api credential object
def get_google_sheets_service_creds():
    print(f"Service account file path: {settings.GOOGLE_SERVICE_ACCOUNT_KEY}")
    print(f"File exists: {os.path.exists(settings.GOOGLE_SERVICE_ACCOUNT_KEY)}")

    creds = service_account.Credentials.from_service_account_file(
        settings.GOOGLE_SERVICE_ACCOUNT_KEY,
        scopes=['https://www.googleapis.com/auth/spreadsheets',
                'https://www.googleapis.com/auth/drive',
                'https://www.googleapis.com/auth/drive.file']
    )

    print(f"Service account email: {creds.service_account_email}")
    print(f"Project ID: {creds.project_id}")
    print(f"Token valid before refresh: {creds.valid}")

    # Force refresh the token
    try:
        creds.refresh(Request())
        print(f"Token valid after refresh: {creds.valid}")
        print("Credentials refreshed successfully")
    except Exception as e:
        print(f"Error refreshing credentials: {e}")
        return None

    return build('sheets', 'v4', credentials=creds)

#gets google drive service credentials (USED IN CREATING SPREADSHEET)
def get_google_drive_service_creds():
    creds = service_account.Credentials.from_service_account_file(
        settings.GOOGLE_SERVICE_ACCOUNT_KEY,
        scopes=['https://www.googleapis.com/auth/drive',
                'https://www.googleapis.com/auth/drive.file']
    )
    print(f"Token valid before refresh: {creds.valid}")

    # Force refresh the token
    try:
        creds.refresh(Request())
        print(f"Token valid after refresh: {creds.valid}")
        print("Credentials refreshed successfully")
    except Exception as e:
        print(f"Error refreshing credentials: {e}")
        return None
    return build('drive', 'v3', credentials=creds, developerKey=settings.GOOGLE_API_KEY)
