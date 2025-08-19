from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework.routers import DefaultRouter
from .views import *


router = DefaultRouter()
router.register(r'spreadsheets', SpreadsheetViewSet, basename='spreadsheet')
router.register(r'analytics', AnalyticsViewSet, basename='analytics')
router.register(r'members', MemberViewSet, basename='members')
router.register(r'clinics', ClinicViewSet, basename='clinic')
router.register(r'payroll', PayrollViewSet, basename='payroll')

urlpatterns = [
    path('csrf/', get_csrf, name='get_csrf'),
    path('user/', user, name='user'),
    path('', include(router.urls)),
]