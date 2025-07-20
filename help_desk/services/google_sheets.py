from help_desk.utils import *
from clinic_help_desk.settings import *

def create_new_google_sheet(title = "New Sheet"): #title needs to be filled when function is referenced, New Sheet is default name if no title is given
    drive_service = get_google_drive_service_creds()
    spreadsheet_metadata = {
        'name': title,
        'parents': [SHARED_DRIVE_ID],
        'mimeType': 'application/vnd.google-apps.spreadsheet'
    }
    #API CALL!!
    try:
        spreadsheet = drive_service.files().create(
            body=spreadsheet_metadata,
            supportsAllDrives=True
        ).execute()
        if spreadsheet:
            sheetID = spreadsheet.get('id')
            print(f"Successfully created spreadsheet: {sheetID}")
            print(f"URL: https://docs.google.com/spreadsheets/d/{sheetID}/edit")
            return sheetID
    except Exception as e:
        print(f"Error creating spreadsheet: {e}")
        return None

def delete_google_sheet(sheetID):
    drive_service = get_google_drive_service_creds()

    try:
        drive_service.files().delete(fileId=sheetID).execute()
        return True
    except Exception as e:
        print(f"Error deleting spreadsheet: {e}")
        return False




def test_drive_connection():
    try:
        drive_service = get_google_drive_service_creds()
        drive_info = drive_service.drives().get(driveId=SHARED_DRIVE_ID).execute()
        print(f"✅ Connected to: {drive_info['name']}")
        results = drive_service.files().list(
            q=f"parents in '{SHARED_DRIVE_ID}'",
            supportsAllDrives=True,
            includeItemsFromAllDrives=True,
            fields="files(id, name, createdTime, owners)"
        ).execute()

        for file in results.get('files', []):
            print(f"Name: {file['name']}, ID: {file['id']}")
    except Exception as e:
        print(f"❌ Error: {e}")

        if "404" in str(e):
            print("\n💡 Troubleshooting 404 error:")
            print("   - Check if SHARED_DRIVE_ID is correct")
            print("   - Verify service account is added to shared drive")

        elif "403" in str(e):
            print("\n💡 Troubleshooting 403 error:")
            print("   - Check if APIs are enabled in Google Cloud Console")
            print("   - Verify service account has proper permissions")
            print("   - Make sure service account is added to shared drive as 'Content manager'")

        return False


def grant_editor_access(spreadsheet_id, email): #gives editor access to users who created the file in google sheets
    drive_service = get_google_drive_service_creds()

    permission = {
        'type': 'user',
        'role': 'writer',  # 'writer' = editor access
        'emailAddress': email
    }

    drive_service.permissions().create(
        fileId=spreadsheet_id,
        body=permission,
        supportsAllDrives=True
    ).execute()