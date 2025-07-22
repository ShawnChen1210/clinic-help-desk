from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.http import HttpResponse
from .utils import *
from .forms import *
from .models import *
from .services.google_sheets import *
# Create your views here.

def index(request):
    return render(request, 'index.html')

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
    if user.usersheet_set.filter(id=sheet_id).exists(): #if spreadsheet exists and the sheet belongs to the user
        return render(request, 'sheet.html')
    else:
        return redirect(dashboard)