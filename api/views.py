from django.contrib.auth.decorators import login_required
from django.db.models.functions import Trunc
from django.shortcuts import render
from rest_framework import viewsets, status
from rest_framework.decorators import api_view, action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import SessionAuthentication
from urllib3 import request
import re
from api.serializers import *
from help_desk.models import *
from .services.google_sheets import *
import pandas as pd
import tempfile
from django.middleware.csrf import get_token


# Create your views here.

@api_view(['GET'])
def get_csrf(request):
    """
    A simple view to get the CSRF token.
    """
    token = get_token(request)
    return Response({'csrfToken': token})

@api_view(['GET'])
def user(request):
    serializer = UserSerializer(request.user)
    return Response(serializer.data)


class SpreadsheetViewSet(viewsets.ViewSet):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]

    def detect_merge_column(self, df):
        """
        Detects column with format #####-P## or #####-C##
        Returns column name if found, None otherwise
        """
        pattern = r'^\d{5}-[PC]\d{2}$'

        for col in df.columns:
            # Check if any non-null values in this column match the pattern
            sample_values = df[col].dropna().astype(str).head(10)  # Check first 10 non-null values
            if any(re.match(pattern, str(val)) for val in sample_values):
                return col
        return None

    def extract_sort_key(self, value):
        """
        Extracts the 5-digit number from format #####-P## or #####-C##
        Returns integer for sorting, or float('inf') if invalid format
        """
        if pd.isna(value):
            return float('inf')

        pattern = r'^(\d{5})-[PC]\d{2}$'
        match = re.match(pattern, str(value))
        if match:
            return int(match.group(1))
        return float('inf')

    def merge_dataframes_by_key(self, existing_df, new_df, existing_merge_col, new_merge_col):
        """
        Merge dataframes with the following logic:
        1. If a key exists in both, update the existing row with new data (non-empty values take precedence)
        2. If a key only exists in new_df, add it as a new row
        3. Keep all existing rows, even if not in new_df
        4. Sort final result by the key column
        """
        try:
            print(f"Starting merge - existing shape: {existing_df.shape}, new shape: {new_df.shape}")
            print(f"Existing merge column: {existing_merge_col}, New merge column: {new_merge_col}")

            if existing_df.empty:
                # If no existing data, rename merge column and return sorted new data
                print("No existing data, returning new data")
                new_df_copy = new_df.copy().fillna('')
                if new_merge_col != existing_merge_col:
                    new_df_copy = new_df_copy.rename(columns={new_merge_col: existing_merge_col})

                new_df_copy['_sort_key'] = new_df_copy[existing_merge_col].apply(self.extract_sort_key)
                result = new_df_copy.sort_values('_sort_key').drop('_sort_key', axis=1)
                return result

            # Clean data - replace NaN with empty strings and create copies
            existing_df = existing_df.copy().fillna('')
            new_df = new_df.copy().fillna('')

            # Rename new merge column to match existing if different
            if new_merge_col != existing_merge_col and new_merge_col in new_df.columns:
                new_df = new_df.rename(columns={new_merge_col: existing_merge_col})
                print(f"Renamed merge column from {new_merge_col} to {existing_merge_col}")

            # Create a combined column set
            all_columns = list(existing_df.columns)
            for col in new_df.columns:
                if col not in all_columns:
                    all_columns.append(col)

            print(f"All columns after merge: {all_columns}")

            # Convert dataframes to dictionaries for easier manipulation
            existing_dict = {}
            for _, row in existing_df.iterrows():
                key = str(row[existing_merge_col]).strip()
                if key and key != 'nan':  # Skip empty or nan keys
                    existing_dict[key] = row.to_dict()

            new_dict = {}
            for _, row in new_df.iterrows():
                key = str(row[existing_merge_col]).strip()
                if key and key != 'nan':  # Skip empty or nan keys
                    new_dict[key] = row.to_dict()

            print(f"Existing keys: {len(existing_dict)}, New keys: {len(new_dict)}")

            # Process all keys (existing and new)
            all_keys = set(existing_dict.keys()) | set(new_dict.keys())
            result_data = []

            for key in all_keys:
                merged_row = {}

                # Initialize with empty values for all columns
                for col in all_columns:
                    merged_row[col] = ''

                # Start with existing data if available
                if key in existing_dict:
                    for col, val in existing_dict[key].items():
                        merged_row[col] = str(val) if val is not None else ''

                # Update/overwrite with new data if available
                if key in new_dict:
                    for col, val in new_dict[key].items():
                        val_str = str(val) if val is not None else ''
                        # Only update if new value is not empty, or if existing value is empty
                        if val_str != '' or merged_row.get(col, '') == '':
                            merged_row[col] = val_str

                result_data.append(merged_row)

            # Create result dataframe
            result_df = pd.DataFrame(result_data, columns=all_columns)

            # Sort by merge column
            result_df['_sort_key'] = result_df[existing_merge_col].apply(self.extract_sort_key)
            result_df = result_df.sort_values('_sort_key').drop('_sort_key', axis=1)

            print(f"Final merged dataframe shape: {result_df.shape}")
            return result_df.fillna('')

        except Exception as e:
            print(f"Error in merge_dataframes_by_key: {str(e)}")
            print(f"Error type: {type(e).__name__}")
            raise e

    # DEFAULT GET: for retrieving a whole spreadsheet from google sheets for display in the frontend
    def retrieve(self, request, pk=None):
        print(f"retrieving table data, pk is: {pk}")
        print(f"User: {request.user}")

        sheet_id = pk
        user = request.user

        # Check if user is authenticated
        if not user.is_authenticated:
            return Response(
                {'error': 'Authentication required'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        # Check if UserSheet exists for this user and sheet_id
        usersheet_queryset = user.usersheet_set.filter(sheet_id=sheet_id)
        print(f"UserSheet queryset count: {usersheet_queryset.count()}")

        if not usersheet_queryset.exists():
            # Debug: Show all sheets for this user
            all_user_sheets = user.usersheet_set.all()
            print(f"User has access to {all_user_sheets.count()} sheets:")
            for sheet in all_user_sheets:
                print(f"  - Sheet ID: {sheet.sheet_id}")

            return Response(
                {'error': f'Sheet with ID {sheet_id} not found or no permission for user {user.username}'},
                status=status.HTTP_404_NOT_FOUND
            )

        usersheet = usersheet_queryset.first()
        print(f"Found UserSheet: {usersheet.sheet_name}")

        try:
            # Fetch fresh data from Google Sheets
            print(f"Fetching data from Google Sheets for ID: {sheet_id}")
            sheet_data, sheet_header = padded_google_sheets(sheet_id, 'Sheet1')
            print(f"Successfully fetched {len(sheet_data)} rows of data")

            return Response({
                'success': True,
                'sheet_data': sheet_data,
                'sheet_header': sheet_header,
                'sheet_name': usersheet.sheet_name,
                'sheet_date': usersheet.created_at,
                'sheet_id': sheet_id,
                'merge_column': getattr(usersheet, 'merge_column', None)  # Return stored merge column
            }, status=status.HTTP_200_OK)

        except Exception as e:
            print(f"Error fetching Google Sheets data: {str(e)}")
            print(f"Exception type: {type(e).__name__}")
            return Response(
                {'error': f'Failed to fetch sheet data: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    # For checking if the user is allowed access to the spreadsheet before uploading
    @action(detail=True, methods=['GET'])
    def check_perms(self, request, pk=None):
        print("checking permissions")
        user = request.user
        if user.usersheet_set.filter(sheet_id=pk).exists():
            return Response(
                {'success': True},
                status=status.HTTP_200_OK
            )
        else:
            return Response(
                {'success': False},
                status=status.HTTP_401_UNAUTHORIZED
            )

    @action(detail=True, methods=['POST'])
    def upload_csv(self, request, pk=None):
        uploaded_file = request.FILES.get('file')
        if not uploaded_file:
            return Response({'error': 'no file provided'}, status=status.HTTP_400_BAD_REQUEST)

        temp_file_path = ''
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.csv') as temp_file:
                for chunk in uploaded_file.chunks():
                    temp_file.write(chunk)
                temp_file_path = temp_file.name

            # Read the uploaded CSV
            uploaded_df = pd.read_csv(temp_file_path).fillna('')

            # Get existing sheet data
            sheet_data, sheet_headers = padded_google_sheets(pk, 'A1:Z5')

            # FIRST UPLOAD CASE
            if not sheet_data and not sheet_headers:
                # Detect merge column in the uploaded file
                merge_column = self.detect_merge_column(uploaded_df)

                if not merge_column:
                    return Response({
                        'error': 'No column with required format (#####-P## or #####-C##) found'
                    }, status=status.HTTP_400_BAD_REQUEST)

                # Store merge column in UserSheet model
                usersheet = request.user.usersheet_set.get(sheet_id=pk)
                usersheet.merge_column = merge_column
                usersheet.save()

                # Sort by the merge column before uploading
                uploaded_df['_sort_key'] = uploaded_df[merge_column].apply(self.extract_sort_key)
                uploaded_df = uploaded_df.sort_values('_sort_key').drop('_sort_key', axis=1)

                data_to_upload = [uploaded_df.columns.tolist()] + uploaded_df.values.tolist()
                write_google_sheets(pk, 'Sheet1', data_to_upload)

                return Response({
                    'status': 'first_upload_complete',
                    'merge_column': merge_column
                }, status=status.HTTP_200_OK)

            # SUBSEQUENT UPLOADS
            else:
                # Get stored merge column
                usersheet = request.user.usersheet_set.get(sheet_id=pk)
                stored_merge_column = getattr(usersheet, 'merge_column', None)

                if not stored_merge_column:
                    return Response({
                        'error': 'No merge column stored for this sheet'
                    }, status=status.HTTP_400_BAD_REQUEST)

                # Detect merge column in uploaded file
                uploaded_merge_column = self.detect_merge_column(uploaded_df)

                if not uploaded_merge_column:
                    return Response({
                        'error': 'No column with required format found in uploaded file'
                    }, status=status.HTTP_400_BAD_REQUEST)

                request.session['temp_file_path'] = temp_file_path
                request.session['uploaded_merge_column'] = uploaded_merge_column
                request.session['stored_merge_column'] = stored_merge_column

                return Response({
                    'success': True,
                    'headers': uploaded_df.columns.tolist(),
                    'body': uploaded_df.head(5).to_dict(orient='records'),
                    'sheet_data': sheet_data,
                    'sheet_headers': sheet_headers,
                    'uploaded_merge_column': uploaded_merge_column,
                    'stored_merge_column': stored_merge_column,
                }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['POST'])
    def merge_sheets(self, request, pk=None):
        try:
            sheet_id = pk
            sheet_name = 'Sheet1'

            # Get merge columns from session
            uploaded_merge_column = request.session.get('uploaded_merge_column')
            stored_merge_column = request.session.get('stored_merge_column')
            temp_file_path = request.session.get('temp_file_path')

            print(f"Session data - uploaded_merge_column: {uploaded_merge_column}")
            print(f"Session data - stored_merge_column: {stored_merge_column}")
            print(f"Session data - temp_file_path: {temp_file_path}")

            if not all([uploaded_merge_column, stored_merge_column, temp_file_path]):
                return Response({
                    'error': 'Missing session data for merge operation'
                }, status=status.HTTP_400_BAD_REQUEST)

            # Verify temp file exists
            if not os.path.exists(temp_file_path):
                return Response({
                    'error': 'Temporary file not found'
                }, status=status.HTTP_400_BAD_REQUEST)

            # Get existing spreadsheet data
            print("Fetching existing spreadsheet data...")
            left_spreadsheet, left_spreadsheet_headers = padded_google_sheets(sheet_id, sheet_name)
            print(f"Existing data - rows: {len(left_spreadsheet)}, headers: {left_spreadsheet_headers}")

            # Create existing dataframe
            if left_spreadsheet and left_spreadsheet_headers:
                existing_df = pd.DataFrame(left_spreadsheet, columns=left_spreadsheet_headers)
            else:
                existing_df = pd.DataFrame()

            # Read uploaded CSV
            print(f"Reading uploaded CSV from: {temp_file_path}")
            uploaded_df = pd.read_csv(temp_file_path).fillna('')
            print(f"Uploaded data - rows: {len(uploaded_df)}, columns: {list(uploaded_df.columns)}")

            # Verify merge columns exist
            if not existing_df.empty and stored_merge_column not in existing_df.columns:
                return Response({
                    'error': f'Stored merge column "{stored_merge_column}" not found in existing data. Available columns: {list(existing_df.columns)}'
                }, status=status.HTTP_400_BAD_REQUEST)

            if uploaded_merge_column not in uploaded_df.columns:
                return Response({
                    'error': f'Upload merge column "{uploaded_merge_column}" not found in uploaded data. Available columns: {list(uploaded_df.columns)}'
                }, status=status.HTTP_400_BAD_REQUEST)

            # Use the new merge logic
            print("Starting merge process...")
            merged_df = self.merge_dataframes_by_key(
                existing_df,
                uploaded_df,
                stored_merge_column,  # Column name to use in final result
                uploaded_merge_column  # Column name in uploaded data
            )

            print(f"Merge completed. Final shape: {merged_df.shape}")

            merged_headers = merged_df.columns.tolist()
            merged_data = merged_df.fillna('').replace([float('inf'), float('-inf')], '').to_dict(orient='records')

            # Store merged data temporarily
            with tempfile.NamedTemporaryFile(delete=False, suffix='.csv', mode='w+', newline='') as temp_file:
                merged_df.to_csv(temp_file, index=False)
                merged_data_path = temp_file.name

            request.session['merged_data_path'] = merged_data_path

            return Response({
                'success': True,
                'merged_headers': merged_headers,
                'merged_data': merged_data,
                'merge_strategy': 'Key-based merge with update/insert logic'
            }, status=status.HTTP_200_OK)

        except Exception as e:
            print(f"Error in merge_sheets: {str(e)}")
            print(f"Error type: {type(e).__name__}")
            import traceback
            print(f"Full traceback: {traceback.format_exc()}")
            return Response({
                'error': f"Failed to merge sheets: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['POST'])
    def confirm_merge_sheets(self, request, pk=None):
        merged_data_path = request.session.get('merged_data_path')
        temp_file_path = request.session.get('temp_file_path')

        if not merged_data_path or not os.path.exists(merged_data_path):
            return Response({'error': 'No merge data found or session expired.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Read the merged data
            merged_df = pd.read_csv(merged_data_path, encoding='latin1').fillna('')

            # Write to Google Sheets
            write_df_to_sheets(pk, 'Sheet1', merged_df)

            return Response({
                'success': True,
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {'error': f"Failed to confirm merge: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        finally:
            # TEMP FILE CLEANUP
            print("Cleaning up temporary files and session data...")
            if merged_data_path and os.path.exists(merged_data_path):
                os.remove(merged_data_path)
            if temp_file_path and os.path.exists(temp_file_path):
                os.remove(temp_file_path)

            # Clean up session variables
            session_keys = ['merged_data_path', 'temp_file_path', 'uploaded_merge_column', 'stored_merge_column']
            for key in session_keys:
                if key in request.session:
                    del request.session[key]

    @action(detail=True, methods=['POST'])
    def delete_session_storage(self, request, pk=None):
        try:
            merged_data_path = request.session.get('merged_data_path')
            temp_file_path = request.session.get('temp_file_path')

            if merged_data_path and os.path.exists(merged_data_path):
                os.remove(merged_data_path)
            if temp_file_path and os.path.exists(temp_file_path):
                os.remove(temp_file_path)

            # Clean up all related session variables
            session_keys = ['merged_data_path', 'temp_file_path', 'uploaded_merge_column', 'stored_merge_column']
            for key in session_keys:
                if key in request.session:
                    del request.session[key]

            return Response({
                'success': True,
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {'error': f"Failed to delete temporary files: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class AnalyticsViewSet(viewsets.ViewSet):
    column_pref_queryset = SheetColumnPreference.objects.all()
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]

    # DEFAULT GET FUNCTION FOR GETTING USER PREFERENCES
    def retrieve(self, request, pk=None):
        sheet_id = pk
        user = request.user

        try:
            preference = SheetColumnPreference.objects.get(user=user, sheet_id=sheet_id)
            serializer = SheetColumnPreferenceSerializer(preference)
            return Response(serializer.data)

        except SheetColumnPreference.DoesNotExist:
            # 4. If no preference is found, return a 404 error
            return Response(
                {'error': 'No preferences found for this sheet.'},
                status=status.HTTP_404_NOT_FOUND
            )

    # DEFAULT POST REQUEST FOR SETTING USER PREFERENCES
    def create(self, request, pk=None):
        sheet_id = pk
        user = request.user
        date_column = request.data.get('date_column')
        income_columns = request.data.get('income_columns')

        if not date_column or not income_columns:
            return Response(
                {'error': 'Both date_column and income_columns must be provided.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # This is the core logic. It finds a preference matching the user and sheet_id,
            # or creates a new one if it doesn't exist.
            preference, created = SheetColumnPreference.objects.update_or_create(
                user=user,
                sheet_id=sheet_id,
                defaults={
                    'date_column': date_column,
                    'income_columns': income_columns,
                }
            )

            status_text = "created" if created else "updated"
            return Response({'status': f'Preference {status_text} successfully'}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['POST'])
    def income_summary(self, request, pk=None):
        try:
            sheet_data, sheet_headers = padded_google_sheets(pk, 'Sheet1')
            date_column = request.data.get('date_column')
            income_columns = request.data.get('income_columns')
            if not sheet_data:
                return Response({
                    'weekly': [],
                    'monthly': [],
                    'yearly': [],
                })

            df = pd.DataFrame(sheet_data, columns=sheet_headers)
            actual_columns = set(df.columns)

            # Check if the provided column names are valid
            if date_column not in actual_columns:
                return Response({'error': f"The date column '{date_column}' was not found in the sheet."}, status=400)

            for col in income_columns:
                if col not in actual_columns:
                    return Response({'error': f"The income column '{col}' was not found in the sheet."}, status=400)

            #data preparation
            try:
                df[date_column] = pd.to_datetime(df[date_column])
                for income_column in income_columns:
                    df[income_column] = pd.to_numeric(df[income_column])
            except Exception as e:
                return Response(
                    {'error': f"Failed to convert columns. Ensure data is in the correct format. Details: {e}"},
                    status=400)
            df.set_index(date_column, inplace=True)
            income_df = df[income_columns]

            #Resample and sum each income column for each time period
            weekly_subtotals = income_df.resample('W').sum()
            monthly_subtotals = income_df.resample('M').sum()
            yearly_subtotals = income_df.resample('Y').sum()

            #Sum the columns together to get a single total for each time period
            #axis=1 tells pandas to sum horizontally (across the columns)
            weekly_totals = weekly_subtotals.sum(axis=1).rename('Total Income')
            monthly_totals = monthly_subtotals.sum(axis=1).rename('Total Income')
            yearly_totals = yearly_subtotals.sum(axis=1).rename('Total Income')

            #formats total number to format for react charts
            def format_report(series, date_format):
                report_df = series.reset_index()
                report_df[date_column] = report_df[date_column].dt.strftime(date_format)
                return report_df.to_dict(orient='records')

            return Response({
                'weeklyReport': format_report(weekly_totals, '%Y-%m-%d'),
                'monthlyReport': format_report(monthly_totals, '%Y-%m'),
                'yearlyReport': format_report(yearly_totals, '%Y'),
            })
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['GET'])
    def get_sheet_headers(self, request, pk=None):
        try:
            sheet_data, sheet_headers = padded_google_sheets(pk, 'A1:Z2')
            return Response(
                {'columns': sheet_headers},
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )




