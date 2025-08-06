from help_desk.utils import *
from clinic_help_desk.settings import *
import csv

#THIS FILE IS FOR ALL OPERATIONS REGARDING GOOGLE SHEET AND ITS API
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
        drive_service.files().delete(
            fileId = sheetID,
            supportsAllDrives = True
        ).execute()

        return True
    except Exception as e: #debug. check console for print error if any arises
        print(f"Error deleting spreadsheet: {e}")
        return False

def rename_google_sheet(sheetID, name):
    drive_service = get_google_drive_service_creds()
    try:
        drive_service.files().delete(
            fileId = sheetID,
            supportsAllDrives = True
        ).execute()

        return True
    except Exception as e: #debug. check console for print error if any arises
        print(f"Error deleting spreadsheet: {e}")
        return False


def test_drive_connection():
    try:
        drive_service = get_google_drive_service_creds()
        drive_info = drive_service.drives().get(driveId=SHARED_DRIVE_ID).execute()
        print(f" Connected to: {drive_info['name']}")
        results = drive_service.files().list(
            q=f"parents in '{SHARED_DRIVE_ID}'",
            supportsAllDrives=True,
            includeItemsFromAllDrives=True,
            fields="files(id, name, createdTime, owners)"
        ).execute()

        for file in results.get('files', []):
            print(f"Name: {file['name']}, ID: {file['id']}")
    except Exception as e:
        print(f" Error: {e}")

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

def read_google_sheets(sheet_id, range_name): #inputs column range from A-Z and row range from 1-100000000.
    sheets_service = get_google_sheets_service_creds()
    try:
        result = sheets_service.spreadsheets().values().get(
            spreadsheetId=sheet_id,
            range=range_name
        ).execute()
        return result.get('values', [])
    except Exception as e:
        print(f"Error reading google sheets: {e}")
        return []

#returns a list of lists that has equal rows and columns since if one row has 3 cells and one row has 4 cells, google's .spreadsheets().values().get() does not return an additional empty cell for the row with 3 cells. this fixes that.
def padded_google_sheets(sheet_id, range_name):
    sheet_data = read_google_sheets(sheet_id, range_name)

    if sheet_data:
        max_length = max(len(row) for row in sheet_data) #returns the row with the longest length
        padded_header = []
        padded_data = []
        for i, row in enumerate(sheet_data):
            if i == 0:
                padded_header = row + [''] * (max_length - len(row))
            else:
                padded_row = row + [''] * (max_length - len(row))
                padded_data.append(padded_row)
        return padded_data, padded_header
    else:
        return [], []

def batch_upload_csv(csv_file_path, spreadsheet_id): #for uploading csv
    sheets_service = get_google_sheets_service_creds()

    with open(csv_file_path, 'r') as file:
        csv_reader = csv.reader(file)
        values = list(csv_reader)

    requests = [{
        'updateCells': {
            'start': {'sheetId': 0, 'rowIndex': 0, 'columnIndex': 0},
            'rows': [
                {'values': [{'userEnteredValue': {'stringValue': str(cell)}}
                            for cell in row]}
                for row in values
            ],
            'fields': 'userEnteredValue'
        }
    }]

    body = {'requests': requests}
    sheets_service.spreadsheets().batchUpdate(
        spreadsheetId=spreadsheet_id,
        body=body
    ).execute()
    return True


def write_google_sheets(spreadsheet_id, sheet_name, values):
    sheets_service = get_google_sheets_service_creds()
    try:
        sheets_service.spreadsheets().values().clear(
            spreadsheetId=spreadsheet_id,
            range=sheet_name
        ).execute()

        body = {
            "values": values
        }

        result = sheets_service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range=f"{sheet_name}!A1",
            valueInputOption="USER_ENTERED",  # Better for parsing dates/numbers
            body=body
        ).execute()
        return True

    except Exception as e:
        print(f"Error writing to Google Sheets: {e}")
        return False

def write_df_to_sheets (spreadsheet_id, range, df):
    try:
        sheets_service = get_google_sheets_service_creds()
        sheets_api = sheets_service.spreadsheets()

        #  Clear the sheet first to remove any old data.
        #  The range should be just the sheet name to clear everything. (Sheet1 for MOST cases)
        sheets_api.values().clear(
            spreadsheetId=spreadsheet_id,
            range=range
        ).execute()
        print(f"Sheet cleared successfully.")

        #  Converts the pandas df to a list of lists acceptable by google sheet's api
        sheet_to_write = [df.columns.tolist()] + df.to_numpy().tolist()

        body = {
            "values": sheet_to_write
        }

        result = sheets_api.values().update(
            spreadsheetId=spreadsheet_id,
            range=range,  # Specifies the top-left cell to start writing from
            valueInputOption="USER_ENTERED",  # This makes Google Sheets interpret data like dates/numbers correctly
            body=body
        ).execute()

        print("cells updated successfully.")
        return True

    except Exception as e:
        print(f"Error writing google sheets: {e}")