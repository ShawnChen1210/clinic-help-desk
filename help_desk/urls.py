from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('sheet/<str:sheet_id>/', views.sheet, name='sheet'),

]