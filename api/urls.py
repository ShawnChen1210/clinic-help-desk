from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('chd-app/', views.chd_app, name='chd_app'),
]