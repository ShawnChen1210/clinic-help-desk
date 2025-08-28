from ..utils import *
from clinic_help_desk.settings import *
import csv
import traceback
import pandas as pd

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


# Add this function to your api/services/google_sheets.py file
# Make sure you have pandas installed (pip install pandas) and imported (import pandas as pd)

def colnum_string(n):
    """Converts a 1-based column index into an A1 notation string (e.g., 1 -> A, 27 -> AA)."""
    string = ""
    while n > 0:
        n, remainder = divmod(n - 1, 26)
        string = chr(65 + remainder) + string
    return string


def read_sheet_by_date_range(sheet_id, date_column_name, start_date, end_date, sheet_name="Sheet1"):
    """
    Efficiently reads a Google Sheet by filtering rows based on a date range in a specified column.
    """
    # --- Step 0: Log Initial Call ---
    print(f"\n[DEBUG] --- Starting read_sheet_by_date_range ---")
    print(f"[DEBUG] Sheet ID: {sheet_id}")
    print(f"[DEBUG] Sheet Name: '{sheet_name}'")
    print(f"[DEBUG] Date Column: '{date_column_name}'")
    print(f"[DEBUG] Date Range: {start_date} to {end_date}")

    try:
        sheets_service = get_google_sheets_service_creds()
        spreadsheets_api = sheets_service.spreadsheets()

        # --- Step 1: Get header to find the date column index ---
        header_range = f"'{sheet_name}'!1:1"
        header_result = spreadsheets_api.values().get(spreadsheetId=sheet_id, range=header_range).execute()
        header = header_result.get('values', [[]])[0]

        if not header:
            print("[DEBUG] ‼️ FAILED: Sheet header is empty or sheet tab not found.")
            return pd.DataFrame()
        print(f"[DEBUG] Found header with {len(header)} columns.")

        try:
            date_col_index = header.index(date_column_name)
            date_col_letter = colnum_string(date_col_index + 1)
            print(f"[DEBUG] Date column '{date_column_name}' is at index {date_col_index} (Column {date_col_letter}).")
        except ValueError:
            print(f"[DEBUG] ‼️ FAILED: Date column '{date_column_name}' not found in sheet header.")
            return pd.DataFrame()

        # --- Step 2: Fetch the entire date column for efficient filtering ---
        date_column_range = f"'{sheet_name}'!{date_col_letter}2:{date_col_letter}"
        date_result = spreadsheets_api.values().get(spreadsheetId=sheet_id, range=date_column_range).execute()
        date_values = date_result.get('values', [])

        if not date_values:
            print("[DEBUG] No data found in the date column.")
            return pd.DataFrame()
        print(f"[DEBUG] Fetched {len(date_values)} total rows from date column.")

        # --- Step 3: Use pandas to identify matching row numbers ---
        df = pd.DataFrame(date_values, columns=['date_str'])
        df['row_num'] = range(2, len(df) + 2)
        df['date'] = pd.to_datetime(df['date_str'], errors='coerce')

        parsing_errors = df['date'].isna().sum()
        if parsing_errors > 0:
            print(f"[DEBUG] Warning: Could not parse {parsing_errors} date values.")

        df.dropna(subset=['date'], inplace=True)
        print(f"[DEBUG] Successfully parsed {len(df)} valid dates.")

        start_date_ts = pd.Timestamp(start_date)
        end_date_ts = pd.Timestamp(end_date)

        matching_rows = df[
            (df['date'].dt.date >= start_date_ts.date()) &
            (df['date'].dt.date <= end_date_ts.date())
            ]['row_num'].tolist()

        if not matching_rows:
            print(f"[DEBUG] Found 0 rows matching the date range.")
            return pd.DataFrame()
        print(f"[DEBUG] Found {len(matching_rows)} rows matching the date range.")

        # --- Step 4: Group consecutive row numbers into blocks ---
        row_groups = []
        if matching_rows:
            start_of_block = matching_rows[0]
            for i in range(1, len(matching_rows)):
                if matching_rows[i] != matching_rows[i - 1] + 1:
                    row_groups.append((start_of_block, matching_rows[i - 1]))
                    start_of_block = matching_rows[i]
            row_groups.append((start_of_block, matching_rows[-1]))
        print(f"[DEBUG] Grouped rows into {len(row_groups)} blocks: {row_groups}")

        # --- Step 5: Construct ranges and batch-fetch the data ---
        # FIXED: Use the helper function to correctly get column letters beyond Z
        last_col_letter = colnum_string(len(header))
        ranges_to_fetch = [f"'{sheet_name}'!A{start}:{last_col_letter}{end}" for start, end in row_groups]
        print(f"[DEBUG] Constructed {len(ranges_to_fetch)} ranges for batch fetch: {ranges_to_fetch}")

        batch_get_result = spreadsheets_api.values().batchGet(spreadsheetId=sheet_id, ranges=ranges_to_fetch).execute()

        # --- Step 6: Combine results into a single DataFrame ---
        all_data = []
        for value_range in batch_get_result.get('valueRanges', []):
            all_data.extend(value_range.get('values', []))
        print(f"[DEBUG] Batch fetch returned a total of {len(all_data)} rows.")

        final_df = pd.DataFrame(all_data)

        # Robustly assign header, padding missing values with empty strings
        if not final_df.empty:
            final_df.columns = header[:len(final_df.columns)]
            # Add any missing columns that should have been in the data
            if len(final_df.columns) < len(header):
                for col in header[len(final_df.columns):]:
                    final_df[col] = ''

        print(f"[DEBUG] ✅ Success! Returning DataFrame with shape: {final_df.shape}")
        return final_df

    except Exception as e:
        print(f"[DEBUG] ‼️ FAILED: An unexpected error occurred.")
        print(f"[DEBUG] Error: {e}")
        traceback.print_exc()
        return pd.DataFrame()