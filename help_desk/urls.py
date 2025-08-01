from django.urls import path
from django.views.generic import TemplateView

from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('sheet/<str:sheet_id>/', views.sheet, name='sheet'),
    path('spreadsheet/<str:sheet_id>/', TemplateView.as_view(template_name='index.html'), name='spreadsheet'),

]