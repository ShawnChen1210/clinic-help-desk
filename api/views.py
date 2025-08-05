from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from rest_framework import viewsets, status
from rest_framework.decorators import api_view, action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import SessionAuthentication
from api.serializers import UserSerializer
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
            sheet_data, sheet_header = padded_google_sheets(sheet_id, 'A1:Z50')
            print(f"Successfully fetched {len(sheet_data)} rows of data")

            return Response({
                'success': True,
                'sheet_data': sheet_data,
                'sheet_header': sheet_header,
                'sheet_name': usersheet.sheet_name,
                'sheet_date': usersheet.created_at,
                'sheet_id': sheet_id,
            }, status=status.HTTP_200_OK)

        except Exception as e:
            print(f"Error fetching Google Sheets data: {str(e)}")
            print(f"Exception type: {type(e).__name__}")
            return Response(
                {'error': f'Failed to fetch sheet data: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    #For checking if the user is allowed access to the spreadsheet before uploading
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
            return Response(
                {'error': 'no file provided'},
                status=status.HTTP_400_BAD_REQUEST
            )
        # Create temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.csv') as temp_file:
            for chunk in uploaded_file.chunks():
                temp_file.write(chunk)
            temp_file_path = temp_file.name

        try:
            df = pd.read_csv(temp_file_path).fillna('')
            headers = df.columns.tolist() # Just headers
            body = df.head(2).to_dict(orient='records') # first 2 rows of the csv file

            sheet_data, sheet_headers = padded_google_sheets(pk, 'A1:Z3') #returns the headers and 2 extra rows of data from google sheets. This will be processed in the frontend

            request.session['temp_file_path'] = temp_file_path #saves temp file path to session
            return Response({
                'success': True,
                'headers': headers,
                'body': body,
                'sheet_data': sheet_data,
                'sheet_headers': sheet_headers,
            }, status=status.HTTP_200_OK)

        except Exception as e:
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)
            return Response({'error': f"Invalid CSV file: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['POST'])
    def merge_sheets(self, request, pk=None):
        try:
            left_column = request.data.get('left_column')
            right_column = request.data.get('right_column')
            sheet_id = pk
            sheet_name = 'Sheet1'
            #IMPORTANT: every user creates their own google sheet file with every spreadsheet created,
            #thus their sheet tab name is all Sheet1. this 'Sheet1' is used to read all data from a google sheet file tab.

            left_spreadsheet, left_spreadsheet_headers = padded_google_sheets(sheet_id, sheet_name) #returns the entire table
            temp_file_path = request.session.get('temp_file_path') #uploaded csv file path

            left_df = pd.DataFrame(left_spreadsheet, columns=left_spreadsheet_headers)
            right_df = pd.read_csv(temp_file_path)

            #IMPORTANT: THE DEFAULT MERGE IS A LEFT SQL JOIN
            merged_df = pd.merge(left_df, right_df, how='left', left_on=left_column, right_on=right_column)
            merged_df = merged_df.where(pd.notnull(merged_df), None)

            merged_headers = merged_df.columns.tolist()
            merged_data = merged_df.to_dict(orient='records')

            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)
                # Remove the path from the session
            if 'temp_file_path' in request.session:
                del request.session['temp_file_path']

            return Response({
                'success': True,
                'merged_headers': merged_headers,
                'merged_data': merged_data,
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {'error': f"Failed to merge sheets: {str(e)}"},
            )


