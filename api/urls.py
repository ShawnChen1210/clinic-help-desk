from django.urls import path
from rest_framework.routers import DefaultRouter
from rest_framework.routers import DefaultRouter
from .views import *

urlpatterns = [
    path('hello/', hello_world),
    path('user/', user, name='user'),
]