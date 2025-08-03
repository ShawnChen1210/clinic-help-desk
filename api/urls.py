from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework.routers import DefaultRouter
from .views import *

router = DefaultRouter()
router.register(r'spreadsheets', SpreadsheetViewSet, basename='spreadsheet') #auto registers url in the form of api/spreadsheets/(insert pk)
urlpatterns = [
    path('hello/', hello_world),
    path('user/', user, name='user'),
    path('', include(router.urls)),
]