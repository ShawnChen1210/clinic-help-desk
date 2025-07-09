import os
from google.oauth2 import service_account
from googleapiclient.discovery import build
from django.conf import settings

#returns api credential object
def get_google_sheets_service_creds():
    creds = service_account.Credentials.from_service_account_file(
        settings.GOOGLE_SERVICE_ACCOUNT_KEY,
        #some google sheets operation require google drive scope permissions, thus its inclusion
        scopes=['https://www.googleapis.com/auth/spreadsheets',
                'https://www.googleapis.com/auth/drive']
    )
    return build('sheets', 'v4', credentials=creds)

def get_google_drive_service_creds():
    creds = service_account.Credentials.from_service_account_file(
        settings.GOOGLE_SERVICE_ACCOUNT_KEY,
        scopes=['https://www.googleapis.com/auth/drive']
    )
    return build('drive', 'v3', credentials=creds)