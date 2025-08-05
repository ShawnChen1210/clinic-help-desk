from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.http import HttpResponse
from .utils import *
from .forms import *
from .models import *
from .services.google_sheets import *
import pandas as pd
import tempfile
from django.middleware.csrf import get_token

# Create your views here.

def home(request):
    return render(request, 'home.html')

@login_required(login_url='login_user')
def dashboard(request):
    if request.method == 'POST':
        user = request.user
        action = request.POST.get('action')
        if action == 'create_spreadsheet':
            sheet_name = request.POST.get('sheet_name')
            test_drive_connection()
            sheet_id = create_new_google_sheet(sheet_name)
            if sheet_id:
                UserSheet.objects.create(user=request.user, sheet_id=sheet_id, sheet_name=sheet_name)
                grant_editor_access(sheet_id, request.user.email) #gives sheet access to the user's email

        elif action == 'browse_drive':
            test_drive_connection()

        elif action == 'delete_spreadsheet' or action == 'rename_spreadsheet':
            spreadsheet_id = request.POST.get('spreadsheet_id')
            if user.usersheet_set.filter(id=spreadsheet_id).exists():
                UserSheetObj = UserSheet.objects.get(id=spreadsheet_id)
                if action == 'delete_spreadsheet': #confirm if the user does own the spreadsheet
                    delete_google_sheet(UserSheetObj.sheet_id)
                    UserSheetObj.delete()
                elif action == 'rename_spreadsheet':
                    rename_google_sheet(UserSheetObj.sheet_id, spreadsheet_id)



    spreadsheets = UserSheet.objects.filter(user=request.user)
    return render(request, 'dashboard.html' , {'spreadsheets':spreadsheets})

def sheet(request, sheet_id):
    user = request.user
    if request.method == 'POST':
        if 'upload_file' in request.POST and 'uploaded_file' in request.FILES: #if the user uploads a file
            print("uploading file")
            uploaded_file = request.FILES['uploaded_file']

            # Clean up any existing temp file
            old_temp_file = request.session.get('temp_file_path')
            if old_temp_file and os.path.exists(old_temp_file):
                os.remove(old_temp_file)

            temp_file_path, headers = handle_file_upload(uploaded_file) #upload file function

            uploaded_df = pd.read_csv(temp_file_path).fillna('') #create pandas dataframe from uploaded csv
            uploaded_headers = uploaded_df.columns.tolist()

            messages.success(request, 'upload_success')
            request.session['temp_file_path'] = temp_file_path
            request.session['uploaded_header'] = uploaded_headers #stores headers of the uploaded csv in session storage

            return redirect('sheet', sheet_id=sheet_id)

        elif request.POST.get('action') == 'select_column': #user selected column to use as merge key

            sheet_data = request.session['recent_sheet_data']
            sheet_header = request.session['recent_sheet_header']
            temp_file_path = request.session['temp_file_path']

            df_left = pd.DataFrame(sheet_data, columns=sheet_header)
            df_right = pd.read_csv(temp_file_path).fillna('')


            result = pd.merge(df_left, df_right, on=request.POST.get('selected_header'), how=request.POST.get('header_side'))

            # Always delete the temp file
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)

            #claer the cache so new data gets served to html
            if 'recent_sheet_data' in request.session:
                del request.session['recent_sheet_data']
            if 'recent_sheet_header' in request.session:
                del request.session['recent_sheet_header']

    if user.usersheet_set.filter(sheet_id=sheet_id).exists(): #if spreadsheet exists and the sheet belongs to the user
        #if there is a sheet in the session
        if 'recent_sheet_data' in request.session and 'recent_sheet_header' in request.session:
            sheet_data = request.session['recent_sheet_data']
            sheet_header = request.session['recent_sheet_header']
            usersheet = user.usersheet_set.get(sheet_id=sheet_id)
        #if it's the first time loading the sheet in the session
        else:
            sheet_data, sheet_header = padded_google_sheets(sheet_id,'A1:Z50')
            usersheet = user.usersheet_set.get(sheet_id=sheet_id)

            request.session['recent_sheet_header'] = sheet_header
            request.session['recent_sheet_data'] = sheet_data

        if 'uploaded_header' in request.session: #if we are on the join tables step of the upload process and have headers from the uploaded file
            uploaded_header = request.session['uploaded_header']
        else:
            uploaded_header = []

        return render(request, 'sheet.html', {
            'sheet_data': sheet_data,
            'sheet_name': usersheet.sheet_name,
            'sheet_date': usersheet.created_at,
            'sheet_header': sheet_header,
            'sheet_id': sheet_id,
            'uploaded_header': uploaded_header
        })

    else:
        return HttpResponse('Sheet Not Found or No Permission', status=403)


def handle_file_upload(uploaded_file):
    """
    Process uploaded CSV file and return temp file path and headers
    Returns: (temp_file_path, headers) or raises ValueError on error
    """
    # Validate file
    if not uploaded_file.name.endswith('.csv'):
        raise ValueError("Only CSV files are supported")

    if uploaded_file.size > 5 * 1024 * 1024:  # 5MB limit
        raise ValueError("File size must be under 5MB")

    # Create temp file
    with tempfile.NamedTemporaryFile(delete=False, suffix='.csv') as temp_file:
        for chunk in uploaded_file.chunks():
            temp_file.write(chunk)
        temp_file_path = temp_file.name

    try:
        # Read headers to validate CSV
        df_sample = pd.read_csv(temp_file_path, nrows=0)  # Just headers
        headers = df_sample.columns.tolist()
        return temp_file_path, headers
    except Exception as e:
        # Clean up file if CSV is invalid
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        raise ValueError(f"Invalid CSV file: {str(e)}")

def spreadsheet(request, sheet_id):
    csrf_token = get_token(request)
    return render(request, 'index.html', context={'csrf_token': csrf_token})