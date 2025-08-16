from django.urls import path
from django.views.generic import TemplateView

from . import views
from .views import spreadsheet

urlpatterns = [
    path('', views.home, name='home'),
    path('sheet/<str:sheet_id>/', views.sheet, name='sheet'),
    path('spreadsheet/<str:sheet_id>/', views.spreadsheet, name='spreadsheet',),

]