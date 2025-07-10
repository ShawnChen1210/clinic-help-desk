from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.http import HttpResponse
from .utils import *
from .forms import *
# Create your views here.

def index(request):
    return render(request, 'index.html')