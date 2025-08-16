from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework.routers import DefaultRouter
from .views import *


router = DefaultRouter()
router.register(r'spreadsheets', SpreadsheetViewSet, basename='spreadsheet') #auto registers url in the form of api/spreadsheets/(insert pk)

analytics_router = DefaultRouter()
analytics_router.register(r'analytics', AnalyticsViewSet, basename='analytics') #api/analytics/(insert pk)

members_router = DefaultRouter()
members_router.register(r'members', MemberViewSet, basename='members')

clinic_router = DefaultRouter()
clinic_router.register(r'clinics', ClinicViewSet, basename='clinic')
urlpatterns = [
    path('csrf/', get_csrf, name='get_csrf'),
    path('user/', user, name='user'),
    path('', include(router.urls)),
    path('', include(analytics_router.urls)),

    path('', include(members_router.urls)),
    path('', include(clinic_router.urls)),
]