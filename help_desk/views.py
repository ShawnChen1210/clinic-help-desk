from django.contrib.auth.decorators import login_required
from django.shortcuts import render
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
        action = request.POST.get('action')
        if action == 'create_spreadsheet':
            sheet_name = request.user.first_name + ' ' + request.user.last_name + ' Spreadsheet'
            test_drive_connection()
            sheet_id = create_new_google_sheet(sheet_name)
            if sheet_id:
                UserSheet.objects.create(user=request.user, sheet_id=sheet_id, sheet_name=sheet_name)
                grant_editor_access(sheet_id, request.user.email) #gives sheet access to the user's email
        elif action == 'browse_drive':
            test_drive_connection()


    spreadsheets = UserSheet.objects.filter(user=request.user)
    return render(request, 'dashboard.html' , {'spreadsheets':spreadsheets})
